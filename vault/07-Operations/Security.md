---
title: Security
tags:
  - operations
  - security
source: docs/05_Infrastructure.md
---

# Security

보안 정책 — CSP, 인증, API 보호, RLS.

인프라 레벨에서 적용하는 보안 설정을 다룬다. 인증 시스템 상세는 백엔드 스펙(`03_Backend_AI_Spec.md` §2)에, 프론트엔드 레벨 방어는 프론트엔드 스펙에 정의되어 있다.

## Content Security Policy (CSP)

Vercel `vercel.json`의 `headers` 섹션(`source: /(.*)`)에서 설정한다.

**CSP 헤더 값:**

```
default-src 'self';
script-src 'self' 'unsafe-inline' googletagmanager.com clarity.ms pagead2.googlesyndication.com;
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self';
connect-src 'self' *.supabase.co *.railway.app google-analytics.com clarity.ms
```

**허용 도메인 (Phase별):**

| Phase | 도메인 | 용도 |
|---|---|---|
| 1b | `googletagmanager.com`, `google-analytics.com`, `clarity.ms` | GA4 + Clarity |
| 2 후반 | `pagead2.googlesyndication.com` | AdSense 신청 시 |
| 4 | Polar 결제 도메인 | 구독 모델 결정 시 |

> [!warning] `unsafe-inline` 리스크
> `script-src 'unsafe-inline'`은 XSS 공격에 취약하다. Astro의 인라인 스크립트(테마 초기화, Clarity 스크립트 등)를 위해 현재 필요하지만, Phase 1부터 인라인 스크립트를 최소화하는 방향으로 개발하고, **Phase 3에서 nonce 기반 CSP로 전환**하여 `unsafe-inline`을 제거한다.

**추가 보안 헤더:**

| 헤더 | 값 |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

## Authentication & Authorization

**Supabase Auth 설정:**

| 설정 | 값 | 이유 |
|---|---|---|
| JWT 만료 시간 | 3600초 (1시간) | Supabase 기본값, 적절한 세션 길이 |
| Refresh Token 순환 | 활성화 | 탈취된 refresh token 재사용 방지 |
| 비밀번호 최소 길이 | 8자 (Admin 계정) | Supabase 기본값 |
| 소셜 로그인 | Google, GitHub | 댓글 사용자용 |
| Redirect URL 화이트리스트 | `https://0to1log.com/**`, `http://localhost:4321/**` | 개발/프로덕션 환경만 허용 |

**Admin 인증:** Supabase Auth + admin role 체크. 백엔드에서 JWT를 검증하고 `user_metadata.role === 'admin'`을 확인한다.

**사용자 인증:** Supabase OAuth (Google, GitHub)를 통한 소셜 로그인. 댓글 작성 시 인증 필수.

**RLS (Row Level Security):**
- 모든 테이블에 RLS 활성화 필수
- Supabase Dashboard에서 수동 확인
- 정책 상세는 백엔드 스펙 참조 → [[Database-Schema-Overview]]

**세션 관리:** JWT 기반. Refresh Token 순환이 활성화되어 탈취된 token의 재사용을 방지한다.

## API Security

**CORS 설정 (FastAPI `CORSMiddleware`):**

| 항목 | 값 |
|---|---|
| `allow_origins` | `https://0to1log.com`, `http://localhost:4321` |
| `allow_methods` | `GET`, `POST`, `PATCH` |
| `allow_headers` | `Authorization`, `Content-Type` |
| `allow_credentials` | `True` |

**CRON_SECRET:** Cron 엔드포인트는 Bearer Token 인증(`CRON_SECRET`)으로 보호된다. Vercel Cron과 Railway 양쪽에 동일한 시크릿을 설정한다. fire-and-forget 패턴으로 202 즉시 반환 후 파이프라인은 백그라운드 실행.

**REVALIDATE_SECRET:** `/api/revalidate` 엔드포인트에 필수. 호출은 server-side only.

**Rate Limiting (FastAPI — slowapi):**

| 엔드포인트 | 제한 | 이유 |
|---|---|---|
| `/api/admin/ai/draft` | 10/분 | Admin AI 기능 |
| `/api/cron/news-pipeline` | 1/시간 | 파이프라인 추가 방어 |
| `/api/search/semantic` (Phase 3) | 30/분 | 사용자 체감 저해 없이 남용 방지 |
| `/api/community/points/earn` (Phase 4) | 10/분 | 치트 방지 |

> Rate Limiting 원칙: 공개 API(검색)는 느슨하게, 상태 변경 API(포인트/퀴즈)는 엄격하게 설정.

**API 키 관리:** OpenAI, Tavily 등 외부 API 키는 서버 사이드에서만 사용. 프론트엔드에 노출하지 않는다.

## XSS & CSRF Protection

**Astro의 빌트인 XSS 방지:** Astro는 기본적으로 HTML 출력을 이스케이프한다. `set:html` 디렉티브 사용 시 주의 필요.

**보안 헤더:** `X-XSS-Protection: 1; mode=block` 및 CSP 헤더로 추가 방어.

**댓글 스팸 방어 (다중 계층):**

| 방어 | 구현 | 시점 |
|---|---|---|
| 프론트엔드 throttle | 30초 작성 간격 + 3회 실패 60초 쿨다운 | Phase 1b |
| RLS rate limiting | 30초 간격 제한 SQL 정책 | Phase 1a |
| DB CHECK 제약 | `char_length(content) <= 2000` | Phase 1a |
| 콘텐츠 필터링 | 스팸 키워드 기본 필터 | Phase 3 (필요 시) |

**RLS 기반 댓글 rate limiting 예시:**

```sql
CREATE POLICY "comments_rate_limit" ON comments
FOR INSERT WITH CHECK (
  auth.uid() IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM comments
    WHERE user_id = auth.uid()
    AND created_at > NOW() - INTERVAL '30 seconds'
  )
);
```

## Secrets Management

> [!important] Secret 노출 금지
> 다음 키는 절대로 프론트엔드나 클라이언트에 노출해서는 안 된다. 서버 사이드 환경 변수로만 관리한다.

**절대 노출 금지 목록:**

- `SUPABASE_SERVICE_ROLE_KEY` — DB 전체 접근 권한, RLS 우회
- `OPENAI_API_KEY` — AI 호출 비용 직결
- `TAVILY_API_KEY` — 검색 API 비용 직결
- `CRON_SECRET` — 파이프라인 트리거 인증
- `REVALIDATE_SECRET` — 캐시 무효화 인증

**환경 변수 분리:**

| 구분 | 예시 | 노출 가능 여부 |
|---|---|---|
| Public (클라이언트) | `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY` | O |
| Private (서버) | `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` | X |

**DB 보안 추가 항목:**

| 항목 | 설정 |
|---|---|
| DB 비밀번호 | Supabase 자동 생성 (노출 불필요) |
| 외부 DB 접속 | 비활성화 (Direct Connection 사용 안 함) |
| pg_graphql | 미사용 시 비활성화 |
| Supabase Storage | 미사용 시 public 버킷 생성하지 않음 |

`.env` 파일은 커밋 금지. `.env.example`만 커밋한다.

## Related

- [[Infrastructure-Topology]] — 보안이 적용되는 인프라
- [[Backend-Stack]] — API 보안 상세 (RLS, admin auth)
- [[Database-Schema-Overview]] — RLS 정책 대상 테이블
- [[Checklists-&-DoD]] — RLS 테스트 시나리오
