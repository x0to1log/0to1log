# Handbook Category-Aware Prompt Architecture Design

## Goal

Seed-generated handbook drafts should not force every term into the same explanation pattern. This design task defines a **common prompt skeleton + category/type-specific guide layer** so each category gets the right content shape before generation, rather than relying on manual remediation after bad drafts appear.

## Problem

Recent seed drafts showed the same failure pattern:

- Safety/governance terms received unnecessary code or formula sections.
- Workflow/capability terms sometimes drifted into provider tutorial mode.
- Product/platform terms need official-doc and version-volatility handling, while math/stat terms need formula intuition and failure conditions.
- `advanced_2` currently behaves too much like “must include formula”, even when taxonomy, workflow, matrix, or architecture is the correct artifact.

## Scope

This is a design/research task, not implementation yet.

In scope:

- Define the category guide structure for the 9 seed categories.
- Decide which prompt parts remain global and which become category/type-specific.
- Define field-specific guidance for `definition`, `summary`, `basic`, `advanced`, `references`, and `code_mode_hint`.
- Specify how category guide, term_type guide, subtype guide, source policy, and remediation gate should compose.
- Produce 2-3 pilot prompts and expected output shapes for validation.

Out of scope:

- Full prompt implementation.
- Bulk seed generation.
- DB schema changes.
- Publishing any new terms.

## Proposed Architecture

Use layered prompt composition:

1. **Global Handbook Contract**
   - Required fields and bilingual structure.
   - Basic/advanced section count.
   - KO/EN reference URL parity.
   - Learner popup summary requirement.
   - No unsupported named claims.

2. **Category Guide**
   - Category-specific explanation emphasis.
   - Preferred advanced artifacts.
   - Reference source preference.
   - Anti-patterns.

3. **Term Type Guide**
   - `foundational_concept`, `system_workflow_pattern`, `capability_feature_spec`, `product_platform_service`, etc.
   - Determines whether code is appropriate.
   - Determines whether advanced should be mechanism, workflow, spec, benchmark, formula, or taxonomy-heavy.

4. **Term-Specific Override**
   - Curated references.
   - Preferred code mode.
   - Focus guide for known high-value or high-risk terms.

5. **Post-Generation Gate**
   - Checks that the generated shape matches the selected category/type guide.
   - Blocks publish review if the draft used the wrong artifact type.

## Category Guide Direction

| Category | Preferred Advanced Shape | Code Default | Reference Priority | Avoid |
|---|---|---|---|---|
| llm-genai | mechanism, runtime loop, tool/data boundary, failure modes | conditional | papers, official docs, strong technical blogs | generic AI trend prose |
| deep-learning | architecture, training dynamics, formula, implementation caveats | conditional | papers, framework docs | product/provider examples |
| products-platforms | feature surface, API/docs, pricing/version volatility, integration boundaries | conditional | official docs first | unsourced claims, benchmark drift |
| ml-fundamentals | intuition, formal definition, assumptions, failure cases | mostly no-code or pseudocode | textbooks/docs/papers | over-modern LLM framing |
| infra-hardware | system architecture, bottlenecks, throughput/latency, deployment constraints | conditional | vendor docs, benchmarks, systems papers | vague performance claims |
| data-engineering | data flow, storage/indexing, consistency, operational tradeoffs | conditional | official docs, architecture docs | model-centric explanation |
| cs-fundamentals | concept, algorithm, complexity, where AI uses it | pseudocode when useful | CS references/docs | overfitting to LLM usage |
| math-statistics | intuition, formula, assumptions, example, failure modes | no-code | textbooks/papers | code-first tutorial |
| safety-ethics | taxonomy, incident workflow, governance evidence, risk controls | no-code by default | official guidance, standards, incident databases | forced formulas/code, philosophical generalities |

## Design Questions

- Should `advanced_2` be renamed internally from formula/spec to `technical_artifact`?
- Should code mode be decided before generation from category/type, or after reference gate?
- Which categories should ever allow real code by default?
- How strict should related-term validation be when DB does not yet contain the related term?
- Should `safety-ethics` and `products-platforms` have stronger official-source requirements than other categories?

## Deliverables

- A prompt composition spec with:
  - global prompt blocks
  - category guide blocks
  - term_type guide blocks
  - composition order
  - conflict resolution rules
- A table mapping 9 categories to:
  - preferred advanced artifact
  - default code mode
  - reference policy
  - anti-patterns
- Pilot prompt examples for:
  - `Safety Incident`
  - `Context Window`
  - one product/platform term
- Acceptance criteria for implementation.

## Acceptance Criteria

- The design clearly explains how category guide and term_type guide combine.
- `safety-ethics` terms default away from formulas/code unless explicitly implementation-oriented.
- `products-platforms` terms prioritize official docs and volatility handling.
- `math-statistics` terms preserve formulas but add assumptions and failure modes.
- The design can be implemented without creating 9 fully separate prompts.
- The design includes at least one pilot comparison against a previously problematic draft.

