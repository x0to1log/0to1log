# 2026-03-31 Handbook Quality Overhaul

## What happened

Published 138개 + draft 155개의 핸드북 용어 품질을 전수 감사했다. 결과가 예상보다 심각해서 대규모 정리 + 파이프라인 개선 + 카테고리 재설계를 한 세션에 진행했다.

## Key decisions

### 1. 용어 추출 로직 전면 개선
- **프롬프트**: 3-point self-check → 5-point로 강화. "established term인가?", "standalone entry 가능한가?" 기준 추가
- **코드 필터**: blocklist(18개) + generic suffix 패턴 + semantic dedup 추가
- **truncation**: 8000자 → 24000자 (입력의 60% 유실 문제 해결)
- **기사별 독립 추출**: 합쳐서 1회 호출 → 기사별 병렬 호출 후 merge

### 2. Draft 83개 삭제
비기술 용어, 제품 specific, ad-hoc compound, 중복 등 핸드북에 부적합한 draft 용어 83개를 DB에서 삭제. 308개 → 225개.

### 3. 카테고리 11개 → 9개 재설계

| Old | New |
|-----|-----|
| ai-ml (172개, 81%) | llm-genai, deep-learning, ml-fundamentals로 분산 |
| db-data, backend, frontend-ux, network, os-core | cs-fundamentals + data-engineering으로 통합 |
| security | safety-ethics (AI 안전/윤리 포함 확장) |
| devops, performance | infra-hardware 통합 |
| web3 (0개) | 삭제, cs-fundamentals에 흡수 |
| ai-business | products-platforms |
| (신설) | math-statistics |

**핵심 이유**: "CS 기초 → AI 최전선" 학습 경로를 카테고리로 표현. ai-ml 블랙홀 해소.

결과: 최대 카테고리 llm-genai가 109개(51%)로, 기존 ai-ml 81%에서 크게 분산됨.

## What I learned

- **파이프라인 개선은 기존 데이터를 자동으로 고치지 않는다.** 프롬프트를 아무리 좋게 바꿔도 이미 생성된 "actionable intelligence" 같은 용어는 남아있다. 구세대 데이터 정리가 별도 작업으로 필요.
- **LLM의 confidence 판단은 거의 무의미했다.** 308개 중 queued(low confidence)는 2개뿐. LLM이 "IT 용어 = high"로 판단하기 때문. 5-point check + 코드 필터 이중 방어가 필수.
- **카테고리 재설계는 프론트엔드 추상화 덕에 쉬웠다.** 14개 페이지/컴포넌트가 2개 정의 파일에 의존하는 구조라 정의 파일만 바꾸면 전체 반영. 이 설계 결정이 유지보수 비용을 극적으로 줄임.
- **hallucination은 생성 시점에 잡아야 한다.** "열역학의 스테레오"처럼 정의 자체에 허위 정보가 들어가면 후속 수정 비용이 높다. self-critique loop 강화 필요.

## Impact

- 핸드북 용어 수: 308 → 225 (quality > quantity)
- 카테고리 분포: ai-ml 81% 집중 → 9개 카테고리 균등 분산
- 추출 정확도: 비기술 용어 유입 차단 (프롬프트 + 코드 이중 레이어)
- 학습 경로: cs-fundamentals → math-statistics → ml-fundamentals → deep-learning → llm-genai 순으로 읽을 수 있는 구조

## Files changed

- `backend/services/agents/prompts_advisor.py` — 추출 프롬프트 재설계
- `backend/services/agents/advisor.py` — truncation 24000자
- `backend/services/pipeline.py` — blocklist, semantic dedup, 기사별 독립 추출, 새 카테고리
- `frontend/src/lib/handbookCategories.ts` — 9개 카테고리 정의
- `frontend/src/lib/handbookCategoryIcons.ts` — 새 아이콘
- `frontend/src/pages/{en,ko}/handbook/index.astro` — 태그 매핑
- `frontend/src/components/newsprint/HandbookListRail.astro` — Rail 아이콘
- `backend/scripts/migrate_categories.py` — DB 마이그레이션 스크립트
- `vault/09-Implementation/plans/2026-03-31-handbook-quality-audit.md` — 감사 노트
