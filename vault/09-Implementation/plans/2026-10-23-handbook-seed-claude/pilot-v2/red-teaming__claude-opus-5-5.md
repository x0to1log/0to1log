# Red Teaming — claude-opus-5-5

- advanced 76 / basic 91 / gate pass / penalty 0 / $0.4188 / 773s

## definition_en

AI red teaming is an adversarial evaluation practice that probes models and AI systems with deliberately challenging inputs and scenarios to uncover security vulnerabilities and safety harms, using human-led or automated exploration to challenge design assumptions and guide iterative remediation and retesting.

## definition_ko

AI 분야의 레드티밍은 공격자 관점의 입력과 시나리오로 모델·응용 시스템의 보안 취약점과 안전상 위해를 탐색하는 적대적 평가 활동으로, 사람의 수동 탐색과 자동화된 시험을 통해 설계 가정과 방어 조치의 약점을 드러내고 발견된 문제를 수정·재검증하는 과정으로 이어진다.

## summary_en

Red teaming means deliberately trying to make an AI system fail in harmful or unsafe ways, with permission and clear limits. Testers try challenging requests and vary their approach rather than follow a fixed script. They look for problems such as unfair treatment, exposed private information, or harmful answers. Their findings help teams decide what to fix and check again.

## summary_ko

레드티밍은 AI에 일부러 까다롭거나 악의적인 요청을 보내 약점을 찾는 활동이다. 제품을 내놓기 전에 예상 밖의 사용 상황을 만들어 보는 점검과 비슷하다. 사람이나 자동화 도구가 시험 요청을 보내고, 답변에서 보안 문제나 사람에게 해로운 결과가 나오는지 살핀다. 발견한 문제를 고치고 다시 시험해 실제 사용자의 피해를 줄이는 것이 목적이다.

## body_basic_en

## Plain Explanation
An AI system can handle ordinary requests while important risks remain unexplored. It might produce harmful answers, treat people unfairly, or reveal information it should protect. **Red teaming** investigates these possibilities by deliberately challenging the system within an agreed, authorized scope.

Think of an authorized security team hired to test a museum's protections. They do not merely rehearse a known alarm response; they vary tactics and question which routes are really protected. AI red teamers similarly change requests and scenarios to challenge both the system's defenses and its designers' assumptions.

In an automated run, a **connector**—software linking the test process to the application—sends a challenging request and returns the application's actual reply. A test can involve one request or a conversation spanning several turns. Reviewers examine the results and distinguish harmful behavior from problems with the test connection itself. The responsible team uses the findings to make changes, then repeats relevant tests to check the fixes.

## Examples & Analogies
- **Illustrative hiring assessment**: Testers create two fictional applicants with identical job qualifications and change only a demographic detail. They challenge a hiring assistant with both profiles and examine differences in its recommendations as possible fairness concerns, not automatic proof of discrimination.
- **Illustrative restricted-record test**: In an authorized test copy of a support application, testers create synthetic—made-up—case records and two accounts with different access permissions. They vary requests to see whether an account with limited access can obtain a record reserved for the other role, without exposing real customers' information.
- **Illustrative design challenge**: Before an internal AI adviser is built, legal and risk staff challenge the assumption that a person will always review its recommendations. They examine a proposed workflow where a recommendation could be acted on without that review and ask who is responsible for preventing it.

## At a Glance
| | Manual probing: person-led challenges | Automated probe execution: software-run challenges |
|---|---|---|
| Adaptation | A tester chooses the next challenge after inspecting a response | Changes depend on how the test process is programmed |
| Scale | A person directs individual attempts and conversations | Software executes configured sets of attempts |
| Reproducibility | Requires recording requests, replies, and relevant context | Requires retaining requests, replies, and run settings |
| Review needs | People interpret unexpected behavior during exploration | People review outputs and distinguish findings from execution errors |

Hybrid workflows combine human investigation with automated execution, so choosing an approach need not mean giving up either judgment or repeatable testing.

## Where and Why It Matters
- **Reaching custom applications**: An adapter—a small piece of connecting software—can translate test requests and extract replies when a built-in connector does not fit. Check that it reaches the intended application and returns the actual answer before interpreting findings.
- **Protecting test credentials**: Keep passwords and access keys in designated secret settings rather than ordinary configuration fields. Confirm where the adapter executes and how its logs handle sensitive values.
- **Preserving conversation context**: Some applications require a session identifier to connect successive messages. Check that the test carries this information correctly, so a conversation is not accidentally evaluated as unrelated requests.
- **Recognizing incomplete tests**: Authentication failures, request limits, and timeouts need separate error handling. A test that never obtains a valid application response should not be counted as evidence that the application resisted the challenge.

## Common Misconceptions
- ❌ Myth: Passing red teaming proves the system is safe. → ✅ Reality: Results provide evidence about the scenarios and conditions examined; test coverage is not a safety guarantee.
- ❌ Myth: Red teaming only means getting a chatbot to produce a forbidden answer. → ✅ Reality: It can also examine privacy, fairness, application behavior, governance, and the assumptions behind a design.
- ❌ Myth: Only technical security specialists can contribute. → ✅ Reality: Management, legal, and risk teams can challenge assumptions and governance choices that technical tests alone do not address.

## How It Sounds in Conversation
- "Keep this round of **red teaming** within the approved application and test accounts."
- "Can the **red team** challenge our assumption that every recommendation gets reviewed?"
- "Please attach the request and reply before we classify this **red-team finding** as a privacy issue."
- "That timeout leaves a gap in our **red-teaming coverage**, so schedule another attempt."
- "Let's **retest the red-team findings** after the fix before the release review."

## Related Reading
- (before) **AI Safety** — Understand which harms matter before choosing the objectives of an adversarial assessment.
- (next) **Prompt Injection** — Explore a specific security risk that can turn a broad assessment into focused challenges.
- (next) **Bias** — Learn how to investigate possible unfair treatment rather than treating every output difference as conclusive evidence.
- (next) **Privacy Protection** — Connect information-exposure findings to the responsibilities of protecting people's data.
- (next) **AI Governance** — Follow findings beyond technical fixes into policies, oversight, and decision responsibilities.

## body_basic_ko

## 쉽게 이해하기
AI가 평범한 질문에 잘 답한다는 사실만으로, 악용하려는 질문에도 안전하다고 판단할 수는 없어요. 이용자에게 해로운 내용을 내놓거나 보호해야 할 정보를 드러내는 상황도 따로 살펴야 해요. 예를 들어, 모델 자체를 살피는 시험과 그 모델을 연결한 업무 앱 전체를 살피는 시험은 확인할 범위가 달라요.

레드 티밍은 건물의 대피 훈련에서 일부러 어려운 상황을 정해 대응을 점검하는 것과 비슷해요. 시험자는 정상 작동을 확인하는 데 그치지 않고, 문제가 생길 법한 조건을 의도적으로 만들어요. 기술 담당자뿐 아니라 법무·위험관리 담당자도 참여해 어떤 피해를 막아야 하는지, 설계가 어떤 가정에 기대고 있는지 검토할 수 있어요.

자동화된 시험에서는 **시험 도구**가 질문을 보내고 **대상 AI**의 답변을 돌려받아요. 대상의 접속 방식이 다르면 **맞춤 연결 도구**가 요청 형식을 맞추고 답변을 꺼내 전달해요. **검토자**는 답변이 미리 정한 실패 기준에 해당하는지 판단해요. 개발팀은 발견한 문제를 수정한 뒤 다시 시험해 개선 여부를 확인해요.

## 비유와 예시
- **가상 상담 앱의 개인정보 노출 시험**: 가상 고객 자료를 넣은 상담 앱에서 권한이 다른 시험 계정으로 같은 자료를 요청해 봐요. 계정 권한을 시험 변수로 삼고, 해당 계정이 볼 수 없는 고객의 가상 개인정보가 답변에 나오면 실패로 판정해요.
- **앞선 대화에 따른 규칙 우회 시험**: 거절하도록 정한 요청을 앞선 대화가 없는 경우와 여러 문답 뒤에 하는 경우로 나눠 시험해요. 마지막 요청은 같게 유지하고 대화 이력만 바꿨을 때, 정해 둔 금지 내용을 제공하면 실패로 판정해요.
- **가상 채용 평가의 편향 시험**: 가상의 지원서 두 개에서 직무와 무관한 개인 특성만 바꿔 AI의 평가 이유를 비교하는 시험을 설계할 수 있어요. 동등하게 다루기로 정한 조건인데 특정 집단을 깎아내리는 설명을 내놓으면 실패로 판정해요.

## 한눈에 비교
| 비교 항목 | 단일 턴 시험 | 다중 턴 시험 |
|---|---|---|
| 문답 구성 | 하나의 시험에서 질문·응답 1회 | 하나의 시험에서 두 차례 이상 문답을 이어감 |
| 탐색할 실패 유형 | 한 요청만으로 드러나는 유해 출력이나 정보 노출 | 앞선 대화에 따라 달라지는 안전 규칙 준수 |
| 재현에 필요한 조건 | 입력, 대상 설정, 계정 권한 | 왼쪽 조건에 더해 전체 대화 순서와 대화 연결 상태 |

앞선 대화가 영향을 주는 실패는 마지막 질문만 복사해서 재현하기 어려우므로, 질문이 오간 순서와 대화 연결 상태도 함께 남겨야 해요.

## 어디서 왜 중요한가
- **AI 조달·도입 검토**: 구매하려는 시스템의 구성과 사용 방식에 시험 범위가 맞는지 확인하는 데 활용할 수 있어요. 모델에 대한 시험인지 실제 업무 시스템까지 포함한 시험인지 구분해야 결과를 도입 판단에 연결할 수 있어요.
- **맞춤 연결 도구의 보안 검토**: 시험 요청을 중계하는 코드를 어디서 실행하는지, 인증정보를 어디에 보관하고 전달하는지 확인해야 해요. 대상 AI뿐 아니라 시험을 연결하는 과정의 정보 취급 방식도 점검 대상이에요.
- **시험 오류와 위험한 응답의 구분**: 인증 실패나 시간 초과는 대상 AI가 내놓은 답변과 구분해 기록해야 해요. 답변을 받지 못한 시험을 ‘위험한 답변 없음’으로 처리하면 평가 결과를 잘못 해석할 수 있어요.
- **설계·관리 지침 검토**: 경영·법무·위험관리 담당자도 설계의 전제와 관리 방식을 검토할 수 있어요. 기술적 수정뿐 아니라 운영 지침을 보완해야 할 문제를 찾는 데도 활용돼요.

## 자주 하는 오해
- ❌ 오해: 문제를 찾지 못했으니 안전이 보증된다. → ✅ 실제: 정해진 시험 범위와 조건에서 발견하지 못했다는 뜻이지, 모든 상황에서의 안전을 보증하지는 않아요.
- ❌ 오해: 보안 시험이니 실제 개인정보와 비밀번호를 그대로 써도 된다. → ✅ 실제: 가상 데이터를 우선 사용하고, 필요한 인증정보는 별도 비밀정보 항목으로 관리하며 기록에 노출되지 않는지 확인해야 해요.
- ❌ 오해: 발견한 공격 입력과 결과는 누구에게나 상세히 공개해도 된다. → ✅ 실제: 악용 단서나 민감정보가 담길 수 있으므로 상세 기록의 접근을 담당자로 제한하고, 공유용 요약에서는 민감한 내용을 제거해야 해요.

## 대화에서는 이렇게
- "**레드 티밍** 결과에 위험도와 수정 담당자를 붙여서 출시 검토 회의에 올릴게요."
- "운영팀에서 **시험 중단 기준**을 정해주시면 그 범위 안에서만 진행할게요."
- "법무팀도 **레드 티밍** 설계 검토에 참여해서 기술팀이 놓친 사용 가정을 짚어주세요."
- "수정한 항목은 **재시험** 결과가 확인된 뒤 완료 처리하죠."
- "연결 담당자는 **시험 오류** 건수와 실제 응답을 받은 건수를 구분해 보고해주세요."

## 함께 읽으면 좋은 용어
- (기초) **AI 안전성** — 레드 티밍으로 무엇을 확인해야 하는지 정하려면, 보안뿐 아니라 공정성과 개인정보 보호 같은 안전의 범위부터 이해하면 좋아요.
- (기초) **편향** — 기술이 정상 작동해도 특정 집단에 해를 줄 수 있다는 점을 이해하면, 시험 목표를 보안 취약점에만 한정하지 않게 돼요.
- (심화) **프롬프트 인젝션** — 레드 티밍의 시험 목표로 다룰 수 있는 위험이므로, 어떤 상황을 공격 성공으로 판정할지 구체화할 때 읽기 좋아요.
- (심화) **AI 거버넌스** — 발견한 문제를 기술적 수정에서 끝내지 않고 조직의 관리 지침과 책임으로 연결하는 다음 단계예요.

## body_advanced_en

## Technical Definition & How It Works
AI red teaming is a scoped adversarial evaluation workflow that tests hypotheses about failures of an AI system's security or safety constraints against observable behavior. Its engineering contract separates the proposed challenge, target execution, outcome assessment, and remediation evidence. A completed request establishes that an interaction occurred; it does not, by itself, establish either a vulnerability or successful protection.

A useful responsibility split is **evaluation control**, **target integration**, **execution**, and **adjudication**. Evaluation control specifies the permitted target, adverse outcome, and success criteria. Integration preserves the target's request format, conversation context, authentication context, and response semantics. The execution boundary performs the interaction; adjudication determines whether the resulting evidence supports the hypothesized failure.

The data path carries prompts and conversation history into the target and returns observed output. The control path governs which interactions are permitted, when a run changes stage, and whether evidence is sufficient to advance from a suspected issue to a confirmed finding. Keeping these paths distinct is especially important when an automated system proposes executable actions: an action proposal is not authorization to execute it.

Recommended evaluation steps are:

- **Specify the hypothesis:** Associate the target entry point and relevant data flow with an expected adverse outcome and explicit success criteria. A software vulnerability claim and a harmful-content claim require different evidence.
- **Execute the permitted interaction:** Preserve the request and target context needed to interpret the result. An adapter may translate transport or serialization, but should not silently change the behavior being evaluated.
- **Assess the observation:** Compare actual output with the stated criteria. Preserve execution status separately from exploit or safety findings; the integration contracts distinguish command status, exploit results, and remediation results.
- **Assign the finding:** Record its category, severity, summary, and supporting evidence. Where applicable, associate it with the affected file or location rather than attributing every failure to the model.
- **Verify closure:** Evaluate evidence of the implemented correction separately from evidence that the correction was applied. A remediation result and a verification result answer different questions.

The resulting assurance is bounded by the exercised target configuration, entry points, and success criteria—not by the number of requests submitted.

## Formulas, Architecture, and Diagrams
**Control-boundary review matrix**

This matrix is a proposed review artifact, not a taxonomy of reported incidents. Its purpose is to prevent a finding at one layer from being treated as evidence about another.

| Evaluation boundary | Failure hypothesis | Evidence needed for review | Mitigation boundary and residual uncertainty |
|---|---|---|---|
| Model response | The target generates content that violates the selected safety objective | Returned text, relevant conversation context, and an explicit outcome criterion | Review the model-facing behavior; this does not establish whether surrounding software is secure |
| AI application entry point | Adversarial instructions produce an outcome inconsistent with the application's intended constraints | Entry-point method, authentication requirement, submitted input, and observed reply | Review application behavior in the exercised configuration; do not generalize to untested interfaces |
| Supporting application software | A software vulnerability can be exploited through the tested path | Vulnerability category, executed steps, observed output, and evidence supporting the claimed impact | Correct the affected software boundary; for SQL injection, the supplied remediation example uses parameterized queries rather than a model-response change |
| Design and governance assumptions | Evaluation coverage does not match the system's configuration or intended usage | Component and data-flow descriptions compared with the actual evaluation scope | Revise scope or design assumptions; additional technical probes cannot alone resolve an undefined control objective |

**Review criterion:** Choose the mitigation owner from the boundary supported by the evidence, not merely from the fact that an AI component participated in the interaction.

## Operational Pattern and Review Procedure
**Operational procedure: accept evidence before accepting a finding**

- **Check the evaluation contract:** Require a target description, permitted interaction, expected outcome, and success criteria. Reject a claim whose criterion is only that a request or command completed successfully.
- **Check execution authority:** Before an automated executor acts, compare the proposed action and target with the authorized scope. Treat generated reasoning and proposed commands as evaluation inputs, not permission to expand that scope.
- **Check correlation:** Associate the observation with its session, run, and step. Retain the relevant request context and the returned output so reviewers can reconstruct which interaction supports the claim.
- **Check evidence completeness:** Inspect output-truncation indicators and distinguish captured output from a summary of that output. If truncation removes material needed to assess the success criterion, classify the result as inconclusive until sufficient evidence is available.
- **Check target fidelity:** Confirm that the interface extracted the intended reply and preserved the required session context. If the recorded target or conversation context does not match the hypothesis, reject the comparison rather than treating it as a negative result.
- **Make the assessment explicit:** Use locally defined outcomes such as **supported finding**, **not observed**, and **inconclusive**. These are proposed review labels, not a published cross-provider standard; record the evidence and rationale supporting the selected label.

The acceptance boundary is evidentiary: incomplete or mismatched observations should not become either confirmed vulnerabilities or claims of successful protection.

## Production Pitfalls
- ❌ Mistake: Treating a successful command status or zero exit code as proof that the hypothesized exploit succeeded → ✅ Fix: Compare the observed output with the step's expected outcome and success criteria, then record exploit confirmation separately from command completion.
- ❌ Mistake: Retaining conversation state in module-level globals inside a Prisma AIRS custom adapter → ✅ Fix: Return persistent values through the supported session-state contract; the script is loaded fresh per turn, and combined serialized authentication and session state must stay within 64 KB.
- ❌ Mistake: Computing request-specific signatures inside a cached authentication function before the actual request exists → ✅ Fix: Keep credential acquisition in authentication and perform per-request signing where the concrete request is available, such as pre_process or call_target in the documented adapter contract.
- ❌ Mistake: Closing a remediation item because the remediation operation reports success without checking verification evidence → ✅ Fix: Review the changed files and fix summary alongside the separate verification result, and keep the finding unresolved when the correction has not been verified.

## Tradeoffs — When to Use What
These choices concern the primary evaluation method; the methods can also be combined within one assessment.

**Suitable**

- **Exploring prompt-injection susceptibility at an AI application boundary:** Adversarial evaluation directly targets behavior under challenging instructions, while the application's entry points and authentication context constrain what the result means.
- **Assessing custom conversational applications or agents:** Exercise the actual target when sessions, custom framing, or streaming affect the interaction; integrating that path adds complexity but avoids evaluating a different interface from the one under review.
- **Determining whether a suspected software weakness produces impact:** Use a scoped exploit evaluation when a scanner finding needs supporting execution evidence; this requires more execution and review effort than identifying a candidate issue alone.

**Unsuitable as the primary method**

- **Determining only whether a service is reachable:** Use an **HTTP health check**; it answers a narrower operational question without the interpretation overhead of an adversarial campaign.
- **Locating candidate code-level security issues:** Start with **vulnerability scanning** when the required output is a categorized issue with a file, line, or remediation hint; reserve adversarial execution for questions requiring impact evidence.
- **Diagnosing request-schema or response-parsing mismatches:** Use **request/response contract validation** first; an interface defect prevents meaningful behavioral assessment and is more directly isolated at the integration boundary.

## Industry Communication
- "For this architecture review, the **entry-point method** and **authentication requirement** must accompany each finding so the exercised interface is explicit."
- "The executor PR must preserve the distinction between an **action proposal** and an **authorized execution**, rather than allowing generated reasoning to expand the target scope."
- "The security review requires an **impact rationale** alongside **severity**, because the category label alone does not explain the observed consequence."
- "For the Prisma AIRS integration, confirm **Network Channel client v1.4.0 or later** and an enabled **adapter sidecar** before approving the custom target path."
- "The evaluation report must retain **duration_ms** as execution metadata rather than treating a slow interaction as evidence of a safety failure."
- "The release assessment must identify **untested configurations** explicitly instead of presenting campaign completion as assurance across every application entry point."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **AI System Architecture** — Components, data flows, entry points, and authentication boundaries determine what a red-team observation can establish and where a supported finding belongs.
- (prerequisite) **HTTP Request–Response Contracts** — Understanding request construction and response extraction is necessary to distinguish the target's behavior from changes introduced by its evaluation interface.
- (alternative) **Vulnerability Scanning** — Identifies candidate software security issues through categorized findings and location information, providing a different primary method when discovery rather than adversarial impact confirmation is the immediate objective.
- (extension) **LLM Red Teaming** — Specializes red teaming to language-model behavior, requiring response-level safety findings to remain distinct from claims about the surrounding application's software security.

## body_advanced_ko

## 기술적 정의와 동작 원리
AI 레드티밍은 공격자가 조작할 수 있는 입력과 시험 대상의 경계를 명시하고, 관측된 실행 결과가 안전·보안 목표를 위반하는지 검증하는 적대적 평가 절차다. 실행 설계에서는 **공격 가설·성공 기준**, **대상·연결 계층**, **관측·판정 계층**, **수정 검증**의 책임을 분리한다. 아래 책임 분리와 검증 게이트는 설계 제안이며, 특정 제품의 전체 평가 알고리즘을 뜻하지 않는다.

**제어 흐름**은 가설 선택 → 실행 조건 확인 → 대상 호출 → 증거 유효성 확인 → 가설 판정 → 수정 검증으로 구성한다. **데이터 흐름**에서는 프롬프트와 대화 이력이 대상의 요청 형식으로 변환되고, 반환된 전송 결과에서 평가할 응답을 추출한다. 이때 연결 계층은 요청 구성과 응답 추출을 담당하고, 판정 계층은 추출된 응답 및 실행 증거를 성공 기준과 대조한다. 연결 계층이 정상 반환했다는 사실만으로 판정 계층의 결론을 대신해서는 안 된다.

평가 사례는 입력 문자열만으로 식별하지 않는다. 동일한 입력도 대상 설정, 인증 상태, 세션 초기 조건이 다르면 서로 다른 실행 조건이므로, 자체 평가 설계에서는 이 조건들을 증거와 연결해야 한다. 모델만 호출한 시험과 응용 시스템을 통과한 시험도 구분해야 실패한 경계와 수정 책임을 특정할 수 있다.

**핵심 검증 단계**
- **가설과 경계 고정:** 공격자가 변경할 수 있는 입력, 시험할 진입점, 필요한 인증 조건, 기대 결과와 성공 기준을 정한다. 연결 설정을 잘못한 결과가 공격 효과로 해석되지 않도록 시험 조건과 공격 입력을 분리한다.
- **실행 책임 분리:** 수동 또는 자동 탐색이 만든 입력을 연결 계층이 대상 형식에 맞춘다. 요청별 서명이나 세션 생성 같은 부수 절차는 대상 호출을 성립시키는 책임이지, 취약점의 존재를 판정하는 책임이 아니다.
- **증거 유효성 확인:** 전송 상태, 응답 구조, 답변 추출 결과가 판정에 사용할 수 있는지 확인한다. 실행 예외나 타임아웃으로 유효한 관측을 얻지 못한 사례는 자체 설계에서 평가 보류로 분리하고, 안전성 결론을 부여하지 않는다.
- **가설 판정:** 예상한 결과와 실제 증거를 대조한다. 실행 상태가 성공이어도 주장한 취약점을 뒷받침하는 증거가 없으면 공격 성공으로 확정하지 않는다. 반대로 판정에 필요한 출력이 누락되었다면 공격 실패로 단정하지 않는다.
- **수정 검증:** 발견 사항, 변경 내용, 재실행 조건, 검증 결과를 연결한다. 종료 판단은 변경 파일의 존재가 아니라 해당 가설에 대한 재검증 증거를 기준으로 하고, 시험하지 않은 경계는 잔여 검토 범위로 남긴다.

따라서 **호출 완료와 공격 가설 입증은 별개다**.

## 핵심 수식·아키텍처·도표
다음은 **증거 분리와 판정 게이트를 위한 제안 프레임워크**다. 가운데 열은 Prisma AIRS 어댑터 계약에서 확인되는 접근 값과 반환형이며, 오른쪽 열은 자체 실행기나 평가 저장소에 별도로 설계할 권장 증거다. 어댑터에서 값에 접근할 수 있다는 사실을 제품이 해당 값을 감사 로그로 영구 보존한다는 의미로 해석해서는 안 된다.

| 별도 관리할 증거 항목 | 어댑터 계약에서 확인되는 값·반환형 | 자체 실행기에 권장하는 기록과 검수 기준 |
|---|---|---|
| 요청 입력 | `InferenceInput`은 프롬프트와 대화 이력을 전달하며, `PreProcessResult`는 대상에 보낼 요청을 구성함 | 평가 입력과 실제 전송 본문을 대응시키고, 연결 변환 과정에서 시험 내용이 달라졌는지 확인 |
| HTTP 상태 | `RawResponse.status_code`로 대상 HTTP 상태에 접근할 수 있음 | HTTP 상태와 전송 실패를 응답 내용과 별도로 기록하고, 알려진 실패는 판정 전에 분기 |
| 응답 구조 | `RawResponse.json_body`와 `headers`에 접근할 수 있음 | 답변 추출에 사용한 응답 경로와 구조 검증 결과를 남겨 파싱 실패를 대상의 행동과 구분 |
| 추출된 응답 | `PostProcessResult.output`은 추출한 답변 텍스트이며, 방식 B는 `CallTargetResult.output`으로 답변을 반환함 | 평가자가 실제로 받은 텍스트를 요청 증거와 연결하고, 오류 메시지가 답변으로 섞이지 않았는지 확인 |
| 평가 판정 | 제공된 어댑터 계약에는 공격 가설의 최종 판정 필드가 제시되지 않음 | 가설, 성공 기준, 판정 근거, 판정 보류 사유를 별도 기록하고 실행 완료 상태와 분리 |

Prisma AIRS의 평가 판정 저장 필드와 전체 감사 로그 보존 범위는 해당 주제에 대한 검증된 정보가 부족합니다. 따라서 이 표는 제품 기능 목록이 아니라, **연결 계약에서 확보할 수 있는 관측과 평가자가 추가로 책임져야 할 판단을 구분하는 검수표**로 사용한다.

## 운영 패턴과 검수 절차
코드 대신 **연결·실행 경계의 운영 검토 절차**를 사용한다. Prisma AIRS의 두 어댑터 방식은 이 경계를 확인하는 구체적인 계약 예시이며, 레드티밍 전체의 판정 절차를 대신하지 않는다.

- **입력 계약 확인:** 대상이 요구하는 요청 구조, 답변 위치, 인증 방식, 세션 생성 필요성을 먼저 확인한다. 연결 계층의 검수 목적은 시험 입력을 정확히 전달하고 응답을 정확히 추출하는 것이며, 공격 성공 판정을 수행하는 것이 아니다.
- **방식 A의 요청 구성 예:** `pre_process(context, inference_input)`에서 `context.vars["endpoint"]`를 `url`로 사용하고, `context.secrets["api_key"]`로 인증 헤더를 구성하며, `inference_input.prompt`를 요청 본문의 `message`에 배치한 `PreProcessResult`를 반환한다. **필수 필드는 `url`뿐이며 `method`의 기본값은 `POST`**다. 본문과 헤더의 필요 여부는 대상 계약에 따라 검토한다. 이 방식의 실제 대상 HTTP 호출은 AI Red Teaming이 수행한다.
- **방식 A의 응답 추출 예:** `post_process(context, raw_response)`에서 상태를 먼저 검사한다. 문서 예시처럼 HTTP 429라면 `raise_rate_limited(retry_after=30)`으로 오류 신호를 발생시키며, 여기의 30초는 해당 예시 값이지 모든 대상의 대기 정책이 아니다. 인증 오류도 오류 신호로 전달한다. 정상 응답은 `raw_response.json_body["reply"]`를 추출해 `PostProcessResult.output`으로 반환한다. `reply` 경로는 예시이므로 대상 스키마와 일치하는지 확인하고, 경로 누락을 빈 답변으로 대체하지 않도록 검토한다.
- **방식 B는 별도 방식으로 선택:** `call_target(context, inference_input)`만 구현해 어댑터가 대상 호출과 응답 반환을 모두 담당한다. 이를 정의하면 `pre_process()`와 `post_process()`는 비활성화되므로 방식 A의 후처리가 이어질 것으로 가정하지 않는다. 기본 연결이 지원하지 않는 WebSocket, SDK 기반 호출, 사용자 정의 스트리밍 등에 적용할 수 있다. 표준 HTTP의 다중 호출만 필요하다면 `pre_process()` 내부의 `context.http`를 사용하는 방식을 검토한다.
- **실패 경로 검수:** 요청 제한·인증 실패는 모델 응답으로 반환하지 않고, 응답 구조 불일치는 추출 실패로 다룬다. 자체 평가기에서는 이런 실행 실패가 공격 판정으로 넘어가지 않도록 게이트를 둔다. 어댑터 함수의 예외나 타임아웃은 해당 턴의 실행 실패로 처리된다는 계약도 함께 확인한다.
- **실행 예산 검수:** 호출 전체 실행 제한은 110초이고 `context.http`의 대상 호출 제한은 100초다. 이 클라이언트 밖의 호출에도 명시적 타임아웃을 설정하고, 무한 대기나 무제한 반복이 증거 수집을 막지 않도록 검토한다.

## 프로덕션 함정
- ❌ 실수: 자체 실행기에 권장한 실행 식별자·소요 시간·출력 잘림 여부를 Prisma AIRS가 자동 보존하는 필드로 간주하고 별도 증거 수집을 생략한다. → ✅ 해결: 해당 항목은 자체 수집 요구사항으로 명시하고, Prisma AIRS에서 확인된 `RawResponse.status_code`, `json_body`, `headers`와 `PostProcessResult.output`은 어댑터 접근 값이라는 범위로 한정한다.
- ❌ 실수: HTTP 429의 요청 제한 메시지나 인증 오류 본문을 `output`으로 반환하여 평가기가 대상의 정상 답변처럼 판정하게 만든다. → ✅ 해결: 요청 제한은 `raise_rate_limited`로, 인증 실패는 인증 오류 신호로 전달하고, 자체 평가기에서는 실행 실패를 판정 입력에서 분리한 뒤 유효한 응답의 재수집 조건을 정한다.
- ❌ 실수: 어댑터 모듈의 전역 변수에 대화 상태를 저장하고 다음 턴에도 유지될 것으로 가정하여 세션 연결이 끊긴 실행을 같은 조건의 시험으로 묶는다. → ✅ 해결: 스크립트는 매 턴 새로 로드되므로 필요한 상태는 계약에 따라 `context.auth`와 `context.session`으로 전달하고, 두 상태의 직렬화 크기 합계가 64 KB를 넘지 않도록 관리한다.
- ❌ 실수: 요청 본문이나 시각에 종속되는 서명을 `authenticate()`에서 한 번 생성해 캐시하고, 후속 요청에도 유효한 인증정보라고 간주하여 재사용한다. → ✅ 해결: `authenticate()`는 TTL이 있는 자격증명 획득에 사용하고, 요청별 서명은 구체적인 요청을 다루는 `pre_process()` 또는 `call_target()`에서 생성하도록 책임을 분리한다.

## 트레이드오프와 언제 무엇을 쓰나
아래는 제품이나 일반 방법론의 검증된 우열이 아니라, 평가 목적과 실행 계약을 바탕으로 한 **설계 판단용 휴리스틱**이다. 부적합은 해당 작업의 첫 번째 수단으로 부적합하다는 뜻이며, 전체 안전성 평가에서 레드티밍을 제외하라는 의미는 아니다.

**이럴 때 적합**
- **모델과 응용 계층 중 실패한 경계가 불명확할 때:** 같은 가설을 경계별로 나누어 시험하도록 설계하면 응답 생성 문제와 연결·세션 구현 문제를 서로 다른 수정 대상으로 배정할 수 있다. 대신 대상별 실행과 증거 대조의 복잡도가 증가한다.
- **보안 스캐너의 발견 사항이 실제 실행에서 성립하는지 확인해야 할 때:** 탐지 위치와 설명을 넘어서 실행 출력과 성공 기준을 대조하는 데 적합하다. 추가 호출 비용을 들여 실제 관측 증거를 확보할 필요가 있는지 판단한다.
- **대상별 인증·세션·요청 형식 차이를 포함한 취약 경로를 탐색할 때:** 대상 구성에 맞춘 실행 경로가 필요하므로 연결 계약을 명시한 레드티밍 설계가 적합하다. 다만 연결 구현 검증과 공격 효과 판정의 비용을 따로 배정해야 한다.

**이럴 때 부적합**
- **변경 범위가 요청·응답 스키마의 일치 여부뿐일 때 — 대안: 통합 계약 검증.** 확인할 조건이 구조적으로 정해져 있으므로 먼저 계약 검증으로 파싱 오류를 제거하는 편이 판정 복잡도를 줄인다.
- **목적이 소스 코드상의 취약 위치와 수정 후보를 찾는 것뿐일 때 — 대안: 보안 스캐닝.** 파일 경로·행 번호·수정 힌트를 제공하는 탐지 결과가 작업 목표에 직접 대응하므로, 대상 실행과 세션 관리 비용을 먼저 지출할 필요가 있는지 검토한다.
- **대상 호출 자체가 인증 갱신이나 요청 제한 처리 때문에 성립하지 않을 때 — 대안: HTTP 오류 처리 및 인증 흐름 검증.** 유효한 대상 관측이 없는 상태에서 공격 입력만 늘리면 실행 비용은 발생하지만 가설 판정에 필요한 증거는 확보되지 않는다.

## 업계 대화 맥락
다음은 실제 장애 보고가 아니라 **설계 리뷰와 사후 분석 문장 예시**다.

- "보안평가팀의 **자체 실행기 식별자 설계 예시**에서는 **`run_id`**를 실행 단위, **`session_id`**를 대화 단위로 정의하며, 이를 Prisma AIRS가 제공하는 필드로 가정하지 않습니다."
- "플랫폼팀의 **자체 캐시 정책 예시**에서는 대상별 인증정보가 섞이지 않도록 대상 설정별로 캐시를 분리하며, 이는 제품 문서에서 확인된 캐시 키 정책을 의미하지 않습니다."
- "어댑터 PR에서는 비민감 설정을 **`context.vars`**, 인증 비밀값을 **`context.secrets`**에서 읽도록 분리하고, 이 런타임 구분만으로 다른 저장소나 UI의 노출 정책까지 추정하지 않겠습니다."
- "런타임 설계 리뷰에서는 **`context.http`의 100초 제한**과 **호출 전체의 110초 제한**을 별도로 확인하고, 다른 클라이언트를 사용하는 경로에도 명시적 타임아웃을 요구합니다."
- "인증 PR에서는 **`authenticate()`의 TTL 캐시**와 **인증 오류 시 1회 재인증** 경로를 검증하되, 이를 공격 판정의 재시도 정책과 혼용하지 않겠습니다."
- "재검증 승인 기준에서는 **요청 입력·세션 초기 조건·대상 설정**의 대응 관계를 요구하며, 조건이 다른 실행 결과를 동일 취약점의 수정 증거로 자동 병합하지 않겠습니다."
- "사후 분석 템플릿에서는 **출력 잘림**과 **판정 근거 부족**을 별도 항목으로 기록하고, 증거가 불완전한 사례를 공격 실패로 종결하지 않도록 검토 게이트를 추가하겠습니다."

## 선행·대안·확장 개념
- (선행) **시스템 아키텍처** — 컴포넌트·데이터 흐름·진입점을 기술하는 별개 설계 개념으로, 평가 대상의 경계와 관측 지점을 정하고 실패 책임을 배정하는 전제가 된다.
- (선행) **인증** — 대상 접근을 성립시키는 독립적인 보안 메커니즘으로, 자격증명 획득·갱신·요청별 서명을 이해해야 실행 조건의 실패와 평가 대상의 행동을 구분할 수 있다.
- (대안) **보안 스캐닝** — 취약점 탐지라는 공통 목적에 대해 파일 위치·분류·수정 힌트 중심의 결과를 제공하는 접근으로, 실제 실행 증거보다 코드상의 문제 위치가 필요한 작업에서 우선 선택할 수 있다.
- (확장) **LLM 레드티밍** — 대규모 언어 모델에 대한 적대적 입력 탐색으로 평가 대상을 특수화한 접근으로, 모델 자체의 응답 평가와 응용 시스템 전체의 실행 경계를 나누는 데 유용하다.
- (확장) **메타 수준 레드티밍** — 개별 모델 평가와 전체 시스템 평가의 조정, 거버넌스 구조와 설계 가정의 검토로 범위를 확장하여 기술 실행 결과만으로 다루기 어려운 위험을 검토한다.

## references_en

- {"title": "Guide to Red Teaming Methodology on AI Safety (Version 1.00)", "authors": "AISI", "type": "docs", "url": "https://aisi.go.jp/assets/pdf/ai_safety_RT_v1.00_en.pdf", "tier": "primary", "annotation": "Guidance for planning assessments around system configurations, usage patterns, and AI safety concerns."}
- {"title": "Custom Target Adapters", "type": "docs", "url": "https://docs.paloaltonetworks.com/ai-runtime-security/ai-red-teaming/identify-ai-system-risks-with-ai-red-teaming/get-started-with-prisma-airs-ai-red-teaming/targets/custom-target-adapters", "tier": "primary", "annotation": "Details custom-target connections, execution location, secret handling, session state, and runtime limits."}
- {"title": "Functions", "type": "docs", "url": "https://docs.paloaltonetworks.com/ai-runtime-security/ai-red-teaming/identify-ai-system-risks-with-ai-red-teaming/get-started-with-prisma-airs-ai-red-teaming/targets/custom-target-adapters/adapter-contract/adapter-contract-functions", "tier": "primary", "annotation": "Clarifies adapter responsibilities for requests, replies, authentication, sessions, and error signals."}
- {"title": "Red Teaming AI Red Teaming", "type": "paper", "url": "https://arxiv.org/html/2507.05538v2", "tier": "primary", "annotation": "Explains why red teaming should challenge design assumptions and governance, not only technical components."}
- {"title": "What Is LLM Red Teaming? AI Safety, Risks, and Best Practices", "type": "blog", "url": "https://www.mend.io/blog/llm-red-teaming-threats-testing-best-practices", "tier": "secondary", "annotation": "Accessible guidance on ethical scope, risk-focused objectives, and the continuous break-fix process."}
