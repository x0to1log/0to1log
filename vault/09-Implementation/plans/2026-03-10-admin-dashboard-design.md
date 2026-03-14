# Admin Dashboard 개선 디자인

## Context
Solo admin이 매일 들어와서 "오늘 할 일 + 파이프라인 상태 + 사이트 건강"을 한 페이지에서 파악할 수 있는 대시보드. 현재 Stats 4칸 + Recent Activity + Stale Drafts만 있어 파이프라인과 사이트 지표가 빠져 있음.

## 레이아웃: 섹션 확장형 (수직 스크롤 한 페이지)

```
1. Header          "Dashboard" + [New Post] [New Term]
2. Stats Grid      6칸 (Posts, Published, Terms, Drafts, Users, Likes)
3. Pipeline Status 마지막 실행 상태 + 비용 + 후보 수
4. Notifications   읽지 않은 알림 (있을 때만 표시)
5. Recent Activity (기존 유지)
6. Stale Drafts    (기존 유지)
```

## Section 상세

### Stats Grid (6칸)

기존 4개(Posts, Published, Terms, Drafts) + 2개 추가:
- **Users**: `profiles` count
- **Likes**: `post_likes` count

Grid: 데스크탑 6col, 태블릿 3col, 모바일 2col.
기존 `.dashboard-stat-card` 스타일 재사용.

### Pipeline Status (새로운)

데이터 소스:
- `pipeline_runs` → 마지막 run (status, started_at, finished_at, last_error)
- `pipeline_logs` → sum(cost_usd), sum(tokens_used) WHERE run_id = last run
- `news_candidates` → 마지막 batch_id의 total / selected count

표시 내용:
- Last run 시간 + status (✓ success / ✗ failed)
- Duration (finished_at - started_at)
- Candidates: N collected → M selected
- Cost: $X.XX · N tokens
- 실패 시 에러 메시지 표시

액션:
- [Run Pipeline] 버튼 → `/api/trigger-pipeline` POST
- (향후) [View Logs →] 링크

스타일: `.dashboard-pipeline` 카드, border-left 색상으로 status 표현 (green=success, red=failed, gray=no data).

### Notifications (새로운)

데이터 소스: `admin_notifications` WHERE is_read = false, ORDER BY created_at DESC, LIMIT 5.

표시: 아이콘 + title + relative time.
액션: "Mark all read" 버튼 → is_read = true로 업데이트.
없으면 섹션 숨김.

### Recent Activity (기존 유지)
변경 없음.

### Stale Drafts (기존 유지)
변경 없음.

## 기술 구현

파일: `frontend/src/pages/admin/index.astro`

데이터 fetching (서버사이드, frontmatter):
```typescript
const [postsRes, termsRes, profilesRes, likesRes, pipelineRes, logsRes, candidatesRes, notifsRes] = await Promise.all([
  sb.from('posts').select('title, slug, status, updated_at'),
  sb.from('handbook_terms').select('term, slug, status, updated_at'),
  sb.from('profiles').select('id', { count: 'exact', head: true }),
  sb.from('post_likes').select('id', { count: 'exact', head: true }),
  sb.from('pipeline_runs').select('*').order('started_at', { ascending: false }).limit(1),
  // pipeline_logs 및 news_candidates는 pipeline run이 있을 때만
  ...
]);
```

CSS: 기존 `<style>` 블록에 `.dashboard-pipeline`, `.dashboard-notification-*` 추가.
JS: "Run Pipeline" 버튼 + "Mark all read" 버튼용 바닐라 JS.

## 검증
`cd frontend && npm run build` — 0 errors
