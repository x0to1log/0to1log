# 📋 0to1log — Project Overview

> **문서 버전:** v2.3  
> **최종 수정:** 2026-03-05  
> **작성자:** Amy (Solo)  
> **상태:** Planning

---

## 1. 프로젝트 정의

**0to1log**는 무(0)에서 유(1)를 창조하는 AI 엔지니어의 성장 기록이자, 최신 LLM 에이전트 기술이 집약된 지능형 콘텐츠 플랫폼이다.

이 프로젝트는 세 가지 목표를 동시에 추구한다:

- **포트폴리오:** AI 파이프라인 설계, 에이전트 시스템 구현, 제품 기획 역량을 실제 작동하는 서비스로 증명
- **콘텐츠 플랫폼:** AI 뉴스와 기술 학습 콘텐츠를 독자 수준별로 재가공하여, 실질적 가치를 전달하는 미디어 운영
- **비즈니스 성장:** 데이터 기반 그로스 전략과 수익화를 통해, 사이드 프로젝트를 지속 가능한 프로덕트로 발전

> **Global-to-Local 확장 비전:** 영문 원천 데이터와 한국/글로벌 독자를 연결하는 상위 전략은 `07_Global_Local_Intelligence.md`에서 정의한다.

---

## 2. 타겟 오디언스

| 오디언스 | 이들이 얻는 가치 |
|---|---|
| **IT 트렌드에 민감한 개발자** | 페르소나별 맞춤 뉴스, 실무 적용 포인트, 기술 분석 |
| **리크루터 / 채용 담당자** | 기술 구현력(Engineering) + 제품 기획력(PM) 이중 역량 확인 |
| **함께 성장하는 동료** | 학습 자료, 프로젝트 트러블슈팅, 커리어 성장 서사 |

---

## 3. 핵심 역량 구조

```
┌───────────────────────────────────────────────────────────┐
│                    0to1log Platform                       │
├──────────────────┬──────────────────┬─────────────────────┤
│ Engineering Layer│ PM Layer         │ Growth Layer        │
│                  │                  │                     │
│ • AI 파이프라인   │ • 콘텐츠 전략     │ • SEO / GEO         │
│ • RAG 시스템     │ • 페르소나 UX     │ • 데이터 분석        │
│ • 멀티 에이전트   │ • 게이미피케이션   │ • 수익화 모델        │
│ • 시맨틱 검색     │ • 데이터 개선 루프 │ • 앱 확장           │
└──────────────────┴──────────────────┴─────────────────────┘
```

---

## 4. 핵심 기능 요약

### 🥇 Tier 1 — MVP 필수 (Phase 1-2)

| 기능 | 한 줄 설명 |
|---|---|
| **Daily Dual News** | 매일 2개 AI NEWS 발행: Research(기술 심화, 자동) + Business(시장 분석, 수동 검수) |
| **Persona-Based RAG-Refine** | Business 포스트를 비전공자/학습자/현직자 3가지 버전으로 자동 재가공 |
| **멀티 에이전트 시스템** | Ranking → Research/Business → Editorial 4단계 AI 파이프라인 |
| **관리자 에디터** | 마크다운 편집 + AI 제안 패널 + 페르소나별 탭 전환 리뷰 |
| **Pink Theme 디자인 시스템** | Dark/Light 적응형 테마, Neon Pink 액센트, 반응형 레이아웃 |
| **SEO 기반 설계** | JSON-LD 구조화 데이터, 사이트맵 자동 생성, 메타 태그 최적화 |
| **IT Blog** | 학습/프로젝트/커리어 포스팅을 AI 뉴스와 분리 운영. `blog_posts` 테이블로 독립 관리 |
| **데이터 분석 도구** | GA4 + MS Clarity 설치 — 유저 행동 패턴 수집 시작 |

### 🥈 Tier 2 — 고도화 (Phase 3)

| 기능 | 한 줄 설명 |
|---|---|
| **AI Semantic Search (Cmd+K)** | pgvector 임베딩 기반 자연어 검색 |
| **Dynamic OG Image** | 카테고리별 미리보기 이미지 자동 생성 |
| **AI Ops Dashboard** | API 비용 모니터링, 모델별 ROI, 프롬프트 버전 관리 |
| **Highlight to Share** | 문장 드래그 → SNS 공유 카드 자동 생성 (바이럴 장치) |
| **AARRR 지표 대시보드** | GA4 데이터 기반 유입/활성화/유지/매출/추천 지표 시각화 |

### 🥉 Tier 3 — 커뮤니티 & 게이미피케이션 (Phase 4)

| 기능 | 한 줄 설명 |
|---|---|
| **포인트 시스템** | 로그인 보너스, 피드백 참여, 소셜 인터랙션 보상 |
| **Prediction Game** | 뉴스 기반 퀴즈, 트렌드 베팅, 투표 시스템 |
| **리워드 & 뱃지** | 포인트 교환 혜택, 네온 돼지저금통 UI, 명예의 전당 |
| **거버넌스 참여** | AI PM에게 질문권, 분석 주제 제안 |
| **프리미엄 구독 검토** | 콘텐츠 계층화 (무료/프리미엄) 가능성 검증 + PWA 배포 |

### 🏆 Tier 4 — 앱 확장 (Phase 5)

| 기능 | 한 줄 설명 |
|---|---|
| **네이티브 앱 (Expo)** | 웹 플랫폼을 iOS/Android 앱으로 확장 — AI 뉴스 딜리버리 + 학습 플랫폼 |
| **구독 결제 (Polar)** | 프리미엄 구독 모델 확정 시 결제 연동 |
| **푸시 알림** | 일일 AI 뉴스 알림, 맞춤 콘텐츠 추천 |

---

## 5. 기술 스택 요약

| 레이어 | 기술 | 역할 |
|---|---|---|
| **Frontend** | Astro v5 + Tailwind v4 + MDX | 콘텐츠 중심 정적 사이트, 인터랙티브 컴포넌트 |
| **Animation** | Motion One + View Transitions API | 페이지 전환, 마이크로 인터랙션 |
| **AI Engine** | OpenAI API (gpt-4o/gpt-4o-mini) + PydanticAI | 콘텐츠 생성, 검수, 스키마 검증 |
| **RAG** | Tavily API (semantic) | 실시간 뉴스 수집, 출처 자동화, 관련 용어 시맨틱 검색 |
| **Backend** | FastAPI (Python) on Railway | 범용 API 백엔드 (AI 파이프라인/검색/커뮤니티/관리 API) |
| **Database** | Supabase (PostgreSQL + pgvector) | 콘텐츠 저장, 시맨틱 검색 임베딩 |
| **Hosting** | Vercel (Frontend + Cron 트리거) + Railway (범용 API 백엔드) | 배포, 도메인 관리 |
| **Auth** | Supabase Auth | Admin(이메일) + 사용자(소셜 로그인) |
| **Analytics** | GA4 + MS Clarity | 트래픽 분석, 히트맵, 세션 리플레이 |
| **SEO** | Astro SSG + JSON-LD + 사이트맵 | 검색 엔진 최적화, 구조화 데이터 |
| **수익화** | Google AdSense → Polar (Phase 5) | 광고 수익 → 구독 수익 (단계적) |

> **Railway 운영 전략 (ADR):** Railway는 FastAPI **범용 API 백엔드**로 운영한다.  
> - **Stage A (Phase 2):** 범용 API 구조를 먼저 구축하고, 파이프라인/Admin API 중심으로 저비용 운영  
> - **Stage B (Phase 3+):** 검색/커뮤니티/API 요청량 KPI 충족 시 Always-on 운영으로 상향

> 상세 기술 명세는 → `03_Backend_AI_Spec.md`, `04_Frontend_Spec.md` 참조  
> 비즈니스 전략 상세는 → `06_Business_Strategy.md` 참조

---

## 6. 콘텐츠 카테고리

### AI NEWS (`/{locale}/news/` · `news_posts` 테이블)

AI 파이프라인을 통해 자동/반자동 발행되는 뉴스 콘텐츠. `post_type`으로 Research/Business 구분.

| 카테고리 | AI 워크플로우 | 설명 |
|---|---|---|
| **AI NEWS (Research)** | 단일 버전 (자동 발행) | 기술 심화 분석 — 모델, 논문, 오픈소스 중심. 뉴스 없는 날은 "없음" 공지 + 최근 동향 보충 |
| **AI NEWS (Business)** | 3페르소나 (수동 검수) | 시장 분석 — 3페르소나 버전 + Related News 3카테고리 (Big Tech / Industry / New Tools) |

### IT Blog (`/{locale}/blog/` · `blog_posts` 테이블)

수동 작성 포스팅. AI 뉴스와 독립 관리. Admin에서 별도 섹션(Blog)으로 관리.

| 카테고리 | AI 워크플로우 | 설명 |
|---|---|---|
| **학습 (Study)** | Type A (Multi-Targeting) | PyTorch, SQL 등 원리 설명, 코드 공유 |
| **커리어 (Career)** | Type B (Authentic Voice) | 성장 서사, 동기부여 — 작성자 목소리 유지 |
| **프로젝트 (Project)** | Type B (Authentic Voice) | 아키텍처 설계, 트러블슈팅 — 작성자 목소리 유지 |

> **DB 분리 운영:** AI News는 `news_posts` 테이블, IT Blog는 `blog_posts` 테이블로 분리. 워크플로우가 다르므로(파이프라인 자동 vs 수동 작성) 테이블을 분리하여 각각의 스키마를 최적화. 좋아요/댓글도 `news_likes`/`news_comments` + `blog_likes`/`blog_comments`로 각각 분리. 북마크/읽기기록은 polymorphic `item_type` (`'news'`/`'blog'`/`'term'`)로 통합 관리.
> Admin 사이드바: Dashboard · News · Blog · Handbook · Settings

> 콘텐츠 전략 상세(훅 포인트, 프롬프트 가이드, 포인트 시스템)는 → `02_Content_Strategy.md` 참조

---

## 7. 사이트맵

```
0to1log.com
├── /                → EN Home (x-default, 기본 진입)
├── /en/news/        → EN AI 뉴스 리스트 (news_posts 테이블)
├── /en/news/[slug]  → EN AI 뉴스 상세
├── /en/blog/        → EN IT 블로그 리스트 (blog_posts 테이블)
├── /en/blog/[slug]  → EN IT 블로그 상세
├── /en/handbook/    → EN AI 용어집 (handbook_terms 테이블)
├── /ko/news/        → KO AI 뉴스 리스트
├── /ko/news/[slug]  → KO AI 뉴스 상세
├── /ko/blog/        → KO IT 블로그 리스트
├── /ko/blog/[slug]  → KO IT 블로그 상세
├── /ko/handbook/    → KO AI 용어집
├── /library/        → 나의 서재
├── /portfolio/      → 프로젝트 쇼케이스
├── /admin/          → 관리자 대시보드 (News · Blog · Handbook)
├── /en/log/ → 301  → /en/news/ (하위 호환 리다이렉트)
└── 언어 스위처/프로필 드롭다운 → ko/en 전환, 페르소나 설정, 테마 전환
```

> **07 연동 정책:** EN canonical + `x-default=/en/` 운영 원칙을 적용한다.

---

## 8. 로드맵

### Phase 1: Foundation (1~2개월)
블로그 기본 골격 + 인증 + DB 연동 + 그로스 기반 설계

- Astro + Tailwind + Motion One 기반 디자인 시스템
- 핵심 앱 구조 (Home / AI News(`/news`) / IT Blog(`/blog`) / Handbook / Library / Admin, with Portfolio as secondary showcase)
- Supabase 스키마 설계 및 CRUD
- Supabase Auth (Admin 이메일 + 사용자 소셜 로그인)
- 기본 마크다운 에디터
- 0to1log.com 커스텀 도메인 연결 (Vercel)
- **SEO 기반 설계:** JSON-LD 구조화 데이터, 자동 사이트맵, 메타 태그 (Phase 1a)
- **GA4 + MS Clarity 설치:** 데이터 수집은 일찍 시작할수록 가치 있음 (Phase 1b)

### Phase 2: AI Core (2~4개월)
핵심 AI 파이프라인 구축 — 포트폴리오 임팩트의 핵심

- Railway에 FastAPI 배포 (범용 API 서버 기반 구축)
- FastAPI + OpenAI API 연동
- 멀티 에이전트 파이프라인 (Ranking → Research/Business → Editorial)
- Daily Dual News: Research(자동 발행) + Business(수동 검수)
- Persona-Based RAG-Refine (Tavily → OpenAI → Supabase)
- PydanticAI 검증 레이어
- Persona Switcher: 로그인 사용자 `DB > 쿠키 > beginner`, 비로그인은 쿠키 기준
- Vercel Cron Jobs 자동화
- **AdSense 신청:** 콘텐츠 30개+ 축적 후 (Phase 2 후반)
- **Global-to-Local 전략 구체화:** 소싱/품질 게이트/티어링/SEO-i18n 원칙 정립 (`07_Global_Local_Intelligence.md`)

### Phase 3: Intelligence & Polish (4~6개월)
탐색 고도화 + 운영 도구 + 포트폴리오 완성 + 그로스 분석

- AI Semantic Search (Cmd+K) + pgvector
- Dynamic OG Image
- AI Ops Dashboard
- Always-on 전환 조건(KPI) 충족 시 Railway 운영모드 상향
- EN canonical / KO localized 운영 워크플로우 정착 (`07_Global_Local_Intelligence.md`)
- Cross-lingual 검색 품질 KPI(Recall@K, locale-aware nDCG@K) 관측 시작
- Highlight to Share (바이럴 장치: SNS 공유 카드)
- 포트폴리오 쇼케이스 섹션
- **AARRR 지표 대시보드:** GA4 데이터 기반 그로스 지표 시각화
- **SEO 고도화:** GEO (생성형 AI 검색 최적화) 전략 적용

### Phase 4: Community & Monetization (6개월+)
사용자 참여 유도 + 수익 모델 검증 — 트래픽 확보 후 단계적 도입

- 통합 포인트 시스템 (Base Points + 카테고리 특화)
- Prediction Game (퀴즈, 베팅, 투표)
- 리워드 체계 (뱃지, 돼지저금통, 명예의 전당)
- 거버넌스 참여 기능
- **프리미엄 구독 모델 검토:** 콘텐츠 계층화 (무료/프리미엄) 가능성 검증
- **PWA 배포:** 앱 설치 경험 제공 + 네이티브 앱 수요 검증

> **왜 PWA를 먼저 하는가:** 네이티브 앱 개발은 비용이 크다. PWA로 "앱처럼 설치"하는 경험을 먼저 제공하고, 실제 사용 데이터로 네이티브 앱의 필요성을 검증한 뒤 Phase 5로 진행한다.

### Phase 5: Native App (Phase 4 안정화 후)
웹 플랫폼을 네이티브 앱으로 확장 — AI 뉴스 딜리버리 & 학습 플랫폼

- Expo를 활용한 iOS/Android 앱 개발
- 푸시 알림: 일일 AI 뉴스 딜리버리, 맞춤 콘텐츠 추천
- 오프라인 읽기: 저장한 글을 오프라인에서 열람
- 구독 결제 연동 (Polar): 프리미엄 콘텐츠 인앱 결제
- 앱 스토어 출시 (App Store + Google Play)

> **Phase 5 진입 기준:** PWA 주간 활성 사용자 일정 수 이상 + 프리미엄 구독 전환율 검증 완료. 수치 기준은 Phase 4 데이터를 기반으로 설정한다.

---

## 9. 프로젝트 제약 조건

- **인원:** 1인 개발 & 운영 (Solo) — 코드 구현은 Claude Code (Opus 4.6) 바이브코딩 활용
- **예산(단계형):**
  - Stage A (현재): 무료/저비용 운영 중심 (API 비용 + 최소 인프라 비용)
  - Stage B (Always-on): Railway 기본료 + 컴퓨팅 변동비 반영으로 월 인프라비 상향
- **시간:** Phase 1~2 MVP 목표, 이후 Phase 3~5 점진적 확장
- **비용 관리:** 단순 분류 작업은 gpt-4o-mini, 품질 중요 작업은 gpt-4o로 분리하여 API 비용 최적화
- **수익화 순서:** SEO + 오가닉 트래픽 확보 → AdSense → 프리미엄 구독 (유료 광고 집행은 수익 발생 후)

---

## 10. 문서 인덱스

| # | 문서명 | 내용 | 상태 |
|---|---|---|---|
| 01 | **Project Overview** (본 문서) | 프로젝트 전체 그림, 로드맵, 스택 요약 | ✅ v2.3 |
| 02 | `Content_Strategy.md` | 훅 포인트, 프롬프트 가이드, 포인트 시스템, 콘텐츠 운영 규칙 | ✅ v1.2 |
| 03 | `Backend_AI_Spec.md` | AI 파이프라인, API 설계, DB 스키마, 인증, 크론 자동화 | ✅ v3.3 |
| 04 | `Frontend_Spec.md` | 디자인 시스템, 컴포넌트 명세, 페이지별 UI/UX, 애니메이션 | ✅ v2.3 |
| 05 | `Infrastructure.md` | 배포 구조, CI/CD, 환경 변수, 모니터링, 보안 | ✅ v2.3 |
| 06 | `Business_Strategy.md` | 수익화, 데이터 분석, SEO/GEO, 그로스 전략, 앱 로드맵 (Stage B 임계치 + 유닛 이코노믹스 + GEO 정량 기준 반영) | ✅ v1.4 |
| 07 | `Global_Local_Intelligence.md` | 영문 원천 데이터 기반 Global-to-Local 인텔리전스 전략, 품질 게이트, i18n 원칙 | ✅ v1.6 |
