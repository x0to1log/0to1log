# Admin UI Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign admin UI from a crude dashboard into a Notion/Linear-style editor-centric interface with sidebar navigation (dashboard) and focused editor layout (edit pages).

**Architecture:** Two distinct layouts — (1) Dashboard pages use 3-column grid: sidebar + main list + stats panel; (2) Editor pages use 2-column layout: editor area + collapsible AI panel, no sidebar. All styling uses existing theme CSS variables from `global.css`.

**Tech Stack:** Astro v5, Tailwind CSS v4, vanilla `<script>`, existing Milkdown Crepe editor, Supabase.

---

### Task 1: Create AdminSidebar Component

**Files:**
- Create: `frontend/src/components/admin/AdminSidebar.astro`

**Step 1: Create the sidebar component**

```astro
---
interface Props {
  activeSection?: 'posts' | 'handbook';
  recentPosts?: Array<{ title: string; slug: string; type: 'post' | 'term' }>;
  stats?: { posts: number; terms: number; drafts: number };
}

const { activeSection = 'posts', recentPosts = [], stats } = Astro.props;
const currentPath = Astro.url.pathname;
---

<aside class="admin-sidebar">
  <div class="admin-sidebar-brand">
    <span class="admin-sidebar-logo">0→1</span>
    <span class="admin-sidebar-label">Admin</span>
  </div>

  <nav class="admin-sidebar-nav">
    <a href="/admin/" class:list={['admin-sidebar-link', { 'admin-sidebar-link--active': activeSection === 'posts' }]}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M2 3h12M2 7h8M2 11h10" />
      </svg>
      Posts
    </a>
    <a href="/admin/handbook/" class:list={['admin-sidebar-link', { 'admin-sidebar-link--active': activeSection === 'handbook' }]}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 2h10v12H3zM6 2v12" />
      </svg>
      Handbook
    </a>
  </nav>

  {recentPosts.length > 0 && (
    <div class="admin-sidebar-section">
      <div class="admin-sidebar-section-title">Recent</div>
      <ul class="admin-sidebar-recent">
        {recentPosts.slice(0, 5).map((item) => (
          <li>
            <a href={item.type === 'post' ? `/admin/edit/${item.slug}` : `/admin/handbook/edit/${item.slug}`} class="admin-sidebar-recent-link">
              <span class="admin-sidebar-recent-type">{item.type === 'post' ? 'P' : 'H'}</span>
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )}

  {stats && (
    <div class="admin-sidebar-section">
      <div class="admin-sidebar-section-title">Stats</div>
      <div class="admin-sidebar-stats">
        <div class="admin-sidebar-stat">
          <span class="admin-sidebar-stat-value">{stats.posts}</span>
          <span class="admin-sidebar-stat-label">Posts</span>
        </div>
        <div class="admin-sidebar-stat">
          <span class="admin-sidebar-stat-value">{stats.terms}</span>
          <span class="admin-sidebar-stat-label">Terms</span>
        </div>
        <div class="admin-sidebar-stat">
          <span class="admin-sidebar-stat-value">{stats.drafts}</span>
          <span class="admin-sidebar-stat-label">Drafts</span>
        </div>
      </div>
    </div>
  )}

  <div class="admin-sidebar-footer">
    <a href="/en/" class="admin-sidebar-link" target="_blank">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M6 3H3v10h10v-3M9 2h5v5M14 2L7 9" />
      </svg>
      View Site
    </a>
    <form method="POST" action={`/api/auth/logout?redirectTo=${encodeURIComponent(currentPath)}`}>
      <button type="submit" class="admin-sidebar-link admin-sidebar-link--button">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M6 2H3v12h3M11 5l3 3-3 3M6 8h8" />
        </svg>
        Logout
      </button>
    </form>
  </div>
</aside>
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/components/admin/AdminSidebar.astro
git commit -m "feat: add AdminSidebar component for redesigned admin layout"
```

---

### Task 2: Replace Admin CSS — New Design System

**Files:**
- Modify: `frontend/src/styles/global.css` (lines 1064–1647, all `.admin-*` classes)

Replace the entire admin CSS block (lines 1064 to end-of-admin-section) with the new design system. The new CSS covers:

**Step 1: Replace all `.admin-*` CSS with new design system**

Delete everything from line 1064 (`.admin-toolbar`) through the last `.admin-filter-btn--active` rule (~line 1647), then insert the following:

```css
/* ===========================
   ADMIN — Sidebar
   =========================== */
.admin-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 220px;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: 1.25rem 0;
  z-index: 40;
  font-family: var(--font-ui);
  font-size: 0.85rem;
}

.admin-sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1.25rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0.75rem;
}

.admin-sidebar-logo {
  font-family: var(--font-masthead);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-accent);
}

.admin-sidebar-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.admin-sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0 0.75rem;
  margin-bottom: 1rem;
}

.admin-sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.5rem;
  border-radius: 6px;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: background 150ms ease, color 150ms ease;
}

.admin-sidebar-link:hover {
  background: var(--color-accent-subtle);
  color: var(--color-text-primary);
}

.admin-sidebar-link--active {
  background: var(--color-accent-subtle);
  color: var(--color-text-primary);
  font-weight: 600;
}

.admin-sidebar-link--button {
  width: 100%;
  border: none;
  background: none;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.admin-sidebar-section {
  padding: 0 1.25rem;
  margin-bottom: 1rem;
}

.admin-sidebar-section-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.admin-sidebar-recent {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.admin-sidebar-recent-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.8rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-sidebar-recent-link:hover {
  color: var(--color-text-primary);
}

.admin-sidebar-recent-type {
  font-size: 0.65rem;
  font-weight: 600;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: var(--color-accent-subtle);
  color: var(--color-accent);
  flex-shrink: 0;
}

.admin-sidebar-stats {
  display: flex;
  gap: 1rem;
}

.admin-sidebar-stat {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.admin-sidebar-stat-value {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.admin-sidebar-stat-label {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.admin-sidebar-footer {
  margin-top: auto;
  padding: 0 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

/* ===========================
   ADMIN — Dashboard Layout
   =========================== */
.admin-dashboard {
  margin-left: 220px;
  display: grid;
  grid-template-columns: 1fr 260px;
  min-height: 100vh;
}

.admin-main {
  padding: 2rem 2.5rem;
  max-width: 900px;
}

.admin-main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.admin-main-title {
  font-family: var(--font-heading);
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
}

.admin-right-panel {
  padding: 2rem 1.5rem;
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.admin-right-panel-section {
  margin-bottom: 2rem;
}

.admin-right-panel-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin-bottom: 0.75rem;
  font-family: var(--font-ui);
}

.admin-stat-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.admin-stat-card {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-primary);
}

.admin-stat-card-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.admin-stat-card-value {
  font-family: var(--font-heading);
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0.25rem 0;
}

.admin-stat-card-detail {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* ===========================
   ADMIN — List Table
   =========================== */
.admin-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.admin-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 0;
  border-bottom: 1px solid var(--color-border);
  gap: 1rem;
}

.admin-list-item:last-child {
  border-bottom: none;
}

.admin-list-info {
  flex: 1;
  min-width: 0;
}

.admin-list-title {
  font-family: var(--font-heading);
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
}

.admin-list-title a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.admin-list-title a:hover {
  color: var(--color-accent);
}

.admin-list-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-family: var(--font-ui);
}

.admin-list-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-shrink: 0;
}

/* ===========================
   ADMIN — Editor Layout (no sidebar)
   =========================== */
.admin-editor-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  min-height: 100vh;
  transition: grid-template-columns 150ms ease;
}

.admin-editor-layout--collapsed {
  grid-template-columns: 1fr 0;
}

.admin-editor-topbar {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  position: sticky;
  top: 0;
  z-index: 30;
}

.admin-editor-topbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.admin-editor-topbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-editor-back {
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  font-family: var(--font-ui);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  transition: color 150ms ease;
}

.admin-editor-back:hover {
  color: var(--color-text-primary);
}

.admin-editor-title {
  font-family: var(--font-heading);
  font-size: 1.75rem;
  font-weight: 700;
  border: none;
  background: none;
  color: var(--color-text-primary);
  outline: none;
  width: 100%;
  padding: 0.25rem 0;
}

.admin-editor-title::placeholder {
  color: var(--color-text-muted);
}

.admin-editor-content {
  padding: 1.5rem 2.5rem;
  overflow-y: auto;
}

.admin-editor-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

/* ===========================
   ADMIN — AI Panel (right side of editor)
   =========================== */
.admin-ai-panel {
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  padding: 1.5rem;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 150ms ease, padding 150ms ease, opacity 150ms ease;
}

.admin-editor-layout--collapsed .admin-ai-panel {
  padding: 0;
  opacity: 0;
  overflow: hidden;
}

.admin-ai-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.admin-ai-panel-title {
  font-family: var(--font-heading);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.admin-ai-panel-toggle {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: color 150ms ease;
}

.admin-ai-panel-toggle:hover {
  color: var(--color-text-primary);
}

.admin-ai-panel-placeholder {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

/* ===========================
   ADMIN — Shared Components
   =========================== */

/* Buttons */
.admin-btn {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.admin-btn:hover {
  background: var(--color-accent-subtle);
  border-color: var(--color-accent);
}

.admin-btn-primary {
  background: var(--color-accent);
  color: var(--color-bg-primary);
  border-color: var(--color-accent);
  font-weight: 600;
}

.admin-btn-primary:hover {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.admin-btn-danger {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-error);
  border-radius: 6px;
  background: transparent;
  color: var(--color-error);
  cursor: pointer;
  transition: background 150ms ease;
}

.admin-btn-danger:hover {
  background: rgba(168, 82, 75, 0.1);
}

/* Status Badge */
.admin-status-badge {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.admin-status-badge--draft {
  background: var(--color-accent-subtle);
  color: var(--color-text-muted);
}

.admin-status-badge--published {
  background: rgba(90, 142, 93, 0.15);
  color: var(--color-success);
}

.admin-status-badge--archived {
  background: var(--color-accent-subtle);
  color: var(--color-text-muted);
  opacity: 0.6;
}

/* Filter Tabs */
.admin-filter-tabs {
  display: flex;
  gap: 0.25rem;
  font-family: var(--font-ui);
}

.admin-filter-btn {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  padding: 0.35rem 0.75rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.admin-filter-btn:hover {
  background: var(--color-accent-subtle);
  color: var(--color-text-primary);
}

.admin-filter-btn--active {
  background: var(--color-accent-subtle);
  color: var(--color-text-primary);
  font-weight: 600;
}

/* Nav Tabs */
.admin-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 1.5rem;
  font-family: var(--font-ui);
}

.admin-tab {
  padding: 0.6rem 1.25rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 150ms ease, border-color 150ms ease;
}

.admin-tab:hover {
  color: var(--color-text-primary);
}

.admin-tab--active {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-accent);
  font-weight: 600;
}

/* Form Fields */
.admin-field {
  margin-bottom: 0.75rem;
}

.admin-field label {
  display: block;
  font-family: var(--font-ui);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 0.35rem;
}

.admin-input,
.admin-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-family: var(--font-body);
  font-size: 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 150ms ease;
}

.admin-input:focus,
.admin-select:focus {
  outline: none;
  border-color: var(--color-accent);
}

.admin-textarea {
  width: 100%;
  padding: 0.75rem;
  font-family: var(--font-body);
  font-size: 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  resize: vertical;
  line-height: 1.6;
  transition: border-color 150ms ease;
}

.admin-textarea:focus {
  outline: none;
  border-color: var(--color-accent);
}

/* Editor Wrapper */
.admin-editor-wrapper {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  min-height: 500px;
  overflow: hidden;
}

.admin-editor-wrapper .milkdown {
  --crepe-color-background: var(--color-bg-primary) !important;
  --crepe-color-surface: var(--color-bg-secondary) !important;
  --crepe-color-on-background: var(--color-text-primary) !important;
  --crepe-color-on-surface: var(--color-text-primary) !important;
  --crepe-color-primary: var(--color-accent) !important;
  --crepe-color-outline: var(--color-border) !important;
  --crepe-color-secondary: var(--color-bg-tertiary) !important;
  --crepe-color-on-secondary: var(--color-text-primary) !important;
  font-family: var(--font-body) !important;
  padding: 1.5rem;
}

/* Feedback Toast */
.admin-feedback {
  padding: 0.6rem 1rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.admin-feedback--toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 100;
  box-shadow: 0 4px 12px var(--color-shadow);
  min-width: 250px;
}

.admin-feedback--success {
  background: rgba(90, 142, 93, 0.15);
  border: 1px solid var(--color-success);
  color: var(--color-success);
}

.admin-feedback--error {
  background: rgba(168, 82, 75, 0.15);
  border: 1px solid var(--color-error);
  color: var(--color-error);
}

.admin-feedback-dismiss {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0 0.25rem;
  opacity: 0.7;
}

.admin-feedback-dismiss:hover {
  opacity: 1;
}

.admin-feedback[hidden] {
  display: none;
}

/* Collapsible Details */
.admin-details {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 0.75rem;
}

.admin-details summary {
  padding: 0.75rem 1rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-details summary::-webkit-details-marker { display: none; }
.admin-details summary::before {
  content: '\25B6';
  font-size: 0.6rem;
  transition: transform 150ms ease;
}

.admin-details[open] summary::before { transform: rotate(90deg); }

.admin-details-body {
  padding: 0 1rem 1rem;
}

/* Checkbox Field */
.admin-field--checkbox label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  color: var(--color-text-primary);
  cursor: pointer;
}

.admin-field--checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--color-accent);
}

/* Category Grid (checkbox group) */
.admin-category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.5rem;
}

.admin-category-check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.admin-category-check input[type="checkbox"] {
  accent-color: var(--color-accent);
}

/* Language Tabs */
.admin-lang-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 1rem;
}

.admin-lang-tab {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.admin-lang-tab:first-child {
  border-radius: 6px 0 0 6px;
}

.admin-lang-tab:last-child {
  border-radius: 0 6px 6px 0;
  border-left: none;
}

.admin-lang-tab--active {
  background: var(--color-accent-subtle);
  color: var(--color-text-primary);
  font-weight: 600;
}

/* Preview Bar (editor preview mode) */
.admin-preview-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  position: sticky;
  top: 0;
  z-index: 30;
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: replace admin CSS with Notion/Linear-style design system"
```

---

### Task 3: Redesign Dashboard Posts Page (`/admin/index.astro`)

**Files:**
- Modify: `frontend/src/pages/admin/index.astro`

**Step 1: Rewrite the dashboard page with 3-column layout**

Replace the entire file. Key changes:
- Remove `AdminHeader` import, add `AdminSidebar` import
- Add recent items query (5 most recent across posts + terms)
- Use `admin-dashboard` grid with sidebar, main list, right stats panel
- Replace inline styles with new CSS classes
- Replace `<ul class="admin-draft-list">` with `<ul class="admin-list">`
- Replace `<li class="admin-term-item">` with `<li class="admin-list-item">`
- Add `+ New Post` button in main header area
- Move stats to right panel with `admin-stat-card` components
- Keep existing `<script>` logic (filter, quick actions) — only update class selectors

The template structure should be:

```astro
<MainLayout title="Admin Dashboard" locale="en">
  <AdminSidebar activeSection="posts" recentPosts={recentItems} stats={{ posts: logTotal, terms: handbookTotal, drafts: logDraft + handbookDraft }} />

  <div class="admin-dashboard">
    <div class="admin-main">
      <div class="admin-main-header">
        <h1 class="admin-main-title">Posts</h1>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <div class="admin-filter-tabs">...</div>
        </div>
      </div>

      {/* Post list using .admin-list / .admin-list-item */}
      <ul class="admin-list" id="post-list">
        {allPosts.map((post) => (
          <li class="admin-list-item" data-status={post.status}>
            <div class="admin-list-info">
              <div class="admin-list-title"><a href={...}>{post.title}</a></div>
              <div class="admin-list-meta">
                <span class={`admin-status-badge admin-status-badge--${post.status}`}>{post.status}</span>
                {post.category && <span>{post.category}</span>}
                <span>{date}</span>
              </div>
            </div>
            <div class="admin-list-actions">
              {/* publish/unpublish/edit/delete buttons */}
            </div>
          </li>
        ))}
      </ul>
    </div>

    <div class="admin-right-panel">
      {/* stat cards + recent activity */}
    </div>
  </div>
</MainLayout>
```

Server-side frontmatter additions:
- Query 5 most recent items (posts + handbook terms combined, sorted by `updated_at`)
- Build `recentItems` array: `{ title, slug, type: 'post' | 'term' }`

**Step 2: Update script selectors**

In the `<script>` block, update selectors:
- `#post-list [data-status]` stays the same
- `[data-filter]` stays the same
- `[data-action]` stays the same

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat: redesign admin dashboard with sidebar + 3-column layout"
```

---

### Task 4: Redesign Handbook List Page (`/admin/handbook/index.astro`)

**Files:**
- Modify: `frontend/src/pages/admin/handbook/index.astro`

**Step 1: Apply same 3-column layout as posts dashboard**

Same pattern as Task 3:
- Replace `AdminHeader` → `AdminSidebar` with `activeSection="handbook"`
- Use `admin-dashboard` / `admin-main` / `admin-right-panel` layout
- Replace list markup with `admin-list` / `admin-list-item`
- Add `+ New Term` button in header
- Move stats to right panel
- Query recent items for sidebar
- Keep existing `<script>` filter + action logic

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/handbook/index.astro
git commit -m "feat: redesign admin handbook list with sidebar + 3-column layout"
```

---

### Task 5: Redesign Post Editor Page (`/admin/edit/[slug].astro`)

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

**Step 1: Replace editor HTML with new layout**

Key changes to the template (Draft Mode section only — keep all server-side logic and `<script>` block intact):

- Remove `admin-toolbar` / `admin-split` structure
- Add `admin-editor-layout` grid wrapper
- Add `admin-editor-topbar` with: back link, title input (Notion-style), Save + Publish buttons, AI panel toggle
- Editor area: `admin-editor-content` with inline meta pills (category select, tags input) + Milkdown editor
- AI panel: `admin-ai-panel` on right side with toggle to collapse
- Title field: change from `<input>` in a field to `<input class="admin-editor-title">` directly in topbar area or below topbar

Template structure:

```html
<div class="admin-editor-layout" id="draft-mode">
  <!-- Top Bar -->
  <div class="admin-editor-topbar">
    <div class="admin-editor-topbar-left">
      <a href="/admin" class="admin-editor-back">&larr; Back</a>
      <span class="admin-status-badge admin-status-badge--{status}">{status}</span>
    </div>
    <div class="admin-editor-topbar-right">
      <button id="btn-save" class="admin-btn">Save</button>
      <button id="btn-preview" class="admin-btn">Preview</button>
      <button id="btn-publish-draft" class="admin-btn admin-btn-primary">Publish</button>
      <button id="btn-ai-toggle" class="admin-ai-panel-toggle" title="Toggle AI Panel">AI</button>
      <button id="btn-delete" class="admin-btn-danger">Delete</button>
    </div>
  </div>

  <!-- Editor Area -->
  <div class="admin-editor-content">
    <input id="edit-title" class="admin-editor-title" type="text" value={post.title} placeholder="Untitled" />
    <div class="admin-editor-meta">
      <select id="edit-category" class="admin-select" style="width: auto;">...</select>
      <input id="edit-tags" class="admin-input" style="flex: 1;" placeholder="Tags..." value={tags} />
    </div>
    <div id="admin-feedback" class="admin-feedback" hidden>
      <span id="admin-feedback-msg"></span>
      <button class="admin-feedback-dismiss" type="button">&times;</button>
    </div>
    <div id="milkdown-editor" class="admin-editor-wrapper" data-content={editableContent}></div>
  </div>

  <!-- AI Panel -->
  <div class="admin-ai-panel" id="ai-panel">
    <div class="admin-ai-panel-header">
      <span class="admin-ai-panel-title">AI Suggestions</span>
      <button id="btn-ai-close" class="admin-ai-panel-toggle">&times;</button>
    </div>
    <p class="admin-ai-panel-placeholder">
      AI suggestion panel will be connected in a future update.
    </p>
  </div>
</div>
```

**Step 2: Add AI panel toggle logic to `<script>`**

Inside the `astro:page-load` handler, after existing DOM refs, add:

```typescript
const aiPanel = document.getElementById('ai-panel');
const aiToggleBtn = document.getElementById('btn-ai-toggle');
const aiCloseBtn = document.getElementById('btn-ai-close');
const editorLayout = document.querySelector('.admin-editor-layout');

function toggleAiPanel() {
  editorLayout?.classList.toggle('admin-editor-layout--collapsed');
}

aiToggleBtn?.addEventListener('click', toggleAiPanel);
aiCloseBtn?.addEventListener('click', toggleAiPanel);
```

**Step 3: Keep Preview mode intact**

The Preview mode (`#preview-mode`) structure stays the same — it uses `NewsprintShell` for published-style preview. Only update its toolbar to use `admin-preview-bar` class (already exists in CSS).

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 5: Commit**

```bash
git add frontend/src/pages/admin/edit/[slug].astro
git commit -m "feat: redesign post editor with focused layout + AI panel"
```

---

### Task 6: Redesign Handbook Editor Page (`/admin/handbook/edit/[slug].astro`)

**Files:**
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

**Step 1: Apply editor-centric layout**

Same pattern as Task 5:
- Remove `AdminHeader` import
- Replace `admin-split` with `admin-editor-layout` grid
- Add `admin-editor-topbar` with back link, term name, save/publish/delete buttons, AI toggle
- Main content: form fields in `admin-editor-content`
- AI panel: `admin-ai-panel` on right side
- Keep all existing form fields, language tabs, details sections intact — just re-wrap in new layout
- Keep existing `<script>` logic intact — only add AI panel toggle

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "feat: redesign handbook editor with focused layout + AI panel"
```

---

### Task 7: Delete Old AdminHeader + Cleanup

**Files:**
- Delete: `frontend/src/components/admin/AdminHeader.astro`

**Step 1: Verify no remaining imports**

Search for `AdminHeader` across the codebase. All imports should have been removed in Tasks 3–6.

Run: `grep -r "AdminHeader" frontend/src/`
Expected: No results

**Step 2: Delete the file**

```bash
rm frontend/src/components/admin/AdminHeader.astro
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/components/admin/AdminHeader.astro
git commit -m "chore: remove unused AdminHeader component"
```

---

### Task 8: Final Build Verification + Visual QA

**Step 1: Full build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 2: Manual QA checklist**

- [ ] `/admin` — sidebar visible with Posts/Handbook nav, recent items, stats
- [ ] `/admin` — post list with filter tabs, status badges, action buttons
- [ ] `/admin` — right panel shows stat cards
- [ ] `/admin/handbook/` — same sidebar, handbook list, handbook stats
- [ ] `/admin/edit/[slug]` — no sidebar, focused editor layout, AI panel on right
- [ ] `/admin/edit/[slug]` — AI panel toggle works (collapse/expand)
- [ ] `/admin/edit/[slug]` — Milkdown editor loads content correctly
- [ ] `/admin/edit/[slug]` — Save, Preview, Publish buttons work
- [ ] `/admin/handbook/edit/[slug]` — same focused editor layout
- [ ] `/admin/handbook/edit/[slug]` — language tabs (KO/EN) work
- [ ] Theme switching (light/dark/pink) works correctly on all admin pages
- [ ] View Transitions navigation (back → edit → back) works

**Step 3: Commit**

```bash
git commit -m "chore: admin UI redesign complete — visual QA pass"
```
