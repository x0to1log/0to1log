# Frontend Rules

Astro v5 + Tailwind CSS v4 + Vercel. ?ㅽ럺 ?곸꽭 ??`docs/04_Frontend_Spec.md`

## Astro 洹쒖튃

- `output` ?ㅼ젙 ?놁쓬 (Astro v5 湲곕낯 static + per-page SSR opt-in)
- ?숈쟻 ?쇱슦??(`[slug].astro`): 珥덇린(DB ?곕룞 ???먮뒗 `export const prerender = false` ?곸슜
- `.astro` ?뚯씪?먯꽌 `client:load` 湲덉? ??諛붾땺??`<script>` ?ъ슜
- FOUC 諛⑹?: `MainLayout.astro`??`<script is:inline>`?쇰줈 ?뚮쭏 利됱떆 ?곸슜
- ?댁옣 `i18n` ?ㅼ젙 ?ъ슜 湲덉? ??臾쇰━ ?대뜑 `/en/`, `/ko/` 諛⑹떇

## Tailwind v4

- `@tailwindcss/vite` ?뚮윭洹몄씤 ?ъ슜 (`@astrojs/tailwind` 湲덉?)
- ?붿옄???좏겙: `src/styles/global.css`??`@theme` + `[data-theme]` CSS 蹂??
- ?뚮쭏 3媛? dark (湲곕낯), light, pink
- ?고듃 ??븷 遺꾨━:
- ?꾩옱 ?ㅽ뿕媛? `Georgia`, `"Times New Roman"`, `serif`瑜?masthead/heading/body/ui 怨듯넻?쇰줈 ?ъ슜
- `--font-masthead`: Georgia + Times New Roman + serif
- `--font-heading`: Georgia + Times New Roman + serif
- `--font-body`: Georgia + Times New Roman + serif
- `--font-ui`: Georgia + Times New Roman + serif
- `--font-code`: JetBrains Mono

## i18n

- EN canonical. `hreflang x-default` = `/en/`
- `/portfolio/`, `/admin/` ??locale ?낅┰ (en/ko ?묐몢???놁쓬)
- 踰덉뿭 留? `src/i18n/index.ts`

## 蹂댁븞

- `/api/revalidate` ??server-side only. `REVALIDATE_SECRET` Bearer 寃利??꾩닔
- client?먯꽌 revalidate 吏곸젒 ?몄텧 湲덉?
- Supabase Service Role Key瑜?frontend?먯꽌 ?덈? ?ъ슜 湲덉? (anon key留?
- `vercel.json` CSP: `script-src 'self' 'unsafe-inline'` ?덉슜 (珥덇린 FOUC 諛⑹??? 異뷀썑 nonce 諛⑹떇?쇰줈 媛쒖꽑 媛??

## SEO

- `Head.astro`: canonical/hreflang? 諛섎뱶???덈? URL (`PUBLIC_SITE_URL` 湲곕컲)
- `astro.config.mjs`??`site`? `PUBLIC_SITE_URL` ?숈씪媛??좎?

## Right Rail

- 리스트 페이지 우측 컬럼은 NewsprintListRail.astro를 사용
- 리스트 rail 라벨 고정:
  - 오늘의 편집 노트 / Editor's Note
  - 지금 많이 읽는 글 / Most Read
  - 처음 읽는 분께 / Start Here
- Most Read는 analytics 기반 인기 데이터가 생기기 전까지 latest-published fallback 사용
- 상세 페이지 우측 컬럼은 별도 정보 구조를 유지하며, 리스트 rail 라벨을 재사용하지 않음
## Admin Editor

- WYSIWYG editor: Milkdown Crepe preset (`@milkdown/crepe`)
- Initialized via vanilla `<script>` (no `client:load`)
- Draft/Preview mode: Draft = editor + AI panel, Preview = full newsprint published view
- Auto-save on Preview transition
- CSS classes: `.admin-*` in `global.css`
- Mock data until Phase 2D API wiring
- State simulation: `?state=401|403|404|empty` query param on `/admin` and `/admin/edit/[slug]`
- Inline feedback banner: `.admin-feedback` with success/error variants, auto-dismiss 3s

## Build

```bash
cd frontend && npm run build   # 0 errors ?꾩닔
```

