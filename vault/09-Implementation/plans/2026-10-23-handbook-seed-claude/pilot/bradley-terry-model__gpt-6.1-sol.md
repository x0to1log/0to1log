# Bradley–Terry Model — gpt-6.1-sol

- advanced 87 / basic 89 / gate pass / penalty 2 / $0.5318 / 774s

## definition_en

The Bradley–Terry model is a probabilistic model for pairwise comparisons that assigns each alternative a positive latent strength and relates their relative strengths to the probability of one being preferred, allowing observed wins or preferences to be used to infer scores, rank AI models or other alternatives, and predict unobserved comparisons.

## definition_ko

브래들리–테리 모형은 AI 모델 평가 등에서 얻은 쌍대 비교 결과로부터 각 대상의 잠재적 강도나 선호 점수를 추정하는 확률 모형으로, 두 대상의 상대적인 강도에 따라 한쪽이 선택될 확률을 표현하여 관측된 승패·선호를 전체 순위와 아직 직접 비교하지 않은 쌍의 결과 예측으로 연결한다.

## summary_en

The Bradley–Terry model estimates relative strength or appeal from comparisons between two options. Think of it as building a league table from head-to-head results, rather than asking everyone to rank all entries at once. It learns a strength for each entry and uses pairs of strengths to estimate which one is more likely to win. This helps turn scattered judgments into useful rankings and predictions.

## summary_ko

브래들리–테리 모형은 둘씩 비교한 결과를 모아 여러 대상의 상대적인 실력이나 선호도를 알아내는 방법이다. 모든 후보의 순위를 한꺼번에 정하는 대신, 두 후보 중 하나를 고른 기록들을 이어 붙인다고 생각하면 된다. 모형은 그 기록을 설명하는 대상별 점수를 찾고, 두 점수를 바탕으로 어느 쪽이 선택될 가능성이 높은지 계산한다. AI 모델 평가부터 상품 선호 조사까지, 흩어진 비교 결과를 전체 순위와 선택 확률로 바꾸는 데 쓰인다.

## body_basic_en

## Plain Explanation
Choosing among many AI models creates a practical problem: people may find it easier to judge two answers than to rank every model at once. These judgments produce **pairwise comparisons**, meaning comparisons of two options at a time. Simply counting victories misses an important detail, because different candidates may have faced different opponents.

To understand Bradley–Terry's probability rule, picture a raffle between two entries. If one entry has 3 tickets and the other has 1, the first has 3 of the 4 chances, or 75%. The model treats each candidate's **strength**, a positive number representing its competitiveness or appeal, like its share of those tickets, although strengths need not be whole numbers.

In real data, the tickets are not supplied in advance: the model estimates strengths from the observed comparisons. It adjusts the strengths together to make the recorded outcomes as probable as possible under its rule. Estimated strength therefore depends on the opponents faced, not just on the number of wins.

## Examples & Analogies
- **Wine tasting without a giant ranking task**: A tasting survey might ask volunteers to choose between two wines per round rather than rank the whole collection. The comparisons must connect all wines into one shared comparison network—a chain of comparisons linking any wine to any other—before relative strengths across the collection can be inferred. The fitted strengths can also support predictions for pairs that were never tasted together.
- **Ordering search results**: Imagine a search team asking reviewers which of two documents better answers the same query. Bradley–Terry could turn those choices into relevance scores used to order the documents.
- **Studying animal dominance**: Researchers studying a group of animals can record which animal wins each observed encounter. The model can turn those paired outcomes into estimated dominance strengths rather than requiring a complete round of encounters between every possible pair.

## At a Glance
| | Win percentage: descriptive baseline | Bradley–Terry model |
|---|---|---|
| Required records | Wins and total contests per candidate | Who beat whom in each comparison |
| Numerical interpretation | 6 wins in 10 contests means 60% | A fitted strength is not itself a win percentage |
| Opponent treatment | Does not adjust for opponent strength | Estimates strengths jointly across opponents |
| Main output | Observed fraction of wins | Relative strengths and choice probabilities for particular pairs |

Choose Bradley–Terry when your data are pairwise choices and your goal is to estimate relative strengths or choice probabilities, rather than just describe past results.

## Where and Why It Matters
- **Hypothetical video recommendations**: A platform could ask which of two videos deserves recommendation and fit Bradley–Terry scores from those choices. This would provide an ordering without requiring contributors to assign a separate numerical rating to every video.
- **Human-feedback training**: A reward model—a system that scores AI responses—can learn from human choices between responses using Bradley–Terry preference probabilities. This connects comparative judgments to scores used in AI training.
- **Tournament analysis**: A documented 2020 analysis used 2,123 games involving 16 teams to estimate team strengths and standard errors, which describe uncertainty in those estimates. This illustrates how a collection of individual results can support a shared strength scale with uncertainty information.
- **Disconnected comparison groups**: If two groups have no chain of comparisons linking them, comparisons alone cannot identify relative strengths across the groups. Bridging comparisons between those groups are needed.

## Common Misconceptions
- ❌ Myth: The higher-strength option will always win. → ✅ Reality: The model predicts probabilities, not guaranteed outcomes; an upset remains possible.
- ❌ Myth: A strength score measures absolute, objective quality. → ✅ Reality: Strength is relative to the alternatives and judgments being modeled; multiplying every positive strength by the same amount leaves all predicted probabilities unchanged.
- ❌ Myth: The original model automatically handles ties. → ✅ Reality: Its outcomes are win or lose; modeling a tie as a distinct outcome requires an extension.

## How It Sounds in Conversation
- "Before Friday's review, can we compare the **Bradley–Terry scores** with the raw **win rates**?"
- "Does the evaluation team's **comparison network** connect every candidate?"
- "For this survey, are we requiring a winner or adding an **extension for ties**?"
- "Can the research team send **uncertainty estimates** with the ranking?"
- "Please check the **predicted probabilities** against the recorded outcomes before we share the results."

## Related Reading
- (before) **Pairwise Comparison** — Learn how two-at-a-time judgments are collected before studying how Bradley–Terry turns them into strengths.
- (similar) **Logistic Regression** — A method for predicting outcome probabilities that shares Bradley–Terry's probability curve; it helps explain how strength differences become win probabilities.
- (similar) **Elo Ratings** — Uses a closely related win-probability rule on a chess-rating scale; compare that rating scale with Bradley–Terry's positive strengths.
- (next) **Plackett–Luce Model** — Extends the two-option rule to rankings of several items; read it when feedback orders more than a pair.
- (next) **Reinforcement Learning from Human Feedback** — Uses human judgments to guide AI training; Bradley–Terry provides a probability model for learning response scores from preferences.

## body_basic_ko

## 쉽게 이해하기
여러 AI 모델의 답변을 평가할 때, 모든 답변에 일관된 점수를 매기기는 어렵다. 후보가 많으면 전체 순서를 한꺼번에 정하는 일도 부담스럽다. 반면 답변 두 개를 나란히 놓고 어느 쪽이 더 나은지 고르는 일은 상대적으로 수월할 수 있다.

**브래들리–테리 모형**은 이렇게 두 개씩 비교한 결과를 모아 대상마다 상대적인 점수를 붙인다. 서로 다른 상대와 치른 경기 기록을 종합해 리그 전체의 전력을 가늠하는 것과 비슷하다. 단순히 선택된 횟수만 세는 것이 아니라, 어떤 상대를 두고 선택됐는지도 함께 반영한다.

모형은 각 대상에 0보다 큰 **강도 점수**를 두고, 두 점수가 합계에서 차지하는 몫으로 선택 확률을 표현한다. 설명을 위한 가상 점수가 A는 3, B는 1이라면, 합계 4 중 A의 몫이 3이므로 A의 선택 확률은 75%다. 실제 분석에서는 이런 점수를 미리 정하는 대신, 모아 둔 비교 결과를 가장 잘 설명하도록 추정한다.

## 비유와 예시
- **AI 모델의 답변 비교**: 같은 질문에 대한 두 모델의 답변을 보여 주고 더 나은 쪽을 고르게 하는 평가를 생각해 보자. 여러 모델 조합에서 모은 선택 기록으로 각 모델의 상대적인 평가 점수를 추정할 수 있다.
- **와인 시음 조사**: 참가자에게 모든 와인의 순서를 정하게 하는 대신, 두 종류를 맛보고 더 좋아하는 쪽을 고르게 한다. 서로 연결된 시음 기록을 모으면 모든 와인 쌍을 직접 비교하지 않아도 전체 선호 순위를 추정할 수 있다.
- **채용 후보 비교**: 지원자가 많아 전체 순서를 정하기 어렵다면, 두 후보 중 누가 더 적합한지 비교하는 상황을 생각해 보자. 모형은 이런 판단들을 상대 점수로 요약할 수 있으며, 그 점수는 입력된 비교 판단을 반영한다.

## 한눈에 비교
| 비교 기준 | 브래들리–테리 모형 | 플래킷–루스 모형 |
|---|---|---|
| 한 번에 다루는 대상 | 2개 | 2개 이상이며, 3개 이상의 순서도 가능 |
| 관측 기록의 예 | A가 B보다 선호됨 | A가 1위, B가 2위, C가 3위 |
| 확률로 설명하는 것 | 두 대상 중 한쪽이 선택되는 결과 | 여러 대상이 특정 순서로 놓이는 결과 |
| 두 대상만 있을 때 | 기본 적용 상황 | 브래들리–테리 모형과 같아짐 |

둘 중 하나를 고른 기록에는 브래들리–테리 모형을, 여러 후보의 순서 전체를 기록한 자료에는 이를 확장한 플래킷–루스 모형을 검토할 수 있다.

## 어디서 왜 중요한가
- **사람의 선호를 학습하는 보상 모형**: AI 응답에 평가 점수를 매기는 보상 모형을 훈련할 때, 사람의 선호 비교를 확률로 표현하는 기초가 된다.
- **검색 문서의 관련성 추정**: 학습 기반 검색 엔진에서 문서의 관련성을 추정하는 데 쓰여, 검색 결과의 순서를 정하는 문제와 연결된다.
- **Tournesol의 동영상 추천**: 고전형이 아닌 일반화된 확장 모형을 활용해, 참여자들이 어느 영상을 더 추천하는지 비교한 기록을 동영상 점수로 변환한다.
- **서로 단절된 평가 집단**: 두 집단 사이에 비교 기록이 전혀 없으면 관측된 비교만으로 공통 순위를 정할 수 없으므로, 평가 전에 집단들을 잇는 비교가 있는지 확인해야 한다.

## 자주 하는 오해
- ❌ 오해: 점수가 높은 대상은 낮은 대상을 반드시 이긴다. → ✅ 실제: 점수는 승리나 선택의 확률을 정할 뿐이며, 점수가 낮은 쪽이 선택되는 결과도 가능하다.
- ❌ 오해: 점수는 대상의 절대적인 품질을 나타낸다. → ✅ 실제: 양의 강도 점수는 상대적인 척도이며, 모든 점수에 같은 양수를 곱해도 비교 확률은 달라지지 않는다.
- ❌ 오해: 원래 모형에 무승부도 그대로 넣으면 된다. → ✅ 실제: 고전적인 모형은 승패처럼 두 가지 결과를 다루며, 무승부를 별도 결과로 설명하려면 이를 허용하는 확장 모형이 필요하다.

## 대화에서는 이렇게
- "평가팀은 금요일 리뷰 전에 **브래들리–테리 점수**와 단순 승률의 순위가 다른 후보부터 확인해 주세요."
- "직접 맞붙지 않은 두 후보의 **선택 확률**을 추정할 수 있을지, 연결된 비교 기록부터 볼까요?"
- "검색팀에서는 **브래들리–테리 모형**으로 문서 관련성을 점수화하는 안을 검토해 볼게요."
- "이번 평가표에는 무승부가 있으니 **기본 브래들리–테리 모형**을 적용하기 전에 처리 방식을 정하죠."
- "리뷰 자료에는 **브래들리–테리 모형**이 예측한 확률과 실제 선택 결과의 차이도 함께 넣어 주세요."

## 함께 읽으면 좋은 용어
- (기초) **쌍대 비교** — 전체 순위를 한 번에 묻는 방식과 무엇이 다른지 알면, 이 모형에 어떤 데이터를 모아야 하는지 이해하기 쉽다.
- (유사) **로지스틱 회귀** — 두 결과의 확률을 표현하는 수학적 연결이 있어, 대상별 강도 추정과 일반적인 확률 예측의 관계를 살펴보기 좋다.
- (유사) **Elo 레이팅** — 척도를 맞추면 승리 확률 표현이 연결되므로, 경기 평점과 쌍대 비교 모형이 어떻게 이어지는지 이해하기 좋다.
- (심화) **플래킷–루스 모형** — 두 대상의 비교를 넘어 여러 대상의 순서 전체를 다루고 싶을 때 읽기 좋은 확장 모형이다.
- (심화) **인간 피드백 기반 강화학습** — 사람의 선호 비교가 보상 모형 학습의 기반이 되는 이유를 익힌 뒤, 그 평가가 AI 학습에 어떻게 연결되는지 살펴보기 좋다.

## body_advanced_en

## Technical Definition & How It Works
The **Bradley–Terry model** is a Bernoulli paired-comparison model whose log-odds equal the difference between two latent log-strengths. Its statistical components are an alternative-indexed parameter vector, an observation design specifying which alternatives were compared, and a likelihood for the recorded binary outcomes. Fitting the model means estimating shared alternative parameters, not estimating an unrelated probability for every pair.

Each comparison contributes a sparse difference row: a positive coefficient for the first alternative, a negative coefficient for the second, and zeros elsewhere. Applying this row to the parameter vector produces the comparison's logit. Under the conditional-independence likelihood, observed outcomes contribute additive negative log-likelihood terms; repeated wins with the same orientation can therefore be compressed into directed win counts without changing the objective.

**The sharing structure is the central modeling constraint.** Every comparison involving an alternative updates the same parameter. Consequently, log-odds add along comparison paths because intermediate score differences cancel. An arbitrary collection of pair-specific probabilities need not satisfy this restriction, so a converged optimizer does not establish that a one-dimensional score representation fits the observations.

A fitting pipeline has the following responsibility boundaries:

- **Validate the observation contract:** assign stable integer indices, retain winner/loser orientation, reject self-comparisons, and require positive counts. A count represents repeated binary observations, not the magnitude of one victory.
- **Assemble the likelihood:** compute a score difference for each observed directed pair and evaluate its contribution in log space. There is no need to exponentiate absolute scores or materialize every possible pair.
- **Choose the estimator:** unregularized maximum likelihood requires an identification convention and a separate check that a finite optimum exists. A zero-mean Gaussian prior on log-strengths instead defines a MAP estimator with explicit shrinkage and an anchor for the score vector.
- **Evaluate objective and gradient:** each directed pair contributes equal-and-opposite likelihood gradients to its two alternatives. The Gaussian prior contributes an additional gradient to every score; the optimizer, rather than the callback, owns parameter updates and stopping decisions.
- **Validate the fitted artifact:** retain objective value, optimizer status, and maximum absolute gradient. Examine observed-minus-predicted residuals separately, because numerical convergence and statistical fit answer different questions.

For n alternatives and K nonzero directed win counts, an objective-and-gradient evaluation requires **O** (n + K) work and storage, including the parameter gradient. With M uncompressed observations, processing those observations instead costs **O** (n + M) per evaluation. These are evaluation costs, not total fitting-time guarantees: the number of optimizer iterations remains a separate concern. The sparse likelihood representation avoids requiring a dense n-by-n probability matrix during fitting.

## Formulas, Architecture, and Diagrams
Let βᵢ be alternative i's log-strength, let pᵢ be its positive strength, and let dᵢⱼ denote the score difference. Define the sigmoid σ and softplus function sp as follows:

$$p_i=e^{\beta_i},\qquad d_{ij}=\beta_i-\beta_j,\qquad \sigma(u)=\frac{1}{1+e^{-u}},\qquad \operatorname{sp}(u)=\log(1+e^u).$$

Substitution into the strength-ratio probability gives:

$$\Pr(i>j)=\frac{e^{\beta_i}}{e^{\beta_i}+e^{\beta_j}}=\sigma(d_{ij}).$$

**From observations to the optimization objective.** Let E contain the observed directed winner/loser pairs, and let wᵢⱼ count how often i defeated j. For independent zero-mean Gaussian priors with variance 1/λ on the log-strengths, where λ is positive prior precision, the negative log-posterior, up to constants independent of β, is:

$$L_\lambda(\boldsymbol\beta)=\sum_{(i,j)\in E}w_{ij}\operatorname{sp}(-d_{ij})+\frac{\lambda}{2}\sum_{i=1}^{n}\beta_i^2.$$

The first term follows from taking the negative logarithm of the product likelihood. The second follows from the Gaussian density's quadratic exponent; setting λ to zero recovers the negative log-likelihood.

Let eᵢ be the ith coordinate basis vector. Differentiating one pair contribution gives:

$$\nabla\!\left[w_{ij}\operatorname{sp}(-d_{ij})\right]=-w_{ij}\sigma(-d_{ij})(e_i-e_j).$$

Thus the winner and loser receive opposite-signed gradients. Differentiating again gives:

$$\nabla^2 L_\lambda=\sum_{(i,j)\in E}w_{ij}\sigma(d_{ij})\sigma(-d_{ij})(e_i-e_j)(e_i-e_j)^\top+\lambda I.$$

Here I is the identity matrix. Each likelihood term is positive semidefinite; positive λ adds curvature in every direction. The quadratic penalty also grows without bound as the score-vector norm grows, yielding a finite, unique MAP optimum for this objective.

**Identification is not finite-MLE existence.** Without the prior, adding a common constant c to every score changes no difference:

$$L_0(\boldsymbol\beta+c\mathbf{1})=L_0(\boldsymbol\beta).$$

The vector 1 contains all ones. A convention such as zero mean removes this universal location ambiguity, but it does not prevent score differences from diverging. For example, consider two alternatives with two wins in one direction and no reverse wins. Even with centered scores, their objective is:

$$\boldsymbol\beta=(t/2,-t/2),\qquad L_0(t)=2\operatorname{sp}(-t),\qquad \frac{dL_0}{dt}=-2\sigma(-t)<0.$$

The loss approaches zero as t increases, but no finite t attains that limit. The scores are identified by the convention, yet a finite MLE does not exist.

**A finite numerical check.** For eight wins in one direction and two in the reverse direction, the unregularized derivative with respect to their score difference d is:

$$-8\sigma(-d)+2\sigma(d)=10\sigma(d)-8.$$

Setting it to zero gives a fitted probability of **0.8**, a difference of **ln(4), approximately 1.386**, and centered scores of approximately **+0.693 and −0.693**. These are unregularized estimates; adding the Gaussian prior changes them.

## Code or Pseudocode
This **pseudocode** fits the summed negative log-posterior using directed win counts. `MINIMIZE_WITH_GRADIENT` denotes an abstract host-side optimizer; the callback supplies only the objective and its gradient. The stable expressions avoid positive exponential arguments and avoid subtracting a nearly saturated sigmoid from one.

```text
# WinCount = (winner: Integer, loser: Integer, count: Integer)
function fit_bt(n: Integer, wins: List[WinCount], precision: Real,
                tolerance: Real) -> FitResult:
    if n < 2 or length(wins) == 0:
        raise InvalidInput("Require alternatives and observed comparisons")
    if not finite(precision) or precision <= 0:
        raise InvalidInput("Require positive Gaussian prior precision")
    if not finite(tolerance) or tolerance <= 0:
        raise InvalidInput("Require a positive gradient tolerance")
    for winner, loser, count in wins:
        if not (0 <= winner < n and 0 <= loser < n):
            raise InvalidInput("Alternative index outside the score vector")
        if winner == loser or count <= 0:
            raise InvalidInput("Require distinct alternatives and positive counts")

    function objective(beta: Vector[n]) -> (Real, Vector[n]):
        if not all_finite(beta):
            raise NumericalFailure("Non-finite optimizer parameters")
        loss = 0.5 * precision * dot(beta, beta)
        gradient = precision * copy(beta)          # Gaussian prior gradient
        for winner, loser, count in wins:
            x = beta[loser] - beta[winner]        # Negative winner margin
            q = exp(-abs(x))
            sigmoid_x = 1 / (1 + q) if x >= 0 else q / (1 + q)
            loss += count * (max(x, 0) + log1p(q)) # Stable softplus(x)
            g = -count * sigmoid_x
            gradient[winner] += g
            gradient[loser] -= g                 # Opposite pair contribution
        if not finite(loss) or not all_finite(gradient):
            raise NumericalFailure("Non-finite posterior evaluation")
        return loss, gradient

    result = MINIMIZE_WITH_GRADIENT(objective, zeros(n), tolerance)
    loss, gradient = objective(result.parameters)
    gradient_inf = max(abs(gradient))
    return FitResult(scores=result.parameters, objective=loss,
                     converged=result.success and gradient_inf <= tolerance,
                     optimizer_status=result.status,
                     iterations=result.iterations, gradient_inf=gradient_inf)
```

Invalid observations fail before optimization; non-finite evaluations fail at the numerical boundary. An iteration limit or other unsuccessful termination remains visible through the returned status and `converged` flag. **Engineering guidance:** do not promote a score vector whose convergence checks fail, even if its ordering appears plausible.

## Production Pitfalls
- ❌ Mistake: Canonicalizing alternative IDs while leaving winner/loser labels unchanged silently reverses some likelihood contributions → ✅ Fix: Make orientation part of the data contract, swap labels when reordering pairs, and test that each pair's likelihood gradients sum to zero before adding the prior.
- ❌ Mistake: Computing exponentials of absolute scores or taking the logarithm of an already rounded win probability creates overflow or infinite loss → ✅ Fix: Evaluate stable softplus and sign-branched sigmoid expressions; test score differences of −1000, 0, and +1000 for finite loss, correct gradient signs, and per-observation gradient magnitudes no greater than one.
- ❌ Mistake: Replacing the summed likelihood with its average while keeping the same prior penalty unintentionally changes the estimator → ✅ Fix: Record the objective normalization explicitly; if dividing the likelihood by the observation count, divide the prior penalty by that count too when the intention is to preserve the original MAP optimum.
- ❌ Mistake: Publishing the last optimizer iterate after an iteration limit treats an available parameter vector as a validated estimate → ✅ Fix: Require finite parameters and objective, inspect termination status and maximum absolute gradient, and keep numerical convergence checks separate from observed-minus-predicted residual analysis.

## Tradeoffs — When to Use What
**Suitable — engineering selection criteria**

- **Binary observations with shared alternative effects:** use classical Bradley–Terry when a single log-strength per alternative is the intended representation. Sharing n parameters across comparisons avoids maintaining an independent probability for every observed pair, at the cost of restricting the probability structure.
- **Repeated binary comparisons in a batch estimator:** directed win counts preserve the likelihood while reducing evaluation work from individual records to distinct directed pairs. This reduces computation when many records repeat the same comparison orientation; it does not justify treating dependent observations as independent.
- **A score estimator that must remain finite under one-sided outcomes:** use a Gaussian-prior Bradley–Terry MAP objective when shrinkage is acceptable. Positive prior precision supplies a unique finite optimum, but the resulting scores depend on that precision and are not unregularized MLEs.

**Unsuitable — change the observation model rather than only the encoding**

- **A finite scale of graded comparison outcomes:** consider **K-nary-GBT** when the categories carry information beyond winner identity. Thresholding them to binary labels discards distinctions; retaining them requires a richer likelihood and an explicit category interpretation.
- **Continuous comparison measurements:** consider **Gaussian-GBT** rather than passing measurement magnitudes into a binary win-count field. Bradley–Terry counts repeated binary events, so this shortcut changes evidence weight instead of modeling a continuous observation; the alternative requires choosing a continuous observation distribution.
- **Unbounded discrete comparison evidence:** consider **Poisson-GBT**, with its observation convention checked before implementation. Binarization cannot retain observed magnitudes, while a richer discrete likelihood adds distributional assumptions and implementation complexity.

The generalized family constructs comparison models from a specified distribution for comparisons between equally scored alternatives. Choosing an observation-matched member is therefore a statistical design decision, not merely a solver replacement. Its Gaussian-prior MAP guarantees should not be transferred automatically to arbitrary encodings or estimators.

## Industry Communication
**Engineering guidance — illustrative review comments:**

- "For the **evaluation team's batch-fit review**, require **optimizer status**, **objective value**, and **maximum absolute gradient** before promoting the score vector."
- "The **data-contract PR** should preserve **winner/loser orientation** during ID canonicalization and verify that count compression leaves the likelihood unchanged."
- "The **numerics review** should include score differences of **−1000 and +1000**, checking finite posterior evaluations and the expected gradient signs."
- "The **estimation design** must record the **zero-mean Gaussian prior precision**, because this implementation returns a **MAP estimate**, not an unregularized MLE."
- "Any claim about **bounded single-comparison effects** must retain the **Gaussian-prior GBT qualification**, rather than extending that result to arbitrary fitting procedures."
- "The **residual report** should retain **observed-minus-predicted outcomes** by ordered pair, because optimizer convergence alone does not establish statistical fit."
- "A schema change from binary labels to **continuous comparison evidence** requires an **observation-model review**, not just a numeric-field migration."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Maximum likelihood estimation** — Provides the product-of-comparison likelihood and its optimization target; understanding it is necessary to distinguish parameter identification from the existence of a finite optimum.
- (prerequisite) **Maximum a posteriori estimation** — Explains why a Gaussian prior adds a quadratic log-score penalty and changes the estimator, making prior precision a statistical choice rather than only an optimizer setting.
- (alternative) **Thurstonian models** — Provide a separate probabilistic approach to paired-comparison scoring, so choosing this family changes the comparison model rather than merely changing how Bradley–Terry parameters are optimized.
- (extension) **Generalized Bradley–Terry models** — Extend paired-comparison observations to richer discrete or continuous values; under Gaussian score priors, their MAP estimators have strong-convexity, monotonicity, and bounded single-comparison-effect guarantees.

## body_advanced_ko

## 기술적 정의와 동작 원리
브래들리–테리 모형은 대상별 로그 강도 β의 차이를 선형예측자로 사용하는 **쌍대 비교 로지스틱 모형**이다. 각 관측의 결과는 조건부 Bernoulli 변수이며, 비교 결과들이 β를 조건으로 독립이라는 가정 아래 전체 우도를 구성한다. 같은 쌍의 관측이 동일한 비교 확률을 공유한다면, 개별 기록을 양방향 승리 횟수로 집계해도 β에 관한 우도 정보는 유지된다.

**추정의 입력과 책임 경계**는 다음과 같다. 데이터 계층은 대상 식별자와 양방향 승리 횟수를 전달하고, 모형 계층은 목적함수와 기울기를 계산한다. 실제 탐색 방향·단계 크기·반복 종료는 호스트 최적화기가 담당하며, 결과 발행 여부는 별도의 검증 계층이 판정한다. 모형의 볼록성과 최적화기의 정상 종료, 관측 자료가 뒷받침하는 해석 범위는 서로 다른 조건이다.

- **입력 검증:** 관측된 쌍만 저장하고, 자기 비교·음수 횟수·범위를 벗어난 식별자를 차단한다. 비교 그래프의 성분 식별자도 함께 계산해 추정값의 해석 범위를 보존한다.
- **추정 대상 결정:** 비정규화 추정은 음의 로그우도 최소화다. 가우스 사전을 사용하는 MAP 추정은 여기에 양의 이차 벌점을 더하므로, 같은 자료라도 두 추정량은 일반적으로 다르다.
- **반복 계산:** 현재 β에서 목적함수와 기울기를 계산해 최적화기에 제공한다. 반복 한도는 계산 자원의 상한이지, 해를 얻었다는 판정 기준이 아니다.
- **종료 검증:** 정상 종료 상태, 반복 한도 준수, 모수·목적함수·기울기의 유한성, 최종 기울기 기준을 모두 통과해야 추정 성공으로 판정한다. 순위가 더 이상 바뀌지 않거나 목적함수 변화가 작다는 사실만으로는 충분하지 않다.
- **발행 검증:** 수치적으로 유일한 MAP 해가 존재하더라도, 관측 없는 대상이나 서로 다른 비교 성분 사이의 차이를 자료가 식별했다고 해석하지 않는다. 아래 코드의 무관측 발행 차단은 이 구분을 강제하는 운영 정책이다.

**유한해와 식별성은 구분해야 한다.** 비정규화 우도는 모든 β에 같은 상수를 더해도 변하지 않는다. 평균을 고정하면 이 위치 자유도는 제거되지만, 한쪽이 전승한 자료에서 점수 차이가 무한대로 커지는 문제까지 해결되지는 않는다. 반면 모든 점수에 양의 정밀도를 갖는 가우스 사전을 적용하면 목적함수가 강볼록하고 무한대에서 발산하므로 유한하고 유일한 MAP 해를 얻는다. 이는 사전이 해를 결정하는 방향을 추가한다는 뜻이지, 없던 비교 증거를 생성한다는 뜻은 아니다.

대상 수를 K, 저장된 관측 쌍 수를 E라고 하면, 희소 입력의 목적함수·기울기 계산은 **O** (E + K) 시간이며 입력과 작업 벡터는 O(E + K) 공간에 저장할 수 있다. 이는 최적화기 자체의 추가 작업 공간을 제외한 값이다. 전체 헤시안을 밀집 행렬로 만들면 O(K²) 공간이 필요하지만, 각 쌍이 두 좌표에만 기여하므로 헤시안–벡터 곱은 O(E + K)에 계산할 수 있다.

**근거와 유도의 경계:** 로짓 표현·승리 횟수 우도와 가우스 사전하의 강볼록성은 제공 자료에 명시되어 있다. 다음 절의 기울기·헤시안·유한해 논증은 그 우도와 명시적으로 선택한 사전에서 직접 유도한 결과다. 코드 절의 허용오차, 발행 차단, 테스트 합격 기준은 논문에 보고된 성능 결과가 아니라 구현 검토를 위한 권고다.

## 핵심 수식·아키텍처·도표
**집계 우도에서 목적함수로**

관측 쌍의 집합을 ℰ라 하고, 각 쌍은 임의로 정한 한 방향으로 한 번만 표현한다. wᵢⱼ는 i의 승리 횟수, wⱼᵢ는 j의 승리 횟수이며, nᵢⱼ는 두 횟수의 합이다. eᵢ는 i번째 좌표만 1인 K차원 단위벡터이고, β는 K차원 로그 강도 벡터다.

$$x_{ij}=e_i-e_j,\qquad d_{ij}=x_{ij}^{\mathsf T}\beta,\qquad q_{ij}=\sigma(d_{ij})=\frac{1}{1+e^{-d_{ij}}},\qquad n_{ij}=w_{ij}+w_{ji}$$

한 쌍의 우도는 qᵢⱼ의 i 승리 횟수 제곱과 1−qᵢⱼ의 j 승리 횟수 제곱을 곱한 것이다. 로그를 취하고 부호를 바꾸면 다음 두 표현을 얻는다. 집계 횟수의 조합계수는 β와 무관하므로 최적화에서 생략할 수 있다.

$$L(\beta)=\sum_{(i,j)\in\mathcal E}\left[-w_{ij}\log q_{ij}-w_{ji}\log(1-q_{ij})\right]$$

$$L(\beta)=\sum_{(i,j)\in\mathcal E}\left[n_{ij}\log(1+e^{d_{ij}})-w_{ij}d_{ij}\right]$$

**가우스 사전과 MAP 목적함수**

각 βᵢ에 독립적인 평균 0, 분산 λ⁻¹의 가우스 사전을 둔다. 여기서 λ는 모든 좌표에 적용되는 사전 정밀도이며, 아래 강볼록성·유일성 결론에는 반드시 **λ > 0**이 필요하다.

$$F_\lambda(\beta)=L(\beta)+\frac{\lambda}{2}\lVert\beta\rVert_2^2,\qquad \lambda>0$$

미분은 쌍별 점수 차이 d에서 시작한다. log(1+exp(d))의 미분은 σ(d)이고, σ(d)의 미분은 σ(d)(1−σ(d))다. 여기에 d의 β에 대한 기울기 xᵢⱼ를 적용한다.

$$\frac{\partial L_{ij}}{\partial d_{ij}}=n_{ij}q_{ij}-w_{ij},\qquad \frac{\partial^2 L_{ij}}{\partial d_{ij}^2}=n_{ij}q_{ij}(1-q_{ij})$$

따라서 벌점은 기울기에 λβ를, 헤시안에 λIₖ를 추가한다. Iₖ는 K차원 항등행렬이다.

$$\nabla F_\lambda(\beta)=\sum_{(i,j)\in\mathcal E}(n_{ij}q_{ij}-w_{ij})x_{ij}+\lambda\beta$$

$$\nabla^2F_\lambda(\beta)=\sum_{(i,j)\in\mathcal E}n_{ij}q_{ij}(1-q_{ij})x_{ij}x_{ij}^{\mathsf T}+\lambda I_K$$

임의의 K차원 벡터 v에 대해 각 쌍의 곡률 기여는 음이 아니다.

$$v^{\mathsf T}\nabla^2F_\lambda(\beta)v=\sum_{(i,j)\in\mathcal E}n_{ij}q_{ij}(1-q_{ij})(v_i-v_j)^2+\lambda\lVert v\rVert_2^2\geq\lambda\lVert v\rVert_2^2$$

이 식이 λ-강볼록성을 보인다. 또한 L은 음이 아니므로 Fλ는 β의 크기가 커질 때 무한대로 발산한다. 따라서 최솟값이 존재하며 강볼록성 때문에 유일하다. λ가 0이면 상수 벡터 방향의 곡률이 사라지고, 비교 그래프가 분리되어 있으면 성분마다 별도의 위치 자유도가 남는다.

**검산용 수치 예시 — 보고된 실험값이 아닌 계산 예제**

대상이 둘이고 승리 횟수가 각각 4회와 2회라고 하자. β=(0, 0), λ=1에서 예측 승리 횟수는 양쪽 모두 3회다.

$$F_1(0,0)=6\log 2,\qquad \nabla F_1(0,0)=\begin{pmatrix}-1\\1\end{pmatrix},\qquad \nabla^2F_1(0,0)=\begin{pmatrix}2.5&-1.5\\-1.5&2.5\end{pmatrix}$$

기울기의 음수 방향으로 이동하면 첫 대상의 점수는 올라가고 둘째 점수는 내려간다. 헤시안의 고유값은 1과 4이며, 사전이 없을 때 곡률이 0이던 공통 이동 방향에도 곡률 1이 생긴다.

**수치 계산에서는 동치인 안정 표현을 사용한다.** 아래 softplus 항등식은 지수함수의 인자를 항상 0 이하로 유지한다. 두 승리 횟수에 대한 항을 따로 계산하면 큰 수끼리의 뺄셈도 피할 수 있다.

$$\operatorname{softplus}(z)=\max(z,0)+\log(1+e^{-|z|})$$

$$L_{ij}=w_{ij}\operatorname{softplus}(-d_{ij})+w_{ji}\operatorname{softplus}(d_{ij})$$

## 코드 또는 의사코드
**교육용 의사코드:** 희소 입력의 각 행은 `(i, j, (i 승리 횟수, j 승리 횟수))`다. 관측 없는 쌍은 저장하지 않는다. `Vector`는 실수 벡터이며, `require`는 조건 불충족 시 실행을 중단한다. `host_minimize`는 목적함수·기울기를 받아 실행하는 추상 호스트 최적화기 계약으로, 특정 라이브러리의 API가 아니다.

ε는 단순한 표시용 설정이 아니라 **호스트 최적화기의 기울기 허용오차**에 전달되고, 반환 직전 동일한 무한대 노름 기준으로 재검사된다. 아래 구현은 양의 가우스 사전을 사용하는 MAP 추정만 허용한다.

```python
# 교육용 의사코드: 벡터 연산과 최적화기는 호스트가 제공한다.
def fit_bt(n: int, pairs: list[tuple[int, int, tuple[int, int]]],
           lam: float, eps: float, max_iter: int,
           host_minimize: Optimizer) -> dict:
    require(is_integer(n) and n >= 2, "대상 수 오류")
    require(is_finite(lam) and lam > 0, "양의 사전 정밀도 필요")
    require(is_finite(eps) and eps > 0, "허용오차 오류")
    require(is_integer(max_iter) and max_iter > 0, "반복 한도 오류")
    require(len(pairs) > 0, "운영 정책: 무관측 결과 발행 금지")
    observed = zeros(n)
    for i, j, (a, b) in pairs:
        require(all_integer(i, j, a, b), "식별자와 횟수는 정수")
        require(0 <= i < n and 0 <= j < n and i != j, "비교 쌍 오류")
        require(a >= 0 and b >= 0 and a + b > 0, "승리 횟수 오류")
        observed[i] += a + b
        observed[j] += a + b
    require(all(observed > 0), "운영 정책: 무관측 대상의 발행 금지")
    components = undirected_components(n, [(i, j) for i, j, _ in pairs])

    def softplus(z: float) -> float:
        return max(z, 0.0) + log1p(exp(-abs(z)))

    def value_grad(beta: Vector) -> tuple[float, Vector]:
        value = lam * dot(beta, beta) / 2
        grad = lam * beta
        for i, j, (a, b) in pairs:
            d = beta[i] - beta[j]
            value += a * softplus(-d) + b * softplus(d)
            if d >= 0:
                t = exp(-d)
                p, q = 1 / (1 + t), t / (1 + t)
            else:
                t = exp(d)
                p, q = t / (1 + t), 1 / (1 + t)
            residual = b * p - a * q
            grad[i] += residual
            grad[j] -= residual
        return value, grad

    result = host_minimize(value_grad, initial=zeros(n),
                           gradient_tolerance=eps, gradient_norm="inf",
                           max_iterations=max_iter)
    require(result.status == "converged" and
            0 <= result.iterations <= max_iter, "最適化未完了".replace("最適化未完了", "최적화 미완료"))
    beta = result.x
    require(len(beta) == n and all_finite(beta), "비유한 모수 또는 차원 오류")
    value, grad = value_grad(beta)
    require(is_finite(value) and all_finite(grad), "비유한 최종 계산값")
    require(max(abs(grad)) <= eps, "최종 기울기 기준 미충족")
    return {"beta": beta, "components": components,
            "cross_component_publication_allowed": False}
```

무관측 자료에서도 사전만으로 수학적 MAP 해는 존재할 수 있다. 따라서 코드의 발행 차단을 모형의 존재 조건으로 설명하면 안 된다. 연결되지 않은 자료는 계산하되 성분 표지를 반환하며, 성분 간 결과를 자동 발행하지 않는 정책을 적용한다.

**필수 회귀 테스트** — 다음 수치와 허용오차는 구현 검산용 설정이다.

| 테스트 | 입력·조작 | 합격 기준 |
|---|---|---|
| 쌍 순서 반전 | `(0, 1, (4, 2))`를 `(1, 0, (2, 4))`로 교체 | 같은 β에서 목적함수와 대상별 기울기가 동일 |
| 기울기 유한차분 | 위 자료, β=(0.2, −0.1), λ=1, 중앙차분 간격 10⁻⁶ | 각 좌표의 중앙차분과 분석 기울기 절대오차가 10⁻⁵ 이하 |
| 극단적 점수 차이 | 양방향 1승씩인 자료에 β=(500, −500) 및 반전값 적용 | 목적함수·기울기가 유한하고 방향 반전에 따른 대칭성 유지 |
| 연결되지 않은 자료 | 대상 4개에 `(0, 1, (2, 1))`, `(2, 3, (1, 2))`, λ=1 | 유한한 추정값, 성분 2개, 성분 간 발행 불허 표지 반환 |
| 무관측 발행 차단 | 빈 자료 또는 관측에 한 번도 등장하지 않는 대상 포함 | 최적화 결과를 발행하지 않고 정책 오류 반환 |
| 종료 검증 | 반복 한도 종료, 비유한 반환값, 기준 초과 기울기를 각각 주입 | 어느 경우도 성공 결과로 반환하지 않음 |

## 프로덕션 함정
- ❌ 실수: 쌍 식별자를 정렬하면서 양방향 승리 횟수는 원래 순서에 남겨 두어 일부 기록의 승패 의미를 뒤집는다. → ✅ 해결: 식별자 순서와 횟수 순서를 하나의 변환으로 처리하고, 순서를 함께 반전해도 목적함수와 기울기가 유지되는 테스트를 둔다.
- ❌ 실수: 합계 로그우도를 평균 로그우도로 변경하면서 벌점 계수는 유지하여 동일한 사전을 적용한 실험이라고 비교한다. → ✅ 해결: 목적함수의 정규화 단위를 계약에 기록하고, 같은 사전을 유지하려면 평균 손실의 벌점 계수를 기존 계수에서 총 관측 수로 나눈 값으로 조정한다.
- ❌ 실수: 서로 다른 관측 조건을 무조건 합친 뒤 전체 잔차 평균만 확인하여, 같은 쌍이 동일한 확률을 공유한다는 가정을 검토하지 않는다. → ✅ 해결: 집계 전에 필요한 조건 식별자를 보존하고 조건별 관측 결과와 예측 잔차를 점검하여, 공통 점수 가정의 적용 범위를 명시한다.
- ❌ 실수: 최적화는 안정적인 로그 공간에서 수행했지만 후속 서비스에서 양의 강도를 얻으려고 점수를 바로 지수화하여 수치 오류를 만든다. → ✅ 해결: 로그 강도를 기본 저장 형식으로 유지하고 요청된 쌍의 점수 차이에서 안정적인 분기식으로 확률을 계산하며, 극단값 테스트를 후속 경로에도 적용한다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**

- **고정된 대상 효과로 설명할 수 있는 이진 비교를 대량 집계할 때:** 쌍별 횟수로 우도를 계산하므로 개별 비교를 매 반복마다 다시 순회할 필요가 없다. 비용은 총 비교 횟수보다 저장된 관측 쌍 수에 의해 좌우된다.
- **한쪽으로 치우친 승패에서도 유한한 점수가 필요할 때:** 양의 가우스 사전을 사용하는 MAP는 발산 방향에 곡률을 추가한다. 대신 점수 차이가 축소될 수 있으므로, 유한해 확보와 추정 편향 사이의 선택을 문서화해야 한다.
- **목적함수와 종료 판정을 독립적으로 검증해야 할 때:** 분석 기울기와 헤시안 구조를 사용할 수 있어 호스트 최적화기의 반환값을 별도로 검사할 수 있다. 다만 강볼록성이 특정 반복 횟수나 지연시간을 보장하지는 않는다.

**이럴 때 부적합**

- **연속적인 비교 강도를 관측하고 그 크기까지 설명해야 할 때:** **Gaussian-GBT** 같은 연속값 비교 모형을 검토한다. 이진화하면 크기 정보가 우도에서 사라지며, 대안에서는 연속 관측에 맞는 분포 가정을 추가로 검토해야 한다.
- **선호 강도가 여러 이산 단계로 기록될 때:** **K-nary-GBT**를 검토한다. 기본 이진 우도는 중간 단계의 차이를 표현하지 못하며, 다단계 모형은 결과 공간과 입력 검증 규칙이 더 복잡해지는 비용을 감수한다.
- **단일 점수보다 모수의 사후 불확실성이 의사결정의 핵심일 때:** **베이지안 BT의 Gibbs 샘플링** 같은 사후 추론을 검토한다. 최종 기울기가 작은 MAP 점 하나만으로 사후 분포를 요약할 수는 없으며, 샘플링을 선택하면 반복 계산과 수렴 진단 부담이 추가된다.

## 업계 대화 맥락
아래는 실제 사건이나 측정 결과를 인용한 것이 아니라, 설계 검토에서 사용할 수 있는 문장 예시다.

- "통계 검증팀의 승인 조건에는 **최종 기울기 무한대 노름 10⁻⁶ 이하**와 **반복 한도 내 정상 종료**를 모두 명시해 주세요."
- "데이터 계약 PR은 **4승·2패의 쌍 순서 반전 테스트**를 포함해야 하며, 식별자만 바꾸는 변환은 입력 계약 위반으로 처리하겠습니다."
- "추정 실험의 재현성 문서에는 **합계 우도와 평균 우도의 구분**을 기록하고, 정규화 변경 전후의 **사전 정밀도**가 같은지 확인해야 합니다."
- "추론 서비스 인터페이스는 **로그 강도와 비교 성분 식별자**를 함께 전달하도록 하고, 점수 벡터만으로 성분 간 결과가 발행되지 않게 검토해 주세요."
- "메모리 설계 검토에서는 **전체 확률 행렬 생성 비용**을 학습 비용과 분리하고, 요청된 쌍만 계산하는 경로를 기본으로 두겠습니다."
- "모형 승인 보고서는 **수치적 수렴**, **사전이 부여한 식별성**, **관측 조건별 적합성**을 별도 항목으로 판정해야 합니다."

## 선행·대안·확장 개념
- (선행) **로지스틱 회귀** — 일반적인 로지스틱 모형에서 설계행을 두 대상의 단위벡터 차이로 제한하면 BT의 선형예측자가 되므로, 설계행렬의 영공간과 식별성 문제를 분석하는 기반이 된다.
- (선행) **최대우도추정** — 우도 최적화라는 일반 추정 원리를 알아야 위치 제약, 유한한 최적점의 존재, 사전을 추가한 MAP가 서로 다른 문제임을 구분할 수 있다.
- (대안) **Thurstone 모형** — 쌍대 비교에서 잠재 점수를 추정하는 별도의 확률 모형 계열로, BT의 로지스틱 비교 가정을 고정하지 않고 관측 모형을 선택할 때 검토하는 대안이다.
- (확장) **일반화 브래들리–테리 모형** — 이진 관측을 넘어 이산·연속 비교값을 다루는 모형군으로 확장하며, 가우스 사전하의 강볼록성과 비교 변화에 대한 MAP의 성질을 분석할 수 있게 한다.
- (확장) **플래킷–루스 모형** — 순위 전체에 대한 곱우도를 구성하는 확장이므로, 하나의 순위 기록을 독립적인 쌍으로 분해하는 설계와 관측 단위 및 우도가 어떻게 달라지는지 검토할 때 중요하다.

## references_en

- {"title": "Modelling Pairwise Comparisons using the Bradley-Terry-Luce (BTL) Model", "authors": "Alvin Vista, Ray Adams, and Dan Cloney", "year": 2020, "type": "docs", "url": "https://www.acer.org/files/Tutorial-13--Pairwise-comparisons.pdf", "tier": "secondary", "annotation": "Work through 16 teams and 2,123 games, including strength estimates, uncertainty, and prediction errors."}
- {"title": "Generalized Bradley-Terry Models for Score Estimation from Paired Comparisons", "authors": "Julien Fageot, Sadegh Farhadkhani, Lê-Nguyên Hoang, and Oscar Villemaud", "type": "paper", "url": "https://arxiv.org/html/2308.08644", "tier": "primary", "annotation": "Explore extensions beyond binary outcomes and the assumptions behind their mathematical guarantees."}
- {"title": "Bradley-Terry Pairwise Ranking Calculator", "type": "docs", "url": "https://metricgate.com/docs/bradley-terry-pairwise-ranking", "tier": "secondary", "annotation": "See why opponent strength and disconnected comparison groups matter when interpreting rankings."}
- {"title": "Bradley–Terry model", "type": "wiki", "url": "https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model", "tier": "secondary", "annotation": "Compare positive-strength and logistic formulations, plus connections to Elo and Plackett–Luce."}
