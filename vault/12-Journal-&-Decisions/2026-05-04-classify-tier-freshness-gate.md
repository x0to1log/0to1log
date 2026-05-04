# Classify Tier × Freshness Gate — 2026-05-04

## 발화점

5월 4일 business-digest review (qs=97점) 에서 진짜 quality 문제 발견:
- "OpenAI raises $122B at $852B" — 발표일 **2026-03-31** (5주 전)
- "OpenAI/AWS partnership" — 발표일 **2026-02-27** (9주 전)
- 출처: toolsstackai.com, aibusinessweekly.net, epinium.com 등 SEO/aggregator
- 옛 사건을 SEO 사이트가 "Just Raised" / "Today" 같은 fresh-bait 표현으로 재발행 → publish_date 필터 통과 → primary 슬롯 차지

QC 가 100/97 점 부여한 건 **structural quality** (섹션 완비, citation, 언어 유창성) 만 측정해서. **content freshness + source quality** 는 측정 안 함.

## 결정

깊은 토론 (freshness vs quality+curation 둘 다 중요) 후 결론:
- 두 목표는 같은 root cause 의 다른 면 — "낮은 출처에서 늦게 등장한 옛 사건" 이 둘 다 깨뜨림
- 하나의 통합된 게이트로 해결: **classify 단계의 source_tier × event_freshness matrix gate**

## Architecture — Phase 1 (prompt-only)

### Tier definitions

| Tier | 매핑 | 예시 |
|---|---|---|
| **TIER-1** | `source_kind ∈ {official_site, paper, official_repo}` 또는 `source_tier=primary` (단 `kind=analysis` 면 제외) | openai.com, arxiv.org, nvidianews, NYT, Reuters, Bloomberg |
| **TIER-2** | `media_tier=secondary AND source_confidence ∈ {high, medium}` + 14개 known-trusted 도메인 override (axios/reuters/bloomberg/nytimes/theverge/techcrunch/arstechnica/ieee/cnbc/forbes/wsj/ft/wired/technologyreview) | TechCrunch, The Verge, Axios, Ars Technica |
| **TIER-3** | 나머지 — analysis/secondary with low confidence, untyped, spam | toolsstackai, aibusinessweekly, epinium 등 SEO/aggregator |

### Decision matrix

| Tier | Freshness | 처리 |
|---|---|---|
| TIER-1 | FRESH (≤14d) | ✅ Primary |
| TIER-1 | UNKNOWN | ✅ Primary (tier-1 trust) |
| TIER-1 | OLD (>14d) | ❌ REJECT |
| TIER-2 | FRESH | ✅ Primary |
| TIER-2 | UNKNOWN | ⚠️ Enrichment only |
| TIER-2 | OLD | ❌ REJECT |
| TIER-3 | ANY | ❌ REJECT |

### Why prompt-only

Candidate formatter (`ranking.py:254`) 가 이미 `Source tier`/`kind`/`confidence` surface — LLM 이 그 신호를 *사용* 만 하면 됨. 코드 변경 0, 위험 0. Phase 2 (event_date 추출) 는 measurement 후 필요 시.

## Commits

| SHA | 변경 |
|---|---|
| `ea73733` | gate 섹션 + 4개 few-shot 예시를 CLASSIFICATION_SYSTEM_PROMPT 에 삽입 |
| `cef376b` | 5개 review 이슈 fix: `{batch_date}` placeholder 제거, TIER-1+analysis 타이브레이커, known-trusted media override (14 domains), multi-date 룰, Decision Process step 0 |
| `3d05dce` | 7개 regression test 추가 (tier 정의, freshness window, reject rules, few-shot, 순서, batch_date 부재, trusted media override) |
| `bea9222` | 4개 weak assertion 강화 (silent-return 제거, 14-day 정규식, TIER-3 proximity check, EXAMPLE PASS/REJECT count) |

총 prompt 길이: 110줄 → 177줄 (+67줄). Token cost 영향: classify 콜당 +~$0.0004 (negligible).

## 측정 계획 — 7일 관찰 윈도우 (2026-05-04 ~ 2026-05-11)

배포 후 매일 cron 결과 점검:

### 추적할 메트릭

| 메트릭 | 측정 방법 | 목표 |
|---|---|---|
| stale-recycle 발생 횟수 | 매일 digest 의 primary stories 마다 본문에서 사건 발생일 확인. batch_date 기준 14일 초과면 incident 1건 카운트 | **0** (Phase 1 충분) / 1-2 (Phase 2 검토) / 3+ (Phase 2 필수) |
| TIER-3 도메인이 source_cards 의 primary 자리 차지 비율 | 새 audit script 로 source_cards 의 첫 5개 출처 도메인 검사 | **0%** (gate 가 차단) |
| 정상 fresh 뉴스 누락 (false negative) | 같은 사건을 다음날 mainstream 이 다뤘는데 우리는 누락한 케이스 | **0** (없으면 ideal) / 1-2 OK / 3+ → 임계값 조정 또는 trusted media list 확장 |
| classify cost 변동 | pipeline_logs 의 classify stage cost 비교 (전 1주 평균 vs 새 1주) | <10% 증가 (token 추가만) |

### 정량적 평가 절차

매일 cron 후:
1. `news_posts.source_cards` 에서 published 된 4 posts 의 모든 출처 도메인 추출
2. 각 도메인을 TIER-1/2/3 로 분류 (gate 정의 따라)
3. 본문의 첫 5개 primary stories 마다 사건 발생일 추출 (manual 또는 LLM-assist)
4. 메트릭 4개 기록

7일 후 통합 평가:
- 메트릭 4개 모두 목표 달성 → Phase 1 sufficient, sprint task 종료
- stale-recycle 1-2건 발생 → root cause 분석 (snippet 에 날짜 명시 안 된 케이스인지) → Phase 2 (event_date LLM 추출) 필요성 결정
- false negative 다수 → known-trusted media list 확장 또는 TIER-2 정의 완화

## Phase 2 검토 트리거 (조건부)

다음 중 하나라도 발생 시 Phase 2 (event_date 추출 LLM 콜):
- stale-recycle 3건+ 발생 / 7일
- snippet 에 날짜 명시 없는 케이스가 stale-recycle 의 60%+
- 같은 출처에서 반복적으로 같은 옛 사건 통과

Phase 2 비용 추정: candidate 30개 × $0.002 ≈ $0.06/cron, 30일이면 ~$1.80 추가. 효과 대비 작은 비용.

## Risk register (plan 에서 가져옴)

| Risk | Likelihood | Mitigation |
|---|---|---|
| LLM 이 gate 일관성 없이 적용 | Medium | 4개 few-shot + 명시적 reject directive. Step 3 측정으로 정량화 |
| 정상 niche 도메인이 enrichment 로 강등 | Low-Med | TIER-2 fresh 는 primary 통과. TIER-3 만 항상 reject. 측정 후 known-trusted list 확장 |
| 기존 tier 분류기 정확도 갭 (NQ-43) | Medium | 이 plan 은 NQ-43 와 독립 — NQ-43 개선 시 gate 정확도 동반 향상 |
| TIER-1 retrospective 가 reject (mainstream 의 회고 분석) | Low | 자주 발생하면 Phase 3 의 "Industry Context" 섹션 별도 검토 |

## 미루어진 것 (NOT in this plan)

- **Phase 2** — event_date 추출 LLM. measurement 후 결정
- **Phase 3** — TIER-1 retrospective 를 별도 "Industry Context" 섹션으로 분리. Product UX 의사결정 필요
- **NQ-09** — story-level dedup against past 30 days (별도 sprint task). 이 plan 과 보완적
- **NQ-43** — source_tier classifier 정확도 개선 (별도 sprint task). 이 plan 과 보완적

## 회고 — 큰 그림

mirror domain 차단을 4월 27일에 18개, 5월 4일에 6개 추가했지만 매번 새 도메인이 등장 — **blocklist 게임이 무한**. Phase 1 의 tier-based gate 가 작동하면 새 SEO 도메인 자동 차단 → blocklist 큐레이션 부담 종료. Quality 측면 큰 architectural 진전.

다만 LLM 의 prompt-following 신뢰성이 곧 효과 — measurement 가 결정적.
