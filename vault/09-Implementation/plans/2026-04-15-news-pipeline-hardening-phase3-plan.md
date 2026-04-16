# Phase 3 — Prompt Hygiene & Token Diet Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프롬프트 dead-code 정리 + 의미 손실 없는 토큰 축소 + `ranking.py`의 user-only 메시지 패턴을 system+user 분리로 정상화. 신호 손실 0, 코드 가독성·토큰 효율 ↑.

**Architecture:** 4개 chunk로 나눠 단계별 진행. 각 chunk는 독립적으로 rollback 가능. 토큰 로깅은 이미 구현돼 있어 before/after 비교는 pipeline_logs에서 SQL로 측정. TDD는 prompt 내용 변경보다 "output shape 유지" 검증에 집중.

**Tech Stack:** Python 3.11 / FastAPI / Supabase / pytest / ruff

**Spec reference:** [2026-04-15-news-pipeline-hardening-design.md](2026-04-15-news-pipeline-hardening-design.md) §6 (Phase 3)

---

## Critical Constraints (read before starting)

1. **Baseline (Phase 2 + API diet 완료 후 2026-04-16)**: 9 pre-existing pytest 실패, 158 passing, 4 pre-existing ruff 에러 in `advisor.py`. **이 숫자가 늘어나면 회귀.**

2. **토큰 로깅은 이미 있음**: `backend/services/pipeline.py` L373-398의 `_log_stage` 함수가 OpenAI response의 `usage.input_tokens`, `usage.output_tokens`, `usage.tokens_used`를 `pipeline_logs.debug_meta`에 자동 저장. **새로 만들 필요 없음** — 측정 SQL만 준비.

3. **Prompt dead code 위치 확정 (2026-04-16 검증)**:
   - `EXPERT_TITLE_STRATEGY`: L581 (dead) → L1048 (active)
   - `LEARNER_TITLE_STRATEGY`: L608 (dead) → L1080 (active)
   - `ONE_LINE_SUMMARY_RULE`: L670 (dead) → L1108 (active)
   - Python 재할당으로 L1048+ 버전이 `TITLE_STRATEGY_MAP` (L1132)에 쓰임. L581~708의 옛 정의는 **완전히 도달 불가능**.
   - 단, L581-L708 구간에 `HALLUCINATION_GUARD` (L639), `FRONTLOAD_LOCALE_PARITY` (L644), `LEARNER_KO_LANGUAGE_RULE` (L685)는 **dead 아님** — 독립 상수. 조심해서 삭제.

4. **`ranking.py` messages 패턴 재확인 (2026-04-16 검증)**:
   - `classify_candidates` (L71): ✅ system+user (정상)
   - `merge_classified` (L183): ✅ system+user (정상)
   - `rank_classified` (L329): ✅ system+user (정상, user는 짧음)
   - `summarize_community` (L452): ❌ **user-only** ← **유일한 수정 대상**

5. **Phase 2의 Few-shot 예시 (2026-04-16 추가분)**는 `EXPERT_TITLE_STRATEGY` (L1048), `LEARNER_TITLE_STRATEGY` (L1080), `LEARNER_KO_LANGUAGE_RULE` (L685)에 들어 있음 → 토큰 축소 시 **Few-shot 보존 필수**.

6. **CLAUDE.md 정책**: main-only 워크플로, NO `Co-Authored-By` 트레일러.

---

## File Structure (target after Phase 3)

```
backend/
├── services/
│   └── agents/
│       ├── prompts_news_pipeline.py    # MODIFY: dead code 삭제 + 의미 손실 없는 단어 축약
│       └── ranking.py                   # MODIFY: summarize_community system+user 분리
├── scripts/
│   └── measure_token_usage.py           # CREATE: baseline + after 측정 script
└── tests/
    └── test_news_digest_prompts.py     # MODIFY (if needed): 삭제 대상이 직접 참조되는지만 확인

vault/09-Implementation/plans/
└── 2026-04-15-news-pipeline-hardening-design.md  # MODIFY: Phase 3 Evidence 기록
```

---

## Chunk 1: Token Usage Baseline Measurement (Task 1)

**목적**: Phase 3 작업 전·후 비교 가능하도록 baseline 기록.
**기간**: ~1시간.

### Task 1: Measurement script + baseline record

**Files:**
- Create: `backend/scripts/measure_token_usage.py`
- Create (나중에 Phase 3 종료 시 update): `vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md` §Phase 3 Evidence

- [ ] **Step 1.1: Baseline 테스트**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 158 passed` (현 baseline).

- [ ] **Step 1.2: Measurement script 작성**

`backend/scripts/measure_token_usage.py` 생성:
```python
"""Measure prompt token usage per pipeline stage from pipeline_logs.

Phase 3 Task 1 of 2026-04-15-news-pipeline-hardening.

Computes rolling averages over the last N days to enable before/after
comparison of prompt token reduction work.

Usage:
    cd backend && python scripts/measure_token_usage.py
    cd backend && python scripts/measure_token_usage.py --days 3   # shorter window
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    rows = (
        supabase.table("pipeline_logs")
        .select("pipeline_type, tokens_used, debug_meta, created_at")
        .gte("created_at", cutoff)
        .execute()
        .data or []
    )

    news_stages = {
        "classify", "merge", "community_summarize", "ranking", "enrich",
        "digest:research:expert", "digest:research:learner",
        "digest:business:expert", "digest:business:learner",
        "quality:research", "quality:business",
    }

    by_stage_total: dict[str, list[int]] = defaultdict(list)
    by_stage_input: dict[str, list[int]] = defaultdict(list)
    by_stage_output: dict[str, list[int]] = defaultdict(list)
    per_run_totals: dict[str, int] = defaultdict(int)

    for r in rows:
        stage = r.get("pipeline_type")
        if stage not in news_stages:
            continue
        total = r.get("tokens_used") or 0
        meta = r.get("debug_meta") or {}
        input_tok = meta.get("input_tokens") or 0
        output_tok = meta.get("output_tokens") or 0
        if total:
            by_stage_total[stage].append(total)
        if input_tok:
            by_stage_input[stage].append(input_tok)
        if output_tok:
            by_stage_output[stage].append(output_tok)
        # group by created_at date for per-run aggregation
        d = (r.get("created_at") or "")[:10]
        if d and total:
            per_run_totals[d] += total

    print(f"\n=== Token usage over last {args.days} days ===\n")
    print(f"Stages observed: {len(by_stage_total)} / {len(news_stages)}")
    print(f"Daily aggregates (approx per-run totals): {dict(sorted(per_run_totals.items()))}\n")

    print(f"{'Stage':<30} {'N':>4} {'Avg total':>11} {'Avg input':>11} {'Avg output':>11}")
    print("-" * 72)
    for stage in sorted(by_stage_total.keys()):
        totals = by_stage_total[stage]
        inputs = by_stage_input.get(stage, [])
        outputs = by_stage_output.get(stage, [])
        avg_total = sum(totals) / len(totals) if totals else 0
        avg_in = sum(inputs) / len(inputs) if inputs else 0
        avg_out = sum(outputs) / len(outputs) if outputs else 0
        print(f"{stage:<30} {len(totals):>4} {avg_total:>11.0f} {avg_in:>11.0f} {avg_out:>11.0f}")

    grand_total_per_day = sum(per_run_totals.values()) / max(len(per_run_totals), 1)
    print(f"\nAverage total tokens per daily run: {grand_total_per_day:.0f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.3: 실행 + baseline 캡처**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe scripts/measure_token_usage.py --days 7 2>&1 | tee /tmp/token_baseline_before.txt
```
Expected: stage별 평균 토큰 + daily aggregate 출력. 스크린 캡처 필요 없고 /tmp 파일로 보관.

- [ ] **Step 1.4: Baseline 수치를 design.md Phase 3 Evidence 섹션에 기록**

`vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md`의 Phase 3 Evidence 블록을 찾아 업데이트:
```markdown
### Phase 3 — Baseline (2026-04-17 기준, Phase 3 시작 전)

**Daily total (7일 평균)**: XXX,XXX tokens/run

**Per-stage avg (input / output / total)**:
| Stage | input | output | total |
|---|---|---|---|
| classify | ... | ... | ... |
| merge | ... | ... | ... |
| digest:research:expert | ... | ... | ... |
| ... | | | |

(Step 1.3의 script 출력을 직접 붙여넣음)
```

- [ ] **Step 1.5: Commit**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/scripts/measure_token_usage.py vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
git commit -m "feat(scripts): add token usage measurement + record 7-day baseline for Phase 3"
```

---

## Chunk 2: Dead Code Cleanup (Task 2)

**목적**: Shadow되어 도달 불가능한 상수 정의 제거. 파일 길이 축소, 읽는 사람 혼란 제거.
**기간**: ~30분. **위험**: 낮음 (Python 재할당으로 이미 실행에서 배제된 코드 삭제).

### Task 2: Remove dead EXPERT/LEARNER_TITLE_STRATEGY + ONE_LINE_SUMMARY_RULE

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (L581-638, L670-683)

- [ ] **Step 2.1: Dead code가 진짜 도달 불가능한지 추가 확인 — 직접 참조 grep**

```bash
cd c:/Users/amy/Desktop/0to1log/backend && grep -rn "EXPERT_TITLE_STRATEGY\|LEARNER_TITLE_STRATEGY\|ONE_LINE_SUMMARY_RULE" services/ tests/ 2>&1 | grep -v __pycache__
```

Expected: 정의 위치 2개씩 (L581+L1048, L608+L1080, L670+L1108) + map에서 참조 (L1132 or nearby) + 함수 내부 사용처. 함수 내 사용은 `TITLE_STRATEGY_MAP`과 `_build_digest_prompt` 등을 통한 간접 참조가 대부분. **직접 import (`from ... import EXPERT_TITLE_STRATEGY`)가 없어야 함** — 있으면 제거 불가능한 경우이므로 보고.

- [ ] **Step 2.2: 현재 shadow 확인 — Python runtime test**

```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import EXPERT_TITLE_STRATEGY, LEARNER_TITLE_STRATEGY, ONE_LINE_SUMMARY_RULE
# Check which version is active (L1048+ should win by Python assignment order)
print('EXPERT len:', len(EXPERT_TITLE_STRATEGY))
print('LEARNER len:', len(LEARNER_TITLE_STRATEGY))
print('ONE_LINE len:', len(ONE_LINE_SUMMARY_RULE))
print('EXPERT head:', EXPERT_TITLE_STRATEGY[:100])
"
```

L1048 버전이 L581보다 더 짧은 "sharp news editor" 스타일이면 L1048가 active. 길이 출력과 head로 확인.

- [ ] **Step 2.3: L581-L708 구간 정확히 삭제 (HALLUCINATION_GUARD + FRONTLOAD_LOCALE_PARITY + LEARNER_KO_LANGUAGE_RULE 보존)**

삭제 대상:
- `EXPERT_TITLE_STRATEGY = """..."""` at L581-606 (~26 lines)
- `LEARNER_TITLE_STRATEGY = """..."""` at L608-637 (~30 lines)
- `ONE_LINE_SUMMARY_RULE = """..."""` at L670-683 (~14 lines)

**보존 대상** (이 구간 안에 있지만 dead 아님):
- `HALLUCINATION_GUARD = """..."""` at L639-642
- `FRONTLOAD_LOCALE_PARITY = """..."""` at L644-668
- `LEARNER_KO_LANGUAGE_RULE = """..."""` at L685-708 (with Phase 2 Few-shot)

**명시적 삭제 범위 3개** (구현자는 3회 분리 Edit 호출):
- Block 1: `EXPERT_TITLE_STRATEGY = """..."""` — L581~L606 (약 26줄, "## Title Strategy" 시작, 해당 상수의 closing `"""` 다음 빈 줄까지)
- Block 2: `LEARNER_TITLE_STRATEGY = """..."""` — L608~L637 (약 30줄)
- Block 3: `ONE_LINE_SUMMARY_RULE = """..."""` — L670~L683 (약 14줄)

각 Edit의 `old_string`은 해당 상수 정의 전체(할당 라인 + 문자열 본문 + closing """)만 포함. 인접한 `HALLUCINATION_GUARD`(L639), `FRONTLOAD_LOCALE_PARITY`(L644), `LEARNER_KO_LANGUAGE_RULE`(L685) 건드리지 않음.

- [ ] **Step 2.4: Active constant 사용 검증**

```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import (
    EXPERT_TITLE_STRATEGY, LEARNER_TITLE_STRATEGY, ONE_LINE_SUMMARY_RULE,
    HALLUCINATION_GUARD, FRONTLOAD_LOCALE_PARITY, LEARNER_KO_LANGUAGE_RULE,
    TITLE_STRATEGY_MAP,
)
# Verify active versions are still usable
assert 'Title Strategy' in EXPERT_TITLE_STRATEGY
assert 'Title Strategy' in LEARNER_TITLE_STRATEGY
assert 'One-Line Summary' in ONE_LINE_SUMMARY_RULE
assert TITLE_STRATEGY_MAP['expert'] == EXPERT_TITLE_STRATEGY
assert TITLE_STRATEGY_MAP['learner'] == LEARNER_TITLE_STRATEGY
# Phase 2 Few-shot examples are still in the active versions
assert 'Meta commits 1GW' in EXPERT_TITLE_STRATEGY  # Few-shot signature
assert 'OpenAI will run enterprise AI' in LEARNER_TITLE_STRATEGY  # Few-shot signature
assert 'natural Korean vs literal' in LEARNER_KO_LANGUAGE_RULE or 'literal translation' in LEARNER_KO_LANGUAGE_RULE
print('Active constants + Few-shot preserved OK')
"
```
Expected: `Active constants + Few-shot preserved OK`. Assert 실패 시 삭제가 잘못된 블록을 건드린 것 → 롤백.

- [ ] **Step 2.5: 관련 테스트 실행**

```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/test_news_digest_prompts.py -v --tb=short 2>&1 | tail -10
```
Expected: 25 tests PASS (전부).

- [ ] **Step 2.6: Full suite 회귀 검증**

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 158 passed` (baseline 유지).

- [ ] **Step 2.7: Ruff**
```bash
cd backend && ./.venv/Scripts/ruff.exe check services/agents/prompts_news_pipeline.py
```
Expected: clean.

- [ ] **Step 2.8: 파일 크기 감소 확인**

```bash
wc -l backend/services/agents/prompts_news_pipeline.py
```
Expected: 이전 1840줄 → ~1770줄 (~70줄 감소).

- [ ] **Step 2.9: Commit**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "refactor(prompts): remove shadowed dead-code duplicates of TITLE_STRATEGY/ONE_LINE_SUMMARY_RULE

Python re-assignment made L1048/L1080/L1108 the active versions used by
TITLE_STRATEGY_MAP. The older L581-L637/L670-L683 blocks were unreachable.
Removed the unreachable definitions; HALLUCINATION_GUARD, FRONTLOAD_LOCALE_PARITY,
LEARNER_KO_LANGUAGE_RULE (adjacent live code in the same region) preserved.

File: 1840 → ~1770 lines."
```

---

## Chunk 3: Prompt Token Reduction (Task 3)

**목적**: 의미 유지하면서 중복/장황한 부분을 축약. Few-shot은 보존.

**Done 기준 (명확)**: 5개 주요 프롬프트 **total net -1250 토큰 이상** 감소 (spec §6.2의 "평균 250 토큰/프롬프트" 기준). 개별 프롬프트는 -100~500 범위에서 자유롭게; 총합이 -1250 이상이면 통과.
**기간**: 2~3시간. **위험**: 중간 (프롬프트 수정 시 digest 품질에 직접 영향).

⚠️ **이 chunk는 한 번에 모든 프롬프트를 건드리지 않고 2개 프롬프트씩 점진적으로 수정 → 각 수정 후 daily cron 검증**.

### Task 3: Target 1 — CLASSIFICATION_SYSTEM_PROMPT

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (L4-76, CLASSIFICATION_SYSTEM_PROMPT)

- [ ] **Step 3.1: 현재 프롬프트 읽고 축약 대상 식별**

L4-76 읽기. 주요 축약 후보:
1. Category 설명 중 장황한 예시 (단축 가능)
2. "Rules" 섹션의 반복 (중복 지시)
3. Litmus test의 "IF BOTH answers are NO" 설명 단순화

**원칙**: 의미 보존 필수. 아래 핵심은 절대 제거 금지:
- Category 정의 (Research/Business)
- Litmus test (분류 품질 핵심)
- Event dedup rules (Phase 2에서 확인된 hardening)
- Output JSON format spec

- [ ] **Step 3.2: 수정 적용 (example diff, 실제 수정은 구현자 판단)**

예시 축약 방향:
```python
# Before (L8-11 근처):
# "Target reader: AI research engineer tracking technical developments.
#  An article belongs here ONLY if its core story is a technical artifact or technical contribution."
# After:
# "Target reader: AI research engineer. Article belongs here ONLY if core story is a technical artifact/contribution."

# Before (L22 근처 litmus test):
# "Litmus test — before assigning ANY article to Research, ask:
#  \"Does this article discuss a model, a codebase, or a paper/technical report as the MAIN subject?\"
#  \"Would an AI research engineer learn something technical from this article?\"
#  If BOTH answers are NO → assign to Business, even if the topic is AI-related technology."
# After:
# "Litmus test: Is the MAIN subject a model/codebase/paper? Would a research engineer learn
#  something technical? If both answers are NO → Business."
```

- [ ] **Step 3.3: 토큰 측정 전후**

```bash
cd backend && ./.venv/Scripts/python.exe -c "
import tiktoken
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT
enc = tiktoken.encoding_for_model('gpt-4')
print('CLASSIFICATION tokens:', len(enc.encode(CLASSIFICATION_SYSTEM_PROMPT)))
"
```
Expected: before 수정 vs after 수정에서 -100~200 토큰 차이.

**주의**: `tiktoken` 패키지가 설치돼 있지 않으면:
```bash
cd backend && ./.venv/Scripts/pip.exe install tiktoken
```

- [ ] **Step 3.4: 프롬프트 테스트**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_news_digest_prompts.py -v --tb=short 2>&1 | tail -10
```
Expected: 25 tests PASS. 만약 기존 테스트가 프롬프트 본문의 특정 phrase를 assert하고 있으면, 그 assertion에 맞는 phrase는 보존하거나 테스트를 함께 수정 (보존 권장).

- [ ] **Step 3.5: Full regression + ruff**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
cd backend && ./.venv/Scripts/ruff.exe check services/agents/prompts_news_pipeline.py
```
Expected: baseline 유지 + ruff clean.

- [ ] **Step 3.6: Commit**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "refactor(prompts): tighten CLASSIFICATION_SYSTEM_PROMPT phrasing (-XXX tokens)"
```

### Task 4: Target 2 — QUALITY_CHECK_* consolidation

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (L1355-1724, 5 QUALITY_CHECK_* constants)

4개의 `QUALITY_CHECK_RESEARCH_EXPERT` / `QUALITY_CHECK_RESEARCH_LEARNER` / `QUALITY_CHECK_BUSINESS_EXPERT` / `QUALITY_CHECK_BUSINESS_LEARNER` + 1개 `QUALITY_CHECK_FRONTLOAD`는 상당한 구조 중복이 있을 가능성 높음.

- [ ] **Step 4.1: 4개 유사 프롬프트의 공통 구조 추출**

```bash
cd backend && ./.venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import (
    QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER,
    QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER,
)
# 4개 프롬프트의 중복 영역 찾기
for name, p in [
    ('RESEARCH_EXPERT', QUALITY_CHECK_RESEARCH_EXPERT),
    ('RESEARCH_LEARNER', QUALITY_CHECK_RESEARCH_LEARNER),
    ('BUSINESS_EXPERT', QUALITY_CHECK_BUSINESS_EXPERT),
    ('BUSINESS_LEARNER', QUALITY_CHECK_BUSINESS_LEARNER),
]:
    lines = p.split(chr(10))
    print(f'{name}: {len(lines)} lines, {len(p)} chars')
"
```

**결정 규칙 (명확)**: 두 프롬프트 쌍의 공통 라인 비율을 `difflib.SequenceMatcher.ratio()`로 측정:

```python
import difflib
pairs = [
    ('RESEARCH_EXPERT', 'RESEARCH_LEARNER'),
    ('BUSINESS_EXPERT', 'BUSINESS_LEARNER'),
    ('RESEARCH_EXPERT', 'BUSINESS_EXPERT'),
]
# For each pair, compute ratio. If any pair >= 0.70 → Option A. Else Option B.
```

- [ ] **Step 4.2: 접근 결정 (ratio 기반)**

**Option A — 어느 쌍이든 ratio >= 0.70**: common template 상수 1개 + 4개 버전이 f-string으로 생성. 구체 예시는 구현자가 코드 보고 설계.

**Option B — 모든 쌍의 ratio < 0.70**: 추출 비효율, 각 프롬프트 내부의 장황한 부분만 개별 축약.

- [ ] **Step 4.3: 수정 + 토큰 측정**

Step 3.3과 동일한 tiktoken 기반 측정. Total for 5 quality prompts before/after.

- [ ] **Step 4.4: 테스트 + 회귀**
Step 3.4, 3.5 반복.

- [ ] **Step 4.5: Commit**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "refactor(prompts): consolidate QUALITY_CHECK_* prompts (-XXX tokens total)"
```

### Task 5 (조건부): Additional targets if budget remains

**Trigger 규칙**: Chunk 3 Task 4 종료 후 cumulative net 감소가 `-1250 토큰 미만`이면 Task 5 실행. 이미 `-1250 이상` 달성했으면 **skip**.

디지스트 persona prompts (`RESEARCH_EXPERT_GUIDE`, `BUSINESS_EXPERT_GUIDE` 등 L346-578)도 검토. 큰 것들 위주로 ~100 토큰/개 cutable할 것으로 추정.

**원칙**: Done criteria (total -1250) 달성되면 여기서 stop. Over-engineering 방지.

- [ ] **Step 5.1: Baseline token 측정 script 재실행 (Chunk 1 complete 후 적용된 프롬프트 기준)**
- [ ] **Step 5.2: 남은 gap 있으면 target 1~2개 추가 선정, 축약**
- [ ] **Step 5.3: Commit (필요시)**

---

## Chunk 4: ranking.py summarize_community Messages Structure (Task 6)

**목적**: `summarize_community`가 사용하는 `messages=[{"role": "user", "content": prompt}]` 패턴을 `system` + `user`로 분리. OpenAI 공식 권고에 맞춤 + 정적/동적 시각 분리.
**기간**: ~30분.

### Task 6: Split summarize_community prompt into system + user

**Files:**
- Modify: `backend/services/agents/ranking.py` (L440-460, `summarize_community`)
- Modify: `backend/services/agents/prompts_news_pipeline.py` (L1800+, `COMMUNITY_SUMMARIZER_PROMPT`) — `{groups_text}` placeholder 분리 필요

- [ ] **Step 6.1: 현재 COMMUNITY_SUMMARIZER_PROMPT 구조 확인**

```bash
cd backend && ./.venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import COMMUNITY_SUMMARIZER_PROMPT
print(COMMUNITY_SUMMARIZER_PROMPT[:500])
print('...')
print(COMMUNITY_SUMMARIZER_PROMPT[-300:])
# 어디에 '{groups_text}' placeholder가 있는지 확인
print('Placeholder at position:', COMMUNITY_SUMMARIZER_PROMPT.find('{groups_text}'))
"
```

- [ ] **Step 6.2: Prompt 상수를 system 부분과 user template로 분리**

`COMMUNITY_SUMMARIZER_PROMPT`를 두 개로:
```python
# Before (single prompt with {groups_text} embedded):
COMMUNITY_SUMMARIZER_PROMPT = """You are an AI community analyst...
[rules]

### Input
{groups_text}

[output format]
"""

# After (split into static system + dynamic user):
COMMUNITY_SUMMARIZER_SYSTEM = """You are an AI community analyst.
[rules]
[output format]
"""

COMMUNITY_SUMMARIZER_USER_TEMPLATE = """### Input
{groups_text}
"""
```

**경계 규칙 (명확)**: `{groups_text}` placeholder가 현재 프롬프트 안 한 곳에 있음 (Step 6.1에서 확인). 그 placeholder가 속한 "### Input\n{groups_text}" 블록과 **그 아래의 모든 것** = user. 그 블록 **위의 모든 것** (rules + output format spec) = system. 즉 `{groups_text}` 마커 이전/이후로 1회 split.

- [ ] **Step 6.3: ranking.py 호출부 수정**

`backend/services/agents/ranking.py` L446-455 영역:
```python
# Before:
prompt = COMMUNITY_SUMMARIZER_PROMPT.format(groups_text=groups_text)
kwargs = build_completion_kwargs(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=2000,
    temperature=0.2,
)

# After:
kwargs = build_completion_kwargs(
    model=model,
    messages=[
        {"role": "system", "content": COMMUNITY_SUMMARIZER_SYSTEM},
        {"role": "user", "content": COMMUNITY_SUMMARIZER_USER_TEMPLATE.format(groups_text=groups_text)},
    ],
    max_tokens=2000,
    temperature=0.2,
)
```

Import 추가 필요:
```python
from services.agents.prompts_news_pipeline import (
    ...existing imports...
    COMMUNITY_SUMMARIZER_SYSTEM,
    COMMUNITY_SUMMARIZER_USER_TEMPLATE,
)
# (COMMUNITY_SUMMARIZER_PROMPT import 제거)
```

- [ ] **Step 6.4: 기존 COMMUNITY_SUMMARIZER_PROMPT 상수 참조 검색**

```bash
cd backend && grep -rn "COMMUNITY_SUMMARIZER_PROMPT" services/ tests/ 2>&1 | grep -v __pycache__
```

만약 다른 곳에서 import하면 **backward-compat re-assign 유지**:
```python
# prompts_news_pipeline.py 끝에 남겨둠:
COMMUNITY_SUMMARIZER_PROMPT = COMMUNITY_SUMMARIZER_SYSTEM + "\n\n" + COMMUNITY_SUMMARIZER_USER_TEMPLATE
# 이후 deprecation warning 주석
```

없으면 삭제.

- [ ] **Step 6.5: Ranking 테스트**

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_ranking.py -v --tb=short 2>&1 | tail -15
```
Expected: 전체 PASS.

- [ ] **Step 6.6: Full regression + ruff**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
cd backend && ./.venv/Scripts/ruff.exe check services/agents/ranking.py services/agents/prompts_news_pipeline.py
```
Expected: baseline 유지 + ruff clean.

- [ ] **Step 6.7: Commit**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/services/agents/ranking.py backend/services/agents/prompts_news_pipeline.py
git commit -m "refactor(ranking): split summarize_community prompt into system + user messages

Previously COMMUNITY_SUMMARIZER_PROMPT was a single monolithic user message.
Splitting into system (static rules + output format) + user (dynamic
groups_text) matches OpenAI best practice and keeps classify/merge/rank
consistent with this path.

No behavior change expected; LLM instruction-following may improve slightly
due to role separation."
```

---

## Chunk 5: Final Verification & Deployment (Task 7-9)

### Task 7: Full regression verification

- [ ] **Step 7.1: 전체 테스트 + ruff + import cycle check**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -10
cd backend && ./.venv/Scripts/ruff.exe check .
cd backend && ./.venv/Scripts/python.exe -c "
import services.pipeline
import services.pipeline_quality
import services.pipeline_digest
import services.pipeline_persistence
import services.agents.ranking
import services.agents.prompts_news_pipeline
print('all imports clean')
"
```
Expected: 9 failed baseline unchanged, 158 passed + any new Phase 3 tests added.

### Task 8: Push + Railway deploy + cron verify

- [ ] **Step 8.1: Push to main**
```bash
cd c:/Users/amy/Desktop/0to1log
git status --short | grep -v "tmp-\|^??" | head
git log origin/main..HEAD --oneline
git push origin main
```

- [ ] **Step 8.2: Railway 배포 대기 (~3-5분) + health check**

Railway URL은 `.env`의 `FASTAPI_URL` 또는 Railway dashboard에서 확인 가능. 대안: dashboard에서 build success 로그만 확인해도 충분.
```bash
# Example (replace with actual domain):
curl https://<your-railway-domain>/health
```
Expected: `{"status": "ok"}`

- [ ] **Step 8.3: 다음 cron 실행 대기 OR manual trigger**

- [ ] **Step 8.4: After token 측정**
```bash
cd backend && ./.venv/Scripts/python.exe scripts/measure_token_usage.py --days 3 2>&1 | tee /tmp/token_after.txt
```
비교: baseline vs 3일 평균. Expected: net 토큰 감소.

- [ ] **Step 8.5: 품질 점수 회귀 확인 (SQL)**

```sql
-- Replace <Phase 3 start date> at runtime with the date Phase 3 deployment landed (YYYY-MM-DD)
select pipeline_batch_id, post_type,
       quality_score,
       fact_pack->'quality_breakdown'->'raw_llm' as raw_scores
from news_posts
where pipeline_batch_id >= '<Phase 3 start date>'
order by pipeline_batch_id desc, post_type, locale;
```
Expected: Phase 2의 raw_llm 점수와 비교 시 ±5 이내 변동. 큰 하락 없음.

### Task 9: Evidence 기록 + Phase 3 공식 complete

- [ ] **Step 9.1: design.md Phase 3 Evidence 섹션 업데이트**

[2026-04-15-news-pipeline-hardening-design.md](2026-04-15-news-pipeline-hardening-design.md)의 Evidence §Phase 3에:
- Commit hashes
- Baseline vs After 토큰 수치 (script 출력)
- 3일 평균 품질 점수 변화 (회귀 없음)
- 파일 라인 수 변화 (prompts_news_pipeline.py before/after)

- [ ] **Step 9.2: Status 업데이트**

design.md의 frontmatter `status`를 `phase 3 complete (YYYY-MM-DD)`로 변경.

- [ ] **Step 9.3: Final commit + push**
```bash
cd c:/Users/amy/Desktop/0to1log
git add vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
git commit -m "docs(plans): mark Phase 3 complete — token diet + ranking.py hygiene"
git push origin main
```

---

## Done Criteria Checklist (spec §6.2 mapping)

- [ ] Token usage logging이 `debug_meta`에 기록 (이미 존재 — Chunk 1에서 확인)
- [ ] 7일 baseline 토큰 사용량이 design.md Evidence에 기록 (Task 1)
- [ ] 5개 주요 프롬프트에서 net 250 토큰/프롬프트 이상 감소 (Task 2+3+4+선택적5)
- [ ] `ranking.py`의 `summarize_community`가 system+user 2-메시지 구조로 변경 (Task 6). 나머지 3개(classify/merge/rank)는 **이미 system+user**였음 → spec의 "4개 호출" 목표는 1곳만 실제로 필요했음으로 조정.
- [ ] 변경 후 daily cron 최소 1회 정상 실행 (Task 8)
- [ ] Phase 3 종료 후 3일 평균 토큰 사용량 < Phase 3 시작 전 7일 평균 baseline (Task 8.4)

---

## Risks & Pitfalls

1. **Prompt 수정으로 품질 회귀 발생 가능**. 각 prompt 수정 commit마다 그 다음 daily cron 결과를 모니터링. 큰 점수 하락 시 즉시 revert.

2. **Few-shot 예시 실수로 삭제**. Chunk 2의 dead code 삭제 시 L685 `LEARNER_KO_LANGUAGE_RULE` (Phase 2 Few-shot 포함)을 건드리지 않게 주의. Step 2.4의 assertion으로 확인.

3. **QUALITY_CHECK_* consolidation 과도**. 4개 프롬프트가 persona별 고유 역할이 있으므로 완전히 하나로 합치면 안 됨. Common frame만 추출하고 persona-specific 부분은 유지.

4. **`COMMUNITY_SUMMARIZER_PROMPT` backward-compat**. 만약 외부에서 import하는 곳이 있으면 re-assign 유지. 없으면 삭제. Step 6.4에서 확인.

5. **Tiktoken 계산 오차**. tiktoken의 "gpt-4" encoding과 실제 API 사용 모델(gpt-4.1-mini/gpt-4.1 등)의 토큰화가 미세 차이 있을 수 있음. 비교에는 충분, 절대 수치 해석은 ±5% 여유 가정.

6. **Daily cron의 LLM judge calls가 non-deterministic**. 품질 점수는 run마다 ±3 정도 변동 있음. 회귀 판단 시 3일 평균 사용.

---

## Estimated Total Effort
- Chunk 1 (measurement): 1시간
- Chunk 2 (dead code cleanup): 30분
- Chunk 3 (token reduction): 2~3시간
- Chunk 4 (messages split): 30분
- Chunk 5 (verification + deploy): 30분 + cron 대기 (~하루)

**Total: 5~6시간 code work + 1일 production 검증 대기**

Spec §6.3의 "2~3일" 예상보다 짧아졌음 — scope이 실제로 더 작았던 것이 주 원인.
