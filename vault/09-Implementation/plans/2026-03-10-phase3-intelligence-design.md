# Phase 3-Intelligence Design

> **작성일:** 2026-03-10
> **작성자:** Amy (Solo)
> **상태:** Approved
> **참조:** `docs/IMPLEMENTATION_PLAN.md` §Phase 3-Intelligence

---

## 목표

독자 경험 개인화 + 어드민 편집 효율 동시 향상.
임베딩 레이어를 공유 기반으로 두어 중복 개발 없이 양쪽을 커버한다.

---

## Architecture Overview

```
[Post Published]
       ↓
[Embedding Service] → OpenAI text-embedding-3-small
       ↓
[Pinecone Index: news-posts]
  metadata: post_id, locale, category, published_at, slug, title
       ↓
       ├──→ [Reader Recommendations]
       │      - 상세 페이지 하단 "비슷한 글"
       │      - /library "추천 읽기" 탭
       │
       └──→ [Admin Intelligence]
              - Quality Gate (발행 전 자동 품질 검토)
              - Analytics Dashboard (참여도 집계)
              - Topic Suggestion (다음 배치 주제 제안)
```

**핵심 원칙:**
- 임베딩은 한 번 생성 → 독자/어드민 양쪽 재사용
- Pinecone MCP 기연결 → 인덱스 생성만 하면 됨
- 로그아웃 사용자: content-based 추천 (현재 글 기반)
- 로그인 사용자: reading_history + bookmarks 반영한 personalized 추천

---

## Task 1: Embedding Pipeline (기반)

**트리거:**
- 파이프라인 실행 완료 시 자동 (`run_daily_pipeline` 마지막 스텝)
- Admin 수동 발행 시 자동
- 백필: `/cron/embed-backfill` 엔드포인트 (기존 글 일괄)

**임베딩 대상:**
```
title + excerpt + category + tags
```
(content 전체 임베딩 불필요 — title/excerpt가 의미 압축 역할)

**Pinecone 레코드 스키마:**
```
Index: news-posts
Record ID: {post_id}
Vector: [1536 dims] (text-embedding-3-small)
Fields:
  - post_id: string
  - locale: "en" | "ko"
  - category: string
  - published_at: ISO date string
  - slug: string
  - title: string
```

**EN/KO 전략:** 같은 인덱스, locale 필드로 필터 → 추천 시 같은 언어 글만 반환.

**신규 파일:**
- `backend/services/embedding.py` — `embed_post(post)`, `embed_backfill()` 함수
- `backend/routers/cron.py` — `/cron/embed-backfill` 엔드포인트 추가

**기존 파일 수정:**
- `backend/services/pipeline.py` — 파이프라인 마지막 스텝에 embedding 호출

---

## Task 2: Similar Articles (상세 페이지)

**동작:**
- 현재 글 embedding으로 Pinecone similarity search → top 3 반환
- 로그인 사용자: `reading_history`에 있는 글 제외
- 로그아웃: 그냥 top 3 유사 글

**API:** `GET /api/recommendations/similar?post_id={id}&locale={locale}`

**렌더링 위치:** `NewsprintSideRail` — "비슷한 뉴스 더 보기" 섹션 (EN: "More Like This")

> **2026-03-15 변경:** 기존에 같은 파이프라인 배치 기반의 "비슷한 뉴스 더 보기" 섹션이 별도 존재했으나 제거. 벡터 유사도 기반 섹션(이전 명칭 "비슷한 글")이 단일 추천 섹션으로 통합되었으며 제목을 "비슷한 뉴스 더 보기"로 변경. 배치 기반 `recentPosts` 쿼리 및 `posts` prop도 함께 제거됨.

**신규 파일:**
- `backend/routers/recommendations.py` — `/recommendations/similar` 엔드포인트
- `backend/services/embedding.py` — `get_similar_posts()` 구현

**기존 파일 수정:**
- `frontend/src/components/newsprint/NewsprintSideRail.astro` — 섹션 통합, `posts` prop 제거
- `frontend/src/pages/en/news/[slug].astro` — `recentPosts` 제거, `similarPosts` 패스
- `frontend/src/pages/ko/news/[slug].astro` — 동일
- `frontend/src/lib/pageData/newsDetailPage.ts` — 배치 쿼리 제거

---

## Task 3: For-You Recommendations (/library)

**동작:**
- 사용자 최근 읽기 기록 5개 글의 embedding 평균 → Pinecone similarity search
- 북마크한 글 + 이미 읽은 글 제외 → 새로운 글만 추천
- 로그아웃 시: 탭 숨김 또는 로그인 유도 안내

**API:** `GET /api/recommendations/for-you?locale={locale}`

**렌더링 위치:** `/library` 기존 탭(읽은 글 / 저장한 글 / 학습 현황) 옆에 "추천" 탭 추가

**신규 파일:**
- `frontend/src/pages/api/recommendations/for-you.ts`

**기존 파일 수정:**
- `frontend/src/pages/[locale]/library.astro` — 추천 탭 추가

---

## Task 4: Quality Gate

**동작:** 파이프라인 완료 시 각 글에 품질 점수 자동 부여

**체크 항목:**
| 항목 | 기준 |
|------|------|
| content 길이 | ≥ 3000자 |
| guide_items | 4개 필드 모두 존재 |
| related_news | 3카테고리 모두 존재 |
| og_image_url | null이 아님 |

**Admin 글 목록 배지:**
- `✅ Ready` — 모든 항목 통과
- `⚠️ Review` — 1~2개 미달
- `❌ Incomplete` — 3개 이상 미달

**DB 변경:**
```sql
ALTER TABLE news_posts ADD COLUMN quality_score integer DEFAULT NULL;
ALTER TABLE news_posts ADD COLUMN quality_flags jsonb DEFAULT NULL;
```

**기존 파일 수정:**
- `backend/services/pipeline.py` — quality score 계산 스텝 추가
- Admin 글 목록 UI — quality 배지 표시

---

## Task 5: Analytics Dashboard

**표시 데이터:** (모두 기존 DB 필드 활용, 신규 테이블 불필요)
- 글별 likes / bookmarks / reads 카운트
- 카테고리별 평균 참여도
- 최근 7일 / 30일 필터

**API:** `GET /api/admin/analytics` (기존 admin 라우터 확장)

**기존 파일 수정:**
- `backend/routers/admin.py` — analytics 엔드포인트 추가
- Admin 대시보드 UI — analytics 섹션 추가

---

## Task 6: Topic Suggestion

**동작:**
1. 최근 14일 발행 글 카테고리/태그 분석
2. Tavily로 현재 트렌딩 AI 뉴스 검색
3. GPT-4o-mini로 "아직 안 다룬 주제 5개" 제안
4. 어드민이 선택 → 다음 파이프라인 `batch_topic` 힌트로 전달

**API:** `POST /api/admin/suggest-topics`

**기존 파일 수정:**
- `backend/routers/admin.py` — suggest-topics 엔드포인트 추가
- Admin 대시보드 UI — Topic Suggestion 버튼/결과 표시

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `backend/services/embedding.py` | **신규** — embed_post(), embed_backfill() |
| `backend/services/pipeline.py` | embedding + quality score 스텝 추가 |
| `backend/routers/cron.py` | /cron/embed-backfill 추가 |
| `backend/routers/admin.py` | analytics + suggest-topics 엔드포인트 추가 |
| `frontend/src/pages/api/recommendations/similar.ts` | **신규** |
| `frontend/src/pages/api/recommendations/for-you.ts` | **신규** |
| `frontend/src/components/newsprint/NewsprintSideRail.astro` | "추천 글" 섹션 추가 |
| `frontend/src/pages/en/news/[slug].astro` | similar posts 데이터 패스 |
| `frontend/src/pages/ko/news/[slug].astro` | 동일 |
| `frontend/src/pages/[locale]/library.astro` | 추천 탭 추가 |
| Admin 대시보드 UI | quality 배지 + analytics + topic suggestion |

---

## 실행 순서 (의존성)

```
Task 1: Embedding Pipeline  ← 기반, 먼저 완료
  └─ Task 2: Similar Articles (Task 1 완료 후)
  └─ Task 3: For-You Recommendations (Task 1 완료 후, Task 2와 병렬)

Task 4: Quality Gate        ← Task 1과 독립, 병렬 가능
Task 5: Analytics Dashboard ← Task 1~4와 독립, 병렬 가능
Task 6: Topic Suggestion    ← Task 5와 병렬 가능
```

**병렬 가능:** Task 2+3 (Task 1 완료 후), Task 4+5+6 (상호 독립)

---

## Verification

1. `cd backend && .venv/Scripts/python -m ruff check .` — lint 통과
2. `cd frontend && npm run build` — 0 errors
3. 상세 페이지 하단에 "비슷한 글" 3개 렌더링 확인
4. /library 추천 탭에 로그인 사용자 기반 추천 표시 확인
5. Admin 글 목록에 quality 배지 표시 확인
6. Admin 대시보드 analytics 섹션 렌더링 확인
7. Topic Suggestion 버튼 클릭 → AI 제안 5개 표시 확인

## Related Plans

- [[plans/2026-03-10-phase3-intelligence|Phase 3 구현]]
