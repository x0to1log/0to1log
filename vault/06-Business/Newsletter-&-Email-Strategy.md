---
title: Newsletter & Email Strategy
tags:
  - business
  - newsletter
  - retention
---

# Newsletter & Email Strategy

리텐션 채널 전략. **RSS를 우선 운영**하고, 이메일 뉴스레터는 Phase 3 이후 데이터를 보고 검토한다.

> [!important] ADR — 왜 뉴스레터보다 RSS를 먼저 하는가
> 1. **발행자 부담 제로** — 글을 발행하면 RSS 피드가 자동 업데이트. 매주 편집/발송하는 수동 작업이 없음
> 2. **타겟 친화** — 개발자/AI 관심층은 이메일보다 RSS 리더(Feedly, Inoreader)를 선호하는 경향
> 3. **구현 비용 최소** — Astro `@astrojs/rss` 플러그인으로 코드 몇 줄이면 완성
> 4. **번아웃 방지** — Solo 프로젝트에서 "매주 반드시 보내야 하는" 의무를 만들지 않음
> 5. **커뮤니티 유입** — GeekNews 등 개발자 커뮤니티에서 RSS 피드를 통해 자동 수집 가능

---

## Phase 2: RSS 피드 (우선)

### RSS란

사이트가 새 글을 올리면 구독자의 RSS 리더에 자동으로 전달되는 표준 포맷. 발행자가 별도로 보내는 게 아니라, **독자가 알아서 가져가는 구조**.

### 구현

- **Astro 내장**: `@astrojs/rss` 패키지 사용
- **피드 URL**: `/rss.xml` (전체) + `/en/rss.xml` + `/ko/rss.xml` (언어별)
- **포함 콘텐츠**: AI News, Blog, Handbook 신규 항목
- **메타**: 제목, 요약(description), 발행일, 카테고리, 링크

### 사이트 노출

- Header/Footer에 RSS 아이콘 + 링크
- `<link rel="alternate" type="application/rss+xml">` 메타 태그 (자동 감지용)

### 기대 효과

| 효과 | 설명 |
|---|---|
| 개발자 커뮤니티 유입 | GeekNews, Hacker News 등에서 RSS 기반 자동 수집 |
| 재방문율 상승 | RSS 구독자는 새 글마다 자동 알림 → 꾸준한 재방문 |
| SEO 보조 | RSS 피드가 검색 엔진 크롤링 가속화 |

---

## Phase 3+: 이메일 뉴스레터 검토

> [!note] 검토 조건
> 아래 조건이 충족되면 이메일 뉴스레터 도입을 **검토**한다. 조건 미달 시 RSS만으로 운영.

### Go Gate `[28D]`

- 재방문율이 목표(25%) 대비 ==정체 또는 하락== 추세
- RSS 구독자만으로는 리텐션이 부족하다는 데이터 근거
- 또는 Premium 구독 퍼널에서 이메일이 필요한 상황 (Phase 4)

### 도입 시 서비스 후보

| 서비스 | 무료 한도 | 특징 |
|---|---|---|
| **Buttondown** | 100명 | 개발자 친화, 마크다운 지원, API 제공 |
| **Resend** | 100통/일 | API 중심, React Email 템플릿 |

### 도입 시 콘텐츠 구조

주간 AI 다이제스트:
1. 이번 주 Top 3 AI 뉴스 (제목 + 2줄 요약 + 링크)
2. 새로 추가된 핸드북 용어 1~2개
3. 주목할 AI 도구 1개 (AI Products에서 선정)

### 도입 시 측정 지표

| 지표 | 목표 |
|---|---|
| Open rate | 40%+ |
| Click rate | 8%+ |
| Unsubscribe rate | <1% |

---

## Phase별 Scope 요약

| Phase | 채널 | 활동 |
|---|---|---|
| **Phase 2** | **RSS** | `@astrojs/rss` 구현, 피드 URL 설정, 사이트 노출 |
| **Phase 3** | RSS + 뉴스레터 **검토** | 리텐션 데이터 기반 도입 여부 판단 |
| **Phase 4** | RSS + 뉴스레터 (필요 시) | Premium 전환 퍼널 연동 |

## Related
- [[Growth-Loop-&-Viral]] — RSS/뉴스레터가 속한 리텐션 루프
- [[Monetization-Roadmap]] — Premium 전환 퍼널과 연결

## See Also
- [[Content-Strategy]] — 피드 콘텐츠의 원천 (05-Content)
