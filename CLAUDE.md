# 0to1log

AI 뉴스 큐레이션 플랫폼. Solo 프로젝트 (Amy).

## Stack

- Frontend: Astro v5 + Tailwind CSS v4 + Vercel (`frontend/`)
- Backend: FastAPI + Railway (`backend/`)
- DB: Supabase (PostgreSQL + Auth + RLS)
- AI: OpenAI (gpt-4o / gpt-4o-mini) + PydanticAI
- Search: Tavily API (semantic)

## Phase

현재 **Phase 1a Foundation**. 태스크 추적 → `docs/plans/ACTIVE_SPRINT.md`

## Docs 참조 규칙

- `docs/01~08` = 원본 스펙 (계약서). 구현 전 반드시 해당 스펙 확인.
- `docs/IMPLEMENTATION_PLAN.md` = Phase 방향 + 게이트 조건 정본.
- `docs/plans/ACTIVE_SPRINT.md` = 현재 스프린트 태스크 상태.
- `docs/plans/2026-03-07-handbook-feature.md` = Handbook(용어 사전) 기능 계획. 메인 Phase와 병렬 트랙.
- `docs/plans/2026-03-08-user-features-design.md` = 일반 사용자 기능 설계 (소셜 로그인, 북마크, 읽기 기록, 내 서재).
- CLAUDE.md는 실행 규칙만. 스펙 내용을 여기에 복제하지 않는다.

## Workflow

1. 세션 시작 → `ACTIVE_SPRINT.md` 읽기 → 다음 `todo` 태스크 확인
2. 태스크 1개만 `doing`으로 전환 → 구현 → 완료 기준 통과 → `done` + `[x]`
3. `Current Doing` 표를 태스크 상태와 동기화
4. `done` 시 증거 링크 필수 (PR/로그/스크린샷)

## 금지 사항 (전역)

- Framer Motion 사용 금지 → `motion` (v11+) 사용
- `docs/` 스펙 파일은 사용자의 명시적인 요청 없이 임의로 수정하지 않는다
- 스프린트 게이트 미충족 시 다음 Phase로 넘어가지 않는다
- `.env` 파일 커밋 금지 (`.env.example`만 커밋)
- `package-lock.json`은 반드시 커밋 (CI 재현성)

## Commit

- 기능 단위 커밋. 메시지: `feat:`, `fix:`, `chore:`, `docs:`
- 코드 구현 세션과 리뷰 세션을 분리한다

## Directory

```
frontend/  → Vercel (Astro v5). CLAUDE.md 참조.
backend/   → Railway (FastAPI). CLAUDE.md 참조.
supabase/  → DB 마이그레이션 (Phase 2)
docs/      → 스펙 문서 (사용자 요청 시만 수정)
```

## Python venv policy

- Use `backend/.venv` only for backend Python commands.
- Do not create or use `backend/venv`.

## Git Branch Policy

- Use a main-only workflow.
- Day-to-day implementation happens directly on `main`.
- Commit small, coherent groups of changes so the history stays readable.
- Push to `main` after local verification and when the checkpoint is stable.
- Feature branches are optional, not the default operating mode.
