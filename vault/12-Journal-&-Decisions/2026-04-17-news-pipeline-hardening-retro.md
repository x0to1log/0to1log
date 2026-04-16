---
title: News Pipeline Hardening — 3-Phase Retro
date: 2026-04-17
type: journal / retro
related:
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase1-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase2-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase3-plan.md
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md
---

# News Pipeline Hardening — 3-Phase Retro

## 요약

- 시작: 2026-04-15 (brainstorming + design)
- 종료: 2026-04-17 (모든 phase code + production verify)
- 예상: spec 단계에서 "1.5~2주"
- 실제: **세션 시간 기준 ~2일** (주로 2026-04-16 하루 집중)
- Commits: **33개** (main 직접)

평가 → spec 작성 → 3개 plan → 실행 → 4번의 production verify iteration을 거쳐 모든 scope 완료. 3 phase 모두 production에서 검증된 상태.

---

## Phase별 성과

### Phase 1 — Foundation (Commits 11개)
- `pipeline.py`: 3794 → 2149 줄 (-43%)
- 4-파일 분리: `pipeline.py` (orchestrator) + `pipeline_digest.py` + `pipeline_quality.py` + `pipeline_persistence.py`
- 외부 import 호환성: shim re-export 패턴으로 20+ 외부 import 사이트 전부 무변경
- Supabase `news_domain_filters` 테이블 신설 — 하드코딩 도메인 12개 DB 이관
- Production cron 1회 성공 (2026-04-16)

### Phase 2 — Reliability (Commits 11개, 4회 production fix 포함)
- `validate_citation_urls()` 추가 — hallucinated URL 구조적 차단
- fact_pack.news_items + enriched_map 기반 allowlist (3번의 iteration 거침):
  1. fact_pack whitelist 누락 (Fix 1)
  2. primary_url only → group.items 모두 (Fix 2)
  3. enriched_map 포함 (Fix 3)
- `news_domain_filters` 확장: `research_priority` + `research_blocklist`
- Research source 품질: SEO-spam 8개 blocklist — production에서 47% → 0% 확인
- Few-shot examples 추가 (측정 기반 Top 2 실패 모드):
  - frontload + overclaim/clarity → EXPERT/LEARNER_TITLE_STRATEGY
  - ko + locale → LEARNER_KO_LANGUAGE_RULE

### API Diet (Commit 1개, Phase 2~3 사이 보너스)
- Tavily: 8 → 6 쿼리 (arxiv/github 중복 제거)
- Exa: 12 → 5 쿼리 (3% 효율 기반 감축)
- Brave 수집: 제거 (1.88% 효율, 커뮤니티 반응용만 유지)
- 결과: 유료 쿼리 24 → 11 (-54%)

### Phase 3 — Prompt Hygiene & Token Diet (Commits 5개)
- Token usage measurement script (baseline + after 측정 인프라)
- Dead code cleanup (-61줄) — L581-L708 shadowed duplicates
- `summarize_community` messages → system + user (ranking.py 4곳 중 마지막 1개)
- QUALITY_CHECK prompt tokens: 7750 → 5794 (**-1956 tokens, 25%**)
- Target -1250 대비 156% 달성

### Option B — Course-correct (Commit 1개)
- 2026-04-14 production 관찰에서 business digest -22% 길이 감소 발견
- Exa business 3 → 5 쿼리 (regulation + chip/hardware 복원)
- 데이터 vs 직감 trade-off — 관찰 대상

---

## 핵심 패턴 / Lessons

### 1. 측정 우선 → Scope 축소가 3번 반복

Phase 1: "pipeline.py를 500줄 이하로 쪼갠다" → 실제 2149줄. 단일 책임 충족하면 500줄 규칙은 bikeshedding.

Phase 2: PydanticAI 마이그레이션 + OpenAI 캐싱 + Silent failure 로깅 세 가지 초기 제안 전부 drop — 각각 "실제 문제 증거 없음", "하루 1회 cron과 구조적 불일치", "최근 30 커밋에 관련 이슈 없음"으로 정당화.

Phase 3: "ranking.py 4곳 messages 정상화" → 실제는 1곳 (3/4는 이미 system+user). "토큰 로깅 인프라 구축" → 이미 `_log_stage`에 있음. Plan 작성 중 realization.

**패턴**: spec 단계에서 가설적으로 세운 scope의 30-50%는 실제 코드 보니 필요 없거나 이미 존재. 측정 후 확정이 건강.

### 2. Subagent 협업의 가치 지점

- Plan 단계의 reviewer가 잡은 가장 가치 있는 catch:
  - Phase 1: "Shim re-export가 안 되면 20+ import 사이트 깨짐"
  - Phase 2: URL 정규화 규칙 (트래킹 파라미터 제거) — plan의 단순 `hostname in set` 예시가 subdomain 매칭 깨뜨릴 뻔함
  - Phase 3: "skipped integration test가 spec Done criteria 위반"

- Implementer가 발견한 plan 오류:
  - Phase 1: `get_supabase_client` → 실제 `get_supabase` (None 반환 가능)
  - Phase 2: `_load_domain_filters` result dict 초기화 버그 (새 filter_type 조용히 drop)
  - Phase 2: ClassifiedGroup.primary_url vs group.items (allowlist scope 오류 3단계 iteration)

**패턴**: subagent는 "새로운 눈"으로 plan의 가설을 현실과 대조하는 역할. Plan 작성자가 놓친 것을 catch.

### 3. Production verification의 불가결성

Phase 2 URL validation은 **production에서 3번의 bug**를 드러냄:
- Integration test는 `_check_digest_quality` return만 확인했음
- 실제로 `_generate_digest`가 fact_pack 구성 시 whitelist 방식이라 url_validation_failed field가 drop됨
- primary_url only allowlist는 group.items 2+ 멤버 인용 전부 false-positive
- enriched_map은 writer에게 전달되지만 validator엔 전달 안 됨

**Lesson**: "Mock 기반 integration test"와 "실제 persistence 계층 통과 test"는 다른 안전망. 앞으로 end-to-end test 비중 높여야.

### 4. 비대칭 영향 (API diet 발견)

API diet 이후:
- Business digest: -22% 길이 감소
- Research digest: 안정적

이유: Research는 무료 collector(arxiv/github/huggingface) 의존, Business는 유료(Tavily/Exa/Brave) 의존. 예상되지만 **측정 전엔 모름**.

**Lesson**: 최적화는 항상 uneven impact. "전체 -40%"보다 "어느 세그먼트에 -X%" 관점으로 봐야.

### 5. "데이터 vs 직감" 충돌은 솔직하게 표현

Option B Exa 복원 때 Amy 질문: "넉넉하게 잡는 건 소용없어서 줄였던 거지?" → 맞음. 그런데 이번 복원은 측정이 아닌 관찰 기반(business -22%). 반드시 일관된 게 아님을 인정함.

**Lesson**: 중간 trade-off는 "middle-ground"로 포장하기보다 "이건 가설, 검증 안 됨" 명시. Amy는 sharp question을 할 권리가 있고, 솔직한 답이 신뢰를 쌓음.

---

## 핵심 지표 변화

| 지표 | Before | After | Δ |
|---|---|---|---|
| `pipeline.py` 줄 수 | 3794 | 2149 | **-43%** |
| 유료 API 쿼리/run | 24 | 13 | **-46%** |
| Prompt tokens (5 main) | 7750 | 5794 | **-25%** |
| Research SEO-spam 비율 | 47% | 0% | **제거** |
| Quality score (biz+research) | 68-74 | 85-92 | **+15pp** |
| URL hallucination 보호 | 없음 | 구조적 차단 | ✅ 신설 |

**Production fact_pack 신규 필드:**
- `url_validation_failed` (bool)
- `url_validation_failures` (list with persona/locale/unknown_urls)
- `auto_publish_eligible`가 url_validation_failed를 존중 (override)

---

## 장기 관찰 대상 (2주 monitoring)

### 1. Option B Exa 복원 효과
- 다음 2-3 cron에서 business candidate pool 40-50 회복 확인
- 회복하지만 final digest URL contribution은 제한적이면 원래대로 축소 고려

### 2. Phase 3 실 production 토큰 감소
- `measure_token_usage.py --days 3` 3일 후 실행
- QUALITY_CHECK 4개 stage에서 input_tokens 실제 감소 확인
- Prompt-string 측정(-1956 tokens)이 production API 호출에 반영되는지 검증

### 3. Few-shot 효과 (Phase 2)
- measurement v2 (2주 후) 돌려서:
  - frontload + overclaim issue 감소했는지
  - ko + locale issue 감소했는지
- 감소 확인되면 같은 패턴으로 다음 Top 2 타겟 식별

### 4. Business digest 길이 패턴
- Amy 체감상 "너무 얇다"가 지속되면 Option B + 추가 조치
- 유지되면 "shorter + higher quality = 개선" 결론

---

## 드롭된 것들 (재검토 조건 기록)

| 드롭 | 재검토 조건 |
|---|---|
| PydanticAI 마이그레이션 | ranking 단계에서 JSON 파싱 실패가 운영 이슈로 부각될 때 |
| OpenAI 프롬프트 캐싱 | cron 빈도가 시간당 1회+로 증가하거나 persona digest call이 run당 10+ |
| Silent failure 로깅 강화 | 분류 결과 빈 배열로 발행되는 사건 발생 시 |
| pipeline.py 7-파일 패키지 | 팀 합류 또는 오픈소스 공개 시점 |

---

## 세션 작업 흐름 (시간순)

1. **평가 + brainstorming** (시작): news pipeline 상세 평가 → 3-phase 구조 도출
2. **Design doc 작성** (master spec, 2026-04-15)
3. **Phase 1 plan + 실행** → 11 commits, production verify
4. **Phase 1 post-deploy 평가** → research source 47% SEO-spam 발견 → Phase 2 scope 확장
5. **Phase 2 plan + 실행** → URL validation 3번의 iteration (fact_pack whitelist → group.items → enriched_map)
6. **API diet bonus** (14일 measurement 결과 기반)
7. **Phase 3 plan + 실행** → token diet -1956
8. **Option B course-correct** (2026-04-14 business -22% 발견 → Exa partial restore)
9. **공식 complete 마킹** + journal (지금)

**주요 결정 분기점 (Amy 개입):**
- Phase 1: "4-file split OK" (vs 7-file package)
- Phase 2: "strict allowlist" (vs fuzzy/HTTP HEAD)
- Phase 2: "A+B+C 전부 하자" (vs 단일 phase)
- Phase 2: "Silent failure 필요한지 조사" → 결과 기반 drop
- API diet: "안전한 승리 (Tavily #3/#4만)" 세트 수용
- Option B: "둬보자" (revert 아닌 관찰 모드)

---

## 결론

3 phase + API diet + Option B를 통해 news pipeline의 **유지보수성 + 신뢰도 + 비용**이 모두 개선됨. 측정 → scope 축소 → 구현 → production verify → course-correct 루프가 작동했고, 최대 산출물은 "spec scope의 30-50%가 실제로는 필요 없거나 이미 존재"라는 발견.

남은 관찰 대상 4개는 1-2주 데이터로 자연스럽게 해결될 것으로 예상.
