# Constrained Decoding — claude-sonnet-5-5

- advanced 82 / basic 78 / gate pass / penalty 0 / $1.2485 / 293s

## definition_en

Constrained decoding is an inference-time technique that intervenes at each token-generation step of a language model, masking out tokens that cannot lead to a valid continuation under a schema, grammar, or regex, so that sampling happens only among legal tokens and the final output conforms to the predefined structure.

## definition_ko

제약 디코딩은 LLM이 토큰을 생성하는 매 단계에서 스키마·문법·정규식 같은 제약에 비추어 유효한 연속이 될 수 없는 토큰을 걸러내고 남은 후보에서만 샘플링하게 하여, 출력이 사전에 정한 구조를 항상 따르도록 보장하는 추론 시점 기법이다.

## summary_en

Constrained decoding is a way to make an AI model write only in a format you specify, such as valid JSON. Think of a form where the box only accepts characters that fit the field: the model still chooses what to write, but impossible choices are blocked. At every step, the system works out which next pieces of text (tokens) would still keep the output valid and hides all the others before the model picks one. This matters because programs that consume AI output break on a single stray bracket or quote.

## summary_ko

제약 디코딩은 AI가 글을 쓸 때 문법에 맞지 않는 글자는 아예 고르지 못하게 막아두는 방식이다. 빈칸 채우기 시험지에서 정답 후보만 보기로 남겨두는 것과 비슷하다. 모델이 다음 단어를 고를 때마다 지금까지의 글이 JSON 같은 정해진 형식을 깨지 않는 후보만 남기고 나머지는 선택 불가로 만든다. 덕분에 결과물이 항상 형식에 맞아서, 프로그램이 AI 답변을 바로 받아 쓸 수 있다.

## body_basic_en

## Plain Explanation
Language models write text one small piece (a **token**) at a time, and each choice is probabilistic. That is fine for a human reader, but when the output feeds another program, such as a service API, one misplaced quote or missing bracket can break everything. Prompting the model to "please answer in JSON" is only a request, and nothing guarantees the model complies.

Constrained decoding turns the request into a rule. Picture a crossword grid where each square only accepts certain letters: the solver still chooses the word, but impossible letters are simply not allowed. You describe the format as a JSON Schema, a grammar, or a regular expression (a pattern for text), and the system checks, step by step, what the text written so far looks like and which next tokens could still lead to a valid result.

Mechanically, the model produces a score (a **logit**) for every token in its vocabulary, which typically holds tens of thousands of entries. The constraint engine sets the scores of illegal tokens to negative infinity, which makes their probability exactly zero after the softmax step that turns scores into probabilities. The model then samples only among the survivors. The engine does not write the answer; it only narrows the path, so the model still decides the content.

## Examples & Analogies
- **Tool-call arguments for an agent**: An agent has a registry of tools such as `search_orders` and `refund_payment`. Constraining the output to those exact names prevents the model from inventing an action that does not exist.
- **SQL generation for an analytics dashboard**: A grammar for SQL keeps the output parseable, so the database does not reject the query because of a syntax slip. Whether the query answers the business question correctly is still up to the model.
- **Forcing a glossary term in translation**: In neural machine translation research, lexically constrained decoding forces specified words or phrases to appear in the output, for example to respect a domain-specific dictionary. A 2018 paper by Post and Vilar presented a method whose cost does not grow with the number of constraints.

## At a Glance
| | Prompt-only formatting | Post-hoc validation and retry | Constrained decoding |
|---|---|---|---|
| When the format is enforced | Not enforced, only requested | After the full output is written | During each token step |
| Invalid output possible? | Yes | Yes, until a retry passes | Structurally invalid output is blocked |
| Extra runtime work | None | Repeat generation on failure | Constraint tracking and masking at every step |
| What it cannot fix | Everything | Cost of retries | Factual correctness, permissions |

Prompting asks for a format, validation catches failures afterward, and constrained decoding prevents structural failures from happening while leaving meaning and correctness to other safeguards.

## Where and Why It Matters
- **JSON Schema in commercial APIs**: A January 2025 benchmark paper notes that providers such as OpenAI have built JSON Schema support directly into their APIs, and that JSON Schema has become a key way to specify output constraints.
- **Open-source grammar engines**: Guidance, Outlines, XGrammar, and the grammar module of llama.cpp are frameworks that apply constrained decoding to local and self-hosted models.
- **JSONSchemaBench evaluation**: Researchers assembled 10K real-world JSON schemas and tested six frameworks. They reported that constrained decoding sped up generation by up to 50% in their tests and improved downstream task accuracy by up to 4%, though framework support for real-world schemas varied widely.
- **Large allowed-sequence sets in generative retrieval**: The STATIC project (a demonstration implementation released on GitHub, now archived) restricts decoding to a prespecified set of token sequences and targets GPUs and TPUs.
- **Fewer retry and repair layers**: Because every sampled token is legal, the finished output parses, so teams can drop much of the retry logic they would otherwise need.

## Common Misconceptions
- ❌ Myth: If the output matches the schema, the answer is correct. → ✅ Reality: Constrained decoding guarantees structure, not truth. A perfectly valid JSON object can still contain a wrong fact or a poor choice of action.
- ❌ Myth: It makes generation slower. → ✅ Reality: Complex constraints add per-step work, but a 2025 benchmark study found that constrained decoding can speed generation by up to 50% compared with unconstrained decoding. The result depends on the framework and the schema.
- ❌ Myth: Every framework supports every schema feature. → ✅ Reality: In the same study, the best framework supported about twice as many real-world JSON schemas as the worst one. Check coverage before relying on a particular schema feature.

## How It Sounds in Conversation
- "The parser keeps choking on the model's output, so let's switch the extraction step to **constrained decoding** with our JSON Schema."
- "Schema-valid doesn't mean right, so we still validate the **tool arguments** and check permissions before anything runs."
- "Which **grammar engine** are we using for the local model, **Outlines** or **llama.cpp grammars**? I want to see how each handles our nested schema."
- "Retry rate on the order-parsing job dropped after we turned on **structured outputs**, so we can delete the repair script."
- "Our enum has a few hundred allowed values, so let's profile the **token masking** overhead before we ship it."

## Related Reading
- (before) **Token** — Constrained decoding works at the token level, so you need to know what a token is first.
- (before) **Softmax** — The explanation of why a score of negative infinity yields exactly zero probability rests on how softmax turns scores into probabilities.
- (similar) **Function Calling** — A related way to get machine-readable output; the model picks a tool and the app executes it, whereas constrained decoding limits tokens directly.
- (similar) **Structured Outputs** — The product-level name for getting schema-conforming responses, often built on constrained decoding.
- (next) **Beam Search** — The search procedure that lexically constrained decoding for translation modifies to force required words into the output.
- (next) **Grammar-Based Sampling** — (GBNF) — A concrete way to write grammars that local inference engines use to restrict output.

## body_basic_ko

## 쉽게 이해하기
AI가 쓴 답은 프로그램이 읽어야 할 때가 많다. 그런데 모델은 확률로 글자를 고르기 때문에, 괄호를 빼먹거나 정해진 항목 이름을 엉뚱하게 바꾸는 일이 생긴다. 한 글자만 어긋나도 받는 쪽 프로그램은 오류를 내기 때문에, 예전에는 다시 시도하거나 고치는 코드를 따로 붙여야 했다.

제약 디코딩은 이 문제를 쓰기 전에 막는다. 숫자만 입력되는 칸에는 글자를 아예 칠 수 없고, 어떤 숫자를 넣을지는 사용자가 정하는 것과 같다. 규칙에 어긋나는 선택지만 지워지고, 규칙 안에서 무엇을 고를지는 여전히 모델이 정한다.

구체적으로는 모델이 다음 토큰의 점수를 계산하면, 지금까지 쓴 부분을 기준으로 규칙상 이어질 수 없는 토큰의 점수를 지워 확률을 0으로 만든다. 남은 후보 중에서 하나를 고르는 일을 매 단계 반복하므로 완성된 결과는 규칙을 지킨다. 연구에서는 이 방식을 구현한 도구들을 '문법 엔진'이라고도 부른다.

## 비유와 예시
- **도구 이름 고정**: 고객센터 에이전트가 `search_orders`와 `refund_payment` 두 도구만 쓸 수 있다고 하자. 제약 디코딩을 걸면 `refund_payments`처럼 없는 이름은 아예 만들어질 수 없다.
- **날짜·전화번호 형식 강제**: 정규식으로 `2026-04-15`나 `010-1234-5678` 같은 형식을 지정하면, 모델은 자릿수와 하이픈 위치를 어길 수 없다. 숫자 자체를 맞게 고르는 일은 여전히 모델의 몫이다.
- **번역에서 용어 고정**: 번역기에 '반드시 이 단어를 쓰라'는 용어집 조건을 줄 수 있다. 2018년 Post와 Vilar의 연구는 이 조건을 빔 서치에 반영하는 방법을 더 빠르게 만들었다.

## 한눈에 비교
| | 제약 디코딩 | 프롬프트로 형식 요청 | 생성 후 검증·재시도 |
|---|---|---|---|
| 작동 시점 | 토큰을 고르기 직전 | 생성 전 지시문 | 생성이 끝난 뒤 |
| 형식 보장 | 규칙상 유효한 출력만 가능 | 보장 없음 | 실패하면 다시 생성 |
| 추가 부담 | 매 단계 규칙 상태 계산 | 거의 없음 | 재시도 비용 |
| 의미 정확성 | 보장 못 함 | 보장 못 함 | 검증 규칙에 따라 다름 |

제약 디코딩은 형식 오류를 생성 단계에서 원천 차단하지만, 값이 맞는지 같은 의미 검증은 여전히 별도로 해야 한다.

## 어디서 왜 중요한가
- **OpenAI·Gemini API**: 두 서비스는 API에서 JSON 스키마 기반 구조화 출력을 제공한다. 2025년 JSONSchemaBench 연구(실제 스키마 1만 개, 6개 프레임워크 평가)는 이를 업계가 스키마로 제약을 지정하는 흐름의 사례로 소개한다.
- **오픈소스 문법 엔진**: 같은 연구는 Guidance, Outlines, XGrammar, llama.cpp의 문법 모듈을 평가 대상으로 다뤘다. 로컬 모델에서도 같은 방식으로 형식을 강제할 수 있다.
- **속도 개선 가능성**: 고정된 키 이름이나 닫는 괄호처럼 가능한 토큰이 하나뿐이면, 엔진이 모델을 부르지 않고 바로 채울 수 있어 그 단계를 건너뛴다. 이 때문에 같은 연구는 제약 없는 생성보다 최대 50% 빨라질 수 있다고 보고했다.
- **도구 호출 안정화**: 도구 이름과 인자 형태를 규칙으로 묶어 두면, 레지스트리에 없는 행동 이름을 만들어 내는 오류를 막을 수 있다.

## 자주 하는 오해
- ❌ 오해: 스키마를 지키면 행동도 올바르다 → ✅ 실제: `refund_payment`가 스키마상 올바르게 호출돼도 환불 대상이 잘못될 수 있다. 형식과 내용의 정확성은 별개라 권한·값 검증이 따로 필요하다.
- ❌ 오해: 규칙만 걸면 공짜로 안전해진다 → ✅ 실제: 매 단계 마스킹과 상태 계산이 추가되고, 스키마를 잘못 설계하면 자연스러운 답마저 막힐 수 있다.
- ❌ 오해: 어떤 JSON 스키마든 똑같이 지원된다 → ✅ 실제: JSONSchemaBench 기준으로 프레임워크마다 실제 스키마 지원 범위가 크게 달라, 가장 많이 지원하는 쪽이 가장 적은 쪽의 두 배였다.

## 대화에서는 이렇게
- "응답이 가끔 JSON이 깨져서 재시도 로직이 계속 늘고 있어요. **constrained decoding** 켜면 파싱 에러는 사라지지 않을까요?"
- "스키마는 통과하는데 환불 금액이 틀렸어요. **스키마 검증**은 형식만 보장하니까 값 검증을 따로 넣어야겠네요."
- "이 스키마가 너무 복잡해서 **grammar engine**이 지원을 못 해요. 중첩을 좀 줄여서 다시 해보죠."
- "마스킹 때문에 **토큰당 처리 시간**이 늘었는지 프로파일링해 봐야겠어요. 키 이름 구간은 오히려 빨라졌을 수도 있고요."
- "로컬 모델이라 OpenAI의 structured outputs는 못 쓰는데, **Outlines**나 llama.cpp 문법 모듈로 같은 효과 낼 수 있어요."

## 함께 읽으면 좋은 용어
- (기초) **디코딩 전략** — (그리디·샘플링) — 제약 디코딩은 이 단계에 끼어드는 기법이라, 토큰을 어떻게 고르는지 먼저 알아야 이해가 쉽다.
- (기초) **빔 서치** — 번역의 어휘 제약 디코딩이 빔 서치를 변형해 필수 단어를 강제했던 만큼, 원래 방식을 알면 흐름이 이어진다.
- (유사) **함수 호출** — (Function Calling) — 도구와 인자 형태를 고르는 인터페이스라는 점은 비슷하지만, 제약 디코딩은 생성 시점에 토큰 수준에서 강제한다는 점이 다르다.
- (유사) **JSON 모드** — 출력이 JSON이 되도록 요청하는 기능으로, 스키마까지 강제하는 구조화 출력과 보장 범위가 어떻게 다른지 비교해 볼 만하다.
- (심화) **구조화 출력** — (Structured Outputs) — 스키마를 지정해 응답 형식을 지키게 하는 API 기능으로, 실무에서 제약 디코딩을 쓰는 가장 흔한 형태다.

## body_advanced_en

## Technical Definition & How It Works
Constrained decoding is an inference-time intervention on autoregressive sampling. A constraint (JSON Schema, grammar, or regex) is compiled offline into a state machine or prefix index. At each step the engine maps the current state s_t to a set of legal next tokens A(s_t), builds a vocabulary-sized mask, sets the logits of every token outside A(s_t) to negative infinity, and only then runs the sampler. After softmax, a token with logit −∞ has probability exactly zero, so any strategy (greedy, temperature, top-p) can only return a legal token. The constraint engine never writes content; it narrows the path while the model supplies probabilities among the survivors.

Components and responsibilities:
- **Constraint compiler**: turns a schema, grammar, or regex into a finite-state machine, pushdown automaton, or trie. The JSONSchemaBench paper calls these frameworks grammar engines and uses the two terms interchangeably.
- **State tracker**: advances s_t with every sampled token.
- **Mask builder**: computes A(s_t) and applies it to the logits at every step.
- **Sampler**: unchanged. It runs after the mask.
- **Host**: validates meaning, permissions, and side effects, which the mask cannot guarantee.

Control flow per step:
1. The model forward pass produces logits over the full vocabulary (typically 32K–128K entries).
2. The engine looks up A(s_t) from the current state.
3. Logits outside A(s_t) are set to −∞.
4. The sampler draws token_t from the masked distribution.
5. The state transitions to s_{t+1}, and the loop ends when EOS is legal and sampled.

Cost: the model forward pass is unchanged, and constraint work adds per-step state processing and masking, which grows with constraint complexity. How it scales depends on the index design. In beam-search settings, the STATIC implementation (sparse transition matrix trie index, per its README) reports a mask cost independent of the total number of constraints, using a dense lookup table for the first layers and a CSR sparse matrix for the tail. The lexically constrained decoding lineage reports O(Nk2^C) for constrained beam search, O(NkC) for grid beam search, and O(Nk) for Post and Vilar's dynamic beam allocation (N = length, k = beam size, C = constraint count). JSONSchemaBench reports that constrained decoding can speed up generation by up to 50% over unconstrained decoding, that the best framework supported twice as many real-world schemas as the worst, and that downstream task accuracy improved by up to 4%, including on GSM8k. The paper does not give per-framework latency formulas here, so benchmark your own schemas.

## Formulas, Architecture, and Diagrams
Architecture and data flow (offline compile, online mask-then-sample):

```
[Schema/Grammar/Regex] --compile--> [FSM / PDA / Trie index]  (offline)
                                          |
 prefix tokens --> [LLM forward] --> logits[V]
                                          |      state s_t
                                          v        |
                                [Mask builder: A(s_t)] --> mask[V]
                                          |
                         logits + mask(-inf) --> [Sampler] --> token_t
                                          |
                                 [State update s_{t+1}]
```

Standard equations. The masked softmax over the legal set A(s_t) is:

$$p_i = \frac{\exp(l_i)}{\sum_{j} \exp(l_j)}, \quad l_i \leftarrow -\infty \;\; \text{for } i \notin A(s_t)$$

Since exp(−∞) = 0, the denominator sums only over legal tokens, so the distribution is the model's own distribution renormalized to A(s_t).

The search objective for beam-based variants (from the NMT constrained decoding literature) is:

$$\hat{y}=\operatorname{argmax}_{y\in\mathcal{Y}}\, p_{\theta}(y\mid x)$$

where the output space is restricted to sequences that satisfy the constraints.

Tensor and data-flow table:

| Artifact | Shape / form | Produced by | Consumed by |
|---|---|---|---|
| logits | [V] per sequence, [k x V] per beam step | model forward | mask application |
| legal set A(s_t) | subset of V | state tracker lookup | mask builder |
| mask | [V] boolean or additive −∞ | mask builder | sampler |
| state s_t | FSM/PDA/trie node | transition on sampled token | next step |

Complexity of lexically constrained beam search (N = length, k = beam, C = constraints):

| Method | Complexity |
|---|---|
| Constrained beam search (Anderson et al., 2017) | O(Nk2^C) |
| Grid beam search (Hokamp and Liu, 2017) | O(NkC) |
| Dynamic beam allocation (Post and Vilar) | O(Nk) |

## Code or Pseudocode
```python
# Pseudocode: minimal loop that inserts legal-token masking before the sampler (trie-based label constraint)
from typing import Sequence
import math, random

NEG_INF = float("-inf")

def build_trie(label_token_seqs: Sequence[Sequence[int]], eos: int) -> dict:
    root: dict = {}
    for seq in label_token_seqs:
        node = root
        for tok in seq:
            node = node.setdefault(tok, {})
        node[eos] = {}            # EOS is allowed only after a complete label
    return root

def sample(logits: list[float]) -> int:
    m = max(x for x in logits if x != NEG_INF)
    w = [0.0 if x == NEG_INF else math.exp(x - m) for x in logits]
    return random.choices(range(len(w)), weights=w)[0]

def constrained_decode(model, prompt_ids: list[int], trie: dict,
                       eos: int, max_len: int = 32) -> list[int]:
    node, out = trie, []
    for _ in range(max_len):
        logits = model.next_logits(prompt_ids + out)  # model proposal: scores over the full vocabulary
        allowed = node.keys()                          # legal set A(s) from the constraint state
        if not allowed:                                # failure path 1: dead-end state
            raise RuntimeError("dead-end: no legal tokens (constraint compile error)")
        masked = [l if i in allowed else NEG_INF for i, l in enumerate(logits)]
        tok = sample(masked)                           # sampling happens only among legal tokens
        if tok == eos:
            return out
        out.append(tok)
        node = node[tok]                               # state transition
    raise TimeoutError("max_len exceeded: EOS was never selected")  # failure path 2

# Host boundary: structure is guaranteed, but meaning and permissions are validated separately by the host.
# label = tokenizer.decode(constrained_decode(...))
# assert label in ALLOWED_LABELS and user_may_use(label)
```

## Production Pitfalls
- ❌ Mistake: Treating schema-valid output as correct and executing tool calls straight from it → ✅ Fix: Validate arguments, permissions, and side effects in host code before execution, since the mask guarantees structure only, not meaning or authorization.
- ❌ Mistake: Assuming every framework supports the full JSON Schema feature set because the docs say 'JSON Schema supported' → ✅ Fix: Run your real schemas and the official JSON Schema Test Suite against each engine, because measured coverage differed up to 2x between frameworks.
- ❌ Mistake: Compiling a constraint that leaves a state with no legal continuation, so the decoder stalls or errors mid-generation → ✅ Fix: Test the compiled automaton with dead-end detection, as in the trie loop that raises on an empty legal set, and make EOS reachable only from accepting states.
- ❌ Mistake: Shipping a complex grammar without measuring per-step overhead and assuming constrained decoding is always faster → ✅ Fix: Benchmark latency per schema and framework, since constraint-state processing and masking run at every step and the speedups reported are framework- and schema-dependent.

## Tradeoffs — When to Use What
Suitable:

- Machine-consumed output such as tool arguments, JSON records, or SQL, where a single parse error breaks the downstream consumer. Enforcing structure at sampling time removes the retry and repair path that post-hoc validation requires.
- Closed label sets or tool registries (taxonomy labels, action names). A trie over the allowed token sequences makes invented labels unreachable, and the mask is cheap to compute when the set is small.
- Local or self-hosted inference where you control the sampler. Engines such as Guidance, Outlines, XGrammar, and the llama.cpp grammar module can insert the mask directly, and you can profile them against your own schemas.
- Pipelines where retry cost dominates. Constraining at generation avoids repeated full generations, and the JSONSchemaBench paper reports speedups of up to 50% over unconstrained decoding.

Unsuitable:

- Cases where the risk is semantic, not structural (wrong values, unauthorized actions). The mask cannot encode business meaning, so use host-side validation, permission checks, and evaluation sets instead.
- Schemas that use JSON Schema features a given engine does not support. Coverage varies widely across frameworks (best supports twice as many real-world schemas as the worst), so check coverage with the official JSON Schema Test Suite or fall back to post-hoc validation with retry.
- Free-form prose or open-ended reasoning with no machine consumer. A mask adds per-step state processing for no benefit; prompt-only generation is enough.
- Hosted models where you cannot access logits. You depend on the provider's schema support, so use the provider's structured-output API or function calling, and validate the result on your side.

## Industry Communication
- "In the **structured-output rollout**, parse failures dropped to zero, but we still saw wrong values; schema validity is a **structural guarantee**, so we're adding host-side argument checks before tool execution."
- "PR feedback: the **trie index** for the label set has no EOS edge after a prefix label, which creates a **dead-end state**; please add an accepting-state test before merge."
- "Design doc, section 4: we compare **Guidance, Outlines, XGrammar, and llama.cpp grammars** on our production schemas, measuring **schema coverage** and **per-step masking latency**, not just the vendor's headline numbers."
- "During the incident review, the root cause was an **unsupported JSON Schema keyword** silently ignored by the grammar engine; we will gate deploys on the **JSON Schema Test Suite** results."
- "The **mask builder** sits between the forward pass and the sampler, so the sampler contract is unchanged; the **model proposes, the constraint engine filters, the host validates**."
- "For the **beam-search path**, we need to confirm the mask is applied per beam, because applying it once per batch would let invalid hypotheses survive into the next step."
- "Postmortem action item: stop treating **function calling** and **constrained decoding** as interchangeable; the first is an interface contract, the second changes the **sampling distribution** itself."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Decoding strategies** — (greedy, temperature, top-p) — The mask is inserted before the sampler, so you must understand how logits become probabilities and how each strategy picks a token to see why −∞ makes illegal tokens unreachable.
- (prerequisite) **JSON Schema** — The de facto constraint specification language for structured output; knowing which features it expresses determines what a grammar engine must compile and where coverage gaps appear.
- (prerequisite) **Beam search** — Lexically constrained decoding originated as a modification to beam search (grid beam search, dynamic beam allocation), so beam banks and k x |V| score matrices are the base for constrained beam variants.
- (alternative) **Function calling** — Has the model select a predefined operation or payload shape that the application validates and executes; it relies on an external interface contract rather than token-level masking, and suits tool selection.
- (alternative) **Post-hoc validation and retry** — Checks the finished output against a schema and regenerates on failure; simpler to integrate on hosted models but costs repeated generations and cannot make invalid output unreachable.
- (extension) **Dynamic beam allocation** — Extends constrained decoding to lexical constraints in beam search with cost O(Nk) in sequence length and beam size, independent of the number of constraints, by dividing a fixed beam across constraint-count banks.

## body_advanced_ko

## 기술적 정의와 동작 원리
제약 디코딩은 자기회귀 생성의 각 시점 t에서, 지금까지의 prefix가 속한 제약 상태(grammar·regex·JSON Schema에서 컴파일된 파서/오토마타 상태)를 조회해 "이 토큰을 붙여도 유효한 완성이 여전히 가능한가"를 판정하고, 불가능한 토큰의 logit을 −∞로 바꾼 뒤 기존 샘플링(greedy, temperature, top-p)을 그대로 적용하는 추론 시점 기법이다. 모델 가중치와 학습은 바뀌지 않고, 변하는 것은 logit과 샘플러 사이에 끼는 마스킹 단계뿐이다. 논문에서는 제약 디코딩 프레임워크를 grammar engine이라고도 부르며, Guidance, Outlines, XGrammar, llama.cpp의 grammar 모듈이 이 범주에 속한다.

데이터/제어 흐름은 다음과 같다.

- **컴파일 단계** (오프라인): 스키마·문법·정규식을 FSM이나 파서 같은 제약 표현으로 변환한다. 허용 시퀀스 집합이 고정된 경우에는 trie를 만들 수 있다. STATIC은 trie의 앞쪽 깊은 층을 dense 테이블로, 희소한 꼬리를 CSR 행렬로 표현하는 하이브리드 인덱스를 오프라인에 구성한다.
- **디코딩 단계** (온라인): 모델이 어휘 전체(대략 32K~128K)에 logit을 내면, 엔진이 현재 상태에서 합법적인 다음 토큰 집합을 계산해 마스크를 만든다.
- **상태 전이**: 샘플링된 토큰으로 제약 상태를 갱신하고, 종료 토큰이 허용되는 상태에서만 EOS를 통과시킨다.

핵심 단계는 다음과 같다.

1. 제약을 상태 기계로 컴파일한다.
2. 매 스텝 모델 forward로 logit을 얻는다.
3. 현재 상태에서 합법 토큰 마스크를 구한다.
4. 불법 토큰의 logit을 −∞로 치환한다. softmax 하에서 확률이 정확히 0이 된다.
5. 남은 분포에서 샘플링하고 상태를 전이시킨다.

비용은 모델 forward에 더해 매 스텝 마스크 계산이 붙는다. 어휘 크기와 제약 복잡도가 커질수록 이 부분이 커진다. 어휘 제약 번역 계열의 선행 연구에서는 제약 개수 C에 대한 복잡도가 grid beam search O(NkC), constrained beam search O(Nk2^C)였고, dynamic beam allocation은 이를 O(Nk)로 줄였다(N은 문장 길이, k는 빔 크기). STATIC은 제약 개수 전체에 대해 마스킹 비용이 독립적이고 분기 계수 K에 대해 O(log K)라고 주장한다.

## 핵심 수식·아키텍처·도표
토큰 마스킹의 표준 정의는 다음과 같다. 상태 s에서 합법 토큰 집합을 A(s)라 하면 마스크된 logit은 다음과 같다.

$$\tilde{l}_i = \begin{cases} l_i & i \in A(s) \\ -\infty & i \notin A(s) \end{cases}$$

$$p_i = \frac{\exp(\tilde{l}_i)}{\sum_{j} \exp(\tilde{l}_j)}$$

−∞ logit은 exp(−∞)=0이므로 불법 토큰의 확률이 정확히 0이 되고, 남은 토큰들은 분모가 줄어든 만큼 재정규화된다. 모델이 원래 매긴 합법 토큰 간 상대 비율은 유지된다.

아키텍처와 데이터 흐름은 다음과 같다.

```
[Schema/Grammar/Regex] --compile--> [FSM / PDA / Trie index]  (오프라인)
                                          |
 prefix tokens --> [LLM forward] --> logits[V]
                                          |      state s_t
                                          v        |
                                [Mask builder: A(s_t)] --> mask[V]
                                          |
                         logits + mask(−∞) --> [Sampler] --> token_t
                                          |
                                 [State update s_{t+1}]
```

책임 경계는 다음과 같다.

- **모델**: 합법 토큰 중 무엇을 고를지에 대한 확률을 낸다. 내용 생성을 담당한다.
- **제약 엔진**: 구문적 유효성(괄호, 따옴표, 필드 위치, 문법 전이)만 책임진다.
- **호스트/애플리케이션**: 사실성, 도구 권한, 스키마의 의미, 부수효과 검증을 책임진다.

제약 표현별 마스크 조회 특성은 다음과 같다.

| 제약 표현 | 적합한 대상 | 마스크 조회 방식 |
|---|---|---|
| Trie | 고정된 허용 시퀀스 집합(라벨, 도구 이름, 아이템 ID) | prefix 노드의 자식 토큰 |
| FSM | 정규식, 평탄한 스키마 | 현재 상태의 전이 가능 토큰 |
| 문법 파서 | 재귀 구조(JSON, SQL) | 파서 상태에서 가능한 다음 터미널 |
| 하이브리드 dense+CSR | 매우 큰 허용 집합, 가속기 배치 디코딩 | 앞 층은 O(1) dense 조회, 이후는 CSR 읽기 |

## 코드 또는 의사코드
```python
# 의사코드: 합법 토큰 마스킹을 샘플러 앞에 끼우는 최소 루프 (trie 기반 라벨 제약)
from typing import Sequence
import math, random

NEG_INF = float("-inf")

def build_trie(label_token_seqs: Sequence[Sequence[int]], eos: int) -> dict:
    root: dict = {}
    for seq in label_token_seqs:
        node = root
        for tok in seq:
            node = node.setdefault(tok, {})
        node[eos] = {}            # 완결된 라벨 뒤에서만 EOS 허용
    return root

def sample(logits: list[float]) -> int:
    m = max(x for x in logits if x != NEG_INF)
    w = [0.0 if x == NEG_INF else math.exp(x - m) for x in logits]
    return random.choices(range(len(w)), weights=w)[0]

def constrained_decode(model, prompt_ids: list[int], trie: dict,
                       eos: int, max_len: int = 32) -> list[int]:
    node, out = trie, []
    for _ in range(max_len):
        logits = model.next_logits(prompt_ids + out)  # 모델 제안: 전체 어휘 점수
        allowed = node.keys()                          # 제약 상태의 합법 집합 A(s)
        if not allowed:                                # 실패 경로 1: 막다른 상태
            raise RuntimeError("dead-end: 합법 토큰 없음 (제약 컴파일 오류)")
        masked = [l if i in allowed else NEG_INF for i, l in enumerate(logits)]
        tok = sample(masked)                           # 샘플링은 합법 토큰 안에서만
        if tok == eos:
            return out
        out.append(tok)
        node = node[tok]                               # 상태 전이
    raise TimeoutError("max_len 초과: 종료 토큰이 한 번도 선택되지 않음")  # 실패 경로 2

# 호스트 경계: 구조는 보장되지만 의미와 권한은 호스트가 따로 검증한다.
# label = tokenizer.decode(constrained_decode(...))
# assert label in ALLOWED_LABELS and user_may_use(label)
```

## 프로덕션 함정
- ❌ 실수: 스키마 준수를 '출력이 맞다'로 취급해 검증 없이 도구를 실행한다 → ✅ 해결: 구조는 보장되지만 값의 사실성과 권한은 아니므로, 실행 전에 호스트 쪽에서 인자 범위·권한·부수효과를 별도로 검증하고 감사 로그를 남긴다.
- ❌ 실수: 프레임워크의 JSON Schema 지원 범위를 확인하지 않고 운영 스키마를 그대로 넘긴다 → ✅ 해결: JSONSchemaBench나 공식 JSON Schema Test Suite 같은 케이스로 사용하는 엔진의 커버리지를 먼저 측정하고, 미지원 키워드는 스키마 단순화나 엔진 교체로 대응한다.
- ❌ 실수: 제약 컴파일 결과에 막다른 상태가 있는데 max_len이나 종료 조건을 점검하지 않는다 → ✅ 해결: 합법 토큰 집합이 비는 상태와 EOS가 영영 허용되지 않는 상태를 컴파일 단계 테스트로 잡고, 런타임에는 길이 상한과 명시적 예외 경로를 둔다.
- ❌ 실수: 복잡한 문법에서 마스킹 오버헤드를 측정하지 않고 지연 예산을 잡는다 → ✅ 해결: 스텝당 마스크 계산 시간과 어휘 크기, 제약 복잡도별 p50/p99 지연을 모델 forward와 분리해 계측하고, 허용 집합이 고정이면 사전 구축 인덱스로 옮긴다.

## 트레이드오프와 언제 무엇을 쓰나
이럴 때 적합:

- 출력을 다른 프로그램(API, 컨트롤러)이 파싱하는 경우: 파싱 실패와 재시도 루프를 생성 단계에서 제거해 재시도에 드는 추가 호출 비용을 없앤다.
- 도구 이름이나 분류 라벨처럼 허용 집합이 닫혀 있는 경우: trie 기반 마스킹으로 존재하지 않는 이름이 생성될 수 없고, 마스크 조회 비용이 허용 집합 크기와 거의 무관하게 유지된다.
- 로컬 모델을 서빙하며 출력 형식을 고정해야 하는 경우: llama.cpp grammar나 Outlines 같은 grammar engine을 붙이면 모델 교체 없이 구조를 강제할 수 있다.
- 스키마가 JSON Schema로 표현되고 프레임워크 지원이 확인된 경우: JSONSchemaBench 논문은 제약 디코딩이 비제약 대비 속도를 최대 50% 높이고 다운스트림 성능을 최대 4% 개선한 사례를 보고했다.

이럴 때 부적합:

- 스키마의 값이 사실이어야 하는 경우: 구조 유효성과 사실성은 별개이므로 RAG나 사후 검증(규칙 기반 검사, 외부 데이터 대조)이 필요하다.
- 복잡하거나 드문 JSON Schema 기능이 많은 경우: 프레임워크마다 지원 범위가 크게 달라(최고가 최저의 두 배 스키마 지원) 미지원 기능은 별도 후처리나 다른 엔진으로 대체해야 한다.
- 도구 선택 자체의 권한과 부수효과가 핵심인 경우: 권한·감사는 호스트 책임이므로 함수 호출 인터페이스와 서버 측 인자 검증을 병행해야 한다.
- 제약 상태 처리와 마스킹의 스텝당 오버헤드가 지연 예산을 넘는 경우: 매우 큰 어휘와 복잡한 문법에서는 프롬프트 + 사후 검증·재시도가 더 단순하고 예측 가능할 수 있다.

## 업계 대화 맥락
- "이번 PR에서 **grammar engine**을 **llama.cpp grammar**에서 다른 엔진으로 바꾸면 **JSON Schema 커버리지**가 달라질 수 있어서, 운영 스키마 샘플로 **지원 여부 회귀 테스트**를 추가했습니다."
- "**파싱 실패율**은 제약 적용 후 0이 됐지만, **값 검증 실패**는 그대로입니다. 구조 보장과 의미 보장을 분리해서 **validator 레이어**를 유지하겠습니다."
- "**스텝당 마스킹 비용**을 forward와 분리해 계측했더니, **중첩 스키마**에서만 **p99**가 튀었습니다. **상태 캐시** 가능성을 다음 스프린트에 검토합니다."
- "에이전트의 **tool registry**에 없는 액션명이 나오던 건 **trie 기반 마스킹**으로 막았고, 권한 체크는 **host 쪽 허용 목록**에서 계속 수행합니다."
- "**design doc** 결론: 함수 호출은 인터페이스 계약, **constrained decoding**은 생성 시점 토큰 제한으로 레이어가 달라서 둘을 대체가 아니라 조합으로 설계합니다."
- "**postmortem**: 스키마 변경 후 **dead-end 상태**로 **max_len**까지 생성되는 요청이 있었고, **컴파일 단계 검증**과 **종료 가능성 테스트**를 배포 게이트에 넣었습니다."
- "**샘플링 설정**은 그대로 두고 **logit 마스킹**만 앞단에 추가했기 때문에 **temperature·top-p** 동작은 합법 토큰 안에서만 유효합니다."

## 선행·대안·확장 개념
- (선행) **디코딩 전략** — (Greedy·Temperature·Top-p) — 제약 디코딩은 logit과 샘플러 사이에 마스크를 끼우는 방식이므로, 기존 샘플링이 −∞ logit을 어떻게 처리하는지 알아야 개입 지점을 정확히 이해할 수 있다.
- (선행) **JSON Schema** — 프레임워크들이 표준화한 제약 명세 언어로, 어떤 키워드가 엔진에서 지원되는지가 커버리지 차이의 원천이 된다.
- (대안) **함수 호출** — (Function Calling) — 모델이 사전 정의된 작업을 고르고 앱이 검증·실행하는 외부 인터페이스 계약 방식으로, 생성 시점 토큰 제한이 아니라는 점에서 같은 기계 가독 출력을 다른 층위에서 푼다.
- (대안) **생성 후 검증·재시도** — 완성된 출력을 파싱·검증해 실패 시 재생성하는 방식으로 구현이 단순하지만 재시도 비용과 지연이 불확실하다.
- (확장) **Grid Beam Search / Dynamic Beam Allocation** — 번역에서 지정한 단어·구가 출력에 반드시 포함되게 하는 빔 서치 확장으로, 동적 빔 할당은 제약 개수에 대해 O(Nk)로 비용을 줄였다.
- (확장) **STATIC** — (Sparse Transition-Accelerated Trie Index) — 허용 시퀀스 집합이 매우 큰 생성형 검색에서 trie를 dense+CSR 하이브리드 인덱스로 벡터화해 가속기에서 마스킹 비용을 제약 개수와 독립적으로 만든 구현이다.

## references_en

- {"title": "Fast Lexically Constrained Decoding with Dynamic Beam Allocation for Neural Machine Translation", "authors": "Matt Post, David Vilar", "year": 2018, "venue": "arXiv", "type": "paper", "url": "https://arxiv.org/pdf/1804.06609", "tier": "primary", "annotation": "Shows how beam search can force required words into the output at a cost independent of the number of constraints."}
- {"title": "youtube/static-constraint-decoding", "type": "code", "url": "https://github.com/youtube/static-constraint-decoding/", "tier": "primary", "annotation": "Reference code for trie-based constrained decoding on GPUs/TPUs; archived demo, not for production."}
- {"title": "Generating Structured Outputs from Language Models: Benchmark and Studies", "authors": "Geng et al.", "year": 2025, "venue": "arXiv", "type": "paper", "url": "https://arxiv.org/html/2501.10868v1", "tier": "primary", "annotation": "Benchmark of six constrained decoding frameworks on 10K real-world JSON schemas: efficiency, coverage, quality."}
- {"title": "Constrained decoding: forcing LLM output to a grammar", "authors": "Alexander Rocha", "type": "blog", "url": "https://zeroentropy.dev/concepts/constrained-decoding", "tier": "secondary", "annotation": "Clear explainer of per-step logit masking and why it beats prompt-only structured output."}
- {"title": "Structured Output Constrained Decoding Explained", "type": "blog", "url": "https://shop.zimaspace.com/blogs/tech-ai-hub/structured-output-constrained-decoding-local-ai", "tier": "secondary", "annotation": "Explains the token mask and the limits: facts, authorization, and schema meaning remain separate."}
