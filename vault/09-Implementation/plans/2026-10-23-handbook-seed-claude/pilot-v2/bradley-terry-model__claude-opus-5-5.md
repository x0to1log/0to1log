# Bradley–Terry Model — claude-opus-5-5

- advanced 70 / basic 78 / gate pass / penalty 3 / $2.2741 / 590s

## definition_en

The Bradley–Terry model is a probability model for pairwise comparisons that assigns each item a positive latent score and sets the chance that one item beats or is preferred over another by the relative size of their scores, so that scores can be inferred in reverse from observed wins and preferences via maximum likelihood. It shares its logistic form with logistic regression on score differences and with the Elo win-probability formula, and it is foundational to reward-model training in RLHF.

## definition_ko

브래들리-테리 모형은 각 대상에 양의 잠재 점수를 부여하고 두 대상 중 하나가 선택될 확률을 두 점수의 상대적 크기로 정하는 쌍대 비교 확률 모형으로, 관측된 승패·선호 결과로부터 최대우도로 점수를 역추정해 전체 순위와 미관측 대결의 승률을 산출하며 로지스틱 회귀·Elo 레이팅과 수학적으로 같은 형태를 가진다.

## summary_en

The Bradley–Terry model is a way to turn many 'A beat B' or 'people preferred A over B' results into one score per item. Think of a referee who never sees a full league table, only a pile of match results, and still works out how strong each team probably is. Each item gets a strength number, and the chance that one item wins a matchup depends on how big its strength is compared with the other's. Once the strengths are estimated, you can rank everything and predict matchups that never happened. That is why it shows up in sports rankings, survey analysis, and training AI systems from human preferences.

## summary_ko

브래들리-테리 모형은 '둘 중 누가 더 나은가'라는 쌍 비교 결과를 모아 각 대상의 숨은 실력 점수를 거꾸로 추정하는 확률 모형이다. 리그 경기 결과만 보고 팀별 전력을 매기는 해설가를 떠올리면 된다. 각 대상에 양수 점수를 하나씩 주고, 두 대상이 붙으면 점수가 큰 쪽이 그 비율만큼 이길 확률이 높다고 본다. 점수를 한 번 구해 두면 실제로 맞붙은 적 없는 조합의 결과도 예측할 수 있다. 사람의 선호를 학습하는 AI 보상 모델과 AI 모델 순위표의 수학적 토대가 된다.

## body_basic_en

## Plain Explanation
Many ranking problems start with a frustrating fact: nobody can give reliable absolute scores. Asking a judge to rate 50 items from 1 to 100 produces inconsistent numbers, and in competitions there is no score at all, only who won. Yet comparing two things at a time is easy, so we end up with a pile of pairwise results and still need a full ranking.

The Bradley–Terry model solves this by imagining that every item carries a hidden strength number. Picture two people drawing a ball from a bag: one owns 3 balls in the bag, the other owns 1. The owner of 3 balls should win about 3 out of 4 draws, or 75%, not every time. The model says any matchup works the same way: the chance that A beats B equals A's strength divided by the sum of both strengths.

The real work runs backward. Given who beat whom and how often, the model searches for the strength values that make the observed results most likely, a method called maximum likelihood; Ernst Zermelo showed in the 1920s that this has a single best answer and can be found by simple repeated updates. Because only ratios matter, multiplying every strength by 10 changes nothing, so a scale convention is needed, such as fixing the average log-strength at zero. When data are sparse or an item never loses, the plain estimate can run off toward infinity, so practitioners add a gentle pull toward the middle, known as regularization or a prior.

## Examples & Analogies
- **Australian football team strengths**: An ACER tutorial fits the model to 2,123 games among 16 AFL teams, treating each game as a win/loss comparison. The output places every team on one logit scale with standard errors, identifying Geelong as strongest and Richmond as weakest in that dataset.
- **Tournesol video recommendations**: Contributors on the Tournesol platform judge which of two videos should be recommended more often. A generalized Bradley–Terry model, released in the open-source Python package solidago, turns those judgments into video scores.
- **Animal dominance hierarchies**: Researchers record which animal wins each encounter within a group, for example who displaces whom at a feeding spot. The model converts these scattered contests into a dominance ordering, even for pairs that were rarely seen interacting.

## At a Glance
| | Bradley–Terry | Elo rating | Win percentage | Plackett–Luce |
|---|---|---|---|---|
| Input data | Pairwise outcomes | Pairwise outcomes, game by game | Wins and total games | Full or partial rankings |
| Matchup model | Strength ratio, logistic in log-scores | Same logistic form, base 10, scale 400 | None; ignores opponent strength | Same positive-worth parameterization, extended to orderings |
| How scores are found | Fit to all data at once (maximum likelihood) | Typically updated online after each game | Simple division | Fit to observed rankings |
| Predicts unseen pairs | Yes | Yes | No | Yes; reduces to BT for two items |

Win percentage treats beating a weak opponent the same as beating a strong one, while Bradley–Terry, Elo, and Plackett–Luce all model who you played, differing mainly in whether scores are refit in a batch, updated game by game, or learned from whole rankings.

## Where and Why It Matters
- **Opponent-adjusted rankings**: Because each win is weighted by the opponent's estimated strength, tournaments with unbalanced schedules get a fairer ordering than raw win rates provide.
- **Reward models in RLHF**: Common pairwise reward-model losses use the Bradley–Terry form, turning a human's 'response A is better than B' into a training signal for a scoring model.
- **Elo's probability rule**: Elo's expected-score formula is the Bradley–Terry probability rescaled to base 10 and 400 points, so Elo ratings can be read as BT-style strengths updated incrementally.
- **Search relevance from preferences**: The model plays a role in estimating document relevance; when preferences are inferred from user behavior rather than stated in explicit pairwise judgments, the noisier input deserves extra scrutiny.
- **Connectivity checks before reporting**: If two groups of items were never compared against each other, their strengths are only comparable within each group, so the comparison graph must be checked before publishing a single ranking.

## Common Misconceptions
- ❌ Myth: A strength of 2.0 is an absolute quality level you can compare across studies. → ✅ Reality: Only ratios or differences matter; every fit picks its own scale convention, so scores from separate fits are not directly comparable.
- ❌ Myth: Any set of comparisons yields a trustworthy full ranking. → ✅ Reality: Disconnected groups cannot be ranked against each other, and an item that never loses (separation) pushes the plain estimate to infinity unless you add regularization or a prior.
- ❌ Myth: If A's score is higher than B's, A is definitely better. → ✅ Reality: Scores are estimates with uncertainty; with few comparisons, standard errors can overlap and the order may flip with more data.

## How It Sounds in Conversation
- "Can we fit **Bradley–Terry** on the annotator picks instead of averaging the 1–5 ratings? They're way more consistent pairwise."
- "Heads up: the new prompts and the old ones were never compared head to head, so the **comparison graph** is disconnected."
- "One checkpoint never lost a single matchup and its score blew up; let's add an **L2 prior** before Friday's review."
- "The **reward model** loss is just BT on chosen vs. rejected, so label noise goes straight into the scores."
- "Please show **confidence intervals** on the leaderboard; models 3 and 4 are basically tied."

## Related Reading
- (before) **Logistic Regression** — BT is logistic regression on score differences; knowing the sigmoid makes the win-probability curve intuitive.
- (before) **Maximum Likelihood Estimation** — The standard way BT strengths are fitted; read it to see why separated data breaks the estimate.
- (similar) **Elo Rating System** — Same logistic win-probability form, but ratings update game by game instead of a single batch fit.
- (similar) **Thurstone Model** — A parallel pairwise model from psychophysics using a normal curve instead of a logistic one; compare their assumptions.
- (next) **Plackett–Luce Model** — Extends BT from pairs to full rankings with the same positive-worth parameters.
- (next) **RLHF** — See how BT-style pairwise losses turn human preferences into reward signals for language models.

## body_basic_ko

## 쉽게 이해하기
대상이 수십 개를 넘으면 사람에게 전체 순위를 매기라고 하기는 어렵지만, 둘 중 어느 쪽이 나은지 고르기는 쉽습니다. 문제는 이런 비교 결과가 들쭉날쭉하고, 모든 쌍을 다 비교하지도 않는다는 점입니다. 단순 승률로 줄 세우면 약한 상대에게 거둔 승리와 강한 상대에게 거둔 승리가 똑같이 취급됩니다.

브래들리–테리 모델은 각 대상에 눈에 보이지 않는 '체급 점수'를 붙여 이 문제를 풉니다. 줄다리기처럼 힘이 3인 팀과 1인 팀이 붙으면 센 팀이 이길 확률을 3÷(3+1)=75%로 봅니다. 그래서 강팀을 이긴 기록은 점수를 크게, 약팀을 이긴 기록은 조금만 올려 상대 강도를 반영한 점수가 됩니다.

점수는 관측된 승패 기록이 나올 확률(우도)이 가장 커지도록 조정해 찾습니다. 모든 점수에 같은 수를 곱해도 확률이 같으므로 평균을 고정하는 정규화가 필요합니다. 직접 붙지 않은 두 대상도 공통 상대를 통해 비교가 충분히 연결되어 있다면 안정적으로 점수를 추정하고 승부를 예측할 수 있습니다.

## 비유와 예시
- **호주 풋볼(AFL) 팀 강도 추정**: ACER 튜토리얼은 16개 팀의 2,123경기 승패에 이 모델을 적합해 팀 강도를 로짓 척도로 추정했습니다. 그 결과 Geelong이 가장 강하고 Richmond가 가장 약한 팀으로 나왔습니다.
- **와인 선호 설문** (가상 예시): 응답자에게 와인 전체 순위 대신 두 잔씩만 비교하게 한 뒤 전체 순위를 만듭니다. 아무도 직접 비교하지 않은 두 와인 사이의 선호 확률도 계산할 수 있습니다.
- **Tournesol 영상 추천**: 참여자가 두 영상 중 더 추천할 쪽을 고르면, 이를 영상 점수로 바꾸는 데 이 모델을 일반화한 GBT 모델 등을 쓴다고 보고되었습니다. 구현은 solidago라는 파이썬 패키지로 공개되어 있습니다.

## 한눈에 비교
| | 브래들리–테리 | Elo 레이팅 | 단순 승률 | Plackett–Luce |
|---|---|---|---|---|
| 입력 | 쌍대 승패 | 경기별 승패 | 승·패 횟수 | 전체 또는 부분 순위 |
| 확률 모형 | 강도 비율(로지스틱) | BT와 같은 로지스틱 기대승률식(400·밑10) | 자체적인 대결 확률 모형 없음 | BT를 순위로 확장 |
| 추정 방식 | 모은 데이터로 우도 최대화 | 보통 경기마다 온라인 갱신 | 단순 집계 | 순위 전체의 확률로 추정 |
| 상대 강도 반영 | 예 | 예 | 아니오 | 예 |

모아 둔 비교를 한 번에 맞추려면 BT, 경기가 계속 쌓여 점수를 바로 고쳐야 하면 Elo, 두 개가 아니라 순위 목록을 받는다면 Plackett–Luce가 자연스럽다.

## 어디서 왜 중요한가
- **점추정 순위표의 불확실성**: BT 점수는 추정값이라 비교 횟수가 적은 대상일수록 표준오차가 큽니다. 점수 차가 작은 상위권은 데이터가 조금만 바뀌어도 뒤집힐 수 있어, 의사결정에는 표준오차나 구간을 함께 봐야 합니다.
- **AI 모델 순위표**: 두 모델 응답 중 선호 투표를 모아 모델별 강도를 추정하는 데 쓰이며, 위 불확실성 문제가 그대로 적용됩니다.
- **RLHF 보상 모델 학습**: 일부 쌍대 선호 기반 보상 모델은 BT 형태의 손실로 '선호된 응답이 더 높은 점수를 받을 확률'을 학습합니다.
- **일정 강도 보정**: 단순 승률과 달리 누구를 상대했는지 반영한 승률표를 만들어 시딩·매치메이킹에 활용됩니다.
- **연결성 진단**: 서로 한 번도 비교되지 않은 그룹이 있으면 강도는 그룹 안에서만 정해져, 그룹 간 순위는 의미가 없습니다.

## 자주 하는 오해
- ❌ 오해: 점수 숫자 자체가 실력을 나타낸다 → ✅ 실제: 양의 강도 p에서는 비율(10:5면 승률 약 67%)이, 로그 강도 β에서는 차이가 의미 있으며, 절대값은 정규화 기준에 따라 달라진다.
- ❌ 오해: 비교 데이터만 있으면 항상 점수가 나온다 → ✅ 실제: 비교망이 끊기면 그룹 간 비교가 불가능하고, 연결돼 있어도 어떤 대상이 모든 비교에서 이기기만(지기만) 하면 우도 최대화 점수가 무한대로 발산한다. 이럴 때 정규화나 사전분포(예: 가우시안 사전분포의 MAP)로 안정화한다.
- ❌ 오해: 점수가 높은 쪽이 반드시 이긴다 → ✅ 실제: 강도 3:1이어도 약한 쪽이 25% 확률로 이긴다고 보는 확률 모델이며, 비교에 잡음이 있다는 전제 위에 서 있다.

## 대화에서는 이렇게
- "보상 모델 **BT 손실** 기준 검증 손실은 줄었는데 홀드아웃 쌍의 **선호 예측 정확도**는 그대로예요. 리포트에 둘 다 따로 적을게요."
- "리더보드 올리기 전에 신규 모델 3개가 기존 모델들과 **공유 비교 경로**로 연결돼 있는지부터 확인해 주세요."
- "1, 2위 **BT 점수** 차이가 표준오차 안이라 공동 1위로 표기하자는 의견입니다."
- "전승한 모델 하나 때문에 MLE가 발산해서 **가우시안 사전분포** 넣고 MAP로 다시 돌렸어요."
- "평가를 쌍대 비교로 바꿨다고 **라벨러 편향**이 사라지진 않아요. 긴 답변만 고르는 경향은 여전히 남을 수 있어요."

## 함께 읽으면 좋은 용어
- (기초) **로지스틱 회귀** — BT 승률을 '로그 강도 차이의 로지스틱 함수'로 읽는 법을 배우면 β 점수 해석이 쉬워진다.
- (기초) **최대우도추정** — 점수를 구하는 원리로, 전승 대상에서 생기는 분리 문제와 정규화가 왜 필요한지 다음으로 배울 포인트.
- (유사) **Elo 레이팅** — 같은 기대승률식을 경기마다 갱신하는 방식이라, 일괄 추정과 온라인 갱신의 트레이드오프를 비교하기 좋다.
- (유사) **서스톤 모형** — 같은 쌍대 비교를 정규분포 기반으로 모델링해, 로지스틱과 프로빗 링크 함수 차이를 배울 수 있다.
- (심화) **Plackett–Luce 모델** — 두 개가 아니라 순위 목록 데이터를 다룰 때 BT를 어떻게 확장하는지 보여 준다.
- (심화) **RLHF** — BT 형태 손실로 학습한 보상 모델이 언어 모델 정렬에 어떻게 쓰이는지 이어서 볼 수 있다.

## body_advanced_en

## Technical Definition & How It Works
The **Bradley–Terry (BT) model** is a parametric model for binary paired comparisons. Each item i carries a positive strength p_i, or equivalently a log-strength β_i = ln p_i. Outcomes are independent Bernoulli trials with P(i beats j) = p_i / (p_i + p_j) = σ(β_i − β_j), where σ is the logistic function. Inference runs in reverse: observed outcomes go in, and the strength vector comes out through maximum likelihood (MLE) or, with a prior, maximum a posteriori (MAP) estimation.

The data path from raw comparisons to predictions has five stages:

- **Comparisons → counts**: each record (winner, loser) increments w_ij, the number of times i beat j. The sufficient statistics are the win totals W_i = Σ_j w_ij and the pair totals n_ij = w_ij + w_ji. Comparison order and timing are discarded, which is why a fitted BT score cannot track drift.
- **Counts → log-likelihood**: ℓ(β) = Σ_ij w_ij [β_i − ln(e^{β_i} + e^{β_j})]. This function is concave in β, but only up to translation, because adding a constant c to every β_i leaves every probability unchanged.
- **Estimator**: setting the gradient to zero gives the moment condition that observed wins equal expected wins for every item. There is no closed form. Zermelo's fixed-point iteration, later framed as an MM (minorization–maximization) algorithm, raises the likelihood on every sweep. Newton or IRLS methods treat the problem as logistic regression on a difference design matrix.
- **Normalization**: after each sweep, divide p by its geometric mean so that Σβ_i = 0. Some tools instead fix a reference item, and ConQuest-style output constrains location parameters to a mean of zero, in logits.
- **Prediction**: plug the fitted β into σ(β_i − β_j) for any pair, including pairs that never met. Residuals r_ij = Y_ij − P̂_ij give per-comparison prediction errors.

The algorithm in steps:

- Validate the count matrix: square, non-negative, zero diagonal.
- Check that the comparison graph is connected enough for the chosen estimator.
- Initialize β = 0.
- Apply the update p_i ← W_i / Σ_j n_ij/(p_i + p_j) for every item.
- Re-center the scores.
- Stop when the maximum change in β falls below a tolerance.

Each sweep costs O(|E|), where E is the set of compared pairs, or O(n²) with a dense matrix. A Newton step costs O(n³) for the linear solve. Convergence can be fast in well-connected data: one 16-team, 2,123-game tutorial fit converged in 4 iterations. The original model ships no benchmark suite. Its quality is judged by held-out predictive fit.

## Formulas, Architecture, and Diagrams
**Likelihood and score equations.** Let w_ij be the number of times i beat j, n_ij = w_ij + w_ji the number of meetings, and W_i = Σ_j w_ij the wins of item i.

$$\ell(\beta)=\sum_{i,j} w_{ij}\left[\beta_i-\ln\left(e^{\beta_i}+e^{\beta_j}\right)\right]$$

Differentiate with respect to β_i, where P_ij = σ(β_i − β_j):

$$\frac{\partial \ell}{\partial \beta_i}=W_i-\sum_j n_{ij}P_{ij}=0$$

Rewriting in p-space gives Zermelo's fixed point:

$$p_i=\frac{W_i}{\sum_j n_{ij}/(p_i+p_j)}$$

**Normalization constraint.** Summing the gradient over all i gives exactly zero, because each pair contributes n_ij(P_ij + P_ji) = n_ij. The likelihood is therefore flat along the all-ones direction. To pin it, impose:

$$\prod_i p_i = 1 \iff \sum_i \beta_i = 0$$

**Logit and Elo forms.** Two equivalent ways to write the same model:

- logit P(i>j) = β_i − β_j
- Elo uses base 10 and scale 400: P = 1/(1+10^{(R_j−R_i)/400}), so a 400-point gap gives 1/(1+0.1) ≈ 0.909.

**Finite MLE vs Gaussian-prior MAP.**

- **Unregularized MLE**: a finite maximizer exists and is unique after normalization only if the directed win graph is strongly connected. That means every item reaches every other item along "beat" edges, so no subset of items wins or loses all of its comparisons against the rest. If one item is undefeated, its β_i diverges to +∞. If the graph splits into components, scores are identified only within each component.
- **Gaussian-prior MAP**: add the penalty −Σβ_i²/(2σ²). The objective becomes strongly convex, so the MAP exists and is unique for any data, even disconnected or separated data. For the generalized BT family, this MAP is also proven to be monotone in comparisons and Lipschitz-resilient to any single new comparison. These guarantees belong to the MAP, not to the raw MLE. Summing the MAP gradient also forces Σβ_i = 0 automatically.

**Numerical check (one MM sweep).** Three items with counts w_AB=3, w_BA=1, w_AC=2, w_CA=1, w_BC=3, w_CB=1. This gives W = (5, 4, 2) and n_AB=4, n_AC=3, n_BC=4. The graph is strongly connected.

- Start from p = (1, 1, 1).
- Raw update: p'_A = 5/(2+1.5) = 1.429, p'_B = 4/(2+2) = 1.000, p'_C = 2/(1.5+2) = 0.571.
- Geometric mean = 0.935, so the normalized p = (1.529, 1.070, 0.611).
- Predicted P(A>C) = 1.529/2.140 ≈ 0.714, compared with an observed 2/3. Later sweeps keep moving toward the point where observed wins equal expected wins.

## Code or Pseudocode
```python
import numpy as np
from collections import deque

def _reaches_all(adj: np.ndarray) -> bool:
    seen, q = {0}, deque([0])
    while q:
        for v in np.nonzero(adj[q.popleft()])[0]:
            if v not in seen:
                seen.add(v); q.append(v)
    return len(seen) == len(adj)

def strongly_connected(w: np.ndarray) -> bool:
    # Finite-MLE condition: every item reaches every other via 'beat' edges.
    # Weaker than this (only undirected connectivity) is NOT enough for a finite MLE.
    return _reaches_all(w > 0) and _reaches_all(w.T > 0)

def fit_bt(w, prior_var: float | None = None, tol: float = 1e-10, max_iter: int = 10_000):
    w = np.asarray(w, dtype=float)
    if w.ndim != 2 or w.shape[0] != w.shape[1] or (w < 0).any() or np.diag(w).any():
        raise ValueError("w must be square, non-negative, zero diagonal")
    n_ij, wins, beta = w + w.T, w.sum(1), np.zeros(len(w))
    if prior_var is None and not strongly_connected(w):
        raise ValueError("no finite MLE: split components or set prior_var (MAP)")
    step = np.inf
    for it in range(1, max_iter + 1):
        if prior_var is None:  # Zermelo / MM fixed point on the MLE
            p = np.exp(beta)
            new = np.log(wins / (n_ij / (p[:, None] + p[None, :])).sum(1))
            new -= new.mean()  # geometric-mean normalization: sum(beta) = 0
        else:  # Newton step on strongly convex Gaussian-prior MAP
            P = 1 / (1 + np.exp(beta[None, :] - beta[:, None]))
            grad = wins - (n_ij * P).sum(1) - beta / prior_var
            M = n_ij * P * P.T
            H = np.diag(M.sum(1)) - M + np.eye(len(w)) / prior_var
            new = beta + np.linalg.solve(H, grad)
        step, beta = np.abs(new - beta).max(), new
        if step < tol:
            return beta, {"converged": True, "iters": it, "max_step": step}
    return beta, {"converged": False, "iters": max_iter, "max_step": step}

def pair_probs(beta: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(beta[None, :] - beta[:, None]))  # P[i, j] = P(i beats j)

# --- tests ---
w = np.array([[0, 3, 2], [1, 0, 3], [1, 1, 0]])
beta, info = fit_bt(w)
assert info["converged"] and abs(beta.sum()) < 1e-9
assert np.allclose(((w + w.T) * pair_probs(beta)).sum(1), w.sum(1))  # observed = expected wins

undefeated = np.array([[0, 2], [0, 0]])  # item 0 never lost -> MLE diverges
try:
    fit_bt(undefeated); raise AssertionError("should have rejected")
except ValueError:
    pass
b_map, info_map = fit_bt(undefeated, prior_var=1.0)
assert info_map["converged"] and np.isfinite(b_map).all() and abs(b_map.sum()) < 1e-9
```

## Production Pitfalls
- ❌ Mistake: Checking only undirected connectivity, then running unregularized MLE on data where one item never lost a comparison → ✅ Fix: Test strong connectivity of the directed win graph before fitting, and fall back to Gaussian-prior MAP or report per-component scores when the test fails.
- ❌ Mistake: Treating an MM run that hit max_iter, with β growing steadily, as a converged fit and publishing those scores → ✅ Fix: Log the convergence flag, iteration count, and final max step for every fit, and fail the job when the run did not converge instead of silently shipping divergent scores.
- ❌ Mistake: Comparing raw β values across two separately fitted batches or label vendors as if they shared one origin → ✅ Fix: Apply the same normalization (Σβ = 0 or a fixed anchor item) and compare only score differences or predicted pair probabilities, never absolute values across fits.
- ❌ Mistake: Validating a fit only by in-sample accuracy, never testing held-out predictive performance against a simple baseline → ✅ Fix: Hold out 10–20% of comparisons and compare held-out log-loss against a constant 0.5 and a win-rate baseline. Inspect residuals Y − P̂ by rater and by pair. If BT does not beat the baselines, look for intransitive cycles, rater heterogeneity, or missing covariates before trusting the ranking.

## Tradeoffs — When to Use What
**Suitable:**

- **Binary or forced-choice preference labels over many items.** The model needs only win and pair counts, and each MM sweep is O(|E|), so sparse comparison designs stay cheap.
- **Predicting unobserved matchups.** σ(β_i − β_j) gives a calibrated probability for any pair once the graph is connected, which a raw win-rate table cannot do.
- **Scoring under unbalanced schedules.** The score equations weight each win by the opponent's strength, so items that faced different opponents become comparable.
- **Uncertainty is required.** Standard errors come from the inverse Fisher information, which is the logistic-regression Hessian, at no extra modelling cost.

**Unsuitable:**

- **Labels are full or partial rankings of k > 2 items.** Exploding rankings into pairs throws away dependency structure. Use **Plackett–Luce**, which reduces to BT for k = 2.
- **Comparisons are graded, continuous, or include ties.** The binary likelihood cannot use margin information. Use the **generalized Bradley–Terry** (GBT) family, which covers discrete and continuous comparison domains, or a ties extension such as Davidson's.
- **Strength drifts and ratings must update online after every match.** A static BT fit discards ordering. Use **Elo** for incremental updates, or **Glicko/TrueSkill** when you need rating uncertainty that evolves over time.
- **Noise is believed to be Gaussian on a latent utility.** The **Thurstone** model replaces the logistic link with a probit. Predictions are usually close, but its assumptions are explicit about that noise.

**Limitations.** Separate the model's mathematical properties from what has been empirically validated.

- **Model properties (follow from the math):**
  - One scalar per item forces transitive, cycle-free odds, so it cannot represent A > B > C > A preferences.
  - Scores are identified only up to an additive constant in β.
  - The MLE is infinite when one item wins or loses all of its comparisons.
  - No covariates such as home advantage or rater identity are included unless the model is extended.
- **Proven guarantees, not empirical claims:** strict convexity of the GBT negative log-likelihood, plus Gaussian-prior MAP existence, uniqueness, monotonicity, and Lipschitz resilience.
- **Empirical fit:** whether BT predicts a given dataset well is not guaranteed. It must be checked on held-out comparisons for every deployment.

## Industry Communication
The following are hypothetical communication examples for illustration:

- "PR review: `fit_bt` raised **no finite MLE** on the March batch because item 412 is undefeated across 37 comparisons. I'd rather switch this path to **Gaussian-prior MAP with σ² = 1** than drop the item."
- "Design doc: we normalize to **Σβ = 0** after every MM sweep and report **pair probabilities**, not raw β. Downstream dashboards must not compare β across weekly refits."
- "Incident postmortem: the leaderboard swap was caused by two annotator pools that never shared prompts. The **directed comparison graph had 2 strongly connected components**, so cross-pool ordering was unidentified, and we now block publishing when that check fails."
- "Architecture review: the rating feature needs per-match updates with uncertainty, so a static **BT refit** is the wrong tool. Proposing an **Elo** service for live updates and a nightly **BT MAP** fit as the audited reference."
- "Eval note: on the 15% held-out split, **BT log-loss is 0.61 vs 0.69 for the constant-0.5 baseline**. Residuals concentrate in one rater group, so we'll test a rater-effect extension before rollout."
- "Review comment: these labels are 4-way rankings, and exploding them into 6 pairs each double-counts dependence. **Plackett–Luce** is the correct likelihood here."
- "Postmortem follow-up: the MM job reported **converged=False after 10,000 iterations** while the max step kept shrinking only slowly. We'll alert on the convergence flag instead of trusting the last iterate."

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Logistic regression** — BT is logistic regression with no intercept on a difference design matrix (+1 for i, −1 for j). Knowing its likelihood, IRLS fitting, and separation failure explains both the Newton path and why the MLE can diverge.
- (prerequisite) **Maximum likelihood estimation** — BT scores are the solution to the score equations where observed wins equal expected wins. Without MLE concepts such as concavity, flat directions, and existence conditions, the normalization step and the strong-connectivity requirement look arbitrary.
- (alternative) **Thurstone model** — Solves the same paired-comparison problem with Gaussian latent noise, giving a probit link instead of a logistic one. It is the relevant competitor when the noise assumption, rather than tractability, should drive the model choice.
- (extension) **Plackett–Luce model** — Generalizes BT from pairs to full rankings via sequential choice probabilities and reduces exactly to BT for two items. It is needed when labels arrive as k-way orderings.
- (extension) **Generalized Bradley–Terry (GBT) models** — An exponential-family generalization covering both discrete and continuous comparison values. Its negative log-likelihood is strictly convex, and with a Gaussian prior the MAP exists, is unique, is monotone in comparisons, and is Lipschitz-resilient. These are MAP guarantees, not a claim that unregularized scores are uniquely identified.
- (extension) **Elo rating system** — Applies the same logistic pairwise probability with base 10 and scale 400, but updates ratings incrementally per match instead of fitting all comparisons jointly. It suits non-stationary, streaming settings.

## body_advanced_ko

## 기술적 정의와 동작 원리
**Bradley–Terry(BT) 모형**은 n개 대상 각각에 잠재 파라미터 $$\beta_i \in \mathbb{R}$$ (또는 $$p_i = e^{\beta_i} > 0$$)를 두고, 쌍 비교 결과를 독립 베르누이 시행으로 보는 모형이다. 성공 확률은 $$\Pr(i>j)=\sigma(\beta_i-\beta_j)$$로 둔다. 따라서 이 모형은 비교 차분 design matrix 위의 **로지스틱 회귀**와 같은 구조다. 다만 함수 형태는 고정되어 있고, 추정 대상은 파라미터다. 확률은 $$\beta$$에 같은 상수를 더해도 변하지 않으므로, 평균 0이나 기하평균 1 같은 **정규화 제약**을 걸어야 해가 식별된다.

**데이터 흐름**: 원시 비교 로그 (i, j, winner) → 승리 행렬 $$W$$ ($$w_{ij}$$ = i가 j를 이긴 횟수) → 비교 그래프 연결성 진단 → 반복 추정 → 정규화된 $$\hat\beta$$ → 미관측 쌍의 승률 행렬 $$P_{ij}$$ 산출.

**추정 단계** (고전 MLE, Zermelo/MM 반복):
- 양의 초기값 $$p^{(0)}$$에서 시작한다.
- 각 i에 대해 $$p_i' = \sum_j w_{ij} \big/ \sum_j (w_{ij}+w_{ji})/(p_i+p_j)$$를 계산한다.
- 기하평균으로 나눠 정규화한다. 이렇게 하면 $$\beta$$의 평균이 0이 된다.
- 이 반복은 매 회 log-likelihood를 개선하며, 유일한 최대값으로 수렴한다고 알려져 있다. 단, 이 결론은 데이터가 충분히 연결되어 있을 때의 이야기다.
- 한 반복의 비용은 관측된 쌍의 수 m에 대해 O(m)이고, 밀집 행렬이면 O(n²)이다.

**held-out 평가**: 학습 우도만 보면 과적합 여부를 판단할 수 없으므로 비교 기록 단위로 분할한다.
- 시간에 따라 강도가 변하는 데이터라면 시간 기준 분할을 쓴다.
- 테스트에 나오는 모든 대상은 학습 그래프의 같은 연결 성분에 속해야 한다. 그렇지 않으면 테스트 확률이 정의되지 않는다.
- 지표는 확률 예측을 직접 평가하는 **held-out log loss**(테스트 NLL/비교 수)와 **Brier score**를 권한다. 잔차 $$r_{ij}=Y_{ij}-P_{ij}$$는 쌍별 진단에 쓴다.
- log loss를 기본으로 추천하는 근거는 두 가지다. 학습 목적함수와 같은 척도라 비교가 일관되고, 과신(overconfidence)에 큰 벌점을 준다.
- 정확도(승자 맞히기)는 calibration을 무시하므로 보조 지표로만 쓴다.

## 핵심 수식·아키텍처·도표
**Log-likelihood와 gradient**

$$\ell(\beta)=\sum_{i,j} w_{ij}\,\log\sigma(\beta_i-\beta_j),\qquad \frac{\partial \ell}{\partial \beta_i}=\sum_j w_{ij}-\sum_j N_{ij}P_{ij}$$

- $$N_{ij}=w_{ij}+w_{ji}$$: 쌍별 총 비교 수
- $$P_{ij}=\sigma(\beta_i-\beta_j)$$: 모형이 예측한 i의 승률
- 해에서는 gradient가 0이 된다. 즉 "실제 승수 = 기대 승수"가 모든 대상에서 성립한다. 이 값의 노름이 수렴 진단 지표다.

**MM 갱신식** (고정점 형태)

$$p_i \leftarrow \frac{\sum_j w_{ij}}{\sum_j N_{ij}/(p_i+p_j)},\qquad p_i \leftarrow \frac{p_i}{(\prod_k p_k)^{1/n}}$$

**Elo 척도 변환**

$$\Pr(i>j)=\frac{1}{1+10^{(R_j-R_i)/400}}$$

**수치 예**: $$\beta_i-\beta_j=1$$이면 $$P_{ij}=1/(1+e^{-1})\approx 0.731$$이다.
- i가 실제로 이겼다면 log loss는 $$-\ln 0.731\approx 0.313$$, Brier는 $$(1-0.731)^2\approx 0.072$$다.
- i가 졌다면 log loss는 $$-\ln 0.269\approx 1.313$$으로, 약 4배의 벌점을 받는다.

**추정 방식 비교** (제공 자료로 확인된 범위)

| 방식 | 관측 형식 | prior | 식별성 | 추정 보장 |
|---|---|---|---|---|
| 고전 BT MLE | 이진 승패 | 없음 | 전체 배수(β의 평행이동) 미정 → 정규화 필요, 분리된 클러스터 간 비교 불가 | 단일 최대값, MM 반복이 매 회 우도 개선 |
| GBT MAP | 이진·이산·연속(K-nary, Gaussian, Uniform, Poisson 인스턴스) | 점수에 Gaussian prior | prior가 위치를 고정 | negative log-posterior 강볼록 → 존재·유일·빠른 계산, 비교에 대한 단조성, 신규 비교 1건에 대한 Lipschitz-resilience |
| Elo | 이진 승패 | 없음 | 밑 10·척도 400 관례 | BT와 동일한 확률식, 갱신 보장은 검증된 정보 부족 |
| Plackett–Luce | 전체 순위 | 없음 | BT와 같은 배수 미정 | 2개 순위에서 BT로 환원, 추정 보장은 검증된 정보 부족 |

## 코드 또는 의사코드
```python
import warnings
import numpy as np

def fit_bt_mm(W: np.ndarray, max_iter: int = 2000, tol: float = 1e-10) -> dict:
    """고전 BT MLE (Zermelo/MM). W[i, j] = i가 j를 이긴 횟수.
    반환 beta는 평균 0 (기하평균 1 정규화와 동치)."""
    W = np.asarray(W, dtype=float)
    n = W.shape[0]
    # 입력 계약: 정방 n×n, n>=2, 유한·비음수, 대각선 0
    if W.ndim != 2 or W.shape[1] != n or n < 2:
        raise ValueError("W must be square n x n with n >= 2")
    if not np.isfinite(W).all() or (W < 0).any() or np.diag(W).any():
        raise ValueError("entries must be finite, >= 0, with zero diagonal")
    N = W + W.T
    wins = W.sum(axis=1)
    # 부분 실패 탐지: MLE 존재의 정확한 조건을 검사하는 것이 아님
    reach = np.eye(n, dtype=bool)[0]
    for _ in range(n):
        reach |= N[reach].sum(axis=0) > 0
    if not reach.all():
        raise ValueError("comparison graph disconnected: scores not comparable")
    if (wins == 0).any() or (wins == N.sum(axis=1)).any():
        raise ValueError("item with 0 wins or 0 losses: beta diverges to +-inf")

    p, step, it = np.ones(n), np.inf, 0
    for it in range(1, max_iter + 1):
        denom = (N / (p[:, None] + p[None, :])).sum(axis=1)
        p_new = wins / denom                       # MM 갱신
        p_new /= np.exp(np.log(p_new).mean())      # 기하평균 1 -> beta 평균 0
        step = np.abs(np.log(p_new) - np.log(p)).max()
        p = p_new
        if step < tol:
            break

    beta = np.log(p)
    P = 1.0 / (1.0 + np.exp(beta[None, :] - beta[:, None]))  # P[i,j]=Pr(i>j)
    loglik = float((W * np.log(P)).sum())
    grad = wins - (N * P).sum(axis=1)               # dl/dbeta_i, 해에서 0
    converged = step < tol
    if not converged:
        warnings.warn(f"max_iter={max_iter} reached, last step={step:.2e}")
    return {"beta": beta, "converged": converged, "iterations": it,
            "loglik": loglik, "grad_norm": float(np.linalg.norm(grad))}

# 최소 테스트: 정상 케이스 + 실패 경로 2개
r = fit_bt_mm(np.array([[0, 3, 1], [1, 0, 2], [2, 1, 0]]))
assert r["converged"] and abs(r["beta"].mean()) < 1e-9 and r["grad_norm"] < 1e-6
for bad in ([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],  # 분리된 클러스터
            [[0, 2], [0, 0]]):                                       # 전패 대상
    try:
        fit_bt_mm(np.array(bad)); raise AssertionError("should fail")
    except ValueError:
        pass
```

연결성 검사와 전승·전패 검사는 발산을 일으키는 흔한 경우를 잡아내는 **부분 탐지**일 뿐이다. MLE 존재를 보장하는 정확한 필요충분조건은 제공 자료 범위에서 검증된 정보가 부족하다. 그래서 두 검사를 통과해도 `converged`와 `grad_norm`을 반드시 함께 확인해야 한다.

## 프로덕션 함정
- ❌ 실수: 전승이나 전패 대상이 있는 상태로 MLE를 돌려 β가 수십까지 커지는데도 반복 상한에서 멈춘 값을 그대로 배포했다 → ✅ 해결: 학습 전에 전승·전패 대상을 탐지하고, Gaussian prior를 둔 MAP으로 전환하며, 결과에 converged 플래그와 gradient norm을 함께 기록한다.
- ❌ 실수: 두 라벨러 풀이 서로 다른 샘플만 비교했는데 하나의 β 테이블로 합쳐 클러스터 간 순위를 발표했다 → ✅ 해결: 비교 그래프의 연결 성분을 먼저 계산하고, 성분이 둘 이상이면 성분별로 따로 보고하거나 교차 비교 쌍을 추가로 수집한다.
- ❌ 실수: 모델 버전마다 정규화 기준을 다르게 써서 β 절대값의 변화를 성능 변화로 해석했다 → ✅ 해결: 평균 0 제약을 고정하거나 기준 대상(anchor)을 두고, 버전 간 비교는 승률 차이나 held-out log loss로만 수행한다.
- ❌ 실수: 무작위 분할로 테스트셋을 만들었더니 학습에 등장하지 않은 대상이 포함되어 평가 지표가 정의되지 않거나 왜곡됐다 → ✅ 해결: 테스트 대상이 학습 연결 성분에 속하는지 검증하고, 강도가 변하는 데이터에는 시간 기준 분할과 log loss·Brier를 함께 쓴다.

## 트레이드오프와 언제 무엇을 쓰나
**이럴 때 적합**
- 결과가 이진 승패나 선호이고 비교 그래프가 연결되어 있을 때: 반복당 O(m) 비용의 MM으로 수렴이 빠르고 해가 유일하다.
- 일정 강도가 불균형한 리그·투표에서 단순 승률을 보정해야 할 때: 상대 강도가 우도에 직접 반영된다.
- 미관측 쌍의 승률이 필요할 때 (시드 배정, 매칭): 추정된 β만으로 전체 $$P$$ 행렬이 닫힌 형태로 나온다.
- 확률 해석과 calibration 평가가 필요할 때: held-out log loss로 모형을 바로 비교할 수 있다.

**이럴 때 부적합**
- 비교가 점수 차나 연속 강도로 들어올 때: 이진화하면 정보를 잃는다. 대안은 **GBT** (Gaussian·Poisson 인스턴스)다.
- 표본이 희소하고 오클릭 같은 이상치가 섞인 온라인 수집일 때: MLE는 전승 대상에서 발산한다. 대안은 Gaussian prior를 쓰는 **GBT MAP**으로, 신규 비교 1건의 영향이 제한된다.
- 한 번에 여러 후보의 전체 순위를 받을 때: 쌍으로 쪼개면 비교 간 독립 가정이 깨진다. 대안은 **Plackett–Luce**다.
- 동점이 잦을 때: 기본 BT에는 동점 결과가 없다. 대안은 **Davidson 동점 확장 모형**이다.
- 강도가 경기마다 변해 온라인 갱신과 불확실성 추적이 필요할 때: 대안은 **Glicko·TrueSkill**이다.

## 업계 대화 맥락
- "이번 PR은 **BT fit**이 **max_iter 2000**에 도달해도 예외 없이 결과를 저장하던 경로를 수정합니다. 이제 **converged=False**면 경고를 남기고 리더보드 갱신을 차단합니다."
- "설계 문서 기준으로 **β는 평균 0 정규화**를 계약으로 고정합니다. 다운스트림은 절대값이 아니라 **β 차이와 승률**만 소비해야 합니다."
- "포스트모템: 3월 배치에서 신규 후보 1개가 **전승 12/12**를 기록해 **β=+14**로 발산했고, 그 결과 상위 순위 전체가 밀렸습니다. 재발 방지책으로 **Gaussian prior MAP**을 기본값으로 바꿉니다."
- "평가 지표는 **held-out log loss**를 primary로, **Brier**를 secondary로 둡니다. 승자 정확도는 calibration을 보지 못하므로 대시보드 참고값으로만 둡니다."
- "리뷰 코멘트: 분할 직후 **연결 성분 검사**가 빠져 있습니다. 테스트 쌍 중 **4%가 학습 그래프 밖** 대상이라 확률이 정의되지 않습니다."
- "동점 응답이 **전체의 18%**라 현재처럼 동점을 버리면 편향이 생깁니다. 다음 분기에 **Davidson 동점 확장**을 비교 실험하겠습니다."
- "순위 응답을 쌍으로 쪼개 넣던 파이프라인은 비교 간 **독립 가정**을 깹니다. 이번 마이그레이션에서 **Plackett–Luce** 우도로 교체합니다."

## 선행·대안·확장 개념
- (선행) **최대우도추정** — 고전 BT의 추정 원리다. Zermelo가 보인 단일 최대값과 MM 반복의 단조 개선은 이 MLE 문제에 대한 결과이며, prior 없이 데이터만으로 결정되므로 연결성과 전승·전패 상황에 민감하다.
- (선행) **로지스틱 회귀** — BT 우도는 비교 차분 design matrix 위의 로지스틱 회귀와 같은 구조다. gradient·Hessian과 log loss 평가를 이 관점으로 그대로 해석할 수 있다.
- (대안) **서스톤 모형** — 같은 쌍 비교 문제를 잠재 점수 위의 정규분포 잡음 가정으로 푼다. 링크 함수 선택이 tail 확률과 calibration에 영향을 주므로 가정 비교 대상이 된다.
- (확장) **Generalized Bradley–Terry (GBT) MAP** — 지수족 기반으로 이산·연속 비교를 수용하고, 점수에 Gaussian prior를 둔 MAP 추정이다. 존재·유일성, 비교에 대한 단조성, 신규 비교 1건에 대한 Lipschitz-resilience는 이 MAP에 대해 증명된 성질이며 고전 MLE에는 그대로 적용되지 않는다.
- (확장) **Plackett–Luce 모델** — 2개 쌍이 아니라 전체 순위의 우도를 정의하는 일반화다. 순위가 두 항목일 때 BT로 환원되며, 순위 데이터를 쌍으로 분해할 때 생기는 독립성 위반을 피한다.
- (확장) **Davidson 동점 모형** — BT 계열에 동점 결과 확률을 추가한 확장이다. 동점이 빈번한 비교 데이터에서 동점을 버리거나 승패로 강제 변환할 때 생기는 편향을 줄인다.

## references_en

- {"title": "Modelling Pairwise Comparisons using the Bradley-Terry-Luce (BTL) Model", "authors": "Alvin Vista, Ray Adams, Dan Cloney", "year": 2020, "type": "docs", "url": "https://www.acer.org/files/Tutorial-13--Pairwise-comparisons.pdf", "tier": "primary", "annotation": "Worked fit on 2,123 AFL games with logit-scale strengths, standard errors, and per-game residuals."}
- {"title": "Diagnostic Framework for the Bradley–Terry Model", "authors": "W. Wu", "year": 2022, "venue": "Journal of the Royal Statistical Society Series A", "type": "paper", "url": "https://academic.oup.com/jrsssa/article/185/Supplement_2/S461/7069516", "tier": "primary", "annotation": "How to check whether a fitted BT model actually matches your comparison data."}
- {"title": "Generalized Bradley-Terry Models for Score Estimation from Paired Comparisons", "authors": "Fageot, Farhadkhani, Hoang, Villemaud", "year": 2023, "venue": "arXiv", "type": "paper", "url": "https://arxiv.org/html/2308.08644", "tier": "primary", "annotation": "Extends BT to graded comparisons; proves convexity, monotonicity, and bounded impact of one comparison; Tournesol use."}
- {"title": "Bradley-Terry Pairwise Ranking Calculator", "type": "docs", "url": "https://metricgate.com/docs/bradley-terry-pairwise-ranking", "tier": "secondary", "annotation": "Practical notes on strength-of-schedule adjustment, MM fitting, and connectivity diagnostics."}
- {"title": "Bradley–Terry model", "type": "wiki", "url": "https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model", "tier": "secondary", "annotation": "Compact overview of parameterizations, Elo equivalence, Plackett–Luce, and Zermelo's iterative fitting."}
