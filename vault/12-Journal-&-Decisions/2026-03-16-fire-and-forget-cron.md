---
title: "ADR: Fire-and-Forget Cron 패턴 — Vercel Cron + Railway Background Job"
tags:
  - architecture
  - decision
  - deployment
  - cron
date: 2026-03-16
---

# ADR: Fire-and-Forget Cron 패턴

> 날짜: 2026-03-16
> 상태: 결정됨
> 관련: [[System-Architecture]], [[Deployment-Pipeline]]

---

## 맥락

뉴스 파이프라인은 한 번 실행 시 Tavily 뉴스 수집 → LLM 랭킹 → LLM 콘텐츠 생성 (복수 호출) → Supabase 저장 순으로 진행된다. 실측 소요 시간은 **2~5분**이다.

Vercel에서 Astro 프론트엔드를 호스팅하고, Vercel Cron Job으로 정기 실행을 트리거하는 구조를 자연스럽게 고려했다. 그러나 **Vercel Serverless Function의 실행 제한이 10초**라는 사실이 문제가 됐다. 파이프라인 자체를 Vercel에서 직접 실행하면 반드시 타임아웃이 발생한다.

### 인프라 현황

| 레이어 | 플랫폼 | 역할 |
|--------|--------|------|
| 프론트엔드 | Vercel (Astro v5) | SSR 페이지 렌더링, 정적 자산 서빙 |
| 백엔드 | Railway (FastAPI) | 파이프라인 실행, LLM 호출, DB 쓰기 |
| DB | Supabase (PostgreSQL + RLS) | 데이터 저장, 인증, 행 수준 보안 |

---

## 결정

**Vercel Cron이 Railway 백엔드를 "시작"만 하고 즉시 202를 반환한다.**
실제 파이프라인은 Railway에서 FastAPI BackgroundTask로 비동기 실행된다.

### 흐름

```
Vercel Cron (10s 이내)
  → POST /cron/run-pipeline  (Railway FastAPI)
      → 202 Accepted 즉시 반환  ← Vercel Cron이 받는 응답
      → BackgroundTask 시작
            → 뉴스 수집 (Tavily)
            → LLM 랭킹 (gpt-4o-mini)
            → LLM 콘텐츠 생성 (gpt-4o × n회)
            → Supabase 저장
            → 스테이지 로깅
        (총 2~5분, Vercel와 무관하게 Railway에서 계속 실행)
```

### 프론트엔드의 데이터 읽기 방식

Astro 페이지는 파이프라인이 완료된 데이터를 읽을 때 **FastAPI를 거치지 않고 Supabase에서 직접 읽는다**. Supabase RLS가 공개 데이터에 대해 `anon` 키 읽기를 허용하므로, 별도 API 레이어 없이 프론트엔드 → Supabase 직접 쿼리가 가능하다.

```
프론트엔드 (Astro SSR)
  → Supabase (anon 키, RLS SELECT 허용)
      → news_posts, handbook_terms 등 읽기
```

FastAPI는 **쓰기 경로(파이프라인, 어드민 CRUD)** 에만 관여한다.

---

## 고려한 대안

### A. Vercel Cron에서 FastAPI를 직접 동기 호출
- 파이프라인을 2~5분 내에 완료해야 하므로 Vercel 10초 제한에서 타임아웃 불가피.
- Pro 플랜에서 300초 제한을 쓸 수 있지만, 그래도 LLM 호출 지연 누적에 취약.
- **기각**: Vercel 플랜 업그레이드 + 제한 시간 내 완료 보장이 모두 불안정.

### B. Railway Cron (별도 스케줄러)
- Railway에서 자체 Cron을 돌려 FastAPI 내부 함수를 직접 호출.
- Vercel Cron을 쓰지 않아도 됨.
- **보류**: Vercel Cron으로 스케줄 관리를 일원화하는 쪽이 설정이 단순. 현재 구조로 충분하다면 도입 이유 없음. Railway Cron은 파이프라인이 더 복잡해질 경우 재검토.

### C. 프론트엔드 → FastAPI → Supabase 읽기 프록시
- Supabase를 직접 노출하지 않고 FastAPI가 모든 읽기를 프록시.
- 장점: 데이터 접근 로직을 백엔드에서 중앙 관리.
- 단점: 읽기마다 Railway 홉이 추가됨. RLS가 이미 행 수준 접근 제어를 제공. Railway 콜드 스타트가 읽기 지연을 유발.
- **기각**: Supabase RLS가 공개 데이터 읽기를 안전하게 제어하므로 프록시 불필요.

---

## 트레이드오프

### 이 패턴의 이점

| 이점 | 이유 |
|------|------|
| Vercel 10초 제한 우회 | 202 즉시 반환이므로 제한에 걸리지 않음 |
| 파이프라인 실행 시간 무제한 | Railway에서 프로세스가 완료될 때까지 실행 |
| 백엔드 책임 명확 | Railway = 쓰기·연산. Supabase = 읽기 |
| 프론트엔드 읽기 지연 최소화 | Supabase 직접 쿼리, Railway 홉 없음 |
| 파이프라인 실패가 응답에 영향 없음 | 202 반환 후 백그라운드에서 실패해도 Vercel Cron은 성공으로 기록 |

### 이 패턴의 약점

| 약점 | 대응 |
|------|------|
| 파이프라인 실패가 침묵할 수 있음 | 스테이지 로깅 + `pipeline_runs` 테이블로 추적 |
| Cron 결과를 Vercel에서 확인 불가 | Railway 로그 + Supabase 로그 직접 확인 |
| Railway 콜드 스타트 | 파이프라인 트리거가 첫 요청이면 수 초 지연 — 허용 범위 |
| 파이프라인 중복 실행 가능 | `pipeline_runs` 상태 체크로 중복 방어 예정 |

---

## 백엔드 역할 정의 (이 결정 이후)

이 패턴을 선택함으로써 FastAPI 백엔드의 역할이 명확해졌다:

- **포함**: Cron 트리거 수신 → BackgroundTask 실행, 어드민 CRUD, AI 파이프라인 오케스트레이션
- **불포함**: 프론트엔드용 읽기 API, 일반 사용자 데이터 프록시

FastAPI는 **운영(ops) 전용 백엔드**다. 사용자가 직접 호출하는 API가 아니다. 이로 인해 FastAPI에 Rate Limiting, 캐싱, 읽기 최적화 등을 신경 쓸 필요가 없어졌다.

---

## 교훈

1. **플랫폼 제한을 먼저 파악해라.** Vercel Cron 10초 제한은 설계 단계에서 알고 있었기 때문에 타임아웃을 경험하기 전에 패턴을 선택했다.

2. **202 Accepted는 "시작했음"이지 "완료했음"이 아니다.** Fire-and-Forget 패턴에서는 파이프라인 완료 여부를 별도 메커니즘(로그, DB 상태)으로 추적해야 한다.

3. **RLS가 있으면 프록시가 필요 없다.** Supabase RLS가 행 수준 접근 제어를 담당하면, FastAPI를 거치지 않아도 보안이 유지된다. 아키텍처 레이어를 줄이는 것이 유지보수성을 높인다.

4. **백엔드의 역할을 좁게 정의할수록 설계가 단순해진다.** "모든 트래픽이 FastAPI를 거쳐야 한다"는 가정을 버리면, 백엔드가 실제로 잘하는 것(연산, 오케스트레이션)에만 집중할 수 있다.

---

## Related

- [[System-Architecture]] — 전체 인프라 레이어 구조
- [[Deployment-Pipeline]] — Vercel / Railway 배포 설정
- [[AI-News-Pipeline-Design]] — 파이프라인 설계 (v2/v3 기준)
- [[2026-03-15-news-pipeline-v1-postmortem]] — v1 실패 포스트모템
- [[2026-03-16-news-pipeline-v3-decision]] — v3 전환 ADR
