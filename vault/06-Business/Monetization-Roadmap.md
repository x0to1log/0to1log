---
title: Monetization Roadmap
tags:
  - business
  - monetization
  - revenue
source: docs/06_Business_Strategy.md
---

# Monetization Roadmap

단계적 수익화 계획. ==무료 → 광고 → 프리미엄 구독== 순서로 진행한다. Solo 프로젝트의 리스크를 최소화하기 위해, 비용 제로인 SEO/바이럴로 트래픽을 먼저 확보하고, 트래픽이 증명된 후에야 수익화를 시작한다.

## Revenue Model Overview

```
Phase 1~2          Phase 2 후반~3 초반     Phase 3 중반~        Phase 3~4            Phase 5
──────────         ──────────────         ──────────          ──────────           ──────────
트래픽 축적    →    AI Products        →   AdSense 검토   →   프리미엄 구독 검토  →   인앱 결제
(SEO + 바이럴)      Affiliate 시작         (트래픽 검증 후)     (콘텐츠 계층화)        (Polar)
                   (첫 번째 수익원)
```

> [!important] ADR — 왜 이 순서인가
> Solo 프로젝트에서 수익 전에 비용을 쓰면(유료 광고, 네이티브 앱 개발) 리스크가 크다. 비용 제로인 SEO/바이럴로 트래픽을 먼저 확보하고, 트래픽이 증명된 후 수익화를 시작한다.

| Phase | 수익 모델 | 핵심 활동 |
|---|---|---|
| Phase 1~2 | 없음 (신뢰 구축) | SEO + 바이럴로 오가닉 트래픽 축적 |
| Phase 2 후반~3 초반 | **AI Products Affiliate** | 제휴 링크를 통한 첫 수익원 확보 |
| Phase 3 중반 | AdSense (디스플레이 광고) | 트래픽 검증 후 추가 수익 채널 |
| Phase 3~4 | 프리미엄 구독 (Polar) | 콘텐츠 계층화, paywall 도입 |
| Phase 5 | 네이티브 앱 인앱 결제 | PWA 검증 후 네이티브 전환 |

## Phase별 Revenue Details

### Phase 1~2 — 트래픽 축적 (No Revenue)

- 수익원: 없음
- 목표: 콘텐츠 30개 이상 축적, 오가닉 세션 ==3,000+==, 재방문 사용자 비율 ==20%+==
- 핵심 메트릭: 일일 방문자, 트래픽 소스별 비율, 평균 engagement time

### Phase 2 후반~3 초반 — AI Products Affiliate (첫 번째 수익원)

- 수익원: AI 제품 제휴 링크 (가입/구독 전환 시 커미션)
- 예상 수익: 전환당 ==$5~$50==, 초기 월 수만 원~수십만 원
- 핵심 메트릭: AI Products 페이지 방문 수, 제품 클릭률, affiliate 전환율

> [!note] ADR — 왜 AdSense보다 Affiliate을 먼저 하는가
> 1. 개발자/AI 도구 타겟은 디스플레이 광고 CPM이 낮지만, 도구 추천 → 가입 전환 가치가 높다
> 2. 에디토리얼 큐레이션과 자연스럽게 결합됨 — 광고가 아닌 "추천"으로 느껴짐
> 3. 초기 트래픽이 적어도 전환 단가가 높아 수익이 발생할 수 있음
> 4. AdSense는 디스플레이 배너로 사용자 경험을 해칠 수 있어, 신뢰 구축 후로 미룸

**Affiliate 구조:**

```
AI Products 페이지 → 제품 카드 ("사이트 방문" CTA)
→ affiliate_url이 있는 제품은 제휴 링크로 연결
→ 가입/구독 발생 시 커미션 수취
```

**DB 연결:**
- `ai_products.affiliate_url` — 제휴 링크 (NULL이면 일반 url 사용)
- `ai_products.is_sponsored` — Sponsored 라벨 표시 여부
- 고지 의무: [[Legal-&-Compliance]] 참조

**초기 Affiliate 후보:**
- AI 코딩 도구: Cursor, GitHub Copilot
- AI 어시스턴트: Claude, ChatGPT Plus
- AI 이미지/영상: Midjourney, ElevenLabs
- AI 워크플로우: n8n, Make

### Phase 3 중반 — AdSense

- 수익원: Google AdSense (디스플레이 광고)
- 전제: 트래픽이 충분히 검증된 후 추가 수익 채널로 도입
- 예상 수익: ==월 수만 원 수준== (Solo 블로그 현실적 한계)
- 핵심 메트릭: 오가닉 세션, engagement time, 재방문율

### Phase 3~4 — 프리미엄 구독

- 수익원: Polar 기반 구독 모델
- 예상 수익: 웨이트리스트 규모 및 전환율에 따라 변동
- 핵심 메트릭: WAU, 페르소나 전환 사용률, 결제 전환율, MRR

### Phase 5 — 네이티브 앱

- 수익원: 인앱 결제 (Polar 연동)
- 전제: PWA 설치율 ==4%+== (4주 연속) + 설치자 4주 유지율 ==25%+==
- 핵심 메트릭: PWA 설치율, 푸시 opt-in, 설치자 유지율

## AI Products Affiliate Strategy

**시작 조건 (Go Gate `[28D]`):**

- AI Products에 등록된 제품 ==20개+==
- AI Products 페이지 최근 28일 방문 ==500+==
- 제품 상세 페이지 클릭률 ==15%+==
- 최소 3개 이상 제품에 affiliate 프로그램 가입 완료
- [[Legal-&-Compliance]] Affiliate 고지 구현 완료

## AdSense Strategy

> [!note] Phase 3 중반 이후 도입
> Affiliate이 첫 번째 수익원이며, AdSense는 트래픽 검증 후 추가 채널로 도입한다. 초기에 디스플레이 광고를 붙이면 사용자 이탈을 유발할 수 있다.

**시작 조건 (Go Gate `[28D]`):**

- 게시글 ==30개== 이상 축적
- 최근 28일 오가닉 세션 ==3,000+==
- 평균 engagement time ==90초+==
- 재방문 사용자 비율 ==20%+==

**배치 원칙:**

- 콘텐츠 하단 또는 사이드바 배치 — 읽기 경험을 해치지 않는 위치
- Content-first: 광고가 본문 콘텐츠보다 눈에 먼저 들어오면 안 됨
- CSP 설정 필요 → `05_Infrastructure.md`에서 관리

> [!note] 현실적 기대치
> 0to1log의 타겟(개발자/AI 관심층)은 일반 디스플레이 광고 CPM이 낮은 편이다. 이 단계의 주 목적은 **수익 극대화가 아니라 수익화 경험 확보**다.

**Phase 3~4 대안 검토:**

- 스폰서 콘텐츠 / 뉴스레터 광고: 개발자 대상 CPM이 AdSense보다 높음
- 트래픽과 브랜드 인지도가 충분히 쌓인 후 고려

## Premium Subscription (Polar)

> [!important] ADR — 왜 Phase 4까지 미루는가
> 신뢰 없이 유료화하면 이탈만 가속된다. 무료 콘텐츠로 6개월 이상 운영하며 "이 블로그의 분석은 다르다"는 평가를 먼저 확보한다.

### Free vs Premium 콘텐츠 계층

| 계층 | 접근 범위 | 대상 |
|---|---|---|
| **무료** | Research 포스트 전체 + Business 포스트 (입문자/학습자 버전) | 모든 방문자 |
| **프리미엄** | Business 포스트 Expert 버전 + 심층 분석 + 아카이브 검색 | 구독자 |

### 전제 조건 (Go Gate `[8W-MA]` / `[28D]`)

- 최근 8주 이동평균 WAU ==500+==
- 재방문 사용자 비율 ==30%+==
- 페르소나 전환 사용률 ==15%+==
- 공유 이벤트율 ==1%+== (세션 기준)
- 웨이트리스트 ==100명+==
- paywall 대상 글 완독률 ==35%+==
- 결제 전환율 ==2%+==

### 결제 연동: Polar

- Stripe 대비 셋업이 간단하고, 개인 개발자에게 친화적
- 구독 모델 확정 시 연동 (Phase 4 후반 ~ Phase 5)
- Supabase RLS 정책 변경 필요: 구독 상태에 따른 콘텐츠 접근 제어

### Conversion Funnel

```
무료 콘텐츠 소비 → 신뢰 형성 → Expert 콘텐츠 맛보기
→ paywall 노출 → 웨이트리스트 등록 → 구독 전환
```

## Revenue KPIs

수익 관련 핵심 KPI 정의:

| KPI | 정의 | 집계 윈도우 |
|---|---|---|
| **MRR** | 해당 월 반복 구독 매출 합 | 월간 |
| **churn rate** | 해당 기간 이탈 유료 구독자 수 / 기간 시작 유료 구독자 수 | `[28D]` |
| **refund rate** | 해당 기간 환불 건수 / 해당 기간 결제 건수 | `[28D]` |
| **paid retention (4주)** | 결제 주차 +4주에도 활성인 유료 구독자 / 결제 주차 신규 유료 구독자 | `[4W-Cohort]` |
| **결제 전환율** | 유료 구독자 수 / paywall 노출 사용자 수 | `[28D]` |

> [!note] 후속 확장 KPI
> `ARPU`, `LTV`, `CAC`, `Payback`은 Phase 4 이후 데이터 안정화 시점에 추가한다.

### 정량 게이트 (Go / Hold) 요약

| 의사결정 | Go 조건 | Hold 조건 |
|---|---|---|
| **AI Products Affiliate 시작** `[28D]` | 등록 제품 20+ / AI Products 방문 500+ / 클릭률 15%+ / affiliate 고지 구현 완료 | 미달 |
| **AdSense 신청** `[28D]` | 게시글 30+ / 오가닉 세션 3,000+ / engagement time 90초+ / 재방문 20%+ | 미달 |
| **프리미엄 검토 시작** `[8W-MA]` | WAU 500+ / 재방문 30%+ / 페르소나 전환 15%+ | 미달 |
| **프리미엄 출시** `[28D]` | 웨이트리스트 100+ / paywall 완독률 35%+ / 결제 전환율 2%+ | 미달 |
| **네이티브 앱 진입** `[4W-Cohort]` | PWA 설치율 4%+ (4주 연속) / 설치자 4주 유지율 25%+ / 푸시 opt-in 35%+ | 미달 |

### 인프라 비용 연결 (Stage A → B)

| 단계 | 운영 모드 | 전환 조건 `[28D]` |
|---|---|---|
| **Stage A** (현재) | 범용 API + 저비용 | API < 300/일 또는 검색 < 80/일 또는 커뮤니티 < 40/일 또는 재방문 < 25% |
| **Stage B** (Always-on) | 상시 API 운영 | API 300+/일 + 검색 80+/일 + 커뮤니티 40+/일 + 재방문 25%+ (==4개 모두 충족==) |

> [!important] 원칙
> 비용 상향은 "기술 선투자"가 아니라 ==KPI 달성 이후 "수요 확인된 증설"==로 진행한다.

## Related
- [[Business-Strategy]] — 상위 비즈니스 전략
- [[KPI-Gates-&-Stages]] — 수익화 KPI
- [[Legal-&-Compliance]] — Affiliate 고지, AdSense 승인 요건
