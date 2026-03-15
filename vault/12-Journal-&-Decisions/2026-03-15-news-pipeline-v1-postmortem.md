---
title: "Post-mortem: News Pipeline v1 실패 → 전체 삭제 → v2 재설계"
tags:
  - postmortem
  - pipeline
  - decision
date: 2026-03-15
---

# Post-mortem: News Pipeline v1

> 2026-03-10 ~ 03-15. 5일간 개발한 AI News Pipeline v1이 콘텐츠 길이 검증 반복 실패로 전체 삭제됨.
> 백엔드 15파일(~3,444줄) + 테스트 16파일(~3,094줄) = 총 32파일, ~6,539줄 삭제.
> DB 데이터(news_posts, pipeline_runs/logs, news_candidates, engagement)도 Supabase에서 수동 삭제.

---

## v1 아키텍처 (삭제된 코드)

### 파일 구조 (백엔드 ~3,444줄 + 테스트 ~3,094줄)

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `services/pipeline.py` | 1,258 | 순차 오케스트레이터 + resume + artifact |
| `services/agents/prompts.py` | 375 | 5개 시스템 프롬프트 (15,622자) |
| `services/agents/business.py` | 309 | Expert-First 2-Call Cascade |
| `services/agents/translate.py` | 373 | Research/Business 번역 |
| `services/agents/research.py` | 193 | Research 포스트 생성 |
| `services/agents/ranking.py` | 60 | 뉴스 후보 LLM 랭킹 |
| `services/news_collection.py` | 196 | Tavily API 뉴스 수집 |
| `services/quality.py` | 41 | 콘텐츠 품질 검사 |
| `routers/admin.py` | 367 | Admin CRUD 엔드포인트 |
| `routers/cron.py` | 122 | Cron 파이프라인 트리거 |
| `models/` (business, ranking, research) | 145 | Pydantic 모델 |
| `services/agents/__init__.py` | 5 | 에이전트 re-export |
| + **테스트 16파일** | ~3,094 | 총 삭제 **~6,539줄** |

### 파이프라인 워크플로우 (v1)

```
1. collect_all_news()          — Tavily API로 AI 뉴스 수집
       ↓
2. rank_candidates()           — gpt-4o-mini로 후보 랭킹 → research 1건 + business 1건 선정
       ↓
3. generate_research_post()    — gpt-4o, max_tokens=16384
   EN research 포스트 생성 (마크다운 본문 + 메타데이터)
       ↓
4. translate_post(research)    — gpt-4o, max_tokens=16384
   Research EN → KO 전문 번역
       ↓
5. generate_business_post()    — gpt-4o, max_tokens=16384 × 2회
   Call 1: generate_business_expert() → fact_pack + source_cards + analysis + expert 본문
   Call 2: derive_business_personas() → expert 기반으로 learner + beginner 파생
       ↓
6. translate_post(business)    — gpt-4o, max_tokens=16384
   Business EN → KO 전문 번역 (3 페르소나 전체)
       ↓
7. Terms 추출 + 저장
```

### 콘텐츠 길이 제약 (v1)

| 필드 | EN 최소 | KO 최소 | 목표 |
|------|---------|---------|------|
| 페르소나 본문 (content) | 5,000자 | 4,000자 | 6,500자 |
| 분석 (analysis) | 2,500자 | 1,400자 | — |

Pydantic 모델에서 hard validation — 미달 시 `ValidationError` 발생 → 재시도 또는 파이프라인 실패.

### 사용 모델

| 에이전트 | 모델 | max_tokens |
|----------|------|------------|
| Ranking | gpt-4o-mini | 기본값 |
| Research 생성 | gpt-4o | 16,384 |
| Business Expert (Call 1) | gpt-4o | 16,384 |
| Business Derive (Call 2) | gpt-4o | 16,384 |
| Translate Research | gpt-4o | 16,384 |
| Translate Business | gpt-4o | 16,384 |

---

## 비용 추정 (v1 1회 실행)

> gpt-4o 가격: input $2.50/1M, output $10.00/1M (2026-03 기준)
> gpt-4o-mini 가격: input $0.15/1M, output $0.60/1M

### 토큰 추정

시스템 프롬프트 총 ~15,600자 ≈ **~4,000 토큰** (한국어/영어 혼합, 1자 ≈ 0.25~0.5 토큰)

| 호출 | Input 추정 | Output 추정 | 모델 |
|------|-----------|------------|------|
| Ranking | ~2,000 | ~500 | gpt-4o-mini |
| Research EN 생성 | ~3,000 (프롬프트 + 뉴스 컨텍스트) | ~4,000 (5,000자 본문) | gpt-4o |
| Research EN→KO 번역 | ~5,000 (프롬프트 + EN 본문) | ~4,000 (KO 본문) | gpt-4o |
| Business Expert (Call 1) | ~3,500 (프롬프트 + 뉴스 컨텍스트) | ~6,000 (fact_pack + expert 본문) | gpt-4o |
| Business Derive (Call 2) | ~7,000 (프롬프트 + expert 전체) | ~8,000 (learner + beginner 본문) | gpt-4o |
| Business EN→KO 번역 | ~15,000 (프롬프트 + 3 페르소나 EN) | ~12,000 (3 페르소나 KO) | gpt-4o |
| **합계** | **~35,500** | **~34,500** | |

### 비용 계산 (1회 실행, 성공 시)

| 항목 | 토큰 | 단가 | 비용 |
|------|------|------|------|
| gpt-4o input | ~33,500 | $2.50/1M | $0.084 |
| gpt-4o output | ~34,000 | $10.00/1M | $0.340 |
| gpt-4o-mini input | ~2,000 | $0.15/1M | $0.0003 |
| gpt-4o-mini output | ~500 | $0.60/1M | $0.0003 |
| **1회 성공 합계** | **~70,000** | | **≈ $0.42** |

### 실패 시 비용 (실제 발생)

v1은 콘텐츠 길이 미달로 **재시도가 빈번**했다:
- 2회 재시도 내장 → 최악의 경우 **3× 비용 = ~$1.26/실행**
- 재시도 후에도 실패 → 토큰 소비만 하고 결과물 없음
- 개발/디버깅 중 수십 회 실행 → 추정 **$15~25 소비** (5일간)

### v2와 비교

| 항목 | v1 | v2 (설계) |
|------|-----|-----------|
| LLM 호출 수 | 6회 (ranking + 2 생성 + 2 번역 + 1 파생) | 4~5회 (수집 → 랭킹 → 팩트추출 → 페르소나 × 카테고리) |
| 번역 방식 | 생성 후 별도 번역 (2회 추가) | 생성 시 EN+KO 동시 생성 |
| 실패 시 | 전체 재시도 또는 파이프라인 중단 | 단계별 저장, draft로 저장 후 진행 |
| 코드량 | ~3,444줄 (백엔드) | ~1,300줄 목표 |

---

## 실패 타임라인

### 3/10~13: 초기 구현

- 3/10: 뉴스 수집 + 랭킹 + Research 생성 구현
- 3/13: `201272d` — partial resume + artifact 시스템 추가
  - pipeline.py가 979줄 → 1,346줄로 급팽창
  - "실패한 지점부터 재개"를 위해 중간 결과를 DB에 저장하는 artifact 시스템 도입
  - 복잡도가 급증했지만 근본 문제(길이 미달)를 해결하지 못함

### 3/13: 첫 번째 타협

- `442235a` — **KO 번역 임계값 완화**
  - 증상: KO 번역 결과가 KO_MIN_CONTENT_CHARS(4,000자) 미달
  - 대응: 임계값 하향
  - 근본 원인 미해결: LLM이 프롬프트 지시를 따르지 않는 구조적 문제

### 3/14: 대규모 리팩터링 시도

- `08ab757` — "comprehensive pipeline resume and artifact translation"
  - 대규모 리팩터링 후: business.py 242줄, translate.py 246줄, pipeline.py 1,214줄
  - 번역 실패 시 부분 복구 로직, artifact 저장/복원 추가
  - 더 복잡해졌지만 여전히 길이 미달 발생

- `104fa5b` — **fact_pack 검증 강화**
  - 증상: AI가 fact_pack을 list로 줄 때도 있고 dict로 줄 때도 있음
  - 대응: before-validator로 list→dict 강제 변환
  - 교훈: AI 출력 포맷의 비결정성을 코드로 방어하는 데 한계

### 3/15: 두 번째, 세 번째 타협 → 포기

- `644b722` — **번역 soft-floor 70%** 도입
  - 재시도 전부 실패해도 목표의 70% 이상이면 수용
  - Pydantic hard floor을 2,100자로 하향
  - 파이프라인 삭제 API(`DELETE /admin/pipeline/{batch_id}`) 추가 — 이미 실패 데이터 정리가 일상화

- `f208f89` — **EN 생성도 soft-floor 50%로** 하향
  - 목표 5,000자 → 2,500자까지 허용
  - 2-tier 경고 시스템: 50~70% = very_short, 70~100% = short
  - **사실상 품질 기준 포기** — 목표의 절반만 채워도 통과

- `241f08f` — **전체 삭제 결정**
  - 백엔드 15파일 + 테스트 16파일 = 32파일, ~6,539줄 삭제
  - DB 데이터 (news_posts, pipeline_runs/logs, news_candidates, engagement) Supabase에서 수동 삭제
  - 프론트엔드 뉴스 UI shell + newsprint 스타일은 보존 (재사용)

---

## 근본 원인 분석

### 1. "생성 후 번역" 아키텍처의 비효율

- EN 생성 → KO 번역 구조에서 번역 단계가 원문 길이를 유지하지 못함
- 한국어는 같은 내용을 더 짧은 글자 수로 표현 → 글자 수 기반 검증이 구조적으로 불리
- 번역 품질을 높이려면 번역 프롬프트가 점점 복잡해지는 악순환

### 2. 과도한 콘텐츠 길이 요구

- 페르소나당 5,000자 이상 × 3 페르소나 = 15,000자+
- LLM(gpt-4o)이 한 번의 호출로 이 분량을 안정적으로 생성하기 어려움
- max_tokens=16,384로 설정했지만, 실제 output은 4,000~8,000 토큰 수준에서 멈추는 경우 빈번

### 3. 복잡도 도피 (Complexity Escape)

- 길이 미달 → 재시도 로직 추가 → 여전히 미달 → artifact/resume 시스템 추가 → 코드 팽창
- 근본 문제(프롬프트 설계, 아키텍처)를 고치지 않고 **방어 코드를 계속 추가**
- pipeline.py가 979 → 1,346 → 1,258줄로 팽창 — 오케스트레이터가 에러 처리 코드로 가득 차서 핵심 흐름 파악 불가

### 4. 임계값 하향의 미끄러운 경사

```
5,000자 (원래 목표)
  → 4,000자 (KO 완화)
    → 2,100자 (hard floor 하향)
      → 70% soft-floor
        → 50% soft-floor (사실상 2,500자)
```

5일 만에 품질 기준이 원래의 50%로 하락. "일단 돌아가게" 하려는 패치가 누적되면서 제품 가치 자체가 훼손.

---

## v2에서 바꾼 것

| v1 문제 | v2 해결 |
|---------|---------|
| 생성 후 번역 (2단계) | 생성 시 EN+KO 동시 출력 (번역 단계 제거) |
| 페르소나 1회 호출로 전체 생성 | 팩트 추출(Call 1) → 페르소나별 생성(Call 2~4) 분리 |
| 글자 수 hard validation | draft 저장 후 admin에서 확인 (파이프라인은 안 죽음) |
| artifact/resume 복잡도 | 단계별 저장, 실패 시 해당 단계만 재시도 |
| pipeline.py 1,258줄 | ~600줄 목표 |

---

## 교훈

1. **임계값을 낮추기 시작하면 멈춰라.** 그건 "아키텍처가 틀렸다"는 신호다.
2. **방어 코드로 근본 문제를 덮지 마라.** resume/artifact/soft-floor는 전부 근본 원인 회피.
3. **LLM 출력 길이는 보장되지 않는다.** 긴 콘텐츠는 1회 호출이 아니라 분할 생성으로 설계해야 한다.
4. **코드가 급팽창하면 설계를 의심해라.** pipeline.py 979→1,346줄은 "뭔가 잘못되고 있다"는 명확한 신호였다.
5. **빠른 포기가 비용을 줄인다.** 3일째에 삭제했으면 2일 + $10~15를 아꼈을 것.

---

## Related

- [[ACTIVE_SPRINT]] — v2 스프린트 (현재 진행 중)
- [[Phase-Flow]] — v2는 "News Pipeline v2" 섹션
- [[AI-News-Pipeline-Design]] — v2 설계 문서
