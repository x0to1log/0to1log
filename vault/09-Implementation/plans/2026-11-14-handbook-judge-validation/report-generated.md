# Handbook judge vs publish/archive decisions

- Scored: published 34, archived 20 (errors 0, judge missing 7)
- Recorded cost: $10.08
- AUC = chance that a published term outscores an archived one. 0.5 is no signal, 1.0 is perfect.

## Does the score separate the groups?

| Score | published mean (sd) | archived mean (sd) | AUC | 95% interval |
|---|---|---|---|---|
| advanced, judge only | 56.2 (10.9) | 52.1 (17.8) | 0.54 | 0.35–0.73 |
| advanced, after penalty | 39.9 (21.4) | 35.3 (24.4) | 0.59 | 0.41–0.75 |
| basic, judge only | 63.9 (9.9) | 59.2 (10.0) | 0.63 | 0.46–0.78 |
| basic, after penalty | 48.3 (20.0) | 42.6 (17.4) | 0.58 | 0.41–0.73 |
| structural penalty (code, negated) | -16.6 (11.6) | -16.2 (9.1) | 0.50 | 0.34–0.65 |

### source = pipeline only (published 34, archived 20)

| Score | published mean (sd) | archived mean (sd) | AUC | 95% interval |
|---|---|---|---|---|
| advanced, judge only | 56.2 (10.9) | 52.1 (17.8) | 0.54 | 0.35–0.73 |
| advanced, after penalty | 39.9 (21.4) | 35.3 (24.4) | 0.59 | 0.41–0.75 |
| basic, judge only | 63.9 (9.9) | 59.2 (10.0) | 0.63 | 0.46–0.78 |
| basic, after penalty | 48.3 (20.0) | 42.6 (17.4) | 0.58 | 0.41–0.73 |
| structural penalty (code, negated) | -16.6 (11.6) | -16.2 (9.1) | 0.50 | 0.34–0.65 |

## Gate at 70

| | published | archived |
|---|---|---|
| advanced ≥ 70 | 5/33 | 0/18 |
| basic ≥ 70 | 7/31 | 0/19 |

## Sub-scores (0–10)

| Sub-score | published mean (sd) | archived mean (sd) | AUC | 95% interval |
|---|---|---|---|---|
| adv · accuracy.factual_correctness | 5.2 (1.4) | 4.7 (1.7) | 0.55 | 0.37–0.72 |
| adv · accuracy.hallucination_absence | 5.2 (2.5) | 4.6 (1.9) | 0.56 | 0.38–0.72 |
| adv · accuracy.term_differentiation | 7.0 (0.0) | — | — | — |
| adv · structural_completeness.format_compliance | 3.3 (3.0) | 3.9 (3.6) | 0.49 | 0.31–0.68 |
| adv · structural_completeness.required_sections_present | 8.3 (0.8) | 7.7 (1.4) | 0.60 | 0.42–0.77 |
| adv · technical_depth.code_or_formula | 5.4 (1.1) | 4.8 (2.2) | 0.56 | 0.38–0.74 |
| adv · technical_depth.concrete_specifics | 5.2 (1.0) | 4.9 (2.4) | 0.50 | 0.30–0.70 |
| adv · technical_depth.factual_correctness | 5.8 (1.9) | 6.2 (0.5) | 0.53 | 0.16–0.88 |
| adv · technical_depth.format_compliance | 3.5 (4.9) | 8.0 (0.0) | 0.00 | — |
| adv · technical_depth.hallucination_absence | 6.3 (2.9) | 5.8 (1.0) | 0.67 | 0.00–1.00 |
| adv · technical_depth.internal_non_redundancy | 4.0 (1.4) | 5.0 (1.4) | 0.25 | 0.00–1.00 |
| adv · technical_depth.mechanism_clarity | 6.4 (1.1) | 5.5 (2.3) | 0.58 | 0.39–0.76 |
| adv · technical_depth.required_sections_present | 7.5 (2.1) | 9.0 (0.0) | 0.25 | — |
| adv · technical_depth.term_differentiation | 5.0 (1.4) | 5.5 (3.5) | 0.50 | 0.00–1.00 |
| adv · uniqueness.internal_non_redundancy | 4.8 (0.8) | 4.7 (1.0) | 0.54 | 0.36–0.72 |
| adv · uniqueness.term_differentiation | 6.5 (1.2) | 5.1 (2.3) | 0.66 | 0.46–0.83 |
| basic · accuracy.concept_clarity | 7.3 (2.1) | — | — | — |
| basic · accuracy.factual_correctness | 5.4 (1.7) | 5.3 (1.2) | 0.51 | 0.34–0.68 |
| basic · accuracy.hallucination_absence | 6.1 (2.2) | 5.8 (1.4) | 0.52 | 0.35–0.68 |
| basic · accuracy.non_redundancy | 5.0 (0.0) | — | — | — |
| basic · accuracy.product_claim_accuracy | 5.3 (2.0) | 5.7 (2.1) | 0.45 | 0.28–0.62 |
| basic · engagement.analogy_effectiveness | 5.9 (1.4) | 5.7 (1.6) | 0.54 | 0.37–0.71 |
| basic · engagement.concept_clarity | 7.0 (1.0) | 7.0 (0.0) | 0.50 | — |
| basic · engagement.factual_correctness | 6.2 (1.8) | 7.0 (0.0) | 0.30 | — |
| basic · engagement.hallucination_absence | 7.4 (2.1) | 9.0 (0.0) | 0.30 | — |
| basic · engagement.misconceptions_and_conversation | 8.0 (0.0) | 6.0 (0.0) | 1.00 | — |
| basic · engagement.non_redundancy | 5.7 (0.6) | 5.0 (0.0) | 0.83 | — |
| basic · engagement.plain_language_clarity | 5.9 (0.7) | 5.7 (1.1) | 0.54 | 0.38–0.70 |
| basic · engagement.product_claim_accuracy | 7.2 (1.6) | 9.0 (0.0) | 0.10 | — |
| basic · engagement.reader_hook | 6.1 (0.9) | 5.5 (1.6) | 0.60 | 0.42–0.77 |
| basic · engagement.required_sections_present | 9.0 (0.0) | 9.0 (0.0) | 0.50 | — |
| basic · structural_completeness.misconceptions_and_conversation | 6.9 (0.8) | 6.1 (1.4) | 0.66 | 0.49–0.80 |
| basic · structural_completeness.required_sections_present | 8.5 (0.7) | 8.2 (0.9) | 0.58 | 0.42–0.73 |
| basic · uniqueness.concept_clarity | 6.5 (1.6) | 5.6 (2.2) | 0.62 | 0.43–0.79 |
| basic · uniqueness.non_redundancy | 5.2 (0.8) | 4.7 (0.7) | 0.70 | 0.55–0.83 |
| basic · uniqueness.required_sections_present | 8.5 (0.7) | 8.0 (0.0) | 0.75 | — |

## Who is in each group

| | published | archived |
|---|---|---|
| source = pipeline | 34 | 20 |
| body_basic_ko chars, mean (sd) | 2962.3 (776.2) | 2845.1 (807.8) |
| body_basic_en chars, mean (sd) | 6542.4 (1848.9) | 5935.6 (1287.7) |
| body_advanced_ko chars, mean (sd) | 8015.2 (2926.6) | 8679.0 (3057.2) |
| body_advanced_en chars, mean (sd) | 14340.4 (5760.3) | 14298.5 (4280.5) |

## Same judge, same text, scored twice

| Score | terms | mean abs difference | max | gate result flipped |
|---|---|---|---|---|
| advanced | 18 | 2.3 | 6 | 0/18 |
| basic | 17 | 3.2 | 9 | 0/17 |

