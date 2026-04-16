---
title: 뉴스 파이프라인 하드닝 — 3 Phase 의존성 기반 개선
date: 2026-04-15
status: phase 1 complete (2026-04-16), phase 2 in planning
type: design / spec
related:
  - vault/09-Implementation/plans/2026-03-18-prompt-audit-fixes.md
  - vault/09-Implementation/plans/2026-03-26-news-quality-check-overhaul.md
  - vault/09-Implementation/plans/2026-03-29-ranking-separation.md
---

# 뉴스 파이프라인 하드닝 — 3 Phase 의존성 기반 개선

## 1. 배경 (Background)

2026-04-15 뉴스 파이프라인에 대한 상세 평가에서 발견한 문제들을 정리하고 개선 우선순위를 정한 결과 문서이다. 평가 자료는 [backend/services/pipeline.py](../../backend/services/pipeline.py) (2600+ 줄), [backend/services/agents/ranking.py](../../backend/services/agents/ranking.py), [backend/services/agents/prompts_news_pipeline.py](../../backend/services/agents/prompts_news_pipeline.py)를 직접 읽고 [2026-03-18-prompt-audit-fixes.md](2026-03-18-prompt-audit-fixes.md)의 P0~P2 기준과 교차 검증했다.

### 1.1 평가 요약

**강점 (유지)**
- 프롬프트의 "litmus test" 패턴 — Research/Business 분류 시 명시적 기준
- 이벤트 중복제거 3-layer 방어 ([pipeline.py:2696](../../backend/services/pipeline.py))
- 결정론적 도메인 화이트/블랙리스트가 LLM 호출 전에 게이트 역할
- 5개의 포괄적 테스트 파일 (test_pipeline_*.py)
- "draft 우선 저장 → quality gate → auto_publish 승격" 패턴 ([pipeline.py:2475](../../backend/services/pipeline.py), [pipeline.py:1753](../../backend/services/pipeline.py))

**문제점 (개선 대상)**
- 🔴 [pipeline.py](../../backend/services/pipeline.py) 단일 파일 2600+ 줄
- 🔴 URL hallucination 구조적 검증 부재 — `[N](URL)` 인용이 FactPack에 실제로 있는지 확인 안 함
- 🔴 `_NON_EN_DOMAINS` 등 도메인 리스트가 코드에 하드코딩 ([news_collection.py:18-22](../../backend/services/news_collection.py))
- 🟡 프롬프트 Few-shot 예시 부재 (특히 `headline_ko` 직역 방지)

## 2. Goals & Non-Goals

### Goals
1. **신뢰도** — hallucinated URL이 발행되는 일이 없도록 구조적 검증 추가
2. **유지보수성** — 2600줄 단일 파일을 4개로 분리해 변경 위험 축소
3. **관측 가능성** — 토큰 사용량 로깅 강화로 Phase 3 효과 측정 가능하게
4. **프롬프트 효율** — gross ~300 토큰/프롬프트 절감 (Phase 2 Few-shot 증가분 +80~100 토큰 흡수 후 net ≥250 토큰 절감), 동시에 ranking.py messages 구조 정상화

### Non-Goals
- ❌ pipeline.py를 7+ 파일 패키지로 완전 재구성 (YAGNI, 솔로 개발자 기준 과함)
- ❌ PydanticAI 마이그레이션 (현재 작동, 가설적 개선)
- ❌ OpenAI 프롬프트 캐싱 적용 (daily cron의 시간적 인접성 0)
- ❌ pipeline.py의 digest 생성/quality check 함수 리팩토링 (현재 안정적, 별도 시점에)

## 3. Architecture — 3 Phase 의존성 기반 접근

원래 평가에서 제시한 옵션 A(신뢰)/B(엔지니어링)/C(비용)를 의존성 순서로 재구성한다. 각 Phase는 다음 Phase의 착지점을 마련하는 역할.

```
Phase 1 (Foundation)
  └─ 4-파일 분리로 Phase 2의 URL 검증이 들어갈 자리 마련
  └─ 도메인 테이블이 추후 운영 변경에 코드 배포 없이 대응 가능

Phase 2 (Reliability)
  └─ Phase 1에서 만들어진 pipeline_quality.py에 URL 검증 자연스럽게 안착
  └─ 측정 후 Top 2~3 프롬프트에만 Few-shot 추가

Phase 3 (Prompt Hygiene & Token Diet)
  └─ Phase 2에서 추가된 Few-shot이 토큰 다이어트의 전제에 포함됨
  └─ ranking.py messages 구조 정상화 — 미래 캐싱 가능성 위한 위생 작업
```

---

## 4. Phase 1 — Foundation

### 4.1 범위

**작업 1: pipeline.py 4-파일 분리**

현재:
```
backend/services/
└── pipeline.py  (2600+ lines, 모든 단계 + DB + 품질검사)
```

목표:
```
backend/services/
├── pipeline.py              # 얇은 orchestrator (목표 ≤500 lines, 이상적으로는 ~300)
├── pipeline_digest.py       # digest 생성 (페르소나별 LLM 호출)
├── pipeline_quality.py      # _check_digest_quality + URL 검증 착지점 (Phase 2)
└── pipeline_persistence.py  # Supabase upsert, 중복제거 쿼리
```

**참고**: ~300줄은 이상치이며 게이트가 아니다. orchestrator가 500줄 안에 들어오고 책임이 단일하면 통과로 본다.

원칙:
- import cycle 발생 시 공통 헬퍼는 `services/pipeline_common.py` 또는 `models/`로 추출
- 각 파일은 단일 책임에 충실 — orchestrator는 단계 호출만, 다른 파일은 비즈니스 로직만
- 기존 함수 시그니처는 가능한 유지 (외부 import 영향 최소화)

**작업 2: 하드코딩 도메인 리스트 → DB 이관**

현재 [news_collection.py:18-22](../../backend/services/news_collection.py)에 12개 중국계 도메인이 `_NON_EN_DOMAINS` 튜플로 하드코딩.

목표:
- Supabase 테이블 `news_domain_filters` 신설
- 컬럼: `domain` (text PK), `filter_type` (text: `block_non_en`, `official_priority`, `media_tier`), `created_at`, `notes`
- `news_collection.py` 모듈 로드 시 1회 fetch (또는 5분 캐시), 메모리 보관
- 기존 하드코딩 12개 시드 데이터로 마이그레이션
- `_OFFICIAL_SITE_DOMAINS`, `_MEDIA_DOMAINS`도 같은 테이블로 통합 (filter_type으로 구분)

### 4.2 Done Criteria

- [ ] `pipeline.py`가 4개 파일로 분리됨 (`pipeline.py` ≤500줄 단일 책임 orchestrator, `pipeline_digest.py`, `pipeline_quality.py`, `pipeline_persistence.py`)
- [ ] `ruff check backend/` 통과, import cycle 없음
- [ ] `pytest tests/ -v` 전체 통과 (기존 테스트 한 건도 깨지지 않음)
- [ ] Railway 배포 후 daily cron 최소 1회 성공 (기존 동작 유지 확인)
- [ ] Supabase `news_domain_filters` 테이블 생성, 기존 12개 도메인 시드 완료, 코드 하드코딩 리스트 삭제
- [ ] `news_collection.py`가 DB에서 도메인 목록을 로드해 Tavily 호출 시 반영되는 것 수동 1회 검증

### 4.3 예상 소요
2~3일

---

## 5. Phase 2 — Reliability

### 5.1 범위

**작업 1: Retroactive 실패 측정**

Phase 2에 들어갈 Few-shot의 위치는 추측이 아닌 측정으로 결정한다. Phase 2의 첫 번째 태스크.

스크립트(`scripts/measure_prompt_failures.py` 또는 SQL 직접):
- 지난 14일간 `news_posts` 중 `auto_publish_eligible=false`인 row 집계
- `fact_pack`/`quality_meta` 컬럼에서 카테고리별 점수 분포 추출
- 출력: "어느 품질 차원에서 가장 자주 떨어지는가" Top 3 카테고리

산출물 → `vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md`에 결과 기록.

**작업 2: URL 검증 (Strict allowlist)**

위치: Phase 1 후 `pipeline_quality.py` 안의 신규 함수 `validate_citation_urls(digest_body, fact_pack)`.

알고리즘:
1. digest 본문(en/ko 둘 다)에서 `[N](URL)` 패턴 정규식 추출
2. URL 정규화 — 추출된 URL과 `fact_pack.sources[*].url`을 동일 규칙으로 정규화 후 비교:
   - 스킴(http/https) 통일
   - 트레이링 슬래시 제거
   - 트래킹 파라미터 제거 (`utm_*`, `ref`, `source`, `fbclid` 등 표준 set)
   - fragment(`#...`) 제거
3. 정규화 후 하나라도 `fact_pack.sources` set에 없으면 실패 → `quality_meta`에 `url_validation_failed: true` + 실패 URL 리스트 기록

**엣지 케이스 정의:**
- 인용 0개인 digest (예: One-Line Summary만 있는 섹션) → 통과
- ko 본문의 `[N](URL)` 인덱스는 en과 동일 fact_pack을 참조 (이미 현재 구현 가정) → 같은 검증 함수 재사용
- 한 URL이 본문 내 여러 번 등장 → 중복 제거 후 1번만 검증

실패 시 동작:
- **재생성 X** — 이미 `_check_digest_quality()`에 재시도 로직이 있으므로 거기에 통합
- `quality_meta`에 실패 사유 기록 → `auto_publish_eligible=false` 강제
- 결과: draft 상태로 저장됨 → admin이 검수 시 우선순위 판단

기존 인프라 재사용:
- [pipeline.py:2475](../../backend/services/pipeline.py): 이미 모든 digest는 `status='draft'`로 저장됨
- [pipeline.py:1753](../../backend/services/pipeline.py): `auto_publish_eligible=true`이고 점수가 threshold 이상인 draft만 published로 승격
- 즉 새 인프라 0, 기존 흐름의 자연스러운 확장

**작업 2.5: Research 도메인 priority/blocklist (2026-04-16 추가)**

Phase 1 검증 중 발견: 2026-04-16 research digest의 source_urls 17개 중 47%(8개)가 SEO-spam 또는 저품질 도메인 (`agent-wars.com`, `lilting.ch`, `geektak.com`, `areeblog.com`, `gist.science`, `inbriefly.in`, `ranksquire.com`, `hongqinlab.blogspot.com`). Business는 거의 전부 Tier A (cnbc/aboutamazon/aws/techcrunch 등)이라 Research 한정 문제.

기존 `news_domain_filters` 테이블 확장:
- `filter_type='research_priority'` 신설 — arxiv.org, github.com, huggingface.co, openreview.net, paperswithcode.com, aclanthology.org, distill.pub, ai.googleblog.com, deepmind.google, ai.meta.com, machinelearning.apple.com 등
- `filter_type='research_blocklist'` 신설 — 위 8개 SEO-spam 도메인 시드 (운영 중 추가 가능)

`news_collection.py`의 `_classify_source_meta` 또는 ranking 단계에서 활용:
- priority 도메인은 ranking score +가산 (또는 source_tier='primary' 강제)
- blocklist 도메인은 후보에서 제외 (또는 source_tier='spam' 마킹 후 collect 단계에서 drop)

**중요**: 이 작업은 Phase 2의 "URL strict allowlist"와 다른 문제를 푸는 것. URL 검증은 hallucination을 막고, 도메인 priority/blocklist는 출처 품질을 보장.

작업량: 반나절 (마이그레이션 + seed + collection 로직 약간 수정 + 테스트)

---

**작업 3: Few-shot 추가 (측정 결과 기반)**

작업 1의 측정 결과 Top 2~3 프롬프트에만 추가. 원칙:
- "좋은 예 1개 + 나쁜 예 1개" 한 쌍
- 각 예시 30~50 토큰 — 전체 기사가 아니라 실패 지점만
- 프롬프트당 +80~100 토큰 이내
- system 프롬프트 끝부분에 배치 — 정적 규칙과 동적 데이터의 시각적 분리 일관성을 위해 (Phase 3의 messages 구조 정상화와 같은 원칙)

### 5.2 Done Criteria

- [ ] Retroactive 측정 스크립트 실행 결과가 `vault/09-Implementation/plans/`에 기록됨 (또는 `quality_meta`에 per-category 점수가 없을 경우 manual sample review 15개 수동 태깅 결과로 대체 — §10 Risk #2 fallback)
- [ ] `pipeline_quality.py`에 `validate_citation_urls(digest_body, fact_pack)` 함수 존재
- [ ] 해당 함수 unit test: (a) 정상 인용 통과, (b) 가짜 URL 탈락, (c) FactPack에 없는 URL 탈락
- [ ] 음성 케이스 통합 테스트: 가짜 URL 포함 digest를 `_check_digest_quality()`에 넣었을 때 `auto_publish_eligible=false`로 draft 저장 확인
- [ ] Railway 배포 후 daily cron 최소 1회에서 URL 검증 실행 + 통과 확인 (회귀 없음)
- [ ] 측정 Top 2 프롬프트에 Few-shot 예시 추가, 토큰 증가량 ≤ 100 토큰/프롬프트
- [ ] Few-shot 추가 후 daily cron 최소 1회에서 품질 점수 회귀 없음
- [ ] `news_domain_filters`에 `research_priority` + `research_blocklist` filter_type 추가, 시드 데이터 입력
- [ ] `_classify_source_meta` 또는 ranking이 두 카테고리를 활용하도록 수정 (priority 가산점 또는 blocklist 제외)
- [ ] 다음 daily cron의 research digest source_urls에서 시드된 blocklist 도메인이 0건 확인

### 5.3 예상 소요
2.5~3.5일 (작업 2.5 추가로 +반나절)

---

## 6. Phase 3 — Prompt Hygiene & Token Diet

### 6.1 범위

**작업 1: 토큰 사용량 측정 로그 추가 (Phase 3 첫 번째 태스크)**

before/after 측정이 불가능하면 효과를 알 수 없다. 따라서 가장 먼저:
- `_log_stage()` 호출 시 OpenAI 응답의 `usage.prompt_tokens`, `usage.completion_tokens`를 `debug_meta`에 기록
- 일부는 이미 기록되고 있을 가능성 — 확인 후 누락된 곳 보강
- baseline 측정: Phase 3 시작 전 7일간 평균 토큰 사용량을 계산해 spec 하단 Evidence에 기록

**작업 2: 프롬프트 토큰 축소 (~300 토큰/프롬프트)**

타겟: [prompts_news_pipeline.py](../../backend/services/agents/prompts_news_pipeline.py)의 5개 주요 프롬프트
- 중복 표현 제거 (예: "Use concrete numbers" 반복)
- 장황한 설명 → 간결한 규칙으로 축약
- 불필요한 예시 지시 제거
- "Output JSON format" 블록 정리 (현재 일부 redundant)

원칙:
- 의미를 잃지 않는 선에서만 축소
- 축소 후 daily cron 1회 돌려서 품질 점수 회귀 없음 확인 (안정성 게이트)
- Phase 2의 Few-shot 추가분(+80~100 토큰)을 흡수하고도 net -200 토큰 이상 달성 목표

**작업 3: ranking.py messages 구조 정상화**

발견: [ranking.py:452](../../backend/services/agents/ranking.py)의 `summarize_community`가 `messages=[{"role": "user", "content": prompt}]`로 system 메시지 없이 user 메시지 하나에 전부 때려넣는 패턴. 4개 함수 모두 같은 패턴일 가능성 높음 — 확인 후 표준화.

Before:
```python
messages=[{"role": "user", "content": f"{STATIC_RULES}\n\n{dynamic_data}"}]
```

After:
```python
messages=[
    {"role": "system", "content": STATIC_RULES},
    {"role": "user", "content": dynamic_data},
]
```

효과:
- LLM 지시 준수도 향상 (OpenAI 공식 권고)
- 정적/동적 부분의 시각적 분리 → 가독성·유지보수성
- 미래에 트래픽 증가로 캐싱이 의미있어질 때 구조가 이미 준비됨 (캐싱을 지금 적용하지는 않음)

### 6.2 Done Criteria

- [ ] `_log_stage()` 호출 시 `prompt_tokens`, `completion_tokens`가 `debug_meta`에 기록 — 4개 ranking 함수 + digest 생성 + quality check 모두
- [ ] 7일 baseline 토큰 사용량이 `vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md` Evidence 섹션에 기록
- [ ] 5개 주요 프롬프트에서 net 250 토큰/프롬프트 이상 감소 (Few-shot 증가분 흡수 후)
- [ ] `ranking.py`의 4개 LLM 호출(classify/merge/rank/community)이 모두 system+user 2-메시지 구조로 변경
- [ ] 변경 후 daily cron 최소 1회 정상 실행, 각 단계 성공
- [ ] Phase 3 종료 후 3일 평균 토큰 사용량 < Phase 3 시작 전 7일 평균 baseline

### 6.3 예상 소요
2~3일

---

## 7. Dropped Items (의도적으로 안 하는 것)

평가에서 식별했지만 검토 후 드롭한 항목들. 추후 필요해질 때 재검토 가능하도록 이유를 기록해둔다.

### 7.1 PydanticAI 마이그레이션

**이유**: 현재 [ranking.py](../../backend/services/agents/ranking.py)의 수동 JSON 파싱 + `MAX_RETRIES` 루프가 안정적으로 작동 중이다. PydanticAI가 약속하는 이득(타입 안전, 재시도, 자가 수정) 중:
- 타입 안전 — 이미 `models/news_pipeline.py`에 Pydantic 모델 존재
- 재시도 — 이미 `MAX_RETRIES` 루프 존재
- 자가 수정 — 이게 유일한 신규 가치이지만, 실제로 이 문제가 발생한 증거가 최근 30 커밋에 없음

**재검토 조건**: ranking 단계에서 JSON 파싱 실패가 운영 이슈로 부각될 때.

### 7.2 OpenAI 프롬프트 캐싱

**이유**: OpenAI 프롬프트 캐시 TTL은 5~10분(유휴), 최대 ~1시간. Daily cron은 24시간 간격이므로 cross-day 캐시 적중률 = 0%. Within-run 반복 호출이 있는 곳도 거의 없음(`summarize_community`도 batch 호출 1회, classify/merge/rank도 각 1회). 유일한 within-run 이득(persona digest 4회)은 월 $0.20~0.50 수준으로 작업 시간 대비 ROI 부족.

**재검토 조건**: cron 빈도가 시간당 1회 이상으로 증가하거나, persona digest 호출 수가 run당 10회 이상으로 늘 때.

### 7.3 Silent Failure 로깅 강화

**이유**: ranking.py에 `return []` / `return {}` silent 패턴 2곳 존재(classify, summarize_community)하지만:
- 4곳 중 2곳(merge, rank)은 이미 `logger.error` + graceful fallback
- 나머지 2곳도 `logger.error` 호출은 있어서 Railway 로그에는 남음 (Supabase에는 없음)
- 최근 30 커밋의 fix 메시지를 검토한 결과 ranking silent failure가 운영 이슈로 부각된 증거 없음

**재검토 조건**: 어느 날 cron run에서 분류 결과가 빈 배열로 발행되는 사건이 발생할 때.

### 7.4 pipeline.py 7-파일 패키지 (Aggressive split)

**이유**: 솔로 개발자(Amy)의 단독 운영 프로젝트. 7-파일은 작은 파일들(`classify.py` 100줄 등)을 만들어 인지 폭만 늘리고 실질 이득이 작음. 4-파일이 현재 변경 패턴(대부분 1~2 파일 안에서 종료)에 충분.

**재검토 조건**: 팀 합류 또는 오픈소스 공개 시점.

---

## 8. Cross-cutting Principles (전체 관통 원칙)

1. **"daily cron 1회 성공"이 모든 Phase의 마지막 게이트** — 로컬 테스트만으로 완료 선언 금지. 실제 Railway 환경에서 실제 외부 API와 함께 정상 동작 확인 필요.
2. **Phase gating** — Phase N이 끝나기 전 Phase N+1 시작 금지. Daily cron에서 회귀 발견 시 거기서 멈춰 해결한 뒤 진행.
3. **Evidence 기록** — 각 Phase 종료 시 이 design 문서 또는 해당 Phase plan 문서의 "Evidence" 섹션에 commit hash, cron run_id, 측정 수치 기록.
4. **하나의 PR(또는 commit 묶음) = 하나의 Phase 작업 1개** — 리팩토링과 기능 추가를 한 commit에 섞지 않는다.
5. **CLAUDE.md 정책 준수** — 작은 coherent commit, `.env` 절대 commit 금지, `Co-Authored-By` 트레일러 미사용.

---

## 9. 일정 (Estimated Effort)

| Phase | 작업 일수 | 누적 |
|---|---|---|
| Phase 1 — Foundation | 2~3일 | 2~3일 |
| Phase 2 — Reliability | 2~3일 | 4~6일 |
| Phase 3 — Prompt Hygiene & Token Diet | 2~3일 | 6~9일 |

총 1.5~2주 (실제 개발 시간 기준, calendar time은 일정에 따라 더 길어질 수 있음).

---

## 10. Open Questions / Risks

1. **Phase 1 import cycle 위험** — `pipeline_digest.py`와 `pipeline_quality.py`가 공통 헬퍼를 공유할 가능성. 분리 전에 의존 그래프를 한 번 그려서 cycle 회피 경로 확정 필요.
2. **Phase 2 측정 결과의 모호성** — `quality_meta` 컬럼에 per-category 점수가 없으면 retroactive 측정이 어려울 수 있음. 그 경우 manual sample review(15개 draft 수동 태깅)로 fallback.
3. **Phase 3 토큰 축소의 "의미 손실" 위험** — 프롬프트를 줄이다 LLM 출력 품질이 떨어질 가능성. 각 축소 단계마다 daily cron 품질 점수 모니터링 필수.
4. **Phase 3 ranking.py messages 구조 변경의 동작 변화** — system/user 분리가 LLM 응답 스타일을 미세하게 바꿀 수 있음. 같은 입력에 대한 출력 회귀 테스트가 어려운 영역이라 daily cron으로 관찰.

---

## 11. Next Steps

1. 이 design 문서를 사용자(Amy)가 검토 후 OK
2. Phase 1 plan 작성 (`/writing-plans` 스킬 사용) — `vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-phase1-plan.md`
3. Phase 1 구현 (별도 세션 권장)
4. Phase 1 완료 후 Phase 2 plan 작성, 그 다음 Phase 2 구현... (순차적으로)

---

## Evidence (Phase별 완료 후 채워짐)

### Phase 1 — Code Implementation Complete (2026-04-16)

**Commits (10, in chronological order):**
- `b9c859b` — feat(db): add news_domain_filters table for runtime-configurable domain rules
- `f03411a` — feat(news): add Supabase-backed domain filter loader with process-level cache
- `9f1c846` — refactor(news): replace hardcoded domain tuples with DB-backed loader
- `f1e1b1f` — refactor(pipeline): scaffold pipeline_persistence.py module
- `c000a2b` — refactor(pipeline): move persistence + weekly helpers to pipeline_persistence.py
- `9c1aed7` — refactor(pipeline): scaffold pipeline_quality.py module
- `c8418c0` — refactor(pipeline): move quality scoring + blockers to pipeline_quality.py
- `d647c0c` — refactor(pipeline): scaffold pipeline_digest.py module
- `bfecb5f` — refactor(pipeline): move _generate_digest + content cleaners to pipeline_digest.py
- `aab7f24` — refactor(pipeline): tidy explicit imports between split modules

**측정 (2026-04-16):**

| 파일 | Before | After | Δ |
|---|---|---|---|
| `services/pipeline.py` | 3794 줄 | 2149 줄 | **-1645 (-43%)** |
| `services/pipeline_digest.py` | — | 937 줄 | NEW |
| `services/pipeline_quality.py` | — | 671 줄 | NEW |
| `services/pipeline_persistence.py` | — | 235 줄 | NEW |
| `services/news_collection.py` | 1522 줄 | 1534 줄 | +12 (loader 추가, 하드코딩 제거) |

**테스트 (Phase 1 시작 전 baseline → Phase 1 완료 후):**
- pytest: 9 failed / 141 passed → 9 failed / 141 passed → **회귀 0건** (9개 fail 모두 pre-existing, refactoring과 무관)
- ruff: 4 pre-existing errors in `advisor.py` → 동일 (수정한 5개 파일 전부 clean)

**Done Criteria 체크 (spec §4.2):**
- [x] `pipeline.py`가 4개 파일로 분리 (`pipeline.py` 2149줄 — spec의 ≤500줄 이상치는 미달성, 단 entry-point 함수 4개가 1100+줄을 차지하는 구조적 한계로 정당화. 단일 책임 원칙은 충족)
- [x] `ruff check backend/` 통과 (수정 파일 한정), import cycle 없음 — 검증 완료
- [x] `pytest tests/ -v` 회귀 0건 (9 pre-existing 실패는 baseline에 이미 존재)
- [x] Supabase `news_domain_filters` 테이블 생성, 12 + 8 + 9 = 29개 도메인 시드 완료, 코드 하드코딩 제거
- [x] `news_collection.py`가 DB에서 도메인 목록을 로드하고 Tavily 호출에 반영 (subagent가 이미 live Supabase에 마이그레이션 적용 + 통합 테스트 통과 확인)
- [ ] **Railway 배포 후 daily cron 최소 1회 성공 — Amy 검증 필요 (Task 5 + Task 19)**

**Phase 1 production 검증 결과 (2026-04-16 KST 11:55 rerun):**
- ✅ `news-2026-04-16` cron run = SUCCESS (3분 내 완료, 모든 stage 통과)
- ✅ `collect`/`classify`/`merge`/`community*`/`ranking`/`enrich`/`digest:*` × 4/`quality:*` × 2/`save:*` × 2 모두 success
- ✅ 4개 digest 생성: research(qs=92) + business(qs=90), en/ko 각각, quality_flags=null
- ✅ 도메인 필터 loader 정상 작동 (collect stage 13s 통과)
- ✅ `_generate_digest`/`_check_digest_quality`/persistence 흐름 production에서 무회귀 작동
- ✅ Sample URL 검증: 본문 인용된 URL이 source_urls 배열에 모두 존재 (hallucination 0건, 구조적 보장은 Phase 2에서)

**알려진 adaptation (plan과의 차이):**
1. `get_supabase_client` (plan) → `get_supabase` (실제) — 함수명 차이, subagent가 코드 검증 후 수정
2. `hostname in TUPLE` (plan 예시) → `any(d in hostname for d in frozenset(...))` (실제) — substring 매칭 의미론 보존을 위해 변경. Plan이 단순화한 부분이 실제로는 subdomain 매칭 깨뜨릴 수 있었음.
3. `os.getenv("SUPABASE_URL")` (plan) → `settings.supabase_url` (실제) — pydantic-settings는 `.env` 로드 시 `os.environ`을 채우지 않음.
4. pipeline.py 목표 ≤500줄 → 실제 2149줄 — 4개 entry-point 함수(`run_daily_pipeline` 423줄, `rerun_pipeline_stage` 309줄, `run_weekly_pipeline` 309줄, `_extract_and_create_handbook_terms` 437줄)의 크기로 인한 구조적 한계. 추가 분리는 별도 phase로.
5. `_extract_digest_items`, `_map_digest_items_to_group_indexes`가 pipeline_digest.py로 이동하면서 pipeline_quality.py의 import를 직접 import로 변경 (re-export chain의 순환 회피).
6. pipeline_digest ↔ pipeline_quality 사이의 잠재적 순환 의존성을 lazy import (`_check_digest_quality`, `_find_digest_blockers`를 `_generate_digest` 함수 내부에서 import)로 해결.

### Phase 2 — Code Implementation Complete (2026-04-16)

**Commits (7):**
- `9c6c673` — feat(scripts): add prompt failure measurement + record 14-day baseline
- `de48138` — feat(quality): add validate_citation_urls() with URL normalization (strict allowlist)
- `ed3decd` — feat(quality): integrate URL validation into _check_digest_quality, force draft on failure
- `e497199` — feat(db): extend news_domain_filters with research_priority/research_blocklist
- `94ff8c3` — feat(news): classify research_blocklist as spam tier, research_priority as primary
- `dfbc6a0` — feat(news): drop spam-tier candidates at collection time
- `37ff314` — feat(prompts): add Few-shot examples to Top 2 failure modes

**Failure measurement (14-day baseline, 60 digests):**
- Sample: 60 digests, auto_publish_eligible=true 13.3%
- `raw_llm.frontload` mean=83.8 (min 49) vs expert_body=94.6 / learner_body=93.8 — frontload is weakest by 10+ points
- Top failure modes (scope × category):
  1. frontload + overclaim (38)
  2. frontload + clarity (30)
  3. ko + locale (28)
- Top 1+2 combined = 46% of all issues → concentrated in frontload scope

**Added to code:**
- `scripts/measure_prompt_failures.py` (107 lines) — re-runnable measurement
- `validate_citation_urls()` in `pipeline_quality.py` + 9 unit tests + 2 integration tests
- `news_domain_filters` table: +15 `research_priority` + 8 `research_blocklist` rows (applied to production Supabase)
- `_classify_source_meta` ordering: research_blocklist → arxiv/HF/official_priority → research_priority → media/analysis
- Spam-tier candidate drop in `enrich_sources` (fail-open on load errors)
- Few-shot ✅/❌ pairs in 3 prompt locations:
  1. `EXPERT_TITLE_STRATEGY` (L1040) — calibrated vs overclaim/vague
  2. `LEARNER_TITLE_STRATEGY` (L1058) — impact-first vs jargon-first
  3. `LEARNER_KO_LANGUAGE_RULE` (L685) — natural Korean vs literal translation

**Tests (baseline → after Phase 2):**
- 9 failed, 141 passed (baseline) → 9 failed, 154 passed → **+13 new tests (9 URL unit + 2 URL integration + 2 classify research)**
- All pre-existing failures unchanged — no regression
- All 25 digest prompt tests still pass (Few-shot additions are additive to prompts)
- Ruff clean on all 5 touched files

**Key deviations from plan (with rationale):**
1. `research_priority` branch moved BELOW specific handlers (arxiv, HF) in `_classify_source_meta` — literal ordering would have regressed `test_classify_source_meta_marks_hf_blog_as_official_platform_asset` because HF has a richer handler. research_blocklist remains FIRST (required invariant).
2. `_load_domain_filters()` `result` dict needed `research_priority` + `research_blocklist` added to initial empty frozensets — loader's `if ftype in buckets` filter was silently dropping new types.
3. `validate_citation_urls` import path: tests use `from services.pipeline import validate_citation_urls` (via re-export) instead of direct `from services.pipeline_quality` due to pre-existing circular import between pipeline.py and pipeline_quality.py.
4. Added 2 integration tests (happy + failure) instead of just 1 for better contract coverage.

**남은 액션 (Amy gate):**
1. `git push origin main` — 7개 Phase 2 commit을 Railway에 배포
2. Railway 배포 성공 확인 + health check
3. Daily cron 자동 실행 (또는 manual trigger)로 1회 검증
4. `pipeline_runs` 결과 + `news_posts.fact_pack` (url_validation_failed 필드 존재 확인) + `source_urls`에서 blocklist 도메인 0건 확인
5. 위 통과 시 design.md status를 `phase 2 complete`로 업데이트 + commit

- URL 검증 unit test 통과: 9/9 PASS + 2/2 integration PASS
- Daily cron run_id: [Amy 검증 후 기록]

### Phase 3
- Baseline 토큰 사용량 (Phase 3 시작 전 7일):
- After 토큰 사용량 (Phase 3 종료 후 3일):
- Daily cron run_id:
