---
title: Supabase Egress & Public Cache Policy
tags:
  - operations
  - supabase
  - caching
  - cost
date: 2026-08-24
status: approved
---

# Supabase Egress & Public Cache Policy

> 2026-08-24 운영 결정. Supabase Free 조직의 egress 초과로 공개 콘텐츠 조회가 제한된 사고를 계기로, 익명 콘텐츠 캐시와 조회 예산을 명시한다.

---

## Incident Snapshot

- Supabase 조직 egress: `6.00 GB / 5 GB`
- Database size: `233 MB / 500 MB`
- 공개 REST 응답: `exceed_egress_quota`
- 사용자 증상: 뉴스와 Handbook 목록이 빈 화면이 아니라 데이터 로드 오류 상태로 렌더됨
- 데이터 상태: 저장된 기사와 용어가 삭제된 것은 아니며, 조직 서비스가 egress 제한 때문에 요청을 거부한 상태
- 즉시 복구 수단: 다음 billing cycle 초기화 대기 또는 유료 플랜 전환

> [!warning] 초기화는 원인 해결이 아니다
> 결제 주기 초기화는 현재 사용량만 다시 계산한다. 요청 구조를 바꾸지 않으면 같은 주기 안에 제한이 재발할 수 있다.

## Root Cause

### 1. Cache headers existed but responses were not cacheable

`frontend/vercel.json`과 상세 페이지에는 `s-maxage`가 있었지만, 운영 응답은 반복해서 `X-Vercel-Cache: MISS`, `Age: 0`을 반환했다.

`frontend/src/middleware.ts`가 모든 `/ko/`, `/en/` 요청에 `site-locale` 쿠키를 설정하면서 응답마다 `Set-Cookie`가 포함됐다. Vercel CDN은 `Set-Cookie` 응답을 캐시하지 않으므로, 설정된 TTL이 Supabase origin 호출을 줄이지 못했다.

### 2. Viewport prefetch amplified each visit

공용 Navigation의 모든 메뉴 링크가 `data-astro-prefetch="viewport"`를 사용했다. 홈 한 번 접속해도 뉴스, Handbook, Products, Library, Blog 문서가 자동으로 요청됐다. CDN이 MISS인 상태에서는 각 문서가 별도 SSR과 Supabase 조회를 실행했다.

### 3. Public SSR over-fetched database rows and columns

- Home은 뉴스 fallback과 용어 fallback을 포함해 여러 쿼리를 매 요청마다 병렬 실행했다.
- News 목록은 최대 100개 daily + 20개 weekly를 가져오며 `guide_items`까지 포함했다.
- Handbook 목록은 최대 500개 용어의 KO/EN 정의를 함께 가져왔다.
- Products 목록은 최대 200개 카드에 `demo_media`, `search_corpus`를 포함했다.
- News, Handbook, Blog, Products 상세 일부는 `.select('*')`를 사용했다.
- News와 Blog 상세는 인라인 용어 연결을 위해 최대 200개 용어의 양쪽 언어 본문을 가져왔다.

## Approved Direction

1. `viewport` prefetch를 제거하고 Astro의 기본 `hover` 전략만 사용한다.
2. locale 쿠키는 명시적 언어 전환에서만 설정하고, 쿠키 설정 후 query 없는 URL로 redirect한다.
3. 익명 공개 HTML만 CDN에 저장한다. 인증·preview·admin 응답은 `private, no-store`로 유지한다.
4. 초기 안정화에서는 `Vary: Cookie`로 익명과 인증 요청을 분리하고, 사용자별 북마크·읽음 조회는 가능한 범위부터 client hydration으로 옮긴다.
5. 공개 쿼리는 필요한 locale과 화면 필드만 select한다. `.select('*')`를 공개 data loader에서 제거한다.
6. 긴 Handbook 본문을 매 상세 요청마다 가져오지 않고 locale별 compact term index를 재사용한다.
7. 1차 배포 후 7일 사용량을 측정하고, 기준을 넘을 때 public editorial route의 SSG/ISR 전환을 시작한다.

## Cache Contract

| Response | Browser | Vercel CDN | Notes |
|---|---|---|---|
| 익명 목록/Home | `max-age=0` | `s-maxage=300`, SWR 1시간 | 모든 방문자에게 같은 HTML |
| 익명 상세 | `max-age=0` | `s-maxage=3600`, SWR 24시간 | 게시된 글만 대상 |
| 인증 사용자 | `private, no-store` | 저장 금지 | persona/admin 상태 포함 가능 |
| Preview/Admin/API user | `private, no-store` | 저장 금지 | 민감 데이터 경계 |
| upstream 오류 | `no-store` | 저장 금지 | 오류 화면 cache poisoning 방지 |

> [!important] 캐시 안전 조건
> 사용자별 HTML에 `public, s-maxage`를 적용하지 않는다. 공용 캐시를 확대하려면 Navigation, persona 초기 상태, bookmark/read 상태까지 user-neutral HTML + client hydration 구조로 바꿔야 한다.

## Egress Budget

- Free plan 이론상 일 평균 한계: 약 `161 MB/day` (`5 GB / 31일`)
- 운영 목표: `<= 120 MB/day`
- 월간 목표: `3.5-4.0 GB` 이하
- 반복 URL cache 검증: 첫 요청 `MISS`, 두 번째 요청 `HIT`, 이후 `Age > 0`
- 익명 공용 route 표본 cache hit 목표: `>= 90%`

## Escalation Gate

아래 조건 중 하나가 3일 연속 발생하면 2차 정적 전환을 시작한다.

- Supabase 조직 egress가 `120 MB/day`를 초과
- 배포 후 반복 public URL이 계속 `MISS`
- bot/익명 트래픽 증가로 Vercel Function 호출과 Supabase read가 다시 선형 증가
- 다른 프로젝트의 조직 egress 비중이 `20%` 이상인데 분리 또는 중지가 불가능

정적 전환 시 공개 editorial HTML은 build/revalidation 시점에만 Supabase를 읽고, 사용자 상태는 client API로 분리한다. 현재 `/api/revalidate`는 인증 응답만 반환하는 stub이므로 실제 path invalidation 계약을 별도로 구현해야 한다.

## Recovery Runbook

1. Supabase Organization Usage에서 egress를 프로젝트와 제품별로 분해한다.
2. 공개 REST 오류가 `exceed_egress_quota`인지 확인한다.
3. Vercel 응답에서 `Set-Cookie`, `X-Vercel-Cache`, `Age`, `Cache-Control`을 확인한다.
4. 홈 네트워크 로그에서 viewport prefetch로 다른 문서가 자동 호출되는지 확인한다.
5. 제한 해제 후 하루 단위 egress를 7일 기록한다.
6. 기준 초과 시 query payload를 다시 측정하고 정적 전환 gate를 연다.

## External References

- [Supabase Egress](https://supabase.com/docs/guides/platform/manage-your-usage/egress)
- [Supabase Cost Control](https://supabase.com/docs/guides/platform/cost-control)
- [Vercel Cache-Control Headers](https://vercel.com/docs/caching/cache-control-headers)
- [Vercel CDN Cache Criteria](https://vercel.com/docs/caching/cdn-cache)

## Related

- [[Cost-Model-&-Stage-AB]] — 무료 티어와 비용 상향 기준
- [[Infrastructure-Topology]] — Supabase와 Vercel 요청 경계
- [[Monitoring-&-Logging]] — 운영 지표와 관측 방법

## See Also

- [[Frontend-Stack]] — Astro SSR/SSG 경계 (02-Architecture)
- [[Checklists-&-DoD]] — 구현 완료 기준 (09-Implementation)
