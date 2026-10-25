# Bradley–Terry Model — claude-sonnet-5-5

- advanced 62 / basic 63 / gate review_required / penalty 0 / $1.8757 / 812s

## definition_en

The Bradley–Terry model is a probability model in which the outcome of a pairwise comparison (a win or a preference) is determined by the relative ratio of positive scores attached to the two items, so that scores can be inferred in reverse from observed comparisons to produce a full ranking. It is foundational to training reward models in reinforcement learning from human feedback (RLHF).

## definition_ko

브래들리–테리 모델은 두 대상을 짝지어 비교한 결과(승패·선호)가 각 대상에 붙은 양의 실수 점수의 상대적 비율로 결정된다고 보는 확률 모델로, 관측된 비교 결과로부터 점수를 역으로 추정해 전체 순위를 도출하는 데 쓰이며 RLHF의 보상 모델 학습의 기반이기도 하다.

## summary_en

The Bradley–Terry model gives every item a positive strength score and says the chance that one item beats another is its share of their combined strength. Think of a tug-of-war: a side pulling 3 against a side pulling 1 wins about 75% of the time. In practice you work backward from observed wins and preferences to find the scores that make those results most likely. That turns many small head-to-head judgments into one ranking, and the same idea underlies reward-model training in RLHF (learning from human feedback).

## summary_ko

브래들리–테리 모델은 '둘씩 붙여서 누가 이겼나'라는 단순한 결과만으로 모두의 실력 점수를 거꾸로 알아내는 방법이다. 와인 수십 종에 순위를 매기기는 어렵지만 두 잔 중 더 나은 쪽을 고르기는 쉬운 것과 같은 상황에서 쓴다. 각 대상에게 보이지 않는 점수가 있다고 보고, 내 점수가 두 점수의 합에서 차지하는 비율만큼 이길 확률이 있다고 계산한다. 이렇게 얻은 점수로 전체 순위를 만들 수 있어서 스포츠 랭킹은 물론, AI가 사람의 선호를 배우는 보상 모델 학습에도 쓰인다.

## body_basic_en

## Plain Explanation
Suppose you want to rank twenty wines, but nobody can sensibly sort the whole list at once. People find it much easier to compare two things and say which is better. The hard part is turning a messy heap of two-way verdicts into one ranking. Counting raw wins is unfair, because beating a weak opponent looks identical to beating a strong one. Results are also noisy: a better team sometimes loses.

The Bradley–Terry model's fix is to give each item a positive "strength" score and say that the chance A beats B is A's strength divided by the two strengths added together. Picture a tug-of-war where each side's pull is its score. With pulls of 3 and 1, A owns 3 of the 4 units of pull and wins about 75% of the time. Only the ratio of the two scores matters, so doubling A's strength changes the odds exactly as much as halving B's.

In practice you rarely know the scores; you have results. The standard method is maximum likelihood estimation, which means choosing the scores that would make the wins and losses you actually observed as probable as possible. The fit balances all games together, and the mathematician Zermelo showed the likelihood has a single best answer, which is found by repeating an update rule because there is no closed-form formula. Because only ratios matter, multiplying every score by 10 leaves every prediction unchanged (30 vs 10 is still 75%), so scores are fixed only up to a common scale. Software pins the scale down by normalizing, for example by dividing by the geometric mean (a multiplicative kind of average). And because the probability always stays strictly between 0% and 100%, an upset is read as an unlikely-but-possible event rather than an error. In the 3-vs-1 example, the underdog still wins 25% of the time.

## Examples & Analogies
- **Wine preference survey**: Respondents are asked only "which of these two do you prefer?" instead of ranking dozens of wines. From enough pairs, the model produces a full ranking, and it can estimate the chance that someone prefers wine X over wine Y even if nobody compared that exact pair. That prediction is only trustworthy if the comparisons link all the wines into one connected network and the model's assumptions hold.
- **A 16-team sports tournament**: A published tutorial for the ACER ConQuest software treats each of 2,123 games among 16 teams as a win/lose comparison. The fit converged in 4 iterations and flagged Geelong as the strongest team and Richmond as the weakest. The scores come out in logits (a log-odds scale) with the average fixed at zero, which is one way to pin down the arbitrary scale.
- **Tournesol video recommendations**: Contributors on this collaborative platform judge which of two videos should be recommended more often. The platform reportedly uses a generalized Bradley–Terry model (a relative that can also handle finer-grained comparisons than win/lose), among other tools, to turn those judgments into video scores. This shows the idea working on opinions rather than on game results.

## At a Glance
| | Bradley–Terry | Elo | Plackett–Luce |
|---|---|---|---|
| Data it consumes | Win/loss or preference outcomes for pairs | Game results between pairs | Orderings of several items |
| Partial rankings | Pairs only | Pairs, one game at a time | Yes: a ranking over any subset reduces to a smaller Plackett–Luce model with the same scores |
| Opponent adjustment | Win probability depends on both scores, so beating a strong item counts for more than beating a weak one | Win probability depends on the rating gap, with the same form as BT at base 10 and scale 400 | Each "who comes next" step compares an item's score with the total of those remaining |
| Fitting procedure | All comparisons fitted together by maximum likelihood, using iterative updates (e.g., Zermelo's iteration, the MM algorithm) | Ratings updated sequentially as results arrive | Scores shared with BT; for two items it reduces exactly to BT |

Bradley–Terry fits all comparisons jointly, Elo-style ratings track results as they arrive, and Plackett–Luce extends the same scores from pairs to whole or partial rankings.

## Where and Why It Matters
- **Reward models in RLHF**: Human preference pairs ("answer A is better than answer B") are turned into scores using the Bradley–Terry model, which is described as foundational to training reward models in reinforcement learning from human feedback. This is how a pile of two-way human judgments becomes a signal a model can be tuned against.
- **Ranking AI models**: Ranking AI models is one of the listed applications of the model. Because Elo's win-probability formula has the same shape as BT (base 10, scale 400), Elo-style point gaps can be read as win probabilities when a leaderboard is built this way.
- **Search relevance**: The model also plays a role in estimating how relevant documents are in machine-learned search engines, where preferences between pairs of results feed a score for each document.
- **Fairer than raw win percentage**: Fitted scores account for strength of schedule, so a win over a strong opponent is not treated the same as a win over a weak one, unlike a naive win-percentage ranking.
- **Dependable fitting on sparse data**: The MM algorithm (Hunter, 2004) converges from any positive starting point, even for sparse and unbalanced tournaments. This made routine checks standard practice, such as verifying that the comparison network is connected before trusting a ranking.

## Common Misconceptions
- ❌ Myth: Any pile of comparisons gives one trustworthy global ranking. → ✅ Reality: If two groups never face each other (directly or through a chain of comparisons), scores are only comparable within each group. An item that wins every one of its comparisons can also have no finite maximum-likelihood score, because its likelihood keeps improving as its score grows. Check connectivity and consider adding a prior; the generalized-BT paper uses a Gaussian prior so the estimate exists and is unique.
- ❌ Myth: A Bradley–Terry score of 3 is an absolute rating, like exam points. → ✅ Reality: Scores are identified only up to a common multiplier. Scores of 3 vs 1 and 30 vs 10 give identical predictions, so only ratios (or gaps on the log scale) carry meaning, and software fixes the scale by normalizing.
- ❌ Myth: Draws and "can't decide" answers are handled automatically. → ✅ Reality: The basic model only knows win or lose. Ties need an extension such as the Rao–Kupper or Davidson models rather than guessing which side "won".

## How It Sounds in Conversation
- "I fit a **Bradley–Terry model** on the 1,200 preference pairs from last week's annotation batch; the scores are in the sheet."
- "Before we trust that ranking, did anyone check the **comparison graph** is **connected**? Prompts B and F never got compared against anything in the other cluster."
- "Model C has a **score** of 3 and model D has 1, so C should win roughly 75% of head-to-heads, if the model's assumptions hold."
- "Don't read the raw **scores** as absolute numbers. We **normalized** them, so only the ratios between models mean anything."
- "Annotators flagged a lot of **ties**, and the basic **BT** model can't take those, so can we try a ties extension before the Friday review?"

## Related Reading
- (before) **Maximum Likelihood Estimation** — The fitting principle behind BT: choose the scores that make the observed outcomes most probable. Read this first if "fit the scores" feels vague.
- (before) **Logistic Regression** — Shares BT's logit-of-a-score-difference form; the difference is that BT's unknowns are one score per item rather than weights on features.
- (similar) **Elo Rating System** — Its win-probability formula has the same shape as BT (base 10, scale 400), but ratings are updated game by game instead of fitted jointly.
- (similar) **Thurstone Model** — An independent 1927 psychophysics approach to the same comparisons-to-scores problem. Read it to see an alternative formulation to BT.
- (next) **Plackett–Luce Model** — Extends BT from pairs to full or partial rankings, and reduces to BT when only two items are ranked.
- (next) **Reward Model** — (RLHF) — The setting where BT is applied to human preference pairs. Read it to see the model used for AI training rather than sports ranking.

## body_basic_ko

## 쉽게 이해하기
여러 후보 중 누가 더 나은지 알고 싶은데, 전체를 한 번에 줄 세우기는 어렵고 '둘 중 하나 고르기'는 쉬운 경우가 많다. 문제는 이 일대일 기록으로 순위를 매길 때 생긴다. 승률만 보면 약한 상대만 만나 5전 5승 한 팀과, 강한 상대만 만나 4승 1패 한 팀 중 누가 더 강한지 알 수 없다. 게다가 강한 쪽도 가끔 지기 때문에, 승패 하나하나를 그대로 믿으면 순위가 들쭉날쭉해진다.

브래들리–테리 모델은 대상마다 '힘'에 해당하는 양수 점수 하나를 붙이고, 두 대상이 만나면 점수의 비율대로 승리 확률이 나뉜다고 가정한다. 줄다리기에서 힘이 3인 팀과 1인 팀이 붙으면 3÷(3+1)=75%로 앞 팀이 이긴다고 보는 식이다. 이긴다고 확정하는 것이 아니라 확률만 주기 때문에 가끔 나오는 이변도 모델 안에서 설명된다. 격차는 점수의 비율로 정해지므로 점수가 6과 2여도 똑같이 75%이고, 점수에 로그를 취하면 이 격차는 '로그 점수의 차이'(ln3≈1.1)로 바뀌어 로지스틱 회귀(예/아니오 확률을 구하는 기본 통계 모델)와 같은 모양이 된다.

점수를 모르는 상태에서는 거꾸로 푼다. 먼저 어떤 점수 조합을 가정하고, 그 점수에서 지금까지 관측된 모든 승패 기록이 나올 확률을 계산한 뒤, 그 확률이 가장 커지는 점수를 찾는다(최대우도추정). 이때 어떤 팀이 이긴 상대의 점수도 함께 추정되므로, '누구를 이겼는가'가 자동으로 반영되고 그래서 단순 승률과 순위가 달라질 수 있다. 점수 전체에 같은 수를 곱해도 확률은 변하지 않으므로, 결과를 읽을 때는 절대 크기가 아니라 상대 비율로 보고 기준을 정해 정규화한다.

## 비유와 예시
- **사내 탁구 리그 순위** (가상 사례): 모든 직원이 서로 붙지는 못해서 일부는 약한 상대 위주로, 일부는 강한 상대 위주로 경기를 했다고 하자. 이 경우 승률 대신 점수를 추정하면, 강한 상대를 상대로 얻은 승리가 더 높은 점수로 이어져 승률 순위와 다른 결과가 나올 수 있다.
- **동물 집단의 서열 분석**: 연구자는 개체 둘이 맞붙었을 때 누가 물러났는지를 기록해 집단 내 지배 서열을 연구한다. 한 마리씩 서열을 직접 재기 어렵지만, 일대일 승패를 모으면 개체별 점수를 추정해 서열을 만들 수 있다.
- **영상 추천 품질 평가** (가상 사례): 영상 수백 개를 한꺼번에 줄 세우기 어려우니, 평가자에게 영상 두 개를 보여 주고 '어느 쪽을 더 추천할까'만 묻는다고 하자. 비교 기록이 서로 끊어지지 않게 이어져 있고 영상마다 점수 하나로 설명된다는 모델 가정이 맞다면, 직접 비교되지 않은 영상 쌍의 선호 확률도 점수로 예측할 수 있다.

## 한눈에 비교
| | Bradley–Terry | Elo 레이팅 | Plackett–Luce |
|---|---|---|---|
| 성격 | 쌍 비교 확률 모형 | 같은 로지스틱 기대승률을 쓸 수 있는 온라인 갱신 방식 | 전체·부분 순위 확률 모형 |
| 입력 데이터 | 이겼다/졌다(또는 선호) 쌍 기록 | 경기 결과가 나오는 순서대로 | 전체 순위 또는 일부 순위 |
| 확률의 모양 | 점수 비율 p_i/(p_i+p_j) | 400 스케일, 밑 10으로 쓰면 같은 형태 | 1등부터 차례로 남은 후보 중 뽑힐 확률의 곱 |
| 점수 구하는 법 | 쌓인 기록 전체에 맞춰 추정(주로 최대우도) | 경기마다 점수를 조금씩 갱신 | 순위 데이터에 맞춰 추정 |

BT는 두 대상의 승리 확률을 정의하는 모형이고 Elo는 같은 형태의 기대승률을 쓰면서 결과가 나올 때마다 점수를 고치는 방식이라, 식이 대응해도 실제 추정·갱신 결과가 반드시 같지는 않으며 Plackett–Luce는 이 구조를 전체·부분 순위 데이터로 넓힌 모델이다.

## 어디서 왜 중요한가
- **보상 모델 학습** (사람 피드백 기반 강화학습, RLHF): 같은 질문에 대한 '선택된 응답'과 '거절된 응답' 쌍마다 두 점수의 차이를 선택 확률로 바꾸는 BT 식을 쓰고, 관측된 선택이 가장 그럴듯해지도록(음의 로그우도를 최소화하도록) 보상 모델의 점수를 학습한다. 덕분에 응답마다 절대 점수 라벨을 달지 않고 '어느 쪽이 낫다'는 상대 선호만으로 학습할 수 있다.
- **쌍 비교 기록으로 순위 만들기** (스포츠, 설문, AI 모델 비교 등): 'i가 j를 이긴 횟수'를 모아 모든 쌍의 BT 확률로 로그우도를 만들고 이를 최대화하는 점수를 반복 계산으로 찾는다. 상대의 강도가 점수에 함께 반영되므로 비교 대상이 서로 다른 빈도로 붙은 기록에서도 같은 척도의 점수를 얻을 수 있다.
- **검색 문서 관련도 추정**: 머신러닝 기반 검색에서 문서 쌍 중 어느 쪽이 더 관련 있는지에 대한 비교 판단으로 문서별 관련도 점수를 추정하는 데 쓰일 수 있다. 이때도 핵심은 점수 차이를 선택 확률로 바꾸는 같은 BT 확률식이다.

## 자주 하는 오해
- ❌ 오해: 브래들리–테리 모델은 비기거나 무승부인 경기도 그대로 다룬다 → ✅ 실제: 기본형은 이김/짐 두 결과만 가정하므로 동점은 직접 처리하지 못하고, 동점을 넣으려면 Davidson, Rao–Kupper 같은 확장 모델을 써야 한다.
- ❌ 오해: 각 대상의 힘이 점수 하나로 요약되니 어떤 대결 구조든 설명할 수 있다 → ✅ 실제: 기본형은 대상마다 점수 하나만 두는 가정이라 '가위바위보'처럼 A가 B를, B가 C를, C가 A를 이기는 상성 구조는 표현하지 못한다.
- ❌ 오해: 비교 기록이 서로 이어져 있기만 하면 항상 유한한 점수가 나온다 → ✅ 실제: 비교망 연결성은 서로 다른 그룹의 점수를 같은 척도에 놓기 위한 조건이고, 유한한 최대우도해가 존재하는지는 별개의 문제다. 전승 또는 전패한 대상이 있으면 점수가 무한대로 치우쳐 유한 추정치가 없을 수 있고, 점수는 전체 배율까지만 정해지므로 정규화 기준이나 가우시안 사전분포 같은 장치가 필요하다.

## 대화에서는 이렇게
- "이번 **보상 모델**은 chosen/rejected 쌍으로 **BT 형태의 선호 손실**을 계산해요. 응답마다 절대 점수 라벨은 안 쓰고 쌍 비교만 써요."
- "Elo랑 비교하자면 **기대승률 식**은 대응되는데, 실제로는 **BT는 전체 기록에 맞춰 한 번에 추정**하고 Elo는 경기마다 갱신해서 최종 점수는 다를 수 있어요."
- "이 평가 데이터는 팀 A와 B 그룹이 한 번도 안 붙었어요. **비교망이 끊겨서** 그룹 간 점수는 같은 척도로 못 비교해요."
- "무승부가 전체 경기의 20%쯤 있어서 **기본 BT로는 동점 처리가 안 되니까** Davidson 같은 확장 모델을 검토해 봐야겠어요."
- "어떤 후보는 전승이라 **점수가 무한대로 발산**해요. **사전분포를 걸어서 정규화**하든지 점수 기준을 하나 고정하든지 해야 합니다."

## 함께 읽으면 좋은 용어
- (기초) **로지스틱 회귀** — BT 확률식에서 로그 점수 차이를 확률로 바꾸는 부분이 같은 구조라서, 이 부분을 이해하면 BT 식이 왜 그런 모양인지 바로 보인다.
- (기초) **최대우도추정** — 승패 기록으로 점수를 역추정하는 원리가 바로 이것이라, BT의 추정 단계를 이해하려면 먼저 알아 둘 개념이다.
- (유사) **Elo 레이팅** — 같은 로지스틱 기대승률을 쓰지만 경기마다 점수를 갱신하는 방식이라, 'BT는 기록 전체를 한 번에 설명'과 대비해 읽기 좋다.
- (심화) **Plackett–Luce 모델** — 후보가 많아도 관측이 쌍 비교라면 BT로 충분하고, 전체·부분 순위 자체를 데이터로 직접 모델링할 때 이쪽이 적합하다.
- (심화) **보상 모델** — (Reward Model) — BT 확률식이 선택/거절 쌍 선호 손실로 실제 쓰이는 대표적 학습 지점이다.
- (심화) **TrueSkill** — Elo를 개선한 평점 시스템으로, 점수의 불확실성까지 다루는 쪽으로 넘어갈 때 읽기 좋다.

## body_advanced_en

## Technical Definition & How It Works
The **Bradley–Terry (BT) model** is a parametric model for binary pairwise outcomes. Each item i carries a latent positive score p_i, and the outcome of a comparison is a Bernoulli variable with Pr(i>j) = p_i/(p_i+p_j). The components are (a) the score vector p, (b) a link that turns a score ratio into a probability, and (c) count data w_ij, the number of times i beat j. Under the exponential parametrization p_i = e^{β_i} the link is the logistic sigmoid of a score difference, so logit Pr(i>j) = β_i − β_j. This is the same functional form as logistic regression on a ±1 comparison design matrix. The two differ in what is known. Logistic regression fixes the design and learns a coefficient vector in a feature space. BT treats the item identities as the design and learns one scalar per item. With base 10 and scale 400 the same formula is the Elo rating curve. Zermelo studied the model in the 1920s, and Bradley and Terry presented it in 1952.

**Data and control flow in a production fit:**
- Aggregate raw judgments into counts w_ij (ordered pairs). Define n_ij = w_ij + w_ji and the win total W_i = Σ_j w_ij.
- Build two graphs from the same counts: an undirected comparison graph (edge if n_ij > 0) and a directed win graph (edge i→j if w_ij > 0).
- Run the identifiability and existence gates. The comparison graph must be connected, otherwise the scale between components is unconstrained. The win graph must be strongly connected for the unpenalized MLE to be finite.
- Fit the scores, either by the Zermelo/MM fixed-point iteration for the MLE or by a penalized (MAP) objective.
- Normalize to remove the scale freedom, then use the scores in the forward direction to predict outcomes for pairs that were never compared.

**Key algorithm steps (MLE):**
1. The log-likelihood is ℓ(p) = Σ_ij [w_ij ln p_i − w_ij ln(p_i + p_j)]. Zermelo showed it has a single maximum.
2. Setting the derivative to zero gives the stationarity condition p_i = W_i / Σ_j n_ij/(p_i + p_j). It has no known closed form, so Zermelo proposed iterating it.
3. Update p_i' = W_i / Σ_j n_ij/(p_i + p_j) for every i, from any positive start. This is the MM algorithm of Hunter (2004), which converges from any positive starting point.
4. Because only ratios matter, renormalize after each sweep. The geometric-mean form is p_i ← p_i'/(Π_k p_k')^{1/n}, equivalently subtracting the mean of ln p_i'.
5. Each sweep improves the log-likelihood, and the iteration reaches the unique maximum when one exists.

**Complexity:** with m distinct compared pairs, one sweep costs O(m). The BFS-based graph checks cost O(n + m).

**Estimation framing:** the MLE exists and is unique up to scale only under a connectivity condition on the win graph (see the formulas and code sections). The Generalized Bradley–Terry (GBT) paper adds a Bayesian view. With a Gaussian prior on scores, the negative log-posterior of every GBT model is strongly convex, so the MAP exists, is unique and is cheap to compute. The paper further proves that the MAP is monotone in the comparisons (the more A beats B, the better A's score) and that a single new comparison has only a bounded effect on all scores (Lipschitz resilience).

The supplied references report no benchmark numbers for the classical model. The ACER ConQuest tutorial's 16-team, 2,123-game league fit is the only quantitative example, and it converged in 4 iterations.

## Formulas, Architecture, and Diagrams
**1. Model and link.** With p_i = e^{β_i} (the Bradley–Terry parametrization), where β_i is the log-strength of item i and σ is the logistic sigmoid:

$$\Pr(i>j)=\frac{p_i}{p_i+p_j}=\frac{1}{1+e^{\beta_j-\beta_i}}=\sigma(\beta_i-\beta_j)$$

It follows that Pr(i>j) + Pr(j>i) = 1, and the model is invariant to a common shift β_i → β_i + c, which is the same as p → c·p. The scale ambiguity is therefore a one-dimensional shift in β.

**2. Log-likelihood.** With w_ij the count of i beating j, n_ij = w_ij + w_ji and W_i = Σ_j w_ij:

$$\ell(\beta)=\sum_{i,j} w_{ij}\,\ln\sigma(\beta_i-\beta_j)=\sum_{i,j} w_{ij}\Big[\beta_i-\ln\big(e^{\beta_i}+e^{\beta_j}\big)\Big]$$

**3. Gradient (moment matching).** Differentiating gives

$$\frac{\partial \ell}{\partial \beta_i}=W_i-\sum_{j} n_{ij}\,\sigma(\beta_i-\beta_j)$$

At the MLE every item's observed win count equals its model-expected win count. This is the stationarity condition that Zermelo's fixed-point iteration solves.

**4. MAP objective (explicit prior).** Place an independent zero-mean Gaussian prior on the log-strengths, β_i ~ N(0, τ²), and minimize the negative log-posterior (up to a constant):

$$J(\beta)=-\ell(\beta)+\frac{1}{2\tau^{2}}\sum_{i=1}^{n}\beta_i^{2}$$

The prior term is strongly convex with modulus 1/τ². This matches the Gaussian-prior setting in which the GBT paper proves existence, uniqueness, monotonicity and Lipschitz resilience of the MAP. The gradient is ∂J/∂β_i = β_i/τ² − W_i + Σ_j n_ij σ(β_i − β_j). The sum of these gradients over i equals Σβ_i/τ², so starting at β = 0 the MAP has zero mean. The prior therefore also fixes the shift ambiguity, and the choice of τ is part of the estimator.

**5. Normalization for the MLE.** Dividing by the geometric mean is the same as subtracting the mean log-strength:

$$\beta_i \leftarrow \beta_i-\frac{1}{n}\sum_{k=1}^{n}\beta_k \quad\Longleftrightarrow\quad p_i \leftarrow \frac{p_i}{\big(\prod_k p_k\big)^{1/n}}$$

Implementations should compute the second form in log space. A direct product of n scores can overflow or underflow when n is large or the scores are spread out.

**6. Existence of the MLE (graph criterion).** Let D be the directed graph with an edge i→j whenever w_ij > 0. The condition used in Zermelo's analysis and in Hunter's (2004) MM convergence theory is that for every split of the items into two non-empty sets, some item in one set beats some item in the other. This is equivalent to D being **strongly connected**. When it holds, ℓ has a unique maximizer up to the shift. When it fails, some item (or group) is never beaten by the rest, and ℓ can be increased without bound by pushing that group's β upward, so no finite MLE exists. The supplied references state the unique-maximum guarantee but not this criterion verbatim, so treat the criterion as a literature result to verify against Hunter (2004) before relying on it in a design doc. Undirected connectivity of the comparison graph is only a necessary condition: if the comparison graph splits into components, scores are identified only within each component.

**7. Small numerical checks.**
- Scores 3 and 1: Pr = 3/(3+1) = 0.75. In log space β_i − β_j = ln 3 ≈ 1.0986 and σ(1.0986) = 0.75. On the Elo scale (base 10, scale 400) the same gap is 400·log10(3) ≈ 190.8 points.
- Boundary case, two items, item 0 beats item 1 in all 3 games. ℓ(d) = 3 ln σ(d) with d = β_0 − β_1 is strictly increasing, so the MLE does not exist. With the prior at τ = 1 and the zero-mean constraint β_0 = d/2, β_1 = −d/2, the stationarity condition is d = 6σ(−d), which gives d ≈ 1.29 and Pr(0>1) ≈ 0.78 rather than 1. This finite value comes from the prior, not from the data alone.

## Code or Pseudocode
```python
import math
from collections import deque

Wins = dict[tuple[int, int], int]  # (i, j) -> number of times i beat j

def build(n: int, wins: Wins):
    und = [set() for _ in range(n)]  # undirected edge if n_ij = w_ij + w_ji > 0
    fwd = [set() for _ in range(n)]  # directed edge i -> j if i beat j at least once
    rev = [set() for _ in range(n)]  # reversed win graph
    W = [0] * n                      # total wins per item
    for (i, j), c in wins.items():
        if c > 0:
            und[i].add(j); und[j].add(i); fwd[i].add(j); rev[j].add(i); W[i] += c
    return und, fwd, rev, W

def n_ij(wins: Wins, i: int, j: int) -> int:
    return wins.get((i, j), 0) + wins.get((j, i), 0)

def reach(adj: list[set[int]]) -> int:  # BFS from node 0, O(n + m)
    seen, q = {0}, deque([0])
    while q:
        for v in adj[q.popleft()]:
            if v not in seen:
                seen.add(v); q.append(v)
    return len(seen)

def classify(n: int, wins: Wins) -> str:
    und, fwd, rev, _ = build(n, wins)
    if reach(und) < n:
        return 'disconnected'  # components: no shared scale across groups
    if reach(fwd) < n or reach(rev) < n:
        return 'separated'     # win digraph not strongly connected: MLE diverges
    return 'mle_exists'        # strongly connected: unique MLE up to scale

def fit_mle_mm(n: int, wins: Wins, iters: int = 5000) -> list[float]:
    if classify(n, wins) != 'mle_exists':
        raise ValueError('MLE does not exist for this comparison graph; use fit_map')
    und, _, _, W = build(n, wins)
    p = [1.0] * n
    for _ in range(iters):  # Zermelo / MM update: p_i = W_i / sum_j n_ij / (p_i + p_j)
        new = [W[i] / sum(n_ij(wins, i, j) / (p[i] + p[j]) for j in und[i]) for i in range(n)]
        mean_log = sum(math.log(x) for x in new) / n  # normalize by mean log-strength
        p = [math.exp(math.log(x) - mean_log) for x in new]
    return p

def fit_map(n: int, wins: Wins, tau: float = 1.0, iters: int = 5000) -> list[float]:
    # minimize J(b) = -loglik(b) + ||b||^2 / (2 tau^2), prior b_i ~ N(0, tau^2)
    und, _, _, W = build(n, wins)
    deg = [sum(n_ij(wins, i, j) for j in und[i]) for i in range(n)]
    step = 1.0 / (0.5 * max(deg) + 1.0 / tau ** 2)  # 1 / (upper bound on Hessian eigenvalue)
    sig = lambda x: 1.0 / (1.0 + math.exp(-x))
    b = [0.0] * n
    for _ in range(iters):
        g = [b[i] / tau ** 2 - W[i] + sum(n_ij(wins, i, j) * sig(b[i] - b[j]) for j in und[i])
             for i in range(n)]
        b = [b[i] - step * g[i] for i in range(n)]
    return b

def run_tests() -> None:
    ok = {(0, 1): 2, (1, 0): 1, (1, 2): 2, (2, 1): 1, (0, 2): 1, (2, 0): 1}
    assert classify(3, ok) == 'mle_exists'
    p = fit_mle_mm(3, ok)
    assert abs(sum(math.log(x) for x in p)) < 1e-9  # mean log-strength is zero
    _, _, _, W = build(3, ok)
    for i in range(3):  # observed wins == expected wins at the MLE
        expected = sum(n_ij(ok, i, j) * p[i] / (p[i] + p[j]) for j in range(3) if j != i)
        assert abs(expected - W[i]) < 1e-5

    sep = {(0, 1): 3, (1, 2): 3, (0, 2): 2}  # connected, but item 0 is never beaten
    assert classify(3, sep) == 'separated'
    try:
        fit_mle_mm(3, sep)
        raise AssertionError('expected ValueError for separated data')
    except ValueError:
        pass
    b = fit_map(3, sep)  # finite and ordered, but shaped by the prior
    assert all(math.isfinite(x) for x in b) and b[0] > b[1] > b[2] and abs(sum(b)) < 1e-9

    disc = {(0, 1): 2, (1, 0): 1, (2, 3): 2, (3, 2): 1}  # two groups never compared
    assert classify(4, disc) == 'disconnected'

run_tests()
```

## Production Pitfalls
- ❌ Mistake: Fitting BT on a leaderboard where two groups of items never faced each other and then ranking all items on one list → ✅ Fix: Run a connectivity check on the comparison graph first (BFS over pairs with n_ij > 0) and refuse to rank across components, or collect bridging comparisons.
- ❌ Mistake: Checking only undirected connectivity and then running the Zermelo/MM iteration on data where one item has never lost, so the scores drift upward without converging → ✅ Fix: Also test strong connectivity of the win digraph (forward and reverse BFS), and switch to a Gaussian-prior MAP fit when it fails.
- ❌ Mistake: Normalizing scores by dividing by the direct product of p_k raised to 1/n, which overflows or underflows when n is large or scores span many orders of magnitude → ✅ Fix: Keep log-strengths and subtract the mean log-strength after each sweep, then exponentiate only when the probabilities are needed.
- ❌ Mistake: Reporting MAP scores from a sparse graph as if they were MLE estimates, so a prior choice of τ silently sets how far apart the items appear → ✅ Fix: Record the prior and τ with the model, state which gaps are data-identified versus prior-shrunk, and show the sensitivity of the ranking to τ.
- ❌ Mistake: Using binary BT on data that has many ties or a systematic ordering effect such as home advantage, which biases the score gaps → ✅ Fix: Move to a tie-aware or home-field extension, or to the GBT family when comparisons carry graded values.

## Tradeoffs — When to Use What
**Suitable:**
- Comparisons are cheap and noisy but absolute scores are not. Binary pairwise judgments from human raters or match results fit the model directly, and the fit costs O(m) per sweep with a single maximum when the MLE exists, so there is no local-minimum risk.
- You need scores or win probabilities for pairs that were never compared. The fitted scores support forward prediction, which a raw win tally cannot do.
- The comparison graph is dense or at least well connected. Scores then account for strength of schedule, and the Gaussian-prior MAP gives a strongly convex objective that any off-the-shelf optimizer solves.
- The downstream consumer is a reward model trained on preference pairs, where the logistic form of the BT loss is the standard formulation.

**Unsuitable:**
- Sparse comparison data where you need a trustworthy ranking. A connected graph makes scores identifiable, but identifiability is not reliability: items with few comparisons get wide uncertainty and their rank can flip with one more game. Report standard errors or a posterior, and consider adding comparisons rather than trusting point estimates.
- Data with undefeated or winless items, or non-strongly-connected win graphs. The unpenalized MLE diverges there. Use the Gaussian-prior MAP (the GBT setting) and say plainly that the resulting gaps are prior-induced, not data-identified.
- Ties or graded outcomes. Plain binary BT discards that information, so use tie-aware extensions (Davidson, Rao–Kupper) or the GBT family for discrete or continuous comparison values.
- Skill that drifts over time or where per-item uncertainty must be tracked online. A static fit averages over time, so use Elo refinements such as Glicko or TrueSkill.
- Preferences that are context-dependent or intransitive. A single scalar per item cannot represent cycles. The supplied references do not name a specific alternative, so treat this as a limitation that needs a model with pair- or context-specific terms.
- Full rankings or choice sets of three or more items per judgment. Collapsing them into pairs loses structure, so use Plackett–Luce, which reduces to BT when only two items are compared.

## Industry Communication
- "In the **BT scoring PR**, the guard only verified **undirected connectivity**; item 7 had **0 losses** across 14 comparisons, so the **Zermelo iteration never converged**. Please add a **strong-connectivity check** on the win digraph and fall back to the **MAP fit** when it fails."
- "The fixed-point update is **O(m) per sweep**, where m is the number of **distinct compared pairs**, so the cost scales with graph density rather than with the number of games."
- "During review of the **score normalization**, we switched from a **direct product** to **mean log-strength** subtraction after seeing **underflow** on the 5k-item fixture; the output is identical up to float error."
- "For the **reward-model dataset**, the **chosen/rejected** pairs give us the **logistic BT loss** directly, but the **comparison graph is sparse**, so we should report **per-item uncertainty** and not treat the rank order as settled."
- "The **τ = 1.0 Gaussian prior** is doing real work on the two **undefeated** items. Those gaps are **prior-induced**, not identified by the likelihood, and the design doc should say that explicitly."
- "Postmortem finding: two **evaluation rounds** never overlapped, and we published a **single merged ranking** anyway. The **comparison graph had two components**, so cross-group order was **unsupported**; the connectivity gate now blocks that release."
- "The **home-advantage** term is out of scope for v1, but the **residuals** show a systematic **first-listed bias**, so we will either randomize presentation order or move to an **extended BT model**."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Maximum Likelihood Estimation** — BT scores are fitted by maximizing the pairwise log-likelihood; understanding stationarity, existence and uniqueness of the maximizer is what makes the Zermelo/MM iteration and its failure cases legible.
- (prerequisite) **Logistic Regression** — BT is the same sigmoid-of-a-difference form applied to a comparison design matrix, so the gradient and convexity arguments carry over directly; the difference is that item identities, not features, are the covariates.
- (alternative) **Thurstone model** — An independently developed latent-score approach to paired comparisons from psychophysics; it solves the same score-from-comparisons problem with a different noise model, so it is the relevant contrast when the logistic link is questioned.
- (extension) **Plackett–Luce model** — Extends BT from pairs to full rankings via sequential choice among remaining items, and reduces to BT when only two items are compared.
- (extension) **Generalized Bradley–Terry (GBT) models** — Extends BT to discrete or continuous comparison values within an exponential-family construction; with a Gaussian prior the MAP is unique, monotone in comparisons and Lipschitz-resilient to single new comparisons.
- (extension) **RLHF reward modeling** — Builds on BT by fitting a learned scoring function to human preference pairs, replacing the free per-item score with a model's output; the sparse-graph and prior-versus-data caveats still apply to the preference dataset.

## body_advanced_ko

## 기술적 정의와 동작 원리
브래들리–테리(BT) 모델은 n개 대상에 양의 점수 $$p_i$$를 붙이고, 각 쌍 비교를 서로 독립인 베르누이 시행으로 보아 $$\Pr(i>j)=p_i/(p_i+p_j)$$로 두는 쌍 비교 확률 모델이다. $$p_i=e^{\beta_i}$$로 재매개화하면 $$\operatorname{logit}\Pr(i>j)=\beta_i-\beta_j$$가 되어 비교 하나가 점수 차이에 대한 로지스틱 회귀 관측이 된다. 모든 $$p_i$$에 같은 양수를 곱해도 확률이 변하지 않으므로 점수는 곱셈 상수(로그 좌표에서는 평행이동)까지만 식별되고, 추정 뒤에는 반드시 기준점을 정해야 한다.

※ 아래에서 '참고자료로 검증되지 않음'은 거짓이라는 뜻이 아니라, 제공된 자료 범위에서 확인하지 못했다는 뜻이다.

**데이터/제어 흐름**
- 입력은 $$w_{ij}$$(i가 j를 이긴 횟수)이다. 충분통계량은 대상별 승수 $$W_i=\sum_j w_{ij}$$와 쌍별 총 비교 수 $$N_{ij}=w_{ij}+w_{ji}$$ 두 가지다.
- 추정 전에 '유한한 MLE가 존재하는가'를 먼저 판정한다. 존재하면 고정점 반복으로 점수를 구하고, 기하평균 1(로그 평균 0)로 기준점을 정렬한 뒤 미관측 쌍의 승리 확률을 예측한다.
- 사전분포가 있는 MAP 추정이면 존재·유일성 판정이 달라진다. 원문 논문은 알려진 가우시안 사전분포 아래 GBT 계열(BT 포함) 전체에서 MAP의 존재·유일성, 비교 결과에 대한 단조성, 새 비교 하나에 대한 Lipschitz 안정성을 증명했다고 보고한다. 이 보장은 사전분포가 들어간 경우의 결과다. 사전분포 없는 비정규화 좌표 전체에 그대로 옮길 수 없다(아래 3번 참조).

**알고리즘 단계** (Zermelo 반복)
1. 입력 검증: 대상 목록의 중복, 미등록 대상, 자기 비교, 음수·비유한 승수를 거부한다.
2. 비교 그래프 점검: 총 비교 수가 양인 쌍으로 이루어진 비방향 그래프와, $$w_{ij}>0$$인 승리 방향 그래프를 만든다.
3. 존재 조건 점검(아래 '존재 조건' 참조): 승리 그래프가 강연결이 아니면 유한 MLE가 없으므로 반복하지 않고 실패로 반환한다.
4. 각 $i$에 대해 $$p_i \leftarrow W_i / \sum_{j:N_{ij}>0} N_{ij}/(p_i+p_j)$$를 차례로 갱신한다. 이 절차는 매 반복 로그우도를 개선하고 유일한 최대값에 도달한다고 보고된다.
5. sweep마다 기하평균으로 나눠 기준점을 정렬하고, 목적함수 변화량과 파라미터 변화량이 둘 다 임계값 아래일 때만 수렴으로 판정한다. 최대 반복 횟수 도달은 성공이 아니다.

**볼록성과 식별성의 구분** (유도)
- 로그 좌표에서 음의 로그우도는 $$\sum w_{ij}\,\mathrm{softplus}(\beta_j-\beta_i)$$이므로 볼록하다. 그러나 $$\beta\to\beta+c\mathbf 1$$ 방향으로는 값이 변하지 않아 비정규화 좌표 전체에서는 엄밀 볼록이 아니다. 그 헤시안은 가중 그래프 라플라시안이며, 영공간이 $$\mathrm{span}(\mathbf 1)$$로 한정되는 것은 비교 그래프가 연결일 때뿐이다.
- 따라서 엄밀 볼록성은 '$$\sum\beta_i=0$$ 같은 기준점 제약 + 비교 그래프 연결' 또는 '가우시안 사전분포'가 있어야 성립한다. 사전분포 $$\mathcal N(0,\sigma^2)$$는 헤시안에 $$I/\sigma^2$$를 더해 강볼록성을 준다.
- 볼록성(최적점의 유일성)과 유한한 최대점의 존재는 다른 문제다. 존재 여부는 아래 조건이 결정한다.

**존재 조건**
- 필요조건(유도 가능): 대상 집합 S와 그 여집합 사이에 비교가 있고 항상 S쪽이 이겼다면, S의 모든 $$\beta$$에 $$+c$$를 더할 때 교차 비교 항의 확률이 단조 증가한다. 나머지 항은 변하지 않으므로 로그우도의 상한에 도달하지 못한다(유한 MLE 없음). 대상별로 승패가 모두 있어도 집단 간 교차 결과가 한 방향이면 이 경우에 해당한다.
- 충분조건: 승리 방향 그래프가 강연결이면 유한한 유일 MLE가 존재한다는 것이 BT 문헌의 표준 결과로 알려져 있다. 다만 이 정리의 명시적 진술은 제공된 참고자료에서 확인되지 않아 '참고자료로 검증되지 않음'으로 둔다. 구현은 이 조건을 점검 항목으로 사용한다.
- 연결 진단이 필수라는 점은 참고자료와도 일치한다. 서로 한 번도 맞붙지 않은 두 군집이 있으면 강도는 군집 안에서만 식별된다.

**복잡도**
- sweep당 비용은 밀집 구현에서 $$O(n^2)$$, 비교된 쌍 수를 $|E|$라 하면 희소 구현에서 $$O(|E|)$$이다.
- 필요한 반복 횟수의 일반 상한은 참고자료로 검증되지 않는다. ACER ConQuest 튜토리얼은 16개 팀·2,123경기 예제가 4회 반복에 수렴했다고 보고하지만, 이는 해당 소프트웨어·설정의 단일 사례다.

## 핵심 수식·아키텍처·도표
**1. 모델과 로그 좌표**

$$\Pr(i>j)=\frac{p_i}{p_i+p_j}=\frac{1}{1+e^{\beta_j-\beta_i}},\qquad p_i=e^{\beta_i}$$

- $$p_i$$는 양의 점수, $$\beta_i=\ln p_i$$는 로그 점수다. 이 식은 점수 차이를 시그모이드에 넣은 로지스틱 모델과 같은 형태다. Elo 스케일(밑 10, 400)은 같은 식을 $10^{R/400}$ 형태로 쓴 것이다.

**2. 로그우도와 점수 방정식**

$$\ell(\mathbf p)=\sum_{i,j} w_{ij}\left[\ln p_i-\ln(p_i+p_j)\right]$$

$$\frac{\partial \ell}{\partial p_i}=\frac{W_i}{p_i}-\sum_j\frac{N_{ij}}{p_i+p_j}=0\;\Rightarrow\; p_i=\frac{W_i}{\sum_j N_{ij}/(p_i+p_j)}$$

- $$w_{ij}$$는 i가 j를 이긴 횟수, $$W_i=\sum_j w_{ij}$$는 i의 총 승수, $$N_{ij}=w_{ij}+w_{ji}$$는 쌍별 총 비교 수다. 미분에서 $$p_i$$는 첫 번째 인덱스로 나올 때 $$w_{ij}\ln p_i$$ 항에, 두 로그항 $$\ln(p_i+p_j)$$에서는 $$w_{ij}$$와 $$w_{ji}$$ 양쪽에 등장하므로 분모 계수가 $$N_{ij}$$가 된다.
- 이 방정식의 닫힌 해는 알려져 있지 않으며, 고정점 반복(Zermelo)으로 푼다.
- 기준점 정렬: $$p_i\leftarrow p_i/(\prod_j p_j)^{1/n}$$. 로그 좌표에서는 $$\beta_i\leftarrow\beta_i-\bar\beta$$(평균 빼기)와 같다.

**3. 헤시안과 기준점·사전분포**

$$\nabla^2(-\ell)(\boldsymbol\beta)=\sum_{i<j}N_{ij}\,\pi_{ij}(1-\pi_{ij})\,(e_i-e_j)(e_i-e_j)^\top,\quad \pi_{ij}=\frac{1}{1+e^{\beta_j-\beta_i}}$$

- $$e_i$$는 i번째 단위벡터다. 이 행렬은 양의 가중 그래프 라플라시안이다. 모든 쌍에서 $$\pi_{ij}(1-\pi_{ij})>0$$이므로 PSD이고, 영공간은 비교 그래프가 연결일 때 $$\mathrm{span}(\mathbf 1)$$뿐이다.
- 그래서 비정규화 목적함수는 $$\mathbf 1$$ 방향으로 평평하다. 엄밀 볼록성은 기준점 제약이나 사전분포가 있어야 성립한다.
- 가우시안 사전분포 $$\mathcal N(0,\sigma^2)$$를 쓰면 음의 로그사후는 $$-\ell(\boldsymbol\beta)+\|\boldsymbol\beta\|^2/(2\sigma^2)$$이고, 헤시안에 $$I/\sigma^2$$가 더해진다. 원문이 보고한 MAP의 존재·유일성은 이런 가우시안 사전분포 가정 아래의 결과다. $$\sigma$$는 외부에서 정하는 하이퍼파라미터이며, 값에 따라 추정치가 0쪽으로 수축한다.

**4. 완결된 수치 예제** (미관측 쌍 예측까지)

- 예제 A (2개 대상): A가 B를 3번, B가 A를 1번 이겼다. 이때 $$\hat p_A/(\hat p_A+\hat p_B)=3/4$$이므로 $$\hat p_A=3\hat p_B$$이다. 기하평균 1로 정렬하면 $$\sqrt{\hat p_A\hat p_B}=1$$에서 $$\hat p_A=\sqrt3\approx1.732$$, $$\hat p_B=1/\sqrt3\approx0.577$$, $$\beta_A=+0.549$$, $$\beta_B=-0.549$$이다. 예측 확률은 $1.732/(1.732+0.577)=0.75$로 관측 승률과 일치한다.
- 예제 B (3개 대상 사슬): A–B 비교에서 승패가 3:1, B–C 비교에서 3:1이고 A–C는 직접 비교가 없다. 가정상 각 쌍의 가능도가 하나의 차이 $$\beta_A-\beta_B$$, $$\beta_B-\beta_C$$에만 의존하므로 MLE는 $$p_A:p_B:p_C=9:3:1$$이다. 기하평균은 $27^{1/3}=3$이므로 정렬 후 $$p=(3,\,1,\,1/3)$$, $$\beta=(+1.099,\,0,\,-1.099)$$이다(평균 0). 미관측 쌍 예측은 $$\Pr(A>C)=3/(3+1/3)=0.9$$이고, 로그 오즈는 $$\beta_A-\beta_C=\ln 9\approx2.197$$이다.
- Elo 스케일로 환산하면 점수비 3은 $400\log_{10}3\approx191$점 차이다. 스케일만 바뀔 뿐 확률은 같다.
- 존재하지 않는 예제 C: A가 B를 4:0으로 이긴다. $$\Pr(A>B)^4\to1$$은 $$p_A/p_B\to\infty$$에서만 도달하므로 상한은 1이지만 도달하지 않는다. 비정규화 MLE는 유한하지 않다.

**점수가 0으로 접근할 때의 정책**
- $$p_i\to0$$은 $$\beta_i\to-\infty$$를 뜻한다. 승리 그래프가 강연결이면 이론상 일어나지 않으므로, 구현은 $$p_i$$를 하한 $$\epsilon$$(예: $10^{-12}$)으로 자르고 수렴 후 $$\min p\le10\epsilon$$이면 성공이 아니라 '경계 접근' 상태로 반환한다.
- 이 상태에서 나온 극단적 순위 격차는 데이터가 아니라 $$\epsilon$$ 선택의 산물이다. 사전분포(MAP)로 격차를 유한하게 유지하거나 해당 대상에 비교를 추가해야 한다.

**5. 보상 모델 손실과의 대응**

$$\mathcal L(\theta)=-\mathbb E_{(x,y_w,y_l)}\left[\ln\sigma\big(r_\theta(x,y_w)-r_\theta(x,y_l)\big)\right]$$

- 선호 확률을 BT로 두고 $$\beta$$를 파라미터화된 보상 $$r_\theta$$로 치환하면, 이 손실은 BT의 음의 로그우도(chosen=승자, rejected=패자)와 같다. 대상별 자유 파라미터가 아니라 모델 출력이 점수 역할을 하며, 프롬프트 $x$$ 안에서 보상의 상수 이동이 불변이라는 기준점 문제는 그대로 남는다.

## 코드 또는 의사코드
```python
# 의사코드(실행 가능한 Python 형태): 승수 w[(i, j)]로 BT 점수를 추정한다.
# 정책: 빈 입력 -> 'empty', 단일 대상 -> 'trivial'(beta=0), 승리 그래프가 강연결이 아니면 'no_finite_mle'.
import math
from collections import deque
from dataclasses import dataclass
import numpy as np

@dataclass
class BTResult:
    status: str                   # converged | max_iter_reached | near_boundary | no_finite_mle | invalid_input | empty | trivial
    beta: dict                    # 평균 0으로 정렬한 log 점수 (기준점 정렬 후)
    iterations: int
    loglik: float | None
    last_dloglik: float | None    # 마지막 sweep의 목적함수 변화량

def loglik(p: np.ndarray, w: np.ndarray) -> float:
    lp = np.log(p)
    lse = np.log(p[:, None] + p[None, :])
    return float(np.sum(np.where(w > 0, w * (lp[:, None] - lse), 0.0)))

def strongly_connected(adj: np.ndarray) -> bool:
    def reach_all(a: np.ndarray) -> bool:
        seen, q = {0}, deque([0])
        while q:
            u = q.popleft()
            for v in map(int, np.flatnonzero(a[u])):
                if v not in seen:
                    seen.add(v); q.append(v)
        return len(seen) == a.shape[0]
    return reach_all(adj) and reach_all(adj.T)

def fit_bt(items: list[str], wins: dict[tuple[str, str], float],
           tol: float = 1e-10, max_iter: int = 10_000, eps: float = 1e-12) -> BTResult:
    if not items:
        return BTResult('empty', {}, 0, None, None)
    if len(set(items)) != len(items):
        return BTResult('invalid_input', {}, 0, None, None)
    idx = {x: k for k, x in enumerate(items)}
    n = len(items)
    w = np.zeros((n, n))
    for (a, b), c in wins.items():          # 대상·승수 유효성 검사
        if a not in idx or b not in idx or a == b or not math.isfinite(c) or c < 0:
            return BTResult('invalid_input', {}, 0, None, None)
        w[idx[a], idx[b]] += c
    if n == 1:
        return BTResult('trivial', {items[0]: 0.0}, 0, 0.0, 0.0)
    N = w + w.T                              # 쌍별 총 비교 수
    if not strongly_connected(w > 0):        # 유한 MLE 존재 조건 점검
        return BTResult('no_finite_mle', {}, 0, None, None)
    W = w.sum(axis=1)
    p = np.ones(n)
    ll_prev = loglik(p, w)
    status, d_ll, it = 'max_iter_reached', math.nan, 0
    for it in range(1, max_iter + 1):
        old = np.log(p)
        for i in range(n):
            nbr = np.flatnonzero(N[i] > 0)   # 총 비교 수가 양인 쌍만 사용
            p[i] = max(W[i] / np.sum(N[i, nbr] / (p[i] + p[nbr])), eps)
        p /= math.exp(np.log(p).mean())      # 기하평균 1로 기준점 정렬
        ll = loglik(p, w)
        d_ll, ll_prev = ll - ll_prev, ll
        step = float(np.max(np.abs(np.log(p) - old)))
        if abs(d_ll) < tol and step < 1e-6:  # 목적함수와 파라미터가 모두 안정될 때만 수렴
            status = 'near_boundary' if p.min() <= 10 * eps else 'converged'
            break
    beta = dict(zip(items, map(float, np.log(p))))
    return BTResult(status, beta, it, ll_prev, d_ll)  # max_iter_reached는 성공이 아니다

# 테스트
r = fit_bt(['A', 'B'], {('A', 'B'): 3, ('B', 'A'): 1})
assert r.status == 'converged' and abs(r.beta['A'] - 0.5 * math.log(3)) < 1e-6
assert fit_bt(['A', 'B'], {('A', 'B'): 4}).status == 'no_finite_mle'     # 4:0 한 방향
g = {('a1', 'a2'): 1, ('a2', 'a1'): 1, ('b1', 'b2'): 1, ('b2', 'b1'): 1,
     ('a1', 'b1'): 2, ('a2', 'b2'): 2}                                     # 대상마다 승패는 있으나 집단 간은 한 방향
assert fit_bt(['a1', 'a2', 'b1', 'b2'], g).status == 'no_finite_mle'
assert fit_bt([], {}).status == 'empty' and fit_bt(['A'], {}).status == 'trivial'
assert fit_bt(['A', 'B'], {('A', 'A'): 1}).status == 'invalid_input'
```

## 프로덕션 함정
- ❌ 실수: '대상마다 승패가 모두 있으니 점수가 정해진다'고 보고 개별 승패 유무만 점검한다. 한 집단이 다른 집단에 항상 이기는 구조가 가려져 한 집단의 점수가 한없이 올라간다 → ✅ 해결: 승리 방향 그래프의 강연결성을 검사해 실패 상태로 반환하고, 해당 쌍의 비교를 추가 수집하거나 사전분포를 둔 MAP으로 바꾼다.
- ❌ 실수: 반복이 최대 횟수에 도달했는데 값이 나왔다는 이유로 성공으로 처리한다. 고정점 반복은 선형 속도로 수렴해 희소 그래프에서 아직 수렴 전일 수 있고, 로그우도 변화량만 보면 완만한 구간에서 일찍 멈춘다 → ✅ 해결: 상태를 converged와 max_iter_reached로 분리해 반환하고, 목적함수 변화량과 파라미터 변화량을 함께 기준으로 쓴다.
- ❌ 실수: 서로 다른 학습·평가 라운드의 β 절댓값을 직접 비교한다. 평균을 0으로 맞추는 기준점 정렬은 대상 구성이 바뀌면 모든 점수를 같은 양만큼 평행이동시킨다 → ✅ 해결: 점수 차이 $$\beta_i-\beta_j$$나 승리 확률만 비교하고, 라운드 간 연속성이 필요하면 고정 기준 대상을 두고 그 점수를 0으로 정렬한다.
- ❌ 실수: 같은 평가자의 반복·중복 비교를 독립 시행으로 모두 센다. 우도가 비교별 확률의 곱이라 독립을 가정하는데, 한 평가자의 편향이 수백 건에 들어가면 점수가 한쪽으로 쏠리고 불확실성이 과소평가된다 → ✅ 해결: 평가자·세션 단위로 비교를 중복 제거하거나 가중치를 낮추고, 평가자별 효과를 확인한 뒤 모델 확장 여부를 정한다.
- ❌ 실수: 승리가 없는 대상의 극단적 점수를 eps 하한으로 눌러 두고 순위표에 그대로 싣는다. 하한 값은 데이터가 아니라 설정에서 나온 것이어서 순위 격차가 임의적이다 → ✅ 해결: near_boundary 상태를 별도로 표시하고 가우시안 사전분포의 MAP으로 격차를 유한하게 만들되, 사전분포 σ를 실험 설정에 명시한다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**
- 절대 점수는 얻기 어렵고 1:1 선택만 안정적으로 수집되는 경우: 레이블이 이분(승/패)이라 평가자별 척도 보정이 필요 없고, 모델 파라미터가 대상당 1개라 희소한 비교에서도 추정이 가능하다.
- 직접 비교하지 않은 쌍의 확률도 필요한 경우: 점수 차이를 시그모이드에 넣으면 추이적 비교로 예측할 수 있다(예제 B의 $$\Pr(A>C)=0.9$처럼). 모든 쌍을 비교할 필요가 없어 비용이 $$O(n^2)$$ 대신 연결된 부분 그래프 수준으로 줄어든다.
- 보상 모델이나 선호 학습처럼 선택된 응답과 거절된 응답 쌍이 이미 있는 경우: 손실이 $$-\ln\sigma(r_w-r_l)$$ 한 줄이라 구현 복잡도가 낮고 로지스틱 회귀 도구를 그대로 쓸 수 있다.
- 볼록 목적함수의 재현성이 중요한 경우: 기준점 제약이나 사전분포 아래에서 유일해가 보장되고 초기값 의존성이 없어, 모델 간 비교나 재학습 감사에 유리하다.

**이럴 때 부적합**
- 후보가 3개 이상이고 전체 순서나 상위 k개 순위가 관측되는 경우: 순위를 쌍으로 쪼개면 비교들이 독립이 아니게 되는데 BT는 독립을 가정한다. 순서 전체를 확률로 다루는 **Plackett–Luce**가 정보 손실이 적다.
- 무승부가 흔한 경우: 이분 결과만 다루므로 무승부를 임의로 버리거나 반반으로 나누게 되어 점수 차가 왜곡된다. 무승부 항을 명시한 **Davidson / Rao–Kupper** 계열이 맞다.
- 비교 결과에 점수 차(마진)나 연속값이 있는 경우: 이분화하면 정보를 버린다. 연속·이산 결과를 다루는 **Gaussian-GBT, Poisson-GBT** 등 GBT 계열이 비교 크기를 반영한다.
- 대국 직후 온라인으로 점수를 갱신하고 불확실성도 함께 추적해야 하는 경우: 배치 MLE를 매번 다시 풀면 비용이 크다. 증분 갱신인 **Elo**나 불확실성을 같이 갱신하는 **TrueSkill**이 낫다.
- 비교가 집단 사이에서 한 방향으로만 일어난 경우: 유한 MLE가 존재하지 않아 집단 간 순위에 근거가 없다. 비교 데이터를 추가 수집하거나 사전분포를 둔 MAP으로 전환해야 한다. 이는 모델 선택 문제가 아니라 데이터 설계 문제다.
- 취향이 사람·맥락마다 갈려 선호 순환이 구조적으로 나타나는 경우: 단일 스칼라 점수로는 순환을 표현할 수 없다. 참고자료에 구체적 대안 모델이 없어 이 부분은 일반적 설계 논리로만 남기며, 점수를 사용자·맥락별로 분리하는 방향이 필요하다.

## 업계 대화 맥락
- "(가상 PR 리뷰 예시) **fit_bt**가 **max_iter_reached**일 때도 점수 테이블을 그대로 내보내고 있습니다. **converged**와 상태를 분리해서 반환하고, 후자는 대시보드에 올리지 않도록 막아 주세요."
- "(가상 인시던트 포스트모템 예시) 신규 평가 그룹을 붙인 라운드에서 두 집단의 교차 비교가 **한 방향**뿐이었는데, 대상별 승패 유무만 점검해서 **유한 MLE가 없는 상태**를 놓쳤습니다. **승리 그래프 강연결성** 검사를 파이프라인 앞단에 넣었습니다."
- "(가상 디자인 문서 예시) 점수는 곱셈 상수까지만 식별되므로 **기하평균 1 정렬**(로그 평균 0)을 쓰고, 대시보드에는 **β 절댓값** 대신 **쌍별 승리 확률**을 보여 주는 안을 제안합니다."
- "(가상 회귀 분석 예시) 대상 3개를 추가한 뒤 기존 대상의 β 평균이 -0.4 이동했는데, 이는 **기준점 정렬 효과**일 수 있습니다. 먼저 기존 쌍의 **β 차이**가 유지되는지 확인하고, 차이가 변했다면 **대상 구성·비교 데이터 변화**로 따로 원인을 분리합니다."
- "(가상 리뷰 예시) 보상 모델 손실이 **−ln σ** (r_w − r_l) 형태라 **BT 가정**을 그대로 따릅니다. 따라서 chosen/rejected가 무승부에 가까운 쌍은 **라벨 노이즈**로 처리하고, 마진이 있다면 **GBT 계열**로 확장할지 검토하겠습니다."
- "(가상 실험 보고 예시) 승리가 한 번도 없는 대상은 **MLE가 발산**해서 **eps 하한** 때문에 순위가 극단적으로 벌어졌습니다. **가우시안 사전분포**(σ를 실험 설정에 명시)로 MAP을 쓰면 순위가 유한하게 유지되지만 **수축 편향**이라는 trade-off가 있습니다."
- "(가상 문서 리뷰 예시) 레이팅 표시 스케일을 **Elo** (400/ln10 ≈ 173.7)로 바꿔도 확률은 같습니다. 단위 변환 때문에 점수 차이가 달라 보이는 것은 모델 변화가 아니라 **스케일 변환**이므로 변경 이력에 분리해서 적어 주세요."

## 선행·대안·확장 개념
- (선행) **로지스틱 회귀** — BT는 점수 차이 $$\beta_i-\beta_j$$를 시그모이드에 넣는 모델이라 형태가 같지만, BT는 함수형을 알고 점수를 추정한다는 점이 다르다. 비교-차이 설계 행렬 위의 로지스틱 회귀로 구현할 수 있어 기존 최적화 도구를 재사용할 수 있다.
- (선행) **최대 사후 확률(MAP) 추정** — 비정규화 MLE는 승리 그래프가 강연결이 아니면 유한하지 않다. 가우시안 사전분포를 둔 MAP은 존재·유일성과 비교 하나에 대한 안정성을 주므로, 사전분포의 역할을 이해하는 선행 개념이다.
- (대안) **Thurstone 모델** — 같은 문제(쌍 비교에서 잠재 점수 추정)를 BT와 독립적으로 푼 심리물리학 계열 접근이다. 선택 확률의 링크 함수가 달라 두 모델을 비교하면 BT의 로지스틱 링크 가정을 점검할 수 있다.
- (대안) **TrueSkill** — Elo의 정교화 중 하나로, 점수와 함께 불확실성을 온라인으로 갱신한다. 대국이 계속 들어오는 환경에서는 배치 BT보다 갱신 비용이 낮은 대안이다.
- (확장) **Plackett–Luce 모델** — BT를 3개 이상 대상의 전체 순서로 확장한 모델이다. 두 대상만 보면 BT로 환원되므로, 순위형 선호 데이터를 쌍으로 쪼개 생기는 독립성 위반을 줄인다.
- (확장) **Generalized Bradley–Terry(GBT) 모델** — 이분 비교를 지수족 기반으로 일반화해 이산·연속 비교를 모두 다루고, 가우시안 사전분포 아래 MAP의 존재·유일성과 안정성을 증명한 계열이다. 마진이 있는 비교 데이터에서 BT가 버리던 정보를 쓴다.

## references_en

- {"title": "Modelling Pairwise Comparisons using the Bradley-Terry-Luce (BTL) Model", "authors": "Vista, Adams, Cloney", "year": 2020, "type": "docs", "url": "https://www.acer.org/files/Tutorial-13--Pairwise-comparisons.pdf", "tier": "primary", "annotation": "Worked example fitting BT to 2,123 games among 16 teams, with logit scores and residuals."}
- {"title": "Asymptotic theory of sparse Bradley-Terry model", "authors": "Han et al.", "year": 2020, "venue": "Annals of Applied Probability", "type": "paper", "url": "https://projecteuclid.org/journals/annals-of-applied-probability/volume-30/issue-5/Asymptotic-theory-of-sparse-BradleyTerry-model/10.1214/20-AAP1564.pdf", "tier": "primary", "annotation": "Rigorous statistical theory for BT when each item is compared with only a few others."}
- {"title": "Diagnostic Framework for the Bradley–Terry Model", "authors": "Wu et al.", "year": 2022, "venue": "Journal of the Royal Statistical Society: Series A", "type": "paper", "url": "https://academic.oup.com/jrsssa/article/185/Supplement_2/S461/7069516", "tier": "primary", "annotation": "Shows how to check whether a fitted BT model actually suits the data."}
- {"title": "Generalized Bradley-Terry Models for Score Estimation from Paired Comparisons", "authors": "Fageot, Farhadkhani, Hoang, Villemaud", "year": 2023, "type": "paper", "url": "https://arxiv.org/html/2308.08644", "tier": "primary", "annotation": "Shows convexity, MAP existence and uniqueness for BT-style models, and reviews BT's history from Zermelo to Elo and Thurstone."}
- {"title": "Bradley-Terry Pairwise Ranking Calculator", "type": "docs", "url": "https://metricgate.com/docs/bradley-terry-pairwise-ranking", "tier": "secondary", "annotation": "Practical notes on strength of schedule, the MM algorithm, and why disconnected comparison clusters break the ranking."}
- {"title": "Bradley–Terry model", "type": "wiki", "url": "https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model", "tier": "secondary", "annotation": "Clear overview of the formula, logit and Elo forms, Plackett–Luce, and Zermelo's iterative maximum-likelihood fit."}
