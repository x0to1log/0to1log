---
title: Handbook Prompt Redesign
status: planned
created: 2026-03-15
tags:
  - ai-system
  - handbook
  - prompt
---

# Handbook Prompt Redesign

> 설계 기반: [[2026-03-15-handbook-quality-design]]
> 현재 프롬프트: `backend/services/agents/prompts_advisor.py` → `GENERATE_TERM_PROMPT`
> 파이프라인: [[AI-Handbook-Pipeline-Overview]]

---

## 현재 프롬프트 문제점

### 1. 언어 혼합 (가장 심각)

섹션 헤더가 KO/EN 이중 언어로 작성되어 있어 LLM 출력에서 언어가 섞임:

```
## 💡 이 개념은 뭘까? / What Is This?    ← KO+EN 혼합
## 🍎 쉽게 이해하기 / Easy Explanation    ← KO+EN 혼합
```

규칙에 "Korean headers for _ko fields, English headers for _en fields"라고 적혀 있지만, 템플릿 자체가 이중 언어이므로 LLM이 혼란.

**결과**: `body_basic_ko`에 영어 헤더가 섞이거나, `body_basic_en`에 한국어가 남음.

### 2. 섹션 구조 불일치

현재 프롬프트의 Basic 섹션 (6개):
```
💡 이 개념은 뭘까?
🍎 쉽게 이해하기
🔧 어디에 쓰일까?
⚠️ 알아두면 좋은 점
💬 이런 표현과 함께 써요
🔗 함께 알면 좋은 용어
```

새 설계의 Basic 섹션 (8개):
```
쉽게 이해하기 / Plain Explanation
예시와 비유 / Example & Analogy
한눈에 보기 / At a Glance              ← 신규 (비교표/설명표)
왜 중요한가 / Why It Matters            ← 신규 (독립 섹션)
실제로 어디서 쓰이나 / Where It's Used
주의할 점 / Precautions
대화에서는 이렇게 / Communication
함께 알면 좋은 용어 / Related Terms
```

현재 프롬프트의 Advanced 섹션 (7개):
```
💡 기술적 개요
🏗️ 작동 원리
✅ 실무 적용
❓ 왜 중요한가
⚠️ 주의사항과 한계
📚 참조 자료
🔗 연관 용어
```

새 설계의 Advanced 섹션 (9개):
```
기술적 설명 / Technical Description
핵심 수식 & 도표 / Key Formulas & Diagrams  ← 신규
동작 원리 / How It Works
코드 예시 / Code Example                    ← 독립 섹션으로 분리
실무 활용 & 주의점 / Practical Use & Precautions  ← 합침
왜 중요한가 / Why It Matters
업계 대화 맥락 / Communication              ← 신규
참조 링크 / Reference Links
관련 기술 & 비교 / Related & Comparison
```

### 3. 대화 맥락 누락

현재 Basic에 "이런 표현과 함께 써요"는 있지만, Advanced에는 **대화/회의 맥락 섹션이 없음**. 업계에서 이 용어가 어떤 맥락으로 쓰이는지 빠져 있음.

### 4. 수식/도표 지시 없음

수학 공식이 있는 용어(Z-Score, LASSO 등)에 대한 수식 포함 지시가 전혀 없음. Advanced에 "핵심 수식 & 도표" 전용 섹션 필요.

### 5. 용어 필드 부족

현재 출력 JSON:
```json
{ "korean_name": "한국어 용어명" }
```

새 설계 출력:
```json
{
  "term_full": "Long Short-Term Memory",
  "korean_name": "LSTM",
  "korean_full": "장단기 기억 네트워크"
}
```

`term_full`과 `korean_full` 생성 지시가 없음.

### 6. 톤/대상 지시 약함

- Basic: "accessible analogies, no assumed knowledge" 정도만 언급
- Advanced: "precise details, assumed CS fundamentals" 정도만 언급
- **구체적 대상 정의 없음** (Basic = 비개발자/PM/디자이너, Advanced = 시니어 개발자)

---

## 재설계 결정 사항

### 결정 1: KO/EN 헤더 분리 + 자연스러운 언어 혼합

- `_ko` 필드는 **한국어 섹션 헤더** 사용 (`## 쉽게 이해하기`)
- `_en` 필드는 **영어 섹션 헤더** 사용 (`## Plain Explanation`)
- 이중 언어 헤더 (`## 한국어 / English`) 금지
- **단, KO 본문 안에서 기술 용어는 영어 그대로 사용** — "Transformer", "API", "fine-tuning" 등은 한국어 기술 콘텐츠에서 자연스럽게 영어로 쓰임. 한국인 독자가 실제로 궁금해하는 영어 용어를 자연스럽게 녹이는 것이 중요.

### 결정 2: LLM 호출 2회 분리 (C안 확정)

| 호출 | 생성 필드 | 이유 |
|------|---------|------|
| **호출 1: 메타 + Basic** | term_full, korean_full, categories, definition_ko/en, body_basic_ko/en | 가벼운 필드 + Basic 분량 적음 |
| **호출 2: Advanced** | body_advanced_ko/en | 수식/코드/비교표가 포함된 가장 긴 콘텐츠에 집중 |

- 호출 2에 호출 1의 definition을 컨텍스트로 전달
- 기존 1회 호출 대비 퀄리티 향상, 비용은 ~$0.05 추가

### 결정 3: 비용/토큰 추적

News Pipeline의 `_log_stage()` 패턴을 핸드북에도 적용:
- `pipeline_type = "handbook.generate.basic"` / `"handbook.generate.advanced"`
- input/output 토큰, cost_usd, model_used, duration_ms, debug_meta 기록
- 어드민 analytics에서 News/Handbook 탭으로 분리 확인 가능

### 결정 4: 이모지 헤더 유지

현재 이모지 헤더(💡, 🍎, 📊 등) 유지 — 시각적 구분에 효과적.

### 결정 5: 프롬프트 재작성 완료

`GENERATE_TERM_PROMPT` 재작성 완료 (2026-03-15). 주요 변경:
- KO/EN 섹션 구조 완전 분리 (8+8 = 16개 템플릿 블록)
- Basic 8개 섹션 + Advanced 9개 섹션 명시
- `term_full`, `korean_full` 생성 지시
- 대상/톤 명확 정의
- 수식/도표/비교표 전용 섹션 추가

---

## 구현 파일

| 파일 | 변경 | 상태 |
|------|------|------|
| `backend/services/agents/prompts_advisor.py` | `GENERATE_TERM_PROMPT` 전체 재작성 | ✅ 완료 |
| `backend/models/advisor.py` | `GenerateTermResult`에 `term_full`, `korean_full` 추가 | ✅ 완료 |
| `backend/services/agents/advisor.py` | Generate 로직 2회 호출 분리 + `_log_stage()` 추가 | TODO |
| `frontend/src/pages/admin/pipeline-analytics.astro` | Handbook 탭 추가 | TODO |

---

## Related

- [[2026-03-15-handbook-quality-design]] — 전체 퀄리티 시스템 설계
- [[AI-Handbook-Pipeline-Overview]] — 파이프라인 구현
- [[Handbook-Content-Rules]] — 콘텐츠 작성 규칙
