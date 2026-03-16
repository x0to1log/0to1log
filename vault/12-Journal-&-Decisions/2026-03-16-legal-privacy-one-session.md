---
title: "Legal & Privacy 한 세션에 끝내기 — 브레인스토밍부터 배포까지"
tags:
  - retro
  - process
  - legal
  - privacy
  - workflow
  - brainstorming
date: 2026-03-16
---

# Legal & Privacy 한 세션에 끝내기

## 무슨 일이 있었나

Legal & Privacy 기능 전체 — vault 문서 정리, 설계 스펙 작성, 스펙 리뷰, 구현 계획, 코드 구현, 배포 확인 — 를 단 한 세션 안에 완료했다.

보통 이런 흐름은 여러 세션에 걸쳐 진행된다. "vault 정리 → 다음 세션에 설계 → 그 다음 세션에 구현" 식으로 끊기기 쉽다. 오늘은 그렇지 않았다.

---

## 세션 흐름 요약

### 1단계 — 브레인스토밍

브레인스토밍 스킬로 시작했다. vault를 훑어보고 기존 [[Legal-&-Compliance]] 문서 상태를 확인한 후 5개의 명확화 질문을 던졌다.

- Privacy / Terms / Cookie / Affiliate / Copyright 페이지를 각각 별도 파일로 분리할 것인가?
- 쿠키 동의 배너는 어느 레이어에 구현할 것인가?
- Analytics (GA4, Clarity) 동의 게이팅을 어떻게 처리할 것인가?
- Footer 링크는 i18n 지원이 필요한가?
- canonical URL slug 구조는?

이 질문들에 답하는 과정에서 작업 범위가 명확해졌다. "뭘 만들어야 하는지"가 흐릿한 상태에서 바로 코드를 짜는 대신, 경계를 먼저 그었다.

### 2단계 — Vault 정리

기존 [[Legal-&-Compliance]] 문서 하나가 5개 정책 내용을 전부 담고 있었다. 이를 `vault/07-Operations/legal/` 아래 5개 원자적 노트로 분리했다:

- `Privacy-Policy.md`
- `Terms-of-Service.md`
- `Cookie-Policy.md`
- `Affiliate-Disclosure.md`
- `Copyright-Notice.md`

허브 문서([[Legal-&-Compliance]])는 개요 + AdSense 체크리스트 + Phase 범위로 리팩터링했다. 각 정책 문서의 내용을 중복하지 않고 링크로만 연결했다.

### 3단계 — 설계 스펙 작성

`vault/09-Implementation/plans/2026-03-16-legal-privacy-design.md`를 작성했다. 다룬 내용:

- 4개 법적 페이지 라우팅 (`/legal/privacy`, `/legal/terms`, `/legal/cookies`, `/legal/affiliate`)
- Footer 링크 구조 (EN/KO i18n)
- CookieConsent 배너 컴포넌트 설계
- Analytics 동의 게이팅: 동의 전까지 GA4·Clarity 스크립트 로드 차단

### 4단계 — 스펙 리뷰

스펙을 직접 검토하면서 4개의 치명적 문제를 발견했다.

| # | 문제 | 발견 경위 |
|---|------|-----------|
| 1 | `prerender = true` — 코드베이스 전체가 `prerender = false` 컨벤션 | 기존 페이지 파일 확인 |
| 2 | `analytics.ts`는 데드 코드 — 실제 스크립트는 `MainLayout.astro` 인라인에 있었음 | vault grep |
| 3 | Instant-load 메커니즘 미명세 — `data-ga-id`, `data-clarity-id` 속성 전달 방식 누락 | 구현 시뮬레이션 |
| 4 | `slug` prop 누락 — canonical URL 생성에 필요 | 기존 컴포넌트 패턴 확인 |

스펙 리뷰를 구현 전에 했기 때문에, 이 문제들이 코드 수준에서 버그로 나타나기 전에 잡혔다.

### 5단계 — 구현 계획

8개 태스크로 분해한 구현 계획을 작성했다. 각 태스크마다 완성된 코드 스니펫을 명세했다.

계획 리뷰에서 3개 추가 문제를 발견했다:

1. `altSlug`가 잘못된 URL 생성 (로케일 prefix 중복)
2. `addEventListener` 누적 — 페이지 전환 시 이벤트 리스너가 쌓이는 구조
3. Analytics 초기화 중복 가드 누락

이것도 코드를 치기 전에 잡았다.

### 6단계 — 구현

5개 커밋으로 완료:

1. `feat(i18n): add legal page translations + Footer legal links (EN/KO)`
2. `feat(legal): add 4 legal pages (/privacy, /terms, /cookies, /affiliate)`
3. `feat(legal): add CookieConsent banner component`
4. `feat(legal): wire analytics consent-gating in MainLayout`
5. `chore(legal): delete dead analytics.ts`

### 7단계 — 최종 스펙 준수 검토

9개 체크포인트를 모두 통과했다. 배포 확인 완료.

---

## 왜 한 세션에 됐나

### 브레인스토밍이 탐색 비용을 앞으로 당겼다

보통 "설계 → 구현 도중 문제 발견 → 다시 설계 → 재구현" 사이클로 시간이 늘어난다. 오늘은 브레인스토밍 단계에서 vault 전체를 훑고, 기존 컨벤션을 확인하고, 모호한 부분을 명확화 질문으로 해소했다.

탐색 비용이 세션 초반에 집중됐기 때문에, 구현 단계에서 뜻밖의 차단 요소가 나타나지 않았다.

### 스펙 리뷰와 계획 리뷰를 따로 했다

스펙을 짜고 바로 구현하지 않았다. 스펙을 리뷰하고, 계획을 짜고, 계획을 다시 리뷰했다. 총 7개 문제를 코드 레벨이 아닌 문서 레벨에서 발견했다.

문서 수정 비용 < 코드 수정 비용이다. 당연하지만 실제로 지키기 어려운 원칙이다.

### Vault가 진실의 근원이었다

`analytics.ts`가 데드 코드라는 사실을 어떻게 알았는가? vault grep으로 `MainLayout.astro`에 인라인 스크립트가 있다는 걸 확인했기 때문이다. vault에 컴포넌트 구조가 문서화되어 있었기 때문에 실제 파일을 일일이 열어보지 않아도 됐다.

vault를 최신 상태로 유지하는 것이 이렇게 직접적인 형태로 개발 속도에 영향을 준다는 걸 다시 확인했다.

---

## 숫자로 보기

| 항목 | 수 |
|------|----|
| Vault 문서 분리 | 5개 신규 노트 |
| 스펙 리뷰에서 발견한 문제 | 4개 |
| 계획 리뷰에서 발견한 문제 | 3개 |
| 구현 커밋 | 5개 |
| 최종 스펙 준수 체크포인트 | 9/9 통과 |
| 세션 수 | **1** |

---

## 교훈

**구조화된 브레인스토밍은 탐색 비용을 세션 앞쪽으로 당긴다.**

탐색이 앞에 집중되면 구현이 직선으로 진행된다. 구현 도중 방향 전환이 없으면 한 세션에 훨씬 많은 것을 완료할 수 있다.

반대로, 탐색을 생략하고 바로 구현에 들어가면 구현 도중 차단 요소를 만날 때마다 컨텍스트를 전환해야 한다. 세션이 길어지거나 다음 세션으로 넘어간다.

솔로 프로젝트에서 "빠르게 코딩"하는 것보다 "올바른 순서로 진행하는 것"이 실제 속도에 더 직접적인 영향을 준다.

---

## 관련 문서

- [[Legal-&-Compliance]] — 허브 문서 (리팩터링됨)
- [[Phase-Flow]] — 현재 Phase 범위
- [[2026-03-16-products-redesign-design]] — 같은 날 병렬 진행된 다른 스프린트
