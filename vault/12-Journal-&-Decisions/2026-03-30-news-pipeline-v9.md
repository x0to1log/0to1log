# 결정: AI 뉴스 파이프라인 v9 — 다중 소스 + 코드 기반 citation 관리

> 날짜: 2026-03-30
> 맥락: v8(90점)에서 citation 번호 리셋, 소스 1개 한계, source_cards 불일치를 발견하고 구조적 해결
> 세션: 2026-03-30 작업 (6 커밋)

---

## 배경

v8에서 내용 품질은 90점으로 안정됐지만, backfill(3/21, 3/22) 검증에서 citation 구조적 문제가 드러남:

### 발견된 3가지 구조적 문제

**1. Writer가 기사 1개만 보고 작성**
- `raw_content[:4000]` — 1개 소스의 관점만 반영
- "OpenAI $110B 투자"를 TechCrunch 1개만 참조해서 작성
- 같은 이벤트를 다룬 Reuters, 공식 블로그가 별도 아이템으로 분류되거나 탈락

**2. Citation 번호가 섹션마다 리셋**
- LLM이 각 `###` 블록을 독립적으로 써서 `[1]`부터 다시 시작
- Business Expert: `[1]`이 첫 섹션에서는 Reuters, 두 번째에서는 openai.com
- source_cards 19개인데 본문은 `[1]-[4]`만 반복 — 매핑 불일치

**3. source_cards가 LLM 생성이라 본문과 불일치**
- LLM이 sources JSON을 만들지만, 본문의 citation 번호와 매핑이 안 됨
- dedup 후처리로도 해결 불가 — 근본적으로 번호 체계가 다름

---

## 결정

### A. 다중 소스 수집 (Multi-Source Enrichment)

```
이전: 수집 → 분류 → 커뮤니티 → 랭킹 → 글쓰기(기사 1개 × 4000자)
이후: 수집 → 분류 → 커뮤니티 → 랭킹 → ★2차 수집 → 글쓰기(기사 1~4개 × 전문)
```

**enrich_sources()** 함수 신규 추가 (`news_collection.py`):
- 각 ranked 아이템의 URL로 `exa.find_similar_and_contents()` 호출
- 48시간 날짜 필터 (`start_published_date`/`end_published_date`)로 같은 시기 기사만
- 원본 포함 최대 4개 소스, 40자 미만 빈 페이지 자동 제외
- 전체 아이템 대상 (LEAD + SUPPORTING)
- 병렬 호출 (`asyncio.gather`)로 latency 최소화
- API 실패 시 원본 1개로 graceful fallback

**설계 결정 (5건):**

| # | 결정 | 선택 | 이유 |
|---|------|------|------|
| 1 | 글자 제한 | 제한 없음 (전문) | gpt-4.1 컨텍스트의 3-5%, 비용 ~$0.03 |
| 2 | 2차 수집 방법 | Exa find_similar | URL 기반 정확도 높음, 키워드 재검색 불필요 |
| 3 | 소스 상한 | 최대 4개 | 원본 + 3, 다각도 충분하면서 과하지 않음 |
| 4 | 이벤트 판별 | 날짜 필터만 | find_similar + 48h 필터로 충분, LLM 판별 불필요 |
| 5 | 대상 | 전체 | 비용 미미, SUPPORTING 품질도 향상 |

**Writer 입력 포맷 변경:**

Before:
```
### [LEAD] [llm_models] Article Title
Source URL (MUST cite this): https://...

{body — 4000자}
```

After:
```
### [LEAD] [llm_models] Article Title

Source 1: https://techcrunch.com/...
{content_1 — 전문}

Source 2: https://theverge.com/...
{content_2 — 전문}
```

**커밋:** `eb69b62`

### B. Citation 넘버링 코드 후처리 전환

v8까지는 LLM이 citation 번호를 매겼으나, **섹션별 리셋 문제가 프롬프트로 해결 불가**함을 확인. 역할을 분리:

| 역할 | 담당 | 내용 |
|------|------|------|
| LLM | citation 삽입 | 문단 끝에 `[N](URL)` 넣기 — 번호는 아무거나 |
| 코드 | 넘버링 | URL 등장 순서대로 순차 번호 부여 |
| 코드 | 소제목 집계 | 각 `###` 섹션의 citation을 소제목에 모으기 |
| 코드 | source_cards 생성 | 본문 URL에서 추출 → 순차 ID 부여 |

**_renumber_citations()** 함수 신규 추가 (`pipeline.py`):
- 본문의 모든 `[N](URL)` 을 정규식으로 탐색
- URL 첫 등장 순서대로 1, 2, 3... 재번호
- 같은 URL은 같은 번호 (중복 없음)
- source_cards도 동시 생성 (LLM sources 필드 무시)

**후처리 순서 (v9):**
```
bold fix → tag strip → ★renumber citations → aggregate headings
```

**source_cards 생성 주체 변경:**
- v8: LLM의 `data["sources"]` → `_dedup_source_cards()` → DB
- v9: `_renumber_citations()` → source_cards 직접 반환 → DB (LLM sources 무시)

**커밋:** `87443a2`, `b3d4a4e`

### C. 프롬프트 간소화

**Rule 1 (CITATION FORMAT):**

Before (v8):
```
Number citations sequentially across the entire article.
- News items: Cite the source ONCE after the item title.
  Format: `### Item Title [1](URL)`
```

After (v9):
```
Cite at the END of each paragraph with the source(s) used. Format: `...content. [1](URL)`
- Use [N](URL) format where N is any number. Use different citations in different paragraphs when multiple sources are provided.
```

**sources 필드 규칙:**

Before: "The number of sources MUST match the highest citation number in the body"
After: "Citation numbers will be auto-corrected by post-processing, so exact id matching is not required"

**Quality check:**
- "Source Citations" → "Source Quality" (다중 소스 종합 평가)
- "multiple sources are synthesized (not just one perspective)" 기준 추가

**프롬프트 사고 교훈:**
- `[](URL)` 빈 괄호 포맷을 예시로 넣었더니 3/4 페르소나에서 citation 완전 누락
- "번호는 중요하지 않다"고 말하면 LLM은 citation 자체를 안 함
- 해결: `[1](URL)` 숫자 포함 포맷으로 복원, 코드가 뒤에서 조용히 교정

**커밋:** `90b56bd`, `b3d4a4e`

---

## v9 파이프라인 흐름 (최종)

```
6개 소스 병렬 (Tavily + HF Papers + arXiv + GitHub + Exa + Google RSS)
    | 50-60 candidates/day
    v
URL dedup + 발행 이력 제외 (3일) + Google News URL 해석 + 필러 필터
    v
★ merge+classify (gpt-4.1-mini) — 같은 이벤트 그룹화 + Research/Business 분류 동시
    → 0-5 그룹/카테고리 (그룹 = 같은 이벤트의 기사 1~N개)
    v
커뮤니티 수집 (HN Algolia + Reddit JSON) — 그룹 내 모든 URL
    v
랭킹 (gpt-4.1-mini) → [LEAD]/[SUPPORTING] 그룹 단위 판단
    v
★ 조건부 enrich (Exa find_similar) — 소스 1개뿐인 그룹만 보충
    v
글쓰기 (gpt-4.1, max_tokens=32K) — 그룹 내 다중 소스 × 전문
    v
후처리: bold fix → tag strip → ★citation renumber (URL 기반 순차)
    v
품질 체크 (o4-mini × 4) — Source Quality 기준 (제공 소스 수에 맞게 평가)
    v
DB 저장 (source_cards = 코드 추출) → Admin 확인 → 발행
```

---

## 비용 영향 (실측)

### 실제 파이프라인 비용 비교

> 주의: `summary` 스테이지는 다른 스테이지의 누적 합계이므로 제외하고 계산.

| 날짜 | 버전 | 총 토큰 | 총 비용 | Research Expert | Business Expert | 비고 |
|------|------|---------|---------|----------------|-----------------|------|
| 3/20 | v8 | 169,592 | **$0.46** | 29,280 ($0.09) | 47,155 ($0.13) | 1소스 × 4000자 |
| 3/22 | v9 enrich only | 333,334 | **$0.77** | 103,626 ($0.24) | 55,617 ($0.14) | merge 없이 enrich만 → 입력 폭발 |
| **3/30** | **v9 + merge** | **164,375** | **$0.45** | 37,301 ($0.12) | 36,376 ($0.11) | merge+조건부enrich → **v8 수준으로 복귀** |

### 비용 변화 분석

**v9 초기 (enrich만, merge 없음)**: $0.46 → $0.77 (67% 증가)
- Research Expert가 29K → 103K 토큰 (3.5배) — 5개 아이템 × 4소스 × 전문
- Business는 47K → 56K (1.2배)

**v9 + NQ-16 merge (최종)**: $0.77 → **$0.45** (42% 감소, v8 이하)
- merge가 같은 이벤트 기사를 묶어서 입력 중복 제거
- 조건부 enrich: 소스 2개 이상 그룹은 Exa 호출 스킵
- Research Expert: 103K → **37K** (65% 감소) — merge 효과가 가장 큼
- Business Expert: 55K → **36K** (35% 감소)
- 4개 페르소나 토큰이 균등해짐 (36-37K 범위)

### 스테이지별 비용 (3/30 최종, summary 제외)

| 스테이지 | 토큰 | 비용 | 비중 |
|----------|------|------|------|
| classify (merge 포함) | 6,231 | $0.005 | 1.1% |
| ranking | 908 | $0.0004 | 0.1% |
| enrich (조건부) | — | ~$0.001 | 0.2% |
| digest:research (expert+learner) | 73,382 | $0.22 | 50% |
| digest:business (expert+learner) | 72,527 | $0.21 | 48% |
| quality check × 2 | 11,327 | $0.005 | 1.1% |
| **합계** | **164,375** | **$0.45** | |

**핵심**: merge로 입력 중복을 제거하면서 비용이 v8 수준으로 돌아왔고, 품질은 다중 소스 분석으로 더 높아짐.

---

## 교훈

### 1. LLM은 콘텐츠, 코드는 구조

v8까지 "LLM에게 잘 시키면 된다"는 접근이었지만, citation 넘버링처럼 **정확한 순서 관리는 LLM의 약점**이다. LLM이 잘하는 것(어떤 소스를 어디에 인용할지)만 시키고, 코드가 보장할 수 있는 것(순차 번호, source_cards 매핑)은 코드에 맡기는 게 더 안정적.

### 2. LLM에게 "중요하지 않다"고 말하면 안 된다

`[](URL)` 빈 괄호 + "번호는 중요하지 않다"가 citation 완전 누락을 유발. LLM은 "중요하지 않다"를 "안 해도 된다"로 해석한다. **코드가 뒤에서 교정한다는 사실을 LLM에게 알릴 필요가 없다.**

### 3. 다중 소스는 글자 제한 해제와 함께 와야 의미 있다

기사 3개를 가져와도 4000자 제한이면 첫 번째 기사만 들어간다. `[:4000]` 제거 후에야 다중 소스의 실질적 가치가 발현. gpt-4.1 컨텍스트(1M)에 비하면 입력 3-5%로 여유 넉넉.

### 4. 소제목 citation은 가독성을 해친다

처음에는 `### Title [1][2][3]`처럼 소제목에 citation을 집계하는 후처리를 넣었으나, 실제 읽을 때 제목 읽기를 방해. skeleton에서도 제거하고, 후처리 코드도 삭제. citation은 본문 문단 끝에만 존재하면 충분.

### 5. merge 없는 enrich는 입력 폭발을 일으킨다

enrich만 도입하면 5아이템 × 4소스 × 전문 = 84K 토큰(Research). merge가 같은 이벤트 기사를 묶으면 중복 소스가 자연스럽게 정리되고, 조건부 enrich로 API 호출도 줄어든다. **enrich는 merge 이후에 보충 역할만 해야 한다.**

### 6. merge 규칙은 예시가 필수다

"same topic"이라고 쓰면 LLM이 논문 5개를 "AI research"로 묶어버린다. ✅/❌ 구체적 예시를 넣어야 의도대로 동작. Show Don't Tell 원칙이 분류기에서도 적용됨.

### 7. 비용과 품질은 동시에 개선할 수 있다

v9 초기($0.77)에서 merge 추가 후 $0.45로 42% 감소, 동시에 Research Expert 출력은 3,744자 → 11,059자로 3배 증가. **입력 중복 제거가 비용 절감과 품질 향상을 동시에 달성.**

---

## v9 안정화 단계 (3/30~31)

### NQ-16 v1→v2: classify/merge 분리

**v1 실패 (classify+merge 동시):**
- 3/16: Research papers 10개를 한 그룹으로 과묶기
- 3/30: Research papers 5개 한 그룹
- 원인: LLM이 "분류"와 "묶기"를 혼동 — subcategory가 같으면 전부 묶음
- ✅/❌ 예시 추가해도 해결 안 됨 → 프롬프트로 해결 불가능한 구조적 문제

**v2 해결 (classify/merge 분리):**
```
classify(개별 7-8개) → merge(선별 기준 + 전체 50개에서 같은 이벤트 매칭) → 이후 기존 흐름
```
- classify: v8 방식 복원 (개별 아이템, 그룹 아님) — 검증된 로직
- merge: 별도 LLM 호출, 선별된 아이템 기준으로 전체 후보에서 매칭
- 추가 비용: ~$0.002 (gpt-4.1-mini 1회)
- ClassificationResult에 `research_picks`/`business_picks` 추가 (flat → grouped 2단계)

**merge 파싱 버그:**
- LLM이 items를 `["url"]` 문자열 배열로 반환 → dict 기대하는 코드에서 매칭 실패
- 같은 URL 중복 삽입 (자기 자신과 묶기)
- 해결: string/dict 양쪽 파싱 + seen_urls dedup

**커밋:** `074966d`, `bbd1e5c`, `635ae11`

### Citation 안정화

**빈 괄호 사고:**
- `[](URL)` 포맷 예시를 넣었더니 3/4 페르소나에서 citation 완전 누락
- "번호는 중요하지 않다"고 말하면 LLM은 citation 자체를 안 함
- 해결: `[1](URL)` 숫자 포함 포맷 복원, 코드가 뒤에서 조용히 교정

**One-Line Summary citation:**
- LLM이 "every paragraph" 규칙을 한 줄 요약에도 적용
- 해결: "One-Line Summary does NOT need citations" 명시

**heading citation 제거:**
- `### Title [1][2][3]` — 소제목에 citation 집계하면 제목 읽기 방해
- skeleton에서 제거 + 후처리 코드도 삭제
- citation은 본문 문단 끝에만 존재하면 충분

**프론트엔드 superscript:**
- `[1](URL)` 렌더링 → subscript `[1]` 스타일 (muted, hover accent)
- `::before`/`::after`로 `[]` 괄호 CSS 생성

**source_cards title 누락:**
- `_renumber_citations()`가 source_cards를 만들 때 title 빈값
- `_fill_source_titles()`로 LLM sources의 title을 URL 매칭해서 채움

**커밋:** `b3d4a4e`, `8b5c8fa`, `81c60cc`, `5c30734`

### Quality Check 수정

- "Source Citations" → "Source Quality" (다중 소스 종합 평가)
- "multiple sources synthesized" → "all provided sources utilized" — 소스 1개뿐인 그룹도 정당하게 평가

**커밋:** `848fd75`

### 수집 다변화

**카테고리 페이지 필터:**
- `techcrunch.com/category/`, `economist.com/topics/` 같은 비기사 URL이 classify를 통과
- 코드 필터: `/category/`, `/topics/`, `/tag/`, `/archive/`, 도메인 루트 차단
- classify 프롬프트에도 NO/YES URL 예시 추가

**Exa 쿼리 확대:**
- 4개 → 8개 (enterprise deployment, chip/hardware, pricing, workforce 추가)
- 3/18 수집량: 21개 → 45개 (2배 이상)

**Brave Search API 수집기:**
- `_collect_brave()` 신규 — 4개 뉴스 쿼리, `freshness=pd`(하루)
- 6개 수집기 병렬 실행 (Tavily + HF + arXiv + GitHub + Exa + Brave)
- API 키 미설정 시 graceful skip

**merge 로그 강화:**
- `debug_meta`에 `llm_output` 저장 — 어드민에서 merge가 어떻게 묶었는지 확인 가능

**커밋:** `194456e`, `5a24702`

---

## 커밋 목록 (전체)

### Phase 1: 다중 소스 + Citation 코드화
| 커밋 | 내용 |
|------|------|
| `eb69b62` | **다중 소스 enrichment** — Exa find_similar + 4000자 제한 제거 |
| `87443a2` | **citation 넘버링 코드 후처리** — _renumber_citations + source_cards 코드 추출 |
| `b3d4a4e` | citation 포맷 예시 복원 — `[](URL)` 빈 괄호가 citation 누락 유발 |
| `81c60cc` | heading citation 제거 — skeleton + 후처리 코드 삭제 |
| `5c30734` | citation superscript UI + source_cards title 복원 |

### Phase 2: NQ-16 merge+classify
| 커밋 | 내용 |
|------|------|
| `3c61ffc` | **NQ-16 v1 merge+classify 통합** — 분류기가 같은 이벤트 그룹화 |
| `bbd1e5c` | ClassifiedGroup .url → .primary_url 수정 |
| `d80968b` | merge 규칙 강화 — ✅/❌ 예시로 과도한 묶기 방지 |
| `848fd75` | quality check Source Quality 기준 수정 |

### Phase 3: NQ-16 v2 classify/merge 분리
| 커밋 | 내용 |
|------|------|
| `074966d` | **NQ-16v2 classify/merge 분리** — 과묶기 근본 해결 |
| `8b5c8fa` | One-Line Summary citation 제외 + merge 로그 llm_output 추가 |
| `635ae11` | merge 파싱 — string/dict 양쪽 지원 + URL dedup |

### Phase 4: 수집 다변화
| 커밋 | 내용 |
|------|------|
| `194456e` | classify에 카테고리/토픽 페이지 제외 규칙 추가 |
| `5a24702` | **카테고리 페이지 필터 + Exa 쿼리 8개 + Brave Search 수집기** |

---

## 품질 추이 (v9)

| 날짜 | Research | Business | 비용 | Sources R/B | 비고 |
|------|----------|----------|------|------------|------|
| 3/20 (v8) | 95 | 96 | $0.46 | 8/8 | baseline |
| 3/22 (v9 enrich only) | 94 | 95 | $0.77 | 8/19 | 입력 폭발, Research Expert 축소 |
| 3/30 (v9 + merge v1) | 94 | 95 | $0.45 | 15/12 | merge 과묶기 발생 |
| 3/16 backfill (v2 초기) | 94 | 95 | — | 12/11 | papers 10개 과묶기 |
| 3/17 backfill (v2 + dedup fix) | 95 | 96 | — | 15/4 | Business 소스 부족 |
| **3/18 backfill (v2 안정)** | **95** | **95** | — | **16/10** | merge 정상, 수집 다변화 효과 |

---

## 교훈 (추가)

### 8. classify와 merge는 분리해야 한다

한 호출에서 "뭐가 중요한가" + "같은 이벤트인가"를 동시에 시키면 LLM이 subcategory 기준으로 과묶기한다. 각각 단순한 작업으로 분리하면 둘 다 잘한다. 추가 비용 $0.002로 구조적 안정성 확보.

### 9. LLM 출력 포맷을 가정하지 마라

merge LLM이 `{"url": "..."}` dict 대신 `"url"` string을 반환해도 파싱이 되어야 한다. `isinstance(item_data, str)` 체크 한 줄로 해결. 방어적 파싱이 필수.

### 10. 수집 다양성이 최종 품질을 결정한다

Exa 쿼리 4→8개 확대 + 카테고리 페이지 필터로 3/17(21개) → 3/18(45개) 수집량 2배. Business source_cards 4개 → 10개. **좋은 입력 없이 좋은 출력 없다.**

---

## v9.1: Community Pulse 품질 개선 (2026-03-31)

> 세션: 2026-03-31 작업 (2 커밋: `7745367`, `062026a`)

### 왜 CP가 중요한가

0to1log의 핵심 가치는 "AI 커뮤니티의 일원으로서, 하루의 AI 뉴스를 한 곳에서 완결"하는 것이다. 독자가 뉴스를 읽고 → 인사이트를 얻고 → 커뮤니티 반응을 살피고 → 퀴즈로 마무리하면서, **자신이 AI 커뮤니티 안에 속해있고 지식을 얻어나간다는 느낌**을 받게 하는 게 목표다. Community Pulse는 이 흐름에서 소속감의 핵심 요소이며, 단순 부가 정보가 아니다.

그런데 v9에서 CP가 불안정했다:
- 저품질 코멘트 인용 (URL-only, off-topic)
- CP 섹션 누락 (Expert에서 빠지고 Learner에만 있는 경우)
- band-aid 필터(spam, relevance, URL-ratio)가 계속 늘어나는 패턴

### 결정 A: Community Summarizer 단계 추가

**문제**: Writer가 raw comment를 직접 받아 선별+요약+포맷+번역을 동시에 하면서 품질이 흔들림.

**해결**: community 수집과 Writer 사이에 `community_summarize` 단계를 추가해 역할 분리.

```
Before: community → rank → enrich → write (Writer가 raw comment 선별+포맷)
After:  community → community_summarize → rank → enrich → write
                    ^^^^^^^^^^^^^^^^
                    gpt-4.1-mini 배치 1회, ~$0.001
```

- **Summarizer**: top 5 코멘트 → `{sentiment, quotes(0-2), key_point}` 추출. 영어 원문.
- **source_label**: `"HN 342↑ · 89 comments"` — 코드가 결정적으로 파싱 (LLM에 맡기면 포맷 흔들림).
- **Writer**: 정제된 데이터만 받아서 포맷+KO 번역. Rule 15 규칙이 6개 → 5개로 단순화되고, 선별 책임이 사라짐.
- **실패 시**: quotes=[], key_point=null → Writer는 CP 섹션을 아예 생략 (graceful degradation).

**비용**: ~$0.001 추가 (전체 그룹 배치 1회, 615 토큰 수준).

### 결정 B: Entity-First Search

**문제**: 기존 키워드 검색이 HN Algolia에서 0 결과를 반환. `"Atlassian Cuts 1,600 Jobs AI: Means"` 같은 6개 키워드 연결은 검색 엔진이 전부 AND 매칭하려다 실패. 3/27 비즈니스 5개 중 4개가 CP 수집 실패.

**해결**: Entity-First Search — 타이틀에서 고유명사/버전 패턴만 추출해 2-3 단어 쿼리로 검색.

```
Before: "Atlassian Cuts 1,600 Jobs AI: Means" → 0 results
After:  "Atlassian AI" → 5 results (189pts Atlassian layoffs 발견)
```

핵심 로직:
- **엔티티 추출**: 대문자 시작 + 일반 영어 아닌 단어 (Atlassian, GPT-5.4, EverMind)
- **선택적 부스트**: 버전 패턴(GPT-5.4) +40, 긴 고유명사(≥8자, Atlassian) +20, 짧은 단어(AI, US) +0
- **Foreign entity 패널티**: 스레드에만 있는 엔티티가 많으면 감점 (-8/entity, max -30). "Sam Altman AGI" vs "Sam Altman Sister Abuse Claims" → foreign 4개 → -30 → 차단.
- **시간 필터**: `target_date` 기준 7일 전부터만 검색 (backfill 대응). HN `numericFilters` 활용.

### 결정 C: Summarizer 2중 방어 (관련성 판단)

Summarizer에 원본 기사 제목을 전달하고, 커뮤니티 스레드가 다른 주제면 `sentiment=null`을 반환하도록 했다. Entity-First Search의 패널티로 대부분 걸러지지만, edge case에서 마지막 방어선 역할.

### 교훈

### 11. LLM에게 너무 많은 책임을 주지 마라

Writer에게 "raw comment에서 좋은 걸 골라서 자연스럽게 인용하라"는 건 선별+요약+포맷+번역을 동시에 시키는 것이다. 각 단계를 분리하면 각각의 품질이 올라간다. Summarizer는 "코멘트 5개 중 대표 1-2개 고르기"라는 단순한 작업 하나만 하면 되니까 정확도가 높다.

### 12. 검색어는 짧을수록 좋다

HN Algolia, Reddit 검색은 긴 쿼리를 잘 처리 못 한다. 6개 키워드 → 0 결과, 2-3개 엔티티 → 5+ 결과. 검색 엔진에는 핵심 고유명사만 던져야 한다.

### 13. 부스트만으로는 부족하다 — 패널티가 있어야 오탐이 잡힌다

"Atlassian"이 매칭됐다고 점수를 올려주면, "Atlassian Remote Work" 같은 무관한 스레드도 통과한다. 스레드에 우리 기사에 없는 엔티티(foreign entities)가 많으면 감점하는 패널티가 false positive를 효과적으로 차단했다.

---

## 남은 과제

- **NQ-09**: 어제 발행 뉴스 제목을 랭킹에 전달 — 같은 이벤트 반복 방지
- **NQ-15**: Learner 콘텐츠 재설계 — "Expert의 쉬운 버전"이 아닌 학습자 관점 재구성
- **NQ-22 Phase 3-4**: CP targeted subreddit search + LLM comment selection (미구현)
- **COLLECT-BRAVE-01**: Brave Search API 키 설정 + 실제 수집 검증 (수집기 코드는 완료)

## Related

- [[2026-03-30-news-pipeline-v8]] — 이전 세션 (분류/랭킹 분리, Research Guide 리팩토링)
- [[2026-03-30-multi-source-enrichment]] — NQ-13 설계 문서
- [[2026-03-30-merge-classify-design]] — NQ-16 merge+classify 설계 문서 (v1→v2 진화 과정 포함)
- [[2026-03-30-nq16-v2-classify-merge-split]] — NQ-16v2 구현 계획
- [[ACTIVE_SPRINT]] — NQ-13/14/16 done, NQ-15 todo
