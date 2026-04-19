---
title: Database Schema Overview
tags:
  - architecture
  - database
  - supabase
source: docs/03_Backend_AI_Spec.md
---

# Database Schema Overview

Supabase PostgreSQL 기반. pgvector 확장 (Phase 3). RLS로 권한 관리.

## 핵심 테이블

### admin_users — Admin 단일 소스

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `email` | TEXT (PK) | Admin 이메일 |
| `user_id` | UUID (FK → auth.users) | Supabase Auth uid |
| `is_active` | BOOLEAN | 활성 여부 |

> [!note] Auth Contract
> `valid token + admin_users.user_id = auth.uid() + is_active=true`

### news_posts — 뉴스 콘텐츠

| 컬럼 그룹 | 주요 컬럼 | 설명 |
|---|---|---|
| **식별** | `id`, `title`, `slug`, `category`, `post_type`, `status` | Research/Business 구분, draft/published/archived |
| **페르소나 콘텐츠** | `content_beginner`, `content_learner`, `content_expert` | Business 포스트용 3버전 (MDX) |
| **단일 콘텐츠** | `content_original` | Research/Type B 포스트용 |
| **가이드 블록** | `guide_items` (JSONB) | daily: `{quiz_poll_expert, quiz_poll_learner, sources_expert, sources_learner, excerpt_learner, title_learner}` · weekly: `{week_numbers, week_tool, week_terms, weekly_quiz_expert, weekly_quiz_learner, excerpt_learner, title_learner}` |
| **Related News** | `related_news` (JSONB) | `{big_tech, industry_biz, new_tools}` — Business만 |
| **뉴스 없음** | `no_news_notice`, `recent_fallback` | Research "없음" 공지 |
| **메타** | `source_urls`, `news_temperature`, `reading_time_min`, `tags` | |
| **파이프라인** | `pipeline_model`, `pipeline_tokens`, `pipeline_cost`, `prompt_version`, `pipeline_batch_id` | AI 추적 |
| **타임스탬프** | `created_at`, `updated_at`, `published_at` | |

**인덱스:** category, post_type, status, published_at DESC, slug, pipeline_batch_id
**유니크 제약:** `(pipeline_batch_id, post_type)` WHERE `category = 'ai-news'` — 일일 중복 방지

### Locale Referential Integrity

- EN row 먼저 생성 → `translation_group_id` 발급
- KO row는 `source_post_id` + `source_post_version` 필수
- KO publish 시 EN 버전 일치 확인 → 불일치 시 re-sync queue

### comments / comment_likes

- `comments`: `post_id`, `user_id`, `parent_id` (대댓글), `content` (max 2000자)
- `comment_likes`: `(user_id, comment_id)` 복합 PK
- ==Supabase SDK 직접 호출== — FastAPI 미경유, RLS로 권한 관리

### news_candidates — 뉴스 수집 후보

| 컬럼 | 설명 |
|---|---|
| `assigned_type` | research / business_main / big_tech / industry_biz / new_tools / unassigned |
| `relevance_score` | 0~1 AI 평가 점수 |
| `ranking_reason` | AI가 이 점수를 준 이유 |
| `status` | pending → selected → published |
| `batch_id` | 일일 파이프라인 실행 키 |

### pipeline_logs — 파이프라인 로그

| 컬럼 | 설명 |
|---|---|
| `pipeline_type` | news_collection / ranking / research_draft / business_draft / editorial / daily_pipeline |
| `status` | started / success / failed / retried / no_news |
| `model_used`, `tokens_used`, `cost_usd` | AI 비용 추적 |

### pipeline_runs — 중복 실행 방지

- `run_key` (PK): `daily:2026-03-04` 형식
- `status`: running / success / failed

### admin_notifications

- `type`, `title`, `message`, `is_read` — 파이프라인 실패 등 Admin 알림

### embeddings (Phase 3)

- `post_id`, `chunk_text`, `embedding` (VECTOR(1536))
- pgvector `ivfflat` 인덱스 (cosine)

> [!note] JSONB 통합 결정 (ADR)
> guide_items 5개 컬럼 + related_news 3개 컬럼을 각각 JSONB 1개로 통합. 항상 한 덩어리로 읽고 쓰므로 JOIN 불필요. [[Quality-Gates-&-States\|PydanticAI]]가 내부 구조 검증.

## Related
- [[System-Architecture]] — 전체 시스템에서 DB 위치
- [[Backend-Stack]] — DB를 사용하는 백엔드

## See Also
- [[Quality-Gates-&-States]] — PydanticAI 스키마 검증 (04-AI-System)
