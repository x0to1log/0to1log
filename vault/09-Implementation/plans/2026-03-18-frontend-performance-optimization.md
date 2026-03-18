# 프런트엔드 성능 최적화

> 날짜: 2026-03-18
> 상태: done
> 관련: [[Frontend-Architecture]]

---

## 문제

사이트 전반에서 페이지 전환이 느림. 공개 페이지(홈, 뉴스, 용어집)와 어드민 페이지 모두 해당.

## 병목 분석

5가지 축에서 병목 발견:

| 병목 | 영향 범위 | 원인 |
|------|-----------|------|
| 미들웨어 auth 호출 | 모든 페이지 | 매 요청마다 `supabase.auth.getUser()` 네트워크 호출 (~100-200ms) |
| Vercel CDN 캐시 누락 | 홈페이지 | `/(en\|ko)/` 경로에 캐시 헤더 없음 → 매번 full SSR |
| 쿼리 워터폴 | 뉴스 목록, 홈페이지, 대시보드 | 독립적 쿼리들이 순차 실행 (`await A; await B; await C;`) |
| 어드민 과잉 fetch | 어드민 handbook 목록 | body 마크다운 전문(6개 컬럼) 전체 로드, 실제로는 존재 여부만 필요 |
| 프리페치 부재 | 네비게이션 | 주요 링크에 viewport prefetch 미적용 |

---

## 구현 내역

### Phase 1 — Quick Wins

#### 1.1 Navigation viewport prefetch
- **파일:** `Navigation.astro`
- 데스크탑/모바일 nav 링크에 `data-astro-prefetch="viewport"` 추가
- 링크가 화면에 보이는 즉시 prefetch → 클릭 시 캐시 히트

#### 1.2 Vercel CDN 캐시: 홈페이지 추가
- **파일:** `vercel.json`
- `/(en|ko)/` 경로에 `s-maxage=60, stale-while-revalidate=300` 적용
- 기존 콘텐츠 페이지와 동일한 캐시 전략

#### 1.3 어드민 목록 페이지 `.limit(500)` 추가
- **파일:** `admin/handbook/index.astro`, `admin/posts/index.astro`, `admin/blog/index.astro`, `admin/products/index.astro`
- 무제한 fetch 방지 안전 장치

#### 1.4 어드민 Handbook 목록: body 컬럼 제거
- **파일:** `admin/handbook/index.astro`
- SELECT에서 `body_basic_ko/en`, `body_advanced_ko/en` 4개 컬럼 제거
- 완성도 점은 `definition_ko/en` 존재 여부로 변경 (4점 → 2점)
- 용어 수 × 4 body 컬럼(각 2-10KB) = 수백KB~수MB 전송량 절감

#### 1.5 어드민 Handbook 편집: 중복 클라이언트 제거
- **파일:** `admin/handbook/edit/[slug].astro`
- Supabase 클라이언트 2개 생성 → 1개로 통일 (상위 스코프로 이동)

### Phase 2 — 쿼리 병렬화

#### 2.1 뉴스 목록: 3단계 워터폴 → 1단계 병렬
- **파일:** `ko/news/index.astro`, `en/news/index.astro`
- 기존: `[posts ~100ms] → [user data ~100ms] → [site content ~50ms]` = ~250ms
- 변경: `Promise.all([posts, history, bookmarks, siteContent])` = ~100ms
- `authSb`를 조건부 생성 후 null일 때 `Promise.resolve({ data: null })` 사용

#### 2.2 홈페이지: backfill 쿼리 병렬 포함
- **파일:** `homePage.ts`
- 기존: 5개 병렬 → 결과 확인 → 조건부 6번째 순차 쿼리
- 변경: 6개 모두 병렬 실행, 불필요 시 결과 무시 (speculative fetching)
- `is_favourite=false` 조건으로 fallback 쿼리를 초기 배치에 포함

#### 2.3 어드민 대시보드: 워터폴 제거 + count 쿼리 최적화
- **파일:** `admin/index.astro`
- blog_posts 전체 fetch → count 쿼리 2개(`{ count: 'exact', head: true }`)로 교체
- pipeline 상세 쿼리(logs, candidates)를 초기 `Promise.all`에 포함
- `run_id`/`batch_id`로 클라이언트 사이드 필터링
- 9개 쿼리 + 2개 워터폴 → 12개 단일 병렬 배치

### Phase 3 — 미들웨어 최적화

#### 3.1 공개 페이지: 토큰 검증 캐싱 (Zone 3)
- **파일:** `middleware.ts`
- `auth-validated` 쿠키에 토큰 검증 결과 캐시 (2분 TTL)
- 같은 `accessToken` 값이면 `getUser()` 호출 건너뜀
- 토큰 변경(refresh) 시 자동 무효화
- admin/user 보호 라우트는 변경 없음 (매번 검증 유지)

#### 3.2 어드민 라우트: fetchUserExtras 캐시 적용 (Zone 1)
- **파일:** `middleware.ts`
- `fetchUserExtras()` 직접 호출 → `getOrFetchUserExtras()` (기존 5분 캐시 재활용)
- `validateToken()`은 여전히 매 요청 실행 → 인증 보안 유지

### Phase 4 — 마크다운 렌더링 최적화

#### 4.1 렌더 결과 인메모리 캐시
- **파일:** `markdown.ts`
- `Map<contentHash, html>` (최대 150개, FIFO 퇴출)
- `renderMarkdown`, `renderMarkdownWithTerms` 모두 적용
- termsMap fingerprint = slug 목록 해시로 캐시 키 생성
- Vercel warm 상태(~15분) 동안 동일 콘텐츠 재요청 시 전체 파이프라인(9개 플러그인) 스킵 → 렌더링 0ms

#### 4.2 블로그 상세 병렬화
- **파일:** `blogDetailPage.ts`
- terms 쿼리 + termsMap 빌드 + 마크다운 렌더를 하나의 async 체인(renderTrack)으로 묶어 나머지 7개 쿼리와 병렬 실행
- 기존: 8개 쿼리 완료 → termsMap 빌드 → 렌더 (순차)
- 변경: renderTrack(terms + 렌더) ∥ 나머지 7개 쿼리
- 첫 방문(캐시 미스) 시 ~50-150ms 절감

#### 4.3 Shiki 언어 제한
- **파일:** `markdown.ts`
- 332개 bundled 언어 → 24개 주요 언어(JS, TS, Python, Bash 등)로 제한
- 콜드 스타트 시 ~200-400ms 절감. 미지원 언어는 plain text fallback.

### Phase 5 — 어드민 무한 스크롤

#### 5.1 IntersectionObserver 기반 progressive rendering
- **파일:** `admin/handbook/index.astro`, `admin/posts/index.astro`, `admin/blog/index.astro`, `admin/products/index.astro`
- 초기 50개만 표시, 스크롤 시 50개씩 자동 추가 (BATCH_SIZE=50, rootMargin=300px)
- 검색/필터 활성 시 전체 매칭 결과 표시 (lazy limit 무시)
- 탭 전환 시 maxVisible 리셋
- DOM 기반: 서버에서 전부 렌더링하되 JS로 점진적 노출 → 검색/필터 즉시 동작

### Phase 6 — 제품 페이지 최적화

#### 6.1 Vercel CDN 캐시: products 추가
- **파일:** `vercel.json`
- 기존 캐시 규칙에 `products` 추가: `/(en|ko)/(news|blog|handbook|products)/(.*)`
- 60초 edge 캐시 + 5분 stale-while-revalidate

#### 6.2 제품 상세: 순차 쿼리 → 병렬화
- **파일:** `ko/products/[slug].astro`, `en/products/[slug].astro`
- 기존: product(100ms) → alternatives(80ms) → relatedNews(80ms) = ~260ms
- 변경: product 후 `Promise.all([alternatives, relatedNews])` = ~180ms

#### 6.3 fetchRelatedNews locale 버그 수정
- **파일:** `productsPage.ts`
- `.eq('locale', 'en')` 하드코딩 → locale 파라미터 사용

#### 6.4 제품 목록 .limit(200) 안전 장치
- **파일:** `productsPage.ts`

---

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `frontend/src/components/Navigation.astro` | viewport prefetch |
| `frontend/vercel.json` | 홈페이지 + products 캐시 헤더 |
| `frontend/src/middleware.ts` | Zone 3 토큰 캐싱 + Zone 1 extras 캐싱 |
| `frontend/src/pages/ko/news/index.astro` | 쿼리 병렬화 |
| `frontend/src/pages/en/news/index.astro` | 쿼리 병렬화 |
| `frontend/src/lib/pageData/homePage.ts` | backfill 병렬화 |
| `frontend/src/lib/markdown.ts` | 렌더 캐시 + Shiki 언어 제한 |
| `frontend/src/lib/pageData/blogDetailPage.ts` | 렌더 트랙 병렬화 |
| `frontend/src/pages/admin/index.astro` | count 쿼리 + 워터폴 제거 |
| `frontend/src/pages/admin/handbook/index.astro` | body 컬럼 + limit + 무한 스크롤 |
| `frontend/src/pages/admin/posts/index.astro` | limit + 무한 스크롤 |
| `frontend/src/pages/admin/blog/index.astro` | limit + 무한 스크롤 |
| `frontend/src/pages/admin/products/index.astro` | limit + 무한 스크롤 |
| `frontend/src/pages/admin/handbook/edit/[slug].astro` | 중복 클라이언트 제거 |
| `frontend/src/pages/ko/products/[slug].astro` | alternatives + relatedNews 병렬화 |
| `frontend/src/pages/en/products/[slug].astro` | 동일 |
| `frontend/src/lib/pageData/productsPage.ts` | locale 수정 + limit(200) |

---

## 핵심 패턴

### 쿼리 워터폴 → 병렬화
```typescript
// Before: 순차 (합산 ~250ms)
const posts = await fetchPosts();
const history = await fetchHistory();
const sc = await getSiteContents();

// After: 병렬 (최대 ~100ms)
const [posts, history, sc] = await Promise.all([
  fetchPosts(),
  fetchHistory(),
  getSiteContents(),
]);
```

### Speculative fetching
결과가 필요할지 모르는 쿼리를 미리 병렬로 실행. 불필요 시 결과를 버림.
네트워크 왕복 시간 >> 불필요한 작은 쿼리 비용이므로 유리한 트레이드오프.

### Zone별 캐싱 전략
| Zone | 토큰 검증 | Extras 캐시 | 이유 |
|------|-----------|-------------|------|
| Zone 1 (어드민) | 매번 실행 | 5분 캐시 | 인증은 필수, 프로필은 거의 불변 |
| Zone 2 (유저 보호) | 매번 실행 | 5분 캐시 | 기존 유지 |
| Zone 3 (공개) | 2분 캐시 | 5분 캐시 | 읽기 전용, 보안 영향 최소 |

---

## 향후 고려사항

- 어드민 목록 페이지네이션: content 500개 초과 시 서버 사이드 페이지네이션
- Supabase DB 뷰: `handbook_terms_admin_list` 뷰로 body 존재 boolean 반환
- Edge Middleware: JWT 직접 검증으로 Supabase auth 호출 완전 제거
- Streaming SSR: 대시보드 같은 다중 쿼리 페이지에 스트리밍 적용
