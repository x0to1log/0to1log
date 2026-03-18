# Admin Security Hardening

- **날짜**: 2026-03-18
- **목적**: 어드민 관련 보안 취약점 수정
- **범위**: Frontend API 라우트, Backend 라우터, Supabase RPC

## 작업 목록

### 1. Supabase 에러 메시지 프론트엔드 노출 제거 (중)
- **파일**: `frontend/src/pages/api/admin/` 하위 전체
- **문제**: `error.message`를 클라이언트에 그대로 반환 → DB 구조 노출 위험
- **수정**: 서버 로그에만 기록, 클라이언트에는 generic 메시지 반환

### 2. Change Password 인메모리 Rate Limiting → Supabase Auth 위임 (중)
- **파일**: `frontend/src/pages/api/admin/change-password.ts`
- **문제**: Vercel 멀티 인스턴스에서 인메모리 Map 무효화
- **수정**: 인메모리 rate limit 제거, Supabase Auth 자체 rate limiting에 의존

### 3. GA4 `days` 파라미터 범위 제한 (낮)
- **파일**: `backend/routers/admin_ga4.py`
- **수정**: `Query(default=30, ge=1, le=365)` 적용

### 4. Cron 엔드포인트 Rate Limiting 추가 (낮)
- **파일**: `backend/routers/cron.py`
- **수정**: slowapi `@limiter.limit()` 추가

### 5. run-pipeline 자체 인증 로직 중복 제거 (참고→수정)
- **파일**: `frontend/src/pages/api/admin/run-pipeline.ts`, `pipeline-cancel.ts`
- **문제**: 미들웨어와 별도로 `requireAdminFromCookies()` 구현 → 유지보수 분기 위험
- **수정**: 미들웨어 보호로 통합, 자체 인증 로직 제거

### 6. increment_product_view_count RPC GRANT 명시 (참고→수정)
- **파일**: 새 마이그레이션 SQL
- **수정**: 명시적 GRANT 추가

## 검증
- [ ] `cd frontend && npm run build` 통과
- [ ] 백엔드 import 에러 없음
