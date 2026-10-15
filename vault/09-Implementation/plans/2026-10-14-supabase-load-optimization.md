---
title: Supabase 부하 최적화 (CDN 캐시 복구 + 조회/저장량 감축)
date: 2026-10-14
status: implemented-pending-deploy
tags:
  - operations
  - supabase
  - caching
  - cost
---

# Supabase 부하 최적화

> 2026-09-29~10-13 Supabase 일시정지 재발 방지. 선행 결정: [[Supabase-Egress-&-Public-Cache-Policy]] (2026-08-24 egress 6.00/5 GB 사고).

## 관측 사실 (2026-10-14)

- 운영 `https://0to1log.com` 의 `/ko/`, `/ko/news/`, `/en/handbook/` 를 **쿠키 없이** 연속 2회 요청 → 전부 `X-Vercel-Cache: MISS`, `Age: 0`, `Vary: Cookie`.
- Vercel 문서 (CDN Cache, last_updated 2026-09-14): "Vercel's CDN doesn't cache a response whose `Vary` names ... `Cookie`." → 8/25 커밋 `1a875e6d` 이 넣은 `Vary: Cookie` 때문에 **공개 HTML CDN 캐시가 전혀 작동하지 않음.** 익명·봇 요청 모두 매번 SSR + Supabase 조회.
- 상세 페이지 1회당 쿼리: news ~8, blog ~11, handbook ~9 (+ 클라이언트의 comments 2, likes/status 401 호출).

## DB 크기 실측 (2026-10-14, 읽기 전용 조회)

| 대상 | 크기 |
|---|---|
| DB 전체 | 248 MB / 500 MB |
| `pipeline_checkpoints` | 181 MB (73%), 1,325 rows, 2026-03-31부터 무기한. 월 16–57 MB 증가 |
| `news_posts` | 25 MB (대부분 TOAST = 본문) |
| `pipeline_logs` | 13 MB, `debug_meta` 월 1–4 MB |

→ DB 크기 한도는 이번 일시정지 원인이 아니다. 단 checkpoint 추세면 약 9개월 뒤 500 MB 도달.

## 가설 (검증 안 됨)

- 9월 일시정지는 8월과 같은 **egress 초과**일 가능성이 가장 높다. 근거: 캐시 0% + 8월 사고와 동일 구조 + DB 크기 가설 기각. Vercel의 Vary: Cookie 비캐시 규칙 도입 시점은 미확인 (8/25 배포 당시엔 HIT였을 수도 있음).
- **확정 방법:** Supabase Dashboard → Organization → Usage 의 egress 일별 그래프.

## 작업 목록

### P0 — CDN 캐시 복구 (가장 큰 효과)
1. `publicCachePolicy.ts` 에서 `Vary: Cookie` 제거. 익명 HTML이 CDN에 실제로 저장되게 한다.
2. 로그인 사용자 분리 방식 (결정 필요, 아래 참고).
3. `Vercel-Cache-Tag` 부여 (`news`, `handbook`, `blog`, `products`, `list`) + `/api/revalidate` 를 stub → `invalidateByTag()` 로 실제 구현. 백엔드 publish/admin 저장 시 호출.
4. 캐시 대상 확대: `/rss.xml` (EN), 공개 `GET /api/user/comments` 짧은 s-maxage.
5. 익명 방문자의 `likes/status` 호출 제거 (401만 받는 낭비 함수 호출).

### P1 — DB 크기 (보관 정책)
6. `pipeline_checkpoints` N일 지난 행 삭제 (promote cron 에 붙임).
7. `pipeline_logs.debug_meta` N일 지난 행 NULL 처리.
8. 인덱스 migration: `pipeline_logs(run_id)`, `pipeline_logs(created_at)`, `news_posts(status, locale, published_at desc)`.

### P2 — 요청당 조회량 감축
9. handbook 상세: 양쪽 locale 본문 → 현재 locale(+fallback)만 select. TI await 를 병렬 배치로.
10. blog: sidebar/page 중복 `fetchCategories`·`fetchCategoryGroups` 제거, sidebar posts 무제한 쿼리에 limit.
11. 미사용 `homePage.ts`, `fetchCategoriesWithPostCount` 정리.

## 결정 (2026-10-14, Amy)

- 로그인 사용자 분리: **client hydration**. 공개 HTML은 user-neutral, 개인 상태는 로드 후 `/api/user/*` 로.
- 보관 기간: `pipeline_checkpoints` 14일, `pipeline_logs.debug_meta` 60일.

## 검증

- 배포 후 같은 URL 2회 요청 → 2번째 `HIT`, `Age > 0`.
- 로그인 상태로 상세 페이지 → 개인 상태(북마크/좋아요/nav) 정상.
- 관리자 publish 후 1분 내 공개 페이지 반영.
- 7일간 Supabase egress 일별 기록, 목표 `<= 120 MB/day` (선행 문서 Egress Budget).

## 진행 기록 (2026-10-14)

| 커밋 | 내용 |
|---|---|
| `4a6344be` | backend 테스트 운영 Supabase 격리 (아래 사고) |
| `b254f1b7` | checkpoint 14일 / debug_meta 60일 retention (promote cron) |
| `97704614` | migration `00059_query_path_indexes.sql` (2026-10-15 적용) |
| `74c9c164` | `/api/user/me` + `session.ts` + nav dual-state |
| `7775aed2` | `/en\|ko` 인증 생략·Vary 제거·cache tag 무효화·상세 페이지 hydration |
| `1f798591` | EN RSS 캐시, blog sidebar 병렬화 |

- P2 중 handbook 상세 양쪽 locale select, sitemap 병렬화, blog 카테고리 중복 제거는 보류: 캐시 적용 후엔 miss 때만 비용이 나므로 남은 절감 효과가 작다.
- 알려진 동작 변화: 로그인 사용자의 news 목록 제목은 learner 기준 (상세는 로드 후 저장 persona 로 전환). 발행 전파는 invalidate 직후 첫 요청이 stale 을 받고 백그라운드 갱신.

### 사고: 테스트가 운영 checkpoint 삭제

retention 테스트 작업 중 `routers.cron` 테스트가 patch 없이 실행돼 운영 `pipeline_checkpoints` 1,311건(2026-09-30 이전) 삭제, 2026-08-15 이전 `debug_meta` 비움. 원인: conftest `delenv` 가 Settings 의 `env_file=".env"` 를 막지 못함 → `4a6344be` 로 수정.

## 배포 후 할 일

- [x] Supabase SQL Editor: `00059_query_path_indexes.sql` 적용 (2026-10-15 Amy, 4개 valid 확인)
- [x] Supabase SQL Editor: `VACUUM FULL pipeline_checkpoints;` (2026-10-15: checkpoints 181 MB→2.4 MB, DB 249→70 MB)
- [x] 같은 URL 2회 요청 → 2번째 `X-Vercel-Cache: HIT` (2026-10-14 배포 후 /ko/, /ko/news/, /en/handbook/ 확인)
- [ ] 로그인 상태로 nav/북마크/좋아요/persona 확인
- [ ] Supabase Usage 에서 9월 egress 확인 (가설 검증) + 7일 일별 egress 기록

## 후속: 페이지 무게 (2026-10-15)

- 운영 상세 페이지 838 KB (gzip 268 KB) 중 ~700 KB 가 `handbook-terms-data` (용어 114개 임베드, 본문 참조 8개). `ae1ae91d` 로 본문이 링크한 용어만 임베드 → 로컬 측정 gzip 78 KB.
- `ca04b5ae`: products 카드 대체 로고 `loading="lazy"`, 20 KB 초과 로고 7개를 같은 이름·포맷으로 256px 리사이즈 (363→54 KB).
- 보류: news 목록 페이지네이션. 검색·필터가 렌더된 카드 전체를 클라이언트에서 거르므로 서버 검색 API 가 먼저 필요하고, gzip 50 KB 라 이득이 작다.
