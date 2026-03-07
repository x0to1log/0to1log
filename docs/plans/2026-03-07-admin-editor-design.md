# Admin Editor Design — P2C-UI-14

> Date: 2026-03-07
> Status: Approved
> Sprint: Phase 2C-EXP
> Task: P2C-UI-14 Admin Editor UI

---

## Context

Phase 2C-EXP sprint task P2C-UI-14. Backend API 4 endpoints already implemented (list/get/publish/update). Current `/admin` page is a placeholder. This design covers the editor UI with WYSIWYG markdown editing (Milkdown), Draft/Preview mode switching, and mock data.

---

## Scope

- Milkdown WYSIWYG markdown editor (Typora/Notion style)
- Draft mode: editor + AI suggestion panel (placeholder)
- Preview mode: full-width published page simulation (NewsprintShell + ArticleLayout)
- Save on Preview transition (auto-save)
- Mock data only (real API wiring is P2C-UI-15)
- AI suggestion panel: placeholder only (real AI integration is future task)

---

## User Flow

```
/admin (draft list)
  -> [Edit] -> /admin/edit/[slug] (Draft mode)
                  -> [Preview] (auto-save + switch)
               Preview mode (full published page view)
                  -> [Edit] (back to Draft mode)
                  -> [Publish] (publish action)
```

---

## Draft Mode

```
+------------------------------+------------------+
|  <- Back to Drafts  [Preview]|                   |
+------------------------------+  AI Suggestions   |
|  Title input                 |  (placeholder)    |
|  Category select / Tags      |                   |
|  ----------------------------+  "AI suggestions  |
|  Milkdown WYSIWYG Editor     |   coming soon"    |
|  (live markdown rendering)   |                   |
|                              |                   |
+------------------------------+------------------+
```

- Left (2fr): editable fields + Milkdown editor
- Right (1fr): AI suggestion panel placeholder
- `[Preview]` click: auto-save current content + switch to Preview mode
- Desktop: CSS Grid `2fr 1fr`
- Mobile (<1024px): single column, AI panel collapsed below with toggle

---

## Preview Mode

```
+--------------------------------------------------+
|  [Edit]                                [Publish]  |
+--------------------------------------------------+
|                                                   |
|  Vol. I . No. 1    Builder's Daily    Mar 7, 2026 |
|              From Void to Value                   |
|         AI . Papers . Projects | Daily Curation   |
|  ================================================ |
|                                                   |
|  Category label                                   |
|  Post Title                                       |
|  Tags . Date                                      |
|  ------------------------------------------------ |
|  Body content (prose style)                       |
|                                                   |
+--------------------------------------------------+
```

- Full width, no side panel
- Renders using NewsprintShell + ArticleLayout (identical to `/en/log/[slug]`)
- Masthead, subkicker, divider included — exactly what readers see after publish
- Read-only, no editing
- `[Edit]`: return to Draft mode
- `[Publish]`: publish action (console.log mock for now)

---

## Page Structure

| Route | File | Role |
|-------|------|------|
| `/admin` | `pages/admin/index.astro` | Draft list (improve existing) |
| `/admin/edit/[slug]` | `pages/admin/edit/[slug].astro` | Editor (new, Draft/Preview switch) |

Both pages use `prerender = false` (SSR for auth checks).

---

## Components

| Component | Location | Role |
|-----------|----------|------|
| Admin draft list | `pages/admin/index.astro` inline | Draft list with [Edit] links |
| Admin editor page | `pages/admin/edit/[slug].astro` | Draft/Preview mode container |
| Milkdown editor | vanilla `<script>` in editor page | WYSIWYG markdown editing |

No separate component files needed — keep it simple with inline markup + `<script>` blocks.

---

## Tech Stack

- **Editor**: Milkdown `crepe` preset, initialized via vanilla `<script>`
- **Styles**: `.admin-*` classes in `global.css`, using existing `--color-*` theme variables
- **Preview rendering**: Reuse `.newsprint-*` classes (masthead, subkicker, article, prose)
- **Data**: Hardcoded mock drafts matching `PostDraftDetail` schema
- **Routing**: SSR (`prerender = false`)

---

## CSS Additions (global.css)

```
.admin-toolbar      — top bar (flex, space-between, sticky)
.admin-btn          — base button (border, newsprint tone)
.admin-btn-primary  — publish button (bg-accent)
.admin-split        — left/right grid (2fr 1fr at desktop, 1fr at mobile)
.admin-field        — input field wrapper (label + input)
.admin-input        — text input style (bg-tertiary, border, font)
.admin-select       — select dropdown style
.admin-panel        — AI panel container (bg-secondary, border)
.admin-preview      — preview mode wrapper (full width, max-width matching shell)
```

All colors use existing `--color-*` variables for automatic 3-theme support.

---

## Mock Data

2-3 hardcoded draft objects matching backend `PostDraftDetail` schema:

```
{
  id, title, slug, category, post_type, status: "draft",
  locale, content_original (markdown),
  tags, created_at, updated_at
}
```

- Save: `console.log('saved', data)`
- Publish: `console.log('published', id)`

---

## Mobile (<1024px)

- Draft mode: single column, AI panel below editor (collapsed, toggle)
- Preview mode: full width (same as desktop, responsive newsprint layout)
- Draft/Preview switching works identically

---

## Verification Criteria

- [ ] `npm run build` 0 error
- [ ] `/admin` shows draft list with [Edit] links
- [ ] `/admin/edit/[slug]` renders Milkdown WYSIWYG editor
- [ ] [Preview] auto-saves + shows full newsprint published page view
- [ ] [Edit] returns to Draft mode with content preserved
- [ ] [Publish] button present and clickable
- [ ] Mobile single-column layout works
- [ ] 3 themes (dark/light/pink) render correctly

---

## Documents to Update

| Document | Change |
|----------|--------|
| `docs/04_Frontend_Spec.md` | Update Admin Editor section (SS3-5): WYSIWYG editor (Milkdown), Draft/Preview mode flow, auto-save on Preview, Preview = full published page view |
| `docs/IMPLEMENTATION_PLAN.md` | Update P2C-UI-14 description to reflect WYSIWYG + Draft/Preview flow |
| `docs/plans/ACTIVE_SPRINT.md` | Update P2C-UI-14 task description and mark as `doing` when work starts |
| `frontend/CLAUDE.md` | Add Admin Editor conventions (Milkdown, Draft/Preview pattern, `.admin-*` CSS classes) |

---

## Out of Scope (future tasks)

- Real API integration (P2C-UI-15)
- Auth/error state handling: 401/403/404/loading (P2C-UI-15)
- AI suggestion panel functionality (future)
- Persona tabs (future)
