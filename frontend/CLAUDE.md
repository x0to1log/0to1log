# Frontend Rules

Astro v5 + Tailwind CSS v4 + Vercel. 상세 스펙 참조 `docs/04_Frontend_Spec.md`

## Astro 규칙

- `output` 설정 없음 (Astro v5 기본 static + per-page SSR opt-in)
- 동적 라우트(`[slug].astro`): 초기(DB 연동 전)에는 `export const prerender = false` 적용
- `.astro` 파일에서 `client:load` 금지 → 바닐라 `<script>` 사용
- FOUC 방지: `MainLayout.astro`의 `<script is:inline>`으로 테마 즉시 적용
- 내장 `i18n` 설정 사용 금지 → 물리 폴더 `/en/`, `/ko/` 방식

## Tailwind v4

- `@tailwindcss/vite` 플러그인 사용 (`@astrojs/tailwind` 금지)
- 커스텀 토큰: `src/styles/global.css`의 `@theme` + `[data-theme]` CSS 변수
- 테마 3개: light (기본), dark, pink
- 폰트: `global.css`에 정의된 `--font-*` CSS 변수 사용. Blog 섹션은 IBM Plex Sans 별도 로딩.

## i18n

- EN canonical. `hreflang x-default` = `/en/`
- `/portfolio/`, `/admin/` → locale 무관 (en/ko 구분 없음)
- 번역 맵 `src/i18n/index.ts`

## Naming

- Public product labels: `AI News`, `IT Blog`, `Handbook`, `Library`
- Internal/admin labels: `News`, `Blog`, `Handbook`

## 보안

- `/api/revalidate` → server-side only. `REVALIDATE_SECRET` Bearer 검증 필수
- client에서 revalidate 직접 호출 금지
- Supabase Service Role Key를 frontend에서 절대 사용 금지 (anon key만)
- CSP는 middleware에서 동적으로 설정 (nonce 기반). `script-src 'unsafe-inline'` 제거 완료.
- 새 `<script is:inline>` 추가 시 반드시 `nonce={Astro.locals.cspNonce || ''}` 속성 포함
- `style-src 'unsafe-inline'`은 유지 (Astro inline styles + Milkdown editor)
- Admin 페이지에서 access token을 `data-*` 속성으로 DOM에 노출 금지. 서버사이드 API 라우트를 통해 프록시.

## SEO

- `Head.astro`: canonical/hreflang은 반드시 절대 URL (`PUBLIC_SITE_URL` 기준)
- `astro.config.mjs`의 `site`와 `PUBLIC_SITE_URL` 동일값 유지

## Admin Editor

- `.astro` 파일에서 `client:load` 금지 → 바닐라 `<script>` 사용
- Admin CSS: `.admin-*` 클래스 네이밍, `global.css`에 정의

## Build

```bash
cd frontend && npm run build   # 0 errors 필수
```
