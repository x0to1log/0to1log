# 🏗 0to1log — Infrastructure

> **문서 버전:** v2.3  
> **최종 수정:** 2026-03-05  
> **작성자:** Amy (Solo)  
> **상태:** Planning  
> **상위 문서:** `01_Project_Overview.md`

### v2.2 변경 이력

| 항목 | v2.0 | v2.2 | 이유 |
|---|---|---|---|
| Railway 역할 | "AI 파이프라인 실행 전용" (sleep/wake) | **범용 API 백엔드** + Stage A→B 단계적 운영 | 검색/커뮤니티/권한 로직 확장 대응 (03 v3.2 동기화) |
| 비용 모델 | Railway $5/월 고정 | API 비용 + Railway 운영비 **단계형 분리** (Stage A/B) | 인프라 의사결정 가시성 강화 |
| 운영 지표 | 없음 | p95 응답시간, error rate, uptime, rate-limit 현황 추가 | Phase 3 Always-on 전환 판단 기준 |
| Phase 동기화 | Overview v2.0 | **Overview v2.1** (Stage A→B 전환 마일스톤 반영) | 01/03/04/06 문서 동기화 |
| 무료 티어 대응 | Railway 크레딧 초과만 언급 | Always-on 전환 시 비용 리스크 + 전환 기준 KPI 명시 | 비용 예측 가시성 강화 |
| 토폴로지 | 파이프라인 전용 구조 | Supabase 직결 + FastAPI **하이브리드 경계** 반영 | 04 Frontend v3.0 동기화 |

<details>
<summary>v2.0 변경 이력</summary>

| 항목 | v1.0 | v2.0 | 이유 |
|---|---|---|---|
| Vercel → Railway 호출 | 동기 호출 | fire-and-forget 패턴 (202 즉시 반환) | Vercel Hobby 10초 타임아웃 우회 |
| 댓글 Rate Limiting | FastAPI slowapi | Supabase RLS 기반 (Frontend 직접 호출) | 댓글 API가 Supabase로 이관됨 |
| CSP | 기본 설정 | GA4/Clarity/AdSense 도메인 추가 + `unsafe-inline` 리스크 명시 | Analytics/수익화 스크립트 대응 |
| 환경 변수 | 모델명 하드코딩 | `OPENAI_MODEL_MAIN/LIGHT` 환경 변수화 | 모델 교체 유연성 |
| 신규 섹션 | — | DB 용량 예측, 스테이징 환경 전략 | 500MB 한계 대비, 품질 보증 |

</details>

---

## 1. 인프라 전체 구조

### 서비스 토폴로지

```
[사용자 브라우저]
      │
      ▼
[Vercel Edge Network]  ← CDN + SSL + 도메인 (0to1log.com)
      │
      ├── Astro Frontend (SSG/SSR Hybrid)
      │     ├── 정적 페이지 → Edge 캐시에서 즉시 응답
      │     └── SSR 페이지 → Vercel Serverless Function (10초 타임아웃)
      │
      ├── /api/trigger-pipeline  ← Vercel Cron (매일 06:00 KST)
      │     └── → Railway FastAPI 호출 (fire-and-forget, 202 반환)
      │
      ├── GA4 + MS Clarity ← 트래킹 스크립트 (Phase 1b~)
      │
      └── 클라이언트 JS → Supabase 직접 통신 (읽기/단순 CRUD)
            ├── 글 조회 (PostgREST)
            ├── 댓글 CRUD (PostgREST + RLS)
            └── 인증 (Supabase Auth)

[Railway]  ← FastAPI — 범용 API 백엔드
      └── FastAPI
            ├── AI 파이프라인 (OpenAI API + Tavily API)
            ├── 시맨틱 검색 API (Phase 3)
            ├── 커뮤니티/포인트 API (Phase 4)
            ├── 구독 권한 검증 API (Phase 4)
            └── 결과 → Supabase 저장

[Supabase]
      ├── PostgreSQL (데이터 저장)
      ├── pgvector (Phase 3 시맨틱 검색)
      ├── Auth (Admin + 소셜 로그인)
      ├── RLS (Row Level Security — 댓글 보안 포함)
      └── 자동 백업 (7일 보관)
```

### 서비스별 역할 & 요금제

| 서비스 | 역할 | 요금제 | 핵심 제한 |
|---|---|---|---|
| **Vercel** | Frontend 호스팅, CDN, Cron 트리거, Serverless Functions | Hobby (무료) | 월 100GB 대역폭, Serverless 10초 타임아웃, Cron 2개 |
| **Railway** | FastAPI — 범용 API 백엔드 (파이프라인/검색/커뮤니티/권한) | Starter ($5/월 크레딧) → Stage B 시 Developer | 8GB RAM, vCPU 8코어 |
| **Supabase** | PostgreSQL, Auth, RLS, 댓글 CRUD, Storage | Free | 500MB DB, 50K MAU, 5GB 대역폭 |
| **OpenAI** | gpt-4o / gpt-4o-mini API | 종량제 | 일일 ~$0.15 (월 ~$4.5) |
| **Tavily** | 뉴스 수집 API | Free (1,000 calls/월) | 일일 ~7쿼리 × 30일 = ~210/월 |
| **GitHub** | 소스 코드, CI/CD (Actions) | Free | Actions 2,000분/월 |
| **GA4** | 트래픽 분석, 유저 흐름 | 무료 | — |
| **MS Clarity** | 히트맵, 세션 리플레이 | 무료 | — |

### 비용 모델 (Stage A / Stage B)

| 단계 | 운영 모드 | Railway 월 비용 | API 비용 (OpenAI+Tavily) | 합계 | 전환 기준 |
|---|---|---|---|---|---|
| **Stage A (Phase 2)** | 범용 API 구조 + 저비용 운영 | Starter 기본료 + 소량 컴퓨팅 | ~$4.5 | ~$5~10 | 초기 트래픽 구간 |
| **Stage B (Phase 3+)** | Always-on 상시 API | 기본료 + 컴퓨팅 변동비 증가 | ~$4.5 | ~$10~20 | KPI 충족 시 상향 |

> **비용 분리 원칙:** OpenAI/Tavily API 비용과 Railway 인프라 비용을 분리 추적한다. 상세 비용 산정은 `03_Backend_AI_Spec.md` 섹션 9 참조. KPI 미달 상태에서는 Stage A를 유지하고, KPI 달성 시 Stage B로 상향한다.

### 리전 전략

모든 서비스를 **us-east-1 (버지니아)** 리전에 통일한다.

| 서비스 | 리전 | 이유 |
|---|---|---|
| Vercel | 자동 (Edge Network) | 글로벌 CDN, 리전 선택 불필요 |
| Vercel Functions | us-east-1 | Supabase/Railway와 같은 리전으로 지연시간 최소화 |
| Railway | us-east-1 | Supabase와 같은 리전 |
| Supabase | us-east-1 | 프로젝트 생성 시 선택 |

> **왜 한국 리전이 아닌가:** Railway와 Supabase Free 티어에서 한국 리전을 지원하지 않는다. 서비스 간 통신(Railway ↔ Supabase)은 같은 리전에서 이루어지므로 지연이 없고, 사용자 요청은 Vercel Edge에서 캐시 히트하므로 체감 지연이 미미하다. SSR 페이지만 us-east-1 왕복이 발생하나, Astro의 가벼운 SSR 특성상 TTFB 200~400ms 수준으로 수용 가능하다.

---

## 2. 배포 파이프라인

### Frontend (Vercel)

```
[GitHub Push: main 브랜치]
      │
      ▼
[Vercel 자동 빌드]
      ├── npm install
      ├── astro build (SSG 페이지 정적 생성)
      ├── Serverless Functions 패키징 (SSR 페이지)
      └── Edge Network 배포 (전 세계 CDN)

[GitHub Push: main 브랜치]
      │
      ▼
[Vercel Production Deployment]
      └── 변경 내용이 즉시 메인 사이트에 반영됨
```

**배포 설정 (vercel.json):** `framework: astro`, `buildCommand: astro build`, `outputDirectory: dist`, Cron: `path: /api/trigger-pipeline`, `schedule: 0 21 * * *`

| 설정 | 값 | 이유 |
|---|---|---|
| Production 브랜치 | `main` | main 머지 시 자동 프로덕션 배포 |
| Preview 브랜치 | 사용 안 함 (main only) | 단일 main 브랜치 워크플로우 |
| 빌드 캐시 | 활성화 (기본) | `node_modules`, `.astro` 캐시로 빌드 시간 단축 |
| Auto-cancel | 활성화 | 같은 브랜치에 연속 push 시 이전 빌드 취소 |

> **Vercel Hobby 타임아웃 주의:** Serverless Function의 최대 실행 시간은 **10초**다. Cron에서 Railway를 호출할 때 fire-and-forget 패턴(202 즉시 반환)을 사용하는 이유가 이것이다. 상세는 `03_Backend_AI_Spec.md` 섹션 1 fire-and-forget ADR 참조.

### Backend (Railway)

```
[GitHub Push: main 브랜치]
      │
      ▼
[Railway 자동 빌드]
      ├── Nixpacks 자동 감지 (Python + requirements.txt)
      ├── pip install
      ├── uvicorn main:app 실행
      └── 헬스체크 통과 후 트래픽 전환
```

**Railway 설정:**

| 설정 | 값 |
|---|---|
| 빌드 감지 | Nixpacks (자동) |
| 시작 명령어 | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| 헬스체크 | `GET /health` → 200 OK |
| 자동 배포 | main 브랜치 push 시 |
| 재시작 정책 | 크래시 시 자동 재시작 (기본) |

헬스체크: `GET /health` → `{"status": "ok", "timestamp": "..."}` (main.py)

> **Railway 운영 전략 (ADR):** Railway를 범용 API 백엔드로 운영한다. Stage A(Phase 2)에서는 파이프라인 및 Admin API 중심의 저비용 운영, Stage B(Phase 3+)에서는 검색/커뮤니티 트래픽 KPI 충족 시 Always-on으로 상향한다. 상세는 `03_Backend_AI_Spec.md` 섹션 1 범용 API 서버 운영 ADR 참조.

### 배포 순서 원칙

Frontend와 Backend가 동시에 변경되는 경우: **Backend(Railway) 먼저 배포 → 헬스체크 통과 확인 → Frontend(Vercel) 배포**. 새 API가 준비된 뒤 Frontend가 호출해야 에러를 방지할 수 있다.

> **[성공 기준]**
> 1. Vercel: main push → 프로덕션 자동 배포 성공, Preview Deployment URL 생성
> 2. Railway: main push → Nixpacks 빌드 성공, `GET /health` → 200 OK
> 3. CI: Frontend PR → lint + build + astro check 통과 / Backend PR → pytest + ruff 통과

---

## 3. CI/CD (GitHub Actions)

### 워크플로우 구조

```
.github/workflows/
├── frontend-ci.yml    (PR 시 린트 + 빌드 체크)
├── backend-ci.yml     (PR 시 린트 + 테스트)
└── lighthouse.yml     (main 머지 후 성능 체크)
```

### CI 워크플로우 요약

| 워크플로우 | 파일 | 트리거 | 스텝 |
|---|---|---|---|
| **Frontend CI** | `frontend-ci.yml` | PR (`src/**`, `public/**`, `astro.config.*`, `package.json`) | `npm ci` → `npm run lint` → `npm run build` → `npx astro check` |
| **Backend CI** | `backend-ci.yml` | PR (`backend/**`, `requirements.txt`) | `pip install` → `pytest tests/ -v --tb=short` → `ruff check backend/` |
| **Lighthouse** | `lighthouse.yml` | main push | `treosh/lighthouse-ci-action@v12` → `/`, `/log` 체크 |

**Lighthouse 예산:** LCP < 1,500ms, 스크립트 리소스 < 10개 (`lighthouse-budget.json`)

> **Solo 프로젝트에 CI가 필요한 이유:** CI가 자동으로 체크하면 기본 품질이 보장되고, 포트폴리오로 보여줄 때 CI/CD 파이프라인 자체가 역량 증명이 된다.

---

## 4. 환경 변수 관리

### 서비스별 환경 변수

#### Vercel (Frontend)

```env
# Public (클라이언트 번들에 포함 — 노출 OK)
PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
PUBLIC_SUPABASE_ANON_KEY=eyJ...
PUBLIC_SITE_URL=https://0to1log.com

# Private (Serverless Functions에서만 접근)
CRON_SECRET=your-random-secret-here
FASTAPI_URL=https://your-app.railway.app
REVALIDATE_SECRET=your-random-secret-here
```

#### Railway (Backend)

```env
# Supabase (Service Key — 서버 전용, RLS 우회)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# AI APIs
OPENAI_API_KEY=sk-...
OPENAI_MODEL_MAIN=gpt-4o          # 메인 모델 (교체 용이)
OPENAI_MODEL_LIGHT=gpt-4o-mini    # 경량 모델
TAVILY_API_KEY=tvly-...

# Auth
ADMIN_EMAIL=admin@0to1log.com

# Cron
CRON_SECRET=your-random-secret-here

# App
FASTAPI_URL=https://your-app.railway.app
REVALIDATE_SECRET=your-random-secret-here
```

> **v2.0 change note:** `OPENAI_MODEL_MAIN` and `OPENAI_MODEL_LIGHT` are split as env vars. `REVALIDATE_SECRET` remains required for `/api/revalidate`.

### 환경 분리 원칙

| 변수 유형 | 설명 | 저장 위치 | 코드 접근 |
|---|---|---|---|
| **PUBLIC_** | 클라이언트 노출 OK (anon key, site URL) | Vercel 환경 변수 | `import.meta.env.PUBLIC_*` |
| **Private (Frontend)** | Serverless에서만 사용 (cron secret) | Vercel 환경 변수 | `process.env.*` (서버 사이드) |
| **Private (Backend)** | AI API 키, DB service key, 모델명 | Railway 환경 변수 | `os.environ["*"]` |

### 보안 규칙

- **`.env` 파일은 절대 Git에 커밋하지 않는다.** `.gitignore`에 `.env*` 패턴 포함 필수.
- **`.env.example` 파일은 커밋한다.** 키 이름만 나열하고 값은 비워둔다.
- **Supabase Service Key는 백엔드(Railway)에서만 사용한다.** Frontend에는 Anon Key만 노출.
- **CRON_SECRET은 Vercel과 Railway 양쪽에 동일한 값을 설정한다.** Vercel Cron → Railway 호출 시 인증용.
- **시크릿 값은 최소 32자 랜덤 문자열을 사용한다.** `openssl rand -hex 32`로 생성.

```
# .env.example
PUBLIC_SUPABASE_URL=
PUBLIC_SUPABASE_ANON_KEY=
PUBLIC_SITE_URL=
SUPABASE_SERVICE_KEY=
OPENAI_API_KEY=
OPENAI_MODEL_MAIN=gpt-4o
OPENAI_MODEL_LIGHT=gpt-4o-mini
TAVILY_API_KEY=
ADMIN_EMAIL=
CRON_SECRET=
FASTAPI_URL=
REVALIDATE_SECRET=
```

---

## 5. 도메인 & SSL

### 도메인 설정

| 항목 | 값 |
|---|---|
| **도메인** | 0to1log.com |
| **등록 기관** | Cloudflare Registrar (이미 구매 완료) |
| **네임서버** | Vercel (도메인 연결 시 설정) |
| **SSL** | Vercel 자동 발급 (Let's Encrypt) |
| **www 리다이렉트** | www.0to1log.com → 0to1log.com (301 Redirect) |

### DNS 레코드

```
Type    Name    Value                   TTL
A       @       76.76.21.21             300    (Vercel)
CNAME   www     cname.vercel-dns.com    300    (Vercel)
```

### 서브도메인 계획

현재는 서브도메인 없이 단일 도메인 운영. 향후 필요시:

| 서브도메인 | 용도 | 시점 |
|---|---|---|
| `api.0to1log.com` | FastAPI 엔드포인트 (현재는 Railway 기본 URL) | 필요 시 |
| `admin.0to1log.com` | Admin 분리 (현재는 /admin 경로) | 필요 없음 (예정 없음) |

---

## 6. 보안

### 6-1. 인증 보안

인증 시스템 상세는 `03_Backend_AI_Spec.md` 섹션 2를 참조. 여기서는 인프라 레벨 보안만 다룬다.

**Supabase Auth 설정:**

| 설정 | 값 | 이유 |
|---|---|---|
| JWT 만료 시간 | 3600초 (1시간) | Supabase 기본값, 적절한 세션 길이 |
| Refresh Token 순환 | 활성화 | 탈취된 refresh token 재사용 방지 |
| 비밀번호 최소 길이 | 8자 (Admin 계정) | Supabase 기본값 |
| 소셜 로그인 | Google, GitHub | 댓글 사용자용 |
| Redirect URL 화이트리스트 | `https://0to1log.com/**`, `http://localhost:4321/**` | 개발/프로덕션 환경만 허용 |

### 6-2. API 보안

**Cron 엔드포인트:**
- Bearer Token 인증 (CRON_SECRET) — `03_Backend_AI_Spec.md` 섹션 7-2 참조
- Vercel Cron과 Railway 양쪽에 동일한 시크릿 설정
- fire-and-forget 패턴으로 202 즉시 반환 → 파이프라인은 백그라운드 실행

**Revalidate ?? ?? ??**
> **Contract:** `REVALIDATE_SECRET` is mandatory for `/api/revalidate`, and calls are server-side only.
- 2? ?? ??: ???? ?? ?? ??, ?? ??? ????? secret ??
- ?? ??? `pipeline_logs`/?? ??? ???? ?? ?? ? ?? ??

**FastAPI CORS:** `CORSMiddleware` — `allow_origins: ["https://0to1log.com", "http://localhost:4321"]`, `allow_methods: ["GET","POST","PATCH"]`, `allow_headers: ["Authorization","Content-Type"]`, `allow_credentials: True`

**Rate Limiting (FastAPI — slowapi):**

| 엔드포인트 | 제한 | 이유 |
|---|---|---|
| `/api/admin/ai/draft` | 10/분 | Admin AI 기능 |
| `/api/cron/news-pipeline` | 1/시간 | 파이프라인 추가 방어 |
| `/api/search/semantic` (Phase 3) | 30/분 | 사용자 체감 저해 없이 남용 방지 |
| `/api/community/points/earn` (Phase 4) | 10/분 | 치트 방지 |

> **Rate Limiting 원칙:** 공개 API(검색)는 느슨하게, 상태 변경 API(포인트/퀴즈)는 엄격하게 설정.

### 6-3. 데이터베이스 보안

**RLS (Row Level Security):**
- 정책 상세는 `03_Backend_AI_Spec.md` 섹션 2 참조
- 모든 테이블에 RLS 활성화 필수 — Supabase Dashboard에서 수동 확인
- **RLS 정책에 버그가 있으면 DB가 직접 노출된다.** 배포 전 반드시 `03_Backend_AI_Spec.md` 섹션 11-2 RLS 테스트 시나리오를 실행할 것.

**추가 보안 항목:**

| 항목 | 설정 |
|---|---|
| DB 비밀번호 | Supabase 자동 생성 (노출 불필요) |
| 외부 DB 접속 | 비활성화 (Supabase Dashboard에서 Direct Connection 사용 안 함) |
| pg_graphql | 사용하지 않으면 비활성화 |
| Supabase Storage | 미사용 시 public 버킷 생성하지 않음 |

### 6-4. 댓글 스팸 방어

프론트엔드 레벨 throttle은 `04_Frontend_Spec.md`에 정의. 여기서는 서버 사이드 방어를 다룬다.

**Supabase RLS 기반 rate limiting:**

```sql
-- 댓글 작성 시 30초 간격 제한 (RLS 정책)
CREATE POLICY "comments_rate_limit" ON comments
FOR INSERT WITH CHECK (
  auth.uid() IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM comments
    WHERE user_id = auth.uid()
    AND created_at > NOW() - INTERVAL '30 seconds'
  )
);
```

**방어 계층:**

| 방어 | 구현 | 시점 |
|---|---|---|
| 프론트엔드 throttle | 30초 작성 간격 + 3회 실패 60초 쿨다운 | Phase 1b (Frontend) |
| RLS rate limiting | 위 SQL 정책 | Phase 1a (DB) |
| DB CHECK 제약 | `char_length(content) <= 2000` | Phase 1a (DB) |
| 콘텐츠 필터링 | 스팸 키워드 기본 필터 | Phase 3 (필요 시) |

### 6-5. 보안 헤더

Vercel에서 자동 적용되는 항목 외에 추가 설정 (vercel.json `headers` 섹션, `source: /(.*)`):

| 헤더 | 값 |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' googletagmanager.com clarity.ms pagead2.googlesyndication.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' *.supabase.co *.railway.app google-analytics.com clarity.ms` |

> **`unsafe-inline` 리스크 주의:** `script-src 'unsafe-inline'`은 XSS 공격에 취약하다. Astro의 인라인 스크립트(테마 초기화, Clarity 스크립트 등)를 위해 현재 필요하지만, Phase 1부터 인라인 스크립트를 최소화하는 방향으로 개발하고, **Phase 3에서 nonce 기반 CSP로 전환**하여 `unsafe-inline`을 제거한다.

> **CSP 도메인 추가 목록 (Phase별):**
> - Phase 1b: `googletagmanager.com`, `google-analytics.com`, `clarity.ms` (GA4 + Clarity)
> - Phase 2 후반: `pagead2.googlesyndication.com` (AdSense 신청 시)
> - Phase 4: Polar 결제 도메인 (구독 모델 결정 시)

> **[성공 기준]**
> 1. CORS: `0to1log.com`에서 FastAPI 호출 성공, 다른 origin 거부
> 2. Rate Limiting: `/api/cron/news-pipeline` 1시간 내 2회 호출 시 429 반환
> 3. RLS: anon 유저로 draft 글 조회 시 0 rows, 타인 댓글 삭제 시 거부
> 4. 보안 헤더: `curl -I https://0to1log.com` → CSP, X-Frame-Options 포함

---

## 7. 모니터링 & 로깅

### 모니터링 전략 원칙

Solo 프로젝트에 복잡한 모니터링 스택(Datadog, Grafana 등)은 과잉이다. 각 서비스의 **내장 대시보드**를 최대한 활용하고, 커스텀으로 만드는 것은 AI 파이프라인 로그 조회 + 운영 지표(Phase 3 AI Ops Dashboard)뿐이다.

### 서비스별 모니터링

| 대상 | 도구 | 확인 항목 | 비용 |
|---|---|---|---|
| **Frontend 성능** | Vercel Analytics | LCP, CLS, INP (Core Web Vitals) | 무료 (Hobby 포함) |
| **Frontend 에러** | Vercel 빌드 로그 | 빌드 실패, SSR 에러 | 무료 |
| **Backend 상태** | Railway 대시보드 | CPU/메모리 사용량, 응답 시간, 크래시 로그 | 무료 |
| **AI 파이프라인** | Supabase `pipeline_logs` 테이블 | 파이프라인 성공/실패, 토큰/비용 추적 | 무료 (DB 내) |
| **DB 성능** | Supabase Dashboard | 쿼리 성능, DB 크기, 연결 수 | 무료 |
| **API 비용** | OpenAI Dashboard + Tavily Dashboard | 일/월 사용량, 잔여 크레딧 | 무료 |
| **도메인/SSL** | Vercel (자동) | SSL 인증서 갱신, 도메인 상태 | 무료 |
| **사용자 행동** | GA4 + MS Clarity | 트래픽 소스, 유저 흐름, 히트맵, 세션 리플레이 | 무료 |

### 운영 지표 (Stage A→B 전환 판단용)

Phase 3에서 Railway Always-on 전환 여부를 판단하기 위한 운영 지표를 정의한다.

| 지표 | 목표 | 측정 방법 | 판단 기준 |
|---|---|---|---|
| **p95 응답시간** | < 500ms (검색/커뮤니티 API) | Railway 대시보드 + FastAPI 미들웨어 로깅 | Stage A에서 목표 미달 시 Stage B 검토 |
| **Error rate** | < 1% (5xx 기준) | Railway 대시보드 + pipeline_logs | 1% 초과 지속 시 원인 분석 |
| **Uptime** | > 99.5% | Railway 대시보드 | Stage B 전환 후 모니터링 |
| **Rate limit 히트율** | < 5% | FastAPI slowapi 로그 | 정상 사용자 차단 시 한도 상향 |
| **일일 API 요청 수** | 추적 | FastAPI 미들웨어 로깅 | Stage B 전환 KPI (커뮤니티/검색 사용량) |

> **Stage A→B 전환 KPI:** 검색 일 평균 요청 수 + 커뮤니티 액션 수가 임계치를 넘으면 Always-on 전환을 검토한다. 구체적 임계치는 Phase 2 운영 데이터 축적 후 결정. `06_Business_Strategy.md` KPI 프레임워크와 연동.

### 파이프라인 모니터링

`03_Backend_AI_Spec.md`에 정의된 `pipeline_logs` 테이블이 AI 파이프라인의 중앙 로깅 시스템이다.

최근 파이프라인 상태 확인: `SELECT pipeline_type, status, created_at, error_message, tokens_used, cost_usd FROM pipeline_logs WHERE created_at > NOW() - INTERVAL '24 hours' ORDER BY created_at DESC;`

**파이프라인 실패 시 알림 흐름:** 실패 → `pipeline_logs` status='failed' 기록 → `admin_notifications` 알림 저장 → Admin 대시보드 확인 → (Phase 3) 이메일 자동 알림

### 알림

| 이벤트 | 알림 방식 | 시점 |
|---|---|---|
| 파이프라인 실패 | `admin_notifications` 테이블 + Admin 대시보드 | Phase 2 |
| 파이프라인 실패 (이메일) | Supabase Webhooks 또는 Resend API | Phase 3 |
| 비용 임계치 초과 ($10/월) | admin_notifications + OpenAI Usage Alert | Phase 2 |
| Vercel 빌드 실패 | GitHub Commit Status (자동) + Vercel 이메일 | Phase 1a |
| Railway 크래시 | Railway 이메일 알림 (기본 설정) | Phase 2 |

> **왜 Slack/Discord 알림이 아닌가:** Solo 프로젝트에서 별도 알림 채널을 관리하는 건 오버헤드다. Vercel, Railway, OpenAI 각각의 이메일 알림 + admin_notifications로 충분하다. 트래픽이 늘어나면 그때 Slack webhook을 추가할 수 있다.

---

## 8. 백업 & 복구

### 데이터베이스 백업

| 항목 | 설정 |
|---|---|
| **자동 백업** | Supabase Free 티어: 일일 자동 백업 (7일 보관) |
| **Point-in-Time Recovery** | Pro 플랜 이상에서 사용 가능 (현재 불가) |
| **수동 백업** | Supabase Dashboard > Database > Backups에서 수동 다운로드 |

**수동 백업 주기:**

| 시점 | 이유 |
|---|---|
| Phase 1 완료 시 | 스키마 + 초기 데이터 스냅샷 |
| Phase 2 파이프라인 첫 실행 성공 후 | AI 생성 데이터 첫 백업 |
| 스키마 변경 전 | 마이그레이션 실패 시 롤백용 |
| 월 1회 | 정기 백업 습관 |

수동 백업: `pg_dump --format=custom --file=backup_$(date +%Y%m%d).dump`

### 소스 코드 백업

- **GitHub이 곧 백업이다.** 모든 코드가 Git에 있으므로 별도 코드 백업은 불필요.
- **주의:** 환경 변수와 시크릿은 Git에 없으므로, Vercel/Railway 설정을 별도로 기록해둬야 한다.
- 환경 변수 목록은 `.env.example`에 키 이름만 보관, 실제 값은 1Password/Bitwarden 등 비밀번호 관리자에 저장 권장.

### 장애 복구 시나리오

| 장애 | 복구 방법 | 예상 복구 시간 |
|---|---|---|
| **Vercel 빌드 실패** | 이전 커밋으로 Git revert → 자동 재배포 | 5분 |
| **Railway 크래시** | 자동 재시작. 지속되면 이전 배포로 rollback (Railway UI) | 1~5분 |
| **Supabase 장애** | Supabase 인프라 복구 대기 (통제 불가). Status 페이지 확인 | 10분~수 시간 |
| **AI 파이프라인 실패** | admin_notifications 확인 → 원인 파악 → 수동 재실행 | 5~10분 |
| **도메인 만료** | Cloudflare에서 갱신. Vercel 연결은 자동 유지 | 24시간 |
| **DB 데이터 손실** | Supabase 자동 백업에서 복원 (7일 이내) | 30분 |
| **환경 변수 유실** | `.env.example` + 비밀번호 관리자에서 복원 | 10분 |

---

## 9. 개발 환경

### 로컬 개발 세팅

1. `git clone` → `npm install` → `cp .env.example .env` → `npm run dev` (http://localhost:4321)
2. Backend (별도 터미널): `cd backend` → `python -m venv .venv` → `pip install -r requirements.txt` → `cp .env.example .env` → `uvicorn main:app --reload --port 8000`

### 개발 도구

| 도구 | 용도 |
|---|---|
| **VS Code** | 에디터 |
| **Astro VS Code Extension** | Astro 구문 강조, 타입 체크 |
| **Tailwind CSS IntelliSense** | 클래스 자동 완성 |
| **ESLint + Prettier** | 코드 포맷팅 |
| **Ruff** | Python 린트 (빠른 대안) |
| **Supabase CLI** | 로컬 DB 스키마 관리, 마이그레이션 |

### Git 브랜치 전략

Solo 프로젝트이므로 단순한 전략을 사용한다:

`main` 하나만 사용한다. 별도 `develop`, `feature/*`, `fix/*` 브랜치는 기본 전략에 포함하지 않는다.

- 모든 변경은 `main`에서 작은 단위로 커밋하고, 로컬 검증 후 push 한다.
- Preview Deployment는 기본 워크플로우가 아니라 필요 시 선택적으로만 사용한다.
- 커밋 메시지: `feat:`, `fix:`, `docs:`, `chore:` prefix (Conventional Commits)

### 스테이징 환경 전략

> **결정:** 별도 스테이징 서버를 두지 않고, Vercel Preview Deployment + Supabase 로컬 환경으로 대체한다.
>
> - **Frontend:** Vercel Preview Deployment (PR별 자동 생성) = 스테이징
> - **Backend:** 로컬 FastAPI (`--reload`)
> - **DB:** `supabase start` → `supabase db reset` → `supabase db push` (로컬 PostgreSQL)
> - **프로덕션 데이터 테스트:** `pg_dump` → `pg_restore` (로컬 54322 포트)

---

## 10. Supabase 스키마 마이그레이션

### 마이그레이션 전략

Supabase CLI로 스키마 변경 버전 관리: `supabase migration new <name>` → SQL 편집 → `supabase db push` (로컬) → `supabase db push --linked` (프로덕션)

### 마이그레이션 파일 구조

```
supabase/
├── config.toml                 # Supabase 프로젝트 설정
├── migrations/
│   ├── 20260304_001_initial_schema.sql       # Phase 1a: posts, comments, likes
│   ├── 20260304_002_rls_policies.sql         # Phase 1a: RLS 정책
│   ├── 20260304_003_pipeline_tables.sql      # Phase 2: pipeline_logs, admin_notifications, news_candidates
│   └── 20260xxx_004_embeddings.sql           # Phase 3: embeddings, pgvector
└── seed.sql                    # 개발용 더미 데이터
```

### 마이그레이션 안전 규칙

- **프로덕션 적용 전 반드시 로컬에서 테스트한다.** (`supabase start` → `supabase db reset`)
- **파괴적 변경(DROP, 컬럼 삭제)은 마이그레이션 전에 수동 백업을 먼저 한다.**
- **마이그레이션 파일은 Git에 커밋한다.** 스키마 변경 이력이 곧 문서다.
- **롤백 SQL은 같은 마이그레이션 파일에 주석으로 포함한다.** (예: `ALTER TABLE ... ADD COLUMN` 아래에 `-- Rollback: ALTER TABLE ... DROP COLUMN`)

---

## 11. DB 용량 예측 & 500MB 대응

### 테이블별 용량 추정

| 테이블 | 행당 크기 (추정) | 월간 증가량 | 6개월 후 | 12개월 후 |
|---|---|---|---|---|
| **posts** | ~10KB (JSONB 포함) | ~60행 (일 2건) | ~3.6MB | ~7.2MB |
| **news_candidates** | ~0.5KB | ~600행 (일 20건) | ~1.8MB | ~3.6MB |
| **pipeline_logs** | ~0.3KB | ~300행 (일 10건) | ~0.5MB | ~1.1MB |
| **comments** | ~0.3KB | 트래픽 의존 | ~0.5MB | ~2MB |
| **embeddings** (Phase 3) | ~6KB (1536차원 벡터) | 포스트당 5~10 청크 | ~18MB | ~36MB |
| **인덱스 + 오버헤드** | — | — | ~10MB | ~25MB |
| **합계** | — | — | **~35MB** | **~75MB** |

> **핵심 결론:** 12개월 후에도 ~75MB로 500MB 한계의 15% 수준. **임베딩이 가장 큰 비중을 차지한다.** Phase 3에서 pgvector를 도입하면 증가 속도가 빨라지지만, 12개월 내 500MB 도달 가능성은 낮다.

### 500MB 도달 시점 예측

임베딩 없이 → 5년+ (사실상 도달 안 함) / 임베딩 포함 → 약 3~4년 (Phase 3 이후)

### 대응 계획

| 시점 | 행동 |
|---|---|
| DB 크기 300MB 도달 | 오래된 pipeline_logs 정리 (90일 이상 된 로그 삭제) |
| DB 크기 400MB 도달 | news_candidates 중 status='rejected' 데이터 정리 |
| DB 크기 450MB 도달 | Supabase Pro ($25/월) 업그레이드 검토 |

정리 쿼리: `pipeline_logs` — status='success' AND 90일 초과 삭제 / `news_candidates` — status='rejected' AND 60일 초과 삭제

---

## 12. Phase별 인프라 구현 범위

> **Project Overview v2.1 동기화:** Phase 구조와 타이밍을 01_Project_Overview.md v2.1과 일치시킨다.

### Phase 1a — 기본 인프라

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| GitHub 레포 생성 + 기본 브랜치 설정 | main 브랜치에서 직접 작업 가능 | Amy (수동) |
| Vercel 프로젝트 연결 + 자동 배포 확인 | main push → 프로덕션 배포 성공 | Amy (수동) |
| 도메인(0to1log.com) Vercel 연결 | DNS 설정, SSL 활성화 | Amy (수동) |
| Supabase 프로젝트 생성 (us-east-1) | Dashboard 접속 가능 | Amy (수동) |
| 초기 스키마 마이그레이션 (posts, comments, likes) | 테이블 생성 + RLS 활성화 | Claude Code |
| RLS 정책 적용 + 테스트 | `03_Backend` 섹션 11-2 시나리오 통과 | Claude Code + Amy 검증 |
| 환경 변수 설정 (Vercel + .env.example) | Frontend에서 Supabase 연동 확인 | Amy (수동) |
| Frontend CI 워크플로우 | PR 시 린트 + 빌드 체크 자동 실행 | Claude Code |
| SEO 기반 설계 (JSON-LD, 사이트맵, 메타 태그) | SEO audit 통과 | Claude Code |
| 보안 헤더 (vercel.json) | CSP, X-Frame-Options 등 적용 | Claude Code |
| `.gitignore` + `.env.example` | 시크릿 노출 방지 확인 | Claude Code |

### Phase 1b — 데이터 연결

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| Supabase Auth 설정 (Admin 이메일 + 소셜 로그인) | 로그인/로그아웃 정상 동작 | Amy (Supabase Dashboard) |
| 댓글 RLS rate limiting | 30초 간격 제한 SQL 정책 적용 | Claude Code |
| GA4 설치 | 트래킹 이벤트 수신 확인 | Amy (GA4 Dashboard) |
| MS Clarity 설치 | 세션 리플레이 작동 확인 | Amy (Clarity Dashboard) |
| Vercel Analytics 활성화 | Core Web Vitals 대시보드 확인 | Amy (Vercel Dashboard) |
| Lighthouse CI 워크플로우 | main 머지 시 자동 성능 체크 | Claude Code |
| 수동 DB 백업 1회 | Phase 1 스냅샷 보관 | Amy (수동) |

### Phase 2 — AI 인프라 (Stage A 운영)

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| Railway 프로젝트 생성 + FastAPI 배포 | `/health` 엔드포인트 200 OK | Amy (수동) + Claude Code |
| FastAPI 범용 API 라우팅 구조 설계 | 검색/커뮤니티/권한 경로 스텁 준비 | Claude Code |
| Backend CI 워크플로우 | PR 시 pytest + ruff 자동 실행 | Claude Code |
| Railway 환경 변수 설정 | 모든 API 키 + 모델명 환경 변수 | Amy (Railway Dashboard) |
| Vercel Cron 설정 (매일 06:00 KST) | fire-and-forget 트리거 → Railway 202 반환 | Claude Code + Amy 검증 |
| FastAPI CORS 설정 | 0to1log.com에서만 API 호출 허용 | Claude Code |
| FastAPI Rate Limiting (slowapi) | AI 엔드포인트 rate limit 동작 | Claude Code |
| `pipeline_logs` 테이블 생성 | 파이프라인 상태 기록 확인 | Claude Code |
| 파이프라인 전체 1회 성공 실행 | Research(published) + Business(draft) 생성 | Amy + Claude Code |
| OpenAI Usage Alert 설정 ($10/월) | 이메일 알림 설정 | Amy (OpenAI Dashboard) |
| 마이그레이션 파일 커밋 | pipeline_logs, news_candidates Git 반영 | Claude Code |
| AdSense 신청 (콘텐츠 30개+ 후) | 승인 대기 | Amy (수동) |

### Phase 3 — 고도화 (Stage A→B 전환 검토)

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| pgvector 확장 활성화 + embeddings 테이블 | 시맨틱 검색 쿼리 동작 | Claude Code |
| AI Ops Dashboard API → Frontend 연동 | 파이프라인 상태/비용 + 운영 지표(p95, error rate, uptime) 시각화 | Claude Code |
| CSP nonce 기반 전환 | `unsafe-inline` 제거 | Claude Code |
| 파이프라인 실패 이메일 알림 | Supabase Webhooks 또는 Resend API | Claude Code |
| AARRR 지표 대시보드 | GA4 데이터 기반 시각화 | Claude Code |
| **Railway 운영모드 상향 결정** | 운영 지표(섹션 7) KPI 기반 Stage A→B 전환 여부 판단 | Amy (판단) |

### Phase 4 — 수익화 & 커뮤니티

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| 프리미엄 구독 모델 검토 | 유료/무료 콘텐츠 분리 설계 | Amy (기획) |
| Polar 결제 연동 (구독 결정 시) | 결제 플로우 테스트 | Claude Code |
| PWA manifest + Service Worker | 모바일 앱 설치 가능 | Claude Code |
| Supabase Pro 업그레이드 (필요 시) | Point-in-Time Recovery 활성화 | Amy (수동) |
| CSP에 Polar 도메인 추가 | 결제 페이지 정상 로드 | Claude Code |

### Phase 5 — 앱 확장

| 항목 | 완료 기준 | 실행 주체 |
|---|---|---|
| PWA 사용 데이터 분석 | "앱 설치율 5%+, 주간 재방문율 30%+" | Amy (분석) |
| Expo 네이티브 앱 개발 | iOS/Android 앱 스토어 제출 | Amy + Claude Code |

---

## 13. 무료 티어 제한 & 대응 계획

### 서비스별 무료 티어 한계 시나리오

| 서비스 | 무료 한계 | 예상 도달 시점 | 대응 |
|---|---|---|---|
| **Vercel** 대역폭 100GB/월 | 월간 방문자 수만 명 이상 | Phase 3~4 | Pro 플랜 ($20/월) 또는 이미지 CDN 분리 |
| **Vercel** Cron 2개 | 크론 잡 3개 이상 필요 시 | Phase 3 | Railway에서 자체 스케줄러 (APScheduler) |
| **Vercel** Serverless 10초 | AI 파이프라인 직접 실행 | — | fire-and-forget 패턴으로 이미 우회 |
| **Supabase** DB 500MB | 섹션 11 예측 참조 (~3~4년) | Phase 3~4 | 로그 정리 → Pro 플랜 ($25/월) |
| **Supabase** MAU 50K | 월간 활성 사용자 5만 명 | Phase 4 | Pro 플랜 (기쁜 비명) |
| **Railway** $5/월 크레딧 | Stage B(Always-on) 전환 시 크레딧 초과 | Phase 3 (KPI 충족 시) | Developer 플랜 ($5/월 추가) 또는 Stage A 유지 |
| **Tavily** 1,000 calls/월 | 일 33쿼리 이상 | Phase 3 | Starter 플랜 ($40/월) 또는 쿼리 최적화 |
| **GitHub Actions** 2,000분/월 | CI 빈번 실행 | 가능성 낮음 | 캐싱 최적화, 불필요한 실행 조건 제한 |

> **현실적 판단:** Phase 2까지는 모든 서비스가 무료/최소 요금 범위 내에서 운영 가능하다 (Stage A). Phase 3에서 Railway Always-on(Stage B) 전환 시 Starter $5 크레딧을 초과할 수 있으나, KPI 미달이면 Stage A를 유지하여 비용을 최소화한다. Supabase Pro는 pgvector 임베딩 용량에 따라 결정하되, 섹션 11 예측에 따르면 12개월 후에도 ~75MB이므로 급하지 않다.

---

## 부록: 체크리스트

### Phase 1a 배포 전 체크리스트

```
[Amy 수동]
□ GitHub 레포 생성 + .gitignore 확인 (.env* 포함)
□ Vercel 프로젝트 연결 + main 브랜치 자동 배포
□ 도메인(0to1log.com) DNS 설정 + SSL 확인
□ Supabase 프로젝트 생성 (us-east-1 리전)
□ Vercel 환경 변수 설정 (PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY)
□ GitHub 기본 브랜치(main) 확인

[Claude Code 자동화 가능]
□ .env.example 작성 + 커밋
□ 초기 스키마 마이그레이션 적용
□ RLS 정책 적용
□ Frontend CI 워크플로우 동작 확인
□ 보안 헤더 적용 확인 (curl -I https://0to1log.com)
□ SEO 기반 (JSON-LD, 사이트맵) 구현

[검증]
□ 0to1log.com 접속 + HTTPS 정상 확인
□ RLS 테스트 시나리오 4개 통과 (03_Backend 섹션 11-2)
□ Supabase에서 글 조회 정상 작동
```

### Phase 2 AI 파이프라인 배포 전 체크리스트

```
[Amy 수동]
□ Railway 프로젝트 생성
□ Railway 환경 변수 설정 (모든 API 키 + OPENAI_MODEL_MAIN/LIGHT)
□ OpenAI Usage Alert 설정 ($10/월)

[Claude Code 자동화 가능]
□ FastAPI 배포 + /health 엔드포인트 200 OK 확인
□ CORS 설정 (0to1log.com만 허용)
□ Rate Limiting 동작 확인
□ fire-and-forget Cron 엔드포인트 + CRON_SECRET 인증 테스트
□ Vercel Cron 설정 + 수동 1회 트리거 테스트
□ pipeline_logs 테이블 로그 기록 확인
□ Backend CI 워크플로우 동작 확인
□ 마이그레이션 파일 Git 커밋

[검증]
□ 파이프라인 전체 1회 성공 실행
□ Research → published, Business → draft 정상 생성
□ admin_notifications에 테스트 알림 정상 기록
□ DB 백업 1회 실행
```


---


## 14. Policy Addendum (v2.3)

### 14-1. Revalidate Security and Call Boundary
- `POST /api/revalidate` must validate `REVALIDATE_SECRET` and return `401` on mismatch
- Browser direct calls are disallowed by operations policy
- Secret injection is allowed only on server-side paths (FastAPI or Vercel server route)
- Log failures and raise warning alerts on repeated authentication failures

### 14-2. Minimal Manual Runbook (Cron fails twice in a row)
1. Check `pipeline_logs` for root cause of last two failures
2. Call `POST /api/admin/pipeline/rerun`
3. Payload:
   - `target_date` (`YYYY-MM-DD`)
   - `mode`: `safe` (default)
   - `reason`: operator note
   - `trigger_revalidate`: `true`
4. Response handling:
   - `202`: queued
   - `200`: safe-skip (already successful run exists)
   - `409`: run already in progress
5. If safe repeatedly skips/fails, retry once with `mode=force`
6. Success criteria: final `pipeline_logs` status is `success` and publish/revalidate outcomes are confirmed

> Auto failover remains out of scope in this stage; only minimal manual runbook is required.
