import json
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.config import settings
from core.rate_limit import limiter
from core.security import require_admin
from models.posts import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Not an admin"},
}


# ─── Response Models ─────────────────────────────────────────


class GA4Summary(BaseModel):
    pageviews: int = 0
    sessions: int = 0
    users: int = 0
    avg_session_duration: float = 0.0
    bounce_rate: float = 0.0


class GA4DailyRow(BaseModel):
    date: str
    pageviews: int


class GA4PageRow(BaseModel):
    page: str
    pageviews: int
    sessions: int


class GA4SourceRow(BaseModel):
    source: str
    sessions: int


class GA4CountryRow(BaseModel):
    country: str
    sessions: int


class GA4Response(BaseModel):
    period_start: str
    period_end: str
    summary: GA4Summary
    daily_pageviews: list[GA4DailyRow]
    top_pages: list[GA4PageRow]
    traffic_sources: list[GA4SourceRow]
    countries: list[GA4CountryRow]


# ─── Helpers ─────────────────────────────────────────────────


def _build_ga4_client():
    """Build an authenticated GA4 BetaAnalyticsDataClient."""
    if not settings.ga4_credentials_json:
        raise HTTPException(
            status_code=503,
            detail="GA4_CREDENTIALS_JSON not configured",
        )
    if not settings.ga4_property_id:
        raise HTTPException(
            status_code=503,
            detail="GA4_PROPERTY_ID not configured",
        )

    try:
        creds_dict = json.loads(settings.ga4_credentials_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=503,
            detail="GA4_CREDENTIALS_JSON is not valid JSON",
        )

    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_info(creds_dict)
    return BetaAnalyticsDataClient(credentials=credentials)


# ─── Endpoint ────────────────────────────────────────────────


@router.get(
    "/ga4-analytics",
    response_model=GA4Response,
    responses=ERROR_RESPONSES,
)
@limiter.limit("10/minute")
async def get_ga4_analytics(
    request: Request,
    days: int = 30,
    _user=Depends(require_admin),
):
    """Fetch GA4 analytics data for the admin dashboard."""
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )

    client = _build_ga4_client()
    property_id = f"properties/{settings.ga4_property_id}"
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    date_range = DateRange(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    try:
        # ── 1. Summary metrics ───────────────────────────────
        summary_resp = client.run_report(
            RunReportRequest(
                property=property_id,
                date_ranges=[date_range],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate"),
                ],
            )
        )
        summary = GA4Summary()
        if summary_resp.rows:
            vals = summary_resp.rows[0].metric_values
            summary = GA4Summary(
                pageviews=int(vals[0].value),
                sessions=int(vals[1].value),
                users=int(vals[2].value),
                avg_session_duration=round(float(vals[3].value), 1),
                bounce_rate=round(float(vals[4].value), 4),
            )

        # ── 2. Daily pageviews ───────────────────────────────
        daily_resp = client.run_report(
            RunReportRequest(
                property=property_id,
                date_ranges=[date_range],
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="screenPageViews")],
                order_bys=[
                    {
                        "dimension": {"dimension_name": "date"},
                        "desc": False,
                    }
                ],
            )
        )
        daily_pageviews = []
        for row in daily_resp.rows:
            raw = row.dimension_values[0].value  # "20260314"
            formatted = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
            daily_pageviews.append(
                GA4DailyRow(
                    date=formatted,
                    pageviews=int(row.metric_values[0].value),
                )
            )

        # ── 3. Top pages ─────────────────────────────────────
        pages_resp = client.run_report(
            RunReportRequest(
                property=property_id,
                date_ranges=[date_range],
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                ],
                order_bys=[
                    {
                        "metric": {"metric_name": "screenPageViews"},
                        "desc": True,
                    }
                ],
                limit=10,
            )
        )
        top_pages = [
            GA4PageRow(
                page=row.dimension_values[0].value,
                pageviews=int(row.metric_values[0].value),
                sessions=int(row.metric_values[1].value),
            )
            for row in pages_resp.rows
        ]

        # ── 4. Traffic sources ───────────────────────────────
        sources_resp = client.run_report(
            RunReportRequest(
                property=property_id,
                date_ranges=[date_range],
                dimensions=[Dimension(name="sessionDefaultChannelGroup")],
                metrics=[Metric(name="sessions")],
                order_bys=[
                    {
                        "metric": {"metric_name": "sessions"},
                        "desc": True,
                    }
                ],
                limit=10,
            )
        )
        traffic_sources = [
            GA4SourceRow(
                source=row.dimension_values[0].value,
                sessions=int(row.metric_values[0].value),
            )
            for row in sources_resp.rows
        ]

        # ── 5. Countries ─────────────────────────────────────
        countries_resp = client.run_report(
            RunReportRequest(
                property=property_id,
                date_ranges=[date_range],
                dimensions=[Dimension(name="country")],
                metrics=[Metric(name="sessions")],
                order_bys=[
                    {
                        "metric": {"metric_name": "sessions"},
                        "desc": True,
                    }
                ],
                limit=10,
            )
        )
        countries = [
            GA4CountryRow(
                country=row.dimension_values[0].value,
                sessions=int(row.metric_values[0].value),
            )
            for row in countries_resp.rows
        ]

    except Exception as exc:
        logger.error("GA4 API error: %s", exc)
        raise HTTPException(status_code=502, detail=f"GA4 API error: {exc}")

    return GA4Response(
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        summary=summary,
        daily_pageviews=daily_pageviews,
        top_pages=top_pages,
        traffic_sources=traffic_sources,
        countries=countries,
    )
