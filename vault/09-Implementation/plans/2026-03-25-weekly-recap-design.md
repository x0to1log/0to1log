# Weekly Recap Design (v4)

> 관련: [[2026-03-16-weekly-digest-design]] — 초기 설계 (이 문서로 대체)
> 관련: [[2026-03-17-news-pipeline-v4-design]] — v4 2 페르소나 기준
> 작성: 2026-03-25

---

## 개요

매주 월~금 데일리 다이제스트(Research + Business)를 입력으로, LLM이 주간 요약 + 트렌드 분석을 자동 생성. Amy가 어드민에서 편집 후 발행. 동일 콘텐츠를 웹(/weekly) + 이메일(Buttondown)로 동시 발행 가능 (이메일은 초기 비활성화).

**대상 독자:**
- 매일 보는 독자 → 이번 주 복습 + 놓친 것 체크
- 바쁜 독자 → 주 1회로 AI 동향 파악

---

## 페르소나별 차이

| 항목 | Expert | Learner |
|------|--------|---------|
| 트렌드 분석 | 의사결정 관점 — "이 흐름이 우리 팀/사업에 뭘 의미하나" | 학습 관점 — "이번 주 AI 업계에 무슨 일이 있었나" |
| TOP 뉴스 설명 | 간결, 임팩트 중심 | 친절, 배경 설명 포함 |
| 주목할 포인트 | "다음 주 의사결정 대기 리스트" | "이 키워드가 나오면 맥락을 안다" |
| 이번 주 숫자 | 동일 (공통) | 동일 (공통) |
| 액션 아이템 | 의사결정 포인트 | 실행 가능한 학습 액션 |

---

## 콘텐츠 구조

```markdown
## AI Weekly — 2026년 3월 4주차

### 이번 주 한 줄
"빅테크 AI 전쟁이 본격화된 주. 성능 → 가격 → 오픈소스 삼파전."

### 이번 주 숫자
- **$2B** — OpenAI 신규 투자 유치
- **40%** — GPT-5 추론 성능 향상
- **8,000명** — OpenAI 채용 목표

### TOP 뉴스 (중요도 순)
1. **GPT-5 출시** — [2~3문장 요약 + 원본 데일리 링크]
2. **Meta Llama 4 오픈소스** — [2~3문장]
...최대 7~10건

### 이번 주 트렌드 분석
[데일리 뉴스들을 엮어서 주간 흐름 해석]
[3~4단락 — 월요일 → 금요일 흐름으로 서술]
(Expert: 의사결정 관점, Learner: 학습 관점 — 별도 생성)

### 주목할 포인트
[이번 주 뉴스에서 아직 결론이 안 난 것들]
[확정 일정이 아닌, 이번 주 뉴스에 근거한 관전 포인트]

### 그래서 나는? (액션 아이템)
[Expert: 의사결정 포인트 3~5개, Learner: 실행 가능한 액션 3~5개]
```

### 하단 카드 (본문 분리)

글 끝에 별도 카드 2개로 표시:

1. **이번 주 용어** — 해당 주 데일리에서 핸드북에 추가된 용어 1~2개. 카드에 용어명 + 한 줄 정의 + 핸드북 링크.
2. **이번 주 도구** — 뉴스에서 언급된 AI 도구 1개 추천. 카드에 도구명 + 한 줄 설명 + 링크.

---

## 퀴즈

Weekly에는 퀴즈를 넣지 않음. Weekly는 분석 콘텐츠 자체가 engagement 역할. 퀴즈는 데일리 전용.

---

## 파이프라인

```
매주 일요일 자동 트리거 (cron) 또는 어드민 수동 "Generate Weekly" 버튼
  |
news_posts에서 해당 주 데일리 다이제스트 fetch
(월~금 research + business, locale별, content_expert + content_learner)
  |
LLM에게 주간 요약 요청 (페르소나별 x 2 언어 = 4 호출):
  - Expert EN, Expert KO
  - Learner EN, Learner KO
  |
하단 카드 데이터 생성:
  - 이번 주 핸드북 용어: DB에서 해당 주 생성된 published 용어 쿼리
  - 이번 주 도구: LLM이 뉴스에서 추천 (프롬프트 내 포함, 추가 호출 없음)
  |
news_posts에 draft 저장 (post_type = 'weekly')
  |
[비활성화] Buttondown API로 이메일 발송
  |
Amy가 어드민에서 편집 -> 발행
```

### 이메일 발송 (Buttondown)

- 파이프라인에 Buttondown API 연동 코드 포함
- `WEEKLY_EMAIL_ENABLED=false` 환경변수로 비활성화
- 활성화 시: Weekly 저장 후 Buttondown API `/emails` 엔드포인트로 draft 이메일 생성
- Amy가 Buttondown 대시보드에서 확인 후 발송 (자동 발송 아님)

---

## DB

기존 `news_posts` 테이블 재활용. 새 테이블 불필요.

| 필드 | 값 |
|------|-----|
| `post_type` | `'weekly'` |
| `pipeline_batch_id` | `'2026-W13'` (ISO 주차) |
| `slug` | `'2026-w13-weekly-digest'` (EN), `'2026-w13-weekly-digest-ko'` (KO) |
| `content_expert` | Expert 페르소나 본문 (마크다운) |
| `content_learner` | Learner 페르소나 본문 (마크다운) |
| `guide_items` | `{ "week_numbers": [...], "week_tool": {...}, "week_terms": [...] }` |

### post_type 컬럼 추가

현재 `news_posts`에 `post_type` 컬럼이 없으면 마이그레이션 필요:

```sql
ALTER TABLE news_posts ADD COLUMN post_type text NOT NULL DEFAULT 'daily';
ALTER TABLE news_posts ADD CONSTRAINT news_posts_post_type_check
  CHECK (post_type IN ('daily', 'weekly'));
```

---

## 프론트엔드

### 뉴스 리스트 페이지
- 기존 비즈니스/리서치 탭 옆에 **Weekly** 탭 추가
- Weekly 탭 클릭 시 `post_type = 'weekly'` 필터
- Weekly 포스트는 카드에 "Weekly Recap" 배지 표시

### 상세 페이지
- 기존 `NewsprintArticleLayout` 그대로 사용 (Expert/Learner 탭 전환)
- 하단에 용어 카드 + 도구 카드 2개 추가 렌더링
- `guide_items.week_numbers`에서 "이번 주 숫자" 데이터 읽어 본문 상단에 표시

### 어드민
- 기존 뉴스 에디터 재사용 (마크다운 통편집)
- `post_type = 'weekly'` 필터 추가
- 어드민 파이프라인 페이지에 "Generate Weekly" 수동 버튼 추가

---

## 비용

| 항목 | 비용 |
|------|------|
| 데일리 fetch | $0 (DB 쿼리) |
| LLM 주간 요약 (2 페르소나 x 2 언어) | ~$0.12~0.15 |
| 도구 추천 (프롬프트 내 포함) | $0 (추가 호출 없음) |
| 핸드북 용어 (DB 쿼리) | $0 |
| Buttondown API | $0 (free tier) |
| **주간 총** | **~$0.15** |

---

## 구현 태스크

```
Phase 1: 파이프라인
  WEEKLY-DB-01     -> post_type 컬럼 마이그레이션
  WEEKLY-PROMPT-01 -> 주간 다이제스트 프롬프트 (expert/learner x EN/KO)
  WEEKLY-PIPE-01   -> run_weekly_digest() 파이프라인 함수
  WEEKLY-EMAIL-01  -> Buttondown API 연동 (비활성화 상태)

Phase 2: 프론트엔드
  WEEKLY-FE-01     -> 뉴스 리스트 Weekly 탭 + 배지
  WEEKLY-FE-02     -> 상세 페이지 하단 카드 (용어 + 도구)
  WEEKLY-ADMIN-01  -> 어드민 "Generate Weekly" 버튼

Phase 3: 검증
  WEEKLY-CRON-01   -> 일요일 cron 엔드포인트
  WEEKLY-TEST-01   -> E2E 검증
```

---

## Related

- [[2026-03-16-daily-digest-design]] — 데일리 다이제스트
- [[AI-News-Pipeline-Design]] — 뉴스 파이프라인 전체 설계
- [[2026-03-17-news-pipeline-v4-design]] — v4 전환 결정
- [[2026-03-25-Business-Reality-Check]] — 비즈니스 분석 (배포 채널 최우선)
