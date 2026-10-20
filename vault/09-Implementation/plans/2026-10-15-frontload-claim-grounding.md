# Frontload Claim Grounding — 작성 단계 주장 검증

> 상위 계획: [[2026-10-13-news-pipeline-gpt6-upgrade]] 개선 과제 P1-3
> 상태: Phase 1 구현·배포 (2026-10-20), 1주 측정 중 → Phase 2 판단 2026-10-27~

**Goal:** 기사 작성 모델이 frontload(헤드라인·요약·포인트)에 출처에 없는 수치·이름을 쓰는 것을 저장 전에 결정적으로 찾아내고, 고쳐서 draft 차단을 줄인다.

## 배경 (실제 사례)

| 날짜 | frontload 주장 | 출처 | 결과 |
|---|---|---|---|
| 10-15 business | "cached inputs 95% off" | ~~없음~~ → **있음** (Google 원문: "cached input tokens at 95% off", 2026-10-20 재확인) | sol major → draft, Amy 수동 발행. **QC 오판이었음** (QC-EVIDENCE-03 발췌 예산 문제와 같은 날) |
| 09-28 research | "63x lower scoring cost" | 확인 안 됨 | QC major (judge 회차마다 흔들림) |
| 09-28 business | "former President Donald Trump" | 원문은 현직 | 발행 전 수동 수정 |

- 지금은 QC가 잡아서 **draft로 막는 것**만 가능 → sol 전환 후 자동 발행률 하락의 주 원인이 됨.
- 걸러내기(퀴즈 검증, QC 발췌, gate)와 반대로, **생성 단계에서 덜 틀리게** 하는 장치.

## 조사 결과 (2026-10-15)

- frontload는 별도 단계가 아니라 **페르소나별 writer JSON 출력**에 포함. expert 호출 값이 canonical (`news_posts.title` / `excerpt` / `focus_items`), QC frontload 검사 대상도 이것. learner/beginner frontload는 `guide_items`에 저장.
- writer가 보는 원문 = `_generate_digest`의 `user_prompt`: 그룹별 enriched 출처(또는 `raw_content_map`)를 **각 12,000자**로 잘라 이어 붙인 텍스트 + Community Pulse 데이터. → 검증 기준 코퍼스는 정확히 이 텍스트.
- 재사용할 기존 패턴: `_translate_focus_items_ko` (frontload 한 필드만 저렴한 모델로 보충, 실패해도 non-blocking), `pipeline_quality._frontload_claim_tokens` (수치·이름 추출, 2026-10-14/15 구현).
- writer 프롬프트에 **오늘 날짜 없음** → "former President" 같은 시점 오류의 원인.

## 설계

### Part A — 수치·이름 근거 검사 (결정적)
- 대상: **EN** expert frontload (headline, excerpt, focus_items). KO는 번역이라 단위 표기가 달라 오탐 위험 ("5,000억 달러" vs "$500 billion") → 검사 제외, 수정 시 EN과 함께 고침.
- 토큰: `_frontload_claim_tokens`의 **수치 + 구체 이름**만 (mixed-case, 비일반 약어, 숫자 포함 이름). 2~3단어 일반 구절은 제외 (Title Case 헤드라인 n-gram이 원문에 그대로 있을 리 없어 오탐).
- 판정: 토큰의 변형(단위·구분자) 중 하나라도 `user_prompt`에 있으면 근거 있음. 없으면 `unsupported`.

### Part B — 시점·직함 지침 (프롬프트)
- writer 시스템 프롬프트에 batch 날짜 주입 + "직함·소속·시점은 출처 표기를 따르고, 자체 지식으로 'former'/'전' 등을 붙이지 말 것".
- 참고: main을 gpt-6.1-sol(지식 시점 2026-04)로 바꾸면 이 유형은 줄어들 가능성 → 그래도 지침은 유지.

### 단계적 적용
1. **Phase 1 — 감지 전용 (1주):** `unsupported` 목록을 `digest:{type}:frontload_grounding` 로그 `debug_meta`에 기록만. 오탐률 측정 (매일 sol QC의 major와 대조).
   - 이유: 9/30 이전 checkpoint가 삭제되어 (2026-10-14 사고) 과거 데이터로 오탐률을 미리 잴 수 없음. 남은 checkpoint는 10-12 / 10-14 / 10-15뿐.
2. **Phase 2 — 수리:** `unsupported`가 있으면 저렴한 모델(light)로 frontload만 재작성 — "아래 주장은 출처에서 확인되지 않음: 제거하거나 출처가 뒷받침하는 표현으로 바꿀 것. 새 수치·이름 추가 금지." EN/KO 함께. 재작성 후 Part A 재검사, 여전히 남으면 원본 유지 + 로그 (QC가 판단). 실패는 non-blocking.

### 범위 밖 (v1)
- learner/beginner frontload (`guide_items`) — Phase 1 오탐률 확인 후 확장 검토
- 본문(body) 주장 검증 — 길고 인용 구조가 달라 별도 설계 필요
- 관계·해석성 과장 ("AISI가 배포 전 평가 중") — 결정적 검사로 불가, QC 담당

## Phase 1 구현 (2026-10-20)

- 모듈: `backend/services/frontload_grounding.py` — QC의 `_frontload_claim_tokens`는 **수정하지 않음** (GPT-6 관찰 기간 QC 점수 고정). 정규식 상수만 재사용.
- 호출: `pipeline_digest._generate_digest`에서 frontload 확정 직후 (expert를 이번 호출에서 만든 경우만) → 로그 `digest:{type}:frontload_grounding`, `debug_meta = {checked, unsupported[], weak[], supported[]}`. 실패해도 진행 (non-blocking). 재실행 cascade(classify/merge/community/write)에 포함.
- 판정 3단계: `unsupported` (원문에 없음) / `weak` (숫자는 있으나 frontload의 주변 단어가 원문의 그 숫자 근처 150자 안에 없음) / `supported`.
- 오탐 방지 (실데이터 사전 점검에서 발견한 6건 → 0건):
  - 이름 구절은 2단어까지 (3단어는 복수형 "M5 Ultra Macs", 문장 첫 동사 "Watch Bolt E4B"로 오탐)
  - 숫자 단어가 구별되는 형태("501B", "1.27.1")면 두 단어가 원문 200자 안에 함께 있어도 근거 인정
  - 월 약어 ↔ 전체 이름 ("Nov 30" ↔ "November 30"), 하이픈 ↔ 공백 ("Gemini-4" ↔ "Gemini 4")
  - 약어 ↔ 머리글자 풀어쓰기 ("MoE" ↔ "Mixture-of-Experts")
  - 단위·버전 꼬리 보존 ("Beam 501" → "Beam 501B", "OpenHands 1.27" → "1.27.1")
- 사전 점검 (10-14~10-20 발행 글 14개, 체크포인트로 원문 근사): 주장 63개 중 unsupported 0 / weak 0. 근사 원문은 writer 입력의 상위집합이라 실제 운영 로그보다 관대할 수 있음 → 운영 로그 1주가 진짜 측정.

## 완료 기준
- Phase 1: 테스트 (실제 사례 3건 축약: 95% / 63x / 정상 수치) + 1주 로그에서 오탐률 산출
- Phase 2: 오탐률이 낮으면 (목표: 감지 건 중 실제 무근거 비율 ≥ 70%) 수리 활성화, sol QC의 frontload major 빈도 감소 확인
- Part B: 프롬프트 변경 + `/prompt-audit news` 통과
