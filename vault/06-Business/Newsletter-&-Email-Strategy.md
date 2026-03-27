---
title: Newsletter & Email Strategy
tags:
  - business
  - newsletter
  - retention
  - webhook
updated: 2026-03-27
---

# Newsletter & Email Strategy

구독자 알림 채널 전략. RSS, 이메일 뉴스레터, Webhook 3가지 채널을 운영 중.

---

## 현재 운영 중인 채널 (2026-03-27 기준)

### 1. RSS 피드 (구현 완료)

- **구현**: `@astrojs/rss` 패키지
- **피드 URL**: `/rss.xml` (전체), `/ko/rss.xml` (한국어)
- **포함 콘텐츠**: AI News 발행 글
- **사이트 노출**: Footer에 RSS 링크, 편지지 모달/뉴스 스트립에 "RSS" 링크
- **비로그인 사용자도 이용 가능**

### 2. 이메일 뉴스레터 (구현 완료)

- **서비스**: Beehiiv (`0to1log Weekly`)
- **구독 폼 위치**:
  - 헤더 편지지 아이콘 클릭 → 편지지 모달 (Navigation.astro)
  - 뉴스 상세 페이지 하단 스트립 (NewsletterSubscribe.astro)
- **구독 해제**: Beehiiv가 이메일 하단에 unsubscribe 링크 자동 포함 (CAN-SPAM/GDPR 준수)
- **비로그인 사용자도 이메일만 입력하면 구독 가능**

### 3. Webhook 알림 (구현 완료)

#### 어드민 Webhook
- **테이블**: `webhooks` (admin RLS)
- **관리**: `/admin/webhooks/`
- **플랫폼**: Discord / Slack / Custom
- **트리거**: 뉴스 발행 시 `fireWebhooks()` 자동 발송
- **Locale 필터**: all / en / ko
- **안전장치**: 24h 이내 발행만 발송 (백필 방지), 연속 5회 실패 시 자동 비활성화
- **테스트**: `/api/admin/webhooks/test` 엔드포인트

#### 유저 셀프서비스 Webhook
- **테이블**: `user_webhooks` (유저 본인 RLS)
- **설계 문서**: [[plans/2026-03-27-user-webhook-subscriptions]]
- **관리 페이지**: `/settings/webhooks/`
- **플랫폼**: Discord / Slack / Custom
- **Locale 필터**: all / en / ko
- **유저당 최대 5개**
- **로그인 필수** (스팸/남용 방지)
- **발송 로직**: `fireWebhooks()`가 admin `webhooks` + `user_webhooks` 동시 조회 후 발송
- **API**:
  - `GET/POST/PUT/DELETE /api/user/webhooks` — CRUD
  - `POST /api/user/webhooks-test` — 테스트 발송

#### Webhook 페이로드 포맷

| 플랫폼 | 포맷 |
|--------|------|
| Discord | embed (title, description, url, color, footer, timestamp) |
| Slack | blocks (section + context) |
| Custom | JSON (event, title, url, excerpt, post_type, locale, timestamp) |

#### Webhook 진입점
- 편지지 모달 하단: "다른 방법으로 받아보기: Webhook · RSS"
- 뉴스 하단 스트립: "다른 방법으로 받아보기: Webhook · RSS"
- "Webhook" 클릭 → `/settings/webhooks/` (미로그인 시 → `/login?redirectTo=...`)

---

## 파일 참조

| 역할 | 파일 |
|------|------|
| RSS 생성 | `frontend/src/pages/rss.xml.ts`, `frontend/src/pages/ko/rss.xml.ts` |
| 편지지 모달 (이메일+진입점) | `frontend/src/components/Navigation.astro` |
| 뉴스 하단 스트립 (이메일+진입점) | `frontend/src/components/NewsletterSubscribe.astro` |
| Webhook 발송 로직 | `frontend/src/lib/webhooks.ts` |
| Admin Webhook 관리 | `frontend/src/pages/admin/webhooks/index.astro` |
| Admin Webhook API | `frontend/src/pages/api/admin/webhooks/*.ts` |
| User Webhook 관리 | `frontend/src/pages/settings/webhooks.astro` |
| User Webhook API | `frontend/src/pages/api/user/webhooks.ts`, `webhooks-test.ts` |
| DB 마이그레이션 (admin) | `supabase/migrations/00043_webhooks.sql` |
| DB 마이그레이션 (user) | `supabase/migrations/00044_user_webhooks.sql` |

---

## Related
- [[Growth-Loop-&-Viral]] — RSS/뉴스레터가 속한 리텐션 루프
- [[Monetization-Roadmap]] — Premium 전환 퍼널과 연결
- [[plans/2026-03-27-user-webhook-subscriptions]] — 유저 Webhook 설계 문서
