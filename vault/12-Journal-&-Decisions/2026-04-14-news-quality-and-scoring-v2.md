---
title: 뉴스 품질 안정화와 scoring v2 도입
tags:
  - journal
  - ai-system
  - news-pipeline
  - scoring
aliases:
  - 2026-04-14 뉴스 품질 안정화
---

# 결정: 뉴스 품질 안정화와 scoring v2 도입

> 날짜: 2026-04-14
> 맥락: 2026-04-13~2026-04-14 동안 daily news pipeline의 품질 검수, source retrieval, prompt calibration, scoring 체계를 연속으로 점검하고 개편했다.
> 결론: 구조/출처/locale 검증은 크게 안정화됐고, 점수 체계는 v1의 “EN body 중심 soft gate”에서 v2의 “실제 발행 품질 점수” 방향으로 전환했다.

---

## 배경

4월 13일 draft를 수동 검수하면서 문제가 명확해졌다.

1. learner readability는 개선이 필요했지만, 프롬프트 자체가 부족하다기보다 긴 prompt 안에서 우선순위가 흐려지고 있었다.
2. business는 해석 자체가 문제라기보다 `title / excerpt / 첫 문단`에서 source tier보다 강한 문장을 쓰는 경우가 많았다.
3. EN/KO locale parity, `source_urls` 정합성, placeholder heading, EN heading Hangul leak처럼 **writer 후단에서 막아야 하는 문제**가 계속 보였다.
4. 품질 점수는 체감 품질과 괴리가 컸다. EN body만 보고 점수를 매겨서 KO, frontload, structured issues가 거의 반영되지 않았다.

즉, “프롬프트만 더 잘 쓰게 만들기”가 아니라 **validator, source retrieval, scoring까지 같이 손봐야 하는 상태**였다.

---

## 이번에 한 일

### 1. Prompt calibration

- learner 각 `###` 아이템 첫 문장은 먼저 “이게 뭔지/무엇을 하는지”를 일상어로 설명하도록 강화했다.
- business는 해석을 제거하지 않고, `headline / excerpt / 첫 문단`만 더 fact-led로 보수화했다.
- `One-Line Summary`는 단일 사건 요약이 아니라 **top 2~3 stories의 공통 흐름을 한 문장으로 묶는 역할**로 재정의했다.
- 한국어 learner/expert body는 `~요`식 대화체보다 **뉴스/에디토리얼 기사체**를 기본으로 맞췄다.

핵심 원칙은 다음 두 가지였다.

1. 해석은 유지한다.
2. 해석의 강도와 위치를 분리한다.

### 2. Validator / post-save quality hardening

- `### —` 같은 placeholder heading은 저장 전에 blocker로 막았다.
- EN `###` heading에 Hangul이 섞이면 저장 차단하고, EN-only recovery를 한 번 더 시도하도록 넣었다.
- `source_urls`는 이제 실제 본문 citation 기준으로 재구성되도록 정리했다.
- locale parity validator를 추가해서, EN/KO가 서로 다른 story set을 다루면 저장하지 않게 했다.
- `One-Line Summary`의 옛 하드 length penalty는 제거했다.

이 단계에서 구조 오류는 거의 정리됐다. 이후의 병목은 formatting보다 source retrieval과 frontload calibration으로 이동했다.

### 3. Source provenance + official retrieval

- source를 LLM이 추정하지 않게 하고, 파이프라인이 먼저 `source_kind / source_confidence / source_tier`를 붙이도록 바꿨다.
- 공식 도메인, 공식 플랫폼 자산, 논문, 공식 repo, media, analysis, community를 구분하는 provenance 메타를 writer prompt와 DB 저장 payload에 같이 실었다.
- source ordering은 `primary`가 먼저 오도록 정리했다.
- `developer.nvidia.com`, `microsoft.com/en-us/research/blog` 같은 공식 개발자/리서치 블로그를 1차 출처로 분류했다.
- single-source lead가 `secondary`로 시작하면, 기존 similar-article enrich 전에 **official-source lookup**을 한 번 더 수행하도록 넣었다.

이 변경으로 “가져온 source를 더 잘 다룬다” 수준에서 한 단계 나아가, **빠진 공식 source를 실제로 찾는 retrieval**까지 들어갔다.

### 4. Scoring v2a

가장 큰 구조 변경은 점수 체계였다.

기존 v1:
- `expert.en`
- `learner.en`
- 평균
- structural penalty 일부

v2a:
- `expert.en + expert.ko`
- `learner.en + learner.ko`
- `title / excerpt / focus_items` frontload scorer
- deterministic score
  - structure
  - traceability
  - locale
- structured issues
  - `severity`
  - `scope`
  - `category`
  - `message`
- issue penalty
  - `major -5`
  - `minor -2`
- score caps
  - source/factual issue
  - frontload overclaim
  - locale issue
  - learner accessibility issue

즉 점수가 “느낌 좋은 EN 본문”이 아니라 **실제 발행물 품질**에 더 가까워지도록 바뀌었다.

---

## 왜 점수가 갑자기 떨어졌는가

최근 7일(`2026-04-08`~`2026-04-14`)을 v2로 backfill하자 점수가 눈에 띄게 내려갔다.

이건 두 가지 이유가 겹친 결과였다.

### A. 예전 점수가 너무 후했다

v1은 EN body 위주라 다음을 거의 반영하지 못했다.

- KO 품질
- title/excerpt/focus_items
- structured issue severity
- score caps
- locale drift

즉 예전의 `90+`는 실제 publish-ready라기보다 **체감보다 부풀려진 점수**인 경우가 많았다.

### B. 과거 데이터 자체도 실제로 약했다

특히 `2026-04-13`을 확인해보니:

- business ko row는 `content_expert`가 비어 있었다.
- research ko row도 `content_expert`가 비어 있었다.

이런 상태는 v1에서는 거의 안 잡혔지만, v2에서는 `major locale issue`로 강하게 반영된다.

즉 점수가 떨어진 건 scoring이 망가졌다기보다, **이전에는 보이지 않던 결함이 드러난 것**에 가깝다.

---

## 최근 재채점 결과 해석

최근 7일 EN row 기준 분포는 대략 다음처럼 나왔다.

- average: 57.4
- `>= 85`: 1건
- `>= 80`: 2건

대표 케이스:

- `2026-04-13 business`: 74
- `2026-04-13 research`: 61
- `2026-04-14 business`: 90
- `2026-04-14 research`: 80

이 숫자는 “현재 생성물이 전부 나쁘다”는 뜻이 아니라:

1. 과거 batch는 지금 기준으로 보면 source/frontload/locale 품질이 약했고
2. 4월 14일처럼 최근에 재생성된 결과는 이미 훨씬 나아졌고
3. threshold는 historical backfill만 보고 바로 낮추면 안 된다는 뜻이다.

현재 판단은 이렇다.

- `85`를 바로 `80`으로 낮추는 건 이르다.
- 다음 몇 일간 **새로 생성되는 batch의 v2 분포**를 보고 조정해야 한다.
- 만약 조정한다면 첫 후보는 `80`보다 `82`가 더 자연스럽다.

---

## 현재 상태

### 안정화된 것

- EN heading locale leak은 최종 저장물 기준 거의 통제된다.
- locale parity validator가 EN/KO story set mismatch를 막는다.
- `source_urls`와 본문 citation 정합성이 맞는다.
- source provenance가 writer prompt와 DB에 같이 저장된다.
- official source retrieval이 일부 lead story에 반영되기 시작했다.
- One-Line Summary는 이제 실제 요약 역할을 한다.
- scoring v2a 코드와 최근 7일 DB backfill이 반영됐다.
- **scoring v2a calibration이 수렴**됐다 (severity rubric / SCORING RESOLUTION / Issue count discipline 세 축 분리).
- **quality judge가 "copy-edit 모드"에서 "review 모드"로 복귀**했다. 2차 rescore 기준 penalty가 -2~-12 range로 퍼지고 cap 실링에 걸리는 run이 사라졌다.
- **frontload locale parity 규칙이 writer 프롬프트에 박혔다**. KO frontload drift에 대한 prevention line이 추가됨.
- **rescore 도구**가 `backend/scripts/rescore_recent_batches.py`로 존재한다. 앞으로의 prompt calibration은 이 도구 기반으로 검증할 수 있다.

### 아직 남은 것

- 일부 historical batch는 full rerun 없이는 품질 회복이 어렵다.
- `rewrite both`만으로는 source retrieval, ranking, enrich 변화가 충분히 반영되지 않는다.
- recent threshold는 새 batch 몇 개를 더 보고 정해야 한다.
- 4월 8 business처럼 비정상 row는 점수보다 **데이터 상태 자체**를 따로 봐야 한다.
- **Frontload locale parity는 현재 prevention만 있고 detection이 없다.** 2-3일 관찰해서 prompt 규칙만으로 KO drift가 수렴하지 않으면, `_check_structural_penalties`에 EN/KO 숫자 token parity 체크 추가가 필요하다.
- **Judge false positive (e.g. `https:/` truncation 오인)** 는 분포 레벨에서 드물지만 완전 제거는 어렵다. 지금은 허용 가능한 noise.

---

## 운영 판단

### rerun 전략

과거 낮은 점수 배치(`2026-04-08`~`2026-04-12`)는 대부분 **rewrite both보다 full rerun**이 맞다.

이유:

- 문제의 상당수가 prompt 문체만이 아니라
  - source mix
  - official source retrieval
  - enrich 단계
  - frontload source strength
  에 있기 때문이다.

가능하면 `community` stage부터 rerun하는 것이 가장 효율적이고, UI가 그걸 지원하지 않으면 `full`이 낫다.

### scoring threshold

현재는 threshold를 바로 조정하지 않는다. `85`로 유지한다.

2차 calibration 후 rescore 기준으로는 다음 이유로 `85`가 적절하다.

- 10/14 (71%) auto-publish — 너무 permissive도 너무 strict도 아닌 범위.
- draft 4개가 **전부 cap이 적용된 run**이다. 즉 scoring system이 "실제 major 결함"을 명시적으로 찍은 결과.
- 83과 86 사이에 점수 분포의 유일한 "3점 gap"이 있다. 이게 threshold를 두기에 가장 자연스러운 지점.
- 뉴스 platform에서는 "나쁜 걸 auto-pub하는 비용" > "좋은 걸 draft로 돌리는 비용"이므로 conservative이 합리적.

운영 원칙:

1. 현재 threshold `85`를 유지.
2. 다음 2주간 auto-publish된 run들을 간헐적으로 manual review.
3. "auto-pub된 run에서 문제 발견" 2건 이상 → `87` 상향.
4. "draft로 밀린 run을 봤더니 왜 밀렸지?" 2건 이상 → `83` 하향.

즉 threshold는 지금 바꾸는 게 아니라 **data-driven으로 조정**한다.

---

---

## 2차: scoring v2a calibration 수렴

오후 작업은 v2a가 의도한 대로 움직이는지 확인하면서 시작했다. 그 과정에서 두 가지가 드러났다.

1. v2a 1차 rollout은 점수를 내리긴 했지만, 대부분의 감점이 **실제 결함이 아니라 LLM judge의 copy-edit 모드**에서 나왔다.
2. 동시에 진짜 결함(frontload locale drift)은 이미 잡히고 있었지만, calibration이 수렴되기 전까지는 그 신호가 noise에 묻혔다.

### 1차 calibration 시도 — 의도한 것 vs 의도하지 않은 것

`fix(scoring): calibrate v2a judges` 커밋에서 세 가지를 한 번에 넣었다.

- **Severity rubric**: 5 프롬프트 전부에 `major = 5개 카테고리 (fabrication / broken structure / factual error / locale corruption / source fabrication)`를 박고 나머지는 전부 `minor`, "불확실하면 minor"를 명시.
- **SCORING RESOLUTION**: 4 body 프롬프트에 `25 / 22-23 / 19-21 / 15-17 / 10-13 / 5-8 / 0-3` 7단계 intermediate anchor 제공. frontload는 분포가 이미 건강해서(49-97) 제외.
- **Scope normalization**: `"frontload|en|ko"` 같은 pipe-joined scope을 canonical 첫 매치로 정규화. `_apply_issue_penalties_and_caps` label 정렬도 명시적으로 변경.

**의도했던 효과**: body raw score가 95-100 saturate에서 내려와 85-95 range로 퍼지고, severity가 엄격해지면서 penalty가 줄어들 것으로 봤다.

**실제 나온 것 (1차 rescore)**:

- body raw: 의도대로 82-94로 퍼짐. ✓
- severity: 의도대로 전부 `minor`만 나옴. `major`는 거의 없음. ✓
- penalty: **역방향으로 악화**. 14 run 중 **13개가 -20 cap에 걸림**. ✗
- 평균: 72.1 (원래 78.0에서 하락)
- `>=85`: 0/14 (원래 3/14)

첫 rescore 결과만 보면 v2a calibration이 파이프라인을 오히려 망친 것처럼 보였다.

### 진짜 원인: judge가 copy-edit 모드에 들어감

`--verbose` rescore로 실제 issue 메시지를 뜯어보니 패턴이 분명해졌다.

- "paragraphs concisely summarize multiple claims" ← 결함 아님, 장점
- "slightly dense with jargon" ← 스타일 선호
- "some product names lack parenthetical notes" ← optional improvement
- "Korean text could be simplified further" ← editorial choice

즉 SCORING RESOLUTION이 "점수 낮추는 gap을 찾아라"로 의도됐는데, LLM은 **"gap을 issue list에 나열해야 한다"고 해석**했다. 결과적으로 두 가지가 동시에 일어남:

1. 점수가 낮아짐 (의도)
2. minor issue 개수가 폭증 (의도 아님)

3개 judge × 5 minor × -2 penalty = -30 → -20 cap. 거의 모든 run이 penalty ceiling에 부딪히고, 점수는 "실제 품질에 비례"가 아니라 **"cap에 부딪혔다"**는 수학적 상수에 가까워졌다.

핵심은: **severity rubric과 score resolution은 독립적인 축**이어야 하는데, 둘이 섞였다. 이걸 분리하려면 "issue list는 점수를 정당화하는 도구가 아니다"라는 규칙이 따로 필요했다.

### 2차 calibration — Issue Count Discipline

`fix(scoring): rein in copy-edit mode` 커밋에서 5 프롬프트 전부에 "Issue count discipline" 블록 추가.

- `AT MOST 5 issues` → `AT MOST **3 issues**`
- `nothing is genuinely broken`면 ZERO issues 반환. 채우지 말 것.
- "이건 report하지 말라"의 explicit 목록:
  - "could be clearer", "slightly dense", "tone is slightly strong"
  - "could benefit from a parenthetical note"
  - "some paragraphs summarize multiple claims"
  - "headline is punchy but compressed"
- **score와 issue list의 역할 분리 명문화**: "score = 전반적 품질, issue list = 고쳐야 할 구체 결함. 점수를 정당화하기 위해 issue를 만들지 말라. score 18에 zero issues는 올바른 상태이다."

이건 단순한 prompt 튜닝이 아니라 **scoring 철학의 명시화**였다. 애초에 severity rubric과 scoring resolution이 설계에서 분리된 축이라는 걸 LLM에게 명시적으로 알려줘야 두 축이 섞이지 않는다.

### 2차 rescore 결과

같은 14개 digest를 새 프롬프트로 다시 채점한 결과:

| 지표 | 1차 rescore (copy-edit 모드) | 2차 rescore (discipline 추가) |
|---|---|---|
| 평균 | 72.1 | **85.9** |
| Range | 66-77 | **73-94** |
| `>= 85` 비율 | 0/14 (0%) | **10/14 (71%)** |
| penalty = -20 run | 13/14 | **0/14** |
| body raw 분포 | 82-94 (유지) | 81-95 (유지) |

4개 run이 draft로 남았고 (`4/8 business 73, 4/10 research 78, 4/12 business 80, 4/14 business 83`), **이 4개 모두 cap이 적용된 run**이었다. 즉 2차 프롬프트는 "실제 major 결함"과 "stylistic noise"를 구분하기 시작했다.

### 저점수의 진짜 원인 — KO frontload locale drift

4개 draft를 verbose로 뜯어보니 완전히 다른 패턴이 드러났다. **본문은 멀쩡하다**. body LLM judge는 draft 4개 전부에 89-94를 줬다. 점수가 빠진 지점은 frontload 하나.

실제 관측된 issue들 (후기 사례 포함해서 7개):

- 4/8 business: KO headline에 EN에 없는 "specific figures" 추가 (major)
- 4/10 research: KO excerpt에 EN에 없는 "5위" 순위 추가 (major)
- 4/12 business: KO headline이 "모든 주요 OS·브라우저 취약점" 주장 추가 (major)
- 4/12 business: EN/KO headline이 실질적으로 다른 이야기 (major)
- 4/13 business: KO headline framing이 EN과 다름 (minor)
- 4/14 business: KO가 "Mira Murati" 이름 생략 (minor)
- 4/14 business: KO가 `$$` 마커를 혼용, EN은 `$` notation (minor)

**3건이 major**로 cap을 발동시켰고, 이게 draft 4개 중 3개의 점수를 끌어내린 직접적 원인이었다. 본문 품질 문제가 아니라 **"KO가 EN을 번역이 아닌 재창작으로 취급"**하는 체계적 편향.

이 편향은 writer 프롬프트의 구조적 결함이다. 현재 writer는 EN과 KO를 **한 번의 JSON call로 동시 생성**한다. 이때 LLM이 KO를 독립적으로 "punchy하게" 다시 쓰는 경향을 가진다. "번역"이 아니라 "같은 사건의 다른 editorial"로 행동한다.

### Frontload Locale Parity 규칙 도입

`fix(prompt): frontload locale parity` 커밋에서 writer 프롬프트에 새 constant 추가.

- `HALLUCINATION_GUARD` 바로 뒤에 `FRONTLOAD_LOCALE_PARITY` 블록 주입.
- 명시적 규칙: **"KO는 자연 번역이지 재창작이 아니다."**
- DO NOT add: EN에 없는 숫자, 순위, 주장, entity, 편집 framing.
- DO NOT omit: EN에 있는 고유명사, 수치, 회사명.
- 4개의 O/X 예시 (전부 실제 4/8-4/14 관측 기반)
- FINAL CHECKLIST item 6 추가: 응답 전 마지막 자기 검증.

현재 시점에서 이 규칙은 **prevention**이다. writer가 KO drift를 시작하기 전에 규칙으로 막는 것. **detection** (코드 레벨 EN/KO 숫자 parity 체크)은 보류했다 — 2-3일 새 batch를 관찰해서 prompt만으로 수렴되는지 보고, 안 되면 추가.

### 부수적 발견: judge false positive

4/10 research의 "truncated citation `[5](https:/`" 이슈는 실제 잘못된 게 아니었다. 전체 URL은 `[5](https://www.cnbc.com/2026/04/09/...)`로 정상. LLM judge가 `https:/`까지만 보고 "잘렸다"고 잘못 판단한 false positive.

이런 개별 false positive는 완전 제거가 어렵다. 하지만 분포 단위로는 드물어서 — 위 모든 calibration이 수렴된 상태에서 10개 이상 run을 봐야 겨우 1-2개 나오는 수준 — 현재는 허용 가능한 noise로 판단한다.

### 운영 도구: `rescore_recent_batches.py`

이 calibration 과정 내내 "프롬프트를 바꿨을 때 기존 데이터에 어떤 영향이 있는지"를 반복 확인해야 했다. 이를 위해 v2 계획의 Task 9였던 rescore script를 뒤늦게 구현.

- DB에서 기존 `news_posts` row를 읽어 `PersonaOutput + frontload`로 재구성
- `_check_digest_quality`를 실행해 현재 prompt로 재채점
- **DB에 쓰지 않음** — `_log_stage`를 `AsyncMock`으로 패치해서 `pipeline_logs` 오염 방지
- 사용: `python -m scripts.rescore_recent_batches --start 2026-04-08 --end 2026-04-14 [--verbose]`

이 도구 없이는 "프롬프트를 바꿨는데 효과가 있을까"를 하루 기다려야 한다. 앞으로 모든 quality 관련 프롬프트 변경은 rescore로 우선 검증하는 워크플로우가 가능해졌다.

### 이번 calibration에서 수정한 커밋

- `a4451b3` — severity rubric + SCORING RESOLUTION + scope normalization + label ordering
- `145f585` — issue count discipline + rescore script
- `dcdd1c2` — frontload locale parity rule

---

## 이번 세션의 핵심 교훈

1. **구조 문제는 prompt보다 validator가 잘 막는다.**
2. **해석은 없앨 게 아니라 앞단과 분석 본문으로 층위를 나눠야 한다.**
3. **source ordering만으로는 부족하고 official retrieval이 따로 필요하다.**
4. **좋은 scoring은 단일 총점이 아니라 component-wise + deterministic + structured issue여야 한다.**
5. **historical batch backfill은 threshold 결정용이 아니라 숨은 결함 발견용으로 더 유용하다.**
6. **Severity rubric과 Scoring resolution은 독립적인 축이다.** 하나의 프롬프트 변경으로 두 축을 동시에 움직이면 LLM이 둘을 섞어 해석한다. Issue count discipline이 이 두 축을 분리하는 접착제 역할을 한다.
7. **LLM judge는 "use full range"를 "find gaps to report"로 오해한다.** Score는 "전반적 품질", issue list는 "고쳐야 할 구체 결함". 이 둘을 명시적으로 분리하지 않으면 judge가 점수를 정당화하기 위해 issue를 만든다.
8. **저점수는 "애매하게 나쁨"이 아니라 "측정 가능한 defect"에서 나온다.** body judge는 주관적이라 saturate하지만, frontload judge는 fact parity라는 binary 질문을 물어보기 때문에 점수 차이가 실제 defect에 비례한다. scoring v2a의 가장 중요한 설계 포인트는 이 binary 판단 축(frontload)의 도입이었다.
9. **KO는 writer가 가만두면 재창작을 시도한다.** 동일 JSON call에서 EN과 KO를 동시 생성할 때, LLM은 KO frontload를 EN의 번역이 아니라 "KO 독자에게 더 어필하는 별도 editorial"로 다룬다. 이건 prompt 규칙으로 막아야 한다.
10. **rescore 도구가 없으면 prompt calibration은 하루 주기로 진행된다.** 도구가 있으면 30분 주기로 수렴한다. scoring 계열 변경에는 rescore가 TDD의 failing test 역할을 한다.

---

## Related

- [[2026-04-01-news-pipeline-v10|news pipeline v10 전환 결정]]
- [[2026-03-30-news-pipeline-v9|v9 품질/구조 개선 기록]]
- [[2026-03-29-news-pipeline-v7|v7 품질 개선 회고]]

## See Also

- [[Daily-Dual-News]] - daily news product 구조
- [[AI-News-Pipeline-Design]] - 뉴스 파이프라인 설계
- [[AI-NEWS-Business-Writing]] - business writing 기준
- [[AI-NEWS-Research-Writing]] - research writing 기준
- [[AI-News-Pipeline-Operations]] - 운영 관점 파이프라인 메모
