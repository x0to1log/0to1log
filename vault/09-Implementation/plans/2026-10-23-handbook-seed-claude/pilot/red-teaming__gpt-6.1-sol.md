# Red Teaming — gpt-6.1-sol

- advanced 72 / basic 84 / gate pass / penalty 0 / $0.399 / 591s

## definition_en

Red teaming is an adversarial evaluation practice that probes AI models and the systems built around them with deliberately challenging inputs and misuse scenarios to expose vulnerabilities and test the effectiveness of safeguards, extending beyond model behavior to risks arising from connected components and human–AI interaction.

## definition_ko

레드티밍은 AI 모델과 이를 포함한 시스템을 공격자 관점에서 시험하는 적대적 평가 활동으로, 의도적으로 구성한 공격 입력과 오용 시나리오로 예상 밖의 동작을 유도하고 그 결과를 분석해 보안·안전상의 취약점과 기존 통제의 한계를 찾아내며, 개별 모델뿐 아니라 연결된 구성요소와 사용자 행동에서 생기는 위험도 점검한다.

## summary_en

Red teaming is a planned test in which people deliberately challenge an AI system to uncover weaknesses. It is like a safety drill: testers investigate what happens when things do not go as intended. They try difficult requests and misuse situations, then examine the system's responses. The exercise can also cover connected software and how people use the AI. Its findings help teams improve protections against security and safety risks.

## summary_ko

레드티밍은 AI를 일부러 곤란한 상황에 놓아 약점을 찾아보는 점검 활동이다. 가게에 잠금장치를 설치한 뒤 침입자 입장에서 빈틈을 살펴보는 것과 비슷하다. 담당자들은 문제를 유발할 만한 질문이나 예상 밖의 사용 상황을 시험하고, AI의 답변과 시스템 반응을 기록한다. 이렇게 발견한 문제는 개발팀이 보호 장치를 고치고 피해를 줄이는 데 쓴다.

## body_basic_en

## Plain Explanation
An artificial intelligence (AI) system can work as intended in routine use yet behave unexpectedly when someone deliberately misuses it. Looking only at its answers also leaves out risks in connected software and people's behavior. Builders therefore need a way to investigate how the system could fail, not just demonstrate what it can do.

**Red teaming** approaches this like a building inspection that checks possible failure points rather than admiring the front entrance. An appointed lead coordinates the exercise with the development team. An attack planner designs the challenges, while AI-system experts help examine what happens.

The team selects a misuse situation, sends deliberately challenging inputs, and records the resulting behavior. It compares that behavior with the protection being tested, such as a rule intended to protect personal information. The findings give builders concrete weaknesses to address and evidence they can use when checking whether a fix worked.

## Examples & Analogies
- **Following a conversation beyond the first message**: Consider a private AI application that requires a signed-in conversation before it responds. Testers must preserve that conversation across follow-up messages so the exercise examines an ongoing interaction rather than a series of unrelated requests.
- **Checking whether people trust an answer too much**: A team examines an AI interface for situations where users might rely too heavily on its advice. Testers review both the system's behavior and how people interact with it, because the interaction itself can compound risk.
- **Changing information between connected parts**: In an AI system with several components, testers examine a path where information could be manipulated before reaching the next component. They investigate the effect on the final behavior instead of assuming that reviewing each part separately covers the whole system.

## At a Glance
| | Model-level red teaming | System-level red teaming |
|---|---|---|
| Test target | An individual AI model | The model, connected software, and user interaction |
| Challenge examined | Deliberately difficult inputs to the model | Misuse and unexpected interactions across components |
| Protection examined | Safeguards governing model behavior | Controls across the working application |
| Evidence considered | The model's responses | Responses, information flows, and resulting system behavior |

Choose the testing scope around the risk you need to investigate, because examining a model alone does not cover every interaction in the application.

## Where and Why It Matters
- **Before a system is released**: An initial red-team exercise gives the development team an opportunity to identify safety weaknesses before release; official guidance recommends conducting the first exercise at this stage.
- **Checking organizational defenses**: Exercises can test whether protective controls and organizational policies work in a specific scenario, connecting technical findings to the responsibilities of security and risk teams.
- **AI purchasing decisions**: Buyers can use red-teaming considerations when assessing the safety of a proposed AI system, rather than evaluating its useful features alone.
- **People beyond the immediate user**: Safety reviews consider indirect effects on other people and society, broadening attention to privacy, fairness, and physical, psychological, or economic harm.

## Common Misconceptions
- ❌ Myth: If a test cannot connect, the AI successfully resisted the attack. → ✅ Reality: Login failures and request-limit errors are test-execution problems, not evidence about how the AI handled the challenge.
- ❌ Myth: An automated tool removes the need for human responsibility. → ✅ Reality: Red teaming still needs a responsible lead, attack planning, and relevant expertise to coordinate and interpret the exercise.
- ❌ Myth: Finding a weakness finishes the job. → ✅ Reality: A useful follow-through records the evidence, addresses the weakness, and checks whether the correction worked.

## How It Sounds in Conversation
- "For Friday's review, let's separate **model behavior** from **application behavior** in the findings."
- "Please mark the **timed-out attempts** separately in Monday's report."
- "For this private-app test, keep the **access keys** on our infrastructure rather than copying them into the report."
- "Can the platform team include **timestamps and run identifiers** so we can trace Tuesday's failed step?"
- "Engineering needs the **changed files and verification result** before we close this finding."

## Related Reading
- (before) **AI Safety** — Learn why an exercise may examine fairness and privacy as well as security weaknesses.
- (before) **Security Controls** — Understand the protections being tested so you can distinguish an attempted attack from an actual control failure.
- (similar) **Penetration Testing** — Compare this complementary security assessment with scenario-focused red teaming rather than treating the two as interchangeable.
- (next) **Human–AI Interaction** — Explore how user behavior, overreliance, and interface choices can create risks beyond the model's replies.
- (next) **Vulnerability Remediation** — Follow a finding through correction and verification, turning test evidence into an engineering response.

## body_basic_ko

## 쉽게 이해하기
AI가 평범한 질문에 잘 답한다고 해서 까다로운 상황에서도 안전하다는 뜻은 아니다. 누군가는 의도적으로 문제를 일으키려 하고, 일반 사용자도 개발자가 예상하지 못한 방식으로 서비스를 쓸 수 있다. 그래서 정상적인 사용법만 확인하는 점검으로는 놓치는 위험이 생긴다.

레드티밍은 **문제를 일으키려는 역할을 맡아 약점을 찾아보는 활동**이다. 공연 리허설에서 누군가 일부러 예상 밖의 대사를 던져 배우와 진행팀이 어떻게 대응하는지 살펴보는 것과 비슷하다. 개발팀과 점검 범위를 맞춘 뒤, 공격을 계획하고 실행하는 담당자와 AI 시스템을 이해하는 전문가가 함께 시험을 준비한다.

공격 담당자는 질문 1개를 보내거나 대화를 이어 가며 예상 밖의 반응을 시도한다. 자동화 도구를 쓴다면 요청과 응답 형식을 맞춰 주는 **연결기**가 시험 입력을 대상 AI에 전달하고 답변을 가져온다. 평가자는 질문·응답과 실행 결과를 살펴 실제로 어떤 문제가 생겼는지 판단한다. 개발팀은 발견된 문제를 수정하고, 다시 시험해 수정이 효과가 있었는지 확인한다.

## 비유와 예시
- **구매 전 업무용 AI 검토**: 회사가 AI를 도입하려 한다면, 가령 직원의 개인정보를 다루는 상황을 점검 대상으로 정할 수 있다. 정상 업무 요청만 시연하게 하기보다 부적절한 정보 이용이 생길 조건을 시험해 구매 판단에 반영한다.
- **여러 업무 시스템을 잇는 자료 분석 서비스**: 자료를 받아 분석 결과를 다른 업무 시스템으로 보내는 AI를 점검한다고 가정해 보자. 중간 데이터가 바뀌거나 예상 범위를 벗어난 입력이 들어올 때 잘못된 결과가 다음 단계로 전달되는지 시험한다.
- **사람이 승인하는 AI 초안**: AI가 만든 초안을 사람이 승인하는 업무라면, 가령 검토자가 답변을 과신하는 상황을 시험할 수 있다. AI의 문장만 보는 대신 사람이 확인을 생략하면서 위험이 커지는지도 살핀다.

## 한눈에 비교
| 비교 항목 | 단일 질문 레드티밍 | 연속 대화 레드티밍 |
|---|---|---|
| 시험 단위 | 질문 1회와 그 응답 | 질문 2회 이상이 이어지는 대화 |
| 앞선 응답의 활용 | 앞선 응답 없이 시도 | 앞선 응답을 보고 다음 질문을 구성할 수 있음 |
| 확인할 기록 | 질문과 응답 1쌍 | 질문·응답의 순서와 대화 연결 상태 |
| 대화 준비 | 대상이 요구하면 첫 질문 전에 대화 생성 | 같은 대화라는 연결 정보를 다음 질문에도 유지 |

대화형 서비스를 점검할 때는 개별 답변뿐 아니라 앞선 대화가 이어진 조건도 확인해야 사용 흐름 속의 위험을 살필 수 있다.

## 어디서 왜 중요한가
- **출시 전 의사결정**: 첫 레드티밍을 공개 전에 수행하면 발견된 위험과 필요한 조치를 출시 검토에 반영할 수 있다.
- **조직의 방어 정책 검증**: 보호 규칙을 문서에 적어 두는 데서 끝내지 않고, 공격 상황에서 실제로 작동하는지 확인하는 데 활용된다.
- **직접 사용자 밖의 피해 검토**: 점검 범위에는 이용자 본인뿐 아니라 주변 사람과 사회에 미치는 영향도 포함할 수 있으며, 신체적·심리적·경제적 위험을 함께 살핀다.
- **발견부터 수정까지의 추적**: 공격 결과의 증거와 수정 후 검증 결과를 연결해 기록하면, 문제를 찾았다는 보고와 실제로 개선됐다는 확인을 구분할 수 있다.

## 자주 하는 오해
- ❌ 오해: 레드티밍에서 문제가 안 나오면 완전히 안전하다. → ✅ 실제: 시험한 시나리오에서 발견되지 않았다는 뜻이며, 구성요소의 상호작용이나 예상 밖의 사용 조건까지 모두 검증했다는 뜻은 아니다.
- ❌ 오해: 공격자 역할이므로 개발팀과 상의하지 않고 몰래 진행해야 한다. → ✅ 실제: 개발·제공팀과 조율하고 책임자를 정해 수행하는 평가 활동이다.
- ❌ 오해: 요청이 실패하면 AI가 공격을 안전하게 막은 것이다. → ✅ 실제: 인증 오류나 요청 제한 같은 접속 문제일 수 있으므로, 실행 오류와 AI의 실제 답변을 구분해야 한다.

## 대화에서는 이렇게
- "보안팀이 **레드티밍** 공격 계획을 맡고, AI 담당자가 대상 서비스의 동작을 설명해 주면 좋겠어요."
- "이번 **레드티밍** 보고서에는 성공 여부만 쓰지 말고, 어떤 입력에서 어떤 결과가 나왔는지도 붙여 주세요."
- "점검 중 접속이 끊긴 건 **레드티밍 방어 성공**으로 세지 말고 실행 오류로 따로 분류해 주세요."
- "개발팀에서 수정한 부분은 같은 조건으로 **레드티밍 재검증**한 뒤 검토회의에 올릴게요."
- "구매팀도 **레드티밍 결과**를 볼 수 있게, 기술 설명 옆에 업무상 피해와 남은 위험을 적어 주세요."

## 함께 읽으면 좋은 용어
- (기초) **AI 안전** — 레드티밍으로 무엇을 지키려는지 이해하려면 보안뿐 아니라 공정성·개인정보·사회적 위험까지 먼저 살펴보면 좋다.
- (유사) **침투 테스트** — 레드티밍과 보완적으로 쓰이는 보안 시험으로, 두 활동의 목적과 점검 범위를 비교하면 평가 계획을 세우기 쉽다.
- (심화) **보안 통제** — 위험을 발견한 다음에는 어떤 방어 조치를 적용하고 그 효과를 확인할지 배워야 하므로 이어 읽기 좋다.
- (심화) **인간–AI 상호작용** — 모델의 답변을 넘어 사용자의 과신과 오용까지 점검 범위를 넓히는 이유를 이해할 수 있다.

## body_advanced_en

## Technical Definition & How It Works
Red teaming is a scoped adversarial evaluation workflow that converts attack hypotheses into execution evidence and reviewed findings about control effectiveness. Its engineering boundary separates proposing a challenge, executing the target interaction, observing the result, and deciding whether the evidence demonstrates the hypothesized failure. A successful request or adapter return establishes an execution outcome—not, by itself, a vulnerability verdict.

The following sequence is a **proposed engineering review model**, not a claim that every red-teaming platform implements the same architecture:

- **Proposed inputs:** Specify the target configuration, relevant entry points, authentication conditions, attack hypothesis, control objective, expected outcome, and success criteria. For example, a test specification should distinguish permission to execute a request from the security property that the request is intended to challenge. Application-context and execution-step contracts can represent architecture, data flows, entry points, expected outcomes, and success criteria separately.
- **Execution steps:** The planner proposes a prompt or command; a target-facing adapter or executor performs the interaction. Preserve the distinction between the proposed action and the action actually executed. Request construction, authentication, transport, and response extraction belong to the execution boundary; they should not silently determine the security verdict. If execution fails, preserve that failure as an execution observation rather than inventing a target response.
- **Observations:** Collect the target reply alongside the execution information needed to interpret it. An event-based executor can expose command status, output, truncation indicators, timestamps, and session/run identifiers; an adapter can return reply text and error signals. These are examples from separate integration designs, not an established shared schema or interoperability guarantee. Correlation should allow a reviewer to connect a finding to the specific action and output that support it.
- **Evaluation decisions:** Compare observed behavior with the declared success criteria. As a proposed review classification, distinguish a supported finding, an unsuccessful attempt under the tested conditions, and an inconclusive attempt with insufficient evidence. A command marked successful may only mean that execution completed; a finding still needs evidence supporting the claimed security consequence. Truncated output or a mismatched target configuration should trigger additional review rather than an automatic verdict.
- **Remediation outputs:** Record the supported weakness, affected component, proposed corrective action, and verification result. A remediation-event contract can keep changed files, the fix summary, and verification status distinct. The proposed closure gate is therefore evidence of the relevant verification outcome, not merely the existence of a code change; broader untested conditions remain outside that closure claim.

## Formulas, Architecture, and Diagrams
This **evidence-review matrix** is a proposed handbook review aid, not a platform-defined finding-admissibility policy. The fields illustrate an event-based executor design; the decisions in the final column are engineering recommendations rather than rules established by the event schema.

| Evidence condition | Concrete observation | What the observation supports | What it does not establish | Proposed review decision |
|---|---|---|---|---|
| Execution completed | Command status is `success`, with an executor result containing `exit_code`, `stdout`, and `stderr` | The execution layer reports completion and provides output to inspect | That the attack achieved its security objective | Compare the actual output with the attack's declared success criteria before issuing a finding |
| Output is incomplete | `OutputEvent.is_truncated` or executor-result `truncated` is true | The captured record does not contain the complete output | That an omitted behavior occurred—or that no harmful behavior occurred | Identify which claim depends on missing output and obtain sufficient evidence before deciding that claim |
| A vulnerability is reported | An exploit-result event contains `success`, `vulnerability_id`, `severity`, and `evidence` | The reporting component has produced a structured vulnerability claim | Independent confirmation that the reported consequence occurred | Inspect the supporting action/output sequence and confirm that it concerns the intended target |
| Remediation is reported without successful verification | A remediation event reports changed files and a fix summary, but `verification_passed` is false | A corrective change has been reported without a passing verification result | That the original weakness is resolved | Keep remediation verification open and distinguish implementation progress from closure |
| Verification is reported as passed | A remediation event contains `verification_passed=true` alongside the fix summary | The declared verification check reports success | Coverage of other attack paths or deployment conditions | Record which check passed and limit the closure statement to its tested scope |

## Operational Pattern and Review Procedure
Use this **operational adapter review procedure** to validate the target-interaction boundary before interpreting attack results. The contract example is deliberately expressed without executable code.

- **Choose execution ownership:** In **Pattern A**, both `pre_process(context, inference_input)` and `post_process(context, raw_response)` are required; the platform makes the actual HTTP call between them. In **Pattern B**, only `call_target(context, inference_input)` is required for the interaction contract, and the adapter performs the interaction directly before returning `CallTargetResult`. Defining `call_target` disables `pre_process` and `post_process`; the optional authentication and session hooks remain available with either pattern.
- **Review a minimal Pattern A request mapping:** Have `pre_process` return a `PreProcessResult` whose URL is `context.vars["endpoint"]`, whose headers are `{"Authorization": "Bearer " + context.secrets["api_key"]}`, and whose JSON body is `{"message": inference_input.prompt}`. Only `url` is required by this result contract, and `method` defaults to **POST**. The header and body fields here illustrate the target-specific mapping, not additional universally required fields.
- **Check the execution boundary:** Confirm that the platform sends the request described by `PreProcessResult` and passes the resulting `RawResponse` to `post_process`. Review the prompt mapping against the target's expected request format; connectivity alone does not validate that mapping.
- **Handle rate limiting before reply extraction:** If `raw_response.status_code` is **429**, signal `raise_rate_limited(retry_after=30)` rather than passing the error body to the evaluator as target reply text. The 30-second value is the documented example's retry interval, not a universal rate-limit policy.
- **Extract the successful reply:** Map `raw_response.json_body["reply"]` into `PostProcessResult.output`. As a review gate, verify that the expected reply field is present before treating extraction as successful; do not manufacture a reply from a parsing failure.
- **Keep authentication failures distinct:** Signal an authentication error instead of returning authentication-error text as output. When the optional `authenticate` hook is used, the platform caches its result for the returned TTL and re-authenticates on expiry or an authentication error, with one retry.

## Production Pitfalls
- ❌ Mistake: Keeping conversation identifiers in module-level globals even though the adapter script is loaded fresh for each request → ✅ Fix: Return carried values as session state and access them through context.session rather than relying on globals surviving another turn.
- ❌ Mistake: Generating request-specific signatures inside authenticate even though that hook does not receive the particular request → ✅ Fix: Cache reusable credentials in authenticate, but perform per-request signing in pre_process or call_target where the request is available.
- ❌ Mistake: Assuming adapter defaults identify the tested environment while target-level overrides silently resolve to different values → ✅ Fix: Review the target's variable and secret overrides because they take precedence over adapter defaults when the scan runs.
- ❌ Mistake: Treating first-turn setup as exclusive to multi-turn attacks and omitting it from single-turn integration validation → ✅ Fix: Validate session_pre_process for every conversation because it runs on the first turn even when the scan is single-turn.

## Tradeoffs — When to Use What
The following is a **proposed task-selection framework**. The alternatives replace the immediate engineering task, not the entire adversarial evaluation program.

**Suitable**
- **Runtime control assessment with an explicit attack objective:** Use red teaming when the question is whether a protective control withstands a targeted challenge; the additional planning and evidence-review effort supports a more specific conclusion than request completion alone.
- **Architecture-risk investigation:** Use it to challenge assumptions about entry points, authentication, algorithms, or third-party components; the tradeoff is greater coordination and interpretation effort than inspecting one isolated interface.
- **Adversarial evaluation of a nonstandard target:** A custom target adapter can enable testing of custom JSON formats, request signing, nonces, or unsupported interaction protocols; the reusable interface reduces bespoke proxy maintenance, but introduces adapter-validation work.

**Unsuitable as the immediate next step**
- **The required deliverable is an external application-security audit:** Select **penetration testing** for that audit objective rather than assuming a red-team exercise produces the same deliverable; this reduces scope ambiguity while leaving the activities complementary.
- **The blocker is a known request-format or authentication defect:** Use **HTTP request/response validation** or the **`authenticate` hook** first; running further adversarial attempts before repairing connectivity consumes execution time without producing the intended target interaction.
- **A confirmed SQL-injection weakness already has an identified corrective action:** Apply **parameterized queries** and remediation verification before expanding the exercise; additional attack discovery does not implement the known fix, and broadening scope adds review work before closure.

## Industry Communication
Illustrative architecture-review statements, not reports of measured incidents:

- "The Platform team's integration gate requires an **AI Red Teaming license**, **Network Channel client v1.4.0 or later**, and an **enabled adapter sidecar** before approving the custom target adapter."
- "The Security architecture review must preserve the documented boundary in which **adapter code and credentials execute on our infrastructure**, inside the sidecar alongside the Network Channel client."
- "The Performance review must budget the documented **approximately 50–200 ms cold start per request** separately from target inference latency."
- "The Reliability review must account for the **110 s overall execution limit per call** and the **100 s timeout for context.http calls** before approving a multi-call target interaction."
- "The State review must keep serialized **authentication and session state within 64 KB**, because oversized session state ends the conversation."
- "The configuration PR must place sensitive credentials in **context.secrets**, not **context.vars**, because variables are visible in the interface while secrets are masked there and scrubbed from logs."
- "The Observability review should treat the **Network Channel heartbeat** as connection-liveness evidence, not as confirmation that the target returned an evaluable reply or that a safety control held."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **HTTP** — Proposed handbook prerequisite, not a deployment requirement for all red teaming: request/response semantics let reviewers distinguish request construction, platform-owned transport, and reply extraction in an HTTP-based target integration.
- (prerequisite) **Authentication** — Proposed conceptual prerequisite rather than an internal red-teaming component: understanding credential acquisition and request authorization helps establish which target interaction was actually exercised, separately from the platform's deployment prerequisites.
- (alternative) **Penetration Testing** — Proposed task-level alternative when an externally audited application-security assessment is the immediate objective; it remains complementary to AI red teaming rather than an established substitute for its full scope.
- (extension) **Custom Target Adapters** — Proposed handbook extension with a documented platform implementation: Prisma AIRS adapters extend red-teaming connectivity to targets unsupported by built-in connectors, but that connectivity capability does not itself supply an evaluation verdict.
- (extension) **Remediation Chains** — Proposed workflow extension linking findings to corrective actions and verification: an example remediation-event schema carries changed files, a fix summary, and verification status, without establishing whether another red-teaming platform implements the same chain.

## body_advanced_ko

## 기술적 정의와 동작 원리
레드티밍은 **공격 시나리오, 대상의 실행 조건, 관측 증거를 결합해 취약성과 통제 효과를 검증하는 적대적 평가 워크플로우**다. 모델 평가뿐 아니라 구현 테스트, 인프라 평가, 런타임 동작 분석을 포함할 수 있으며, 평가 대상의 경계에 따라 필요한 증거가 달라진다. 핵심 책임은 **공격 계획·대상 실행·증거 수집·판정**으로 분리해야 한다.

데이터 흐름은 **대상 구성과 공격 입력 → 요청 변환 → 대상 호출 → 원시 응답 → 평가할 출력 추출 → 증거에 따른 판정**으로 정리할 수 있다. 이때 전송 계층의 정상 완료, 어댑터의 정상 반환, 공격 목표 달성은 서로 다른 상태다. 모델 출력만 관측하는 시험과 인증·세션·연결 구성요소까지 포함하는 시험은 동일한 평가 범위로 취급하지 않는다.

다음 단계 구분은 자료의 실행 계약과 평가 관점을 연결한 **설계 권고**이며, 특정 플랫폼의 공통 판정 규격을 뜻하지 않는다.

- **위협 가설 명세**: 공격자가 조작할 입력과 접근 가능한 진입점, 검증할 통제, 위반을 입증할 관측 결과를 구분한다. 자격증명 노출을 가설로 정했다면 단순한 HTTP 성공이 아니라 실제 노출을 보여 주는 증거가 필요하다.
- **실행 조건 고정**: 대상 endpoint, 인증 방식, 요청·응답 스키마, 대화 상태 전달 방식을 기록한다. 연결 설정이 바뀌면 동일한 공격 입력도 다른 실행 경로를 거칠 수 있으므로 평가 조건에 포함한다.
- **호출과 출력 추출 분리**: 요청을 구성하는 코드, 실제 호출 주체, 응답을 평가용 텍스트로 바꾸는 코드를 구분한다. 오류 본문이 정상 답변으로 변환되는 경로를 검수한다.
- **증거 결합**: 실행 식별자와 시각, 실행 상태, 원시 출력, 출력 잘림 여부를 함께 추적하도록 권고한다. 명령 실행 완료와 취약점 악용 결과, 수정 검증 결과는 별도 기록으로 연결한다.
- **판정과 후속 조치**: 명시한 성공 기준에 증거를 대조하고, 실행 불가와 통제 위반 미관측을 분리한다. 특히 **증거가 부족한 시도를 공격 실패로 단정하지 않고 판정을 유보한다**는 것은 여기서 제안하는 자체 판정 규칙이지, 제공 자료에 명시된 플랫폼 동작은 아니다.

**연결 계약의 책임 경계 예시**로 Prisma AIRS의 두 패턴을 구분할 수 있다. **Pattern A**는 `pre_process()`와 `post_process()`가 모두 필요하다. 전자는 요청 명세를 반환하고, **AIRS가 실제 HTTP 호출을 수행한 뒤** 응답을 후자에 전달한다. **Pattern B**는 `call_target()`만으로 어댑터가 직접 대상을 호출하고 답변을 반환하므로 별도의 `post_process()`가 없다. `call_target()`을 정의하면 `pre_process()`와 `post_process()`는 비활성화된다. 이 계약은 시험 대상에 도달하는 방법을 규정할 뿐, 반환된 답변이 안전한지까지 판정하는 규칙은 아니다.

## 핵심 수식·아키텍처·도표
**응답 처리·판정 경계 매트릭스**

아래 표의 함수와 필드는 연결 계약이며, 검수 기준은 이를 평가 파이프라인에 적용하기 위한 권고다.

| 관측 지점 | 입력·신호 | 처리 및 전달 경계 | 검수 기준 |
|---|---|---|---|
| 원시 응답 수신 | `RawResponse.status_code`, `json_body`, `headers` | AIRS가 HTTP 응답을 `post_process()`에 전달 | 상태 코드·본문·헤더를 하나의 답변 문자열로 뭉개지 않고 각 역할을 유지하는가 |
| 정상 답변 추출 | `raw_response.json_body["reply"]` | 추출한 답변을 `PostProcessResult.output`으로 반환 | `output`이 대상의 답변 텍스트이며, 원시 응답 전체나 오류 설명으로 대체되지 않았는가 |
| 요청 제한 | `status_code == 429` | 자료의 예제는 `raise_rate_limited(retry_after=30)`으로 오류 신호 발생 | 30초의 재시도 대기 정보를 전달하며, 오류 본문이 `output`으로 흘러가지 않는가 |
| 인증 실패 | 인증 관련 실패 조건 | 알려진 실패는 답변 텍스트가 아니라 오류 신호로 전달 | 인증 복구 문제와 대상의 안전성 응답을 별개 경로로 다루는가 |
| 응답 스키마 불일치 | `reply` 누락 또는 기대한 텍스트 형식과 불일치 | 추출 경계의 실패로 분류하도록 권고 | 임의의 대체 문자열을 만들어 정상 평가 입력으로 보내지 않는가 |
| 취약성 판정 | 추출된 답변과 공격 성공 기준, 추가 실행 증거 | 실행 결과에서 취약성 결론으로 넘어가는 별도 검토 단계 | HTTP 완료나 함수의 정상 반환만으로 공격 성공·실패를 결정하지 않는가 |

`headers`는 `RawResponse`의 일부지만, 제공된 예제는 헤더에서 대기 시간을 계산하지 않는다. **429일 때 30초를 지정하는 예제**를 모든 대상의 재시도 정책이나 실제 자동 재시도 보장으로 일반화하지 않는다.

## 운영 패턴과 검수 절차
**Pattern A 연결 계약 검수 절차**

다음은 제공된 요청·응답 예제를 검증하기 위한 절차다. 명시적으로 언급하지 않은 검증 기능이 예제에 이미 구현돼 있다고 가정하지 않는다.

- **입력 계약 확인**: `inference_input`에는 해당 턴의 프롬프트와 대화 이력이 포함된다. 그러나 예제의 요청 본문은 `inference_input.prompt`만 사용한다. 입력 객체에 이력이 존재한다는 사실과 대상 API에 그 이력이 실제 전달된다는 주장을 구분한다.
- **요청 목적지 확인**: `pre_process()`가 반환하는 `PreProcessResult.url`은 `context.vars["endpoint"]`에서 읽는다. `url`은 필수 필드이며 HTTP 메서드의 기본값은 `POST`다. 검수에서는 의도한 대상 설정이 선택됐는지 확인한다.
- **인증과 본문 매핑 확인**: `Authorization` 헤더는 `Bearer` 뒤에 `context.secrets["api_key"]` 값을 붙이는 형태다. JSON 본문의 `message` 필드에는 `inference_input.prompt`가 들어간다. 인증값과 공격 입력이 각각 올바른 헤더·본문 위치에 배치되는지 확인한다.
- **실행 경계 확인**: `pre_process()`의 주 반환값은 HTTP 요청 명세다. Pattern A에서는 AIRS가 실제 HTTP 호출을 수행하고 그 응답을 `post_process()`에 전달한다. 요청 구성 완료를 대상 실행 완료로 기록하지 않는다.
- **정상 응답 경로 검증**: 정상 응답 표본에서 `json_body`의 `reply`가 답변 텍스트인지 확인하고, 같은 텍스트가 `PostProcessResult.output`으로 반환되는지 대조한다. `reply` 누락·형식 불일치를 별도로 시험하는 것은 추가 검수 권고이며, 예제 자체의 명시적 스키마 검증 기능은 아니다.
- **429 오류 경로 검증**: `status_code`가 429인 응답 표본에서는 `raise_rate_limited(retry_after=30)`이 호출되고 정상 `output`이 반환되지 않는지 확인한다. 알려진 인증 오류 역시 오류 문자열을 답변으로 반환하지 않고 오류 신호로 분리하는지 검수한다.
- **대화 상태 경로 검증**: 대상이 대화 이력이나 서버 측 세션을 요구한다면, 그 요구를 현재 요청 매핑이 충족하는지 별도로 확인한다. 프롬프트만 보내는 예제를 그대로 사용했다는 이유로 대화 재현성이 확보됐다고 승인하지 않는다.

**확인 범위**: 함수 계약상 `context`는 `vars`, `secrets`, `auth`, `session`, `http`를 제공한다. 이 절차에서는 그 제공 범위까지만 전제로 삼고, **실제 배포의 코드 실행 위치와 비밀 저장 정책은 별도 배포 검토의 미확인 항목**으로 남긴다. 저장 시 암호화 방식과 보존 기간에 대해서는 해당 주제에 대한 검증된 정보가 부족합니다.

## 프로덕션 함정
- ❌ 실수: 기존 Pattern A 어댑터에 보조 함수처럼 call_target을 추가하고도 pre_process와 post_process의 검증 로직이 계속 실행될 것으로 가정한다. → ✅ 해결: call_target 정의가 두 함수를 비활성화한다는 우선순위를 검토하고, 실제 선택한 패턴의 실행 경로에 요청 검증과 응답 추출 책임을 배치한다.
- ❌ 실수: 요청 본문에 따라 달라지는 서명을 authenticate에서 한 번 생성해 캐시하면서 이후 공격 요청에도 같은 서명 값을 재사용한다. → ✅ 해결: authenticate에는 캐시 가능한 자격증명 획득을 두고, 개별 요청에 종속되는 서명은 해당 요청을 확인할 수 있는 pre_process 또는 call_target에서 처리한다.
- ❌ 실수: 이전 턴의 세션 식별자를 모듈 전역 변수에 보관해 다음 턴에서도 같은 값이 남는다고 가정하고 연속 실행 결과를 분석한다. → ✅ 해결: 스크립트가 턴마다 새로 로드된다는 제약을 반영해 전달할 상태는 session_state로 반환하고, 인증·세션 합산 직렬화 크기가 64 KB 한도를 넘지 않도록 검토한다.
- ❌ 실수: 대상별 변수 재정의를 확인하지 않은 채 어댑터 기본 endpoint로 실행한 결과를 특정 배포 환경의 통제 검증 증거로 승인한다. → ✅ 해결: 대상의 재정의 값이 기본값보다 우선한다는 규칙에 따라 실제 적용된 비민감 설정을 확인하고, 평가 대상과 실행 설정의 일치를 승인 조건으로 둔다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**

- **특정 통제의 실효성을 공격 시나리오로 확인할 때**: 정상 기능의 성공 여부보다 통제 우회 조건을 찾아야 하므로, 위험별 성공 기준을 둔 레드티밍이 적합하다. 대신 시나리오 설계와 증거 검토에 인력이 필요하다.
- **모델 단독 평가로 원인을 설명하기 어려울 때**: 인증, 요청 변환, 세션 상태 등 여러 구성요소의 상호작용을 시험 범위에 포함할 수 있다. 다만 관측 지점이 늘어나 실패 원인 분류가 복잡해진다.
- **실제 배포 조건의 런타임 동작을 확인할 때**: 대상의 요청 형식과 상태 관리 방식을 반영하면 단순 모델 호출에서 드러나지 않는 실행 경로를 검토할 수 있다. 그만큼 연결 계약 검증과 대상별 설정 관리 비용이 발생한다.

**이럴 때 단독 접근으로 부적합**

- **알려진 코드 취약점의 위치와 수정 힌트만 수집하려는 경우 — 대안: 취약점 스캐닝**. 파일 경로·행 번호·수정 힌트 중심의 결과가 필요하다면 스캐너를 먼저 사용하는 편이 목적에 맞는다. 공격 대화 설계가 그 산출물을 대신하지는 않는다.
- **요청·응답 변환의 정확성만 확인하려는 경우 — 대안: 구현 테스트**. 입력 매핑과 파싱 오류를 먼저 격리해야 대상의 안전성 문제와 연결 코드의 결함을 혼동하지 않는다. 적대적 평가 전체를 실행하기 전에 계약 수준의 검증이 필요하다.
- **외부 감사 목적의 보안 시험이 필요한 경우 — 대안: 침투 테스트**. 내부의 특정 위험 시나리오 검증과 외부 감사의 목적·범위는 같지 않으므로, 레드티밍 결과만으로 감사 요구를 충족했다고 간주하지 않는다. 두 활동은 보완적으로 계획한다.

**연결 방식의 선택은 별도 결정**이다. Prisma AIRS의 맞춤 어댑터에는 **AI Red Teaming 라이선스, Network Channel client v1.4.0 이상, adapter sidecar 활성화**가 전제된다. 차이가 헤더 값이나 기본 URL뿐이거나 표준 OAuth를 사용한다면 **내장 커넥터**를 우선 검토해 맞춤 코드의 유지보수 부담을 줄인다. 복잡한 요청 형식이나 인증·세션 준비가 필요할 때 맞춤 어댑터를 검토하되, `call_target()` 계약만으로 임의의 비HTTP 전송·스트리밍 방식까지 지원된다고 추정하지 않는다.

## 업계 대화 맥락
**다음은 설계 문서·PR·사후 분석에 사용할 수 있는 예문이며, 실제 사고 기록이나 측정 결과가 아니다.**

- "보안팀의 **위협 가설 검토**에서는 공격 가능한 진입점과 필요한 증거를 분리하고, 응답 텍스트만으로 입증할 수 없는 항목은 **추가 관측 필요**로 남기겠습니다."
- "플랫폼팀 PR은 **Network Channel client v1.4.0 이상**이라는 어댑터 전제조건을 확인하되, 버전 충족을 대상 API의 **계약 검증 완료**로 취급하지 않도록 승인 항목을 나눠 주세요."
- "실행 설계에는 **호출당 110초**의 전체 제한과 **context.http의 100초** 제한을 별도로 표시하고, 추가 호출을 넣을 때 전체 실행 창 안에 완료되는지 검토하겠습니다."
- "인증 변경 PR에서는 **authenticate의 TTL 캐시**와 만료 또는 인증 오류 시 **자동 재인증**, 인증 오류 시 **1회 재시도** 경로를 구분해 검증해야 합니다."
- "대화 초기화 검토에서는 **session_pre_process**가 다중 턴 설정과 무관하게 **단일 턴을 포함한 모든 대화의 첫 턴**에 실행된다는 조건을 테스트에 반영해 주세요."
- "평가 결과 화면의 설계에서는 **명령 실행 상태**, **취약점 증거**, **수정 검증 상태**를 별도 항목으로 유지해 하나의 성공 표시가 서로 다른 결론을 대신하지 않도록 하겠습니다."
- "사후 분석의 재발 방지 항목은 출력 일부가 누락된 실행을 **완결된 증거**로 승인하지 않는 것이며, **출력 잘림 여부**를 검토자가 확인할 수 있도록 관측 계약을 보완하겠습니다."

## 선행·대안·확장 개념
- (선행) **시스템 아키텍처** — 대상 시스템의 구성요소·진입점·데이터 흐름을 알아야 모델 자체의 실패와 연결 계층의 실패를 구분하고 시험 경계를 정할 수 있다.
- (선행) **API 계약** — 대상의 요청·응답 스키마와 오류 의미를 먼저 이해해야 연결 오류가 공격 결과를 왜곡하지 않도록 실행 경계를 검증할 수 있다.
- (대안) **침투 테스트** — 보안 취약점을 검증하는 보완적 접근으로, 외부 감사 등 목적과 범위에 따라 특정 위험 시나리오 중심의 레드티밍과 별도로 선택하거나 병행한다.
- (확장) **모델 수준 레드티밍** — 레드티밍의 평가 경계를 모델 동작으로 한정한 특수화이며, 애플리케이션 연결 계층과 구분된 결과가 필요할 때 사용한다.
- (확장) **시스템 수준 레드티밍** — 평가 범위를 구성요소 간 상호작용과 배포 환경으로 넓혀 개별 모델 시험만으로 설명되지 않는 복합 실패 경로를 검토한다.

## references_en

- {"title": "Guide to Red Teaming Methodology on AI Safety (Version 1.00)", "type": "docs", "url": "https://aisi.go.jp/assets/pdf/ai_safety_RT_v1.00_en.pdf", "tier": "primary", "annotation": "Official guidance for planning AI safety exercises and tailoring them to a system's configuration and use."}
- {"title": "Custom Target Adapters", "type": "docs", "url": "https://docs.paloaltonetworks.com/ai-runtime-security/ai-red-teaming/identify-ai-system-risks-with-ai-red-teaming/get-started-with-prisma-airs-ai-red-teaming/targets/custom-target-adapters", "tier": "primary", "annotation": "Shows how Prisma AIRS connects tests to private applications while handling credentials and conversation state."}
- {"title": "Functions", "authors": "Palo Alto Networks", "type": "docs", "url": "https://docs.paloaltonetworks.com/ai-runtime-security/ai-red-teaming/identify-ai-system-risks-with-ai-red-teaming/get-started-with-prisma-airs-ai-red-teaming/targets/custom-target-adapters/adapter-contract/adapter-contract-functions", "tier": "primary", "annotation": "인증·대화 준비·응답 추출과 실행 오류 처리의 역할을 구체적으로 확인한다."}
- {"title": "Red Teaming AI Red Teaming", "type": "paper", "url": "https://arxiv.org/html/2507.05538v1", "tier": "primary", "annotation": "Explains why testing must address component interactions, user behavior, and organizational context."}
- {"title": "OWASP Red Teaming: A Practical Guide to Getting Started", "type": "blog", "url": "https://www.promptfoo.dev/blog/owasp-red-teaming", "tier": "secondary", "annotation": "A practical introduction to exercise objectives, control testing, and the teams that use the findings."}
