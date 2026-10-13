# News Pipeline 점검 + GPT-6 마이그레이션 Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) 9/29부터 멈춘 daily/weekly 자동 실행을 복구하고 재발 감지를 추가한다. (2) 2026-12-11 종료되는 gpt-5 계열을 GPT-6 계열로 교체하되, 품질 점수와 run당 비용을 측정해 역할별 모델을 결정한다.

**Decision (2026-10-13, Amy):** 대체 모델은 OpenAI 권장 1:1 대체(GPT-5.6)가 아닌 **최신 GPT-6 계열** 사용.

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
- [ ] 2026-10-14 07~08시 KST 자동 실행에서 새 run row + `success` 확인
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
- [ ] 같은 날짜 입력으로 gpt-5 기준선 vs GPT-6 후보 조합 실행. published 보호(422)를 건드리지 않는 비파괴 경로 확인 필요 (로컬 dry-run 또는 별도 batch_id) — **방법 미정, 착수 시 grep으로 기존 경로부터 확인**
- 후보 조합:
  - A: main=`gpt-6.1-sol`, light/reasoning/nano=`gpt-6-luna`
  - B: main=`gpt-6.1-sol`, reasoning(QC)=`gpt-6.1-sol`, light/nano=`gpt-6-luna`
- 지표: quality score (rubric v2 sub-score), locale_integrity 이슈 수, JSON parse 실패/재시도 수, run당 비용, 소요시간
- 완료 기준: 기준선 대비 quality score -3 이내 + 비용 증가 허용 범위 내(Amy 결정)인 조합 선택
- 예상 비용: 조합당 날짜 1개 ~$1 내외 (추정)

### Task 1.5: Cutover
- [ ] `core/config.py` 기본값 + `.env.example` 갱신
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
