# 결정: AI 뉴스 파이프라인 v11 + v11.1 — Rubric v2 + Quality Gates + URL Plumbing + 거울 동기화

> 날짜: 2026-04-21 (v11 착지), 2026-04-22 (v11.1 거울 동기화 추가)
> 맥락: v10.2 이후 누적된 채점/수집 신뢰도 이슈를 구조적으로 해결. Apr 19 KO locale 사고가 rubric 재설계의 직접적 도화선. v11.1은 Apr 22 첫 fresh run 감사에서 노출된 writer-QC 거울 미정합 + pipeline_logs 일관성 버그 마무리.
> 세션: 2026-04-07~04-22 (약 2주 + 1일)

---

## 배경

v10.2(2026-04-06) 이후 파이프라인은 안정적으로 돌았지만 세 층위에서 구조적 결함이 드러났다:

1. **Apr 19 draft 사고** — KO research digest Community Pulse에 **영어 블록쿼트가 그대로 남아**있는데 LLM quality judge가 **96/100**을 매겼다. `locale_integrity`가 severity marker에 묻혀 있어 judge가 "통틀어 한국어 우세면 pass"로 해석. 점수가 높아서 auto-publish 기준을 통과해버림. "채점이 실제 결함을 못 잡는" 상태.

2. **SEO-spam + dead URL 혼입** — Apr 19 draft에 13개 저품질 URL 포함. 전부 enrich 단계(Exa find_similar)가 추가한 것. Collect는 `_classify_source_meta`로 spam tier를 거르는데 enrich가 같은 게이트를 거치지 않음 (DRY 위반). 추가로 `http://openai.com/index/introducing-gpt-5-4/` 같은 의심스러운 URL이 구조 검증만 통과하고 실제 도달 가능성은 체크 안 됨.

3. **Community Pulse 출처 불명** — CP 블록쿼트에 `> — Hacker News` 같은 attribution만 있고 실제 스레드 URL 없음. 독자가 원본 토론을 확인할 방법 없음. Writer에 "URL 생성해라"고 지시하면 hallucinate 위험.

이 세 문제는 서로 겹쳐 있었다. **채점이 약하고**, **수집이 새고**, **최종 출력에 검증 링크가 없어** 품질 신호가 끊겨있는 구조.

v10.x 점진 개선으로는 한계였다. 채점 아키텍처 자체를 다시 짜야 했다.

---

## 결정 A: Rubric v2 — Evidence-anchored sub-scores + code aggregation (NP-QUALITY-06)

### A1. LLM 채점 contract 변경

**v10**: LLM이 0-100 single score 반환. 구조 감점은 코드가 후처리로 추가.
**v11**: LLM이 10개 sub-score (각 0-10) + **각 sub-score당 evidence 필수** 반환. **총점은 코드가 집계** (LLM이 아님).

근거 설계:
- `8249e9d refactor(handbook): sub-score + evidence-based quality judge, code-side aggregation` — handbook에서 먼저 검증 (4-anchor 스케일 10/7/4/0, evidence 필수, `_aggregate_quality_sub_scores()` 헬퍼)
- `a7b9cd3 feat(news): restructure QC rubric — handbook pattern with evidence + locale_integrity (NP-QUALITY-06)` — news 4개 body 프롬프트(research_expert/learner, business_expert/learner)에 동일 패턴 이식
- `c5ebc35 feat(weekly): port rubric v2 (evidence-anchored 10 sub-scores, code aggregate)` — weekly에도 파리티

각 body 프롬프트는 10개 sub-score를 4개 카테고리로 분할:
- Research Expert: Structural(2) + Source(3) + Technical Depth(3) + Language(2)
- Research Learner: Structural(2) + Source(2) + Accessibility(3) + Language(3 inc. locale_integrity, no_chat_tone)
- Business Expert: Structural(2) + Source(3) + Strategic(3 inc. prediction_guard) + Language(2)
- Business Learner: Structural(2) + Source(2) + Practical Impact(3 inc. actionable_items) + Language(3)

### A2. `locale_integrity`를 explicit sub-dimension으로 승격

v10까지 `locale_integrity`는 severity marker 수준이었다 ("predominantly Korean" 등의 문구). judge가 "대체로 한국어면 통과"로 해석하면서 Apr 19 영어 블록쿼트 사고가 발생.

해결:
- `1a6df5b fix(qc): concrete rules for locale_integrity — measurable not 'predominantly Korean'` — 정성 표현을 정량 규칙으로 치환. "blockquote 중 KO 없이 EN만 있는 것이 있는가", "각 `###` 제목이 해당 locale 언어인가" 같은 명시적 체크.

### A3. 구조 감점 → Issue-based penalty + cap 레이어

v10의 단일 감점 (-15/-5 등)은 감점 상한이 없었다. 영향이 큰 결함 여러 개가 누적되면 음수 점수도 가능.

v11은:
- `a7e2121 feat(weekly): deterministic scoring + URL validation gate (daily parity)` — issue 타입별 penalty + 상한(cap) 시스템
- `70867bb feat(weekly): issue penalties/caps + stricter deterministic (daily full parity)` — daily parity 완성
- `4994884 chore(weekly): surface citation-coverage flags to quality_flags (daily parity)` — citation-coverage를 user-visible flag로

Issue severity(major/minor)별 다른 cap이 적용되고, 같은 카테고리의 issue는 누적 상한에서 멈춘다. 음수 점수 불가능.

### A4. 입력 잘림 한도 조정

KO 본문이 EN보다 character-dense해서 20K 잘림이 Business Expert "## 전략 판단" 섹션을 날려먹는 문제.

- `e93360b fix(qc): raise input slice from 20000 to 35000 chars — KO was getting cut off` — 35K로 상향. Research/Business 모두 full body가 judge context에 들어감.

### A5. Calibration: 톤 guard 정밀화

- `e4c317a fix(qc): allow polite imperatives in Korean action sections (no_chat_tone)` — "해보세요~" 같은 정중 명령형을 chat tone으로 오분류하던 문제 수정. Action Items 섹션 한정 허용.

---

## 결정 B: Multi-layer quality gates (NP-QUALITY-01/02/03)

v10은 수집 → 분류 → 채점 단계가 각자 별도 품질 로직을 가졌는데 **일관되지 않았다**. Apr 19 draft 분석으로 확인된 구멍 3곳에 명시적 gate 신설:

### B1. Enrich-stage source quality gate (NP-QUALITY-01)

- `aa70ee4 feat(news): add enrich-stage source quality gate (NP-QUALITY-01)`
- Collect는 `_classify_source_meta`로 spam tier를 거르지만 enrich(Exa find_similar + lookup_official)는 block_non_en + Chinese chars만 거름. 같은 게이트를 mirror.
- `_enrich_source_passes_quality(payload, source)` 헬퍼 추가:
  - `tier='spam'` drop (research_blocklist 도메인)
  - `analysis+low` drop (content farm: introl.com, neuraplus-ai.github.io, cloudproinc.com.au, aibusinessweekly.net)
  - `official_repo when source='exa_enrich'` drop (find_similar이 회사명만 언급하는 무관한 GitHub repo 반환 — "Kevin-Weil-leaves-OpenAI" 스토리에 `*/superpowers` repo 3개 등장한 사례)
- 18/18 test case로 Apr 19 13개 URL 전부 drop, 정당한 소스는 pass 검증

### B2. Classify authority rule (NP-QUALITY-02)

- `79a90b9 feat(news): add GitHub repo authority rule to classify prompt (NP-QUALITY-02)`
- Classify 프롬프트에 "GitHub 원본 repo(owner/repo) > fork/mirror" 권위 판정 규칙 추가. 소수 명성 부스트.
- `019424a refactor(news): classify prompt review — CoT + few-shot + remove dead score field` — Chain-of-Thought + few-shot으로 분류 안정성 강화, 사용되지 않던 score 필드 제거

### B3. URL liveness gate (NP-QUALITY-03)

- `48a5cdd feat(news): HEAD-check URL liveness before citation rendering (NP-QUALITY-03)`
- 기존 `validate_citation_urls`는 구조 검증만 — "LLM이 새 URL 발명했는지"만 봄. collector가 준 URL은 묻지도 따지지도 않고 통과.
- `_validate_urls_live()` 추가 — async HEAD check, Semaphore(20) 병렬, 3초 timeout, browser UA.
- Drop 규칙 (보수적):
  - HTTP 404/410 (명백히 없어짐)
  - DNS/connect/timeout 실패
  - 다른 apex domain으로 redirect (content farm 이탈)
- Keep 규칙 (benefit of the doubt):
  - 2xx/3xx/403/405/5xx/기타 4xx
  - 예상치 못한 예외 — fail open
- Brand TLD 사고 사후 수정: `4618e9a fix(news): remove cross-apex check in URL liveness — brand TLDs broke it` — `deepmind.google → blog.google` redirect가 cross-apex로 잘못 감지돼 멀쩡한 Google 블로그가 drop되던 문제 제거

### B4. Enrich 필터 완화 (course-correction)

B1 초기 버전이 과도하게 공격적이어서 다양한 관점의 secondary 소스까지 drop하는 문제. Amy 피드백 "메이저 뉴스를 확인하고 다양한 시선으로 각 뉴스를 읽고 재작성하는 거였어" 반영.

- `5796df1 refactor(news): loosen enrich filter — allow secondary media for multi-angle coverage` — spam + exa_enrich GitHub만 drop, TechCrunch/Wired/Forbes류 secondary는 통과

---

## 결정 C: Thread URL plumbing — Community Pulse 인용 신뢰도

### C1. 문제

CP 블록쿼트 attribution이 `> — Hacker News`로 URL 없음. 독자가 "정말 HN에 이런 댓글이 있었나" 확인 불가. Apr 19 QC도 "Community Pulse paragraphs lack explicit citations" minor로 지적.

첫 시도(`90038ef feat(news): linkify Community Pulse blockquote attributions`)는 두 가지 근본 버그로 실패:
1. `CommunityInsight.url`을 참조했는데 모델에 그 필드가 없었다 (URL은 dict key)
2. source_label이 `"Hacker News 79↑ · 116 comments"`인데 body block header는 `**Hacker News**`만 — 문자열 완전 일치 실패

위치 기반 fallback도 시도했으나 writer가 blocks를 재정렬할 수 있어 URL이 swap되는 사례 발생(Apr 21 dry-run에서 검출).

### C2. 설계: 수집 시점에 thread URL 임베드 → 파이프라인 전체로 plumb

`vault/09-Implementation/plans/2026-04-21-cp-thread-url-plumbing.md`

7 Task, TDD:

1. **Model 확장** (`9547eb4`) — `CommunityInsight`에 `hn_url`, `reddit_url` optional 필드 추가. 기존 체크포인트 hydration 영향 없음.

2. **Collection URL 임베드** — `story_id`(HN)/`permalink`(Reddit)을 thread_block 헤더에 임베드:
   - `971c6d3 feat(news-collection): embed HN thread URL in thread_block header` — `[Hacker News|url=https://news.ycombinator.com/item?id=...]`
   - `5985c3e feat(news-collection): embed Reddit thread URL in thread_block header` — `[Reddit r/<sub>|url=https://www.reddit.com<permalink>]`
   - 각각 `_format_hn_thread_block` / `_format_reddit_thread_block` 헬퍼로 추출 (DRY + 테스트 가능)

3. **Parsing** (`0fa85dd feat(ranking): add _parse_source_meta for URL extraction`) — `_HN_HEADER_RE` / `_REDDIT_HEADER_RE`에 `(?:\|url=(\S+?))?` optional group 추가. `_parse_source_meta(raw) -> (label, hn_url, reddit_url)` 반환. 옛 blob(URL 없음)도 None 반환으로 back-compat.

4. **Summarize wiring** (`4a8ba6e feat(ranking): plumb hn_url/reddit_url into CommunityInsight`) — `summarize_community`가 `_parse_source_meta` 3튜플 unpack 후 `CommunityInsight(..., hn_url=..., reddit_url=...)`로 전달. `_parse_source_label` wrapper 제거(0 caller).

5. **Post-processor 재작성** (`fa565b4 refactor(cp-citations): match blocks to insights by upvote count`) — 위치 매칭 폐기, **업보트 카운트 매칭**으로 교체. Body block `**Hacker News** (79↑)`의 79를 파싱해서 source_label에 "79↑" 포함된 insight와 짝지음. 2개 블록이 순서 뒤집혀도 정확.

6. **Smoke script** (`822cc3d chore(scripts): add smoke_cp_citations for post-deploy CP linkify check`) — 체크포인트에서 URL 플럼 여부 + 본문 linkify 여부 출력.

7. **Apr 21 retrofit** (script-only, HN Algolia 재조회로 story_id 복구 + `_inject_cp_citations` 적용) — 과거 데이터 12개 attribution linkify, 본문 내용 변화 없음.

### C3. 설계 원칙

- **URL 보존은 수집 시점에** — API 응답에 있을 때 바로 임베드. 중간에 버리면 재수집 API 호출 필요, fragile.
- **매칭 키는 단일 출처에서** — body `(79↑)`와 insight `source_label`의 "79↑"가 모두 `_parse_source_meta` 출력에서 파생. 두 다른 소스 비교가 아님.
- **안전 degradation 3단계** — CP 섹션 없음 / hn_url 없음 / 업보트 불일치 → 모두 원문 유지.

### C4. 한계 (알려진 이슈)

현재 linkify는 Tavily/Brave 원본 쿼리 시점의 thread URL 1개만 담는다. 같은 primary_url에 HN + Reddit 토론이 모두 있는 경우, CommunityInsight은 둘 다 저장 가능하지만 body는 하나만 쓰면서 attribution 라벨에 의존해 구분. 향후 개선 포인트 (결정 F.4).

---

## 결정 D: `rerun_from=quality` — QC 튜닝용 저비용 재평가 경로

`vault/09-Implementation/plans/2026-04-20-rerun-from-quality-plan.md`

### D1. 문제

Apr 19 draft 사고 후 QC 프롬프트를 여러 번 수정하면서 재평가가 필요했다. 기존 옵션:
- `rerun_from=write` — gpt-5 writer 재실행 (~$0.54/회). 내용 자체가 달라져 scoring 변화가 prompt 개선 효과인지 내용 차이인지 구분 어려움.
- `rerun_from=community` — 더 위쪽부터 재실행. 더 비쌈.

Apr 19 당일 재런 2회만에 $1.10 낭비. **내용 유지한 채 채점만 다시 돌릴 경로 부재**가 근본 문제.

### D2. 해결

- `a9fd8de feat(rerun): add 'quality' to STAGE_CASCADE` — stage cascade에 `quality` 키 추가. quality/save/summary 로그만 삭제.
- `286f79a feat(rerun): add _load_personas_and_frontload_from_db helper` — digest 체크포인트가 없어서 `news_posts` DB에서 직접 PersonaOutput(EN+KO) + frontload 재구성.
- `0f4fb72 feat(rerun): add quality-only branch to rerun_pipeline_stage` — `from_stage=="quality"`일 때 writer 완전 우회. merge + community_summarize 체크포인트만 로드하고 QC 재실행.
- `37ec1a3 fix(rerun): defensive handling in quality branch + category=None test` — `_check_digest_quality`가 int sentinel 반환 케이스 방어. personas_by_type 비었을 때 early return.
- `71a3e85 feat(api): accept 'quality' as rerun_from value` + `3c80055 feat(admin-ui): add Quality-only rerun buttons`
- `5ef93d7 chore(scripts): add quality-rerun E2E validation script` — baseline/verify 모드, 6 criteria 체크:
  1. cost ≤ $0.10
  2. digest:* 스테이지 재실행 없음
  3. quality_score int 타입
  4. content_analysis.scores_breakdown 존재
  5. updated_at 새로 갱신
  6. content_expert/learner 해시 불변

### D3. 비용 효과

기존 rerun_from=write: **~$0.54/회** (gpt-5 writer + QC)
신규 rerun_from=quality: **~$0.05/회** (QC only, gpt-5-mini)

**약 10배 절감**. Prompt 튜닝 사이클 실질 비용이 $0.5 → $0.05로 떨어져 반복 실험 가능해짐.

### D4. 발견한 스키마 오류

초기 구현에 `analyzed_at` 컬럼 update 포함시켰으나 `news_posts` 스키마에 실제로 존재하지 않음 (42703 에러). `74afcc2 fix(rerun): drop non-existent analyzed_at column — use Supabase updated_at trigger`로 수정. Supabase 트리거가 UPDATE마다 `updated_at`을 자동 갱신하므로 명시적 필드 불필요.

---

## 결정 E: Writer prompt hardening + focus_items_ko fallback

### E1. Forward-looking speculation 차단

v10 `HALLUCINATION_GUARD`는 한국어 시간 예측 표현만 금지 ("Q2에", "내년", "다음 분기"). 영어 쪽 수렴 실패로 Apr 19 business에 `"Expect buyers to favor..."` 등장 (QC major).

- `7014058 fix(news): harden writer prompt — forbid forward-looking verbs + REQUIRE focus_items_ko`
- HALLUCINATION_GUARD에 영어 forward-looking verb 명시 금지: "Expect X to Y", "will disrupt", "is set to become", "poised to", "on track to"
- Calibrated 대안 제시: "signals", "points toward", "implies", "positions X as"
- 출처가 직접 예측하는 경우 귀속 명시: `Anthropic says it expects ... [N](URL)`

### E2. `focus_items_ko` 생략 방어

v10의 단일 bilingual writer 호출이 JSON 출력에서 `focus_items_ko`를 가끔 생략 (예: Apr 19 business). QC frontload locale gap (major)로 잡히지만 writer 단계에서 미리 막는 게 낫다.

1단: JSON 스키마에 REQUIRED 마커 명시 (`7014058` 같은 커밋).
2단: **방어적 fallback** 추가:

- `cad1d87 fix(news): add focus_items_ko fallback translation — defensive net for writer omissions`
- `_translate_focus_items_ko(items_en, *, digest_type)` — gpt-5-mini로 3개 bullet 번역 (~$0.001)
- `_generate_digest`의 frontload_payload 빌더 직전에 훅: `focus_items` 3개 있고 `focus_items_ko` 비어있으면 실행
- 4 unit test (happy path, wrong count, LLM exception, noop when input≠3)
- 코스트 zero-overhead (writer 정상 시 미발동), 발동 시 ~$0.001

### E3. Community Pulse 인용 정합성

- `aee61a8 fix(cp): enforce quotes_ko == quotes length to prevent English-in-Korean leakage` — summarize_community가 len(quotes_ko) < len(quotes)일 때 quotes 트림. Writer에 일관된 1:1 매핑 강제.

---

## 결정 F: Cross-pipeline rubric parity (handbook ↔ news ↔ weekly)

### F1. Handbook이 rubric 선도

`8249e9d refactor(handbook): sub-score + evidence-based quality judge, code-side aggregation`이 handbook에서 먼저 검증. 이후 news(`a7b9cd3`) → weekly(`c5ebc35`)로 이식.

### F2. Weekly daily parity 마무리

Weekly pipeline은 daily 대비 다음 요소가 부족했다:
- `ea1dcf6 feat(weekly): add excerpt + focus_items to EN weekly prompts matching daily pattern`
- `d8d658f feat(weekly): add excerpt_ko + focus_items_ko to KO adapter prompt + META marker`
- `95f9183 feat(weekly): pipeline excerpt + focus_items save + KO META marker passthrough`
- `d11c6ef feat(weekly): add _validate_focus_items helper with tests`
- `6bd99dd feat(weekly): inherit source title + publisher from daily digests`
- `bf24d02 feat(weekly): auto-publish when WEEKLY_AUTO_PUBLISH=true and quality passes`
- `38b1ab4 feat(weekly): add quality scoring to weekly pipeline`

매주 생성되는 weekly가 이제 daily와 같은 채점/저장 구조를 공유.

### F3. Handbook scope + naming gates (공통 패턴)

- `eb1f446 feat(handbook): add validate_term_scope gate (blocklist/regex/product-allowlist)`
- `99dad16 feat(handbook): add validate_korean_name gate (Hangul minimum + global-name passthrough)`
- `5732eb9 feat(handbook): add validate_term_grounding gate (verbatim match + compound-fabrication signal)`
- 3 gate 모두 code-side + pipeline_logs rejection entry — **LLM 판정 후 코드 게이트** 패턴이 handbook/news 둘 다에 자리잡음.

### F4. (남은 과제) CommunityInsight에 HN+Reddit 양쪽 URL

현재 한 insight이 HN hn_url OR Reddit reddit_url 중 하나를 주로 담음. 같은 primary_url에 둘 다 토론이 있는 경우 대응. 향후 필드는 모두 있지만 linkify 매칭 로직이 "label별"이라 body block header에 "Hacker News"만 보이면 HN, "r/xxx"만 보이면 Reddit으로 자동 구분.

---

## 결정 G: 2026-04-22 — Fresh-run 감사 기반 rubric/writer 거울 동기화 + infra 일관성 (v11.1)

Apr 22 아침 첫 v11 공식 fresh run의 결과를 검토하다 4 층위의 gap이 드러남: judge 환각 2건, rubric과 writer-prompt 거울 미정합 3건, pipeline_logs 일관성 버그 1건. 거기에 Apr 21 audit의 후행 관찰 + 사용자 피드백으로 admin 도구 정비까지 포함. v11 구조는 유지하되 반사면을 서로 맞추는 마무리 — **"v11.1 거울 동기화"**.

### G1. QC rubric 환각 수정

Fresh run에서 judge가 실제로는 존재하지 않는 locale_integrity 위반을 flag 하는 사례 발견. EN body에만 있는 영어 블록쿼트를 KO body에 있는 것으로 오인.

- `fa89370 fix(qc): anchor locale_integrity to KO BODY section to stop EN/KO confusion` — payload에 `=== EN BODY ===` / `=== KO BODY ===` scope 앵커 추가
- `9bb0a73 fix(qc): add SELF-VERIFY clause to locale_integrity to stop hallucinated EN-in-KO reports` — judge에게 "evidence는 반드시 KO section 내 substring이어야 함" self-verify 의무화
- `d0dbb1d fix(prompts): Apr 22 audit fixes` — CP attribution/section EXEMPT 명시 (`_inject_cp_citations`가 추가하는 `> — Hacker News` 류 attribution은 citation marker이지 body content 아님), Strategic Decisions citation rule, attribution-URL domain match, focus_items tone guidance

위 3 commit이 최종적으로 `7ca0d3b`(squash)로 정리.

### G2. QC rubric gap fill — 사용 중 노출된 빈 영역

- **`citation_coverage` CP EXEMPT** (4 body 프롬프트) — CP blockquote는 `> — [Source](URL)` 별도 attribution 포맷을 쓰므로 inline `[N](URL)` 부재가 감점 원인이 되면 안 됨. Apr 21 research 85 → 95로 반영.
- **`framing_calibration` watch-P3 EXEMPT** (frontload 프롬프트) — focus_item P3 ("what to watch")는 본질적으로 관찰형인데 forward-looking으로 false-flag 되던 tension 해소. Apr 21 research 최종 이슈 1 → 0.
- **Payload scope anchor + SELF-VERIFY** — 위 G1의 세부 메커니즘.

### G3. QC rubric 차원 확장 — `claim_calibration` + temporal + internal consistency

Apr 21 감사의 3개 "루브릭으로 막을 수 있었는데 빠져있던" 차원:

1. **`claim_calibration` sub-score 신설** (`2ffe318 feat(qc): body-level claim_calibration ...`) — 4 body 프롬프트 전부 language_quality 카테고리에 추가. Retrospective/present-tense overclaim (dominates / crushes / 장악 / 압도적) 포착. `prediction_guard`(business)와 구분 — 이건 forward-looking verb specific이고 `claim_calibration`은 현재/과거형 overstatement.
2. **Temporal anchoring** (기존 `fluency` 확장) — "yesterday / last week / 최근 / 지난주" 상대 시간 금지, 절대 날짜("Apr 20", "Q1 2026") 선호. 아카이브된 digest에서 "어제"는 의미 잃음.
3. **Internal consistency** (`concrete_specifics` research + `baseline_comparison` business 확장) — 같은 숫자가 여러 섹션에 나올 때 동일값이어야 함. "One-Line $122B / body $100B" 같은 내부 모순 포착.

Sub-score count: research_expert 13 → 14, research_learner 13 → 14, business_expert 14 → 15, business_learner 13 → 14.

### G4. NQ-40 Phase 2a — Community Pulse quality sub-scoring (measurement-only)

CP의 quote 품질 자체를 채점 대상으로 추가. v11.0의 `locale_integrity`가 Hangul 존재만 보는 것에 더해 CP 내용 평가 차원 확보.

- `00c655e feat(qc): NQ-40 Phase 2a — CP quality sub-scoring (measurement-only)` — 3 sub-score: `cp_relevance` (quotes가 그날 스토리에 연결), `cp_substance` (기술/결정 substance vs hype), `translation_fidelity` (EN↔KO pair 의미/톤 보존).
- **Weight=0 measurement mode** — `_aggregate_subscores`가 `community_pulse` group을 스킵. 2주 관찰(~2026-05-06) 후 분포 보고 Phase 2b에서 weight 결정.
- Code-side Hangul validation + mini-model retranslate fallback in `summarize_community` (`4ec450a`, `7ca0d3b`에 squash) — CP의 quotes_ko가 Korean인지 검증, 아니면 mini model로 재번역. Phase 1 실측: Apr 22 write rerun 후 research CP all 10/10, business CP all 10/10 + N/A 폴백 정상 작동.

### G5. Writer 프롬프트 거울 — QC 룰이 있는데 writer에 없던 것

QC 룰과 writer 룰은 **거울로 맞춰야 한다** (교훈 37). 없으면 "writer는 놀고 QC가 쫓는" 구조:

- `def72b7 refactor(prompts): writer-side mirrors of QC rubric additions` (prompt-engineering-patterns skill 적용 — Pattern 2 CoT self-verify + Pattern 4 progressive disclosure)
- **HALLUCINATION_GUARD 확장**:
  - Retrospective/present-tense overclaim 명시 금지 (dominates / 장악 류, `claim_calibration` 거울)
  - Absolute-date preference (relative 시간 마커 금지, `temporal anchoring` 거울)
- **BODY_LOCALE_PARITY 신규 블록** — FRONTLOAD_LOCALE_PARITY 평행 구조. 본문 EN/KO 숫자/엔티티/구조 strict 대조. 통화 단위 변환 worked example (`$8.3 billion` = `83억 달러`, NOT `8.3억 달러`). Apr 21 business의 100× 오역을 writer 시점에 막는 직접 대응.
- **FINAL CHECKLIST 확장** (기존 7항 + 신규 3항): body number parity (random 3개 샘플), no relative time markers, no overclaim language. Chain-of-thought self-verify 패턴.
- `ab656f4 fix(prompts): post-audit Apr 21-22 refinements` — 동일 세션에서 추가 CP EXEMPT, watch-P3 EXEMPT, currency unit, URL strict-copy, acronym expansion, arxiv detail.

### G6. `rerun_from=quality`의 save log 일관성 버그 + Apr 21 backfill

Pipeline_logs를 "실행 stage의 완전한 audit trail"로 보면 `rerun_from=quality`가 일관성 깨뜨림:

- `STAGE_CASCADE["quality"]`가 save:* 로그 **cascade-delete**
- Quality rerun은 `_generate_digest`를 호출하지 않아 save:* 로그 **재생성 안 함**
- 결과: quality rerun 한 번당 save:* 2개 로그 **영구 손실**. Apr 21이 14 stage로 귀착된 이유.

Fix:
- `57b8aa8 fix(rerun): emit save:* logs in quality rerun for pipeline_logs consistency` — `rerun_pipeline_stage` quality branch에 per-digest-type save log emit 추가 (`_generate_digest`의 save log 거울). debug_meta.rerun_from='quality'로 origin 구분.
- Apr 21 retroactive backfill — `save:research`/`save:business` 로그 수동 insert (debug_meta.backfilled=true, backfill_reason 기록). 16 stage로 정상화.
- `b2d250d style(admin/pipeline-runs): detail Stage Count excludes summary for list parity` — detail 페이지와 list 페이지 stage count 불일치 해소. 양쪽 다 summary meta stage 제외.

### G7. Admin 도구 정비 — v11 iteration loop 완성

v10에서 v11까지 rubric/writer 본체를 세대 교체했지만 admin tool chain이 뒤따라감. Apr 22 사용자 피드백(편집 후 재채점 iteration이 불편)으로 3 commit 묶음:

- `994084e style(admin/QualityPanel): theme-aware colors via CSS vars` — hardcoded `bg-white`/`bg-gray-*`/`bg-green-100` 등 → CSS vars (`var(--color-bg-card)`, `var(--color-success)` 등). 4 테마(light/dark/midnight/pink) 자동 대응.
- `aa7fd37 feat(admin/QualityPanel): collapsible panel with rerun footer slot` — 기본 닫힘 (점수만 보임), 클릭 시 세부 펼침. `<slot name="footer">`로 news editor가 rerun 버튼 주입 (QualityPanel 재사용성 유지). Auto-publish 차단 이슈 있을 때 summary에 `!` 빨간 배지 — 95점인데 url_validation 실패 같은 misleading 상태 방지.
- `c296a5e refactor(admin): split news editor from legacy posts, relabel as Paper` — `/admin/edit/[slug]` → `/admin/news/edit/[slug]`. `/admin/posts/` 레거시 페이지 삭제 (news_posts 테이블 중복 진입점). Dashboard "New Post" CTA는 `/admin/blog/edit/new`로 재배치 (블로그만 수동 생성). 사용자 노출 "News" 라벨 "Paper"로 리브랜드 (URL/API는 `/admin/news/*` 유지 — 테이블명 매칭).
- `e964dc9 feat(admin): inline 'Save & re-run quality' button in news editor` — 편집 → 저장 → rerun 트리거 → 폴링 → reload 원클릭. digest slug 패턴(`YYYY-MM-DD-(research|business)-digest(-ko)?`)일 때만 렌더. 기존 pipeline-runs 페이지 왕복 4 navigation → 0 navigation으로 단축.

### G8. Signal 보강 — GitHub trending 튜닝

Apr 19-22 실측에서 daily github_trending 최종 생존율 0-1/day로 확인 (수집은 매일 10개). Weekly `Open Source Spotlight`가 daily URL에 100% 종속이라 주간 3-5개 요건 미달 위험.

- `106e845 feat(news): tune GitHub trending query + surface recent releases`
  - A. Query 튜닝: `pushed:>7d` (was `created:>7d`) — 성숙 프로젝트 major release 포착; `stars:>500` (was `>20`) — SEO/joke repo 차단; `sort=updated` (was `stars`) — 최근 활동순.
  - B. Release 감지: 각 top 10 repo `/releases?per_page=1` 병렬 조회 → 7일 이내면 snippet에 `Released {tag} on {date}` 프리픽스 + release notes 300자를 raw_content에 첨부. Release carrying repo가 앞으로 정렬.

기대 효과: daily 생존율 1-2/day 도달 시 weekly 3-5 요건 충족. 2026-05-06 게이트로 재평가 (NQ-42).

---

## 비용 영향

| 항목 | v10.2 | v11 | 변화 |
|---|---|---|---|
| Quality scoring (daily) | ~$0.003 | ~$0.012-0.015 | +400% (10 sub-score + evidence) |
| URL liveness check | $0 | $0 (HEAD 무료) | 0 |
| Enrich source filtering | $0 | $0 (코드) | 0 |
| focus_items_ko fallback | $0 | ~$0.001 (발동 시) | 조건부 +$0.001 |
| **Per daily run total** | **~$0.50** | **~$0.54** | +8% |
| rerun_from=write | ~$0.54 | ~$0.54 | 0 |
| **rerun_from=quality (신규)** | N/A | **~$0.05** | 신설 |

QC 비용 증가는 evidence 필드(각 sub-score 당 인용 text)가 max_tokens 500 → 1500-1800로 팽창한 데 기인. 단, sub-score 별 문제 지점 추적 가능성이 크게 올라감 — 디버깅 시간 절감이 비용 증가를 상쇄.

rerun_from=quality 신설로 **프롬프트 튜닝 사이클 비용이 ~10배 절감**. Apr 19처럼 2회 rerun에 $1.10이었던 케이스가 v11에선 ~$0.10.

---

## 교훈 (v10의 24번에서 이어서)

### 25. LLM에게 총점을 맡기지 마라 — 코드가 aggregate 해라

LLM에게 sub-score 10개를 주고 "총점도 내줘"라고 하면, 합이 일치하지 않거나(중간 집계 오류), 편향된 총점(낮은 sub-score에 끌려감)이 나온다. 산술은 코드가 맡고, LLM은 개별 판단만 한다. `_aggregate_subscores()` 한 줄짜리 함수가 score의 **재현성과 검증 가능성**을 동시에 보장.

### 26. 정성 표현은 judge가 재해석한다 — 정량으로 내려라

"predominantly Korean"처럼 유연한 표현은 LLM이 "통틀어 한국어면 OK"로 넓게 해석. 영어 블록쿼트 하나 정도는 봐주는 셈. "blockquote 중 KO 없이 EN만 있는 것이 있는가" 같은 **명시적 체크 항목**으로 내려야 어휘 해석 여지를 없앨 수 있다.

### 27. Evidence 요구는 judge를 정직하게 만든다

각 sub-score에 "근거 텍스트"를 요구하면 LLM이 **없는 결함을 만들어내거나 있는 결함을 숨기기 어려워진다**. 동시에 score가 낮은 이유를 사람이 즉시 이해할 수 있어 디버깅/튜닝 시간이 크게 줄어든다.

### 28. 같은 품질 게이트는 반복되는 stage에 mirror 해라 — DRY 위반은 quality hole

Collect가 spam tier를 거르는데 enrich가 거르지 않는 구조는 필연적으로 Apr 19 같은 사고를 낳는다. "비슷한 역할 하는 두 스테이지는 같은 게이트 공유" 패턴을 설계 시점에 박아야 함. `_classify_source_meta`를 collect/enrich 양쪽에서 호출하는 식.

### 29. 구조 검증 ≠ 실제 도달 검증

"LLM이 새 URL 발명했는지"를 보는 건 구조 검증일 뿐. collector가 준 URL이 실제로 **살아있는지**는 완전히 다른 문제. HEAD check는 3초 timeout, 병렬 20, fail-open으로 부담 없이 추가 가능 — 얻는 신뢰도는 크다.

### 30. 수집 시점 데이터는 수집 시점에 보존해야 한다

`story_id`/`permalink`은 HN/Reddit API 응답에 있을 때 바로 text blob에 임베드해야 한다. "나중에 필요해지면 다시 조회하지 뭐"는 API 할당량 + fragile dependency 문제로 누적. Optional 필드로 모델에 추가하되 수집 시점에 채우는 게 원칙.

### 31. 위치 매칭은 LLM이 재정렬하면 깨진다 — 구조적 키로 매칭해라

CP 블록을 dict 순서로 매칭하던 첫 시도가 URL swap 버그를 낳음. Writer가 내러티브상 (79↑) 블록을 앞에 놓으면 dict의 (58↑) 첫 엔트리가 잘못 붙음. 해결: **upvote 카운트 같은 구조적 키**를 양쪽에서 뽑아서 매칭. Writer 재정렬에 둔감해짐.

### 32. MagicMock은 진짜 모델이 아니다 — 테스트에 그림자 제공

`insight.url`을 참조하는 테스트가 통과했는데 실제 `CommunityInsight`에는 `url` 필드 자체가 없었다. MagicMock은 존재하지 않는 속성도 자동 생성하므로 테스트에선 `.url`이 "있는 것처럼" 돌아감. 테스트 fixture는 **진짜 pydantic 모델**을 써야 한다. 데이터 구조 오해가 production에서 드러나는 비용이 훨씬 크다.

### 33. 채점 아키텍처 변경 = 트렌드 불연속

Rubric을 single score → sub-scores로 바꾸는 순간, **이전 점수 데이터와 직접 비교 불가**. v10 85점과 v11 85점이 "같은 85점"이 아니다. 채점 모델뿐 아니라 채점 contract 자체가 변할 때마다 calibration 재조정과 threshold 재평가가 필요 (auto_publish 85 → 80 하향 조정).

### 34. 저비용 재평가 경로가 없으면 프롬프트 튜닝이 비싸진다

rerun_from=write 말고 **rerun_from=quality** 같은 채점 전용 경로가 없으면 QC 프롬프트 실험이 $0.5/회씩 비용이 쌓인다. 내용 유지한 채 채점만 다시 돌리는 경로를 두면 10배 절감 + "내용 차이 vs 프롬프트 차이" 혼동 제거.

### 35. "완료" 선언 뒤에도 audit review가 남아있다 (v10 교훈 연속)

v10-hardening 회고에서 배운 "audit review가 별도 단계"가 v11에서도 증명됐다. CP citation v1 (`90038ef`)이 spec review + code quality review 모두 통과했는데 **production 첫 접촉에서 2개 근본 버그** 노출. 테스트는 MagicMock 덕에 green이었고 reviewer는 코드만 봤지 데이터 구조 실체를 검증 안 함. Task 별 integration smoke를 spec review 단계에 포함시켰어야.

### 36. 단일 사고는 보통 구조적이다

Apr 19 "KO 영어 블록쿼트 + 96점 사고" 하나가 rubric 재설계(A) + multi-layer gates(B) + writer hardening(E) 세 갈래를 끌어냈다. 사고 하나 = 수정 하나가 아니라 **사고 = 분해해서 각 층위에 분산**시킬 때 재발이 줄어든다.

### 37. QC 룰과 Writer 룰은 거울로 맞춰라

Rubric에 `claim_calibration` 추가한 순간, writer 쪽에 같은 차원 룰이 없으면 "writer는 놀고 QC가 쫓는" 비대칭 구조가 된다. 순효과 = QC 감점만 늘어남. Writer가 생성 시점부터 피하게 해야 양쪽이 동일한 품질 개념을 공유. v11.1 작업 원칙: 새 sub-score 추가 = writer guard 추가 한 쌍으로 묶어서 커밋. 오늘 추가 4 dimension(overclaim / temporal / body locale parity / self-check) 모두 양쪽 동기화.

### 38. Cascade delete는 재생성 주체와 쌍으로 검증하라

`STAGE_CASCADE["quality"]`가 save 로그 삭제만 하고 재생성 안 한 건 "삭제 = 곧 재실행" 암묵 가정이 깨진 경우. Quality 경로는 `_generate_digest`를 안 불러서 save 실행 0회 → 로그 영구 손실. Cascade 규칙 작성 시 **(삭제 대상 stage) AND (재생성 담당 함수)** 쌍으로 mapping 체크해야. 삭제만 있고 재생성 path 없으면 audit gap.

### 39. Hardcoded 색상은 테마 시스템의 조용한 킬러

QualityPanel이 `bg-white` / `bg-gray-*`로 박혀있어 midnight/pink 테마에서 흰 박스가 튄 건 "작동은 함"과 "일관성 있음"이 다른 문제라는 증거. CSS vars(`--color-bg-card` 등)로 통일하면 새 테마 추가 시 component 수정 비용 0. 첫 컴포넌트 작성 시점에 vars로 쓰기 vs 나중 일괄 refactor — 후자가 3-4배 비쌈. 신규 admin component 작성 시 "Tailwind color utilities 금지, `var(--color-*)` 만" 규칙을 체크리스트에 박을 만함.

### 40. 측정만 하는 sub-score도 가치 있다

Phase 2a `community_pulse` 3 sub-score는 weight=0 → 총점 영향 없음. 처음엔 "그럼 왜 넣나?" 싶지만, 2주 측정 후 분포 보고 weight 결정하는 게 이론적 가중치보다 안전. 특히 `translation_fidelity`는 샘플 없이 weight 넣으면 judge가 근거 없이 낮게 매기는 위험. **observed variance로 calibrate 후 gate화** 패턴은 "먼저 재고 나서 조이기".

### 41. Inline iteration loop vs context-switching cost

Editor 페이지 → 저장 → pipeline-runs 이동 → rerun 드롭다운 → 클릭 → 결과 대기 → editor 복귀. **4 navigation + 4 wait**. Inline 버튼은 같은 페이지에서 편집 → 클릭 → reload. **0 navigation**. 같은 기능의 UX 비용이 5-10배 차이. Backend code 0줄(기존 API 재사용) + 프론트 100줄 투자로 구현 가능한 경우 ROI 매우 높음. "기능은 있는데 쓰기 불편"이 반복되면 iteration cycle 자체가 느려져 quality 개선 페이스가 떨어짐.

### 42. GitHub Trending은 `created`가 아니라 `pushed`다

`created:>7d`는 "새로 생긴 repo"만 잡는데 AI 영역에선 그게 대부분 personal 실험·joke repo. `pushed:>7d`는 "최근 활동 있는 repo"라 PyTorch/vLLM/HuggingFace 같은 성숙 프로젝트의 major release를 포착. 쿼리 키워드 한 개 차이가 **완전히 다른 수집풀**을 만듦. Classifier stage 3 단계 tuning하는 것보다 upstream query 1 문자 바꾸는 게 효과 크다. **"잘못된 수집풀은 channel downstream에서 못 고친다"** — 쓰레기 100개 중 1등 뽑기보다 candidate 10개로 좁히고 품질 올리는 게 맞음.

---

## 품질 추이

| 날짜 | 버전 | Research | Business | 비고 |
|------|---|----------|----------|------|
| 4/6 | v10.2 | 96 | 91 | [BODY] 마커 + NQ-09 이벤트 중복 감점 |
| 4/14 | v10.2+hard | 85-92 | 85-92 | Hardening Phase 1/2/3 (v10 유지) |
| 4/19 | v10.2+incident | 75 (new rubric) | 73 (new rubric) | Rubric v2 발동 — 기존 draft 재채점, 점수 하락 = 엄격해짐 |
| 4/19 | v10.2+fix | 75 → (+fix) | 73 → (+fix) | URL liveness + enrich gate 후 재실행 (gpt-5 cost 발생) |
| 4/21 | **v11** | 76 | 93 | Rubric v2 + full parity. Research는 rubric 엄격도 반영. |
| 4/22 | **v11.1** | 95 | 100 | Writer+QC 거울 동기화 후 Apr 21 rewrite-both 재채점. major factual error(KO 단위 오역) 근절 + 거의 모든 sub-score 10/10. |

**주의**: v10 85점과 v11 85점은 직접 비교 불가 (교훈 33). Auto-publish threshold 재평가 필요 — 현재 85 기준은 v11 rubric에선 너무 엄격해 보임 (80 제안 관찰 중). v11.1은 거울 동기화로 점수 분포가 안정화 — 양끝 이상치 감소.

---

## 남은 과제

### 단기 (Apr 22-30)

- **NQ-30**: Auto-publish threshold 재조정 (85 → 80 검토 + 1주 관찰)
- **NQ-31**: rerun_from=quality post-deploy E2E (Apr 22 fresh run 기반 smoke_cp_citations 확인)
- **NQ-32**: Weekly quality score 실측 (v11 rubric 적용 후 평균 점수대 파악)
- **Phase 2b**: CP quality sub-score weight 결정 — `community_pulse` group 분포 2주 관찰 후(~2026-05-06) 유의미하면 가중치 부여, 아니면 rubric 제거. 현재 measurement-only (weight=0).
- **NQ-42 게이트**: daily github_trending 생존율 0.7/day 미달 시 weekly 전용 `_collect_github_weekly` 또는 daily candidate archive 구현. 2026-05-06 재평가.

### 중기 (5월)

- **NQ-34**: CommunityInsight에 HN+Reddit 둘 다 URL 저장 시 linkify label 매칭 로직 (현재 `r/`/`Hacker News` prefix로 구분 — 충분하지만 문서화 필요)
- **NQ-35**: Few-shot 데이터 축적 후 rubric 재교정 (4주 데이터 확보 시)
- **NQ-36**: ~~Rubric v2 evidence 필드를 admin UI에 노출~~ — `994084e` + `aa7fd37`로 QualityPanel collapsible + theme-aware 완료 (Apr 22). **Done.**
- **Currency unit post-processor** (optional C from prompt-engineering analysis): EN/KO 본문 숫자 단위 deterministic 검증. `$X billion ≠ X억` 류 100× 오역을 writer 프롬프트 강화(B3)로 ~50% 경감했지만 결정론적 게이트 없음. 재발 시 도입 검토.

### 잠재 (v12 트리거)

- 모델 패밀리 전환 (gpt-5 → 차기)
- 스테이지 추가 (예: `fact_check` 별도 스테이지)
- Multi-locale 확장 (EN/KO 외 언어)
- Pipeline async refactoring (현재 sequential stage 중 병렬 가능한 구간)

---

## Related

- [[2026-04-01-news-pipeline-v10]] — v10 journal (gpt-5 + CP 재설계 + 품질 체계 도입)
- [[2026-04-17-news-pipeline-hardening-retro]] — v10-hardening retro (3 phase + API diet + audit cleanup)
- [[2026-04-19-handbook-seed-800]] — Handbook 대량 생성 기반 rubric v2 검증 플랜
- [[2026-04-20-rerun-from-quality-plan]] — rerun=quality 구현 플랜
- [[2026-04-21-cp-thread-url-plumbing]] — CP thread URL plumbing 구현 플랜
- [[2026-04-22-nq-40-phase-2-cp-quality]] — Phase 2a CP quality measurement-only 도입 플랜
- [[2026-04-22-admin-news-editor-split-and-rerun]] — Admin editor 리팩터 + inline rerun 버튼 플랜
- [[ACTIVE_SPRINT]] — NP-QUALITY-01/02/03/06 + NQ-30~35 + NQ-42

---

## 세션 흐름 (참고용 시간순)

1. 4/7~14: Weekly Phase 1/2 진화 (excerpt, focus_items, citation 규칙, quiz 등)
2. 4/15~17: Pipeline hardening 3-phase (파일 분리, URL validation, 토큰 다이어트)
3. 4/18: Handbook rubric v2 착수 (`8249e9d`)
4. 4/19: Draft 사고 (KO 영어 블록쿼트 + 96점) → NP-QUALITY-01/02/03/06 착수
5. 4/19-20: Enrich gate + URL liveness + classify authority + news rubric v2 이식
6. 4/20: rerun_from=quality 전체 설계 + 구현 (7 task subagent-driven)
7. 4/21 오전: Apr 19 개선 3개 (writer prompt, focus_items_ko fallback, CP citation v1)
8. 4/21 점심: CP citation v1 production 접촉 → 2 근본 버그 노출 → 분석 → URL plumbing 설계
9. 4/21 오후: CP thread URL plumbing 전면 구현 (7 task) + Apr 21 retrofit
10. 4/21 저녁: Weekly rubric v2 이식 (`c5ebc35`) → 3 pipeline parity 완성
11. 4/21 밤: v11 journal 작성 (이 글)
12. 4/22 아침: Apr 22 첫 fresh run 감사 → judge 환각 2건 발견 (`fa89370`, `9bb0a73`, `d0dbb1d` → squash `7ca0d3b`)
13. 4/22 점심: NQ-40 Phase 2a CP quality sub-scoring (`00c655e`) + QualityPanel theme-aware (`994084e`) + admin editor split (`c296a5e`) + inline rerun 버튼 (`e964dc9`) + collapsible (`aa7fd37`)
14. 4/22 오후: Rubric gap 2차 fill — claim_calibration + temporal + internal consistency (`2ffe318`) → writer-side 거울 (`def72b7`, `ab656f4`)
15. 4/22 저녁: Infra 정비 — rerun save log fix (`57b8aa8`) + Apr 21 backfill + detail/list parity (`b2d250d`)
16. 4/22 밤: GitHub trending 튜닝 (`106e845`) + NQ-42 sprint 등록 (`99c52d1`) + v11.1 journal 추가 (결정 G, 이 섹션)

---

## 결론

Apr 19 사고 하나가 채점 아키텍처를 세대 교체시켰다.

**v10의 "LLM 점수 + 코드 감점"**은 감점 상한이 없고 단일 점수의 출처를 추적할 수 없었다. **v11의 "LLM 10 sub-score + evidence + 코드 aggregation + issue penalty + cap"**은 모든 점수가 출처와 함께 설명되고, 검증 가능한 게이트 레이어가 명시적으로 존재한다.

추가로 URL liveness + enrich gate + classify authority + HN/Reddit thread URL plumbing이 **수집 ~ 최종 출력 전 경로에 "신호 보존" 계층**을 깔았다. 한 번 놓친 신호가 다음 스테이지에서 다시 필요해지지 않도록.

체감 상 느린 작업이었지만(2주), **구조는 단단해졌다**. v10에서 v11로의 이동은 "같은 집 벽지 바꾼 것"이 아니라 "기초에 철근 다시 넣은 것". 비용 +8%는 합당한 값.

v10 retro(2026-04-17)의 "완료 선언은 snapshot이지 관 뚜껑이 아님" 교훈이 v11 작업 중에도 재입증됨. CP citation v1이 review 통과하고도 production에서 2개 근본 버그 노출한 사건(결정 C.2)이 그 증거. Integration smoke를 spec review 단계에 박는 것을 다음 사이클 규율로 삼음.

**가장 단단한 레슨**: "단일 사고는 보통 구조적이다" (교훈 36). 사고 하나를 세 층위(rubric / gates / writer)로 분산해서 수정하는 게 재발 방지의 정석. 한 곳만 패치하면 같은 구조적 틈이 다른 증상으로 또 나온다.

---

## v11.1 추가 결론 (2026-04-22)

v11이 착지한 다음날(4/22) 첫 공식 fresh run을 돌려보니 **v11의 구조는 맞지만 반사면이 덜 맞춰졌음**이 드러남 — judge 환각 2건, writer-QC 거울 미정합 3건, pipeline_logs 일관성 버그 1건.

v11이 "기초에 철근 넣기"였다면 **v11.1은 "그 철근의 끝부분끼리 용접"**. 새 구조물 추가 없이 기존 부재들의 접합부를 일관화:

- Rubric 추가 3 dimension(claim_calibration / temporal / internal consistency) 각각 writer-side 거울 쌍으로 커밋
- `rerun_from=quality`의 cascade-delete가 재생성 없이 끝나던 save 로그 audit gap 메움
- Admin iteration tool chain (editor + QualityPanel + rerun 버튼)이 v11 본체와 속도 맞추게 개선

**가장 중요한 교훈**: 품질 개념은 한쪽에만 두면 비대칭이 누적된다. **QC에 룰 = Writer에 룰 쌍으로 묶어서 설계**하는 것(교훈 37)이 v11.1의 운영 원칙. 이후 차기 sub-score 추가 시 writer-side 거울을 같은 커밋에 포함시키는 게 defaults.

실측 효과: Apr 21 rewrite-both 결과 research 85→95, business 84→100. v11 원본 점수대(76-93)는 v11.1 거울 동기화 후 **이론값과 실제 수렴** (major factual error 근절 + minor issue 대부분 해소). 다음 Apr 23 cron이 자연 조건 측정치 제공.
