# CP 렌더링 체인 + 블록리스트 + 관찰성 — 2026-04-27

전날 [[2026-04-26-cp-per-platform-redesign]] 의 plan 실행을 시작점으로 하루 동안 4개 fix 영역이 시퀀셜하게 펼쳐졌다. 한 fix 가 다음 단계 버그를 노출시키는 패턴이 반복됐고, 결과적으로 코드/데이터/관찰성 세 레이어 모두에서 손을 봤다.

## 발화점

Apr 26 발행분 audit 에서 user 가 세 가지를 지적:
1. Business CP 인용문에 "Who are you quoting?" / "누구 말을 인용한 거야?" 메타-리액션이 quote 안에 박혀 있음
2. Business source_cards 에 zamin.uz, dailyofusa.com, news247network.com, briefglance.com 등 미러 도메인
3. Research KO digest 에 `quiz_poll_expert` 누락 (`quiz_poll_learner` 만 있음)

## 1) Plan 실행 — Voice + Quiz Contract

`vault/09-Implementation/plans/2026-04-26-cp-voice-and-quiz-contract.md` 6개 task 를 subagent-driven 으로 진행. 핵심 변경:

| Task | 변경 | Commit |
|---|---|---|
| 1 | HN scraper 가 `>` quote-of-other-comment 라인 제거 | `410942e` + `d9cd951` |
| 2 | Quiz validator 가 `answer_index: int 0-3` 우선 + legacy `answer` text fallback | `75f569b` + `5c6fd8a` |
| 3 | News writer Pydantic + strict json_schema 가 `answer_index` 강제, `field_validator` 가 bool 거부 | `6b40ec7` + `f2f451b` |
| 4 | 일일 writer 프롬프트 → `answer_index` | `457f8bf` |
| 5 | 위클리 프롬프트 6 사이트 (3 example + 3 rule) → `answer_index` | `7fcd1ee` + `d50b126` |

**근본 원리:** strict json_schema 는 per-field 타입은 강제하지만 cross-field 불변식 (`answer ∈ options`) 은 표현 불가. 데이터 contract 자체를 실패 불가능한 형태로 변경 — 정수 인덱스로 옮기면 검증이 mechanical 매칭이 되어 silent drop 의 클래스가 사라짐.

## 2) CP 렌더링 체인 — 후처리 정규식 3개 충돌 발견

Apr 26 rerun-from-write 로 검증 시도 — Issue 3 는 CLEAN, 그런데 본문에 `**[Hacker News]** (https://news.ycombinator.com/item?id=...) (805↑)` 식의 broken split 이 그대로. 처음엔 Railway redeploy timing 의심 → standalone 테스트로 linkifier 가 정상 작동함 확인.

진짜 원인 추적해서 발견: **`pipeline_digest.py:1389-1391` 의 `_fix_bold_paren_abbrev` 정규식이 너무 광범위해서 linkifier 출력을 다시 깨뜨림.**

이걸 좁히자 (`commit 10c05fb`) 두 번째 버그 노출 — `_renumber_citations.placeholder_re` 가 `[Hacker News](URL)` 같은 정상 마크다운 링크를 placeholder 로 오인해 라벨을 숫자로 바꾸거나 (URL 미허용 시) 통째로 strip 해 `**** (805↑)` 스텁 생성. 거기에 추가로 save-path `allowed_urls` 가 CP thread URL 을 포함 안 해서 strip 트리거됨 (`commit 91f157d`).

**3-stage 후처리 체인 충돌:**

```
linkifier (출력: **[X](URL)**)
   ↓
_fix_bold_paren_abbrev (옛날 광범위 regex가 → **[X]** (URL))   ❌
   ↓
_renumber_citations.placeholder_re (정상 링크를 placeholder로 → **[N](URL)** or strip)  ❌
   ↓
allowed_urls 체크 (thread URL 누락 → strip)  ❌
   ↓
DB 저장
```

세 곳 모두 좁혀서 fix. 메모리 [[feedback_cp_postprocess_chain]] 에 이 패턴 등재.

## 3) Mirror 도메인 블록리스트 — Issue 2

처음엔 `confidence='low'` 일괄 차단 + 작은 화이트리스트로 가려 했으나 14일 audit 결과 **`confidence='low'` 의 ~40% 가 정상 미디어** (axios, cnbc, nytimes, AWS 공식 등) 인 게 드러남. 일괄 차단은 false positive 너무 큼.

수정안 — **확정된 mirror/aggregator 21개 후보 → per-domain content audit 으로 18개 채택**, 3개는 정상으로 제외:

**제외한 정상 콘텐츠 (분류기 false positive):**
- `tianpan.co` — Tian Pan 의 개인 기술 블로그 (debugging 글 등 original content)
- `zhihang-fu.github.io` — 학술 publication page (InteractRAG 논문)
- `agent-sh.github.io` — agnix framework 공식 documentation

**채택한 18개:** Apr 26 미러 6개 (zamin.uz, dailyofusa, news247network, briefglance, harianbasis.co, central-asia.news) + 14일 audit 패턴들 (liner.com 30회 — 논문 wholesale 복제, aisecurity-portal.org 10회 등) + Apr 27 신규 발견 5개. 자세한 근거는 `backend/scripts/seed_blocklist_2026-04-27.py` 의 docstring + `commit 19cc5e2`.

`news_domain_filters.research_blocklist` 에 INSERT (8 → 26 entries). 코드 변경 0 — 기존 `_classify_source_meta` 가 자동 `tier='spam'` 처리.

3개 false positive 는 **분류기 자체 한계의 신호** — sprint 에 `NQ-43` 으로 등재.

## 4) Service Tier 관찰성 (외부 리뷰 피드백)

외부 리뷰가 "service_tier 가 합산 로직에서 사라짐" 을 정확히 지적. 검증:
- Apr 27 cron 의 `pipeline_logs.debug_meta` 확인 → 실제로 `community_summarize`, `ranking`, `quality:*`, `summary` 가 tier=null
- 비용 계산은 정상 (gpt-5-mini flex 단가와 일치) — 즉 **logging-only 버그**

`merge_usage_metrics` 가 service_tier 키를 유지하지 않는 것과, 5개 `extract_usage_metrics` 호출에 `requested_service_tier="flex"` 누락이 원인 (`commit dfa286c`).

**그러나 외부 리뷰의 처방 (`prompt_cache_retention=24h`) 은 잘못됨** — 그건 Anthropic API 의 개념이고, 우리 프로젝트는 OpenAI 전용. OpenAI cache 는 자동/서버 사이드 TTL ~5-10분이라 사용자가 retention 컨트롤 못 함. 일일 cron 간격에서 inter-run cache hit 은 기대 불가 — 불행히도 어떤 파라미터로도 해결 안 됨.

## 5) Verification 자동화

[Routine `trig_018kdT3rij5hcjekMstca4BP`](https://claude.ai/code/routines/trig_018kdT3rij5hcjekMstca4BP) — Apr 28 11:00 KST one-time 에이전트로 cron 결과 자동 점검 (4 posts × quiz keys, 18 블록리스트 leak, CP regex 3 패턴 카운트, 보이스 마커, tier observability, 신규 low-confidence 도메인).

## 무엇이 더 단단해졌나

| 레이어 | 변경 | 효과 |
|---|---|---|
| 데이터 contract | quiz `answer_index` int 0-3 | cross-field 불변식이 schema 레벨에서 enforce됨 |
| 데이터 normalization | HN scraper voice 분리 | 보이스 fusion 클래스 자체 제거 |
| 후처리 체인 | 3 regex 좁힘 + thread URL allowlist | linkifier 출력 내내 보존 |
| 데이터 큐레이션 | research_blocklist 8 → 26 | 14일 audit 기반 즉시 fix |
| 관찰성 | service_tier merge 보존 | DB tier 컬럼이 실제 의도 반영 |

## 무엇이 남았나

- **NQ-43 — Source confidence classifier 개선** (1-2주 작업, sprint 등록). 이 분류기가 정확해지면 blocklist 큐레이션 부담 감소
- **Apr 28 자연 검증** — routine 실행 후 결과 확인
- **Apr 30 metric 윈도우** — 메모리 `project_news_pipeline_state` 가 추적하던 4개 long-tail metric

## 회고 — 패턴

오늘 가장 큰 학습 두 가지:

1. **"한 단계의 fix 가 그 다음 단계를 노출시킨다"** — linkifier 가 비로소 깨끗한 출력을 내자, 그동안 사후처리에서 묻혀있던 두 버그 (bold-paren-abbrev, placeholder_re) 가 동시에 드러남. 나머지 fix 가 이전엔 우연히 망가진 입력에 대해 망가진 출력을 잘 견뎌낸 셈. cumulative 회귀 방지 단위 테스트가 부재했다는 의미.

2. **"분류기의 정확도가 거버넌스 정책의 기반"** — Issue 2 에서 처음 확신한 "confidence='low' = 의심" 은 실제 분포에서 60/40 좋은/나쁜 비율. 정책 (블록리스트) 을 분류기 위에 쌓을 때 분류기 정확도를 먼저 측정하지 않으면 false positive 큰 실수.

## Commit log

| Commit | 영역 |
|---|---|
| `410942e`, `d9cd951` | Task 1 — HN voice normalization |
| `75f569b`, `5c6fd8a` | Task 2 — Quiz validator answer_index + bool guard |
| `6b40ec7`, `f2f451b` | Task 3 — News writer Pydantic + strict schema answer_index |
| `457f8bf` | Task 4 — Daily writer prompt answer_index |
| `7fcd1ee`, `d50b126` | Task 5 — Weekly prompt answer_index (6 sites) |
| `ea70c57` | Plan doc commit |
| `10c05fb` | CP rendering — bold-paren-abbrev 좁힘 |
| `91f157d` | CP rendering — placeholder_re + thread URL allowlist |
| `dfa286c` | service_tier merge preservation + 5 extract sites |
| `19cc5e2` | Blocklist 18 도메인 + NQ-43 sprint task |

총 13개 commit (오늘 13:00 KST 부터 다음 날 11:00 KST까지 약 22h).
