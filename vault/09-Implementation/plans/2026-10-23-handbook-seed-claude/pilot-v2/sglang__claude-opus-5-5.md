# SGLang — claude-opus-5-5

- advanced 63 / basic 98 / gate review_required / penalty 1 / $2.9306 / 608s

## definition_en

SGLang (Structured Generation Language) is an open-source, Apache 2.0–licensed LLM serving runtime paired with a Python-embedded frontend language for writing multi-step generation programs, whose RadixAttention mechanism indexes and reuses the KV cache of shared prompt prefixes across requests and program branches — eliminating redundant computation — while a cache-aware scheduler orders requests to raise prefix hit rates.

## definition_ko

SGLang(Structured Generation Language)은 대규모 언어 모델을 위한 오픈소스 고성능 서빙 런타임이자 Python 내장형 생성 프로그래밍 언어로, RadixAttention이 여러 요청과 분기가 공유하는 프롬프트 앞부분의 KV 캐시를 트리 구조로 보관·재사용해 중복 계산을 없애고 에이전트·다단계 추론 같은 복잡한 생성 작업의 처리 효율을 높인다.

## summary_en

SGLang is free, open-source software that runs large language models on GPUs and answers many users' requests at once. Picture a copy shop that keeps a master copy of a long cover page that many customers use. When the next customer needs the same cover page, the shop only prints the new pages. SGLang does something similar: when several requests start with the same text, it can keep the model's work on that shared opening instead of redoing it. This can save GPU time for chatbots, agents, and batch jobs that repeat long instructions. The savings depend on how much of each request truly matches.

## summary_ko

SGLang은 대형 언어 모델을 서버에 올려 많은 사람의 요청을 빠르게 처리해 주는 오픈소스 엔진이다. 콜센터 상담원이 모든 고객에게 똑같이 읽어주는 공통 안내문을 한 번만 외워두고 다음 고객부터는 바로 본론에 들어가는 것과 비슷하다. 여러 요청이 같은 앞부분, 예를 들어 같은 지시문이나 예시 문장을 공유하면 그 부분의 계산 결과를 다시 쓰고, 이런 재사용이 잘 일어나도록 요청 순서도 조정한다. 같은 GPU로 더 많은 요청을 처리할 수 있어 AI 서비스 운영 비용과 응답 대기 시간을 줄이는 데 쓰인다.

## body_basic_en

## Plain Explanation
Before a language model writes a single word, it must read the whole prompt. This reading step is called **prefill**, and it produces a stored summary of the text called the **KV cache** (the model's working memory for the prompt). Many apps send the same long opening, such as a policy manual or a fixed set of examples, with every request. Without reuse, the GPU redoes that same prefill work each time.

SGLang tackles this repetition. Think of a librarian who has already read the first chapters of a popular book. When a new visitor asks about that book, the librarian only needs to read the pages that differ. SGLang's **RadixAttention** keeps the KV cache of earlier prompt openings in a tree, so requests that share a beginning can reuse it.

The reuse only covers the part that matches from the very start, token by token. Once the new request differs, the rest of its input still has to be read normally. The answer itself is always generated fresh, one token at a time, in a step called **decode**. SGLang can also reorder waiting requests so that ones with the same opening run close together, which raises the chance of a match.

## Examples & Analogies
- **Support bot with a long rulebook**: Every request starts with the same 2,000-token refund policy, then a different customer question. The policy's prefill can be reused across requests, while each question and each reply are still computed.
- **Few-shot ticket labeling at night**: A batch job sends thousands of tickets, each preceded by the same ten labeled examples. The examples are read once and reused; only each ticket's text and its short label need new work.
- **Agent that explores several branches**: A multi-step program asks the model to try three different next steps from the same conversation so far. The shared conversation history is reused by all three branches, and only each branch's new instruction and output are computed separately.

## At a Glance
| | SGLang (default) | SGLang with --disable-radix-cache | vLLM |
|---|---|---|---|
| Keeps prefix KV cache between requests | Yes, in a radix tree | No | Yes, via prefix caching |
| Who can share a cached prefix | Matching requests on the server | Nobody | Can be limited with per-request salts |
| Cache-aware scheduling | Optional lpm policy (longest prefix match) | Not applicable | Not the focus of the sources reviewed |
| Deployment interface | launch_server, OpenAI-compatible endpoint | Same | OpenAI-compatible API server |
| Best-fit workload | Many requests with shared openings | Unique prompts or clean baselines | General serving; ranking depends on tuning |

Scheduling (lpm) and cache isolation (salts) are separate knobs, and lpm's gain over the default must be measured on matched hardware, model, precision, concurrency, and prompt mix because it adds scheduling overhead.

## Where and Why It Matters
- **NVIDIA SGLang container**: NVIDIA publishes an SGLang container monthly, with release notes such as 26.07 (August 2026), giving teams a vendor-packaged way to deploy it.
- **Agent and multi-step prompting**: NVIDIA's release notes name complex agents, chain-of-thought reasoning, and few-shot prompting as common use cases, the workloads where shared openings repeat most.
- **Benchmarks need a fixed contract**: SGLang's own v0.2.7 comparison against vLLM 0.5.2 and TensorRT-LLM ran with the radix cache disabled, so those numbers do not show prefix reuse; a GLM-5 comparison issue likewise pins hardware, model, precision, workloads, and metrics before testing.
- **Hardware gating shapes deployments**: For GLM-5, SGLang's specialized kernels target newer NVIDIA GPU generations (sm_90/sm_100), so that comparison moved off A100 onto H100 or H200.
- **Prefill/decode split in practice**: Release v0.5.21 lets PD instances switch between prefill and decode roles without a restart, reducing downtime when rebalancing GPUs.

## Common Misconceptions
- ❌ Myth: Any similar-looking prompt gets a cache hit. → ✅ Reality: Only an exact match from the first token counts; a timestamp or user name placed at the top breaks reuse for everything after it.
- ❌ Myth: The cache is free extra memory. → ✅ Reality: The KV cache pool shares GPU memory with model weights; when it fills, SGLang retracts requests, and enlarging it via --mem-fraction-static risks out-of-memory errors.
- ❌ Myth: A published benchmark proves SGLang is faster for my model on my GPUs. → ✅ Reality: Results shift with prompt mix and tuning, and some model kernels only run on specific GPU generations, so test your own workload on your own hardware.

## How It Sounds in Conversation
- "Our system prompt is 3k tokens and identical for every call, so **SGLang**'s **prefix reuse** is worth a pilot before we buy more GPUs."
- "Logs keep showing **KV cache pool is full. Retract requests** at peak; let's check **token usage** before touching anything else."
- "I ran **bench_serving** with lpm and default on the same H100, same model and FP8, same 16 concurrency, and the same prompt set; TTFT diff is within noise."
- "Wait, that vendor chart used **--disable-radix-cache**, so it says nothing about our shared-prefix traffic."
- "Product wants a timestamp at the top of the prompt; that kills the **cache hit**, can we move it to the end?"

## Related Reading
- (before) **KV cache** — The stored prompt summary that SGLang reuses; understand it first to see what is actually saved.
- (before) **Prefix caching** — The general idea of reusing a matching prompt opening; SGLang's radix tree is one way to organize it.
- (similar) **vLLM** — Another open-source serving engine that also does prefix caching; compare scheduling, isolation salts, and tuning on your own workload.
- (similar) **TensorRT-LLM** — NVIDIA's serving stack used as a comparison point in SGLang's own benchmark scripts.
- (next) **Prefill/decode disaggregation** — Once prefill vs decode is clear, learn why teams run them on separate GPUs and how SGLang's PD mode routes between them.

## body_basic_ko

## 쉽게 이해하기
LLM 서비스에서는 요청마다 긴 지시문이나 같은 예시 문장이 반복해서 붙습니다. 모델은 답을 쓰기 전에 입력 전체를 읽으며 중간 계산 결과(**KV 캐시**)를 만드는데, 앞부분이 같아도 매번 새로 계산하면 GPU 시간과 메모리가 낭비됩니다. 에이전트처럼 한 작업에서 여러 번 모델을 부르는 경우 이 낭비가 더 커집니다.

SGLang은 이 반복을 줄이는 서빙 엔진입니다. 도서관 사서가 자주 찾는 책의 같은 장에 책갈피를 꽂아 두고, 다음 사람이 같은 장을 찾으면 그 자리부터 펼쳐 주는 것과 비슷합니다. 이미 읽은 앞부분은 건너뛰고 달라지는 뒷부분만 새로 처리합니다.

핵심은 **RadixAttention**입니다. 요청들의 공통 앞부분을 가지가 갈라지는 나무 모양으로 저장해, 새 요청이 오면 가장 길게 겹치는 가지를 찾아 그 계산 결과를 재사용합니다. 공통 접두사가 많은 작업이라면 `lpm`(가장 긴 접두사 일치) 정책으로 요청 순서를 바꿔 재사용을 늘릴 수 있지만, 그만큼 순서 정리 부담이 늘어납니다.

## 비유와 예시
- **같은 예시를 붙이는 few-shot 분류**: 수천 건의 문의를 분류할 때 매 요청 앞에 같은 예시 10개를 붙입니다. 이 공통 앞부분은 한 번 계산된 뒤 재사용되고, 각 문의 본문만 새로 처리됩니다.
- **공통 지시문이 긴 대량 문서 처리**: 계약서 수백 건에 같은 긴 검토 지침을 앞에 붙여 요약합니다. 접두사가 길게 겹치는 작업이라 공식 튜닝 문서는 `lpm` 스케줄 정책을 시도해 보라고 안내합니다.
- **RAG 검색 결과 재정렬**: 2026년 v0.5.21 릴리스 공지에 따르면 `/v1/score` 엔드포인트로 검색 결과 여러 건을 한 번에 다시 순위 매길 수 있습니다. 생성 대신 점수 매기기에도 같은 엔진을 쓰는 셈입니다.

## 한눈에 비교
| | SGLang (자체 운영) | vLLM (자체 운영) | 상용 LLM API |
|---|---|---|---|
| 캐시 구조 | 기수 트리로 공유 접두사 보관 | 페이징 할당 + 접두사 캐싱 | 접두사 캐싱 사용(제공사 관리) |
| 요청 스케줄링 | 캐시 적중 높이는 순서 조정(`lpm`) | 청크 prefill 크기 등으로 조정 | 제공사 내부, 사용자 제어 불가 |
| 캐시 격리 | 참고 자료에서 확인되지 않음 | 요청별 salt로 재사용 범위 제한 | 공개 정보 제한 |
| 관측 지표 | 서버 로그로 KV 캐시 점유율 확인 | 서버 지표 직접 확인 | 클라이언트 지연 측정 가능, 내부 GPU 지표 접근 제한 |

두 오픈소스 엔진 모두 페이징과 접두사 재사용을 하므로, 선택은 공통 접두사가 많은 워크로드인지와 캐시 격리·관측을 얼마나 직접 통제해야 하는지에 달려 있습니다.

## 어디서 왜 중요한가
- **GPU 세대별 지원 차이**: GLM-5 서빙에 쓰는 일부 전용 커널은 H100급(sm_90)·B200급(sm_100)에만 열려 있고 cookbook에 A100은 없습니다. 도입 전 모델·GPU 조합별 공식 지원표 확인이 필수입니다.
- **압축 모델 서빙**: `--quantization fp8` 같은 옵션으로 FP8 양자화를 시도할 수 있습니다. 다만 모델 형식과 GPU 커널 호환이 맞아야 하며, 정밀도 변경은 품질에 영향을 줄 수 있습니다.
- **NVIDIA 월간 컨테이너**: NVIDIA가 SGLang 컨테이너를 매월 배포해(2026년 8월 26.07 릴리스), 드라이버·라이브러리 조합을 직접 맞추는 부담이 줄었습니다.
- **성능 비교 절차**: 공식 `bench_serving` 도구가 첫 토큰 시간(TTFT)·토큰 간 지연(ITL)을 재므로, 같은 하드웨어·설정에서 엔진을 비교하는 기준이 생겼습니다.

## 자주 하는 오해
- ❌ 오해: 비슷한 내용이면 캐시가 재사용된다 → ✅ 실제: 요청의 앞부분이 토큰 단위로 일치하는 구간만 재사용됩니다. 지시문 맨 앞에 날짜나 사용자 이름을 넣으면 공유 구간이 사라집니다.
- ❌ 오해: 캐시는 많을수록 공짜로 이득이다 → ✅ 실제: KV 캐시 풀은 GPU 메모리 한도 안에서만 커집니다. 풀이 가득 차면 진행 중 요청을 되돌리는(retract) 경고가 뜨고, 과하게 잡으면 OOM 위험이 생깁니다.
- ❌ 오해: 캐시 공유 범위는 엔진이 알아서 안전하게 나눈다 → ✅ 실제: 여러 고객·테넌트가 한 서버를 쓴다면 요청 간 캐시 공유 경계를 직접 확인하고 설계해야 합니다.

## 대화에서는 이렇게
- "로그에 **token usage**가 0.82로 나오는데 #queue-req도 계속 쌓여요. **KV 캐시 풀**이 남는데 요청을 덜 받는 거라 schedule-conservativeness부터 낮춰 볼게요."
- "'KV cache pool is full. Retract requests.' 경고가 분당 여러 번 떠요. 캐시 부족으로 요청이 밀리는지 먼저 보고 메모리 설정을 조정하죠."
- "기동 로그 available_gpu_mem이 13GB예요. 5~8GB 여유면 충분하다니 **mem-fraction-static**을 0.01씩 올려서 캐시 풀을 키워 봅시다."
- "이번 배치는 같은 검토 지침이 앞에 붙으니까 **SGLang** 스케줄 정책을 lpm으로 바꿔서 캐시 적중률 비교해 주세요."
- "vLLM이랑 비교는 금요일까지 **bench_serving**으로 같은 H100, 같은 프롬프트 길이에서 TTFT·ITL 맞춰서 뽑아요."

## 함께 읽으면 좋은 용어
- (기초) **KV 캐시** — SGLang이 아끼려는 대상 자체라, 무엇을 재사용하는지 먼저 알아야 메모리 튜닝이 이해됩니다.
- (유사) **vLLM** — 같은 오픈소스 서빙 엔진으로, 캐시 격리(salt)와 스케줄링 방식 차이를 비교해 보기 좋습니다.
- (유사) **TensorRT-LLM** — NVIDIA 쪽 서빙 스택으로, 하드웨어 최적화와 설정 부담의 트레이드오프를 비교할 수 있습니다.
- (심화) **프리픽스 캐싱** — 상용 API와 오픈소스 엔진이 공통으로 쓰는 재사용 원리를 일반화해서 이해하는 다음 단계입니다.
- (심화) **PD 분리** — 입력 처리(prefill)와 생성(decode)을 다른 서버로 나누는 대규모 운영 단계로 넘어갈 때 읽으면 좋습니다.

## body_advanced_en

## Technical Definition & How It Works
**SGLang** is an LLM/VLM serving system with two layers: a Python-embedded **frontend language** for multi-step generation programs, and a **backend runtime**. The runtime has three layers. An HTTP server is launched with `sglang.launch_server`. An in-process **`Engine`** owns the **scheduler**. A **`ModelRunner`** executes the model through `extend()` (prefill) and `decode()` calls. Its core memory mechanism is **RadixAttention**, which indexes KV-cache entries in a radix tree keyed by token prefixes, so requests and program branches that share a prefix reuse cached KV instead of recomputing it.

Runtime flow, assembled from the official benchmark/profiling and hyperparameter-tuning docs:

- **Ingress**: a request arrives over HTTP or through `engine.generate()` in-process. For data parallelism, the docs point to the **SGLang Model Gateway** (formerly Router) instead of `--dp-size`. In **PD disaggregation** mode, `sglang_router` fronts separate prefill workers (`--disaggregation-mode prefill`) and decode workers (`--disaggregation-mode decode`).
- **Prefix match**: the radix tree is searched for the longest cached prefix. Only the unmatched suffix needs prefill compute.
- **Admission**: requests wait in a queue, visible as `#queue-req` in the logs. The default policy admits in arrival order. `--schedule-policy lpm` reorders by longest prefix match to raise hit rate, at the cost of extra scheduling overhead.
- **Admission budget**: three knobs bound admission. `--schedule-conservativeness` sets how much future decode headroom is reserved; it matters when `max_new_tokens` is large but requests stop early on EOS. `--max-running-requests` caps the batch, and the KV pool size (`max_total_num_tokens`) caps total cached tokens.
- **Execution**: prefill runs in chunks of `--chunked-prefill-size`, so a long prompt does not need one giant activation buffer. Decode steps are batched. **CUDA graphs** replay decode for batch sizes up to `--cuda-graph-max-bs-decode`.
- **Cache update and pressure**: newly computed KV becomes reusable through the tree. When the pool is exhausted, the scheduler logs `KV cache pool is full. Retract requests.`, retracts running requests back to the queue, and raises `new_token_ratio`. Verified information on the exact eviction ordering policy is limited.
- **Response**: output tokens return to the client. Client-side tools measure **TTFT**, **TPOT**, **ITL**, and throughput.

Cost model: prefill work scales with the *unmatched* suffix length, not the full prompt. The engine is profitable when shared prefixes are long and reuse is frequent. No single paper benchmark table appears in the reference set; the figures under specs are vendor-reported release or PR numbers.

## Key Hardware and Runtime Specs
- **Latency / throughput**: 4594.01 gen tokens/s at 233 running requests, token usage 0.82 (illustrative steady-state log line in the official tuning doc; hardware and model not stated)
- **Benchmarks**:
  - Time to first token, DeepSeek-V4.1 Flash: 22% faster — long prompts; v0.5.21 release announcement (vendor-reported, no setup disclosed)
  - Prefill throughput, Kimi K3: +20.6% — PD-disaggregated serving; v0.5.21 release announcement (vendor-reported)
  - FLUX.3 NVFP4 vs prior build: +8.88% T2I / +7.84% I2I (base); -4.05% T2I (distilled) — PR #44493 diffusion fix; per-server peak allocated memory unchanged across 12 workload rows

## Formulas, Architecture, and Diagrams
Per-GPU memory accounting from the tuning doc. `mem_fraction_static` is relative to the capacity of each GPU, so under tensor parallelism you evaluate it per device against that device's weight shard:

$$M_{total} = M_{weights} + M_{KV\,pool} + M_{CUDA\,graph} + M_{activations}$$

$$\text{mem\_fraction\_static} = \frac{M_{weights} + M_{KV\,pool}}{M_{GPU}}$$

The remainder, $$M_{GPU}(1-\text{mem\_fraction\_static})$$, must cover CUDA-graph buffers plus activations. The doc's rule of thumb is that 5–8 GB of `available_gpu_mem` at startup is sufficient.

Configured capacity and observed concurrency are different quantities. Do not conflate them.

| Quantity | Kind | Source in logs | Example value |
|---|---|---|---|
| `max_total_num_tokens` | configured KV pool capacity (tokens) | startup line | 665690 |
| `max_running_requests` | configured batch cap | startup line | 4096 |
| `context_len` | configured per-request max | startup line | 65536 |
| `#running-req` | observed concurrency | `Decode batch.` line | 233 |
| `token usage` | observed KV utilization (fraction) | `Decode batch.` line | 0.82 |
| `#queue-req` | observed backlog | `Decode batch.` line | 317 |

The example values come from two different log lines in the doc and are not one consistent run. A cap of 4096 does not imply 4096 requests will run concurrently: the KV token budget and conservativeness usually bind first.

Workload-to-flag matrix:

| Symptom | Flag | Direction | Cost |
|---|---|---|---|
| `available_gpu_mem` 10–20 GB | `--mem-fraction-static` | raise in 0.01 steps | OOM risk if overshot |
| OOM during prefill | `--chunked-prefill-size` | 4096 or 2048 | slower long-prompt prefill |
| OOM during decode | `--max-running-requests` | lower | lower peak throughput |
| usage < 0.9 with queue > 0 | `--schedule-conservativeness` | ~0.3 | more retractions |
| frequent retractions | `--schedule-conservativeness` | ~1.3 | lower utilization |
| large TP, big decode batches | `--cuda-graph-max-bs-decode` | 512–768 | graph memory; lower mem fraction |
| many shared prefixes | `--schedule-policy lpm` | enable | scheduling overhead |

## Code or Pseudocode
```python
import re
from datetime import datetime

# Rules transcribed from docs.sglang.io 'Hyperparameter Tuning'; log formats as shown
# there (2025-08 sample). Re-verify regexes against your release before trusting output.
TS = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\]")
DECODE = re.compile(r"Decode batch\..*?token usage: ([\d.]+).*?#queue-req: (\d+)")
MEM = re.compile(r"available_gpu_mem=([\d.]+) GB")
RETRACT = "KV cache pool is full. Retract requests."

def analyze(lines: list[str], min_samples: int = 5) -> list[str]:
    usage: list[float] = []; queue: list[int] = []
    retracts: list[datetime] = []; stamps: list[datetime] = []
    mem, seen = None, set()
    for raw in lines:
        if not isinstance(raw, str) or raw in seen:  # HEURISTIC: exact repeats = fan-in dupes
            continue
        seen.add(raw)
        m = TS.match(raw)
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") if m else None
        if t:
            stamps.append(t)
        if d := DECODE.search(raw):           # decode phase only; prefill lines are not
            usage.append(float(d.group(1)))  # documented, so they are ignored on purpose
            queue.append(int(d.group(2)))
        elif RETRACT in raw and t:
            retracts.append(t)
        elif g := MEM.search(raw):
            mem = float(g.group(1))
    advice: set[str] = set()                  # set = deduplicated recommendations
    if mem is not None:                       # documented: 5-8 GB is the target band
        if mem > 8: advice.add("raise --mem-fraction-static")
        elif mem < 5: advice.add("lower --mem-fraction-static (OOM risk)")
    if len(usage) >= min_samples:             # need a steady-state window, not one batch
        n = len(usage)                        # HEURISTIC: 'frequently' := >50% of samples
        if sum(q == 0 for q in queue) / n > 0.5:
            advice.add("client submits too slowly (#queue-req ~0)")
        if sum(u < 0.9 and q > 0 for u, q in zip(usage, queue)) / n > 0.5:
            advice.add("decrease --schedule-conservativeness (~0.3)")
    span = (max(stamps) - min(stamps)).total_seconds() / 60 if len(stamps) > 1 else 0.0
    if span > 0 and len(retracts) / span > 1.0:   # documented: ~1/min is acceptable
        advice.add("increase --schedule-conservativeness (~1.3)")
    return sorted(advice)

if __name__ == "__main__":
    line = ("[2025-08-11 17:17:{:02d}] Decode batch. #running-req: 233, #token: 370959, "
            "token usage: 0.82, cuda graph: True, gen throughput (token/s): 4594.01, #queue-req: 317")
    logs = [line.format(s) for s in range(6)] + [line.format(0), "garbage", None,
            "[2025-08-11 17:17:03] max_total_num_tokens=665690, available_gpu_mem=13.50 GB"]
    out = analyze(logs)  # repeated line, malformed line, non-str all tolerated
    assert out == ["decrease --schedule-conservativeness (~0.3)", "raise --mem-fraction-static"]
    assert analyze([]) == []                    # absent measurements -> no advice
    assert analyze([line.format(1)]) == []      # one sample is below steady-state floor
    print(out)
```

## Production Pitfalls
- ❌ Mistake: Quoting `bench_one_batch` numbers as serving capacity, although it calls `ModelRunner` `extend()`/`decode()` on a static batch with no scheduler or dynamic batching → ✅ Fix: Use it only to profile individual kernels. It can OOM at batch sizes a real server handles, because the real server chunks prefill.
- ❌ Mistake: Treating `bench_one_batch_server` output as steady-state latency, even though one HTTP batch never reaches steady state → ✅ Fix: Use it for HTTP-plus-scheduler single-batch latency. Add `--enable-multi-batch` with batch size a multiple of `--max-running-requests`, and then trust only `overall_throughput`.
- ❌ Mistake: Comparing `bench_offline_throughput` figures against an HTTP endpoint's SLA, ignoring that it drives `Engine` in-process with all prompts submitted at once → ✅ Fix: Report it as the no-network throughput ceiling, and run `bench_serving` with `num-prompts >= 5 * max-concurrency` for online TTFT/TPOT/ITL.
- ❌ Mistake: Benchmarking with real prompts while forced past EOS, which skews outputs toward gibberish and inflates decode length → ✅ Fix: Pass `--disable-ignore-eos`, then read the steady-state columns computed only over the window where every request is still decoding.
- ❌ Mistake: Raising `--cuda-graph-max-bs-decode` to 512+ without adjusting memory, then hitting OOM at startup or under load → ✅ Fix: Lower `--mem-fraction-static` at the same time, and recheck that `available_gpu_mem` stays in the 5–8 GB band.

## Tradeoffs — When to Use What
Suitable:

- **Agent, few-shot, or multi-branch programs with long shared prefixes.** Prefill cost drops to the unmatched suffix, and `lpm` reordering further raises reuse; the price is added scheduler overhead.
- **Throughput-bound offline batch jobs.** The docs name batch size as the dominant lever. `Engine.generate()` in-process removes HTTP overhead, and the logs (`token usage`, `#queue-req`) give a direct tuning loop.
- **Mixed NVIDIA/AMD fleets.** The v0.5.21 release reports GLM-5.3-Flash running on AMD MI355X with FP8/MXFP4 MoE and MTP. Verify each model's kernel path before committing.
- **Prefill-heavy, large-scale serving.** PD disaggregation splits prefill and decode workers behind the router; v0.5.21 lets an instance switch roles without restart.

Unsuitable:

- **A100 (sm_80) fleets serving GLM-5 with DSA kernels.** Per a third-party benchmark-contract issue, FlashMLA sparse, the DeepGEMM indexer, and trtllm kernels are gated to sm_90/sm_100, and the cookbook does not list A100. This statement is scoped to that model and kernel path. Consider **vLLM** after confirming its own support matrix.
- **Tenant-isolated prefix sharing.** vLLM exposes per-request cache salts that restrict reuse to matching salts. SGLang's cache plus scheduler design is aimed at maximizing hits instead, so multi-tenant isolation requirements favor **vLLM**.
- **Low-ops teams with no GPU tuning capacity.** Memory fraction, conservativeness, and chunk size need per-workload tuning. A managed API (**OpenAI**-style hosted endpoint) trades per-token cost for zero runtime ownership.
- **Unique-prompt traffic with negligible shared prefixes.** Radix reuse yields little benefit there. Any comparable engine (**vLLM**, **TensorRT-LLM**) should be selected on measured TTFT/TPOT for your workload, not on cache design.

## Industry Communication
Illustrative statements; all figures are hypothetical unless noted.

- "Observation: under the **v0.5.x** canary, `Decode batch` logs show **token usage at 0.78–0.84** with **#queue-req above 300**. That is the documented under-admission signature, not a capacity limit."
- "Hypothesis, not yet confirmed: our clients send `max_new_tokens=4096` but most completions hit EOS early, so the scheduler over-reserves; this matches the doc's description of an overly conservative server."
- "Proposed experiment: drop **`--schedule-conservativeness` to 0.3** on one replica and track the **retraction rate per minute** against the ~1/min tolerance before rolling wider."
- "PR review: please don't cite `bench_one_batch` numbers in the capacity doc. It bypasses the scheduler, so rerun with **`bench_serving`** at `num-prompts >= 5x max-concurrency`."
- "Postmortem observation: decode-phase OOMs began after we raised **`--cuda-graph-max-bs-decode` to 768**. Startup logs show `available_gpu_mem` fell below **5 GB**."
- "Postmortem action item: lower **`--mem-fraction-static` by 0.02** and gate future graph-size changes on the startup memory check."
- "Design doc: the GLM-5 comparison is pinned to **H100/H200** (sm_90), because the DSA kernel path is gated there. A100 results are out of scope rather than negative."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **KV Cache** — Conceptual relationship: RadixAttention, the KV pool, and `mem-fraction-static` all manage this structure, so its per-token memory cost explains why pool capacity bounds concurrency.
- (prerequisite) **Prefill and Decode Phases** — Conceptual relationship: chunked prefill, decode CUDA graphs, and the separate OOM remedies map onto these two phases with different compute and memory profiles.
- (alternative) **vLLM** — Competing open-source serving engine that also does prefix caching on paged blocks and adds per-request cache salts; the default comparison target in SGLang's own benchmark scripts.
- (alternative) **TensorRT-LLM** — NVIDIA serving stack benchmarked alongside SGLang in the v0.2.7 reproduction scripts (batch 512, 8192 max tokens); a better choice when NVIDIA-specific compilation is the priority.
- (extension) **PD Disaggregation** — Builds on the runtime by placing prefill and decode on separate workers behind `sglang_router`; it pushes past single-instance prefill/decode interference and requires per-role profiling.

## body_advanced_ko

## 기술적 정의와 동작 원리
**SGLang**은 Python 내장 프론트엔드 언어와 GPU 서빙 런타임으로 이루어진 LLM 실행 시스템이다. 런타임은 HTTP 서버, 요청을 배치로 묶는 **scheduler**, 실제 forward를 수행하는 **ModelRunner**로 나뉜다. 프롬프트 접두부의 KV 캐시는 **RadixAttention**이 관리한다.

**검증된 계층 구조** (공식 benchmark 문서 기준): 공식 문서는 측정 도구를 스택 계층에 대응시켜 설명한다. 이 대응을 따라가면 요청의 제어 흐름이 드러난다.
- HTTP 클라이언트 → `launch_server`의 HTTP 서버 → scheduler(`Engine`) → `ModelRunner`의 `extend()`(prefill)와 `decode()` 순으로 내려간다.
- 실제 서버는 긴 prefill을 작은 배치로 나누는 **chunked prefill**과 **동적 배치**를 수행한다. 그래서 정적 배치로 `ModelRunner`를 직접 호출하면 서버가 감당하는 배치 크기에서도 OOM이 날 수 있다.

**검증된 메모리·스케줄링 동작** (튜닝 문서 기준):
- GPU 메모리는 가중치, KV cache pool, CUDA graph 버퍼, activation 네 덩어리로 나뉜다. `--mem-fraction-static`은 이 중 앞의 두 덩어리가 차지하는 비율을 정한다.
- scheduler는 대기열(`#queue-req`)에 있는 요청을 KV pool 여유에 맞춰 받아들인다. pool이 가득 차면 실행 중인 요청을 **retract**한다.
- `--schedule-policy lpm`(longest prefix match)은 접두부가 겹치는 요청을 앞으로 재배열해 캐시 적중을 늘린다. 대신 스케줄링 오버헤드가 커진다.
- decode는 기본적으로 작은 배치 크기(예: 160 또는 256 미만)에서만 CUDA graph로 실행된다.

**미검증 영역**: RadixAttention의 트리 노드 구조, eviction 정책, 탐색 복잡도는 해당 주제에 대한 검증된 정보가 부족합니다. 위 동작 설명은 공개 문서에 적힌 플래그와 로그로 관찰되는 수준까지로 한정한다. 공식 문서는 모델 성능 benchmark 점수를 제시하지 않으며, 측정 도구와 측정 방법만 제공한다.

## 핵심 하드웨어·런타임 스펙
- **Benchmarks**:
  - bench_serving: HTTP 서버 포함 / scheduler 간접 경유 — 공식 기본 권장 도구. 비동기 HTTP 부하로 TTFT·TPOT·ITL·throughput 측정, num-prompts ≥ 5 × max-concurrency 권장
  - bench_one_batch_server: HTTP 서버 포함 / scheduler 간접 경유 — 단일 배치라 steady-state에 도달하지 않아 지표가 편향됨
  - bench_offline_throughput: HTTP 서버 없음 / scheduler 직접(Engine in-process) — 네트워크 오버헤드를 뺀 최대 throughput 측정
  - bench_one_batch: HTTP 서버 없음 / scheduler 없음(ModelRunner 직접 호출) — 정적 배치 커널 프로파일링용. 지표 자체는 비현실적

## 핵심 수식·아키텍처·도표
공식 튜닝 문서에 나오는 메모리 모델은 다음과 같다. W는 가중치, KV는 KV cache pool, G는 CUDA graph 버퍼, A는 activation, M은 GPU 메모리 용량이다.

$$M_{used} = W + KV + G + A$$

$$\text{mem\_fraction\_static} = \frac{W + KV}{M}$$

이 비율을 높이면 KV pool이 커져 동시 처리 가능한 요청 수가 늘어난다. 반대로 G와 A에 쓸 여유가 줄어든다. 서버 기동 로그의 `available_gpu_mem`이 5–8 GB 범위에 있으면 적정하다고 본다.

| 플래그 | 관찰 신호 | 조정 방향 | 비용 |
|---|---|---|---|
| `--mem-fraction-static` | available_gpu_mem 10–20 GB | 0.01씩 상향 | OOM 위험 증가 |
| `--schedule-conservativeness` | token usage < 0.9이면서 queue > 0 | 0.3 근처로 하향 | retract 빈도 증가 |
| `--schedule-conservativeness` | retract 경고가 잦음 | 1.3 근처로 상향 | KV pool 활용률 하락 |
| `--chunked-prefill-size` | prefill 단계 OOM | 4096 또는 2048로 축소 | 긴 프롬프트의 prefill 속도 저하 |
| `--max-running-requests` | decode 단계 OOM | 하향 | 동시성 감소 |
| `--cuda-graph-max-bs-decode` | 큰 TP에서 대배치 decode | 512–768로 상향 | 메모리 추가 소모 |

병렬화의 경우, 공식 튜닝 가이드는 GPU 메모리가 충분하면 throughput 목적에는 data parallelism을 우선하라고 권한다. 이때 `dp_size` 파라미터보다 SGLang Model Gateway 사용을 권장한다.

## 코드 또는 의사코드
```python
# 대상 형식: SGLang 공식 Hyperparameter Tuning 문서의 'Decode batch.' 예시 로그.
# 버전마다 필드가 달라질 수 있으므로 누락·손상 라인은 버리지 않고 개수로 보고한다.
import re
from dataclasses import dataclass
from statistics import median

FIELD = re.compile(r"(#running-req|#token|token usage|gen throughput \(token/s\)|#queue-req): ([\d.]+)")
REQUIRED = {"token usage", "#queue-req", "gen throughput (token/s)"}

@dataclass
class Report:
    samples: int
    skipped: int
    token_usage: float
    queue_req: float
    hypotheses: list[str]

def parse_line(line: str) -> dict[str, float] | None:
    fields: dict[str, float] = {}
    for key, raw in FIELD.findall(line):
        try:
            fields[key] = float(raw)
        except ValueError:  # 예: '0.8.2' 같은 손상된 숫자
            return None
    return fields if REQUIRED <= fields.keys() else None  # 필수 필드 누락 시 None

def diagnose(lines: list[str], warmup: int = 5, window: int | None = None,
             min_samples: int = 20) -> Report:
    if warmup < 0 or min_samples < 1 or (window is not None and window < min_samples):
        raise ValueError("warmup>=0, min_samples>=1, window>=min_samples 이어야 함")
    decode = [l for l in lines if "Decode batch." in l][warmup:]  # 워밍업 구간 제외
    if window is not None:
        decode = decode[-window:]  # 최근 구간만 사용
    ok = [p for p in map(parse_line, decode) if p is not None]
    if len(ok) < min_samples:
        raise ValueError(f"steady-state 표본 부족: {len(ok)} < {min_samples}")
    usage = median(p["token usage"] for p in ok)
    queue = median(p["#queue-req"] for p in ok)
    hyp: list[str] = []  # 단정하지 않고 실험할 진단 가설로만 반환
    if queue == 0:
        hyp.append("가설: 클라이언트 제출 속도 부족 → 요청 속도를 올려 재측정")
    elif usage < 0.9:
        hyp.append("가설: 스케줄러 과보수 → --schedule-conservativeness 하향 실험")
    if queue > 2000:
        hyp.append("가설: 대기열 과다로 스케줄링 오버헤드 증가")
    return Report(len(ok), len(decode) - len(ok), usage, queue, hyp)

# 문서 예시 라인 그대로. 출력 예: Report(samples=20, skipped=0, token_usage=0.82, queue_req=317.0, ...)
GOOD = ("Decode batch. #running-req: 233, #token: 370959, token usage: 0.82, "
        "cuda graph: True, gen throughput (token/s): 4594.01, #queue-req: 317")

def test_normal() -> None:
    r = diagnose([GOOD] * 25)
    assert r.samples == 20 and r.token_usage == 0.82 and "과보수" in r.hypotheses[0]

def test_variant_order_and_timestamp() -> None:
    v = "[2025-08-11 17:17:03] Decode batch. #queue-req: 0, token usage: 0.95, gen throughput (token/s): 10.0"
    assert "제출 속도" in diagnose([v] * 25).hypotheses[0]

def test_corrupted_and_missing() -> None:
    bad = [GOOD.replace("0.82", "0.8.2"), "Decode batch. token usage: 0.5"]
    assert diagnose([GOOD] * 25 + bad * 3).skipped == 6

def test_too_few_samples() -> None:
    import pytest
    with pytest.raises(ValueError):
        diagnose([GOOD] * 10)
```

## 프로덕션 함정
- ❌ 실수: bench_one_batch로 측정한 지연 수치를 온라인 SLA 근거로 보고했다. 이 도구는 scheduler와 동적 배치를 우회하므로 실제 서비스 상황을 반영하지 못한다 → ✅ 해결: SLA 측정은 bench_serving으로 하고 num-prompts를 max-concurrency의 5배 이상으로 잡는다. bench_one_batch 결과는 커널 프로파일링에만 쓴다.
- ❌ 실수: 실제 프롬프트로 벤치마크하면서 EOS 무시를 그대로 켜 두었다. 그 결과 출력 분포가 왜곡되고 throughput이 부풀려졌다 → ✅ 해결: --disable-ignore-eos를 켜고, 전체 실행 평균 대신 모든 요청이 decode 중인 구간의 steady-state 컬럼으로 비교한다.
- ❌ 실수: OOM이 나자 단계 구분 없이 mem-fraction-static부터 크게 낮췄다. 그 탓에 최대 동시성과 peak throughput이 같이 떨어졌다 → ✅ 해결: prefill OOM이면 chunked-prefill-size를, decode OOM이면 max-running-requests를 먼저 줄인다. 원인 단계를 분리한 뒤에 조정한다.
- ❌ 실수: cuda-graph-max-bs-decode를 512로 올리면서 메모리 비율은 그대로 두었다. 그 결과 기동 직후 가용 메모리가 바닥났다 → ✅ 해결: CUDA graph 버퍼가 늘어난 만큼 mem-fraction-static을 함께 낮춘다. 기동 로그의 available_gpu_mem이 5–8 GB인지 재확인한다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**
- 시스템 프롬프트나 few-shot 접두부가 길게 공유되는 에이전트 트래픽: `lpm` 정책으로 접두부 재계산을 줄일 수 있다. 재배열에 드는 스케줄링 오버헤드보다 prefill 절감 효과가 클 때 이득이다.
- H100·H200·B200 같은 sm_90/sm_100 GPU에서 최신 모델을 서빙하는 경우: 일부 모델의 전용 커널이 이 세대에 맞춰 gated되어 있다.
- 오프라인 대량 추론: 서버 로그의 queue와 token usage만 보고 배치 크기를 키워 throughput을 끌어올리는 튜닝 루프가 문서화되어 있다.
- PD disaggregation 구성: prefill 워커와 decode 워커를 분리해 따로 프로파일링하는 경로가 공식 도구에 포함되어 있다.

**이럴 때 부적합**
- A100(sm_80)만 보유한 팀이 특정 신모델을 서빙하려는 경우: 해당 커널이 지원되지 않는다. **vLLM** 등 다른 엔진에서 해당 모델 지원 여부를 먼저 확인하는 편이 낫다.
- 테넌트 간 캐시 격리가 필수인 멀티테넌트 환경: 요청별 salt로 캐시 공유 범위를 제한하는 **vLLM**의 기능이 더 직접적인 해법이다.
- GPU를 직접 운영할 인력이 없는 소규모 팀: 메모리 튜닝과 OOM 대응 부담이 남는다. **상용 API**가 총비용 면에서 유리할 수 있다.
- NVIDIA 전용 스택에 컴파일 기반 최적화로 표준화한 조직: 기존 **TensorRT-LLM** 파이프라인에서 이전하는 비용이 크다.

## 업계 대화 맥락
- "이번 PR의 수치는 **bench_one_batch_server** 단일 배치 결과라 steady-state가 아닙니다. **bench_serving**에서 **max-concurrency 16, num-prompts 80** 조건으로 다시 측정해 첨부 부탁드립니다."
- "설계 문서 기준으로 **token usage**의 중앙값이 0.82이고 **#queue-req**는 300대입니다. 그래서 **schedule-conservativeness**를 0.3으로 내리는 실험을 먼저 제안합니다."
- "포스트모템: 배포 직후 decode 단계 **OOM**이 반복됐습니다. 원인은 **cuda-graph-max-bs-decode**를 768로 올리면서 **mem-fraction-static**을 함께 조정하지 않은 데 있었습니다."
- "**lpm** 정책을 켠 뒤 TTFT가 개선됐는지는 접두부 공유율이 낮은 트래픽에서도 검증해야 합니다. 그런 트래픽에서는 스케줄링 오버헤드만 남을 수 있기 때문입니다."
- "**PD disaggregation** 환경이라 **profile-prefill-url**과 **profile-decode-url**은 동시에 쓸 수 없습니다. 트레이스는 워커별로 두 번 수집하겠습니다."
- "vLLM과의 비교 계약은 **H200** (sm_90), 정밀도와 워크로드, 측정 지표(**TTFT·TPOT·ITL**)를 고정한 뒤에 진행합니다. A100 결과는 이번 비교에서 제외합니다."

## 선행·대안·확장 개념
- (선행) **KV Cache** — KV pool의 크기가 동시성과 retract 빈도를 결정한다. 메모리 비율 플래그를 해석하려면 토큰당 KV 메모리가 어떻게 쌓이는지 먼저 알아야 한다.
- (선행) **Prefill과 Decode** — OOM 대응, chunked prefill, CUDA graph 적용 범위가 모두 단계별로 다르게 동작한다. 두 단계의 연산 특성을 구분해야 튜닝 방향을 정할 수 있다.
- (대안) **vLLM** — 같은 자체 호스팅 서빙 문제를 다룬다. prefix caching을 하면서 요청별 salt로 캐시 공유를 제한할 수 있어, 격리 요구가 있는 환경에서 경쟁 선택지가 된다.
- (대안) **TensorRT-LLM** — NVIDIA 전용 서빙 경로다. 공식 벤치마크 재현 스크립트에 비교 대상으로 함께 등장하며, 하드웨어 종속성이 큰 대신 NVIDIA 스택에 최적화되어 있다.
- (확장) **PD Disaggregation** — SGLang 런타임 위에서 prefill 워커와 decode 워커를 분리하는 배포 형태다. router와 워커별 프로파일링이 함께 필요하다.
- (확장) **SGLang Model Gateway** — router의 후속 구성요소다. dp_size 파라미터 대신 여러 인스턴스에 걸친 data parallelism을 제공해 throughput 확장을 맡는다.

## references_en

- {"title": "SGLang Release Notes - NVIDIA Docs", "type": "docs", "url": "https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/index.html", "tier": "primary", "annotation": "NVIDIA's monthly container notes: overview of RadixAttention, use cases, and known issues per release."}
- {"title": "Benchmark and Profiling - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling", "tier": "primary", "annotation": "Which benchmark tool to use, TTFT/TPOT/ITL metrics, and how to profile prefill and decode workers separately."}
- {"title": "Hyperparameter Tuning - SGLang Documentation", "type": "docs", "url": "https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning", "tier": "primary", "annotation": "Official guide to KV cache memory, request retraction, and the lpm cache-aware scheduling option and its overhead."}
- {"title": "How to reproduce the benchmark results of SGLang (v0.2)", "type": "code", "url": "https://github.com/sgl-project/sglang/blob/main/benchmark/blog_v0_2/README.md", "tier": "primary", "annotation": "Exact versions, hardware, and flags behind SGLang's vLLM/TensorRT-LLM comparison, including disabled radix cache."}
- {"title": "SGLang vs vLLM (2026): Which Is Best for Your Workload?", "type": "blog", "url": "https://tensormesh.ai/learn/vllm-vs-sglang", "tier": "secondary", "annotation": "Separates cache allocation, retention, isolation, and scheduling; explains why tuning can flip benchmark rankings."}
- {"title": "SGLang: The Complete Guide to High-Performance LLM Inference", "type": "blog", "url": "https://inference.net/content/sglang-complete-guide", "tier": "secondary", "annotation": "Practical walkthrough of installing via pip, Docker, or Kubernetes and the frontend language plus runtime split."}
