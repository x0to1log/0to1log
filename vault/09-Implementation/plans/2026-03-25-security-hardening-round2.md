# Security Hardening Round 2

- **날짜**: 2026-03-25
- **목적**: 보안 감사에서 발견된 잔여 취약점 수정
- **범위**: Frontend (logout, robots.txt, vercel.json, Security.md)

## 작업 목록

### A. logout.ts Open Redirect 수정 (높음)
- **파일**: `frontend/src/pages/api/auth/logout.ts`
- **문제**: `redirectTo` 파라미터를 검증 없이 `Location` 헤더에 사용 → 외부 URL로 리다이렉트 가능
- **수정**: `callback.ts`의 `sanitizeRedirect()` 패턴 적용 — `/`로 시작하되 `//` 거부

### B. robots.txt Disallow 추가 (중)
- **파일**: `frontend/public/robots.txt`
- **수정**: `/admin/`, `/api/`, `/auth/`, `/preview/`, `/login`, `/settings`, `/library` Disallow 추가

### C. 보안 헤더 추가 (중)
- **파일**: `frontend/vercel.json`
- **수정**:
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()` 추가
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` 추가

### D. Security.md 문서 현행화 (낮)
- **파일**: `vault/07-Operations/Security.md`
- **수정**: CSP 섹션을 실제 구현(nonce 기반, strict-dynamic)에 맞게 업데이트

## 검증
- [ ] `cd frontend && npm run build` 통과
- [ ] logout redirect 검증: `sanitizeRedirect` 함수가 외부 URL 차단
- [ ] robots.txt에 Disallow 포함 확인
- [ ] vercel.json에 5개 보안 헤더 포함 확인
