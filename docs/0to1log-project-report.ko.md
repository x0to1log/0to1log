# 0to1log 프로젝트 보고서

> **프로젝트:** 0to1log  
> **형태:** AI 뉴스 큐레이션 + AI 용어집 + IT 블로그/제품 가이드 플랫폼  
> **역할:** Amy, 1인 풀스택 개발 및 운영  
> **문서 목적:** Gemini Notebook / 포트폴리오 / 프로젝트 회고용 종합 보고서  
> **작성 기준:** 로컬 저장소 문서와 구현 상태 기준, 2026-07-05 정리  

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [프로젝트 배경과 문제 정의](#2-프로젝트-배경과-문제-정의)
3. [제품 개요](#3-제품-개요)
4. [핵심 기능](#4-핵심-기능)
5. [기술 아키텍처](#5-기술-아키텍처)
6. [AI Engineering Deep Dive](#6-ai-engineering-deep-dive)
7. [주요 의사결정과 트레이드오프](#7-주요-의사결정과-트레이드오프)
8. [구현 진행 기록](#8-구현-진행-기록)
9. [정량 성과](#9-정량-성과)
10. [보안과 품질 관리](#10-보안과-품질-관리)
11. [배운 점](#11-배운-점)
12. [앞으로의 로드맵](#12-앞으로의-로드맵)
13. [Appendix A. 주요 문서 목록](#appendix-a-주요-문서-목록)
14. [Appendix B. 용어 정리](#appendix-b-용어-정리)
15. [Appendix C. 주요 데이터 모델](#appendix-c-주요-데이터-모델)
16. [Appendix D. Gemini Notebook 질문 예시](#appendix-d-gemini-notebook-질문-예시)

---

## 1. Executive Summary

0to1log는 빠르게 쏟아지는 글로벌 AI 뉴스를 수집, 분류, 검증, 요약, 발행하는 AI 뉴스 큐레이션 플랫폼이다. 단순히 OpenAI API로 글을 생성하는 프로젝트가 아니라, **비결정적인 LLM 출력을 제품 수준의 editorial pipeline으로 통제하는 AI engineering 프로젝트**에 가깝다.

핵심 제품은 세 가지 축으로 구성된다.

| 축 | 설명 | 해결하는 문제 |
|---|---|---|
| **AI News** | 매일 AI 뉴스를 수집하고 Research / Business 다이제스트로 발행 | "뉴스가 너무 많고, 무엇이 중요한지 모르겠다" |
| **Handbook** | 뉴스 속 AI 용어를 기초/심화 수준으로 설명하는 용어집 | "용어와 배경지식이 부족해 뉴스를 이해하기 어렵다" |
| **Library / Blog / Products** | 읽기 기록, 북마크, IT 블로그, AI 제품 가이드 | "읽은 것과 배운 것을 다시 찾고 실제 도구로 연결하기 어렵다" |

프로젝트의 가장 큰 특징은 AI 파이프라인을 **수집 - 분류 - 병합 - 보강 - 생성 - 검증 - 재실행 - 관리자 검수 - 발행**까지 하나의 운영 시스템으로 설계했다는 점이다. LLM은 글을 쓰는 역할만 맡지 않는다. 분류, 랭킹, source enrichment, community summarization, persona writing, quiz generation, quality scoring, handbook generation 등 여러 역할로 분해되어 사용된다.

AI engineering 관점에서 가장 중요한 성과는 다음과 같다.

- **Task decomposition:** 하나의 LLM 호출에 모든 일을 맡기지 않고 classify, merge, writer, summarizer, quiz, QC를 분리했다.
- **Schema enforcement:** citation URL hallucination을 프롬프트가 아니라 strict JSON schema와 enum allowlist로 차단했다.
- **Quality evaluation architecture:** LLM은 sub-score와 evidence를 평가하고, 최종 점수 계산은 코드가 수행하도록 분리했다.
- **Cost engineering:** flex tier, prompt cache, 부분 재실행 경로를 도입하여 비용을 실측하고 개선했다.
- **Production workflow:** draft-first, pipeline logs, checkpoint, fallback, admin review를 갖춘 운영 흐름을 만들었다.

요약하면, 0to1log는 "AI로 콘텐츠를 생성하는 사이트"가 아니라 **LLM을 신뢰 가능한 editorial system 안에 배치하고, 품질/비용/신뢰성/운영성을 함께 다룬 프로젝트**다.

---

## 2. 프로젝트 배경과 문제 정의

### 2.1 문제 배경

AI 분야의 핵심 정보는 영어권에서 가장 빠르게 나온다. 논문, 모델 릴리스, GitHub 프로젝트, 제품 발표, 투자 뉴스, 정책 변화, 커뮤니티 반응이 매일 여러 채널에서 발생한다. 하지만 한국어 독자가 이를 따라가기에는 몇 가지 구조적 문제가 있다.

1. **정보량이 너무 많다.**  
   매일 수십 건 이상의 AI 뉴스가 나오지만, 그중 어떤 것이 실제로 중요한지 판단하기 어렵다.

2. **중복 보도가 많다.**  
   하나의 사건을 여러 매체가 반복 보도한다. 단순 수집만 하면 같은 이벤트가 여러 번 등장한다.

3. **영문 기술 용어가 진입 장벽이 된다.**  
   "RAG", "MoE", "fine-tuning", "context window", "agent" 같은 용어는 자주 나오지만, 독자의 배경지식에 따라 이해도가 크게 갈린다.

4. **뉴스와 학습이 분리되어 있다.**  
   오늘의 뉴스에서 등장한 개념을 바로 학습하고, 나중에 다시 찾아보는 흐름이 약하다.

5. **AI가 쓴 콘텐츠의 신뢰성을 확인하기 어렵다.**  
   LLM은 유창하게 쓰지만 URL을 날조하거나, 숫자를 오역하거나, 출처 없는 주장을 만들 수 있다.

### 2.2 0to1log의 문제 정의

0to1log가 해결하려는 문제는 단순한 "AI 뉴스 요약"이 아니다.

> 글로벌 AI 정보를 한국어 독자에게 전달하되, 출처와 품질을 통제하고, 독자의 수준에 따라 다른 깊이의 설명을 제공하는 자동화된 editorial AI system을 만든다.

이 문제는 세 가지 하위 문제로 나뉜다.

| 하위 문제 | 필요한 시스템 |
|---|---|
| 중요한 뉴스를 고르는 문제 | multi-source retrieval, classification, ranking, merge |
| 믿을 수 있는 글을 만드는 문제 | source gate, strict schema, citation substitution, QC rubric |
| 독자 수준별로 전달하는 문제 | persona writing, bilingual adaptation, handbook linking, quiz |

### 2.3 타깃 사용자

| 사용자 | 필요 |
|---|---|
| **AI/IT 트렌드를 따라가고 싶은 개발자** | 기술 깊이가 있는 Research digest, 논문/모델/오픈소스 맥락 |
| **AI 업계 흐름을 보는 PM/기획자/마케터** | 투자, 제품, 기업 전략 중심 Business digest |
| **AI 입문자** | ChatGPT는 쓰지만 AI 뉴스를 꾸준히 보지는 않는 사람을 위한 Beginner 설명 |
| **채용 담당자/리크루터/동료 개발자** | Amy가 기획, AI, 백엔드, 프론트엔드, 운영까지 직접 설계했다는 포트폴리오 증거 |

---

## 3. 제품 개요

### 3.1 한 줄 설명

0to1log는 AI 뉴스를 매일 수집하고, 출처 기반으로 검증한 뒤, 독자의 수준에 맞는 다국어 다이제스트와 용어 해설로 발행하는 AI 기반 지식 플랫폼이다.

### 3.2 제품 표면

| 제품 표면 | 공개 라벨 | 설명 |
|---|---|---|
| 뉴스 | AI News | Research / Business 다이제스트 |
| 용어집 | Handbook | AI 용어의 기초/심화 해설 |
| 개인 공간 | Library | 읽기 기록, 북마크, 학습 진행 |
| 블로그 | IT Blog | 프로젝트, 커리어, 학습 글 |
| 제품 가이드 | Products | AI 제품 탐색과 비교 |
| 관리자 | Admin | 뉴스/블로그/핸드북 편집, 파이프라인 실행, 품질 점수 확인 |

### 3.3 사용자 경험 흐름

대표적인 사용자 흐름은 다음과 같다.

```text
뉴스 목록 진입
  -> Research / Business 뉴스 선택
  -> Expert / Learner / Beginner 페르소나 전환
  -> 본문 안의 용어를 Handbook 팝업으로 확인
  -> 퀴즈로 핵심 이해 확인
  -> 북마크 또는 읽기 기록 저장
  -> 관련 Handbook / Library / Blog로 이어 읽기
```

관리자 흐름은 다음과 같다.

```text
Admin 로그인
  -> 파이프라인 수동 실행 또는 cron 결과 확인
  -> pipeline logs / cost / quality score 확인
  -> draft 글 검수
  -> markdown 편집 및 preview
  -> publish / promote
  -> revalidate 또는 webhook 알림
```

### 3.4 다국어 운영 방향

제품은 영어와 한국어를 모두 제공한다. 영어가 canonical 역할을 하고, 한국어는 단순 번역이 아니라 한국어 독자에게 맞는 설명과 문맥을 제공한다.

중요한 점은 다국어가 "문자열 번역" 문제가 아니라 **locale integrity** 문제라는 것이다. 숫자 단위, 인용 위치, citation 수, 고유명사 표기, 한국어 문체, 용어 난이도가 모두 품질 기준에 포함된다.

---

## 4. 핵심 기능

### 4.1 Daily Dual News

매일 AI 뉴스 후보를 수집하고 두 종류의 다이제스트를 만든다.

| 다이제스트 | 초점 | 예시 |
|---|---|---|
| **Research** | 논문, 모델, 오픈소스, 기술 성능, 벤치마크 | 새 모델 구조, inference 최적화, eval 결과 |
| **Business** | 기업 전략, 제품 출시, 투자, 시장 변화 | Big Tech 발표, 스타트업 투자, AI 도구 출시 |

Research와 Business는 같은 AI 뉴스라도 다른 질문에 답한다.

- Research: "기술적으로 무엇이 달라졌는가?"
- Business: "시장과 제품 관점에서 무엇이 달라졌는가?"

### 4.2 Persona 기반 콘텐츠

같은 뉴스라도 독자의 배경지식에 따라 다르게 읽혀야 한다. 0to1log는 persona별 본문을 별도로 생성하고 저장한다.

| Persona | 대상 | 콘텐츠 방향 |
|---|---|---|
| **Expert** | 리서치 엔지니어, 깊이 있는 개발자 | prior work, benchmark, architecture, limitation |
| **Learner** | 개발자/기획자/학습자 | 비유와 기술 깊이의 균형, 핵심 용어 해설 |
| **Beginner** | ChatGPT는 쓰지만 AI 뉴스를 따라가지는 않는 입문자 | 가장 중요한 1-2개 흐름, 과한 해석 방지, Learner로 이어지는 funnel |

Beginner는 v13에서 다시 추가되었다. 중요한 설계는 Beginner를 required layer로 바로 넣지 않고 optional layer로 둔 점이다. Expert/Learner가 성공하면 기본 발행이 가능하고, Beginner 실패는 auto-publish eligible 판단에만 반영된다.

### 4.3 AI News Pipeline

AI News Pipeline은 다음 단계를 가진다.

1. 7개 내외의 소스에서 뉴스 후보 수집
2. URL 중복 제거 및 최근 발행 이력 필터링
3. Research / Business 후보 분류
4. 같은 이벤트를 merge
5. HN/Reddit 등 community pulse 수집
6. relevance filter로 off-topic 댓글 제거
7. 소스 품질 게이트와 enrich
8. persona별 digest 생성
9. strict schema로 citation URL 제한
10. citation 후처리 및 renumbering
11. quiz 별도 생성
12. quality scoring
13. draft 저장
14. admin 검수 후 발행

### 4.4 Handbook

Handbook은 AI 용어를 basic / advanced 두 수준으로 설명하는 용어집이다. 뉴스에서 등장한 용어를 자동 추출하거나 관리자가 수동으로 등록할 수 있다.

핵심 설계는 다음과 같다.

- term type 분류
- Tavily 검색 컨텍스트 수집
- basic / advanced content 생성
- Self-Critique
- quality scoring
- queued / draft / published 상태 관리
- Handbook quality measurement CLI
- 800개 seed 확장 계획

Handbook은 단독 기능이 아니라 AI News와 연결된다. 뉴스 본문에서 용어를 클릭하면 Handbook 설명으로 이어지고, Library에서는 읽은 용어와 학습 진행을 다시 볼 수 있다.

### 4.5 Library

Library는 사용자의 재방문 흐름을 위한 기능이다.

- 읽은 뉴스
- 북마크한 뉴스/용어
- 학습 진행
- persona preference
- 재방문 추천의 기반 데이터

현재 계획상 Phase 3 Intelligence에서 추천, resurfacing, Handbook feedback 집계와 더 강하게 연결될 예정이다.

### 4.6 Admin

Admin은 이 프로젝트의 운영 핵심이다. AI가 만든 결과를 무조건 자동 발행하지 않고, draft-first로 저장한 뒤 사람이 최종 검수한다.

Admin에서 다루는 주요 기능은 다음과 같다.

- 뉴스/블로그/핸드북 목록 관리
- markdown 편집 및 미리보기
- publish / promote
- pipeline run logs 확인
- quality score 및 breakdown 확인
- pipeline 수동 실행
- rerun_from 특정 stage 실행
- 비용/토큰/오류 추적

---

## 5. 기술 아키텍처

### 5.1 전체 구조

```text
사용자 브라우저
  |
  v
Vercel / Astro Frontend
  |                         \
  |                          \-> Supabase JS SDK
  |                              - published content 조회
  |                              - auth
  |                              - bookmark / reading history / feedback
  |
  \-> Vercel API Route
        |
        v
Railway / FastAPI Backend
  - AI pipeline
  - admin API
  - cron endpoint
  - semantic/recommendation API
  - OpenAI/Tavily/Exa/Brave integration
        |
        v
Supabase PostgreSQL
  - news_posts
  - blog_posts
  - handbook_terms
  - pipeline_logs
  - pipeline_runs
  - user tables
```

### 5.2 프론트엔드

| 항목 | 선택 |
|---|---|
| Framework | Astro v5 |
| Styling | Tailwind CSS v4 |
| Hosting | Vercel |
| Routing | `/en/`, `/ko/` 명시적 locale route |
| 주요 페이지 | News, Handbook, Blog, Products, Library, Admin |

프론트엔드는 콘텐츠 중심 사이트의 성능과 SEO를 위해 Astro를 사용한다. 공개 콘텐츠는 빠른 렌더링과 검색 노출이 중요하고, 관리자/사용자 기능은 필요한 곳에만 클라이언트 스크립트를 붙이는 구조다.

중요한 프론트엔드 원칙은 다음과 같다.

- Astro의 `client:load` 남용 금지
- 일반 `<script>` 블록으로 필요한 상호작용만 구현
- CSP nonce 유지
- Supabase service role key 노출 금지
- canonical / hreflang / sitemap / RSS 관리
- public language와 admin language 분리

### 5.3 백엔드

| 항목 | 선택 |
|---|---|
| Framework | FastAPI |
| Hosting | Railway |
| AI orchestration | Python services + OpenAI SDK + Pydantic/PydanticAI 패턴 |
| Background execution | Cron endpoint + fire-and-forget |
| Tests | pytest |
| Rate limit | slowapi |

FastAPI는 단순 파이프라인 실행기가 아니라 범용 API 백엔드로 설계되었다. 향후 semantic search, 추천, 구독 권한, 포인트/퀴즈 같은 서버사이드 로직을 수용하기 위해 Railway에 별도 백엔드를 둔다.

### 5.4 데이터베이스와 인증

| 항목 | 선택 |
|---|---|
| DB | Supabase PostgreSQL |
| Auth | Supabase Auth |
| Security | RLS |
| 주요 테이블 | news_posts, blog_posts, handbook_terms, pipeline_logs, profiles, user_bookmarks, reading_history |

읽기 중심 데이터는 프론트엔드가 Supabase에 직접 접근할 수 있다. 하지만 AI pipeline, admin mutation, cron, external API secret이 필요한 작업은 FastAPI를 경유한다.

### 5.5 AI와 검색

| 역할 | 기술 |
|---|---|
| Main generation | OpenAI gpt-5 |
| Light classification / merge / quiz | OpenAI gpt-5-mini |
| Lightweight filtering | OpenAI gpt-5-nano |
| Search / retrieval | Tavily, Exa, Brave, HN Algolia, GitHub, arXiv, Hugging Face |
| Structured validation | strict JSON schema, Pydantic models |

현재 구현의 모델 설정은 환경 변수로 분리되어 있다.

```text
OPENAI_MODEL_MAIN      = gpt-5
OPENAI_MODEL_LIGHT     = gpt-5-mini
OPENAI_MODEL_NANO      = gpt-5-nano
OPENAI_MODEL_REASONING = gpt-5-mini
```

이 설계는 모델 변경이나 롤백을 코드 수정 없이 환경 변수 변경으로 처리하기 위한 것이다.

---

## 6. AI Engineering Deep Dive

### 6.1 AI 파이프라인 문제 정의

0to1log의 AI engineering 문제는 "뉴스를 요약하라"가 아니다. 실제 문제는 다음과 같다.

> 매일 들어오는 불완전하고 중복된 외부 정보를, 출처와 품질을 통제하면서, 여러 독자 수준에 맞는 다국어 콘텐츠로 변환하고, 비용과 실패 가능성을 운영 가능한 수준으로 유지한다.

이 문제에는 다음 리스크가 포함된다.

| 리스크 | 예시 | 대응 |
|---|---|---|
| 중복 입력 | 같은 이벤트를 여러 매체가 보도 | classify 후 merge |
| 저품질 출처 | SEO spam, content farm, mirror repo | source quality gate |
| URL hallucination | LLM이 존재하지 않는 URL 생성 | strict schema enum allowlist |
| locale 오류 | `$8.3B`를 `8.3억 달러`로 오역 | locale integrity rubric + Writer/QC mirror |
| 과도한 비용 | multi-source 입력 폭발 | merge, flex tier, prompt cache |
| LLM 평가 불안정 | 96점인데 실제 KO quote가 영어 | sub-score + evidence + code aggregation |
| 장애/실패 | LLM timeout, 5xx, flex 429 | retry, estimated usage logging, draft-first |

### 6.2 모델 오케스트레이션 구조

초기에는 하나의 Writer에게 많은 역할을 맡기는 구조였다. 하지만 프로젝트가 진행되면서 반복적으로 확인한 패턴은 명확했다.

> 한 호출에 두 가지 이상의 독립적인 판단을 결합하면, 둘 중 하나는 품질이 떨어진다.

그래서 파이프라인은 점점 역할 단위로 분리되었다.

| 버전/단계 | 분리한 역할 | 결과 |
|---|---|---|
| v8 | classification과 ranking 분리 | 후보 선별 정확도 개선 |
| v9 | classify와 merge 분리 | 같은 이벤트 과묶기 문제 해결 |
| v10 | Writer와 Community Summarizer 분리 | raw comment 처리 안정화 |
| v13 | Writer와 Quiz Generator 분리 | body 생성과 quiz 정답 정확도 분리 |

현재 모델 오케스트레이션은 대략 다음 구조다.

```text
gpt-5-mini
  -> classify candidates
  -> merge same event
  -> rank groups
  -> summarize community

gpt-5-nano
  -> lightweight relevance filtering
  -> low-cost validation/filtering

gpt-5
  -> expert/learner/beginner digest generation
  -> complex synthesis

gpt-5-mini / reasoning tier
  -> quality scoring
  -> quiz generation
```

모델을 하나로 통일하지 않은 이유는 비용과 품질의 균형 때문이다. 생성과 종합에는 큰 모델이 필요하지만, 분류와 간단한 필터링은 더 작은 모델로 충분하다.

### 6.3 Retrieval & Source Quality

뉴스 파이프라인의 품질은 Writer prompt보다 입력 데이터의 품질에 더 크게 좌우된다. 이 프로젝트에서 얻은 중요한 결론은 다음과 같다.

> 좋은 생성 프롬프트보다 좋은 소스 필터링이 먼저다.

수집 계층은 여러 소스를 사용한다.

- Tavily
- Exa
- Brave
- GitHub
- arXiv
- Hugging Face
- HN Algolia
- Reddit/Discussion sources

그 다음 다음과 같은 게이트를 통과시킨다.

| 게이트 | 설명 |
|---|---|
| URL deduplication | 같은 URL 반복 제거 |
| recent publish filter | 최근 발행한 같은 이벤트 반복 방지 |
| category page filter | 기사 본문이 아닌 카테고리/홈페이지 제거 |
| source quality gate | content farm, SEO spam, mirror domain 차단 |
| authority rule | GitHub 원본 repo를 fork/mirror보다 우선 |
| community relevance filter | upvote가 높아도 off-topic인 댓글 제거 |
| enrich condition | 소스가 부족한 그룹만 Exa 보강 |

특히 v11에서 Apr 19 품질 사고 이후 source quality gate가 강화되었다. 문제의 핵심은 Writer가 나쁜 글을 쓴 것이 아니라, 낮은 품질의 source가 Writer에게 그대로 전달된 것이었다. 이후 enrich 단계에서 spam/content farm/mirror source를 차단하도록 개선했다.

### 6.4 Hallucination 방지 설계

LLM hallucination 방지는 이 프로젝트의 핵심 AI engineering 성과다.

초기 접근은 프롬프트였다.

```text
"URL을 만들지 마라."
"제공된 출처만 사용하라."
"출처 없는 주장을 하지 마라."
```

하지만 프롬프트는 100% 안전장치가 아니다. LLM은 지시를 어길 수 있고, 그 결과는 유창해 보여서 발견하기 어렵다.

v12에서 해결 방식을 바꿨다.

```text
Writer input:
  fact_pack.source_urls = [허용된 URL 목록]

Writer output schema:
  body: "... [CITE_1] ..."
  citations: [
    { n: 1, url: enum(source_urls) }
  ]
```

즉, `citations[].url`이 allowlist enum 안의 값만 가질 수 있게 strict JSON schema를 만든다. 그러면 LLM이 잘못된 URL을 쓰려고 해도 API가 응답 자체를 거부한다.

이 방식의 의미는 크다.

| 방식 | 신뢰도 | 한계 |
|---|---|---|
| Prompt instruction | 85-97% 수준의 준수 | 모델이 어길 수 있음 |
| Post-hoc URL check | 실제 검증 가능 | false positive가 많으면 좋은 citation도 제거 |
| Schema enum allowlist | API 레벨에서 잘못된 URL 거부 | allowlist 구축 필요 |

0to1log는 최종적으로 **프롬프트가 아니라 contract로 hallucination을 막는 방향**을 택했다.

### 6.5 Citation 후처리

Writer는 본문에 `[CITE_N]` placeholder를 넣고, sidecar `citations` 배열에 URL을 담는다. 이후 코드가 다음을 수행한다.

1. `[CITE_N]`이 실제 citations 배열과 일치하는지 확인
2. URL이 allowlist에 있는지 확인
3. `[CITE_N]`을 `[N](URL)` markdown 링크로 치환
4. 본문 전체에서 citation 번호를 다시 순서대로 정렬
5. source_cards를 생성해 DB에 저장

이 설계는 두 가지 장점이 있다.

- LLM이 citation 번호를 섹션마다 리셋해도 코드가 전역 번호로 정리한다.
- 본문에 드러나는 링크와 DB에 저장되는 source metadata가 일치한다.

### 6.6 Quality Evaluation System

품질 평가는 단순히 "좋은 글인가?"를 묻지 않는다. 프로젝트가 커지면서 단일 점수는 한계를 드러냈다. 특히 KO 본문에 영어 인용만 남아 있어도 총점이 96점으로 나오는 사고가 있었다.

이후 품질 평가는 다음 구조로 바뀌었다.

```text
LLM judge:
  - sub-score별 점수
  - 각 점수의 evidence
  - issue list

Code:
  - 점수 aggregation
  - structural penalty
  - caps
  - quality flags
  - final_score 계산

Admin:
  - breakdown 확인
  - draft 검수
  - publish 판단
```

대표적인 평가 차원은 다음과 같다.

| 평가 차원 | 설명 |
|---|---|
| section completeness | 필요한 섹션이 빠지지 않았는가 |
| source quality | 근거가 실제 출처에 기반하는가 |
| citation integrity | citation이 충분하고 올바른가 |
| locale integrity | EN/KO가 같은 사실과 출처를 유지하는가 |
| claim calibration | 과장이나 미래 예측이 사실처럼 쓰이지 않았는가 |
| temporal anchoring | 날짜와 시점이 명확한가 |
| internal consistency | 본문 내부에서 주장이 충돌하지 않는가 |
| persona fit | Expert/Learner/Beginner 대상에 맞는가 |
| quiz answer integrity | 선택지와 정답 인덱스가 일치하는가 |

중요한 원칙은 다음과 같다.

> LLM은 정성 평가와 근거 서술에 집중하고, 계산과 감점은 코드가 담당한다.

이 방식은 LLM의 장점과 약점을 분리한다. LLM은 글의 의미와 품질을 평가하는 데 강하지만, 산술 계산과 일관된 감점 적용은 코드가 더 안정적이다.

### 6.7 Cost & Latency Optimization

AI 비용 최적화는 모델 이름만 바꾸는 문제가 아니었다. 0to1log는 입력 크기, 중복, reasoning token, cache, service tier, 재실행 단위를 모두 관리했다.

대표적인 비용 이슈는 v9에서 발생했다. 다중 소스 보강을 추가하자 입력이 폭발해 run 비용이 $0.77까지 증가했다. 원인은 같은 이벤트의 여러 기사를 각각 처리하면서 입력이 중복된 것이었다. 이를 merge 단계로 해결해 비용을 $0.43 수준으로 낮췄다.

v12에서는 비용과 품질을 동시에 다뤘다.

| 설정 | 비용 효과 |
|---|---|
| reasoning_effort만 high로 상향 | $0.50 -> $0.86, 72% 증가 |
| flex tier 추가 | serving tier 비용 절감 |
| prompt_cache_key 추가 | 반복 prompt input cache |
| URL liveness 제거 | false positive와 불필요한 검증 제거 |
| 최종 구조 | $0.33-$0.41 수준으로 안정 |

또한 `rerun_from=quality` 경로를 만들어 Writer를 다시 돌리지 않고 QC만 다시 실행할 수 있게 했다.

| 재실행 방식 | 비용 |
|---|---|
| Writer부터 재실행 | 약 $0.54 |
| QC만 재실행 | 약 $0.05 |

이것은 단순 절감이 아니라 실험 속도에 영향을 준다. QC rubric을 바꿀 때 전체 글 생성을 반복하지 않아도 되므로, 품질 평가 설계를 더 자주 검증할 수 있다.

### 6.8 Reliability & Failure Handling

AI pipeline은 외부 API, 네트워크, 모델 응답, 스키마 검증 실패 등 여러 실패 지점을 가진다. 0to1log는 실패를 모두 "중단"으로 처리하지 않는다.

핵심 원칙은 draft-first다.

> 인프라 에러는 재시도하지만, 품질 이슈는 draft로 저장하고 사람이 판단한다.

대표적인 reliability 장치는 다음과 같다.

| 장치 | 설명 |
|---|---|
| fire-and-forget cron | Vercel timeout을 피하기 위해 FastAPI가 202를 즉시 반환하고 백그라운드 실행 |
| pipeline_runs lock | 같은 날짜 파이프라인 중복 실행 방지 |
| pipeline_logs | stage별 상태, 비용, token, error 기록 |
| checkpoint | 중간 결과 저장 및 rerun 지원 |
| flex retry | 429/5xx transient error backoff |
| estimated failed usage | 응답 없이 실패한 OpenAI 호출도 입력 token 비용 추정 |
| optional Beginner layer | 새 persona 실패가 전체 발행을 막지 않도록 격리 |
| preserve_existing_fields | 부분 재실행 시 기존 필드 손실 방지 |

### 6.9 Multilingual / Persona Engineering

0to1log의 콘텐츠 생성은 "영어 글을 만들고 한국어로 번역"하는 단순 구조가 아니다. 다국어와 persona는 품질 기준에 직접 들어간다.

특히 한국어에서는 다음 문제가 중요했다.

- 숫자 단위 변환 오류
- 영어 인용문만 남는 문제
- citation 누락
- 영어식 문장 구조
- 전문 용어를 설명 없이 그대로 쓰는 문제
- 고유명사와 제품명을 과도하게 번역하는 문제

v11.1에서는 `$8.3 billion`을 `8.3억 달러`로 옮긴 사고가 계기가 되어 Writer와 QC를 동시에 강화했다. 여기서 얻은 원칙은 다음과 같다.

> QC에 새 기준을 추가하면 Writer에도 같은 기준을 반영해야 한다.

QC만 강화하면 점수는 낮아지지만 생성 behavior는 바뀌지 않는다. Writer prompt와 QC rubric은 같은 커밋 단위로 동기화해야 한다.

Persona 설계에서도 중요한 변화가 있었다. Learner가 "Expert에서 jargon만 뺀 버전"이 되는 문제가 있었고, v13에서 진짜 입문자를 위한 Beginner를 별도로 설계했다. Beginner는 짧은 버전이 아니라 다른 목적의 글이다.

| Persona | 실패하면 안 되는 것 |
|---|---|
| Expert | 기술 깊이 부족, 근거 없는 claim |
| Learner | 쉬운 척하지만 사실상 expert 글 |
| Beginner | 용어가 너무 많아 첫 문단부터 이해 불가 |

### 6.10 Observability

AI pipeline에서 관측성은 단순 로그가 아니라 제품 품질의 일부다. 0to1log는 다음을 기록한다.

- model_used
- input_tokens
- output_tokens
- cached_tokens
- reasoning_tokens
- tokens_used
- service_tier
- cost_usd
- quality_score
- quality_breakdown
- quality_issues
- structural_penalty
- pipeline stage status
- duration_ms
- error_message

특히 reasoning token을 기록한 것은 중요하다. gpt-5 계열에서는 completion_tokens 중 보이지 않는 reasoning token이 큰 비중을 차지할 수 있다. 이 값을 보지 않으면 "왜 비용이 늘었는지"를 설명할 수 없다.

---

## 7. 주요 의사결정과 트레이드오프

### 7.1 Railway FastAPI를 범용 API 백엔드로 둔 결정

처음에는 파이프라인 실행 전용 서버처럼 보일 수 있었지만, 프로젝트는 검색, 추천, 권한, 포인트, 퀴즈, 구독 검증으로 확장될 수 있다. 그래서 Railway의 FastAPI를 범용 API 서버로 설계했다.

| 대안 | 장점 | 한계 |
|---|---|---|
| Vercel Serverless | 프론트와 가까움 | 긴 AI pipeline 처리에 timeout 위험 |
| Supabase Edge Function | Supabase와 가까움 | Python/PydanticAI 재사용성 낮음 |
| Railway FastAPI | Python AI stack, 장시간 작업, 범용 API | 운영비와 별도 배포 관리 필요 |

### 7.2 Supabase 직접 호출과 FastAPI 경유의 경계

모든 요청을 FastAPI로 보내지 않는다. 단순 조회와 RLS로 보호 가능한 CRUD는 Supabase 직접 호출이 더 단순하다. 반면 비밀키, 외부 API, 복잡한 트랜잭션, AI pipeline은 FastAPI로 보낸다.

| 작업 | 경로 |
|---|---|
| published 글 조회 | Frontend -> Supabase |
| 댓글/좋아요/북마크 등 단순 user action | Frontend -> Supabase 또는 API route + Supabase |
| AI pipeline 실행 | Frontend/API Route -> FastAPI |
| Cron | Vercel Cron -> FastAPI |
| Semantic search / recommendation | Frontend -> FastAPI |
| 구독/포인트/퀴즈 트랜잭션 | Frontend -> FastAPI |

### 7.3 Draft-first 운영

완전 자동 발행은 매력적이지만, AI 콘텐츠는 품질과 신뢰성이 중요하다. 그래서 기본 정책은 draft-first다.

장점:

- 품질 미달 콘텐츠가 바로 공개되지 않는다.
- admin이 quality breakdown을 보고 판단할 수 있다.
- 파이프라인이 실패해도 중간 결과를 보존한다.
- auto-publish는 점진적으로 도입할 수 있다.

단점:

- 사람이 검수해야 하므로 완전 자동화보다 운영 부담이 있다.
- 매일 발행 속도가 admin workflow에 영향을 받는다.

### 7.4 Prompt보다 Contract

이 프로젝트는 "프롬프트를 더 길게 쓰면 해결된다"는 접근에서 점점 멀어졌다. 많은 문제는 더 강한 프롬프트가 아니라 더 나은 contract로 해결했다.

| 문제 | 프롬프트식 해결 | 최종 해결 |
|---|---|---|
| URL hallucination | URL을 만들지 말라고 지시 | schema enum allowlist |
| citation numbering | 번호를 순서대로 쓰라고 지시 | 코드로 renumber |
| quiz 정답 오류 | 정답을 정확히 고르라고 지시 | answer_index integer schema |
| CP thread link | 링크를 넣으라고 지시 | 코드 후처리 linkify |
| locale parity | 한국어도 맞추라고 지시 | locale_integrity sub-score + citation preservation |

### 7.5 Beginner optional layer

Beginner persona는 제품적으로 중요하지만 새 레이어는 실패 위험을 만든다. 그래서 바로 발행 필수 조건으로 넣지 않고 optional layer로 도입했다.

```text
DAILY_DIGEST_PERSONAS = expert, learner, beginner
REQUIRED_DAILY_DIGEST_PERSONAS = expert, learner
```

이 설계는 새 기능을 넣을 때 안정적인 경로다.

- 생성은 시도한다.
- 실패해도 기존 핵심 흐름은 유지한다.
- 품질 점수에는 반영한다.
- 안정화 후 required로 승격할 수 있다.

---

## 8. 구현 진행 기록

### 8.1 Phase 흐름

프로젝트는 여러 phase로 나뉘어 진행되었다.

| Phase | 내용 | 상태 |
|---|---|---|
| Phase 1a Foundation | 디자인 시스템, Supabase schema, Auth, markdown editor, SEO/Analytics 기반 | 완료 |
| Phase 1b Analytics | GA4, MS Clarity, 초기 데이터 수집 | 완료 |
| Phase 2B OPS | FastAPI, OpenAI 연동, admin API, cron skeleton | 완료 |
| Phase 2C EXP | 뉴스 리스트/상세, Admin Editor, mock-first UI | 완료 |
| Phase 2D INT | 실제 API fetch, Auth guard, cron 연동, 보안 하드닝 | 완료 |
| Phase 3-USER | 소셜 로그인, 북마크, 읽기 기록, 학습 진행, Library 설계/구현 | 완료/확장 중 |
| Phase 3A-SEC | CSP nonce, script loading, security review 수정 | 완료 |
| Phase 3B-SHARE | X/LinkedIn/URL copy/Web Share API 공유 | 완료 |
| NP4-Q | News Pipeline v4 quality stabilization | 2026-04-10 close |
| HB-QM | Handbook Quality & Content Migration | 진행 중 |

### 8.2 현재 스프린트

현재 실제 active sprint는 `vault/09-Implementation/plans/ACTIVE_SPRINT.md` 기준으로 **HB-QM: Handbook Quality & Content Migration**이다.

핵심 목표는 다음과 같다.

- published 용어를 v4 구조로 regenerate
- 800개 신규 seed term 큐레이션 및 생성 파이프라인
- hallucination 즉시 수정
- 비기술 용어 archive
- Handbook SEO 구조화 데이터
- 최종 검증: `ruff check .` + `pytest tests/ -v`

### 8.3 News Pipeline 버전 진화

| 버전 | 핵심 변화 |
|---|---|
| v2-v4 | 단일 소스 기반, 초기 prompt 구조 |
| v5-v6 | 다중 소스, skeleton map |
| v7-v8 | classification/ranking 분리, DON'T 제거 |
| v9 | multi-source enrich, merge 도입 |
| v10 | gpt-5 전환, Community Pulse Summarizer 분리 |
| v11 | Rubric v2, source quality gate, rerun_from=quality |
| v11.1 | Writer-QC mirror sync, locale/claim calibration 강화 |
| v12 | schema enum, flex tier, prompt cache, liveness 제거 |
| v13 | Beginner persona, quiz pipeline 분리 |

### 8.4 코드 구조 변화

News pipeline hardening 과정에서 `pipeline.py`가 3,794줄에서 2,149줄로 줄었고, 관련 기능이 여러 파일로 분리되었다.

대표 구조:

```text
backend/services/
  pipeline.py
  pipeline_digest.py
  pipeline_quality.py
  pipeline_persistence.py
  news_collection.py
  agents/
    ranking.py
    advisor.py
    persona_writer.py
    prompts_news_pipeline.py
    schemas/news_writer.py
    schemas/news_quiz.py
```

이 변화는 단순 리팩터링이 아니라, 파이프라인이 커지면서 stage별 책임을 분리하기 위한 구조 정리다.

---

## 9. 정량 성과

### 9.1 Run당 비용 변화

| 구간 | 평균 비용/run | 의미 |
|---|---:|---|
| v2-v4 | $0.18 | 초기 단일 소스 |
| v5-v6 | $0.20 | 다중 소스 일부 도입 |
| v7-v8 | $0.25 | ranking 분리 |
| v9 초기 | $0.62-$0.77 | multi-source 입력 폭발 |
| v9 + merge | $0.43 | 입력 중복 제거로 복구 |
| v10 | $0.58 | gpt-5 전환과 CP 강화 |
| v11 | $0.54 | rubric 강화 후 안정 |
| v12 | $0.33-$0.41 | flex/cache/schema 구조 최적화 |
| v13 | 측정 중 | Beginner + quiz 분리 |

핵심은 비용이 단조롭게 줄어든 것이 아니라, 품질을 올리며 일시적으로 비용이 늘었고, 이후 구조 개선으로 다시 낮췄다는 점이다.

### 9.2 Citation density

초기 Expert citation은 1.8-2.7 수준이었고, v5-v8에서 12.9-16.8까지 증가했다. v12에서는 Research Expert가 peak 30 citation까지 도달했다.

Citation density가 중요한 이유는 다음과 같다.

- AI 글의 주장이 검증 가능한 출처에 연결된다.
- 독자가 원문을 확인할 수 있다.
- Admin이 품질을 판단할 수 있다.
- hallucination 가능성을 줄인다.

### 9.3 Pipeline hardening 성과

| 항목 | 개선 |
|---|---|
| `pipeline.py` 크기 | 3,794줄 -> 2,149줄, 43% 감소 |
| 유료 API 쿼리 | 24건 -> 11건, 46% 감소 |
| SEO spam 도메인 | 47% -> 0% |
| QUALITY_CHECK 공유 블록 | -1,956 tokens |
| rerun_from=quality | 약 10배 비용 절감 |

### 9.4 테스트 커버리지와 검증 자산

백엔드에는 pipeline, ranking, quality scoring, citation substitution, handbook, weekly, quiz, usage metrics, security 관련 테스트가 다수 존재한다.

대표 테스트 영역:

- news collection
- ranking/classification
- classify/merge
- citation substitution
- news writer schema
- news quiz schema
- digest validation
- quality scoring
- weekly recap
- handbook validators
- handbook quality checks
- usage metrics
- cron
- security/auth

프론트엔드에는 product tags, admin pipeline cost metrics, handbook quality 등 일부 테스트와 `npm run check` 기반 타입 검증 흐름이 있다.

---

## 10. 보안과 품질 관리

### 10.1 인증과 권한

0to1log는 Supabase Auth를 사용한다.

| 역할 | 권한 |
|---|---|
| Visitor | published 콘텐츠 읽기 |
| User | 북마크, 읽기 기록, 댓글, feedback, 설정 |
| Admin | 콘텐츠 작성/수정/삭제, pipeline 실행, admin dashboard 접근 |

Admin 권한은 코드 상수보다 DB의 `admin_users` 테이블을 기준으로 판단하는 설계가 더 안전하다. FastAPI admin endpoint는 `require_admin` 의존성으로 보호한다.

### 10.2 RLS

Supabase RLS는 사용자 데이터와 공개 콘텐츠의 경계를 보호한다.

주요 정책 방향:

- published content는 visitor가 읽을 수 있음
- draft는 admin만 접근
- 댓글/좋아요/북마크는 본인 데이터만 수정
- admin mutation은 admin_users 기준

### 10.3 Cron 보안

Cron endpoint는 `x-cron-secret` 같은 secret header를 검증해야 한다. 프론트엔드가 공개 대리 호출 경로가 되지 않도록 `/api/trigger-pipeline` 같은 API는 공개 호출 차단과 secret 검증이 필요하다.

### 10.4 CSP

프론트엔드는 CSP nonce 기반으로 inline script를 통제한다. `unsafe-inline` 제거와 nonce 부여는 Phase 3A-SEC에서 중요한 보안 하드닝이었다.

### 10.5 Markdown sanitize

AI가 생성하거나 admin이 편집한 markdown은 공개 페이지에 렌더링된다. 따라서 raw HTML 실행을 허용하면 XSS 위험이 생긴다. 프로젝트는 markdown rendering에서 sanitize 또는 raw HTML 차단을 보안 gate로 둔다.

### 10.6 품질 관리 원칙

품질 관리는 세 층으로 이루어진다.

1. **입력 품질:** source quality gate, dedup, merge
2. **출력 구조:** strict schema, Pydantic validation, citation substitution
3. **콘텐츠 품질:** LLM rubric, code penalty, admin review

이 구조는 AI 시스템에서 중요한 패턴이다.

> 품질을 마지막 평가 단계에서만 잡으려고 하면 늦다. 입력, 생성 계약, 후처리, 평가, 운영 검수를 모두 연결해야 한다.

---

## 11. 배운 점

### 11.1 LLM에게 한 번에 너무 많은 역할을 맡기면 품질이 흔들린다

0to1log에서 반복적으로 검증된 가장 큰 교훈이다. Writer에게 선별, 요약, 번역, 포맷, 퀴즈, citation까지 모두 맡기면 일부가 실패한다. 역할을 분리하면 비용은 약간 늘 수 있지만 품질과 디버깅 가능성이 크게 좋아진다.

### 11.2 좋은 source filtering이 좋은 prompt보다 중요하다

Writer가 아무리 좋아도 입력이 나쁘면 좋은 글이 나오기 어렵다. content farm, mirror, fork, 죽은 URL, off-topic discussion을 먼저 걸러야 한다.

### 11.3 Hallucination은 prompt보다 schema로 막는 편이 강하다

"만들지 마라"는 instruction은 안전장치가 아니다. URL처럼 allowlist가 가능한 값은 schema enum으로 제한하는 것이 더 강하다.

### 11.4 LLM 평가는 가능하지만, 총점 계산은 코드가 해야 한다

LLM은 근거 기반 정성 평가에 강하지만 산술/일관된 aggregation에는 약하다. sub-score와 evidence는 LLM이 만들고, 최종 점수와 감점은 코드가 계산하는 구조가 더 안정적이다.

### 11.5 비용 최적화는 모델 선택보다 pipeline 구조 문제다

비용은 모델 단가뿐 아니라 입력 중복, reasoning token, cache hit, service tier, retry, 실패 호출, 재실행 범위에 의해 결정된다. merge와 rerun_from=quality는 모델 변경보다 더 큰 비용 구조 개선이었다.

### 11.6 QC와 Writer는 함께 바뀌어야 한다

QC rubric만 강화하면 점수는 낮아지지만 Writer behavior는 바뀌지 않는다. QC에서 측정하는 기준을 Writer prompt와 generation contract에도 반영해야 한다.

### 11.7 자동화와 human review는 대립하지 않는다

0to1log는 자동으로 수집하고, 생성하고, 평가하지만 최종 발행 판단은 사람이 한다. 이 구조는 초기 제품에서 특히 중요하다. 자동화는 사람을 제거하는 것이 아니라, 사람이 더 좋은 판단을 하도록 정보를 정리해주는 역할을 한다.

---

## 12. 앞으로의 로드맵

### 12.1 Phase 3 Intelligence

다음 큰 방향은 개인화와 검색 지능이다.

- AI News 개인화 추천
- 최근 읽기 기록 기반 추천
- 북마크와 카테고리 선호 반영
- My Library 재방문 흐름
- Handbook feedback 집계
- Handbook advanced body AI 보강
- 추천 클릭률/feedback 반응률/재방문율 측정

### 12.2 AI Semantic Search

Cmd+K 형태의 semantic search는 0to1log의 중요한 확장 가능성이다. 뉴스, 핸드북, 블로그, 제품 가이드를 하나의 지식 베이스처럼 검색할 수 있다.

기술적으로는 embedding, pgvector 또는 별도 vector DB, query cache, keyword fallback, locale-aware ranking이 필요하다.

### 12.3 AI Ops Dashboard

현재 pipeline_logs와 quality breakdown이 쌓이고 있으므로, 이를 시각화하면 AI Ops Dashboard가 된다.

보여줄 수 있는 지표:

- run당 비용
- 모델별 token 사용량
- reasoning token 비율
- cached token 비율
- quality score trend
- source count
- citation density
- failure stage
- rerun cost
- auto_publish eligible 비율

### 12.4 Handbook 확장

현재 active sprint인 HB-QM의 핵심은 Handbook 품질과 규모 확장이다.

- 기존 published 용어 regeneration
- 800개 seed term
- term type/facet 재설계
- DefinedTerm / FAQPage / BreadcrumbList JSON-LD
- stale model comparison 측정
- advanced section 품질 강화

### 12.5 Monetization / Community / Native App

장기적으로는 다음 확장이 가능하다.

- 광고 또는 구독
- premium content
- quiz / point / prediction game
- PWA
- Expo native app
- push notification
- user webhook subscription

---

## Appendix A. 주요 문서 목록

이 보고서는 다음 로컬 문서와 구현 파일을 근거로 정리했다.

| 경로 | 용도 |
|---|---|
| `README_KR.md` | 프로젝트 소개와 세 기둥 |
| `ARCHITECTURE_KR.md` | 백엔드/파이프라인 구조 |
| `docs/IMPLEMENTATION_PLAN.md` | Phase 흐름과 운영 원칙 |
| `docs/03_Backend_AI_Spec.md` | 백엔드/AI 설계 스펙 |
| `docs/04_Frontend_Spec.md` | 프론트엔드 설계 스펙 |
| `docs/portfolio/pipeline-journey.ko.md` | AI 뉴스 파이프라인 개발 여정 |
| `vault/09-Implementation/plans/ACTIVE_SPRINT.md` | 현재 스프린트 상태 |
| `backend/core/config.py` | 모델/환경 변수 설정 |
| `backend/services/agents/client.py` | OpenAI 호출, gpt-5 compat, cost usage 추적 |
| `backend/services/pipeline_digest.py` | daily digest 생성, persona, citation, quiz 저장 |
| `backend/services/pipeline_quality.py` | quality scoring과 breakdown |
| `backend/services/agents/schemas/news_writer.py` | strict schema 기반 writer output |
| `backend/services/agents/schemas/news_quiz.py` | quiz answer_index schema |

---

## Appendix B. 용어 정리

| 용어 | 설명 |
|---|---|
| **Digest** | 매일 발행되는 AI 뉴스 요약 글 |
| **Research Digest** | 기술/논문/모델 중심 뉴스 |
| **Business Digest** | 제품/시장/기업/투자 중심 뉴스 |
| **Persona** | Expert, Learner, Beginner처럼 독자 수준별 글 버전 |
| **Fact Pack** | Writer에게 전달되는 구조화된 뉴스/출처 입력 |
| **Citation sidecar** | 본문과 분리된 `{n, url}` citation 배열 |
| **Schema enum allowlist** | 허용 URL 목록 안의 값만 출력하도록 강제하는 JSON schema |
| **Rubric v2** | 단일 총점 대신 sub-score와 evidence를 갖는 평가 체계 |
| **Draft-first** | AI 결과를 바로 공개하지 않고 draft로 저장한 뒤 검수하는 운영 원칙 |
| **rerun_from=quality** | Writer를 재실행하지 않고 품질 평가만 다시 실행하는 저비용 경로 |
| **Community Pulse** | HN/Reddit 등 커뮤니티 반응 요약 |
| **Locale Integrity** | EN/KO가 같은 사실, citation, 숫자, 의미를 유지하는지 보는 품질 기준 |

---

## Appendix C. 주요 데이터 모델

### C.1 news_posts

뉴스 콘텐츠의 중심 테이블이다.

주요 필드:

- title
- title_learner
- title_beginner
- slug
- locale
- category
- post_type
- status
- content_expert
- content_learner
- content_beginner
- excerpt
- focus_items
- source_urls
- source_cards
- guide_items
- fact_pack
- quality_score
- pipeline_batch_id
- pipeline_model
- translation_group_id

### C.2 pipeline_logs

파이프라인 실행 관측성을 위한 테이블이다.

주요 필드:

- pipeline_type
- status
- input_summary
- output_summary
- error_message
- duration_ms
- model_used
- tokens_used
- cost_usd
- created_at
- debug_meta

### C.3 handbook_terms

Handbook 용어를 저장한다.

주요 필드:

- term
- slug
- locale
- category
- basic body
- advanced body
- references
- quality score
- status
- term type/facet 관련 필드

### C.4 user tables

사용자 기능을 위한 주요 테이블은 다음과 같다.

- profiles
- user_bookmarks
- reading_history
- learning_progress
- content_feedback
- quiz_responses
- user_webhooks

---

## Appendix D. Gemini Notebook 질문 예시

이 문서를 Gemini Notebook에 넣은 뒤 다음 질문으로 프로젝트를 빠르게 탐색할 수 있다.

1. 0to1log의 핵심 제품 가치를 5문장으로 요약해줘.
2. 이 프로젝트의 AI engineering 포인트를 채용 면접 답변 형식으로 정리해줘.
3. 0to1log의 뉴스 파이프라인을 단계별로 설명해줘.
4. schema enum allowlist가 hallucination을 어떻게 줄였는지 설명해줘.
5. Writer와 Quiz Generator를 분리한 이유를 설명해줘.
6. 이 프로젝트에서 비용 최적화가 어떻게 이루어졌는지 표로 정리해줘.
7. 0to1log에서 가장 중요한 기술적 의사결정 5개를 골라줘.
8. 이 프로젝트를 포트폴리오 README로 줄이면 어떤 구조가 좋을까?
9. 이 프로젝트의 약점이나 앞으로 보완할 점을 비판적으로 정리해줘.
10. Amy가 이 프로젝트를 통해 보여준 역량을 product, frontend, backend, AI engineering, operations로 나누어 정리해줘.

---

## 한 문장 결론

0to1log는 AI 뉴스를 자동으로 쓰는 서비스가 아니라, LLM의 불확실성을 retrieval, schema, evaluation, cost tracking, human review로 감싸 제품 수준의 지식 발행 시스템으로 만든 solo full-stack AI engineering 프로젝트다.
