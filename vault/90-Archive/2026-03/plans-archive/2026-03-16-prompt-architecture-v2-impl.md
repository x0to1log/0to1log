# Prompt Architecture v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 핸드북 프롬프트를 근본적으로 개선 — 핸드북 링크를 코드 후처리로 이동, 섹션을 JSON 키별 분리, 프롬프트 간소화.

**Architecture:** LLM은 순수 콘텐츠만 생성 (링크/체크리스트 부담 없음). 생성 후 코드가 (1) JSON 키들을 마크다운으로 조합 (2) 핸드북 용어 자동 링크 삽입.

**Tech Stack:** Python, Pydantic, OpenAI gpt-4o, Supabase

---

### Task 1: 핸드북 자동 링크 후처리 함수

**Files:**
- Modify: `backend/services/agents/advisor.py`

**구현:** `_auto_link_handbook_terms()` 함수 추가.

```python
def _auto_link_handbook_terms(content: str, handbook_slugs: dict[str, str]) -> str:
    """Replace first occurrence of each handbook term with a markdown link.

    Args:
        content: markdown text
        handbook_slugs: {term_name: slug} mapping (e.g., {"Transformer": "transformer"})

    Returns:
        content with handbook links inserted
    """
    import re
    linked = set()
    for term, slug in sorted(handbook_slugs.items(), key=lambda x: -len(x[0])):
        # Skip if already linked
        if slug in linked:
            continue
        # Match whole word, case-insensitive, first occurrence only
        pattern = re.compile(r'(?<!\[)(' + re.escape(term) + r')(?!\])', re.IGNORECASE)
        if pattern.search(content):
            content = pattern.sub(f'[\\1](/handbook/{slug}/)', content, count=1)
            linked.add(slug)
    return content
```

`_run_generate_term()` 끝에서 생성된 body 필드들에 적용:

```python
# Fetch handbook terms for auto-linking
handbook_map = {}
supabase = get_supabase()
if supabase:
    try:
        terms = supabase.table("handbook_terms").select("term, slug").eq("status", "published").execute()
        handbook_map = {t["term"]: t["slug"] for t in (terms.data or [])}
    except Exception:
        pass

# Auto-link handbook terms in generated content
if handbook_map:
    for field in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en"):
        if data.get(field):
            data[field] = _auto_link_handbook_terms(data[field], handbook_map)
```

**Commit:** `feat: add handbook auto-link post-processing`

---

### Task 2: 프롬프트 재구성 — JSON 키별 섹션 분리

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`

**GENERATE_BASIC_PROMPT 변경:**

출력 포맷을 마크다운 뭉치 → 섹션별 JSON 키로 분리:

```json
{
  "term_full": "...",
  "korean_name": "...",
  "korean_full": "...",
  "categories": ["ai-ml"],
  "definition_ko": "...",
  "definition_en": "...",
  "basic_ko_1_plain": "비유와 일상 예시로 설명...",
  "basic_ko_2_example": "- **비유1**: ...\n- **비유2**: ...",
  "basic_ko_3_glance": "| 비교 | ... |",
  "basic_ko_4_why": "- 이유1\n- 이유2...",
  "basic_ko_5_where": "- 사례1\n- 사례2...",
  "basic_ko_6_caution": "- 주의1\n- 주의2...",
  "basic_ko_7_comm": "- **용어** 어쩌구...",
  "basic_ko_8_related": "- **용어** — 관계...",
  "basic_en_1_plain": "...",
  "basic_en_2_example": "...",
  ...
}
```

프롬프트에서 **핸드북 링크 지시 + MANDATORY CHECKLIST 제거** (코드가 처리하므로).

**GENERATE_ADVANCED_PROMPT 동일 패턴:**

```json
{
  "adv_ko_1_technical": "...",
  "adv_ko_2_formulas": "...",
  "adv_ko_3_howworks": "...",
  "adv_ko_4_code": "```python\n...\n```",
  "adv_ko_5_practical": "...",
  "adv_ko_6_why": "...",
  "adv_ko_7_comm": "...",
  "adv_ko_8_refs": "...",
  "adv_ko_9_related": "...",
  "adv_en_1_technical": "...",
  ...
}
```

**Commit:** `feat: restructure handbook prompts — section-per-key JSON output`

---

### Task 3: 코드에서 JSON 키 → 마크다운 조합

**Files:**
- Modify: `backend/services/agents/advisor.py`

**`_run_generate_term()` 수정:**

LLM 응답의 JSON 키들을 마크다운으로 조합:

```python
BASIC_SECTIONS_KO = [
    ("basic_ko_1_plain", "## 💡 쉽게 이해하기"),
    ("basic_ko_2_example", "## 🍎 예시와 비유"),
    ("basic_ko_3_glance", "## 📊 한눈에 보기"),
    ("basic_ko_4_why", "## ❓ 왜 중요한가"),
    ("basic_ko_5_where", "## 🔧 실제로 어디서 쓰이나"),
    ("basic_ko_6_caution", "## ⚠️ 주의할 점"),
    ("basic_ko_7_comm", "## 💬 대화에서는 이렇게"),
    ("basic_ko_8_related", "## 🔗 함께 알면 좋은 용어"),
]
# EN, Advanced도 동일 패턴

def _assemble_markdown(data: dict, sections: list[tuple[str, str]]) -> str:
    """Assemble section-per-key JSON data into markdown."""
    parts = []
    for key, header in sections:
        content = data.get(key, "").strip()
        if content:
            parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)

# In _run_generate_term(), after parsing:
data["body_basic_ko"] = _assemble_markdown(data, BASIC_SECTIONS_KO)
data["body_basic_en"] = _assemble_markdown(data, BASIC_SECTIONS_EN)
# Remove individual section keys from data
```

**Commit:** `feat: assemble section JSON keys into markdown + auto-link`

---

### Task 4: 테스트 업데이트 + 검증

**Files:**
- Modify: `backend/tests/test_handbook_advisor.py`

Mock LLM 응답을 새 JSON 키 포맷으로 업데이트.

**Commit:** `test: update handbook tests for section-per-key format`
