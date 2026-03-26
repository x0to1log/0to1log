# Admin Feedback Page — 설계 문서

> **생성:** 2026-03-18
> **목표:** 어드민에서 사용자 피드백을 확인할 수 있는 통합 피드백 페이지
> **상태:** Phase 1 구현 예정, Phase 2는 추후

---

## 개요

사용자가 콘텐츠(핸드북/뉴스/블로그)와 사이트 전반에 대해 보내는 피드백을 어드민이 한 곳에서 확인할 수 있는 페이지.

---

## Phase 1: 핸드북 피드백 (이번 구현)

### 페이지 구조

- **URL:** `/admin/feedback/`
- **사이드바:** "Feedback" 메뉴 추가 (Handbook과 Blog 사이)
- **레이아웃:** 기존 어드민 리스트 페이지 패턴 준수

### UI 구성

```
[전체]  [핸드북]  [뉴스 (coming soon)]  [블로그 (coming soon)]  [사이트 (coming soon)]
[All (52)]  [Helpful (28)]  [Confusing (14)]                          [Search 🔍]

──────────────────────────────────────────────────────

RAG (Retrieval-Augmented Generation)
✓ helpful · user@email.com · 2026-03-18
"설명이 아주 명확해요!"

MCP (Model Context Protocol)
? confusing · other@email.com · 2026-03-17
"예시가 좀 더 있으면 좋겠어요"

Embedding
✓ helpful · test@email.com · 2026-03-16
(메시지 없음)
```

### 데이터 소스

- `term_feedback` 테이블: reaction, message, created_at, updated_at
- `handbook_terms` JOIN: 용어명(term), slug
- 사용자 이메일: 어드민 전용 API 라우트에서 service role로 `auth.users` 조회

### 기능

- **소스 탭:** 전체 / 핸드북 (활성) / 뉴스·블로그·사이트 (비활성, coming soon 표시)
- **반응 필터:** All / Helpful / Confusing (개수 표시)
- **검색:** 용어명 또는 메시지 텍스트
- **정렬:** updated_at DESC (최신순)
- **용어명 클릭:** 해당 용어 에디터(`/admin/handbook/edit/{slug}`)로 이동
- **표시 정보:** 용어명 + 반응 아이콘 + 사용자 이메일 + 날짜 + 메시지(있으면)

### 필요 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/pages/admin/feedback/index.astro` | 새 파일: 피드백 리스트 페이지 |
| `frontend/src/pages/api/admin/feedback.ts` | 새 파일: 어드민 전용 피드백 API (service role로 user email JOIN) |
| `frontend/src/components/admin/AdminSidebar.astro` | "Feedback" 메뉴 추가 |
| `frontend/src/styles/global.css` | 피드백 리스트 CSS (기존 admin-list 패턴 재활용) |

---

## Phase 2: 확장 (추후)

### 뉴스/블로그 콘텐츠 피드백

- 뉴스 기사, 블로그 포스트에 피드백 버튼 추가
- DB: `term_feedback` 패턴을 따라 `content_feedback` 테이블 생성 또는 기존 테이블 확장 (`item_type` 필드 추가)
- 어드민 페이지: "뉴스"/"블로그" 탭 활성화

### 사이트 일반 피드백

- 사이트 하단 또는 설정에서 버그 리포트 / 기능 제안 폼
- DB: `site_feedback` 별도 테이블 (category: bug/suggestion/other)
- 어드민 페이지: "사이트" 탭 활성화

---

## 참조

- 피드백 Bottom Sheet 구현: `vault/09-Implementation/plans/2026-03-18-feedback-sheet-impl.md`
- DB 스키마: `supabase/migrations/00014_term_feedback.sql` + `00029_term_feedback_message.sql`
- API: `frontend/src/pages/api/user/term-feedback.ts`
