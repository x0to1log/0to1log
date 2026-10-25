# Handbook Seed 재개 — Claude 크레딧으로 생성

> 상위: [[2026-04-19-handbook-seed-800]] (원 설계, 2026-05-24 이후 정지)
> 상태: 계획 확정 (2026-10-23) — 큐레이션 C(뉴스 수요 + 기존 목록 보충), 판정 sol 유지, 개수·모델은 시범 후 결정
> 기한: **2026-11-13** — Team API 크레딧 $500 만료일

## 배경

- Claude Startups 프로그램 크레딧 (Console 확인, 2026-10-23):

| 크레딧 | 금액 | 만료 |
|---|---|---|
| API credit (Team) | $500 | **2026-11-13** |
| 프로그램 크레딧 | $1,000 | 2027-04-08 |

- 월 지출 한도(티어) $1,000. 크레딧은 API·Claude Code·Playground 공용.
- 뉴스 파이프라인은 월 ~$25라 크레딧 대부분이 남음 → 비용 때문에 멈췄던 **핸드북 시드**에 투입.
- "Team $500이 매달 들어오는지"는 Console에서 확인 불가 — Amy가 프로그램 안내로 확인 필요. **이 계획은 1회분만 가정.**

## 현재 상태 (2026-10-23 조사)

| 항목 | 상태 |
|---|---|
| DB `handbook_terms` | published 114 / draft 17 / archived 40, 마지막 수정 2026-05-24 |
| 후보 큐레이션 | 9 카테고리 JSONL **731개** (목표 800). Amy 승인 여부 미확인 |
| 배치 스크립트 | `backend/scripts/run_handbook_seed_batch.py` **이미 있음** — JSONL 읽기, DB에 있는 용어 건너뜀, `generate_term_content` 호출, `--max-concurrent`, `--draft-only`(기본) / `--full-quality`, 항상 `status='draft'`, `source='seed'` 저장 |
| 카테고리별 artifact 정책 | `prompts_handbook_types.CATEGORY_ARTIFACT_POLICIES` 등 **이미 구현** (`bea2d6fd`) — HB-SEED-PROMPT-01의 핵심 |
| 공급자 추상화 | **없음.** 모든 호출이 `client.chat.completions.create` 직접 호출, OpenAI 전용 인자(`service_tier="flex"`, `reasoning_effort`, `prompt_cache_key`, `max_completion_tokens`) 하드코딩 |
| `anthropic` 의존성 | 없음 |

### 용어 1개 생성 흐름 (`advisor._run_generate_term`)

- 검색: Tavily + Brave + Exa (항상, ~35k자 원문 주입)
- 생성 4회 (main): Meta+KO Basic → (EN Basic ∥ KO Advanced) → EN Advanced. `json_object`, 출력 상한 24k(×3 → 72k)
- full-quality 모드에서 추가: Basic 비평 1 + Advanced 비평 2 (reasoning) → 조건부 재생성 + 엔티티 검증(nano + Brave) + 판정 2 (reasoning)
- 시스템 프롬프트 26~41k자 (한국어 다수) → **프롬프트 캐싱 효과 큼**
- 판정 게이트 `_build_generation_gate`: 점수 < 55 blocked, < 70 review_required (sol 점수 척도 기준)

## 설계

### 결정 0 — 후보: 우리 뉴스의 수요 + 기존 731개 보충 (확정)

- 기존 731개는 2026-04 기준 (6개월치 최신 용어 없음), Amy 검토 여부 불확실 → 그대로 쓰지 않음.
- **뉴스 수요 추출:** 발행된 EN 뉴스 369편 (2026-03-18 ~ 10-23, research 177 / business 172 / weekly 20)에 기존 `advisor.extract_terms_from_content` (luna)를 돌려 용어 후보 수집. 전체 < $1, Claude 어댑터와 무관하게 바로 실행 가능.
  - 점수: 등장 편수 (빈도) + 최근 등장일 (최근성) + 카테고리.
  - 2026-05-24 이후 핸드북 자동 추출이 꺼져 있었음 → 5개월치 뉴스 용어가 핸드북에 없는 상태. 이 공백이 1순위.
- **보충:** 뉴스에 잘 안 나오는 기초 용어(math-statistics, cs-fundamentals, ml-fundamentals)는 기존 731개에서.
- **정리:** DB 기존 용어(published/draft/archived)·별칭과 중복 제거 → 기존 `gate_candidate_terms` + `validate_term_scope`로 범위 밖 용어 거름 → 순위표.
- **Amy 검토:** 순위표 상위부터 승인/제외. 승인된 것만 시드 JSONL (기존 스키마: term, aliases, type, note)로 → 기존 배치 스크립트가 그대로 읽음.

### 결정 1 — 작성만 Claude, 판정은 OpenAI 유지 (확정)

- **작성(생성 4회 + 재생성)** → Claude. 크레딧을 쓰는 본체.
- **비평·판정(reasoning)** → 기존 gpt-6.1-sol 유지.
  - 판정 기준(55/70)이 sol 점수 척도로 맞춰져 있어 재보정 불필요.
  - 작성 모델 ≠ 판정 모델 → 같은 모델끼리 후한 채점 편향 감소.
- 엔티티 추출(nano) → 기존 luna 유지.

### 결정 2 — 얇은 공급자 어댑터 (핸드북 작성 호출에만)

- `services/agents/llm.py` (가칭): `complete_json(role, system, user, max_tokens, effort, cache_key) -> (text, usage)`.
  - OpenAI 경로: 기존 kwargs 그대로.
  - Anthropic 경로: Messages API, 시스템 프롬프트에 `cache_control` (캐시), 긴 출력은 스트리밍, JSON은 지시 + `parse_ai_json`(기존, 공급자 무관).
- 설정: `handbook_writer_provider` / `anthropic_model_handbook_writer` (config.py 기본값 = 운영값, 기존 원칙 유지). 뉴스·advisor는 **건드리지 않음**.
- 사용량·비용: `extract_usage_metrics`에 Anthropic 경로 추가 (cache read/write 토큰), 가격표에 Claude 모델 추가.
- 구현 전 확인 (claude-api 스킬 문서): 구조화 출력 지원 범위, 캐시 최소 길이, effort/thinking 파라미터, 레이트 리밋 티어.

### 결정 3 — 모델과 생성 개수는 시범 결과로 결정 (확정)

- 예산(11/13까지 ~$500)이 고정이라 **개수 × 용어당 비용**의 맞교환. 시범 실측 후 "Sonnet으로 많이" vs "Opus로 엄선"을 결정.

- 후보: **Sonnet 5.5** ($2/$10) vs **Opus 5.5** ($4/$20).
- 5월 실패 패턴이 났던 카테고리에서 3개 (safety-ethics, products-platforms, math-statistics 각 1) × 2 모델 = 6회 생성, sol 판정 점수 + Amy 직접 비교.
- 비용 추정 (4월 실측 15만 토큰/용어, 입력 ~70% 가정, 캐싱 전):

| 모델 | 용어당 | 731개 |
|---|---|---|
| Sonnet 5.5 | ~$0.6 | ~$450 |
| Opus 5.5 | ~$1.2 | ~$900 |

  → Sonnet은 $500(11/13)에 맞고, Opus는 $1,000분까지 써야 함. **추정치 — 시범 실측으로 교체.**

### 결정 4 — 기한은 "생성"에만, 발행은 이후

- 11/13까지 목표: 731개 **draft 생성 완료**. 발행(검수)은 기한 없음.
- 원 설계의 Phase 1~3 (validator, state 파일 오케스트레이터, 2-tier 게이트, 어드민 배지 UI)은 이번 범위에서 제외 — 기존 배치 스크립트 + DB 존재 체크로 재실행 안전성 확보.
- 자동 발행 게이트는 warmup 검수 뒤 별도 결정.

## 일정 (11/13 역산)

| 기간 | 작업 (A·B 병행) | 산출 |
|---|---|---|
| 10/23~10/25 | **A.** 뉴스 369편 용어 추출 → 중복·범위 정리 → 순위표 | Amy 검토용 후보표 |
| 10/23~10/25 | **B.** 어댑터 + 설정 + 사용량 계측, 단위 테스트 | 기존 OpenAI 경로 회귀 없음 |
| 10/26~10/27 | Amy 후보 검토 (상위부터) + 시범 6회 (3용어 × 2모델) | 승인 목록 초안, 모델·개수 결정 |
| 10/28~10/30 | warmup 30개 (full-quality) → Amy 검수 | 품질 OK / 프롬프트 수정 필요 판단 |
| 10/31~11/10 | 나머지 승인분, 동시 실행 N개 | 전량 draft |
| 11/11~11/13 | 실패분 재시도, 크레딧 잔액 점검 | |

- 시간: 용어당 ~8분, 동시 6개면 700개 ≈ 16시간 → 여유 있음. 병목은 레이트 리밋과 **검색 API** (Tavily/Brave/Exa 쿼터 — 731 × 3회 + 엔티티 검증).
- 뉴스 GPT-6 관찰(~10/26)과 겹치지만 뉴스 코드는 건드리지 않음.

## 시범 결과 (2026-10-25~26)

**1차 (10-25): 9건 전부 실패** → 원인 3가지
- OpenAI 크레딧 소진 (429 "no credits remaining") — Amy 충전 후 해결. 판정·비평이 sol이라 full-quality는 OpenAI 필수.
- Claude는 JSON을 ` ```json ` 펜스로 감싸고, 본문 안의 ` ```python ` 예시에서 `parse_ai_json`의 비탐욕 정규식이 잘라 "Unterminated string" → `claude_client.json_payload`가 바깥 펜스만 벗기도록 수정.
- "Red Teaming"을 Sonnet·Opus 모두 거절 (`stop_details.category=cyber`) → 거절 시 해당 용어만 OpenAI 작성 모델로 재생성 (`generate_term_content`, `_writer_fallback` 기록).

**2차 (10-26): full-quality, 판정 sol** — `pilot/summary.md`

| 모델 | 평균 adv | 평균 basic | 게이트 통과 | 용어당 비용 | 용어당 시간 |
|---|---|---|---|---|---|
| Claude Sonnet 5.5 | 63 | 59 | 0/3 | $1.8 | 12분 |
| Claude Opus 5.5 | 63 | 72 | 0/3 | $3.1 | 18분 |
| gpt-6.1-sol | 75 | 82 | 2/3 | $0.5 | 12분 |

(Opus의 Red Teaming은 거절 → sol 대체 생성분)

- **비용이 3.5~6배인 이유:** Claude가 길게 씀 (adv KO 13~16천 자 vs 9.8천), 비평 점수가 낮아 재생성 루프 증가 (입력 1.7배), 프롬프트 캐시 거의 미적중 (시스템 블록 끝에 용어별 카테고리·타입 가이드가 붙어 공통 접두부가 매번 다름).
- **구조 감점:** 코드 캡슐 과대 (3~6천 자), advanced 7/8 섹션.
- **직접 읽어 본 판단 (Bradley–Terry, sol 87 vs Opus 68; 판단자도 Claude라 편향 가능성 명시):** 내용 깊이·정확성·예시 구체성은 Opus 우위 (MLE 존재 조건, Zermelo MM, 충분통계량, 무승부 확장 인용). sol은 수준 조절·규칙 준수 우위, advanced 문장은 추상적·장황. Opus 감점 사유 = Basic에 수식·전문용어 (수준 이탈), 근거 없는 단정 2건, 코드 ~100줄 → **프롬프트로 고칠 수 있는 결함.** 점수 차(19점)는 실제 품질 차보다 큼 → sol 판정 편향 일부 가능성 (검증 안 된 가설).

**3차 (10-26, Claude용 조정 후)** — `pilot-v2/`. 조정: 본문별 분량 상한 (발행 p75: Basic KO 3,000 / EN 6,000, Advanced KO 7,500 / EN 12,000), 코드 1블록 ≤55줄·3,500자, 근거 없는 단정 금지, effort high→medium (재생성 포함), 시스템 프롬프트 2블록 (고정 상수 캐시). 모두 Claude 작성일 때만.

| 용어 | sol (기준선) | Sonnet 1차 → **3차** | Opus 1차 → **3차** |
|---|---|---|---|
| Red Teaming | 72 / 84, $0.40 | 70 / 63, $1.60 → **71 / 92 pass, $0.92** | 거절→sol 대체 (두 번 모두, cyber) |
| SGLang | 66 / 73, $0.63 | 57 / 52, $2.08 → **63 / 70, $1.25** | 51 / 55, $4.60 → **63 / 98, $2.93** |
| Bradley–Terry | 87 / 89, $0.53 | 62 / 63, $1.88 → **파싱 실패** | 68 / 69, $4.30 → **70 / 78 pass, $2.27** |

(advanced / basic, 판정 sol)

- **Basic은 sol 이상**, Advanced는 아직 sol보다 ~8점 낮음 (판정 sol 편향 가능성 유지).
- **비용:** Sonnet $1.8 → ~$1.1/용어 (-40%), Opus $4.5 → ~$2.6 (-42%). 캐시 적중 35~105K 토큰/용어 (1차 ~0).
- **분량:** KO는 상한 근처 (adv KO 5.5~8.5천), **EN은 여전히 초과** (adv EN 14~16천 vs 12천).
- **Sonnet 파싱 실패:** 로그상 max_tokens·거절 없음, 파서의 fence 대체가 원래 오류를 가림 → 수식 많은 용어의 LaTeX 단일 백슬래시(`\sigma`)가 잘못된 JSON 이스케이프였을 가능성 (**검증 안 된 가설**, 원문 미저장). `json_payload`가 엄격 파싱이 "Invalid \escape"로 실패할 때만 백슬래시 보정.
- **별도 기존 문제 발견:** `\beta`·`\frac`·`\nabla`처럼 JSON이 유효 이스케이프로 받는 LaTeX는 조용히 깨짐 (`\b`=백스페이스). OpenAI 경로도 동일 → 과제 HB-LATEX-01.

**결정 (2026-10-26, Amy):** Claude 방향으로 진행하되 **프롬프트 조정 후 재시범.** 그리고 교체 가능한 역할은 모두 Claude API로 옮기는 방향 → 별도 계획 [[2026-10-26-claude-api-migration]].

## 리스크

| 리스크 | 완화 |
|---|---|
| Amy 검토 부담 (후보 수백 개) | 순위표 상위부터 검토, 승인된 만큼만 생성. 검토 속도가 생성 일정의 상한 |
| 뉴스 추출 용어가 너무 좁거나 일시적 (제품명·사건명) | `gate_candidate_terms` + `validate_term_scope`로 거르고, 순위에 등장 편수 반영 (1회성 제외) |
| 검색 API 쿼터 소진 | 실행 전 Tavily/Brave/Exa 잔여 쿼터 확인, 필요 시 동시 실행 수 조절 |
| 5월 실패 패턴 재발 (카테고리 틀 강요) | 시범·warmup에서 해당 카테고리 우선 검수 |
| $500 차감 순서 (먼저 만료분부터 쓰이는지) | **검증 안 된 가정.** 시범 후 Console 잔액 변화로 확인 |
| 731개 draft 검수 부담 | 기한과 분리. warmup 결과로 자동 발행 게이트 여부 결정 |
| 크레딧 종료 후 | 공급자 설정만 바꾸면 OpenAI로 복귀 (어댑터의 목적) |

## 완료 기준

- 어댑터: OpenAI 경로 테스트 전부 통과 + Anthropic 경로 단위 테스트 + 실제 1회 호출 성공
- 시범: 6회 결과표 (점수, 비용, 시간) + 모델 결정 기록
- 전량: 731개 중 생성 성공 ≥ 95%, 실패 목록 기록, 실제 지출 기록
