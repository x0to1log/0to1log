# Prompt Audit — 52개 이슈 수정 계획

> **작성일:** 2026-03-18
> **목적:** 전체 프롬프트 감사 결과 기반 품질/신뢰도/일관성 개선
> **대상 파일:** `prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`

---

## CRITICAL (P0) — 즉시 수정

### C1. URL hallucination 방지
- **현재:** "Reference links must be real URLs" — 지시만 있고 구조적 방지 없음
- **문제:** LLM이 존재하지 않는 URL 생성 (GPT-5.4 페이지에서 확인됨)
- **수정:** 프롬프트에 "Do NOT fabricate URLs. If unsure a URL exists, OMIT it" + 코드 `_validate_ref_urls()` 이미 있으니 프롬프트 강화만

### C2. Citation 번호-소스 매핑
- **현재:** Perplexity 스타일 `[1](URL)` 지시하지만 `[1]`이 어떤 소스인지 LLM에게 명시 안 됨
- **문제:** LLM이 가짜 번호를 달거나 URL 없이 번호만 쓸 수 있음
- **수정:** "Every [N] citation MUST use a URL from the provided news items. Never fabricate [N] without a real URL"

### C3. 제품명 사실 오류 방지
- **현재:** "확실한 사례만 작성" — 지시만 있고 검증 없음
- **문제:** "Google 번역이 BERT 사용" 같은 거짓 주장 발생
- **수정:** "제품-기술 매핑은 reference materials에 명시된 것만 사용. 추측 금지. 불확실하면 '~에 활용될 수 있다' 표현 사용"

---

## HIGH (P1) — 이번 스프린트

### H1. 토큰 비효율 제거
- handbook linking 블록 2곳 중복 → 상수 추출
- tone guide (BAD/GOOD) 2곳 중복 → 템플릿 추출
- "Respond in JSON format only" 8곳 반복 → 상수 추출
- **절감:** ~300+ 토큰/호출

### H2. Few-shot 예시 추가
- Quality check 프롬프트에 점수 예시 추가 (0점/50점/100점 각각 어떤 수준인지)
- Self-critique 프롬프트에 BAD/GOOD 예시 추가 (pass vs fail 케이스)
- Fact extraction 프롬프트에 confidence 기준 예시 추가

### H3. Score 해석 정의
- Self-critique: `score >= 75: accept, 50-74: revise, <50: restart`
- Quality check: `depth 0=정의만, 12=블로그 수준, 25=시니어 엔지니어 레퍼런스`
- `score = depth + accuracy + uniqueness + completeness (각 0-25, 합계 0-100)` 명시

### H4. 유형 분류 모호성 해소
- 모호한 예시 추가: "PyTorch = infrastructure_tool (프레임워크), GitHub Copilot = product_brand (상용 서비스)"
- "하이브리드 용어는 PRIMARY use case 기준으로 분류" 규칙 추가
- 유형 간 경계 명확화 (tool vs product, technique vs algorithm)

---

## MEDIUM (P2) — 다음 스프린트

### M1. 일관성 개선
- 필드명 표준화: `note` (설명용), `suggestion` (액션용), `reason` (판단 근거)
- Score 범위 통일: 0-100 정수로 통일 (0.0-1.0 제거)
- 날짜 형식: ISO 8601 (YYYY-MM-DD) 명시
- Tag 형식: "영어 소문자, 회사명은 원어 유지" 규칙 추가

### M2. 코드 품질 기준 명확화
- "15줄 이상" → "15줄 이상 (빈줄, 주석, 단독 괄호 제외)"
- "production-grade" → "에러 핸들링, 타입 힌트, 실제 라이브러리 사용 (torch, sklearn, pandas)"
- "표준 라이브러리 + 널리 사용되는 패키지만" 규칙 추가

### M3. 구조적 정리
- Section 헤더 형식 통일: "EN 작성 시 EN 헤더, KO 작성 시 KO 헤더. 혼합 금지"
- focus_items 형식 명시: "1문장, KO 15-40자, EN 5-12 words"
- excerpt vs one-line summary 차이 명확화: "excerpt=클릭 유도, summary=팩트 요약"

### M4. RANKING vs CLASSIFICATION 정리
- 중복 규칙 명확화: RANKING은 "1건/카테고리", CLASSIFICATION은 "3-5건/카테고리"
- 네이밍: `RANKING_SYSTEM_PROMPT` → `SELECTION_PROMPT` (혼동 방지)

### M5. 반복 제거 리팩토링
- `_HANDBOOK_SECTION_TEMPLATE` 상수 추출
- `_TONE_ASSERTIVE_GUIDE` 템플릿 추출
- `_JSON_RESPONSE_RULE` 상수 추출
- TYPE_DEPTH_GUIDES 구조 중복 제거

---

## 수정 파일

| 파일 | P0 | P1 | P2 |
|------|----|----|-----|
| `prompts_advisor.py` | C1, C3 | H2, H3 | M1, M2, M3, M5 |
| `prompts_news_pipeline.py` | C2 | H1 | M1, M3, M4 |
| `prompts_handbook_types.py` | — | H3, H4 | M5 |

---

## Related

- [[2026-03-18-handbook-advanced-quality-design]] — 심화 퀄리티 시스템
- [[Handbook-Prompt-Redesign]] — 프롬프트 아키텍처 v2
- [[2026-03-16-prompt-audit-checklist]] — 이전 감사 체크리스트
