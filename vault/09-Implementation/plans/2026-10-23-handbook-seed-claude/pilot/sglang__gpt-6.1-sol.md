# SGLang — gpt-6.1-sol

- advanced 66 / basic 73 / gate review_required / penalty 7 / $0.6279 / 833s

## definition_en

SGLang (Structured Generation Language) is an open-source system combining an LLM inference runtime with a Python-embedded language for structured generation, using RadixAttention to reuse computations for shared input prefixes and scheduling requests to reduce redundant work in multi-step generation programs.

## definition_ko

SGLang은 대규모 언어 모델의 추론 런타임과 Python 기반 구조화 생성 언어를 결합한 오픈소스 시스템으로, 공통 입력의 중간 계산을 재사용하는 RadixAttention과 요청 스케줄링을 통해 중복 계산을 줄이면서 조건 분기와 반복이 포함된 다단계 생성 작업을 실행한다.

## summary_en

SGLang is open-source software for running large language models and organizing multi-step text-generation tasks. One part runs the model and handles requests, while another lets developers describe generation steps in Python. It can reuse intermediate calculations when requests begin with the same text. Teams evaluate it to process their workloads efficiently, but results depend on hardware memory, software versions, and service settings.

## summary_ko

SGLang은 언어 모델이 답변을 만드는 작업을 효율적으로 실행하는 오픈소스 소프트웨어다. 여러 요청에서 같은 입력 앞부분의 계산을 재사용하고, 요청을 묶어 처리하는 방식을 조절한다. Python으로 조건에 따라 다음 단계가 달라지는 생성 작업도 표현할 수 있다. 모델을 직접 운영하는 팀이 검토할 수 있지만, 효과는 사용하는 모델과 장비, 요청 형태에 따라 달라지고 메모리 설정도 조정해야 한다.

## body_basic_en

## Plain Explanation
Serving many language-model requests creates two pressures: completing enough work and keeping waiting times acceptable. Each unfinished response also needs memory, alongside the model itself. SGLang addresses this execution problem, but adopting it still requires hardware capacity planning and tuning how requests run.

SGLang combines **two roles**, rather than supplying a new model. Its **runtime**, the software that executes model requests, groups and schedules requests—chooses what runs together and when. Its **Python-based structured-generation language** lets developers describe generation steps, including choices and repetition. Think of a workshop: the language provides the job instructions, and the runtime coordinates the machines.

Inside the runtime, a **KV cache** stores attention keys and values: intermediate numbers used when generating text. **Attention** is how the model relates different parts of the text to one another. **RadixAttention** organizes these stored calculations so requests with identical opening text can reuse the matching work instead of computing it again.

## Examples & Analogies
- **Repeated catalog instructions**: To evaluate SGLang, try product-description requests that begin with the same editorial guide but end with different item records. Compare them with otherwise similar requests whose openings differ, keeping the model and hardware unchanged. This tests whether shared-opening reuse helps your workload rather than assuming a particular speedup.
- **Conditional document review**: For a pilot, choose a workflow that first reviews a document and generates follow-up questions only when needed. Test both the follow-up and no-follow-up paths using a fixed SGLang release, and verify the required Python-language behavior before adoption. Treat this as a workflow evaluation, not a promise that every release exposes identical functionality.
- **Nightly archive summaries**: Evaluate a fixed collection of archive texts as a bulk job submitted together. Record completion time and peak memory under the chosen model and request limits. Use those measurements to judge whether that particular deployment can meet the overnight deadline.

## At a Glance
| | Online server test | Offline engine test |
|---|---|---|
| Request route | A client sends web requests to a running server | One program submits requests directly to the engine |
| Extra work included | Web-request handling and scheduling—choosing what runs next | Scheduling remains; web-request handling is removed |
| Workload conditions | Controlled arrival rate and number of simultaneous requests | A specified request set submitted together |
| Measurements | Waiting time for first output, gaps between output pieces, and text processed per second | Text processed per second for specified model, hardware, text lengths, and settings |
| Decision supported | Responsiveness of the deployed service under the tested load | Bulk-processing capacity under the tested configuration |

The two paths include different overheads, so an offline throughput measurement cannot substitute for an online service result.

## Where and Why It Matters
- **High-volume batch processing**: When sufficient device memory is available, SGLang's tuning guidance favors separate model copies handling different requests for throughput—the amount of work completed per second—rather than automatically splitting one model across more devices.
- **Long-input services**: Processing an input in smaller chunks can reduce memory pressure, but it slows the initial processing of long inputs. This makes memory savings an operational tradeoff rather than a free improvement.
- **Busy request queues**: Too few waiting requests can indicate that the client is not supplying work quickly enough. An excessively large queue adds scheduling overhead, so client behavior also affects how effectively the service runs.
- **Container-based deployments**: NVIDIA distributes SGLang containers monthly with updated software libraries and upstream changes. Teams need to track the selected container release and its known issues, rather than treating all SGLang installations as the same environment.

## Common Misconceptions
- ❌ Myth: SGLang is itself a language model. → ✅ Reality: It is software for executing models and describing generation workflows; the model is a separate choice.
- ❌ Myth: SGLang always outperforms vLLM, another model-serving engine. → ✅ Reality: Comparisons depend on software versions, hardware, model settings, workload shape, and the measurement being optimized.
- ❌ Myth: Giving the cache as much device memory as possible always improves performance. → ✅ Reality: The model and temporary calculations also need memory; an oversized cache allocation can cause out-of-memory failures.

## How It Sounds in Conversation
- "Can the platform team pin the **SGLang release** before Friday's trial?"
- "Please attach the **model and hardware settings** to the engine comparison."
- "Can operations check the **request queue** before we change the server settings?"
- "Let's test the **follow-up and no-follow-up branches** before Tuesday's review demo."
- "Please add the **container version** to the deployment handover."

## Related Reading
- (before) **Large Language Model** — Understand the model being executed first; SGLang manages its execution rather than replacing it.
- (similar) **vLLM** — Compare another model-serving engine using matched workloads and releases instead of assuming a permanent performance ranking.
- (next) **KV Cache** — Explore how stored attention calculations consume memory and affect the number of requests a service can handle together.
- (next) **Prefill and Decode** — Separating input processing from step-by-step output generation helps explain where waiting time and memory pressure arise.
- (next) **Quantization** — Learn how compressing model numbers changes deployment requirements before comparing engines that use different numerical settings.

## body_basic_ko

## 쉽게 이해하기
언어 AI 모델을 직접 운영할 때는 답변 하나를 만드는 것뿐 아니라, 여러 요청을 제한된 메모리 안에서 처리해야 한다. 요청마다 같은 안내문을 처음부터 계산하면 작업이 겹친다. 동시에 처리할 요청을 늘리면 계산용 장치인 **GPU**의 메모리도 더 필요하므로, 처리량과 메모리 여유를 함께 관리해야 한다.

SGLang은 이런 실행 관리를 맡으며, Python으로 여러 생성 단계를 연결하는 기능도 제공한다. 공통 서식은 보관하고 달라진 부분만 작성하는 문서 작업처럼, 같은 입력 앞부분의 계산 결과를 찾아 다시 쓴다. 이때 재사용하는 중간 계산 저장소를 **KV 캐시**라고 한다.

핵심 기능인 **RadixAttention**은 **토큰**, 즉 모델이 글을 처리하는 조각들의 공통 접두부를 트리 형태로 관리해 재사용 가능한 KV 캐시를 찾는다. 여기에 요청을 언제 묶어 실행할지 정하는 **스케줄러**가 결합된다. 예를 들어 공통 앞부분이 많은 작업에서는 기존 캐시와 길게 일치하는 요청부터 처리하는 정책을 선택할 수 있지만, 요청 순서를 정하는 비용도 늘어난다.

## 비유와 예시
- **판정 예시를 공유하는 문장 분류**: 콘텐츠 운영팀이 같은 판정 예시를 입력 앞에 붙이고 문장별 분류를 맡기는 작업을 생각해 보자. SGLang은 이처럼 입력 앞부분이 반복되는 작업에서 캐시 재사용을 활용할 수 있다.
- **조건에 따라 갈라지는 문구 생성**: 편집 도구에서 초안을 만든 뒤 조건에 따라 서로 다른 후속 문구를 생성하는 작업을 구성할 수 있다. SGLang의 Python 기반 언어는 이런 분기와 반복을 포함하는 생성 흐름을 표현한다.
- **서버를 띄우지 않는 일괄 생성**: 사용자에게 즉시 응답할 필요가 없는 문서 묶음 처리에서는 요청을 프로그램 안의 실행 엔진에 한꺼번에 전달할 수 있다. 이 경로는 웹 서버를 거치지 않고도 엔진의 요청 묶음 처리 기능을 사용한다.

## 한눈에 비교
| 비교 항목 | 온라인 서비스 측정 | 오프라인 일괄 처리 측정 |
|---|---|---|
| 목적 | 사용자가 겪는 응답 지연과 처리량 확인 | 웹 통신을 제외한 최대 처리량 확인 |
| 요청 경로 | 웹 서버를 1회 거쳐 실행 엔진으로 전달 | 웹 서버 경유 0회, 프로그램 안에서 엔진 직접 호출 |
| 요청 제출 방식 | 도착 속도와 동시 요청 수를 조절 | 준비된 요청을 한꺼번에 제출 |
| 주요 지표 | 첫 토큰 대기 시간·토큰 간 시간·초당 처리량 | 초당 처리량 |

사용자에게 제공할 서비스의 응답성을 판단하려면 웹 요청 경로를 포함해 측정해야 하며, 오프라인 최대 처리량만으로 그 결과를 대신할 수 없다.

## 어디서 왜 중요한가
- **긴 입력에서 메모리 부족 대응**: 입력을 나누어 처리하는 **청크 크기**를 줄이는 것은 메모리 부족을 완화하는 조정 방법이다. 효과는 모델·부하·스케줄링 설정에 따라 달라지므로 **메모리 사용량·첫 토큰 지연·처리량을 함께 측정**해야 한다.
- **답변 생성 중 동시 실행 제어**: 답변을 생성하는 단계에서 메모리가 부족하면 동시 실행 요청 수를 줄일 수 있다. 조정 뒤에는 대기 중인 요청 수와 처리량을 함께 확인해 운영 영향을 판단한다.
- **캐시와 실행용 메모리 배분**: GPU 메모리를 캐시에 많이 배정하더라도 모델 실행 중 필요한 임시 공간을 남겨야 한다. 캐시 비중을 낮추면 메모리 부족 위험을 줄일 수 있지만, 최대 동시 처리 수와 최고 처리량도 제한될 수 있다.
- **추론 엔진 도입·교체 판단**: vLLM 같은 대안과 비교할 때는 모델·GPU·계산 정밀도·입출력 길이·측정 버전을 맞춰야 한다. 특정 조건에서 나온 속도 순위보다 실제 서비스의 작업 조건에 맞는 결과를 도입 근거로 삼는 것이 중요하다.

## 자주 하는 오해
- ❌ 오해: SGLang은 답변을 만드는 AI 모델의 이름이다. → ✅ 실제: 학습된 모델을 실행하는 소프트웨어이며, 생성 흐름을 표현하는 언어도 포함한다.
- ❌ 오해: 뜻이 비슷한 질문이면 이전 답변을 그대로 재활용한다. → ✅ 실제: 여기서 설명한 캐시 재사용은 공통된 입력 토큰 접두부의 중간 계산을 다시 쓰는 것이지, 질문의 의미만 보고 완성된 답변을 돌려주는 기능이 아니다.
- ❌ 오해: 오프라인 처리량이 높으면 사용자에게 첫 답변도 반드시 빨리 나온다. → ✅ 실제: 웹 요청과 대기열을 포함한 첫 토큰 지연은 별도로 측정해야 하며, 최대 처리량과 같은 지표가 아니다.

## 대화에서는 이렇게
- "지민님, **SGLang**은 현재 측정 버전과 모델·GPU·계산 정밀도를 고정하고, 같은 입력으로 vLLM 비교표를 만들어 주세요."
- "수아님, **온라인 응답 성능**은 입력 256토큰·출력 32토큰·동시 요청 16개 조건으로 재고, 첫 토큰 대기 시간과 처리량을 같이 올려 주세요."
- "민수님, 같은 모델과 부하에서 **입력 청크 크기**만 바꾸고, 메모리 사용량·첫 토큰 지연·처리량을 비교한 뒤 운영 설정을 제안해 주세요."

## 함께 읽으면 좋은 용어
- (기초) **대규모 언어 모델** — SGLang이 실행하는 대상이므로, 모델 자체와 실행 소프트웨어의 역할을 구분하는 출발점이다.
- (기초) **GPU** — 모델 계산과 캐시가 사용하는 메모리에 한계가 있는 이유를 이해하면 장비 선택과 운영 제약을 읽기 쉬워진다.
- (유사) **vLLM** — 같은 추론 엔진 선택지로, 실제 요청 형태와 측정 버전을 맞춰 비교하는 법을 익히기 좋다.
- (심화) **KV 캐시** — 재사용하는 중간 계산이 무엇인지 알면 메모리 사용량과 동시 처리 수의 관계를 이해할 수 있다.
- (심화) **프리필과 디코딩** — 입력 처리와 답변 생성 단계를 구분하면 메모리 부족이 발생한 위치에 맞춰 설정을 조정할 수 있다.

## body_advanced_en

## Technical Definition & How It Works
SGLang separates the expression of structured generation programs from their scheduled execution in an inference runtime. Its documented execution boundaries include an HTTP server, an in-process **Engine** with a scheduler, and direct **ModelRunner** execution that bypasses scheduling; these are distinct measurement boundaries, not interchangeable deployment paths.

The frontend expresses generation control flow, while the runtime determines how submitted requests are batched and executed. Consequently, a benchmark must identify which runtime responsibilities it includes before its results can support an architectural decision.

- **Submission boundary:** HTTP execution requires a running server launched through `sglang.launch_server`. By contrast, `bench_offline_throughput` instantiates `Engine` in-process and submits requests through `engine.generate()`, without an HTTP server.
- **Scheduling boundary:** The Engine scheduler remains active during offline throughput measurement. Removing HTTP therefore does not remove request batching or scheduling overhead. The optional `lpm` scheduling policy reorders requests to encourage prefix-cache hits, trading additional scheduling work for increased reuse.
- **Execution boundary:** At the lowest documented benchmark level, `bench_one_batch` calls `ModelRunner.extend()` and `ModelRunner.decode()` on a static batch. It separates prefill and decode for profiling but omits scheduler behavior, including the server's ability to chunk prefill.
- **Capacity feedback:** Runtime logs expose running requests, queued requests, and KV-cache token usage. A nonempty queue with low cache utilization can indicate conservative admission; frequent cache-pool retractions indicate a different pressure condition. Large requested output caps followed by early stopping can make admission estimates unnecessarily conservative.
- **Measurement boundary:** `bench_serving` uses asynchronous HTTP requests with controlled arrival rates and concurrency, measuring TTFT, TPOT, ITL, and throughput. In-process Engine throughput includes scheduling but excludes HTTP, while direct ModelRunner timing excludes both.

A defensible investigation therefore proceeds from server-level measurement to scheduler-inclusive execution and then to static-batch profiling, narrowing the boundary rather than treating every throughput result as equivalent. The supplied materials do not establish a deployment-independent latency or throughput specification.

## Formulas, Architecture, and Diagrams
**Memory and configuration review matrix**

Assume the CUDA-backed memory model described in the tuning documentation. Model weights, the KV-cache pool, CUDA graph buffers, and activations are its stated planning categories; this is not an exhaustive account of every allocator or process allocation. The values below are workload-dependent tuning examples, not universal defaults or hardware limits.

| Control or allocation boundary | Documented interpretation | Performance consequence | Review condition |
|---|---|---|---|
| `--mem-fraction-static` | Sets the fraction of GPU capacity assigned to model weights plus the KV-cache pool | Increasing it expands cache capacity but leaves less room for activations and graph buffers | The documented 5–8 GB activation-headroom guideline requires workload validation; successful startup is not proof of runtime safety |
| `--chunked-prefill-size` | Controls the prefill chunk size; 4096 or 2048 are suggested reductions for prefill OOM | Smaller chunks save memory but slow prefill for long prompts | Attribute the failure to prefill before selecting this intervention |
| `--max-running-requests` | Limits concurrently running requests | Lowering it can address decode OOM at the expense of concurrency | Distinguish running-request capacity from an API request-rate quota |
| `--cuda-graph-max-bs-decode` | Extends decode CUDA-graph coverage; 512 or 768 are examples useful for some models | More graph coverage consumes additional memory | Reassess static memory allocation when expanding graph coverage |
| `--schedule-conservativeness` | Examples include decreasing toward 0.3 for conservative admission or increasing toward 1.3 for frequent retractions | Changes admission behavior rather than physical GPU capacity | Interpret queue depth, cache utilization, and retraction frequency together |

**Version assumption:** validate flag availability against the pinned deployment release. Historical reproduction commands and unversioned tuning examples should not be combined into an assumed release-compatible configuration.

## Code or Pseudocode
The following is **host-side benchmark-policy pseudocode**, not SGLang API signatures or automatic recovery behavior. `host_trial` launches a fresh server with the supplied flags, runs `bench_serving --profile`, and tears the server down before returning; startup and execution failures both become `Failure`. Phase classification requires affirmative server-log or profiler call-stack evidence—an HTTP error alone establishes no phase.

```text
# Pseudocode: one initial trial and at most one configuration retry.
type Config = {release: string, model: string, chunk: int, running: int}
type Workload = {prompts: list[string], output_cap: int, concurrency: int}
type Metrics = {ttft_ms: float, tpot_ms: float,
                itl_ms: float, output_tokens_s: float}
type Trial = Success(metrics: Metrics)
           | Failure(kind: "oom" | "other", evidence: string)
type Result = Accepted(config: Config, metrics: Metrics)
            | Rejected(reason: string)

def evaluate(cfg: Config, workload: Workload) -> Result:
    if not cfg.release or not cfg.model:
        return Rejected("Pin the runtime release and model")
    if min(cfg.chunk, cfg.running, workload.output_cap,
           workload.concurrency) <= 0:
        return Rejected("Configuration values must be positive")
    if len(workload.prompts) < 5 * workload.concurrency:
        return Rejected("Insufficient prompts for the steady-state test")

    for attempt in range(2):
        # Host execution boundary: changed flags reach a NEW server.
        trial = host_trial(
            release=cfg.release,
            server_flags={"--model-path": cfg.model,
                          "--chunked-prefill-size": cfg.chunk,
                          "--max-running-requests": cfg.running},
            workload=workload)
        if trial is Success:
            return Accepted(cfg, trial.metrics)
        if trial.kind != "oom":
            return Rejected("Non-OOM failure; inspect server evidence")
        if attempt == 1:
            return Rejected("OOM persisted after the single retry")

        phase = confirm_phase_from_server_evidence(trial.evidence)
        if phase == "prefill" and cfg.chunk > 2048:
            cfg.chunk = 4096 if cfg.chunk > 4096 else 2048
        elif phase == "decode" and cfg.running > 1:
            cfg.running = max(1, cfg.running // 2)
        else:
            return Rejected("Unknown phase or no bounded reduction available")
    return Rejected("Trial budget exhausted")
```

Halving decode concurrency is an illustrative host policy, not a documented SGLang recovery algorithm. Keep hardware, model, precision, and workload fixed, and record the changed configuration with its result; the retried measurement is a separate configuration, not a replacement observation under identical conditions.

## Production Pitfalls
- ❌ Mistake: Setting only the server's profiler directory and assuming `bench_serving --profile` will select it → ✅ Fix: Set an explicit client `--profile-output-dir` or configure `SGLANG_TORCH_PROFILER_DIR` consistently on client and server; the benchmark client selects the path sent in `/start_profile`.
- ❌ Mistake: Treating a profile collected from one worker in a prefill/decode-disaggregated deployment as coverage of both execution phases → ✅ Fix: Profile prefill and decode workers separately using their respective worker URLs; the prefill and decode targeting options are mutually exclusive, and all worker nodes need the profiler environment configured before startup.
- ❌ Mistake: Using a direct static-batch ModelRunner profile to explain scheduler admission or end-to-end HTTP latency → ✅ Fix: Collect `bench_serving --profile` traces for the server execution path, and use the static-batch profile only to isolate execution-level behavior that its narrower boundary actually includes.

## Tradeoffs — When to Use What
**Matched benchmark contract**

Before comparing SGLang with another runtime, fix the GPU model, GPU count and memory capacity; model checkpoint; precision and quantization; parallelism layout; input/output-length distribution; shared-prefix distribution; arrival rate and concurrency; EOS behavior; and measurement boundary. Record runtime versions and flags, then report throughput together with TTFT, TPOT, ITL, failures, and memory observations where applicable. Use contemporaneous candidate releases for a deployment decision rather than promoting a historical comparison into a current ranking.

**Suitable**
- **Saturated batch inference with controllable admission:** SGLang exposes scheduler and cache-utilization signals that support throughput tuning, provided the client can maintain sufficient queued work without excessive scheduling overhead.
- **Prefix-heavy traffic with measurable reuse:** Evaluate `--schedule-policy lpm` when request reordering can improve cache hits; retain it only if the saved execution work outweighs additional scheduler cost under the actual workload.
- **Throughput scaling when model replicas fit in memory:** Evaluate data parallelism rather than automatically increasing tensor parallelism; the tuning guidance favors data parallelism for throughput when memory permits and points to Model Gateway for this arrangement.

**Unsuitable**
- **Replacing an accepted vLLM deployment without a matched improvement:** Retain **vLLM** until SGLang demonstrates the required latency, capacity, or operational advantage; migration otherwise adds configuration and acceptance-test work without established benefit.
- **Replacing an established TensorRT-LLM pipeline using an unmatched leaderboard result:** Retain **TensorRT-LLM** until both runtimes satisfy the same benchmark contract; different preparation settings and workload limits make the comparison technically inconclusive.
- **Selecting a backend before validating the target model, precision, and hardware combination:** Prefer an already validated **vLLM** or **TensorRT-LLM** deployment, if one exists for that exact combination, rather than assuming SGLang support or kernel compatibility from another configuration.

**Deployment economics:** compare infrastructure cost at the required accepted throughput and latency, not peak tokens per second alone. Verified information on hosted pricing, rate limits, quotas, and SLAs is limited. The documented running-request limit is a concurrency control, not evidence of a provider billing unit or rate-limit contract.

## Industry Communication
- "For the **serving acceptance review**, **bench_serving** must issue asynchronous HTTP requests to the running server and report online latency metrics including **TTFT**, **TPOT**, and **ITL**, together with throughput."
- "The **capacity report** must identify **bench_offline_throughput** as in-process **Engine** execution with its scheduler and **no HTTP server**, rather than labeling it scheduler-free kernel throughput."
- "The **v0.2.7 reproduction** must remain a separate baseline because its documented launch commands include **--disable-radix-cache**, which changes the cache configuration being evaluated."
- "For **bench_one_batch_server --enable-multi-batch**, the review must treat **overall_throughput** as authoritative and the other listed throughput and latency fields as informational because their denominators include cross-batch queueing."
- "The **FLUX.3 serving-change validation** reports **24 pixel-identical version-paired PNGs** and unchanged per-server runtime peak allocated memory across **12 workload rows**, which is evidence about that tested change rather than equivalence between precision modes."
- "The **quality gate** must preserve the model variant and precision for each before-and-after comparison, and must not reinterpret those diffusion checks as proof that **FP8R or NVFP4 are lossless relative to BF16** or as validation of other quantization modes."
- "The **configuration review** must assess **--cuda-graph-max-bs-decode** and **--mem-fraction-static** together because expanding graph coverage consumes additional memory that the deployment must reserve."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **HTTP** — Understanding the transport boundary is necessary to distinguish server-inclusive measurements from in-process execution without attributing their difference solely to model execution.
- (prerequisite) **Tensor parallelism** — Parallelism layout is an external deployment concept that must be understood before comparing the documented multi-GPU configurations or choosing between tensor-parallel execution and data-parallel scaling.
- (alternative) **vLLM** — A competing inference runtime for the same serving decision; the supplied reproduction scripts verify its role as a comparison backend, not current feature parity or a universal performance ranking.
- (alternative) **TensorRT-LLM** — A competing inference runtime with a separately prepared configuration in the supplied benchmark materials, making preparation settings and workload limits part of the migration and comparison contract.
- (extension) **Prefill/decode disaggregation** — A documented SGLang deployment mode separates prefill and decode workers behind a router, extending the deployment topology and requiring separate worker-targeted profiling rather than a single combined trace.

## body_advanced_ko

## 기술적 정의와 동작 원리
SGLang의 추론 런타임은 요청 제출 인터페이스와 스케줄러 기반 배치 실행을 제공하는 실행 계층이며, **HTTP 서버를 통한 실행**과 **Engine 직접 호출**을 구분한다. 실행 용량은 모델 가중치뿐 아니라 KV 캐시 풀, CUDA graph 버퍼, 활성화 메모리가 함께 결정하므로, 요청 수와 메모리 설정을 독립적인 제한으로 취급하면 안 된다.

**확인되는 실행 경계**는 다음과 같다. 서버 경로에서는 실행 중인 서버에 HTTP 요청을 제출한다. 직접 호출 경로에서는 호출 프로세스가 `Engine`을 생성하고 `engine.generate()`로 요청들을 제출하며, 엔진의 스케줄러가 배치 구성과 실행을 담당한다. 따라서 HTTP를 제거해도 스케줄러는 제거되지 않는다. 여기서 **in-process Engine 사용**은 모든 GPU 작업자가 호출자와 동일한 프로세스에서 실행된다는 뜻으로 확대 해석하지 않아야 한다. 작업자 프로세스 배치와 내부 통신 방식의 세부사항은 해당 주제에 대한 검증된 정보가 부족합니다.

**요청과 메모리의 제어 흐름**은 다음 단계로 검토할 수 있다.

- **제출:** 호스트가 입력과 생성 조건을 전달한다. 대기 요청이 없고 처리량이 낮다면 엔진 실행보다 요청 공급이 병목일 가능성부터 확인한다.
- **수용·배치 구성:** 스케줄러가 대기 요청을 실행 배치에 포함한다. 큰 `max_new_tokens`를 지정했지만 EOS나 중지 문자열로 일찍 끝나는 요청이 많으면, 스케줄러가 새 요청을 지나치게 보수적으로 받아들이는 상황이 생길 수 있다.
- **실행:** prefill과 decode가 메모리를 사용한다. 서버는 prefill을 작은 배치로 나눌 수 있으며, decode 중 KV 캐시 풀이 부족하면 요청 철회 경고가 발생할 수 있다. 따라서 OOM과 KV 캐시 압박을 같은 장애로 처리하지 말고 발생 단계와 경고를 구분한다.
- **완료·검증:** 결과를 회수한 뒤 처리량뿐 아니라 TTFT, TPOT, ITL과 메모리 상태를 함께 확인한다. 최대 처리량이 높더라도 지연 목표를 충족하지 못한 설정은 온라인 배포 후보에서 제외하는 것이 검수 기준이다.

**메모리 회계의 경계**도 중요하다. `--mem-fraction-static`은 전체 GPU 메모리 용량 중 **모델 가중치와 KV 캐시 풀의 합계**에 배정하는 비율이다. 실행 직전에 조회한 가용 메모리의 비율도, KV 캐시만의 비율도 아니다. 나머지 공간에는 활성화와 CUDA graph 버퍼를 위한 여유가 필요하다. 이 회계는 호스트의 사전 용량 추정에 활용할 수 있지만, 실제 워크로드에서 OOM이 발생하지 않는다는 보장은 아니다.

## 핵심 수식·아키텍처·도표
아래 표는 **튜닝 가설과 검수 기준**이다. 수치는 문서에 제시된 시험 후보이며, 모든 모델에 적용되는 기본값이나 성능 보장이 아니다. 비교할 때는 한 번에 바꾸는 설정을 제한하고, 동일한 부하에서 기준 설정과 대조한다.

| 설정·시험 후보 | 적용 조건 | 기대하는 변화와 비용 | 측정 지표 | 실패 판정 기준 |
|---|---|---|---|---|
| `--schedule-conservativeness`를 0.3 방향으로 낮추기 | 대기 요청이 지속되지만 `token usage`가 0.9 미만이고 조기 종료가 많은 부하 | 요청 수용을 늘릴 가능성, KV 캐시 압박 증가 가능성 | KV 캐시 사용률, 생성 token/s, 요청 철회 경고 빈도 | 처리량 이득 없이 철회 경고가 빈번해지거나 지연 목표 위반 |
| 같은 설정을 1.3 방향으로 높이기 | KV 캐시 사용률이 높고 요청 철회 경고가 빈번한 부하 | 수용을 보수적으로 조정, 처리량 감소 가능성 | 철회 경고 빈도, 생성 token/s, TTFT | 철회가 줄지 않거나 처리량 감소가 허용 범위를 초과 |
| `--mem-fraction-static`을 0.01씩 높여 시험 | 준비 직전 `available_gpu_mem`에 여유가 있고 동시성 확대가 필요한 경우 | KV 캐시 풀 확대, 실행 중 메모리 여유 감소 | 준비 로그의 가용 메모리, 장치별 실측 피크, OOM, 처리량 | 대표 부하에서 OOM 발생 또는 처리량 개선 없음 |
| `--chunked-prefill-size`를 4096 또는 2048로 축소 | prefill 단계에서 OOM이 발생하는 긴 입력 부하 | 메모리 절감, 긴 입력 prefill 속도 저하 | prefill OOM 재현 여부, TTFT, 처리량 | OOM이 지속되거나 TTFT 목표 위반 |
| `--cuda-graph-max-bs-decode`를 512 또는 768까지 확대 시험 | 일부 모델의 큰 TP 구성에서 큰 decode 배치가 발생하는 경우 | graph 적용 범위 확대 가능성, 추가 메모리 소비 | decode 배치 크기, ITL, 처리량, 실측 피크 | ITL·처리량 이득 없이 메모리만 증가하거나 OOM 발생 |
| `--schedule-policy lpm` 시험 | 공유 접두사가 많은 요청 분포 | 캐시 적중을 유도하는 재정렬, 스케줄링 오버헤드 증가 | TTFT, 처리량, 별도 계측한 캐시 재사용 효과 | 재사용 효과보다 스케줄링 비용이 커져 지연·처리량 악화 |

메모리 튜닝 문서는 준비 시점의 `available_gpu_mem` **5–8 GB**를 경험적 점검 범위로 제시한다. 이를 장치 종류와 워크로드에 무관한 안전 하한으로 사용하지 말고, 긴 입력과 높은 동시성을 포함한 실측 피크로 검증해야 한다. CUDA graph 범위를 늘리는 시험에서는 같은 메모리 예산을 공유하는 `--mem-fraction-static`도 함께 검토한다.

## 코드 또는 의사코드
다음은 **호스트의 사전 추정 검사와 Engine 실행 경계**를 보여 주는 의사코드다. `추정_추가피크_B`는 엔진 생성부터 결과 수집까지 추가로 필요할 것으로 예상하는 장치별 피크이며, `안전여유_B`와 분리한다. 실측 피크도 동일한 추가 사용량 기준으로 수집한다. 생성·계측·정리 표기는 계약 수준의 추상 연산이며 SGLang의 실제 메서드명이 아니다. 실제 생성 인자와 종료 API는 배포 버전에 맞춰 연결해야 한다.

```text
함수 일괄생성(
    설정: 배포설정, 입력: 목록[문자열], 최대출력토큰: 정수,
    추정_추가피크_B: 장치별[실수], 안전여유_B: 장치별[실수]
) -> 실행결과:
    검증 설정.모델경로가 비어 있지 않음
    검증 설정.장치들이 비어 있지 않고 중복되지 않음
    검증 입력이 비어 있지 않고 모든 항목이 문자열임
    검증 최대출력토큰이 양의 정수임
    가용_B = 호스트에서_장치별_가용메모리_조회(설정.장치들)
    검증 두 메모리 계획의 장치 집합이 설정.장치들과 같음
    각 장치 d에 대해:
        각 값 v in [가용_B[d], 추정_추가피크_B[d], 안전여유_B[d]]:
            만약 v가 유한한 수가 아니거나 v < 0:
                입력오류 발생("메모리 값은 유한한 비음수여야 함")
        만약 추정_추가피크_B[d] + 안전여유_B[d] > 가용_B[d]:
            사전검사거절 발생("해당 장치의 추정 메모리 예산 초과")

    자원 = 호스트_자원소유권_범위()  # 부분 초기화 실패도 정리 대상으로 추적
    시도:
        계측 = 자원에서_장치별_추가사용량_피크계측_시작(설정.장치들)
        엔진 = 자원에서_추적하며_Engine_생성(설정)
        응답 = 엔진.generate(입력, 생성조건={max_new_tokens: 최대출력토큰})
        결과 = 호스트에서_결과_수집(응답)
        만약 결과.개수 != 입력.개수:
            결과오류 발생("일부 요청의 결과가 누락됨")
        실측_추가피크_B = 계측에서_동일기준_피크_읽기()
        반환 실행결과(결과, 가용_B, 안전여유_B,
                      추정_추가피크_B, 실측_추가피크_B)
    예외 실행중메모리부족:
        실행실패 발생("사전 검사는 용량 보장이 아님; 실패 단계를 재평가")
    예외 엔진생성오류 또는 생성실행오류 또는 결과오류:
        실행실패 발생("부분 결과를 정상 완료로 취급하지 않음")
    마지막에:
        자원에서_엔진과_계측자원_모두정리()
```

이 검사는 **GPU 전체의 메모리 합계가 아니라 각 장치의 예산**을 비교한다. 검사 통과는 실행 허가에 대한 호스트의 판단일 뿐이며, SGLang 스케줄러의 요청 수용 규칙을 재현한 것이 아니다. 가용량은 실행 전 관측치, 안전 여유는 운영자가 정한 예산, 실측 피크는 실행 결과이므로 같은 필드로 덮어쓰지 않는다.

## 프로덕션 함정
- ❌ 실수: Decode 로그의 한 시점에서 token usage가 높다는 이유로 전체 GPU 활용과 요청 처리 효율이 충분하다고 판정한다. → ✅ 해결: 로그 해석 계약에 #queue-req는 대기 요청 수, token usage는 KV 캐시 메모리 사용률, gen throughput은 token/s임을 명시하고 정상상태의 지속 구간을 비교한다.
- ❌ 실수: HTTP를 제외한 오프라인 결과와 서버 측 결과를 같은 지연 측정으로 합치고, 스케줄러가 포함되는 경계도 기록하지 않는다. → ✅ 해결: bench_serving과 bench_one_batch_server는 HTTP와 스케줄러를 모두 포함하고, bench_offline_throughput은 HTTP 없이 Engine 스케줄러를 포함한다고 기록하며 단일 배치 결과는 정상상태 평가와 분리한다.
- ❌ 실수: bench_one_batch_server의 multi-batch 결과에서 last_ttft와 ITL을 일반 온라인 지연처럼 해석해 설정 변경의 효과를 승인한다. → ✅ 해결: --enable-multi-batch에서는 overall_throughput만 권위 있는 처리량 지표로 취급하고, 배치 간 대기가 분모에 포함되는 다른 지표는 참고용으로 분리해 온라인 지연을 별도 검증한다.
- ❌ 실수: 서버에만 프로파일 출력 환경변수를 설정한 뒤 bench_serving --profile 결과가 예상 경로에 없다는 이유로 계측 실패로 판단한다. → ✅ 해결: 이 경로에서는 클라이언트의 --profile-output-dir 또는 SGLANG_TORCH_PROFILER_DIR 선택값이 서버로 전달됨을 반영하고, 직접 /start_profile을 호출하는 경우의 서버 측 경로 선택과 구분한다.

## 트레이드오프와 언제 무엇을 쓰나
다음의 기능 설명과 **도입·구성 선택에 대한 설계 권고**를 구분해야 한다. 특정 설정을 지원한다는 사실만으로 다른 런타임보다 저렴하거나 빠르다고 결론 내릴 수는 없다.

**이럴 때 적합**

- **종료 길이 변동이 큰 포화 부하를 조정할 때:** 큰 출력 상한과 잦은 EOS 종료가 함께 나타나면 요청 수용이 보수적일 수 있다. SGLang의 스케줄링 보수성 설정을 시험하고, 처리량 증가와 KV 캐시 철회 빈도를 함께 검수할 수 있다.
- **모델을 복제할 메모리가 충분하고 처리량이 우선일 때:** 튜닝 지침은 데이터 병렬화를 우선 검토하며, SGLang Model Gateway를 통한 구성을 권한다. GPU를 추가할 때 TP 확대만 시험하지 않고 복제 구성을 비교하는 근거가 된다.
- **작은 모델·작은 배치의 실행 지연을 줄이려 할 때:** `--enable-torch-compile`이 시험 후보로 제시되어 있다. 다만 해당 모델과 부하에서 지연 개선이 재현되는지를 확인한 뒤 채택하는 것이 설계 권고다.

**이럴 때 부적합**

- **기존 vLLM 배포가 목표를 충족하고 SGLang의 추가 이득이 검증되지 않았을 때:** 대안은 **vLLM 유지**다. 일반적인 전환 비용에는 실행 설정 재작성과 회귀 시험이 포함되므로, 처리량 수치 하나만으로 마이그레이션을 승인하지 않는다.
- **TensorRT-LLM 기반 배포의 운영 기준을 이미 확보했지만 SGLang 비교 실험이 없을 때:** 대안은 **TensorRT-LLM 유지 후 병렬 검증**이다. 기능 누락을 가정하는 대신, 새 설정·배포 경로를 검증할 팀의 복잡도와 비용을 판단한다.
- **메모리가 충분한데 처리량 확대를 위해 TP만 늘리는 구성을 선택할 때:** 대안은 **SGLang Model Gateway 기반 데이터 병렬화**다. 이는 SGLang 자체의 부적합이 아니라 구성 선택의 부적합이며, 문서의 처리량 중심 권고와 맞지 않는 구성을 피하려는 판단이다.

**비용 비교 계약**에는 GPU 종류·수량, 모델과 리비전, 정밀도, 요청 도착률·동시성, 입출력 길이와 접두사 분포, EOS 처리, TTFT·TPOT 목표를 고정하거나 명시한다. 일반적인 산정 권고는 GPU 사용 시간과 운영 비용을 기록하고, 지연 목표를 충족한 완료 요청·출력 토큰을 기준으로 비용을 비교하는 것이다. 제공 자료에는 SGLang의 서비스 과금 단가, 기본 rate limit, quota, SLA를 확정할 정보가 없으므로 해당 주제에 대한 검증된 정보가 부족합니다.

## 업계 대화 맥락
다음은 **가상의 PR·설계 검토 문장**이다. 팀명은 예시이며 실측 결과나 실제 장애를 보고하는 문장이 아니다. 버전이 특정된 설정과 버전이 특정되지 않은 기능 설명을 분리했다.

- "**추론 플랫폼팀의 재현성 검토**에서는 **v0.2.7 재현 설정의 --disable-radix-cache**를 실험 조건에 기록하고, 그 결과를 캐시 재사용 효과의 검증 자료로 사용하지 않도록 요청합니다."
- "**서빙팀의 입장 제어 설계**에서는 **--max-running-requests**를 실행 동시성 설정으로 다루고, 이를 서비스의 외부 **rate limit·quota 계약**과 동일한 것으로 문서화하지 않겠습니다."
- "**평가팀의 트래픽 재생 검토**에서는 custom 데이터의 기록된 완료 길이가 무시되고 **--output-len이 공통 max_new_tokens 상한**으로 사용되는 점을 평가 조건에 반영해야 합니다."
- "**성능팀의 EOS 검토**에서는 실제 프롬프트에 **--disable-ignore-eos**를 적용한 실험과 강제 길이 실험을 분리하고, 조기 종료가 있는 전체 실행 지표와 정상상태 구간 지표를 구별하겠습니다."
- "**인프라팀의 분리 배포 계측안**은 **prefill·decode 작업자를 따로 프로파일링**하도록 수정하고, 서로 배타적인 두 프로파일 대상 옵션을 같은 실행에 지정하지 않도록 검수하겠습니다."
- "**마이그레이션 설계 검토**에서는 **HTTP 요청 계약**과 **SGLang 고유 실행 플래그**를 별도 계층으로 관리하고, 런타임 교체 시 플래그와 결과 수집 경로의 재검증 비용을 전환 계획에 포함하겠습니다."

## 선행·대안·확장 개념
- (선행) **GPU 메모리 용량 계획** — 런타임 바깥의 배포 설계 작업으로, 장치별 가용량과 실행 피크를 구분해야 SGLang의 메모리 설정을 호스트의 용량 예산에 연결할 수 있다.
- (선행) **부하 시험** — 요청 도착률·동시성·정상상태를 통제하는 평가 방법으로, SGLang의 처리량과 지연 결과가 어느 실행 경계를 측정했는지 판단하는 전제다.
- (대안) **vLLM** — 동일한 LLM 서빙 문제의 대안 런타임이며, 선택할 때 기능 유무만 비교하지 말고 배포 버전·설정과 요청 분포를 맞춘 회귀 시험을 수행해야 한다.
- (대안) **TensorRT-LLM** — LLM 추론 배포의 대안으로 비교 자료에 포함되며, 런타임 전환 판단에서는 처리량뿐 아니라 기존 구성의 검증 비용과 새 배포 설정의 운영 복잡도도 비교해야 한다.
- (확장) **SGLang Model Gateway** — SGLang 튜닝 지침에서 데이터 병렬 구성을 위해 권하는 확장 계층으로, 단일 엔진 설정과 여러 인스턴스를 활용하는 배포 선택을 구분하게 한다.
- (확장) **Prefill–Decode 분리 배포** — SGLang 실행을 prefill과 decode 작업자로 나누는 배포 형태이며, 프로파일링도 작업자별로 분리해야 하므로 단일 서버와 다른 계측 경계를 요구한다.

## references_en

- {"title": "SGLang Release Notes", "type": "docs", "url": "https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/index.html", "tier": "primary", "annotation": "NVIDIA 배포판의 개요와 릴리스별 변경·알려진 문제를 확인한다."}
- {"title": "Benchmark and Profiling", "type": "docs", "url": "https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling", "tier": "primary", "annotation": "Choose between server, offline, and low-level tests, and understand which overheads each measurement includes."}
- {"title": "Hyperparameter Tuning", "type": "docs", "url": "https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning", "tier": "primary", "annotation": "Understand memory allocation, request queues, shared-prefix scheduling, and their operational tradeoffs."}
- {"title": "How to reproduce the benchmark results of SGLang", "type": "code", "url": "https://github.com/sgl-project/sglang/blob/main/benchmark/blog_v0_2/README.md", "tier": "primary", "annotation": "v0.2.7의 과거 재현 설정으로 버전·장비·옵션 확인법을 배운다."}
- {"title": "SGLang vs vLLM (2026): Which Is Best for Your Workload?", "type": "blog", "url": "https://tensormesh.ai/learn/vllm-vs-sglang", "tier": "secondary", "annotation": "Consider workload shape, cache behavior, and configuration when comparing the two serving engines."}
- {"title": "SGLang: The Complete Guide to High-Performance LLM Inference", "type": "blog", "url": "https://inference.net/content/sglang-complete-guide", "tier": "secondary", "annotation": "생성 언어와 실행 엔진이라는 두 역할을 함께 이해하는 데 도움된다."}
