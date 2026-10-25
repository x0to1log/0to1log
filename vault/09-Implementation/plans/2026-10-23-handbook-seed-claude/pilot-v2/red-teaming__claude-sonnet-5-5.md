# Red Teaming — claude-sonnet-5-5

- advanced 71 / basic 92 / gate pass / penalty 0 / $0.9177 / 302s

## definition_en

Red teaming is an adversarial evaluation practice that adopts an attacker's viewpoint to deliberately surface vulnerabilities and harmful behaviors in an AI system, using manual or automated probing followed by a repeated fix-and-retest loop before deployment, and extending beyond models to scrutinize governance structures and underlying design assumptions.

## definition_ko

레드티밍은 공격자의 관점에서 시스템의 취약점과 해로운 동작을 의도적으로 찾아내는 적대적 검증 활동으로, 수동 또는 자동 방식으로 모델과 시스템을 탐색한 뒤 발견된 문제를 수정하고 다시 시험하는 반복 과정을 통해 배포 전에 위험을 줄이며 기술 요소뿐 아니라 거버넌스와 설계 가정까지 점검 대상으로 삼는다.

## summary_en

Red teaming means deliberately trying to break an AI system, with permission, before real attackers or real users find the weak spots. Think of a building inspector who tests the locks and also questions the floor plan. Testers probe with tricky inputs, record what goes wrong, and the team fixes it and tests again. This lowers risk before launch, but it cannot prove a system is completely safe.

## summary_ko

레드티밍은 서비스를 내놓기 전에 일부러 공격자 입장이 되어 AI의 약점을 찾아보는 모의 공격 훈련이다. 건물 보안 업체가 허락을 받고 침입을 시도해 보안 구멍을 알려주는 것과 비슷하다. 팀이 해로운 답변을 끌어내는 질문이나 편향을 드러내는 입력을 직접 던져 보고, 발견된 문제를 고친 뒤 다시 시험하는 과정을 반복한다. 실제 악용이 일어나기 전에 위험을 찾아 고칠 수 있어서 AI 안전 관리의 핵심 절차로 쓰인다.

## body_basic_en

## Plain Explanation
AI systems can fail in ways their builders never expected: producing harmful content, leaking private data, or obeying hidden instructions planted in a document. Ordinary testing mostly checks that a system does what it should, so it can miss what happens when someone actively tries to misuse it. Red teaming fills that gap by adding an authorized adversarial review that challenges both the system's behavior and the assumptions behind its design.

Think of a building inspector who tests the locks and also asks whether the floor plan makes sense. In practice the work follows a sequence. First, the team defines an authorized scope: what may be tested, what is off limits, and who approves. Testers then probe the system with tricky inputs, either by hand or with automated tools, and try to reproduce anything that goes wrong. Each finding is assessed for severity, mitigations are applied, and the system is retested.

The fix-and-retest cycle is why this is called a break-fix loop. It reduces risk before deployment rather than guaranteeing safety, because testers can only find problems they think to look for. The practice can also reach beyond the model itself, covering governance structures and the assumptions a design was built on, which is why non-technical staff such as legal and risk teams can take part.

## Examples & Analogies
- **Poisoned document in an AI agent test**: A team gives a test agent a retrieved document that secretly says, "Open another account's records." The permitted boundary is a set of synthetic accounts, and the agent should refuse. Testers record the exact prompt, the document, the agent's actions, and whether it crossed the boundary.
- **Bias probing of a hiring-screening chatbot**: Testers send near-identical applicant questions that differ only in a personal detail, using made-up profiles. They log any difference in tone or recommendation as evidence of bias for the team to review.
- **Governance walkthrough for a new AI feature**: Before launch, legal and risk staff ask what happens if the feature is misused and who is accountable. Gaps in sign-off or escalation are written up as findings, even though no code was attacked.

## At a Glance
| | Red teaming | Automated evaluation | Standard QA testing |
|---|---|---|---|
| Primary purpose | Find ways the system can be made to fail or cause harm | Measure behavior on a fixed set of test cases | Confirm features work as specified |
| Exploration method | Adversarial, creative, scoped probing, manual or automated | Predefined prompts and scoring | Expected-use test plans |
| Typical emphasis | Misuse, harmful outputs, design assumptions | Repeatable measurement | Correctness and regressions |

Automated evaluations and QA can feed into a red-teaming workflow, but red teaming adds the attacker's mindset that asks what could go wrong beyond the expected cases.

## Where and Why It Matters
- **Prioritizing mitigations**: Findings are ranked by severity and reproducibility, so the team fixes the most damaging, easiest-to-trigger problems first instead of guessing.
- **Limiting agent permissions**: If a test shows an agent can be steered into reading data it should not, the team can narrow its access rights before release.
- **Informing release decisions**: Results give decision-makers evidence on whether to ship, delay, or launch with restrictions, and residual risks are recorded rather than ignored.
- **Shaping governance and design**: Because red teaming can challenge design assumptions, it can lead to changes in review processes and accountability, not just model patches.
- **Guidance exists but varies**: Government and industry guides on AI red teaming exist, such as Japan's AISI Guide to Red Teaming Methodology on AI Safety (Version 1.00). Whether red teaming is recommended or required depends on the jurisdiction and document.

## Common Misconceptions
- ❌ Myth: Red teaming means attacking any system you like. → ✅ Reality: It requires an approved scope, rules of engagement, and ethical boundaries agreed in advance.
- ❌ Myth: Test data can be handled casually because it is just a test. → ✅ Reality: Use synthetic or approved data, protect logs and findings, and avoid exposing real personal information.
- ❌ Myth: If the exercise finds nothing serious, the system is safe. → ✅ Reality: A clean result only means testers did not find problems within their scope and time. It does not establish complete safety.

## How It Sounds in Conversation
- "Can we get **scope approval** for the agent test before Thursday? We need the synthetic accounts listed."
- "I have a **reproducible finding**: the retrieved doc makes the agent open another account. Logs attached."
- "Assigning this **remediation** to the platform team. Can we tighten the agent's permissions first?"
- "Fix is merged. Please **retest** the same prompts and a few variants before we sign off."
- "Let's log the **residual risk** in the release notes, since we can't claim it's fully closed."

## Related Reading
- (before) **Prompt Injection** — The most common attack red teamers try on language-model apps, so learn it first.
- (before) **Guardrail** — The protective controls that red teaming tests and that findings often lead to improving.
- (similar) **Adversarial Attack** — Focuses on crafted inputs that fool a model, a narrower technique than the whole red-teaming process.
- (similar) **AI Safety Evaluation** — Measures safety against fixed criteria, which complements open-ended adversarial probing.
- (next) **Jailbreak** — A specific kind of finding red teams look for: getting a model to ignore its safety rules.
- (next) **AI Governance** — Explains how findings turn into policy, accountability, and release decisions.

## body_basic_ko

## 쉽게 이해하기
AI 서비스는 개발팀이 예상한 대로만 쓰이지 않는다. 개발팀은 자기 설계를 잘 알기 때문에 놓친 가정을 스스로 찾기 어렵고, 일반적인 기능 테스트는 명세대로 동작하는지만 확인하는 경우가 많다. 그 사이에 유해한 답변, 개인정보 노출, 도구의 의도치 않은 사용 같은 위험이 남을 수 있다.

레드티밍은 승인된 범위에서 기존 가정에 도전하는 역할과 시험 절차를 마련해 위험을 찾는 방식이다. 건물 오픈 전에 보안 점검 팀이 침입을 시도해 보는 것과 비슷하다. 참고 자료는 이를 군사 모의훈련에서 사이버보안을 거쳐 AI로 이어진 비판적 사고 훈련으로 설명하며, 모델만이 아니라 거버넌스 구조와 설계의 기본 가정까지 점검 대상으로 본다.

흐름은 이렇다. 먼저 목표와 윤리적 경계, 시험 범위를 정한다. 그다음 사람이나 자동화 도구가 적대적 입력으로 시스템을 시험한다. 문제가 나오면 같은 입력으로 재현하고 심각도를 평가한 뒤 수정하고, 고친 부분을 다시 시험한다. 이 반복을 흔히 break-fix 루프(깨뜨리고 고치는 순환)라고 부른다.

## 비유와 예시
- **고객지원 챗봇의 경계 시험**: 가상의 고객지원 서비스에서 시험 계정이 다른 고객의 주문정보를 알려 달라고 요청한다. 대상은 챗봇과 주문 조회 도구, 기대 경계는 본인 정보만 응답하는 것이며, 거절하지 못하고 응답한 경우를 실패로 기록한다. 실제 개인정보 대신 승인된 합성 데이터만 사용한다.
- **유해 답변 유도 시험**: 승인된 시험 팀이 우회 표현과 여러 턴의 대화로 금지된 내용을 끌어내 본다. 안전장치가 뚫린 입력과 응답을 저장해 두면 개발팀이 같은 조건으로 재현해 고칠 수 있다.
- **외부 연결 도구의 호출 흐름 점검**: 보안 도구가 시험용 프롬프트를 대상 시스템에 보내고 응답을 받아 오는 과정을 자동화한다. 요청 형식이나 인증 방식이 제각각인 대상도 어댑터라는 연결 코드로 같은 시험에 올릴 수 있다.

## 한눈에 비교
| | 기능 테스트 | 레드티밍 | 사고 대응 |
|---|---|---|---|
| 주목적 | 명세 충족 확인 | 적대적 탐색과 가정 검증 | 실제 사고의 억제·복구 |
| 핵심 질문 | 의도대로 동작하나 | 어떻게 깨질 수 있나 | 발생한 피해를 어떻게 막고 되돌리나 |
| 주요 산출물 | 통과·실패 결과 | 재현 가능한 취약점과 개선 권고 | 조치 기록과 복구 결과 |

세 활동은 목적과 산출물이 다르지만 범위가 겹칠 수 있고, 레드티밍은 아직 일어나지 않은 문제를 일부러 찾아 미리 수정하게 한다는 점이 특징이다.

## 어디서 왜 중요한가
- **출시 보류 판단**: 민감 정보 노출처럼 심각한 취약점이 재현되면 수정과 재시험이 끝날 때까지 출시를 미루는 근거가 된다.
- **도구 권한 축소**: 에이전트가 주문 조회나 삭제 같은 도구를 의도 밖으로 쓰는 경로가 발견되면, 해당 도구의 권한이나 접근 범위를 줄이는 결정으로 이어질 수 있다.
- **운영 정책 변경**: 반복되는 실패 유형이 확인되면 입력 제한, 응답 점검, 사람 승인 단계 같은 운영 규칙을 바꾸는 근거가 된다.
- **수정 우선순위 결정**: 재현 가능성과 피해 크기를 기준으로 어떤 문제부터 고칠지 정할 수 있다.
- **시험 범위의 사전 합의**: 목표와 윤리적 경계를 미리 정해 두면 시험이 조직의 AI 안전 전략과 어긋나지 않고 결과도 비교하기 쉬워진다.

## 자주 하는 오해
- ❌ 오해: 레드티밍은 해킹 기술을 가진 보안 전문가만 하는 일이다 → ✅ 실제: 비판적 사고 훈련이어서 경영, 법무, 위험관리 같은 비기술 인력도 참여해 거버넌스 지침을 점검할 수 있다.
- ❌ 오해: 한 번 통과하면 안전이 증명된다 → ✅ 실제: 시험은 정해진 범위와 시점의 결과일 뿐이며, 발견·수정·재시험을 되풀이하는 지속적 과정이다.
- ❌ 오해: 모델에 나쁜 질문을 던지는 것이 전부다 → ✅ 실제: 하드웨어, 소프트웨어, 네트워크, 모델은 물론 설계의 기본 가정과 거버넌스 구조까지 대상이 될 수 있다.

## 대화에서는 이렇게
- "수정한 세 건은 **같은 입력으로 다시 확인**해 주세요. 재현 로그는 티켓에 붙여 뒀습니다."
- "이번에는 **고객정보 조회 기능만 승인 범위**로 잡죠. 결제 연동은 다음 라운드로 넘기겠습니다."
- "**레드팀 결과**상 도구 권한이 너무 넓어서, 출시 전에 조회 전용으로 줄이는 안을 올릴게요."
- "시험 데이터는 전부 **합성 데이터**로 쓰고, 실패한 입력과 응답은 빠짐없이 기록해 주세요."
- "심각도 높음으로 분류된 두 건이 안 닫혔으니, 이번 주 **배포는 보류**하고 재시험 일정부터 잡겠습니다."

## 함께 읽으면 좋은 용어
- (기초) **프롬프트 인젝션** — 레드티밍에서 시험 대상이 될 수 있는 공격 유형으로, 입력으로 모델의 지시를 바꾸려는 시도다. 어떤 공격을 시험하는지 알려면 먼저 읽어 두면 좋다.
- (유사) **탈옥** — (Jailbreak) — 안전장치 우회를 시도하는 기법이다. 레드티밍의 시험 수단으로 쓰이지만, 레드티밍은 범위·기록·재시험까지 포함하는 더 넓은 절차라는 점이 다르다.
- (유사) **감사** — (Audit) — 레드티밍 결과를 증거로 활용할 수 있는 별도 검토 절차다. 적대적 탐색이 아니라 통제와 기록의 적정성을 따진다는 점이 비교 포인트다.
- (심화) **가드레일** — (Guardrail) — 레드티밍이 찾은 허점을 막는 대표적인 방어 장치다. 발견 다음 단계인 완화 방법을 이해하기에 좋다.
- (심화) **AI 안전 평가** — (AI Safety Evaluation) — 레드티밍을 포함한 더 넓은 평가 관점이다. 안전, 공정성, 프라이버시 같은 요소별로 무엇을 점검할지 정리하는 단계에서 읽기 좋다.

## body_advanced_en

## Technical Definition & How It Works
Red teaming is an adversarial evaluation workflow in which testers adopt an attacker's viewpoint to elicit vulnerabilities and harmful behaviors from an AI system, then feed the findings into a repeated fix-and-retest cycle. The reference literature frames it as a critical thinking exercise that spans micro-level model testing, macro-level system testing, and scrutiny of governance structures and design assumptions. It is therefore a workflow with several control points, not a single test suite.

A proposed engineering decomposition of the flow, synthesized from the sources rather than quoted from a single standard:

1. **Scope and authorization.** Objectives are specific (for example bias, privacy risk, prompt-injection susceptibility) and bounded by ethical rules. In the open-source orchestration harness in the references, a scope check runs first: a target that is not self-owned is refused unless an ownership artifact is supplied, and its SHA-256 is appended to an audit log. A per-invocation authorization variable gates the orchestrator.
2. **Configuration validation.** Missing target or invalid rate-limit and query-budget values stop the run before any probe is sent.
3. **Probing.** Manual or automated adversarial inputs are sent to the model or the full application. The harness runs numbered probe stages (recon, sensitivity, boundaries, evasion, extraction) and writes JSON artifacts per stage.
4. **Analysis.** Per-area analyzers interpret probe artifacts in parallel; a report generator runs last so it can incorporate their interpretations.
5. **Findings to remediation.** Each finding is triaged, assigned an owner, and patched (guardrail rule, prompt hardening, access change, or a design or policy change).
6. **Retest.** The same probes are re-run to confirm the fix holds and no new hole opened. The loop closes only on explicit acceptance criteria; otherwise the finding returns to remediation.

Where governance and design assumptions are in scope, steps 3 to 6 apply to policy and architecture decisions as well as to model behavior, and non-technical staff (management, legal, risk) can take part.

**Integration with a managed platform (documented adapter behavior).** One vendor documents a custom target adapter: a Python script that lets its AI Red Teaming product reach targets the built-in connectors do not support. The adapter runs in a sidecar on the customer's infrastructure beside the Network Channel client, so adapter code and credentials do not execute in the vendor's service. Per turn, the platform sends the script and configuration over an encrypted tunnel, the sidecar loads the script fresh and passes a context object (vars, secrets, auth, session, http), the code reaches the target and returns the reply text, and the sidecar returns the reply, any error signals, and print output. The script is stateless: only auth state and session state survive between turns. A turn succeeds only if the function returns cleanly; an exception or timeout fails the turn.

Complexity is dominated by probe volume: total cost is roughly attack-strategy count × turns per conversation × retest rounds, bounded in practice by the query budget and rate limit.

## Formulas, Architecture, and Diagrams
Proposed incident taxonomy and control matrix. The rows combine attack surfaces named in the sources (harmful content, bias, privacy leakage, prompt injection, tool misuse, governance assumptions) with engineering fields that are proposed operational conventions, not a published standard.

| Finding class | Attack path | Detection signal | Mitigation boundary | Residual risk |
|---|---|---|---|---|
| Harmful content generation | Role-play or rephrased requests that bypass refusals | Evaluator flags policy-violating output | Input/output guardrail plus model-level safety tuning | Novel phrasings not in the probe set |
| Prompt injection | Hidden instructions in user input or retrieved content | Model ignores system rules or exposes internal instructions | Instruction separation, output filtering | Indirect channels outside tested scope |
| Privacy leakage | Repeated questioning that elicits internal or training information | Sensitive strings in responses | Data minimization, response filtering | Low-frequency leakage under adaptive probing |
| Tool or agent misuse | Crafted message drives tool calls on a session or login it should not touch | Unexpected tool-call arguments in logs | Least-privilege credentials, call allow-lists, approval gates | Multi-step chains across tools |
| Bias | Paired prompts differing in a protected attribute | Divergent outputs across pairs | Data and policy review, evaluator thresholds | Context-dependent bias outside tested pairs |
| Governance or design assumption | Design review asks what happens if a core assumption is wrong | Documented assumption with no owner or test | Policy change, scope restriction, human oversight | Assumptions not yet surfaced |

Proposed evidence and closure fields to attach to every finding:

- **Evidence identifier**: unique finding ID linking the exact prompt or probe, target version, timestamp, raw response, and the artifact file. In the orchestration harness, self-certification is logged with an ISO timestamp, target, artifact path, and SHA-256.
- **Remediation owner**: a named team (model, platform, policy, or legal) accountable for the fix, plus a due date and the change reference.
- **Retest acceptance criteria**: the original probe plus a set of paraphrased variants must all fail to reproduce the harm on the patched build, and a regression subset of earlier closed findings must still pass.
- **Exception record**: when residual risk is accepted, the approver, rationale, and review date are recorded.
- **Scope record**: authorization basis, query budget used versus allowed, and probe stages executed.

## Operational Pattern and Review Procedure
Operational review procedure for wiring a target into a managed red-teaming platform through the documented custom target adapter contract. No code is shown; the contract is described so reviewers can check an adapter against it.

**Choosing the pattern**

- **Pattern A (pre_process + post_process).** Both functions are required. pre_process receives the context and the current prompt plus conversation history, and returns a PreProcessResult. Only the URL is required; the method defaults to POST. The reviewer should confirm the URL comes from context.vars, the Authorization header is built from context.secrets (never hard-coded), and the JSON body carries the prompt. Critically, the platform (AI Red Teaming) makes the HTTP call, not the adapter, and passes the response to post_process. post_process receives a RawResponse (status code, JSON body, headers) and returns a PostProcessResult whose output is the reply text. For known failure conditions it must raise the documented error signal rather than return error text as the reply. The documented example raises the rate-limited signal with a retry_after of 30 when the status code is 429, and otherwise extracts the reply field from the JSON body into the output.
- **Pattern B (call_target only).** The adapter itself sends the request through context.http and returns a CallTargetResult containing the reply directly, with no post_process step. Defining call_target disables pre_process and post_process. Use it for non-HTTP transports such as WebSocket, GraphQL, SDK clients, or custom streaming. For standard HTTP targets needing several calls, the documentation says to use context.http inside pre_process instead.

**Contrast to check in review:** in Pattern A the platform owns the network call and the adapter only shapes the request and parses the response; in Pattern B the adapter owns the call and the parsing in one function.

**Shared functions** (either pattern)

- authenticate (optional): obtains credentials and returns a TTL. The platform caches the result, exposes it as context.auth, and re-authenticates on expiry or on an authentication error with one retry. Per-request signing such as HMAC or SigV4 does not belong here; it belongs in pre_process or call_target. Non-200 token responses should raise the documented auth-error signal.
- session_pre_process (optional): runs once on the first turn of every conversation, including single-turn attacks. Its session state is available as context.session on every later turn.

**Review checklist**

1. No secrets, tokens, or endpoints are hard-coded; all come from context.vars or context.secrets, with per-target overrides used for staging versus production.
2. Known failures (rate limit, auth failure) are signaled with the documented error signals, not returned as reply text.
3. Each call completes within the 110 s overall limit and 100 s HTTP timeout; calls not covered by context.http have explicit timeouts, and no unbounded loops exist.
4. Cross-turn values are carried only through session state, kept within the combined 64 KB auth-and-session limit, since module globals are discarded each turn.
5. Only stdlib, httpx, and websockets are assumed to be available.
6. The adapter targets only an authorized, in-scope system, matching the scope record.

## Production Pitfalls
- ❌ Mistake: Returning an error string such as "rate limited" as the reply text from an adapter's post_process when the target answers HTTP 429 → ✅ Fix: Follow the documented guidance and raise the rate-limited error signal (with a retry_after value) so known failure conditions are signaled as errors instead of masquerading as target replies.
- ❌ Mistake: Hard-coding endpoints, API keys, or client secrets inside the adapter script and reusing it across staging and production → ✅ Fix: Read non-sensitive values from context.vars and sensitive values from context.secrets, and use per-target overrides; secrets are masked in the web interface and scrubbed from logs.
- ❌ Mistake: Storing conversation state in module-level variables and expecting it on the next turn, because the script is stateless and globals are discarded between turns → ✅ Fix: Return needed values from session_pre_process as session state and read them from context.session, keeping combined auth and session state within the 64 KB limit.
- ❌ Mistake: Putting per-request signing (HMAC, SigV4) inside authenticate, where the specific request is not available → ✅ Fix: Perform per-request signing in pre_process or call_target, and use authenticate only for cached credentials with a TTL.
- ❌ Mistake: Declaring a finding closed after a single patched probe passes, or running probes without a defined scope, objective, and ethical boundary → ✅ Fix: Define specific objectives and boundaries up front, and close findings only after retesting the original probe, paraphrase variants, and a regression set, since the cycle is repeated break-fix.

## Tradeoffs — When to Use What
Suitable (qualified by engagement goals, target access, and evaluation requirements):

- **Pre-deployment assurance of a system whose misuse paths are unknown.** When the goal is to discover harmful content, bias, privacy leakage, or injection susceptibility before launch, adversarial probing finds failures that fixed benchmark scores do not. Requires write-access to a staging target and agreed scope.
- **Agentic or tool-connected applications.** When the application can call external tools, system-level testing is needed because the risk sits in the integration, not only in the model. Requires visibility into tool-call logs to detect misuse.
- **Governance and design-assumption review.** When the question is whether a design's foundational assumptions hold, a facilitated red-team exercise with legal and risk staff needs no model access at all and is cheap relative to late-stage rework.
- **Targets behind non-standard auth, sessions, or protocols.** When the target uses custom request formats, fresh per-request values, pre-created sessions, or non-standard transports, a custom adapter lets an automated platform run at scale; the adapter code and credentials stay on your infrastructure.

Unsuitable or weaker fit:

- **You only need regression scores on fixed tasks.** Use an automated benchmark evaluation pipeline; red teaming costs more per result and is not designed to produce comparable scores.
- **You need to confirm features meet specified requirements.** Standard QA testing is the right tool; red teaming asks how the system can be made to fail, not whether it meets the spec.
- **The target is a standard integration differing only by header or base URL, or uses standard OAuth.** The vendor guidance is to use a built-in connector rather than writing an adapter, which avoids maintaining custom code.
- **No authorization or scope exists for the target.** Do not proceed; obtain written scope first. Without an ownership basis, a one-off review of a third-party system should be replaced by a vendor-run assessment or the provider's coordinated disclosure channel.

Cost trade-off: more probe volume raises coverage but also query budget, rate-limit pressure, and analyst triage load; a single pass gives a point-in-time result, so continuous retesting is needed after each model, prompt, or tool change.

## Industry Communication
- "Hypothetical PR comment: the new adapter uses **Pattern A**, but **post_process** returns the string 'too many requests' as the reply on a **429**; per the documented contract, please **raise the rate-limited signal with retry_after** instead of returning error text."
- "Design-doc note (hypothetical): we chose **call_target** over **pre_process/post_process** because the assistant endpoint speaks **WebSocket**; **defining call_target disables the other two**, so all parsing lives in one function."
- "Review remark (hypothetical): the **API key** is inlined in the script; move it to **context.secrets** and use a **per-target override** so staging and production don't share credentials."
- "Hypothetical postmortem: the multi-turn probe lost its conversation ID on turn two because we stored it in a **module-level global**; the script is **stateless**, so it must be returned via **session_pre_process** as session state."
- "Scope review (hypothetical): the target failed the **scope check** and we have no **self-certification artifact** on file, so the engagement is blocked until ownership is documented and its **SHA-256** is logged to the audit trail."
- "Findings triage (hypothetical): finding **RT-014**, a **prompt-injection** bypass on the tool-calling path, is assigned to the platform team with **retest acceptance criteria** covering the original probe, three paraphrases, and the regression subset."
- "Closure note (hypothetical): the fix to **RT-014** passed the original probe but one **paraphrased variant** still succeeded, so the finding returns to **remediation** and the break-fix loop stays open."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Prompt Injection** — A frequently probed attack class in LLM red teaming; understanding how hidden instructions override rules clarifies what probes target and what detection signals to define.
- (prerequisite) **AI Alignment** — Related concept that supplies the intended-behavior baseline red teaming tests against; not a strict technical prerequisite for running probes.
- (alternative) **Automated Benchmark Evaluation** — Scores a model on fixed test sets for comparable metrics; cheaper to repeat but does not search for unexpected exploits the way adversarial probing does.
- (alternative) **Standard QA Testing** — Checks behavior against specified requirements; complements red teaming but does not adopt an attacker's mindset.
- (extension) **Guardrail** — The defensive control that red teaming findings typically harden; retest confirms whether a rule change actually closes the bypass.
- (extension) **Audit** — Related concept that takes red-teaming evidence (finding IDs, remediation owners, retest results, exception records) and uses it for governance and compliance review.

## body_advanced_ko

## 기술적 정의와 동작 원리
레드티밍은 공격자 관점의 적대적 입력으로 시스템의 취약점과 유해 동작을 찾고, 발견 사항을 수정한 뒤 재시험하는 break-fix 루프를 되풀이하는 검증 워크플로우다. 대상은 모델(마이크로 수준)뿐 아니라 시스템 전체와 거버넌스, 설계 가정(매크로 수준)까지 포함하며, 참고 자료는 이 둘의 조율을 메타 수준 레드티밍이라고 부른다. 수동·자동 탐색은 모두 가능하며 목표와 윤리적 경계를 먼저 정하는 것이 전제다.

실행 흐름은 다음과 같다.

1. **범위·목표 확정**: 편향, 프라이버시, 프롬프트 인젝션 등 구체 목표와 윤리 경계를 정한다.
2. **대상 연결**: 테스트 도구가 대상 앱·에이전트·모델과 통신할 접점을 만든다.
3. **적대적 탐색**: 프롬프트별로 대상 응답을 수집하고 유해성·취약성을 판정한다.
4. **수정과 재시험**: 발견 사항을 고친 뒤 같은 시나리오를 다시 돌려 루프를 닫는다.

3번 단계의 연결 방식은 Palo Alto Networks Prisma AIRS 문서의 커스텀 타깃 어댑터 계약에 두 패턴으로 나온다. 이는 한 제품의 구현 예이며 레드티밍 일반 규격이 아니다.

- **Pattern A**: `pre_process`와 `post_process`가 모두 필요하다. `pre_process`가 URL, 헤더, 본문을 반환하면 실제 HTTP 호출은 AI Red Teaming 플랫폼이 수행하고, 응답은 `post_process`로 넘어가 답변 텍스트가 추출된다.
- **Pattern B**: `call_target`만 정의한다. 어댑터가 직접 대상에 요청을 보내 답변을 곧바로 반환하며 별도의 `post_process` 단계가 없다. 정의하면 `pre_process`/`post_process`는 비활성화되고, 비HTTP 전송(WebSocket, GraphQL, SDK 등)에 쓴다.

어댑터 코드와 자격 증명은 사용자 인프라의 sidecar에서 실행되고 AI Red Teaming 쪽에서는 실행되지 않는다. 스크립트는 매 턴 새로 로드되며 턴 사이에 유지되는 상태는 auth와 session 상태뿐이다.

## 핵심 수식·아키텍처·도표
**① 출처 기반 실행 흐름** (Prisma AIRS 어댑터 문서 기준, 한 제품의 구현)

- Pattern A: `pre_process` → 플랫폼 HTTP 호출 → `post_process`
- Pattern B: `call_target` → 직접 반환
- 공통(선택): `authenticate`(결과를 캐시하고 만료·인증 오류 시 1회 재인증), `session_pre_process`(대화 첫 턴에 1회 실행)
- 런타임 제한: 호출당 전체 110초, 대상 HTTP 타임아웃 100초, auth+session 상태 합계 64KB. 오류나 타임아웃이면 해당 턴은 실패로 처리된다.

**② 제안 통제 매트릭스** (아래는 출처에 없는 설계 제안이며 조직별로 조정한다)

| 통제 목표 | 탐지 신호 | 완화 경계 | 잔여 위험 |
|---|---|---|---|
| 승인 범위 이탈 방지 | 대상이 승인 목록에 없음 | 스코프 검증 후 실행, 감사 로그 기록 | 목록 자체의 오류 |
| 유해 출력 발견 | 우회 프롬프트 성공 사례 | 방어 규칙 보강 후 동일 시나리오 재시험 | 미시도 공격 유형 |
| 오류와 취약점 구분 | 429·인증 오류 | 응답 본문이 아닌 오류 신호로 보고 | 신호 누락 시 거짓 음성 |
| 거버넌스 가정 점검 | 설계 가정과 운영 현실의 불일치 | 법무·리스크 참여 리뷰 | 조직 합의 지연 |

공개 저장소의 오케스트레이션 문서(bdfinst/agentic-dev-team)에는 스코프 검증 후 실행, 승인 환경 변수 게이트, 분석 에이전트 후속 실행, 에스컬레이션 조건이 사례로 나온다. 이 역시 한 구현 예일 뿐이다.

## 운영 패턴과 검수 절차
이 섹션은 코드 없이 문서에 나온 어댑터 계약을 따르는 운영 검토 절차다.

- **패턴 선택**: 표준 HTTP 대상이면 Pattern A, 비HTTP 전송이면 Pattern B를 택한다. 다중 호출이 필요한 표준 HTTP 대상은 `pre_process` 안에서 `context.http`를 쓴다.
- **요청 구성 검토** (`pre_process`): `PreProcessResult`의 `url`만 필수이고 `method` 기본값은 POST다. 문서 예제는 `url`을 `context.vars["endpoint"]`에서 읽고, `Authorization: Bearer` 헤더를 `context.secrets["api_key"]`로 만들며, `json_body={"message": inference_input.prompt}`로 본문을 구성한다. 비밀값은 `secrets`, 비민감 값은 `vars`에 둔다.
- **응답 처리 검토** (`post_process`): 문서 예제는 `status_code`가 429이면 `raise_rate_limited(retry_after=30)`로 오류 신호를 올리고, 정상이면 `json_body["reply"]`를 `PostProcessResult(output=...)`로 반환한다. 속도 제한 같은 알려진 실패를 응답 텍스트로 돌려주면 대상의 실제 답변과 구분되지 않으므로 반드시 오류 신호로 올린다. 인증 오류도 같은 원칙이며, 문서의 `authenticate` 예제는 토큰 엔드포인트가 200이 아니면 `raise_auth_error`를 호출한다.
- **Pattern B 검토**: `call_target`이 `context.http.post`로 직접 호출하고 `CallTargetResult(output=...)`로 답변을 반환한다. 이 경로의 오류도 예외나 타임아웃으로 턴 실패 처리되므로 정상 응답과 실패를 섞지 않는다.
- **상태 검토**: 모듈 전역 변수는 턴마다 폐기되므로 턴 간 값은 `session_state`로만 전달한다. 요청별 서명(HMAC 등)은 `authenticate`가 아니라 `pre_process`나 `call_target`에 둔다.
- **한계 검토**: 110초, 100초, 64KB 한도 안에서 끝나도록 무한 루프를 피한다.

## 프로덕션 함정
- ❌ 실수: 429나 인증 실패 같은 알려진 오류를 에러 문구 그대로 reply로 반환해 모델의 답변처럼 기록한다 → ✅ 해결: 문서 계약대로 `raise_rate_limited` 같은 오류 신호를 올려 실패 턴과 정상 응답을 분리한다.
- ❌ 실수: 턴 간에 모듈 전역 변수로 세션 ID나 토큰을 들고 간다 → ✅ 해결: 스크립트는 매 턴 새로 로드되어 상태가 폐기되므로 `session_state`와 `authenticate` 결과로만 상태를 전달하고 64KB 한도를 지킨다.
- ❌ 실수: 요청별 서명을 `authenticate()`에 넣는다 → ✅ 해결: 개별 요청이 아직 없는 함수이므로 HMAC, SigV4 같은 서명은 `pre_process()`나 `call_target()`에 둔다.
- ❌ 실수: 수정 후 재시험 없이 발견 목록만 닫고 통과로 간주한다 → ✅ 해결: 동일 시나리오를 다시 실행해 break-fix 루프를 닫고 목표·범위·윤리 경계를 문서화한다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**
- 출시 전 해로운 콘텐츠·편향·프롬프트 인젝션을 체계적으로 찾아야 할 때: 수동과 자동 탐색을 함께 써 break-fix 루프로 닫을 수 있다.
- 커스텀 JSON, 매 요청 nonce, 사전 세션 생성처럼 비표준 대상을 시험할 때: 어댑터 하나를 여러 타깃에 재사용하면 대상별 프록시 유지 비용이 줄어든다.
- 모델 밖의 설계 가정과 거버넌스를 점검해야 할 때: 비기술 인력이 참여하는 리뷰가 코드 테스트로는 안 보이는 빈틈을 드러낸다.
- 규제 대응 근거가 필요할 때: 참고 자료는 여러 국가가 레드티밍을 권고하거나 의무화하는 방향이라고 소개한다.

**이럴 때 부적합**
- 기능 정확도만 확인하는 단계: 일반 기능 테스트나 회귀 테스트 스위트가 더 저렴하고 목적에 맞는다.
- 표준 OAuth에 헤더 값·base URL만 다른 대상: 커스텀 어댑터 대신 내장 커넥터가 낫다. 스크립트 유지 비용이 없다.
- 승인되지 않은 외부 시스템: 허락 없는 시험은 범위 위반이며 대상 소유자가 허가한 환경의 시험이 전제다.
- 이미 발생한 사고의 원인 규명: 사후 사고 대응(incident response) 절차가 맞다. 레드티밍은 사고 이전의 취약점 탐색이 목적이다.

## 업계 대화 맥락
아래는 설명을 위한 가상 운영 대화다. 오류 신호 처리 외의 정책(재시도 횟수, 보고 형식 등)은 조직별 선택 사항이다.

- "**Pattern A** 어댑터에서 **429**를 reply 텍스트로 반환하고 있어 리뷰에서 막았습니다. `raise_rate_limited`로 바꿔 실패 턴과 정상 응답을 분리해 주세요."
- "WebSocket 대상이라 **Pattern B**로 가야 합니다. `call_target`을 정의하면 `pre_process`/`post_process`가 비활성화되는 점을 PR 설명에 적어 주세요."
- "세션 ID를 모듈 전역에 두면 턴마다 폐기됩니다. **session_pre_process**의 `session_state`로 옮기는 수정이 필요합니다."
- "이번 라운드 **break-fix** 결과는 수정 후 동일 시나리오 **재시험**까지 포함해야 종료로 인정하겠습니다."
- "**스코프 검증**을 통과하지 못한 대상은 실행하지 않는다는 조건을 설계 문서에 명시합시다. 자기 소유 증빙을 받는 방식은 조직별로 정하면 됩니다."
- "**authenticate**가 200이 아닐 때 `raise_auth_error`로 올리는지 확인했습니다. 인증 오류가 reply로 새지 않는 것이 이번 PR의 승인 조건입니다."
- "법무·리스크 팀이 합류하는 **거버넌스 리뷰**를 별도 세션으로 잡겠습니다. 모델 테스트가 못 보는 설계 가정을 거기서 다루겠습니다."

## 선행·대안·확장 개념
- (선행) **위협 모델링** — (Threat Modeling) — 공격자 관점에서 자산·공격면·가정을 정리하는 분석으로, 레드팀의 목표와 범위를 정하는 입력이 된다.
- (선행) **프롬프트 인젝션** — (Prompt Injection) — 레드팀이 가장 자주 시험하는 공격 경로로, 탐색 입력을 설계하려면 먼저 이해해야 한다.
- (대안) **일반 기능 테스트** — 정상 사용자 관점에서 기능 오류를 찾는 접근으로, 악의적 사용에서의 파손은 다루지 않는다.
- (대안) **사후 사고 대응** — (Incident Response) — 이미 발생한 피해의 원인과 재발 방지에 초점을 두며, 사고 이전 탐색인 레드티밍과 시점이 다르다.
- (확장) **가드레일** — (Guardrail) — 레드팀 발견 사항을 방어 규칙으로 환원하는 완화 계층으로, 수정 후 재시험의 대상이 된다.
- (확장) **감사** — (Audit) — 레드티밍 결과를 증거로 남겨 거버넌스와 연결하는 단계로, 반복 개선의 책임 추적에 쓰인다.

## references_en

- {"title": "Guide to Red Teaming Methodology on AI Safety (Version 1.00)", "authors": "Japan AI Safety Institute (AISI)", "type": "docs", "url": "https://aisi.go.jp/assets/pdf/ai_safety_RT_v1.00_en.pdf", "tier": "primary", "annotation": "Official guide for planning and running AI red teaming, aimed at developers and executives."}
- {"title": "Red Teaming AI Red Teaming", "type": "paper", "url": "https://arxiv.org/html/2507.05538v2", "tier": "primary", "annotation": "Argues red teaming extends beyond technical testing to governance and design assumptions."}
- {"title": "AI Red-Teaming: A Strategic Guide to Securing AI Systems Against Emerging Threats", "authors": "Info-Tech Research Group", "type": "blog", "url": "https://finance.yahoo.com/news/ai-red-teaming-strategic-guide-202300854.html", "tier": "secondary", "annotation": "각국 규제 동향과 4단계 도입 프레임워크 소개."}
- {"title": "What Is LLM Red Teaming? AI Safety, Risks, and Best Practices", "type": "blog", "url": "https://www.mend.io/blog/llm-red-teaming-threats-testing-best-practices", "tier": "secondary", "annotation": "Explains the break-fix loop and why clear objectives and ethical limits matter."}
