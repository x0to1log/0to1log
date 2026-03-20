# DIGEST-03: 파이프라인 오케스트레이터 전환 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `run_daily_pipeline()`에서 v2(1건 분석) → v3(다이제스트) 전환. `rank_candidates()` → `classify_candidates()`, `_generate_post()` → `_generate_digest()`.

**Architecture:** 수집된 후보를 `classify_candidates()`로 카테고리별 분류 → 분류된 뉴스 목록을 user prompt로 변환 → 페르소나별 다이제스트 마크다운 생성 → EN/KO row 저장. 기존 v2 함수들은 유지 (fallback).

**Tech Stack:** Python, Pydantic, OpenAI gpt-4o, pytest

---

### Task 1: `_generate_digest()` 함수 작성

**Files:**
- Modify: `backend/services/pipeline.py`

**개요:** 분류된 뉴스 목록 + raw_content를 받아서 3 페르소나 × 2 언어 콘텐츠를 생성하고 DB에 저장.

**구현:**

```python
from services.agents.ranking import classify_candidates
from services.agents.prompts_news_pipeline import get_digest_prompt
from services.agents.client import get_openai_client, parse_ai_json

async def _generate_digest(
    classified: list,  # list[ClassifiedCandidate]
    digest_type: str,  # "research" or "business"
    batch_id: str,
    handbook_slugs: list[str],
    raw_content_map: dict[str, str],
    supabase,
    run_id: str,
) -> tuple[int, list[str], dict[str, Any]]:
    """Generate a daily digest post for one category (research or business).

    Creates 3 persona versions (expert/learner/beginner) × 2 locales (en/ko).
    Returns (posts_created, errors, usage).
    """
    errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    posts_created = 0

    if not classified:
        return 0, [], {}

    # Build user prompt from classified news items
    news_items = []
    for item in classified:
        body = raw_content_map.get(item.url, item.snippet)[:2000]
        news_items.append(
            f"### [{item.subcategory}] {item.title}\n"
            f"URL: {item.url}\n"
            f"Relevance: {item.relevance_score}\n\n"
            f"{body}"
        )
    user_prompt = "\n\n---\n\n".join(news_items)

    # Generate 3 personas
    client = get_openai_client()
    model = settings.openai_model_main
    personas: dict[str, PersonaOutput] = {}

    for persona_name in ("expert", "learner", "beginner"):
        t_p = time.monotonic()
        system_prompt = get_digest_prompt(digest_type, persona_name, handbook_slugs)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=16000,
            )
            data = parse_ai_json(response.choices[0].message.content, f"Digest-{digest_type}-{persona_name}")
            persona_output = PersonaOutput(
                en=data.get("en", ""),
                ko=data.get("ko", ""),
            )
            usage = extract_usage_metrics(response, model)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
            personas[persona_name] = persona_output

            await _log_stage(
                supabase, run_id,
                f"digest:{digest_type}:{persona_name}", "success", t_p,
                output_summary=f"en={len(persona_output.en)}chars, ko={len(persona_output.ko)}chars",
                usage=usage,
                post_type=digest_type,
                debug_meta={
                    "en_length": len(persona_output.en),
                    "ko_length": len(persona_output.ko),
                    "en_preview": _trim(persona_output.en, 500),
                    "ko_preview": _trim(persona_output.ko, 500),
                    "news_count": len(classified),
                },
            )
        except Exception as e:
            error_msg = f"{digest_type} {persona_name} digest failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            await _log_stage(
                supabase, run_id,
                f"digest:{digest_type}:{persona_name}", "failed", t_p,
                error_message=error_msg, post_type=digest_type,
            )

    if not personas:
        return 0, errors, cumulative_usage

    # Save EN + KO rows
    t_save = time.monotonic()
    translation_group_id = str(uuid.uuid4())
    slug_base = f"{batch_id}-{digest_type}-digest"

    # Build source data from classified items
    source_urls = [item.url for item in classified]
    digest_meta = {
        "digest_type": digest_type,
        "news_items": [
            {"title": item.title, "url": item.url, "subcategory": item.subcategory}
            for item in classified
        ],
    }

    for locale in ("en", "ko"):
        slug = f"{slug_base}" if locale == "en" else f"{slug_base}-ko"
        title = f"AI {'Research' if digest_type == 'research' else 'Business'} Daily — {batch_id}"

        row = {
            "title": title,
            "slug": slug,
            "locale": locale,
            "category": "ai-news",
            "post_type": digest_type,
            "status": "draft",
            "content_expert": personas.get("expert", PersonaOutput()).en if locale == "en"
                else personas.get("expert", PersonaOutput()).ko,
            "content_learner": personas.get("learner", PersonaOutput()).en if locale == "en"
                else personas.get("learner", PersonaOutput()).ko,
            "content_beginner": personas.get("beginner", PersonaOutput()).en if locale == "en"
                else personas.get("beginner", PersonaOutput()).ko,
            "source_urls": source_urls,
            "fact_pack": digest_meta,
            "pipeline_batch_id": batch_id,
            "published_at": f"{batch_id}T09:00:00Z",
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            supabase.table("news_posts").upsert(row).execute()
            posts_created += 1
            logger.info("Saved %s %s digest draft: %s", digest_type, locale, slug)
        except Exception as e:
            error_msg = f"Failed to save {digest_type} {locale} digest: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    await _log_stage(
        supabase, run_id, f"save:{digest_type}", "success" if posts_created > 0 else "failed", t_save,
        output_summary=f"{posts_created} digest rows saved",
        post_type=digest_type,
        debug_meta={"slug_base": slug_base, "locales": ["en", "ko"]},
    )

    return posts_created, errors, cumulative_usage
```

**Step 2: Run lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check .`

**Step 3: Commit**

```
git add backend/services/pipeline.py
git commit -m "feat(pipeline): add _generate_digest() for v3 daily digest"
```

---

### Task 2: `run_daily_pipeline()` 전환 — classify + digest

**Files:**
- Modify: `backend/services/pipeline.py`

**개요:** `run_daily_pipeline()`에서 v2 흐름(rank → _generate_post)을 v3 흐름(classify → _generate_digest)으로 교체.

**변경 영역:** lines 587~648 (rank + picks + _generate_post 루프)

**교체 내용:**

```python
# 기존 v2:
# ranking, rank_usage = await rank_candidates(candidates)
# picks = [(type, candidate) for ...]
# for post_type, candidate in picks:
#     await _generate_post(...)

# v3:
# Stage: classify
t0 = time.monotonic()
classification, classify_usage = await classify_candidates(candidates)
cumulative_usage = merge_usage_metrics(cumulative_usage, classify_usage)

classify_output = {
    "research": [{"title": c.title, "url": c.url, "subcategory": c.subcategory} for c in classification.research],
    "business": [{"title": c.title, "url": c.url, "subcategory": c.subcategory} for c in classification.business],
}

await _log_stage(
    supabase, run_id, "classify", "success", t0,
    input_summary=f"{len(candidates)} candidates",
    output_summary=f"research={len(classification.research)}, business={len(classification.business)}",
    usage=classify_usage,
    debug_meta={
        "llm_input": _trim(rank_input_summary),
        "llm_output": classify_output,
        "candidates_count": len(candidates),
    },
)

handbook_slugs = _fetch_handbook_slugs(supabase)
raw_content_map = {c.url: c.raw_content for c in candidates if c.raw_content}

for digest_type, classified_items in [("research", classification.research), ("business", classification.business)]:
    if not classified_items:
        continue
    posts, errors, usage = await _generate_digest(
        classified=classified_items,
        digest_type=digest_type,
        batch_id=batch_id,
        handbook_slugs=handbook_slugs,
        raw_content_map=raw_content_map,
        supabase=supabase,
        run_id=run_id,
    )
    total_posts += posts
    all_errors.extend(errors)
    cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
```

**Step 2: Update imports at top of pipeline.py**

Add `classify_candidates` import and `extract_usage_metrics`:

```python
from services.agents.ranking import classify_candidates, rank_candidates
from services.agents.prompts_news_pipeline import get_digest_prompt
```

Note: keep `rank_candidates` import (used in tests, backward compat).

**Step 3: Run tests + lint**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short && .venv/Scripts/python.exe -m ruff check .`

Some pipeline tests may need updating since they mock `rank_candidates` — update mocks to also handle `classify_candidates`.

**Step 4: Commit**

```
git add backend/services/pipeline.py
git commit -m "feat(pipeline): switch run_daily_pipeline from v2 rank to v3 classify+digest"
```

---

### Task 3: 테스트 업데이트

**Files:**
- Modify: `backend/tests/test_pipeline.py`

**개요:** pipeline 테스트가 `rank_candidates` 대신 `classify_candidates`를 모킹하도록 업데이트.

**변경:**

```python
from models.news_pipeline import ClassifiedCandidate, ClassificationResult

SAMPLE_CLASSIFICATION = ClassificationResult(
    research=[
        ClassifiedCandidate(title="GPT-5", url="https://a.com/1", snippet="Model release",
            category="research", subcategory="llm_models", relevance_score=0.9, reason="Major"),
    ],
    business=[
        ClassifiedCandidate(title="AI Fund", url="https://b.com/2", snippet="$500M raised",
            category="business", subcategory="industry", relevance_score=0.85, reason="Big funding"),
    ],
)
```

Replace `patch("services.pipeline.rank_candidates", ...)` with `patch("services.pipeline.classify_candidates", ..., return_value=(SAMPLE_CLASSIFICATION, EMPTY_USAGE))`.

Replace `patch("services.pipeline.extract_facts", ...)` and `patch("services.pipeline.write_persona", ...)` with mocks for `get_openai_client` and `parse_ai_json` (since `_generate_digest` calls OpenAI directly).

**Step 2: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`

**Step 3: Commit**

```
git add backend/tests/test_pipeline.py
git commit -m "test: update pipeline tests for v3 classify+digest flow"
```
