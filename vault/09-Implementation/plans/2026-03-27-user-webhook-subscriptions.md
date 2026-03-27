# User Webhook Subscriptions

**Date**: 2026-03-27
**Status**: Design approved

## Summary

일반 로그인 유저가 Discord/Slack/커스텀 webhook을 직접 등록하여 뉴스 발행 알림을 받을 수 있는 셀프서비스 시스템.

## Requirements

- 로그인 사용자만 이용 가능
- Discord / Slack / Custom 3가지 플랫폼 지원
- locale 필터 선택 가능 (all / en / ko)
- 유저당 최대 5개 webhook
- 여러 개 등록 가능 (같은 플랫폼도 복수 가능)
- 기존 어드민 webhook과 동일한 페이로드 포맷 재사용

## Architecture

### DB: `user_webhooks` 테이블

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | gen_random_uuid() |
| user_id | UUID FK → auth.users ON DELETE CASCADE | 소유자 |
| label | TEXT NOT NULL | 사용자 지정 이름 |
| url | TEXT NOT NULL | HTTPS webhook URL |
| platform | TEXT NOT NULL | CHECK: discord, slack, custom |
| locale | TEXT NOT NULL DEFAULT 'all' | CHECK: all, en, ko |
| is_active | BOOLEAN NOT NULL DEFAULT true | |
| fail_count | INTEGER NOT NULL DEFAULT 0 | |
| last_error | TEXT | |
| last_fired_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

RLS policies:
- SELECT: `auth.uid() = user_id`
- INSERT: `auth.uid() = user_id` + 유저당 5개 상한 체크
- UPDATE: `auth.uid() = user_id`
- DELETE: `auth.uid() = user_id`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/webhooks` | GET | 내 webhook 목록 |
| `/api/user/webhooks` | POST | 생성 (5개 상한 체크) |
| `/api/user/webhooks` | PUT | 수정 (본인 소유 확인) |
| `/api/user/webhooks` | DELETE | 삭제 (본인 소유 확인) |
| `/api/user/webhooks/test` | POST | 테스트 발송 |

Validation:
- URL은 `https://`로 시작
- platform은 discord/slack/custom 중 하나
- locale은 all/en/ko 중 하나
- label 필수

### Firing Logic

기존 `frontend/src/lib/webhooks.ts`의 `fireWebhooks()` 확장:
- 기존 어드민 `webhooks` 테이블 조회 후
- `user_webhooks` 테이블도 조회 (is_active = true, locale 필터)
- 동일한 `formatDiscordPayload` / `formatSlackPayload` / `formatCustomPayload` 재사용
- 실패 시 동일 로직: fail_count 증가, 5회 연속 실패 시 자동 비활성화

### Page: `/settings/webhooks/`

- 로그인 필수 (미로그인 → `/login?redirectTo=/settings/webhooks/`)
- 상단: webhook 목록 (카드 형태)
  - 각 카드: 라벨, 플랫폼 아이콘, locale 뱃지, 상태, 마지막 발송 시간
  - 액션: 편집 / 삭제 / 테스트 / 활성화 토글
- 하단: 추가 폼
  - 라벨 (text input)
  - 플랫폼 (select: Discord / Slack / Custom)
  - 언어 (select: 전체 / English / 한국어)
  - Webhook URL (text input, https:// 필수)
- 플랫폼별 간단 가이드 (Discord: 서버 설정 → 연동 → 웹후크 URL 복사)

### Entry Points

- 편지지 모달 (Navigation.astro) "Webhook" 링크 → `/settings/webhooks/`
- 뉴스 하단 스트립 (NewsletterSubscribe.astro) "Webhook" 링크 → `/settings/webhooks/`
- 미로그인 클릭 시 → `/login?redirectTo=/settings/webhooks/`

## Non-goals

- 비로그인 사용자 webhook (보안/남용 이유로 제외)
- 이메일 알림 (beehiiv로 별도 운영 중)
- post_type 필터 (locale 필터만 제공, 향후 확장 가능)
