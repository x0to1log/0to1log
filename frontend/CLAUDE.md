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
- 폰트 역할 분리:
- 현재 스택이 `Georgia`, `"Times New Roman"`, `serif`를 masthead/heading/body/ui 공통으로 사용
- `--font-masthead`: Georgia + Times New Roman + serif
- `--font-heading`: Georgia + Times New Roman + serif
- `--font-article-heading`: Georgia + Times New Roman + serif
- `--font-body`: Georgia + Times New Roman + serif
- `--font-ui`: Georgia + Times New Roman + serif
- `--font-code`: JetBrains Mono

## i18n

- EN canonical. `hreflang x-default` = `/en/`
- `/portfolio/`, `/admin/` → locale 무관 (en/ko 구분 없음)
- 번역 맵 `src/i18n/index.ts`

## 보안

- `/api/revalidate` → server-side only. `REVALIDATE_SECRET` Bearer 검증 필수
- client에서 revalidate 직접 호출 금지
- Supabase Service Role Key를 frontend에서 절대 사용 금지 (anon key만)
- `vercel.json` CSP: `script-src 'self' 'unsafe-inline'` 허용 (초기 FOUC 방지용 → 추후 nonce 방식으로 개선 가능)

## SEO

- `Head.astro`: canonical/hreflang은 반드시 절대 URL (`PUBLIC_SITE_URL` 기준)
- `astro.config.mjs`의 `site`와 `PUBLIC_SITE_URL` 동일값 유지

## Right Rail

- 리스트 페이지 우측 컬럼은 NewsprintListRail.astro를 사용
- 리스트 rail 라벨 고정:
  - 오늘의 편집 노트 / Editor's Note
  - 지금 많이 읽는 글 / Most Read
  - 처음 읽는 분께 / Start Here
- Most Read는 analytics 기반 인기 데이터가 생기기 전까지 latest-published fallback 사용
- 상세 페이지 우측 컬럼은 NewsprintSideRail.astro를 사용
- 상세 rail 라벨 고정:
  - 이 글의 중점 / Focus of This Article
  - 같은 호에서 더 읽기 / More in This Issue
- Focus of This Article는 admin 작성 데이터가 생기기 전까지 category-based template fallback 사용
- 상세 페이지 우측 컬럼은 리스트 rail 라벨을 재사용하지 않음

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
cd frontend && npm run build   # 0 errors 필수
```
