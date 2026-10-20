# Quiz Partial Health — 발행 글 퀴즈 누락 표시

> 상위: [[2026-10-20-daily-run-recovery]] 와 같은 파이프라인 점검 후속 (QUIZ-PARTIAL-01)
> 상태: 구현 (2026-10-20)

**Goal:** 퀴즈 일부가 빠진 채 발행된 daily 글을 어드민 대시보드 Pipeline Status 카드에 경고로 보여준다.

## 배경

- 10-18 business KO: expert 퀴즈가 답 검증을 3회 통과하지 못해 제외됨 → 퀴즈 5/6개로 발행.
- 로그(`digest:business:quiz`)에는 `failed`로 남지만, 글은 정상 발행이라 놓치기 쉬움.

## 설계

- **기준은 로그가 아니라 발행된 글.** `news_posts.guide_items.quiz_poll_{expert,learner,beginner}`를 직접 확인 → 어드민이 퀴즈를 다시 만들면(Rerun from quiz) 경고도 사라짐.
- 쿼리: 최근 7일 published, `post_type in (research, business)`. 본문은 가져오지 않고 `guide_items->quiz_poll_{persona}->>question`만 선택 (egress 최소, [[2026-10-14-supabase-load-optimization]]).
- 판정: 질문 문자열이 비어 있는 persona = 누락. 3 persona 모두 기대 (beginner 도입 이후 글만 7일 창에 들어옴).
- 표시: `summarizePipelineHealth(..., { quizPosts })` → `warning` / `daily_quiz_missing`, 예: `Quiz missing on published posts: 2026-10-18 business KO (expert).`

## 검증

- `pipelineHealth.test.js`: 누락 없음 → 이슈 없음, 일부 누락 → 날짜·카테고리·언어·persona 표시, 다른 이슈와 함께 표시.
- 로컬 dev 어드민에서 10-18 business KO 경고가 실제로 보이는지 확인 (데스크톱 + 375px).
