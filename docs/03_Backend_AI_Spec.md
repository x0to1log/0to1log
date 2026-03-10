# ⚙️ 0to1log — Backend & AI Spec

> **문서 버전:** v3.3  
> **최종 수정:** 2026-03-05  
> **작성자:** Amy (Solo)  
> **상태:** Planning  
> **상위 문서:** `01_Project_Overview.md`

### v3.2 변경 이력

| 항목 | v3.1 | v3.2 | 이유 |
|---|---|---|---|
| Railway 운영 모델 | 파이프라인 실행 전용 | 범용 API 백엔드 + 단계적 Always-on 전환 | 검색/커뮤니티/권한 로직 확장 대응 |
| Frontend-Backend 경계 | 직결 중심(일부 API) | 하이브리드 경계 정책 명문화 | 보안/속도/복잡도 균형 확보 |
| FastAPI 엔드포인트 분류 | Cron + AI 중심 | 검색/커뮤니티/구독 권한 API 범위 확장 | Phase 3~4 기능 수용 |
| 비용 모델 | API 비용 중심 | API 비용 + Railway 운영비 단계형 분리 | 인프라 의사결정 가시성 강화 |
| 테스트 전략 | 파이프라인/RLS 중심 | API 경계 검증 시나리오 추가 | 문서-구현 불일치 예방 |

---

## 1. 시스템 아키텍처

### 전체 구조

```
[사용자 브라우저]
       │
       ▼
[Vercel] ← Astro Frontend (0to1log.com)
       │
       ├──→ [Supabase] ← 콘텐츠 저장/조회/인증/댓글 (PostgreSQL + pgvector + Auth)
       │         ↑
       │         │ (파이프라인 결과 저장)
       │         │
       └──→ [Railway] ← FastAPI — 범용 API 백엔드
                │         (AI 파이프라인 + 검색 + 커뮤니티 + 구독 권한)
                │
                ├── OpenAI API ─── Ranking Agent (뉴스 분류 + 랭킹)
                │              ├── Research Engineer Agent (기술 심화 포스트)
                │              └── Business Analyst Agent (시장 분석 포스트)
                ├── PydanticAI    (출력 스키마 검증)
                └── Tavily API    (RAG 뉴스 수집)

[Vercel Cron Jobs] ──→ Vercel API Route ──→ Railway (fire-and-forget)
                        (202 즉시 반환)      (비동기 파이프라인 실행)
```

### 범용 API 서버 운영 (ADR)

> **결정:** Railway(FastAPI)를 "파이프라인 실행기"가 아닌 **범용 API 백엔드**로 운영한다.
>
> **맥락:** Phase 3~4의 시맨틱 검색(Cmd+K), 포인트/퀴즈/베팅, 구독 권한 검증은 단순 CRUD를 넘어서는 서버사이드 비즈니스 로직이 필요하다.
>
> **운영 전략(단계적 전환):**
> - **Stage A (Phase 2):** 범용 API 구조를 먼저 구축하고, 파이프라인 및 Admin API 중심으로 저비용 운영
> - **Stage B (Phase 3+):** 검색/커뮤니티 트래픽 KPI 충족 시 Always-on 운영으로 상향
>
> **대안 검토:**
> - Vercel Serverless Function: Hobby 플랜 10초 제한으로 장시간 파이프라인 처리 부적합
> - Supabase Edge Function: Python/PydanticAI 중심 파이프라인 재사용성이 낮음
> - Railway 유지가 Python 생태계 활용 + 확장성 + 운영 일관성 측면에서 가장 현실적

### 서비스 배포 구조

| 서비스 | 플랫폼 | 리전 | 역할 |
|---|---|---|---|
| Frontend | Vercel | us-east-1 | Astro SSG/SSR, 도메인, Cron 트리거 |
| Backend | Railway | us-east-1 | FastAPI — 범용 API 백엔드 (파이프라인/검색/커뮤니티/권한) |
| Database | Supabase | us-east-1 | PostgreSQL, pgvector, Auth, Storage, 댓글 CRUD |

> **리전 통일 원칙:** 세 서비스 모두 동일 리전(us-east-1)에 배치하여 서비스 간 레이턴시를 최소화한다.

### 서비스 간 통신

```
Vercel (Frontend)
  │
  ├── [직접] Supabase JS SDK → 글 조회, 단순 댓글 CRUD, 인증, 좋아요
  │
  └── [API] Vercel API Route → Railway FastAPI (fire-and-forget)
         │     (Cron 트리거 + 검색/커뮤니티/구독 권한 + Admin AI 기능)
         │
         └── FastAPI 내부에서 Supabase Python SDK → 비즈니스 로직/초안/결과 저장
```

| 작업 유형 | 기본 경로 | 이유 |
|---|---|---|
| **콘텐츠 읽기(리스트/상세)** | Frontend → Supabase 직접 | 지연 최소화, 단순 조회 |
| **단순 댓글 CRUD/좋아요** | Frontend → Supabase 직접 | RLS로 권한 통제 가능 |
| **AI 파이프라인/검수** | Frontend/API Route → FastAPI | 장시간 작업, 외부 API 호출 |
| **시맨틱 검색(Cmd+K)** | Frontend → FastAPI | 임베딩/랭킹 로직 캡슐화 |
| **포인트/퀴즈/베팅** | Frontend → FastAPI | 트랜잭션/치트 방지/규칙 엔진 |
| **구독 권한 검증** | Frontend → FastAPI | 결제 상태 검증, 비밀키 보호 |

### fire-and-forget 패턴 (ADR)

> **결정:** Vercel → Railway 호출 시 fire-and-forget 패턴을 사용한다.
>
> **문제:** Vercel Hobby 플랜의 Serverless Function 타임아웃은 10초다. AI 파이프라인은 OpenAI API 호출 여러 번 + Tavily 수집 + 후처리로 2~5분 소요된다.
>
> **해결:**
> 1. Vercel Cron → Vercel API Route 호출
> 2. Vercel API Route → Railway에 HTTP POST (CRON_SECRET 포함)
> 3. Railway는 요청을 받으면 **즉시 202 Accepted 반환** (파이프라인은 백그라운드 실행)
> 4. Vercel API Route는 202를 받고 즉시 종료 (10초 내 완료)
> 5. Railway는 비동기로 파이프라인 실행 → 결과를 Supabase에 저장 → 실패 시 admin_notifications에 기록
>
> **결과 확인:** Admin 대시보드에서 pipeline_logs 테이블 조회, 또는 실패 시 admin_notifications 확인

### 프로젝트 디렉토리 구조

```
api/  (Railway FastAPI)
  ├── main.py              (FastAPI 진입점 + 라우터 등록)
  ├── core/                (config, db client, security/auth)
  ├── models/              (Pydantic 스키마 — PydanticAI 검증용)
  ├── services/            (에이전트 로직, 뉴스 수집, 파이프라인 오케스트레이터)
  ├── routers/             (엔드포인트 그룹별 라우터)
  └── tests/               (pytest 테스트)

src/  (Astro Frontend)
  ├── pages/               (라우팅 — /, /log, /portfolio, /admin)
  ├── components/          (UI 컴포넌트)
  ├── layouts/             (페이지 레이아웃)
  ├── lib/                 (supabase client, api wrapper, utils)
  └── styles/              (글로벌 CSS, 테마 토큰)

supabase/
  └── migrations/          (SQL 마이그레이션 파일)
```

---

## 2. 인증 시스템

### Supabase Auth 선택 이유

관리자(Admin) 인증 + 일반 사용자 소셜 로그인(댓글)을 모두 지원해야 하므로, Supabase Auth를 채택한다.

### 사용자 역할

| 역할 | 권한 | 인증 방식 |
|---|---|---|
| **Admin** | 글 작성/수정/삭제, AI 파이프라인 실행, 대시보드 접근 | Supabase Auth (이메일/비밀번호) |
| **User** | 글 읽기, 댓글 작성/수정/삭제, 페르소나 설정, 피드백 | Supabase Auth (Google/GitHub 소셜 로그인) |
| **Visitor** | 글 읽기, 페르소나 전환 (쿠키 저장) | 인증 없음 |

### Admin 보호 로직

FastAPI 의존성 주입(`Depends(require_admin)`)으로 Admin 전용 엔드포인트를 보호한다.

**인증 흐름:** Bearer 토큰 추출 → `supabase.auth.get_user(token)` → `admin_users` 테이블에 이메일 존재 여부 확인 → 미등록 시 403

### RLS (Row Level Security) 정책

```sql
-- 글(news_posts): 누구나 published 읽기 가능, admin_users에 등록된 계정만 쓰기
CREATE POLICY "news_posts_read" ON news_posts FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );
CREATE POLICY "news_posts_write" ON news_posts FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );
CREATE POLICY "news_posts_update" ON news_posts FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );
CREATE POLICY "news_posts_delete" ON news_posts FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

-- 댓글(comments): 로그인 사용자만 작성, 본인 댓글만 수정/삭제
CREATE POLICY "comments_read" ON comments FOR SELECT USING (true);
CREATE POLICY "comments_insert" ON comments FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY "comments_update" ON comments FOR UPDATE
    USING (auth.uid() = user_id);
CREATE POLICY "comments_delete" ON comments FOR DELETE
    USING (auth.uid() = user_id);

-- 좋아요(comment_likes): 로그인 사용자만, 본인 좋아요만 관리
CREATE POLICY "likes_insert" ON comment_likes FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "likes_delete" ON comment_likes FOR DELETE
    USING (auth.uid() = user_id);
CREATE POLICY "likes_read" ON comment_likes FOR SELECT USING (true);
```

> **Admin 단일 소스 원칙:** Admin 이메일은 코드 상수/하드코딩으로 비교하지 않고 `admin_users` 테이블만 기준으로 사용한다.

> **RLS 보안 주의:** RLS 정책에 버그가 있으면 DB가 직접 노출된다. 배포 전 반드시 테스트 시나리오를 실행할 것 (섹션 11 테스트 전략 참조).

### 댓글 시스템을 Supabase 직접 호출로 이관한 이유 (ADR)

> **결정:** 댓글 CRUD를 FastAPI에서 제거하고 Frontend → Supabase SDK 직접 호출로 변경한다.
>
> **이유:**
> - 댓글은 단순 CRUD 작업으로, RLS 정책만으로 보안(본인 댓글만 수정/삭제)이 충분하다
> - 읽기/단순 CRUD는 Supabase 직결이 지연시간과 운영 복잡도 측면에서 가장 단순하다
> - 향후 포인트 지급, 치트 방지, 다중 트랜잭션이 필요한 시점에는 댓글/커뮤니티 로직을 FastAPI 경유로 확장한다
>
> **스팸 방어:** Frontend에서 기본 rate limiting + Supabase RLS로 1차 방어. 스팸이 심해지면 Phase 3에서 서버 사이드 필터링 도입 검토.

---

## 3. 데이터베이스 스키마 (Supabase PostgreSQL)

### admin_users 테이블 (Admin 단일 소스)

```sql
CREATE TABLE admin_users (
    email         TEXT PRIMARY KEY,
    user_id       UUID REFERENCES auth.users(id),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);
```

> **Admin auth contract:** `valid token + admin_users.user_id = auth.uid() + is_active=true` (uid 기반 인증)

### news_posts 테이블

```sql
CREATE TABLE news_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    category        TEXT NOT NULL CHECK (category IN ('ai-news')),
    post_type       TEXT CHECK (post_type IN ('research', 'business')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    
    -- 페르소나별 콘텐츠 (Business Analyst 포스트용)
    content_beginner    TEXT,          -- 비전공자 버전 (MDX)
    content_learner     TEXT,          -- 학습자 버전 (MDX)
    content_expert      TEXT,          -- 현직자 버전 (MDX)
    
    -- 단일 콘텐츠 (Research Engineer 포스트 / Type B 커리어·프로젝트)
    content_original    TEXT,
    
    -- 프롬프트 가이드 5블록 (JSONB로 통합)
    guide_items         JSONB,
    -- 구조: {one_liner, action_item, critical_gotcha, rotating_item_type, rotating_item, quiz_poll}
    -- PydanticAI PromptGuideItems 스키마가 구조를 보장
    
    -- Related News (Business Analyst 포스트용, JSONB로 통합)
    related_news        JSONB,
    -- 구조: {big_tech, industry_biz, new_tools}
    -- 각 값: 한 줄 요약 문자열 또는 "없음" 메시지
    
    -- 뉴스 없음 표기 (Research Engineer 포스트용)
    no_news_notice      TEXT,          -- "24시간 내 해당 뉴스 없음" 공지
    recent_fallback     TEXT,          -- 기간 외 최근 동향 보충
    
    -- 메타데이터
    source_urls         TEXT[],        -- 원문 출처 URL 배열
    news_temperature    INTEGER CHECK (news_temperature BETWEEN 1 AND 5),
    reading_time_min    INTEGER,
    tags                TEXT[],
    og_image_url        TEXT,
    
    -- AI 파이프라인 메타
    pipeline_model      TEXT,          -- 사용된 OpenAI 모델명
    pipeline_tokens     INTEGER,       -- 총 토큰 사용량
    pipeline_cost       DECIMAL(10,6), -- 예상 비용 (USD)
    prompt_version      TEXT,          -- 사용된 프롬프트 버전
    pipeline_batch_id   TEXT,          -- daily pipeline run key (예: 2026-03-04)
    
    -- 타임스탬프
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    published_at    TIMESTAMPTZ,

    -- ai-news는 반드시 post_type 필요
    CONSTRAINT chk_post_type_by_category CHECK (
        category = 'ai-news' AND post_type IN ('research', 'business')
    )
);

CREATE INDEX idx_news_posts_category ON news_posts(category);
CREATE INDEX idx_news_posts_type ON news_posts(post_type);
CREATE INDEX idx_news_posts_status ON news_posts(status);
CREATE INDEX idx_news_posts_published ON news_posts(published_at DESC);
CREATE INDEX idx_news_posts_slug ON news_posts(slug);
CREATE INDEX idx_news_posts_batch ON news_posts(pipeline_batch_id);
CREATE UNIQUE INDEX uq_news_posts_daily_ai_type
    ON news_posts(pipeline_batch_id, post_type)
    WHERE category = 'ai-news' AND pipeline_batch_id IS NOT NULL;
```

#### Locale Referential Integrity Contract (07-aligned)

- Create EN row first and issue `translation_group_id`.
- KO row requires `source_post_id` and `source_post_version`.
- EN row rule: `source_post_id IS NULL`.
- KO row rule: `source_post_id IS NOT NULL`.
- During KO save, lock EN row with `FOR UPDATE`.
- Allow KO publish only when `source_post_version == EN current version`.
- On EN revision mismatch, block KO publish and move to re-sync queue.

> **JSONB 통합 결정 (ADR):** v2.0에서 guide_items 관련 5개 컬럼 + related_news 관련 3개 컬럼을 각각 JSONB 1개로 통합했다. 이유: (1) 컬럼 수를 크게 줄여 스키마 복잡도 완화, (2) 두 그룹 모두 항상 한 덩어리로 읽고 쓰므로 JOIN 불필요, (3) PydanticAI가 JSONB 내부 구조를 검증하므로 데이터 무결성 유지. 개별 필드로 WHERE 조건 검색이 필요해지면 GIN 인덱스를 추가하면 된다.

### comments 테이블

```sql
CREATE TABLE comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     UUID REFERENCES news_posts(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_id   UUID REFERENCES comments(id) ON DELETE CASCADE,  -- 대댓글 지원
    content     TEXT NOT NULL CHECK (char_length(content) <= 2000),
    likes_count INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_post ON comments(post_id, created_at);
```

> **댓글 CRUD:** FastAPI를 거치지 않고 Frontend에서 Supabase JS SDK로 직접 처리한다. RLS 정책(섹션 2)이 권한을 관리하고, `char_length(content) <= 2000` CHECK 제약이 DB 레벨에서 글자 수를 제한한다.

### comment_likes 테이블

```sql
CREATE TABLE comment_likes (
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    comment_id  UUID REFERENCES comments(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, comment_id)
);
```

### news_candidates 테이블 (뉴스 수집 후보)

```sql
CREATE TABLE news_candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tavily_query    TEXT NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    snippet         TEXT,
    assigned_type   TEXT CHECK (assigned_type IN ('research', 'business_main', 'big_tech', 'industry_biz', 'new_tools', 'unassigned')),
    relevance_score DECIMAL(3,2),
    ranking_reason  TEXT,                    -- AI가 이 점수를 준 이유
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'selected', 'rejected', 'published')),
    collected_at    TIMESTAMPTZ DEFAULT NOW(),
    batch_id        TEXT NOT NULL
);

CREATE INDEX idx_candidates_batch ON news_candidates(batch_id, assigned_type, relevance_score DESC);
```

### pipeline_logs 테이블

```sql
CREATE TABLE pipeline_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_type   TEXT NOT NULL,         -- 'news_collection', 'ranking', 'research_draft', 'business_draft', 'editorial', 'daily_pipeline'
    status          TEXT NOT NULL,          -- 'started', 'success', 'failed', 'retried', 'no_news'
    input_summary   TEXT,
    output_summary  TEXT,
    error_message   TEXT,
    duration_ms     INTEGER,
    model_used      TEXT,
    tokens_used     INTEGER,
    cost_usd        DECIMAL(10,6),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_logs_type ON pipeline_logs(pipeline_type, created_at DESC);
```

### pipeline_runs 테이블 (중복 실행 방지 락)

```sql
CREATE TABLE pipeline_runs (
    run_key      TEXT PRIMARY KEY, -- 예: daily:2026-03-04
    status       TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    started_at   TIMESTAMPTZ DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    last_error   TEXT
);
```

### admin_notifications 테이블

```sql
CREATE TABLE admin_notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### embeddings 테이블 (Phase 3)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     UUID REFERENCES news_posts(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    embedding   VECTOR(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## 4. PydanticAI 검증 스키마

모든 OpenAI API 출력은 Supabase 저장 전 PydanticAI로 검증한다. 스키마 파일 위치: `api/models/`

### 보조 스키마 (필드 명세)

| 모델 | 필드 | 타입 | 제약 |
|---|---|---|---|
| **QuizPoll** | question | `str` | |
| | options | `list[str]` | 2~4개 |
| | answer | `str` | |
| | explanation | `str` | 정답 해설 |
| **PromptGuideItems** | one_liner | `str` | |
| *(→ news_posts.guide_items JSONB)* | action_item | `str` | |
| | critical_gotcha | `str` | |
| | rotating_item | `str` | market_context / analogy / source_check 중 1개 내용 |
| | quiz_poll | `QuizPoll` | |
| **RelatedNewsItem** | title | `str` | |
| | url | `str` | |
| | summary | `str` | 한 줄 요약 |
| **RelatedNews** | big_tech | `Optional[RelatedNewsItem]` | null이면 해당 카테고리 뉴스 없음 |
| *(→ news_posts.related_news JSONB)* | industry_biz | `Optional[RelatedNewsItem]` | |
| | new_tools | `Optional[RelatedNewsItem]` | |
| **NewsCandidate** | title, url, snippet | `str` | |
| | source | `str` | tavily \| hackernews \| github |
| **RankedCandidate** | title, url, snippet, source | `str` | |
| | assigned_type | `Literal["research","business_main","big_tech","industry_biz","new_tools"]` | |
| | relevance_score | `float` | 0~1 |
| | ranking_reason | `str` | |
| **RelatedPicks** | big_tech | `Optional[RankedCandidate]` | |
| | industry_biz | `Optional[RankedCandidate]` | |
| | new_tools | `Optional[RankedCandidate]` | |
| **NewsRankingResult** | research_pick | `RankedCandidate` | Top 1 연구 뉴스 |
| | business_main_pick | `RankedCandidate` | Top 1 비즈니스 뉴스 |
| | related_picks | `RelatedPicks` | 카테고리별 관련 뉴스 |

### 메인 출력 스키마 — ResearchPost

```python
class ResearchPost(BaseModel):
    """Research Engineer 포스트 검증 스키마"""
    has_news: bool
    title: str
    slug: str
    content_original: Optional[str] = None    # has_news=True일 때 필수
    no_news_notice: Optional[str] = None      # has_news=False일 때 필수
    recent_fallback: Optional[str] = None
    guide_items: Optional[PromptGuideItems] = None
    source_urls: list[str] = []
    news_temperature: int                     # 1~5
    tags: list[str] = []
```

### 메인 출력 스키마 — BusinessPost

```python
class BusinessPost(BaseModel):
    """Business Analyst 포스트 검증 스키마"""
    title: str
    slug: str
    content_beginner: str                     # 비전공자 버전
    content_learner: str                      # 학습자 버전
    content_expert: str                       # 현직자 버전
    guide_items: PromptGuideItems
    related_news: RelatedNews
    source_urls: list[str] = []
    news_temperature: int                     # 1~5
    tags: list[str] = []
```

### 메인 출력 스키마 — EditorialFeedback

```python
class EditorialFeedback(BaseModel):
    """Editorial Agent 검수 결과 스키마"""
    accuracy_score: int = Field(ge=1, le=10)
    readability_score: int = Field(ge=1, le=10)
    seo_score: int = Field(ge=1, le=10)
    tone_consistency: int = Field(ge=1, le=10)
    suggestions: list[str]
    critical_issues: list[str]
    overall_verdict: Literal["publish_ready", "needs_revision", "major_rewrite"]
```

> **교차 검증 규칙 (field_validator로 구현):**
> - `ResearchPost`: has_news=True → content_original 필수
> - `ResearchPost`, `BusinessPost`: news_temperature는 1~5 범위
>
> **Editorial 판정 기준:**
> - 모든 항목 7점 이상 + critical_issues 없음 → `publish_ready`
> - 어느 항목이든 5점 미만 또는 critical_issues 1개 이상 → `needs_revision`
> - 어느 항목이든 3점 미만 → `major_rewrite`

---

## 5. AI 프롬프트 시스템

### 5-1. Ranking Agent 프롬프트

변수명: `RANKING_SYSTEM_PROMPT` / 출력 스키마: `NewsRankingResult`

<prompt>
당신은 0to1log의 뉴스 에디터입니다. Tavily가 수집한 AI 뉴스 목록을 분류하고 중요도를 평가합니다.

## 분류 기준

각 뉴스를 아래 5가지 타입 중 가장 적합한 1개에 배정하세요:

1. **research**: 새로운 모델 출시, SOTA 달성, 아키텍처 혁신, 주요 논문 — 기술적 깊이가 핵심
2. **business_main**: 시장에 큰 영향을 주는 전략적 발표, 대규모 투자, 핵심 정책 변화 — 분석 가치가 가장 높은 1개
3. **big_tech**: OpenAI, Google, Microsoft, Meta, Apple, Amazon의 AI 관련 발표
4. **industry_biz**: AI 스타트업 투자, 기업 파트너십, 규제/정책 변화
5. **new_tools**: 새로 출시된 AI 도구, 서비스, 플랫폼

## 중요도 평가 기준 (0~1)
- 기술적 혁신성 또는 비즈니스 임팩트
- 독자 관심도 (개발자/PM이 관심 가질 주제)
- 시의성 (24시간 이내 발표)
- 출처 신뢰도 (1차 출처 우선)

## 핵심 규칙
- research 타입에서 Top 1을 선별하세요
- business_main은 분석 가치가 가장 높은 뉴스 1개만 배정하세요
- big_tech, industry_biz, new_tools는 각각 최대 1개씩 Related News로 배정하세요
- 해당 카테고리에 적합한 뉴스가 없으면 해당 pick을 null로 두세요
- 하나의 뉴스가 여러 카테고리에 해당할 수 있지만, 가장 적합한 1개에만 배정하세요

반드시 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.
</prompt>

### 5-2. Research Engineer Agent 프롬프트

변수명: `RESEARCH_SYSTEM_PROMPT` / 출력 스키마: `ResearchPost`

<prompt>
당신은 0to1log의 AI 리서치 엔지니어입니다. Tavily가 수집한 기사를 바탕으로 기술 심화 포스트를 작성합니다.

## 당신의 원칙
- 마케팅 미사여구를 절대 사용하지 않습니다
- 확인되지 않은 수치는 반드시 "미확인"으로 표기합니다
- 모든 주장에는 출처(논문, 공식 블로그, GitHub)를 명시합니다

## 포스트 작성 지침

### 뉴스가 있을 때
Tavily가 제공한 기사를 바탕으로 아래 구조의 포스트를 작성하세요:

**본문 (content_original):**
1. 기술적 변경점 요약 (아키텍처, 학습 방법, 데이터셋)
2. 정량적 지표 (파라미터 수, 벤치마크 점수, SOTA 대비 개선율)
3. 실무 적용 가능성 (어떤 상황에서 써볼 만한지)
4. 관련 코드/논문 링크

**5블록 항목 (guide_items):**
1. [The One-Liner]: 이 기술을 한 문장으로 정의
2. [Action Item]: 개발자가 당장 해볼 수 있는 것 (라이브러리, 튜토리얼 등)
3. [Critical Gotcha]: 성능 수치 뒤에 숨겨진 한계점 (비용, 추론 속도, 재현성 등)
4. [회전 항목]: market_context / analogy / source_check 중 이 뉴스에 가장 적합한 1개 선택
5. [Today's Quiz/Poll]: 기술 내용 기반 퀴즈 또는 예측 투표

### 뉴스가 없을 때
has_news를 false로 설정하고:
- no_news_notice: "지난 24시간({날짜 범위}) 동안 공개된 실질적인 AI 기술 업데이트는 확인되지 않았습니다." 형식으로 작성
- recent_fallback: 최근(기간 외) 주목할 만한 기술 동향을 카테고리별로 보충 설명. 반드시 "기간 외"임을 명시할 것.
  - LLM & SOTA Models
  - Open Source & Repos
  - Research Papers

## Verification Filters
- Write in English. Use precise technical terminology.
- Unverified figures must be marked "unverified"
- No fabricated information

Respond in JSON format only.
</prompt>

### 5-3. Business Analyst Agent 프롬프트

변수명: `BUSINESS_SYSTEM_PROMPT` / 출력 스키마: `BusinessPost`

<prompt>
당신은 0to1log의 AI 비즈니스 분석가이자 PM입니다. Tavily가 수집한 기사를 바탕으로 3가지 독자 페르소나에 맞춘 포스트와 Related News를 작성합니다.

## 당신의 원칙
- 기술적 세부사항보다 "그래서 누가 돈을 벌고, 누가 위험해지는가"에 집중합니다
- 비전공자도 이해할 수 있는 비유를 반드시 포함합니다
- 투자, 파트너십, 규제 등 비즈니스 맥락을 놓치지 않습니다

## 메인 포스트 — 3페르소나 버전

### 비전공자 버전 (content_beginner)
- 모든 전문 용어를 일상적 비유로 대체
- 배경지식 없이 이해 가능한 스토리텔링 형식
- "왜 이게 중요한데?"에 대한 답이 명확해야 함
- 분량: 300~500자

### 학습자 버전 (content_learner)
- 핵심 개념 + 코드 스니펫 또는 레퍼런스 링크 포함
- "왜 중요한지" 맥락 + "뭘 공부하면 되는지" 방향 제시
- 분량: 500~800자

### 현직자 버전 (content_expert)
- 기술적 세부사항 + 업계 영향도 + 실무 적용 포인트
- 비용 분석, 경쟁 구도, 비즈니스 기회 포함
- 분량: 800~1200자

## 5블록 항목 (guide_items — 프롬프트 가이드 v1.3)

1. [The One-Liner]: 초등학생도 이해할 수 있는 핵심 한 문장 — 디폴트: 비전공자
2. [Action Item]: Dev와 PM 각각이 당장 할 수 있는 것 — 디폴트: 학습자
3. [Critical Gotcha]: 화려한 수치 뒤 한계점 리얼리티 체크 — 디폴트: 현직자
4. [회전 항목]: market_context / analogy / source_check 중 이 뉴스에 가장 적합한 1개 선택
5. [Today's Quiz/Poll]: 뉴스 기반 퀴즈 또는 도발적인 투표 주제

## Related News — 3개 카테고리 (related_news)

Tavily 수집 결과 중 메인 뉴스 외의 기사들을 아래 카테고리별로 한 줄 요약하세요.
해당 카테고리에 뉴스가 없으면 반드시 "지난 24시간 내 확인된 [카테고리] 소식 없음" 형식으로 작성하세요.

1. **Big Tech:** OpenAI, Google, Microsoft, Meta 등의 주요 발표
2. **Industry & Biz:** AI 스타트업 투자, 기업 파트너십, 규제 이슈
3. **New Tools:** 새로 출시된 AI 툴이나 서비스

## Verification Filters
- Write in English. Use precise technical terminology.
- Unverified figures must be marked "unverified"
- No fabricated information

Respond in JSON format only.
</prompt>

### 5-4. Translation Agent 프롬프트

변수명: `TRANSLATE_SYSTEM_PROMPT`

> EN-first 원칙 (docs/07 §4 참조): EN canonical draft를 먼저 생성한 후, Translation Agent가 KO localized derivative를 생성한다.

<prompt>
You are a professional Korean localizer for 0to1log, an AI news intelligence platform.
Translate the given English AI news post into natural Korean.

## Rules
- This is NOT literal translation. Adapt for Korean readers with local market context.
- Technical terms: keep English original in parentheses (e.g., 정렬(Alignment))
- Preserve all markdown formatting, links, and structure
- Preserve all URLs unchanged
- Match the tone: informative but accessible
- Do NOT add or remove information from the original
- 번역투 금지: 자연스러운 한국어 문장 사용

Respond in JSON format only. Return the same JSON structure with all text fields translated to Korean.
</prompt>

### 5-5. Editorial Agent 프롬프트

변수명: `EDITORIAL_SYSTEM_PROMPT` / 출력 스키마: `EditorialFeedback`

<prompt>
당신은 0to1log의 수석 에디터입니다. Business Analyst Agent가 작성한 초안을 검수합니다.

## 검수 기준
1. **기술적 정확도 (1~10):** 사실 오류, 수치 오류, 개념 혼동 여부
2. **가독성 (1~10):** 페르소나별 톤 적절성, 문장 자연스러움. 특히 비전공자/학습자/현직자 버전이 형식과 깊이에서 확실히 구분되는지 확인
3. **SEO 적합성 (1~10):** 제목, 태그, 슬러그의 검색 최적화 수준
4. **톤앤매너 일관성 (1~10):** 0to1log 브랜드 톤과의 일치도

## 판정 기준
- 모든 항목 7점 이상 + critical_issues 없음 → "publish_ready"
- 어느 항목이든 5점 미만 또는 critical_issues 1개 이상 → "needs_revision"
- 어느 항목이든 3점 미만 → "major_rewrite"

## 특별 검수 항목
- 비전공자 버전에 전문 용어가 비유 없이 사용되었는지
- 현직자 버전에 구체적 수치/비용 정보가 포함되어 있는지
- Related News에 "없음" 표기가 적절한지 (실제로 없는 건지 확인)

반드시 JSON 형식으로만 응답하세요.
</prompt>

---

## 6. AI 파이프라인

### 6-1. Daily News Pipeline 전체 흐름

```
[Vercel Cron: 매일 06:00 KST]
       │
       ▼
[Vercel API Route] → Railway POST /api/cron/news-pipeline (fire-and-forget)
       │                    │
       │                    ▼
       │             [Railway: 202 Accepted 즉시 반환]
       │                    │
       ▼                    ▼ (백그라운드 실행)
[Vercel 종료]        [Step 1] Tavily 뉴스 수집 (15~20개)
  (10초 내)                 │
                            ▼
                     [Step 2] Ranking Agent (gpt-4o-mini): 분류 + 랭킹
                            │  ├── research_pick: Top 1 URL (또는 null)
                            │  ├── business_main_pick: Top 1 URL
                            │  └── related_picks: {big_tech, industry_biz, new_tools} 각 1개 URL
                            │
                            ▼ (병렬 실행)
                     [Step 3-A] Research Engineer Agent (gpt-4o)
                            │  ├── 뉴스 있음 → 기술 심화 포스트 생성 → PydanticAI 검증 → 자동 발행
                            │  └── 뉴스 없음 → "없음" 공지 + 최근 동향 보충 → 자동 발행
                            │
                     [Step 3-B] Business Analyst Agent (gpt-4o)
                            │  ├── 메인 뉴스 → 3페르소나 포스트 + 5블록 생성
                            │  └── Related News → 3카테고리 한 줄 요약 (없으면 "없음" 표기)
                            │
                            ▼
                     [Step 4] PydanticAI 스키마 검증
                            │
                            ▼
                     [Step 5] Supabase 저장
                            │  ├── Research → status: 'published' (자동)
                            │  └── Business → status: 'draft' (검수 대기)
                            │
                            ▼
                     [Step 6] Business 포스트: Editorial Agent (gpt-4o) 검수
                            │  → Admin 대시보드에서 확인 후 수동 발행
                            │
                            ▼
                     [완료] pipeline_logs에 결과 기록
                            └── 실패 시 admin_notifications에 알림 저장
```

### 6-2. Step 1: Multi-Source 뉴스 수집

**함수:** `collect_news()` → `list[dict]` (각 항목: `{title, url, content, source}`)

**수집 흐름:**
1. **Tavily 검색** — 4개 쿼리 병렬 실행 (각 max 3건, search_depth=advanced, time_range=24h)
2. **Hacker News** — Top 80개 중 AI 키워드 필터 (`ai|llm|gpt|openai|anthropic|gemini|claude`, 대소문자 무시)
3. **GitHub Trending** — 어제 생성된 `topic:ai` 레포 중 Stars 상위 3개
4. **URL 정규화 중복 제거** — `url.split("#")[0].split("?")[0].rstrip("/")` 기준

**수집 설정 (COLLECTION_CONFIG):**

| 키 | 값 | 설명 |
|---|---|---|
| queries | 4개 영어 쿼리 | "AI LLM new model release today" 등 |
| max_results_per_query | 3 | |
| search_depth | "advanced" | |
| time_range | "24h" | |
| http_timeout_sec | 10 | HN/GitHub API 타임아웃 |
| hn_top_n | 80 | HN에서 가져올 상위 게시물 수 |
| hn_concurrency | 12 | HN 병렬 요청 제한 |

**실패 처리:** Tavily 쿼리별 30초 후 1회 재시도, 실패 시 해당 쿼리 스킵. HN/GitHub 실패 시 빈 리스트 반환.

### 6-3~6-6. 에이전트 함수 명세

모든 에이전트는 `generate_with_validation_retry()` 유틸리티를 통해 호출한다 (섹션 8 참조).

| Step | 함수 | 모델 | 입력 | 출력 스키마 | 핵심 로직 |
|---|---|---|---|---|---|
| 2 | `rank_news()` | gpt-4o-mini | 수집된 후보 + batch_id | `NewsRankingResult` | JSON mode, RANKING_SYSTEM_PROMPT |
| 3-A | `generate_research_post()` | gpt-4o | research_pick 후보 + 본문 (또는 None) | `ResearchPost` | 뉴스 유무에 따라 user_content 분기 |
| 3-B | `generate_business_post()` | gpt-4o | business_main 후보 + 본문 + related 3카테고리 | `BusinessPost` | 메인 뉴스 + Related News 섹션 조합 |
| 6 | `review_business_post()` | gpt-4o | Business 초안 JSON | `EditorialFeedback` | EDITORIAL_SYSTEM_PROMPT로 검수 |

**user_content 구성 규칙:**
- Research (뉴스 있음): 날짜 + 선별 뉴스 Title/URL/이유 + 기사 본문
- Research (뉴스 없음): 날짜 + "has_news=false로 설정하고 no_news_notice/recent_fallback 작성" 지시
- Business: 날짜 + 메인 뉴스(Title/URL/이유/본문) + Related News 3카테고리(각 Title/URL/요약 또는 "없음")

### 6-7. 전체 파이프라인 오케스트레이터

**함수:** `run_daily_news_pipeline()` — 위 6-1 흐름도를 코드로 구현

**핵심 규칙:**
- **batch_id:** KST 기준 `YYYY-MM-DD` (예: `2026-03-04`)
- **중복 실행 방지:** `pipeline_runs` 테이블에 `run_key = "daily:{batch_id}"` INSERT 시도 → 이미 존재하면 스킵
- **Research/Business 병렬:** `asyncio.gather()`로 두 에이전트 동시 실행
- **slug 패턴:** `{batch_id}-research-daily`, `{batch_id}-business-daily` (멱등성)
- **발행 분리:** Research → `status='published'` (자동), Business → `status='draft'` (검수 대기)
- **멱등 저장:** `supabase.table("news_posts").upsert(data, on_conflict="slug")` — 같은 slug면 갱신
- **실패 처리:** `pipeline_logs`에 실패 기록 + `admin_notifications`에 알림 + `pipeline_runs` status='failed'

### 6-8. JSONB 저장 변환

**함수:** `save_post(post, status, batch_id)` — Pydantic 모델 → Supabase news_posts 테이블

**매핑 규칙:**
- `guide_items` → `PromptGuideItems.model_dump()` → news_posts.guide_items JSONB
- `related_news` → `RelatedNews.model_dump()` → news_posts.related_news JSONB (Business만)
- `persona_content` → 개별 컬럼으로 분해: `content_beginner`, `content_learner`, `content_expert` (Business만)
- `status='published'`일 때 `published_at` 자동 설정

> **[성공 기준]**
> 1. `collect_news()` 반환 리스트에서 중복 URL 0개
> 2. `run_daily_news_pipeline()` 1회 실행 → news_posts 테이블에 Research(status=published) 1행 + Business(status=draft) 1행 적재
> 3. 동일 batch_id로 2회 트리거 → pipeline_runs 락으로 2번째 스킵, pipeline_logs에 "skip: already running/completed" 기록
> 4. pipeline_logs 최종 행 status=success, error_message=NULL

---

## 7. FastAPI 엔드포인트

### 7-1. 엔드포인트 목록

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| **Cron / Pipeline** | | | |
| POST | `/api/cron/news-pipeline` | Daily News Pipeline 트리거 (fire-and-forget) | Cron Secret |
| **Admin — 콘텐츠 관리** | | | |
| GET | `/api/admin/drafts` | 검수 대기 초안 목록 조회 | Admin |
| GET | `/api/admin/drafts/{slug}` | 초안 상세 + Editorial 피드백 조회 | Admin |
| PATCH | `/api/admin/posts/{id}/publish` | 초안 → 발행 상태 변경 | Admin |
| PATCH | `/api/admin/posts/{id}/update` | 초안 내용 수정 (수동 편집) | Admin |
| POST | `/api/admin/posts/{id}/regenerate` | 특정 초안 재생성 요청 | Admin |
| **Admin — AI 기능** | | | |
| POST | `/api/admin/ai/draft` | 수동 초안 생성 (키워드 또는 URL 입력) | Admin |
| POST | `/api/admin/ai/review` | 수동 Editorial 검수 요청 | Admin |
| POST | `/api/admin/ai/rewrite` | Editorial 피드백 기반 재작성 | Admin |
| **Admin — 대시보드 (Phase 3)** | | | |
| GET | `/api/admin/dashboard/costs` | API 비용 모니터링 데이터 | Admin |
| GET | `/api/admin/dashboard/prompts` | 프롬프트 버전 이력 | Admin |
| **Public — 검색 (Phase 3)** | | | |
| POST | `/api/search/semantic` | 시맨틱 검색 (pgvector) | Public |
| **Public/User — 커뮤니티 & 포인트 (Phase 4)** | | | |
| GET | `/api/community/me/points` | 내 포인트/레벨 조회 | User |
| POST | `/api/community/points/earn` | 이벤트 기반 포인트 적립 | User |
| POST | `/api/community/predictions` | 퀴즈/베팅 참여 | User |
| POST | `/api/community/predictions/{id}/settle` | 정답 처리 및 포인트 정산 | Admin |
| **User/Admin — 구독 권한 (Phase 4+)** | | | |
| GET | `/api/subscription/me/access` | 현재 구독 등급/접근 권한 조회 | User |
| POST | `/api/subscription/webhook/polar` | 결제 이벤트 동기화 웹훅 | Webhook Secret |

> **댓글 API 제거 (ADR):** v2.0에 있던 `/api/comments` 엔드포인트를 제거했다. 댓글 CRUD는 Frontend에서 Supabase JS SDK로 직접 처리하며, RLS 정책이 권한을 관리한다. FastAPI는 검색/커뮤니티/구독 권한/AI 파이프라인처럼 서버 로직이 필요한 도메인에 집중한다. (상세 근거: 섹션 2 댓글 시스템 ADR 참조)

### 7-2. Cron 엔드포인트 — fire-and-forget 구현

```python
import asyncio
from fastapi import BackgroundTasks

CRON_SECRET = os.environ["CRON_SECRET"]

async def verify_cron_secret(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "유효하지 않은 Cron 시크릿")

@app.post("/api/cron/news-pipeline", status_code=202)
async def trigger_news_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_cron_secret)
):
    """fire-and-forget: 202 즉시 반환, 파이프라인은 백그라운드 실행
    실제 중복 실행 방지는 run_daily_news_pipeline 내부 run_key 락으로 처리
    """
    background_tasks.add_task(run_daily_news_pipeline)
    return {"status": "accepted", "message": "파이프라인 백그라운드 실행 시작"}
```

> **핵심:** FastAPI의 `BackgroundTasks`를 사용하여 HTTP 응답(202)을 먼저 보내고, 파이프라인은 백그라운드에서 실행한다. Vercel의 10초 타임아웃 문제를 완전히 우회한다.

### 7-3. Vercel Cron 설정

```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/trigger-pipeline",
      "schedule": "0 21 * * *"
    }
  ]
}
```

> **시간:** UTC 21:00 = KST 06:00 (매일 아침 6시)

```typescript
// Astro: src/pages/api/trigger-pipeline.ts
export async function POST({ request }) {
  try {
    const response = await fetch(`${import.meta.env.FASTAPI_URL}/api/cron/news-pipeline`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${import.meta.env.CRON_SECRET}`,
        "Content-Type": "application/json"
      },
      signal: AbortSignal.timeout(8000) // 8초 타임아웃 (Vercel 10초 한도 내)
    });
    
    if (response.status === 202) {
      return new Response(JSON.stringify({ status: "triggered" }), { status: 200 });
    }
    
    return new Response(JSON.stringify({ error: "Railway 응답 오류" }), { status: 502 });
  } catch (error) {
    // 네트워크 타임아웃이 나면 실행 여부가 불확실할 수 있으므로
    // pipeline_logs에서 실제 실행 상태를 확인
    return new Response(JSON.stringify({ 
      status: "uncertain", 
      message: "Railway 응답 타임아웃 — pipeline_logs에서 실행 여부 확인 필요" 
    }), { status: 200 });
  }
}
```

> **타임아웃 처리 원칙:** Vercel Serverless 제한(10초) 내에서 안전하게 종료하기 위해 8초 타임아웃을 둔다. 타임아웃이 발생하면 성공/실패를 추정하지 않고 `pipeline_logs`를 단일 진실 소스로 확인한다.

---

## 8. 에러 핸들링 & 재시도 로직

### 8-1. 파이프라인 체인별 에러 정책

| 단계 | 실패 원인 | 재시도 | 실패 시 동작 |
|---|---|---|---|
| **Tavily 수집** | API 타임아웃, 429 Rate Limit | 30초 후 1회 | 해당 쿼리 스킵, 나머지 쿼리로 진행 |
| **Ranking (4o-mini)** | API 타임아웃, 잘못된 JSON | 60초 후 1회 | 랭킹 없이 전체 후보를 Admin에게 전달 |
| **Research Draft (4o)** | API 타임아웃, 잘못된 JSON | 60초 후 2회 | "뉴스 없음" 공지로 대체 발행 |
| **Business Draft (4o)** | API 타임아웃, 잘못된 JSON | 60초 후 2회 | 해당 뉴스 스킵, 로그 기록 |
| **Editorial (4o)** | API 타임아웃, 잘못된 JSON | 60초 후 1회 | 검수 없이 draft 저장, "수동 검수 필요" 태그 |
| **PydanticAI 검증** | 스키마 불일치 | 재시도 없음 | 에러 내용 포함하여 재생성 1회 시도 |
| **Supabase 저장** | 연결 실패, 중복 slug | 10초 후 2회 | 실패 로그 + Admin 알림 |

### 8-2. 재시도 유틸리티

```python
import asyncio
from functools import wraps

def with_retry(max_retries: int = 2, delay_seconds: float = 30, backoff: float = 2.0):
    """재시도 데코레이터 — 지수 백오프"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = delay_seconds * (backoff ** attempt)
                        await log_pipeline(
                            func.__name__, "retried",
                            error_message=f"Attempt {attempt+1} failed: {str(e)}. Retrying in {wait}s"
                        )
                        await asyncio.sleep(wait)
            
            await log_pipeline(
                func.__name__, "failed",
                error_message=f"All {max_retries+1} attempts failed: {str(last_error)}"
            )
            raise last_error
        return wrapper
    return decorator
```

### 8-3. PydanticAI 검증 실패 시 자동 재생성

```python
async def generate_with_validation_retry(
    system_prompt: str,
    user_content: str,
    schema_class: type[BaseModel],
    model: str = "gpt-4o"
) -> BaseModel:
    """1차 생성 → 검증 실패 시 에러 포함하여 재생성 1회"""
    
    # 1차 시도
    response = await openai_client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )
    
    try:
        return schema_class.model_validate_json(response.choices[0].message.content)
    except ValidationError as e:
        validation_errors = str(e)
    
    # 2차 시도: 에러 내용 포함
    response = await openai_client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": response.choices[0].message.content},
            {"role": "user", "content": f"위 응답에서 다음 검증 오류가 발생했습니다. 수정하여 다시 생성하세요:\n{validation_errors}"}
        ]
    )
    
    return schema_class.model_validate_json(response.choices[0].message.content)
```

### 8-4. Admin 알림

```python
async def notify_admin_on_failure(pipeline_type: str, error: str):
    """파이프라인 실패 시 Admin 알림 저장"""
    await supabase.table("admin_notifications").insert({
        "type": "pipeline_failure",
        "title": f"[{pipeline_type}] 파이프라인 실패",
        "message": error[:500],  # 에러 메시지 길이 제한
        "is_read": False
    }).execute()
```

> **알림 확인 방법:** Admin 대시보드에서 admin_notifications 테이블을 조회한다. Phase 3에서 이메일 알림(Supabase Webhooks 또는 Resend API)으로 업그레이드 가능.

---

## 9. 비용 관리

### 9-1. API 사용 비용 (OpenAI + Tavily)

#### 모델별 사용 전략

| 작업 | 모델 | 이유 |
|---|---|---|
| 뉴스 분류 + 랭킹 | gpt-4o-mini | 단순 분류, 비용 최소화 |
| Research Engineer 초안 | gpt-4o | 기술 정확도 필요 |
| Business Analyst 초안 | gpt-4o | 3페르소나 품질 필요 |
| Editorial 검수 | gpt-4o | 정확한 평가 필요 |
| 슬러그/태그 생성 | gpt-4o-mini | 단순 변환 |
| 시맨틱 검색 임베딩 (Phase 3) | text-embedding-3-small | pgvector 호환, 비용 효율 |

> **모델 교체 유연성 (ADR):** 현재 gpt-4o/gpt-4o-mini를 기본으로 설계하되, 모델명을 환경 변수 또는 config로 관리하여 GPT-5.2 등 신규 모델로 교체가 용이하도록 한다. 2026년 3월 기준 GPT-5.2($1.75/$14.00)가 출시되었으나, 비용 대비 성능 검증 후 교체 결정. 현재 gpt-4o($2.50/$10.00)가 출력 토큰 단가가 더 저렴하므로 당장 교체할 이유 없음.

#### 일일 예상 비용 산정

```
[매일 뉴스 2건 기준 — gpt-4o 기준가]

Step 2 — 랭킹 (gpt-4o-mini):
  Input: ~3,000 tokens × $0.15/1M = $0.00045
  Output: ~1,500 tokens × $0.60/1M = $0.0009

Step 3-A — Research (gpt-4o):
  Input: ~3,000 tokens × $2.50/1M = $0.0075
  Output: ~2,000 tokens × $10.00/1M = $0.02

Step 3-B — Business (gpt-4o):
  Input: ~5,000 tokens × $2.50/1M = $0.0125
  Output: ~4,000 tokens × $10.00/1M = $0.04

Step 6 — Editorial (gpt-4o):
  Input: ~4,000 tokens × $2.50/1M = $0.01
  Output: ~1,000 tokens × $10.00/1M = $0.01

Tavily API: 기본 ~4 queries × $0.01 = $0.04
            (쿼리별 재시도 발생 시 최대 ~8 queries = $0.08)

일일 예상 총 비용: ~$0.14 (재시도 평균 포함 ~$0.15 내외)
월간 예상 총 비용: ~$4.2~4.5
```

> **API 비용 모니터링:** 모든 API 호출의 토큰/비용을 pipeline_logs 테이블에 기록하여 Phase 3 AI Ops Dashboard에서 추적. 월 $10 초과 시 admin_notifications에 비용 경고 알림 생성.

### 9-2. Railway 운영비 (단계별)

| 운영 단계 | 운영 모드 | 월 비용 가정 | 전환 기준 |
|---|---|---|---|
| **Stage A (Phase 2)** | 범용 API 구조 + 저비용 운영 | Starter 기준 저비용 운영 (기본료 + 소량 컴퓨팅) | 초기 트래픽 구간, 파이프라인/관리 API 중심 |
| **Stage B (Phase 3+)** | Always-on 상시 API 운영 | 기본료 + 컴퓨팅 변동비 증가 | 검색 사용량/커뮤니티 액션/API 요청량 KPI 충족 시 |

> **운영비 원칙:** OpenAI/Tavily API 비용과 Railway 인프라 비용을 분리 추적한다. KPI 미달 상태에서는 Stage A를 유지하고, KPI 달성 시 Stage B로 상향한다.

---

## 10. 환경 변수

```env
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_MODEL_MAIN=gpt-4o          # 메인 모델 (교체 용이)
OPENAI_MODEL_LIGHT=gpt-4o-mini    # 경량 모델

# Tavily API
TAVILY_API_KEY=tvly-...

# Admin bootstrap (선택)
ADMIN_EMAIL=admin@0to1log.com  # 최초 admin_users 시드 입력용

# Cron
CRON_SECRET=your-random-secret-here

# App
FASTAPI_URL=https://your-app.railway.app
```

> **모델명 환경 변수화:** `OPENAI_MODEL_MAIN`과 `OPENAI_MODEL_LIGHT`를 환경 변수로 분리하여, 코드 수정 없이 Railway 대시보드에서 모델을 교체할 수 있다.
> **Admin 권한 기준:** 런타임 권한 판별은 `admin_users` 테이블을 사용하며, `ADMIN_EMAIL`은 초기 시드 자동화를 위한 보조 변수로만 사용한다.

---

## 11. 테스트 전략

### 11-1. 테스트 계층

| 계층 | 대상 | 도구 | 실행 시점 |
|---|---|---|---|
| **Unit** | PydanticAI 스키마, 재시도 로직, JSONB 변환, 유틸 함수 | pytest | 매 커밋 |
| **Integration** | Tavily → OpenAI → Supabase 체인 | pytest + 실제 API | PR 머지 전 |
| **E2E Pipeline** | Daily News Pipeline 전체 1회 실행 | 수동 트리거 | 주 1회 |
| **Schema Regression** | 프롬프트 변경 시 출력 형식 유지 | pytest + snapshot | 프롬프트 수정 시 |
| **API Boundary** | Supabase 직결 vs FastAPI 경유 경계 검증 | pytest + contract test | 경계 정책 변경 시 |
| **RLS** | 권한 정책 정상 작동 검증 | Supabase SQL Editor 수동 테스트 | RLS 변경 시 |

### 11-2. RLS 테스트 시나리오

RLS 정책에 버그가 있으면 DB가 직접 노출되므로, 배포 전 반드시 아래 시나리오를 검증한다.

```sql
-- 테스트 1: Visitor는 published 글만 볼 수 있는가?
-- (anon role로 실행)
SELECT * FROM news_posts WHERE status = 'draft';
-- 기대 결과: 0 rows

-- 테스트 2: User는 본인 댓글만 수정할 수 있는가?
-- (user_a로 로그인 후 user_b의 댓글 수정 시도)
UPDATE comments SET content = 'hacked' WHERE user_id = 'user_b_id';
-- 기대 결과: 0 rows affected

-- 테스트 3: User는 다른 사람의 좋아요를 삭제할 수 없는가?
DELETE FROM comment_likes WHERE user_id != auth.uid();
-- 기대 결과: 0 rows affected

-- 테스트 4: Admin이 아닌 User는 news_posts를 INSERT할 수 없는가?
INSERT INTO news_posts (title, slug, category, post_type) VALUES ('test', 'test', 'ai-news', 'research');
-- 기대 결과: RLS policy violation error
```

> **자동화 가능성:** Phase 3에서 pgTAP(PostgreSQL 테스트 프레임워크) 도입을 검토. 현재는 Supabase SQL Editor에서 수동 실행으로 충분.

### 11-3. API 경계 테스트 시나리오

| 시나리오 | 기대 경로 | 검증 포인트 |
|---|---|---|
| 글 목록/상세 조회 | Frontend → Supabase 직접 | FastAPI 호출 로그가 없어야 함 |
| 단순 댓글 CRUD | Frontend → Supabase 직접 | RLS 정책으로 권한 통제 |
| 시맨틱 검색(Cmd+K) | Frontend → FastAPI | `/api/search/semantic` 응답/에러 핸들링 검증 |
| 포인트 적립/퀴즈 참여 | Frontend → FastAPI | 트랜잭션 처리, 중복 요청 방지 |
| 구독 접근 권한 확인 | Frontend → FastAPI | 외부 결제 상태와 권한 매핑 일치 |
| Cron 트리거 | Vercel → FastAPI | 202 즉시 반환 + pipeline_logs 비동기 기록 |

### 11-4. 핵심 테스트 케이스

```python
# tests/test_schemas.py
# fixture/helper 예시: make_guide_items_fixture(), sample_business_candidate() 등은 conftest.py에 정의
class TestResearchPostSchema:
    def test_valid_post_with_news(self):
        """뉴스가 있을 때 정상 검증"""
        post = ResearchPost(
            title="GPT-5 추론 성능 2배 향상",
            slug="gpt-5-inference-2x",
            category="ai-news",
            post_type="research",
            has_news=True,
            content_original="GPT-5는 기존 대비...",
            source_urls=["https://openai.com/blog/gpt-5"],
            tech_spec=ResearchTechSpec(
                parameters="미공개",
                benchmark="MMLU 92.3%",
                improvement="GPT-4o 대비 15% 향상"
            ),
            news_temperature=4,
            guide_items=make_guide_items_fixture(),
            tags=["openai", "gpt-5"]
        )
        assert post.has_news is True
    
    def test_valid_post_no_news(self):
        """뉴스가 없을 때 '없음' 공지 검증"""
        post = ResearchPost(
            title="2026-03-04 AI Study Daily",
            slug="2026-03-04-study-daily",
            category="ai-news",
            post_type="research",
            has_news=False,
            no_news_notice="지난 24시간 동안 실질적인 AI 기술 업데이트는 확인되지 않았습니다.",
            recent_fallback="최근 주목할 만한 동향으로는...",
            tags=["daily-roundup"]
        )
        assert post.has_news is False
        assert post.no_news_notice is not None
    
    def test_news_exists_but_no_content_rejected(self):
        """has_news=True인데 content_original이 없으면 거부"""
        with pytest.raises(ValidationError):
            ResearchPost(
                title="invalid-case",
                slug="invalid-case",
                category="ai-news",
                post_type="research",
                has_news=True,
                content_original=None,
                source_urls=["https://example.com/news"],
                guide_items=make_guide_items_fixture(),
                tags=["invalid"]
            )
    
    def test_no_news_but_no_notice_rejected(self):
        """has_news=False인데 no_news_notice가 없으면 거부"""
        with pytest.raises(ValidationError):
            ResearchPost(
                title="invalid-no-news-case",
                slug="invalid-no-news-case",
                category="ai-news",
                post_type="research",
                has_news=False,
                no_news_notice=None,
                tags=["invalid"]
            )

class TestBusinessPostSchema:
    def test_valid_business_post(self):
        """Business 포스트 정상 검증 — 3페르소나 + Related News"""
        post = BusinessPost(
            title="AI 스타트업 Cursor, 시리즈 B 6천만 달러 투자 유치",
            slug="cursor-series-b-60m",
            category="ai-news",
            post_type="business",
            source_urls=["https://techcrunch.com/cursor-series-b"],
            news_temperature=3,
            persona_content=PersonaContent(
                content_beginner="코딩을 도와주는 AI 비서가 큰 투자를 받았습니다...",
                content_learner="Cursor는 VS Code 기반 AI 코드 에디터로...",
                content_expert="시리즈 B $60M은 AI 코드 에디터 시장의..."
            ),
            guide_items=make_guide_items_fixture(),
            related_news=RelatedNews(
                big_tech="Google, Gemini 2.5 Flash 공개 — 추론 비용 40% 절감",
                industry_biz="지난 24시간 내 확인된 AI 투자/파트너십 소식 없음",
                new_tools="Anthropic, Claude Code CLI 정식 출시"
            ),
            tags=["cursor", "startup", "investment"]
        )
        assert post.related_news.industry_biz.startswith("지난 24시간")
    
    @pytest.mark.asyncio
    async def test_persona_versions_are_different(self):
        """비전공자/학습자/현직자 버전이 동일하면 경고"""
        post = await generate_business_post(
            candidate=sample_business_candidate(),
            source_content="sample source content",
            related_candidates=sample_related_candidates(),
            related_contents=sample_related_contents(),
            batch_id="2026-03-04"
        )
        assert post.persona_content.content_beginner != post.persona_content.content_expert

class TestEditorialFeedback:
    def test_publish_ready(self):
        """모든 점수 7+, critical_issues 없음 → publish_ready"""
        feedback = EditorialFeedback(
            accuracy_score=8, readability_score=7,
            seo_score=7, tone_consistency=8,
            suggestions=["태그 추가 권장"],
            critical_issues=[],
            overall_verdict="publish_ready"
        )
        assert feedback.overall_verdict == "publish_ready"
    
    def test_critical_issue_blocks_publish(self):
        """critical_issues 있으면 publish_ready 불가"""
        feedback = EditorialFeedback(
            accuracy_score=6, readability_score=8,
            seo_score=7, tone_consistency=7,
            suggestions=[],
            critical_issues=["벤치마크 수치 출처 불명확"],
            overall_verdict="needs_revision"
        )
        assert len(feedback.critical_issues) > 0

class TestJsonbConversion:
    def test_guide_items_to_jsonb(self):
        """guide_items가 올바른 JSONB 구조로 변환되는지 검증"""
        items = PromptGuideItems(
            one_liner="GPT-5는 추론 성능이 2배 빨라진 모델",
            action_item="pip install openai 후 model='gpt-5'로 교체",
            critical_gotcha="추론 비용이 4o 대비 1.5배 — 대량 호출 시 주의",
            rotating_item_type="market_context",
            rotating_item="OpenAI vs Anthropic 경쟁 심화로 가격 인하 가능성",
            quiz_poll=QuizPoll(type="quiz", question="GPT-5의 MMLU 점수는?", options=["85%", "90%", "92.3%", "95%"], answer="92.3%")
        )
        jsonb = items.model_dump()
        assert "one_liner" in jsonb
        assert jsonb["quiz_poll"]["type"] == "quiz"

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        call_count = 0
        
        @with_retry(max_retries=2, delay_seconds=0.1)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("일시적 오류")
            return "success"
        
        assert await flaky() == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_exhausted_raises(self):
        @with_retry(max_retries=1, delay_seconds=0.1)
        async def always_fails():
            raise ConnectionError("영구 오류")
        
        with pytest.raises(ConnectionError):
            await always_fails()

class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_tavily_returns_results(self):
        results = await collect_news()
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_no_duplicate_urls(self):
        results = await collect_news()
        normalized_urls = [normalize_url(r["url"]) for r in results if "url" in r]
        assert len(normalized_urls) == len(set(normalized_urls))

    @pytest.mark.asyncio
    async def test_tavily_uses_24h_time_range(self, mocker):
        client = mocker.Mock()
        client.search.return_value = {"results": []}
        await search_tavily_with_retry(client, "test query")
        assert client.search.call_args.kwargs["time_range"] == "24h"
    
    @pytest.mark.asyncio
    async def test_ranking_assigns_types(self):
        mock_candidates = [...]
        ranking = await rank_news(mock_candidates, "2026-03-04")
        for c in ranking.candidates:
            assert c.assigned_type in ["research", "business_main", "big_tech", "industry_biz", "new_tools"]
    
    @pytest.mark.asyncio
    async def test_full_pipeline_produces_two_posts(self):
        """전체 파이프라인: Research(published) + Business(draft) 2개 생성"""
        results = await run_daily_news_pipeline()
        assert results["research"]["status"] == "published"
        assert results["business"]["status"] == "draft"
```

### 11-5. 테스트 실행

```bash
# 유닛 테스트 (로컬)
pytest tests/test_schemas.py tests/test_retry.py tests/test_jsonb.py -v

# 통합 테스트 (API 키 필요)
TESTING=true pytest tests/test_pipeline_integration.py -v

# 전체 파이프라인 수동 테스트
curl -X POST https://your-app.railway.app/api/cron/news-pipeline \
  -H "Authorization: Bearer $CRON_SECRET"
# → 202 Accepted 즉시 반환. pipeline_logs에서 결과 확인.
```

---

## 12. Phase별 Backend 구현 범위

> **Project Overview v2.1 동기화:** Phase 구조와 타이밍을 01_Project_Overview.md v2.1과 일치시킨다.

| 기능 | Phase 1a | Phase 1b | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|---|---|---|
| **인프라 기반** | | | | | | |
| Supabase 스키마 + CRUD | ✅ | | | | | |
| Supabase Auth (Admin + 소셜 로그인) | ✅ | | | | | |
| RLS 정책 | ✅ | | | | | |
| **데이터 수집 (Analytics)** | | | | | | |
| GA4 + MS Clarity 이벤트 수신용 스키마 | | ✅ | | | | |
| **AI 파이프라인** | | | | | | |
| FastAPI 기본 구조 + Railway 배포 | | | ✅ | | | |
| FastAPI 범용 API 라우팅 구조 (검색/커뮤니티/권한) | | | ✅ | ✅ | ✅ | |
| Tavily 뉴스 수집 | | | ✅ | | | |
| Ranking Agent (gpt-4o-mini) | | | ✅ | | | |
| Research Engineer Agent (gpt-4o) | | | ✅ | | | |
| Business Analyst Agent (gpt-4o) | | | ✅ | | | |
| Editorial Agent (gpt-4o) | | | ✅ | | | |
| PydanticAI 검증 레이어 | | | ✅ | | | |
| Vercel Cron 자동화 (fire-and-forget) | | | ✅ | | | |
| 에러 핸들링 + 재시도 로직 | | | ✅ | | | |
| pipeline_logs + admin_notifications | | | ✅ | | | |
| pipeline_runs(run_key 락) + 멱등 upsert | | | ✅ | | | |
| 자동/검수 발행 분리 | | | ✅ | | | |
| 테스트 (Unit + Integration + RLS) | | | ✅ | | | |
| **검색 & 대시보드** | | | | | | |
| pgvector 임베딩 + 시맨틱 검색 | | | | ✅ | | |
| AI Ops Dashboard API | | | | ✅ | | |
| Prompt Versioning | | | | ✅ | | |
| AARRR 지표 대시보드 | | | | ✅ | | |
| **수익화 & 커뮤니티** | | | | | | |
| 프리미엄 구독 모델 검토 | | | | | ✅ | |
| Polar 결제 연동 (구독 결정 시) | | | | | ✅ | |
| 포인트 시스템 API | | | | | ✅ | |
| 퀴즈/베팅 API | | | | | ✅ | |
| PWA Service Worker | | | | | ✅ | |
| **앱 확장** | | | | | | |
| Expo 네이티브 앱 API | | | | | | ✅ |


---


## 13. Policy Addendum (v3.3)

### 13-1. Locale Referential Integrity
- EN post is created first and issues `translation_group_id`.
- KO post cannot be created without `source_post_id` and `source_post_version`.
- EN row rule: `source_post_id IS NULL`. KO row rule: `source_post_id IS NOT NULL`.
- Lock EN row with `FOR UPDATE` during KO generation/save.
- KO publish is allowed only when `source_post_version == EN current version`.
- On mismatch, block publish and move KO to `hold/stale` re-sync queue.

### 13-2. Admin Manual Rerun API
`POST /api/admin/pipeline/rerun` (Admin only)

- Request: `target_date(YYYY-MM-DD)`, `mode(safe|force)`, `reason(1-200 chars)`, `trigger_revalidate(boolean=true)`
- Response: `202(queued)`, `200(safe skip)`, `409(running conflict)`, `422(validation error)`
- Behavior: `safe` skips if success run exists. `force` allows rerun but keeps idempotency via slug upsert.

### 13-3. Admin Access Contract
- Gate: `valid token + admin_users row + is_active=true`
- Minimal fields: `email`, `is_active`, `created_at`, `last_login_at`

### 13-4. Point Ledger Contract (Phase 4)
- Use `point_transactions` as the source of truth for point accounting.
- Recommended fields: `id`, `user_id`, `amount`, `reason`, `event_key`, `created_at`
- Duplicate guard: `UNIQUE(user_id, event_key)`
- Earn/spend must be processed in a single DB transaction.

### 13-5. Embedding Operations Policy
- Query cache key: `trim(lower(query))`
- Query embedding cache TTL: 5 minutes
- On embedding API failure, fallback to keyword search
- Capacity guardrails:
  - DB `< 400MB`: no cleanup
  - DB `>= 400MB`: set `embedding=NULL` for old archived low-traffic posts
  - DB `>= 450MB`: evaluate Pro plan before stronger cleanup
- Never delete canonical post body text; only shrink embeddings.

### 13-6. Extra Test Scenarios
- Block KO generation when EN reference row is missing
- Block KO publish on EN revision mismatch
- Deny admin API when `is_active=false`
- Block duplicate point awards by `event_key`
- Verify embedding failure fallback path
