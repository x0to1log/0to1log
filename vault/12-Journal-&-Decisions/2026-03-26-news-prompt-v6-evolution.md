# 뉴스 프롬프트 v6 진화 — 6회 반복, 56점에서 90점

> 날짜: 2026-03-26
> 관련: [[ACTIVE_SPRINT]], [[2026-03-25-research-news-quality]]

---

## 요약

3/25 뉴스 다이제스트 품질을 6번 반복 개선하여 평균 점수 56 -> 90으로 끌어올림.
핵심 발견: 모델 교체(gpt-4o vs gpt-4.1)는 효과 없었고, **프롬프트 구조 재설계**가 결정적이었음.

참고: KO citation이 없다고 평가했던 것은 WebFetch 도구가 한국어 페이지를 영어로 번역하면서 citation을 제거한 것이 원인. DB 확인 결과 KO에도 처음부터 EN과 동일하게 15개 citation이 정상 존재했음.

---

## 점수 이력

| 버전 | EN Biz | EN Res | KO Biz | KO Res | 평균 | 주요 변경 |
|------|--------|--------|--------|--------|------|-----------|
| v1 | 50 | 75 | 60 | 40 | **56** | 규칙만 (13개 writing rules) |
| v2 | 45 | 70 | 30 | 45 | **48** | gpt-4o 롤백 (A/B 테스트) |
| v3 | 85 | 90 | 65 | 60 | **75** | Few-shot skeleton (EN Business Expert 1개) |
| v4 | 92 | 88 | 80 | 75 | **84** | Full KO skeleton + 구조 동등성 가드 |
| v5 | 93 | 88 | 80 | 75 | **84** | 구조 동등성 (섹션/아이템/단락 수 기준) |
| v6 | 95 | 93 | 85 | 88 | **90** | 페르소나별 skeleton (4개 분리) |

참고: v3~v5의 KO 점수는 WebFetch 번역 오류로 citation이 누락된 것처럼 보여 낮게 평가했었음. citation이 처음부터 정상이었으므로 소급 보정함.

### Quality Score 트렌드 (자동 평가, gpt-4.1-mini)

| 날짜 | Business | Research | Expert | Learner | 비고 |
|------|----------|----------|--------|---------|------|
| 3/26 | **99** | **95** | E:100/95 | L:98/95 | v6 프롬프트 + 12000자 truncation |
| 3/25 | 88 | 69 | E:88/68 | L:88/70 | 4000자 truncation으로 뒷부분 섹션 오탐 |
| 3/24 | 85 | 65 | ? | ? | o4-mini (변별력 부족, 거의 항상 85) |

3/26 결과가 실제 콘텐츠 품질을 정확히 반영함을 확인:
- Business Expert 100점: 모든 섹션 존재, citation 매 단락, Strategic Decisions bullet 형식 완벽
- Research Learner 95점: "actor-critic paradigm, self-distillation 설명 부족" 감점 — 합리적
- 자동 publish 기준 (≥80) 설정을 위해 2~3일 추가 모니터링 필요

---

## 핵심 의사결정 & 배운 점

### 1. 모델이 아니라 프롬프트가 문제

gpt-4o vs gpt-4.1 A/B 테스트(v2) 결과 두 모델 모두 동일한 패턴으로 실패:
- 섹션 헤더 무시
- Citation 누락
- KO 콘텐츠 축약

결론: 지시 따르기 품질은 모델이 아닌 프롬프트 구조에 달려 있음.
결정: gpt-4.1 유지 (IFEval 87.4% vs gpt-4o 81%, 비용도 저렴).

### 2. Few-shot skeleton > 규칙 나열

v1(13개 규칙)은 56점. v3(같은 규칙 + skeleton 예시 1개)은 75점.
LLM은 지시사항보다 **완성된 예시**를 훨씬 정확히 따름. skeleton은 원하는 출력의 뼈대를 직접 보여줌.

### 3. 페르소나별 skeleton이 핵심

v3는 Business Expert skeleton 1개를 4개 페르소나가 공유.
결과: Research Learner가 Business Expert처럼 작성 (섹션도 톤도 다름).
v6에서 각 페르소나에 맞는 skeleton을 분리 -> Research Learner가 비유와 쉬운 표현을 먼저 사용.

### 4. KO는 글자 수가 아닌 구조 동등성으로 검증

"EN 길이의 80% 이상"은 잘못된 기준 — 한국어는 같은 내용을 영어보다 짧게 표현함.
"같은 수의 ## 섹션, ### 아이템, 단락"으로 변경.
v4부터 KO 커버리지가 EN과 동일해짐.

### 5. Sandwich 패턴이 체크리스트 항목에 효과적

프롬프트 최하단 FINAL CHECKLIST(8개 검증 항목)가 다음 항목의 준수율을 높임:
- Citation 형식
- 섹션 헤더 존재 여부
- KO = EN 동등성
- headline_ko 한국어 여부

### 6. Research Learner 접근성: "쉬운 말 먼저, 기술 용어 뒤에"

나쁜 예: "diffusion 기반 병렬 디코딩을 사용한다"
좋은 예: "한 글자씩 순서대로 읽는 대신 페이지 전체를 한 번에 처리한다 -- 이를 병렬 diffusion 디코딩이라고 한다"

이 규칙 + skeleton 예시가 Research Learner의 접근성을 실질적으로 개선. v6 출력에서 확인됨.

---

## 남은 과제

### 높은 우선순위
- ~~**KO citation 누락**~~: **해결됨** — DB 확인 결과 KO에도 15개 citation 정상 존재. WebFetch 도구의 번역 과정에서 citation이 제거되어 잘못 평가한 것.
- **페르소나별 출처 표시**: 백엔드에서 sources_expert/sources_learner 분리 저장 완료. 프론트엔드 탭 전환 시 출처 목록 교체 구현 완료 (ca04ef5).

### 낮은 우선순위
- **Vol.01 No.10 환각**: LLM이 프롬프트에 없는 에디토리얼 메타데이터를 추가. 무해하지만 거슬림.
- **EN Research Expert 톤 혼입**: Learner 스타일의 비유가 Expert 콘텐츠에 나타남 (skeleton 교차 오염 가능성).

---

## 기술 변경사항

### 프롬프트 (prompts_news_pipeline.py)
- 4개 skeleton 상수: BUSINESS_EXPERT_SKELETON, BUSINESS_LEARNER_SKELETON, RESEARCH_EXPERT_SKELETON, RESEARCH_LEARNER_SKELETON
- SKELETON_MAP이 (digest_type, persona) 조합에 맞는 skeleton을 라우팅
- _build_digest_prompt가 {skeleton} 보간으로 skeleton 파라미터를 수용
- Citation 형식: [Source Title](URL) -> [N](URL) Perplexity 스타일
- 수식: $$ 강제 (단일 $는 달러 표기와 충돌)
- sources 필드를 JSON 출력 스키마에 추가 (id, url, title)
- Research Learner 가이드: "기술 이름을 말하기 전에 그것이 무엇을 하는지 쉬운 말로 먼저 설명"
- FINAL CHECKLIST: 프롬프트 끝에 8개 검증 항목 (sandwich 패턴)
- Quality check 프롬프트를 현재 다이제스트 형식에 맞게 업데이트

### 파이프라인 (pipeline.py)
- KO headline fallback: 한국어 문자 없으면 "AI {type} 데일리 --" 접두사
- persona_sources: 페르소나별 출처를 따로 캡처하는 dict
- source_cards: 빈 URL 필터링 후 저장
- Quality check 모델: o4-mini -> gpt-4.1-mini (o4-mini가 빈 응답 반환)
- 균등 커버리지 규칙 적용
- 분석 섹션은 항상 필수 (생략 불가)

### 프론트엔드
- rehypeKatex를 rehypeSanitize 뒤로 이동 (수식 콘텐츠에서 500 에러 방지)
- personaSourceCardsMap: try-catch 가드 포함
- 탭 전환 시 출처 목록도 함께 교체 (updateSources 함수)

### 설정
- A/B 테스트 후 gpt-4.1을 기본 모델로 복원
- gpt-4.1-mini를 품질 체크 및 분류에 사용

### v6 이후 추가 수정 (3/27)

**뉴스 수집:**
- Tavily 쿼리 리밸런싱: research 4 + business 1 → research 3 + business 4 + common 1 (총 8개)
- New Tools 전용 쿼리 추가: "new AI tool product feature release update"
- 3단 fallback: Tavily → Exa → Google News RSS (Tavily 할당량 초과 시)
- Tavily 0건 시 wider date range 자동 재시도

**뉴스 분류:**
- 분류기 모델: o4-mini → gpt-4.1-mini (o4-mini 빈 응답 문제)
- cross-category dedup 제거: 같은 기사가 research + business 양쪽에 나올 수 있도록
- 분류 프롬프트: "Prefer ONE category" → "CAN and SHOULD appear in both" (기술+비즈니스 의미 모두 있는 뉴스)

**커뮤니티 반응:**
- 4개 페르소나에 Community Pulse 섹션 추가 (요약 1단락 + blockquote 인용 1~2개)
- 출처는 Reddit/Hacker News만 허용 (뉴스 매체 금지)
- 인용문 날조 금지, em dash 통일

**타임아웃 보호:**
- OpenAI SDK: 300초
- Tavily 검색: asyncio.wait_for(30초)
- 핸드북 용어 1개: 10분
- 핸드북 파이프라인 전체: 30분

---

## 다음 단계

1. **품질 점수 모니터링 (2~3일)** — 3일 연속 Business ≥ 85, Research ≥ 80 확인
2. **자동 publish 구현** — 점수 기준 충족 시 AUTOPUB-01 착수 (quality_score ≥ 80 → draft → published)
3. Weekly Recap 활성화 (뉴스 품질 안정 확인 후)
4. Vol.01 환각 메타데이터 제거
5. 하이브리드 품질 체크 고려 (코드 기반 규칙 + LLM 평가)

---

## 관련 문서
- [[2026-03-17-v4-two-persona-decision]] — 2 페르소나 결정
- [[2026-03-25-research-news-quality]] — 초기 품질 감사
- [[2026-03-24-3tier-model-decision]] — 모델 선정 근거
