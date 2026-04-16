---
title: News Pipeline Hardening 회고
date: 2026-04-17
type: journal / retro
related:
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase1-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase2-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase3-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md
---

# News Pipeline Hardening 회고

## TL;DR

이틀 동안 뉴스 파이프라인을 통째로 갈아엎었다. 3 phase + API 다이어트 + audit cleanup까지 commit 34개. 처음엔 "1-2주 걸릴 것 같은데…" 싶었는데 실제론 사실상 이틀 세션 안에 끝났음. 이유는 하나 — **scope가 계속 축소돼서**. 측정해보니 원래 계획의 절반은 이미 필요 없거나 이미 존재하는 것이었다.

## 시작 — 왜 굳이 했나

파이프라인 코드가 너무 부담스러워진 지가 꽤 됐다. `pipeline.py` 한 파일이 3794줄. 한 줄 고치려고 열면 스크롤만 한참 하다가 "나중에 하지 뭐" 하고 닫은 게 여러 번. 뉴스 생성 비용도 은근히 쌓이고 있었고, 가끔 가짜 URL 인용이 눈에 띄어서 찜찜했다.

평가부터 시작했다. 전체 파이프라인을 훑고 강점/약점/개선안을 정리받았다. 나온 옵션 3개: A(신뢰도 — URL 검증), B(엔지니어링 — 파일 분리), C(비용 — 토큰 축소). **다 하기로 했다**. 어차피 한 번에 하는 게 context 안 잃고 효율적.

## Phase 1 — 파일 분리

3794줄을 4개 파일로 쪼갤지 7개로 쪼갤지 고민했다. "솔로 프로젝트면 4개가 적당, 7개는 과하다"는 조언 듣고 4개로. 결과: pipeline.py 3794 → 2149줄 (-43%).

여기서 하마터면 큰 사고 날 뻔한 부분이 하나 있었다. 외부에서 pipeline.py를 import하는 지점이 20곳이 넘어서 (routers/cron.py + 6개 test files), 단순히 분리하면 다 깨진다. **shim re-export 패턴**을 미리 잡아준 덕분에 외부 코드 한 줄도 안 건드리고 리팩토링 가능했다. 나 혼자 했으면 import를 일일이 고치다가 어디선가 놓쳤을 것.

## Phase 2 — 신뢰도

여기서 처음 "scope 축소" 패턴이 나왔다. 원래 spec에 PydanticAI 마이그레이션이 있었는데, 내가 "지금 멀쩡히 돌아가는 걸 왜 굳이?" 하고 물었다. 바로 인정하고 drop — "최신 툴 편향이었다"고. 캐싱도, silent failure 로깅 강화도 같은 패턴으로 drop. **이번 세션 내내 반복된 흐름**: 측정 → "생각보다 필요 없음" 발견 → 축소.

URL 검증 구현은 세 번 뒤집었다:
1. 첫 production 검증 → `fact_pack`에 `url_validation_failed` 필드가 아예 없음. fact_pack 구성이 화이트리스트 방식인데 새 필드를 추가 안 했음.
2. 고쳤더니 **모든 citation이 "unknown"**으로 찍힘. `primary_url` 1개만 allowlist에 넣었는데 writer는 group 전체를 받음.
3. 고쳤더니 research만 4개 false positive. `enriched_map` URL이 allowlist에 없음.

매번 production에서만 드러났다. 로컬 테스트는 mock 기반이라 실제 persistence 계층은 안 가봄. **이 교훈이 이번에 제일 비쌌다.** 다음엔 integration test가 실제 DB payload까지 봐야 한다.

중간에 예상 밖의 발견이 있었다. 14일치 research digest source를 분석해보니 **47%가 SEO-spam 도메인**이었다. agent-wars.com, lilting.ch 같은 것들. 그냥 우연이라기엔 너무 편중돼 있었다. `news_domain_filters` 테이블에 blocklist 추가하고 production에서 0%로 떨어뜨림. 원래 계획에 없던 작업이라 bonus.

Few-shot 예시는 측정 결과 기준 Top 2 failure mode에만 추가: frontload + overclaim/clarity, ko + locale. **추측으로 "여기가 문제일 거야" 하지 말고 데이터부터 보는 게 습관이 됐다.**

## API 다이어트 (보너스)

Tavily 무료 쿼터가 은근히 빠듯해서 신경 쓰였다. 6개 collector 각각의 효율을 측정:

- hf_papers: 31% (가장 효율적)
- github_trending: 12%
- tavily: 6.5%
- arxiv: 6%
- exa: 3%
- brave: 1.88% (거의 낭비)

Brave 수집은 통째로 제거 (커뮤니티 반응용은 유지), Exa 12→5, Tavily도 arxiv/github 중복 쿼리 2개 제거. 유료 쿼리 24→11개.

여기서 **내가 pushback 한 번 잘했다** 싶은 순간이 있었다. 처음에 "Tavily는 workhorse라 유지" 얘기가 나왔는데 내가 "Tavily quota 부족한데 많이 쓰는 거 아깝지 않아?" 하니까 바로 재계산해서 Tavily도 중복 쿼리 2개는 줄일 수 있다고 수정됨. 내가 안 물었으면 놓쳤을 포인트.

## Phase 3 — 토큰 다이어트

또 scope 축소. Spec엔 4곳 messages 수정 + 토큰 로깅 인프라 + 프롬프트 축소가 있었는데:
- 토큰 로깅은 **이미 `_log_stage`에 구현돼 있음**
- ranking.py 4곳 중 **3곳은 이미** system+user 구조. 1곳만 수정하면 됨

남은 건 프롬프트 축소. QUALITY_CHECK 5개 프롬프트가 공유 블록을 거의 그대로 반복하고 있었고 (유사도 0.76-0.86), `replace_all` 한 번으로 3블록 단축 → **-1956 tokens**, 목표 -1250의 156% 달성.

"CLASSIFICATION도 축약하자"는 계획이 있었는데 목표 초과 달성해서 건너뜀. **이게 나중에 audit에서 문제가 됨.**

## 내가 "뭔가 짧아진 것 같은데?" 한 순간

2026-04-14 뉴스 돌려보니 내용이 좀 짧게 느껴졌다. 측정해보니:

- Business digest: **-22%** (EN expert 12855 → 9994)
- Research digest: +7% (사실상 안정)

이유: API diet가 비대칭으로 때렸다. Research는 무료 collector(arxiv/github/HF)에 의존해서 영향 없고, Business는 유료(Tavily/Exa/Brave)에 크게 의존 → candidate pool 축소. Business digest만 짧아진 것.

Quality score는 오히려 올라감 (68→85). 짧아졌지만 집중된 느낌.

Option A(관찰) / B(Exa 부분 복원) / C(완전 revert) 중에서 B 선택. **단, 단서가 달렸다**: "3→5 복원은 측정 근거 없는 middle-ground, 관찰 후 재판단". 솔직한 답변이라 편했다.

그리고 내가 물었다: "Exa 넉넉하게 잡는 게 소용없어서 줄였던 건데 지금 복원이 뭐야?" 대답: **"맞음. 일관성 살짝 뒤섞임. 데이터 → 직감 전환한 셈."** 우기지 않고 인정해서 좋았다. 이 정도 정직함은 신뢰감을 쌓음.

## Audit 피드백 — 이번에 제일 많이 배운 부분

"모든 phase 끝났다"고 journal까지 쓴 후에 audit 피드백 4건이 왔다:

1. Dead 재정의 6건 중 3건만 제거함 (TITLE_STRATEGY/ONE_LINE_SUMMARY만 했고 GUIDEs 3개 남음)
2. "Return JSON only" 문구 7회 반복 — H1 audit 기준 미완료
3. RANKING_SYSTEM_PROMPT_V2 rename 안 됨, M4 category mismatch도 남음
4. C2 구조적 방지가 post-hoc validator만 있음, 프롬프트 앞단에 citation guard 없음

내가 날카롭게 물었다: **"너가 무슨 생각이 따로 있어서 이렇게 작업됐던 거야?"**

솔직한 답이 왔다:
- 1, 2, 4번: "생각이 있어서"가 아니라 **그냥 놓쳤음**. 체계적 재스캔 안 했음.
- 3번: 의도적 scope 축소 (별도 prompt-audit cycle 대상)

자기 비판으로 "target 달성 → YAGNI 관성 stop" 패턴을 정리해줌. 반론 우기지 않고 정직하게. 이게 이번 세션에서 제일 배운 부분.

**내 쪽에서도 반성할 점**: phase complete 선언할 때 "spec Done criteria 충족"을 "모든 가능한 개선 끝"으로 너무 관대하게 해석했음. Review cycle이 별도 단계라는 인식이 없었다. 다음엔 **"Phase N.5 — audit review + cleanup"**을 명시적으로 scope에 넣기.

1, 2, 4번 cleanup 20분 만에 끝냄. 파일 1690 → 1610줄, citation guard 1 단락 추가 (prompt-side + post-hoc 2층 방어).

## 실측 변화

| 지표 | Before | After | Δ |
|---|---|---|---|
| pipeline.py 줄 수 | 3794 | 2149 | **-43%** |
| prompts_news_pipeline.py 줄 수 | 1840 | 1610 | -12.5% |
| 유료 API 쿼리/run | 24 | 13 | -46% |
| Prompt tokens (5 main) | 7750 | 5794 | -25% |
| Research SEO-spam 비율 | 47% | 0% | 제거 |
| Quality score (biz/research) | 68-74 | 85-92 | **+15pp** |
| URL hallucination 보호 | 없음 | 2층 방어 | 신설 |

## 드롭한 것들 (나중에 혹시 필요하면)

| 드롭 | 재검토 조건 |
|---|---|
| PydanticAI 마이그레이션 | JSON 파싱 실패가 운영 이슈로 부각될 때 |
| OpenAI 프롬프트 캐싱 | cron 빈도가 시간당 1회 이상 or persona digest call 10+ |
| Silent failure 로깅 강화 | 분류 결과 빈 배열 발행 사건 발생 시 |
| pipeline.py 7-파일 패키지 | 팀 합류 or 오픈소스 공개 시점 |
| Phase 3 CLASSIFICATION 축약 | 별도 prompt-audit cycle에서 |

## 다음에 다르게 할 것

1. **Phase N.5 개념을 미리 계획**: "Phase complete" 선언 후 별도 audit review + cleanup을 명시적으로 scope에 넣기. 오늘 같은 post-hoc catch-up 필요 없게.
2. **Dead code 제거는 체계적 grep 먼저**: 눈에 띈 것만 처리하지 말고 `^CONSTANT_NAME = """` 전체 패턴 스캔.
3. **Integration test는 persistence까지**: mock 기반 "function returns right dict" 수준으로는 부족. 실제 DB payload까지 검증하는 end-to-end test 비중 늘리기.
4. **Target 달성 = YAGNI 정지선이 아님**: "추가 low-hanging fruit 있나?" 한 번 더 묻는 습관. YAGNI는 "필요 없는 것 안 만들기"지 "필요 있는데 귀찮은 것 skip"이 아님.
5. **데이터 vs 직감 충돌 시 기본은 데이터**: Option B Exa 복원 같은 middle-ground는 유혹적이지만 검증 안 된 가설 추가일 뿐. 관찰 → 재조정 패턴이 더 건강.

## 2주 관찰 대상 (자연스럽게 해결)

1. Option B Exa 복원이 business 길이 회복시키는가 (다음 2-3 cron)
2. Phase 3 runtime 토큰 감소 (`measure_token_usage.py --days 3` 3일 후)
3. Few-shot 효과 — frontload+overclaim / ko+locale issue 감소 (measurement v2, 2주 후)
4. Business digest "얇음" 체감 지속 여부 (주관 체크)
5. Citation guard 효과 — `url_validation_failed=true` 비율 감소 (post-hoc validator 의존도 감소 기대)

## 세션 흐름 (참고용 시간순)

1. 평가 + brainstorming → 3-phase 구조 도출
2. Design doc + 3 plan 작성 (each plan reviewed & polished)
3. Phase 1 실행 (11 commits, production verify)
4. Phase 1 post-deploy에서 **47% SEO-spam 발견** → Phase 2 scope 확장
5. Phase 2 실행 → URL validation 3번 iteration
6. API diet (14일 measurement 결과 기반)
7. Phase 3 실행 → -1956 tokens
8. Option B course-correct (04-14 business -22% 발견)
9. Phase 1/2/3 공식 complete + journal (첫 번째 버전)
10. **Audit 피드백 4건 → cleanup 3건 (3번은 별도 cycle)**
11. Journal 업데이트 (이 글)

## 결론

측정 → scope 축소 → 구현 → production verify → course-correct → **audit review → cleanup** 루프가 작동했다. 이 "audit review"가 이번에 처음 명시적으로 의식된 단계. 다음 프로젝트부터는 phase 계획에 포함할 것.

`pipeline.py` -43%, 프롬프트 -12.5%, 유료 쿼리 -46%, 품질 +15pp. **Solo 2일 작업으로는 나쁘지 않다.**

가장 비싼 교훈: **"완료" 선언은 snapshot이지 관 뚜껑이 아님.** 완료했다고 생각한 뒤에도 review가 별도 단계.
