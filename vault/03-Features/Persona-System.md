# Persona System

[[AI-NEWS-Business-Writing\|AI-NEWS-Business]] 포스트를 독자 수준별로 재가공하는 RAG-based 시스템.

## 3가지 페르소나

| 페르소나 | 톤 & 스타일 | 디폴트 [[Prompt-Guides\|프롬프트]] 항목 |
|---|---|---|
| **입문자** (`content_beginner`) | 비유와 일상 언어 중심, 배경지식 없이 이해 가능 | [The One-Liner] |
| **학습자** (`content_learner`) | 핵심 개념 + 관련 학습 링크 + 맥락 | [Action Item] |
| **현직자** (`content_expert`) | 기술적 세부사항 + 업계 영향도 + 실무 적용 | [Critical Gotcha] |

## Locale × Persona 매핑

| 축 | KO | EN |
|---|---|---|
| **라벨** | 입문자 / 학습자 / 현직자 | Beginner / Learner / Expert |
| **톤 기준** | 친절하고 자연스러운 설명 + 한국 시장 맥락 | 간결하고 증거 중심 + 과장 금지 |
| **차이 허용** | 비유/예시의 현지화 허용 | 요약 밀도 최적화 허용 |
| **불변 조건** | 사실/수치/출처는 EN canonical과 일치 | 사실/수치/출처가 기준 원본 |

## Locale별 톤 가드레일

| 구분 | EN | KO |
|---|---|---|
| **톤** | concise, evidence-first, no hype | 친절/명료, 번역투 금지 |
| **문장** | 짧은 문장, 신호 중심 압축 | 문맥 연결 강화, 독자 이해 우선 |
| **리스크** | 제한점/불확실성 명시 필수 | 한계/주의점 한국어로 명확화 |
| **금지** | 과장형 CTA, 근거 없는 단정 | 직역체, 영어 문장 구조 직수입 |
| **공통** | 수치·비용·성능 주장에 출처 링크 포함 | 수치·비용·성능 주장에 출처 링크 포함 |

## 전환 UX

- **적용 범위:** Business 포스트 + Study 카테고리. Research는 단일 버전 (Switcher 없음)
- **기본값:** 로그인 사용자 `DB > 쿠키 > beginner` / 비로그인 `쿠키 > beginner`
- **전환:** 포스트 상단 탭에서 자유 전환
- **언어 전환:** `translation_group_id` 기준 KO↔EN 이동
- **Phase 4:** 프로필에 저장, 기기 간 동기화

## 구현

- Agent: [[AI-News-Pipeline-Design#business-agent\|Business Analyst]]
- DB: [[Database-Schema-Overview#persona-columns\|persona 컬럼 구조]]
- UI: [[Component-States#PersonaSwitcher\|Persona Switcher]]

## Related
- [[Daily-Dual-News]] — 페르소나가 적용되는 뉴스 기능
- [[AI-News-Product]] — 페르소나 기반 AI News 제품

## See Also
- [[AI-News-Pipeline-Design]] — 페르소나 생성 파이프라인 (04-AI-System)
