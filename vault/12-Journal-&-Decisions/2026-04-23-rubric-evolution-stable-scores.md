# Rubric Evolution × Stable High Scores (2026-04-23)

**TL;DR**: 지난 한 달간 뉴스 QC rubric을 여러 방향으로 엄격하게 조였는데 (overclaim 감지, 날짜 절대화, locale parity, URL attribution, citation coverage, strict schema 등) writer의 quality 점수가 떨어지지 않고 **89-97로 안정 유지**. 보통 새 검사가 추가되면 일시적 점수 drop이 있는데 이번엔 없었음. Schema enforcement + 프롬프트 강화 + reasoning_effort=high 조합이 writer behavior를 사전에 교정한 효과로 추정.

---

## 최근 한 달간 올라간 rubric bar

### 2026-03-25 ~ 04-15 전후 (NQ-37 / v11)

- **v11 rubric 도입** — 기존 단일 `score` → 9개 sub-score 구조 (evidence-anchored)
- **`claim_calibration`** — "dominates / 장악 / 압도적 / 석권" 같은 retrospective overclaim 감지
- **`temporal_anchoring`** (fluency sub-score) — "recently / yesterday / 최근 / 지난주" 같은 relative date 감지 (디지털 아카이브 컨텍스트에서 의미 열화)
- **`internal_consistency`** — 섹션 간 주장 일관성 검증 (한 섹션에서 "대세 오픈소스", 다른 섹션에서 "폐쇄 추세" 같은 상충)

### 2026-04-15 ~ 04-22 전후 (NQ-40 / Phase 2 / 주간 추가)

- **`citation_coverage`** — paragraph 당 최소 1개 citation 필수
- **Community Pulse exempt 규칙** — `> — [Source](URL)` 형식 blockquote는 inline citation 예외
- **`attribution_domain_match`** — "AP reports [4](https://www.mrt.com/...)" 같은 syndication 오귀속 감지 (wire service 이름을 쓰면 URL도 해당 wire 도메인이어야)
- **NQ-40 Phase 2a CP quality** — community_pulse 3개 sub-scores (cp_relevance / substance / translation_fidelity). Weight=0 (measurement-only, 2주 관찰 후 Phase 2b에서 가중치 결정)
- **`$X million` 통화 변환 엄격 검증** — `$150M = 1.5억 달러` (not 5,000만 = 3x 오류) 같은 자릿수 정확성
- **`claim_coverage` — focus_items P2 평가형 문구 금지** — "raises bar / sets new standard / transforms" 같은 press-release 표현 대신 "enables X / reduces Y" 같은 객관적 메커니즘 요구
- **주간 Top Stories 5-7 → 7-10** — 컨텐츠 밀도 상향

### 2026-04-23 (오늘)

- **`[CITE_N]` placeholder contract** — body에 inline `[N](URL)` 금지, `citations[]` 별도 배열 필수
- **OpenAI strict `json_schema`** — `citations[].url` enum으로 API 레벨 allowlist 강제
- **BODY_LOCALE_PARITY 강화** — EN/KO 간 citation placeholder 수 동일 요구
- **HALLUCINATION_GUARD 재작성** — 7개 언어 규칙 + attribution domain 매칭 + absolute-date preference

## 실측 — 점수는 안 떨어졌어

3일간 (Apr 21-23) final config로 평가:

| Date | Research exp/lrn | Business exp/lrn | 평균 |
|------|------------------|------------------|------|
| Apr 21 | 94/94 | 94/94 | 94.0 |
| Apr 22 | 94/94 | 95/95 | 94.5 |
| Apr 23 | 90/90 | 89/89 | 89.5 |

전부 **auto-publish threshold 85 이상**. 3일 평균 **92.7**.

비교 기준점으로, NQ-37 (v11 도입) 직후 2026-03-25~28 평균 ~87-93, NQ-40 Phase 2a 도입 후 2026-04-17~20 평균 ~90-96. **지속적으로 엄격해지는데 점수는 오히려 안정 상승 추세**.

## 왜 떨어지지 않았나

일반적 패턴: 새 rubric 항목 추가 → writer가 아직 적응 못 함 → 일시적 점수 drop → 프롬프트 조정 후 회복. 이번엔 drop 없이 바로 안정.

추정 원인:

### 1) Schema enforcement가 구조적 실패를 선제 차단

URL hallucination은 `fact_pack.url_validation_failed`로 감지되어 `url_validation` rubric에서 점수를 크게 깎았었어. 지금은 strict `json_schema` enum이 API 레벨에서 원천 차단 → `url_validation_failed=0` 항상. 이 사분면 점수 손실 없음.

### 2) 프롬프트 강화가 writer behavior 내재화

HALLUCINATION_GUARD에 추가된 구체 예시들 (forbidden 영어 / 한국어 동사 리스트, 날짜 절대화 worked example, attribution domain matching demo, `$X million` 변환 예시)이 writer의 "주의 대상"을 명확히 했어. Writer가 self-check에서 해당 패턴 회피함.

### 3) `reasoning_effort=high`가 self-check 루프 철저화

프롬프트 끝에 있는 FINAL CHECKLIST 11개 항목 (citation coverage, sub-item count, paragraph count, frontload locale parity, body number parity, relative time scan, overclaim scan 등). High effort에서는 이 checklist를 실제로 훑고 나서 제출. Low에서는 skim-through에 그칠 가능성 높음.

### 4) BODY_LOCALE_PARITY + schema enum → EN/KO 자동 대칭

이전엔 KO body가 EN 대비 citation 수, 섹션 수, 숫자 각각 개별적으로 틀릴 수 있었어. 지금은 citation이 공통 `citations[]` 배열에서 substitute되므로 count 자동 일치. locale_integrity rubric에서 점수 안정.

### 5) Code-level validation이 LLM-level validation 대체

`_renumber_citations` + `validate_citation_urls`가 LLM에게 "이거 지켜" 말하는 대신 코드로 검증/처리. LLM은 이제 구조 준수보다 **내용 품질**에 reasoning token을 쓸 수 있음.

## 교훈

1. **Rubric을 올리기 전에 구조적 enforcement 먼저** — schema + code validation으로 bottom-line을 고정하면 rubric 상승 시 점수 변동 흡수 가능. 반대 순서 (rubric만 먼저 올리면) 점수 롤러코스터.

2. **Writer의 failure mode는 "주의 분산"** — 한 번에 1개 룰만 엄격히 강요하면 잘 따르지만, 10개 룰을 동시에 내밀면 가장 먼저 나오는 몇 개에만 주의 감. 해법: 중요 룰을 system message 최상단에 + HALLUCINATION_GUARD 같은 격리된 블록에 재진술 + FINAL CHECKLIST에 또 반복.

3. **"바뀐 bar가 높다"를 정량 측정하기 어려움** — 점수는 절대값이지만 rubric 정의가 바뀌면 비교 기준이 바뀜. Apr 21 94점과 Mar 10 94점은 같은 94가 아님 (기준이 올라갔으니 지금의 94가 더 높은 품질). 이런 "rubric drift"를 어떻게 기록할지 향후 고민.

4. **reasoning_effort=high는 "self-check" 가치가 rubric 엄격화 환경에서 특히 높다** — 체크할 항목이 11개로 늘어나니 skim-through 하면 놓치기 쉬움. 이 맥락이 "business에서도 high 유지" 결정의 숨은 근거.

## Follow-up

- Rubric drift 정량화 방법 연구 (예: 같은 기사를 구/신 rubric으로 각각 채점해서 offset 구하기)
- 4월 22일 이전 포스트들을 신 rubric으로 재채점해서 "진짜 개선폭" 측정 (현재 점수는 신 rubric 기반이니까 비교 불가)
- Weekly writer에도 동일한 rubric 강화 일관 적용 검토

## 참고

- [GPT-5 Efficiency Overhaul Results (2026-04-23)](2026-04-23-gpt5-efficiency-results.md) — 오늘 한 비용/citation 작업 전반
- URL compliance plan: `vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md`
- NQ-37 v11 rubric 전환: `vault/12-Journal-&-Decisions/2026-04-21-news-pipeline-v11.md` (있다면)
- NQ-40 Phase 2: `vault/09-Implementation/plans/2026-04-22-nq-40-phase-2-cp-quality.md`
