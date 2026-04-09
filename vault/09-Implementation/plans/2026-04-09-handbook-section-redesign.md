# Handbook 섹션 구조 재설계

> **날짜:** 2026-04-09
> **관련 스프린트:** NP4-Q (HQ-12 톤 재설계 + HQ-06 콘텐츠 최소 기준의 재정의)
> **참조:** [[Handbook]], [[Handbook-Content-Rules]], [[2026-03-15-handbook-quality-design]]
> **선행 분석:** 2026-04-09 생성 5개 용어(overfitting, DPO, Hugging Face, MCP, fine-tuning) 평가

---

## 1. 배경

### 기존 구조의 문제

2026-03-15 설계는 **Basic 8섹션 / Advanced 9섹션**이었으나, 이후 프롬프트가 진화하며 실제 생성은 **Basic 13섹션 / Advanced 11섹션**으로 비대화됨. 2026-04-09 생성된 5개 용어 평가 결과:

1. **섹션 반복** — `0_summary` + `1_plain` + `4_why`가 같은 정보를 다른 톤으로 세 번 반복. Popup 독자는 첫 문장만 읽고 떠나고, 학습자는 신뢰감이 떨어짐.
2. **Basic/Advanced 차별화 실종** — 길이 차이만 있고 섹션 역할이 유사. 같은 페이지 두 번 읽는 느낌.
3. **Entry path 혼재** — Popup(15초) / 학습 브라우즈(10분) / Google 착륙(5분)을 한 페이지가 동시에 받으려다 셋 다 어중간.
4. **Orphan link** — `basic_ko_8_related` / `10_learning_path`의 추천 용어 대부분이 미작성 상태. 클릭하면 404.
5. **References 중복** — `basic_ko_10_learning_path`와 `adv_ko_8_refs`에 각각 출처 섹션이 존재. Level 토글 시 출처가 사라졌다 나타남. 같은 논문을 두 번 저장.
6. **본문 비대** — `basic_ko_9_roles`, `6c_checklist`가 본문 안에 있어 학습자 아닌 독자에겐 노이즈.

### 재설계 목표

- 한 섹션 = 한 질문. 중복 제거.
- Basic/Advanced를 **다른 질문에 답하는 두 페이지**로 분리. 길이가 아니라 역할로 구분.
- Path A(popup) 사용자는 **본문에 진입하기 전에** 졸업시킨다.
- Sidebar / Hero card / Footer를 활용해 본문에서 제거되는 요소를 보존.

---

## 2. 설계 원칙

1. **한 섹션 = 한 질문.** 같은 정보를 다른 톤으로 다시 말하는 섹션은 통합 또는 제거.
2. **Hero card는 level-independent.** Definition + 뉴스 맥락이 level switcher 위에 상시 노출.
3. **Basic ≠ Advanced의 짧은 버전.** 다른 질문에 답함. 검증은 §5 차별화 매트릭스로.
4. **References는 본문이 아니다.** 페이지 footer block, level 무관. 1차 출처 강제.
5. **Sidebar는 학습 도구의 자리.** 체크리스트 같은 "학습자 전용" 요소는 여기.

---

## 3. 사용자 질문 → 섹션 매핑

| Q | 사용자 질문 | Hero | Basic | Advanced | Sidebar | References |
|---|---|:---:|:---:|:---:|:---:|:---:|
| Q1 | 한 줄로 뭔데? | ✓ | | | | |
| Q2 | 뉴스에선 무슨 뜻? | ✓ | | | | |
| Q3 | 비전문가한테 설명? | | ✓ | | | |
| Q4 | 실생활 예시? | | ✓ | | | |
| Q5 | 비슷한 것과 차이? | | ✓ | ✓ | | |
| Q6 | 왜 다들 얘기해? | | ✓ | | | |
| Q7 | 어디서 쓰여? | | ✓ | | | |
| Q8 | 자주 하는 오해? | | ✓ | | | |
| Q9 | 회의에서 뭐라 말해? | | ✓ | ✓ | | |
| Q10 | 다음에 뭘 읽어? | | ✓ | ✓ | | |
| Q11 | 기술적으로 어떻게? | | | ✓ | | |
| Q12 | 코드/수식? | | | ✓ | | |
| Q13 | 프로덕션에서 깨지는 지점? | | | ✓ | | |
| Q14 | 1차 출처? | | | | | ✓ |
| Q15 | 이해했는지 확인? | | | | ✓ | |

---

## 4. 페이지 레이아웃

```
┌────────────────────────────────────────────┐
│ Header: category + term + term_full        │  공유
├────────────────────────────────────────────┤
│ definition_ko (한 줄)                        │  공유
│ ┌──────────────────────────────────────┐   │
│ │ HERO CARD                             │   │  공유 (NEW)
│ │ • 뉴스에서 이 용어가 쓰이는 3가지 맥락    │   │
│ │ • "원래 뉴스로 돌아가기" 버튼             │   │
│ └──────────────────────────────────────┘   │
├────────────────────────────────────────────┤
│ Level Switcher: Basic / Advanced            │  공유
├────────────────────────────────────────────┤
│ BODY (Basic OR Advanced, JS로 교체)          │  level-specific
│ §1 ... §7                                   │
├────────────────────────────────────────────┤
│ REFERENCES footer block                     │  공유 (NEW)
│ [primary 2-5개, secondary 0-3개]             │
├────────────────────────────────────────────┤
│ ContentFeedback (도움됨/헷갈림)               │  공유
└────────────────────────────────────────────┘

Sidebar (HandbookSideRail):
├ related_terms (기존)
├ same_category_terms (기존)
├ related_articles (기존)
└ understanding_checklist (NEW, Basic 뷰 한정)
```

---

## 5. 새 프롬프트 출력 필드 스펙

### 5.1 Hero / Meta (level-independent, 공유)

| 필드 | 설명 | 제약 |
|---|---|---|
| `term` | 영어 메인 표기 (약어 우선) | 기존 |
| `term_full` | 영어 풀네임 | 기존 |
| `korean_name` | 한국어 발음/통용 표기 | 기존 |
| `korean_full` | 한국어 정식 명칭 | 기존 |
| `categories` | 1~3개 | 기존 |
| `definition_ko` / `definition_en` | 1~2 문장 | **max 140자** (popup 1초 졸업용, 현재 171자 사례 축소) |
| `hero_news_context_ko` / `hero_news_context_en` | 뉴스 맥락 3줄 | **정확히 3줄**, 각 줄 ≤60자. 형식: `"X"라고 나오면 → 이런 뜻` |

**Hero card 렌더링:** `definition` + `hero_news_context` + "원래 뉴스로" 버튼. Level switcher 위. **Path A 사용자는 이 카드에서 졸업한다.**

기존 `basic_ko_6b_news_context`를 hero 필드로 승격. 본문에서 제거.

### 5.2 Basic body 섹션 (7개)

| 필드 | 섹션명 | 답하는 질문 | 분량 | 기존 필드에서 유래 |
|---|---|---|---|---|
| `basic_ko_1_plain` | 쉽게 이해하기 | Q3 | **600~800자** | 기존 `1_plain` (압축) |
| `basic_ko_2_example` | 비유와 예시 | Q4 | **3개** (각 100자) | 기존 `2_example` (4→3) |
| `basic_ko_3_glance` | 한눈에 비교 | Q5 | 표 1개만 | 기존 `3_glance` (**prefix 3줄 라인 제거**) |
| `basic_ko_4_impact` | 어디서 왜 중요한가 | Q6+Q7 | 4~5 bullet | 기존 `4_why` + `5_where` **통합** |
| `basic_ko_5_caution` | 자주 하는 오해 | Q8 | **3개** | 기존 `6_caution` (4→3) |
| `basic_ko_6_comm` | 대화에서는 이렇게 | Q9 | 5개 | 기존 `7_comm` (그대로) |
| `basic_ko_7_related` | 함께 읽으면 좋은 용어 | Q10 | 4~6개 | 기존 `8_related` + `10_learning_path` Part 2 통합 |

**Basic body 목표 분량: 2,800~3,500자** (현재 5,400~6,000자 → -45%)

### 5.3 Advanced body 섹션 (7개)

| 필드 | 섹션명 | 답하는 질문 | 분량 | 기존 필드에서 유래 |
|---|---|---|---|---|
| `adv_ko_1_mechanism` | 기술적 정의 & 동작 원리 | Q11 | 600~900자 | 기존 `1_technical` + `3_howworks` **통합** |
| `adv_ko_2_formulas` | 수식·아키텍처·도표 | Q11+Q12 | 조건부 | 기존 `2_formulas` (그대로) |
| `adv_ko_3_code` | 코드 또는 의사코드 | Q12 | 15줄+ | 기존 `4_code` (그대로) |
| `adv_ko_4_tradeoffs` | 트레이드오프 & 언제 무엇을 쓰나 | Q5(Advanced) | 3~4 + 3~4 | 기존 `10_when_to_use` (**이름 변경**) |
| `adv_ko_5_pitfalls` | 프로덕션 함정 | Q13 | 3~4 pair | 기존 `5_practical` 후반부 + `11_pitfalls` **통합** |
| `adv_ko_6_comm` | 업계 대화 맥락 | Q9(Advanced) | 6~8개 | 기존 `7_comm` (그대로) |
| `adv_ko_7_related` | 선행·대안·확장 개념 | Q10 | 4~6개 | 기존 `9_related` (그대로) |

**Advanced body 목표 분량: 6,500~9,000자** (현재 10,000~13,800자 → -35%)

### 5.4 References footer (level-independent, 공유)

| 필드 | 타입 | 설명 |
|---|---|---|
| `references_ko` | JSON 배열 | 아래 스키마 |
| `references_en` | JSON 배열 | 동일 |

**스키마:**
```json
[
  {
    "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
    "authors": "Rafailov et al.",
    "year": 2023,
    "venue": "NeurIPS",
    "type": "paper",
    "url": "https://arxiv.org/abs/2305.18290",
    "tier": "primary",
    "annotation": "DPO 원 논문. 선호 확률 조정의 수학적 유도."
  }
]
```

**필드 정의:**
- `type`: `paper` / `docs` / `code` / `blog` / `wiki` / `book`
- `tier`: `primary` (논문/공식문서/공식 구현) / `secondary` (블로그/해설)
- `annotation`: 한 줄, 60자 이내

**품질 규칙 (프롬프트 내 강제):**
- 최소 `primary` 2개 필수
- 최대 `secondary` 3개
- 총 3~7개
- 각 URL은 Reference Materials에서 확인된 것만. 추측 URL 금지.
- 기존 `basic_ko_10_learning_path` Part 1(정석 자료) + `adv_ko_8_refs`를 이 필드로 통합.

### 5.5 Sidebar 전용 필드

| 필드 | 설명 | 렌더 위치 |
|---|---|---|
| `sidebar_checklist_ko` / `sidebar_checklist_en` | 4~5개 이해 확인 질문 | Sidebar, Basic 뷰 한정 |

기존 `basic_ko_6c_checklist`를 여기로 이동. 본문에서 제거. `HandbookSideRail`에 `<UnderstandingChecklist>` 블록 추가.

---

## 6. 제거되는 기존 필드

본문 생성 자체를 중단:

| 기존 필드 | 처리 |
|---|---|
| `basic_ko_0_summary` | **삭제.** Hero card + `1_plain`으로 충분. 세 번 반복 제거. |
| `basic_ko_9_roles` | **삭제.** 직군별 활용은 본문에 맞지 않음. 향후 profile.role 기반 위젯은 별도 plan. |
| `adv_ko_5_practical` 전반부 | **삭제.** use case 나열은 `1_mechanism`에 흡수. 함정 부분만 `5_pitfalls`로 유지. |
| `adv_ko_6_why` | **삭제.** "왜 중요한가"는 Basic `4_impact`에서 충분. Advanced 리더는 이미 "왜"를 안다. |
| `adv_ko_8_refs` | **이동.** `references_*` footer로 통합. |
| `basic_ko_6b_news_context` | **승격.** `hero_news_context_*`로. |
| `basic_ko_6c_checklist` | **이동.** `sidebar_checklist_*`로. |
| `basic_ko_10_learning_path` Part 1 | **통합.** `references_*`에. |
| `basic_ko_10_learning_path` Part 2 | **통합.** `basic_ko_7_related`에. |

---

## 7. Basic ↔ Advanced 차별화 매트릭스

재설계 후 두 페이지가 **진짜로 다른 페이지**인지 검증:

| 항목 | Basic | Advanced |
|---|---|---|
| **비유** | 있음 (§1, §2) | 없음 |
| **코드** | 없음 | 있음 (§3) |
| **수식** | 없음 (§3 표만) | 있음 (§2) |
| **사용 맥락** | "세상에서 어디 쓰이는가" (§4) | "프로덕션에서 어떻게 깨지는가" (§5) |
| **비교의 성격** | 개념 차이 (§3) | 기술 트레이드오프 (§4) |
| **대화 톤** | Slack / 회의 일상 (§6) | PR 리뷰 / 설계 문서 / incident (§6) |
| **관련 용어** | 학습 다음 단계 (§7) | 선행·대안·확장 (§7) |

**검증 기준: "있음/없음" 또는 "의미가 다름"인 줄이 최소 5개.** 현재 결과 7개 모두 차별화 → 통과.

---

## 8. 프롬프트 재작성 명세

### 8.1 파일 위치

- `backend/services/agents/prompts_advisor.py`
  - `GENERATE_BASIC_PROMPT` (L570)
  - `GENERATE_BASIC_EN_PROMPT` (L729)
  - `GENERATE_ADVANCED_PROMPT` (L867)
  - `GENERATE_ADVANCED_EN_PROMPT` (L967)

- `backend/services/agents/prompts_handbook_types.py`
  - `BASIC_TYPE_GUIDES` (L449) — 10개 type별 basic 가이드. 섹션 키 참조 업데이트 필요.
  - `TYPE_DEPTH_GUIDES` (L87) — advanced type 가이드. 섹션 키 참조 업데이트 필요.
  - `TYPE_SECTION_WEIGHTS` (L201) — (type, intent) → section weight 매핑. 새 섹션 키로 재매핑.
  - `CATEGORY_CONTEXT` (L306) — 그대로 유지. 내용 영향 없음.

### 8.2 GENERATE_BASIC_PROMPT 재작성 핵심 변경

**섹션 리스트 재정의:**

기존 13섹션 키 → 신규 8키(hero 1 + body 7):

```
hero_news_context_ko         (NEW, 3줄 고정)
basic_ko_1_plain             (압축 — 600~800자, 현재 1,500자)
basic_ko_2_example           (4→3)
basic_ko_3_glance            (prefix 라인 규칙 삭제 — 표만)
basic_ko_4_impact            (4_why + 5_where 병합, 규칙 통합)
basic_ko_5_caution           (4→3)
basic_ko_6_comm              (그대로)
basic_ko_7_related           (8_related + 10_learning_path Part 2 병합)
```

**Self-Check 블록 재작성:**
- "No section shares analogy/example" 유지
- "hero_news_context는 3줄 고정, 각 줄 60자 이하" 추가
- "1_plain은 600~800자" 추가
- "references는 이 프롬프트에서 생성하지 않음" 추가 (통합 references 섹션이 별도)
- **삭제된 체크:** 0_summary jargon 체크, 9_roles 체크, 10_learning_path 체크

**Output JSON Structure 블록 재작성:**
- 기존 JSON의 13 키 → 신규 8 키
- `references_ko` 배열 필드 추가 (아래 8.4 참조)
- `sidebar_checklist_ko` 필드 추가 (단일 문자열)

### 8.3 GENERATE_ADVANCED_PROMPT 재작성 핵심 변경

**섹션 리스트 재정의:**

기존 11키 → 신규 7키:

```
adv_ko_1_mechanism      (1_technical + 3_howworks 병합 — "Technical + How It Works")
adv_ko_2_formulas       (그대로)
adv_ko_3_code           (기존 4_code 리넘버링)
adv_ko_4_tradeoffs      (기존 10_when_to_use 리네임 — "Tradeoffs" 강조)
adv_ko_5_pitfalls       (기존 5_practical 후반부 + 11_pitfalls 병합)
adv_ko_6_comm           (기존 7_comm 리넘버링)
adv_ko_7_related        (기존 9_related 리넘버링)
```

**제거된 기존 키:**
- `adv_ko_5_practical` 전반부 (use cases) — `1_mechanism` 말미 1문단에 흡수
- `adv_ko_6_why` — 완전 삭제
- `adv_ko_8_refs` — references footer로 이동

**Self-Check 블록 재작성:**
- "No repeat from basic" 유지
- "1_mechanism은 definition + architecture + data flow를 한 섹션에" 추가
- "5_pitfalls은 최소 3 mistake-solution pair" 유지
- "references는 이 프롬프트에서 생성하지 않음" 추가
- **삭제된 체크:** 6_why 체크, 5_practical use case 체크

### 8.4 References 생성 — 3가지 선택지

References를 어느 프롬프트가 생성할지 결정 필요:

**옵션 A: Basic 프롬프트에 통합 생성 (추천)**
- `GENERATE_BASIC_PROMPT`가 `references_ko` 배열을 함께 출력
- Basic 프롬프트의 Reference Materials 입력이 가장 풍부하므로 자연스러움
- Advanced 프롬프트는 references를 건드리지 않음
- 장점: 호출 수 추가 없음. 한 프롬프트 안에 1차 출처 강제 규칙.
- 단점: Basic 출력 JSON이 조금 커짐

**옵션 B: 별도 5번째 호출로 분리**
- `GENERATE_REFERENCES_PROMPT` 신설
- `gpt-4.1-mini` 또는 `gpt-5-nano`로 저비용
- 장점: 관심사 분리. Basic 프롬프트 단순화.
- 단점: 호출 1회 증가 (시간 + 비용). 4-call이 5-call이 됨.

**옵션 C: Advanced 프롬프트에 통합 생성**
- Advanced가 어차피 논문/기술문서를 인용하므로 자연스러움
- 장점: Basic 프롬프트 단순화
- 단점: Advanced 출력이 이미 가장 긴데 더 길어짐. 품질 저하 위험.

**결정: 옵션 A.** 2026-03-15 설계에서 4-call 분리로 간 이유가 "출력 길이가 너무 길면 후반부 품질 저하"였음. Basic은 현재 5,400자 → 2,800자로 줄어들므로 references 배열 추가 여유 충분. Advanced는 오히려 줄어드니 references를 여기 두면 10,000자+13,000자가 되어 위험.

### 8.5 신규 섹션 프롬프트 블록 (초안)

아래는 새 프롬프트 블록의 핵심 문구 초안. 최종 프롬프트는 구현 단계에서 세부 조정.

**hero_news_context_ko:**
```
- **hero_news_context_ko**: 뉴스에서 이 용어가 실제로 등장하는 맥락 3줄.
  정확히 3줄. 각 줄 60자 이하. 형식: `"X"라고 나오면 → 이런 뜻`
  이 필드는 페이지 최상단 카드에 표시되어, 뉴스에서 온 독자가 본문을 읽지 않고도 졸업할 수 있게 함.
  BAD: "Transformer 기반 모델이 발표됐다고 하면 → 이 아키텍처를 핵심 구조로 쓴다는 의미이며, 최신 LLM 대부분이 그렇다."
      (한 줄이 너무 김, 설명적)
  GOOD: `"Transformer 기반" → 이 아키텍처 위에 만들었다는 뜻, 거의 모든 최신 LLM 해당`
```

**basic_ko_4_impact (통합 섹션):**
```
- **basic_ko_4_impact**: 이 개념이 "어디서 실제로 쓰이는가" + "왜 중요한가"를 하나로 엮어 4~5 bullet.
  각 bullet은 [실제 사용처] + [그래서 뭐가 달라졌는지] 2요소 포함.
  사용처는 실제 제품/서비스 이름 필수. 반사실("없었다면") 금지.
  BAD: "추천 시스템에 사용되어 정확도가 향상됐다" (일반론)
  GOOD: "Netflix 추천 알고리즘의 핵심 구성요소로 쓰여, 2023년 시청 세션당 클릭률 12% 상승을 자사 블로그에서 보고함"
  GOOD: "GitHub Copilot의 코드 자동완성이 이 기술 기반. 개발자 설문에서 55%가 '일상 도구'로 응답"
```

**references_ko:**
```
- **references_ko**: JSON 배열. 3~7개.
  최소 primary(논문/공식문서/공식 구현) 2개 필수.
  최대 secondary(블로그/해설) 3개.
  각 항목 필드: title, authors (optional), year (optional), venue (optional),
               type (paper|docs|code|blog|wiki|book), url, tier (primary|secondary),
               annotation (한 줄, 60자 이하).
  추측 URL 절대 금지. Reference Materials에서 확인된 URL만.
  확인 불가 항목은 제외.
```

**sidebar_checklist_ko:**
```
- **sidebar_checklist_ko**: 독자가 본문을 읽고 진짜 이해했는지 스스로 확인할 질문 4~5개.
  이 필드는 페이지 본문이 아닌 사이드바에 별도 렌더됨.
  각 질문 별도 bullet, `□ ` 접두사. 단순 암기 금지 — 이해를 확인하는 질문.
  BAD: "□ Transformer가 언제 발표됐는가?" (사실 암기)
  GOOD: "□ RNN 대비 Transformer의 병렬 처리 이점이 왜 가능한가?"
```

---

## 9. BASIC_TYPE_GUIDES / TYPE_DEPTH_GUIDES 업데이트

### 9.1 BASIC_TYPE_GUIDES

현재 10개 term_type별로 Basic 섹션에 어떤 톤/내용을 담을지 가이드. **구조 유지, 참조 키만 교체:**

- `basic_ko_0_summary` 참조 → 삭제 (해당 섹션 없음)
- `basic_ko_4_why` + `basic_ko_5_where` 참조 → `basic_ko_4_impact`로 통합
- `basic_ko_9_roles` 참조 → 삭제
- 나머지 참조는 유지

### 9.2 TYPE_DEPTH_GUIDES

Advanced 섹션 키 참조 업데이트:

- `adv_ko_1_technical` + `adv_ko_3_howworks` → `adv_ko_1_mechanism`
- `adv_ko_4_code` → `adv_ko_3_code`
- `adv_ko_10_when_to_use` → `adv_ko_4_tradeoffs`
- `adv_ko_11_pitfalls` + `adv_ko_5_practical` 후반부 → `adv_ko_5_pitfalls`
- `adv_ko_7_comm` → `adv_ko_6_comm`
- `adv_ko_9_related` → `adv_ko_7_related`
- `adv_ko_6_why`, `adv_ko_8_refs` 참조 → 삭제

### 9.3 TYPE_SECTION_WEIGHTS

(term_type, intent) → section weight 매핑. 각 weight dict의 섹션 키를 9.1/9.2 매핑대로 재작성. 내용 가중치 로직 자체는 유지.

---

## 10. Phenomenon/Problem 용어 적응 규칙 업데이트

현재 "Adaptive headings for phenomenon/problem terms" 블록이 Basic/Advanced 프롬프트 각각에 존재. 재설계 후:

**Basic (new):**
- `basic_ko_4_impact`: "어디서 쓰이는가" → "어디서 이 문제가 **발생하는가**"로 적응
- `basic_ko_6_comm`: 그대로 (대화 예시는 동일)

**Advanced (new):**
- `adv_ko_4_tradeoffs`: "언제 써야 하나" → "언제 **주의·완화**해야 하나"로 적응
- `adv_ko_5_pitfalls`: "도입 실수" → "**탐지·대응** 실수"로 적응

`9_roles` 적응 규칙은 해당 섹션 제거로 자동 소멸.

---

## 11. 프론트엔드 렌더링 영향

> 이 섹션은 구조 결정을 기록하는 용도. 구체 구현은 별도 plan.

### 11.1 [slug].astro 변경

- Header + definition 블록 아래 **Hero Card 컴포넌트** 추가 (`<HandbookHeroCard>`)
  - props: `definition`, `newsContext` (3줄 배열), `backUrl`
  - Level switcher 위에 위치. level과 무관하게 상시 렌더.
- 본문 영역은 기존 level switcher + innerHTML 교체 방식 유지
  - Basic body = §1~§7을 markdown으로 concat
  - Advanced body = §1~§7을 markdown으로 concat
- 본문 아래 **References Footer 컴포넌트** 추가 (`<HandbookReferences>`)
  - props: `references` (배열), primary/secondary 자동 정렬
  - Level 토글 시 깜빡임 없음
- `<HandbookSideRail>` 확장: `checklist` prop 추가
  - Basic 뷰일 때만 `<UnderstandingChecklist>` 블록 렌더
  - Advanced 토글 시 숨김

### 11.2 getHandbookDetailPageData 변경

현재 `body_basic_ko` / `body_advanced_ko` 단일 컬럼을 HTML로 변환해 전달. 변경 후:

- `definition_ko`, `hero_news_context_ko` 별도 반환
- `body_basic_ko` = §1~§7 concat (기존과 호환)
- `body_advanced_ko` = §1~§7 concat (기존과 호환)
- `references_ko` (JSON) 별도 반환
- `sidebar_checklist_ko` 별도 반환

### 11.3 DB 스키마 영향

- 기존 `body_basic_ko/en` `body_advanced_ko/en` 컬럼은 **유지** (concat된 markdown 저장용)
- 신규 컬럼:
  - `hero_news_context_ko` text
  - `hero_news_context_en` text
  - `references_ko` jsonb
  - `references_en` jsonb
  - `sidebar_checklist_ko` text
  - `sidebar_checklist_en` text

> 마이그레이션은 전량 regenerate 방침이므로 기존 데이터 매핑 스크립트 불필요.

---

## 12. "함께 읽으면 좋은 용어" 렌더링 전략

Orphan link 문제는 **렌더링 단계에서 해결.** 프롬프트 생성 단계는 자유롭게 둠.

```ts
// HandbookRelatedTerms 컴포넌트
relatedTerms.map(({ slug, label }) => {
  const term = lookupBySlug(slug);
  if (term?.status === 'published') {
    return <a href={`/${locale}/handbook/${slug}/`}>{label}</a>;
  }
  if (term?.status === 'draft') {
    return <span class="related-term-pending">{label} <small>(작성 중)</small></span>;
  }
  return <span class="related-term-planned">{label} <small>(예정)</small></span>;
});
```

- 용어 시드를 점점 채우는 계획과 정합성 있음
- "예정" 라벨이 visible → 학습 그래프가 자라는 신호
- 어드민이 "예정" 용어 목록을 다음 시드 후보로 활용 (선순환)

---

## 13. 구현 순서

1. **프롬프트 재작성** (이 plan의 §5, §8)
   - `prompts_advisor.py` 4개 프롬프트 (KO/EN × Basic/Advanced)
   - `prompts_handbook_types.py` 섹션 키 참조 업데이트
2. **models/advisor.py** Pydantic 모델 업데이트 — 신규 필드, 삭제 필드
3. **DB 마이그레이션** — 신규 컬럼 추가
4. **advisor.py `_run_generate_term`** — concat 로직 업데이트 (§1~§7만 body에 포함)
5. **전량 regenerate** — 기존 138개 published 용어
6. **프론트엔드 컴포넌트** — `HandbookHeroCard`, `HandbookReferences`, `UnderstandingChecklist`, `[slug].astro` 레이아웃 수정
7. **getHandbookDetailPageData** — 신규 필드 조회
8. **렌더링 status 분기** — `HandbookRelatedTerms`

---

## 14. Success Criteria

- [ ] Basic body_ko 길이 평균 2,800~3,500자 (±10%)
- [ ] Advanced body_ko 길이 평균 6,500~9,000자 (±10%)
- [ ] Basic vs Advanced 차별화 매트릭스(§7) 7항목 중 5항목 이상 통과
- [ ] 5개 용어(overfitting, DPO, Hugging Face, MCP, fine-tuning) 재생성 후 수동 리뷰 통과
- [ ] Hero card 3줄이 정확히 3줄, 각 60자 이하로 생성
- [ ] References 최소 primary 2개 / 최대 secondary 3개 규칙 통과율 100%
- [ ] 본문에서 "30초 요약"·"직군별 활용"·"이해 체크리스트"·"정석 자료" 섹션 없음
- [ ] Level 토글 시 references / hero card / sidebar checklist 깜빡임 없음

---

## 15. Related

- [[Handbook]] — 기능 스펙
- [[Handbook-Content-Rules]] — 콘텐츠 작성 규칙 (이 plan 반영 후 업데이트 필요)
- [[2026-03-15-handbook-quality-design]] — 이전 품질 설계 (섹션 구조가 이 plan으로 대체됨)
- [[ACTIVE_SPRINT]] — HQ-06, HQ-08, HQ-11, HQ-12의 재정의에 영향
