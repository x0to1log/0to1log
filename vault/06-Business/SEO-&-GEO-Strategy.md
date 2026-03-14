---
title: SEO & GEO Strategy
tags:
  - business
  - seo
  - geo
  - growth
source: docs/06_Business_Strategy.md
---

# SEO & GEO Strategy

검색 엔진 최적화(SEO) + AI 검색 대응(GEO) 전략. 전통적 검색 엔진과 생성형 AI 검색 양쪽에서 0to1log 콘텐츠의 가시성을 확보하기 위한 전략을 정리한다.

## SEO Strategy

### Technical SEO (Phase 1a — 최우선)

> [!important]
> Astro SSG 특성상 SEO에 기본적으로 유리하지만, 구조화 데이터·사이트맵·메타 태그 최적화는 콘텐츠 생성 **전에** 설계해야 한다. 나중에 적용하면 기존 콘텐츠 전체를 수정해야 하기 때문이다.

| 항목 | 설명 | 구현 위치 |
|---|---|---|
| **JSON-LD 구조화 데이터** | 뉴스 기사 스키마 (`NewsArticle`, `Person`, `WebSite`) | Astro 레이아웃 |
| **사이트맵 자동 생성** | Astro 빌트인 사이트맵 + `robots.txt` | `astro.config.mjs` |
| **i18n SEO 태그** | `hreflang(ko/en/x-default)` + self-canonical | 공통 `<Head>` 컴포넌트 |
| **메타 태그 최적화** | `<title>`, `<meta description>`, Open Graph, Twitter Card | 공통 `<Head>` 컴포넌트 |
| **시맨틱 HTML** | `<article>`, `<time>`, `<nav>` 등 적절한 시맨틱 태그 사용 | 모든 페이지 |
| **URL 구조** | locale-aware slug: `/en/log/[slug]`, `/ko/log/[slug]` | Astro 라우팅 |

### Content SEO

- 매일 발행되는 **AI NEWS**는 검색 유입의 핵심 자산
- 뉴스 키워드를 제목과 slug에 반영 — AI 파이프라인의 Editorial 에이전트가 자동 처리
- `NewsArticle` JSON-LD에 `datePublished`, `author`, `publisher` 필수 포함

### Link Building

- Phase 4 이후 본격화 — 초기에는 콘텐츠 품질과 자연 링크 확보에 집중
- AI/Tech 커뮤니티에서의 인용 및 참조 유도

### Monitoring

- **Google Search Console**: 인덱싱 상태, 검색 쿼리, CTR 추적
- **Lighthouse 점수**: Performance, Accessibility, Best Practices, SEO 항목 지속 모니터링

### EN-first 기본 진입 언어 정책

- 루트 및 기본 진입은 EN을 기준으로 운영
- `x-default`는 `/en/`을 가리킴
- KO 페이지는 EN 기준 콘텐츠의 localized 버전으로 운영

## GEO (Generative Engine Optimization)

GEO는 기존 SEO를 넘어, **AI 검색 엔진**(Google AI Overview, ChatGPT, Perplexity, Gemini 등)에서 0to1log 콘텐츠가 **인용**되도록 최적화하는 전략이다.

### AI 검색 대응 콘텐츠 전략

- **질문-답변 형식** 섹션 추가 — AI가 추출하기 쉬운 구조
- **명확한 정의와 수치 데이터**를 본문에 포함 — 인용 확률 증가
- **콘텐츠 요약(TL;DR)**을 포스트 상단에 배치
- **출처 링크를 명시적으로 표기** — AI 검색의 신뢰도 신호

### EN Canonical Advantage

> [!note]
> EN-first 정책은 글로벌 AI 검색에서 인용될 확률을 높인다. 대부분의 AI 검색 엔진이 영어 콘텐츠를 우선 인덱싱하기 때문이다.

### GEO 성공 기준 (월간, 정량)

| 지표 | 정의 | 초기 기준 |
|---|---|---|
| **AI 검색 유입 세션(월)** | AI 검색 엔진/어시스턴트 유입 세션 수 | 300+ |
| **AI 검색 유입 비중(%)** | 전체 세션 대비 AI 검색 유입 비중 | 10%+ |
| **인용/출처 노출 확인 건수(월)** | AI 검색 결과에서 0to1log가 인용·출처로 노출된 확인 건수 | 20+ |

## Phase별 SEO/GEO Scope

| Phase | SEO/GEO 범위 |
|---|---|
| **Phase 1** | 기본 Technical SEO — JSON-LD, sitemap, meta tags, canonical URL, 시맨틱 HTML, RSS |
| **Phase 2** | Content SEO 최적화 — 키워드 전략 고도화, Search Console 기반 개선 |
| **Phase 3** | GEO 적극 최적화 + 측정 — AI 검색 대응 콘텐츠 구조, 인용 추적 |
| **Phase 4+** | 고급 링크 빌딩, 도메인 권위 구축, AI 검색 점유율 확대 |

> [!note]
> GEO를 Phase 3에서 시작하는 이유: GEO는 기존 콘텐츠가 풍부해야 효과가 있다. Phase 1~2에서 콘텐츠와 기본 SEO를 확보한 뒤, Phase 3에서 콘텐츠 구조를 AI 검색에 맞게 고도화한다.

## Related

- [[Business-Strategy]] — SEO/GEO가 속한 비즈니스 전략
- [[KPI-Gates-&-Stages]] — SEO/GEO 성과 KPI
- [[Frontend-Stack]] — SEO 구현 (meta, JSON-LD, sitemap)
- [[Content-Strategy]] — SEO 최적화 대상 콘텐츠
- [[Global-Local-Intelligence]] — EN canonical 다국어 전략
