---
title: Component States
tags:
  - design
  - components
  - states
source: docs/04_Frontend_Spec.md
---

# Component States

핵심 컴포넌트의 상태 정의, 공통 컴포넌트 패턴, 에러 핸들링 UI 정책.

## Post Card

- **일반 상태**: 제목, 한줄 요약(`one_liner`), 카테고리 배지(`AI NEWS · Research`), 온도 바, 읽기 시간, 태그
- **호버**: 보더 accent glow + `translateY(-2px)` 미세 스케일업
- **온도 시각화**: `news_temperature` 값에 따른 5단계(1~5) 좌측 세로 바, 색상 그라데이션

| 상태 | UI 표현 |
|---|---|
| Loading | 카드 틀 유지 + shimmer(skeleton) 애니메이션, 3개 placeholder |
| Empty | "아직 발행된 글이 없습니다" + Admin이면 "새 글 작성" 버튼 |
| Error | "글을 불러오는 데 실패했습니다" + 다시 시도 버튼 |
| Success | 정상 카드 렌더링 |

## Persona Switcher

| State | UI | Fallback |
|---|---|---|
| 첫 방문 (쿠키 없음) | "입문자" 탭 기본 활성 + "읽기 수준을 선택하세요" 툴팁 (1회만) | `beginner` 기본 |
| 쿠키 있음 | 저장된 페르소나 탭 자동 활성, 알림 없음 | — |
| 전환 중 | 이전 탭 fade-out → 새 탭 fade-in (150ms) + 언더라인 spring slide | — |
| 전환 실패 | 이전 버전 유지 + "전환에 실패했습니다" 토스트 (3초 후 자동 닫힘) | 이전 버전 유지 |
| Research 포스트 | Switcher 미렌더링 (`post_type === 'research'`) | — |
| 콘텐츠 없음 | 요청한 페르소나 콘텐츠가 없을 때 | `learner → beginner` 폴백 |

> [!important] Fallback 우선순위
> `DB preference → cookie → beginner`
>
> 로그인 사용자가 첫 1회 페르소나를 선택하면 쿠키와 DB에 동시 upsert.

## Comment Section

| 상태 | UI 표현 |
|---|---|
| 비로그인 | 댓글 목록 보임 + "댓글을 작성하려면 로그인하세요" + Google / GitHub 버튼 |
| 로그인 + 댓글 없음 | "첫 번째 댓글을 남겨보세요!" + 작성 input |
| 작성 중 | 실시간 글자 수 카운터 + spinner + 비활성 (중복 방지) |
| 전송 성공 | Optimistic update — 즉시 반영 |
| 전송 실패 | 작성 중이던 텍스트 유지 + "댓글 등록에 실패했습니다" + 다시 시도 |
| 삭제 확인 | 인라인 확인 (모달 아님) — "정말 삭제하시겠습니까?" + 삭제 / 취소 |
| Loading | 댓글 영역 skeleton 3개 |
| 스팸 throttle | 30초 내 연속 댓글 방지, "N초 후 다시 작성할 수 있습니다" 카운트다운 |
| 연속 실패 | 3회 연속 실패 시 "잠시 후 다시 시도해주세요" + 60초 쿨다운 |

> [!note]
> 서버 사이드 스팸 방어(Supabase RLS rate limiting, 봇 차단)는 `05_Infrastructure.md`에서 별도 정의. 여기서는 프론트엔드 레벨 throttle만 다룬다.

## Today's AI Pick

| 상태 | UI 표현 |
|---|---|
| 정상 | Research 카드 + Business 카드 2장 나란히 |
| Research 뉴스 없음 | Research 카드에 "오늘 기술 뉴스 없음" (muted 톤) + Business 카드 정상 |
| 둘 다 없음 | "오늘의 AI Pick이 아직 준비 중입니다" 안내 + 최근 글 리스트로 대체 |
| Loading | 2장 카드 skeleton |

## Cmd+K Search Modal

- **트리거**: `Cmd+K` (Mac) / `Ctrl+K` (Windows)
- **입력 중**: 디바운스 300ms → 결과 요청
- **결과 있음**: 포스트 제목 + 카테고리 + 매칭 snippet (최대 5개)
- **결과 없음**: "검색 결과가 없습니다" + 다른 키워드 제안
- **오류**: "검색에 실패했습니다" + 재시도 안내

| Phase | 검색 방식 |
|---|---|
| Phase 1~2 | 기본 키워드 필터링 (클라이언트 사이드) |
| Phase 3 | `FastAPI /api/search/semantic` 경유 pgvector 시맨틱 검색 |

## Common Components

### Navigation

```
┌──────────────────────────────────────────────────┐
│  [Logo]    Home   Log   Portfolio    🔍   🌙  👤 │
└──────────────────────────────────────────────────┘
```

| 요소 | 동작 |
|---|---|
| Logo | 클릭 시 Home, accent 글로우 호버 |
| 네비 링크 | Home, Log, Portfolio — 활성 페이지 accent 언더라인 |
| 🔍 검색 | `Cmd+K` 모달 트리거 |
| 🌙 테마 토글 | Dark ↔ Light 전환 (OS 설정 기본) |
| 👤 프로필 | 비로그인: 로그인 버튼 / 로그인: 드롭다운 (페르소나 설정, 테마 설정, 로그아웃) |

- **데스크탑**: 상단 고정, 로고 + 메뉴 + 검색 아이콘 + 테마 토글, 스크롤 시 배경 blur (`backdrop-filter`)
- **모바일**: 햄버거 메뉴 → 풀스크린 드로어

### Feedback Widget

```
도움이 되었나요?  [👍 12]  [👎 2]
```

- 포스트 최하단 배치, 클릭 시 optimistic update
- 비로그인도 가능 (쿠키로 중복 방지)
- **제출 완료**: "피드백 감사합니다" 토스트
- **모바일**: 스크롤 80% 이상 시 sticky bottom bar로 노출

## Error Handling UI

### Fallback 정책

| 실패 상황 | Fallback |
|---|---|
| 글 목록 로드 실패 | "글을 불러오는 데 실패했습니다" + 다시 시도 |
| 페르소나 전환 실패 | 이전 버전 유지 + 토스트 |
| 댓글 작성 실패 | 텍스트 유지 + 에러 메시지 + 다시 시도 |
| 검색 실패 | "검색에 실패했습니다" + 키워드 검색 폴백 |
| 이미지 로드 실패 | 카테고리별 기본 placeholder |
| Admin AI 실패 | 에러 상세 + "수동으로 작성하기" |

### 에러 UI 원칙

- **사용자 친화적 한국어** — 기술 에러 코드 숨김
- **항상 "다음에 할 수 있는 행동" 함께 제시** — 다시 시도, 대체 경로 등
- **Optimistic Update** — 댓글/좋아요 즉시 반영, 실패 시 롤백

## Related
- [[Design-System]] — 상위 디자인 시스템
- [[Mobile-UX]] — 모바일 컴포넌트 상태
