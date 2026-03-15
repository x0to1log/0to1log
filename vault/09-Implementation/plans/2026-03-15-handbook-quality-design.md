# AI Handbook 퀄리티 시스템 설계

> 현재 구현: [[AI-Handbook-Pipeline-Overview]]
> 기능 스펙: [[Handbook]]
> 콘텐츠 규칙: [[Handbook-Content-Rules]]
> 이전 퀄리티 계획: [[2026-03-14-handbook-quality-plan]]

---

## 1. 용어 데이터 모델 확장

### 현재 (2개 필드)

| 필드 | 용도 |
|------|------|
| `term` | 영어 용어명 |
| `korean_name` | 한국어 용어명 |

### 확장 (4개 필드)

| 필드 | 용도 | 예시 (LSTM) | 예시 (Transformer) |
|------|------|-----------|-------------------|
| `term` | 메인 표기 (약어 우선) | LSTM | Transformer |
| `term_full` | 영어 풀네임 (항상 기록) | Long Short-Term Memory | Transformer |
| `korean_name` | 한국어 발음/통용 표기 | LSTM | 트랜스포머 |
| `korean_full` | 한국어 정식 명칭 | 장단기 기억 네트워크 | 트랜스포머 |

- 약어가 없는 용어는 `term = term_full`
- 한국어 발음과 정식 명칭이 같으면 `korean_name = korean_full`
- DB 마이그레이션: `term_full TEXT`, `korean_full TEXT` 컬럼 추가

---

## 2. Basic / Advanced 용도 정의

### Basic (기초) — "빠른 파악 + 비개발자"

**대상**: AI에 관심 있는 일반인 (PM, 디자이너, 경영진, 학생)
**사용 상황**: 뉴스/블로그 읽다 모르는 용어 → 팝업/카드로 빠르게 파악
**핵심 가치**: "이 용어를 이해하고, 대화에 참여할 수 있게"

### Advanced (심화) — "깊이 학습 + 개발자"

**대상**: 개발자, 엔지니어, 기술 리더
**사용 상황**: 용어 상세 페이지에 직접 들어와서 공부
**핵심 가치**: "코드와 아키텍처 수준으로 실무에 적용할 수 있게"

---

## 3. 섹션 구조

### Basic 섹션 (8개)

| # | 섹션 (KO / EN) | 설명 | 수량 |
|---|---------------|------|------|
| 1 | 쉽게 이해하기 / Plain Explanation | 비유, 일상 예시로 설명. 기술 용어 최소화. | — |
| 2 | 예시와 비유 / Example & Analogy | 실생활 비유, 도식, 유사 시스템에 빗댄 예시 | 3~4개 |
| 3 | 한눈에 보기 / At a Glance | 이해를 돕는 쉬운 비교표, 설명표, 단계표. 복잡한 수식 없이 시각적으로 정리. | 1~2개 |
| 4 | 왜 중요한가 / Why It Matters | 왜 알아야 하는지. 실생활/업무 연관성. | 4~5개 |
| 5 | 실제로 어디서 쓰이나 / Where It's Used | 제품, 서비스, 일상에서의 사용 사례. 현장 말투로 작성. | 4~5개 |
| 6 | 주의할 점 / Precautions | 흔한 오해, 함정, 잘못된 상식 (쉬운 언어) | 3~4개 |
| 7 | 대화에서는 이렇게 / Communication | 실제 대화/기사에서 이 용어가 등장하는 예시 문장 | 4~5개 |
| 8 | 함께 알면 좋은 용어 / Related Terms | 관련 핸드북 용어 + 한 줄 설명 | 4~6개 |

> [!note] "한눈에 보기" 섹션 가이드 (Basic)
> 수식 없이 쉬운 언어로 된 표. 예:
> - **비교표**: "GPU vs CPU — 뭐가 다를까?" (속도/용도/가격을 간단히 비교)
> - **단계표**: "Decision Tree가 결정하는 법" (질문→분기→결과를 단계별로)
> - **설명표**: "Z-Score로 보는 시험 성적" (점수→Z-Score→의미를 한눈에)

### Advanced 섹션 (9개)

| # | 섹션 (KO / EN) | 설명 | 수량 |
|---|---------------|------|------|
| 1 | 기술적 설명 / Technical Description | 기술적 정의 + 핵심 구성요소/흐름 | — |
| 2 | 핵심 수식 & 도표 / Key Formulas & Diagrams | 수학 공식, 구조도, 프로세스 단계표, 기술 비교표. 해당 없으면 생략 가능. | 해당 시 |
| 3 | 동작 원리 / How It Works | 내부 아키텍처, 알고리즘, 메커니즘 상세 | — |
| 4 | 코드 예시 / Code Example | 실제 코드 스니펫 또는 구현 패턴 (Python/JS 우선) | — |
| 5 | 실무 활용 & 주의점 / Practical Use & Precautions | 실무 사용 사례 + 오용 시 문제점/성능 이슈/보안 취약점 | 4~5 + 4~5 |
| 6 | 왜 중요한가 / Why It Matters | 기술/조직/비즈니스에 미치는 영향 | 4~5개 |
| 7 | 업계 대화 맥락 / Communication | PM·엔지니어 간 회의/문서에서 자주 등장하는 문장. 핵심 용어 굵게 표시. | 6~8개 |
| 8 | 참조 링크 / Reference Links | 공식 문서, 표준, 논문, 기술 블로그, GitHub | — |
| 9 | 관련 기술 & 비교 / Related & Comparison | 유사/경쟁 기술 차이점 + 관련 핸드북 용어 링크 | 4~6개 |

> [!note] "핵심 수식 & 도표" 섹션 가이드 (Advanced)
> - **수식**: 핵심 수학 공식 (예: `z = (x - μ) / σ`, `L₁ = λΣ|βᵢ|`)
> - **비교표**: 유사 기술 간 기술적 차이 (예: LASSO vs Ridge vs ElasticNet — 정규화 방식/특성 선택/수렴 속도)
> - **프로세스 표**: 기술적 단계 흐름 (예: KDD 5단계 상세, Decision Tree 분기 알고리즘 — Gini vs Entropy)
> - **구조도**: 아키텍처 시각화 (마크다운 표 또는 텍스트 다이어그램)
> - 수식이 없는 개념(예: API, REST)은 비교표/구조표만 포함해도 됨

---

## 4. 퀄리티 체크리스트

### 필수 포함 요소 (모든 항목)

- [ ] **대화 속 사용법**: 실제 대화 예시 문장이 Basic 4개+, Advanced 6개+ 포함
- [ ] **왜 중요한지**: 단순 정의가 아니라 "알아야 하는 이유" 서술
- [ ] **실제 사용 사례**: 제품/서비스/프로젝트에서의 구체적 활용 예시
- [ ] **주의점**: 흔한 오해, 함정, 또는 실수 최소 3개 (Basic), 4개 (Advanced)
- [ ] **표/도표**: Basic "한눈에 보기" 비교표/설명표 1개+, Advanced "핵심 수식 & 도표" 해당 시 포함

### 글자 수 기준

| 필드 | 최소 | 비고 |
|------|------|------|
| `definition_ko/en` | 80자 | 팝업/카드에 표시되는 짧은 정의 |
| `body_basic_ko/en` | 2,000자 | 8개 섹션을 충실히 작성하면 자연스럽게 충족 |
| `body_advanced_ko/en` | 3,000자 | 코드 예시 + 수식/표 포함 시 자연스럽게 충족 |

### 구조 검증

- [ ] Basic의 8개 섹션이 모두 H2(`##`)로 구분되어 있는가
- [ ] Advanced의 9개 섹션이 모두 H2(`##`)로 구분되어 있는가
- [ ] Basic 톤: 비유와 일상 언어 사용, 기술 용어 최소화
- [ ] Advanced 톤: 기술적으로 정확, 코드 포함, 현장 실무 톤

### Basic ↔ Advanced 차별화 검증

- [ ] Basic에는 코드가 없고, Advanced에는 코드가 있는가
- [ ] 같은 정보를 반복하지 않고, 각각의 대상에 맞게 작성되었는가

---

## 5. 프롬프트 개선 방향

### 현재 문제점

1. **섹션 구조 미지정**: 프롬프트가 "body_basic" 전체를 자유 형식으로 생성 → 일관성 없음
2. **대화 맥락 누락**: "대화에서 이 용어가 어떻게 쓰이는지" 지시 없음
3. **주의점 누락**: "흔한 실수나 오해"에 대한 지시 없음
4. **Basic/Advanced 차이 불명확**: 길이 차이만 있고, 대상과 톤 차이를 강조하지 않음
5. **용어 풀네임/한국어 정식 명칭**: 프롬프트에서 `term_full`과 `korean_full` 생성 지시 필요

### 프롬프트 재설계 원칙

- **섹션별 지시**: H2 헤더와 함께 각 섹션에서 무엇을 써야 하는지 명시
- **톤 가이드**: Basic → "중학생도 이해할 수 있게", Advanced → "시니어 개발자가 읽기에 충분하게"
- **필수 요소 체크**: 대화 예시, 실사용 사례, 주의점을 프롬프트에서 명시적으로 요구
- **EN+KO 동시 생성**: 현재 패턴 유지 (번역이 아닌 각 언어 네이티브 작성)
- **4개 명칭 생성**: term, term_full, korean_name, korean_full을 AI가 함께 생성

### 출력 JSON 구조 (확장)

```json
{
  "term_full": "Long Short-Term Memory",
  "korean_name": "LSTM",
  "korean_full": "장단기 기억 네트워크",
  "categories": ["ai-ml"],
  "definition_en": "...",
  "definition_ko": "...",
  "body_basic_en": "## Plain Explanation\n...\n\n## Example & Analogy\n...",
  "body_basic_ko": "## 쉽게 이해하기\n...\n\n## 예시와 비유\n...",
  "body_advanced_en": "## Technical Description\n...\n\n## How It Works\n...",
  "body_advanced_ko": "## 기술적 설명\n...\n\n## 동작 원리\n..."
}
```

---

## 6. 파이프라인 & 워크플로우 재설계

### 현재 흐름

```
뉴스 파이프라인 → 용어 자동 추출 (gpt-4o-mini)
                → 콘텐츠 생성 (gpt-4o)
                → draft 저장 → (방치됨)

어드민 수동 → 에디터에서 AI Generate → Apply → 저장 → 발행
```

### 개선 흐름

```
[자동 추출]
뉴스 파이프라인 → 용어 추출 → 중복 체크 → draft 저장
                                          ↓
[어드민 검수 대시보드]
draft 목록 → 용어별 퀄리티 점수 표시 → 어드민 확인
  ↓
  ├─ 승인 → published
  ├─ 수정 필요 → AI Regenerate → 재검수
  └─ 불필요 → archived (soft delete)

[퀄리티 게이트 강화]
발행 시 자동 검증:
  1. 글자 수 (기존)
  2. 섹션 구조 검증 (H2 7/8개 존재 확인)
  3. 필수 요소 검증 (대화 예시, 사용 사례 포함 여부)
  4. Basic/Advanced 모두 작성 확인
  5. term_full, korean_full 작성 확인
```

### 미완성 항목 (기존 plan에서 이관)

| 항목 | 우선순위 | 상태 |
|------|---------|------|
| Hard delete → Soft delete (archived) | HIGH | TODO |
| Content completeness dots (UI) | MEDIUM | TODO |
| 비용 최적화 (related_terms/translate → gpt-4o-mini) | LOW | TODO |
| Slug conflict pre-check (409) | LOW | TODO |
| SEO structured data (JSON-LD) | LOW | TODO |

---

## 7. 구현 로드맵

### Phase 1: 데이터 모델 + 프롬프트 재설계
- DB 마이그레이션: `term_full`, `korean_full` 컬럼 추가
- `prompts_advisor.py`의 `GENERATE_TERM_PROMPT` 재작성 (새 섹션 구조)
- `advisor.py`의 응답 모델에 `term_full`, `korean_full` 추가
- 프론트엔드 에디터에 새 필드 표시
- 테스트

### Phase 2: 퀄리티 게이트 강화
- 발행 시 섹션 구조 검증 로직 추가
- 필수 요소 체크 (프론트엔드 또는 백엔드)
- `term_full`, `korean_full` 필수 검증

### Phase 3: 워크플로우 개선
- Soft delete 구현
- 자동 추출 용어 검수 UX 개선
- 비용 최적화

---

## Related

- [[AI-Handbook-Pipeline-Overview]] — 현재 파이프라인 구현 상세
- [[Handbook]] — 핸드북 기능 스펙
- [[Handbook-Content-Rules]] — 콘텐츠 작성 규칙
- [[2026-03-14-handbook-quality-plan]] — 이전 퀄리티 계획 (Phase 1~3)
- [[Pipeline-Stage-Logging-Schema]] — 로깅 스키마 (향후 핸드북 AI 비용 추적에 활용)
