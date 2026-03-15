---
title: Backend Stack
tags:
  - architecture
  - backend
  - stack
source: docs/03_Backend_AI_Spec.md
---

# Backend Stack

FastAPI + Railway 기반 범용 API 백엔드. AI 파이프라인 + 검색 + 커뮤니티 + 구독 권한.

## 서비스 배포 구조

| 서비스 | 플랫폼 | 리전 | 역할 |
|---|---|---|---|
| Frontend | Vercel | us-east-1 | Astro SSG/SSR, 도메인, Cron 트리거 |
| Backend | Railway | us-east-1 | FastAPI — 범용 API 백엔드 |
| Database | Supabase | us-east-1 | PostgreSQL, pgvector, Auth, Storage |

> [!important] 리전 통일 원칙
> 세 서비스 모두 us-east-1에 배치하여 서비스 간 레이턴시 최소화.

## 서비스 간 통신

| 작업 유형 | 경로 | 이유 |
|---|---|---|
| **콘텐츠 읽기 (리스트/상세)** | Frontend → Supabase 직접 | 지연 최소화, 단순 조회 |
| **단순 댓글 CRUD/좋아요** | Frontend → Supabase 직접 | RLS로 권한 통제 |
| **AI 파이프라인/검수** | Frontend/API Route → FastAPI | 장시간 작업, 외부 API 호출 |
| **시맨틱 검색 (Cmd+K)** | Frontend → FastAPI | 임베딩/랭킹 로직 캡슐화 (Phase 3) |
| **포인트/퀴즈/베팅** | Frontend → FastAPI | 트랜잭션/치트 방지 (Phase 4) |
| **구독 권한 검증** | Frontend → FastAPI | 결제 상태 검증 (Phase 4+) |

## fire-and-forget 패턴

> [!note] ADR
> Vercel Hobby 플랜 Serverless 타임아웃 10초 → AI 파이프라인 2~5분 소요 문제 해결.

1. Vercel Cron → Vercel API Route 호출
2. API Route → Railway POST (`CRON_SECRET` 포함)
3. Railway ==즉시 202 Accepted 반환== (백그라운드 실행)
4. API Route는 202 받고 종료 (10초 내)
5. Railway 비동기로 파이프라인 실행 → Supabase 저장 → 실패 시 `admin_notifications`

## 인증 시스템

### 사용자 역할

| 역할 | 권한 | 인증 방식 |
|---|---|---|
| **Admin** | 글 작성/수정/삭제, 파이프라인 실행, 대시보드 | Supabase Auth (이메일/비밀번호) |
| **User** | 글 읽기, 댓글, 페르소나 설정, 피드백 | Supabase Auth (Google/GitHub 소셜) |
| **Visitor** | 글 읽기, 페르소나 전환 (쿠키) | 인증 없음 |

### Admin 보호 로직

FastAPI `Depends(require_admin)` 의존성 주입:

Bearer 토큰 추출 → `supabase.auth.get_user(token)` → `admin_users` 테이블 이메일 존재 확인 → 미등록 시 403

> [!important] Admin 단일 소스 원칙
> Admin 이메일은 코드 하드코딩 비교 금지. `admin_users` 테이블만 기준.

### RLS (Row Level Security)

- `news_posts`: 누구나 published 읽기, admin만 쓰기/수정/삭제
- `comments`: 로그인 사용자 작성, 본인만 수정/삭제
- `comment_likes`: 로그인 사용자, 본인 좋아요만 관리

> [!warning] RLS 버그 시 DB 직접 노출. 배포 전 반드시 테스트 시나리오 실행.

## FastAPI 엔드포인트

### Cron / Pipeline

| Method | Path | 인증 |
|---|---|---|
| POST | `/api/cron/news-pipeline` | Cron Secret (optional body: `{ target_date: "YYYY-MM-DD" }`) |

### Admin — 콘텐츠 관리

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/drafts` | 검수 대기 초안 목록 |
| GET | `/api/admin/drafts/{slug}` | 초안 상세 + Editorial 피드백 |
| PATCH | `/api/admin/posts/{id}/publish` | 발행 상태 변경 |
| PATCH | `/api/admin/posts/{id}/update` | 초안 수동 편집 |
| POST | `/api/admin/posts/{id}/regenerate` | 재생성 요청 |

### Admin — AI 기능

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/admin/ai/draft` | 수동 초안 생성 |
| POST | `/api/admin/ai/review` | 수동 Editorial 검수 |
| POST | `/api/admin/ai/rewrite` | 피드백 기반 재작성 |

### Phase 3+ API

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| POST | `/api/search/semantic` | 시맨틱 검색 (pgvector) | Public |
| GET | `/api/community/me/points` | 내 포인트/레벨 | User |
| POST | `/api/community/predictions` | 퀴즈/베팅 참여 | User |
| GET | `/api/subscription/me/access` | 구독 접근 권한 | User |

## 환경 변수

| 변수 | 용도 |
|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` | Supabase 연결 |
| `OPENAI_API_KEY` | OpenAI API |
| `OPENAI_MODEL_MAIN` (`gpt-4o`) | 메인 모델 (환경 변수로 교체 용이) |
| `OPENAI_MODEL_LIGHT` (`gpt-4o-mini`) | 경량 모델 |
| `TAVILY_API_KEY` | 뉴스 수집 |
| `CRON_SECRET` | Cron 인증 |
| `FASTAPI_URL` | Railway URL |

## 디렉토리 구조

```
backend/  (Railway FastAPI)
  ├── main.py              (진입점 + 라우터 등록)
  ├── core/                (config, db client, security)
  ├── models/              (Pydantic 스키마)
  ├── services/            (에이전트 로직, 파이프라인)
  ├── routers/             (엔드포인트 라우터)
  └── tests/               (pytest)
```

## Related
- [[System-Architecture]] — 전체 시스템 아키텍처
- [[Database-Schema-Overview]] — DB 스키마 상세
- [[Frontend-Stack]] — Astro 프론트엔드

## See Also
- [[Cost-Model-&-Stage-AB]] — Railway 운영비 + API 비용 (07-Operations)
