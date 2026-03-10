import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.rate_limit import limiter
from routers import cron, admin, admin_ai, admin_blog_ai
from models.posts import HealthResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="0to1log API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://0to1log.com", "http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cron.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_ai.router, prefix="/api")
app.include_router(admin_blog_ai.router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
