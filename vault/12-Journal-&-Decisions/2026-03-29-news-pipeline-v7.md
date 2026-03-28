# 결정: AI 뉴스 파이프라인 v7 — 품질 중심 전면 리팩토링

> 날짜: 2026-03-29
> 맥락: 3/28 뉴스 품질 평가에서 사용자 관점 평균 76점 → 반복 개선 → 롤백 → 선별 재적용을 거쳐 v7 확정
> 세션: 2026-03-28~29 연속 작업

---

## 배경

3/25 세션에서 수집 다변화(4개 소스), 분류 강화(litmus test, 0-5 룰)를 완료한 상태에서, 3/28 세션에서는 **실제 발행된 뉴스의 사용자 경험 품질**을 처음으로 종합 평가함.

3/28 뉴스(이전 파이프라인)를 사용자 관점 6개 기준(읽을 가치, 정보 밀도, 출처 신뢰, 차별화, 읽기 경험, KO 품질)으로 냉정하게 평가한 결과:

| 콘텐츠 | 점수 | 핵심 문제 |
|--------|------|----------|
| Research Expert EN | 72 | 논문 초록 확장판, 메리하리 없음 |
| Research Learner EN | 80 | Expert의 쉬운 복사본 |
| Business Expert EN | 78 | Google News RSS URL, 필러 항목 |
| Business Learner EN | 74 | 빈 섹션 placeholder |
| Research KO | 75 | EN 대비 43% 분량 |
| Business KO | 73 | 번역체, 출처 문제 |

5개 핵심 문제를 식별하고 순차 해결함.

---

## 문제 → 해결 → 결과

### #1. Google News RSS redirect URL

**문제:** Google News RSS fallback이 `news.google.com/rss/articles/CBMi...` 형식의 redirect URL을 그대로 저장. 사용자가 출처 링크를 클릭해도 원본 기사에 도달 불가.

**해결:** `googlenewsdecoder` 라이브러리로 수집 시점에 원본 URL 추출. `_resolve_google_news_url()` 함수 추가. Tavily/arXiv/HF/GitHub 소스는 원래 원본 URL이라 영향 없음.

**결과:** 이후 모든 run에서 Google redirect URL 0건 확인.

**커밋:** `68ee6a2`

---

### #2. 필러 항목 + 빈 섹션 placeholder

**문제:** (a) "OpenAI: Latest News and Insights" 같은 내용 없는 Google News 허브 페이지가 분류를 통과해 LLM이 3문단 필러를 생성. (b) Rule 11("빈 섹션 생략")과 Rule 12("모든 섹션 필수")가 충돌해 "(No items today)" placeholder 생성.

**해결:** (a) `pipeline.py`에서 body < 80자인 아이템을 LLM 전달 전 필터링. (b) Rule 11/12 표현 통일 — "빈 NEWS 섹션은 헤딩 자체를 쓰지 마라."

**결과:** 이후 필러 항목 0건, placeholder 0건.

**커밋:** `b304e6b`

---

### #3. 품질 체크 프롬프트 전면 재작성

**문제:** 품질 체크 프롬프트가 `pipeline.py`에 인라인, Expert EN만 평가, 섹션명 미명시("All 5 sections"), Research 0-5 룰 미반영.

**해결:**
- 프롬프트를 `prompts_news_pipeline.py`로 이동 (관리 통합)
- 2개 → 4개 분리: Research/Business × Expert/Learner
- Expert: Technical Depth / Analysis Quality
- Learner: Accessibility / Actionability
- Research 0-5 룰: "Do NOT penalize intentional omissions"
- `_check_digest_quality()` Expert+Learner 병렬 평가, 평균 score 반환

**결과:** Persona별 다른 잣대로 평가. Learner 품질도 추적 가능.

**커밋:** `b1fcf46`

---

### #4. Layered Reading Design (Expert ↔ Learner 차별화)

**문제:** Research Expert와 Learner가 5/5 동일 아이템, 동일 순서, ~70% 내용 겹침. Learner를 읽고 Expert로 전환해도 "이미 읽은 내용"의 기술적 버전일 뿐.

**사용자 시나리오:** "Learner로 이해 → Expert로 깊이 파기" 패턴에서 Expert가 새로운 가치를 제공해야 함.

**해결:** RESEARCH_EXPERT_GUIDE에 "Layered Reading Design" 블록 추가:
- Expert가 다루는 4개 priority layer: (1) prior work 비교, (2) 구체 벤치마크 delta, (3) 한계/주의사항, (4) 실무 신호
- "Assume the reader already knows WHAT each item is"
- 가드레일: "Only compare to prior work mentioned in the source" → 이후 "well-known examples from same domain" 허용으로 완화

**결과:** 3/19 backfill에서 Expert만의 새 정보 비율 2/6 → 3/6으로 개선. 한계점/실무 시사점이 Expert에만 등장.

**커밋:** `adef8a3`

---

### #5. WEIGHTED DEPTH (Lead story 강조)

**문제:** "EQUAL COVERAGE: Every news item deserves its full analysis" 룰이 모든 아이템을 동일 깊이로 작성하게 강제. 5개 × 1,500자 = 밋밋한 균등 배분. "오늘 뭐가 제일 중요한데?"가 안 보임.

**해결:** Rule 7을 "WEIGHTED DEPTH"로 교체:
- Lead story (1-2개): 3-4 문단 (Expert & Learner 동일)
- Supporting stories: Expert ≥3 문단, Learner ≥2-3 문단
- "The difference is WHAT they write, not how MUCH"
- 개별 가이드 5곳의 "3-4 paragraphs for ALL items" 충돌 제거

**결과:** 3/19 Business에서 HuggingFace(6p, 3,675ch) vs 나머지(3p, ~1,400ch) — Lead 확실히 구분. 3/26 v3에서도 T-MAP(6p) vs 나머지(3-4p) 작동 확인.

**커밋:** `ca425dc`, `ca94b14`, `4e12165`, `7438c20`

---

### #6. h2/h3 시각 계층 (프론트엔드)

**문제:** 뉴스 본문의 h2(섹션 제목: "Research Papers")와 h3(아이템 제목: "MetaClaw:")이 거의 동일한 크기/굵기로 렌더링. 스캔 시 계층 구분 불가.

**해결:**
- h2: 위에 구분선(`border-top: 1px solid`) + 여백 증가 → 섹션 전환 신호
- h3: 왼쪽 accent bar(`border-left: 3px solid accent`) + `font-weight: 600` + 크기 축소 → 아이템 마커
- `.newsprint-article .newsprint-prose` 스코프로 뉴스에만 적용 (용어집/블로그 미영향)

**커밋:** `ca94b14`, `bdcce7c`

---

### #7. Community Pulse 복구

**문제:** `collect_community_reactions()`가 Tavily API key를 필요로 하는데, key가 없어서 항상 빈 문자열 반환 → CP 섹션 전 날짜에서 0건.

**해결 (3단계):**
1. **HN Algolia + Reddit JSON API로 교체** — 무료, key 불필요 (`0955195`)
2. **실제 댓글 텍스트 수집** — 스레드 제목만이 아니라 상위 3개 실제 댓글을 가져옴. LLM이 인용을 날조하는 문제 해결 (`7730e6c`)
3. **CP 필수화** — Rule 15: "데이터가 입력에 있으면 MUST include." CHECKLIST 9번에 CP 확인 항목 추가 (`eb514f2`)

**결과:** 3/26 v3에서 Business Learner에 실제 Reddit 인용이 포함된 CP 섹션 최초 생성.

---

### #8. 마크다운 bold 후처리

**문제:** LLM이 `**Rejection Fine-Tuning(RFT)**` 같은 패턴을 생성하면 마크다운 파서가 bold를 인식 못 함. 사용자 화면에 `**` 기호가 그대로 노출.

**해결:** `pipeline.py`(뉴스)와 `advisor.py`(핸드북) 양쪽에 후처리 regex 추가:
```python
re.sub(r'\*\*([^*]+?)\(([^)]+)\)\*\*', r'**\1** (\2)', content)
```
`**term(abbr)**` → `**term** (abbr)` — bold를 먼저 닫고 괄호를 밖으로.

**커밋:** `7730e6c`

---

### #9. 롤백 + 선별 재적용

**문제:** `0d89ade` 이후 3개 커밋(anti-repetition, Business quality guard, CP placeholder 금지)이 복합적으로 품질을 떨어뜨림:
- Business quality guard → 5개 → 1개로 과교정
- CP placeholder 금지 → CP 완전 사망
- anti-repetition → 콘텐츠 축소

**해결:** `prompts_news_pipeline.py`를 마지막 검증된 상태(`7438c20`, 86.5점)로 롤백 후, 3건만 선별 재적용:
1. Rule 12 "do not INVENT sections" — 실제 문제(3/17 Business에 `## Papers` 생성) 해결
2. CP 규칙 공통화 — 토큰 절약, 기능 변경 없음
3. prior work 비교 완화 — well-known examples 허용

**재적용하지 않은 것:**
- Business quality guard (과교정)
- CP placeholder 금지 (CP 사망 원인)
- Rule 9 NO REPETITION (콘텐츠 축소)
- CHECKLIST "non-negotiable" (불필요한 강화)

**교훈:** 프롬프트 변경은 한 번에 하나씩 검증해야 함. 3개를 한 커밋에 넣으면 어떤 변경이 문제인지 분리 불가. "패치 위에 패치"보다 "롤백 후 선별 재적용"이 더 안전.

**커밋:** `759cd5c`

---

### #10. 분류 프롬프트 정합성

**문제:** 도입부 "Select 3-5 articles per category"와 Rule 1 "0-5"가 모순.

**해결:** 도입부에서 숫자 제거 → Rule 1이 유일한 기준.

**커밋:** `eb514f2`

---

## 품질 추이

| 날짜 | 파이프라인 | R Expert | R Learner | B Expert | B Learner | 평균 |
|------|-----------|----------|-----------|----------|-----------|------|
| 3/28 | v5 (이전) | 72 | 80 | 78 | 74 | **76.0** |
| 3/20 | v6 초기 | 82 | 85 | 80 | 83 | **82.5** |
| 3/19 | v6 완성 | 85 | 86 | 88 | 87 | **86.5** |
| 3/26 v2 | 과교정 | 78 | 75 | 55 | 58 | **66.5** |
| 3/26 v3 | v7 (롤백 후) | 86 | 83 | 85 | 87 | **85.3** |

→ v5(76) → v6(86.5) → 과교정(66.5) → v7(85.3)

---

## v7 최종 구성

### 수집 (`news_collection.py`)

| 소스 | 수집 범위 | 특이사항 |
|------|----------|---------|
| Tavily | 2일 | 메인 소스 |
| HuggingFace Daily Papers | 1일 | 커뮤니티 큐레이션 |
| arXiv API | 1일 (cs.AI/CL/LG) | submittedDate 필터 |
| GitHub Search | 3일 | topic: 태그 필터 + README excerpt |
| HN Algolia + Reddit JSON | 실시간 | 상위 댓글 텍스트 수집 (Community Pulse용) |

- Google News RSS URL → `googlenewsdecoder`로 원본 URL 추출
- 발행 URL 제외: 최근 3일 내 `news_posts.source_urls` 조회
- body < 80자 아이템 필터링 (필러 방지)

### 분류 (`CLASSIFICATION_SYSTEM_PROMPT`)

- Research: litmus test + NOT Research 리스트
- 0-5 룰: 기준 미달 시 빈 리스트 허용
- Cross-Category Rules: 양쪽 모두 가능 (다른 관점)

### 글쓰기 (`_build_digest_prompt`)

- **WEIGHTED DEPTH**: Lead 3-4p, Supporting Expert ≥3p / Learner ≥2-3p
- **Layered Reading** (Research Expert): prior work, delta, 한계, 실무
- **Rule 12**: 정의되지 않은 섹션 자의 생성 금지
- **Rule 15**: CP 데이터 있으면 필수 포함, 날조 금지
- **FINAL CHECKLIST**: 9개 항목 (CP 포함 여부 체크 추가)

### 품질 체크

- 4개 프롬프트: Research/Business × Expert/Learner
- Expert: Technical Depth / Analysis Quality
- Learner: Accessibility / Actionability
- 병렬 평가, 평균 score

### 후처리

- bold 괄호 fix: `**term(abbr)**` → `**term** (abbr)` (뉴스 + 핸드북)

### 프론트엔드

- h2: 위 구분선 (섹션 구분)
- h3: 왼쪽 accent bar (아이템 마커)
- 뉴스 전용 스코프 (`.newsprint-article .newsprint-prose`)

---

## 영향 받는 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/services/news_collection.py` | Google URL 해석, HN/Reddit 댓글 수집, 필러 필터 |
| `backend/services/agents/prompts_news_pipeline.py` | 분류/글쓰기/품질체크 프롬프트 전면 개선 |
| `backend/services/pipeline.py` | 품질체크 함수 확장, 필러 필터, bold 후처리 |
| `backend/services/agents/advisor.py` | 핸드북 bold 후처리 |
| `frontend/src/styles/global.css` | h2/h3 시각 계층 (뉴스 전용) |
| `backend/requirements.txt` | googlenewsdecoder 추가 |

## 커밋 목록

| 커밋 | 내용 |
|------|------|
| `68ee6a2` | Google News RSS URL 해석 |
| `b304e6b` | 필러 필터 + Rule 11/12 충돌 해소 |
| `b1fcf46` | 품질 체크 4개 프롬프트 |
| `adef8a3` | Layered Reading Design |
| `ca425dc` | WEIGHTED DEPTH |
| `ca94b14` | 문단 충돌 제거 + h2/h3 계층 |
| `bdcce7c` | h2/h3 뉴스 전용 스코프 |
| `4e12165` | 양쪽 persona 최소 문단 상향 |
| `7438c20` | 남은 문단 충돌 해소 |
| `0d89ade` | CP 공통화 + anti-repetition (이후 롤백) |
| `023405d` | 섹션 자의 생성 방지 |
| `0955195` | HN/Reddit API로 교체 |
| `8b6d11d` | Business guard + CP 금지 (이후 롤백) |
| `759cd5c` | **롤백 + 선별 재적용 (v7 기점)** |
| `7730e6c` | 실제 댓글 수집 + CP 필수화 + bold 후처리 |
| `eb514f2` | 3-5 vs 0-5 충돌 해소 + CP 체크리스트 |

## 교훈

1. **프롬프트 변경은 한 번에 하나씩 검증.** 3개를 한 커밋에 넣으면 문제 분리 불가.
2. **"패치 위에 패치"보다 "롤백 후 선별 재적용"이 안전.** 복합적 품질 하락은 근본 원인 분리가 어려움.
3. **사용자 관점 평가가 내부 점수보다 중요.** quality_score 92점이어도 사용자 경험은 72점일 수 있음.
4. **Learner가 짧아야 한다는 건 편견.** Learner는 설명이 더 필요하므로 Expert 이상으로 길 수 있음.
5. **Community Pulse는 실제 댓글이 있어야 의미.** 스레드 제목만으로 LLM이 인용을 날조함.

## Related

- [[2026-03-25-research-news-quality]] — 이전 세션 (수집 다변화, 분류 강화)
- [[ACTIVE_SPRINT]] — 현재 스프린트 상태
- [[AI-News-Pipeline-Design]] — 파이프라인 설계 원본
