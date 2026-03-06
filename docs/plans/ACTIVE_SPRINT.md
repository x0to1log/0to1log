# ACTIVE SPRINT — Phase 1b Analytics

> **스프린트 시작:** 2026-03-06
> **목표:** GA4 + Microsoft Clarity 연동으로 데이터 수집 시작
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 스펙 → `docs/05~06`
> **이전 스프린트:** Phase 1a Foundation — 2026-03-06 게이트 전체 통과

---

## 스프린트 완료 게이트

- [ ] GA4 Realtime 탭에서 이벤트 수신 확인
- [ ] Clarity Dashboard에서 세션 리플레이 녹화 확인
- [ ] `astro build` — 0 error
- [ ] CSP 위반 없음 (브라우저 Console 확인)
- [ ] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [ ] `Current Doing` 슬롯이 비어 있음(`-`)
- [ ] 완료 태스크마다 `증거` 링크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| - | - | - | Amy |

규칙:
- 문서 내 `상태: doing` 태스크가 있으면 이 표에는 반드시 1개만 기입한다.
- 문서 내 `상태: doing` 태스크가 0개면 표는 `-`를 유지한다.
- 태스크 상태 변경 시 이 표를 같은 커밋에서 함께 갱신한다.

---

## 상태 업데이트 규칙

- 혼합형 고정: `상태(todo/doing/review/done/blocked)` + `체크([ ]/[x])`를 함께 사용한다.
- `todo/review/doing/blocked`는 `체크: [ ]`로 유지한다.
- `done`은 반드시 `체크: [x]`로 변경한다.
- `상태`와 `체크`가 불일치하면 무효로 간주한다. 예: `상태: done` + `체크: [ ]` 금지.
- `증거`는 태스크 완료(`상태: done`) 시 필수이며, PR/로그/스크린샷 중 최소 1개 링크를 남긴다.

---

## 태스크 (실행 순서)

### 1. GA4 연동 `[P1-ANL-01]`
- **체크:** [ ]
- **상태:** review
- **산출물:** GA4 gtag.js 스크립트 + CSP 허용 + 환경변수
- **완료 기준:** GA4 Realtime 탭에서 페이지뷰 이벤트 수신
- **검증:** Google Analytics > Realtime > 이벤트 확인
- **증거:** (완료 시 필수)
- **참조:** 05 §1, §6-5, §12 | 06 §3.1

### 2. Microsoft Clarity 연동 `[P1-ANL-02]`
- **체크:** [ ]
- **상태:** review
- **산출물:** Clarity 스크립트 + CSP 허용 + 환경변수
- **완료 기준:** Clarity Dashboard에서 세션 리플레이 녹화 확인
- **검증:** Clarity Dashboard > Recordings 탭 확인
- **증거:** (완료 시 필수)
- **참조:** 05 §6-5 | 06 §3.1

---

## 의존성 흐름

```
P1-ANL-01 ──┐
             ├── 게이트 검증 (수동)
P1-ANL-02 ──┘
```

---

## 다음 스프린트 예고

Phase 1b 게이트 통과 시 → **Phase 2 AI Core** (Railway/FastAPI + AI 파이프라인)
