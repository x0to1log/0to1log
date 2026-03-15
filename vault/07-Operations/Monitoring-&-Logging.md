---
title: Monitoring & Logging
tags:
  - operations
  - monitoring
  - logging
source: docs/05_Infrastructure.md
---

# Monitoring & Logging

서비스별 모니터링, 로깅, 알림 체계. Solo 프로젝트 특성상 각 서비스의 내장 대시보드를 최대한 활용하고, 커스텀 구축은 AI 파이프라인 로그 조회와 운영 지표(Phase 3 AI Ops Dashboard)에 한정한다.

## Service-Level Monitoring

| Service | Monitoring Tool | Metrics |
|---|---|---|
| **Vercel (Frontend)** | Vercel Analytics + 빌드 로그 | Core Web Vitals (LCP, CLS, INP), deployment status, SSR 에러 |
| **Railway (Backend)** | Railway 대시보드 | CPU/Memory 사용량, 응답 시간, error rate, 크래시 로그 |
| **Supabase (DB)** | Supabase Dashboard | DB 크기, active connections, 쿼리 성능 |
| **AI Pipeline** | Supabase `pipeline_logs` 테이블 | 파이프라인 성공/실패, 토큰/비용 추적 |
| **API 비용** | OpenAI Dashboard + Tavily Dashboard | 일/월 사용량, 잔여 크레딧 |
| **사용자 행동** | GA4 + MS Clarity | 트래픽 소스, 유저 흐름, 히트맵, 세션 리플레이 |

## Logging

- **Frontend**: Vercel Functions logs — 서버사이드 렌더링(SSR) 에러, 빌드 실패 로그
- **Backend**: Railway logs — FastAPI stdout 기반 structured logging
- **Pipeline**: `pipeline_logs` 테이블 (Supabase) — **per-stage** status (1회 실행당 6~8개 로그)
  - `_log_stage()` 헬퍼로 각 스테이지(collect, rank, facts, persona, save, summary) 기록
  - 각 LLM 스테이지: `tokens_used`, `cost_usd`, `model_used`, `duration_ms`, `attempt` 기록
  - `debug_meta` (JSONB): input/output 토큰, LLM 입출력 내용, 백필 파라미터 등
  - 상세 스키마: [[Pipeline-Stage-Logging-Schema]]
  - 최근 24시간 조회: `SELECT pipeline_type, status, created_at, error_message, tokens_used, cost_usd, debug_meta FROM pipeline_logs WHERE created_at > NOW() - INTERVAL '24 hours' ORDER BY created_at DESC;`
- **Alerts**: `admin_notifications` 테이블 — editorial/error 알림 저장, Admin 대시보드에서 확인

## Alerting

| 이벤트 | 알림 방식 | 시점 |
|---|---|---|
| Pipeline failure | `admin_notifications` INSERT + Admin 대시보드 확인 | Phase 2 |
| Pipeline failure (이메일) | Supabase Webhooks 또는 Resend API | Phase 3 |
| Cost threshold 초과 ($10/월) | `admin_notifications` + OpenAI Usage Alert | Phase 2 |
| Vercel 빌드 실패 | GitHub Commit Status (자동) + Vercel 이메일 | Phase 1a |
| Railway 크래시 | Railway 이메일 알림 (기본 설정) | Phase 2 |

**파이프라인 실패 알림 흐름:** 실패 → `pipeline_logs` status='failed' 기록 → `admin_notifications` 알림 저장 → Admin 대시보드 확인 → (Phase 3) 이메일 자동 알림

## Operational KPIs

Stage A→B 전환 판단 및 서비스 건강성 추적을 위한 핵심 운영 지표.

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| **p95 응답시간** | < 500ms | Railway 대시보드 + FastAPI 미들웨어 로깅 |
| **Error rate** | < 1% (5xx 기준) | Railway 대시보드 + `pipeline_logs` |
| **Uptime** | > 99.5% | Railway 대시보드 |
| **Pipeline success rate** | 추적 | `pipeline_logs` 테이블 (성공/실패 비율) |
| **Daily cost** | 추적 (월 $10 임계치) | OpenAI Dashboard + `pipeline_logs` cost_usd |
| **Rate limit 히트율** | < 5% | FastAPI slowapi 로그 |
| **일일 API 요청 수** | 추적 | FastAPI 미들웨어 로깅 |

> [!note] Phase 3 AI Ops Dashboard
> Phase 3에서 Admin 대시보드 내 AI Ops 뷰를 구축하여 위 KPI를 시각적으로 추적할 예정. 검색 일 평균 요청 수 + 커뮤니티 액션 수가 임계치를 넘으면 Railway Always-on(Stage B) 전환을 검토한다. 구체적 임계치는 Phase 2 운영 데이터 축적 후 결정.

## Related
- [[Infrastructure-Topology]] — 모니터링 대상 서비스
- [[Pipeline-Stage-Logging-Schema]] — 스테이지별 로깅 스키마

## See Also
- [[AI-News-Pipeline-Design]] — 파이프라인 로깅 (04-AI-System)
