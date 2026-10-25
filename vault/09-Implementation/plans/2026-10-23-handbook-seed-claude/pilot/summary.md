# Handbook writer pilot — summary

> full-quality 생성, 판정은 모두 gpt-6.1-sol. 본문은 같은 폴더의 `<slug>__<model>.md`.

| term | model | advanced | basic | gate | penalty | cost | time | basic KO 글자 | advanced KO 글자 |
|---|---|---|---|---|---|---|---|---|---|
| Red Teaming | claude-sonnet-5-5 | 70 | 63 | review_required | 0 | $1.5958 | 652s | 4286 | 9101 |
| Red Teaming | claude-opus-5-5 | 69 | 91 | review_required | 0 | $0.4892 | 778s | 2602 | 6828 |
| Red Teaming | gpt-6.1-sol | 72 | 84 | pass | 0 | $0.399 | 591s | 2594 | 7202 |
| SGLang | claude-sonnet-5-5 | 57 | 52 | blocked | 4 | $2.0762 | 746s | 4216 | 10767 |
| SGLang | claude-opus-5-5 | 51 | 55 | blocked | 7 | $4.6042 | 1178s | 4585 | 16150 |
| SGLang | gpt-6.1-sol | 66 | 73 | review_required | 7 | $0.6279 | 833s | 2853 | 8051 |
| Bradley–Terry Model | claude-sonnet-5-5 | 62 | 63 | review_required | 0 | $1.8757 | 812s | 3847 | 13027 |
| Bradley–Terry Model | claude-opus-5-5 | 68 | 69 | review_required | 0 | $4.3022 | 1263s | 4037 | 13124 |
| Bradley–Terry Model | gpt-6.1-sol | 87 | 89 | pass | 2 | $0.5318 | 774s | 2643 | 9814 |

| model | 평균 advanced | 평균 basic | 용어당 비용 | 용어당 시간 |
|---|---|---|---|---|
| claude-sonnet-5-5 | 63.0 | 59.3 | $1.8 | 736.7s |
| claude-opus-5-5 | 62.7 | 71.7 | $3.1 | 1073.0s |
| gpt-6.1-sol | 75.0 | 82.0 | $0.5 | 732.7s |
