# SGLang — claude-sonnet-5-5

- advanced 63 / basic 70 / gate review_required / penalty 1 / $1.2522 / 328s

## definition_en

SGLang is an open-source LLM serving runtime and structured generation language that pairs a Python-embedded frontend for writing multi-step generation programs with RadixAttention, which reuses the KV cache of shared prompt prefixes across requests to avoid redundant computation.

## definition_ko

SGLang은 LLM을 위한 고성능 서빙 런타임이자 구조화 생성 언어로, 파이썬 기반 프런트엔드로 다단계 생성 프로그램을 작성하고 RadixAttention으로 요청 간 공통 접두부의 KV 캐시를 재사용해 중복 계산을 줄이는 오픈소스 시스템이다.

## summary_en

SGLang is open-source software for running large language models and for writing multi-step prompts in Python. Think of a cook who keeps the already-chopped vegetables from the last order and reuses them whenever the next order starts the same way. SGLang does something similar: it keeps the model's working notes (the KV cache) for the beginning of a prompt, and when another request starts with exactly the same beginning, it skips redoing that part. That mainly saves the up-front reading step, not the writing of the answer, which is why it helps most when many requests share long instructions or documents.

## summary_ko

SGLang은 거대 언어 모델(LLM)을 빠르게 돌려주는 오픈소스 서빙 엔진이자, 복잡한 생성 작업을 파이썬으로 짤 수 있게 해 주는 언어다. 도서관 사서가 방금 찾은 책을 책상 위에 그대로 두었다가 같은 질문이 오면 다시 찾지 않고 바로 꺼내 주는 것과 비슷하다. 앞부분이 같은 요청들이 이미 계산해 둔 중간 결과(KV 캐시)를 다시 쓰도록 관리해서 중복 계산을 줄인다. 그래서 에이전트나 여러 단계 추론처럼 비슷한 프롬프트가 반복되는 서비스에서 효율을 높이는 데 쓰인다.

## body_basic_en

## Plain Explanation
Running a language model has two phases. First the model reads the whole prompt (called prefill), then it writes the answer one token at a time (decode). Many real applications send prompts that begin identically: the same long instructions, the same document, or the same few-shot examples (sample answers pasted into the prompt). A server without cross-request prefix caching re-reads that identical beginning from scratch for every request, wasting GPU time.

SGLang tackles this in two parts. On the frontend, it offers a Python interface for writing multi-step generation programs with loops and conditionals, such as agents or chain-of-thought flows. On the backend, a runtime uses RadixAttention to remember the KV cache (the model's stored working notes about tokens it has already read) in a tree-like structure keyed by token sequences. Picture a filing cabinet where folders are organized by how a prompt begins, so a new request can walk down the tree and find the longest beginning it shares with earlier ones.

When a new request matches a stored beginning exactly, SGLang reuses those cached entries instead of recomputing them. The saving falls mainly on prefill: the answer is still generated token by token. The reuse only works if the prefix matches exactly and the cache has not been evicted, and SGLang's scheduler can reorder requests (for example with a longest-prefix-match policy) to raise cache hits, at the cost of extra scheduling overhead.

## Examples & Analogies
- **Branching questions about one document**: A team loads a 50-page contract and asks ten different questions about it. If every request begins with the same contract text, the server can reuse the cached notes for that shared start and only process each new question, which cuts prefill work. Each answer is still generated from scratch.
- **A multi-step tool workflow**: An agent plans a task, calls a search tool, reads the result, then decides the next step, each step extending the same conversation. Because every step starts with the earlier text, a retained cache lets the server skip re-reading what it already processed. If the cache was evicted or the earlier text was edited, the saving shrinks or disappears.
- **Reranking search results**: SGLang's v0.5.21 release post describes a score endpoint that can rerank search or RAG (retrieval-augmented generation) results in one go. Candidates that share the same query text at the start are the kind of workload where prefix reuse may help, but whether it does depends on your setup and should be measured.

## At a Glance
| | SGLang | vLLM |
|---|---|---|
| Prefix cache reuse across requests | Yes, via RadixAttention (radix tree) | Yes, via prefix caching |
| Cache access control | Not covered in provided sources | Optional per-request salts limit reuse to matching salts |
| Scheduling for cache hits | Policy that orders requests to raise hit rate (e.g. longest prefix match) | Not covered in provided sources |
| Frontend programming language | Python-embedded language for multi-step programs | Not covered in provided sources |
| Best-fit workload | Benchmark on your own traffic | Benchmark on your own traffic |

Both engines retain and reuse shared prefixes, so the real differences lie in the surrounding scheduling and tooling, and the only reliable way to choose is to benchmark your own workload against an uncached baseline on the same hardware, model, and metrics.

## Where and Why It Matters
- **NVIDIA container releases**: NVIDIA publishes official SGLang release notes and a container that it states is released monthly, so teams can run SGLang on a vendor-maintained image rather than building from source.
- **Hardware coverage**: A project issue notes SGLang serves GLM-5 on H100, H200, B200 and MI300-class GPUs, while some specialized kernels are tied to newer GPU generations and its cookbook does not list A100 for that model. Check your GPU generation before planning a rollout.
- **Benchmark claims need context**: Chunked-prefill settings can change which engine looks faster on identical hardware, and the SGLang paper excludes optimizations that alter computation results. A headline number such as a 22% faster first token on one model is a vendor-reported gain, not a guarantee for your workload.
- **Memory tuning is part of operations**: SGLang's docs describe splitting GPU memory between model weights, the KV cache pool, CUDA graph buffers and activations, and suggest reserving roughly 5-8 GB for activations. Too little headroom risks out-of-memory errors, and too much limits concurrency.
- **Switching cost**: Using the Python frontend language ties programs to SGLang-specific code, while the server can be tested through standard benchmark tools shipped with the project.

## Common Misconceptions
- ❌ Myth: SGLang makes every request faster. → ✅ Reality: Reuse only helps when requests share an exactly matching beginning and the cache is still retained. Unique prompts see little benefit.
- ❌ Myth: Prefix caching removes the cost of generating the answer. → ✅ Reality: It saves prefill (reading the prompt). The model still produces each output token one at a time.
- ❌ Myth: A benchmark showing SGLang beating another engine applies to you. → ✅ Reality: Results depend on hardware, model, precision, workload shape, and tuning such as chunked-prefill size, so test on your own traffic.

## How It Sounds in Conversation
- "Our agent prompts all start with the same 3k-token **system prompt**, so let's check whether **RadixAttention** gives us a real **prefill** saving before we buy more GPUs."
- "Run **bench_serving** against the staging server with our actual traffic shape and compare **TTFT** with and without the **prefix cache**; I don't trust the vendor chart."
- "We're seeing **KV cache pool is full** warnings every few seconds, so let's lower **mem-fraction-static** a bit or raise **schedule-conservativeness** and rerun."
- "The docs say the **NVIDIA container** ships monthly, so pin the tag in the Dockerfile and note the version in the runbook before the Friday deploy."
- "If we write the workflow in the **SGLang frontend**, how hard is it to move back to a plain **OpenAI-compatible** client later? I want the **switching cost** on the slide."

## Related Reading
- (before) **KV Cache** — The stored working notes that RadixAttention reuses; understand this first or prefix reuse will feel abstract.
- (before) **Prefill and Decode** — The two inference phases explain exactly what caching saves and what it does not.
- (similar) **vLLM** — A competing open-source serving engine that also does prefix caching; read it to compare scheduling and cache-control choices.
- (similar) **TensorRT-LLM** — NVIDIA's inference stack that SGLang's benchmark README also compares against; different tooling and deployment path.
- (next) **Prefill-Decode Disaggregation** — Running prefill and decode on separate workers, which SGLang's docs cover for profiling and serving.
- (next) **Speculative Decoding** — A follow-up speedup idea that targets the decode phase rather than prefill.

## body_basic_ko

## 쉽게 이해하기
LLM에게 질문을 보낼 때 앞부분은 거의 똑같은 경우가 많다. 긴 시스템 안내문, 같은 문서, 같은 예시 문장이 매 요청마다 붙으면 서버는 그 앞부분을 매번 처음부터 다시 계산한다. 이 과정을 프리필(prefill, 입력 전체를 먼저 읽어 처리하는 단계)이라 부르는데, 입력이 길수록 낭비가 커진다.

SGLang은 이 낭비를 줄이는 서빙 엔진이다. 도서관 사서가 자주 찾는 책 묶음을 카운터 옆에 따로 꺼내 두고 다음 손님에게 그대로 건네는 것과 비슷하다. 앞부분이 같은 요청이 오면 이미 계산해 둔 결과를 가져다 쓰고, 달라지는 뒷부분만 새로 계산한다.

핵심 장치는 RadixAttention이다. 모델이 이전 토큰을 기억하는 데 쓰는 메모리인 KV 캐시를, 같은 토큰 접두부끼리 묶어 트리 구조로 보관한다. 새 요청이 들어오면 일치하는 접두부를 찾아 그 캐시를 재사용한다. 단, 재사용되는 것은 공통 접두부의 입력 계산뿐이며, 새 토큰을 생성하는 계산이 사라지는 것은 아니다.

## 비유와 예시
- **같은 문서에 질문 여러 개 던지기**: 50쪽짜리 계약서를 앞에 붙이고 "위험 조항은?", "해지 조건은?", "지급 일정은?"을 차례로 묻는다. 계약서 부분은 모든 요청에서 같으므로 한 번 계산한 캐시를 공유하고, 질문 부분만 새로 계산한다.
- **같은 안내문을 쓰는 고객 응대 봇**: 수백 자짜리 응대 규칙이 모든 대화 맨 앞에 붙는다. 이 공통 앞부분은 재사용되고 고객별 대화 내용만 추가로 처리된다.
- **한 질문에서 여러 갈래로 뻗는 추론**: 하나의 문제에서 여러 풀이 경로를 동시에 시도하는 프로그램을 짠다. 갈라지기 전의 공통 부분을 공유하므로 분기마다 앞부분을 다시 읽지 않아도 된다.

## 한눈에 비교
| | SGLang | vLLM |
|---|---|---|
| 접두부 재사용 | 트리 구조로 캐시를 보관하고, 일치 길이가 긴 요청을 우선하는 스케줄링 정책(`lpm`)을 제공 | 접두부 캐싱을 지원하며 요청별 salt로 재사용 범위를 제한할 수 있음 |
| 프로그래밍 인터페이스 | 파이썬 기반 프런트엔드 언어와 서버 런타임을 함께 제공 | 확인된 자료 없음(별도 검증 필요) |
| 하드웨어 지원 | NVIDIA 및 AMD GPU에서 사용된 사례가 공식 자료에 있음 | 확인된 자료 없음(별도 검증 필요) |

두 엔진 모두 접두부 캐싱을 쓰지만, SGLang은 캐시 보관 방식에 요청 순서를 조정하는 스케줄링까지 묶어 적중률을 높이려 하므로, 어느 쪽이 빠른지는 워크로드와 설정에 따라 달라 직접 측정해 보아야 한다.

## 어디서 왜 중요한가
- **NVIDIA SGLang 컨테이너**: NVIDIA가 월별로 SGLang 컨테이너와 릴리스 노트를 제공하며, 문서에는 에이전트 구성, 단계별 추론, few-shot 프롬프트 같은 다단계 생성 작업이 대표 용도로 적혀 있다.
- **PyTorch 생태계 합류**: SGLang 프로젝트 학습 자료 저장소는 SGLang이 PyTorch 생태계에 공식 합류했다고 안내한다.
- **오픈소스 배포**: Apache 2.0 라이선스로 공개되어 있어 팀이 직접 설치해 운영 환경에서 조정해 볼 수 있다.
- **공통 접두부가 많은 서비스에서 효과를 볼 수 있음**: 긴 공통 안내문이나 문서를 반복해서 쓰는 워크로드라면 캐시 재사용으로 입력 계산을 줄일 가능성이 있다.

## 자주 하는 오해
- ❌ 오해: 캐시를 재사용하면 응답 계산이 통째로 사라진다 → ✅ 실제: 재사용되는 것은 같은 토큰 접두부의 입력 처리 결과뿐이며, 새로 달라지는 부분과 이후 토큰 생성은 여전히 계산해야 한다.
- ❌ 오해: 모든 요청에서 항상 캐시 적중이 일어난다 → ✅ 실제: 접두부가 토큰 단위로 일치하고 해당 캐시가 메모리에 남아 있을 때만 재사용된다. 공통 앞부분이 없거나 캐시가 밀려나면 이점이 줄어든다.
- ❌ 오해: 벤치마크 숫자 하나로 SGLang과 vLLM의 우열이 정해진다 → ✅ 실제: 하드웨어, 모델, 설정값(예: chunked prefill 크기)에 따라 같은 장비에서도 순위가 바뀔 수 있어 자기 워크로드로 측정해야 한다.

## 대화에서는 이렇게
- "캐시를 켜고 끈 조건에서 **첫 토큰 지연** (TTFT)과 처리량을 같은 트래픽으로 비교해 볼까요?"
- "시스템 프롬프트가 길어서 **접두부 재사용**이 얼마나 잡히는지 로그의 token usage부터 확인해 보죠."
- "공통 접두부가 많으면 `lpm` 스케줄링을 시험해 볼 만한데, 스케줄링 오버헤드가 늘 수 있으니 켜기 전후를 측정합시다."
- "OOM이 나면 **mem-fraction-static**을 바로 내리기보다, 공식 문서 기준으로 남는 GPU 메모리부터 로그에서 확인해 볼게요."
- "버전마다 옵션이 바뀔 수 있으니 **bench_serving**으로 우리 트래픽 패턴을 재현해서 SGLang과 vLLM을 같은 조건에서 비교해 보겠습니다."

## 함께 읽으면 좋은 용어
- (기초) **KV 캐시** — SGLang이 재사용하는 대상이 바로 이것. 토큰별 중간 결과를 메모리에 저장해 둔다는 개념을 알아야 접두부 재사용이 이해된다.
- (기초) **프리필과 디코드** — 입력을 읽는 단계와 토큰을 한 개씩 생성하는 단계를 구분해야 어떤 단계가 줄어드는지 알 수 있다.
- (유사) **vLLM** — 같은 층위의 오픈소스 LLM 서빙 엔진. 접두부 캐싱과 스케줄링 방식의 차이를 비교하며 읽기 좋다.
- (유사) **TensorRT-LLM** — NVIDIA 쪽 추론 엔진으로, 벤치마크 자료에서 SGLang과 함께 비교 대상으로 쓰인다.
- (심화) **PD 분리** — (Prefill-Decode Disaggregation) — 프리필과 디코드를 서로 다른 워커로 나누는 일반적인 서빙 구조. 서빙 엔진 구조를 이해한 다음 단계로 적합하다.
- (심화) **구조화 출력** — (Structured Output) — 모델 출력 형식을 제약하는 기능. 생성 흐름을 프로그래밍하는 기능과는 다른 개념이라 함께 구분해서 읽으면 좋다.

## body_advanced_en

## Technical Definition & How It Works
SGLang is an open-source LLM serving runtime paired with a Python-embedded structured generation language. The frontend expresses multi-step programs (loops, conditionals, several model calls). The backend runtime executes them and manages the KV cache with RadixAttention, which the NVIDIA release notes describe as a mechanism for managing KV cache efficiently in generation programs with loops and conditionals. The references describe the cache as a radix tree keyed by text, so requests that share a prefix reuse earlier computation.

Control/data flow, as documented:

- A client sends requests to a server started with `sglang.launch_server`, or calls an in-process `Engine` directly.
- The scheduler batches requests. The tuning guide documents `--schedule-policy lpm` (longest prefix match), which reorders waiting requests to encourage more cache hits at the price of extra scheduling overhead. It also documents `--schedule-conservativeness`, which governs how eagerly new requests are admitted.
- A `ModelRunner` executes prefill (`extend`) and decode steps. Memory is described as: total = model weights + KV cache pool + CUDA graph buffers + activations. `--mem-fraction-static` = (weights + KV pool) / GPU capacity.
- When the KV pool fills, the server logs `KV cache pool is full. Retract requests.` and retracts requests.

Documented interfaces versus unverified details:

- Documented: the four benchmark entry points, the launch flags above, the log fields (`#running-req`, `#queue-req`, `token usage`, `available_gpu_mem`), and the `/start_profile` endpoint.
- Not verified in the provided references: radix-tree node layout, eviction policy, the exact scheduler algorithm, and the zero-overhead scheduler internals mentioned only in a third-party guide. Treat any claim about these as a hypothesis until checked against the source.

Complexity: the references give no asymptotic analysis, so none is stated here. The comparison article notes that the SGLang paper excludes optimizations that alter computation results, which matters when comparing against other engines.

## Key Hardware and Runtime Specs
- **Parameters**: not_published (SGLang is a runtime, not a model; no parameter count applies)
- **Context window**: not_published (determined by the served model; a sample log shows context_len=65536 for one configuration)
- **Training data**: not_published (not applicable to a serving runtime)
- **Latency / throughput**: Sample log from the official tuning guide: gen throughput 4594.01 token/s with #running-req 233 and token usage 0.82 (illustrative log line, not a benchmark). Project-reported v0.5.21 claims: 22% faster first token (DeepSeek-V4.1 Flash, long prompts) and 20.6% higher prefill throughput (Kimi K3, PD serving); setup not published in the provided references.

## Formulas, Architecture, and Diagrams
The four documented benchmark tools operate at different stack levels (from the official Benchmark and Profiling page):

| Tool | HTTP server | Scheduler | Use case |
|---|---|---|---|
| `bench_serving` | Yes (async client) | Yes, via server | Realistic online serving; TTFT, TPOT, ITL |
| `bench_one_batch_server` | Yes | Yes, via server | Single-batch end-to-end latency; metrics biased because never steady-state |
| `bench_offline_throughput` | No | Yes, in-process `Engine` | Max throughput without HTTP overhead |
| `bench_one_batch` | No | No (calls `ModelRunner`) | Kernel-level latency of one static batch |

The docs recommend `bench_serving` by default and `num-prompts >= 5 * max-concurrency` for steady-state measurement.

Tuning signals documented in the hyperparameter guide:

| Signal (log) | Documented reading | Documented action |
|---|---|---|
| `#queue-req: 0` often | Client submits too slowly | Submit faster; healthy range stated as 100-2000 |
| `token usage > 0.9` | Good KV utilization | None |
| `token usage < 0.9` and `#queue-req > 0` | Server too conservative | Lower `--schedule-conservativeness` (e.g. 0.3) |
| Frequent `KV cache pool is full. Retract requests.` | Admitting too much | Raise `--schedule-conservativeness` (e.g. 1.3); about once per minute is stated as okay |
| `available_gpu_mem` 5-8 GB | Good activation headroom | None |
| `available_gpu_mem` 10-20 GB | Headroom wasted | Raise `--mem-fraction-static` |
| Prefill OOM | Chunk too large | `--chunked-prefill-size` 4096 or 2048 |
| Decode OOM | Too many running requests | Lower `--max-running-requests` |

The workload-fit matrix below is a design judgment, not a sourced benchmark result:

- Shared-prefix, multi-call programs: try `--schedule-policy lpm`, then verify with your own traffic.
- Offline batch throughput: maximize batch size; the docs say data parallelism is favored for throughput when memory allows.
- Small models at small batch sizes: `--enable-torch-compile` is documented as helpful.

## Code or Pseudocode
```python
"""Benchmark contract sketch: start server, wait for readiness, run bench_serving, always clean up.
Commands and flags follow the official Benchmark and Profiling page; verify them against your installed version."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path

MODEL = "meta-llama/Llama-3.1-8B-Instruct"  # record the exact model revision/commit in CONTRACT
PORT = 30000
CONTRACT = {
    "sglang_version": subprocess.run([sys.executable, "-c", "import sglang;print(sglang.__version__)"],
                                     capture_output=True, text=True).stdout.strip() or "unknown",
    "gpu": subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip() or "unknown",
    "model": MODEL, "model_revision": "FILL_IN", "precision": "FILL_IN",
    "workload": {"dataset": "random", "in": 256, "out": 32, "concurrency": 16, "num_prompts": 80},
}

server = subprocess.Popen([sys.executable, "-m", "sglang.launch_server",
                           "--model-path", MODEL, "--port", str(PORT)])
try:
    for _ in range(120):                      # readiness polling, 10 min cap
        if server.poll() is not None:
            raise RuntimeError("server exited during startup")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            break
        except OSError:
            time.sleep(5)
    else:
        raise TimeoutError("server never became ready")

    w = CONTRACT["workload"]
    run = subprocess.run(
        [sys.executable, "-m", "sglang.bench_serving", "--backend", "sglang", "--port", str(PORT),
         "--dataset-name", w["dataset"], "--random-input-len", str(w["in"]),
         "--random-output-len", str(w["out"]), "--max-concurrency", str(w["concurrency"]),
         "--num-prompts", str(w["num_prompts"])],   # keep num_prompts >= 5 * concurrency
        capture_output=True, text=True)
    if run.returncode != 0:                   # failure path: benchmark itself failed
        raise RuntimeError(f"bench_serving failed: {run.stderr[-500:]}")
    CONTRACT["raw_output"] = run.stdout       # TTFT/TPOT/ITL/throughput live in this text
    Path("result.json").write_text(json.dumps(CONTRACT, indent=2))
finally:
    server.terminate()                        # guaranteed cleanup
    try:
        server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server.kill()
```

The `/health` path and the `--port` flag on `bench_serving` are assumptions to confirm against the CLI documentation for the version you pin; the readiness poll exists because the server is a separate process.

## Production Pitfalls
- ❌ Mistake: Benchmarking with `bench_one_batch_server` or `bench_one_batch` and reporting the numbers as serving performance → ✅ Fix: The docs state single-batch runs are never steady-state and static-batch runs bypass the scheduler. Use `bench_serving` as the default and keep `num-prompts >= 5 * max-concurrency` (documented guidance).
- ❌ Mistake: Comparing SGLang and vLLM with one default configuration and treating the ranking as final → ✅ Fix: A comparison article notes that tuning for different metrics can change the ranking on identical hardware. Fix hardware, model revision, precision, workload and metrics up front (the contract issue's framing), and record the engine versions, as the project's own reproduction README pins vLLM 0.5.2.
- ❌ Mistake: Seeing frequent `KV cache pool is full. Retract requests.` warnings and ignoring them → ✅ Fix: The tuning guide says roughly once per minute is okay, while frequent occurrences suggest raising `--schedule-conservativeness` (e.g. 1.3). Treat the exact value as a starting point to test, not a guarantee.
- ❌ Mistake: Hitting OOM and changing several memory flags at once → ✅ Fix: The docs map symptoms to levers: prefill OOM to `--chunked-prefill-size` (4096 or 2048, slower long-prompt prefill), decode OOM to `--max-running-requests`, and `--mem-fraction-static` (0.8 or 0.7) as a cap that lowers concurrency. Change one lever per run so the cause is attributable.
- ❌ Mistake: Assuming a kernel path available on H100 also exists on A100 for the same model → ✅ Fix: One comparison issue reports sm_90/sm_100 gating for GLM-5 DSA kernels. Check the model's support list for your GPU generation first; that report does not establish a general rule. The 'quantized is lossless' assumption is also unsafe: a diffusion PR states its FP8R/NVFP4 results are not lossless relative to BF16.

## Tradeoffs — When to Use What
Suitable:

- Shared-prefix, multi-step workloads (agents, few-shot prompting, reranking). Reuse of cached prefixes avoids redundant prefill; the docs also provide `lpm` scheduling for many shared prefixes. Confirm the gain with your own traffic, since the references publish no universal speedup.
- Teams that want a Python-embedded frontend plus runtime in one system for loops, conditionals and parallel branches, instead of writing orchestration around a plain OpenAI-compatible server.
- Hardware on the documented support list for your model. A comparison issue lists H100, H200, B200 and MI300-class GPUs for serving GLM-5, and a release post describes GLM-5.3-Flash on AMD MI355X.
- Environments that prefer vendor-packaged containers: NVIDIA documents an SGLang container released monthly.

Unsuitable:

- Workloads with little prefix overlap: `lpm` reordering adds scheduling overhead per the tuning guide, so gains may not materialize. Measure against vLLM's prefix caching, or plain serving, before committing.
- A100 (sm_80) fleets for GLM-5-class models: the comparison issue states that SGLang's DSA kernels (FlashMLA sparse, DeepGEMM indexer, trtllm) are gated to sm_90/sm_100 and that its cookbook does not list A100. This is a model- and kernel-specific constraint reported in that issue and must not be generalized to all SGLang workloads. Older Llama-class benchmarks in the project README did use A100 80GB.
- Kernel-level profiling of isolated layers: `bench_one_batch` bypasses the scheduler and is the documented tool, so server-level benchmarks are the wrong instrument.
- Single-batch latency claims through `bench_one_batch_server`: the docs say metrics are biased because the server never reaches steady state; use `bench_serving` instead.

## Industry Communication
The following are hypothetical communication templates for design docs and reviews, not quotes from any team.
- "In the design doc we propose evaluating **SGLang** with `--schedule-policy lpm` on the shared-system-prompt traffic, and we will only adopt it if **TTFT p99** improves under our recorded workload; the documented caveat is extra scheduling overhead."
- "This PR pins the **benchmark contract**: GPU model, **sglang version**, model revision, precision, and the `bench_serving` workload, so reruns are comparable. Results without that header will not be accepted."
- "The load test used `--num-prompts 80` at `--max-concurrency 16`, which satisfies the documented **5x concurrency** guideline; the earlier `bench_one_batch_server` numbers should be discarded for steady-state claims."
- "Postmortem hypothesis: the OOM during long prompts may be prefill-related, so the first experiment is lowering **`--chunked-prefill-size`** to 4096. We have not yet confirmed the cause and will change one flag per run."
- "Review note: the log showed **token usage** below 0.9 with a non-empty **#queue-req**; the tuning guide suggests lowering **`--schedule-conservativeness`**, so we will test 0.3 and compare against baseline."
- "Hardware scoping: for the GLM-5 evaluation, a public comparison issue reports that DSA kernels are gated to **sm_90/sm_100**, so we will run on H100/H200 rather than A100. This applies to that model's kernel path and we are not extending it to our other models."
- "Before any vLLM comparison, we record both engines' versions and chunked-prefill settings, since the ranking can shift with configuration."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **KV cache** — The stored attention state that RadixAttention indexes and reuses; the memory formula (weights + KV pool + graph buffers + activations) in the tuning guide only makes sense with it.
- (prerequisite) **Prefill and decode phases** — The benchmark docs separate `extend()` and `decode()`, and PD disaggregation profiling targets each phase separately, so TTFT versus TPOT interpretation depends on this split.
- (alternative) **vLLM** — A competing LLM serving engine that also supports prefix caching (with optional per-request salts); a comparison article says rankings can change with configuration, so the choice should rest on your own benchmark.
- (alternative) **TensorRT-LLM** — An NVIDIA-oriented inference library compared against SGLang in the project's own reproduction README (batch size 512, max input length 8192 in that setup); the provided references do not support broader claims.
- (extension) **PD disaggregation** — SGLang documents separate prefill and decode servers behind a router, and profiling must target each worker group separately due to torch profiler limitations.
- (extension) **SGLang Model Gateway** — (router) — The tuning guide points to it for better data parallelism than the `dp_size` parameter, which matters for throughput-oriented deployments.

## body_advanced_ko

## 기술적 정의와 동작 원리
SGLang은 파이썬 내장 프런트엔드 언어와 백엔드 런타임으로 구성된 LLM 실행 시스템이다. 프런트엔드는 반복·조건 분기를 포함한 다단계 생성 프로그램을 기술하고, 백엔드는 RadixAttention으로 요청 간 공통 접두부의 KV 캐시를 재사용한다. NVIDIA 릴리스 노트는 이를 반복·조건문이 있는 생성 프로그램의 KV 캐시를 관리하는 핵심 장치로 설명한다.

제어/데이터 흐름은 다음과 같다.

- 클라이언트가 HTTP로 요청을 보내면 서버 내부 스케줄러가 큐에서 요청을 꺼내 배치를 구성한다.
- 공통 접두부가 있으면 캐시된 KV를 재사용하고, 나머지 구간만 prefill한다.
- 이후 decode 배치가 반복 실행되며, 로그에는 `#running-req`, `#token`, `token usage`, `#queue-req`가 기록된다.
- 메모리는 모델 가중치 + KV 캐시 풀 + CUDA graph 버퍼 + activations로 나뉘고, `--mem-fraction-static`은 앞의 두 항목이 GPU 메모리에서 차지하는 비율을 정한다.
- KV 풀이 가득 차면 요청 회수(retract)가 일어나고 `#new_token_ratio`가 올라간다.

튜닝 절차는 다음 순서로 정리된다.

1. `#queue-req`가 0에 자주 머무르면 클라이언트 제출이 느린 것이다.
2. `token usage`와 큐 길이를 함께 본다.
3. 사용률이 낮은데 큐가 쌓이면 `--schedule-conservativeness`를 낮춘다.
4. 회수 경고가 잦으면 값을 높인다.

스케줄 정책 `lpm`(longest prefix match)은 접두부 적중을 높이지만 스케줄링 부담이 늘어난다.

복잡도나 알고리즘 상세(radix tree 연산 비용 등)는 제공된 자료에 없어 해당 주제에 대한 검증된 정보가 부족합니다.

## 핵심 하드웨어·런타임 스펙
- **Parameters**: not_published (런타임이므로 서빙하는 모델에 따라 다름)
- **Context window**: not_published (모델별. 로그 예시에는 context_len=65536이 표시됨)
- **Training data**: not_published (학습 대상이 아닌 서빙 런타임)
- **Latency / throughput**: not_published (공식 문서의 로그 예시 한 건: gen throughput 4594.01 token/s, 워크로드·하드웨어 조건 의존)

## 핵심 수식·아키텍처·도표
공식 벤치마크 문서가 구분하는 네 도구를 HTTP 서버·스케줄러 경유 여부로 정리한 표다.

| 도구 | HTTP 서버 | 스케줄러 | 용도 |
|---|---|---|---|
| bench_serving | 경유 (실행 중인 서버에 비동기 HTTP 요청) | 서버를 통해 간접 경유 | 현실적인 온라인 서빙 측정 (TTFT, TPOT, ITL, 처리량) |
| bench_one_batch_server | 경유 | 서버를 통해 간접 경유 | HTTP·스케줄러 오버헤드를 포함한 단일 배치 지연 |
| bench_offline_throughput | 미경유 | Engine을 프로세스 내에서 직접 사용 | HTTP 오버헤드 없는 최대 처리량 |
| bench_one_batch | 미경유 | 미경유 (ModelRunner 직접 호출) | 정적 배치 하나의 커널 수준 지연 |

- 기본 권고: 특별한 필요가 없으면 `bench_serving`을 쓴다.
- 정상 상태 측정: `num-prompts >= 5 * max-concurrency`를 권고한다.
- `bench_one_batch_server`는 단일 배치라 서버가 정상 상태에 들어가지 못해 지표가 편향된다고 문서가 경고한다.
- `--enable-multi-batch` 사용 시 `overall_throughput`만 권위 있는 값이고, `input_throughput`, `output_throughput`, `last_ttft`, ITL은 참고용이다.
- `bench_one_batch`는 동적 배칭이 없어 실제 서버가 처리하는 배치 크기에서도 OOM이 날 수 있다.

메모리 구성(로그 기반 점검 항목)은 다음과 같다.

- 가중치 + KV 풀 + CUDA graph 버퍼 + activations 합이 총 사용량이다.
- `available_gpu_mem`은 서버 준비 직전 로그에서 확인한다.
- 공식 문서는 activations용 여유를 경험칙으로 안내하지만, 이는 문서가 제시하는 가이드일 뿐 모든 모델·GPU에 대한 보장 값은 아니므로 자기 환경에서 검증해야 한다.

## 코드 또는 의사코드
```python
import json, shlex, subprocess, time
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass(frozen=True)
class BenchPlan:
    model: str
    base_url: str       # 이미 실행 중인 서버 (수명주기는 호출자 책임)
    max_concurrency: int
    num_prompts: int
    input_len: int
    output_len: int
    sglang_version: str  # 측정 대상 버전을 반드시 기록

def validate(p: BenchPlan) -> None:
    # 문서 권고: 정상 상태 측정을 위해 num-prompts >= 5 * max-concurrency
    if p.num_prompts < 5 * p.max_concurrency:
        raise ValueError("steady-state 미달: num_prompts < 5 * max_concurrency")
    if min(p.max_concurrency, p.input_len, p.output_len) <= 0:
        raise ValueError("양수 값이 필요함")

def build_cmd(p: BenchPlan, out: Path) -> list[str]:
    # 옵션명은 사용하는 SGLang 버전의 --help로 먼저 검증할 것
    return [
        "python3", "-m", "sglang.bench_serving",
        "--backend", "sglang",
        "--base-url", p.base_url,
        "--model", p.model,
        "--dataset-name", "random",
        "--max-concurrency", str(p.max_concurrency),
        "--num-prompts", str(p.num_prompts),
        "--random-input-len", str(p.input_len),
        "--random-output-len", str(p.output_len),
        "--output-file", str(out),
    ]

def run(p: BenchPlan, out: Path) -> dict:
    validate(p)
    cmd = build_cmd(p, out)
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:  # 실패 경로 1: 서버 미기동/옵션 불일치
        raise RuntimeError(f"bench 실패: {shlex.join(cmd)}\n{proc.stderr[-500:]}")
    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    if not rows:  # 실패 경로 2: 결과 파일 비어 있음
        raise RuntimeError("결과 JSONL이 비어 있음")
    # 워크로드와 실행 메타데이터를 함께 저장해 재현성 확보.
    # TTFT/TPOT/ITL/처리량 키는 버전별로 다를 수 있으므로 원본 행을 그대로 보존
    return {"plan": asdict(p), "cmd": cmd, "wall_s": time.time() - t0, "raw": rows}

if __name__ == "__main__":
    plan = BenchPlan("meta-llama/Llama-3.1-8B-Instruct", "http://127.0.0.1:30000",
                     16, 80, 256, 32, "fill-in-version")
    out = Path("bench.jsonl")
    assert build_cmd(plan, out)[2] == "sglang.bench_serving"  # 명령 생성 최소 테스트
    print(json.dumps(run(plan, out))[:300])
```

서버 기동은 `python -m sglang.launch_server --model-path <model>`로 별도 터미널에서 수동 실행한 뒤 위 스크립트를 돌린다. 코드는 서버를 직접 관리하지 않는다.

## 프로덕션 함정
- ❌ 실수: `#queue-req`가 0으로 자주 보이는데도 서버 설정부터 의심하고 파라미터를 바꾼다 → ✅ 해결: 먼저 클라이언트 제출 속도를 확인한다. 문서 기준 큐 길이 100–2000 범위를 목표로 제출량을 조정하고, 그 다음 `token usage`와 처리량이 달라지는지 본다.
- ❌ 실수: `token usage`가 낮고 큐가 쌓이는 상황에서 여러 옵션을 동시에 바꾼다 → ✅ 해결: 원인 진단 후 `--schedule-conservativeness` 하나만 낮춘 뒤 지연·처리량·회수 빈도를 비교한다. 회수 경고가 잦아지면 이 값을 다시 올린다. 문서상 분당 1회 안팎의 회수는 허용 범위다.
- ❌ 실수: OOM이 났을 때 단계 구분 없이 `--mem-fraction-static`부터 크게 낮춘다 → ✅ 해결: prefill 중 OOM이면 `--chunked-prefill-size`, decode 중이면 `--max-running-requests`를 먼저 조정한다. 한 번에 한 변수만 바꾸고 동시성·처리량 변화를 확인한다. 가이드의 5–8GB 같은 수치는 환경별 검증 전까지 고정 규칙으로 쓰지 않는다.
- ❌ 실수: 총 요청 수가 적은 상태에서 TTFT와 처리량을 비교한다 → ✅ 해결: `num-prompts >= 5 * max-concurrency`로 정상 상태를 확보하고, 엔진 비교 시 chunked prefill 같은 설정을 맞춰 기록한다. 이 설정에 따라 TTFT와 ITL의 순위가 달라질 수 있다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**

- 공통 접두부가 많은 워크로드: 시스템 프롬프트나 문서 앞부분이 반복되면 RadixAttention과 `--schedule-policy lpm`으로 중복 prefill을 줄일 수 있다. 다만 lpm은 스케줄링 오버헤드가 늘어난다.
- 반복·조건 분기가 있는 에이전트형 생성 프로그램: 프런트엔드 언어로 흐름을 직접 기술하고 런타임이 분기 간 캐시를 공유하는 구조라 맞는다.
- 오프라인 배치 추론: 큰 배치가 처리량의 핵심이고 `#queue-req`, `token usage`로 병목을 로그에서 직접 읽을 수 있다.
- 모델을 분류기·채점기로 쓰는 경우: v0.5.21 공지의 Decisions API와 `/v1/score`가 이 용도를 겨냥한다(프로젝트 측 발표).

**이럴 때 부적합**

- 사용하려는 모델의 특정 커널이 제한된 경우: GLM-5 비교 이슈에 따르면 FlashMLA sparse, DeepGEMM indexer, trtllm 커널은 sm_90/sm_100으로 제한되고 쿡북에 A100이 없었다. 이는 해당 GLM-5 DSA 경로에 대한 내용이며 A100 전체 미지원을 뜻하지 않는다. 해당 경로가 필요한데 A100뿐이면 H100/H200으로 바꾸거나 vLLM 등 다른 엔진을 검토한다.
- 요청 간 접두부가 거의 겹치지 않는 트래픽: 캐시 재사용 이점이 작고 lpm 재정렬 부담만 남을 수 있다. vLLM의 기본 접두부 캐싱으로 충분한지 비교해 본다.
- 요청별 캐시 격리가 필요한 환경: vLLM은 선택적 per-request salt로 재사용 범위를 제한하는 기능을 문서화한다. SGLang에 같은 기능이 있는지는 제공된 자료로 확인되지 않아 검증이 필요하다.
- 단일 배치 지연만으로 결론을 내려는 경우: `bench_one_batch_server` 결과는 편향되므로 `bench_serving`을 쓴다.

## 업계 대화 맥락
- "이번 PR은 **bench_serving** 기준으로 측정했습니다. **num-prompts를 max-concurrency의 5배 이상**으로 맞춰 정상 상태 구간만 비교했습니다."
- "**bench_one_batch_server** 수치는 단일 배치라 편향된다는 공식 경고가 있어서, 설계 문서의 근거 지표에서 제외했습니다."
- "사후 분석 결과, 로그에서 **KV cache pool is full. Retract requests**가 반복됐습니다. **schedule-conservativeness**를 한 단계만 올려 **회수 빈도와 gen throughput**을 재측정하겠습니다."
- "**lpm 스케줄 정책**은 접두부 적중을 높이지만 스케줄링 오버헤드가 늘기 때문에, 공통 접두부 비율을 먼저 확인한 뒤 켜는 걸로 하죠."
- "**A100** (sm_80)에서는 GLM-5의 DSA 커널 경로가 제한된다는 보고가 있어, 비교 실험은 **H100/H200** (sm_90) 기준으로 계약을 고정했습니다."
- "벤치마크 계약에 **하드웨어, 모델, 정밀도, 워크로드, 지표**를 명시하지 않으면 vLLM과의 우열 주장은 리뷰에서 반려하겠습니다."
- "결과 JSON에는 **SGLang 버전과 실행 명령**을 같이 남겨 주세요. 릴리스마다 옵션과 지표 키가 달라질 수 있습니다."

## 선행·대안·확장 개념
- (선행) **KV 캐시** — RadixAttention이 재사용하는 대상이며, 메모리 풀 크기와 token usage 해석의 전제 개념이다.
- (선행) **프리필과 디코드** — TTFT·TPOT·ITL을 구분하고 PD 분리 프로파일링을 이해하려면 두 단계의 성격 차이를 알아야 한다.
- (대안) **vLLM** — 같은 서빙 엔진 범주의 직접 비교 대상으로, 접두부 캐싱과 per-request salt 등 주변 기능이 달라 설정을 맞춰 비교해야 한다.
- (대안) **TensorRT-LLM** — 공식 벤치마크 README에서 SGLang의 비교 백엔드로 쓰이며, 별도 서버 구성(Triton)에 따른 설정 부담이 다르다.
- (확장) **PD 분리 서빙** — prefill과 decode 워커를 분리해 운영하는 방식으로, 프로파일링도 워커별로 따로 해야 하는 운영 확장이다.
- (확장) **SGLang Model Gateway** — (구 Router) — 공식 튜닝 문서가 dp_size 파라미터 대신 권하는 데이터 병렬 라우팅 계층이다.

## references_en

- {"title": "SGLang Release Notes", "type": "docs", "url": "https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/index.html", "tier": "primary", "annotation": "NVIDIA's official notes: what SGLang is, RadixAttention, and the monthly container release."}
- {"title": "Benchmark and Profiling - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling", "tier": "primary", "annotation": "Official guide to the four benchmark tools and metrics like TTFT, TPOT and ITL."}
- {"title": "Hyperparameter Tuning - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning", "tier": "primary", "annotation": "Memory fractions, queue health, OOM fixes and the longest-prefix-match scheduling policy."}
- {"title": "benchmark/blog_v0_2/README.md", "type": "code", "url": "https://github.com/sgl-project/sglang/blob/main/benchmark/blog_v0_2/README.md", "tier": "primary", "annotation": "Reproduction steps and hardware setup behind the project's v0.2 benchmark comparison."}
- {"title": "SGLang: The Complete Guide to High-Performance LLM Inference", "type": "blog", "url": "https://inference.net/content/sglang-complete-guide", "tier": "secondary", "annotation": "Install options, what the name stands for, and Apache 2.0 licensing as stated by a hosting provider."}
- {"title": "SGLang vs vLLM (2026): Which Is Best for Your Workload?", "type": "blog", "url": "https://tensormesh.ai/learn/vllm-vs-sglang", "tier": "secondary", "annotation": "Workload-shape checklist and a clear note on how benchmark settings can flip rankings."}
