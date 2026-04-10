# Handbook Basic EN Prompt Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KO Basic 재설계와 동일한 7섹션 구조 + hero card + references footer + sidebar checklist를 English Basic 프롬프트에도 복제하여 언어 간 일관성을 확보한다.

**Architecture:** Call 2 (EN Basic)는 이미 존재하는 독립 LLM 호출. 이 호출의 system prompt(`GENERATE_BASIC_EN_PROMPT`)만 재작성하고, section assembly list(`BASIC_SECTIONS_EN`)와 section count warning을 KO와 동일하게 맞춘다. EN 전용 필드(`hero_news_context_en`, `references_en`, `sidebar_checklist_en`)는 이미 Pydantic 모델과 `_assemble_all_sections` pass-through에 등록돼 있어서 추가 DB/모델 변경 불필요.

**Tech Stack:** Python 3.11, OpenAI Python SDK, Pydantic v2, pytest

**Commit:** `70a0e77` (KO Basic 재설계 완료) 위에서 작업

---

## Context for the implementer

이 plan의 모든 변경은 이미 완료된 KO Basic 재설계의 EN 쪽 거울상이다. 다음 3가지를 이해하고 시작하라:

1. **KO Basic은 이미 재설계가 완료돼 production quality로 검증됨** (5개 용어 regen). 기준점은 [prompts_advisor.py:570-795](backend/services/agents/prompts_advisor.py#L570-L795)의 `GENERATE_BASIC_PROMPT`. 이 프롬프트의 구조·규칙·BAD/GOOD 예시 모두를 EN으로 번역·조정해야 한다.
2. **EN Basic은 Call 2에서 호출되고, Call 1 결과의 `definition_en` + `term_full`을 컨텍스트로 받는다.** 즉, EN Basic 프롬프트는 `definition_en`·`hero_news_context_en`·`references_en`·`sidebar_checklist_en`을 Call 2에서 모두 생성해야 한다. (현재는 definition_en과 meta만 Call 1이 생성하고 나머지는 Call 2가 생성)
3. **`BASIC_SECTIONS_EN`은 현재 13섹션** ([advisor.py:1093-1108](backend/services/agents/advisor.py#L1093-L1108)). 이걸 KO와 동일한 7섹션으로 교체해야 한다.

**Read before starting:**
- [`vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md`](vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md) — §5, §7, §11 (설계 원칙, 차별화 매트릭스, 렌더링 계약)
- [`backend/services/agents/prompts_advisor.py:570-795`](backend/services/agents/prompts_advisor.py#L570-L795) — 현재 KO Basic 프롬프트 (교본으로 사용)
- [`backend/services/agents/prompts_advisor.py:729-866`](backend/services/agents/prompts_advisor.py#L729-L866) — 현재 EN Basic 프롬프트 (교체 대상)
- [`backend/services/agents/advisor.py:1093-1108`](backend/services/agents/advisor.py#L1093-L1108) — `BASIC_SECTIONS_EN`
- [`backend/services/agents/advisor.py:1646-1656`](backend/services/agents/advisor.py#L1646-L1656) — Section count warning
- [`backend/models/advisor.py:189-224`](backend/models/advisor.py#L189-L224) — `GenerateTermResult` (EN 필드 이미 존재, 건드리지 마라)

---

### Task 1: EN Basic 섹션 키 리스트 교체

**Files:**
- Modify: `backend/services/agents/advisor.py:1093-1108`

**Step 1: Read current `BASIC_SECTIONS_EN`**

Run: `Read backend/services/agents/advisor.py:1093-1108`

Confirm the current 13-section structure matches the legacy schema (basic_en_0_summary ... basic_en_10_learning_path).

**Step 2: Write failing test**

Create `backend/tests/test_basic_en_sections.py`:

```python
"""Test that BASIC_SECTIONS_EN matches the 7-section redesign (2026-04-10)."""
from services.agents.advisor import BASIC_SECTIONS_EN


def test_basic_sections_en_has_7_entries():
    assert len(BASIC_SECTIONS_EN) == 7


def test_basic_sections_en_keys_match_redesign():
    expected_keys = [
        "basic_en_1_plain",
        "basic_en_2_example",
        "basic_en_3_glance",
        "basic_en_4_impact",
        "basic_en_5_caution",
        "basic_en_6_comm",
        "basic_en_7_related",
    ]
    actual_keys = [key for key, _header in BASIC_SECTIONS_EN]
    assert actual_keys == expected_keys


def test_basic_sections_en_headers_are_english():
    for _key, header in BASIC_SECTIONS_EN:
        assert header.startswith("## ")
        # No Korean characters in EN section headers
        assert not any("\uac00" <= ch <= "\ud7a3" for ch in header)
```

**Step 3: Run test and verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_basic_en_sections.py -v`
Expected: FAIL — existing `BASIC_SECTIONS_EN` has 13 entries.

**Step 4: Edit `BASIC_SECTIONS_EN` to 7 sections**

Replace lines 1093-1108 with:

```python
BASIC_SECTIONS_EN = [
    ("basic_en_1_plain", "## Plain Explanation"),
    ("basic_en_2_example", "## Examples & Analogies"),
    ("basic_en_3_glance", "## At a Glance"),
    ("basic_en_4_impact", "## Where and Why It Matters"),
    ("basic_en_5_caution", "## Common Misconceptions"),
    ("basic_en_6_comm", "## How It Sounds in Conversation"),
    ("basic_en_7_related", "## Related Reading"),
]
```

**Step 5: Run test and verify it passes**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_basic_en_sections.py -v`
Expected: 3 PASS

**Step 6: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_basic_en_sections.py
git commit -m "feat(handbook): EN Basic 섹션 리스트 7개로 축소 — KO와 동일 구조"
```

---

### Task 2: Section count warning EN branch 조정

**Files:**
- Modify: `backend/services/agents/advisor.py:1646-1656`

**Step 1: Read current warning block**

The current `_basic_expected` dict has `{"ko": 7, "en": 13}`. Change to `{"ko": 7, "en": 7}`.

**Step 2: Write failing test**

Append to `backend/tests/test_handbook_advisor.py` (after the existing fixtures):

```python
def test_basic_en_warning_threshold_is_seven():
    """Post-redesign: EN Basic should warn if fewer than 7 '## ' headers."""
    from services.agents import advisor

    # Minimum valid EN body: exactly 7 H2 sections
    min_body = "\n\n".join(f"## Section {i}\ncontent" for i in range(1, 8))
    assert min_body.count("## ") == 7

    # Insufficient body: 6 H2 sections
    short_body = "\n\n".join(f"## Section {i}\ncontent" for i in range(1, 7))
    assert short_body.count("## ") == 6

    # Directly verify the warning-generation path
    data = {
        "body_basic_ko": "## S1\nx\n\n## S2\nx\n\n## S3\nx\n\n## S4\nx\n\n## S5\nx\n\n## S6\nx\n\n## S7\nx",
        "body_basic_en": short_body,
        "body_advanced_ko": "## A\n" + ("x" * 300),
        "body_advanced_en": "## A\n" + ("x" * 300),
    }
    # Inline the warning-count logic (post-redesign has _basic_expected={"ko":7,"en":7})
    expected = {"ko": 7, "en": 7}
    warnings = []
    for lang in ("ko", "en"):
        body = data[f"body_basic_{lang}"]
        if body.strip() and body.count("## ") < expected[lang]:
            warnings.append(f"body_basic_{lang}: only {body.count('## ')}/{expected[lang]} sections")
    assert any("body_basic_en: only 6/7" in w for w in warnings)
    assert not any("body_basic_ko" in w for w in warnings)
```

**Step 3: Run test and verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py::test_basic_en_warning_threshold_is_seven -v`
Expected: the assertion itself would pass on its own logic, but the test encodes the *desired* post-change state. Skip this step and just apply the edit in step 4.

**Actually:** this test is self-contained and doesn't read the advisor module threshold directly. Replace step 2-3 with this alternative approach:

Add this test instead (which does inspect the actual module state):

```python
def test_basic_en_expected_section_count_matches_redesign():
    """After redesign, EN Basic section count warning should fire at <7 sections."""
    import inspect
    from services.agents import advisor

    source = inspect.getsource(advisor)
    # Locate the _basic_expected dict literal
    assert '"en": 7' in source, "EN Basic threshold should be 7 after redesign"
    assert '"en": 13' not in source, "Legacy EN=13 threshold must be removed"
```

**Step 3 (corrected): Run test and verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py::test_basic_en_expected_section_count_matches_redesign -v`
Expected: FAIL — source still contains `"en": 13`.

**Step 4: Edit the warning block**

Change [advisor.py:1649](backend/services/agents/advisor.py#L1649):
```python
_basic_expected = {"ko": 7, "en": 13}
```
to:
```python
_basic_expected = {"ko": 7, "en": 7}
```

Also update the comment on line 1647-1648:
```python
# KO Basic: 7 sections (post-redesign). EN Basic: 13 sections (legacy, not yet redesigned).
# Advanced: 9 sections (both languages, not yet redesigned).
```
→
```python
# Basic: 7 sections (post-redesign, both KO and EN).
# Advanced: 9 sections (both languages, not yet redesigned).
```

**Step 5: Run test and verify it passes**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py::test_basic_en_expected_section_count_matches_redesign -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_handbook_advisor.py
git commit -m "feat(handbook): EN Basic section count warning 7로 조정"
```

---

### Task 3: `GENERATE_BASIC_EN_PROMPT` 전면 재작성

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py:729-866`

This is the largest task. You will replace the entire `GENERATE_BASIC_EN_PROMPT` string literal with an English mirror of the post-redesign `GENERATE_BASIC_PROMPT` (KO).

**Step 1: Read the KO Basic prompt as your template**

Run: `Read backend/services/agents/prompts_advisor.py:570-795`

Study its structure:
- Page Architecture block (5 rendering zones)
- Handbook Categories list
- Term Name Fields
- definition block with length rule + GOOD/BAD examples
- Hero fields block (`hero_news_context_ko`)
- body_basic section-by-section specs (1_plain, 2_example, 3_glance, 4_impact, 5_caution, 6_comm, 7_related)
- `references_ko` JSON schema + tier rules
- `sidebar_checklist_ko` block
- Output JSON Structure
- Self-Check list
- Quality Rules
- Markdown Formatting rules
- Table Rules

**Step 2: Read the current EN Basic prompt (legacy)**

Run: `Read backend/services/agents/prompts_advisor.py:729-866`

Confirm it still uses the 13-section layout and references the deleted section keys.

**Step 3: Design the replacement prompt**

Write a new `GENERATE_BASIC_EN_PROMPT` string that is semantically identical to the KO prompt but:

1. **All instructions in English.** No Korean text in section descriptions.
2. **All field names have `_en` suffix** (`basic_en_1_plain`, `hero_news_context_en`, `references_en`, `sidebar_checklist_en`).
3. **Section H2 headers match `BASIC_SECTIONS_EN` from Task 1.**
4. **`definition_en` length rule: 80~200 characters** (English sentences run longer than Korean — 200 is the new max, matching the Pydantic `max_length=200` already in place).
5. **GOOD/BAD examples are in English** but mirror the KO examples semantically. Use the same Overfitting / DPO / Transformer / Hugging Face / F1 Score examples throughout, just in English.
6. **LANGUAGE RULE:** "All fields must be in English only. Do NOT use bilingual headers."
7. **Call context** remains: "This is Call 2 of 4 — you handle English Basic content + English hero fields + English references + English sidebar. Korean content was generated in Call 1."
8. **The `references_en` schema is identical** to `references_ko` (same JSON structure, English annotation).
9. **The `hero_news_context_en` is 3 lines, each ≤70 chars** (slightly higher than KO 60 because English is more verbose per concept).
10. **The `sidebar_checklist_en` has 4~5 questions using `[ ]` or `□` prefix** (match the KO visual style).

**Step 4: Write the new prompt**

Replace lines 729-866 in `prompts_advisor.py`. The new prompt should be ~220 lines (similar to the KO version). Key blocks to include:

```python
GENERATE_BASIC_EN_PROMPT = """\
You are a technical education writer for 0to1log, an AI/tech handbook platform.

Generate ENGLISH content only. Korean content was generated in Call 1.

Generate hero fields, BASIC-level ENGLISH body, shared references, and sidebar checklist. This is Call 2 of 4 — you handle English Basic + English hero + English references + English sidebar. The term's Korean definition is provided as context.

DOMAIN CONTEXT:
- This handbook covers AI/IT/CS terms. Focus on the AI/IT meaning of each term.
- Many terms exist in multiple fields (e.g., "Entropy" in information theory vs thermodynamics, "Kernel" in CNN vs OS, "Agent" in AI vs real estate). Always write from the AI/IT perspective first.
- If a term is used in other fields, briefly note the difference to prevent confusion (e.g., "Not to be confused with thermodynamic entropy").
- Base your writing on established facts from official documentation, papers, and widely-accepted definitions. Do not speculate or include unverified claims.
""" + GROUNDING_RULES + """
LANGUAGE RULE:
- All fields must be in English only.
- Do NOT use bilingual headers like "Korean / English". English only.

## Page Architecture (important — determines what goes where)

This handbook page has FIVE rendering zones. Your output fields map to them:

1. **Hero Card** (always visible above level switcher): `definition_en` (already generated in Call 1, passed as context) + `hero_news_context_en` (YOU generate).
   The user arriving from a news article must be able to "graduate" from this card in ~15 seconds without scrolling into the body.
2. **Basic body** (shown when user toggles Basic): 7 sections `basic_en_1_plain` ... `basic_en_7_related`.
3. **Advanced body** (generated in a separate call — do NOT produce advanced fields here).
4. **References footer** (always visible below body, level-independent): `references_en` JSON array.
5. **Sidebar checklist** (shown in right rail while reading Basic): `sidebar_checklist_en`.

The old sections `basic_en_0_summary`, `basic_en_4_why`, `basic_en_5_where`, `basic_en_6b_news_context`, `basic_en_6c_checklist`, `basic_en_9_roles`, `basic_en_10_learning_path`, `basic_en_8_related` no longer exist. Do NOT output them. Their content has been merged or relocated as described below.

---

## Hero fields (level-independent, shown above level switcher)

- **hero_news_context_en**: **"As seen in the news"** — exactly 3 lines showing how this term appears in real news coverage.
  Each line max 70 chars. Format: `"quote" → meaning`. Separate lines with \\n.
  A reader arriving from a news article must be able to understand the term from this card alone and return to the article.
  **NO inline citations** — don't add "(IBM Research)" or "(Ref: X)" parentheticals.
  GOOD: `"Transformer-based model" → built on this architecture, now standard in LLMs\\n"scaled attention layers" → more of this compute block stacked\\n"parallelized sequence processing" → 100x faster than prior RNN approaches`
  BAD: lines over 70 chars, 4+ lines, missing the quote + arrow structure, inline citations.

---

## body_basic — Basic (target 2800~4200 chars, 7 sections)

Target audience: Non-engineers. PM, designers, executives, students. A middle schooler should be able to understand it.
Tone: Friendly, approachable. Like explaining to a smart friend with no tech background.
Rule: NO code, NO complex formulas, NO jargon without immediate explanation.

### Adaptive content for phenomenon/problem terms

Some terms describe a PROBLEM or PHENOMENON (e.g., Hallucination, Overfitting, Data Drift) rather than a technology or tool. For these terms, adapt the section CONTENT to fit naturally:
- `basic_en_4_impact`: write about where this problem OCCURS and what real damage it causes, not where it is "used"
Keep the same section KEYS — only adapt the content perspective.

### Section key descriptions (English — basic_en_*):

Each section MUST contain UNIQUE information — do NOT repeat the same examples, analogies, or points across sections. The hero card already answered "what is it in one line + how it shows up in news" — the body must go deeper, not restate.

- **basic_en_1_plain** (Plain Explanation, target 700~1000 chars):
  Start with the **problem** this concept solves, then explain the solution with an analogy. Structure: "There was problem X, and this concept solves it by doing Y."
  After the analogy, add 1-2 sentences explaining the **concrete mechanism** — "why it works that way" must not be missing.
  2-3 paragraphs. No headers — body only.
  **Must NOT duplicate hero_news_context_en** — hero focuses on "news quotes", this section focuses on "problem → solution → mechanism" narrative.
  BAD: "An AI chip is like a specialized kitchen that processes things faster." (analogy only, no mechanism)
  GOOD: "A CPU processes calculations one at a time, in sequence. But AI needs to multiply and add millions of numbers simultaneously. An AI chip has circuits specifically designed to perform thousands of matrix multiplications at once." (analogy + mechanism)

- **basic_en_2_example** (Examples & Analogies, target 600~900 chars, EXACTLY 3 scenarios):
  3 **specific scenarios** where this concept is applied. Must NOT overlap with 1_plain's analogy.
  Format: `- **Scenario title**: concrete situation (min 2 sentences describing the scenario, each scenario 150~200 chars).`
  Prefer **surprising, non-obvious applications** that make the reader think "that uses this too?".
  BANNED: smartphone face recognition, self-driving cars, voice assistants — overused AI examples. Do NOT use these.
  BAD: "Smartphone face recognition: AI chip recognizes faces in real time" (cliche, no situation detail)
  GOOD: "**Netflix real-time subtitles**: Subtitles appear within 0.2 seconds of pressing play. The server's AI chip converts speech to text in real time." (surprising + situation detail)

- **basic_en_3_glance** (At a Glance, markdown table only):
  A **comparison table** between **2+ specific technologies/concepts**. Must use markdown table (| format).
  **Important: do NOT write "X vs Y →" prefix lines above the table.** Earlier prompts required both prefix lines + table, which duplicated information. Just the table now.
  BAD table: "| Aspect | High Efficiency | Low Efficiency |" (attribute contrast banned)
  BAD table: "| Item | Description |" (simple glossary table banned)
  GOOD table: "| | Transformer | RNN | CNN |\\n| Processing | Parallel | Sequential | Local patterns |..."
  You may add 1-2 summary sentences below the table (optional). But no prefix lines above.

- **basic_en_4_impact** (Where and Why It Matters, 4~5 bullets):
  Combine "where it is actually used or occurs + what it changed" into a single section.
  NO counterfactual speculation ("without this, X wouldn't exist"). Only real changes/damages.
  Only confident examples. If uncertain, say "may be used for ~" or drop the bullet entirely.

  **⛔ MOST IMPORTANT RULE: Do NOT list learning resources, libraries, demos, tutorials, or blog posts as bullets.**
  Those belong in `references_en`. Writing "scikit-learn demo", "AWS guide", "Hugging Face blog" as bullets here is a failure.

  Each bullet must follow ONE of 3 patterns. **You may mix patterns in the same section** — choose whichever is natural for the term.

  ---

  ### Pattern 1 — Concrete use case (product/service name + measurable change)
  **Prefer this pattern when possible.** Strongest bullet format.
  Format: `- **Product/service name**: what changed (+ source/evidence)`

  GOOD (DPO):
  - **Hugging Face TRL DPO Trainer**: Enables LLM fine-tuning from preference data alone, cutting alignment-experiment engineering complexity vs RLHF pipelines.
  - **Zephyr-7B (HuggingFace H4)**: A 7B model tuned with DPO scored on par with Llama-2-70B-chat on MT-Bench, demonstrating "small model + DPO" viability.

  GOOD (Transformer):
  - **Google Translate**: Adopted Transformers in 2016; the company reported large BLEU gains over the prior RNN-based system in its Research blog.
  - **GitHub Copilot**: Ships Transformer-based Codex as its code-completion engine; developer surveys report it is now a daily tool for many users.

  ---

  ### Pattern 2 — Occurrence conditions / shifted engineering practice (phenomena, abstract concepts)
  **Use this when you can't force-fit a product name.**
  Describe "when/where does this happen" or "what practice changed after this concept became known".
  Format: `- **Situation or changed practice**: concrete mechanism/result`

  GOOD (Overfitting):
  - **Most visible when IID assumptions break**: The wider the gap between training and test distributions, the more overfitting shows up — common in time-series, biased datasets, and distribution-shift regimes.
  - **Cross-validation as standard practice**: K-fold, early stopping, and holdout splits became table-stakes; "trust training accuracy alone" is no longer an accepted baseline.
  - **Model-selection mindset shift**: The intuition "bigger model = better" was replaced by "balance capacity with data volume" as a selection rule.
  - **Default deployment gate**: Models with large train-validation gaps are routinely rejected from production candidate pools.

  GOOD (Hallucination):
  - **Primary blocker for enterprise LLM adoption**: "Confidently stating unverified facts" is now cited as the top risk in legal, medical, and other high-stakes verticals.
  - **Why RAG architectures became mainstream**: Bolting external retrieval onto generation — rather than trusting the model's internal knowledge — became the de-facto production pattern.

  ---

  ### Pattern 3 — Evaluation context + misuse warning (metrics · benchmarks)
  Format: `- **Evaluation context**: what decision it drives + common misreading`

  GOOD (F1 Score):
  - **Standard for imbalanced classification**: On medical tasks with 1% positive rate, accuracy of 99% is meaningless — F1 is what actually reveals performance.
  - **Watch out for micro vs macro**: Reports that don't specify the averaging strategy quietly hide minority-class performance.

  ---

  **BAD — absolutely forbidden (resource listing)**:
  - "- **scikit-learn polynomial regression demo**: Training error decreases while test error rises..." ← **This is a resource, belongs in references.**
  - "- **AWS guide** (What is Overfitting?): Covers early stopping, pruning..." ← **Resource.**
  - "- **OpenAI blog**: Announced this technology..." ← **Resource.**
  - "- **Cross-validation** (k-fold, scikit-learn): Splits data into folds..." ← **Resource.**

  If 3+ bullets match the BAD pattern, this section fails. Write "use contexts · occurrence conditions · shifted practices · evaluation misuse" — not resource lists.

- **basic_en_5_caution** (Common Misconceptions, EXACTLY 3):
  3 **common misconceptions** paired with **what's actually true**. Format: `- ❌ Myth: ... → ✅ Reality: ...`. Exactly 3, no more, no less.
  Select the 3 most important misconceptions, not "every misconception". Focus on what a reader would actually get wrong.

- **basic_en_6_comm** (How It Sounds in Conversation, 5 sentences):
  5 example sentences as they appear in **team meetings, Slack threads, code reviews**. **Bold key terms** with `**`.
  NO news article tone — include specific context like team names, metrics, or deadlines. Conversational.
  Format: `- "Sentence..."`. Each a natural, single-line utterance.
  BAD: "The AI chip market is growing rapidly as major players compete." (news tone)
  GOOD: "- \\"We swapped the inference server from **A100** to **H100** and **latency dropped in half**. Cost went up but SLA comes first...\\"" (team chat tone)

- **basic_en_7_related** (Related Reading, 4~6 items):
  4~6 **related terms to read next** in a learning flow. Merges the old `8_related` + `10_learning_path Part 2`.
  Format: `- **Term name** — relationship to this term + why to read it next (one line).`
  Not a dictionary definition — include **comparison points** (performance/use-case/trade-off differences) or **learning-order reasons** that make the reader want to click.
  BAD: "**TPU** — Google's AI-specialized chip, optimized for large-scale deep learning" (dictionary, no curiosity)
  GOOD: "**TPU** — Google's answer to 'GPUs aren't enough'; ~5x faster training than GPUs but narrower general-purpose use → good to read after GPU for comparison."
  **Note**: It's OK if some related terms don't yet exist in the handbook. The frontend auto-labels missing terms as "(coming soon)". Just write correct term names.

---

## references_en (JSON array, level-independent footer)

This field is rendered in the page **footer block**, not the body. It stays visible regardless of the Basic/Advanced toggle.

**Schema** (each item in the array):
```json
{{
  "title": "Resource title",
  "authors": "Author (optional)",
  "year": 2023,
  "venue": "Venue (optional, for papers)",
  "type": "paper|docs|code|blog|wiki|book",
  "url": "https://...",
  "tier": "primary|secondary",
  "annotation": "One-line description (max 120 chars)"
}}
```

**Quality rules (must follow):**
- Total: 3~7 items
- At least 2 `primary` items required (papers, official docs, official code implementations, standards docs)
- At most 3 `secondary` items (blog posts, explainers, tutorials, marketing pages)
- URLs must come from **Reference Materials provided in the user prompt**. Do NOT fabricate URLs from memory.
- Omit any item you cannot verify.
- `annotation` is one line, max 120 chars. Explain **why a reader should look at it**. No empty labels like "intro" or "overview".
- Skip optional fields (authors, year, venue) if unknown. Empty strings are fine.
- **Tier guidance:** primary = papers, RFC/spec docs, vendor API reference, official implementation repos. secondary = marketing blogs, tutorials, intro guides, conference talk summaries.

**GOOD example (Transformer):**
```json
[
  {{"title": "Attention Is All You Need", "authors": "Vaswani et al.", "year": 2017, "venue": "NeurIPS", "type": "paper", "url": "https://arxiv.org/abs/1706.03762", "tier": "primary", "annotation": "Original Transformer paper: self-attention math + ablation experiments."}},
  {{"title": "The Illustrated Transformer", "authors": "Jay Alammar", "type": "blog", "url": "https://jalammar.github.io/illustrated-transformer/", "tier": "secondary", "annotation": "The clearest visual walkthrough of attention for newcomers."}}
]
```

**BAD examples:**
- 0 primary items + 5 blog posts (**rule violation**)
- Fabricated URL: `"url": "https://openai.com/blog/transformer-deep-dive"` (not in provided Reference Materials)
- Annotation like "a good paper" — meaningless

---

## sidebar_checklist_en (sidebar only, not body)

This field is rendered as the **"Understanding Check"** block in the right sidebar in Basic view. It is NOT part of the body.

- 4~5 questions testing whether the reader actually understood the term.
- Each question is a separate bullet separated by `\\n\\n`.
- No rote memorization — ask "why/how" questions that test understanding.
- Prefix each question with `□ ` or `[ ] `.
- No inline citations.
- GOOD: "□ What role do Q, K, V play in self-attention, and why do you need all three?\\n\\n□ Why can Transformers parallelize in a way RNNs cannot?\\n\\n□ Why does positional encoding matter — what breaks without it?"
- BAD: "□ When was the Transformer paper published?" (rote fact)
- BAD: "□ Question (Ref: W&B)" (inline citation)

---

## Output JSON Structure

```json
{{
  "hero_news_context_en": "\\"quote 1\\" → meaning\\n\\"quote 2\\" → meaning\\n\\"quote 3\\" → meaning",
  "basic_en_1_plain": "Problem → solution → mechanism, 700~1000 chars",
  "basic_en_2_example": "- **Scenario 1**: description\\n- **Scenario 2**: description\\n- **Scenario 3**: description",
  "basic_en_3_glance": "| | A | B |\\n|---|---|---|\\n| Aspect | ... | ... |",
  "basic_en_4_impact": "- **Product/service**: change\\n- **Shift in practice**: mechanism\\n- ...",
  "basic_en_5_caution": "- ❌ Myth: ... → ✅ Reality: ...\\n- ❌ Myth: ... → ✅ Reality: ...\\n- ❌ Myth: ... → ✅ Reality: ...",
  "basic_en_6_comm": "- \\"sentence 1\\"\\n- \\"sentence 2\\"\\n- \\"sentence 3\\"\\n- \\"sentence 4\\"\\n- \\"sentence 5\\"",
  "basic_en_7_related": "- **Term 1** — relationship + why to read next\\n- **Term 2** — ...\\n- **Term 3** — ...\\n- **Term 4** — ...",
  "references_en": [
    {{"title": "...", "type": "paper", "url": "...", "tier": "primary", "annotation": "..."}}
  ],
  "sidebar_checklist_en": "□ Question 1\\n\\n□ Question 2\\n\\n□ Question 3\\n\\n□ Question 4"
}}
```

## Self-Check (verify before responding)
✓ `hero_news_context_en` is EXACTLY 3 lines, each ≤70 chars, each line has a quote + arrow + meaning
✓ `basic_en_1_plain` has problem → solution → concrete mechanism (not analogy only)
✓ `basic_en_2_example` has EXACTLY 3 scenarios, none use smartphone/self-driving/voice assistant
✓ `basic_en_3_glance` is table ONLY — no "X vs Y →" prefix lines above the table
✓ `basic_en_4_impact` has 4~5 bullets. Each bullet follows ONE of the 3 allowed patterns. Mixing patterns within the section is fine.
✓ `basic_en_4_impact` does NOT list learning resources, docs, tutorials, or library names as bullets — those belong to references_en. If 3+ bullets look like resource listings, rewrite.
✓ `basic_en_5_caution` has EXACTLY 3 myth-reality pairs, not 4, not 2
✓ `basic_en_6_comm` has 5 sentences in team-meeting/slack tone, not news-article tone
✓ `basic_en_7_related` has 4~6 entries, each with comparison/learning-order reason (not dictionary definition)
✓ `references_en` has ≥2 primary items, ≤3 secondary items, total 3~7
✓ All reference URLs are from the provided Reference Materials — no fabricated links
✓ `sidebar_checklist_en` has 4~5 questions testing understanding, not memorization
✓ No section repeats content from hero_news_context_en or from another section
✓ NO deleted fields in output: no `basic_en_0_summary`, `basic_en_4_why`, `basic_en_5_where`, `basic_en_6b_news_context`, `basic_en_6c_checklist`, `basic_en_9_roles`, `basic_en_10_learning_path`, `basic_en_8_related`

## Quality Rules
- Only generate fields that are EMPTY in the input. Preserve existing non-empty fields.
- NO code in basic sections. NO complex formulas. If a simple formula is unavoidable, use double-dollar signs: $$E = mc^2$$ (NOT single $).
- FACTUAL ACCURACY: Only include examples you are confident about. If unsure, do NOT claim it.
- NO REPETITION across sections: each section must add NEW information.
- Do NOT create markdown links to /handbook/ URLs in the body text. Links are added automatically by the system. Just write plain text with **bold** for key terms.
- Do NOT fabricate URLs anywhere (body text or references_en). If unsure, OMIT.

## Markdown Formatting (within each section value)
- Use **bold** for key terms and important concepts
- Use bullet points (`-`) for lists instead of cramming items into one sentence
- Do NOT use `###` sub-headings inside body sections — sections are already rendered with H2 headers by the system
- BAD: "EDA methods are 1) visualization 2) summary statistics 3) outlier detection."
- GOOD: "- **Visualization**: patterns via plots\\n- **Summary statistics**: mean, median, etc.\\n- **Outlier detection**: flag abnormal records"

## Table Rules (glance section)
- MUST be comparison/contrast tables that ADD VALUE — NOT simple definition tables
- BAD table: "| Item | Description |\\n| EDA | Initial data analysis |" (restating a definition)
- GOOD table: "| | EDA | Statistical Analysis | Data Mining |\\n| Purpose | Explore/understand | Verify/infer | Discover patterns |\\n| Stage | Early | Hypothesis testing | Late |"
- Do NOT add "X vs Y →" prefix lines above the table. Just the table.

Respond in JSON format only."""
```

**Step 5: Run ruff to verify syntax**

Run: `cd backend && .venv/Scripts/python -m ruff check services/agents/prompts_advisor.py`
Expected: All checks passed!

**Step 6: Run the existing handbook tests to verify no imports are broken**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py -v -k "generate" --tb=short`
Expected: 4/4 generate-related tests PASS.

**Step 7: Commit**

```bash
git add backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): GENERATE_BASIC_EN_PROMPT 재작성 — 7섹션 + hero + references + checklist"
```

---

### Task 4: 5개 용어 EN 재생성 + 결과 검증

**Files:**
- Use: `c:/tmp/regen_handbook.py` (existing script)
- Read: generated JSON files in `c:/tmp/regen_<term>_result.json`

**Step 1: Regenerate overfitting**

Run: `cd backend && PYTHONPATH=. PYTHONIOENCODING=utf-8 .venv/Scripts/python c:/tmp/regen_handbook.py overfitting`
Wait until `c:/tmp/regen_overfitting_result.json` is updated.

**Step 2: Check EN fields populated correctly**

Inspect the JSON file. Verify the following EN fields exist and match spec:
- `definition_en` — 80~200 chars
- `hero_news_context_en` — exactly 3 lines, each ≤70 chars
- `body_basic_en` — 7 sections (count `## ` occurrences → must be 7)
- `references_en` — 3~7 items, ≥2 primary, ≤3 secondary
- `sidebar_checklist_en` — 4~5 questions

Run in Python:
```python
import json, re
data = json.load(open("c:/tmp/regen_overfitting_result.json", encoding="utf-8"))
assert 80 <= len(data["definition_en"]) <= 200, f"def_en={len(data['definition_en'])}"
hero_lines = data["hero_news_context_en"].split("\n")
assert len(hero_lines) == 3, f"hero={len(hero_lines)}"
assert all(len(l) <= 70 for l in hero_lines), f"line lens={[len(l) for l in hero_lines]}"
body = data["body_basic_en"]
assert body.count("## ") == 7, f"sections={body.count('## ')}"
refs = data["references_en"]
prim = sum(1 for r in refs if r["tier"] == "primary")
sec = sum(1 for r in refs if r["tier"] == "secondary")
assert 3 <= len(refs) <= 7 and prim >= 2 and sec <= 3, f"refs={len(refs)} p={prim} s={sec}"
print("OK")
```

**Step 3: Regenerate remaining 4 terms in parallel**

Run these three in parallel (background):
```bash
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py dpo
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py fine-tuning
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py hugging-face
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py mcp
```

**Step 4: Extend `c:/tmp/analyze_regen.py` to also check EN fields**

Add an `analyze_en()` helper that mirrors the KO checks. Print anti-pattern flags for `basic_en_4_impact` (look for "tutorial", "blog", "guide", "demo" as suspicious standalone tokens in bullets).

**Step 5: Run analysis**

Run: `PYTHONIOENCODING=utf-8 python c:/tmp/analyze_regen.py`
Expected output: All 5 terms show 7-section EN body, clean anti-pattern scan, references tier rules passing.

**Step 6: Manual review checklist**

For each of 5 terms, spot-check:
- [ ] `hero_news_context_en` lines are natural English news quotes
- [ ] `basic_en_1_plain` has problem → solution → mechanism structure
- [ ] `basic_en_2_example` scenarios don't overlap
- [ ] `basic_en_3_glance` table renders correctly (proper markdown pipes)
- [ ] `basic_en_4_impact` bullets follow one of the 3 patterns, no resource listing
- [ ] `basic_en_6_comm` sounds like team Slack, not news article
- [ ] `basic_en_7_related` entries give click-worthy reasons
- [ ] `references_en` URLs all resolve to real pages (spot-check 2~3 per term)
- [ ] `sidebar_checklist_en` questions test understanding, not memorization

If any spot-check fails, iterate on the prompt (Task 3) and re-regen.

**Step 7: Commit the successful regen samples (JSON files only, for record)**

Actually — **skip** this step. JSON files live in `c:/tmp/` outside the repo. No commit needed.

---

### Task 5: Plan closure — sprint status update

**Files:**
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`

**Step 1: Mark HB-REDESIGN-B as done in ACTIVE_SPRINT.md**

Find the HB-REDESIGN-B row (added when the 3 plans were registered in sprint) and change `todo` → `done`, add the completion date.

**Step 2: Commit**

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "chore: sprint sync — HB-REDESIGN-B done"
```

---

## Success Criteria

- [ ] `BASIC_SECTIONS_EN` has exactly 7 entries, keys match `basic_en_1_plain` ... `basic_en_7_related`
- [ ] `_basic_expected` dict has `"en": 7`
- [ ] `GENERATE_BASIC_EN_PROMPT` fully replaced with 7-section layout + hero + references + checklist
- [ ] All 5 sample terms regenerated and pass the manual review checklist
- [ ] `ruff check` passes on all modified files
- [ ] Existing generate tests (4/4) still pass
- [ ] New `test_basic_en_sections.py` tests pass

## Rollback Plan

If any regen produces unacceptable output, revert with:
```bash
git revert <commit-sha-of-task-3>
```
This preserves Task 1 and 2 (which are structural) while only reverting the prompt text.

## Related

- [[2026-04-09-handbook-section-redesign]] — Overall redesign spec (B is phase 2 of this)
- [[2026-04-10-handbook-save-and-render]] — Plan A (next, DB + frontend)
- [[2026-04-10-handbook-advanced-redesign]] — Plan C (last, Advanced prompts)
