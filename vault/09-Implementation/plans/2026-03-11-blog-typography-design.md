# IT Blog Typography Design

> Date: 2026-03-11
> Status: Approved

## Goal

Give the IT Blog section its own typeface, distinct from the newsprint serif (Playfair Display + Lora) used across News and Handbook. The blog covers study/career/project content for a mixed audience (developers + non-developers), so the type should feel technical yet approachable.

## Decision

**IBM Plex Sans** (EN) + **IBM Plex Sans KR** (KO), loaded via Google Fonts. Applied to the entire blog section — headings, body, and UI elements. Code blocks remain JetBrains Mono.

### Why IBM Plex Sans

- Single family covers both EN and KR with consistent design language
- Engineered feel ("엔지니어의 블로그") without being cold
- Clear contrast with News section's Playfair Display serif
- Well-supported on Google Fonts with unicode-range splitting for KR

## Font Variables

New blog-only CSS custom properties in `global.css`:

| Variable | Value |
|---|---|
| `--font-blog-heading` | `'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif` |
| `--font-blog-body` | `'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif` |
| `--font-blog-ui` | `'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif` |

Existing variables (`--font-display`, `--font-heading`, `--font-body`, `--font-ui`, `--font-code`) are unchanged.

## Weight Mapping

| Usage | Weight |
|---|---|
| Body text | 400 |
| UI labels, sidebar | 400–500 |
| Card titles, subheadings | 500 |
| Page titles, masthead | 600 |
| Article h1 | 700 |

## Google Fonts Loading

Weights: IBM Plex Sans 400, 400i, 500, 600, 700 + IBM Plex Sans KR 400, 500, 600, 700.

Loaded conditionally in `Head.astro` only when the page URL contains `/blog/`. Uses `display=swap` for FOUT-tolerant loading. News, Handbook, and Admin pages incur no extra font loading.

## Scope of CSS Changes

### Changed

- `.blog-shell` base: `font-family: var(--font-blog-body)`
- `.blog-masthead-title`: `var(--font-blog-heading)`, weight 600
- `.blog-article-title`: `var(--font-blog-heading)`, weight 700
- `.blog-featured-card-title`: `var(--font-blog-heading)`, weight 500
- `.blog-list-item-title`: inherits blog body, weight 500
- `.blog-sidebar-nav`: `var(--font-blog-ui)`
- `.blog-section-header`: `var(--font-blog-ui)` (was `--font-code`)
- `.blog-mono-tag`: `var(--font-blog-ui)` (was `--font-code`)
- `.blog-breadcrumb`: inherits blog body
- `.blog-toc-header`: `var(--font-blog-ui)` (was `--font-code`)
- `.newsprint-prose` headings inside blog: `var(--font-blog-heading)` (was `--font-article-heading`)
- `.newsprint-prose` body inside blog: inherits `var(--font-blog-body)`
- Blog persona switcher: inherits `var(--font-blog-ui)`
- Blog article meta: `var(--font-blog-ui)` (was `--font-code`)
- Blog next-article nav title: `var(--font-blog-heading)` (was `--font-heading`)

### Unchanged

- All News, Handbook, Admin typography
- `@theme` font variables
- Code blocks (`var(--font-code)` / JetBrains Mono)
- Dark/light/pink theme colors
- Drop cap styling (will use blog heading font instead of display)

## Performance

- IBM Plex Sans latin (5 weights): ~120KB
- IBM Plex Sans KR (4 weights): ~1.5MB total, but Google Fonts serves unicode-range splits so actual download is much smaller
- Conditional loading means zero impact on non-blog pages

## Related Plans

- [[plans/2026-03-11-blog-typography-plan|Blog 타이포그래피 구현]]
- [[plans/2026-03-11-blog-kb-design|Blog KB 설계]]
