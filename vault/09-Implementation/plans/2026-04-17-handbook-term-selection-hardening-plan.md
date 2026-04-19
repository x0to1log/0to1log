# Handbook Term Selection Hardening — Implementation Plan

> **Status (as of 2026-04-19):** ✅ **COMPLETE — all four chunks shipped.** See the [Completion & Retro](#completion--retro-2026-04-19) section at the bottom for the commit map, detour story, and deferred items.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close four root-cause gaps in the handbook term selection pipeline so that (1) the queue system actually accumulates items, (2) Korean naming failures are caught at code level, (3) out-of-scope (HR/regulatory) terms are rejected with structured logs, and (4) fabricated compound entities are routed to queue for manual review.

**Architecture:**
Each fix is a "prompt says X but no code gate enforces X" problem. The pipeline's generation/extraction prompts already describe intent correctly; the failures happen because code doesn't validate what the LLM actually returned. We add a small `handbook_validators.py` module (pre-insertion gates, pure functions) and wire three routing disposition paths: **accept / queue / reject-and-log**. A Pydantic schema bug (missing `confidence` field in `ExtractedTerm`) is fixed first since every other chunk depends on the queue being alive.

**Tech Stack:** Python 3.11, Pydantic v2, Supabase client, pytest. No new dependencies.

---

## Context & Motivation

See discussion on 2026-04-16/17 and the prior Explore diagnoses. Amy's long-term plan is seed-list parallel regeneration; the selection/validation hardening here is **Phase 1** of that roadmap (stop the source of garbage before doing mass regen).

Four observed failure samples Amy had to manually delete or archive:

| Sample | Pattern | Root layer |
|---|---|---|
| `acquihire`, `ISO 42001` | **A** — out-of-scope (HR / regulatory) | Extraction prompt + no domain exclusion |
| `OpenAI Frontier` | **B** — fabricated compound entity | No source-verbatim grounding |
| `LLM Internals` → `LLM 인디나스(Internals)` | **C** — phonetic transliteration | No Korean-name code gate |
| `ISO 42001 · ISO 42001` | **C** — identical KO=EN (pending Chunk A fix to prevent upstream) | No Korean-name code gate |

Plus a blocking prerequisite discovered during diagnosis:

**Queue bug (Chunk 0):** `confidence` field is in `EXTRACT_TERMS_PROMPT` output spec but missing from the `ExtractedTerm` Pydantic model. Pydantic's default `extra="ignore"` silently strips it. The downstream `if confidence == "low": queued_terms.append(...)` gate thus never fires.

## 3-bucket Disposition Design

| Pattern | Disposition | Rationale |
|---|---|---|
| A (out-of-scope) | **reject + structured log** (to `pipeline_logs`) | Amy already judged these as wrong — no need to re-surface. Logs enable weekly pattern review. |
| B (ambiguous entity) | **queue** (`handbook_terms.status = 'queued'`) | Judgment call; Amy reviews in admin UI. |
| C (Korean failure) | **queue** (generation succeeds, Korean flagged) | Term body may be salvageable; only Korean needs manual fix. |

## Non-Goals

- Seed-list parallel regeneration infrastructure (later sprint).
- Rewriting the entire advisor prompt architecture.
- LLM-judge post-hoc validation (we already decided in the prior handbook measurement plan to NOT add LLM judges here).
- Cleaning up existing bad terms in `handbook_terms` (seed regen handles that).
- Fixing the admin UI review flow for queued items (separate concern; this plan produces the data, UI work is independent).

---

## File Structure

| File | Purpose | Status |
|---|---|---|
| `backend/models/advisor.py` | Add `confidence` field to `ExtractedTerm` + `extra="allow"` config | Modify |
| `backend/services/handbook_validators.py` | Pure pre-insertion gate functions (Korean, scope, grounding) | Create |
| `backend/tests/test_handbook_validators.py` | Unit tests per validator | Create |
| `backend/services/handbook_quality_config.py` | Extend with `IMPORTANT_NON_TECH_ALLOWLIST`, `GLOBAL_NAME_PATTERNS`, `HR_REGULATORY_BLOCKLIST` | Modify |
| `backend/services/agents/prompts_advisor.py` | Tighten `EXTRACT_TERMS_PROMPT` (scope exclusions) + `GENERATE_BASIC_PROMPT` (Korean rules) | Modify |
| `backend/services/pipeline.py` | Wire validators into `_extract_and_create_handbook_terms` with 3-bucket routing | Modify |
| `backend/tests/test_handbook_advisor.py` | Add ExtractedTerm regression test for `confidence` field | Modify |

**Why this layout:**
- `handbook_validators.py` is separate from `handbook_quality_checks.py` (created 2026-04-16). Validators run **pre-insertion in the pipeline**; quality checks run **post-hoc on stored content**. Different layers, different lifecycles.
- Config additions stay in `handbook_quality_config.py` so all handbook-related config is in one place.
- Prompt changes stay in their existing files to preserve blame/history clarity.

---

## Chunk 0: Fix queue accumulation (`confidence` schema bug)

**Goal:** Make low-confidence terms actually route to the queue by fixing the Pydantic schema mismatch.

**Files:**
- Modify: `backend/models/advisor.py` (around lines 251-254 — `ExtractedTerm` class)
- Modify: `backend/tests/test_handbook_advisor.py`

### Task 0.1: Add `confidence` field to ExtractedTerm + `extra="allow"`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_handbook_advisor.py`:

```python
def test_extracted_term_preserves_confidence_field():
    """Regression: confidence was in EXTRACT_TERMS_PROMPT output spec but missing
    from the Pydantic model, causing Pydantic's default extra=ignore to drop it.
    Result: all terms defaulted to 'high', queue never accumulated."""
    from models.advisor import ExtractedTerm

    # Simulate an LLM response with confidence="low"
    payload = {
        "term": "Borderline Concept",
        "korean_name": "경계 개념",
        "reason": "appears in one article",
        "confidence": "low",
    }
    t = ExtractedTerm(**payload)
    assert t.confidence == "low"


def test_extracted_term_defaults_confidence_to_high():
    """Backwards-compatible: existing callers not passing confidence still work."""
    from models.advisor import ExtractedTerm

    t = ExtractedTerm(term="Transformer", korean_name="트랜스포머", reason="core concept")
    assert t.confidence == "high"
```

- [ ] **Step 2: Run test — expect FAIL (AttributeError: no field 'confidence')**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_advisor.py -v -k extracted_term_preserves
```

- [ ] **Step 3: Update ExtractedTerm in `backend/models/advisor.py`**

Find the class (around lines 251-254) and change it to:

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal


class ExtractedTerm(BaseModel):
    """Term proposed by EXTRACT_TERMS_PROMPT. Schema must match the prompt's
    output spec — Pydantic defaults would silently drop any drift.

    extra='allow' lets new prompt-output fields survive future additions
    without another schema-drop bug (see 2026-04-17 queue diagnosis)."""

    model_config = ConfigDict(extra="allow")

    term: str
    korean_name: str = ""
    reason: str = ""
    confidence: Literal["high", "low"] = "high"
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_advisor.py -v -k extracted_term
```

- [ ] **Step 5: Run full advisor test suite to catch regressions**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_advisor.py -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```
git add backend/models/advisor.py backend/tests/test_handbook_advisor.py
git commit -m "fix(handbook): restore queue routing — add confidence field to ExtractedTerm

Pydantic default extra='ignore' was silently dropping the 'confidence'
field that EXTRACT_TERMS_PROMPT produces, causing term_info.get('confidence',
'high') to always return 'high'. As a result, if confidence == 'low' never
fired and queued_terms table never accumulated rows. Now configured extra='allow'
to prevent similar schema drops in future prompt revisions."
```

### Task 0.2: Verify queue comes alive in a real pipeline run

This is verification-only (no code change). Amy runs a digest and inspects logs + DB.

- [ ] **Step 1: Trigger a news pipeline run** (manual, via admin or cron). Capture the run_id.

- [ ] **Step 2: Grep logs for queue activity**

From Railway logs or local:
```
grep "Queuing low-confidence term" <logs>
```

Expected: at least one line per pipeline run (low-confidence is relatively common — 10%+ terms historically fit this).

- [ ] **Step 3: Check `handbook_terms` table for `status='queued'` rows created in the last run's window**

Via Supabase SQL or dashboard:
```sql
SELECT slug, term, korean_name, status, created_at
FROM handbook_terms
WHERE status = 'queued'
ORDER BY created_at DESC
LIMIT 20;
```

Expected: non-empty (if any low-confidence terms existed in this run's source articles).

- [ ] **Step 4: If zero rows**: the secondary gate path may have an issue, or the run had no low-confidence candidates. Dispatch a diagnostic Explore to trace the specific run's extraction output — do not ship Chunks C/A/B until the queue is observed to accumulate in at least one live run.

- [ ] **Step 5 (optional): Vault note**

Append a one-liner to `vault/12-Journal-&-Decisions/` noting "queue restored 2026-04-17 via schema fix, observed N queued rows in first run post-deploy." Makes future audits trivial.

---

## Chunk C: Korean name validation

**Goal:** Prevent `LLM 인디나스` (phonetic gibberish) and reject identical-to-English `korean_name` unless the term matches a recognized global-name pattern (ISO xxx, GPT-N, etc.).

**Files:**
- Modify: `backend/services/handbook_quality_config.py` (add `GLOBAL_NAME_PATTERNS`)
- Create: `backend/services/handbook_validators.py`
- Create: `backend/tests/test_handbook_validators.py`
- Modify: `backend/services/agents/prompts_advisor.py` (tighten Korean naming rules)
- Modify: `backend/services/pipeline.py` (wire validator + route to queue on failure)

### Task C.1: Extend config with global-name patterns

- [ ] **Step 1: Add to `backend/services/handbook_quality_config.py`**

Append (bottom of file, after existing constants):

```python
# Regex patterns for terms whose korean_name may legitimately equal the English
# term (standards, versioned models, all-caps abbreviations). These are NOT
# translation failures — they are genuine global names.
GLOBAL_NAME_PATTERNS: tuple[str, ...] = (
    r"^ISO\s*\d+",           # ISO 42001, ISO 27001
    r"^IEC\s*\d+",           # IEC 62443
    r"^IEEE\s*\d+",          # IEEE 802.11
    r"^(GPT|Claude|Llama|Gemini|Mistral)\s*[-.\d]",  # GPT-5, Claude 4.6, Llama 4
    r"^[A-Z]{2,}\d*$",       # LSTM, BERT, GAN, T5, RAG
    r"^[A-Z]+-\d",           # GPT-4, BERT-base variants
)

# Minimum Hangul character count for korean_name to be considered a real
# translation (not a stray label). Applied only when korean_name is non-empty
# and not a global-name pattern.
KOREAN_MIN_HANGUL_CHARS: int = 2
```

- [ ] **Step 2: Commit**

```
git add backend/services/handbook_quality_config.py
git commit -m "feat(handbook): add global-name patterns for Korean validator

ISO/IEC/IEEE standards, versioned model families, and all-caps abbreviations
may legitimately have korean_name == term. Pattern list lets the upcoming
validator distinguish 'intentional global name' from 'translation gave up'."
```

### Task C.2: Write `_validate_korean_name` with TDD

- [ ] **Step 1: Create test file**

```python
# backend/tests/test_handbook_validators.py
from services.handbook_validators import validate_korean_name


def test_korean_name_none_is_accepted():
    ok, reason = validate_korean_name(term="Attention Mechanism", korean_name=None)
    assert ok is True


def test_korean_name_empty_string_is_accepted():
    ok, _ = validate_korean_name(term="Attention Mechanism", korean_name="")
    assert ok is True


def test_korean_name_real_hangul_translation_passes():
    ok, _ = validate_korean_name(term="Attention Mechanism", korean_name="어텐션 메커니즘")
    assert ok is True


def test_korean_name_identical_to_english_global_pattern_passes():
    """ISO standards, versioned models are legitimate as-is."""
    for term in ["ISO 42001", "GPT-5", "Claude 4.6", "LSTM", "RAG"]:
        ok, reason = validate_korean_name(term=term, korean_name=term)
        assert ok is True, f"{term}: {reason}"


def test_korean_name_identical_to_english_non_global_fails():
    """Non-global concepts must not copy English unchanged."""
    ok, reason = validate_korean_name(term="Attention Mechanism", korean_name="Attention Mechanism")
    assert ok is False
    assert "identical" in reason.lower() or "english" in reason.lower()


def test_korean_name_pure_ascii_non_global_fails():
    ok, _ = validate_korean_name(term="Attention Mechanism", korean_name="Attention Meka")
    assert ok is False


def test_korean_name_single_hangul_char_fails():
    """'가' alone is not a real translation."""
    ok, _ = validate_korean_name(term="Attention Mechanism", korean_name="가")
    assert ok is False


def test_korean_name_with_english_parenthetical_passes():
    """'RAG (검색 증강 생성)' style is fine — Hangul meets threshold."""
    ok, _ = validate_korean_name(
        term="Retrieval-Augmented Generation",
        korean_name="검색 증강 생성(RAG)",
    )
    assert ok is True
```

- [ ] **Step 2: Run tests — expect FAIL (ImportError)**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_validators.py -v
```

- [ ] **Step 3: Create `backend/services/handbook_validators.py`**

```python
"""Pre-insertion validators for handbook terms.

Unlike handbook_quality_checks (post-hoc measurement), these validators run
IN the pipeline before insertion to route terms into accept/queue/reject
buckets.

Each validator returns (ok: bool, reason: str). Pure — no DB, no IO.
"""
from __future__ import annotations

import re

from services.handbook_quality_config import (
    GLOBAL_NAME_PATTERNS,
    KOREAN_MIN_HANGUL_CHARS,
)

_HANGUL_RE = re.compile(r"[\uac00-\ud7af]")


def _count_hangul(s: str) -> int:
    return len(_HANGUL_RE.findall(s))


def _matches_global_pattern(term: str) -> bool:
    for pattern in GLOBAL_NAME_PATTERNS:
        if re.match(pattern, term):
            return True
    return False


def validate_korean_name(term: str, korean_name: str | None) -> tuple[bool, str]:
    """Validate that korean_name is a plausible Korean rendering of term.

    Rules:
    1. None / empty string is acceptable (UI shows English).
    2. korean_name == term is OK only when term matches a global-name pattern
       (ISO 42001, GPT-5, LSTM, etc.).
    3. Otherwise korean_name MUST contain at least KOREAN_MIN_HANGUL_CHARS
       Hangul characters. English copies, stray ASCII, and single-char labels
       all fail.

    Does NOT detect phonetic transliteration (e.g., "인디나스" for "Internals")
    — that rejection relies on the prompt rule. This validator catches the
    easier cases that pure substring comparison can decide.
    """
    if korean_name is None or korean_name.strip() == "":
        return True, ""

    kn = korean_name.strip()
    if kn == term.strip():
        if _matches_global_pattern(term):
            return True, ""
        return False, "korean_name identical to English but term is not a global-name pattern"

    hangul_count = _count_hangul(kn)
    if hangul_count < KOREAN_MIN_HANGUL_CHARS:
        return False, (
            f"korean_name has {hangul_count} Hangul character(s), "
            f"below threshold {KOREAN_MIN_HANGUL_CHARS}"
        )

    return True, ""
```

- [ ] **Step 4: Run tests — expect 8/8 PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_validators.py -v
```

- [ ] **Step 5: Commit**

```
git add backend/services/handbook_validators.py backend/tests/test_handbook_validators.py
git commit -m "feat(handbook): add validate_korean_name pre-insertion gate

Catches identical-to-English korean_name (when not a global-name pattern
like ISO 42001 or GPT-5) and requires at least 2 Hangul characters for
real translations. 8 unit tests cover pass/fail paths including ISO-style
standards, versioned models, and Hangul-with-parenthetical patterns."
```

### Task C.3: Tighten Korean naming rules in the generation prompt

- [ ] **Step 1: Locate `GENERATE_BASIC_PROMPT` in `backend/services/agents/prompts_advisor.py`**

Around line 621-629. The current block says:

```
- korean_name: Korean translation or commonly used Korean name. MUST be in Korean, NOT English. BAD: "EDA". GOOD: "탐색적 데이터 분석". If no standard Korean translation exists, use Korean phonetic transcription (e.g., "트랜스포머" for Transformer).
```

The "use phonetic transcription" clause is what produces `인디나스`. Replace with:

```
- korean_name: Korean translation or commonly used Korean name. MUST be in Korean characters (Hangul). If no standard Korean term exists for this concept, leave korean_name empty (null or ""). Do NOT invent phonetic transcriptions of English words — "인디나스" is NOT a valid korean_name for "Internals", and "스테이블" for "stable" is not real Korean. Only use phonetic transcription when the phonetic form is itself widely used in Korean tech writing (e.g., "트랜스포머" for Transformer is acceptable because Korean engineers routinely write "트랜스포머"; "인디나스" is not because Korean engineers write "내부구조" or leave it as "Internals").

Identical-to-English korean_name is allowed ONLY for:
- ISO/IEC/IEEE standards (e.g., "ISO 42001")
- Versioned model names (e.g., "GPT-5", "Claude 4.6")
- All-caps technical abbreviations (e.g., "LSTM", "RAG")

For any other term, if you cannot find a real Korean translation, return korean_name="" rather than copying the English.
```

- [ ] **Step 2: Verify the file still parses**

```
cd backend && .venv/Scripts/python.exe -c "import services.agents.prompts_advisor; print('OK')"
```

- [ ] **Step 3: Commit**

```
git add backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): tighten Korean naming rule — forbid invented phonetics

GENERATE_BASIC_PROMPT previously allowed 'phonetic transcription' as a
fallback, which produced 인디나스 for Internals. Now: empty korean_name is
preferred over invented phonetics. Identical-to-English is allowed only for
global-name patterns (ISO, versioned models, all-caps abbreviations).
Examples added to distinguish 트랜스포머 (legitimate loanword) from
인디나스 (invented nonsense)."
```

### Task C.4: Wire validator into pipeline with queue routing

- [ ] **Step 1: Locate the term insertion site in `backend/services/pipeline.py`**

Around lines 838-860, where `content_data.get("korean_name", korean_name)` is used to populate the insert row. Find the block that calls `supabase.table("handbook_terms").insert(row).execute()`.

- [ ] **Step 2: Add the validator call just before insert**

Replace the insert block with a routing pattern. Pseudocode structure (adapt to actual variable names you find):

```python
from services.handbook_validators import validate_korean_name

# ... existing extraction / generation code ...

korean_name = content_data.get("korean_name", korean_name)
korean_ok, korean_reason = validate_korean_name(term=term_name, korean_name=korean_name)

if not korean_ok:
    row["status"] = "queued"
    row["queue_reason"] = f"korean_name: {korean_reason}"
    logger.info("Queuing term '%s' for Korean review: %s", term_name, korean_reason)
# else: status stays "published" or whatever the existing accept path sets

result = supabase.table("handbook_terms").insert(row).execute()
```

**Note to implementer**: The actual `row` dict structure may need a `queue_reason` column added to `handbook_terms` schema. If the column does not exist, either (a) add the column via Supabase migration (requires Amy's approval to touch DB schema), or (b) stash the reason in an existing JSON field like `metadata` if available. Ask before creating a new column.

- [ ] **Step 3: Add integration test**

In `backend/tests/test_pipeline.py` (or a new `test_handbook_pipeline_integration.py`), add:

```python
def test_invalid_korean_name_routes_to_queue(monkeypatch):
    """Term with invalid korean_name should land with status='queued'."""
    # Mock extraction to return a term with identical EN/KO and not a global pattern
    # Mock supabase client to capture insert
    # Assert the captured row has status='queued' and non-empty queue_reason
    # ... (full mock setup — implementer writes per existing test patterns)
    pass
```

If the full mock setup is heavy, skip this test and rely on post-deploy observation. Mark `@pytest.mark.skip(reason="integration — observe in first live run instead")` with a clear comment.

- [ ] **Step 4: Run existing pipeline tests — make sure nothing breaks**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline.py tests/test_handbook_generation_flow.py -v
```

- [ ] **Step 5: Commit**

```
git add backend/services/pipeline.py  # + any test additions
git commit -m "feat(handbook): route Korean-name failures to queue

Invalid korean_name (identical EN/KO for non-global terms, or insufficient
Hangul) now sets status='queued' with queue_reason instead of publishing
directly. Term body is preserved — Amy fixes only the Korean in admin."
```

---

## Chunk A: Scope gate (reject HR/regulatory)

**Goal:** Reject out-of-scope terms (HR, pure compliance standards) at extraction time, with structured log entries in `pipeline_logs` for observability.

**Files:**
- Modify: `backend/services/handbook_quality_config.py` (add `HR_REGULATORY_BLOCKLIST`, `IMPORTANT_NON_TECH_ALLOWLIST`)
- Modify: `backend/services/handbook_validators.py` (add `validate_term_scope`)
- Modify: `backend/tests/test_handbook_validators.py` (tests)
- Modify: `backend/services/agents/prompts_advisor.py` (EXTRACT_TERMS_PROMPT scope section)
- Modify: `backend/services/pipeline.py` (wire reject + log)

### Task A.1: Extend config

- [ ] **Step 1: Add to `handbook_quality_config.py`**

```python
# Literal term names that should always be rejected as out-of-scope.
# Amy-curated from manually-deleted terms (2026-04-17 retro).
HR_REGULATORY_BLOCKLIST: frozenset[str] = frozenset({
    # HR / business-process
    "acquihire",
    "acqui-hire",
    # Specific regulatory standards (general "AI regulation" concepts stay via allowlist)
    "ISO 42001",
    "ISO 27001",
    "SOC 2",
    "GDPR article",  # articles of GDPR, not GDPR itself if someone wants it
})

# Regex patterns for whole families to reject. Easier to maintain than
# enumerating every ISO/IEC number.
OUT_OF_SCOPE_REGEX: tuple[str, ...] = (
    r"^ISO\s*\d+(?:[:\-]\d+)?$",     # any ISO xxxxx, ISO xxx:yyyy
    r"^IEC\s*\d+",                   # any IEC standard
    r"^IEEE\s*\d+",                  # any IEEE standard
    r"^NIST\s*SP\s*\d",              # NIST Special Publications
    r"^SOC\s*\d",                    # SOC 1/2/3
)

# Curated exceptions — specific named regulations that ARE in scope for
# AI handbook (e.g., landmark AI legislation). Must be an exact match.
# Start EMPTY — Amy adds as needed. Do NOT try to anticipate.
IMPORTANT_NON_TECH_ALLOWLIST: frozenset[str] = frozenset({
    # e.g., "EU AI Act", "AI Safety Institute" — add deliberately
})
```

- [ ] **Step 2: Commit**

```
git add backend/services/handbook_quality_config.py
git commit -m "feat(handbook): add scope blocklist + regex + allowlist config

HR_REGULATORY_BLOCKLIST covers Amy-observed out-of-scope terms. OUT_OF_SCOPE_REGEX
handles whole standard families without enumerating numbers. IMPORTANT_NON_TECH_ALLOWLIST
is empty by default — deliberately curated exceptions, not prompt judgment calls."
```

### Task A.2: `validate_term_scope` with TDD

- [ ] **Step 1: Add tests to `backend/tests/test_handbook_validators.py`**

```python
def test_term_scope_rejects_hr_literal():
    from services.handbook_validators import validate_term_scope
    ok, reason = validate_term_scope("acquihire")
    assert ok is False
    assert "blocklist" in reason.lower() or "scope" in reason.lower()


def test_term_scope_rejects_iso_pattern():
    from services.handbook_validators import validate_term_scope
    ok, _ = validate_term_scope("ISO 42001")
    assert ok is False


def test_term_scope_rejects_arbitrary_iec():
    from services.handbook_validators import validate_term_scope
    ok, _ = validate_term_scope("IEC 62443")
    assert ok is False


def test_term_scope_allows_technical_term():
    from services.handbook_validators import validate_term_scope
    ok, _ = validate_term_scope("Attention Mechanism")
    assert ok is True


def test_term_scope_allows_allowlisted_exception():
    from services.handbook_validators import validate_term_scope, _allowlist_override
    # Temporarily patch the allowlist for test determinism
    ok, _ = validate_term_scope("Attention Mechanism", _allowlist_override=frozenset({"Attention Mechanism"}))
    assert ok is True


def test_term_scope_allowlist_overrides_blocklist():
    """Allowlist wins over blocklist — e.g., if Amy decides 'ISO 42001' is worth an entry after all."""
    from services.handbook_validators import validate_term_scope
    ok, _ = validate_term_scope("ISO 42001", _allowlist_override=frozenset({"ISO 42001"}))
    assert ok is True
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement in `handbook_validators.py`**

Add:

```python
from services.handbook_quality_config import (
    HR_REGULATORY_BLOCKLIST,
    IMPORTANT_NON_TECH_ALLOWLIST,
    OUT_OF_SCOPE_REGEX,
)


def validate_term_scope(
    term: str,
    _allowlist_override: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Reject terms that are clearly out-of-scope for an AI/CS handbook.

    Priority order:
    1. Allowlist (curated exceptions) — always accept.
    2. Literal blocklist (Amy-curated) — reject with 'blocklist' reason.
    3. Regex families (ISO/IEC/IEEE/NIST/SOC) — reject with 'out_of_scope_pattern' reason.
    4. Otherwise accept.

    `_allowlist_override` is a test-only hook to patch the allowlist without
    modifying module state.
    """
    allowlist = _allowlist_override if _allowlist_override is not None else IMPORTANT_NON_TECH_ALLOWLIST
    term_stripped = term.strip()

    if term_stripped in allowlist:
        return True, ""

    if term_stripped in HR_REGULATORY_BLOCKLIST:
        return False, f"blocklist match: {term_stripped}"

    for pattern in OUT_OF_SCOPE_REGEX:
        if re.match(pattern, term_stripped):
            return False, f"out_of_scope_pattern: {pattern}"

    return True, ""
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```
git add backend/services/handbook_validators.py backend/tests/test_handbook_validators.py
git commit -m "feat(handbook): add validate_term_scope with allowlist override

Allowlist > blocklist > regex-patterns > accept. The _allowlist_override
parameter lets tests patch behavior without touching module state."
```

### Task A.3: Add explicit scope exclusions to `EXTRACT_TERMS_PROMPT`

- [ ] **Step 1: Find `EXTRACT_TERMS_PROMPT` in `prompts_advisor.py`**

Around line 2030 onwards. Find the "What to EXCLUDE" section (lines 2030-2039 per Explore findings).

- [ ] **Step 2: Append these categories to the exclude list**

Add to the existing "What to EXCLUDE" block:

```
- HR / business-operations terms (e.g., "acquihire", "headcount reduction", "performance improvement plan", "RIF") — even when they appear in AI company news
- Regulatory / compliance standards and their article numbers (e.g., "ISO 42001", "ISO 27001", "SOC 2", "NIST SP 800-53", "GDPR Article 22") — these are not tech concepts to learn
  - EXCEPTION: landmark AI-specific legislation as a whole concept MAY be included (e.g., "EU AI Act" yes; but "EU AI Act Article 6" no)
- Corporate finance terms (e.g., "Series A", "IPO", "valuation multiple") — they appear in AI news but are not AI concepts
```

- [ ] **Step 3: Verify the file still parses**

- [ ] **Step 4: Commit**

```
git add backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): explicit scope exclusions in EXTRACT_TERMS_PROMPT

HR terms, regulatory standards with numbers, and corporate finance are now
explicitly excluded. Landmark AI legislation allowed as whole concepts
but not as article-level references."
```

### Task A.4: Wire validator + structured log

- [ ] **Step 1: Find where term extraction results are processed in `pipeline.py`**

Around line 594 onwards — the loop over `extracted` terms. Before the existing confidence-based routing.

- [ ] **Step 2: Add scope validation as first gate**

```python
from services.handbook_validators import validate_term_scope, validate_korean_name

for term_info in extracted:
    term_name = term_info.get("term", "").strip()

    # Pattern A gate: reject out-of-scope, log for weekly review
    scope_ok, scope_reason = validate_term_scope(term_name)
    if not scope_ok:
        logger.info("Rejecting out-of-scope term '%s': %s", term_name, scope_reason)
        supabase.table("pipeline_logs").insert({
            "run_id": run_id,  # or whatever the current run context variable is named
            "event": "handbook_term_rejected",
            "level": "info",
            "data": {
                "term": term_name,
                "pattern": "A",
                "reason": scope_reason,
                "source_article_urls": [a.get("url") for a in articles][:3],
            },
        }).execute()
        continue  # skip this term entirely

    # ... existing confidence / gate logic continues unchanged here
```

Implementer: verify `pipeline_logs` schema can accept the above shape. If not, adapt field names.

- [ ] **Step 3: Sanity test — no existing tests should break**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```
git add backend/services/pipeline.py
git commit -m "feat(handbook): reject out-of-scope terms with structured log

Pattern A terms (HR, ISO/IEC/IEEE/NIST/SOC standards, corporate finance)
are now rejected before insertion. Rejection events logged to pipeline_logs
with term, reason, pattern tag, and source URLs for weekly review."
```

---

## Chunk B: Entity grounding (verbatim match + compound heuristic)

**Goal:** Reject or queue terms that were never spoken verbatim in source articles (likely fabricated compounds like `OpenAI Frontier`).

**Files:**
- Modify: `backend/services/handbook_validators.py` (add `validate_term_grounding`)
- Modify: `backend/tests/test_handbook_validators.py`
- Modify: `backend/services/pipeline.py` (wire grounding gate before insert)

### Task B.1: `validate_term_grounding` with TDD

Signature: `validate_term_grounding(term: str, source_texts: list[str]) -> tuple[bool, str]`.

Logic:
1. If `term` appears verbatim (case-insensitive) as a contiguous substring in any source text → pass.
2. Else: compute a "compound-hallucination score" — if term has 2+ words, check whether each word appears in SOME source text but the compound itself doesn't. If so, reject with high confidence.
3. Single-word terms that don't appear verbatim: reject.

- [ ] **Step 1: Add tests**

```python
def test_grounding_passes_when_verbatim_in_source():
    from services.handbook_validators import validate_term_grounding
    sources = [
        "OpenAI announced GPT-5 yesterday. The frontier model includes...",
        "Anthropic's Claude 4.6 is also available.",
    ]
    ok, _ = validate_term_grounding("GPT-5", sources)
    assert ok is True


def test_grounding_case_insensitive():
    from services.handbook_validators import validate_term_grounding
    ok, _ = validate_term_grounding("gpt-5", ["The GPT-5 model..."])
    assert ok is True


def test_grounding_fails_on_fabricated_compound():
    """'OpenAI Frontier' — neither word missing, but compound never appears."""
    from services.handbook_validators import validate_term_grounding
    sources = [
        "OpenAI announced a frontier model capable of reasoning.",
        "The frontier of AI research continues to advance.",
    ]
    ok, reason = validate_term_grounding("OpenAI Frontier", sources)
    assert ok is False
    assert "compound" in reason.lower() or "not verbatim" in reason.lower()


def test_grounding_fails_when_neither_fragment_present():
    from services.handbook_validators import validate_term_grounding
    ok, _ = validate_term_grounding("Quantum Entanglement", ["OpenAI released a model."])
    assert ok is False


def test_grounding_passes_multi_word_verbatim():
    from services.handbook_validators import validate_term_grounding
    sources = ["The retrieval-augmented generation approach..."]
    ok, _ = validate_term_grounding("retrieval-augmented generation", sources)
    assert ok is True


def test_grounding_empty_sources_fails_gracefully():
    """Defensive: no sources shouldn't crash, just reject."""
    from services.handbook_validators import validate_term_grounding
    ok, reason = validate_term_grounding("Anything", [])
    assert ok is False
    assert "source" in reason.lower() or "empty" in reason.lower()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

Add to `handbook_validators.py`:

```python
def validate_term_grounding(term: str, source_texts: list[str]) -> tuple[bool, str]:
    """Verify term appears verbatim in at least one source text.

    Returns (False, reason) if:
    - source_texts is empty, or
    - term (case-insensitive) does not appear as a contiguous substring, OR
    - for multi-word terms, each word appears individually somewhere but the
      compound itself never does (fabricated compound).
    """
    if not source_texts:
        return False, "empty source_texts — cannot verify grounding"

    term_lower = term.strip().lower()
    if not term_lower:
        return False, "empty term"

    combined_lower = "\n".join(s or "" for s in source_texts).lower()

    if term_lower in combined_lower:
        return True, ""

    words = term_lower.split()
    if len(words) >= 2:
        all_words_present = all(w in combined_lower for w in words)
        if all_words_present:
            return False, "compound term never appears verbatim despite all words being present"

    return False, "term not found verbatim in any source"
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```
git add backend/services/handbook_validators.py backend/tests/test_handbook_validators.py
git commit -m "feat(handbook): add validate_term_grounding for fabricated compounds

Rejects terms that don't appear verbatim in any source. Special-case
compound detection: if all words are present individually but the phrase
never is, flag as compound hallucination (e.g., 'OpenAI Frontier')."
```

### Task B.2: Wire grounding gate + route to queue

- [ ] **Step 1: Find where source articles are available in `pipeline.py`**

The extraction loop has access to `articles` (the news items fed to the LLM). Each article has `content` or `body` or similar text.

- [ ] **Step 2: Add grounding gate after scope gate, before insert**

```python
source_texts = [a.get("content") or a.get("body") or "" for a in articles]
grounding_ok, grounding_reason = validate_term_grounding(term_name, source_texts)
if not grounding_ok:
    row["status"] = "queued"
    row["queue_reason"] = f"grounding: {grounding_reason}"
    logger.info("Queuing ungrounded term '%s': %s", term_name, grounding_reason)
# else: proceed to existing confidence/gate logic
```

- [ ] **Step 3: Sanity run full test suite**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```
git add backend/services/pipeline.py
git commit -m "feat(handbook): route ungrounded terms to queue

Terms not appearing verbatim in source articles (likely fabricated
compounds like 'OpenAI Frontier') now get status='queued' with
queue_reason='grounding: ...' for Amy's admin review."
```

---

## Exit criteria

- [ ] Chunk 0: `confidence='low'` LLM output survives Pydantic validation. At least one observed queue accumulation in a real pipeline run.
- [ ] Chunk C: `validate_korean_name` tests pass. Prompt forbids invented phonetics. Pipeline routes Korean failures to queue.
- [ ] Chunk A: `validate_term_scope` tests pass. EXTRACT_TERMS_PROMPT excludes HR/regulatory. Pipeline rejects + logs.
- [ ] Chunk B: `validate_term_grounding` tests pass. Pipeline routes ungrounded terms to queue.
- [ ] Full test suite (`pytest tests/ -v`) passes after each chunk.
- [ ] At least one post-deploy pipeline run observed: Amy spot-checks `handbook_terms` where `status='queued'` and `pipeline_logs` where `event='handbook_term_rejected'`. Sanity-check the content makes sense.

## Deliberately out of scope

- Admin UI for reviewing queued terms (that infrastructure is separate).
- Cleaning existing bad rows in `handbook_terms` (seed regen handles).
- Auto-correction of Korean names or auto-suggestion of alternatives.
- LLM-judge validators (deliberate: these are rule-based, deterministic, cheap).
- A "rescore all existing terms with new validators" batch job (can be written later, but not in this plan's scope).

## Risk notes

- **New column `queue_reason`** in `handbook_terms` may not exist. If so, Chunk C Task C.4 needs a Supabase migration decision from Amy. Fallback: stash reason in `metadata` JSON field if one exists; otherwise use `pipeline_logs` entries keyed by term slug for the queue reason.
- **`validate_term_grounding` false negatives** — Amy may want to occasionally accept terms that technically don't appear verbatim (e.g., when multiple articles use "Mixture-of-Experts" but our LLM extraction normalized to "MoE"). Monitor the queue for such cases; if high, add a "normalize whitespace/punctuation" pre-pass in grounding.
- **Allowlist drift** — `IMPORTANT_NON_TECH_ALLOWLIST` starts empty. Each addition is a deliberate Amy call. Do NOT auto-add from LLM proposals. A file-based review log of allowlist additions is a good Phase 2 concern.
- **Pipeline_logs retention** — the `pipeline_logs` table may have TTL or size limits in Supabase. If the rejection stream is high-volume, consider a retention policy. Check `pipeline_logs` row count post-deploy; if >10k/week, plan archival.
- **Chunk order matters** — do Chunk 0 FIRST. If Chunks B/C insert queue rows before the `confidence` field propagates correctly, there may be edge cases where status='queued' but the downstream queue consumer (admin UI) can't render them. Observing Chunk 0's effect in a live run before Chunks C/A/B is mandatory.

## Related

- [[2026-04-16-handbook-quality-measurement-plan]] — prior measurement plan. Its `handbook_quality_checks.py` module is POST-hoc; this plan's `handbook_validators.py` is PRE-insertion. Distinct purposes, both retained.
- [[2026-04-15-news-pipeline-hardening-phase2-plan]] — structural URL hallucination gate was the template for this plan's structural scope/grounding gates.
- [[ACTIVE_SPRINT]] — HB-QM sprint. Update after Chunk 0 ships.
- Explore diagnosis in-conversation 2026-04-17 — root cause for queue bug (Pydantic `extra="ignore"` dropping `confidence`).

---

## Completion & Retro (2026-04-19)

All four chunks shipped over a single long working session on 2026-04-19 / 2026-04-20. Summary below by commit, followed by retrospective notes.

### Commit map

**Chunk 0 — queue accumulation fix**
- `606bfa7` fix(handbook): restore queue routing — add confidence field to ExtractedTerm

**Chunk 0 verify — live confirmation**
- Not a code commit. Observed in the live pipeline run on 2026-04-17: 4 / 13 newly-extracted terms routed to `status='queued'`, confirming the Pydantic schema fix propagated the `confidence` field through to the pipeline's routing logic.

**Chunk A — scope gate (reject + log)**
- `1c7766c` feat(handbook): add scope-gate config (blocklists, allowlists, version patterns)
- `eb1f446` feat(handbook): add validate_term_scope gate (blocklist/regex/product-allowlist)
- `9015b4c` feat(handbook): add HR/regulatory/corporate-finance exclusions to EXTRACT_TERMS_PROMPT
- `f78d159` feat(handbook): wire validate_term_scope gate + pipeline_logs rejection entry

**Chunk C — Korean-name gate (queue)**
- `292b4be` feat(handbook): add Korean-name validator config (Hangul minimum + abbreviation pattern)
- `99dad16` feat(handbook): add validate_korean_name gate (Hangul minimum + global-name passthrough)
- `0842aaf` feat(handbook): tighten Korean-name prompt rule — forbid invented phonetic transliterations
- `975bf36` feat(handbook): wire validate_korean_name into pipeline with queue routing

**Chunk B — entity grounding gate (queue)**
- `5732eb9` feat(handbook): add validate_term_grounding gate (verbatim match + compound-fabrication signal)
- `df9b248` feat(handbook): wire validate_term_grounding into pipeline with queue routing

### The detour — definition length & quality judge (not in original scope)

Between Chunks 0 and A, we spent a significant block of session time on **ancillary infrastructure** that the original plan didn't anticipate. The trigger was Amy's test regeneration of the `Agentic UX` term, which surfaced three separate problems:

1. **`definition_en` consistently lands at 500–700 chars** despite every prompt target 250–400. Four iterations of prompt engineering (structural sentence limits, scope-discipline rule, conceptual-vs-algorithmic framing, glossary vs Wikipedia framing, diversified GOOD examples across 6 term categories) moved the distribution only slightly. The final conclusion: **LLM's Wikipedia-style prior for "technical definition" is stronger than any prompt rule; only post-gen LLM rewrite would close the gap**. Deferred to a separate tech-debt memo — `project_handbook_en_def_length.md` in auto-memory.

2. **Quality judge variance of ~69 points for same content** (Agentic UX advanced scored 5, 7, 74 across three runs). Root cause: the judge had only four broad 0-25 dimensions with no anchors, no evidence requirement, and was computing the total itself. Fixed by redesigning the judge into 10 sub-scores × 0-10 with evidence fields (Chain-of-Thought), code-side aggregation (no LLM arithmetic), and `source_grounding` dropped from the advanced rubric since handbook references live in a dedicated field, not inline. Variance dropped to ~15 points — 4.6× improvement.

3. **Quality judge truncation bug** — `_check_handbook_quality` was slicing content at 6000 chars, causing the judge to miss `❌/✅` format markers that often live later in a 15K-char body. Bumped to 12000.

These fixes weren't in the plan but became necessary for the plan's chunks to be evaluable. Leaving them out would have meant shipping the gates without a way to measure their effect on content quality.

### What went well

- **Pydantic schema bug was the correct first target.** Every downstream chunk depended on the queue actually accumulating; if we'd shipped A/B/C first without fixing Chunk 0, `status='queued'` rows would have been dead letters.
- **3-bucket disposition design (accept / queue / reject+log) held up cleanly under implementation.** Chunk A → reject+log, Chunks B/C → queue. The code mirrored the design without needing mid-flight re-evaluation.
- **Schema-convention discovery during A.4 paid compound interest.** The implementer noticed `pipeline_logs` uses `pipeline_type` (not `stage`) and places event metadata inside `debug_meta` rather than at the top level. That pattern was reused verbatim by C.4 and B.2 — consistent log shape across three gates enables a single `WHERE pipeline_type IN (...) AND status IN (...)` review query.
- **Non-fatal logging (try/except around `pipeline_logs.insert`)** prevented a logging-layer failure from taking down the actual pipeline. Lifted directly from news-pipeline-hardening lessons.
- **Test append pattern.** All validators share `backend/tests/test_handbook_validators.py` — 35 tests across scope / Korean / grounding — so future validator additions have a stable place to land. No test-file proliferation.
- **Chunks A and C converged on a common structure** (config constants → pure function + TDD → prompt-level mirror → pipeline wire-in). By the time Chunk B was dispatched, the implementer finished B.1 + B.2 in one round with zero back-and-forth — all accumulated convention became free leverage.

### What surprised us

- **Pattern B (compound fabrication) turned out to be rare in actual data.** The 2026-04-17 batch analysis of 4 queued terms (`AI Mode`, `Agentic UX`, `GPT-Rosalind`, `Prism`) found all 4 appeared verbatim in their source articles — i.e., no fabrication in that sample. Chunk B was still implemented as a defensive layer, but its expected firing rate is low. This is an argument for B being the last chunk and deprioritizable if time were tighter.
- **Chunk 0's live-verify uncovered an orphan-score linking bug** (`handbook_quality_scores.term_id = NULL` for scores written before the corresponding `handbook_terms` row existed). Not in the original plan. Patched inline; probably needs a broader retroactive cleanup pass for older orphans (low priority).
- **The `term_type` field is assigned AFTER extraction, not during it.** That means the `product_platform_service` auto-reject branch in `validate_term_scope` is currently dormant for the pipeline path — the gate runs before classification, so `term_type=None` is the norm. Dormant, not broken. To activate: either pull classification earlier in the pipeline or add a second-pass gate after classification. Deferred.

### Deferred items

- **Post-gen LLM rewrite for `definition_en`** — sketched in conversation; would close the 5-8 second popup-UX gap Amy flagged as non-negotiable. ~$0.001–0.005 per term, guaranteed target length. Triggered when Amy wants to revive the UX goal.
- **`term_type`-aware scope gate** — activate the currently-dormant `product_platform_service` branch by either pushing classification earlier or running a post-classify second pass.
- **Retroactive cleanup for orphan `handbook_quality_scores.term_id`** — one-off SQL job to backfill `term_id` via slug join. Low priority; only matters for admin-UI joins that filter by term.
- **Admin UI for queue review flow** — `handbook_terms` now produces `status='queued'` rows from two different gates (Korean and grounding). Admin needs a way to surface both + show the reason from `pipeline_logs`. Out of scope per plan's Non-Goals, but blocks Amy from actually reviewing the queue.

### Monitoring — weekly review query

```sql
SELECT
  pipeline_type,
  debug_meta->>'event' AS event,
  debug_meta->>'term' AS term,
  debug_meta->>'reason' AS reason,
  COUNT(*) AS occurrences,
  MAX(created_at) AS last_seen
FROM pipeline_logs
WHERE pipeline_type IN (
        'handbook.scope_gate',
        'handbook.korean_gate',
        'handbook.grounding_gate'
      )
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2, 3, 4
ORDER BY occurrences DESC;
```

Decisions this query drives:
- If the same `term` shows up repeatedly across runs in `handbook.scope_gate`, review whether the blocklist is too aggressive or the term has crept back in.
- If `handbook.korean_gate` flags many terms with `korean_name=""`, that's healthy (generation prompt is correctly returning empty instead of inventing transliteration).
- If `handbook.grounding_gate` has near-zero firings (matches 2026-04-17 finding), we can deprioritize further investment in B and potentially relax the check to reduce false positives.

### Related

Same as above. Companion notes in auto-memory:
- `project_handbook_en_def_length.md` — the deferred post-gen rewrite tech debt
- `bug_fact_pack_whitelist.md` — the pattern of "silent field drop via whitelist" surfaced again here in Pydantic form (Chunk 0)
- `feedback_scope_verification.md` — reinforced; several prompt-iteration rounds could have been shorter had we grep-verified that GOOD examples already hit target length
