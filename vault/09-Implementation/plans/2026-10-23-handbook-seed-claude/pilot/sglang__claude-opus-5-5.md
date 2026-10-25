# SGLang — claude-opus-5-5

- advanced 51 / basic 55 / gate blocked / penalty 7 / $4.6042 / 1178s

## definition_en

SGLang (Structured Generation Language) is an open-source LLM serving runtime paired with a Python-embedded frontend language, which reuses KV cache across requests that share a prompt prefix through RadixAttention and a cache-aware scheduler, cutting redundant computation in multi-step generation workloads such as agents and few-shot prompting. It is deployed as an OpenAI-compatible inference backend and is most often evaluated against vLLM and TensorRT-LLM.

## definition_ko

SGLang(Structured Generation Language)은 대규모 언어 모델(LLM)용 오픈소스 서빙 런타임이자 Python 내장 프론트엔드 언어로, RadixAttention으로 공통 프롬프트 앞부분의 KV 캐시를 요청 간에 재사용하고 캐시 적중률을 높이도록 요청 순서를 조정해, 에이전트·few-shot처럼 여러 단계로 이어지는 생성 작업의 중복 연산을 줄인다.

## summary_en

SGLang is free, open-source software for running large language models on your own GPUs and serving their answers to apps. Before a model can reply, it has to read the whole prompt. Many apps send prompts that start with the same long text, such as instructions, examples, or earlier chat turns. SGLang keeps the model's notes on that shared opening and reuses them, so it only reads the new part of each request. Picture a tutor who keeps notes on the textbook chapters that every student brings and reads only each student's new homework. This saves GPU time and makes replies start sooner for chatbots, agents, and batch jobs. The savings disappear if the prompt openings differ.

## summary_ko

SGLang은 이미 학습된 AI 언어 모델을 실제 서비스에서 더 빠르고 저렴하게 돌려주는 오픈소스 엔진이다. 같은 안내문으로 시작하는 질문이 계속 들어오면 매번 처음부터 다시 읽지 않는다. 이미 읽은 부분에 책갈피를 꽂아 두고 그 뒤부터 이어 읽는 식으로 일한다. 앞부분이 비슷한 요청끼리 순서도 맞춰 처리하기 때문에 비싼 GPU가 같은 계산을 반복하는 일이 줄어든다. 그래서 여러 번 대화를 주고받는 AI 에이전트나 대량 처리 작업에서 같은 장비로 더 많은 요청을 감당할 수 있다.

## body_basic_en

## Plain Explanation
SGLang is an open-source **serving runtime** for large language models. A serving runtime is the software that loads a model onto GPUs and answers requests from apps. SGLang also includes a small Python-based **frontend language** for writing multi-step generation programs. Before a model writes a single word, it has to read the entire prompt. This reading step is called **prefill**, and during it the model builds a **KV cache**, which is a set of internal notes (keys and values) for every token it has read. In agents, few-shot prompting, and multi-turn chat, many requests begin with the same long text. In a serving setup without effective prefix caching, that shared opening can be re-read on every request. The GPU then spends time on work it has already done, and users wait longer for the first word of the reply.

Think of a tutor who helps many students who all bring the same textbook. The first time, the tutor reads chapters 1 to 5 carefully and takes notes. When the next student brings the same chapters plus new homework, the tutor flips to the saved notes and reads only the new pages. SGLang applies this idea to prompts through a feature called **RadixAttention**. Its official description says this feature manages the KV cache so that redundant computation across program branches is eliminated.

Under the hood, SGLang stores cached keys and values in a tree that is organized by **token prefix**, meaning the exact sequence of tokens at the start of a prompt. When a new request arrives, SGLang walks the tree to find the longest matching prefix that is still held in GPU memory. The new request skips prefill for those matched tokens. The tokens after the match, such as a new user question, still have to be computed normally, and so does every token the model generates in its answer. The match must be token-for-token from the very beginning, so changing one early word breaks reuse for everything after it. Cached entries also live in a limited memory pool and can be pushed out when that pool fills up. To raise the hit rate, SGLang offers an optional scheduling policy called **lpm** (longest prefix match). It reorders waiting requests so that requests sharing a prefix run close together, but it adds some scheduling overhead.

## Examples & Analogies
- **An agent's second step reusing its first**: On step 1, an agent sends a long system prompt, a tool list, and the user's task. SGLang prefills all of it and keeps that token prefix in its cache. On step 2, the agent sends the exact same text plus the tool's result and a new instruction. Because the cached prefix is still in GPU memory, only the newly added suffix needs prefill. If a developer inserts a changing timestamp at the top of the system prompt, the match breaks at the first token and step 2 has to prefill everything again.
- **An overnight few-shot labeling batch**: A team labels 50,000 support tickets. Every ticket uses the same instruction followed by eight worked examples, and only the ticket text at the end changes. With the `lpm` scheduling policy, SGLang groups requests that share this prefix so the cached examples are reused instead of re-read for each ticket. If the queue mixes in many unrelated prompts and the KV cache pool runs full, the shared prefix can be pushed out of memory, and reuse drops until it is rebuilt.
- **Many customer-specific adapters on one server**: A platform serves one base model and gives each customer a small add-on set of tuned weights called a **LoRA adapter**. SGLang's documentation describes launching the server with LoRA support enabled and routing each request through a pre-loaded adapter by name. The team runs one shared deployment instead of a separate GPU server for each customer's fine-tuned variant.

## At a Glance
| | SGLang (radix cache on) | SGLang (`--disable-radix-cache`) | vLLM |
|---|---|---|---|
| Shared-prefix reuse | Matching resident prefix skips prefill | Every request prefills its full prompt | Prefix caching also available |
| Reuse controls | Optional `lpm` policy reorders requests for cache hits, with extra scheduling overhead | Not applicable | Optional per-request salts limit reuse to requests with the same salt |
| Best-fit workload | Agents, few-shot, multi-turn chat with long shared openings | Raw-speed tests on random prompts, as in SGLang's v0.2 benchmark setup | General OpenAI-compatible serving; similar prefix-heavy cases |
| Extra layer | Python-embedded frontend language for multi-step programs | Same runtime, cache reuse switched off | Serving engine with an OpenAI-compatible API server |

SGLang's prefix reuse pays off only when your traffic actually repeats long prompt openings, so compare it with vLLM on your own prompts rather than on random-text benchmarks where the cache is either off or irrelevant.

## Where and Why It Matters
- **NVIDIA's monthly SGLang container**: NVIDIA ships SGLang as a packaged container with its own release notes, such as release 26.07 dated August 2026. Teams can adopt a vendor-tested build instead of assembling GPU libraries by hand.
- **Joining the PyTorch ecosystem**: The SGLang team announced that the project officially joined the PyTorch ecosystem. This places SGLang alongside other community-recognized tools that infrastructure teams already evaluate.
- **Benchmarks now require a "contract"**: One published SGLang vs vLLM comparison paired SGLang v0.2.3 with vLLM 0.11.0, releases roughly two years apart. Engineers now pin versions, flags, hardware, and workload before trusting any throughput gap. SGLang's own v0.2 benchmark scripts turned the radix cache off for exactly this reason.
- **Hardware planning tied to GPU generation**: For serving GLM-5, SGLang's newer attention kernels are limited to sm_90 and sm_100 GPUs (H100, H200, B200 class), and its cookbook does not list the A100. Teams with older A100 fleets have to plan comparisons and deployments around this limit.
- **GPU memory budgeting as routine ops work**: SGLang's tuning guide splits GPU memory between model weights, the KV cache pool, and working buffers. It advises keeping roughly 5–8 GB free for working memory and aiming for KV cache usage above 0.9. Operators tune these settings directly, trading the risk of out-of-memory crashes against the number of requests the server can handle at once.

## Common Misconceptions
- ❌ Myth: SGLang makes every request faster by caching everything. → ✅ Reality: Reuse only happens when a new request starts with exactly the same tokens as a prefix still held in memory. New tokens and every generated output token are still computed, and prompts with random or reordered openings get little or no benefit.
- ❌ Myth: A published benchmark proves SGLang is faster (or slower) than vLLM. → ✅ Reality: Results depend on engine versions, flags, hardware, and how much your prompts overlap. The two engines have traded the lead across releases, so test with your own traffic before switching.
- ❌ Myth: SGLang is only a programming language for writing prompts. → ✅ Reality: It is both a Python-embedded frontend language and a full serving runtime. Many teams use only the runtime, as a drop-in OpenAI-compatible backend.

## How It Sounds in Conversation
- "Our support bot sends the same 3k-token system prompt on every turn, so turning on the **radix cache** in **SGLang** should cut **time to first token** from turn two onward."
- "Heads up: someone added a timestamp at the very top of the system prompt last sprint, and our **prefix cache hit rate** basically dropped to zero."
- "Before anyone posts **SGLang vs vLLM** numbers in #infra, pin both versions and launch flags; the last comparison mixed releases from different years."
- "Logs show **token usage** stuck around 0.7 with a deep queue, so let's lower **schedule-conservativeness** before we ask finance for more GPUs."
- "The GLM-5 kernels are gated to **sm_90**, so the A100 pool can't run this config; I'm requesting H100 time for Thursday's eval."

## Related Reading
- (before) **KV Cache** — SGLang's main advantage is reusing these per-token notes, so understanding what they store and why they eat GPU memory comes first.
- (before) **Prefill and Decode** — Knowing why reading the prompt and writing the answer are separate phases explains why prefix reuse speeds up the first token but not later output.
- (similar) **vLLM** — The most common alternative serving engine; it also offers prefix caching, so the choice comes down to version, workload shape, and operating tooling.
- (similar) **TensorRT-LLM** — NVIDIA's serving stack, often included in the same three-way benchmarks; compare it on deployment effort as well as throughput.
- (next) **Prefill-Decode Disaggregation** — SGLang can run prefill and decode on separate workers; read this next to see how large deployments scale past a single server.
- (next) **Structured Output** — The "structured generation" in SGLang's name; learn how forcing outputs into formats like JSON fits multi-step agent programs.

## body_basic_ko

## 쉽게 이해하기
LLM이 답을 만들 때는 두 단계를 거칩니다. 먼저 입력 전체를 한 번에 읽어 계산하는 **프리필** (prefill) 단계가 있고, 그다음 글자를 한 토큰씩 이어 쓰는 **디코드** (decode) 단계가 이어집니다. 실제 서비스에서는 수많은 요청이 같은 시스템 프롬프트나 같은 예시 묶음으로 시작합니다. 그런데 이 공통 부분을 요청마다 처음부터 다시 읽으면 GPU 시간과 메모리가 같은 계산에 반복해서 쓰입니다.

**SGLang**은 앞부분을 읽으며 만든 중간 계산 결과인 **KV 캐시**를 보관했다가, 같은 앞부분으로 시작하는 다음 요청에 다시 쓰는 방식으로 이 낭비를 줄입니다. 도서관 열람실을 떠올리면 쉽습니다. 앞사람이 같은 판본 책의 1~30쪽을 요약한 메모를 서가에 남겨 두면, 다음 사람은 31쪽부터 읽기 시작하면 됩니다. 여기에 더해 SGLang은 질문 → 계획 → 답변처럼 여러 단계로 이어지는 생성 작업을 Python 코드 하나로 쓸 수 있는 프론트엔드 언어도 함께 제공합니다.

재사용의 핵심 장치는 **RadixAttention**입니다. 지금까지 처리한 입력의 앞부분을 나무 모양 구조(radix tree)로 저장해 두고, 새 요청이 오면 처음부터 가장 길게 일치하는 토큰 구간을 찾아 그 부분의 프리필을 건너뜁니다. 단, 이 재사용은 같은 모델을 같은 실행 설정으로 띄운 서버 안에서만 일어납니다. 또 입력이 첫 토큰부터 정확히 일치해야 하고, 그 캐시가 메모리 부족 때문에 밀려나지 않고 남아 있어야 합니다. 스케줄러는 같은 앞부분을 가진 요청끼리 묶어 처리하는 정책(longest prefix match)으로 적중률을 높일 수 있습니다. 대신 요청 순서를 정하는 계산 부담이 조금 늘어납니다.

## 비유와 예시
- **공통 시스템 프롬프트를 쓰는 사내 상담봇**: 모든 요청이 같은 긴 안내문으로 시작하고 끝에 사용자 질문만 붙는다고 가정해 봅시다. 캐시가 적중한 요청은 새로 붙은 질문 부분만 프리필하면 되므로 첫 글자가 나오기까지의 시간(TTFT)이 짧아질 수 있습니다. 반대로 트래픽이 몰려 캐시가 밀려났거나 안내문 맨 앞에 날짜처럼 매번 바뀌는 값이 끼어 있으면, 처음부터 전부 다시 계산하게 되어 이 이점이 사라집니다.
- **few-shot 예시를 붙인 대량 문서 분류**: 수천 건의 문서마다 앞에 같은 예시 묶음을 붙여 분류하는 일괄 작업에서는 앞부분이 대부분 겹칩니다. 공식 튜닝 문서는 이렇게 공통 프리픽스가 많은 작업이라면 lpm 스케줄링을 시도해 보라고 안내합니다. 같은 앞부분을 가진 요청을 몰아 처리해 적중을 늘리는 대신, 스케줄링 부담이 다소 늘어나는 맞교환입니다.
- **여러 단계를 거치는 에이전트 프로그램**: 계획 → 도구 호출 결과 반영 → 최종 답변처럼, 단계마다 이전 대화를 다시 입력으로 넣는 구조라면 앞 단계까지의 입력이 다음 단계의 공통 앞부분이 됩니다. NVIDIA 릴리스 노트도 에이전트, chain-of-thought 추론, few-shot 프롬프팅을 SGLang의 대표 용도로 꼽습니다. 다만 실제 이득은 단계 사이에 캐시가 남아 있는지에 따라 달라집니다.

## 한눈에 비교
| | SGLang | vLLM |
|---|---|---|
| 프론트엔드 | Python 내장 생성 언어 + 서버 런타임 | OpenAI 호환 API 서버 중심 (자체 생성 언어는 참고 자료에서 확인 안 됨) |
| 프리픽스 캐싱 | 지원, radix tree로 요청 간 재사용 | 지원, 요청별 salt로 재사용 범위 제한 가능 |
| 스케줄링 조절 | lpm 정책으로 적중률 향상, 보수성 값(예: 0.3~1.3) 조정 | chunked prefill 크기로 TTFT·ITL 균형 조정 |
| 하드웨어 지원 | NVIDIA·AMD 사례 있음, 모델 쿡북별로 상이 | 모델·정밀도·버전별 공식 문서 확인 필요 |
| 확인 기준 시점 | SGLang 공식 문서, NVIDIA 26.07 릴리스 노트(2026년 8월) | vLLM 설계 문서를 인용한 2026년 비교 자료 |

두 엔진 모두 프리픽스 재사용을 하므로 실제 차이는 그 주변의 스케줄링과 설정에서 갈립니다. 따라서 어느 쪽이 빠른지는 같은 모델·하드웨어·입력 길이·동시성 조건에서 각 엔진의 대응 설정을 맞춰 직접 측정해야 판단할 수 있습니다.

## 어디서 왜 중요한가
- **NVIDIA SGLang 컨테이너의 월간 릴리스**: 확인 가능한 사실은 NVIDIA가 SGLang 컨테이너를 매월 공개하고, 2026년 8월 기준 26.07 릴리스 노트가 나와 있다는 점입니다. 운영상으로는 소스를 직접 빌드하지 않고 버전이 붙은 이미지를 고정해 배포하거나 되돌릴 수 있다는 뜻입니다. 대신 매월 갱신되므로 올리기 전에 릴리스 노트의 알려진 이슈를 확인하는 절차가 필요합니다.
- **캐시를 의식한 프롬프트 설계 관행**: 재사용은 첫 토큰부터 일치하는 구간에만 적용됩니다. 그래서 시스템 프롬프트와 예시는 요청 맨 앞에 고정하고, 날짜·사용자 ID처럼 바뀌는 값은 뒤쪽에 두는 설계가 적중률을 좌우합니다.
- **모델별 쿡북 단위의 하드웨어 확인**: GLM-5 서빙 사례에서는 H100·H200·B200·MI300급 GPU가 언급되고, 일부 전용 커널은 특정 GPU 세대로 제한된다는 지적이 있습니다. 이는 해당 모델·커널에 한정된 이야기입니다. 쿡북에 없는 GPU가 곧 실행 불가능하다는 뜻은 아니므로, 모델·정밀도·버전 조합별로 직접 검증하는 것이 맞습니다.
- **엔진 비교 시 측정 조건 고정**: 공식 bench_serving 도구는 첫 토큰 지연(TTFT), 출력 토큰당 시간(TPOT), 토큰 간 지연(ITL)을 측정하고, vLLM 같은 다른 백엔드도 같은 도구로 잴 수 있습니다. 공식 문서는 안정 구간을 재려면 요청 수를 최대 동시성의 5배 이상으로 잡으라고 권장합니다. 짧게 잰 한 번의 수치를 결론으로 쓰는 실수를 줄여 줍니다.
- **프리필·디코드 분리 운영** (PD 분리): 입력을 읽는 서버와 답을 이어 쓰는 서버를 따로 띄우고 라우터로 묶는 모드를 지원합니다. 두 단계에 GPU를 나눠 배정할 수 있다는 장점이 있습니다. 대신 성능 분석(프로파일링)도 두 쪽을 따로 해야 해서 운영 절차가 늘어납니다.

## 자주 하는 오해
- ❌ 오해: SGLang으로 바꾸기만 하면 프리필이 자동으로 빨라진다 → ✅ 실제: 캐시 재사용은 앞부분 토큰이 정확히 일치하고 그 캐시가 아직 메모리에 남아 있을 때만 효과가 있습니다. 요청마다 앞부분이 다르거나 트래픽이 많아 캐시가 자주 밀려나면, 캐시 미적중으로 매번 처음부터 계산하게 됩니다.
- ❌ 오해: KV 캐시용 메모리를 최대한 크게 잡을수록 좋다 → ✅ 실제: GPU 메모리에는 모델 가중치와 KV 캐시 외에도 중간 계산값과 CUDA graph 버퍼가 들어가야 합니다. 캐시 몫을 너무 키우면 메모리 부족(OOM) 오류가 나거나 서버가 진행 중인 요청을 되돌리는 일이 잦아집니다. 적정값은 고정된 숫자가 아니라 입력 길이, 동시 요청 수, 지연 목표, GPU 메모리 크기에 맞춰 조금씩 올려 가며 찾아야 합니다.
- ❌ 오해: 앞부분 일치 순으로 묶는 lpm 스케줄링은 켜 두면 손해가 없다 → ✅ 실제: lpm은 적중률을 높이는 대신 요청 순서를 정하는 계산 부담을 더합니다. 공통 앞부분이 적은 트래픽에서는 얻는 것보다 부담이 클 수 있으니, 켜기 전후를 같은 조건에서 비교해야 합니다.

## 대화에서는 이렇게
- "로그에 **#queue-req: 0**이 자주 찍히네요. 서버보다 요청 생성기가 병목일 수 있으니 클라이언트 쪽부터 확인할게요."
- "공통 시스템 프롬프트를 쓰는데 **캐시 적중**이 낮아요. 프롬프트 맨 앞에 타임스탬프가 들어가는지부터 볼게요."
- "**KV cache pool is full** 경고가 분당 여러 번 떠요. 메모리가 빠듯한 것 같으니 동시 요청 상한을 낮춰서 다시 재보죠."
- "MI300 쪽은 **모델·정밀도·SGLang 버전** 조합별로 지원 여부를 먼저 확인하고 일정 잡을게요."
- "vLLM이랑 비교할 때는 **워밍업** 구간을 빼고, 요청 수를 동시성의 5배 이상으로 잡아서 안정 구간만 비교합시다."

## 함께 읽으면 좋은 용어
- (기초) **KV 캐시** — SGLang이 재사용하는 대상 자체라서, 이것부터 알아야 '왜 다시 계산하지 않아도 되는지'가 이해됩니다.
- (기초) **Prefill** — 캐시 적중이 줄여 주는 구간이 바로 프리필이므로, 프리필과 디코드의 차이를 알면 TTFT가 줄어드는 이유가 보입니다.
- (유사) **vLLM** — 같은 층위의 오픈소스 서빙 엔진으로 프리픽스 캐싱도 지원합니다. 구체적인 기능·하드웨어 지원은 버전별 공식 문서로 확인해야 합니다.
- (유사) **TensorRT-LLM** — 같은 벤치마크 도구로 함께 비교되곤 하는 NVIDIA 쪽 추론 엔진입니다. 지원 모델과 GPU는 버전별 공식 문서를 기준으로 봐야 합니다.
- (심화) **RadixAttention** — SGLang을 써 본 뒤 '어떤 조건에서 캐시가 맞고 빠지는지'를 구조 수준에서 이해하고 싶을 때 이어서 읽기 좋습니다.
- (심화) **양자화** — FP8 같은 저정밀도 실행으로 메모리를 아끼는 다음 단계의 최적화입니다. 실제 속도 개선은 하드웨어와 커널 지원에 따라 달라집니다.

## body_advanced_en

## Technical Definition & How It Works
SGLang is an LLM serving system with two parts. The first is a Python-embedded frontend language for structured generation programs. The second is a backend runtime made of an HTTP/OpenAI-compatible server, a scheduler, a radix-tree-indexed KV cache pool (**RadixAttention**), and a **ModelRunner** that runs prefill (`extend()`) and `decode()` steps on the GPU. Two properties separate it from a stateless inference server. KV state is kept after a request finishes and indexed by token prefix. The scheduler's admission and ordering decisions are tied to that cache, so they can raise hit rate at the cost of more scheduling work.

**Request data/control flow** (server path)

1. **Ingress.** A request arrives through `sglang.launch_server` (HTTP) or through an in-process `Engine` (`engine.generate()`). Both paths end at the same scheduler.
2. **Prefix match.** The scheduler walks the radix tree with the request's token sequence. Matched tokens already have KV entries and skip prefill. Only the unmatched suffix is computed. Lookup cost grows with prompt length, not with the number of cached requests.
3. **Ordering.** The default policy schedules requests as they come. With `--schedule-policy lpm` (longest prefix match), the queue is reordered to raise cache hits. The docs warn this adds scheduling overhead, and that overhead also grows when `#queue-req` is very large. The documented healthy queue range is 100–2000.
4. **Admission against the KV pool.** New requests are admitted only if the pool can hold their projected growth, and `--schedule-conservativeness` scales that estimate.
   - If admission is too optimistic, the pool fills and the scheduler **retracts** running requests (`KV cache pool is full. Retract requests.`). About one retraction per minute is documented as acceptable.
   - If admission is too pessimistic, `token usage` stays below 0.9 while requests wait. This typically happens with large `max_new_tokens` and early EOS.
5. **Execution.** Prefill is split into chunks of `--chunked-prefill-size` tokens. Decode runs as a continuous batch capped at `--max-running-requests`. Decode batches under `--cuda-graph-max-bs-decode` replay a captured CUDA graph. By default CUDA graphs are enabled only for small batches (the docs cite fewer than 160 or 256). At large tensor-parallel sizes, raising the cap to 512–768 can help but costs extra memory.
6. **Retention.** Finished sequences leave their KV nodes in the tree for later prefix hits, until memory pressure forces eviction.

**Memory model.** GPU memory is split into four parts: model weights, KV cache pool, CUDA graph buffers, and activations. `--mem-fraction-static` covers only the first two. Every KV token you gain by raising it is memory taken from activations and graph buffers, which is the source of the OOM failures covered later.

**Parallelism.** The docs favor data parallelism for throughput when memory allows. They route DP through the SGLang Model Gateway (formerly Router) rather than the `dp_size` flag. Tensor, expert, and DP-attention parallelism (`--attn-dp-size` for DeepSeek models) are alternatives when one replica does not fit.

**Four execution paths, four different numbers.** SGLang's benchmark tooling enters the stack at different depths, and their outputs are not interchangeable:

- **HTTP path.** `bench_serving` and `bench_one_batch_server` send HTTP requests to a running server. They exercise the scheduler *indirectly*, so latencies include HTTP handling, queueing, and scheduling.
- **Offline throughput path.** `bench_offline_throughput` builds the `Engine` *in-process* without an HTTP server and submits all requests at once. The scheduler still batches and executes them, so scheduling cost is included, but network and HTTP overhead are not. The result is a ceiling, not an online SLO.
- **ModelRunner path.** `bench_one_batch` calls `ModelRunner.extend()` / `decode()` on a fixed static batch and bypasses the scheduler entirely. It is useful for kernel profiling. It may OOM at batch sizes a real server handles, because the server chunks prefill.

**Published numbers.** The reference set does not publish a standardized benchmark score for SGLang itself, so `benchmarks` is empty. Throughput depends on model, GPU, precision, and flags. The tuning guide's sample decode log (233 running requests, 370,959 KV tokens, token usage 0.82, 4,594.01 generated tok/s, 317 queued) is a diagnostic illustration with unstated hardware, not a benchmark.

## Formulas, Architecture, and Diagrams
**Memory model** (from the hyperparameter tuning guide)

$$M_{total} = M_{weights} + M_{KV} + M_{graph} + M_{act}$$

$$f_{static} = \frac{M_{weights} + M_{KV}}{M_{GPU}}$$

Solving for the KV pool gives the quantity you are actually tuning:

$$M_{KV} = f_{static} \cdot M_{GPU} - M_{weights}$$

- Each documented +0.01 step of `--mem-fraction-static` moves 0.01 × GPU capacity from activations and graph buffers into the KV pool. On an 80 GB A100 that is about 0.8 GB per step.
- The guide targets 5–8 GB of `available_gpu_mem` left at startup. 10–20 GB means the KV pool is undersized. Below 5 GB means OOM risk under load.
- Raising `--cuda-graph-max-bs-decode` grows the graph-buffer term, so it usually has to be paired with a lower `--mem-fraction-static`.

**Steady-state rule for online benchmarks**

$$N_{prompts} \ge 5 \cdot C_{max}$$

Here N is `--num-prompts` and C is `--max-concurrency`. Shorter runs are dominated by warm-up and tail effects.

**Execution-path matrix**

| Entry point | HTTP server | Scheduler | What the number means | Do not use it for |
|---|---|---|---|---|
| `bench_serving` | Yes | Indirect, via server | Online TTFT / TPOT / ITL plus throughput at a controlled rate or concurrency | Kernel attribution |
| `bench_one_batch_server` | Yes | Indirect, via server | One batch end-to-end, including HTTP and scheduler overhead; never steady state | Capacity planning, unless `--enable-multi-batch` is set and only `overall_throughput` is read |
| `bench_offline_throughput` | No | Direct, `Engine` in-process | Maximum throughput with scheduling but no network | Latency SLOs for an HTTP deployment |
| `bench_one_batch` | No | Bypassed (`ModelRunner`) | Kernel-level latency of a static prefill and decode | Anything involving dynamic batching; may OOM where a server would not |

**Runtime symptom → knob matrix**

| Symptom in decode / startup logs | Interpretation | Knob | Cost of turning it |
|---|---|---|---|
| `#queue-req: 0` most of the time | Client submits too slowly | Raise client concurrency | None server-side |
| `#queue-req` well above 2000 | Queue large enough to inflate scheduling overhead | Throttle the client | Higher client-side wait |
| `token usage` < 0.9 while `#queue-req` > 0 | Admission too conservative (large `max_new_tokens`, early EOS) | `--schedule-conservativeness` toward 0.3 | More retractions |
| Frequent `KV cache pool is full. Retract requests.` | Over-admission | `--schedule-conservativeness` toward 1.3 | Lower pool utilization |
| `available_gpu_mem` 10–20 GB at startup | KV pool undersized | Raise `--mem-fraction-static` in 0.01 steps | OOM risk |
| OOM during prefill | Prefill chunk too large | `--chunked-prefill-size` 4096 or 2048 | Slower prefill on long prompts |
| OOM during decode | Too many concurrent sequences | Lower `--max-running-requests` | Lower concurrency |
| High shared-prefix ratio | Cache hits left on the table | `--schedule-policy lpm` | Extra scheduling work per step |
| Small model, small batches | Python and launch overhead dominate | `--enable-torch-compile` | Compile time at startup |

## Code or Pseudocode
```python
from __future__ import annotations
from dataclasses import dataclass
from statistics import median

# Fixtures are pinned to the log format they were captured from. Re-capture on every
# SGLang upgrade: scheduler log lines are diagnostics, not a stable API.
FIXTURES: dict[str, str] = {
    'tuning-doc-2025-08': ('Decode batch. #running-req: 233, #token: 370959, token usage: 0.82, '
                           'cuda graph: True, gen throughput (token/s): 4594.01, #queue-req: 317'),
    'synthetic-reordered': ('Decode batch. #queue-req: 0, token usage: 0.55, new-field: x, '
                            '#running-req: 40, #token: 81000, gen throughput (token/s): 900.5'),
}
FIELDS: dict[str, tuple[str, type]] = {
    '#running-req': ('running_req', int), '#token': ('num_tokens', int),
    'token usage': ('token_usage', float), 'gen throughput (token/s)': ('gen_tok_s', float),
    '#queue-req': ('queue_req', int),
}

@dataclass(frozen=True)
class DecodeSample:
    running_req: int
    num_tokens: int      # tokens currently held in the KV pool
    token_usage: float   # KV pool utilization in [0, 1]
    gen_tok_s: float     # kept: throughput context travels with every piece of advice
    queue_req: int

def parse_decode_line(line: str) -> DecodeSample | None:
    '''None for non-decode lines; ValueError for decode lines that cannot be trusted.'''
    if 'Decode batch.' not in line:
        return None
    raw: dict[str, int | float] = {}
    for chunk in line.split('Decode batch.', 1)[1].split(','):
        key, sep, value = chunk.partition(':')
        if not sep or key.strip() not in FIELDS:
            continue  # tolerate unknown or newly added fields and any field order
        attr, cast = FIELDS[key.strip()]
        try:
            raw[attr] = cast(value.strip())  # explicit int/float conversion per field
        except ValueError as exc:
            raise ValueError(f'{key.strip()!r} is not {cast.__name__}: {value.strip()!r}') from exc
    missing = {attr for attr, _ in FIELDS.values()} - raw.keys()
    if missing:
        raise ValueError(f'decode line missing {sorted(missing)}')
    s = DecodeSample(**raw)  # type: ignore[arg-type]
    if not 0.0 <= s.token_usage <= 1.0:
        raise ValueError(f'token usage out of range: {s.token_usage}')
    if min(s.running_req, s.num_tokens, s.queue_req) < 0 or s.gen_tok_s < 0:
        raise ValueError('negative counter in decode line')
    return s

@dataclass(frozen=True)
class ServerConfig:  # read from the running server's args/startup log, never assumed
    mem_fraction_static: float
    schedule_conservativeness: float
    max_running_requests: int
    chunked_prefill_size: int
    available_gpu_mem_gb: float

    def __post_init__(self) -> None:
        if not 0.0 < self.mem_fraction_static < 1.0:
            raise ValueError('mem_fraction_static must be in (0, 1)')
        if self.max_running_requests <= 0 or self.chunked_prefill_size <= 0:
            raise ValueError('request and prefill limits must be positive')

@dataclass(frozen=True)
class Advice:
    knob: str
    current: float | None
    suggested: float | None
    support: float  # share of samples matching the rule: explicit uncertainty
    evidence: str

def advise(cfg: ServerConfig, samples: list[DecodeSample],
           retracts_per_min: float, min_samples: int = 30) -> list[Advice]:
    if len(samples) < min_samples:
        raise ValueError(f'{len(samples)} samples < {min_samples}: not a steady-state window')
    n = len(samples)
    ctx = (f'median {median(s.gen_tok_s for s in samples):.0f} tok/s, '
           f'{median(s.running_req for s in samples):.0f} running, '
           f'{median(s.num_tokens for s in samples):.0f} KV tokens')
    out: list[Advice] = []
    starved = sum(s.queue_req == 0 for s in samples) / n
    if starved > 0.5:  # server waits on the client; no server flag fixes this
        out.append(Advice('client submission rate', None, None, starved, f'#queue-req == 0; {ctx}'))
    if median(s.queue_req for s in samples) > 2000:
        out.append(Advice('client submission rate', None, None, 1.0,
                          f'queue > 2000 inflates scheduling overhead; {ctx}'))
    underfilled = sum(s.token_usage < 0.9 and s.queue_req > 0 for s in samples) / n
    saturated = sum(s.token_usage >= 0.9 for s in samples) / n
    if retracts_per_min > 1.0:  # about once per minute is documented as tolerable
        out.append(Advice('--schedule-conservativeness', cfg.schedule_conservativeness, 1.3,
                          saturated, f'{retracts_per_min:.1f} retractions/min; {ctx}'))
    elif underfilled > 0.5:
        out.append(Advice('--schedule-conservativeness', cfg.schedule_conservativeness, 0.3,
                          underfilled, f'usage < 0.9 while requests wait; {ctx}'))
    gb = cfg.available_gpu_mem_gb
    if gb > 8.0 or gb < 5.0:  # 5-8 GB activation headroom is the documented target
        step = 0.01 if gb > 8.0 else -0.01
        out.append(Advice('--mem-fraction-static', cfg.mem_fraction_static,
                          round(cfg.mem_fraction_static + step, 2), 0.5,
                          f'{gb:.1f} GB headroom from one startup reading; change one step, re-test for OOM'))
    return out

if __name__ == '__main__':
    for name, line in FIXTURES.items():
        assert parse_decode_line(line) is not None, name
    assert parse_decode_line('unrelated log line') is None
    malformed = [
        'Decode batch. #running-req: abc, #token: 1, token usage: 0.5, gen throughput (token/s): 1, #queue-req: 0',
        'Decode batch. #running-req: 1, #token: 1, token usage: 1.7, gen throughput (token/s): 1, #queue-req: 0',
        'Decode batch. #running-req: 1, token usage: 0.5',
    ]
    for bad in malformed:
        try:
            parse_decode_line(bad)
        except ValueError as err:
            print('rejected:', err)
        else:
            raise AssertionError(f'accepted malformed line: {bad}')
    sample = parse_decode_line(FIXTURES['tuning-doc-2025-08'])
    assert sample is not None
    cfg = ServerConfig(mem_fraction_static=0.85, schedule_conservativeness=1.0,  # illustrative values
                       max_running_requests=4096, chunked_prefill_size=8192, available_gpu_mem_gb=13.5)
    try:
        advise(cfg, [sample] * 5, retracts_per_min=0.2)
    except ValueError as err:
        print('refused:', err)
    for a in advise(cfg, [sample] * 40, retracts_per_min=0.2):  # replicated only for the demo
        print(a)
```

## Production Pitfalls
- ❌ Mistake: Publishing bench_offline_throughput results as the capacity of an HTTP deployment, even though SGLang's benchmark docs state it instantiates the Engine in-process with no HTTP server and submits all requests at once → ✅ Fix: Report it only as a throughput ceiling, and size online SLOs with bench_serving, which measures TTFT, TPOT and ITL against a running server with num-prompts at least 5 × max-concurrency.
- ❌ Mistake: Treating bench_one_batch_server output as steady-state performance, when the docs say a single batch never reaches steady state and the numbers include HTTP and scheduler overhead → ✅ Fix: Pass --enable-multi-batch with batch-size set to a multiple of the server's max-running-requests, treat only overall_throughput as authoritative, and read TTFT and ITL as informational.
- ❌ Mistake: Using bench_one_batch numbers to pick a production batch size, even though it calls ModelRunner directly, bypasses the scheduler, and can OOM where a chunked-prefill server would not → ✅ Fix: Restrict bench_one_batch to kernel profiling, and validate batch size and memory flags through a scheduler-inclusive path (bench_serving or offline throughput).
- ❌ Mistake: Raising --cuda-graph-max-bs-decode to 512 on a large tensor-parallel deployment without touching memory flags, then hitting OOM because graph buffers come out of the non-static share → ✅ Fix: Lower --mem-fraction-static in the same change, then confirm the startup log still leaves 5–8 GB of available_gpu_mem before rollout.

## Tradeoffs — When to Use What
**Suitable**

- **Agent loops, multi-turn chat, and few-shot classification with long shared prefixes.** Radix-tree retention plus `--schedule-policy lpm` converts repeated system prompts and examples into prefill skipped. The extra scheduling cost of lpm is paid back only when prefix overlap is high.
- **Offline batch inference where you control the submission rate.** You can keep `#queue-req` in the documented 100–2000 band and push `token usage` above 0.9. Large steady batches are the main throughput lever, and the scheduler's admission and retraction controls make that tunable from logs rather than guesswork.
- **Deployments that need to separate prefill and decode.** PD disaggregation with a router lets prefill-heavy and decode-heavy phases scale on separate workers. The benchmark tooling can target prefill or decode workers individually for profiling.
- **Hopper/Blackwell/MI300-class fleets for the GLM-5 configurations reported in a third-party benchmark-contract issue.** That issue lists H100, H200, B200 and MI300-class GPUs, notes the DSA kernels (FlashMLA sparse, DeepGEMM indexer, trtllm) are gated to sm_90 / sm_100, and says the cookbook does not list A100. Treat this as secondary evidence about one model's kernel path, not as a general SGLang hardware support matrix.

**Unsuitable**

- **Workloads with near-zero prefix overlap, such as independent one-shot documents.** lpm reordering adds scheduler overhead with no hit-rate payoff. Run the default policy, or keep an incumbent **vLLM** deployment if it already meets SLOs, since migration cost buys no cache benefit.
- **Multi-tenant serving that requires cache-reuse isolation per request.** **vLLM** documents optional per-request salts that restrict prefix-cache reuse to matching requests. Verified information on an equivalent SGLang control is limited in this reference set, so validate isolation before migrating.
- **A100 (sm_80) fleets planning to serve GLM-5 through the DSA kernel path.** In the reported configurations those kernels require sm_90 / sm_100. Keep the existing engine (**vLLM** or **TensorRT-LLM**) on A100 and run any SGLang comparison on H100/H200 rather than extrapolating.
- **Organizations already standardized on TensorRT-LLM behind Triton.** SGLang's own v0.2 comparison configured TensorRT-LLM with batch size 512, max input and token length 8192, and 16 pre/post-processing instances in Triton Server. Matching that tuned baseline is real work, so stay on **TensorRT-LLM** unless a contemporaneous, flag-matched benchmark on your traffic shows a gain.
- **Assuming low-precision formats help every diffusion model.** In one FLUX.3 serving PR, NVFP4 was explicitly not lossless relative to BF16 and regressed a distilled variant. Keep the **BF16** path as the default until each model is measured.

## Industry Communication
- "Postmortem action item: the capacity figure in the design doc came from **bench_offline_throughput**, which runs the **Engine in-process** with no HTTP layer, so it never reflected production **TTFT**. We are re-baselining with **bench_serving** at **num-prompts ≥ 5 × max-concurrency**."
- "PR review: before we merge the **--mem-fraction-static 0.85 → 0.88** bump, attach the startup log line. If **available_gpu_mem** falls below **5 GB**, we're trading KV capacity for OOM risk under peak load."
- "Steady-state decode logs show **token usage near 0.82** with **#queue-req in the hundreds**, so admission is too conservative. I propose **--schedule-conservativeness 0.3** on one canary replica, with an alert if **KV-pool retractions** exceed roughly one per minute."
- "Design doc decision: **--schedule-policy lpm** is enabled only on the agent tier, where requests share multi-kilotoken system prefixes. The summarization tier has little prefix overlap, so lpm's extra **scheduling overhead** would buy nothing there."
- "I'm not accepting the vendor's **29% throughput delta** as evidence: it pairs **SGLang v0.2.3 with vLLM 0.11.0**, roughly two years apart. Rerun on contemporaneous releases with matched flags before this goes into the migration proposal."
- "Hardware review: per the **GLM-5 benchmark contract** we referenced, the **DSA kernels** are gated to **sm_90 / sm_100**. Our **A100** (sm_80) results are out of scope for that model, and the comparison must run on **H100 or H200**."
- "This PR raises **--cuda-graph-max-bs-decode to 512** for the **TP-8** replicas and lowers **--mem-fraction-static** by one step in the same change. Please don't split them, since the graph buffers come out of the non-static share."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **KV Cache** — SGLang's retention, admission, and retraction logic all operate on the KV pool, so you cannot reason about token usage, mem-fraction-static, or prefix hits without knowing what one cached token costs.
- (prerequisite) **Prefill and Decode Phases** — Chunked prefill, CUDA-graph decode, and the OOM-by-phase tuning rules assume you know prefill is compute-bound over the prompt while decode is iterative per token; the knobs map to one phase or the other.
- (alternative) **vLLM** — A competing serving engine that also combines paged allocation with prefix caching; it differs in surrounding controls such as per-request cache salts, so choosing between the two depends on workload shape and version-matched benchmarks.
- (alternative) **TensorRT-LLM** — A competing serving stack, often deployed behind Triton Server, used as a baseline in SGLang's own published comparisons; it is the relevant option when an organization already runs a tuned TensorRT-LLM pipeline.
- (extension) **Prefill-Decode Disaggregation** — Built on the SGLang runtime by splitting prefill and decode onto separate workers behind a router, removing prefill/decode interference at the cost of extra deployment and profiling complexity.
- (extension) **SGLang Model Gateway** — The routing layer (formerly Router) that the tuning docs recommend for data parallelism across replicas, extending single-server scheduling to multi-replica throughput scaling.

## body_advanced_ko

## 기술적 정의와 동작 원리
**SGLang**은 LLM 실행 시스템이다. 두 층으로 구성된다. 하나는 다단계 생성 프로그램을 Python 문법으로 표현하는 **프론트엔드 언어**이고, 다른 하나는 요청을 받아 GPU에서 실행하는 **백엔드 런타임**이다. 런타임의 핵심 구성요소는 세 가지다.
- **RadixAttention**: KV 캐시를 radix tree로 색인한다.
- **캐시 인지 스케줄러**: 요청 순서를 조정해 캐시 적중률을 높인다.
- **정적 메모리 풀**: 가중치와 KV 캐시 풀을 함께 담는다.

NVIDIA 릴리스 노트는 RadixAttention과 함께 전용 LLM 컴파일러를 핵심 요소로 꼽는다. 다만 프론트엔드 프로그램이 런타임 호출로 낮춰지는(lowering) 구체 과정은 해당 주제에 대한 검증된 정보가 부족합니다.

캐시 계층에서는 두 책임을 구분해야 한다.
- **Paging** (할당): 요청 내부에서 블록을 나눠 주고 회수한다. 단편화 때문에 배치 크기가 제한되지 않게 하는 역할이다.
- **Radix-tree 색인** (보존): 요청이 끝난 뒤에도 무엇을 남길지, 다음 요청이 그것을 어떻게 찾을지를 정한다.

vLLM도 두 기법을 모두 갖고 있다. SGLang의 차이는 이 캐시 위에 **적중률을 높이는 스케줄링 정책**(`--schedule-policy lpm`)을 얹는다는 점이다.

요청 하나의 생명주기는 아래와 같다. 각 단계에 근거 수준을 표시했다.

1. **수신·토큰화** [부분 검증]: OpenAI 호환 HTTP 엔드포인트로 요청이 들어온다. 토크나이저가 어느 프로세스에서, 어떤 병렬도로 도는지는 해당 주제에 대한 검증된 정보가 부족합니다. 공식 벤치마크 문서 기준으로 `bench_serving`과 `bench_one_batch_server`는 이 HTTP 계층을 포함해 측정하고, `bench_offline_throughput`은 이 계층을 건너뛰고 `Engine`을 프로세스 내부에서 직접 호출한다.
2. **큐잉·입장 제어** [문서 명시]: 들어온 요청은 대기열에 쌓이며, 그 길이가 로그의 `#queue-req`다. 스케줄러는 `--schedule-conservativeness`로 신규 요청 입장의 공격성을 조절한다. 상한은 `max_running_requests`다(문서 예시 로그 값은 4096).
3. **캐시 조회** [문서 명시 + 일반 메커니즘]: 요청의 토큰 시퀀스로 radix tree에서 가장 긴 공통 접두부를 찾는다. 일반적인 radix tree 성질상 조회 비용은 매칭 길이 L에 비례하는 O(L)이다. 매칭된 L 토큰만큼 prefill 연산을 건너뛴다. `lpm` 정책을 켜면 longest prefix match가 큰 요청이 앞으로 재정렬되어 적중률은 오르지만 스케줄링 오버헤드가 늘어난다.
4. **배치 구성** [문서 명시]: 긴 프롬프트의 prefill은 `chunked_prefill_size` 단위로 쪼개 넣는다. 문서 예시 로그의 설정은 `chunked_prefill_size=8192`, `max_prefill_tokens=16384`다. 디코딩 중인 요청 집합은 동적으로 유지되며, 현재 개수가 `#running-req`, 점유 토큰 수가 `#token`으로 보고된다.
5. **실행** [문서 명시]: `ModelRunner`가 prefill 단계에서 `extend()`, 생성 단계에서 `decode()`를 호출한다. 작은 디코드 배치에는 CUDA graph를 적용한다. 기본 적용 범위는 약 160 또는 256 미만이며 `--cuda-graph-max-bs-decode`로 넓힐 수 있다. 실행 계층에는 TP, DP, expert parallelism, `--enable-torch-compile`, `--quantization fp8` 같은 선택지가 붙는다.
6. **캐시 회수·축출** [부분 검증]: KV 풀이 가득 차면 실행 중인 요청 일부를 되돌린다(retract). 이때 `KV cache pool is full. Retract requests. #retracted_reqs: N, #new_token_ratio: a -> b` 경고가 찍힌다. 완료된 요청의 KV는 즉시 버려지지 않고 radix tree에 남아 다음 요청의 접두부 재사용 대상이 된다. 다만 트리 노드 축출 순서(예: LRU 여부)와 retract된 요청의 재입장 방식은 해당 주제에 대한 검증된 정보가 부족합니다.

**PD disaggregation 모드**에서는 prefill 워커(`--disaggregation-mode prefill`)와 decode 워커(`--disaggregation-mode decode`)가 별도 프로세스로 뜨고, `sglang_router`가 앞단에서 라우팅한다. 이 구조에서는 prefill이 만든 KV를 decode 워커로 넘겨야 한다. 그 전송 비용과 대역폭 요구치는 제공 자료에 수치가 없다.

**측정 데이터의 공개 범위**: 공식 저장소의 v0.2.7 벤치마크 재현 문서는 절차와 하드웨어만 공개한다. 8B는 A100 80GB 1장, 70B는 A100 80GB 8장(TP8), 70B FP8은 H100 8장(TP8)이며, 해당 재현 스크립트는 `--disable-radix-cache`로 서버를 띄운다. 결과 수치는 제공 자료에 포함되어 있지 않아 공식 벤치마크 점수는 비워 둔다.

## 핵심 수식·아키텍처·도표
**GPU 메모리 분할 모델**

공식 튜닝 문서가 제시하는 메모리 구성은 다음과 같다.

$$M_{\text{total}} = M_{\text{weights}} + M_{\text{KV}} + M_{\text{graph}} + M_{\text{act}}$$

`--mem-fraction-static`은 앞의 두 항을 GPU 용량 대비 비율로 정한다.

$$f_{\text{static}} = \frac{M_{\text{weights}} + M_{\text{KV}}}{M_{\text{GPU}}}$$

이를 KV 풀에 대해 정리하면, 가중치가 고정일 때 f를 올린 만큼이 전부 KV 풀로 간다.

$$M_{\text{KV}} = f_{\text{static}} \cdot M_{\text{GPU}} - M_{\text{weights}}$$

남는 영역은 CUDA graph 버퍼와 activation을 감당해야 한다.

$$(1 - f_{\text{static}}) \cdot M_{\text{GPU}} \ge M_{\text{graph}} + M_{\text{act}}$$

**토큰 용량 근사** (표준 MHA/GQA 가정)

토큰 하나의 KV 바이트는 레이어 수, KV 헤드 수, 헤드 차원, 원소 바이트 수로 정해진다. K와 V 두 개이므로 2를 곱한다.

$$b_{\text{tok}} = 2 \cdot n_{\text{layer}} \cdot n_{\text{kv\_head}} \cdot d_{\text{head}} \cdot \text{bytes}$$

$$N_{\text{tok}} \approx \frac{M_{\text{KV}}}{b_{\text{tok}}}$$

**식의 가정과 한계**
- SGLang이 풀을 잡을 때 페이지 단위 반올림, 런타임 예약 영역, TP 분할 후 GPU별 계산을 어떻게 하는지는 제공 자료에 공개되어 있지 않다. 따라서 위 식은 상한 근사로만 쓴다.
- MLA 계열 어텐션, FP8 KV, sliding window 모델은 b_tok 식 자체가 달라진다.
- M_graph는 `--cuda-graph-max-bs-decode`에 따라 커지지만 계산식이 공개되어 있지 않다.

**실측 검증 방법**
- 서버 준비 직전 로그의 `max_total_num_tokens`를 N_tok 근사치와 비교한다. 문서 예시 값은 665690이다.
- 같은 로그의 `available_gpu_mem`이 5–8GB인지 확인한다. 이 범위는 문서의 경험칙이다.
- 문서 예시처럼 13.50GB가 남아 있으면 f를 0.01씩 올리며 실제 워크로드에서 OOM 경계를 찾는다.

**정상 상태 측정 조건**

`bench_serving`은 프롬프트 수가 동시성의 5배 이상일 때 정상 상태로 본다.

$$N_{\text{prompts}} \ge 5 \cdot C_{\text{max\_concurrency}}$$

**런타임 플래그 영향 매트릭스**

| 플래그 | 영향 영역 | 올릴 때 | 내릴 때 | 확인할 로그 신호 |
|---|---|---|---|---|
| `--mem-fraction-static` | 가중치+KV 풀 | 동시성·처리량 상승, activation OOM 위험 | OOM 회피(예: 0.8/0.7), 피크 처리량 감소 | `available_gpu_mem`, `max_total_num_tokens` |
| `--chunked-prefill-size` | prefill 활성 메모리 | 긴 프롬프트 prefill 속도 상승 | prefill OOM 회피(4096/2048), 긴 프롬프트 지연 증가 | prefill 단계 OOM 여부 |
| `--max-running-requests` | 디코드 동시성 | 배치 확대 | decode OOM 회피 | `#running-req` |
| `--schedule-conservativeness` | 입장 제어 | retract 감소(예: 1.3) | KV 활용률 상승(예: 0.3) | `token usage`, retract 경고 빈도 |
| `--cuda-graph-max-bs-decode` | graph 버퍼 | 대형 TP에서 512/768까지 유효할 수 있음 | 메모리 확보 | `cuda graph: True/False` |
| `--schedule-policy lpm` | 스케줄링 | 공유 접두부 적중률 상승 | 스케줄링 오버헤드 제거 | 처리량과 TTFT 변화 |

**측정 계층 매트릭스**

| 도구 | HTTP | 스케줄러 | 측정 대상 | 해석 시 주의 |
|---|---|---|---|---|
| `bench_serving` | 포함 | 포함(간접) | TTFT, TPOT, ITL, 처리량 | 기본 선택지 |
| `bench_one_batch_server` | 포함 | 포함(간접) | 단일 배치 E2E 지연 | 정상 상태에 도달하지 않아 편향됨 |
| `bench_offline_throughput` | 제외 | 직접(`Engine`) | 네트워크 없는 최대 처리량 | 온라인 지연 지표가 아님 |
| `bench_one_batch` | 제외 | 우회(`ModelRunner`) | 커널 수준 지연 | 동적 배치가 없어 실서버보다 일찍 OOM 가능 |

## 코드 또는 의사코드
```python
"""SGLang decode-batch 로그 윈도우 분석기 (관측과 튜닝 권고를 분리).

근거: SGLang 공식 Hyperparameter Tuning 문서의 'Decode batch.' 로그 예시와 임계값
(#queue-req 100-2000, token usage > 0.9, retract 경고 분당 ~1회는 허용).
대상 릴리스는 고정되지 않음: 운영 버전의 실제 로그로 FIXTURE를 교체해 회귀 테스트할 것.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import Callable

TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
FIELDS: dict[str, tuple[re.Pattern[str], Callable[[str], float]]] = {
    "running": (re.compile(r"#running-req: (\d+)"), int),
    "tokens": (re.compile(r"#token: (\d+)"), int),
    "usage": (re.compile(r"token usage: ([0-9.]+)"), float),
    "gen_tps": (re.compile(r"gen throughput \(token/s\): ([0-9.]+)"), float),
    "queue": (re.compile(r"#queue-req: (\d+)"), int),
}
RETRACT = "KV cache pool is full. Retract requests."
MIN_SAMPLES = 3   # 내부 경험칙: 단일 샘플로 튜닝 판단 금지
FREQUENT = 0.5    # 내부 경험칙: 문서의 'frequently'를 윈도우 내 비율 50%로 해석

@dataclass
class Window:
    rows: list[dict[str, float]] = field(default_factory=list)
    parse_failures: int = 0  # 'Decode batch.' 후보지만 필드 누락 -> 로그 형식 변경 의심
    out_of_range: int = 0    # token usage가 [0, 1] 밖 -> 파서/형식 불일치
    retracts: int = 0
    minutes: float = 0.0

def parse_window(lines: list[str]) -> Window:
    w = Window()
    stamps: list[datetime] = []
    for line in lines:
        if ts := TS.match(line):
            stamps.append(datetime.fromisoformat(ts.group(1)))
        if RETRACT in line:
            w.retracts += 1
        if "Decode batch." not in line:
            continue
        row: dict[str, float] = {}
        for name, (pat, cast) in FIELDS.items():  # 필드별 독립 추출
            if hit := pat.search(line):
                row[name] = cast(hit.group(1))
        if len(row) != len(FIELDS):
            w.parse_failures += 1                  # 실패 경로 1: 형식 드리프트
        elif not 0.0 <= row["usage"] <= 1.0:
            w.out_of_range += 1                    # 실패 경로 2: 값 범위 위반
        else:
            w.rows.append(row)
    if len(stamps) >= 2:
        w.minutes = (max(stamps) - min(stamps)).total_seconds() / 60
    return w

def observe(w: Window) -> dict[str, float]:
    """관측값만 계산한다. 판단은 recommend()의 책임."""
    n = len(w.rows)
    if n == 0:
        return {"samples": 0, "parse_failures": w.parse_failures}
    return {
        "samples": n,
        "parse_failures": w.parse_failures,
        "out_of_range": w.out_of_range,
        "usage_p50": median(r["usage"] for r in w.rows),
        "queue_p50": median(r["queue"] for r in w.rows),
        "gen_tps_p50": median(r["gen_tps"] for r in w.rows),
        "low_usage_with_queue": sum(r["usage"] < 0.9 and r["queue"] > 0 for r in w.rows) / n,
        "zero_queue": sum(r["queue"] == 0 for r in w.rows) / n,
        "retract_per_min": w.retracts / w.minutes if w.minutes > 0 else 0.0,
    }

def recommend(obs: dict[str, float]) -> list[str]:
    if obs["samples"] < MIN_SAMPLES:
        return ["HOLD: 정상 상태 샘플 부족, 윈도우 확대"]
    recs: list[str] = []
    if obs["zero_queue"] >= FREQUENT:
        recs.append("CLIENT: #queue-req 0 빈발, 제출 속도 상향")
    if obs["low_usage_with_queue"] >= FREQUENT:
        recs.append("SERVER: usage<0.9 & 대기열 존재, --schedule-conservativeness 하향(예: 0.3)")
    if obs["retract_per_min"] > 1.0:
        recs.append("SERVER: retract 분당 1회 초과, --schedule-conservativeness 상향(예: 1.3)")
    if obs["queue_p50"] > 2000:
        recs.append("CLIENT: #queue-req 2000 초과, 스케줄링 오버헤드 우려")
    return recs or ["OK: 문서 기준 정상 범위"]

FIXTURE = [
    "[2025-08-11 17:20:00] Decode batch. #running-req: 233, #token: 370959, token usage: 0.82, cuda graph: True, gen throughput (token/s): 4594.01, #queue-req: 317",
    "[2025-08-11 17:20:20] Decode batch. #running-req: 240, #token: 380112, token usage: 0.85, cuda graph: True, gen throughput (token/s): 4610.50, #queue-req: 290",
    "[2025-08-11 17:20:40] Decode batch. #running-req: 241, #token: 378004, token usage: 0.84, cuda graph: True, gen throughput (token/s): 4602.10, #queue-req: 305",
    "[2025-08-11 17:21:00] Decode batch. #running-req: 12, token usage: 0.80, #queue-req: 3",
    "[2025-08-11 17:21:00] Decode batch. #running-req: 5, #token: 9, token usage: 1.70, cuda graph: True, gen throughput (token/s): 10.0, #queue-req: 0",
]

def test_window() -> None:
    obs = observe(parse_window(FIXTURE))
    assert (obs["samples"], obs["parse_failures"], obs["out_of_range"]) == (3, 1, 1)
    assert obs["usage_p50"] == 0.84 and obs["queue_p50"] == 305
    assert recommend(obs) == ["SERVER: usage<0.9 & 대기열 존재, --schedule-conservativeness 하향(예: 0.3)"]
    noisy = FIXTURE + ["[2025-08-11 17:20:30] KV cache pool is full. Retract requests. #retracted_reqs: 1"] * 2
    assert observe(parse_window(noisy))["retract_per_min"] == 2.0
    assert recommend(observe(parse_window(FIXTURE[:1])))[0].startswith("HOLD")

if __name__ == "__main__":
    test_window()
    print(recommend(observe(parse_window(FIXTURE))))
    # 예상 출력: ['SERVER: usage<0.9 & 대기열 존재, --schedule-conservativeness 하향(예: 0.3)']
```

## 프로덕션 함정
- ❌ 실수: `bench_one_batch_server` 한 번의 결과나 `bench_one_batch`의 정적 배치 지연을 서비스 용량 계획에 그대로 쓴다. 공식 문서가 밝히듯 전자는 정상 상태에 도달하지 않아 편향되고, 후자는 스케줄러를 우회한다 → ✅ 해결: 용량 계획에는 `bench_serving`을 쓰고 `num-prompts >= 5 * max-concurrency`를 지킨다(공식 문서 권고). 단일 배치 도구는 커널 회귀 추적용으로만 남겨 두고, 보고서에 도구 이름과 측정 계층을 반드시 함께 적는다.
- ❌ 실수: 실제 프롬프트로 `bench_one_batch_server`를 돌리면서 EOS 무시 기본 동작을 그대로 둔다. 혹은 `--enable-multi-batch`를 켠 상태에서 ITL과 `output_throughput`을 비교 지표로 쓴다. 두 경우 모두 출력 분포나 분모가 왜곡된다 → ✅ 해결: 실제 프롬프트에는 `--disable-ignore-eos`를 넣고 정상 상태 컬럼만 비교한다. multi-batch 모드에서는 공식 문서대로 `overall_throughput`만 권위 있는 값으로 취급하며, 나머지 지표는 참고값으로 표기한다.
- ❌ 실수: `--mem-fraction-static`을 올린 직후 `--cuda-graph-max-bs-decode`까지 같이 키운다. 그러면 graph 버퍼가 남은 activation 영역을 잠식해 부하가 올라가는 시점에 OOM이 난다 → ✅ 해결: 두 플래그는 하나씩 바꾼다. 매번 시작 로그의 `available_gpu_mem`이 5–8GB인지 확인한다(공식 문서의 경험칙). f는 0.01씩 올리며 실제 워크로드로 OOM 경계를 찾는다.
- ❌ 실수: `KV cache pool is full. Retract requests.` 경고가 한 번 찍힐 때마다 장애로 분류하거나, `token usage` 순간값 하나만 보고 conservativeness를 조정한다 → ✅ 해결: 공식 문서는 분당 약 1회 수준의 retract는 정상으로 본다. 수십 분 단위 윈도우에서 retract 빈도와 '저활용 + 대기열 존재' 비율을 집계한 뒤 0.3이나 1.3 방향으로 조정한다. 윈도우 길이와 '빈번함'의 비율 기준은 공식 수치가 아니라 팀 내부 경험칙임을 런북에 명시한다.

## 트레이드오프와 언제 무엇을 쓰나
이럴 때 적합:

- **공유 접두부 비중이 높은 워크로드**: few-shot 템플릿, 긴 시스템 프롬프트, 에이전트의 반복 호출이 여기에 해당한다. 매칭된 접두부 토큰만큼 prefill 연산이 생략되고, `--schedule-policy lpm`으로 적중률을 더 끌어올릴 수 있다. 대가는 공식 문서가 명시한 스케줄링 오버헤드 증가다.
- **큰 배치를 유지할 수 있는 오프라인 대량 추론**: 공식 튜닝 문서는 오프라인 처리량의 최우선 조건으로 큰 배치 크기를 꼽는다. 클라이언트가 `#queue-req`를 100–2000 범위로 유지하고 `token usage`를 0.9 이상으로 끌어올리면 KV 풀이 처리량을 거의 다 활용하는 상태가 된다.
- **sm_90/sm_100 세대 GPU로 최신 희소 어텐션 모델 운영**: GLM-5 서빙 경로는 H100, H200, B200, MI300급을 대상으로 하며, DSA 커널(FlashMLA sparse, DeepGEMM indexer, trtllm)은 sm_90/sm_100으로 게이팅되어 있다. 이 하드웨어를 이미 보유했다면 모델 지원 시점의 이점이 있다.
- **NVIDIA 외 GPU 또는 월간 컨테이너 기반 운영**: 프로젝트가 PyTorch 생태계에 합류했고 AMD nightly 이미지에서의 성능을 발표했다. NVIDIA는 SGLang 컨테이너를 월간 릴리스로 제공한다(2026년 8월 시점 26.07). 드라이버와 라이브러리 조합을 직접 맞추는 비용이 줄어든다.

이럴 때 부적합:

- **A100(sm_80) 전용 플릿에서 DSA 커널에 의존하는 모델 서빙**: 해당 커널이 sm_90/sm_100으로 게이팅되어 있고 cookbook도 A100을 다루지 않는다. 같은 모델과 정밀도로 vLLM 또는 TensorRT-LLM의 지원 여부를 먼저 검증해야 한다. 그렇지 않으면 하드웨어 교체 비용이 엔진 선택 비용에 그대로 얹힌다.
- **테넌트 간 캐시 공유를 정책상 막아야 하는 멀티테넌트 서빙**: vLLM은 요청별 salt로 캐시 재사용 범위를 제한하는 옵션을 제공한다. SGLang의 동등 기능은 제공 자료로 확인되지 않으므로, 격리 요구가 강하면 vLLM이 설계 리스크가 낮다.
- **접두부가 거의 겹치지 않는 단발성 요청 위주의 트래픽**: radix 보존과 `lpm` 재정렬에서 얻을 이득이 작고 스케줄링 오버헤드만 남는다. 기본 정책을 쓰거나, 정적 배치·입력 길이 상한을 미리 고정하는 TensorRT-LLM 방식과 비교 측정하는 편이 낫다. TensorRT-LLM 방식의 예로, v0.2.7 비교 실험은 batch 512, max input 8192, max tokens 8192로 구성했다.
- **런타임 튜닝 인력이 없는 소규모 팀**: 공식 문서 스스로 `--mem-fraction-static` 기본값이 단순 휴리스틱이라고 밝힌다. 기본값만으로는 OOM과 저활용 사이를 오갈 수 있으므로, Inference.net 같은 관리형 SGLang 배포를 검토하는 편이 운영 부담이 적다.

**구성 선택별 비용 비교** (수치가 공개되지 않은 항목은 그렇게 표기)

| 선택 | 얻는 것 | 치르는 비용 | 검증 방법 |
|---|---|---|---|
| `lpm` 스케줄링 | 공유 접두부 적중률 | 스케줄링 오버헤드 (수치 미공개) | 동일 트래픽 재생 후 TTFT·처리량 비교 |
| 멀티 LoRA (`--enable-lora --lora-paths`) | 원본 모델 하나에 여러 어댑터 | 어댑터 가중치가 정적 메모리를 점유해 KV 풀과 경쟁 (점유량 미공개) | 어댑터 로드 전후 `max_total_num_tokens` 비교, `bench_one_batch_server --lora-name` |
| PD disaggregation | prefill과 decode의 간섭 분리 | 워커 간 KV 전송 (대역폭·지연 미공개), 프로세스 2종 + router 운영, 프로파일을 워커별로 따로 떠야 함 | `--pd-separated --profile-prefill-url` / `--profile-decode-url`로 각각 측정 |
| CUDA graph 범위 확대 | 대형 TP에서 512/768 배치까지 이득 가능 | graph 버퍼 메모리 증가로 `--mem-fraction-static` 하향 필요 | `available_gpu_mem`과 디코드 처리량 동시 확인 |
| DP 우선 (Model Gateway 경유) | 처리량 (문서 권장) | 레플리카마다 가중치를 중복 적재 | 메모리 여유가 있을 때만 적용 |
| FP8/NVFP4 양자화 | 메모리 절감, 일부 성능 향상 | 무손실 아님. FLUX.3 사례에서 base NVFP4 T2I는 +8.88%, distilled NVFP4 T2I는 -4.05% | 품질 회귀 세트로 BF16 대비 확인 |

## 업계 대화 맥락
- "[가상 사례·design doc] 엔진 비교 계약은 **SGLang과 vLLM을 같은 분기에 릴리스된 버전**으로 고정하고, 하드웨어는 **H100** (sm_90)으로 맞춥니다. 버전 차이가 약 2년인 비교는 결론에 쓰지 않습니다."
- "[가상 사례·PR review] 측정 스크립트가 **bench_one_batch_server** 단일 실행 값을 p50으로 보고하고 있어서 머지를 보류합니다. **bench_serving**으로 바꾸고 **num-prompts ≥ 5 × max-concurrency**를 지켜 주세요."
- "[가상 사례·postmortem, 원인 가설] 피크 시간대 OOM의 1차 가설은 **--cuda-graph-max-bs-decode 512 상향**으로 늘어난 graph 버퍼가 activation 여유분을 잠식했다는 것입니다. **mem-fraction-static**은 이번 변경에서 건드리지 않았습니다."
- "[가상 사례·postmortem, 추가 관측] 가설을 확인하려고 롤백 전후의 시작 로그에서 **available_gpu_mem**과 **max_total_num_tokens**를 수집했습니다. 같은 30분 윈도우에서 **retract 빈도**도 함께 비교할 예정입니다."
- "[가상 사례·postmortem, 변경 전후 검증] 롤백 뒤에는 동일 **ShareGPT 재생 트래픽**으로 TTFT·ITL 분포를 다시 측정합니다. **단일 샘플이 아니라 윈도우 중앙값**으로 회귀 여부를 판정합니다."
- "[가상 사례·architecture review] 접두부 공유율을 아직 측정하지 않았으므로 **--schedule-policy lpm** 도입은 보류합니다. 먼저 트래픽 샘플에서 공통 접두부 길이 분포를 뽑아, 스케줄링 오버헤드를 정당화할 수 있는지부터 봐야 합니다."
- "[가상 사례·design doc] **PD disaggregation**으로 전환하려면 prefill→decode **KV 전송 비용**을 실측해야 합니다. 프로파일링은 **--profile-prefill-url**과 **--profile-decode-url**이 상호 배타적이라 워커별 두 번 실행으로 계획합니다."
- "[가상 사례·PR review] **NVFP4** 전환 PR은 처리량 개선만 보고하고 있습니다. distilled 변형에서 성능이 오히려 떨어진 공개 사례가 있으니, 모델 변형별 **BF16 대비 품질 회귀 결과**를 첨부해 주세요."

## 선행·대안·확장 개념
- (선행) **KV Cache** — 트랜스포머 디코딩에서 이전 토큰의 key/value를 저장해 재계산을 피하는 일반 기법이다. SGLang의 메모리 분할식, token usage, retract 동작이 모두 이 캐시의 용량을 기준으로 정의되므로 먼저 이해해야 한다.
- (선행) **Prefill과 Decode 단계** — 프롬프트 전체를 한 번에 처리하는 계산 집약적 단계와, 토큰을 하나씩 생성하는 단계의 구분이다. chunked prefill 크기, decode 단계 OOM 대응, PD 분리 같은 SGLang 튜닝 축이 이 구분 위에 세워져 있다.
- (대안) **vLLM** — 같은 OpenAI 호환 서빙 문제를 paging과 prefix caching으로 푸는 엔진이다. 핵심 캐시 기법은 SGLang과 겹치고, 차이는 요청별 salt를 통한 캐시 격리 같은 주변 기능에 있다. 그래서 비교 범위는 같은 시기의 버전, 같은 플래그, 같은 트래픽으로 제한해야 의미가 있다.
- (대안) **TensorRT-LLM** — 배치 크기와 입력·출력 길이 상한을 미리 고정해 구성하는 NVIDIA 추론 스택이다. SGLang v0.2.7 비교 실험에서는 batch 512, max input 8192, max tokens 8192로 구성되었다. 비교의 초점은 동적 스케줄링의 유연성 대비 고정 구성의 예측 가능성이다.
- (확장) **PD Disaggregation** — SGLang 서버를 prefill 워커와 decode 워커로 나누고 router로 묶는 배포 형태다. 두 단계의 자원 간섭을 분리하는 대신, 워커 간 KV 전송과 워커별 분리 프로파일링이라는 운영 비용이 추가된다.
- (확장) **SGLang Model Gateway** — 이전 이름이 Router인 컴포넌트다. 공식 튜닝 문서는 단일 프로세스의 `dp_size` 대신 이 게이트웨이로 데이터 병렬을 구성하라고 권한다. 여러 레플리카에 걸친 라우팅으로 처리량 확장을 맡는 상위 계층이다.

## references_en

- {"title": "Benchmark and Profiling - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling", "tier": "primary", "annotation": "Official guide to SGLang's four benchmark tools and which metrics (TTFT, TPOT, ITL, throughput) each one can be trusted for."}
- {"title": "Hyperparameter Tuning - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning", "tier": "primary", "annotation": "Official tuning guide: KV cache memory sizing, OOM fixes, and the lpm policy for shared-prefix workloads."}
- {"title": "SGLang Release Notes", "authors": "NVIDIA", "year": 2026, "type": "docs", "url": "https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/index.html", "tier": "primary", "annotation": "NVIDIA's container release notes: SGLang overview, RadixAttention role, and per-release features and known issues."}
- {"title": "sgl-learning-materials", "authors": "sgl-project", "type": "code", "url": "https://github.com/sgl-project/sgl-learning-materials", "tier": "primary", "annotation": "공식 팀이 모은 발표·블로그 자료와 PyTorch 생태계 합류 공지."}
- {"title": "SGLang vs vLLM (2026): Which Is Best for Your Workload?", "type": "blog", "url": "https://tensormesh.ai/learn/vllm-vs-sglang", "tier": "secondary", "annotation": "Explains how paging and radix-tree prefix retention differ, and why workload shape decides the engine choice."}
- {"title": "vLLM vs SGLang: Performance, Features & Deployment Compared", "type": "blog", "url": "https://deepinfra.com/blog/vllm-vs-sglang", "tier": "secondary", "annotation": "Shows how mismatched versions and tuning flags can distort head-to-head engine benchmarks."}
