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

## 재설계 원칙

### 원칙 1: KO/EN 섹션 구조 완전 분리

프롬프트 안에서 KO 템플릿과 EN 템플릿을 별도로 명시:

```
### body_basic_ko 섹션 구조:
## 쉽게 이해하기
## 예시와 비유
## 한눈에 보기
...

### body_basic_en 섹션 구조:
## Plain Explanation
## Example & Analogy
## At a Glance
...
```

### 원칙 2: 대상 명확 정의

```
body_basic 대상: 중학생도 이해 가능. PM, 디자이너, 경영진, 학생.
body_advanced 대상: 시니어 개발자가 읽기에 충분. 코드와 아키텍처 수준.
```

### 원칙 3: 필수 요소 명시적 요구

각 섹션에서 반드시 포함해야 하는 내용을 프롬프트에서 명시:
- 대화 예시 문장 (Basic 4~5개, Advanced 6~8개)
- 비교표/설명표 (Basic 1개+, Advanced 해당 시)
- 주의점 (Basic 3~4개, Advanced 4~5개)
- 실사용 사례 (Basic 4~5개, Advanced 4~5개)

### 원칙 4: 새 용어 필드 생성

```
term_full: 영어 풀네임 (약어가 있을 때)
korean_full: 한국어 정식 명칭
```

### 원칙 5: 이모지 헤더 유지/제거 결정

현재 이모지 헤더(💡, 🍎, 🔧 등) 사용 중 — 유지할지 제거할지 결정 필요.

---

## 구현 파일

| 파일 | 변경 |
|------|------|
| `backend/services/agents/prompts_advisor.py` | `GENERATE_TERM_PROMPT` 전체 재작성 |
| `backend/models/advisor.py` | `GenerateTermResult`에 `term_full`, `korean_full` 추가 |
| `backend/services/agents/advisor.py` | 응답 처리에 새 필드 반영 |

---

## Related

- [[2026-03-15-handbook-quality-design]] — 전체 퀄리티 시스템 설계
- [[AI-Handbook-Pipeline-Overview]] — 파이프라인 구현
- [[Handbook-Content-Rules]] — 콘텐츠 작성 규칙
