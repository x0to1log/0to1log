---
title: Admin Dashboard Stat Card Redesign
date: 2026-03-14
status: approved
tags:
  - admin
  - dashboard
  - ui
---

# Admin Dashboard Redesign

## 목표

- 상단 stat 카드를 "콘텐츠 타입별" 명칭으로 재편 (News / Handbook / Blog)
- AI 운영 비용과 사이트 성과를 별도 zone으로 분리
- Quick Actions에 "Check News" 버튼 추가
- 모든 카드에 관련 페이지 링크 연결

## 변경 전 → 후

### Stat Cards

**Before:** Posts · Published · Terms · Drafts · Users · Likes (6개, 단순 나열)

**After:**

```
Zone A — 콘텐츠 현황 (3 large, 클릭 가능)
  NEWS → /admin/posts/          (totalPosts, news_posts 전체)
  HANDBOOK → /admin/handbook/   (totalTerms, handbook_terms 전체)
  BLOG → /admin/blog/           (totalBlogPosts, blog_posts 전체)

Zone B — AI 운영 비용 (1 wide card, 클릭 → /admin/pipeline-analytics)
  AI COST (이번 달)  $X.XX · XX,XXX tokens

Zone C — 사이트 성과 (3 small)
  DRAFTS (highlight)   USERS   LIKES
```

### Quick Actions

**Before:** `[ New Post ]` `[ New Term ]`
**After:**  `[ Check News → /admin/posts/ ]` `[ New Term ]` `[ New Post ]`

## 데이터 변경

| 변경 | 쿼리 | 비고 |
|---|---|---|
| 추가 | `blog_posts` count (head: true) | 현재 대시보드에 없음 |
| 추가 | `pipeline_logs` cost_usd + tokens_used sum (최근 30일) | pipeline-analytics와 동일 데이터 |
| 제거 | `publishedPosts` 변수 | stat 카드에서 제거 (Published 카드 없어짐) |

## 구현 범위

파일 1개만 변경: `frontend/src/pages/admin/index.astro`

1. Frontmatter 쿼리 추가 (`totalBlogPosts`, `monthlyCost`, `monthlyTokens`)
2. Quick Actions HTML — "Check News" 버튼 추가
3. Stat cards HTML/CSS — Zone A/B/C 구조로 재편
4. 불필요한 `publishedPosts` 제거

## CSS 설계

```
.dashboard-stats-zone-a   /* 3-col grid, 큰 카드 */
.dashboard-stats-zone-b   /* 1 wide card */
.dashboard-stats-zone-c   /* 3-col grid, 작은 카드 */
.dashboard-ai-cost-card   /* Zone B 전용 */
```

## 완료 기준

- [ ] Zone A 카드 3개 — News / Handbook / Blog, 각각 해당 관리 페이지로 링크
- [ ] Zone B 카드 — 이번 달 AI 비용 + 토큰 수, /admin/pipeline-analytics 링크
- [ ] Zone C 카드 — Drafts (highlight) / Users / Likes
- [ ] Quick Actions — Check News / New Term / New Post 3개 버튼
- [ ] 모바일 반응형 유지 (Zone A: 1-col, Zone B: full-width, Zone C: 3-col)
- [ ] npm run build 0 errors

## Related Plans

- [[plans/2026-03-14-admin-dashboard-stat-cards|Stat Cards]]
- [[plans/2026-03-10-admin-dashboard-design|Dashboard 초기 설계]]
