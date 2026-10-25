# SGLang — claude-sonnet-5-5

- advanced 57 / basic 52 / gate blocked / penalty 4 / $2.0762 / 746s

## definition_en

SGLang (Structured Generation Language) is an open-source runtime for serving large language models, paired with a Python-embedded frontend language, that reuses cached key-value state across requests sharing a prompt prefix through RadixAttention's radix-tree index. Its scheduler can reorder queued requests to raise cache hits, targeting multi-step workloads such as agents and few-shot prompting.

## definition_ko

SGLang은 LLM 추론을 위한 오픈소스 서빙 런타임이자 Python 기반 구조화 생성 언어로, 프롬프트 앞부분이 겹치는 요청들의 KV 캐시를 RadixAttention의 트리 색인으로 재사용하고 캐시 적중률을 높이는 요청 스케줄링을 결합해, 에이전트나 few-shot처럼 반복 구간이 많은 다단계 워크로드의 중복 계산을 줄인다.

## summary_en

SGLang is an open-source engine for running large language models, plus a Python-based way to write multi-step prompts. Think of a filing cabinet for work the model has already done: when a new request starts with the same opening text as an earlier one, SGLang finds the matching folder through a tree-shaped index and reuses the saved work instead of redoing it. It then processes only the part that is new. This helps most for agents and few-shot prompts, where many requests share a long beginning, but the savings depend on how much text overlaps and whether the saved work is still in memory.

## summary_ko

SGLang은 AI 모델에게 질문을 전달하고 답을 뽑아 주는 '서빙 엔진'이에요. 같은 육수를 매번 새로 끓이는 대신 큰 솥에 미리 끓여 두고 덜어 쓰는 식당처럼, 앞부분이 똑같은 질문들의 계산 결과를 저장해 두었다가 다시 써서 시간을 아낍니다. 이 저장소를 트리 모양으로 정리하는 방식(RadixAttention)과, 재사용이 잘 되도록 대기 중인 요청 순서를 조정하는 방식이 핵심이에요. 같은 지시문을 반복하는 에이전트나 챗봇에서 특히 효과가 클 수 있지만, 속도 비교는 버전과 설정에 따라 달라지니 직접 측정해 보는 게 좋습니다.

## body_basic_en

## Plain Explanation
Serving a large language model (LLM) has a hidden waste problem. Before the model can write its first word, it reads the whole prompt and saves intermediate results for every token. That saved state is called the **KV cache** (key-value cache), and it keeps the model from re-reading earlier text at every step. In agent loops or few-shot prompts (prompts that open with a handful of worked examples), thousands of requests can begin with the same long opening, yet a naive server rebuilds that same state every time.

**SGLang** (short for Structured Generation Language) is an open-source serving runtime for LLMs, paired with a Python-embedded language for writing multi-step generation programs. Its core idea, **RadixAttention**, keeps cached KV entries and indexes them in a **radix tree**, a tree whose branches follow shared sequences of tokens. Picture a filing cabinet: the folders and their labels are the radix-tree index, branching into more specific folders as a prompt gets longer, and the papers inside the folders are the stored KV-cache entries. When a new request arrives, the server walks down the folders as far as the prompt matches, reuses what it finds, and computes only the unmatched remainder.

The reuse applies only when compatible prefix entries are still available in the cache, and that cache lives in limited GPU memory. The match also has to start at the beginning of the prompt, so a prompt whose opening differs has little to reuse after it. SGLang adds a scheduler that can reorder waiting requests; its longest-prefix-match (lpm) policy, for example, reorders requests to encourage more cache hits, at the cost of extra scheduling overhead.

## Examples & Analogies
- **Few-shot ticket classification**: The fixed segment is a prompt holding, say, ten labeled support tickets as examples. The changing segment is the one new ticket appended at the end of each request. The server can reuse the stored KV entries for the ten examples and compute only the new ticket's tokens.
- **Branching drafts from one document**: A program reads a long contract once, then forks into three branches: "summarize the risks", "list the deadlines", and "draft a reply". The contract text is the shared prefix and is computed once. Only each branch's instruction and generated answer are branch-specific computation.
- **Agent loop with growing history**: An agent's system prompt and tool descriptions stay identical on every turn, and each turn adds the latest tool result to the conversation. The earlier part of the history matches what is already cached, so only the newly appended tokens need fresh computation. This holds only while those earlier entries remain in the cache. If they have been dropped, they must be recomputed.

## At a Glance
| | SGLang | vLLM |
|---|---|---|
| Prefix reuse | Radix-tree index of cached prefixes (RadixAttention) | Prefix caching, listed in vLLM's design docs |
| Request ordering to raise cache hits | Scheduling policy paired with the cache; lpm (longest prefix match) option | Not described in the sources used here |
| Limiting who can reuse a cached prefix | Not described in the sources used here | Optional per-request salts restrict reuse to the same salt |
| Setting that can shift a latency metric | Chunked-prefill size: smaller saves memory but slows long-prompt prefill | Chunked-prefill size: smaller improves inter-token latency, larger improves time to first token |

These are design differences, not a speed ranking, and a fair comparison needs matched release versions, flags, hardware, and workload; one published setup, for instance, paired SGLang v0.2.3 with vLLM 0.11.0, releases roughly two years apart.

## Where and Why It Matters
- **Supported use cases: agents, chain-of-thought, few-shot**: NVIDIA's SGLang release notes name complex agents, chain-of-thought reasoning, and few-shot prompting strategies as common use cases. These are the workloads where repeated prompt openings are most likely, so they are where prefix reuse has the most to offer. How much it actually saves still depends on your traffic.
- **Cache-aware scheduling is an option, not a free win**: The docs suggest trying the lpm policy when a workload has many shared prefixes, since it reorders requests to encourage more cache hits. The same docs note it introduces more scheduling overhead. Whether the trade pays off has to be measured per workload.
- **Memory is the budget for reuse**: SGLang's tuning guide describes the KV cache pool as sharing GPU memory with model weights, CUDA graph buffers, and activations. A larger pool supports higher concurrency, and the docs treat token usage above 0.9 as good utilization. Pool capacity therefore bounds how many prefixes can stay cached.
- **Hardware and model support is checked per model**: One third-party comparison project's GitHub issue reports that SGLang serves GLM-5 on H100, H200, B200 and MI300-class GPUs, with some kernels gated to newer GPU generations and A100 not listed in its cookbook. Treat this as a reason to check the support matrix for your exact model and GPU before planning a rollout.
- **Evaluation context: measure on your own traffic**: SGLang's docs recommend bench_serving by default for realistic online benchmarks, reporting time to first token (TTFT), time per output token (TPOT), and inter-token latency (ITL). Published SGLang-vs-vLLM gaps depend on versions, flags, and workload shape, so a leaderboard number is a starting hypothesis rather than a purchasing decision.

## Common Misconceptions
- ❌ Myth: Using SGLang makes every request faster. → ✅ Reality: Savings come only from requests whose beginnings overlap with earlier ones, and only while the matching cached entries are still available. Fully unique prompts get little from the cache.
- ❌ Myth: A benchmark win for SGLang (or for vLLM) settles the choice. → ✅ Reality: The two engines have taken turns leading as new releases land, and results shift with versions, flags, hardware, and workload. A result from mismatched releases cannot tell you which is faster today.
- ❌ Myth: Defaults are tuned for your workload, so there is nothing to adjust. → ✅ Reality: SGLang sets defaults with simple heuristics, and its docs recommend checking server logs, such as token usage and available GPU memory, and adjusting settings like the memory fraction or scheduling policy for your own traffic.

## How It Sounds in Conversation
- "Before we switch the agent backend, let's replay a day of real traffic through **bench_serving** and look at **TTFT** and **ITL**, not just total throughput."
- "Our prompts all start with the same long system prompt, so check the logs to see whether the **radix cache** is actually being hit before we credit it for the latency drop."
- "Run it twice with the same model, GPU, and flags: once with **--disable-radix-cache** and once with defaults. Otherwise we can't say what the cache bought us."
- "That blog comparison paired an old **SGLang** release with a much newer **vLLM**, so let's rerun both on matching versions before it goes in the planning doc."
- "Try **--schedule-policy lpm** on the few-shot workload. It adds scheduling overhead, so compare p99 latency before and after, not only the average."

## Related Reading
- (before) **KV Cache** — The saved per-token state that RadixAttention indexes and reuses; read this first to see what is actually being cached and why it takes GPU memory.
- (before) **Prefill and Decode** — The two phases of serving a request; prefix reuse mainly saves prefill work, and SGLang's docs show prefill and decode workers profiled separately in disaggregated setups.
- (similar) **vLLM** — The most common peer serving runtime; it also does prefix caching but with different surrounding machinery, so compare them on matched versions and flags.
- (similar) **TensorRT-LLM** — NVIDIA's serving stack, used as a comparison backend in SGLang's own benchmark reproduction scripts; useful as a third reference point.
- (next) **Tensor Parallelism** — Splits one model across several GPUs; SGLang exposes it through a tensor-parallel size setting, and its tuning docs contrast it with data parallelism for throughput.
- (next) **Prefill-Decode Disaggregation** — Runs prefill and decode on separate workers; read this once single-server prefix reuse feels familiar and you want to scale out.

## body_basic_ko

## 쉽게 이해하기
LLM으로 서비스를 만들면 요청 수백 개가 똑같은 긴 지침문이나 예시로 시작하는 일이 흔하다. 에이전트처럼 한 번의 작업 안에서 모델을 여러 번 부르거나, 하나의 질문에서 여러 후보 답안으로 갈라지는 구조도 많다. 모델은 입력을 읽을 때마다 앞부분을 처음부터 계산하는데, 이 계산 결과가 KV 캐시(이미 읽은 토큰에 대해 모델이 만들어 둔 중간 기록)다. 앞부분이 같은데도 매번 새로 계산하면 GPU 시간과 메모리를 그대로 낭비하게 된다.

SGLang은 이 낭비를 줄이려는 시스템이다. 이름 그대로 구조화된 생성 프로그램을 쓰는 파이썬 기반 언어와, 그 프로그램을 빠르게 돌리는 백엔드 런타임이 한 묶음으로 되어 있다. 비유하자면 같은 책의 앞 장을 손님이 올 때마다 처음부터 다시 읽는 대신, 사서가 앞 장 요약 노트를 책상에 올려 두고 손님들이 함께 쓰게 하는 방식이다. 이 노트를 관리하는 핵심 기술이 RadixAttention이다.

작동 원리는 이렇다. 요청이 들어오면 앞부분이 이미 저장된 캐시와 겹치는지 찾아보고, 겹치는 만큼은 계산을 건너뛰고 나머지부터 계산한다. 분기가 있는 프로그램에서는 갈라진 가지들이 공통 앞부분을 공유하므로 가지들을 병렬로 처리하기 쉽다. 여기에 요청 순서를 바꿔 캐시 적중을 높이는 스케줄링 정책(예: 가장 긴 접두사 일치 우선)이 더해진다. 대신 캐시는 GPU 메모리에 있어야 하므로 메모리가 가득 차면 일부 요청을 되돌리는 일이 생기고, 순서를 재정렬하는 만큼 스케줄링 비용도 늘어난다.

## 비유와 예시
- **공통 시스템 프롬프트를 쓰는 다수 요청**: 예컨대 사내 질의응답 서비스에서 모든 요청이 같은 긴 지침문으로 시작한다고 하자. 그 앞부분의 캐시가 메모리에 남아 있으면 뒤따르는 요청은 그 계산을 건너뛸 수 있고, SGLang 튜닝 문서도 공유 접두사가 많은 워크로드에서는 가장 긴 접두사 일치 정책을 시험해 보라고 안내한다.
- **한 질문에서 여러 후보 답안으로 갈라지는 생성**: 하나의 프롬프트에서 여러 답안을 동시에 만들어 비교하는 프로그램을 생각해 보자. 각 가지는 같은 앞부분을 공유하므로, RadixAttention이 이 공통 부분의 계산을 한 번만 하고 가지들을 병렬로 처리하도록 설계되어 있다.
- **같은 few-shot 예시 묶음을 붙인 반복 호출**: 분류나 추출 작업에서 똑같은 예시 몇 개를 매번 앞에 붙여 입력만 바꿔 호출하는 경우다. 예시 묶음이 공통 접두사가 되므로 캐시 재사용 대상이 되며, NVIDIA 릴리스 노트도 few-shot 프롬프팅 전략을 대표 사용처로 든다.

## 한눈에 비교
| | SGLang | vLLM |
|---|---|---|
| 프리픽스 캐싱 | 사용 | 사용 (vLLM 설계 문서가 프리픽스 캐싱을 언급) |
| 캐시 구조의 두 층 | 블록 단위 할당(페이징)과 접두사 보관·탐색(radix 트리)을 모두 수행 | 두 층을 모두 수행 |
| 캐시 재사용 제어 | 요청 순서를 재정렬하는 스케줄링 정책으로 적중률을 높이는 방향 | 요청별 salt(선택)로 재사용 범위를 제한하는 방향 |

두 엔진은 캐시 구조 자체가 많이 겹치므로 어느 쪽이 빠른지는 버전·설정·워크로드를 맞춘 자체 측정으로만 판단해야 한다.

## 어디서 왜 중요한가
- **NVIDIA의 SGLang 컨테이너 배포**: NVIDIA 릴리스 노트에 따르면 SGLang 컨테이너는 월 단위로 배포되며, 문서에는 26.07(2026년 8월 표기)과 26.06 릴리스 장이 있다. 직접 빌드하는 대신 컨테이너를 받아 실행하는 경로가 공식 문서화되어 있다는 점이 운영상 의미다.
- **공유 접두사가 많은 워크로드에서의 스케줄링 선택**: 같은 앞부분을 가진 요청이 많으면 SGLang 문서는 가장 긴 접두사 일치(lpm) 정책을 시도해 보라고 안내한다. 캐시 적중을 늘리는 대신 스케줄링 오버헤드가 커진다고 함께 명시되어 있어, 도입 전 전후 비교가 필요하다.
- **오프라인 배치 추론의 메모리·대기열 점검 지표**: SGLang 튜닝 문서는 서버 로그의 토큰 사용률(KV 캐시 메모리 사용률)이 0.9를 넘으면 활용이 좋은 편이라고 본다. 대기 요청 수(#queue-req)가 0이 자주 보이면 클라이언트가 요청을 너무 천천히 넣는 신호일 수 있다고 설명하며, 이는 문서가 다루는 오프라인 배치 조건의 해석이다.
- **에이전트·사고 연쇄·few-shot 같은 다단계 호출의 대표 사용처**: NVIDIA 릴리스 노트는 복잡한 에이전트, 사고 연쇄(chain-of-thought) 추론, few-shot 프롬프팅 전략을 대표 사용처로 꼽는다. 모델 호출이 여러 번 이어지는 서비스가 검토 대상이 된다는 뜻이다.
- **엔진 간 벤치마크 비교의 오용 주의**: 한 해설 글은 SGLang v0.2.3과 vLLM 0.11.0처럼 약 2년 차이 나는 버전을 맞붙인 사례를 지적하며, 같은 시기 릴리스와 같은 플래그인지 확인하라고 말한다. GPU 메모리 사용률을 0.95로 두면 죽고 0.8에서는 돌았다는 사례도 엔진 자체가 아니라 튜닝 조건의 차이로 봐야 한다고 한다.

## 자주 하는 오해
- ❌ 오해: SGLang을 쓰면 어떤 요청이든 빨라진다 → ✅ 실제: 캐시 이득은 공통 앞부분이 있고, 그 캐시가 GPU 메모리에 남아 있어 재사용될 수 있을 때만 생긴다. 공유 앞부분이 거의 없거나 KV 캐시 풀이 가득 차 요청을 되돌리는 경고가 자주 뜨는 상황에서는 이득이 줄어든다.
- ❌ 오해: SGLang은 프로그래밍 언어일 뿐이거나, 반대로 서버 프로그램일 뿐이다 → ✅ 실제: 파이썬에 내장되는 프론트엔드 언어와 백엔드 런타임이 한 이름 아래 결합된 시스템이다. 서버를 띄워 HTTP로 요청을 보내는 사용과, 프로그램을 작성하는 프론트엔드 사용은 구분해서 봐야 한다.
- ❌ 오해: 프리픽스 캐싱은 SGLang만의 기능이라 항상 vLLM보다 빠르다 → ✅ 실제: vLLM도 프리픽스 캐싱을 사용하고, 두 엔진 모두 블록 할당과 접두사 보관 구조를 갖는다. 순위는 버전, 청크 프리필 크기 같은 설정, 워크로드에 따라 바뀌므로 하나의 수치로 결론 내릴 수 없다.

## 대화에서는 이렇게
- "프리픽스 캐시 **적중률**만 올라갔다고 좋아하지 말고 **TTFT**랑 처리량도 같이 뽑아서 전후 비교해 보죠. 적중률은 오르는데 TTFT가 그대로면 병목이 다른 데 있을 수 있어요."
- "**bench_serving**으로 동시성별로 돌릴게요. num-prompts는 최대 동시성의 5배 이상으로 맞춰서 **TTFT, TPOT**까지 같이 기록하겠습니다."
- "로그에 **#queue-req**가 계속 0이에요. 오프라인 배치 기준으로는 클라이언트가 요청을 천천히 넣는다는 신호일 수 있는데, 우리는 온라인 서비스라 부하 패턴 기준으로 다시 해석해야 해요."
- "**token usage**가 높다고 바로 안심하긴 일러요. 우리 p99 지연 목표를 먼저 보고, **--mem-fraction-static** 같은 튜닝 값은 쓰는 버전 문서를 확인한 다음 조금씩 바꿔 가며 OOM 여부를 보죠."
- "시스템 프롬프트가 긴 서비스라면 **lpm** 스케줄링 정책을 시험해 볼 만해요. 대신 스케줄링 오버헤드가 늘 수 있으니 같은 버전, 같은 트래픽으로 전후를 꼭 비교합시다."

## 함께 읽으면 좋은 용어
- (기초) **KV 캐시** — 모델이 이미 읽은 토큰에 대해 만들어 둔 중간 기록으로, 이것을 먼저 이해해야 SGLang이 무엇을 재사용하는지 보인다.
- (유사) **vLLM** — 같은 범주의 LLM 추론 엔진이며 프리픽스 캐싱도 사용한다. 비교할 때는 버전과 설정을 맞추는 법부터 같이 익히면 좋다.
- (유사) **TensorRT-LLM** — SGLang 벤치마크 재현 문서에서 비교 대상으로 등장하는 또 다른 추론 백엔드로, 엔진 선택지의 폭을 가늠하는 데 쓴다.
- (심화) **RadixAttention** — SGLang이 캐시를 보관하고 찾는 방식 자체를 다룬다. 이 문서를 읽은 뒤 캐시 재사용이 어떻게 이뤄지는지 파고들 때 읽는다.
- (심화) **텐서 병렬화** — (Tensor Parallelism) — 모델 연산을 여러 GPU에 나눠 실행하는 방식이다. SGLang의 tp-size 옵션과 이어지고 데이터 병렬과의 처리량 트레이드오프로 넘어가기 좋다.
- (심화) **Prefill-Decode 분리** — (PD Disaggregation) — 입력을 읽는 단계와 토큰을 생성하는 단계를 서로 다른 워커로 나누는 서빙 방식이다. SGLang 프로파일링 문서에서 별도 모드로 다룬다.

## body_advanced_en

## Technical Definition & How It Works
SGLang is an open-source LLM serving runtime (Apache 2.0, per one secondary guide) paired with a Python-embedded frontend language for multi-step generation programs. Its central idea is retaining KV-cache state across requests that share a prompt prefix, using a radix-tree index (RadixAttention), and pairing that cache with a scheduler policy that can reorder queued requests to raise hit rates. It runs as an HTTP server (`sglang.launch_server`) or in-process through an `Engine` object.

**Supported by the reference materials (interface and operational facts):**
- A request reaches the scheduler either through the HTTP server or directly via `Engine.generate()`. The benchmark docs expose these layers separately: `bench_serving` and `bench_one_batch_server` go through HTTP and the scheduler, `bench_offline_throughput` skips HTTP, and `bench_one_batch` calls `ModelRunner.extend()/decode()` and bypasses the scheduler.
- GPU memory is partitioned as model weights + KV cache pool + CUDA graph buffers + activations. `--mem-fraction-static` covers the first two terms only.
- Prefill can be chunked (`--chunked-prefill-size`). Decode batches are capped by `--max-running-requests`. CUDA graphs are enabled by default only for small batch sizes.
- When the KV pool is exhausted, the server logs `KV cache pool is full. Retract requests` along with a `#new_token_ratio` value. `--schedule-conservativeness` shifts how aggressively new requests are admitted.
- `--schedule-policy lpm` (longest prefix match) reorders requests to encourage cache hits and, per the docs, adds scheduling overhead.
- Prefill and decode can be disaggregated into separate workers behind a router. Profiling the two must be done separately.

**Not verified by the provided references (treat as unknown):** radix-tree node granularity, eviction policy, reference counting or pinning of in-use cache entries, how `lpm` computes and caches match lengths, and any starvation guard for low-match requests. The sources also describe RadixAttention differently. NVIDIA's release notes call it a GPU kernel that manages the KV cache, while a comparison article describes it as radix-tree indexing for retention across requests. Neither description is a specification of internals, so read the SGLang paper or source before depending on specific behavior.

**Control flow (as far as documented):**
1. A client program or HTTP request submits a prompt.
2. The scheduler queues it. With `lpm`, queue order may change based on prefix overlap with cached state.
3. The runtime looks up reusable cached state for the prompt prefix. How it does so is not detailed in the references.
4. The unmatched tail is prefilled (possibly in chunks), then decode steps run in batches.
5. Under KV pressure, requests are retracted and re-queued. Admission aggressiveness follows `--schedule-conservativeness`.

**Complexity:** no asymptotic bounds for lookup or scheduling are published in the provided references. The only documented cost statement is qualitative (`lpm` adds scheduling overhead).

## Key Hardware and Runtime Specs
- **Parameters**: not_published (SGLang is a serving runtime, not a model; parameter counts depend on the model being served)
- **Context window**: not_published (model- and deployment-dependent; one doc log sample shows context_len=65536 for a single sample deployment, which is not a product limit)
- **Training data**: not_published (not applicable to a serving runtime)
- **Latency / throughput**: not_published as a general figure; one doc log sample shows 'gen throughput (token/s): 4594.01' with 233 running requests, 1 sample, hardware not stated, and is illustrative only
- **Benchmarks**:
  - sgl-project/sglang PR #44493 (FLUX.3 diffusion serving), base NVFP4: +8.88% text-to-image, +7.84% image-to-image (metric not stated in the available excerpt) — A serving-change comparison under the PR's stated precision and workload settings, not a demonstrated NVFP4-versus-BF16 speedup. The PR text says it 'does not make FP8R/NVFP4 lossless relative to BF16'. Reported over a limited sample: 24 version-paired PNGs matched pixel-for-pixel and per-server peak allocated memory was unchanged in all 12 workload rows. Do not generalize to other models or hardware.
  - sgl-project/sglang PR #44493 (FLUX.3 diffusion serving), distilled NVFP4 text-to-image: -4.05% (regression) — Same PR and same limited-sample caveat. The distilled configuration regressed in this sample, so the effect varies by configuration.

## Formulas, Architecture, and Diagrams
SGLang's documented memory model has one standard relationship worth writing down. Let $W$ be model weights, $$C_{KV}$$ the KV cache pool, $$B_{graph}$$ the CUDA graph buffers, $$A_{act}$$ activations, and $$M_{GPU}$$ GPU memory capacity.

$$M_{used} = W + C_{KV} + B_{graph} + A_{act}$$

$$f_{static} = \frac{W + C_{KV}}{M_{GPU}}$$

Here $$f_{static}$$ is the value set by `--mem-fraction-static`. Raising it grows the KV pool but leaves less headroom for $$A_{act}$$ and $$B_{graph}$$.

**Tuning reference:** the table follows the SGLang Hyperparameter Tuning documentation. The middle column is what you observe in logs. The right column is the doc's suggested interpretation or change, which is a hypothesis to validate with an A/B run, not a guaranteed fix.

| Observed symptom (log signal) | Hypothesis / doc-suggested change |
|---|---|
| `#queue-req` frequently 0 under load | Client may be submitting too slowly. The doc cites 100-2000 as a healthy `#queue-req` range, with larger queues adding scheduling overhead. |
| `token usage` below 0.9 while `#queue-req` > 0 | Server may be too conservative. Consider lowering `--schedule-conservativeness` (doc example: 0.3). Likely when `max_new_tokens` is large but requests stop early on EOS or stop strings. |
| Frequent `KV cache pool is full. Retract requests` | KV pool pressure. Consider raising `--schedule-conservativeness` (doc example: 1.3). The doc treats roughly one occurrence per minute as acceptable. |
| `available_gpu_mem` in the startup log outside 5-8 GB | Above range (doc example: 10-20 GB): headroom is likely unused, so consider raising `--mem-fraction-static`. Below range: OOM risk, so consider lowering it. |
| OOM during prefill | Consider reducing `--chunked-prefill-size` (doc examples: 4096 or 2048). Long-prompt prefill gets slower. |
| OOM during decode | Consider lowering `--max-running-requests`. |
| Many requests share long prefixes | Consider `--schedule-policy lpm`. The doc notes more scheduling overhead. |

**Benchmark tool layers (use the matching layer for the question):**

| Tool | HTTP server | Scheduler | Suited for |
|---|---|---|---|
| `bench_serving` | yes | yes (via server) | Online serving latency (TTFT, TPOT, ITL) and throughput. The doc's default choice. |
| `bench_one_batch_server` | yes | yes (via server) | Single-batch end-to-end latency. Server never reaches steady state, so metrics are biased. |
| `bench_offline_throughput` | no | yes (in-process `Engine`) | Maximum throughput without HTTP overhead |
| `bench_one_batch` | no | no (`ModelRunner` direct) | Kernel-level profiling of one static batch. May OOM at batch sizes a real server handles via chunked prefill. |

## Code or Pseudocode
```python
# PSEUDOCODE: TOY model of prefix matching + capacity-checked admission.
# NOT SGLang's implementation. It illustrates the contract only:
# reuse is valid only while every cached-state reference along the matched path is still valid.
# Out of scope: eviction policy, pinning/refcounts for running requests, paging,
# max_new_tokens/decode growth, and double-counting of prefixes shared inside one admitted batch.
from dataclasses import dataclass, field

@dataclass
class Node:
    kv_valid: bool = False                      # cached-state entry exists and is not evicted
    children: dict[int, 'Node'] = field(default_factory=dict)

def insert(root: Node, tokens: list[int]) -> None:
    node = root
    for t in tokens:
        node = node.children.setdefault(t, Node())
        node.kv_valid = True

def evict(root: Node, tokens: list[int]) -> None:
    node = root
    for t in tokens:
        node = node.children[t]
    node.kv_valid = False                       # descendants become unreachable for reuse

def matched_len(root: Node, tokens: list[int]) -> int:
    node, n = root, 0
    for t in tokens:
        child = node.children.get(t)
        if child is None or not child.kv_valid:  # stop at first miss OR invalid reference
            break
        node, n = child, n + 1
    return n

def schedule(root: Node, queue: list[tuple[int, list[int]]], free_tokens: int):
    # queue: (arrival_index, prompt_tokens). Longest match first; ties keep arrival order.
    ranked = sorted(queue, key=lambda r: (-matched_len(root, r[1]), r[0]))
    admitted: list[int] = []
    deferred: list[int] = []
    for arrival, prompt in ranked:
        need = len(prompt) - matched_len(root, prompt)   # only the unmatched tail costs new KV
        if need <= free_tokens:
            free_tokens -= need
            admitted.append(arrival)
        else:
            deferred.append(arrival)                      # insufficient capacity: stays queued
    return admitted, deferred

def make_root() -> Node:
    root = Node()
    insert(root, [1, 2, 3, 4])
    return root

# --- toy tests ---
assert matched_len(make_root(), [9, 9]) == 0                      # miss
assert matched_len(make_root(), [1, 2, 7, 8]) == 2                # partial match
r = make_root(); evict(r, [1, 2, 3])
assert matched_len(r, [1, 2, 3, 4, 5]) == 2                       # evicted node cuts reuse
assert schedule(make_root(), [(0, [5, 6]), (1, [7, 8])], 10) == ([0, 1], [])   # tie: arrival order
assert schedule(make_root(), [(0, [9]), (1, [1, 2, 3, 4, 5])], 10) == ([1, 0], [])  # longer match first
assert schedule(make_root(), [(0, [1, 2, 3, 4, 5])], 1) == ([0], [])  # only 1 tail token needed
assert schedule(make_root(), [(0, [9, 9, 9])], 1) == ([], [0])         # insufficient capacity: deferred
```

## Production Pitfalls
- ❌ Mistake: Quoting a published head-to-head (for example a 29% throughput gap between SGLang v0.2.3 and vLLM 0.11.0, releases roughly two years apart) as the basis for an engine decision → ✅ Fix: Write the benchmark contract first (hardware, model, precision, workloads, metrics), use contemporaneous releases with matched flags, and re-measure on your own traffic.
- ❌ Mistake: Reporting TTFT or throughput from `bench_one_batch_server`, which sends one batch so the server never reaches steady state and the metrics are biased → ✅ Fix: Use `bench_serving` with `num-prompts >= 5 * max-concurrency`. If you must use multi-batch mode, treat only `overall_throughput` as authoritative, since the other fields include cross-batch queueing.
- ❌ Mistake: Pushing the memory fraction up without checking headroom (one published comparison notes GPU memory utilization 0.95 crashed while 0.8 worked) → ✅ Fix: Read `available_gpu_mem` in the startup log (doc target 5-8 GB), raise `--mem-fraction-static` in small steps such as 0.01 until OOM, then back off. Fix prefill OOM with a smaller `--chunked-prefill-size` and decode OOM with a lower `--max-running-requests`.
- ❌ Mistake: Reusing A100 (sm_80) measurements when the target model's SGLang kernels (for GLM-5, the DSA kernels) are gated to sm_90 / sm_100 → ✅ Fix: Rerun the comparison on H100 or H200 (sm_90) or newer. Record the GPU architecture in the benchmark contract so stale evidence is rejected in review.

## Tradeoffs — When to Use What
**Suitable:**
- Agent or tool-loop traffic where each step extends the same growing context. Shared prefixes are the case the radix-tree cache and the `lpm` policy were designed around, and the reuse saves prefill work on the matched portion.
- Few-shot or long-system-prompt workloads where many requests begin with identical text. Only the unmatched tail needs new KV memory, which also raises achievable concurrency for a given KV pool.
- Branching generation programs (chain-of-thought with multiple candidates) where branches share a prefix and can use the frontend language's loops and conditionals.
- NVIDIA-container or mixed-vendor fleets. The references show an NVIDIA container released monthly and GLM-5 serving on H100, H200, B200, and MI300-class GPUs, which lowers build and portability cost.

**Unsuitable:**
- Traffic where prompts share little or no prefix. The cache yields little reuse, and `lpm` adds scheduling overhead for no gain. Pick the engine on other criteria and measure with `bench_serving` against vLLM.
- A100 (sm_80) deployments of GLM-5. The comparison issue states the DSA kernels are gated to sm_90 / sm_100 and the cookbook does not list A100. Use H100/H200, or evaluate another engine such as vLLM for that model.
- Strict per-request isolation of cached state. vLLM documents optional per-request salts that restrict reuse to requests with the same salt. The provided references show no SGLang equivalent, so verify before assuming one exists. Until then, vLLM is the documented choice for this requirement.
- Decisions made from a single published leaderboard delta. A reported 29% gap paired SGLang v0.2.3 with vLLM 0.11.0, releases roughly two years apart. Re-measure with contemporaneous releases and matched flags on your own workload.

## Industry Communication
- (hypothetical review comment on the GLM-5 comparison) "Please fix the **benchmark contract** (**hardware, model, precision, workloads, metrics**) before any run. SGLang's **DSA kernels** (**FlashMLA sparse, DeepGEMM indexer, trtllm**) are gated to **sm_90 / sm_100** and its cookbook doesn't list **A100**, so our **sm_80** evidence can't be reused and the comparison runs on **H100 or H200** (sm_90)."
- (hypothetical PR review on a FLUX.3 serving change) "The PR reports a **serving-change comparison** with **24 version-paired PNGs matching pixel-for-pixel**, but it states this does **not make FP8R/NVFP4 lossless relative to BF16**, and the **distilled NVFP4 text-to-image regression of 4.05%** shows the effect varies by configuration. Please don't cite the gains as a general speedup."
- (hypothetical design-doc excerpt) "We'll enable **`--schedule-policy lpm`** on the agent tier only after measuring prefix overlap in our traces. The docs flag **extra scheduling overhead**, so the A/B must include queue-time metrics, not just throughput."
- (hypothetical incident postmortem) "The **'KV cache pool is full. Retract requests'** warning became frequent after we raised concurrency. We adjusted **`--schedule-conservativeness`** per the tuning docs and rechecked **token usage**. We have **not** established retraction as the root cause of the latency regression; we need per-request traces first."
- (hypothetical review comment on a benchmark script) "This used **`bench_one_batch_server`** with a single batch, so the server never reached steady state and **TTFT is biased**. Rerun with **`bench_serving`** at **`num-prompts` >= 5x `max-concurrency`** and attach the exact launch flags."
- (hypothetical OOM triage note) "Prefill OOM: reduce **`--chunked-prefill-size`** and accept slower long-prompt prefill. Decode OOM: lower **`--max-running-requests`**. Record the pre- and post-change **`available_gpu_mem`** in the change ticket."
- (hypothetical design-doc open question) "We have no verified documentation on **radix-tree eviction behavior** for our pinned version. Before promising a **cache-hit-rate SLO**, we'll read the SGLang paper and source and add tests against our own traffic."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **KV cache and prefill/decode phases** — RadixAttention retains per-token KV state across requests and `--chunked-prefill-size` splits the prefill phase, so both concepts must be clear first. The provided references do not document memory layout or eviction details; the SGLang paper or source would be needed for that.
- (alternative) **vLLM** — Competing serving engine that also reuses shared prefixes (prefix caching) and adds optional per-request salts for reuse isolation. References describe the two as having leapfrogged each other, so comparison needs matched versions and flags.
- (alternative) **TensorRT-LLM** — Appears in SGLang's benchmark reproduction scripts as a comparison backend. The references give configuration for it but no capability analysis, so deeper comparison would need its own documentation.
- (extension) **Prefill/decode (PD) disaggregation** — SGLang documents launching prefill and decode workers separately behind a router, with profiling done per worker type. Sizing and routing guidance is not covered in the provided references.
- (extension) **SGLang Model Gateway** — (former Router) — The tuning docs recommend it over the `dp_size` parameter for data parallelism. The provided references say little beyond that, so its behavior needs its own documentation.

## body_advanced_ko

## 기술적 정의와 동작 원리
SGLang은 서빙 런타임과 Python 내장 프론트엔드 언어로 구성된 LLM 실행 시스템이다. 런타임 쪽에는 요청 대기열과 배치를 관리하는 스케줄러, 모델 순전파를 실행하는 `ModelRunner`, 이를 in-process로 감싼 `Engine`, HTTP 서버 진입점이 있다. KV 캐시는 RadixAttention의 radix tree로 색인되어 프리픽스가 겹치는 요청 사이에서 재사용된다. 이 구조에서 성능을 가르는 요소는 모델 연산 자체보다 캐시 적중, 배치 크기, GPU 메모리 분할이다.

데이터/제어 흐름은 다음과 같다.

- **진입 경로 두 가지**: `sglang.launch_server`로 띄운 HTTP 서버를 거치거나, `Engine.generate()`를 in-process로 호출한다. 후자는 HTTP 오버헤드가 없고, 스케줄러가 배치와 실행을 담당한다.
- **스케줄링 정책**: 대기열(`#queue-req`)의 요청 순서는 정책이 정한다. `--schedule-policy lpm`(longest prefix match)은 캐시 적중이 늘도록 요청을 재배열하며, 그 대가로 스케줄링 오버헤드가 늘어난다.
- **프리픽스 매칭**: 새 요청의 토큰열을 radix tree에서 매칭해 겹치는 구간의 KV를 재사용한다. 겹치지 않는 나머지만 prefill 하며, prefill은 `--chunked-prefill-size` 단위로 잘려 실행된다.
- **디코드 배치**: 실행 중 요청(`#running-req`)이 한 배치로 묶여 디코딩되고, 작은 배치 크기까지는 CUDA graph가 기본 적용된다.
- **KV 풀 압박 대응**: KV 캐시 풀이 가득 차면 `KV cache pool is full. Retract requests.` 경고와 함께 일부 요청이 회수(retract)된다. `--schedule-conservativeness`가 새 요청 수용의 보수성을 조절한다.
- **메모리 분할**: 총 사용량은 모델 가중치, KV 캐시 풀, CUDA graph 버퍼, 활성화(activations)의 합이다. `--mem-fraction-static`은 이 중 앞의 두 항목이 차지하는 비율을 정한다.

핵심 구성 단계는 다음과 같다.

1. 요청 수신 후 대기열 삽입
2. (선택) lpm 정책으로 재정렬
3. radix tree 프리픽스 매칭으로 재사용 구간 결정
4. 비재사용 구간을 청크 단위로 prefill
5. 디코드 배치 편성 및 CUDA graph 경로 선택
6. KV 풀 포화 시 retract

PD disaggregation 모드에서는 `--disaggregation-mode prefill`과 `decode` 서버를 따로 띄우고 router 뒤에 둔다. 이때 torch profiler 제약 때문에 prefill 워커와 decode 워커를 따로 프로파일해야 한다.

radix tree의 탐색·삽입·축출 복잡도(Big O)와 축출 정책의 세부 알고리즘은 제공된 참고 자료에 없으므로, 해당 주제에 대한 검증된 정보가 부족합니다. 또한 이 참고 자료 묶음에는 SGLang 자체의 벤치마크 점수가 없다. 그래서 specs의 benchmarks는 빈 배열로 두었고, 수치 비교는 아래 도구로 직접 측정해야 한다.

## 핵심 수식·아키텍처·도표
메모리 분할은 문서에 적힌 정의를 그대로 식으로 쓰면 다음과 같다.

$$\text{mem\_fraction\_static} = \frac{W_{\text{weights}} + M_{\text{KV pool}}}{M_{\text{GPU}}}$$

여기서 $$W_{\text{weights}}$$는 모델 가중치, $$M_{\text{KV pool}}$$은 KV 캐시 풀, $$M_{\text{GPU}}$$는 GPU 메모리 용량이다. 나머지(CUDA graph 버퍼와 활성화)는 이 비율 바깥에 남는다.

아래 표는 첫 세 행이 문서에서 확인된 사실이고, 마지막 열은 작성자가 별도로 붙인 실험상 주의사항(가설 포함)이다. 네 번째 행은 근거 자료가 없어 비워 둔다.

| 항목 | 확인된 사실 (문서·이슈 기록) | 작성자의 실험상 주의 (미검증 가설 포함) |
|---|---|---|
| 메모리 모델 | 총 사용량 = 가중치 + KV 풀 + CUDA graph 버퍼 + 활성화. 서버 기동 직전 로그의 `available_gpu_mem`을 보라고 안내하며, 활성화 여유 5–8GB를 rule of thumb으로 제시한다. | 5–8GB는 일반 경험칙이다. 모델·배치·청크 크기가 바뀌면 같은 여유가 맞는다는 보장이 없으므로 대상 구성에서 재확인한다. |
| 오프라인 배치 처리량 | 풀 로드 정상 상태에서 `token usage`가 0.9보다 높으면 활용이 좋은 것으로 본다. `#queue-req`는 100–2000 범위를 건강하다고 서술하고, 항상 0이면 클라이언트 제출이 느린 것으로 본다. | 이 값들은 오프라인 배치 추론 맥락의 서술이다. 지연 목표가 있는 온라인 서빙에 그대로 옮기면 TTFT가 악화될 수 있다는 것은 가설이며 측정이 필요하다. |
| 지연·처리량 측정 | `bench_serving`이 TTFT, TPOT, ITL, 처리량을 측정하며 기본 선택지로 안내된다. 정상 상태 측정에는 `num-prompts >= 5 * max-concurrency`를 쓴다. 단일 배치 도구(`bench_one_batch_server`, `bench_one_batch`)는 정상 상태가 아니거나 스케줄러를 우회해 수치가 실제 서빙과 다르다. | 문서 예시 명령(`max-concurrency 16`, `num-prompts 80`)은 5배 조건의 경계값이다. 측정 구간이 짧아 보이면 `num-prompts`를 늘려 재측정한다. |
| GPU 아키텍처별 지원 범위 | 해당 주제에 대한 검증된 정보가 부족합니다. GLM-5의 DSA 커널이 sm_90/sm_100으로 게이트되어 있다는 이슈 기록 한 건만 확인되며, 이를 모델·커널 전반의 지원 매트릭스로 일반화할 근거는 없다. | 해당 없음 (자료 부족) |

증상별로 문서가 제시하는 조정 노브는 다음과 같다.

- **prefill 중 OOM**: `--chunked-prefill-size`를 4096 또는 2048로 낮춘다. 메모리는 절약되지만 긴 프롬프트의 prefill이 느려진다.
- **디코드 중 OOM**: `--max-running-requests`를 낮춘다.
- **양쪽 모두 OOM**: `--mem-fraction-static`을 0.8 또는 0.7 정도로 낮춘다. 최대 동시성과 피크 처리량이 줄어드는 대가가 따른다.
- **`token usage`가 낮은데 대기열이 있음**: `--schedule-conservativeness`를 낮춘다(문서 예시 0.3). 반대로 retract 경고가 잦으면 높인다(문서 예시 1.3). 분당 1회 안팎의 retract는 괜찮다고 서술한다.

## 코드 또는 의사코드
```python
# [의사코드 / 설계 스케치] 그대로 실행되지 않는다.
# measure()는 사용자가 구현하는 훅이다: 서버 재기동 + bench_serving 실행 + 로그 파싱을 한 호출로 묶는다.
# 임계값과 허용 범위는 전부 사용자 실험 파라미터이며, 코드에 기본값을 두지 않는다.
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Gate:
    max_retract_per_min: float   # retract 경고 허용 빈도
    max_p99_ttft_ms: float       # 지연 상한
    min_gain_ratio: float        # 채택에 필요한 최소 처리량 개선율

@dataclass(frozen=True)
class Metrics:
    throughput: float
    p99_ttft_ms: float
    retract_per_min: float
    oom: bool

Config = dict[str, float]

def tune_one_knob(
    base: Config,
    knob: str,
    candidates: list[float],
    allowed: dict[str, tuple[float, float]],
    measure: Callable[[Config], Metrics],
    gate: Gate,
) -> Config:
    # 1) 입력 검증: 허용 범위가 없는 노브, 범위 밖/중복/빈 후보는 측정 전에 거부
    if knob not in allowed:
        raise ValueError(f'허용 범위가 정의되지 않은 노브: {knob}')
    lo, hi = allowed[knob]
    if not candidates or len(set(candidates)) != len(candidates):
        raise ValueError('후보가 비었거나 중복됨')
    if any(not (lo <= v <= hi) for v in candidates):
        raise ValueError('후보가 허용 범위를 벗어남')

    def passes(m: Metrics, ref: Metrics) -> bool:
        return (not m.oom
                and m.retract_per_min <= gate.max_retract_per_min
                and m.p99_ttft_ms <= gate.max_p99_ttft_ms
                and m.throughput >= ref.throughput * (1 + gate.min_gain_ratio))

    base_m = measure(base)
    if base_m.oom:
        raise RuntimeError('baseline이 이미 OOM: 노브 탐색 전에 설정부터 복구')

    best_cfg, best_m = base, base_m
    for v in sorted(candidates):
        trial = {**base, knob: v}          # 2) 한 번에 노브 하나만 변경
        m = measure(trial)
        if m.oom:                          # 실패 경로 1: OOM -> 후보 폐기, best 유지
            continue
        if (m.retract_per_min > gate.max_retract_per_min
                or m.p99_ttft_ms > gate.max_p99_ttft_ms):
            continue                       # 실패 경로 2: 처리량이 올라도 retract/지연 게이트 위반이면 폐기
        if passes(m, best_m):
            best_cfg, best_m = trial, m

    if best_cfg is base:
        return base
    confirm = measure(best_cfg)            # 3) 우승 설정 재측정 (단발 측정 노이즈 방어)
    return best_cfg if passes(confirm, base_m) else base   # 4) 재측정 실패 시 롤백

# --- 합성 측정기로 계약만 확인하는 테스트 (수치는 전부 가짜) ---
def fake_measure(cfg: Config) -> Metrics:
    f = cfg['mem_fraction_static']
    return Metrics(throughput=f * 100, p99_ttft_ms=1.0, retract_per_min=0.0, oom=f > 0.9)

gate = Gate(max_retract_per_min=1.0, max_p99_ttft_ms=10.0, min_gain_ratio=0.01)
allowed = {'mem_fraction_static': (0.5, 0.99)}
base = {'mem_fraction_static': 0.8}

out = tune_one_knob(base, 'mem_fraction_static', [0.85, 0.95], allowed, fake_measure, gate)
assert out['mem_fraction_static'] == 0.85          # 0.95는 OOM으로 폐기
try:
    tune_one_knob(base, 'mem_fraction_static', [1.2], allowed, fake_measure, gate)
    raise AssertionError('범위 밖 후보가 통과함')
except ValueError:
    pass
```

## 프로덕션 함정
- ❌ 실수: SGLang v0.2.3과 vLLM 0.11.0처럼 릴리스가 약 2년 벌어진 조합의 29% 처리량 격차를 현재 엔진 우열의 근거로 인용한다 → ✅ 해결: 비교 PR에는 엔진 버전, 플래그, GPU 아키텍처, 정밀도, 워크로드, 지표를 고정한 표를 첨부한다. 비교는 동시대 릴리스와 동일 플래그 조건에서 자기 워크로드로 재측정한 수치만 근거로 쓴다.
- ❌ 실수: GPU 메모리 사용률을 0.95로 올렸더니 크래시가 났는데 이를 엔진의 결함으로 기록한다(같은 글에서 0.8은 정상 동작) → ✅ 해결: 튜닝 아티팩트와 엔진 속성을 분리한다. `--mem-fraction-static`은 0.01 단위로 올리며 OOM 직전 값을 찾고, 서버 기동 직전 로그의 `available_gpu_mem`으로 활성화 여유가 남는지 확인한다.
- ❌ 실수: SGLang 저장소의 FLUX.3 PR #44493에서 본 FP8R/NVFP4 속도 향상을 모든 모델·정밀도에 적용 가능한 일반 법칙으로 받아들인다 → ✅ 해결: 이 PR의 측정은 24개 PNG 쌍과 12개 workload row라는 해당 샘플 한정이다. 거기서도 base NVFP4는 T2I +8.88%, I2I +7.84%였지만 distilled NVFP4의 T2I는 −4.05%였고, BF16 대비 무손실도 아니라고 명시한다. 정밀도 설정은 모델 변종마다 A/B로 재측정하고 출력 품질 비교도 함께 한다.
- ❌ 실수: `bench_one_batch`나 `bench_one_batch_server`의 단일 배치 수치를 서빙 성능으로 보고한다 → ✅ 해결: 두 도구는 각각 스케줄러를 우회하거나 정상 상태가 아닌 단일 배치만 보내 수치가 편향된다고 문서가 밝힌다. 기본은 `bench_serving`으로 하고, `num-prompts >= 5 * max-concurrency`를 지켜 정상 상태를 확보한다. 단일 배치 도구는 커널 수준 프로파일링에만 쓴다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**

- **공유 프리픽스가 큰 에이전트·few-shot 트래픽**: 앞부분이 겹치는 요청은 그 구간의 prefill을 radix tree 매칭으로 건너뛴다. 문서도 공유 프리픽스가 많으면 `--schedule-policy lpm`을 시도해 보라고 안내한다.
- **분기·반복이 섞인 다단계 생성 프로그램**: 갈래들이 앞부분 KV를 공유해 중복 prefill이 줄고, 프론트엔드 언어가 이 구조를 Python 코드로 표현해 준다.
- **오프라인 배치 추론의 로그 기반 튜닝**: `token usage`, `#queue-req`, `available_gpu_mem`이 로그로 노출되어 병목을 수치로 좁힐 수 있다. 다만 이 가이드는 오프라인 배치 맥락이다.
- **H100/H200/B200/MI300 계열에서 GLM-5 서빙** (이슈 기록 범위): 이슈 기록은 이 GPU들에서 SGLang이 GLM-5를 서빙한다고 적는다. 이 항목의 근거 범위는 해당 모델 한 건이며, 다른 모델의 지원 범위로 확장할 수 없다.

**이럴 때 부적합**

- **요청 프롬프트가 거의 겹치지 않는 트래픽**: 캐시 재사용으로 건너뛸 구간이 없어 이득이 작다. 이 경우 SGLang을 고집할 이유가 약하므로 **vLLM** 등과 동일 버전·플래그 조건에서 직접 비교한다.
- **요청별 캐시 재사용 범위를 격리해야 하는 멀티테넌트**: **vLLM**은 요청별 salt로 재사용 범위를 제한하는 옵션을 문서화한다. SGLang의 동등 기능 유무는 제공된 자료에 없어 검증된 정보가 부족합니다. 격리 요건이 하드하면 vLLM을 먼저 검토한다.
- **엄격한 p99 TTFT 목표가 걸린 온라인 서비스에서 lpm 재배열을 무비판적으로 켜는 경우**: 문서는 lpm이 스케줄링 오버헤드를 늘린다고 밝힌다. 대기 요청이 밀릴 가능성은 작성자의 가설이므로, 기본 정책과 `bench_serving`으로 TTFT 분포를 비교한 뒤 결정한다. 대안은 기본 스케줄 정책 유지다.
- **A100(sm_80)에서 GLM-5의 DSA 커널 경로를 쓰려는 경우**: 이슈 기록상 해당 커널(FlashMLA sparse, DeepGEMM indexer, trtllm)은 sm_90/sm_100으로 게이트되고 cookbook에 A100이 없다. 이는 GLM-5 DSA 경로에 한정된 기록이며 A100 전반의 지원 여부와는 별개다. 반면 v0.2.7 시점 벤치마크 README는 Llama 계열 8B/70B를 A100 80GB로 재현하도록 기술한다. 현재 버전에서의 A100 지원 범위는 자료가 부족하다. GLM-5 비교가 목적이면 H100/H200(sm_90)에서 진행하는 것이 이슈의 결론이다.

## 업계 대화 맥락
- "이 PR의 `--mem-fraction-static` 변경은 근거 로그가 없습니다. 서버 기동 직전의 **available_gpu_mem**을 첨부해 주세요. 문서의 활성화 여유 5–8GB는 일반 rule of thumb이라, 이 모델·배치 구성에도 맞는지는 재측정이 필요합니다."
- "**lpm** 정책 도입 가설은 공유 프리픽스 비율이 높을 때 캐시 적중이 늘어 처리량이 오른다는 것입니다. 문서가 스케줄링 오버헤드 증가를 명시하므로, 기본 정책과 **p99 TTFT** 분포를 같은 부하에서 비교한 결과를 같이 올려 주세요."
- "벤치마크가 **bench_serving**으로 측정된 건가요? 문서상 정상 상태 조건은 `num-prompts >= 5 * max-concurrency`입니다. 현재 80/16은 그 경계값이라 측정 구간이 짧을 수 있어서, `num-prompts`를 늘려 재실행한 값을 요청드립니다."
- "FLUX.3 PR #44493의 base NVFP4 T2I +8.88%, distilled NVFP4 T2I −4.05%는 그 PR의 측정 샘플 한정 수치입니다. 우리 모델·GPU에서 같은 방향이라고 가정하지 말고 변종별 A/B 결과를 첨부해 주세요."
- "기존 하드웨어 증거가 전부 **sm_80**(A100)이라는 점이 문제입니다. 이슈 기록상 GLM-5의 DSA 커널은 sm_90/sm_100으로 게이트되어 있어, 이 비교는 H100/H200(sm_90)에서 다시 돌리는 방향을 제안합니다. 다른 모델 경로의 A100 지원은 별도로 확인이 필요합니다."
- "**KV cache pool is full. Retract requests.** 경고의 분당 빈도를 로그에서 집계해 주세요. 문서는 분당 1회 안팎이면 괜찮다고 서술합니다. 빈번하다면 `--schedule-conservativeness` 상향이 원인을 줄이는지 한 번에 하나씩 변경하며 검증해 봅시다."
- "PD disaggregation 프로파일링은 **--profile-prefill-url**과 **--profile-decode-url**이 상호 배타라서 두 번에 나눠 실행해야 합니다. 두 트레이스를 각각 첨부해 주시고, 모든 워커 노드에 `SGLANG_TORCH_PROFILER_DIR`이 설정되어 있는지도 확인 부탁드립니다."

## 선행·대안·확장 개념
- (선행) **KV 캐시** — SGLang이 재사용하는 대상 자체이며 토큰별 중간 계산 결과를 저장한다. 풀 크기가 곧 동시성 한계이고 `--mem-fraction-static`이 이 풀의 용량을 좌우하므로, 메모리 모델을 읽기 전에 알아야 한다.
- (선행) **Prefill과 Decode 단계** — 프리픽스 재사용은 prefill 비용을 줄이는 기법이고 디코드는 배치 크기와 CUDA graph에 좌우된다. 청크 prefill, `bench_one_batch`의 단계 분리, PD disaggregation의 분리 기준이 모두 이 구분에서 나온다.
- (대안) **vLLM** — 같은 서빙 문제를 푸는 현재 시점의 경쟁 엔진으로, 프리픽스 캐싱을 지원하며 요청별 salt로 캐시 재사용 범위를 제한하는 옵션이 문서화되어 있다. 우열이 릴리스 시점과 플래그에 따라 뒤집혀 왔으므로 동시대 버전·동일 조건 비교가 전제다.
- (대안) **TensorRT-LLM** — SGLang 벤치마크 README가 비교 백엔드로 포함한 엔진이다. 해당 비교는 배치 크기 512, 최대 입력 길이 8192 같은 별도 준비 설정을 쓰는 것으로 기술되어 있어, 설정 비용과 비교 조건을 함께 따져야 하는 대안이다.
- (확장) **PD disaggregation** — prefill과 decode 워커를 분리해 띄우고 router로 묶는 SGLang의 배포 모드다. 두 단계의 병목 특성이 달라 따로 프로파일링해야 하며, 문서가 별도 프로파일 옵션을 제공한다.
- (확장) **SGLang Model Gateway** — (구 Router) — 문서가 `dp_size` 파라미터보다 나은 데이터 병렬 구성으로 안내하는 계층이다. 처리량 목적에서는 메모리가 충분할 때 데이터 병렬을 우선하라는 가이드와 연결된다.

## references_en

- {"title": "SGLang Release Notes (NVIDIA Docs)", "type": "docs", "url": "https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/index.html", "tier": "primary", "annotation": "Vendor description of SGLang, RadixAttention, intended use cases, and the monthly container release cadence."}
- {"title": "Benchmark and Profiling - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling", "tier": "primary", "annotation": "Official guide to the four benchmark tools and the TTFT, TPOT, and ITL metrics for measuring serving."}
- {"title": "Hyperparameter Tuning - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning", "tier": "primary", "annotation": "KV cache memory sizing, the lpm schedule policy, and OOM tuning knobs, straight from the project docs."}
- {"title": "benchmark/blog_v0_2/README.md (sgl-project/sglang)", "type": "code", "url": "https://github.com/sgl-project/sglang/blob/main/benchmark/blog_v0_2/README.md", "tier": "primary", "annotation": "Reproduction script for SGLang v0.2 benchmarks, showing the version, hardware, and flags pinned for each comparison."}
- {"title": "SGLang vs vLLM (2026): Which Is Best for Your Workload?", "type": "blog", "url": "https://tensormesh.ai/learn/vllm-vs-sglang", "tier": "secondary", "annotation": "Compares cache design and how chunked-prefill tuning can change a ranking on identical hardware."}
- {"title": "SGLang: The Complete Guide to High-Performance LLM Inference", "type": "blog", "url": "https://inference.net/content/sglang-complete-guide", "tier": "secondary", "annotation": "Beginner walkthrough of installation options, the name's meaning, and the Apache 2.0 licensing."}
- {"title": "vLLM vs SGLang: Performance, Features & Deployment Compared", "type": "blog", "url": "https://deepinfra.com/blog/vllm-vs-sglang", "tier": "secondary", "annotation": "Cautionary read on why mismatched versions and flags make head-to-head benchmark gaps unreliable."}
