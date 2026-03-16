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

## 구현 파일

| 파일 | 변경 |
|------|------|
| `backend/services/agents/prompts_advisor.py` | EXTRACT_TERMS_PROMPT self-check, GENERATE 프롬프트 링크 강제 + 체크리스트 |
| `backend/services/pipeline.py` | 용어명 길이 검증 (3단어 이상 skip) |
| `backend/services/agents/advisor.py` | 생성 후 H2 수 + 링크 수 검증 → warning |

---

## Related

- [[2026-03-15-handbook-quality-design]] — 핸드북 퀄리티 시스템 설계
- [[Handbook-Prompt-Redesign]] — 프롬프트 재설계
