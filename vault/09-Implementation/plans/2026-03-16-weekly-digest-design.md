# AI Weekly Digest 설계 (v4 업데이트)

> 관련: [[2026-03-16-daily-digest-design]] — 데일리 다이제스트 (선행)
> 관련: [[AI-News-Pipeline-Design]] — 파이프라인 설계
> 관련: [[2026-03-17-news-pipeline-v4-design]] — v4 2 페르소나 전환
> 업데이트: 2026-03-24 — v4 (2 페르소나) 기준으로 재설계

---

## 개요

매주 월~금 데일리 다이제스트를 입력으로, LLM이 주간 요약+트렌드 분석을 자동 생성.
Amy가 어드민에서 편집 후 발행.

**대상 독자:**
- 매일 보는 독자 → 이번 주 복습 + 놓친 것 체크
- 바쁜 독자 → 주 1회로 AI 동향 파악

---

## v4 변경사항 (v3 대비)

| 항목 | v3 | v4 |
|------|----|----|
| 페르소나 | 3개 (expert/learner/beginner) | **2개 (expert/learner)** |
| 모델 | gpt-4o | **gpt-4.1** |
| 입력 | 데일리 10개 (R5 + B5) | 데일리 최대 10개 (R5 + B5), content_expert + content_learner 모두 |
| 퀴즈 | 없음 | **주간 퀴즈 1개 (페르소나별)** |
| 비용 | ~$0.20/주 | ~$0.15/주 (gpt-4.1 가격 유사, 페르소나 2개로 축소) |

---

## 콘텐츠 구조

```markdown
## AI Weekly — 2026년 3월 4주차

### 이번 주 한 줄
"빅테크 AI 전쟁이 본격화된 주. 성능→가격→오픈소스 삼파전."

### TOP 뉴스 (중요도 순)
1. **GPT-5 출시** — [2~3문장 요약 + 원본 데일리 링크]
2. **Meta Llama 4 오픈소스** — [2~3문장]
...최대 7~10건

### 이번 주 트렌드 분석
[데일리 뉴스들을 엮어서 주간 흐름 해석]
[3~4단락 — 월요일→금요일 흐름으로 서술]

### 다음 주 전망
[다음 주 예상 이벤트/발표 1~2단락]

### 그래서 나는? (액션 아이템)
[Expert: 의사결정 포인트, Learner: 실행 가능한 액션]
```

**Expert vs Learner 차이:**
- Expert: 트렌드 분석 깊이 ↑, 의사결정 프레임워크, "이번 주 결정해야 할 것"
- Learner: TOP 뉴스 설명 친절 ↑, "이번 주 배울 것", 용어 설명 포함

---

## 파이프라인

```
매주 일요일 자동 트리거 (cron) 또는 어드민 수동 "Generate Weekly" 버튼
  ↓
news_posts에서 해당 주 데일리 다이제스트 fetch
(월~금 research + business, locale별, content_expert + content_learner)
  ↓
LLM에게 주간 요약 요청 (페르소나별 × 2 언어):
  - Expert: 심층 분석 + 의사결정 관점
  - Learner: 핵심 정리 + 학습 관점
  ↓
news_posts에 draft 저장 (post_type = 'weekly')
  ↓
Amy가 어드민에서 편집 → 발행
```

---

## DB

- `news_posts` 테이블 재활용
- `post_type = 'weekly'`
- `pipeline_batch_id = '2026-W13'` (ISO 주차 형식)
- `slug = '2026-w13-weekly-digest'` (EN), `'2026-w13-weekly-digest-ko'` (KO)
- `content_expert`, `content_learner` 페르소나별 콘텐츠
- `guide_items.quiz_poll_expert`, `guide_items.quiz_poll_learner` 주간 퀴즈

---

## 프론트엔드 표시

- 뉴스 리스트 페이지: 비즈니스/리서치 탭 옆에 **Weekly** 탭 추가
- Weekly 탭 클릭 → `post_type = 'weekly'` 필터
- 상세 페이지: 기존 NewsprintArticleLayout 그대로 사용 (페르소나 탭 + 퀴즈 포함)
- 주간 포스트는 상단에 "📌 Weekly Recap" 배지 표시

---

## 비용

| 항목 | 비용 |
|------|------|
| 데일리 fetch | $0 (DB 쿼리) |
| LLM 주간 요약 (2 페르소나 × 2 언어) | ~$0.12~0.15 |
| 퀴즈 (프롬프트 내 포함) | $0 (추가 호출 없음) |
| **주간 총** | **~$0.15** |

---

## 구현 태스크

1. `WEEKLY-PROMPT-01` — 주간 다이제스트 프롬프트 작성 (expert/learner 분리)
2. `WEEKLY-PIPE-01` — `run_weekly_digest()` 파이프라인 함수
3. `WEEKLY-CRON-01` — Cron 엔드포인트 (일요일 자동) + 어드민 수동 버튼
4. `WEEKLY-FE-01` — 뉴스 리스트 Weekly 탭 + 배지
5. `WEEKLY-TEST-01` — E2E 검증

---

## Related

- [[2026-03-16-daily-digest-design]] — 데일리 다이제스트
- [[AI-News-Pipeline-Design]] — 뉴스 파이프라인 전체 설계
- [[2026-03-17-news-pipeline-v4-design]] — v4 전환 결정
