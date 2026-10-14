# News Pipeline 점검 + GPT-6 마이그레이션 Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) 9/29부터 멈춘 daily/weekly 자동 실행을 복구하고 재발 감지를 추가한다. (2) 2026-12-11 종료되는 gpt-5 계열을 GPT-6 계열로 교체하되, 품질 점수와 run당 비용을 측정해 역할별 모델을 결정한다.

**Decision (2026-10-13, Amy):** 대체 모델은 OpenAI 권장 1:1 대체(GPT-5.6)가 아닌 **최신 GPT-6 계열** 사용.

**Decision (2026-10-14, Amy):** QC judge(`openai_model_reasoning`)는 **gpt-6.1-sol**. 근거: Task 1.4 재채점에서 같은 글 점수 편차 최소(3점), 실제 결함(근거 없는 수치·주장, 퀴즈 정답 오류) 탐지율 최고. 비용은 일일 약 +$0.13이지만 합계(~$0.46)는 현행($0.52) 미만.

**역할별 목표 모델 (cutover 기준):**

| role | 현재 | 목표 | 근거 / 조건 |
|---|---|---|---|
| `openai_model_main` (writer) | gpt-5 | `gpt-6.1-sol` | A-j5: judge 고정 시 품질 동등, 비용 -36% |
| `openai_model_reasoning` (QC judge) | gpt-5-mini | `gpt-6.1-sol` | 위 Decision |
| `openai_model_light` (classify/rank/퀴즈 등) | gpt-5-mini | `gpt-6-luna` | **조건부:** 퀴즈 생성도 light. A-j5에서 luna 퀴즈 오답 1건 → Task 1.6 퀴즈 검증 단계가 먼저 배포되어야 함. 미배포 시 퀴즈 생성만 별도 role로 분리 검토 |
| `openai_model_nano` (comment relevance) | gpt-5-nano | `gpt-6-luna` | 비교 안 됨 (checkpoint 재사용 구간). cutover 후 관찰 |

- ⚠️ `openai_model_reasoning`은 handbook/blog/product **advisor**도 사용 (`advisor.py`의 critique/quality check 등). Railway env를 sol로 바꾸면 advisor 비용도 상승 → cutover 전 advisor 호출량 확인 또는 advisor용 role 분리 결정 필요.
- judge 교체로 점수 분포가 하향 (같은 글 business 91 → 77) → **NQ-30 auto-publish threshold 재보정 필수** (Task 1.7).

**Scope:** 뉴스 파이프라인 우선 (daily + weekly). Handbook / Advisor는 같은 `settings.openai_model_*`를 공유하므로 모델 교체 영향은 받지만, 품질 검증은 이 plan 범위 밖.

---

## Background (2026-10-13 확인)

### 운영 상태

- 마지막 `pipeline_runs`: `news-2026-09-28` (success). 9/29 ~ 10/13 **run row 0건** — daily 15회, weekly W39~W41 누락.
- 9/16~9/18: `429 You have no credits remaining` 로 failed 기록 존재 → 크레딧 소진 시에는 row가 남음. 이번에는 row 자체가 없음 → **백엔드 파이프라인 진입 전 단계에서 끊김**.
- **원인 확인 (2026-10-13, Amy):** Vercel cron 3개는 등록·활성 상태였고, Railway에는 매일 예약 요청이 도착했으나 **Supabase 프로젝트가 일시정지되어 DB 연결 실패 → `500`**. run row를 쓸 DB 자체가 없어서 기록이 남지 않았음.
- 조치: Supabase 복구 → 수동 실행 `news-2026-10-12` success (13:02~13:06 UTC). Vercel 설정 변경 근거 없음.
- **미검증:** 자동 실행 경로. 다음 cron(2026-10-14 07~08시 KST)에서 새 run row + `success` 확인 전까지 복구 완료로 보지 않음.
- **미확인:** Supabase가 일시정지된 이유 (비활동 정지 vs 사용량 한도 등). 이유에 따라 재발 방지책이 달라짐.

### 모델 종료 일정 ([OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations))

| 현재 role | 현재 모델 | 종료 | OpenAI 권장 대체 |
|---|---|---|---|
| `openai_model_main` | `gpt-5` | 2026-12-11 | `gpt-5.6-sol` |
| `openai_model_light`, `openai_model_reasoning` | `gpt-5-mini` | 2026-12-11 | `gpt-5.6-terra` |
| `openai_model_nano` | `gpt-5-nano` | 2026-12-11 | `gpt-5.6-luna` |

- 공지 대상은 dated snapshot (`gpt-5-2025-08-07` 등). undated alias `gpt-5`의 처리 방식은 문서에 없음 → **같이 종료된다고 가정 (미검증 가설)**. 목표 cutover 2026-11-15 (4주 버퍼).

### GPT-6 후보 ([Models](https://developers.openai.com/api/docs/models), [Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model))

| 모델 | 추정 tier | 가격 in/out per 1M (models 페이지) | 비고 |
|---|---|---|---|
| `gpt-6-astra` | large | $10 / $50 | daily 파이프라인엔 과함. 후보 제외 (필요 시 weekly만 검토) |
| `gpt-6.1-sol` | mid | $2 / $10 | main 후보 |
| `gpt-6-luna` | small | $0.10 / $0.50 | light / nano / reasoning 후보 |

- Chat Completions 지원 (Responses API 전환 불필요). 단 Chat Completions에서 function calling은 `reasoning_effort=none`일 때만 — **우리 코드는 tools 미사용**이라 무관.
- `reasoning_effort` 기본값 `medium` (gpt-5는 우리가 `low`를 기본 주입). levels: none/low/medium/high/xhigh/max.
- ~~미검증: flex / verbosity / prompt_cache_key / json_object / json_schema~~ → Task 1.2 probe로 전부 지원 확인 (2026-10-13). cached input 가격은 여전히 미확인 → Task 1.3.

### 코드 영향 지점 (grep 2026-10-13)

- 모델명은 `core/config.py:12-15` 4개 role로 중앙화. 서비스 코드 37곳이 `settings.openai_model_*` 참조.
- 하드코딩 1곳: `services/pipeline_digest.py:654` fallback `"gpt-5-mini"`.
- **함정:** `services/agents/client.py:93` `_apply_gpt5_kwargs`가 `model.startswith("gpt-5")`일 때만 동작 → gpt-6 이름으로 바꾸면 max_completion_tokens 3x headroom과 `reasoning_effort=low` 기본값이 **조용히 빠짐**. GPT-6 기본 effort가 medium이므로 빈 응답/JSON truncation 위험.
- `client.py:72-76` 가격 테이블이 gpt-5 = $2/$8 (gpt-4.1 가격으로 보임) → admin 비용 표시 부정확 가능. GPT-6 가격으로 교체.
- `service_tier=flex` 사용: 10개 파일, 75곳. Flex 미지원 시 일괄 fallback 필요.
- `chat.completions.create` 57곳, Responses API 0곳, tools/function calling 0곳.
- `pydantic-ai`는 requirements에만 있고 import 0건 (정리 후보).
- **운영 override:** Railway env `OPENAI_MODEL_*`가 config 기본값보다 우선. 코드 변경만으로는 운영 모델이 안 바뀜.

---

## Phase 0 — 자동 실행 복구 (BLOCKING)

### Task 0.1: 중단 원인 특정 + 복구
- [x] Vercel cron 3개 등록·활성 확인 (Amy)
- [x] 원인: Supabase 일시정지 → Railway DB 연결 실패 500 (Amy)
- [x] Supabase 복구 + 수동 실행 `news-2026-10-12` success
- [x] 2026-10-14 07~08시 KST 자동 실행에서 새 run row + `success` 확인 — `news-2026-10-14` 22:12~22:20 UTC success, 4 posts 자동 발행 (quality 96~97)
- [ ] Supabase 일시정지 사유 확인 (대시보드 Usage/알림). 사유별 재발 방지책 결정

### Task 0.2: Dead-man alert
- [ ] "마지막 news run이 26시간 이상 없음" 감지 → 알림. 이번처럼 DB가 죽으면 run row 기반 감지도 DB에 의존하므로, **감지 주체는 DB 밖**(예: Railway 측 트리거 실패 시 외부 알림)이어야 함. 채널은 기존 webhook/admin 인프라 재사용 우선, grep 후 결정
- 완료 기준: DB 연결 실패 상황을 가정한 테스트로 alert 경로 1회 검증

### Task 0.3: 누락분 처리 결정
- [ ] 9/29~10/13 backfill 여부 결정 (Amy). backfill은 과거 날짜 경계 로직(`933f1052`) 사용. GPT-6 전환 후 실행하면 A/B 데이터로도 활용 가능

## Phase 1 — GPT-6 마이그레이션

### Task 1.1: client.py reasoning-model 보정 일반화
- [x] `_apply_gpt5_kwargs` → `_apply_reasoning_model_kwargs` + `_is_reasoning_model()` 분리
- [x] 판정 규칙: `^gpt-(\d+)` major >= 5 (패턴 방식). 근거: 오판정 시 과보정은 첫 호출 400으로 즉시 드러나고, 누락은 truncation으로 늦게 드러남 → 새 세대는 기본 reasoning 취급, 예외는 명시적으로 제외
- [x] 단위 테스트: gpt-6-luna / gpt-6.1-sol / gpt-6-astra / 미래 gpt-7 = True, gpt-4o / gpt-4.1 / embedding = False, headroom + effort 기본값 적용
- [x] `pipeline_digest.py:654` 하드코딩 `"gpt-5-mini"` → `Settings.model_fields["openai_model_light"].default` (sentinel 테스트로 config 추종 검증)
- 결과: 전체 887 passed, ruff 통과 (변경 파일 기준. 레포 전체 ruff 35건은 기존 이슈)

### Task 1.2: Capability probe
- [ ] `scripts/probe_flex_tier.py` 확장 → `scripts/probe_model_capabilities.py`: 후보 모델 × {flex, verbosity, prompt_cache_key, json_object, json_schema, reasoning_effort low/high} 매트릭스
- [x] 결과를 이 문서에 기록. Flex 미지원이면 Task 1.3에 fallback 정책 추가
- 비용: 최소 프롬프트, < $0.05

**결과 (2026-10-13, `scripts/probe_model_capabilities.py`, 33개 중 30 ok):**

| Probe | gpt-6-luna | gpt-6.1-sol | gpt-5-mini (기준) |
|---|---|---|---|
| baseline `reasoning_effort=low` | ok | ok | ok |
| `service_tier=flex` (응답 tier=flex) | ok | ok | ok |
| `json_object` | ok | ok | ok |
| `json_schema` strict | ok | ok | ok |
| `prompt_cache_key` | ok | ok | ok |
| `verbosity=low` | ok | ok | ok |
| `reasoning_effort=high` | ok | ok | ok |
| `max_completion_tokens=96000` (32000×3) | ok | ok | ok |
| `temperature=0.2` | 400 | 400 | 400 |
| **PROD combo** (flex + json_object + cache key + low) | ok (flex) | ok (flex) | ok (flex) |

- 운영 코드가 보내는 파라미터 조합은 GPT-6 두 후보 모두 **코드 변경 없이 수락**. Flex 일괄 fallback 불필요.
- `temperature` 거부는 gpt-5와 동일 → 기존 정책(미전송) 유지.
- **Open Question 1 부분 해소:** undated alias가 `gpt-5`→`gpt-5-2025-08-07`, `gpt-5-mini`→`gpt-5-mini-2025-08-07`, `gpt-5-nano`→`gpt-5-nano-2025-08-07`로 resolve. 우리 운영 호출은 전부 종료 대상 snapshot으로 가고 있음. 12/11 이후 alias 동작(에러 vs 재지정)은 여전히 문서 미명시 → 그 전에 전환한다는 결론은 동일.
- **probe 한계:** 1단어 프롬프트라 reasoning token 소비량, 긴 JSON truncation, Flex 용량 부족(`flex_unavailable`) 빈도는 측정 안 됨 → Task 1.4 A/B에서 실측.

### Task 1.3: 가격 테이블 + 비용 추적
- [x] OpenAI 공식 pricing 페이지로 GPT-6 in/cached/out 가격 확인 후 `OPENAI_MODEL_PRICING_PER_1M` 교체 (gpt-5 엔트리는 cutover 후 제거)
- [x] Flex 할인율 반영 로직이 GPT-6에도 맞는지 확인

**결과 (2026-10-13, [OpenAI Pricing](https://developers.openai.com/api/docs/pricing)):**

| 모델 | Input | Cached | Output | Cached 비율 |
|---|---|---|---|---|
| gpt-6-astra | $10.00 | $1.00 | $50.00 | 10% |
| gpt-6.1-sol | $2.00 | $0.10 | $10.00 | **5%** |
| gpt-6-luna | $0.10 | $0.01 | $0.50 | 10% |
| gpt-5 | $1.25 | $0.125 | $10.00 | 10% |
| gpt-5-mini | $0.25 | $0.025 | $2.00 | 10% |
| gpt-5-nano | $0.05 | $0.005 | $0.40 | 10% |

- **기존 버그:** gpt-5 테이블이 $2/$8 (실제 $1.25/$10) → admin 비용이 input 60% 과대, output 20% 과소 집계되어 왔음. 과거 `pipeline_logs.cost_usd`는 재계산하지 않음 (추세 비교 시 주의).
- **로직 변경:** cached input을 `input × 0.1` 하드코딩 → 모델별 `cached_input` 필드. gpt-6.1-sol이 5%라 하드코딩이면 캐시 비용 2배 과대.
- Flex = 전 모델 정확히 50% (input/cached/output 모두) → 기존 `tier_multiplier` 유지.
- 참고: OpenAI가 2026-07-30 "Priority" → "Fast mode"로 개명. 우리는 미사용, 코드상 standard 취급 유지.
- 테스트: `test_usage_metrics.py` 33 passed. 전체 876 passed (실패 5개는 Task 1.1 의도된 RED).

### Task 1.4: A/B 측정
- [ ] 같은 날짜 입력으로 gpt-5 기준선 vs GPT-6 후보 조합 실행

**비파괴 실행 경로 조사 결과 (2026-10-13):**
- 기존 경로는 모두 부적합:
  - `/pipeline-rerun`: source run을 재사용하고 그 run의 logs를 삭제. draft는 덮어씀. published 날짜에서는 거부되지만, **거부 전에 이미 logs를 삭제하고 run을 failed로 바꾸는 버그**가 있음 (별도 태스크로 분리).
  - suffix 붙인 `batch_id`: `published_at = f"{batch_id}T00:00:00Z"`가 깨지고, community target_date도 batch_id에서 파생됨.
  - dry-run / no-persist 플래그 없음.
- **채택: checkpoint replay + 가짜 Supabase 클라이언트** (`scripts/ab_daily_models.py`, 신규 ~150줄)
  1. 읽기 전용: `pipeline_runs.run_key='news-YYYY-MM-DD'` → `pipeline_checkpoints`의 rank / community_summarize / enrich 로드 (`pipeline.py` rerun write 경로의 객체 복원 로직 재사용)
  2. 조합마다 `settings.openai_model_*` 교체 후 `_generate_digest(..., supabase=RecorderClient(), auto_publish=False)` 를 research/business에 대해 실행. 조합은 순차 실행 (settings는 전역)
  3. `RecorderClient`는 insert/upsert/update를 메모리에만 기록 → 캡처된 `pipeline_logs` 행에서 단계별 cost/tokens/model, `news_posts` 행에서 quality_score / sub-score / 본문 추출
  4. 조합별 JSON + markdown 덤프 + 비교 표 출력 (`ab_verbosity_qc.py` 스타일)
- 안전성 근거 (직접 확인): `_generate_digest`와 QC는 DB를 **인자로 받은 `supabase`로만** 접근. 내부에서 `get_supabase()`를 부르는 곳 없음. `pipeline.py`에서 가져다 쓰는 헬퍼 6개도 DB를 직접 열지 않음. handbook 추출은 `run_daily_pipeline`에서만 트리거되므로 이 경로에서는 실행 안 됨.
- 한계: writer / quiz / QC(main, light 일부, reasoning)만 비교. classify / rank / merge(light, nano)는 checkpoint 결과를 재사용하므로 측정 안 됨 → 필요하면 2단계로 collect + community checkpoint에서 classify→rank 재실행 모드 추가.
- **비용 집계 주의:** daily QC 사용량은 `cumulative_usage`에 합산되지 않고 `quality:{type}` 로그 행에만 남음 → `pipeline_runs`의 run 합계 비용은 QC를 빠뜨림. A/B는 캡처된 로그 행을 전부 합산해서 비교.
- 9/7 날짜 경계 수정(`933f1052`) 이후 데이터라 오염 경고 해당 없음.
- [x] 스크립트 작성: `backend/scripts/ab_daily_models.py` + `tests/test_ab_daily_models.py` (RecorderClient 안전 계약 4개). `--check-only`는 OpenAI 호출 없이 checkpoint만 확인. 결과는 `backend/output/ab-daily-models/` (gitignore)
- checkpoint 확인 결과 (`--check-only`, 2026-10-13):

| 날짜 | research 그룹/건 | business 그룹/건 | 운영 결과 |
|---|---|---|---|
| 09-28 | 5 / 5 | 5 / 7 | 둘 다 draft |
| 09-27 | 5 / 6 | 1 / 1 | published (business 표본 부족) |
| 09-26 | 5 / 5 | 3 / 5 | published |
| 09-25 | 4 / 4 | 3 / 7 | published |
| 09-24 | 4 / 4 | 4 / 9 | published |
| 09-23 | 5 / 8 | 3 / 7 | published |

- **대상 날짜: 09-28 + 09-23.** 09-28은 운영에서 draft로 남은 날(새 모델이 auto-publish 기준을 넘기는지), 09-23은 입력이 가장 풍부한 published 날.

**결과 1차 (2026-09-28, 조합당 1회):**

| 조합 | writer / judge | 비용 | research | business | research raw_llm (exp/lrn/beg/front) | business frontload |
|---|---|---|---|---|---|---|
| baseline | gpt-5 / gpt-5-mini | $0.517 | 94 | 91 | 92/100/100/88 | 94 |
| A | 6.1-sol / 6-luna | $0.310 | 84 (cap) | 86 | 97/97/99/85 | 82 |
| A-j5 | 6.1-sol / gpt-5-mini | $0.331 | 84 (cap) | 91 | 97/100/100/91 | 94 |

- 세 조합 모두 API 실패/빈 응답 0. Flex 429는 재시도로 전부 복구.
- **writer 효과 (baseline vs A-j5, judge 고정):** business 91 = 91, research raw 점수 동등 이상. 비용 -36% (writer gpt-5 $0.485 → 6.1-sol $0.306). → **writer 교체는 품질 손실 근거 없음.**
- **research 84의 정체:** 모든 조합의 writer가 frontload에 같은 "63x cheaper" 수치를 썼고, source excerpt에 근거가 없음. 이를 baseline judge(gpt-5-mini)는 1회차에서 minor, A-j5 회차에서 **major**로 판정 → `major_source_cap_84`. **같은 judge 모델도 회차마다 severity가 흔들림** → cap 규칙이 judge 편차를 10점 단위로 증폭.
- **judge 효과 (A-j5 vs A, writer 동일 모델):** luna judge가 business frontload를 94 → 82로 더 엄격하게 채점 (-5점). 표본 1개라 편차와 구분 불가.
- judge 비용은 writer 대비 무시 가능 (gpt-5-mini judge $0.022) → judge 모델은 비용보다 **일관성** 기준으로 고를 것.
- 미해결: (1) judge severity 편차 크기, (2) luna vs 6.1-sol judge 일관성, (3) 다른 날짜 일반화.

**결과 2차 — judge 재채점 (`--rescore`, A-j5 기사 고정, judge별 3회):**

| judge | research | business | 최대 편차 | 6회 비용 |
|---|---|---|---|---|
| gpt-6-luna | 84, 93, 84 | 91, 86, 88 | 9 | $0.013 |
| gpt-6.1-sol | 81, 84, 81 | 77, 78, 77 | 3 | $0.397 |
| gpt-5-mini (현행) | 84, 84, 96 | 91, 92, 92 | 12 | $0.054 |

- 편차의 원인은 raw 점수가 아니라 **major 판정 여부 (이진) → cap 84** 구조. raw_llm은 회차 간 거의 동일.
- 실제 결함 탐지: "63x" 근거 없음 (luna 2/3, sol 3/3, mini 2/3), learner 퀴즈 정답-해설 모순 (luna 0/3, **sol 2/3**, mini 0/3), business "US opposition" 근거 없음 major (luna 0/3, **sol 3/3**, mini 0/3).
- **정정:** judge 비용은 mini/luna에서만 무시 가능. sol judge는 일일 약 $0.13 (writer $0.31의 ~40%). sol judge 포함 일일 합계 ~$0.46 (현행 $0.52 미만).
- A-j5 learner 퀴즈 정답 오류는 **gpt-6-luna가 생성** → light 역할(퀴즈 생성) luna 하향에 대한 위험 신호.

**퀴즈 구조적 빈틈:** `quiz_answer_integrity` 등 quiz_quality 루브릭은 `QUALITY_CHECK_RESEARCH_BEGINNER` / `QUALITY_CHECK_BUSINESS_BEGINNER`에만 존재. expert/learner 퀴즈는 QC payload에 들어가지만 채점 항목이 없어 정답 오류가 점수에 반영되지 않음.

**운영 퀴즈 감사 (`scripts/audit_daily_quizzes.py`, sol judge, 2026-10-14):**
- 양성 대조군: A-j5 learner 오답 퀴즈 → `wrong_answer` + 올바른 보기 정확히 지목.
- 최근 발행 40 rows (09-15..10-14), 퀴즈 120개, 비용 $0.34, 호출 실패 0.
- expert 38 ok / 2 ambiguous, learner 39 ok / 1 ungrounded, beginner 39 ok / **1 wrong_answer**.
- wrong_answer (직접 확인): `2026-09-25-business-digest-ko` beginner — 해설은 "허가·파트너 가용성 필요"를 설명하는데 정답은 "모든 상점이 자동 연결" (명백한 오답). EN 퀴즈는 정상. `_repair_quiz_answer_from_explanation`은 원인 아님 (직접 실행: 어느 쪽에서 시작해도 변경 없음). 한국어는 조사 붙은 토큰 때문에 support score가 낮아 repair 임계값(5)에 못 미쳐 **KO에서는 사실상 동작 안 함**. → gpt-5-mini 생성 오류를 repair가 못 잡은 것.
- ambiguous 2 / ungrounded 1은 판단 여지가 있는 항목으로 수동 검증 안 함.
- 결론: 현행 운영 퀴즈 오답률 ~1% (1/120). 이 감사에서 beginner 퀴즈 오답은 beginner QC 루브릭이 있는데도 발행됨 (해당 글 QC가 잡지 못함).
- **조치 (2026-10-14, Amy 승인):** `2026-09-25-business-digest-ko` `guide_items.quiz_poll_beginner.answer`를 올바른 보기로 수정 (status published 유지, 다른 필드 불변 확인). 해당 퀴즈 `quiz_responses` 0건이라 기존 응답 영향 없음. 원본 백업: `backend/output/quiz-fixes/` (gitignore). CDN 캐시(s-maxage ≤ 3600)로 최대 1시간 후 반영.
- 후보 조합:
  - A: main=`gpt-6.1-sol`, light/reasoning/nano=`gpt-6-luna`
  - B: main=`gpt-6.1-sol`, reasoning(QC)=`gpt-6.1-sol`, light/nano=`gpt-6-luna`
- 지표: quality score (rubric v2 sub-score), locale_integrity 이슈 수, JSON parse 실패/재시도 수, run당 비용, 소요시간
- 완료 기준: 기준선 대비 quality score -3 이내 + 비용 증가 허용 범위 내(Amy 결정)인 조합 선택
- 예상 비용: 조합당 날짜 1개 ~$1 내외 (추정)

### Task 1.6: 퀴즈 정답 검증 단계 (cutover 선행 조건)
배경: Task 1.4 퀴즈 감사 참조. 현재 오답 퀴즈가 발행까지 가는 경로가 3겹으로 열려 있음 — (1) 생성 모델 오류, (2) `_repair_quiz_answer_from_explanation`이 KO에서 사실상 미동작 (조사 붙은 토큰으로 support score 미달), (3) QC quiz 루브릭은 beginner 프롬프트에만 존재.
- [ ] `_generate_digest_quizzes` 이후, 저장 전에 퀴즈별 정답 검증 호출 추가. `scripts/audit_daily_quizzes.py`의 프롬프트 + strict schema 재사용 (대조군·운영 120개로 검증됨). judge는 `openai_model_reasoning`
- [ ] verdict `wrong_answer`: `better_option`이 options 안에 있으면 answer 교체 + 로그, 아니면 해당 퀴즈 재생성 1회 → 실패 시 drop. `ambiguous`/`ungrounded`: 재생성 1회 → 실패 시 drop (오답 노출보다 퀴즈 없음이 나음 — Amy 확인 필요)
- [ ] 결과를 `pipeline_logs` `quiz_verify:{type}` 단계로 기록 (cost 포함)
- [ ] 테스트: wrong_answer 교체 / 재생성 / drop 분기, verify 호출 실패 시 fail-open(기존 퀴즈 유지) 여부 결정
- 예상 비용: 퀴즈 12개/일 × ~$0.003 ≈ $0.04/일
- 별도 검토: expert/learner QC 프롬프트에 quiz_answer_integrity 추가 여부 (검증 단계가 있으면 중복일 수 있음)

### Task 1.7: Auto-publish threshold 재보정 (NQ-30 흡수)
- [ ] sol judge로 최근 발행분(예: 09-15..10-14) quality-only 재채점 → 점수 분포 확인 (`--rescore` 또는 비파괴 경로 재사용)
- [ ] 현행 threshold로 sol 점수 적용 시 auto-publish 비율 변화 측정 → threshold 결정 (Amy)
- [ ] cap 규칙(`major_source_cap_84` 등) 재검토: major 판정 하나로 10점 단위 하락하는 이진 구조. sol은 일관적이라 문제가 줄지만, cap 값 자체가 새 분포에 맞는지 확인

### Task 1.5: Cutover
- 선행 조건: Task 1.6 (퀴즈 검증) 배포, Task 1.7 (threshold) 결정, advisor reasoning role 처리 결정
- [ ] `core/config.py` 기본값 + `.env.example` 갱신 (위 "역할별 목표 모델" 표 기준)
- [ ] **Railway env `OPENAI_MODEL_*` 4개 갱신** (Amy, 대시보드)
- [ ] 첫 daily run 후 `pipeline_logs` 에서 model/tokens/cost/empty-response 확인
- [ ] 3일 관찰 후 gpt-5 가격 엔트리 및 gpt-5 전용 분기 정리
- 마감: 2026-11-15 (하드 마감 2026-12-11)

## Phase 2 — 뉴스 파이프라인 품질 점검

- [ ] 9/22, 9/28 research digest가 draft로 남은 이유 (auto-publish threshold vs 실패) — NQ-30 연계
- [ ] 최근 30일 quality score 분포, auto-publish 비율
- [ ] 4~5월 관찰 항목(NP-OBSERVE, NQ-30~35, NQ-42, NQ-44) close/drop 결정

## Phase 3 — 정리

- [ ] ACTIVE_SPRINT.md 리셋 (4/22 이후 미반영, Current Doing done row 9개 + ghost 2개)
- [ ] 루트 `CLAUDE.md` Stack의 모델 표기 갱신 (현재 gpt-4.1 / o4-mini로 stale)
- [ ] 미커밋 변경 4개(`pipelineRunLogs.js`, `publicTermIndex.ts`, pagination test, public-term-index test) 의도 확인 후 커밋/폐기
- [ ] `pydantic-ai` 의존성 제거 검토

## Open Questions

1. undated `gpt-5` alias 처리 방식 — 현재 종료 대상 snapshot으로 resolve 확인. 12/11 이후 동작은 문서 미명시
2. ~~GPT-6 Flex 지원 여부~~ — 지원 확인 (Task 1.2)
3. A/B 비파괴 실행 경로 — Task 1.4 착수 시
4. 비용 증가 허용 상한 — Amy 결정
