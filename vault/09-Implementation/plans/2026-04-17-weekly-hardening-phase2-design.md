---
title: Weekly Hardening Phase 2 — Measurement + Source Infra + Persona Titles
date: 2026-04-17
status: design (approved, pending spec review)
type: design / spec
related:
  - vault/09-Implementation/plans/2026-04-17-weekly-hardening-phase1-design.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
---

# Weekly Hardening Phase 2 — Measurement + Source Infra + Persona Titles

## 1. 배경

Phase 1 (2026-04-17 complete)에서 weekly prompt를 rewrite하고 KO citation 보존, citation renumbering, framing guard, concrete-event gate, source priority 규칙을 추가했다. 결과:
- KO citation: 0 → 50+ per locale
- Citation 번호 충돌: 해소 (renumber 후처리)
- source_cards/source_urls: null → 채워짐
- Expect/framing 톤 완화

하지만 구조적 한계가 남아있다:
- **1차 출처 우선순위**: 프롬프트 규칙만으로 ~36%. LLM이 URL 도메인으로 primary/secondary를 추론하는 데 한계.
- **quality_score 없음**: 수동 검증이 유일한 gate.
- **제목 1개만 저장**: expert headline만 DB에 들어가고 learner headline 버려짐.
- **auto-publish 없음**: 항상 draft → 수동 발행.
- **length target 구식**: Phase 1 실측(expert 14k-19k, learner 14k-17k) 대비 target(12k/10k)이 낮음.

## 2. Goals & Non-Goals

### Goals (Phase 2)
- Daily source_cards 메타데이터를 weekly LLM에 전달 → 1차 출처 우선순위 구조적 해결
- Weekly quality scoring 인프라 구축 (daily와 동일 패턴)
- Persona별 제목 저장 + 어드민에서 페르소나 전환 시 제목 변경
- Auto-publish (어드민 Enabled 설정 기반)
- Length target 현실 반영
- Few-shot 예시 추가 (quality data 기반)

### Non-Goals
- ❌ Weekly KO adapter 추가 수정 (Phase 1에서 citation 보존 해결됨 — 관찰 유지)
- ❌ Weekly 발행 빈도 변경 (주 1회 유지)
- ❌ Frontend weekly 페이지 리디자인

## 3. Task 분해 및 의존 관계

```
T4 (Length target 상향) ─── 독립, 가장 쉬움
T3 (Persona titles)    ─── 독립, migration + backend + frontend
T1 (Source pipeline)   ─── 독립
T2 (Quality measurement) ─ T1 이후 (출처 인프라 있어야 quality check 의미 있음)
T6 (Auto-publish)      ─── T2 이후 (quality_score 필요)
T5 (Few-shot)          ─── T2 이후 + 4주 관찰 데이터 필요
```

실행 순서: **T4 → T3 → T1 → T2 → T6 → T5**

## 4. Task 상세

### T4: Length Target 상향

**파일**: `backend/services/agents/prompts_news_pipeline.py`

변경:
- WEEKLY_EXPERT_PROMPT Length Target: `12000+` → `16000+`
- WEEKLY_LEARNER_PROMPT Length Target: `10000+` → `13000+`
- KO 기준: EN의 ~65-70% (expert ≈ 10400+, learner ≈ 8500+)
- "depth > length" 원칙 유지. 뉴스 적은 주에는 짧게.

### T3: Persona Titles

**현재 상태**: Daily는 learner headline을 `guide_items["title_learner"]`에 저장 중 (top-level 컬럼 아님). Weekly는 learner headline을 아예 저장하지 않음.

**설계 결정**: top-level `title_learner` 컬럼 추가. 이유:
- 어드민에서 페르소나 전환 시 `news_posts.title_learner`로 직접 쿼리 가능 (guide_items JSON 파싱 불필요)
- Daily도 guide_items 대신 이 컬럼 사용으로 통일 (guide_items.title_learner는 deprecate)

**DB migration** (`supabase/migrations/000XX_title_learner.sql`):
```sql
ALTER TABLE news_posts ADD COLUMN title_learner TEXT;

-- Backfill: daily posts의 guide_items.title_learner → 새 컬럼
UPDATE news_posts
SET title_learner = guide_items->>'title_learner'
WHERE guide_items->>'title_learner' IS NOT NULL
  AND title_learner IS NULL;
```

**Backend — Weekly** (`backend/services/pipeline.py` — `run_weekly_pipeline`):
```python
headline_en = expert_data.get("headline") or f"AI Weekly — {week_id}"
headline_learner_en = learner_data.get("headline") or headline_en
headline_ko = expert_data.get("headline_ko") or headline_en
headline_learner_ko = learner_data.get("headline_ko") or headline_ko
```

row에 `title_learner` 추가.

**Backend — Daily** (`backend/services/pipeline_digest.py`):
- 기존 `guide_items["title_learner"] = learner_title` 유지 (하위호환)
- row에 `title_learner = learner_title` 추가 (새 컬럼에도 저장)

**Frontend (어드민)**: 페르소나 toggle 시 표시할 제목을 분기:
- expert → `news_posts.title`
- learner → `news_posts.title_learner` (없으면 `title` fallback)
- 구체적 컴포넌트 파일: T3 착수 시 `frontend/src/` 내 admin news 관련 컴포넌트 탐색 후 확정

**LLM prompt 변경**: 없음. 이미 expert/learner 각각 `"headline"` 반환 중.

### T1: Source Pipeline

**파일**:
- `backend/services/pipeline_persistence.py` — `_fetch_week_digests` 확장
- `backend/services/pipeline.py` — `run_weekly_pipeline` input 빌드 변경

**_fetch_week_digests 변경**:
```python
# 현재 select
.select("slug, title, post_type, content_expert, content_learner, published_at, guide_items")

# 변경
.select("slug, title, post_type, content_expert, content_learner, published_at, guide_items, source_cards, source_urls")
```

**Weekly LLM input 빌드 변경** (`run_weekly_pipeline`):

1. Daily posts에서 source_cards 추출 → URL → tier/kind 맵 생성:
```python
url_meta: dict[str, dict] = {}
for d in digests_en:
    for card in (d.get("source_cards") or []):
        url_meta[card["url"]] = {
            "source_tier": card.get("source_tier", ""),
            "source_kind": card.get("source_kind", ""),
        }
```

2. PRIMARY / SECONDARY URL 분류:
```python
primary_urls = [u for u, m in url_meta.items() if m.get("source_tier", "").lower() == "primary"]
secondary_urls = [u for u, m in url_meta.items() if m.get("source_tier", "").lower() != "primary"]
```

3. LLM input prepend:
```
## SOURCE REFERENCE (for citation priority)
PRIMARY: url1 | url2 | url3
SECONDARY: url4 | url5

--- BUSINESS EN (2026-04-14) ---
# Daily digest title
[content...]
```

4. `_renumber_citations()` 호출 시 `allowed_urls` 전달:
```python
aggregate_urls = set(url_meta.keys())
en_expert, en_expert_cards = _renumber_citations(en_expert, allowed_urls=aggregate_urls)
```

### T2: Quality Measurement

**파일**:
- `backend/services/agents/prompts_news_pipeline.py` — 프롬프트 2개 신설
- `backend/services/pipeline_quality.py` — `_check_weekly_quality()` 별도 함수 신설
- `backend/services/pipeline.py` — `run_weekly_pipeline`에서 quality check 호출

**프롬프트 신설** (`QUALITY_CHECK_WEEKLY_EXPERT`, `QUALITY_CHECK_WEEKLY_LEARNER`):
- Daily QUALITY_CHECK_BUSINESS_EXPERT 패턴 기반
- 공통 severity rubric 블록 재사용 (inline inject)
- Scoring 4축 (0-25 each, total 0-100):
  1. **Section Completeness** — 7개 required sections 존재 + depth
  2. **Source Quality** — citation 커버리지, 1차 출처 비율, URL 유효성
  3. **Depth & Synthesis** — Trend Analysis theme evolution, Top Stories WHAT/WHY/CONTEXT
  4. **Language & Tone** — persona 차별화, prediction 금지, framing word 절제

**별도 함수 `_check_weekly_quality()`** (기존 `_check_digest_quality`와 분리):

기존 `_check_digest_quality`는 daily 전용 파라미터(`classified: list`, `community_summary_map: dict`, `PersonaOutput`)에 강하게 결합돼있어서 weekly 분기를 끼워넣으면 복잡해짐. 별도 함수로 신설:

```python
async def _check_weekly_quality(
    content_expert_en: str,
    content_learner_en: str,
    content_expert_ko: str,
    content_learner_ko: str,
    source_urls: list[str],
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> dict[str, Any]:
```

내부 구조:
1. Expert prompt 호출 (EN+KO body 전달)
2. Learner prompt 호출 (EN+KO body 전달)
3. URL validation (`validate_citation_urls` 재사용)
4. Structural penalty (length, section count 등 deterministic checks)
5. Final score 합산

Daily의 scoring 로직(LLM score + deterministic penalty + structural penalty)은 헬퍼로 추출해서 양쪽이 공유. Frontload check는 weekly에 해당 없으므로 생략.

**`run_weekly_pipeline` 확장**:
- 생성 + renumber 후 `_check_weekly_quality()` 호출
- 결과를 row에 추가: `quality_score`, `quality_flags`, `content_analysis`, `fact_pack`

### T6: Auto-publish

**조건**: 어드민 설정 `weekly_auto_publish_enabled` = true AND `quality_score >= threshold`

```python
if weekly_auto_publish_enabled and quality_score and quality_score >= AUTO_PUBLISH_THRESHOLD:
    row["status"] = "published"
else:
    row["status"] = "draft"
```

- `weekly_auto_publish_enabled`: `core/config.py`의 Settings 클래스에 `weekly_auto_publish: bool = False` 추가 (env var `WEEKLY_AUTO_PUBLISH`). 어드민에서 Enabled 토글 시 이 값 변경.
- threshold: 초기 70점 (보수적 시작). Phase 2 관찰 후 조정.
- Enabled=false → 항상 draft → 수동 검토.

### T5: Few-shot 예시

**전제**: T2 완료 + W13-W16 (4주) quality data 축적

- Score 상위 1개를 "good example"로 선정
- WEEKLY_EXPERT_PROMPT / WEEKLY_LEARNER_PROMPT에 few-shot 추가:
  - Top Stories 항목 1개 (WHAT/WHY/CONTEXT + primary citation 패턴)
  - Trend Analysis 문단 1개 (theme evolution + citation)
- 토큰 예산: few-shot 당 ~300-400 tokens 이내

## 5. Done Criteria

- [ ] T4: Length target 변경 + ruff clean
- [ ] T3: migration 적용, weekly + daily pipeline에서 title_learner 저장, 어드민에서 페르소나 변경 시 제목 바뀜
- [ ] T1: _fetch_week_digests가 source_cards 반환, LLM input에 SOURCE REFERENCE 포함, _renumber_citations에 allowed_urls 전달
- [ ] T2: QUALITY_CHECK_WEEKLY_* 2개 프롬프트, _check_weekly_quality() 함수 신설, quality_score/fact_pack 채워짐
- [ ] T6: 어드민 Enabled 시 quality_score ≥ threshold → published
- [ ] T5: few-shot 1개 추가, 토큰 예산 내
- [ ] 전체: pytest 통과, ruff clean
- [ ] W15 또는 W16에서 manual run + 검증: quality_score 생성됨, 1차 출처 우선순위 개선 (>50%), title_learner 저장됨

## 6. 위험 및 대응

1. **Source cards 누락**: 일부 daily post에 source_cards가 null일 수 있음 (Phase 1 이전 생성분). **대응**: null 체크 + graceful fallback (source_cards 없으면 SOURCE REFERENCE 생략).

2. **Quality check 토큰 비용**: Weekly 본문이 daily 대비 3-5배 길어 quality check input도 큼. **대응**: quality check에 expert content만 전달 (learner는 별도 호출 or skip). 또는 content 앞 N chars만 샘플링.

3. **Few-shot 토큰 예산**: Weekly prompt가 이미 큼 (daily digests aggregate). Few-shot 추가 시 context window 압박. **대응**: 300-400 tokens 제한. 1 example만.

4. **Frontend 제목 분기**: 어드민 컴포넌트 구조에 따라 작업량 달라짐. **대응**: T3 착수 시 프론트엔드 코드 탐색 후 판단.

## 7. 일정

- T4: 10분 (프롬프트 한 줄)
- T3: 1일 (migration + backend + frontend)
- T1: 반나절 (fetch 확장 + input 빌드 + allowlist)
- T2: 1일 (프롬프트 2개 + routing + pipeline 연결)
- T6: 반나절 (조건 로직 + 설정)
- T5: T2 완료 + 4주 관찰 후 반나절

총: ~3일 (T5 제외) + 관찰 기간
