---
title: KPI Gates & Stages
tags:
  - business
  - kpi
  - metrics
  - aarrr
source: docs/06_Business_Strategy.md
---

# KPI Gates & Stages

단계별 KPI 게이트와 AARRR 측정 체계. 각 Phase의 비즈니스 마일스톤 달성 여부를 판단하는 정량 기준과, 그 기준을 측정하기 위한 AARRR 프레임워크를 정리한다.

## AARRR Framework

0to1log에 적용하는 AARRR 5단계 그로스 지표 (Phase 3에서 대시보드 시각화):

| Stage | 측정 항목 | 데이터 소스 |
|---|---|---|
| **Acquisition (유입)** | 일일 방문자, 트래픽 소스별 비율, 검색 유입 키워드 | GA4 |
| **Activation (활성화)** | 페르소나 설정 완료율, 첫 포스트 끝까지 읽은 비율 (read > 50%) | GA4 + Clarity |
| **Retention (유지)** | 주간 재방문율, 세션 깊이 (2페이지+ 방문 비율) | GA4 |
| **Revenue (매출)** | AdSense 수익, 프리미엄 전환율 (Phase 4+) | AdSense + Polar |
| **Referral (추천)** | SNS 공유 횟수, Highlight to Share 사용률 | 커스텀 이벤트 |

> [!note] Technical 지표 (보조)
> AARRR 외에 **Technical (운영)** 지표도 함께 추적한다: 검색 요청량, 커뮤니티 액션량, API 요청량/오류율 (FastAPI 로그 + Railway + Supabase).

## Measurement Windows

KPI 집계 윈도우 규칙 (v1.4 계약):

| 태그 | 의미 | 용도 |
|---|---|---|
| `[28D]` | 최근 28일 롤링 | ==기본 의사결정 윈도우== |
| `[8W-MA]` | 최근 8주 이동평균 | 프리미엄 구독 검토 시 |
| `[4W-Cohort]` | 4주 코호트 | PWA/유료 유지율 측정 시 |

> [!important] 계약 조건
> 게이트 표/마일스톤 표에는 **반드시** 윈도우 태그를 함께 표기한다.

## KPI Tables per Stage

### KPI 계산 정의

| KPI | 정의 |
|---|---|
| 재방문 사용자 비율 | `returning_users / total_users` |
| 평균 engagement time | GA4 `user_engagement` 기준 평균 참여 시간 |
| 페르소나 전환 사용률 | `persona_switch 이벤트 발생 세션 / 전체 세션` |
| 공유 이벤트율 | `share 이벤트 발생 세션 / 전체 세션` |
| PWA 설치율 | `설치 완료 수 / 설치 프롬프트 노출 세션` |
| 설치자 4주 유지율 | `설치 주차 +4주에도 활성인 설치자 / 설치 주차 설치자` |
| 결제 전환율 | `유료 구독자 수 / paywall 노출 사용자 수` |
| MRR | `해당 월 반복 구독 매출 합` |
| churn rate | `해당 기간 이탈 유료 구독자 수 / 기간 시작 유료 구독자 수` |
| refund rate | `해당 기간 환불 건수 / 해당 기간 결제 건수` |
| paid retention (4주) | `결제 주차 +4주에도 활성인 유료 구독자 / 결제 주차 신규 유료 구독자` |
| 검색 사용량 | `semantic_search 요청 수 / 일` |
| 커뮤니티 액션량 | `points_earn + prediction_join 이벤트 수 / 일` |
| API 요청량 | `전체 FastAPI 요청 수 / 일` |
| Cross-lingual Recall@K | 한국어/영어 쿼리 상호 검색 시 관련 문서 회수율 |
| Locale-aware nDCG@K | locale 우선순위를 반영한 검색 정렬 품질 |
| Language-mismatch bounce | 언어 불일치 결과 클릭 후 즉시 이탈 비율 |

> [!note] 후속 확장
> `ARPU`, `LTV`, `CAC`, `Payback`은 Phase 4 이후 데이터 안정화 시점에 추가한다.

### Stage B 전환 기준 (Go/Hold)

기술 KPI가 비즈니스 KPI와 연결되는 핵심 게이트:

> [!important] Stage A → Stage B 전환 조건 `[28D]`
> ==API 300+/일== + ==검색 80+/일== + ==커뮤니티 40+/일== + ==재방문 25%+==
> **하나라도 미달 시 Hold.**

| 기술 KPI | 비즈니스 해석 | 운영 의사결정 |
|---|---|---|
| 검색 사용량 증가 | 콘텐츠 탐색 니즈 증가, 체류 가능성 상승 | Stage B (Always-on) 전환 검토 |
| 커뮤니티 액션량 증가 | 참여도/충성도 상승 신호 | 포인트/게임 기능 확대 |
| API 요청량 + 재방문율 동반 상승 | 기능 가치가 반복 방문을 유도 | Go 조건 충족 여부 판단 |

### Revenue KPIs

| KPI | 윈도우 | Phase |
|---|---|---|
| MRR | `[28D]` | 4+ |
| churn rate | `[28D]` | 4+ |
| refund rate | `[28D]` | 4+ |
| paid retention (4주) | `[4W-Cohort]` | 4+ |
| 결제 전환율 | `[28D]` | 4+ |

### 다국어 채널 KPI

| 채널 | KPI 묶음 | 해석 |
|---|---|---|
| **KO 채널** | 접근성(진입률), 체류(완독/읽기시간), 재방문율, 공유율 | 정보 비대칭 해소 가치 검증 |
| **EN 채널** | 큐레이션 소비율, 7일/28일 재방문율, 탐색 효율 | 고밀도 큐레이션 가치 검증 |
| **공통** | Cross-lingual Recall@K, Locale-aware nDCG@K, mismatch bounce | 다국어 검색 품질 및 언어 정합성 검증 |

## GA4 & Clarity Setup

### 분석 도구 스택

| 도구 | 설치 시점 | 역할 | 비용 |
|---|---|---|---|
| **Vercel Analytics** | Phase 1 | 페이지 성능, Web Vitals | 무료 (Hobby) |
| **GA4** | Phase 1b | 트래픽 소스, 유저 흐름, 전환 추적 | 무료 |
| **MS Clarity** | Phase 1b | 히트맵, 세션 리플레이, 분노 클릭 감지 | 무료 |

> [!note] Phase 1b 설치 이유
> - 스크립트 한 줄이면 설치 완료 — 기술 부담 거의 없음
> - 데이터는 일찍 쌓기 시작할수록 나중에 의미 있는 분석이 가능
> - Phase 3 AARRR 대시보드에 최소 3~4개월 데이터 필요

### GA4 주요 추적 이벤트

- `page_view` — 페이지 조회
- `user_engagement` — 참여 시간
- `persona_switch` — 페르소나 전환
- `share` — 콘텐츠 공유
- `semantic_search` — 검색 요청

### Clarity 히트맵 포커스

- 뉴스 카드 클릭 영역
- 용어집 탐색 패턴
- 분노 클릭(rage click) 감지 영역
- 스크롤 depth 분석

### 대시보드 구성

- Phase 3 AI Ops Dashboard 내 AARRR 탭으로 통합
- GA4 Reporting API → Supabase 캐싱 → 프론트엔드 차트 렌더링
- 외부 BI 도구(Looker, Metabase) 사용하지 않음 — 자체 대시보드로 충분

### 인프라 CSP 설정

- GA4: `connect-src`에 `https://www.google-analytics.com` 추가
- Clarity: `connect-src`에 `https://www.clarity.ms` 추가
- 상세 CSP → [[Infrastructure-Overview]]

## Phase별 Business Milestones

| Phase | 비즈니스 마일스톤 | 성공 기준 |
|---|---|---|
| **1a** | SEO 기반 설계 (JSON-LD, 사이트맵, 메타 태그) | 첫 포스트부터 구조화 데이터 포함 |
| **1b** | GA4 + MS Clarity 설치 | 데이터 수집 시작 확인 |
| **2 후반** | AdSense 신청 | 콘텐츠 ==30개+== / 오가닉 세션 ==3,000+== / 재방문 사용자 ==20%+== |
| **3** | Stage A → B 전환 결정 | `[28D]` ==API 300+/일== + ==검색 80+/일== + ==커뮤니티 40+/일== + ==재방문 25%+== |
| **3** | AARRR 대시보드 + 바이럴 기능 | 주요 지표 시각화 완료, SNS 공유 기능 라이브 |
| **3** | Cross-lingual KPI 관측 체계 | Recall@K / nDCG@K / mismatch bounce 모니터링 시작 |
| **3** | GEO 전략 적용 | AI 검색 유입 세션 ==300+/월== + 유입 비중 ==10%+== + 인용 노출 ==20건+/월== |
| **4** | 프리미엄 구독 모델 검토 + PWA 배포 | `[8W-MA]` ==WAU 500+== / ==재방문 30%+== / ==페르소나 전환 15%+== |
| **5** | Expo 네이티브 앱 출시 | `[4W-Cohort]` ==PWA 설치율 4%+ 4주 유지== + ==설치자 4주 유지율 25%+== |

## Related
- [[Business-Strategy]] — 상위 비즈니스 전략
- [[Growth-Loop-&-Viral]] — 그로스 루프

## See Also
- [[Phase-Flow]] — Phase별 게이트 (09-Implementation)
