# 0to1log

AI 뉴스 큐레이션 + AI 용어집 + IT 블로그 플랫폼. Solo 프로젝트 (Amy).

## Stack

- Frontend: Astro v5 + Tailwind CSS v4 + Vercel (`frontend/`)
- Backend: FastAPI + Railway (`backend/`)
- DB: Supabase (PostgreSQL + Auth + RLS)
- AI: OpenAI (gpt-4o / gpt-4o-mini) + PydanticAI
- Search: Tavily API (semantic)

## Phase

현재 Phase → `vault/09-Implementation/plans/ACTIVE_SPRINT.md` 참조.

## 참조 규칙

- `vault/` = 프로젝트 지식 베이스 (Obsidian vault). 스펙, 설계, 계획, 의사결정 모두 여기.
- `vault/09-Implementation/plans/` = 설계 문서, 구현 계획, 스프린트 파일.
- `docs/01~08` = 원본 스펙 (레거시, 읽기 전용). vault로 변환 완료된 것은 vault 참조.
- CLAUDE.md는 실행 규칙만. 스펙 내용을 여기에 복제하지 않는다.
- 새 설계/계획 문서는 `vault/09-Implementation/plans/YYYY-MM-DD-<topic>.md`에 작성.

## Workflow

0. **계획 먼저.** 사소한 코드 수정(오타, 1줄 변경)을 제외한 모든 작업은 구현 전에 계획을 세운다. Plan mode 또는 vault 계획 문서를 사용한다.
1. 세션 시작 → `vault/` 확인 → 현재 스프린트/계획 파악
2. 태스크 1개만 `doing`으로 전환 → 구현 → 완료 기준 통과 → `done` + `[x]`
3. `Current Doing` 표를 태스크 상태와 동기화
4. `done` 시 증거 링크 필수 (PR/로그/스크린샷)
5. 계획 완료 후 → vault 관련 노트 업데이트 (변경된 아키텍처, 새로운 결정 등 반영)

## Vault 운영 규칙

- 설계/계획 문서는 `vault/09-Implementation/plans/`에 작성.
- 구현 완료 후 `vault/` 내에서 변경된 파일/기능명을 grep → 관련 노트 식별 → 필수 내용만 업데이트.

## 금지 사항 (전역)

- Framer Motion 사용 금지 → `motion` (v11+) 사용
- `docs/` 레거시 스펙 파일은 사용자의 명시적인 요청 없이 임의로 수정하지 않는다
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
vault/     → 프로젝트 지식 베이스 (Obsidian vault). 스펙/설계/계획.
docs/      → 원본 스펙 (레거시, 읽기 전용)
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
