---
title: Cost Model & Stage A/B
tags:
  - operations
  - cost
  - infrastructure
source: [docs/03_Backend_AI_Spec.md, docs/05_Infrastructure.md]
---

# Cost Model & Stage A/B

API 비용 + Railway 인프라 비용 분리 추적. KPI 기반 단계적 운영 확장.

## API 비용 (OpenAI + Tavily)

### 모델별 사용 전략

| 작업 | 모델 | 이유 |
|---|---|---|
| 뉴스 분류 + 랭킹 | gpt-4o-mini | 단순 분류, 비용 최소화 |
| Research/Business 초안 | gpt-4o | 기술 정확도/품질 필요 |
| Editorial 검수 | gpt-4o | 정확한 평가 필요 |
| 슬러그/태그 생성 | gpt-4o-mini | 단순 변환 |
| 시맨틱 검색 임베딩 (Phase 3) | text-embedding-3-small | pgvector 호환, 비용 효율 |

> [!note] 모델 교체 유연성
> `OPENAI_MODEL_MAIN`/`OPENAI_MODEL_LIGHT` 환경 변수로 코드 수정 없이 교체 가능.

### 일일 예상 비용 (v4)

> [!note] v4 변경
> Expert-First 2-Call Cascade + 전문 번역 반영. 기존 테이블은 번역 비용 미포함이었으나 v4부터 포함.

| Step | 모델 | Input | Output | 소계 |
|---|---|---|---|---|
| Ranking | 4o-mini | ~3K tokens | ~1.5K tokens | ~$0.001 |
| Research EN | 4o | ~3K tokens | ~2.5K tokens | ~$0.033 |
| Research KO 번역 | 4o | ~3.5K tokens | ~2.5K tokens | ~$0.034 |
| Business Expert (Call 1) | 4o | ~5K tokens | ~5K tokens | ~$0.063 |
| Business Derive (Call 2) | 4o | ~6K tokens | ~4K tokens | ~$0.055 |
| Business KO 번역 | 4o | ~7K tokens | ~5K tokens | ~$0.068 |
| Editorial | 4o | ~5K tokens | ~1K tokens | ~$0.023 |
| Tavily | — | 4 queries | — | ~$0.04 |
| **합계** | | | | **~$0.32/일** |

- ==월간 예상: ~$9.6~10.5==
- 재시도 포함 시 ~$0.35/일
- 월 $10 초과 시 `admin_notifications`에 비용 경고
- vs v3 실제 비용: $0.22~0.31/일 — v4는 호출 수 대폭 감소 (17~36 → ~7), persona당 분량 증가로 비용은 유사 또는 소폭 상승

## Railway 운영비 (Stage A/B)

| Stage | Phase | 운영 모드 | 전환 기준 |
|---|---|---|---|
| **A** | Phase 2 | 범용 API 구조 + 저비용 운영 | 초기 트래픽, 파이프라인/관리 API 중심 |
| **B** | Phase 3+ | Always-on 상시 API | 검색/커뮤니티 액션/API 요청량 KPI 충족 |

> [!important] 운영비 원칙
> API 비용과 인프라 비용 분리 추적. KPI 미달 시 Stage A 유지, 달성 시 Stage B 상향.

## 비용 모니터링

- 모든 API 호출의 토큰/비용 → `pipeline_logs` 테이블 기록
- Phase 3: [[Admin]] AI Ops Dashboard에서 시각적 추적
- 모델별 ROI 비교, 프롬프트 버전별 비용 추이

## DB Capacity Planning

Supabase Free tier 500MB 한계 기준 용량 예측 (docs/05 §11).

### 테이블별 용량 추정

| 테이블 | 행당 크기 | 월간 증가량 | 12개월 후 |
|---|---|---|---|
| posts | ~10KB (JSONB 포함) | ~60행 (일 2건) | ~7.2MB |
| news_candidates | ~0.5KB | ~600행 (일 20건) | ~3.6MB |
| pipeline_logs | ~0.3KB | ~300행 (일 10건) | ~1.1MB |
| comments | ~0.3KB | 트래픽 의존 | ~2MB |
| embeddings (Phase 3) | ~6KB (1536차원 벡터) | 포스트당 5~10 청크 | ~36MB |
| 인덱스 + 오버헤드 | — | — | ~25MB |
| **합계** | | | **~75MB** |

> [!note] 12개월 후에도 ~75MB로 500MB의 15% 수준. ==임베딩이 가장 큰 비중==을 차지하며, Phase 3 pgvector 도입 후에도 12개월 내 500MB 도달 가능성은 낮다.

- 임베딩 없이 → 5년+ (사실상 도달 안 함)
- 임베딩 포함 → 약 3~4년 (Phase 3 이후)

### 500MB 대응 전략

> [!warning] 아래 트리거 포인트에 도달하면 즉시 대응 필요

| 트리거 | 행동 |
|---|---|
| DB 300MB 도달 | 오래된 `pipeline_logs` 정리 (90일 초과 삭제) |
| DB 400MB 도달 | `news_candidates` 중 `status='rejected'` 정리 (60일 초과) |
| DB 450MB 도달 | Supabase Pro ($25/월) 업그레이드 검토 |

## Phase별 Infrastructure Scope

Phase마다 인프라 구성이 단계적으로 확장된다 (docs/05 §12).

| Phase | 핵심 인프라 | 운영 모드 |
|---|---|---|
| **1a** | Vercel free + Supabase free + GitHub CI | 정적 배포, RLS, SEO 기반 |
| **1b** | + GA4, Clarity, Vercel Analytics, Lighthouse CI | 분석/모니터링 추가 |
| **2** | + Railway (sleep mode) + Vercel Cron | Stage A, 파이프라인 스케줄링, $5 크레딧 내 운영 |
| **3** | + pgvector + Railway always-on 검토 | Stage A→B 전환 판단, 시맨틱 검색, [[AI-News-Pipeline-Overview\|AI Ops Dashboard]] |
| **4** | + Polar 결제 + PWA + Supabase Pro (필요 시) | 수익화, 커뮤니티, 트래픽 확장 |
| **5** | + Expo 네이티브 앱 | 앱 스토어 배포 |

> [!note] Phase 2까지는 모든 서비스가 무료/최소 요금 범위 내에서 운영 가능 (Stage A). Phase 3에서 KPI 미달이면 Stage A를 유지하여 비용 최소화.

## Free Tier Limits & Response Plan

각 서비스의 무료 한계와 대응 계획 (docs/05 §13).

| 서비스 | 무료 한계 | 예상 도달 시점 | 대응 |
|---|---|---|---|
| **Vercel** 대역폭 | 100GB/월 | Phase 3~4 | Pro ($20/월) 또는 이미지 CDN 분리 |
| **Vercel** Cron | 2개 | Phase 3 | Railway 자체 스케줄러 (APScheduler) |
| **Vercel** Serverless | 10초 timeout | — | fire-and-forget 패턴으로 이미 우회 |
| **Supabase** DB | 500MB | ~3~4년 | 로그 정리 → Pro ($25/월) |
| **Supabase** MAU | 50K | Phase 4 | Pro 플랜 (기쁜 비명) |
| **Railway** 크레딧 | $5/월 | Phase 3 (Stage B 시) | Developer 플랜 ($5/월 추가) 또는 Stage A 유지 |
| **Tavily** API | 1,000 calls/월 | Phase 3 | Starter ($40/월) 또는 쿼리 최적화 |
| **GitHub Actions** | 2,000분/월 | 가능성 낮음 | 캐싱 최적화 |

## Policy Addendum (v2.3)

인프라 운영 정책 추가 사항 (docs/05 §14).

### Revalidate Security
- `POST /api/revalidate`는 반드시 `REVALIDATE_SECRET` 검증 → 불일치 시 `401`
- 브라우저 직접 호출 금지 (운영 정책)
- Secret 주입은 서버 사이드 경로(FastAPI 또는 Vercel server route)에서만 허용
- 반복 인증 실패 시 경고 알림

### Minimal Manual Runbook (Cron 2회 연속 실패 시)
1. `pipeline_logs`에서 최근 2회 실패 원인 확인
2. `POST /api/admin/pipeline/rerun` 호출
   - `target_date`: `YYYY-MM-DD`
   - `mode`: `safe` (기본) / 반복 실패 시 `force`
   - `trigger_revalidate`: `true`
3. 응답 코드: `202` (queued) / `200` (safe-skip) / `409` (이미 실행 중)
4. 성공 기준: `pipeline_logs` status가 `success`이고 publish/revalidate 확인 완료

> [!note] 자동 failover는 현 단계에서 범위 밖. Minimal manual runbook만 유지.

## Related

- [[AI-News-Pipeline-Overview]] — 비용이 발생하는 파이프라인
- [[Backend-Stack]] — 비용이 발생하는 인프라
- [[Infrastructure-Topology]] — 서비스 배포 토폴로지
- [[KPI-Gates-&-Stages]] — Stage 전환 기준 KPI
- [[Monitoring-&-Logging]] — 운영 모니터링 및 로그
- [[Phase-Flow]] — Phase별 진행 흐름
