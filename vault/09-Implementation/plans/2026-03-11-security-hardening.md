# Security Hardening (2026-03-11)

Checkpoint note for the March 11 security cleanups.

## Scope

- Remove inline script dependency from CSP where possible
- Stop exposing admin tokens through DOM `data-*` attributes
- Proxy admin site-content updates through server routes
- Add basic rate limiting to password change requests

## Implemented

### 1. CSP nonce alignment

- `frontend/src/middleware.ts`
  - `script-src` now uses per-request nonce instead of `'unsafe-inline'`
- `frontend/src/pages/preview/newsprint-dark.astro`
- `frontend/src/pages/preview/newsprint-light.astro`
- `frontend/src/pages/preview/newsprint-pink.astro`
  - inline theme scripts now receive the CSP nonce

### 2. Remove token leakage from admin DOM

- `frontend/src/pages/admin/settings.astro`
- `frontend/src/pages/admin/edit/[slug].astro`
- `frontend/src/pages/admin/blog/edit/[slug].astro`

Removed `data-access-token` exposure from rendered HTML.

### 3. Server-side site content proxy

- `frontend/src/pages/api/admin/site-content.ts`

New admin-only API route:
- `GET` reads `site_content`
- `POST` upserts one `site_content` row

`admin/settings.astro` now talks to this API instead of directly embedding auth-bearing Supabase client config in the page.

### 4. Password change rate limiting

- `frontend/src/pages/api/admin/change-password.ts`

Added in-memory rate limiting:
- max 5 attempts
- 15 minute window
- returns `429` after limit is exceeded

## Deferred

- admin audit logging
- MFA / step-up auth
- stronger shared rate limiting storage

## Related Plans

- [[plans/2026-03-08-3a-sec-csp-hardening|CSP 하드닝]]
