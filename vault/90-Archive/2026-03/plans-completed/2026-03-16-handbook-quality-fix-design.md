# 핸드북 자동 생성 퀄리티 개선

> 관련: [[2026-03-15-handbook-quality-design]], [[Handbook-Prompt-Redesign]]

---

## 발견된 문제 3가지

### 1. 비기술 용어 추출
- "data misinterpretation", "deep learning architecture" 같은 비기술/포괄적 용어가 핸드북에 들어옴
- LLM이 `ai-ml` 카테고리를 붙여서 코드 검증을 통과

### 2. 핸드북 링크 누락
- 콘텐츠에 `[용어](/handbook/slug/)` 링크가 하나도 없음
- 프롬프트에 지시는 있지만 LLM이 무시

### 3. 섹션 불완전
- Basic 8개 섹션 중 후반부(⚠️ 주의할 점, 💬 대화에서는 이렇게, 🔗 관련 용어)가 누락되는 경우

---

## 해결: 프롬프트 개선 + 코드 검증

### 프롬프트 개선 (90% 해결)

**`EXTRACT_TERMS_PROMPT`에 self-check 추가:**
```
## Self-check before including
Ask yourself: "Would a developer search for this term in a technical glossary?"
- "Transformer" → YES (specific technique with a clear definition)
- "Data Misinterpretation" → NO (general concept, not a technology)
- "Deep Learning Architecture" → NO (umbrella category, not a specific thing)
- "AUC" → YES (specific metric with a formula)
```

**`GENERATE_BASIC_PROMPT` / `GENERATE_ADVANCED_PROMPT`에 핸드북 링크 강제:**
- handbook_slugs를 system prompt뿐 아니라 **user prompt에도 포함**
- "You MUST use at least 3 handbook links in body_basic and at least 5 in body_advanced"

**`GENERATE_BASIC_PROMPT`에 섹션 체크리스트:**
```
## MANDATORY: Verify all 8 sections exist
Your body_basic MUST contain ALL of these H2 headers:
💡, 🍎, 📊, ❓, 🔧, ⚠️, 💬, 🔗
Missing any = invalid. Do not skip the last sections.
```

### 코드 검증 (10% 안전망)

**`_extract_and_create_handbook_terms()`에서:**
- 추출 후 용어명 검증: 3단어 이상이면 skip ("deep learning architecture" = 3단어 → skip)
- 또는 LLM에게 "이 용어가 핸드북에 적합한지" 2차 확인 (비용 추가)

**`_run_generate_term()`에서:**
- 생성 후 H2 헤더 수 체크 → 8개 미만이면 validation warning
- 핸드북 링크 수 체크 → 0개면 validation warning

---

## 1차 개선 (구현 완료)

- EXTRACT_TERMS_PROMPT self-check 예시
- GENERATE 프롬프트 mandatory checklist
- 코드: 3단어 초과 skip + H2/링크 수 warning

## 2차 개선: 근본적 프롬프트 아키텍처 변경

### 원칙 1: 핸드북 링크 → 코드 후처리로 이동
- 프롬프트에서 200개 slug 목록 + 링크 지시 **제거**
- LLM은 용어를 자연스럽게 쓰기만 함
- 생성 후 코드가 handbook_terms DB에서 매칭하여 자동 링크 삽입
- 프롬프트 30%+ 간소화 + 100% 링크 보장

### 원칙 2: 섹션 → JSON 키별 분리
- 마크다운 하나로 뭉치면 후반 섹션 생략됨
- 각 섹션을 별도 JSON 키로 분리 → 구조적으로 생략 불가
- 코드에서 나중에 `## 💡 + section_1 + ## 🍎 + section_2...`로 조합

### 원칙 3: 프롬프트 간소화
- 핸드북 링크 지시 제거 + 체크리스트 제거 → 핵심 지시만 남김
- LLM은 짧은 프롬프트를 더 잘 따름

## 구현 파일

| 파일 | 변경 |
|------|------|
| `backend/services/agents/prompts_advisor.py` | GENERATE 프롬프트 재구성 (JSON 키 분리, 핸드북 지시 제거) |
| `backend/services/agents/advisor.py` | 생성 후 JSON 키 → 마크다운 조합 + 핸드북 링크 후처리 |
| `backend/services/pipeline.py` | 핸드북 링크 후처리 함수 |

---

## Related

- [[2026-03-15-handbook-quality-design]] — 핸드북 퀄리티 시스템 설계
- [[Handbook-Prompt-Redesign]] — 프롬프트 재설계
