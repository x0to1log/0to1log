# Bradley–Terry Model — claude-opus-5-5

- advanced 68 / basic 69 / gate review_required / penalty 0 / $4.3022 / 1263s

## definition_en

The Bradley–Terry model is a probability model for pairwise comparisons that assigns each item a positive latent strength and sets the probability that one item beats another to its share of the pair's combined strength — equivalently, a logistic function of the difference in log-strengths — so that strengths can be inferred by maximum likelihood from observed win/loss outcomes and then used to rank items or predict matchups that were never observed.

## definition_ko

브래들리-테리 모델은 각 항목에 양수의 잠재 강도를 부여하고, 두 항목이 맞붙을 때 한쪽이 이길 확률을 두 강도의 합에서 그 항목이 차지하는 비율로 정의하는 쌍대 비교 확률 모델로, 관찰된 승패 데이터로부터 최대우도 방식으로 강도를 추정해 전체 순위를 매기거나 아직 비교되지 않은 조합의 결과를 예측하는 데 쓰인다.

## summary_en

The Bradley–Terry model turns a pile of 'A beat B' results into a score for every item. Picture a taste test where people only ever judge two samples at a time, and you still want a full ranking at the end. The model gives each item a hidden strength and says the chance of winning a matchup depends on how big your strength is compared with your opponent's. It then works backward from the observed wins and losses to find the strengths that best explain them. That is why it shows up in sports ratings, survey analysis, and the ranking of AI answers by human preference.

## summary_ko

브래들리-테리 모델은 '둘 중 누가 더 나은가'라는 1:1 비교 결과를 모아서 전체 순위를 매기는 통계 모델이다. 동네 탁구 리그에서 모두가 서로 다 붙어보지 않았어도, 누가 누구를 이겼는지만 알면 실력 순위를 짐작할 수 있는 것과 비슷하다. 모델은 각 대상에게 눈에 보이지 않는 '힘 점수'가 있다고 보고, 두 대상이 붙으면 힘이 센 쪽이 그만큼 더 자주 이긴다고 가정한다. 그리고 실제 승패 기록을 가장 잘 설명하는 점수를 거꾸로 찾아낸다. 스포츠 레이팅부터 사람이 고른 답변으로 AI를 가르치는 일까지, 직접 점수를 매기기 어려운 곳에서 널리 쓰인다.

## body_basic_en

## Plain Explanation
Suppose you ask reviewers to score 30 chatbot answers on a 1–10 scale. Scores drift quickly: one reviewer's 7 is another reviewer's 5, and the same person often gets stricter after an hour of work. Asking "which of these two is better?" is often easier for people, which is why surveys and evaluation teams frequently collect A-or-B judgments instead. Pairwise judgments are not automatically reliable, though — annotators still disagree and sometimes contradict themselves — and a stack of verdicts is not yet a ranking. Raw win counts also mislead, because some items happened to face much tougher opponents than others.

The **Bradley–Terry model** solves this by giving every item one hidden positive number, its **strength**. Think of a raffle: each of the two contenders drops tickets into a hat equal to its strength, and one ticket is drawn to decide the winner. With strengths 3 and 1, the stronger item holds 3 of the 4 tickets, so it wins 75% of the time: $$P(i \text{ beats } j) = \frac{s_i}{s_i + s_j}$$ Two items of equal strength win 50% each, and even a strong item sometimes loses — that built-in randomness is how the model absorbs noisy or inconsistent judgments.

In practice the model runs backward: you have the observed results and need the strengths. It searches for the strengths that make the observed wins and losses as probable as possible, a principle called **maximum likelihood**; a common recipe raises an item's strength when it wins more than its current strength predicts, lowers it otherwise, and repeats until the numbers settle. Only ratios between strengths matter, so multiplying every strength by 10 changes no prediction, and software therefore pins the scale — for example by dividing by the geometric mean or centering the log-strengths at zero. The data also has to cooperate: every item must be linked to the others through a chain of comparisons, and an item that wins every single comparison has no finite best estimate, because raising its strength always improves the fit.

## Examples & Analogies
- **Choosing between two help-center answers**: A support team writes several draft answers to "How do I reset two-factor login?" and shows reviewers two drafts at a time, asking which one a confused customer would understand faster. A draft that beats an already-strong draft gains more strength than one that only beats a weak draft, because the model expected the first win to be harder. After fitting, the team publishes the top draft and can estimate how often it would beat a draft it was never directly paired with — but only if both drafts are connected through shared opponents, and only as well as the model's assumptions hold.
- **A hypothetical amateur league with an uneven schedule**: Imagine Team A goes 5–0 but only played the three weakest clubs, while Team B goes 3–2 against the top of the table. A win-percentage table puts A far ahead, yet Bradley–Terry discounts A's wins against weak opponents and credits B's wins against strong ones, so the two can end up close or even reversed. The league can also produce a win probability for an A-vs-B match that has not been scheduled yet, which is only meaningful because both teams share opponents.
- **Ranking short videos by viewer preference**: A curation project shows volunteers pairs of short explainer videos and asks which one deserves to be recommended more often. Nobody watches all 200 videos, but each video appears in enough pairs that the comparisons form one connected web. Fitting strengths turns thousands of small A-or-B choices into a single ordered list, while videos that appeared in only one or two comparisons get much less certain scores.

## At a Glance
| | Win percentage | Bradley–Terry (batch fit) | Elo (sequential updates) |
|---|---|---|---|
| Input | Each item's total wins and games | The full set of pairwise outcomes at once | One game result at a time, as it happens |
| Opponent strength | Ignored: every win counts the same | Built in: beating a strong item counts more | Built in through the expected score before each game |
| How scores are computed | Simple division | All strengths fitted jointly by maximum likelihood, iterated until stable | Both ratings nudged after each game by how surprising the result was |
| Order of results | Does not matter | Does not matter: one fit over all data | Matters: the same results in a different order give different ratings |
| Output | A percentage from 0 to 100% | Relative strengths on an arbitrary scale, plus win probabilities for any connected pair | Ratings where a 400-point gap means 10-to-1 odds, drifting as new games arrive |

Elo uses the same win-probability curve as Bradley–Terry rescaled to base 10 and 400 points, but it updates ratings game by game instead of fitting all results jointly, so Bradley–Terry suits a fixed batch of comparisons while Elo suits results that stream in live.

## Where and Why It Matters
- **Reward models in reinforcement learning from human feedback** (RLHF): The Bradley–Terry model is foundational to training reward models, where human labelers pick the better of two AI responses and a scorer is trained so the preferred response gets the higher Bradley–Terry win probability. This made "which answer is better?" labels a standard data format for aligning language models.
- **Ranking AI models from head-to-head votes**: Ranking AI models is a listed application of the model, letting evaluators place many models on one scale even when not every pair of models was compared directly.
- **Strength-of-schedule became table stakes in ratings**: Because the model credits wins by opponent quality, ranking by raw win percentage is no longer accepted as a fair default in sports, chess, and similar competitions; the Elo rating system used in chess grew out of these ideas.
- **Connectivity checks before trusting a ranking**: When two groups of items never meet, strengths are only identified within each group, so checking that the comparison network is connected became a routine step before publishing a combined leaderboard.
- **Search relevance and consumer surveys**: The model plays a role in estimating document relevance in machine-learned search engines and in turning paired product-preference surveys into full rankings.

## Common Misconceptions
- ❌ Myth: A Bradley–Terry score is an absolute quality grade, so a strength of 2.0 means the same thing across studies. → ✅ Reality: Scores are relative and only defined up to a chosen scale; only differences (or ratios) within one fitted dataset are meaningful, and comparing numbers from two separate fits is invalid.
- ❌ Myth: Any pile of comparisons will produce a full, trustworthy ranking. → ✅ Reality: Items must be linked through a connected web of comparisons, and an item that wins (or loses) every comparison has no finite maximum-likelihood estimate; disconnected groups or undefeated items need more data, extra constraints, or a prior.
- ❌ Myth: The model handles draws and "about the same" answers out of the box. → ✅ Reality: The basic model only knows win or loss; ties require extended versions such as those of Davidson (1970) or Rao and Kupper (1967), or a modeling decision about how to record them.

## How It Sounds in Conversation
- "Before we publish the leaderboard, can someone run the **connectivity check**? I think the two new vendor models were only ever compared against each other."
- "Draft C is 9–0 in the help-center review, so the **Bradley–Terry fit** gives it an infinite strength — let's add a weak prior or get a few more comparisons."
- "Don't compare this sprint's **BT scores** with last quarter's; they're on different scales, so only the ranking and the win probabilities carry over."
- "About 12% of the annotation pairs were marked 'tie' — the plain **Bradley–Terry model** can't use those, so decide by Friday whether we drop them or switch to a tie-aware variant."
- "The live dashboard can stay on **Elo updates**, but the quarterly eval report should use a full **batch BT refit** so match order doesn't skew the numbers."

## Related Reading
- (before) **Logistic Regression** — Bradley–Terry is essentially logistic regression on the difference of two items' log-strengths; knowing the S-shaped curve first makes the win-probability formula feel familiar.
- (before) **Maximum Likelihood Estimation** — The fitting principle behind Bradley–Terry; understanding it explains why an undefeated item has no finite estimate.
- (similar) **Elo Rating System** — Uses the same win curve rescaled to base 10 and 400 points, but updates ratings after each game instead of fitting all results jointly; read it to choose between live and batch ratings.
- (similar) **Thurstone Model** — An independent approach from psychophysics (1927) that also turns paired judgments into scale values but assumes a different shape for the judgment noise.
- (next) **Plackett–Luce Model** — Extends Bradley–Terry from pairs to full rankings of many items and reduces to Bradley–Terry when only two items are ranked.
- (next) **Reward Model** — Where Bradley–Terry meets language models: preference pairs train a scorer used in RLHF, the most visible modern use of the pairwise likelihood.

## body_basic_ko

## 쉽게 이해하기
대상이 수십, 수백 개가 되면 사람이든 시스템이든 전체 순위를 한 번에 매기기가 매우 어렵습니다. 반면 '이 둘 중 어느 쪽이 나은가'는 훨씬 쉽게 답할 수 있죠. 문제는 이렇게 모은 비교 결과가 들쭉날쭉하다는 점입니다. 강팀도 가끔 약팀에게 지고, 단순 승률로 줄을 세우면 약한 상대만 만나 쌓은 승리와 강한 상대를 꺾은 승리가 똑같은 1승으로 취급됩니다.

브래들리-테리 모형은 이 문제를 '숨은 실력 점수'라는 개념으로 풉니다. 각 대상이 파이 한 조각씩을 들고 있다고 상상해 보세요. 두 대상이 맞붙으면 두 조각을 합친 파이에서 내 조각이 차지하는 비율만큼 내가 이길 확률이 됩니다. A의 조각 크기가 3, B가 1이라면 A가 이길 확률은 3을 4로 나눈 75%, 즉 3:1의 승산입니다.

실제로는 조각 크기(강도)를 모르고 승패 기록만 보이므로, 모형을 거꾸로 씁니다. 관측된 승패가 가장 그럴듯하게 나오는 강도 조합을 찾는 방법을 **최대우도 추정**이라고 부릅니다. 이때 모든 조각을 똑같이 두 배로 키워도 승률은 그대로라서, 점수의 기준을 먼저 고정해야 합니다. 점수의 기준을 고정하고 승패 연결 구조가 적절한 조건을 만족하면 최대우도로 상대 강도를 추정할 수 있습니다. 다만 한 번도 지지 않은 대상이 있으면 그 점수는 끝없이 커질수록 '더 그럴듯해' 보여 값이 정해지지 않으므로, 극단값에 벌점을 주는 **정규화** (regularization)나 미리 정한 점수 분포인 **사전분포**를 더해 안정시켜야 할 수 있습니다.

## 비유와 예시
- **와인 선호 조사**: 응답자에게 와인 수십 병을 전부 줄 세우게 하는 대신 두 병씩 맛보고 더 나은 쪽만 고르게 합니다. 이 쌍대 비교들을 모형에 넣으면 전체 순위가 나오고, 아무도 직접 비교하지 않은 두 와인의 선호 확률까지 계산할 수 있습니다.
- **동물 무리의 서열 분석**: 개체 간 다툼의 승패를 쌍대 비교로 보고 무리 안의 우열 서열을 강도 점수로 추정합니다. 다만 어떤 개체들이 서로 얼마나 연결되어 다퉜는지, 승패가 어느 방향으로 났는지에 따라 추정 가능성이 달라지며, 늘 이기기만 하는 개체가 있으면 정규화가 필요합니다.
- **호주 풋볼(AFL) 팀 강도 측정**: 16개 팀의 2,123경기 승패를 넣어 팀별 강도를 평균 0인 로짓 척도로 추정한 교육용 분석 사례가 있습니다. 이 분석에서는 Geelong이 가장 강한 팀으로 나왔고, 경기별로 '예측 승률과 실제 결과의 차이'까지 확인할 수 있습니다.

## 한눈에 비교
| | 브래들리-테리 | Elo 레이팅(표준 로지스틱) | Plackett–Luce | 단순 승률 |
|---|---|---|---|---|
| 입력 데이터 | 두 대상 간 승패·선호 | 경기 결과 1건씩 | 여러 대상의 전체 또는 부분 순위 | 승·패 횟수 |
| 확률 형태 | 강도 비율 = 로그 강도 차의 로지스틱 | BT와 같은 형태(밑 10, 척도 400) | 위 순위부터 차례로 강도 비율을 곱함 | 확률 모형 없음 |
| 추정·갱신 방식 | 모은 데이터 전체로 최대우도를 반복 계산 | 경기마다 점수를 조금씩 고치는 온라인 갱신 | 순위 데이터 전체의 가능도를 최대화 | 승수를 경기 수로 나눔 |
| 상대 강도 반영 | 반영 | 반영 | 반영 | 미반영(약팀 상대 1승도 같은 1승) |
| 대표 용도 | 선호 조사, 보상 모델 학습 | 체스 등 실시간 랭킹 | 여러 후보의 순위 목록 분석 | 간단한 성적표 |

Elo는 BT와 같은 승률 공식을 쓰지만 결과가 들어올 때마다 점수를 고치는 반면 BT는 쌓인 데이터를 한꺼번에 맞추고, Plackett–Luce는 비교 단위를 둘에서 여럿으로 넓힌 것이라 데이터가 어떤 모양으로 들어오는지가 선택 기준이 됩니다.

## 어디서 왜 중요한가
- **상대 강도를 반영한 평가**: 단순 승률은 약한 상대를 이긴 것과 강한 상대를 꺾은 것을 구분하지 못하지만, BT는 '누구를 상대로 이겼는가'까지 반영해 일정 난이도를 보정한 순위를 냅니다.
- **불완전한 비교에서의 추론**: 대상이 100개면 가능한 쌍은 4,950개지만, 모든 쌍을 비교하지 않아도 비교들이 서로 이어져 있으면 직접 붙지 않은 쌍의 승률까지 예측할 수 있어 평가 비용을 크게 줄입니다.
- **평가 설계의 중요성 부각**: 서로 한 번도 맞붙지 않은 두 집단이 있으면 강도는 각 집단 안에서만 정해지고 집단 간 비교는 불가능해, 어떤 쌍을 비교하게 할지 배정하는 설계 자체가 결과의 신뢰도를 좌우하게 됐습니다.
- **사람 선호 기반 AI 학습의 토대**: 사람이 두 답변 중 더 나은 쪽을 고른 데이터로 보상 모델을 학습하는 RLHF의 기초가 되며, AI 모델끼리의 대결 결과로 순위를 매기는 데에도 활용됩니다.
- **레이팅 시스템의 뿌리**: 체스의 Elo 레이팅은 BT와 같은 확률 형태를 공유하며, Glicko·TrueSkill은 Elo를 다듬어 실제로 쓰이는 별도의 레이팅 방식으로 BT 자체와는 구분해서 봐야 합니다.

## 자주 하는 오해
- ❌ 오해: BT 점수는 그 자체로 절대적인 실력 수치다 → ✅ 실제: 모든 강도를 같은 배수로 바꿔도 승률이 그대로라 비율(또는 차이)만 의미가 있습니다. 그래서 양수 강도는 기하평균을 1로, 로그 강도는 평균을 0으로 고정하는 식으로 기준을 정해야 하고, 기준이 다른 데이터셋의 점수를 그대로 비교하면 안 됩니다.
- ❌ 오해: 대상들이 비교로 서로 이어져 있기만 하면 항상 점수가 계산된다 → ✅ 실제: 승패 방향을 무시한 연결은 집단 간 비교를 위한 필요조건일 뿐입니다. 정규화 없는 최대우도 추정에는 더 강한 조건, 즉 대상들을 어떻게 두 무리로 나누든 각 무리가 상대 무리를 한 번 이상 이긴 기록이 있어야 하며, 그렇지 않으면 점수가 끝없이 커지거나 작아집니다.
- ❌ 오해: 점수가 높은 쪽은 항상 이긴다고 가정하는 모형이다 → ✅ 실제: 승부를 확률로 다루기 때문에 이변을 자연스럽게 흡수합니다. 예를 들어 Elo 척도로 400점 차이가 나도 약한 쪽의 승률은 약 9%로 남아 있습니다.

## 대화에서는 이렇게
- "이번 사내 모델 아레나 결과는 단순 승률 말고 **Bradley–Terry**로 다시 뽑아봐요. 약한 베이스라인만 많이 만난 모델이 지금 과대평가돼 있어요."
- "**로그 강도**에서 기준 모델을 0으로 두고, 평가 문항과 평가자 조건도 맞춘 뒤 비교하죠. 지난 분기 점수표랑 그냥 나란히 놓으면 안 돼요."
- "신규 모델 2개가 다른 모델이랑 한 번도 안 붙었어요. 이대로 **최대우도** 돌리면 점수가 안 정해지니까 금요일까지 교차 매칭부터 추가합시다."
- "한 번도 안 진 모델이 하나 있어서 점수가 발산하네요. **사전분포** 넣어서 MAP으로 다시 추정하고 신뢰구간도 같이 리포트할게요."
- "보상 모델은 A/B 선호 쌍을 **BT 손실**로 학습했는데, 검증셋 선호 일치율이 기대보다 낮아요. 라벨러 간 불일치부터 먼저 확인해볼까요?"

## 함께 읽으면 좋은 용어
- (기초) **로지스틱 회귀** — BT는 두 대상의 로그 강도 차이를 선형 예측값으로 쓰는 구조화된 로지스틱 모형이라, 로지스틱 회귀를 먼저 알면 BT의 승률 식이 바로 읽힙니다.
- (기초) **최대우도 추정** — 관측된 승패의 가능도를 최대화하는 원리와 해가 존재하는 조건을 이해하는 기초로, BT 점수가 왜 발산하거나 정해지지 않는지 설명해 줍니다.
- (유사) **Elo 레이팅** — BT와 같은 로지스틱 승률 형태를 쓰지만 경기마다 점수를 고치는 온라인 방식이라, 일괄 추정인 BT와 갱신 방식의 차이를 비교해 보기 좋습니다.
- (심화) **Plackett–Luce 모형** — 비교 단위를 '둘'에서 '여럿의 순위'로 넓힌 확장형으로, 전체 또는 부분 순위 데이터를 다뤄야 할 때 다음 단계로 읽기 좋습니다.
- (심화) **RLHF** — 사람의 A/B 선호로 보상 모델을 학습하는 과정의 기반이 BT라서, BT를 이해한 뒤 읽으면 보상 모델이 무엇을 배우는지 선명해집니다.
- (심화) **TrueSkill** — Elo를 다듬은 별도의 레이팅 방식으로, BT·Elo를 이해한 뒤 온라인·베이지안 추정이 레이팅에 어떻게 결합되는지 살펴볼 때 좋습니다.

## body_advanced_en

## Technical Definition & How It Works
The **Bradley–Terry (BT) model** is a parametric model for binary paired-comparison outcomes. Each item i ∈ {1,…,n} carries a log-strength βᵢ ∈ ℝ, equivalently a positive strength pᵢ = e^{βᵢ}. Each comparison between i and j is treated as an independent Bernoulli trial whose success probability is the logistic function of βᵢ − βⱼ. Estimation solves the inverse problem: recover β from observed outcomes. β is only identified up to an additive constant on each connected component of the comparison graph.

**Data and control flow**

- **Aggregation.** Raw events (i, j, winner) collapse into per-pair counts: wᵢⱼ (wins of i over j) and nᵢⱼ = wᵢⱼ + wⱼᵢ. Under the logistic parametrization, the log-likelihood depends on the data only through the item win totals Wᵢ = Σⱼ wᵢⱼ and the pair totals nᵢⱼ. These are the **sufficient statistics**, so storing anything beyond them adds no information for the classical model.
- **Comparison graph.** Items are nodes and observed pairs (nᵢⱼ > 0) are edges. Identifiability is a property of this graph, not of the sample size. If the graph has k connected components, the likelihood is invariant to k independent shifts, one per component. Scores from different components therefore share no common axis.
- **Existence of a finite MLE.** Connectivity guarantees uniqueness up to a shift, but not existence. Suppose a subset S of items never loses to its complement (an undefeated item is the simplest case). Then shifting all β in S upward strictly increases the likelihood, and the supremum is never attained. A finite maximizer requires the directed "beat" graph to be strongly connected. Practical fixes regularize the objective with **pseudo-counts** or a **Gaussian prior** (MAP).
- **Fitting.** The log-likelihood is concave in β. Zermelo showed it has a single maximum. The fixed-point iteration he proposed improves the likelihood at every step. In its simultaneous (MM) form it reaches the maximizer from any positive starting point.
- **Gauge fixing.** Because the likelihood is invariant to p → c·p, each iterate is divided by its geometric mean. This is equivalent to centering β to mean zero. Some tools report the same convention as "location parameters constrained to a mean of zero." The step changes no predicted probability and serves only identifiability and reporting.
- **Forward use.** σ(β̂ᵢ − β̂ⱼ) predicts any pair, including pairs never observed, provided both items sit in the same component.

**Algorithm steps** (sparse MM)

1. Validate inputs and drop zero-count edges.
2. Run a BFS connectivity check over the undirected comparison graph, at O(n + |E|) cost.
3. Either check strong connectivity of the directed win graph (for plain MLE), or add pseudo-counts to every observed edge.
4. Per sweep, compute rᵢⱼ = nᵢⱼ / (pᵢ + pⱼ) once per edge and scatter-add it to both endpoints. Then set pᵢ ← Wᵢ / Σⱼ rᵢⱼ. This costs **O(|E| + n) time** and needs **O(|E| + n) memory**. A dense n×n count matrix costs O(n²) memory and O(n²) per sweep even when most pairs are unobserved.
5. Renormalize by the geometric mean and stop when max |Δβ| < tol, or fail loudly after max_iter sweeps.
6. Optionally estimate uncertainty. Use the observed-information matrix, which is a weighted graph Laplacian, with a pseudo-inverse on the sum-zero subspace (O(n³) dense). Alternatively, resample at the correct unit and refit.

MM converges linearly, with a data-dependent number of sweeps. A Newton step on the same concave objective converges quadratically, but each step needs a linear solve against the n×n Laplacian.

**Relation to logistic regression.** BT is logistic regression without an intercept on the design row x = eᵢ − eⱼ. Logistic regression is usually framed as learning a function of known covariates; BT fixes that functional form and estimates one coefficient per item.

**Generalized Bradley–Terry (GBT).** The classical model is binary. The **GBT** family keeps the same scoring structure but allows discrete or continuous comparison values through a well-behaved subset of the exponential family. Its instances include **K-nary-GBT**, **Poisson-GBT**, **Gaussian-GBT**, and **Uniform-GBT**. All GBT models give a strictly convex negative log-likelihood. With a Gaussian prior on scores, the MAP exists, is unique, varies monotonically with the comparisons, and is Lipschitz-resilient: a single new comparison has only a bounded effect on all estimated scores.

## Formulas, Architecture, and Diagrams
**Model.** The latent strength is pᵢ = e^{βᵢ}, and σ is the logistic function:

$$P(i \succ j) = \frac{p_i}{p_i + p_j} = \sigma(\beta_i - \beta_j), \qquad \sigma(x) = \frac{1}{1 + e^{-x}}$$

The log-odds of i beating j equal βᵢ − βⱼ exactly. One unit of β is a factor of e in the odds.

**Log-likelihood in sufficient-statistic form.** Wᵢ is item i's total wins and nᵢⱼ the number of i–j comparisons:

$$\ell(\beta) = \sum_{i} W_i\, \beta_i \; - \sum_{i<j} n_{ij} \ln\!\left(e^{\beta_i} + e^{\beta_j}\right)$$

This follows from substituting the model into the sum of wᵢⱼ ln P(i ≻ j) and grouping the two directions of each pair.

**Score equation (MLE condition).**

$$\frac{\partial \ell}{\partial \beta_i} = W_i - \sum_{j} n_{ij}\, \sigma(\beta_i - \beta_j) = 0$$

At the optimum, every item's observed wins equal its model-expected wins against the opponents it actually faced. This is the mechanism by which strength of schedule enters the estimate.

**Curvature and identifiability.** Writing πᵢⱼ = σ(βᵢ − βⱼ) and letting eᵢ be the i-th unit vector:

$$-\nabla^2 \ell(\beta) = \sum_{i<j} n_{ij}\, \pi_{ij}(1 - \pi_{ij})\, (e_i - e_j)(e_i - e_j)^{\top}$$

This matrix is a weighted graph Laplacian, so it is positive semidefinite. Its null space is spanned by the indicator vectors of the connected components. Hence a connected graph leaves exactly one undetermined direction (a global shift), and a graph with k components leaves k. Each edge's weight nᵢⱼ πᵢⱼ(1 − πᵢⱼ) is largest when πᵢⱼ ≈ 0.5, so lopsided matchups carry little information about the gap.

**MM / Zermelo update and gauge.** Setting the score to zero in p-space and iterating gives the update. Normalizing by the geometric mean is identical to centering β to mean zero:

$$p_i^{(t+1)} = \frac{W_i}{\sum_{j} \dfrac{n_{ij}}{p_i^{(t)} + p_j^{(t)}}}, \qquad p_i \leftarrow \frac{p_i}{\left(\prod_{k} p_k\right)^{1/n}} \iff \beta_i \leftarrow \beta_i - \bar{\beta}$$

The update is scale-equivariant: multiplying every p by c multiplies the next iterate by c. Renormalizing each sweep therefore changes no predicted probability.

**Augmented (pseudo-count) objective.** Add a ≥ 0 virtual wins in each direction on every observed edge set E:

$$\ell_a(\beta) = \sum_{(i,j) \in E} \Big[ (w_{ij} + a) \ln \sigma(\beta_i - \beta_j) + (w_{ji} + a) \ln \sigma(\beta_j - \beta_i) \Big]$$

The MM update keeps the same form with Wᵢ replaced by Wᵢ + a·deg(i) and nᵢⱼ by nᵢⱼ + 2a. For a > 0, every observed edge carries wins in both directions. As a result, any connected graph yields a strongly connected win graph and a finite maximizer. The cost is shrinkage of every gap toward zero, with strength set by a.

**Gaussian-prior MAP (the GBT-style alternative regularizer).** With prior variance s²:

$$-\ln \text{posterior}(\beta) = -\ell(\beta) + \frac{1}{2 s^2} \sum_{i} \beta_i^2 + \text{const}$$

This objective is strongly convex, so the MAP is unique even on a disconnected graph. However, cross-component gaps are then set by the prior, not by data.

**Worked example.** Two items meet five times, and item 0 wins all five.

- With a = 0, the score equation requires 5 = 5·σ(Δ). This forces σ(Δ) = 1, so Δ = β₀ − β₁ → ∞ and no finite MLE exists.
- With a = 0.5, the augmented counts are 5.5 and 0.5. Then σ(Δ) = 5.5 / 6, giving Δ = ln 11 ≈ 2.398 and centered scores of about (+1.199, −1.199). The predicted P(0 ≻ 1) is about 0.917 rather than 1.0.
- On the Elo scale, the conversion factor is 400 / ln 10 ≈ 173.7 rating points per logit. The same gap is therefore about 417 Elo points.

**Assumption → failure → diagnostic matrix**

| Assumption | What breaks if violated | Diagnostic |
|---|---|---|
| Comparisons are conditionally independent | Standard errors too narrow; ranks look falsely separated | Cluster-level bootstrap vs. per-comparison bootstrap width |
| One scalar strength per item | Stable preference cycles cannot be represented; residuals concentrate on specific pairs | Per-pair residuals (observed minus predicted) |
| No presentation-order effect | Item shown first or "at home" gets inflated strength | Fit with and without an order term; compare held-out log loss |
| Stationary strengths | Old outcomes bias current scores | Fit on time windows; inspect drift of centered scores |
| Binary outcome, no ties | Ties silently dropped or miscoded as wins | Tie rate per pair; switch to a tie-aware or GBT variant |
| Connected comparison graph | Cross-group gaps unidentified | BFS component count before fitting |

## Code or Pseudocode
The capsule below is a runnable sparse MM fitter for classical binary BT with optional pseudo-count augmentation. It is written as Python with numpy, but treat it as a reference design rather than a library.

- **Storage:** one row per observed unordered pair, so memory is O(n + |E|).
- **Updates:** edge-based scatter-adds, so time is O(|E| + n) per sweep.
- **Centering:** a reporting/identifiability gauge only, since the likelihood is invariant to it.
- **Inline tests:** cover normalization, undefeated items, disconnected graphs, invalid inputs, and convergence failure.

```python
import numpy as np
from collections import deque
from numpy.typing import ArrayLike

def _reachable(n: int, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """BFS from item 0 over directed edges src->dst; O(n + |E|)."""
    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in zip(src.tolist(), dst.tolist()):
        adj[a].append(b)
    seen = np.zeros(n, dtype=bool)
    seen[0] = True
    queue = deque([0])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                queue.append(v)
    return seen

def fit_bt_mm(n_items: int, i: ArrayLike, j: ArrayLike, w_ij: ArrayLike, w_ji: ArrayLike,
              pseudo_count: float = 0.5, max_iter: int = 10_000, tol: float = 1e-10) -> np.ndarray:
    """Sparse MM fit of classical binary Bradley-Terry.

    Input: one row per observed unordered pair (i, j); w_ij = wins of i over j.
    Objective (a = pseudo_count, s = logistic):
        sum_e (w_ij + a) ln s(b_i - b_j) + (w_ji + a) ln s(b_j - b_i)
    a = 0 is plain MLE. Returns beta = ln p centered to mean 0; centering is a
    reporting gauge and changes no predicted probability.
    """
    if isinstance(n_items, bool) or not isinstance(n_items, int) or n_items < 2:
        raise ValueError("n_items must be an int >= 2")
    if not (np.isfinite(pseudo_count) and pseudo_count >= 0):
        raise ValueError("pseudo_count must be finite and >= 0")
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter must be an int >= 1")
    if not (np.isfinite(tol) and tol > 0):
        raise ValueError("tol must be finite and > 0")

    i, j = np.asarray(i, dtype=np.int64), np.asarray(j, dtype=np.int64)
    w_ij, w_ji = np.asarray(w_ij, dtype=float), np.asarray(w_ji, dtype=float)
    if i.ndim != 1 or i.size == 0 or not (i.shape == j.shape == w_ij.shape == w_ji.shape):
        raise ValueError("edge arrays must be 1-D, non-empty, and equal length")
    if np.any((i < 0) | (i >= n_items) | (j < 0) | (j >= n_items) | (i == j)):
        raise ValueError("item index out of range or self-comparison")
    if not (np.all(np.isfinite(w_ij)) and np.all(np.isfinite(w_ji))) or np.any(w_ij < 0) or np.any(w_ji < 0):
        raise ValueError("win counts must be finite and >= 0")

    keep = (w_ij + w_ji) > 0  # pseudo-counts go only on edges that were actually observed
    i, j = i[keep], j[keep]
    w_ij, w_ji = w_ij[keep] + pseudo_count, w_ji[keep] + pseudo_count

    if not _reachable(n_items, np.r_[i, j], np.r_[j, i]).all():
        raise ValueError("comparison graph is disconnected: strengths only identified within components")
    if pseudo_count == 0:  # finite MLE needs a strongly connected winner->loser graph
        src = np.r_[i[w_ij > 0], j[w_ji > 0]]
        dst = np.r_[j[w_ij > 0], i[w_ji > 0]]
        if not (_reachable(n_items, src, dst).all() and _reachable(n_items, dst, src).all()):
            raise ValueError("MLE does not exist (e.g. undefeated item); use pseudo_count > 0")

    wins = np.zeros(n_items)
    np.add.at(wins, i, w_ij)
    np.add.at(wins, j, w_ji)
    n_e = w_ij + w_ji
    p = np.ones(n_items)
    for _ in range(max_iter):
        r = n_e / (p[i] + p[j])                    # one pass over edges: O(|E|)
        denom = np.zeros(n_items)
        np.add.at(denom, i, r)
        np.add.at(denom, j, r)
        p_new = wins / denom                       # MM step: ascent on the (augmented) likelihood
        p_new /= np.exp(np.log(p_new).mean())      # geometric-mean gauge; MM is scale-equivariant
        if np.max(np.abs(np.log(p_new) - np.log(p))) < tol:
            return np.log(p_new)                   # already mean-zero after the gauge step
        p = p_new
    raise RuntimeError(f"MM did not converge in {max_iter} iterations (tol={tol})")

def _raises(exc: type[Exception], fn) -> None:
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")

def _tests() -> None:
    edges = dict(i=[0, 1, 0], j=[1, 2, 2], w_ij=[3, 3, 2], w_ji=[1, 1, 1])
    b = fit_bt_mm(3, **edges)
    assert abs(b.mean()) < 1e-12 and b[0] > b[1] > b[2]           # normalization + ordering
    b2 = fit_bt_mm(2, [0], [1], [5], [0], pseudo_count=0.5)
    assert np.isclose(b2[0] - b2[1], np.log(11.0))                  # undefeated item: finite gap ln 11
    _raises(ValueError, lambda: fit_bt_mm(2, [0], [1], [5], [0], pseudo_count=0.0))
    _raises(ValueError, lambda: fit_bt_mm(4, [0, 2], [1, 3], [1, 1], [1, 1]))  # two components
    _raises(RuntimeError, lambda: fit_bt_mm(3, **edges, max_iter=1, tol=1e-15))
    for bad in ({"n_items": 1}, {"pseudo_count": -1.0}, {"max_iter": 0}, {"tol": 0.0}, {"j": [0]}):
        kw = {"n_items": 2, "i": [0], "j": [1], "w_ij": [1], "w_ji": [1], **bad}
        _raises(ValueError, lambda kw=kw: fit_bt_mm(**kw))

_tests()
```

The two-item test checks the worked example from the formulas section. It shows that the pseudo-count turns a divergent MLE into a finite, shrunk gap. Uncertainty estimation (Hessian pseudo-inverse or a cluster bootstrap) is deliberately left outside the fitter, so the resampling unit stays an explicit caller decision.

## Production Pitfalls
- ❌ Mistake: Publishing a strict 1..n ranking from point estimates even when neighboring items differ by a fraction of their uncertainty → ✅ Fix: Compute uncertainty for each pairwise gap βᵢ − βⱼ. Use the pseudo-inverse of the observed-information Laplacian on the sum-zero subspace, which assumes independent comparisons, a correctly specified model, and enough comparisons per edge for the asymptotic approximation; or use a cluster bootstrap. Report items as a shared rank band whenever the 95% interval of their difference covers zero.
- ❌ Mistake: Judging rank separation by whether two items' marginal confidence intervals overlap → ✅ Fix: Test the interval of the difference itself, which accounts for the covariance between βᵢ and βⱼ induced by shared opponents and the centering constraint. Overlap of marginal intervals is neither necessary nor sufficient for overlap of the difference interval.
- ❌ Mistake: Bootstrapping individual comparisons when many of them share an annotator, a prompt, or a match session → ✅ Fix: Resample at the level of the independent unit (annotator, prompt, or session) and keep all of that unit's comparisons together. Per-comparison resampling treats correlated judgments as independent and produces intervals that are too narrow.
- ❌ Mistake: Running plain MLE on data with an undefeated item or a never-losing subset and accepting the huge β as converged → ✅ Fix: Check strong connectivity of the winner→loser graph before fitting. If it fails, fit the pseudo-count-augmented objective or a Gaussian-prior MAP, select the regularization strength by held-out log loss, and record it with the published scores.
- ❌ Mistake: Comparing centered scores across separately fitted runs, or across groups that were never compared against each other → ✅ Fix: Refit jointly on the union of comparisons after adding bridging comparisons or shared anchor items. Run a BFS component check on every fit and refuse to emit a single table when more than one component exists.

## Tradeoffs — When to Use What
**Suitable**

- **Static binary preference data over many items with a sparse but connected comparison graph.** Sparse MM costs O(|E| + n) per sweep, and no per-item absolute scale is required. This is the regime the classical model was built for.
- **Leaderboards with non-uniform opponent assignment.** The score equation equates observed and expected wins against the opponents actually faced, so strength-of-schedule correction comes built in. Raw win rate cannot provide it.
- **Learning a scalar scorer from pairwise labels only.** The BT likelihood on two candidates' scores is a binary cross-entropy on the score difference, −ln σ(rᵢ − rⱼ). This is the form used when training reward models from human preference pairs.
- **Predicting unobserved matchups inside one component.** σ(β̂ᵢ − β̂ⱼ) is available for every pair, provided residual checks on held-out pairs support the single-scalar assumption.

**Unsuitable**

- **Graded or continuous judgments (slider values, margins, scores, goal counts).** Collapsing them to win/loss discards the margin information. Use the **generalized Bradley–Terry** (GBT) family instead:
  - **K-nary-GBT** or **Poisson-GBT** for discrete outcomes.
  - **Gaussian-GBT** or **Uniform-GBT** for continuous outcomes.
  - With a Gaussian prior, GBT also guarantees a unique MAP and bounded per-comparison influence.
- **Data where ties are common.** Classical BT has no tie outcome, so ties are either dropped (biasing nᵢⱼ) or miscoded. Use the tie-aware extensions from Davidson or Rao–Kupper.
- **Strengths that drift over time or arrive as a stream.** Batch MLE weighs a year-old outcome the same as yesterday's, and every refit is a full pass. Use online rating systems such as **Elo**, **Glicko**, or **TrueSkill**.
- **Full or partial rankings of N items per judgment.** Splitting a ranking into pairs creates dependent comparisons and misstates uncertainty. Use **Plackett–Luce**, which models the ranking directly and reduces to BT when N = 2.

**Limitations to state in any design doc**

- **Calibration is not guaranteed.** The model always outputs a probability, but those probabilities are calibrated only if the model is correctly specified. Validate empirically on held-out comparisons using log loss, Brier score, and reliability bins, and inspect per-pair residuals (observed minus predicted) before using predicted win rates for matchmaking or gating decisions.
- **One scalar per item.** The model cannot represent stable preference cycles or context-dependent preferences; such structure shows up as concentrated residuals.
- **No order effects in the classical form.** Presentation order or home advantage must be added as an explicit extra parameter, or it leaks into item strengths.
- **Identification is per component.** Scores from separate fits or from disconnected groups cannot be compared without shared bridging comparisons.
- **Regularization changes the estimand.** Pseudo-counts and Gaussian priors shrink gaps. Their strength is a modeling choice to tune on held-out data, not a constant to copy across datasets.

## Industry Communication
*Hypothetical communication examples. All numbers are illustrative, not taken from a real system.*

- "Design doc: we fit **classical binary BT** on 41k preference pairs across 120 checkpoints. The **comparison graph** is one connected component, but 3 checkpoints are undefeated, so the plain **MLE does not exist** and we fit the **pseudo-count-augmented objective** instead."
- "PR review: a hard-coded **pseudo_count** of 1.0 isn't justified for this dataset — it shrinks every pairwise gap toward zero by an amount that depends on edge counts. Please sweep it on **held-out log loss** and record the chosen value in the eval config."
- "Postmortem: ranks 4 and 5 flipped between two nightly runs because we **bootstrapped individual comparisons**. After resampling by **prompt cluster**, the 95% interval on **β₄ − β₅** covered zero, so both are now reported as a shared rank band."
- "Architecture review: the **MM sweeps** are O(|E|) on sparse edge lists, so the refit stays cheap. The dense **Hessian pseudo-inverse** for standard errors is the O(n³) step, so we run it only on the final iterate."
- "Incident note: two vendor pools were never compared against each other, yet the merged table put them on one axis. The fitter now rejects **disconnected components**, and bridging comparisons are scheduled before the next release."
- "Eval review: predicted win probabilities are not **calibrated** by construction — in the held-out reliability check, the 0.8–0.9 bin won only 74% of the time. We're adding a **presentation-order term** and re-checking residuals before using these probabilities for gating."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Maximum Likelihood Estimation** — BT scores are the maximizer of a concave log-likelihood. Existence conditions, score equations, and observed-information standard errors all come from MLE theory, so failure modes such as divergent estimates for undefeated items only make sense with that background.
- (prerequisite) **Logistic Regression** — BT is intercept-free logistic regression on the design row eᵢ − eⱼ. Knowing logistic regression explains why the BT loss is binary cross-entropy on score differences and why generic GLM or Newton solvers can fit it.
- (alternative) **Thurstone model** — Independently proposed in psychophysics, it addresses the same paired-comparison problem with a different link between latent scores and outcomes. Choosing between the two is a modeling decision about the noise distribution.
- (alternative) **TrueSkill** — A Bayesian refinement of Elo-style rating that updates skill estimates online with explicit uncertainty. It is the relevant competitor when strengths drift and batch BT refits become stale.
- (extension) **Plackett–Luce model** — Generalizes BT from pairs to full rankings over N items while keeping the same strength parameters. It reduces exactly to BT when N = 2 and avoids splitting rankings into dependent pairs.
- (extension) **Generalized Bradley–Terry (GBT) models** — Extends the binary model to discrete outcomes (K-nary, Poisson) and continuous outcomes (Gaussian, Uniform) via an exponential-family construction. With a Gaussian prior, the MAP is guaranteed unique, monotone in the comparisons, and Lipschitz-resilient to any single new comparison.

## body_advanced_ko

## 기술적 정의와 동작 원리
**Bradley–Terry(BT) 모델**은 항목 집합 {1,…,n}의 각 항목에 로그-강도 β_i ∈ ℝ (p_i = e^{β_i} > 0)를 부여한다. 그리고 서로 독립인 각 비교 (i, j)의 결과를, i가 이길 확률이 σ(β_i − β_j)인 베르누이 변수로 모델링하는 쌍대 비교 모형이다. 대진 수 n_ij = w_ij + w_ji가 주어지면 항목별 총승수 W_i = Σ_j w_ij가 β에 대한 **충분통계**가 된다. 확률은 β의 **차이**에만 의존하므로 β와 β + c·**1**은 같은 분포를 낸다. 따라서 모수는 위치(게이지) 자유도 1개를 제외하고만 식별된다. Σβ_i = 0(= p의 기하평균 1)이나 앵커 항목 β_k = 0 같은 제약을 걸어야 해가 하나로 고정된다.

**데이터·제어 흐름**: 원시 비교 로그 (승자, 패자, 가중치) → 쌍별 집계(희소 간선 리스트 또는 밀집 W) → **비교 그래프 검사** → 초기화 → [MM 갱신 → 정규화 → 수렴 판정] 루프 → 출력. 출력은 β̂, 예측 승률 σ(β̂_i − β̂_j), 곡률 기반 근사 표준오차다. 그래프 검사는 반드시 루프 **앞**에 둬야 한다. 데이터 구조상 해가 존재하지 않으면 반복을 아무리 돌려도 β가 발산할 뿐이기 때문이다.

**최대우도 적합 알고리즘** (Zermelo 반복 = MM)

1. **입력 계약 확인**: 대각(자기 비교)은 0이어야 하고, 음수·NaN·inf는 금지한다. 기본형은 이진 승패 모형이다. 동점을 0.5승씩 나눠 넣는 가중 우도를 허용할지는 적합 전에 계약으로 정한다.
2. **그래프 검사**: w_ij > 0이면 간선 i→j를 둔다.
   - **무방향 연결성**이 깨지면 성분 사이의 상대 위치가 데이터로 결정되지 않는다. 성분 수만큼 평행이동 자유도가 생긴다.
   - **방향 강연결성**이 깨지면, 바깥 항목에게 한 번도 지지 않은 집합 S가 존재한다. 이때 S에 속한 모든 β에 +t를 더하면 S가 이긴 항의 우도만 커지므로, ℓ이 t에 대해 단조 증가하고 유한 MLE가 없다.
   - 실패 시에는 강연결 성분을 보고한 뒤 다음 중 하나를 고른다: 교차 비교 보강, 성분별 분리 적합, Gaussian prior MAP로 명시적 전환.
3. **초기화**: 임의의 양수로 시작하며, 보통 p_i = 1을 쓴다. 강연결이면 모든 W_i > 0이므로 갱신 중 p가 0으로 붕괴하지 않는다.
4. **MM 갱신**: −n_ij log(p_i + p_j) 항은 p_i와 p_j가 얽혀 있어 닫힌 해가 없다.
   - log의 오목성에서 나오는 접선 부등식 −log x ≥ 1 − log y − x/y를 쓴다. 여기서 y = p_i^{(k)} + p_j^{(k)}다.
   - 이 부등식으로 해당 항을 아래에서 감싸면, 항목별로 분리되는 대리함수가 생긴다.
   - 대리함수를 최대화하면 갱신식 p_i^{(k+1)} = W_i / Σ_j [n_ij / (p_i^{(k)} + p_j^{(k)})]를 얻는다.
   - 대리함수는 현재 점에서 원함수와 접하므로, 매 반복 ℓ이 줄어들지 않는다(단조 상승).
5. **정규화**: 갱신 후 p를 기하평균으로 나눈다. 우도는 변하지 않고 게이지만 Σβ = 0으로 고정되므로, 반복 간 값을 비교할 수 있다.
6. **수렴 판정**: score 잔차 r_i = W_i − Σ_j n_ij σ(β_i − β_j)(관측 승수 − 기대 승수)는 ∂ℓ/∂β_i와 같다. 따라서 max_i |r_i| < tol을 판정 기준으로 쓰면 허용오차의 단위가 '승수'라 해석하기 쉽다. 반면 파라미터 변화량만 보는 판정은 수렴이 느린 구간에서 조기 종료를 오판할 수 있다.
7. **미수렴 처리**: max_iter에 도달하면 마지막 값을 조용히 반환하지 말고 실패를 올린다. MM은 선형 수렴이라 다음 상황에서 느려질 수 있다: 교차 비교가 적은 군집 구조(작은 대수적 연결도), 분리 직전의 데이터. 대응책은 두 가지다.
   - 제약 부분공간에서 Hessian L(β)를 쓰는 Newton 단계로 전환
   - MAP로 전환
8. **사후 산출**: 쌍별 잔차 Y_ij − P_ij(관측 결과 − 예측 확률)로 적합도를 점검한다. L(β̂)의 유사역행렬로 근사 공분산을 얻는다.

**복잡도**

- 밀집 구현: 메모리 O(n²), 반복당 O(n²).
- 비교가 존재하는 쌍 m개만 간선 리스트로 들고 있으면: 반복당 O(n + m).
- 강연결성 검사: 한 정점에서 정방향·역방향 BFS를 두 번 돌리면 되므로 O(n + m).
- Newton 전환: 밀집 선형계 풀이가 반복당 O(n³)이라, n이 크면 희소 솔버가 필요하다.

참고 사례로, 16개 팀·2,123경기 데이터에 IRT 소프트웨어로 BTL 모형을 적합한 튜토리얼은 위치 모수를 평균 0으로 제약했고 4회 반복에 수렴했다고 보고한다. 범용 성능 벤치마크 수치는 참고자료에 제시되어 있지 않다.

## 핵심 수식·아키텍처·도표
**모형과 로그우도** — σ(x) = 1/(1 + e^{−x})로 두면

$$\Pr(i \succ j) = \frac{p_i}{p_i + p_j} = \sigma(\beta_i - \beta_j), \qquad p_i = e^{\beta_i}$$

d = β_i − β_j라 하면 쌍 (i, j)의 기여는 w_ij·log σ(d) + w_ji·log σ(−d)다. 여기에 log σ(d) = d − log(1 + e^d), log σ(−d) = −log(1 + e^d)를 대입하면 다음을 얻는다.

$$\ell(\beta) = \sum_{i<j} \Big[ w_{ij}(\beta_i - \beta_j) - n_{ij}\log\big(1 + e^{\beta_i - \beta_j}\big) \Big]$$

**기울기 = 관측 승수 − 기대 승수**

$$\frac{\partial \ell}{\partial \beta_i} = W_i - \sum_{j \neq i} n_{ij}\,\pi_{ij}, \qquad \pi_{ij} = \sigma(\beta_i - \beta_j)$$

MLE 조건은 모든 항목에서 '관측 총승수 = 모형 기대 총승수'다. 승수가 같더라도 강한 상대와 많이 붙은 항목은 기대 승수가 낮게 잡힌다. 그 결과 β가 올라가는데, 이것이 일정 강도(strength of schedule) 보정의 수학적 정체다.

**곡률: 가중 그래프 라플라시안과 식별성**

∂π_ij/∂β_i = π_ij·π_ji이므로, 음의 로그우도 Hessian은 비교 그래프의 가중 라플라시안이 된다.

$$-\nabla^2 \ell(\beta) = L(\beta), \qquad L_{ij} = -n_{ij}\,\pi_{ij}\pi_{ji}\ (i \neq j), \qquad L_{ii} = \sum_{j \neq i} n_{ij}\,\pi_{ij}\pi_{ji}$$

- **L·1 = 0**: 모든 β를 같은 양만큼 옮기는 방향의 곡률이 정확히 0이다. 이것이 게이지 자유도다. 1ᵀβ = 0 제약은 바로 이 영공간 방향 하나만 제거한다.
- **제약 공간의 최소 곡률**: 1의 직교여공간에서 최소 곡률은 L의 두 번째로 작은 고유값 λ₂(L)이다. λ₂ > 0은 무방향 비교 그래프가 연결된 것과 동치다. 연결 성분이 c개면 영공간이 c차원이므로, 합-0 제약 하나만으로는 c − 1개 방향이 여전히 평평하다.
- **곡률 양수 ≠ 유한 해 존재**: 무방향으로 연결돼 있어 ℓ이 제약 공간에서 엄격 오목이더라도, 방향 강연결이 깨지면 상한에 무한대 방향으로만 다가간다. 이 경우 MLE가 존재하지 않는다.
- **근사 공분산**: Cov(β̂) ≈ L(β̂)⁺(유사역행렬, 합-0 게이지 기준)이다. 곡률이 작은 방향, 즉 교차 비교가 적은 군집 사이의 차이일수록 분산이 크다.

**MLE와 Gaussian-prior MAP의 곡률 비교** — β_i ~ N(0, σ₀²)가 서로 독립이고 λ = 1/σ₀²일 때

$$\ell_{\text{MAP}}(\beta) = \ell(\beta) - \frac{\lambda}{2}\lVert \beta \rVert^2, \qquad -\nabla^2 \ell_{\text{MAP}}(\beta) = L(\beta) + \lambda I \succeq \lambda I$$

- **MLE**: 게이지 방향의 최소 곡률이 0이므로 식별성 제약이 필수다. 해의 존재 여부는 방향 강연결성에 달려 있다.
- **MAP**: 모든 방향의 곡률이 λ 이상인 강볼록(negative log-posterior) 문제다. 따라서 그래프 구조와 무관하게 유일한 유한 해가 존재한다.
- **게이지 자동 고정**: MAP 정상 조건 W_i − E_i = λβ_i를 i에 대해 합한다. 매 비교의 승자는 정확히 1명이므로 Σ_i W_i = Σ_i E_i = 총 비교 수이고, 따라서 λΣβ_i = 0이다. 즉 prior가 합-0 게이지를 자동으로 고른다.
- **대가**: 끊어진 성분 사이의 상대 위치는 데이터가 아니라 prior가 정한다(모두 0 쪽으로 당겨짐). 성분 간 비교가 '가능해진' 것이 아니라 값이 '정의된' 것뿐이다.

**Elo 스케일 변환**: 10^{R/400} = e^{β}에서 R_i = (400 / ln 10)·β_i ≈ 173.7·β_i다. 즉 1 logit은 약 173.7 Elo 점에 해당한다.

**수치 예: 두 항목 A, B를 10번 비교** (d = β_A − β_B)

- **A 7승 3패, MLE**: d̂ = ln(7/3) ≈ 0.847이고 예측 승률은 0.70이다. d 좌표의 곡률은 10 × 0.7 × 0.3 = 2.1이므로 SE(d̂) ≈ 1/√2.1 ≈ 0.69다. 95% 구간 ≈ [−0.51, 2.20]으로 0을 포함하므로, 10번으로는 우열을 단정할 수 없다.
- **같은 데이터, MAP** (λ = 1): β_A = d/2, β_B = −d/2이므로 prior 항은 −λd²/4다. 정상 조건 7 − 10σ(d) − d/2 = 0을 풀면 d ≈ 0.69(승률 ≈ 0.666)다. 곡률은 10 × 0.666 × 0.334 + 0.5 ≈ 2.72로 MLE보다 크고, 추정치는 0 쪽으로 수축한다.
- **A 10승 0패**: MLE 기울기 10(1 − σ(d))는 모든 d에서 양수이므로 d̂ = ∞다. 방향 강연결 위반의 최소 사례다. 반면 MAP(λ = 1)는 10 − 10σ(d) − d/2 = 0에서 d ≈ 2.13(승률 ≈ 0.89)로 유한하다.

## 코드 또는 의사코드
밀집 행렬 기반의 실행 가능한 참조 구현이다(numpy만 사용). 구성 순서는 다음과 같다.

- 입력 계약 검증
- 방향 강연결성 검사
- MM 갱신과 기하평균 정규화
- score 잔차 기반 수렴 판정
- 미수렴 시 명시적 실패

```python
from collections import deque
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class BTResult:
    beta: np.ndarray   # 로그-강도, sum(beta) == 0 게이지
    converged: bool
    n_iter: int
    residual: float    # max_i |W_i - E_i|, 단위: 승수

def _all_reachable(adj: np.ndarray, start: int = 0) -> bool:
    seen = np.zeros(adj.shape[0], dtype=bool)
    seen[start] = True
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in np.flatnonzero(adj[u] & ~seen):
            seen[v] = True
            queue.append(v)
    return bool(seen.all())

def fit_bradley_terry(W, *, max_iter: int = 10_000, tol: float = 1e-8,
                      allow_weighted: bool = False, strict: bool = True) -> BTResult:
    '''Zermelo/MM 최대우도 적합. W[i, j] = i가 j를 이긴 횟수.
    비용: 밀집 구현이라 메모리 O(n^2), 반복당 O(n^2).
          비교 쌍 m개만 간선 리스트로 들면 반복당 O(n + m)으로 줄일 수 있다.
    계약: 기본은 정수 승수만 받는다. allow_weighted=True일 때만
          비음수 실수 가중(예: 동점을 0.5승씩 분할)을 가중 우도로 받는다.
    tol: 승수 단위 절대 잔차. 총 비교 수가 매우 크면 비례해 키운다.'''
    W = np.asarray(W, dtype=float)
    if W.ndim != 2:
        raise ValueError(f'W must be 2-D, got ndim={W.ndim}')
    n = W.shape[0]
    if W.shape[1] != n:
        raise ValueError(f'W must be square, got shape={W.shape}')
    if n < 2:
        raise ValueError('need at least 2 items')
    if not np.isfinite(W).all():
        raise ValueError('W contains NaN or inf')
    if (W < 0).any():
        raise ValueError('W must be nonnegative')
    if np.any(np.diag(W) != 0):
        raise ValueError('diagonal must be 0 (no self-comparison)')
    if not allow_weighted and not np.array_equal(W, np.round(W)):
        raise ValueError('non-integer counts: pass allow_weighted=True explicitly')
    if not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError('max_iter must be a positive int')
    if not (np.isfinite(tol) and tol > 0):
        raise ValueError('tol must be a positive finite float')

    beats = W > 0                      # 간선 i -> j: i가 j를 1번 이상 이김
    if not (_all_reachable(beats) and _all_reachable(beats.T)):
        raise ValueError('comparison digraph not strongly connected: '
                         'finite MLE does not exist (use MAP or add comparisons)')

    wins = W.sum(axis=1)               # W_i, 강연결이면 모두 > 0
    N = W + W.T                        # n_ij
    p = np.ones(n)
    residual = np.inf
    for it in range(1, max_iter + 1):
        p = wins / (N / (p[:, None] + p[None, :])).sum(axis=1)   # MM 갱신
        p /= np.exp(np.log(p).mean())                          # 기하평균 1 == sum(beta) 0
        P = p[:, None] / (p[:, None] + p[None, :])             # pi_ij
        residual = float(np.abs(wins - (N * P).sum(axis=1)).max())
        if residual < tol:
            return BTResult(np.log(p), True, it, residual)
    if strict:
        raise RuntimeError(f'no convergence in {max_iter} iters, residual={residual:.2e}')
    return BTResult(np.log(p), False, max_iter, residual)

# 최소 실행 예: A>B 2:1, B>C 2:1, A>C 4:1 -> 참 MLE는 p = 2 : 1 : 0.5
W = np.array([[0, 2, 4],
              [1, 0, 2],
              [1, 1, 0]])
res = fit_bradley_terry(W)
print(res.converged, np.round(res.beta, 4))   # True [ 0.6931  0.  -0.6931] (가운데는 -0.으로 찍힐 수 있음)
print(round(float(1 / (1 + np.exp(res.beta[2] - res.beta[0]))), 3))   # Pr(A>C) = 0.8

# 실패 경로 1: B가 A를 한 번도 못 이김 -> 강연결 아님 -> ValueError
# fit_bradley_terry(np.array([[0, 5], [0, 0]]))
# 실패 경로 2: max_iter=1이면 대부분 미수렴 -> RuntimeError (strict=False면 converged=False 반환)
# fit_bradley_terry(W, max_iter=1)
```

**예상 결과를 손으로 검증하는 방법**: β = (ln2, 0, −ln2)를 대입해 기대 승수를 계산한다.

- A: 3×(2/3) + 5×(4/5) = 6으로 관측 승수 6과 같다.
- B: 3×(1/3) + 3×(2/3) = 3으로 관측 승수 3과 같다.
- C: 3×(1/3) + 5×(1/5) = 2로 관측 승수 2와 같다.

세 항목 모두 score 잔차가 0이므로 이 값이 MLE다. A>B>C>A 방향의 패배가 섞여 있어도 강연결이면 적합에는 아무 문제가 없다.

## 프로덕션 함정
- ❌ 실수: 무방향 연결성만 확인하고 적합을 돌린다. 그 결과 한 번도 지지 않은 항목군의 β가 반복마다 커지다가 max_iter에서 끊긴 값이 그대로 리더보드에 배포된다 → ✅ 해결: 적합 전에 승리 간선 기준 방향 강연결성을 정방향·역방향 BFS 두 번으로 검사한다. 실패하면 강연결 성분 목록을 보고하고, 교차 비교 보강이나 Gaussian prior MAP로 명시적으로 전환한다.
- ❌ 실수: 서로 다른 시점이나 데이터로 적합한 두 BT 결과의 β를 직접 빼서 버전 간 개선폭으로 보고한다. 각 적합의 합-0 게이지가 서로 다른 항목 집합 기준이라 기준점이 다르다 → ✅ 해결: 두 데이터를 하나의 비교 그래프로 합쳐 재적합한다. 또는 양쪽에 공통으로 등장하는 앵커 항목의 β를 0으로 고정해 같은 게이지에서 비교한다.
- ❌ 실수: 점 추정 β̂의 순서만으로 순위를 확정한다. 그러면 비교 수가 적어 곡률이 작은 항목이 표본 잡음만으로 상위에 오르거나 순위가 매주 요동친다 → ✅ 해결: L(β̂)의 유사역행렬이나 부트스트랩으로 구간을 계산해 순위와 함께 노출한다. 구간이 크게 겹치는 항목은 동순위로 묶고, 추가 비교를 우선 배정한다.
- ❌ 실수: 비교 레코드의 방향 규약(첫 열이 승자인지, i 기준 결과 0/1인지)을 파이프라인마다 다르게 해석한다. 그 결과 W의 일부가 전치된 채 적합되어 순위가 부분적으로 뒤집힌다 → ✅ 해결: 수집 단계에서 (winner_id, loser_id, weight) 정규 스키마로 변환한다. 원본 로그 대비 항목별 총승수 W_i와 쌍별 대진 수 n_ij가 일치하는지는 단위 테스트로 고정한다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**

- **결과가 이진이고 품질을 단일 스칼라로 요약해도 되는 경우**(승/패, 선택/비선택): 로그우도가 제약 공간에서 오목하다. 충분통계도 W_i와 n_ij뿐이라, 간선 리스트 기반 반복당 O(n + m)으로 대규모 비교 로그를 배치 적합할 수 있다.
- **대진이 불균형한 경우**: 기울기가 '관측 승수 − 기대 승수'라서 상대 강도가 자동으로 반영된다. 강한 상대를 많이 만난 항목이 단순 집계보다 공정하게 평가된다.
- **점 추정과 함께 불확실성을 보고해야 하는 경우**: 곡률 행렬 L(β̂)의 유사역행렬로 표준오차를 바로 얻는다. 미관측 쌍의 승률 σ(β̂_i − β̂_j)도 같은 모수로 예측된다.
- **쌍 선호를 학습 손실로 바꿔야 하는 경우**(예: RLHF 보상 모델): β_i를 신경망 출력 점수 r(x)로 바꾸면 같은 로그우도가 쌍별 손실 −log σ(r(x_승) − r(x_패))가 된다. 항목 수가 무한한 상황으로 자연스럽게 일반화된다.

**이럴 때 부적합**

- **동점, 점수 차, 연속 평점이 핵심 정보인 경우**: 이진 BT로 축약하면 마진 정보가 버려진다. 대안은 Davidson·Rao–Kupper류 동점 확장, 또는 Gaussian-GBT·Poisson-GBT처럼 비교값 분포를 직접 모델링하는 **Generalized Bradley–Terry**다.
- **데이터가 전체 순위나 top-k 목록인 경우**: 순위를 쌍으로 쪼개 BT에 넣으면 같은 순위에서 나온 쌍들을 독립으로 잘못 취급한다. 대안은 순위 전체의 우도를 쓰는 **Plackett–Luce**다.
- **비교가 스트리밍으로 들어오고 강도가 시간에 따라 변하는 경우**: 배치 MLE를 매번 전체 재적합하면 비용이 커지고, 과거 결과도 동일 가중으로 남는다. 대안은 경기 단위로 점진 갱신하는 **Elo / Glicko / TrueSkill**이다.
- **희소하거나 분리된 데이터인 경우**(예: 무패 신규 항목, 교차 비교가 거의 없는 군집): MLE가 존재하지 않거나 분산이 폭발한다. 대안은 강볼록성이 보장되는 **Gaussian prior MAP**(GBT의 MAP 설정)나 베이지안 계층 모형이다. 다만 성분 간 위치는 prior가 정한다는 점을 함께 공지해야 한다.

## 업계 대화 맥락
- "(가상 예시 · PR 리뷰) `fit_bradley_terry` 호출 전에 **방향 강연결성 검사**가 빠져 있습니다. 이번 배치에서 아직 패배 기록이 없는 신규 항목 3개는 **MLE가 발산**할 수 있습니다. 검사 실패 시 **λ=1 Gaussian prior MAP**로 폴백하는 분기를 추가해 주세요."
- "(가상 예시 · 설계 문서) 노출 점수는 **합-0 게이지**의 β를 **Elo 스케일** (×173.7)로 변환해 사용합니다. 순위 옆에는 **L(β̂)⁺ 기반 95% 구간**을 함께 표시하고, 구간이 겹치는 항목은 동순위로 묶습니다."
- "(가상 예시 · 인시던트 회고) 주간 재적합 잡이 **max_iter=10,000**에 도달해 실패했고, 최종 **score 잔차는 3e-4**에서 정체됐습니다. 교차 비교가 적은 두 군집 때문에 **λ₂** (L)가 작아졌을 가능성을 한 가설로 보고 있습니다. 다만 분리 직전의 항목 쌍이나 데이터 적재 오류도 배제되지 않았으므로, 원인을 확정하기 전까지는 MAP 결과를 임시 배포합니다."
- "(가상 예시 · PR 리뷰) 이번 데이터에서 A>B>C>A **순환 패턴**이 관측됐습니다. 하지만 확률 모형에서도 순환은 우연히 충분히 나올 수 있어, 이것만으로 **BT 부적합**으로 판단하긴 이릅니다. 쌍별 **잔차 Y_ij − P_ij**를 집계해 체계적 편향이 있는지 먼저 확인하죠."
- "(가상 예시 · 설계 문서) 동점이 전체 비교의 약 12%라서 우선 **0.5승 분할** (allow_weighted=True)로 적합합니다. 동점률이 강도 차와 함께 움직이는 패턴이 보이면, **동점 확장 모형**이나 **GBT**로 옮기는 안을 비교 실험하겠습니다."
- "(가상 예시 · 리뷰 코멘트) v3와 v4 점수를 **서로 다른 적합 결과**에서 바로 빼면 게이지가 달라 해석할 수 없습니다. 두 버전을 **같은 비교 그래프에 합쳐 재적합**하거나, 공통 앵커 항목을 0으로 고정한 뒤 비교해야 합니다."
- "(가상 예시 · 인시던트 회고) 오클릭으로 추정되는 비교 수십 건이 한 항목의 순위를 끌어올린 것으로 보입니다. 현재 **MLE 경로**에는 단일 비교의 영향을 직접 제한하는 장치가 없습니다. 비교 하나의 영향이 유계로 보장되는 **Gaussian prior MAP** 경로로의 전환을 다음 스프린트 안건으로 올립니다."

## 선행·대안·확장 개념
- (선행) **Logistic Regression** — BT는 '두 항목 지시변수의 차이(+1/−1)'를 설계행렬로 둔 절편 없는 로지스틱 회귀와 같은 우도를 가진다. 따라서 기울기·Hessian·분리(separation) 문제를 그대로 이해하는 기반이 된다.
- (선행) **Maximum Likelihood Estimation** — BT 적합은 승리 행렬에 대한 로그우도 최대화 문제다. 식별성 제약, 해의 존재 조건, 곡률 기반 표준오차가 모두 MLE 이론에서 나온다.
- (대안) **Thurstone model** — 같은 쌍대 비교 문제를 로지스틱 대신 정규분포(probit) 잡음으로 모델링하는 접근이다. 잡음 분포 가정을 바꾸고 싶을 때 비교 대상이 된다.
- (대안) **TrueSkill** — 강도를 분포로 두고 경기마다 베이지안 방식으로 점진 갱신한다. 배치 재적합 비용 없이 스트리밍 비교와 시간에 따른 강도 변화를 다룰 때 BT 배치 MLE의 대안이 된다.
- (확장) **Plackett–Luce model** — BT의 비율 확률을 전체 순위의 순차 선택으로 확장한 모형이다. 두 항목만 남기면 BT로 환원되며, 쌍으로 쪼갤 때 생기는 의존성 무시 문제를 해결한다.
- (확장) **Generalized Bradley–Terry** — (GBT) — 지수족의 부분집합으로 이산·연속 비교값을 함께 다루도록 BT를 일반화한 계열이다. Gaussian prior 아래에서 MAP가 강볼록이고, 비교 하나의 영향이 유계(Lipschitz-resilient)라는 성질이 증명되어 있다.

## references_en

- {"title": "Modelling Pairwise Comparisons using the Bradley-Terry-Luce (BTL) Model", "authors": "Alvin Vista, Ray Adams, Dan Cloney", "year": 2020, "venue": "ACER ConQuest tutorial", "type": "docs", "url": "https://www.acer.org/files/Tutorial-13--Pairwise-comparisons.pdf", "tier": "primary", "annotation": "Step-by-step worked fit on a 16-team dataset, including mean-zero scaling and per-game residuals."}
- {"title": "Asymptotic theory of sparse Bradley-Terry model", "authors": "R. Han", "year": 2020, "venue": "Annals of Applied Probability", "type": "paper", "url": "https://projecteuclid.org/journals/annals-of-applied-probability/volume-30/issue-5/Asymptotic-theory-of-sparse-BradleyTerry-model/10.1214/20-AAP1564.pdf", "tier": "primary", "annotation": "Theory for when estimates stay trustworthy if most pairs are never compared, a common real-world situation."}
- {"title": "Diagnostic Framework for the Bradley–Terry Model", "authors": "W. Wu", "year": 2022, "venue": "Journal of the Royal Statistical Society Series A", "type": "paper", "url": "https://academic.oup.com/jrsssa/article/185/Supplement_2/S461/7069516", "tier": "primary", "annotation": "Tools for checking whether a fitted Bradley–Terry model actually matches your comparison data."}
- {"title": "Generalized Bradley-Terry Models for Score Estimation from Paired Comparisons", "authors": "Julien Fageot, Sadegh Farhadkhani, Lê-Nguyên Hoang, Oscar Villemaud", "year": 2023, "venue": "arXiv", "type": "paper", "url": "https://arxiv.org/html/2308.08644", "tier": "primary", "annotation": "Extends BT beyond win/loss and proves convexity, monotonicity, and bounded influence of any single comparison."}
- {"title": "Bradley-Terry Pairwise Ranking Calculator", "type": "docs", "url": "https://metricgate.com/docs/bradley-terry-pairwise-ranking", "tier": "secondary", "annotation": "Practical notes on strength-of-schedule, scale normalization, and why connectivity diagnostics matter."}
- {"title": "Bradley–Terry model", "type": "wiki", "url": "https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model", "tier": "secondary", "annotation": "Compact reference for the formula, logit and Elo forms, Zermelo's iterative fit, and Plackett–Luce."}
