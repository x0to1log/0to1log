---
title: Implementation Plan
tags:
  - implementation
  - planning
---

# Implementation Plan

> 바이브 코딩 속도는 유지하되, 재작업을 유발하는 핵심 리스크만 강제하는 ==실행 계약==.
>
> 이 문서는 "무엇을 만들까"보다 **"어떻게 일할까"**를 정한다. Phase/Sprint 흐름은 [[Phase-Flow]], 현재 진행 태스크는 [[plans/ACTIVE_SPRINT]].

---

## 문서 역할 분리

| 문서 | 역할 | 갱신 시점 |
|------|------|----------|
| [[Implementation-Plan]] | **실행 계약**, Hard Gates, 상태 규칙, Task ID 규칙 | 운영 규칙 변경 시 |
| [[Phase-Flow]] | Phase/Sprint 흐름, 진입/완료 Gate, 미래 기능 맵 | Phase 진입/완료 시 |
| [[plans/ACTIVE_SPRINT]] | 현재 진행 중인 태스크 현황 | 작업 시작/상태 변경 시 |
| `vault/09-Implementation/plans/` | 개별 작업의 상세 계획, 세부 체크리스트 | 새 작업 계획 수립 시 |
| [[Checklists-&-DoD]] | 테스트 계층 + RLS/API 경계 + 파이프라인 DoD | 검증 정책 변경 시 |

---

## Hard Gates

> [!important] 모든 Phase에서 강제하는 7개 규칙.

### 1. DB/API/타입 계약은 같이 바꾼다

Supabase 스키마, FastAPI 응답, Astro TS 타입 중 **하나라도** 바뀌면 같은 작업 묶음에서 함께 반영한다. 프론트만 먼저 가면 계약이 깨진다.

### 2. 쓰기·생성·권한·비용 흐름은 FastAPI를 통과한다

Supabase direct read는 허용한다. 하지만 **AI 호출 / INSERT·UPDATE / 권한 판정 / 비용 발생**은 FastAPI가 단일 진입점이어야 한다. Astro에서 Supabase로 직접 쓰면 RLS만 믿어야 하는데, 그것만으론 부족하다.

### 3. 권한과 과금은 서버에서 재검증한다

RLS + FastAPI 권한 체크 + tier gating을 **클라이언트만으로 믿지 않는다**. 프론트 숨김 처리는 UX 힌트일 뿐, 보안 경계가 아니다.

### 4. `done`에는 검증 명령·통과 조건·증거가 있어야 한다

"확인함"만으로 끝내지 않는다. 상태=`done`이면 반드시:
- `체크=[x]`
- 검증 명령 또는 확인 방법 기재
- 통과 조건 충족
- 증거 1개 이상 (commit hash / PR / 로그 요약 / 스크린샷)

### 5. 백엔드 트랙과 프론트엔드 트랙은 페어링한다

프론트에 필드만 추가하고 백엔드 실제 출력 생산이 미뤄지면 안 된다. **한 스프린트 범위 안에서 end-to-end로 돌아가게** 묶는다. (NP4-Q 초기의 교훈 — 스켈레톤만 올라가 있고 실제 페르소나 생성 안 되던 기간.)

### 6. 화면 구조·Phase 범위가 바뀌면 관련 문서를 같이 갱신한다

최소한 아래 중 하나는 같이 동기화:
- [[plans/ACTIVE_SPRINT]]
- [[Phase-Flow]]
- 관련 space/feature note (03-Features, 08-Design 등)

### 7. Gate 실패 시 다음 Phase로 가지 않는다

G3i 실패면 Phase 3-Intelligence Wave 1을 시작하지 않는다. 다음을 더하는 대신 **현재 루프의 품질/직관성/가치를 먼저 개선**한다.

---

## Task ID 규칙

> **결정 (2026-04-16):** 0to1log는 뉴스/핸드북/블로그 **동시 트랙**이라 도메인 기반 prefix가 sprint 기반보다 자연스럽다.

### 형식

```
{DOMAIN}-{SEQ}
{DOMAIN}-{SUB}-{SEQ}
```

### Domain prefix (현재 사용 중)

| Prefix | 영역 |
|--------|------|
| `HB-*` | Handbook (redesign, migrate, editor 등) |
| `HQ-*` | Handbook Quality (hallucination, tone, facet 등) |
| `HB-UX-*` | Handbook UX (callout, code block, layout 등) |
| `HB-QUALITY-*` | Handbook 심화 품질 (advanced depth, comparison 등) |
| `NQ-*` | News Quality |
| `GPT5-*` | GPT-5 마이그레이션 |
| `UA-*` | User Analytics |
| `WEBHOOK-USER-*` | 유저 Webhook 구독 |
| `COLLECT-*` | 수집기 (Brave, Exa 등) |
| `AUTOPUB-*` | 자동 발행 |
| `FASTAPI-DIRECT-*` | Admin FastAPI 직접 호출 |
| `QUALITY-CHECK-*` | 품질 평가 시스템 |
| `PROMPT-AUDIT-*` | 프롬프트 감사 |
| `PERF-*` | 성능 |
| `SEC-*` | 보안 |

### 원칙

- 기존 ID 의미를 바꾸지 않는다. 범위가 크게 달라지면 **새 ID를 발급**한다
- 세부 태스크는 suffix letter로 확장 (예: `WEBHOOK-USER-01a`, `01b`)
- 신규 도메인 생길 때만 새 prefix 발급 — 임의 난립 금지

---

## 상태 규칙

> **결정 (2026-04-16):** Idea Mine의 5개 기본 상태 + 0to1log 고유의 2차 자동 상태 병행.

### 1차 상태 (수동)

| 상태 | 의미 |
|------|------|
| `todo` | 아직 시작 전 |
| `doing` | 현재 진행 중 (`in_progress`와 동의어 — 표준은 `doing`) |
| `review` | 동작은 했지만 검증/정리 대기 |
| `blocked` | 의존성/결정 부족으로 멈춤 |
| `done` | 검증과 증거까지 완료 |
| `cancelled` | 의도적으로 드롭 (사유 1줄 기록) |

### 2차 상태 (자동 판정 — commit 기반)

| 마커 | 의미 | 기준 |
|------|------|------|
| `⚠️ stale` | 1차 상태는 `doing`인데 진전이 멈춤 | 마지막 매칭 commit **7일+** |
| `⚠️ ghost` | 시작은 선언됐으나 실체가 없음 | 시작 후 **14일+** & 매칭 commit **0건** |

**운영 규칙:**
- `⚠️ stale`: 사유 1줄 추가하거나 `blocked`로 전환
- `⚠️ ghost`: **drop or restart** 결정 — 방치 금지
- 2차 상태는 sprint sync 시 자동 점검 (skill: `0to1-sprint-sync`)

### `done` 최소 규칙

- [x] 체크 표시
- 검증 명령 또는 확인 방법 기재
- 통과 조건 충족
- 증거 1개 이상 (commit hash / PR / 로그 요약 / 스크린샷 경로)

---

## 검증과 증거

작업 종류에 따라 검증 방식은 달라도 된다. 다만 **없으면 안 된다.**

| 작업 유형 | 검증 예시 |
|-----------|-----------|
| 웹 UI | `npm run dev` + 브라우저 확인 + 필요 시 Playwright 스모크 |
| 백엔드/API | `python -m pytest` + 라우트 호출 결과 |
| DB 마이그레이션 | `supabase db reset --linked --no-seed --yes` + contract test |
| 프롬프트 | 샘플 입력 대비 출력 스냅샷 + quality_score |
| 파이프라인 | E2E 1회 실행 + `pipeline_logs.status=success` |
| 문서 | 관련 문서 간 링크/용어 일치 확인 |

상세는 [[Checklists-&-DoD]].

---

## ACTIVE_SPRINT 연동 규칙

- 태스크 템플릿 권장 필드:
  1. Task ID
  2. 제목 / 목표
  3. 상태 (+ ⚠️ 2차 마커)
  4. 우선도 (P0/P1/P2)
  5. 완료 기준
  6. 검증 명령
  7. 증거 (commit hash 등)
  8. 참조 / 의존성
- 같은 Phase 내 기본 참조는 **[[plans/ACTIVE_SPRINT]] 우선**
- Phase 전환 또는 Gate 판정 시에만 이 문서 + [[Phase-Flow]] 재조회
- Sprint 클로즈 시: 스프린트 요약을 **[[12-Journal-&-Decisions/]]로 이동**하고 ACTIVE_SPRINT는 현재 스프린트 내용만 유지

---

## 기본 가정

- 이 문서는 구현 코드가 아니라 ==실행 계약 문서==다.
- Phase별 상세 범위/태스크/게이트는 [[Phase-Flow]]에서 관리한다.
- 목표는 "최소 규칙으로 최대 실행 속도"이며, 과도한 세부 규칙은 Nice-to-have로 분리한다.
- Backend Python virtualenv는 `backend/.venv`만 사용한다 (`backend/venv` 금지).

---

## Nice-to-have (선택)

- 태스크별 성능 예산 세분화 (INP/LCP)
- UI 회귀 스냅샷 자동화
- 디자인 토큰 lint 자동 검사
- pgTAP 도입 (현재는 SQL Editor 수동으로 충분)

---

## Product Language Boundary

| 구분 | 용어 |
| --- | --- |
| Public | `AI News`, `Handbook`, `Library` |
| Internal / Admin | `Posts`, `Handbook` |
| Route | `/{locale}/log/` (AI News 호환 경로) |

## Navigation Shell Contract

| Shell | 구조 |
| --- | --- |
| Web | `[Brand] [Primary Nav] [Utilities]` |
| Mobile / App | `[Brand/Page] [Profile or Settings]` + primary nav 별도 노출 |
| Primary Nav | `AI News \| Handbook \| Library` (고정) |
| Utility Drawer | Language, Theme 컨트롤 (공개 헤더 인라인 아님) |

---

## Related

- [[Phase-Flow]] — Phase/Sprint 흐름 + Gate 정량 기준
- [[plans/ACTIVE_SPRINT]] — 현재 스프린트 태스크
- [[Checklists-&-DoD]] — 완료 기준 체크리스트

## See Also

- [[KPI-Gates-&-Stages]] — Phase 4 Gate 정량 기준 (06-Business)
