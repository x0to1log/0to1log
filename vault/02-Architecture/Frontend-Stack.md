---
title: Frontend Stack
tags:
  - architecture
  - frontend
  - stack
source: [docs/01_Project_Overview.md, docs/04_Frontend_Spec.md]
---

# Frontend Stack

Astro v5 + Tailwind CSS v4 + MDX 기반 콘텐츠 중심 정적 사이트.

## 기술 스택

| 레이어 | 기술 | 역할 |
|---|---|---|
| **프레임워크** | Astro v5 + MDX | 콘텐츠 중심 정적 사이트, 인터랙티브 컴포넌트 |
| **스타일** | Tailwind CSS v4 | 유틸리티 기반 스타일링 |
| **애니메이션** | Motion One + View Transitions API | 페이지 전환, 마이크로 인터랙션 |
| **호스팅** | Vercel | 배포, 도메인 관리, Cron 트리거 |
| **SEO** | Astro SSG + JSON-LD + 사이트맵 | 검색 엔진 최적화, 구조화 데이터 |
| **Analytics** | GA4 + MS Clarity | 트래픽 분석, 히트맵, 세션 리플레이 |

## 사이트맵

```
0to1log.com
├── /                → EN Home (x-default, 기본 진입)
├── /en/news/        → EN AI 뉴스 리스트
├── /en/news/[slug]  → EN AI 뉴스 상세
├── /en/blog/        → EN IT 블로그 리스트
├── /en/blog/[slug]  → EN IT 블로그 상세
├── /en/handbook/    → EN AI 용어집
├── /ko/news/        → KO AI 뉴스 리스트
├── /ko/news/[slug]  → KO AI 뉴스 상세
├── /ko/blog/        → KO IT 블로그 리스트
├── /ko/blog/[slug]  → KO IT 블로그 상세
├── /ko/handbook/    → KO AI 용어집
├── /library/        → 나의 서재
├── /portfolio/      → 프로젝트 쇼케이스
├── /admin/          → 관리자 대시보드
└── 언어 스위처       → ko/en 전환, 페르소나 설정, 테마 전환
```

> [!note] i18n 정책
> EN canonical + `x-default=/en/` 운영 원칙. 상세 → [[Global-Local-Intelligence]]

## Islands Architecture

Astro Islands 전략: 정적 HTML 셸 위에 인터랙티브 React/Svelte 아일랜드만 선택적으로 하이드레이션한다.

### 하이드레이션 디렉티브

| 컴포넌트 | 디렉티브 | 이유 |
|---|---|---|
| 글 본문, 레이아웃, 네비게이션 | 없음 (정적 HTML) | JS 불필요, 최대 성능 |
| Persona Switcher | `client:visible` | 뷰포트 진입 시 활성화 |
| Cmd+K 검색 모달 | `client:idle` | 페이지 로드 후 대기 |
| 댓글 시스템 | `client:visible` | 스크롤 시 하단에서 활성화 |
| Admin 에디터 | `client:load` | 즉시 완전 인터랙티브 필요 |
| 테마 토글 | `client:load` | FOUC 방지, 즉시 로드 |

### 페이지별 렌더링 전략 (SSG / SSR)

Astro `hybrid` 모드 사용: `output: 'hybrid'` + `adapter: vercel()`. 기본 SSG, 페이지별 SSR 선택.

| 페이지 | 렌더링 | 설정 | 이유 |
|---|---|---|---|
| **Home** (`/`) | SSR | `prerender = false` | Today's AI Pick이 매일 바뀜 |
| **Log** (`/log`) | SSR | `prerender = false` | 매일 자동 발행, 항상 최신 목록 필요 |
| **Post Detail** (`/log/[slug]`) | SSG + on-demand revalidation | `prerender = true` | 발행 후 내용이 거의 안 바뀜 |
| **Portfolio** (`/portfolio`) | SSG | `prerender = true` | 정적 콘텐츠 |
| **Admin** (`/admin/*`) | SSR | `prerender = false` | 최신 데이터 + 인증 체크 필요 |

- SSR 페이지: `export const prerender = false;` 선언
- Post Detail revalidation: `/api/revalidate`는 서버 사이드 전용, `REVALIDATE_SECRET` 검증 필수

## SEO & Performance

### SEO

- **메타 태그:** 포스트별 동적 `title`, `description`, `og:image`
- **구조화 데이터:** JSON-LD (`Article`, `BlogPosting`)
- **sitemap.xml:** Astro 자동 생성
- **RSS 피드:** `/rss.xml` 자동 생성
- **Canonical URL:** 페르소나별 URL이 아닌 단일 URL (중복 콘텐츠 방지)

### 성능 목표

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| **LCP** | < 1.5s | Vercel Analytics (자동) |
| **Lighthouse Performance** | 90+ | 주요 페이지 변경 시 Chrome DevTools 수동 체크 |

**모니터링:** Vercel Analytics 활성화 (무료 티어). Core Web Vitals 대시보드에서 LCP, CLS, INP 자동 추적.

### 폰트 로딩

셀프 호스팅 + preload 전략:

- **Clash Display, Satoshi** — `/fonts/` 에서 woff2 preload
- **Pretendard** — 동적 서브셋 셀프 호스팅 (`/fonts/pretendard/`)
- 폴백: `font-display: swap`

> [!note] 왜 셀프 호스팅인가
> Pretendard만 jsDelivr CDN에 의존하면 CDN 장애 시 한국어 텍스트가 시스템 고딕으로 폴백되며, 한글 폰트는 글자 폭 차이가 커서 레이아웃 시프트가 발생한다. 동적 서브셋은 유니코드 레인지별로 쪼개져 있어 각 수십 KB이므로 셀프 호스팅 용량 부담이 적다.

## Data Integration Boundary

### Supabase 클라이언트 초기화

`src/lib/supabase.ts`에서 `createClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY)`로 초기화.

### 데이터 접근 경계

| 작업 유형 | 호출 경로 | 이유 |
|---|---|---|
| 콘텐츠 읽기 (리스트/상세) | Frontend → Supabase 직접 | 응답 지연 최소화, 단순 조회 |
| 단순 댓글 CRUD / 좋아요 | Frontend → Supabase 직접 | RLS로 권한 통제 가능 |
| 시맨틱 검색 (Cmd+K) | Frontend → [[Backend-Stack\|FastAPI]] | 임베딩/랭킹 로직 캡슐화 |
| 포인트 / 퀴즈 / 베팅 | Frontend → [[Backend-Stack\|FastAPI]] | 트랜잭션/치트 방지 |
| 구독 권한 검증 | Frontend → [[Backend-Stack\|FastAPI]] | 결제 상태 검증, 시크릿 보호 |
| Admin AI 기능 | Frontend → [[Backend-Stack\|FastAPI]] | OpenAI 키 비노출, 비즈니스 로직 집중 |

### API 래퍼

`src/lib/api.ts` — `apiFetch<T>(path, init?)` 함수로 FastAPI 호출을 공통화. `credentials: "include"` 포함.

### 인증 흐름

Supabase OAuth (Google 등)로 소셜 로그인. `onAuthStateChange`로 UI 상태 동기화.

## Directory Structure

```
src/
├── components/
│   ├── common/          Navigation, Footer, ThemeToggle, SearchModal, SkipNavigation
│   ├── post/            PostCard, PersonaSwitcher, RelatedNews, CommentSection
│   ├── home/            HeroSection, TodaysAIPick, RecentPosts
│   ├── portfolio/       ArchitectureDiagram, CaseStudyCard
│   └── admin/           PostList, DraftList, PostEditor, AIPanel, PipelineStatus
├── layouts/
│   ├── BaseLayout.astro       공통 head, nav, footer
│   ├── PostLayout.astro       글 상세 레이아웃
│   └── AdminLayout.astro      Admin 전용
├── pages/
│   ├── index.astro            Home
│   ├── log/                   글 리스트 + [slug] 상세
│   ├── portfolio/
│   ├── admin/                 대시보드, drafts, new, edit/[id]
│   └── api/                   trigger-pipeline.ts
├── lib/
│   ├── supabase.ts            Supabase 클라이언트 초기화
│   └── api.ts                 FastAPI 래퍼
├── styles/
│   ├── global.css             CSS 변수, 폰트, 리셋, 테마
│   └── code-theme.css         코드 블록 구문 강조
└── content/                   MDX 콘텐츠
```

## Policy Addendum

### Persona Preference Priority

`DB > cookie > beginner` 순서로 페르소나 결정.

- 로그인 사용자: DB 설정 우선
- DB 비어 있으면 cookie 사용
- 둘 다 없으면 기본값 `beginner`
- 로그인 시 1회 동기화: cookie 존재 + DB 비어 있으면 cookie 값을 DB에 upsert
- 콘텐츠 폴백: `learner → beginner`

### Revalidate Security Boundary

- `/api/revalidate`는 `REVALIDATE_SECRET` 미일치 시 `401` 반환
- 클라이언트 컴포넌트에서 직접 호출 금지 — 서버 사이드 전용 (FastAPI 또는 Vercel server route)
- `src/lib/api.ts` 공개 래퍼에 revalidate 헬퍼 노출 금지
- 검증 기준: 클라이언트 번들에 `/api/revalidate` fetch 호출 0건

## Related

- [[System-Architecture]] — 프론트엔드가 속한 전체 시스템 아키텍처
- [[Backend-Stack]] — API를 제공하는 백엔드
- [[AI-News-Page-Layouts]] — 뉴스 페이지 레이아웃 디자인
- [[Component-States]] — 컴포넌트 상태 정의
- [[Design-System]] — 디자인 시스템 (폰트, 색상, 테마)
- [[Mobile-UX]] — 모바일 UX 최적화
- [[Accessibility]] — 접근성 정책
