# Backend Development Guide

**Stack:** FastAPI + Railway (Nixpacks)

For detailed specifications, see:
- `docs/03_Backend_AI_Spec.md` — Full API & pipeline spec
- `docs/05_Infrastructure.md` — Infrastructure & deployment

---

## Project Structure

```
backend/
├── main.py              FastAPI app + router registration + CORS
├── core/                Shared utilities (config, database, security)
├── routers/             API endpoint groups (cron, admin, search)
├── services/            Business logic (agents, pipelines)
├── models/              Pydantic schemas
├── tests/               Test suite
└── requirements.txt     Python dependencies
```

### Core Modules

- **`core/config.py`** — Settings (env vars via Pydantic)
- **`core/database.py`** — Supabase connection & query helpers
- **`core/security.py`** — JWT validation, auth decorators
- **`core/rate_limit.py`** — slowapi rate limiting

---

## Python Setup

**Virtualenv Policy:**
- Use `backend/.venv` only
- `backend/venv` is NOT allowed
- VSCode should detect `.venv` automatically

**Version & Dependencies:**
- Python 3.11+ (see `.python-version`)
- Install: `pip install -r requirements.txt`
- Linter: `ruff check .` (run from backend/)
- Tests: `pytest tests/ -v --tb=short`

---

## Development Workflow

### Running Locally

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Start dev server
uvicorn main:app --reload --port 8000

# Check health
curl http://localhost:8000/health
```

### Code Quality

```bash
# Lint with ruff
ruff check .

# Run tests
pytest tests/ -v --tb=short

# Format (if enabled)
ruff format .
```

---

## API Endpoints

### Admin Pipelines

All admin endpoints require `Depends(require_admin)` auth decorator.

```python
# POST /api/admin/news
# Generate and publish daily news
# Returns: 202 Accepted (async)
response = requests.post(
    "http://localhost:8000/api/admin/news",
    headers={"Authorization": "Bearer <token>"}
)

# POST /api/admin/blog
# Generate blog articles

# POST /api/admin/products
# Generate product guides
```

### Cron Endpoints

All cron endpoints require `x-cron-secret` header (set in `core/config.py`).

```python
# POST /api/cron/news
# Automated daily news generation (Vercel Cron)

# POST /api/cron/weekly
# Weekly recap generation
```

---

## Security Rules

### Authentication

- **Admin endpoints:** `@require_admin` decorator required
  ```python
  from core.security import require_admin
  
  @router.post("/news")
  async def generate_news(admin: dict = Depends(require_admin)):
      # Only admins can call this
  ```

- **Cron endpoints:** `x-cron-secret` header validation
  ```python
  # Header: x-cron-secret: <CRON_SECRET from .env>
  ```

- **User auth:** Supabase JWT (anon key)

### Database Security

- **Backend uses:** Service Role Key (backend-only)
  - Never expose in API responses
  - Never send to frontend
  
- **Frontend uses:** Anon Key (limited by RLS)
  - RLS policies restrict access by user_id

- **Supabase RLS:** All tables must have row-level security
  - Policies enforce user data isolation

### Rate Limiting

```python
from slowapi import Limiter
from core.rate_limit import limiter

@router.get("/recommendations")
@limiter.limit("10/minute")
async def get_recommendations(request: Request):
    # Max 10 requests per minute
    pass
```

---

## Common Patterns

### Fire-and-Forget with BackgroundTasks

Cron endpoints should return `202 Accepted` immediately and process async:

```python
from fastapi import BackgroundTasks

@router.post("/api/cron/news")
async def cron_news(background_tasks: BackgroundTasks, secret: str = Header(...)):
    validate_cron_secret(secret)
    background_tasks.add_task(pipeline.generate_news)
    return {"status": "queued"}
```

### Error Handling

```python
from fastapi import HTTPException

if not user:
    raise HTTPException(status_code=401, detail="Unauthorized")

try:
    result = await pipeline.generate_news()
except Exception as e:
    logger.error(f"Pipeline failed: {e}")
    raise HTTPException(status_code=500, detail="Pipeline error")
```

### Logging (NOT print)

```python
import logging

logger = logging.getLogger(__name__)

logger.info("News generation started")
logger.warning("Rate limit approaching")
logger.error("Failed to fetch from Tavily")
```

---

## Environment Variables

**Required (`.env` file):**

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxx...

OPENAI_API_KEY=sk-...
OPENAI_MODEL_MAIN=gpt-4.1
OPENAI_MODEL_LIGHT=gpt-4.1-mini

TAVILY_API_KEY=tvly-...
PINECONE_API_KEY=pck-...
PINECONE_INDEX_NAME=0to1log

FASTAPI_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:4321", "https://0to1log.vercel.app"]
CRON_SECRET=your-secret-here
REVALIDATE_SECRET=your-secret-here
```

**Optional:**
- `GA4_PROPERTY_ID` — Analytics property ID
- `GA4_CREDENTIALS_JSON` — GA4 service account (JSON string)
- `BUTTONDOWN_API_KEY` — Newsletter integration

---

## Deployment (Railway)

### Build

```bash
# Railway auto-detects Python & runs:
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Health Check

```
GET /health
→ {"status": "ok"}
```

### Auto-Restart

Railway auto-restarts the app on crash. Monitor in Railway dashboard.

### CI/CD

- Push to `main` branch → auto-deploy to Railway
- Check logs in Railway dashboard

---

## Forbidden Patterns

### ❌ Don't Use print()

```python
# BAD
print("Debug info:", result)

# GOOD
import logging
logger = logging.getLogger(__name__)
logger.info(f"Debug info: {result}")
```

### ❌ Don't Hardcode Environment Values

```python
# BAD
database_url = "postgresql://..."
api_key = "sk-xxx"

# GOOD
from core.config import settings
database_url = settings.supabase_url
api_key = settings.openai_api_key
```

### ❌ Don't Expose Service Keys

```python
# BAD
response = {
    "posts": posts,
    "supabase_key": settings.supabase_service_key  # NEVER!
}

# GOOD
response = {
    "posts": posts
    # Client uses anon key via environment
}
```

### ❌ Don't Hardcode CORS Origins

```python
# BAD
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"]
)

# GOOD
app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(settings.cors_origins)
)
# Set in .env: CORS_ORIGINS=["https://0to1log.vercel.app"]
```

---

## Testing

### Run Tests

```bash
pytest tests/ -v --tb=short
```

### Test Structure

```
tests/
├── conftest.py           Fixtures & test setup
├── test_routers.py       API endpoint tests
├── test_services.py      Business logic tests
└── test_agents.py        AI agent tests
```

### Example Test

```python
from unittest.mock import patch

def test_generate_news():
    with patch("services.news_collection.collect_news") as mock:
        mock.return_value = [{"title": "Test"}]
        result = pipeline.generate_news()
        assert result["status"] == "success"
```

---

## Debugging

### Enable Debug Logging

Set in `.env`:
```
LOG_LEVEL=DEBUG
```

Check logs:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Detailed info: {var}")
```

### Railway Logs

View in Railway dashboard or use CLI:
```bash
railway logs --follow
```

---

## References

- **FastAPI:** https://fastapi.tiangolo.com
- **PydanticAI:** https://ai.pydantic.dev/
- **Supabase:** https://supabase.com/docs
- **Railway:** https://docs.railway.app
