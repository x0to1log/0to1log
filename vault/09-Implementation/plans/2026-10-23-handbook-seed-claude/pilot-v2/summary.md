# Handbook writer pilot — summary

> full-quality 생성, 판정은 모두 gpt-6.1-sol. 본문은 같은 폴더의 `<slug>__<model>.md`.

| term | model | advanced | basic | gate | penalty | cost | time | basic KO 글자 | advanced KO 글자 |
|---|---|---|---|---|---|---|---|---|---|
| Red Teaming | claude-sonnet-5-5 | 71 | 92 | pass | 0 | $0.9177 | 302s | 2816 | 5454 |
| Red Teaming | claude-opus-5-5 | 76 | 91 | pass | 0 | $0.4188 | 773s | 2730 | 7182 |
| SGLang | claude-sonnet-5-5 | 63 | 70 | review_required | 1 | $1.2522 | 328s | 2981 | 7546 |
| SGLang | claude-opus-5-5 | 63 | 98 | review_required | 1 | $2.9306 | 608s | 3077 | 8478 |
| Bradley–Terry Model | claude-sonnet-5-5 | — | — | **error** | — | $0.0 | 260s | JSONDecodeError: Expecting value: line 1 column 1 (char 0) | |
| Bradley–Terry Model | claude-opus-5-5 | 70 | 78 | pass | 3 | $2.2741 | 590s | 2959 | 7963 |

| model | 평균 advanced | 평균 basic | 용어당 비용 | 용어당 시간 |
|---|---|---|---|---|
| claude-sonnet-5-5 | 67.0 | 81.0 | $1.1 | 315.0s |
| claude-opus-5-5 | 69.7 | 89.0 | $1.9 | 657.0s |
