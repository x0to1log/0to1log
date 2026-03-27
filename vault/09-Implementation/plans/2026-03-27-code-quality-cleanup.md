# Code Quality Cleanup Plan

> B4UShip 보안 스캐너 결과 기반 코드 품질 정리

## Background

B4UShip GitHub 레포 스캔(2026-03-27) 결과: Security Grade C (9 issues, 1 HIGH / 9 MEDIUM / 56 LOW).
실제 조사 후 대부분 false positive 또는 의도적 패턴으로 확인됨.

### Scanner vs Reality

| 스캐너 이슈 | 건수 | 실제 | 비고 |
|-------------|------|------|------|
| Hardcoded localhost URL | 1 HIGH | ❌ false positive | `test_integration.py` 테스트 파일 |
| Empty catch Block | 9 MEDIUM | **2개만 수정 필요** | 나머지 9개는 fire-and-forget / progressive enhancement |
| console.log in Production | 8 LOW | ❌ false positive | 전부 `console.error()` (정상 에러 로깅) |
| Unused Import | 10 LOW | ❌ false positive | 전부 사용 중 |
| TypeScript 'any' | 10 LOW | 리팩터링 수준 | 다음 기회에 |
| Env Var Without Validation | 6 LOW | ❌ false positive | `supabase.ts`에서 이미 falsy 체크 |
| Hardcoded HTTP URLs | 2 LOW | ❌ false positive | XML namespace + http→https 변환 코드 |
| Magic Numbers | 10 LOW | 리팩터링 수준 | 다음 기회에 |
| TODO/FIXME Comments | 10 LOW | 리팩터링 수준 | 다음 기회에 |

### Already Fixed (이번 세션)

- [x] Cookie 'site-locale' Missing Security Flags → `secure: true`, `httpOnly: true` 추가 (7ee5844)
- [x] robots.txt Reveals Sensitive Paths → 무시 (인증으로 보호 중, Disallow 제거 시 인덱싱 위험)

## Tasks

### Task 1: Empty catch block에 에러 로깅 추가

**수정 대상 2개:**

#### 1-1. `frontend/src/pages/api/admin/run-pipeline.ts:41`
- 현재: `catch {}`
- 문제: 어드민 API에서 malformed JSON을 조용히 무시
- 수정: `catch (err) { console.error('[run-pipeline] Invalid request payload:', err); }`

#### 1-2. `frontend/src/pages/api/admin/pipeline-cancel.ts:23`
- 현재: `catch {}`
- 문제: 어드민 API에서 malformed JSON을 조용히 무시
- 수정: `catch (err) { console.error('[pipeline-cancel] Invalid request payload:', err); }`

**의도적 silence (수정 불필요):**
- `middleware.ts:294` — 캐시 파싱 실패 → 재검증으로 fallback
- `middleware.ts:29` — fire-and-forget `touchLastSeen`
- `share.ts:35,96` — `navigator.share()` 취소/실패
- `bulk-action.ts:79`, `status.ts:97`, `handbook/status.ts:99-100` — CDN warm + webhook fire-and-forget
- `bookmark.ts:86`, `likes.ts:70` — progressive enhancement hydration
- `contentFeedback.ts:271` — 피드백 삭제 실패 (retry 가능)

### Task 2: (Optional) TypeScript 'any' 정리

> 다음 스프린트 이후로 연기. 기능 개발 우선.

## Completion Criteria

- [ ] Task 1 완료: 2개 empty catch에 에러 로깅 추가
- [ ] 빌드 통과
- [ ] 커밋: `chore: add error logging to silent admin API catch blocks`
