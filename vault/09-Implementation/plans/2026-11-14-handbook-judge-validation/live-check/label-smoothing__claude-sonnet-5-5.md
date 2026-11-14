# Label Smoothing — claude-sonnet-5-5

- advanced 81 / basic 79 / gate pass / penalty 0 / $1.673 / 390s

## definition_en

Label smoothing is a regularization technique that linearly mixes one-hot target labels with a uniform distribution over classes, assigning a small probability mass to incorrect classes so that the model is no longer pushed toward extremely confident outputs, which reduces overfitting and overconfidence.

## definition_ko

레이블 스무딩은 원-핫 정답 레이블을 균등 분포와 선형 결합해 오답 클래스에도 약간의 확률을 나눠 주는 정규화 기법으로, 모델이 정답 클래스에 극단적으로 높은 확률을 내도록 몰아가는 압력을 줄여 과적합과 과신을 완화한다.

## summary_en

Label smoothing is a small change to how a classifier is graded during training. Instead of saying 'this photo is 100% a cat and 0% everything else', the answer key says something like '90% cat, with the remaining 10% spread over the other classes'. You can picture a teacher who never gives a student full marks for being completely sure, so the student stays a little humble. Because the model is not pushed to be extremely certain, it tends to overfit less and report more realistic confidence. The catch is that the same humility can make it harder to tell which predictions are likely wrong.

## summary_ko

레이블 스무딩은 모델에게 '정답은 100%, 나머지는 0%'라고 가르치는 대신 '정답은 90% 정도, 나머지는 조금씩'이라고 알려주는 방법이다. 시험 문제의 정답을 너무 확신하는 학생이 오히려 새로운 유형에서 크게 틀리는 것과 비슷한 상황을 막아준다. 훈련 정답 값을 살짝 부드럽게 바꿔서 모델이 지나치게 자신만만해지는 것을 줄인다. 구현이 간단해서 이미지 분류와 번역 모델 등 여러 훈련 레시피에 쓰인다. 다만 모델이 틀릴 때와 맞을 때의 자신감 차이가 흐려질 수 있다.

## body_basic_en

## Plain Explanation
Standard classifiers are trained against "hard" answer keys: the correct class gets probability 1 and every other class gets 0. To match that exactly, the network must push the score (logit) of the right class far above all the others, and the loss keeps rewarding it for going further. The result is a model that can become overconfident, announcing near-certainty even when it is wrong, and that can overfit its training set.

Label smoothing softens the answer key. Think of a quiz where the top mark is 90 out of 100 instead of 100: a student can still clearly do well, but there is no reward for claiming perfect certainty. Concretely, you pick a small number called epsilon (often written α in papers), keep (1 − epsilon) of the probability on the true class, and share epsilon evenly across the classes. With 10 classes and epsilon = 0.1, a one-hot target of 1 for the correct class becomes about 0.91 for it and 0.01 for each of the other nine.

The mechanism is simple: the loss is still cross-entropy, but its best achievable output is now 'high, not extreme'. The network gets no extra reward for pushing the correct-class logit toward infinity, so the gap between logits stays bounded. Because only the target values change, it needs no new layers and adds no training time, and in practice it is a one-line change to the loss function.

## Examples & Analogies
- **E-commerce product tagger**: A team classifies product photos into a few hundred categories, and many items are borderline (is a tote bag 'handbag' or 'travel accessory'?). They add label smoothing and try epsilon values such as 0.05, 0.1 and 0.2, picking the one with the best validation accuracy and calibration, because the borderline items otherwise drag the model into confident mistakes.
- **Machine translation training**: Label smoothing appears in the original Transformer training recipe. In a survey table in Chen et al., an English-German Transformer's BLEU score rose from 25.3 without label smoothing to 25.8 with it.
- **Medical triage classifier**: A model sorts scans into 'urgent' and 'routine', and some training labels may be wrong because even doctors disagree on borderline scans. Smoothing the labels stops the model from treating each noisy label as absolute truth, which research on label noise suggests is exactly where label smoothing helps most.

## At a Glance
| | Hard one-hot labels | Label smoothing | Knowledge distillation (soft targets from a teacher) |
|---|---|---|---|
| Where the target comes from | The dataset's annotation | The annotation mixed with a uniform distribution | A trained teacher model's output probabilities |
| What non-target classes get | Exactly 0 | The same small value for every wrong class | Different values per class, reflecting the teacher's view of similarity |
| Extra training cost | None | None, since only the target values change | An extra teacher model must be trained first |
| Tuning knob | None | Epsilon (smoothing strength) | Temperature and teacher choice |

Label smoothing gives every wrong class the same small share for free, whereas distillation hands out different shares learned from a teacher, so it carries more information but costs a whole extra model.

## Where and Why It Matters
- **Image classification recipes**: Xia et al. note that label smoothing appears in many recent training recipes and is particularly popular on the ImageNet-1k benchmark, because it improves test accuracy and is simple to implement.
- **Tight, evenly spaced class clusters**: Müller et al. (2019) found that label smoothing encourages the penultimate-layer representations of each class to form tight clusters that are equally distant from one another, which they link to the better generalization and calibration they observe.
- **Better-calibrated confidence**: Because label smoothing pushes the model to output lower probabilities, and models are typically more confident than they are accurate, it is well explored as a calibration aid.
- **Teacher models for distillation**: Müller et al. report that although label smoothing helps generalization and calibration, it can hurt distillation, because it erases information that a teacher's soft outputs would otherwise pass on.
- **Safety-critical rejection**: On ImageNet with ResNet-50, Xia et al. report that label-smoothed models accept almost no samples at a strict 1% error limit, so teams that need to reject uncertain inputs should read that paper first.

## Common Misconceptions
- ❌ Myth: Label smoothing is a free win, so it should always be on → ✅ Reality: Typical starting values for epsilon are around 0.1. Tune it on validation accuracy and calibration together, since too high a value causes underfitting while too low gives too little regularization.
- ❌ Myth: Label smoothing fixes overconfidence in every sense → ✅ Reality: It lowers output probabilities, but it can make it harder to tell right predictions from wrong ones, so check how you will use the confidence scores.
- ❌ Myth: It changes the network architecture → ✅ Reality: Only the target values (the modified cross-entropy loss) change. No layers are added and training time does not increase.

## How It Sounds in Conversation
- "Let's add **label smoothing** with epsilon 0.1 to the baseline and see if validation accuracy moves before Friday's run."
- "The ablation shows **label smoothing** helped accuracy, but our confidence-threshold rejection got worse. Can we check that before we ship?"
- "If we want to use this model as the teacher for **distillation**, I'd train it without **label smoothing**."
- "Validation loss is flat but the model underfits at epsilon 0.3. Let's drop **epsilon** back to 0.1."
- "Our annotators disagree on about a tenth of these tickets, so **label smoothing** makes sense here to avoid trusting noisy labels."

## Related Reading
- (before) **Cross-Entropy Loss** — The loss that label smoothing modifies; understand how it rewards pushing the correct class toward probability 1 first.
- (before) **Overfitting** — The problem label smoothing is meant to reduce; read it to see why overconfident outputs can signal poor generalization.
- (similar) **Dropout** — Another regularizer, but it acts on hidden activations, whereas label smoothing acts only on the targets.
- (similar) **Knowledge Distillation** — Also trains on soft targets, but learned from a teacher instead of a uniform mix, and it can interact badly with label smoothing.
- (next) **Model Calibration** — Explains how to measure whether a model's confidence matches its accuracy, the main effect label smoothing aims to improve.
- (next) **Selective Classification** — Shows the trade-off where a model abstains when unsure, and why label smoothing can degrade it.

## body_basic_ko

## 쉽게 이해하기
분류 모델은 보통 정답이 [0, 0, 1, 0]처럼 한 칸만 1인 '원-핫' 레이블로 학습한다. 이 목표를 맞추려면 모델은 정답 클래스 점수(logit)를 다른 클래스보다 계속 키워야 하고, 결국 실제 정확도보다 더 자신만만한 확률을 내놓게 된다. 이런 과신은 과적합과 일반화 저하로 이어질 수 있다.

레이블 스무딩은 정답 칸에서 조금 덜어 다른 칸들에 나눠 주는 방식이다. 시험 채점에서 정답에 만점 대신 90점을 주고 나머지 보기에 작은 점수를 나눠 주는 것과 같다. 클래스가 10개이고 α=0.1이면 정답 클래스의 목표는 0.9+0.01=0.91이 되고, 나머지 9개 클래스는 각각 0.01이 된다.

목표가 0.91로 정해지면 출력이 그보다 커져도 손실이 오히려 늘어난다. 그래서 모델은 정답 클래스 logit과 나머지 logit의 격차를 무한정 벌리지 않게 된다. 레이블만 바꾸는 방식이라 네트워크 구조는 그대로이고, 교차 엔트로피 손실을 조금 수정하는 것으로 구현할 수 있다.

## 비유와 예시
- **쇼핑몰 상품 이미지 자동 태깅**: 분류 모델의 확신도가 임계값을 넘으면 태그를 자동으로 붙이는 서비스를 생각해 보자. 레이블 스무딩은 정확도를 높일 수 있지만 확신도 순위가 흐려질 수 있어서, 임계값으로 걸러낼 때 틀린 태그가 섞일 위험을 따로 점검해야 한다.
- **의료·품질 검사에서 사람에게 넘기기**: 모델이 애매하면 의사나 검수자에게 넘기는 시스템에서는 불확실성의 신호가 중요하다. 논문(Xia et al.)에 따르면 레이블 스무딩은 이런 선택적 분류에서 틀린 예측을 걸러내는 능력을 떨어뜨리는 경향이 있다.
- **기계 번역 모델 학습**: 출력 어휘가 수만 개인 번역 모델에서도 정답 단어 하나에만 100%를 주면 과신하기 쉽다. 번역 모델 학습 레시피에 레이블 스무딩이 포함된 사례가 있으며, 트랜스포머 연구에서는 BLEU가 25.3에서 25.8로 올랐다고 정리된 표가 있다(Chen et al. 요약표).

## 한눈에 비교
| | 레이블 스무딩 | 신뢰도 페널티 | 온도 스케일링 |
|---|---|---|---|
| 개입 시점 | 학습 중 (정답 레이블 수정) | 학습 중 (출력 분포에 벌점) | 학습 후 (logit 조정) |
| 재학습 필요 | 필요 | 필요 | 불필요 |
| 바꾸는 대상 | 학습 목표값 | 손실 항 | 출력 확률 보정 |
| 겨냥하는 문제 | 과신, 과적합 | 과신 | 과신 (보정) |

레이블 스무딩은 가장 단순한 정규화 기법 중 하나로 학습 단계에서 과신을 막고, 온도 스케일링 같은 사후 보정은 이미 학습된 모델을 다시 훈련하지 않고도 확률만 다듬는다는 점이 다르다.

## 어디서 왜 중요한가
- **ImageNet 이미지 분류 학습 레시피**: 레이블 스무딩은 ImageNet-1k 분류 학습에서 특히 많이 쓰이며, 여러 최신 학습 레시피에 포함되어 있다.
- **페널티메이트 층 표현의 구조 변화**: Müller et al.(2019)은 레이블 스무딩이 마지막 직전 층의 표현을 클래스별로 촘촘하고 서로 같은 거리로 떨어진 군집으로 모으는 경향이 있음을 보였다.
- **선택적 분류 성능 저하**: ResNet-50 ImageNet 실험에서 위험 1% 조건의 커버리지가 CE 15.66%에서 LS α=0.1일 때 0.05%로 떨어졌다. 정확도는 오를 수 있어도 틀린 예측을 걸러내는 능력은 약해진다.
- **증류 교사 모델에서의 부작용**: 레이블 스무딩으로 학습한 교사 출력은 클래스 간 유사도 정보가 지워져, 이를 학생 모델이 배우는 지식 증류에 불리할 수 있다.

## 자주 하는 오해
- ❌ 오해: 레이블 스무딩 α는 크게 줄수록 정규화가 강해져 항상 좋다 → ✅ 실제: α가 너무 크면 과도한 평활로 과소적합이 생길 수 있고, 최적 값은 데이터와 과제에 따라 달라서 검증 성능으로 튜닝해야 한다.
- ❌ 오해: 정확도가 오르면 확률 신뢰도도 모두 좋아진다 → ✅ 실제: 보정(calibration)은 좋아져도 선택적 분류처럼 확신도로 오답을 걸러내는 용도에서는 오히려 나빠질 수 있고, α가 클수록 악화된다.
- ❌ 오해: 모든 과제에서 똑같이 효과가 있다 → ✅ 실제: 효과는 과제와 데이터셋에 따라 다르며, 증류처럼 출력 분포 정보를 활용하는 작업에서는 해가 될 수 있다.

## 대화에서는 이렇게
- "ResNet 학습 레시피에 **label smoothing** 0.1 넣었더니 top-1이 조금 올랐어요."
- "**α**를 0.2로 올렸더니 정확도는 비슷한데 reject 기준으로 거를 때 커버리지가 확 줄었어요."
- "이 모델은 오답 걸러내는 게 핵심이라 **label smoothing**은 빼고 **온도 스케일링**으로 보정하는 게 낫겠어요."
- "교사 모델을 **label smoothing**으로 학습했더니 증류 성능이 안 나와요. 클래스 유사도 정보가 날아간 것 같아요."
- "라벨 노이즈가 좀 있는 데이터라 **label smoothing** 켜고 α만 0.05, 0.1로 나눠서 검증해 볼게요."

## 함께 읽으면 좋은 용어
- (기초) **Cross-Entropy Loss** — 레이블 스무딩이 정답 목표값을 바꾸는 대상이 바로 이 손실이라 먼저 알아야 한다.
- (기초) **Overfitting** — 레이블 스무딩이 줄이려는 문제로, 과신과의 관계를 이해하는 출발점이다.
- (유사) **Temperature Scaling** — 학습 후 logit을 조정해 보정하는 방식으로, 재학습 없이 과신을 다루는 점이 레이블 스무딩과 대비된다.
- (유사) **Dropout** — 같은 정규화 계열이지만 은닉 활성을 건드리는 방식이라, 출력 쪽을 건드리는 레이블 스무딩과 작용 지점이 다르다.
- (심화) **Knowledge Distillation** — 레이블 스무딩이 교사 출력의 클래스 간 유사도 정보를 지우는 문제와 직결되어, 둘을 함께 쓸 때의 트레이드오프를 배울 수 있다.
- (심화) **Selective Classification** — 확신도로 오답을 걸러내는 문제 설정으로, 레이블 스무딩이 이를 해칠 수 있는 이유를 이어서 볼 수 있다.

## body_advanced_en

## Technical Definition & How It Works
Label smoothing (LS) is an output-distribution regularizer for a K-class softmax classifier trained with cross-entropy (CE). The one-hot target is replaced by a convex combination of the one-hot vector and the uniform distribution over classes, with strength alpha (written epsilon or p in other papers). Only the target tensor changes; the network, the optimizer and the loss form stay the same, so the method adds no parameters and no extra training passes.

Data and control flow, with shapes for batch size B and K classes:

- Final layer: pre-logit features z [B, L] go through W [K, L] and b [K] to give logits v [B, K].
- Softmax and log-softmax over the last dimension give pi and log pi, both [B, K].
- Target construction: an integer label y [B] becomes y' [B, K] with y'_k = (1 - alpha) * 1[k = y] + alpha / K.
- Loss: L = -(1/B) * sum_n sum_k y'_k log pi_k.

At the logit level, the gradient of CE with respect to logit k is pi_k - y'_k. Under hard labels the optimum requires pi_y -> 1, so the logit gap grows without bound. Under LS the gradient vanishes only when pi_y = 1 - alpha + alpha/K. The max logit therefore stops growing once the model reaches this finite target.

Steps:
1. Choose alpha, typically 0.1 to 0.3 in the reference experiments.
2. Build y' without gradient.
3. Compute log-softmax over the logits.
4. Take the cross-entropy against y'.
5. Backpropagate as usual.
6. At inference, use the plain softmax with no smoothing.

Cost: target construction and loss are O(B*K), the same order as standard CE, with one extra [B, K] target tensor.

Two analyses from the references qualify this picture:

- Logit-gradient analysis (the ICLR 2025 paper): the amount LS suppresses the max logit corresponds to the true probability of error. Suppression is stronger when a prediction is likely correct and weaker when it is likely wrong. This compresses the uncertainty rank ordering between correct and incorrect predictions and degrades selective classification based on the maximum softmax probability (MSP).
- Representation analysis ("When does label smoothing help?"): LS pulls penultimate-layer representations into tight, equally distant class clusters. It can also erase inter-class similarity information, which is why it can hurt distillation.

## Formulas, Architecture, and Diagrams
Objective, with y'_k = (1 - alpha) * delta_{k,y} + alpha / K:

$$\mathcal{L}_{LS}(\theta) = -\frac{1}{N}\sum_{n}\sum_{k} y'^{(n)}_k \log \pi_k(x^{(n)};\theta)$$

Equivalent decomposition into a CE term and a regularizer:

$$\mathcal{L}_{LS} = (1-\alpha)\,\mathcal{L}_{CE} + \alpha\,\mathcal{L}_{U}, \qquad \mathcal{L}_{U} = -\frac{1}{K}\sum_k \log \pi_k$$

The second term equals the cross-entropy to the uniform distribution. It equals KL(U || pi) up to the constant log K, so LS penalizes mass concentrated on one class.

Gradient with respect to logit k:

$$\frac{\partial \mathcal{L}}{\partial v_k} = \pi_k - y'_k$$

The stationary point for the target class is pi_y = 1 - alpha + alpha/K. Under hard labels the same gradient lies in [-1, 1] and never reaches zero.

Generalization: a smoothing matrix S gives y_hat = S y, where S has diagonal p and off-diagonal (1-p)/(M-1) for uniform smoothing (the notation of the Chen et al. generalization paper). Non-uniform off-diagonal entries yield variants such as structural LS, which sets per-region strength before training.

Configuration levers:

- **alpha**: too large underfits, too small gives little regularization.
- **Uniform vs data-dependent smoothing**: uniform is one scalar; structural and k-NN variants compute per-sample or per-region strength.
- **Deployment-time post-processing**: logit normalisation is applied after training, not in the loss.

## Code or Pseudocode
```python
# PyTorch-style pseudocode: the core LS loss mechanism
import torch
import torch.nn.functional as F

def label_smoothing_ce(logits: torch.Tensor,   # [B, K] final-layer logits
                       target: torch.Tensor,   # [B] integer class indices
                       alpha: float = 0.1) -> torch.Tensor:
    assert 0.0 <= alpha < 1.0                  # alpha=1 makes the target purely uniform
    B, K = logits.shape
    log_p = F.log_softmax(logits, dim=-1)      # [B, K]

    # smoothed target y' = (1-alpha)*onehot + alpha/K  -> [B, K]
    with torch.no_grad():                      # the target is not a gradient target
        y_soft = torch.full_like(log_p, alpha / K)
        y_soft.scatter_(1, target.unsqueeze(1), 1.0 - alpha + alpha / K)

    # per sample: -sum_k y'_k log p_k, then average over the batch
    return -(y_soft * log_p).sum(dim=-1).mean()

def train_step(model, opt, x, y, alpha=0.1):
    model.train()
    loss = label_smoothing_ce(model(x), y, alpha)  # training: smoothing applied
    opt.zero_grad()
    loss.backward()
    opt.step()
    return loss.item()

@torch.no_grad()
def evaluate(model, x, y):
    model.eval()
    probs = F.softmax(model(x), dim=-1)        # inference: no smoothing
    conf, pred = probs.max(dim=-1)             # MSP-based confidence
    return (pred == y).float().mean().item(), conf
```

## Production Pitfalls
- ❌ Mistake: Shipping an LS-trained classifier with an MSP-threshold abstain rule tuned on accuracy alone, so that accepted-sample risk no longer tracks the threshold → ✅ Fix: Evaluate risk-coverage curves (for example coverage at 1% risk) for the LS model, and apply post-hoc logit normalisation or retrain with CE if rejection quality matters.
- ❌ Mistake: Raising alpha monotonically because validation accuracy improved at 0.1, then seeing underfitting or worse rejection at 0.3 → ✅ Fix: Sweep alpha on validation data for both accuracy and an uncertainty metric, and stop where either degrades; the reference shows SC degradation worsening with stronger LS.
- ❌ Mistake: Using an LS-trained model as the distillation teacher and finding the student gains little from the soft outputs → ✅ Fix: Retrain the teacher without LS, since LS erases information about similarities between classes that distillation relies on.
- ❌ Mistake: Applying smoothing at evaluation time or building the smoothed target inside the autograd graph, which makes the reported loss non-comparable with the CE baseline → ✅ Fix: Smooth only the training target under no_grad, evaluate with plain softmax and plain CE, and log the smoothed training loss separately.

## Tradeoffs — When to Use What
Suitable:

- Large-scale image classification training recipes (for example ImageNet-1k): the reference reports LS in many recent recipes, and it is a loss-side change with no architecture edits and no extra training time.
- Sequence models trained with token-level cross-entropy, such as the Transformer translation setup in the survey table: the BLEU gain reported there is 25.3 to 25.8, and the cost is one extra [B, K] target tensor.
- Datasets with partially mislabeled examples: the generalization analysis formalizes LS's benefit in the label-noise setting and predicts an optimal smoothing value.
- Settings where you want lower output probabilities for calibration, since models are typically more confident than accurate.

Unsuitable:

- Selective classification or abstention based on MSP: on ResNet-50 ImageNet, coverage at 1% risk fell from 15.66% (CE) to 0.05% (alpha=0.1). Train with plain CE, or keep LS and add post-hoc logit normalisation (22.31% at alpha=0.2).
- Teacher models for knowledge distillation: LS erases inter-class similarity information. Train the teacher with hard labels.
- Regions of high class overlap versus clean regions, when one global alpha is too blunt: uniform LS biases the Bayes error rate in the training data. Use structural label smoothing with per-region strength.
- Tasks with extremely sparse target distributions, which the survey of prior work flags as unfavorable to LS. Consider entropy penalization or temperature-based approaches instead.

## Industry Communication
- "In the **LS ablation**, the **alpha=0.1 run** improved top-1 by a small margin, but **coverage@risk=1%** collapsed from **15.66% to 0.05%** on ResNet-50, so the abstain path is effectively disabled."
- "Design-doc note: the **MSP-based reject rule** is incompatible with the current **label smoothing recipe**; we either retrain with **plain CE** or ship **post-hoc logit normalisation** at deployment."
- "Per the **logit-gradient analysis**, LS suppresses the **max logit** more for likely-correct samples, which compresses the **uncertainty ranking**; that matches what we see in our risk-coverage curves."
- "Review comment: the **smoothed target** must be built under **torch.no_grad()**, and the **eval path** must use unsmoothed softmax so the baseline loss stays comparable."
- "For the **teacher model** feeding **distillation**, I'd drop **LS**; the **inter-class similarity** signal gets erased and the student gains less."
- "Postmortem: we tuned **alpha** on accuracy alone, so the **underconfidence** side effects only surfaced after the **abstention threshold** went to production."
- "Open question for the next sprint: is a **structural LS** variant, with strength set per cluster before training, worth the extra preprocessing over a single **global alpha**?"

## Prerequisites, Alternatives, and Extensions
- (prerequisite) **Cross-Entropy Loss** — LS replaces the target inside this loss; the logit gradient pi_k - y_k is what LS reshapes, so it must be understood first.
- (prerequisite) **Softmax and logits** — LS acts on the softmax output distribution, and the max-logit suppression analysis depends on the logit-to-probability mapping.
- (alternative) **Entropy penalization** — (low-entropy output penalty) — Regularizes the output distribution directly with a penalty term rather than by modifying targets; the structural LS paper treats it as castable as a label-smoothing method.
- (alternative) **Dropout** — A competing regularizer that acts on hidden activations instead of the output targets, so it can be combined with or substituted for LS.
- (extension) **Structural Label Smoothing** — Computes per-region smoothing strength once before training to limit the Bayes-error bias that uniform LS introduces.
- (extension) **Selective Classification with logit normalisation** — The setting where LS side effects appear; post-hoc logit normalisation recovers the lost rejection performance.

## body_advanced_ko

## 기술적 정의와 동작 원리
Label Smoothing(LS)은 K-클래스 softmax 분류기의 학습 타깃을 원-핫 y에서 y' = (1−α)·y + α/K 로 바꾸는 출력 분포 정규화다. 손실은 cross-entropy를 그대로 쓰고 타깃만 달라지므로 네트워크 구조와 옵티마이저는 건드리지 않으며, 참고 논문들도 수정된 CE로 구현되어 추가 학습 시간이 거의 없다고 설명한다. 단, 정의가 두 가지 존재한다. ICLR 2025 논문(Xia et al.)은 균등 분포 U를 섞어 정답에 1−α+α/K를 주고, Chen et al.은 정답에 p, 오답에 (1−p)/(M−1)을 주는 방식이라 α 값이 서로 다른 의미를 가진다.

데이터/제어 흐름은 다음과 같다.

- 입력 x에서 pre-logit 특징 z ∈ R^L을 얻고, 로짓 v = Wz + b ∈ R^K, π = softmax(v)를 계산한다.
- 하드 레이블 y를 y' = (1−α)y + α/K 로 변환한다. 변환은 배치 단위 텐서 연산이며 [B,K] 크기의 타깃만 바뀐다.
- 손실 L = −Σ_k y'_k log π_k 를 계산하고, 로짓에 대한 gradient는 π − y' 가 된다.
- 역전파는 CE와 동일한 경로를 따르므로 메모리·지연 오버헤드는 타깃 텐서 생성 수준이다. 추론 시에는 아무 연산도 추가되지 않는다.

핵심 효과는 CE의 최소점이 로짓 무한대(π_정답→1)인 반면, LS에서는 최적 π_정답이 유한한 값(1−α+α/K)으로 고정된다는 점이다. 그래서 최대 로짓이 무한히 커지는 압력이 사라진다. 한편 Müller et al.(NeurIPS 2019)은 LS가 penultimate layer 표현을 같은 클래스끼리 조밀하고 클래스 간 등거리인 클러스터로 모으며, 이것이 calibration과 일반화에는 긍정적이지만 distillation에는 해롭다고 분석했다.

복잡도는 타깃 생성 O(BK)이고 forward/backward 비용은 CE와 같다. 추가 하이퍼파라미터는 α 하나다.

## 핵심 수식·아키텍처·도표
표준 정의(Xia et al. 표기, K 클래스):

$$y'_k = (1-\alpha)\,y_k + \frac{\alpha}{K},\qquad \mathcal{L}_{LS} = -\sum_{k} y'_k \log \pi_k$$

분해하면 LS 손실은 CE 항과 균등 분포 정규화 항의 가중합이다.

$$\mathcal{L}_{LS} = (1-\alpha)\,\mathcal{L}_{CE} + \alpha\left(-\frac{1}{K}\sum_k \log \pi_k\right)$$

로짓 v_k에 대한 gradient는 다음과 같다. softmax-CE의 미분 π_k − y'_k 를 그대로 적용한 결과다.

$$\frac{\partial \mathcal{L}_{LS}}{\partial v_k} = \pi_k - y'_k = \pi_k - (1-\alpha)\,y_k - \frac{\alpha}{K}$$

정답 클래스(y_k=1)에서는 다음과 같다.

$$\frac{\partial \mathcal{L}_{LS}}{\partial v_k}\bigg|_{y_k=1} = \pi_k - \left(1-\alpha+\frac{\alpha}{K}\right)$$

- π_정답 > 1−α+α/K 이면 gradient가 양수가 되어 경사하강 시 해당 로짓이 낮아진다. 즉 정답 확률이 이 상한을 넘으면 max logit이 억제된다. CE에서는 이 항이 π−1 ≤ 0 이라 정답 로짓을 계속 키우는 방향이다.
- 따라서 LS는 확신이 높은(맞을 가능성이 큰) 예측의 max logit을 더 강하게 누르고, 틀릴 가능성이 큰 예측은 덜 누른다. Xia et al.은 이 억제 정도가 실제 오류 확률 P_error와 대응한다고 분석했고, 이것이 맞은 예측의 불확실성은 상대적으로 높이고 오분류의 불확실성은 낮춰 selective classification의 순위를 망가뜨린다는 논증의 출발점이다.

비교 정리:

| 항목 | CE | LS |
|---|---|---|
| 정답 타깃 | 1 | 1−α+α/K (균등 혼합 정의) |
| 최적 로짓 | 발산 | 유한 |
| 추가 비용 | 없음 | 타깃 텐서 생성뿐 |
| 하이퍼파라미터 | 없음 | α |

학습 루프는 (1) 배치 로드 (2) forward로 로짓 [B,K] 계산 (3) 타깃을 y'로 변환 (4) 손실·역전파 (5) 검증에서 accuracy와 calibration·selective classification 지표를 함께 확인하는 순서다. 구성 레버는 α, 클래스 수 K, 정의 방식(α/K vs α/(K−1))이다.

## 코드 또는 의사코드
```python
# 분류 전용 예시 (pseudocode 수준, PyTorch 스타일). 시퀀스 모델에는 ignore_index 마스킹을 사용한다.
import torch
import torch.nn.functional as F

def ls_loss(logits, target, alpha, ignore_index=-100):
    # logits: [N, K], target: [N]. ignore_index 위치는 마스킹하고 유효 토큰 수로 평균한다.
    K = logits.size(-1)
    valid = target != ignore_index
    logp = F.log_softmax(logits, dim=-1)
    ce = -logp.gather(1, target.clamp(min=0).unsqueeze(1)).squeeze(1)  # -log pi_y
    uni = -logp.mean(dim=-1)                                            # -(1/K) sum log pi
    per = (1 - alpha) * ce + alpha * uni   # y' = (1-a)y + a/K 정의 (정답 포함)
    return (per * valid).sum() / valid.sum().clamp(min=1)

# 단위 테스트: alpha=0 -> F.cross_entropy, 분해식 일치
lg = torch.randn(8, 10); tg = torch.randint(0, 10, (8,))
assert torch.allclose(ls_loss(lg, tg, 0.0), F.cross_entropy(lg, tg), atol=1e-6)
logp = F.log_softmax(lg, -1)
ref = (1 - 0.1) * F.cross_entropy(lg, tg) + 0.1 * (-logp.mean())
assert torch.allclose(ls_loss(lg, tg, 0.1), ref, atol=1e-6)
# 주의: F.cross_entropy(label_smoothing=a)가 a/K(정답 포함) 정의인지
# a/(K-1) 정의인지 사용 중인 프레임워크 문서로 확인할 것.

def confidence(logits, mode="msp"):
    if mode == "msp":
        return F.softmax(logits, -1).max(-1).values
    if mode == "logit_norm":
        # Cattelan & Silva (2024)의 post-hoc logit normalisation.
        # 정확한 식은 본 자료에 없으므로 원 논문 정의로 교체해 구현해야 한다.
        raise NotImplementedError("원 논문 식 참조")
    raise ValueError(mode)

def evaluate(logits, target, mode="msp", risk_tol=0.01):
    # 신뢰도 내림차순 정렬 -> 누적 risk-coverage 곡선
    conf = confidence(logits, mode)
    err = (logits.argmax(-1) != target).float()
    order = conf.argsort(descending=True)
    cum_err = err[order].cumsum(0)
    n = torch.arange(1, len(err) + 1, dtype=torch.float32)
    risk = cum_err / n
    cov = n / len(err)
    ok = risk <= risk_tol
    cov_at_risk = cov[ok].max().item() if ok.any() else 0.0  # coverage@risk=1%
    return {"acc": 1 - err.mean().item(), "coverage@risk": cov_at_risk}

# CE 모델과 LS 모델을 같은 함수로 비교 (logits_ce, logits_ls는 각 모델의 검증 로짓)
# for name, lg_ in [("CE", logits_ce), ("LS", logits_ls)]:
#     print(name, evaluate(lg_, val_y, "msp"))
#     print(name, evaluate(lg_, val_y, "logit_norm"))
```

## 프로덕션 함정
- ❌ 실수: LS 모델을 accuracy만 보고 배포하고 MSP 같은 신뢰도 점수로 거부 임계값을 설정한다 → ✅ 해결: 같은 평가 함수로 CE와 LS의 risk-coverage 곡선과 coverage@risk를 함께 측정한다. ImageNet ResNet-50 실험에서 LS는 accuracy가 올라도 거부 성능이 크게 떨어질 수 있었다.
- ❌ 실수: 다른 코드베이스나 프레임워크의 α 값을 그대로 가져온다 → ✅ 해결: 정의가 α/K(정답 포함)인지 α/(K−1)인지 확인하고 단위 테스트로 손실 수치를 대조한다. 정의가 다르면 같은 α라도 타깃이 달라진다.
- ❌ 실수: α를 관행값(예: 0.1) 하나로 고정하고 튜닝을 생략한다 → ✅ 해결: Chen et al.은 최적 스무딩 지점이 존재하며 label noise 정도에 의존한다고 보였으므로, 검증 세트에서 α를 sweep하고 accuracy·calibration·거부 성능을 함께 비교한다(sweep 값은 예시로 0, 0.05, 0.1, 0.2).
- ❌ 실수: 시퀀스 모델에서 패딩 토큰까지 스무딩 손실에 포함하거나 전체 위치 수로 평균한다 → ✅ 해결: ignore_index 위치를 마스킹하고 유효 토큰 수로 나눠 평균한다. 안 그러면 손실 스케일과 gradient가 왜곡된다.
- ❌ 실수: LS로 학습한 모델을 teacher로 쓰고 증류 성능 저하의 원인을 못 찾는다 → ✅ 해결: Müller et al.의 분석대로 LS가 클래스 간 유사도 정보를 지울 수 있으므로 teacher는 LS 없이 학습한다.

## 트레이드오프와 언제 무엇을 쓰나
이럴 때 적합:

- ImageNet-1k처럼 클래스 수가 많은 이미지 분류 훈련 레시피: 구현이 타깃 변환뿐이라 학습 비용이 늘지 않고, 참고 논문들이 다수 최신 레시피에 포함된다고 보고한다.
- 기계 번역·음성 인식 등 시퀀스 학습: 문헌 요약표에서 BLEU 25.3→25.8, WER 8.9→6.7 같은 개선이 보고되었다. 단, 시퀀스 손실에는 패딩 마스킹이 필요하다.
- 과신으로 인한 calibration 악화를 줄이고 싶을 때: Müller et al.(NeurIPS 2019)은 LS가 일반화와 calibration에 긍정적임을 보였다.
- 학습 레이블에 노이즈가 섞인 설정: Chen et al.은 label noise 설정에서 최적의 스무딩 지점이 존재함을 이론과 실험으로 보였다.

이럴 때 부적합:

- 불확실성 기반 거부(selective classification)가 핵심인 시스템: ResNet-50 ImageNet에서 coverage@risk=1%가 CE 15.66%인데 LS α=0.1은 0.05%였다. 대안: LS 제거 또는 post-hoc logit normalisation(Cattelan & Silva, 2024) 병행(α=0.2 + 정규화 시 22.31%).
- 이 모델을 teacher로 쓰는 지식 증류: Müller et al.은 LS가 클래스 간 유사도 정보를 지워 증류를 해칠 수 있다고 설명했다. 대안: LS 없이 학습한 teacher.
- α를 과도하게 키우는 경우: opengenus 자료는 과도한 epsilon이 과도한 스무딩으로 underfit을 유발한다고 서술한다. 대안: 검증 세트에서 α를 낮춰 재탐색.
- 샘플별 정규화 강도가 달라야 하는 경우(결정 경계 근처 vs 먼 곳): 균등 스무딩은 일부 영역을 과도하게 정규화할 수 있다. 대안: Structural Label Smoothing(Li et al., AISTATS 2020).

## 업계 대화 맥락
- "이번 **ablation**에서 **LS α=0.1**을 넣으니 top-1은 올랐지만, **MSP 기반 coverage@risk=1%**가 사실상 0에 가깝게 떨어졌습니다. 거부 기능이 요구사항이면 **CE baseline**으로 되돌려야 합니다."
- "리뷰 코멘트: 우리 구현은 **α/K 정의**인데 비교 대상 레포는 **α/** (K−1)일 수 있습니다. **alpha=0 동치 테스트**와 분해식 assert를 CI에 추가해 주세요."
- "**logit normalisation**은 재학습 없이 **deployment-time**에 붙일 수 있어 우선 시도했고, 논문 기준으로 LS가 만든 SC 저하를 상당 부분 복구한다고 알려져 있어 우리 검증 세트에서도 재현 여부를 확인하겠습니다."
- "**max logit 억제**가 정답 확률에 비례해 강해지는 구조라 **uncertainty ranking**이 뒤집힌다는 분석이 있습니다. **correct vs incorrect 분리도**를 기존 지표에 추가하는 걸 제안합니다."
- "**teacher 모델**에 LS가 켜져 있었습니다. **distillation** 성능이 기대에 못 미친 원인으로 보여 teacher를 **LS off**로 재학습하는 PR을 올렸습니다."
- "시퀀스 태스크에서 **패딩 토큰이 평균에 포함**되고 있었습니다. **ignore_index 마스킹**과 유효 토큰 수 정규화로 수정했고 손실 스케일이 달라지니 **learning rate**도 재확인이 필요합니다."
- "**α sweep** 결과 최적점이 데이터셋마다 달랐습니다. **label noise** 비율이 높은 셋에서는 더 큰 α가 유리했으니 단일 기본값 대신 **per-dataset 튜닝**을 설계 문서에 명시하겠습니다."

## 선행·대안·확장 개념
- (선행) **Cross-Entropy Loss** — LS는 CE의 타깃 분포만 바꾸는 방식이라, softmax-CE의 로짓 gradient(π − y)를 이해해야 LS의 gradient π − y'와 max logit 억제가 읽힌다.
- (선행) **Bias-Variance Tradeoff** — α가 클수록 정규화(편향 증가)와 표현력(분산 감소)의 균형이 이동하며, 과도한 α가 underfit으로 이어지는 이유를 설명하는 틀이다.
- (대안) **Dropout** — 은닉 활성화를 건드리는 정규화로, 출력 분포를 타깃 수준에서 조정하는 LS와 개입 지점이 달라 함께 쓰거나 비교할 수 있다.
- (대안) **Weight Decay** — 가중치 크기를 제한해 과적합을 줄이는 방식이며, 타깃 분포가 아니라 파라미터 공간에서 정규화한다는 점이 LS와 다르다.
- (확장) **Structural Label Smoothing** — 균등 α 대신 영역별 스무딩 강도를 학습 전에 계산해 Bayes error rate 편향을 줄이는 데이터 의존형 변형이다.
- (확장) **Locally Adaptive Label Smoothing** — k-NN으로 지역 분포를 반영해 타깃을 스무딩하며, 예측 churn 감소가 목적이다. 사전 학습 모델이 필요해 추가 학습 비용이 든다.
- (확장) **(보완) Post-hoc Logit Normalisation** — (Cattelan & Silva, 2024) — LS가 망가뜨린 selective classification 성능을 배포 시점에 복구하는 후처리로, max logit이 커질수록 불확실성을 높여 LS의 불균형 억제를 보상한다.

## references_en

- {"title": "An Investigation of how Label Smoothing Affects Generalization", "authors": "Chen, Ziyin, Wang, Liang", "type": "paper", "url": "https://arxiv.org/html/2010.12648", "tier": "primary", "annotation": "Theory of how LS controls generalization loss under label noise, with a survey table of gains."}
- {"title": "Regularization via Structural Label Smoothing", "authors": "Li, Dasarathy, Berisha", "year": 2020, "venue": "AISTATS", "type": "paper", "url": "https://arxiv.org/pdf/2001.01900", "tier": "primary", "annotation": "균일 스무딩의 편향을 분석하고 데이터 의존적 스무딩을 제안."}
- {"title": "Towards Understanding Why Label Smoothing Degrades Selective Classification and How to Fix It", "authors": "Xia, Laurent, Franchi, Bouganis", "year": 2025, "venue": "ICLR", "type": "paper", "url": "https://arxiv.org/html/2403.14715v3", "tier": "primary", "annotation": "Shows LS lowers selective-classification quality and why post-hoc logit normalisation helps."}
- {"title": "When Does Label Smoothing Help?", "authors": "Müller, Kornblith, Hinton", "year": 2019, "venue": "NeurIPS", "type": "paper", "url": "https://arxiv.org/pdf/1906.02629", "tier": "primary", "annotation": "Explains how label smoothing shapes penultimate-layer clusters and why it can hurt distillation."}
- {"title": "Understanding Label Smoothing", "type": "blog", "url": "https://iq.opengenus.org/label-smoothing", "tier": "secondary", "annotation": "Plain-language overview of epsilon selection, underfitting risk and common variants."}
