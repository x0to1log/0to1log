"""Persistence and notification helpers for the news pipeline.

Contains:
  - promote_drafts: scheduled draft -> published promotion logic
  - _send_draft_alert: email/Slack alert when digest saved as draft
  - _notify_auto_publish: notification when draft auto-published
  - _fetch_week_digests, _fetch_week_handbook_terms: weekly aggregation helpers
  - _send_weekly_email: weekly recap email sender

Extracted from pipeline.py during 2026-04-15 news-pipeline-hardening Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import settings, today_kst
from core.database import get_supabase

logger = logging.getLogger(__name__)


async def _send_draft_alert(batch_id: str, digest_type: str, quality_score: int | None) -> None:
    """Send email alert when a digest is saved as draft (below auto-publish threshold)."""
    if not settings.resend_api_key or not settings.admin_email:
        logger.info("Draft alert skipped — resend_api_key or admin_email not configured")
        return
    try:
        import httpx
        await httpx.AsyncClient().post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": "0to1log <noreply@0to1log.com>",
                "to": [settings.admin_email],
                "subject": f"[0to1log] Draft alert: {batch_id} {digest_type} (score: {quality_score})",
                "text": (
                    f"{batch_id} {digest_type} scored {quality_score}/100 "
                    f"(threshold: {settings.auto_publish_threshold}).\n\n"
                    f"Saved as draft — manual review required.\n\n"
                    f"Admin: https://0to1log.com/admin/news"
                ),
            },
            timeout=10,
        )
        logger.info("Draft alert email sent for %s %s (score=%s)", batch_id, digest_type, quality_score)
    except Exception as e:
        logger.warning("Failed to send draft alert email: %s", e)


async def _notify_auto_publish(slugs: list[str]) -> None:
    """Notify frontend to fire webhooks + warm CDN for auto-published posts."""
    frontend_url = "https://0to1log.com"
    if not settings.cron_secret:
        logger.warning("cron_secret not set, skipping auto-publish notification")
        return
    for slug in slugs:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{frontend_url}/api/internal/notify-publish",
                    headers={"x-cron-secret": settings.cron_secret},
                    json={"slug": slug},
                    timeout=10,
                )
            logger.info("Auto-publish notification sent for %s", slug)
        except Exception as e:
            logger.warning("Failed to notify auto-publish for %s: %s", slug, e)


async def promote_drafts(batch_id: str | None = None) -> dict[str, Any]:
    """Promote eligible drafts (score >= threshold) from today's batch to published.

    Only promotes drafts with fact_pack.auto_publish_eligible=true (cron-triggered).
    Sends email alert for drafts below threshold. Fires webhooks for promoted posts.
    """
    if batch_id is None:
        batch_id = today_kst()

    supabase = get_supabase()
    if not supabase:
        logger.error("promote_drafts: Supabase unavailable")
        return {"promoted": 0, "kept_draft": 0, "errors": ["supabase unavailable"]}

    # Fetch all drafts for this batch
    result = (
        supabase.table("news_posts")
        .select("id,slug,quality_score,post_type,fact_pack,title")
        .eq("pipeline_batch_id", batch_id)
        .eq("status", "draft")
        .in_("post_type", ["research", "business"])
        .execute()
    )
    drafts = result.data or []
    logger.info("promote_drafts: %d drafts found for batch %s", len(drafts), batch_id)

    if not drafts:
        logger.warning("promote_drafts: no drafts found for batch %s — pipeline may have failed", batch_id)
        return {"promoted": 0, "kept_draft": 0, "batch_id": batch_id, "errors": ["no drafts found"]}

    threshold = settings.auto_publish_threshold
    promoted_slugs: list[str] = []
    kept_drafts: list[dict] = []
    errors: list[str] = []

    for draft in drafts:
        fp = draft.get("fact_pack") or {}
        eligible = fp.get("auto_publish_eligible", False)
        score = draft.get("quality_score")

        if not eligible:
            logger.info("Skipping %s — not eligible (manual trigger)", draft["slug"])
            continue

        if score is None or score < threshold:
            logger.info("Keeping draft %s — score %s < threshold %d", draft["slug"], score, threshold)
            kept_drafts.append(draft)
            continue

        # Promote to published
        try:
            supabase.table("news_posts").update({
                "status": "published",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", draft["id"]).execute()
            promoted_slugs.append(draft["slug"])
            logger.info("Promoted %s (score=%d) to published", draft["slug"], score)
        except Exception as e:
            error_msg = f"Failed to promote {draft['slug']}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Fire webhooks + warm CDN for promoted posts
    if promoted_slugs:
        await _notify_auto_publish(promoted_slugs)

    # Send draft alert emails (one per distinct post_type that was kept)
    alerted_types: set[str] = set()
    for d in kept_drafts:
        ptype = d.get("post_type") or "unknown"
        if ptype not in alerted_types:
            await _send_draft_alert(batch_id, ptype, d.get("quality_score"))
            alerted_types.add(ptype)

    return {
        "promoted": len(promoted_slugs),
        "kept_draft": len(kept_drafts),
        "promoted_slugs": promoted_slugs,
        "batch_id": batch_id,
        "errors": errors,
    }


def _iso_week_id(d=None) -> str:
    """Return ISO week string like '2026-W13'."""
    if d is None:
        d = datetime.strptime(today_kst(), "%Y-%m-%d").date()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


async def _fetch_week_digests(supabase, week_id: str, locale: str) -> list[dict]:
    """Fetch daily digests for the given ISO week and locale."""
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = (
        supabase.table("news_posts")
        .select("slug, title, post_type, content_expert, content_learner, published_at, guide_items")
        .eq("locale", locale)
        .eq("category", "ai-news")
        .in_("post_type", ["research", "business"])
        .eq("status", "published")
        .gte("published_at", monday.isoformat())
        .lte("published_at", sunday.isoformat() + "T23:59:59")
        .order("published_at", desc=False)
        .execute()
    )
    return result.data or []


async def _fetch_week_handbook_terms(supabase, week_id: str, locale: str) -> list[dict]:
    """Fetch handbook terms created/published this week for bottom card."""
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = (
        supabase.table("handbook_terms")
        .select("slug, term, korean_name, definition_en, definition_ko")
        .eq("status", "published")
        .gte("published_at", monday.isoformat())
        .lte("published_at", sunday.isoformat() + "T23:59:59")
        .limit(3)
        .execute()
    )
    return result.data or []


async def _send_weekly_email(supabase, week_id: str) -> None:
    """Send weekly recap via Buttondown API (draft only — Amy sends manually)."""
    import httpx

    if not settings.buttondown_api_key:
        logger.info("Buttondown API key not set, skipping email")
        return

    slug = f"{week_id.lower()}-weekly-digest"
    result = (
        supabase.table("news_posts")
        .select("title, content_expert")
        .eq("slug", slug)
        .eq("locale", "en")
        .single()
        .execute()
    )

    if not result.data:
        logger.warning("No weekly post found for email: %s", slug)
        return

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://api.buttondown.com/v1/emails",
            headers={"Authorization": f"Token {settings.buttondown_api_key}"},
            json={
                "subject": result.data["title"],
                "body": result.data["content_expert"],
                "status": "draft",
            },
        )
        resp.raise_for_status()
        logger.info("Weekly email draft created in Buttondown for %s", week_id)
