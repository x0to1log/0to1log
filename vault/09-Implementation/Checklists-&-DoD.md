---
title: Checklists & Definition of Done
tags:
  - implementation
  - testing
  - quality
source:
  - docs/03_Backend_AI_Spec.md
  - docs/IMPLEMENTATION_PLAN.md
---

# Checklists & Definition of Done

테스트 전략 + 배포 전 검증 체크리스트.

## 테스트 계층

| 계층 | 대상 | 도구 | 실행 시점 |
|---|---|---|---|
| **Unit** | PydanticAI 스키마, 재시도 로직, JSONB 변환 | pytest | 매 커밋 |
| **Integration** | Tavily → OpenAI → Supabase 체인 | pytest + 실제 API | PR 머지 전 |
| **E2E Pipeline** | Daily Pipeline 전체 1회 실행 | 수동 트리거 | 주 1회 |
| **Schema Regression** | 프롬프트 변경 시 출력 형식 유지 | pytest + snapshot | 프롬프트 수정 시 |
| **API Boundary** | Supabase 직결 vs FastAPI 경유 경계 | contract test | 경계 정책 변경 시 |
| **RLS** | 권한 정책 정상 작동 | SQL Editor 수동 | RLS 변경 시 |

## RLS 테스트 시나리오

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | Visitor가 draft 글 조회 | 0 rows |
| 2 | User A가 User B 댓글 수정 | 0 rows affected |
| 3 | User가 타인 좋아요 삭제 | 0 rows affected |
| 4 | 일반 User가 news_posts INSERT | RLS violation error |

> [!note] Phase 3에서 pgTAP 도입 검토. 현재는 Supabase SQL Editor 수동 실행으로 충분.

## API 경계 테스트

| 시나리오 | 기대 경로 | 검증 포인트 |
|---|---|---|
| 글 목록/상세 | Frontend → Supabase 직접 | FastAPI 호출 로그 없음 |
| 단순 댓글 CRUD | Frontend → Supabase 직접 | RLS 권한 통제 |
| 시맨틱 검색 | Frontend → FastAPI | 응답/에러 핸들링 |
| 포인트/퀴즈 | Frontend → FastAPI | 트랜잭션, 중복 요청 방지 |
| Cron 트리거 | Vercel → FastAPI | 202 반환 + pipeline_logs 기록 |

## 파이프라인 DoD (Definition of Done)

- [ ] `collect_news()` 중복 URL 0개
- [ ] 1회 실행 → Research(published) + Business(draft) 2행 생성
- [ ] 동일 batch_id 2회 트리거 → 2번째 스킵
- [ ] `pipeline_logs` 최종 행 `status=success`
- [ ] PydanticAI 스키마 검증 통과
- [ ] Editorial 검수 결과 `admin_notifications` 정상 기록

## 태스크 DoD 최소 규칙

[[Implementation-Plan]] 전체 태스크에 적용되는 완료 판정 규칙.

- `상태=done`이면 반드시 `체크=[x]` + ==증거 링크==(PR/로그/스크린샷 중 1개 이상)
- 문서/코드 변경 후 `Current Doing` 표 동기화
- 실패 시 `review` 또는 `blocked`로 전환하고 원인 1줄 기록

> [!important] Nice-to-have (선택)
> - 태스크별 성능 예산 세분화 (INP/LCP)
> - UI 회귀 스냅샷 자동화
> - 디자인 토큰 lint 자동 검사

## 문서 운영 검증 체크리스트

Implementation Plan 문서 자체의 정합성 검증 항목.

- [ ] Hard Gate 5개가 [[Active-Sprint]] 태스크/게이트에 반영되어 있다
- [ ] 2B에는 Cron skeleton만 있고, 실연동/E2E는 2D에만 있다
- [ ] 2C QA 항목에 Lighthouse/반응형/접근성/CWV 수치 기준이 있다
- [ ] 모든 done 태스크가 `[x] + 증거 링크`를 갖는다
- [ ] OpenAPI 고정 이후 2C mock 필드가 계약과 일치한다

## Related

- [[Quality-Gates-&-States]] — PydanticAI 검증 + 에러 핸들링 상세
- [[AI-News-Pipeline-Design]] — 테스트 대상 파이프라인
- [[Backend-Stack]] — RLS + API 경계 정의
- [[Database-Schema-Overview]] — 테스트 대상 스키마
- [[Active-Sprint]] — 현재 스프린트 태스크
- [[Implementation-Plan]] — 전체 실행 계획 + Hard Gates
