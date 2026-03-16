---
title: "Phase 1a~3B: 7단계 완주 회고"
tags:
  - retro
  - phases
  - journal
  - milestone
date: 2026-03-16
---

# Phase 1a~3B: 7단계 완주 회고

오늘 [[Phase-Flow]] 기준으로 Phase 3B까지 7단계를 모두 완주했다. 짧지 않은 여정이었고, 각 단계마다 예상치 못한 곳에서 막혔다. 가장 힘들었던 것 하나씩만 남겨둔다.

---

## Phase 1a — Foundation

**완료 내용:** Astro + Tailwind + 3 테마(light/dark/newsprint) + 폰트 + BaseLayout + Vercel 배포.

**가장 힘들었던 것:** 폰트 렌더링. 3개 테마를 동시에 지원하면서 light 모드 코드 블록 가독성이 계속 무너졌다. 배경과 폰트 컬러 조합을 테마마다 따로 잡아야 했는데, CSS 변수 계층을 설계하기 전에 컬러를 먼저 정해버린 게 원인이었다.

**교훈:** 테마 시스템은 처음부터 토큰 계층을 먼저 정의하고, 컬러는 그 이후에 채워야 한다. 순서를 바꾸면 나중에 전부 다시 손댄다.

---

## Phase 1b — Data Connection

**완료 내용:** Supabase 연동, 하이브리드 SSR/SSG, 로그 목록/상세, Admin CRUD, ARIA/a11y.

**가장 힘들었던 것:** 페이지별 SSR vs SSG 결정. "어떤 페이지가 실시간 데이터가 필요한가?"라는 질문이 생각보다 어려웠다. 처음에는 전부 SSR로 잡았다가 빌드 시간이 폭발했고, 반대로 SSG로 전환하면 어드민 반영이 느렸다.

**교훈:** 페이지를 "누가 보는가(public/auth)" + "얼마나 자주 바뀌는가(static/dynamic)"로 2×2 매트릭스로 분류하면 결정이 빠르다. 이 기준을 처음부터 문서화했어야 했다.

---

## Phase 2B — OPS/Backend

**완료 내용:** AI Agent 로직, Admin CRUD 엔드포인트, Cron 스켈레톤.

**가장 힘들었던 것:** 401과 403 분리. FastAPI에서 인증 실패(토큰 없음/만료)와 인가 실패(권한 없음)를 같은 에러로 뭉개버리면 프론트에서 처리가 불가능하다. 초기에 둘 다 401로 내려보냈다가 어드민 리다이렉트 로직이 꼬였다.

**교훈:** 401은 "누구인지 모름", 403은 "누군지 알지만 안 됨". HTTP 의미론을 처음부터 지키면 프론트 에러 핸들링이 단순해진다.

---

## Phase 2C — EXP/Frontend

**완료 내용:** Newsprint 토큰, 목록/상세 페이지, i18n 스위처, Admin 에디터(Milkdown).

**가장 힘들었던 것:** [[MEMORY#Milkdown Crepe 7.19 — setMarkdown 없음|Milkdown Crepe 통합]]. `setMarkdown()` API가 존재하지 않아서 body 교체가 안 됐다. 공식 문서에는 나와 있지 않고, 소스를 직접 파서 `replaceAll` action 패턴을 찾아내야 했다.

**교훈:** 써드파티 에디터 라이브러리는 버전별 API 차이가 크다. 통합 전에 해당 버전 소스코드를 먼저 확인하는 것이 문서보다 신뢰할 수 있다.

---

## Phase 2D — INT/Integration

**완료 내용:** CSP 초기 하드닝, Supabase Auth 실제 연동, Mock 제거, Cron 파이프라인.

**가장 힘들었던 것:** Mock을 걷어내는 과정. Mock → 실제 API 전환 시 인터페이스가 미묘하게 달라서 조용히 깨지는 곳이 많았다. 특히 에러 구조가 달라서 에러 핸들러가 통째로 무용지물이 됐다.

**교훈:** Mock은 실제 API와 에러 구조까지 동일하게 맞춰야 전환 비용이 0에 가까워진다. Mock 설계 시 happy path만 흉내 내면 나중에 두 배로 고생한다.

---

## Phase 3-USER — User Features

**완료 내용:** OAuth(GitHub + Google), 읽기 기록, 북마크, 학습 진도, My Library.

**가장 힘들었던 것:** Supabase RLS 정책. 4개 테이블, 테이블마다 접근 패턴이 달랐다. 읽기 기록은 본인만 읽기, 북마크는 본인 읽기/쓰기, 학습 진도는 어드민도 읽기 가능 등 조합이 복잡했고, 정책 하나 잘못 쓰면 전체가 막히거나 전부 열린다.

**교훈:** RLS는 테이블 단위가 아니라 "역할 × 작업(SELECT/INSERT/UPDATE/DELETE)" 매트릭스로 먼저 설계하고 SQL을 작성해야 한다. 코드 먼저 짜고 나중에 정책 추가하면 디버깅이 끔찍하다.

---

## Phase 3A-SEC + 3B-SHARE — Security & Social

**완료 내용:** CSP nonce 마이그레이션, 소셜 공유(X/LinkedIn/URL 복사), OG 메타.

**가장 힘들었던 것:** CSP nonce + `strict-dynamic` + 써드파티 스크립트 상호작용. nonce 기반 CSP는 이론상 깔끔한데, 써드파티 스크립트가 자식 스크립트를 동적으로 추가하면 `strict-dynamic` 없이는 막힌다. 반대로 `strict-dynamic`을 켜면 기존 `allowlist` 기반 도메인 허용이 무시돼서 의도치 않은 부분이 열렸다.

**교훈:** CSP는 nonce + `strict-dynamic`을 함께 설계해야 한다. 나중에 둘 중 하나만 추가하면 기존 정책과 충돌한다. 또 써드파티 스크립트 목록은 처음부터 CSP 설계에 포함시켜야 한다.

---

## 전체 회고

7단계를 돌아보면 공통 패턴이 보인다. **"나중에 고치면 되겠지"가 통한 적이 없었다.** 토큰 계층, 에러 구조, RLS 매트릭스, CSP 설계 — 전부 처음에 제대로 잡았어야 나중 비용이 적었다. 반대로 Mock 제거나 Milkdown처럼 예상 못 한 복잡도는 소스를 직접 파고드는 것 외에 지름길이 없었다.

다음 Phase부터는 **설계 단계에서 "나중에 바꾸기 가장 어려운 것"을 먼저 결정하는 습관**을 의식적으로 유지한다.
