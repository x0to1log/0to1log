# Frontend Rules

Astro v5 + Tailwind CSS v4 + Vercel. Detailed spec: `docs/04_Frontend_Spec.md`

## Astro

- Keep Astro v5 default output behavior. Use per-page SSR opt-in when needed.
- For dynamic routes such as `[slug].astro`, use `export const prerender = false` when DB-backed rendering is required.
- Do not use `client:load` in `.astro` files. Use plain `<script>` blocks instead.
- Prevent FOUC in `MainLayout.astro` with an early `<script is:inline>`.
- Do not use Astro's built-in i18n routing. Locale structure stays explicit under `/en/` and `/ko/`.

## Tailwind v4

- Use `@tailwindcss/vite`. Do not use `@astrojs/tailwind`.
- Keep theme tokens in `src/styles/global.css` with `@theme` and `[data-theme]` CSS variables.
- Supported themes: `light` (default), `dark`, `pink`.
- Fonts must use the `--font-*` CSS variables defined in `global.css`. Blog sections may load IBM Plex Sans separately.

## i18n

- EN is canonical. `hreflang x-default` points to `/en/`.
- `/portfolio/` and `/admin/` stay locale-neutral.
- Translations live in `src/i18n/index.ts`.

## Naming

- Public product labels: `AI News`, `IT Blog`, `Handbook`, `Library`
- Internal/admin labels: `News`, `Blog`, `Handbook`

## Security

- `/api/revalidate` is server-side only. `REVALIDATE_SECRET` bearer validation is required.
- Never call revalidation directly from client code.
- Never use the Supabase Service Role Key in the frontend. Frontend only uses the anon key.
- CSP is set dynamically in middleware with request nonces. `script-src 'unsafe-inline'` stays removed.
- Every added `<script is:inline>` must include `nonce={Astro.locals.cspNonce || ''}`.
- After any CSP change, verify the rendered HTML, not just source files. Every `<script>` tag must carry the request nonce, including Astro-generated module scripts.
- `style-src 'unsafe-inline'` remains allowed for Astro inline styles and Milkdown.
- Do not expose access tokens into the DOM via `data-*` attributes on admin pages. Use server-side API routes.

## SEO

- `Head.astro` must emit absolute canonical and hreflang URLs based on `PUBLIC_SITE_URL`.
- `astro.config.mjs` `site` must stay aligned with `PUBLIC_SITE_URL`.

## Admin Editor

- Do not use `client:load` in `.astro` files. Use plain `<script>` blocks instead.
- Admin CSS should stay under `.admin-*` selectors in `global.css`.

## Build

```bash
cd frontend && npm run build   # must pass with 0 errors
```
