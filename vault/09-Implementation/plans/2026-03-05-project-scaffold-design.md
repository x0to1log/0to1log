# Phase 1a Project Scaffold — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** frontend/ + backend/ 분리 구조의 Astro v5 프로젝트를 처음부터 스캐폴딩하고, 4개 페이지 골격 + 디자인 시스템 + 기본 보안을 구축한다.

**Architecture:** Astro v5 hybrid (SSG 기본 + SSR opt-in) + Tailwind CSS v4 (CSS-first @theme) + 물리적 en/ko 폴더 i18n. Vercel Root Directory = `frontend/`. Supabase/FastAPI는 stub만.

**Tech Stack:** Astro v5, @astrojs/vercel, Tailwind CSS v4, @tailwindcss/vite, motion (v11+), @supabase/supabase-js, TypeScript

---

## Task 1: 루트 설정 파일

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `supabase/.gitkeep`

**Step 1: .gitignore 작성**

```gitignore
# Dependencies
node_modules/

# Build
dist/
.astro/

# Environment
.env
.env.*
!.env.example

# OS
.DS_Store
Thumbs.db

# Python (Phase 2)
__pycache__/
*.py[cod]
.venv/

# IDE
.vscode/settings.json
.idea/

# Temp
.tmp_publish_*/
```

> **주의:** `package-lock.json`은 커밋 대상 — CI 재현성 보장.

**Step 2: .env.example 작성**

```env
# === Frontend (Vercel) ===
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_ANON_KEY=your-anon-key
PUBLIC_SITE_URL=https://0to1log.com
REVALIDATE_SECRET=your-revalidate-secret
CRON_SECRET=your-cron-secret
FASTAPI_URL=https://your-railway-app.railway.app

# === Backend (Railway) — Phase 2 ===
# SUPABASE_URL=
# SUPABASE_SERVICE_KEY=
# OPENAI_API_KEY=
# OPENAI_MODEL_MAIN=gpt-4o
# OPENAI_MODEL_LIGHT=gpt-4o-mini
# TAVILY_API_KEY=
# ADMIN_EMAIL=admin@0to1log.com
```

**Step 3: supabase 플레이스홀더**

```bash
mkdir -p supabase && touch supabase/.gitkeep
```

**Step 4: Commit**

```bash
git add .gitignore .env.example supabase/.gitkeep
git commit -m "chore: add root config files (.gitignore, .env.example, supabase placeholder)"
```

---

## Task 2: Frontend 프로젝트 초기화

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/astro.config.mjs`
- Create: `frontend/.env.example`
- Create: `frontend/vercel.json`

**Step 1: package.json 작성**

```json
{
  "name": "0to1log-frontend",
  "type": "module",
  "version": "0.1.0",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "check": "astro check"
  },
  "dependencies": {
    "astro": "^5.0.0",
    "@astrojs/vercel": "^8.0.0",
    "@astrojs/sitemap": "^3.0.0",
    "@astrojs/mdx": "^4.0.0",
    "@astrojs/check": "^0.9.0",
    "@supabase/supabase-js": "^2.0.0",
    "motion": "^11.0.0"
  },
  "devDependencies": {
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "typescript": "^5.0.0"
  }
}
```

**Step 2: tsconfig.json 작성**

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

**Step 3: astro.config.mjs 작성**

> **CRITICAL:** 내장 `i18n` 설정 사용 금지 — 물리 폴더와 충돌.

```js
import { defineConfig } from 'astro/config';
import vercel from '@astrojs/vercel';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://0to1log.com',
  output: 'hybrid',
  adapter: vercel(),

  integrations: [
    sitemap(),
    mdx(),
  ],

  vite: {
    plugins: [tailwindcss()],
  },

  markdown: {
    shikiConfig: {
      theme: 'css-variables',
    },
  },
});
```

**Step 4: frontend/.env.example 작성**

```env
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_ANON_KEY=your-anon-key
PUBLIC_SITE_URL=https://0to1log.com
REVALIDATE_SECRET=your-revalidate-secret
CRON_SECRET=your-cron-secret
FASTAPI_URL=https://your-railway-app.railway.app
```

**Step 5: vercel.json 작성**

> **CRITICAL:** CSP의 `script-src`에 `'unsafe-inline'` 필수 — FOUC 방지 inline script 동작 보장.
> Phase 1a에서는 GA4/Clarity/AdSense 도메인 제외 (Phase 1b에서 추가).

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' *.supabase.co"
        }
      ]
    }
  ]
}
```

**Step 6: npm install**

```bash
cd frontend
npm install
```

Run: `npm run build`
Expected: 빌드 실패 (페이지 파일 없음) — 정상. 다음 태스크에서 생성.

**Step 7: Commit**

```bash
git add frontend/
git commit -m "chore: initialize Astro v5 frontend project with Tailwind v4, Vercel adapter"
```

---

## Task 3: 디자인 시스템 (global.css)

**Files:**
- Create: `frontend/src/styles/global.css`
- Create: `frontend/public/fonts/.gitkeep`

**Step 1: global.css 작성**

스펙 04 §2-4의 전체 디자인 토큰을 Tailwind v4 CSS-first 방식으로 작성.

```css
@import "tailwindcss";

/* ===========================
   FONT FACES
   =========================== */
@font-face {
  font-family: 'Pretendard';
  src: local('Pretendard');
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: local('JetBrains Mono');
  font-display: swap;
}

/* ===========================
   TAILWIND v4 THEME
   =========================== */
@theme {
  --font-display: 'Clash Display', 'Pretendard', sans-serif;
  --font-body: 'Satoshi', 'Pretendard', sans-serif;
  --font-code: 'JetBrains Mono', 'D2Coding', monospace;

  --breakpoint-mobile: 640px;
  --breakpoint-tablet: 768px;
  --breakpoint-desktop: 1024px;
  --breakpoint-wide: 1280px;
}

/* ===========================
   DARK THEME (Default)
   =========================== */
[data-theme="dark"] {
  --color-bg-primary: #0f0f0f;
  --color-bg-secondary: #1a1a1a;
  --color-bg-tertiary: #242424;
  --color-text-primary: #f5f5f5;
  --color-text-secondary: #a0a0a0;
  --color-text-muted: #666666;
  --color-border: #2a2a2a;
  --color-accent: #ff2d78;
  --color-accent-hover: #ff4d91;
  --color-accent-glow: rgba(255, 45, 120, 0.15);
  --color-accent-subtle: rgba(255, 45, 120, 0.08);
  --color-success: #00d68f;
  --color-warning: #ffaa00;
  --color-error: #ff4d4f;

  /* Shiki — One Dark Pro */
  --shiki-token-keyword: #c678dd;
  --shiki-token-string: #98c379;
  --shiki-token-function: #61afef;
  --shiki-token-comment: #5c6370;
  --shiki-token-constant: #d19a66;
  --shiki-token-punctuation: #abb2bf;
  --shiki-color-text: #abb2bf;
  --shiki-color-background: var(--color-bg-tertiary);
}

/* ===========================
   LIGHT THEME
   =========================== */
[data-theme="light"] {
  --color-bg-primary: #FFFDF9;
  --color-bg-secondary: #F5ECCD;
  --color-bg-tertiary: #FCC8C2;
  --color-text-primary: #2D2024;
  --color-text-secondary: #6B5460;
  --color-text-muted: #A8929C;
  --color-border: #F0DDD5;
  --color-accent: #D94070;
  --color-accent-hover: #E85A88;
  --color-accent-glow: rgba(255, 135, 171, 0.2);
  --color-accent-subtle: rgba(255, 135, 171, 0.12);
  --color-success: #2E8B57;
  --color-warning: #D4940A;
  --color-error: #C53030;

  /* Shiki — GitHub Light */
  --shiki-token-keyword: #d73a49;
  --shiki-token-string: #22863a;
  --shiki-token-function: #6f42c1;
  --shiki-token-comment: #6a737d;
  --shiki-token-constant: #005cc5;
  --shiki-token-punctuation: #24292e;
  --shiki-color-text: #24292e;
  --shiki-color-background: var(--color-bg-tertiary);
}

/* ===========================
   MIDNIGHT THEME
   =========================== */
[data-theme="midnight"] {
  --color-bg-primary: #051923;
  --color-bg-secondary: #003554;
  --color-bg-tertiary: #006494;
  --color-text-primary: #E4F0F6;
  --color-text-secondary: #8ABED0;
  --color-text-muted: #4A7A8F;
  --color-border: #0A4D6E;
  --color-accent: #00A6FB;
  --color-accent-hover: #33B8FC;
  --color-accent-glow: rgba(0, 166, 251, 0.15);
  --color-accent-subtle: rgba(0, 166, 251, 0.08);
  --color-success: #00d68f;
  --color-warning: #ffaa00;
  --color-error: #ff6b6b;

  /* Shiki — Night Owl */
  --shiki-token-keyword: #c792ea;
  --shiki-token-string: #addb67;
  --shiki-token-function: #82aaff;
  --shiki-token-comment: #637777;
  --shiki-token-constant: #f78c6c;
  --shiki-token-punctuation: #d6deeb;
  --shiki-color-text: #d6deeb;
  --shiki-color-background: var(--color-bg-tertiary);
}

/* ===========================
   TYPOGRAPHY SCALE
   =========================== */
.text-display-xl { font-size: 3.5rem; line-height: 1.1; letter-spacing: -0.02em; }
.text-display-lg { font-size: 2.5rem; line-height: 1.2; letter-spacing: -0.015em; }
.text-heading    { font-size: 1.75rem; line-height: 1.3; }
.text-subheading { font-size: 1.25rem; line-height: 1.4; }
.text-body       { font-size: 1rem; line-height: 1.75; }
.text-small      { font-size: 0.875rem; line-height: 1.5; }
.text-code       { font-size: 0.875rem; line-height: 1.6; }

/* ===========================
   FOCUS STYLES (Accessibility)
   =========================== */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 4px;
}

:focus:not(:focus-visible) {
  outline: none;
}

/* ===========================
   REDUCED MOTION
   =========================== */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* ===========================
   BASE STYLES
   =========================== */
html {
  font-family: var(--font-body);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
}

code, pre {
  font-family: var(--font-code);
}
```

**Step 2: 폰트 디렉토리 생성**

```bash
mkdir -p frontend/public/fonts && touch frontend/public/fonts/.gitkeep
```

> 실제 폰트 파일(Pretendard woff2, JetBrains Mono 등)은 별도 다운로드. 스캐폴딩에서는 `local()` fallback만 설정.

**Step 3: Commit**

```bash
git add frontend/src/styles/ frontend/public/fonts/
git commit -m "feat: add design system with 3 themes (dark/light/midnight) and Tailwind v4 tokens"
```

---

## Task 4: 레이아웃 + 공통 컴포넌트

**Files:**
- Create: `frontend/src/components/Head.astro`
- Create: `frontend/src/components/Navigation.astro`
- Create: `frontend/src/components/Footer.astro`
- Create: `frontend/src/components/ThemeToggle.astro`
- Create: `frontend/src/layouts/MainLayout.astro`

**Step 1: Head.astro 작성**

> **CRITICAL:** canonical, hreflang은 반드시 절대 URL (`PUBLIC_SITE_URL` 기반).

```astro
---
interface Props {
  title: string;
  description?: string;
  locale?: 'en' | 'ko';
  slug?: string;
}

const { title, description = '0to1log — AI News & Insights', locale = 'en', slug = '' } = Astro.props;
const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
const canonicalUrl = `${siteUrl}/${locale}/${slug}`.replace(/\/+$/, '/');
const altLocale = locale === 'en' ? 'ko' : 'en';
const altUrl = `${siteUrl}/${altLocale}/${slug}`.replace(/\/+$/, '/');
---

<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} | 0to1log</title>
  <meta name="description" content={description} />

  <!-- Canonical & Hreflang -->
  <link rel="canonical" href={canonicalUrl} />
  <link rel="alternate" hreflang={locale} href={canonicalUrl} />
  <link rel="alternate" hreflang={altLocale} href={altUrl} />
  <link rel="alternate" hreflang="x-default" href={`${siteUrl}/en/`} />

  <!-- Open Graph -->
  <meta property="og:title" content={`${title} | 0to1log`} />
  <meta property="og:description" content={description} />
  <meta property="og:url" content={canonicalUrl} />
  <meta property="og:type" content="website" />
  <meta property="og:locale" content={locale === 'ko' ? 'ko_KR' : 'en_US'} />

  <!-- Styles -->
  <link rel="stylesheet" href="/src/styles/global.css" />
</head>
```

**Step 2: Navigation.astro 작성**

```astro
---
interface Props {
  locale?: 'en' | 'ko';
}

const { locale = 'en' } = Astro.props;
const altLocale = locale === 'en' ? 'ko' : 'en';
const currentPath = Astro.url.pathname;
const altPath = currentPath.replace(`/${locale}/`, `/${altLocale}/`);
---

<header style={`background-color: var(--color-bg-secondary); border-bottom: 1px solid var(--color-border);`}>
  <nav style={`max-width: 1280px; margin: 0 auto; padding: 1rem; display: flex; align-items: center; justify-content: space-between;`}>
    <a href={`/${locale}/`} style={`font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: var(--color-accent); text-decoration: none;`}>
      0to1log
    </a>

    <div style="display: flex; align-items: center; gap: 1.5rem;">
      <a href={`/${locale}/log/`} style={`color: var(--color-text-secondary); text-decoration: none;`}>Log</a>
      <a href="/portfolio/" style={`color: var(--color-text-secondary); text-decoration: none;`}>Portfolio</a>
      <a href={altPath} style={`color: var(--color-text-muted); text-decoration: none; font-size: 0.875rem;`}>
        {locale === 'en' ? '한국어' : 'EN'}
      </a>
      <div id="theme-toggle-slot"></div>
    </div>
  </nav>
</header>
```

**Step 3: Footer.astro 작성**

```astro
---
const year = new Date().getFullYear();
---

<footer style={`background-color: var(--color-bg-secondary); border-top: 1px solid var(--color-border); padding: 2rem; text-align: center;`}>
  <p style={`color: var(--color-text-muted); font-size: 0.875rem;`}>
    &copy; {year} 0to1log. All rights reserved.
  </p>
</footer>
```

**Step 4: ThemeToggle.astro 작성**

> **CRITICAL:** `client:load` 사용 금지. 바닐라 `<script>` 태그로 구현.

```astro
<button
  id="theme-toggle"
  aria-label="Toggle theme"
  style={`background: none; border: 1px solid var(--color-border); border-radius: 8px; padding: 0.5rem; cursor: pointer; color: var(--color-text-secondary); font-size: 0.875rem;`}
>
  <span id="theme-icon">🌙</span>
</button>

<script>
  const themes = ['dark', 'light', 'midnight'] as const;
  const icons: Record<string, string> = { dark: '🌙', light: '☀️', midnight: '🌊' };

  function getTheme(): string {
    return localStorage.getItem('theme') || 'dark';
  }

  function setTheme(theme: string): void {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    const iconEl = document.getElementById('theme-icon');
    if (iconEl) iconEl.textContent = icons[theme] || '🌙';
  }

  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    const current = getTheme();
    const idx = themes.indexOf(current as typeof themes[number]);
    const next = themes[(idx + 1) % themes.length];
    setTheme(next);
  });

  // Set icon on load
  const iconEl = document.getElementById('theme-icon');
  if (iconEl) iconEl.textContent = icons[getTheme()] || '🌙';
</script>
```

**Step 5: MainLayout.astro 작성**

> **CRITICAL:** `<script is:inline>` 으로 FOUC 방지 — CSP에 `'unsafe-inline'` 필수.

```astro
---
import Head from '../components/Head.astro';
import Navigation from '../components/Navigation.astro';
import Footer from '../components/Footer.astro';
import ThemeToggle from '../components/ThemeToggle.astro';
import { ViewTransitions } from 'astro:transitions';

interface Props {
  title: string;
  description?: string;
  locale?: 'en' | 'ko';
  slug?: string;
}

const { title, description, locale = 'en', slug } = Astro.props;
---

<!doctype html>
<html lang={locale} data-theme="dark">
  <Head title={title} description={description} locale={locale} slug={slug} />

  <!-- FOUC Prevention: must run before paint -->
  <script is:inline>
    (function() {
      var stored = localStorage.getItem('theme');
      if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
      } else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
        document.documentElement.setAttribute('data-theme', 'light');
      }
    })();
  </script>

  <ViewTransitions />

  <body style={`min-height: 100vh; display: flex; flex-direction: column; background-color: var(--color-bg-primary); color: var(--color-text-primary); margin: 0;`}>
    <!-- Skip Navigation -->
    <a href="#main-content" class="sr-only" style={`position: absolute; top: -100%; left: 0; background: var(--color-accent); color: white; padding: 0.5rem 1rem; z-index: 9999;`}>
      Skip to content
    </a>

    <Navigation locale={locale} />

    <main id="main-content" style={`flex: 1; max-width: 1280px; margin: 0 auto; padding: 2rem 1rem; width: 100%;`}>
      <slot />
    </main>

    <Footer />
    <ThemeToggle />
  </body>
</html>
```

**Step 6: Commit**

```bash
git add frontend/src/components/ frontend/src/layouts/
git commit -m "feat: add MainLayout, Head, Navigation, Footer, ThemeToggle components"
```

---

## Task 5: i18n 유틸리티 + 데이터 레이어 stubs

**Files:**
- Create: `frontend/src/i18n/index.ts`
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/lib/api.ts`

**Step 1: i18n/index.ts 작성**

```ts
export type Locale = 'en' | 'ko';

export const defaultLocale: Locale = 'en';
export const locales: Locale[] = ['en', 'ko'];

export function getLocaleFromPath(path: string): Locale {
  const match = path.match(/^\/(en|ko)\//);
  return (match?.[1] as Locale) || defaultLocale;
}

export const t: Record<Locale, Record<string, string>> = {
  en: {
    'nav.log': 'Log',
    'nav.portfolio': 'Portfolio',
    'home.title': 'AI News & Insights',
    'home.subtitle': 'From Zero to One, Every Day',
    'log.title': 'Log',
    'log.empty': 'No posts yet. Check back soon!',
    'post.back': 'Back to Log',
  },
  ko: {
    'nav.log': '로그',
    'nav.portfolio': '포트폴리오',
    'home.title': 'AI 뉴스 & 인사이트',
    'home.subtitle': '매일, 제로에서 원으로',
    'log.title': '로그',
    'log.empty': '아직 포스트가 없습니다. 곧 돌아올게요!',
    'post.back': '로그로 돌아가기',
  },
};
```

**Step 2: lib/supabase.ts 작성**

```ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
const supabaseKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;

export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null;
```

**Step 3: lib/api.ts 작성**

```ts
const FASTAPI_URL = import.meta.env.FASTAPI_URL || '';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${FASTAPI_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}
```

**Step 4: Commit**

```bash
git add frontend/src/i18n/ frontend/src/lib/
git commit -m "feat: add i18n utility, Supabase client stub, API wrapper stub"
```

---

## Task 6: 페이지 스켈레톤 (9개)

**Files:**
- Create: `frontend/src/pages/index.astro`
- Create: `frontend/src/pages/en/index.astro`
- Create: `frontend/src/pages/ko/index.astro`
- Create: `frontend/src/pages/en/log/index.astro`
- Create: `frontend/src/pages/en/log/[slug].astro`
- Create: `frontend/src/pages/ko/log/index.astro`
- Create: `frontend/src/pages/ko/log/[slug].astro`
- Create: `frontend/src/pages/portfolio/index.astro`
- Create: `frontend/src/pages/admin/index.astro`

**Step 1: / 리다이렉트 (SSR)**

`frontend/src/pages/index.astro`:

```astro
---
export const prerender = false;
return Astro.redirect('/en/', 307);
---
```

**Step 2: EN Home (SSR)**

`frontend/src/pages/en/index.astro`:

```astro
---
export const prerender = false;
import MainLayout from '../../layouts/MainLayout.astro';
import { t } from '../../i18n/index';
---

<MainLayout title={t.en['home.title']} locale="en">
  <section style="text-align: center; padding: 4rem 0;">
    <h1 class="text-display-xl" style={`font-family: var(--font-display); color: var(--color-accent);`}>
      0to1log
    </h1>
    <p class="text-subheading" style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
      {t.en['home.subtitle']}
    </p>
  </section>
</MainLayout>
```

**Step 3: KO Home (SSR)**

`frontend/src/pages/ko/index.astro`:

```astro
---
export const prerender = false;
import MainLayout from '../../layouts/MainLayout.astro';
import { t } from '../../i18n/index';
---

<MainLayout title={t.ko['home.title']} locale="ko">
  <section style="text-align: center; padding: 4rem 0;">
    <h1 class="text-display-xl" style={`font-family: var(--font-display); color: var(--color-accent);`}>
      0to1log
    </h1>
    <p class="text-subheading" style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
      {t.ko['home.subtitle']}
    </p>
  </section>
</MainLayout>
```

**Step 4: EN Log 목록 (SSR)**

`frontend/src/pages/en/log/index.astro`:

```astro
---
export const prerender = false;
import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
---

<MainLayout title={t.en['log.title']} locale="en" slug="log/">
  <h1 class="text-heading">{t.en['log.title']}</h1>
  <p style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
    {t.en['log.empty']}
  </p>
</MainLayout>
```

**Step 5: EN Log 상세 (SSR)**

> **CRITICAL:** `prerender = false` 필수. 빈 `getStaticPaths`는 404 유발.

`frontend/src/pages/en/log/[slug].astro`:

```astro
---
export const prerender = false;
import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';

const { slug } = Astro.params;
---

<MainLayout title={slug || 'Post'} locale="en" slug={`log/${slug}/`}>
  <a href="/en/log/" style={`color: var(--color-accent); text-decoration: none;`}>
    &larr; {t.en['post.back']}
  </a>
  <article style="margin-top: 2rem;">
    <h1 class="text-heading">{slug}</h1>
    <p style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
      Post content will be loaded from Supabase (P1-FE-02).
    </p>
  </article>
</MainLayout>
```

**Step 6: KO Log 목록 + 상세 (SSR)**

`frontend/src/pages/ko/log/index.astro`: EN과 동일 구조, `locale="ko"`, `t.ko` 사용.

`frontend/src/pages/ko/log/[slug].astro`: EN과 동일 구조, `locale="ko"`, `t.ko` 사용.

**Step 7: Portfolio (SSG)**

`frontend/src/pages/portfolio/index.astro`:

```astro
---
import MainLayout from '../../layouts/MainLayout.astro';
---

<MainLayout title="Portfolio" locale="en">
  <h1 class="text-heading">Portfolio</h1>
  <p style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
    Projects coming soon.
  </p>
</MainLayout>
```

**Step 8: Admin (SSR)**

`frontend/src/pages/admin/index.astro`:

```astro
---
export const prerender = false;
import MainLayout from '../../layouts/MainLayout.astro';
---

<MainLayout title="Admin" locale="en">
  <h1 class="text-heading">Admin Dashboard</h1>
  <p style={`color: var(--color-text-secondary); margin-top: 1rem;`}>
    Authentication required. (Phase 1a P1-DB-01)
  </p>
</MainLayout>
```

**Step 9: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: add 9 page skeletons (Home EN/KO, Log list/detail, Portfolio, Admin)"
```

---

## Task 7: API Revalidate Endpoint

**Files:**
- Create: `frontend/src/pages/api/revalidate.ts`

**Step 1: revalidate.ts 작성**

> **CRITICAL:** Stub만 — secret 검증 후 401 또는 200. client direct call 금지, server-side only.

```ts
import type { APIRoute } from 'astro';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  const authHeader = request.headers.get('authorization');
  const secret = import.meta.env.REVALIDATE_SECRET;

  if (!secret || authHeader !== `Bearer ${secret}`) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ revalidated: true }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
```

**Step 2: Commit**

```bash
git add frontend/src/pages/api/
git commit -m "feat: add /api/revalidate stub endpoint with REVALIDATE_SECRET validation"
```

---

## Task 8: 빌드 검증 + 라우트 테스트

**Step 1: 빌드 실행**

```bash
cd frontend
npm run build
```

Expected: 0 errors, 0 warnings

**Step 2: Dev 서버 라우트 확인**

```bash
npm run dev
```

브라우저에서 확인:
- `http://localhost:4321/` → `/en/`으로 307 리다이렉트
- `http://localhost:4321/en/` → EN Home 표시
- `http://localhost:4321/ko/` → KO Home 표시
- `http://localhost:4321/en/log/` → EN Log 목록
- `http://localhost:4321/ko/log/` → KO Log 목록
- `http://localhost:4321/en/log/test-slug` → EN Post detail
- `http://localhost:4321/portfolio/` → Portfolio
- `http://localhost:4321/admin/` → Admin

**Step 3: 테마 토글 검증**

- 테마 토글 클릭 → dark → light → midnight 순환
- 페이지 새로고침 → 선택한 테마 유지 (FOUC 없음)
- `prefers-color-scheme: light` 시스템 설정 → 최초 방문 시 light 자동 적용

**Step 4: Revalidate 검증**

```bash
# 잘못된 secret → 401
curl -X POST http://localhost:4321/api/revalidate \
  -H "Authorization: Bearer wrong-secret" \
  -H "Content-Type: application/json"

# 올바른 secret → 200 (REVALIDATE_SECRET env 설정 필요)
curl -X POST http://localhost:4321/api/revalidate \
  -H "Authorization: Bearer your-revalidate-secret" \
  -H "Content-Type: application/json"
```

**Step 5: Reduced motion 검증**

Chrome DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce` → 모든 애니메이션 비활성화 확인

**Step 6: 최종 Commit**

```bash
git add -A
git commit -m "chore: Phase 1a scaffold complete — P1-BOOT-01/02 + P1-FE-01"
```

---

## ACTIVE_SPRINT.md 업데이트

빌드 검증 통과 후 ACTIVE_SPRINT.md에서:
- P1-BOOT-01 → `상태: done`, `체크: [x]`
- P1-BOOT-02 → `상태: done`, `체크: [x]` (Supabase 프로젝트는 수동 생성 확인 후)
- P1-FE-01 → `상태: done`, `체크: [x]`
- Current Doing 슬롯 → `-` (비움)
