# News Prompt v6 Evolution — 6 Iterations, 56 to 85 Points

> Date: 2026-03-26
> Related: [[ACTIVE_SPRINT]], [[2026-03-25-research-news-quality]]

---

## Summary

3/25 뉴스 다이제스트 품질을 6번 반복 개선하여 평균 점수 56 -> 85로 끌어올림.
핵심 발견: 모델 교체(gpt-4o vs gpt-4.1)는 효과 없었고, **프롬프트 구조 재설계**가 결정적이었음.

---

## Score History

| Version | EN Biz | EN Res | KO Biz | KO Res | Avg | Key Change |
|---------|--------|--------|--------|--------|-----|------------|
| v1 | 50 | 75 | 60 | 40 | **56** | Rules only (13 writing rules) |
| v2 | 45 | 70 | 30 | 45 | **48** | gpt-4o rollback (A/B test) |
| v3 | 85 | 90 | 45 | 50 | **68** | Few-shot skeleton (EN Business Expert only) |
| v4 | 92 | 88 | 70 | 65 | **79** | Full KO skeleton + 80% length guard |
| v5 | 93 | 88 | 70 | 65 | **79** | Structural parity (sections/items/paragraphs) |
| v6 | 95 | 93 | 75 | 78 | **85** | Per-persona skeleton (4 separate skeletons) |

---

## Key Decisions & Learnings

### 1. Model is not the problem, prompt is

gpt-4o vs gpt-4.1 A/B test (v2) showed both models fail identically:
- Section headers ignored
- Citations missing
- KO content shortened

Conclusion: instruction following quality depends on prompt structure, not model choice.
Decision: Keep gpt-4.1 (better IFEval 87.4% vs gpt-4o 81%, cheaper).

### 2. Few-shot skeleton > rule listing

v1 (13 rules) scored 56. v3 (same rules + 1 skeleton example) scored 68.
LLMs follow examples better than instructions. The skeleton shows the desired output shape directly.

### 3. Per-persona skeleton is critical

v3 had only Business Expert skeleton shared across all 4 personas.
Result: Research Learner wrote like Business Expert (wrong sections, wrong tone).
v6 gave each persona its own skeleton -> Research Learner now uses analogies and plain language first.

### 4. KO requires explicit structural parity rules

"80% of EN length" was wrong — Korean is naturally shorter in characters.
Changed to: "same number of ## sections, ### sub-items, and paragraphs per item."
KO coverage matched EN from v4 onward.

### 5. Sandwich pattern works for checklist items

FINAL CHECKLIST at prompt end (8 verification items) improved compliance for:
- Citation format
- Section headers
- KO = EN parity
- headline_ko in Korean

### 6. Research Learner accessibility: "plain language first, technique name second"

BAD: "uses diffusion-based parallel decoding"
GOOD: "processes the entire page at once instead of one character at a time -- a technique called parallel diffusion decoding"

This rule + skeleton example made Research Learner genuinely accessible. Verified in v6 output.

---

## Remaining Issues

### High Priority
- **KO citation missing**: EN has [N](URL) or bottom Sources, KO has neither. Persistent across all versions.
- **Persona-specific source display**: Backend saves sources_expert/sources_learner separately, but frontend tab switching doesn't update source list yet (reverted due to 500 error).

### Low Priority
- **Vol.01 No.10 hallucination**: LLM adds editorial metadata not in prompt. Harmless but annoying.
- **EN Research Expert tone bleed**: Learner-style analogies appearing in Expert content (skeleton cross-contamination).

---

## Technical Changes Made

### Prompt (prompts_news_pipeline.py)
- 4 skeleton constants: BUSINESS_EXPERT_SKELETON, BUSINESS_LEARNER_SKELETON, RESEARCH_EXPERT_SKELETON, RESEARCH_LEARNER_SKELETON
- SKELETON_MAP routes correct skeleton to each (digest_type, persona) combination
- _build_digest_prompt accepts skeleton parameter via {skeleton} interpolation
- Citation format: [Source Title](URL) -> [N](URL) Perplexity style
- Math formula: $$ enforced (single $ conflicts with currency)
- sources field added to JSON output schema (id, url, title)
- Research Learner guide: "lead with WHAT IT DOES before naming the technique"
- FINAL CHECKLIST: 8 verification items at prompt end (sandwich pattern)
- Quality check prompts aligned with current digest format

### Pipeline (pipeline.py)
- KO headline fallback: prefix "AI {type} Daily --" if no Korean chars
- persona_sources: dict capturing sources per persona separately
- source_cards: filtered by URL validity before saving
- Quality check model: o4-mini -> gpt-4.1-mini (o4-mini returned empty responses)
- Equal coverage rule enforced
- Analysis sections marked MANDATORY (never omit)

### Frontend (markdown.ts)
- rehypeKatex moved after rehypeSanitize (prevents 500 error on math content)
- personaSourceCardsMap with try-catch guard (prepared for future tab switching)

### Config
- gpt-4.1 restored as primary model after A/B test
- gpt-4.1-mini for quality checks and classification

---

## Next Steps

1. Fix KO citation -- most impactful remaining improvement
2. Implement persona source tab switching (frontend)
3. Monitor quality scores with updated quality check prompts
4. Consider hybrid quality check (code-based rules + LLM scoring)

---

## Related
- [[2026-03-17-v4-two-persona-decision]] — 2 persona decision
- [[2026-03-25-research-news-quality]] — initial quality audit
- [[2026-03-24-3tier-model-decision]] — model selection rationale
