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

## v9 파이프라인 흐름

```
6개 소스 병렬 (Tavily + HF Papers + arXiv + GitHub + Exa + Google RSS)
    | 50-60 candidates/day
    v
URL dedup + 발행 이력 제외 (3일) + Google News URL 해석 + 필러 필터
    v
분류 (gpt-4.1-mini) → Research 0-5개, Business 0-5개
    v
커뮤니티 수집 (HN Algolia + Reddit JSON) — 전체 분류 아이템
    v
랭킹 (gpt-4.1-mini) → [LEAD]/[SUPPORTING] 태그
    v
★ 2차 수집 (Exa find_similar) — 전체 아이템, 최대 4개 소스/아이템
    v
글쓰기 (gpt-4.1, max_tokens=32K) — 다중 소스 × 전문
    v
후처리: bold fix → tag strip → ★citation renumber
    v
품질 체크 (o4-mini × 4) — Source Quality 기준 포함
    v
DB 저장 (source_cards = 코드 추출) → Admin 확인 → 발행
```

---

## 비용 영향 (실측)

### 실제 파이프라인 비용 비교

| 날짜 | 버전 | 총 토큰 | 총 비용 | Research Expert | Business Expert | 비고 |
|------|------|---------|---------|----------------|-----------------|------|
| 3/20 | v8 | 328,746 | **$0.91** | 29,280 ($0.09) | 47,155 ($0.13) | 1소스 × 4000자 |
| 3/21 | v9 초기 | 494,353 | **$1.24** | 61,646 ($0.16) | 56,978 ($0.15) | enrichment 활성화 |
| 3/22 | v9 | 656,560 | **$1.54** | 103,626 ($0.24) | 55,617 ($0.14) | 다중 소스 × 전문 |

### 비용 증가 분석

- v8→v9: **$0.91 → $1.54** (69% 증가)
- 주요 원인: Writer 입력 토큰 폭증 (4000자 제한 해제 + 다중 소스 전문 전달)
- Research Expert가 가장 큰 증가: 29K → 103K 토큰 (3.5배) — 논문/기술 기사가 본문이 긴 편
- Business는 상대적으로 안정: 47K → 56K (1.2배)
- 초기 예상($0.28-0.29)보다 훨씬 높음 — 기사 전문 길이를 과소 추정

### 스테이지별 비용 (3/22 기준)

| 스테이지 | 토큰 | 비용 | 비중 |
|----------|------|------|------|
| classify | 4,091 | $0.003 | 0.2% |
| ranking | 1,356 | $0.001 | 0.1% |
| enrich | — | ~$0.005 | 0.3% |
| digest:research (expert+learner) | 206,365 | $0.47 | 31% |
| digest:business (expert+learner) | 111,414 | $0.29 | 19% |
| quality check × 2 | 10,108 | $0.005 | 0.3% |
| **합계** | **656,560** | **$1.54** | |

Writer(digest) 단계가 전체 비용의 ~50%를 차지. 입력 토큰 관리가 비용 최적화의 핵심.

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

---

## 커밋 목록

| 커밋 | 내용 |
|------|------|
| `eb69b62` | **다중 소스 enrichment** — Exa find_similar + 4000자 제한 제거 + Writer 다중 소스 포맷 |
| `90b56bd` | citation per-paragraph + quality check Source Quality |
| `87443a2` | **citation 넘버링 코드 후처리** — _renumber_citations + source_cards 코드 추출 |
| `b3d4a4e` | citation 포맷 예시 복원 — `[](URL)` 빈 괄호가 citation 누락 유발 |
| `81c60cc` | heading citation 제거 — skeleton + 후처리 코드 삭제 + v9 journal |

---

## 남은 과제

- **NQ-09**: 어제 발행 뉴스 제목을 랭킹에 전달 — 같은 이벤트 반복 방지
- **NQ-15**: Learner 콘텐츠 재설계 — "Expert의 쉬운 버전"이 아닌 학습자 관점 재구성
- **NQ-13 추가 검증**: 다음 파이프라인 run에서 다중 소스 반영 + citation 순차 확인

## Related

- [[2026-03-30-news-pipeline-v8]] — 이전 세션 (분류/랭킹 분리, Research Guide 리팩토링)
- [[2026-03-30-multi-source-enrichment]] — NQ-13 설계 문서
- [[ACTIVE_SPRINT]] — NQ-13 done, NQ-14 done, NQ-15 todo
