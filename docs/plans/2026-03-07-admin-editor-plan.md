# Admin Editor (P2C-UI-14) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Admin Editor UI with Milkdown WYSIWYG markdown editing, Draft/Preview mode switching, and mock data.

**Architecture:** SSR Astro pages (`prerender = false`) with vanilla `<script>` for Milkdown initialization and mode switching. Draft mode uses a 2fr/1fr grid (editor + AI placeholder panel). Preview mode renders the full published page view using existing newsprint components. Mock data only; real API wiring is P2C-UI-15.

**Tech Stack:** Astro v5, Milkdown Crepe preset, vanilla JS, CSS custom properties (newsprint theme)

**Design Doc:** `docs/plans/2026-03-07-admin-editor-design.md`

---

## Task 1: Install Milkdown packages

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install Milkdown Crepe**

Run:
```bash
cd frontend && npm install @milkdown/crepe
```

**Step 2: Verify install**

Run:
```bash
cd frontend && npm run build
```
Expected: Build succeeds with 0 errors.

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install milkdown crepe for admin editor"
```

---

## Task 2: Add admin CSS styles to global.css

**Files:**
- Modify: `frontend/src/styles/global.css` (append before closing)

**Step 1: Add admin styles**

Append the following CSS block at the end of `global.css`, before any final closing comments:

```css
/* ===========================
   ADMIN EDITOR
   =========================== */
.admin-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
  position: sticky;
  top: 0;
  background: var(--color-bg-primary);
  z-index: 10;
}

.admin-toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.admin-toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-btn {
  padding: 0.5rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 700;
  font-family: var(--font-sans);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease;
}

.admin-btn:hover {
  background: var(--color-accent-subtle);
}

.admin-btn-primary {
  background: var(--color-accent);
  color: var(--color-bg-primary);
  border-color: var(--color-accent);
}

.admin-btn-primary:hover {
  background: var(--color-accent-hover);
}

.admin-back {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-family: var(--font-sans);
}

.admin-back:hover {
  color: var(--color-text-primary);
}

.admin-split {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .admin-split {
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
  }
}

.admin-field {
  margin-bottom: 1rem;
}

.admin-field label {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  margin-bottom: 0.35rem;
  font-family: var(--font-sans);
}

.admin-input {
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 1rem;
  font-family: var(--font-body);
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  outline: none;
}

.admin-input:focus {
  border-color: var(--color-accent);
}

.admin-select {
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 0.9rem;
  font-family: var(--font-sans);
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  outline: none;
  cursor: pointer;
}

.admin-select:focus {
  border-color: var(--color-accent);
}

.admin-panel {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  padding: 1.25rem;
  font-family: var(--font-sans);
}

.admin-panel-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.admin-panel-placeholder {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.admin-editor-wrapper {
  border: 1px solid var(--color-border);
  min-height: 400px;
}

/* Milkdown Crepe theme overrides for newsprint */
.admin-editor-wrapper .milkdown {
  --crepe-color-background: var(--color-bg-tertiary);
  --crepe-color-surface: var(--color-bg-secondary);
  --crepe-color-surface-low: var(--color-bg-primary);
  --crepe-color-on-background: var(--color-text-primary);
  --crepe-color-on-surface: var(--color-text-primary);
  --crepe-color-on-surface-variant: var(--color-text-secondary);
  --crepe-color-primary: var(--color-accent);
  --crepe-color-secondary: var(--color-accent-subtle);
  --crepe-color-outline: var(--color-border);
  --crepe-color-hover: var(--color-accent-subtle);
  --crepe-color-selected: var(--color-accent-glow);
}

.admin-preview-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
  position: sticky;
  top: 0;
  background: var(--color-bg-primary);
  z-index: 10;
}

/* Draft list */
.admin-draft-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.admin-draft-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
}

.admin-draft-info {
  flex: 1;
}

.admin-draft-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 0.25rem;
}

.admin-draft-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-family: var(--font-sans);
}

@media (max-width: 767px) {
  .admin-toolbar,
  .admin-preview-bar {
    padding: 0.5rem 0;
  }

  .admin-btn {
    padding: 0.4rem 0.75rem;
    font-size: 0.75rem;
  }
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors.

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: add admin editor CSS styles"
```

---

## Task 3: Update admin index page with draft list

**Files:**
- Modify: `frontend/src/pages/admin/index.astro`

**Step 1: Replace the current placeholder with a mock draft list**

Replace the entire file content:

```astro
---
export const prerender = false;
import MainLayout from '../../layouts/MainLayout.astro';

// Mock draft data (matches backend PostDraftListItem schema)
const mockDrafts = [
  {
    id: 'uuid-001',
    title: 'AI Reasoning Models: Chain-of-Thought Breakthroughs in 2026',
    slug: '2026-03-07-ai-reasoning-models',
    category: 'ai-news',
    status: 'draft',
    created_at: '2026-03-07T09:00:00Z',
    updated_at: '2026-03-07T14:30:00Z',
  },
  {
    id: 'uuid-002',
    title: 'Understanding Transformer Attention Patterns',
    slug: '2026-03-06-transformer-attention',
    category: 'study',
    status: 'draft',
    created_at: '2026-03-06T10:00:00Z',
    updated_at: '2026-03-06T16:00:00Z',
  },
  {
    id: 'uuid-003',
    title: 'Building a CLI Tool with Claude Agent SDK',
    slug: '2026-03-05-cli-tool-agent-sdk',
    category: 'project',
    status: 'draft',
    created_at: '2026-03-05T08:00:00Z',
    updated_at: '2026-03-05T12:00:00Z',
  },
];
---

<MainLayout title="Admin Dashboard" locale="en">
  <div style="max-width: 800px; margin: 0 auto;">
    <h1 class="newsprint-masthead" style="font-size: 2rem; text-align: left; margin-bottom: 0.5rem;">
      Admin Dashboard
    </h1>
    <p class="admin-draft-meta" style="margin-bottom: 1.5rem;">
      {mockDrafts.length} draft{mockDrafts.length !== 1 ? 's' : ''} pending
    </p>

    <ul class="admin-draft-list">
      {mockDrafts.map((draft) => (
        <li class="admin-draft-item">
          <div class="admin-draft-info">
            <div class="admin-draft-title">{draft.title}</div>
            <div class="admin-draft-meta">
              {draft.category} &middot; {new Date(draft.updated_at).toLocaleDateString('en-US')}
            </div>
          </div>
          <a href={`/admin/edit/${draft.slug}`} class="admin-btn">Edit</a>
        </li>
      ))}
    </ul>
  </div>
</MainLayout>
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors.

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat: admin dashboard with mock draft list"
```

---

## Task 4: Create admin editor page with Draft/Preview modes

**Files:**
- Create: `frontend/src/pages/admin/edit/[slug].astro`

**Step 1: Create the editor page**

Create directory and file:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import NewsprintShell from '../../../components/newsprint/NewsprintShell.astro';
import NewsprintArticleLayout from '../../../components/newsprint/NewsprintArticleLayout.astro';
import { getCategoryLabel, getCategoryColorVar, getDefaultCategories } from '../../../lib/categories';

const { slug } = Astro.params;
const pageSlug = slug ?? '';

// Mock draft data (matches backend PostDraftDetail schema)
const mockDrafts: Record<string, any> = {
  '2026-03-07-ai-reasoning-models': {
    id: 'uuid-001',
    title: 'AI Reasoning Models: Chain-of-Thought Breakthroughs in 2026',
    slug: '2026-03-07-ai-reasoning-models',
    category: 'ai-news',
    post_type: 'business',
    status: 'draft',
    locale: 'en',
    content_original: '## The Rise of Reasoning\n\nRecent breakthroughs in chain-of-thought reasoning have transformed how AI models approach complex problems.\n\n### Key Developments\n\n- **Extended thinking**: Models now show their reasoning process step by step\n- **Self-correction**: Built-in verification loops catch logical errors\n- **Multi-step planning**: Complex tasks broken into manageable sub-goals\n\n> "The ability to reason through problems, rather than pattern-match answers, represents a fundamental shift in AI capability." — Research Lead\n\n### What This Means for Builders\n\n1. Prompting strategies need to evolve\n2. Evaluation frameworks must test reasoning quality\n3. Applications can tackle previously impossible tasks\n\nThe implications extend beyond benchmarks into real-world problem solving.',
    tags: ['reasoning', 'chain-of-thought', 'llm', 'ai-research'],
    created_at: '2026-03-07T09:00:00Z',
    updated_at: '2026-03-07T14:30:00Z',
  },
  '2026-03-06-transformer-attention': {
    id: 'uuid-002',
    title: 'Understanding Transformer Attention Patterns',
    slug: '2026-03-06-transformer-attention',
    category: 'study',
    post_type: 'research',
    status: 'draft',
    locale: 'en',
    content_original: '## Attention Mechanisms Decoded\n\nTransformer attention is the backbone of modern LLMs. Understanding how attention patterns form helps us build better models.\n\n### Self-Attention Basics\n\nEach token attends to every other token, creating a weighted representation.\n\n```python\nimport torch\nimport torch.nn.functional as F\n\ndef scaled_dot_product(Q, K, V):\n    d_k = Q.size(-1)\n    scores = torch.matmul(Q, K.transpose(-2, -1)) / d_k**0.5\n    weights = F.softmax(scores, dim=-1)\n    return torch.matmul(weights, V)\n```\n\n### Multi-Head Attention\n\nMultiple attention heads allow the model to focus on different aspects simultaneously.\n\n- **Head 1**: Syntactic relationships\n- **Head 2**: Semantic similarity\n- **Head 3**: Positional patterns',
    tags: ['transformer', 'attention', 'deep-learning'],
    created_at: '2026-03-06T10:00:00Z',
    updated_at: '2026-03-06T16:00:00Z',
  },
  '2026-03-05-cli-tool-agent-sdk': {
    id: 'uuid-003',
    title: 'Building a CLI Tool with Claude Agent SDK',
    slug: '2026-03-05-cli-tool-agent-sdk',
    category: 'project',
    post_type: 'business',
    status: 'draft',
    locale: 'en',
    content_original: '## Project Overview\n\nA command-line tool that leverages the Claude Agent SDK to automate code review workflows.\n\n### Architecture\n\n- **CLI Entry**: `argparse` for command parsing\n- **Agent Core**: Claude Agent SDK with custom tools\n- **Output**: Formatted markdown reports\n\n### Getting Started\n\n```bash\npip install claude-agent-sdk\npython cli.py review --repo ./my-project\n```\n\n### Key Learnings\n\n1. Agent loops need clear exit conditions\n2. Tool definitions should be minimal and focused\n3. Context management is critical for large codebases',
    tags: ['claude', 'agent-sdk', 'cli', 'automation'],
    created_at: '2026-03-05T08:00:00Z',
    updated_at: '2026-03-05T12:00:00Z',
  },
};

const draft = mockDrafts[pageSlug];
if (!draft) {
  return Astro.redirect('/admin');
}

const categories = getDefaultCategories();
---

<MainLayout title={`Edit: ${draft.title}`} locale="en">
  <!-- Draft Mode -->
  <div id="draft-mode">
    <div class="admin-toolbar">
      <div class="admin-toolbar-left">
        <a href="/admin" class="admin-back">&larr; Back to Drafts</a>
      </div>
      <div class="admin-toolbar-right">
        <button id="btn-preview" class="admin-btn" type="button">Preview</button>
      </div>
    </div>

    <div class="admin-split">
      <div>
        <div class="admin-field">
          <label for="edit-title">Title</label>
          <input
            id="edit-title"
            class="admin-input"
            type="text"
            value={draft.title}
            placeholder="Post title..."
          />
        </div>

        <div style="display: flex; gap: 1rem;">
          <div class="admin-field" style="flex: 1;">
            <label for="edit-category">Category</label>
            <select id="edit-category" class="admin-select">
              {categories.map((cat) => (
                <option value={cat} selected={cat === draft.category}>
                  {getCategoryLabel('en', cat)}
                </option>
              ))}
            </select>
          </div>
          <div class="admin-field" style="flex: 2;">
            <label for="edit-tags">Tags</label>
            <input
              id="edit-tags"
              class="admin-input"
              type="text"
              value={(draft.tags || []).join(', ')}
              placeholder="tag1, tag2, tag3..."
            />
          </div>
        </div>

        <div class="admin-field">
          <label>Content</label>
          <div id="milkdown-editor" class="admin-editor-wrapper"></div>
        </div>
      </div>

      <div>
        <div class="admin-panel">
          <div class="admin-panel-title">AI Suggestions</div>
          <p class="admin-panel-placeholder">
            AI suggestion panel will be connected in a future update.
            This panel will show editorial verdicts, accuracy scores,
            and actionable suggestions with one-click apply.
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- Preview Mode -->
  <div id="preview-mode" style="display: none;">
    <div class="admin-preview-bar">
      <div class="admin-toolbar-left">
        <a href="/admin" class="admin-back">&larr; Back to Drafts</a>
      </div>
      <div class="admin-toolbar-right">
        <button id="btn-edit" class="admin-btn" type="button">Edit</button>
        <button id="btn-publish" class="admin-btn admin-btn-primary" type="button">Publish</button>
      </div>
    </div>

    <NewsprintShell
      locale="en"
      masthead="From Void to Value"
      editionLabel="Builder's Daily"
      subkicker={['AI · Papers · Projects', 'Daily Curation', 'Open Access']}
    >
      <div id="preview-content">
        <NewsprintArticleLayout
          locale="en"
          slug={pageSlug}
          title={draft.title}
          category={draft.category}
          publishedAt={new Date().toISOString()}
          readingTimeMin={5}
          tags={draft.tags}
          htmlContent=""
          backLabel="Back to List"
        />
      </div>
    </NewsprintShell>
  </div>
</MainLayout>

<script>
  import { Crepe } from '@milkdown/crepe';
  import '@milkdown/crepe/theme/common/style.css';

  let crepe: Crepe | null = null;
  let currentMarkdown = '';

  // Read initial markdown from the server-rendered data attribute
  const editorEl = document.getElementById('milkdown-editor');
  const draftMode = document.getElementById('draft-mode');
  const previewMode = document.getElementById('preview-mode');
  const btnPreview = document.getElementById('btn-preview');
  const btnEdit = document.getElementById('btn-edit');
  const btnPublish = document.getElementById('btn-publish');
  const titleInput = document.getElementById('edit-title') as HTMLInputElement;
  const categorySelect = document.getElementById('edit-category') as HTMLSelectElement;
  const tagsInput = document.getElementById('edit-tags') as HTMLInputElement;

  // Initialize Milkdown Crepe
  async function initEditor() {
    if (!editorEl) return;

    // Get initial content from data attribute
    const initialContent = editorEl.dataset.content || '';

    crepe = new Crepe({
      root: editorEl,
      defaultValue: initialContent,
      featureConfigs: {
        [Crepe.Feature.Placeholder]: {
          text: 'Start writing your post...',
          mode: 'block',
        },
      },
    });

    await crepe.create();
  }

  // Simple markdown to HTML (for preview)
  function markdownToHtml(md: string): string {
    let html = md;
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Bold and italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Blockquotes
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Paragraphs (lines not already wrapped)
    html = html.replace(/^(?!<[hublop]|<li|<blockquote|<pre)(.+)$/gm, '<p>$1</p>');
    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    return html;
  }

  // Auto-save + switch to Preview
  function switchToPreview() {
    if (!crepe) return;

    currentMarkdown = crepe.getMarkdown();
    const title = titleInput?.value || '';
    const category = categorySelect?.value || '';
    const tags = tagsInput?.value || '';

    console.log('Auto-saved draft:', { title, category, tags, content: currentMarkdown });

    // Update preview content
    const previewContent = document.getElementById('preview-content');
    if (previewContent) {
      // Update the title in preview
      const previewTitle = previewContent.querySelector('.newsprint-lead-title');
      if (previewTitle) previewTitle.textContent = title;

      // Update the category in preview
      const previewCategory = previewContent.querySelector('.newsprint-category');
      if (previewCategory) previewCategory.textContent = category;

      // Update the prose content
      const previewProse = previewContent.querySelector('.newsprint-prose');
      if (previewProse) previewProse.innerHTML = markdownToHtml(currentMarkdown);
    }

    // Toggle visibility
    if (draftMode) draftMode.style.display = 'none';
    if (previewMode) previewMode.style.display = 'block';
  }

  // Switch back to Draft
  function switchToDraft() {
    if (draftMode) draftMode.style.display = 'block';
    if (previewMode) previewMode.style.display = 'none';
  }

  // Publish mock
  function handlePublish() {
    const title = titleInput?.value || '';
    console.log('Published:', { title, slug: window.location.pathname.split('/').pop() });
    alert('Published! (mock — check console for details)');
  }

  // Event listeners
  btnPreview?.addEventListener('click', switchToPreview);
  btnEdit?.addEventListener('click', switchToDraft);
  btnPublish?.addEventListener('click', handlePublish);

  // Init
  initEditor();
</script>
```

Note: The editor page needs the initial markdown content passed via data attribute. Add this to the `#milkdown-editor` div:

```html
<div id="milkdown-editor" class="admin-editor-wrapper" data-content={draft.content_original}></div>
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors.

**Step 3: Manual verification**

- Navigate to `/admin` — draft list with 3 items
- Click [Edit] on any draft — editor page loads
- Milkdown WYSIWYG editor renders with markdown content
- Type in editor — WYSIWYG formatting applies
- Click [Preview] — console shows auto-save, full newsprint page renders
- Click [Edit] — returns to editor
- Click [Publish] — alert + console log
- Test on mobile viewport — single column
- Test all 3 themes (dark/light/pink)

**Step 4: Commit**

```bash
git add frontend/src/pages/admin/edit/
git commit -m "feat: admin editor page with milkdown WYSIWYG and draft/preview modes"
```

---

## Task 5: Update project documentation

**Files:**
- Modify: `docs/plans/ACTIVE_SPRINT.md`
- Modify: `frontend/CLAUDE.md`

**Step 1: Update ACTIVE_SPRINT.md**

Update P2C-UI-14 task:
- Change `체크: [ ]` to `체크: [x]`
- Change `상태: todo` to `상태: done`
- Add evidence link (commit hash)
- Update `Current Doing` table to `-`

**Step 2: Update frontend/CLAUDE.md**

Add Admin Editor section:

```markdown
## Admin Editor

- WYSIWYG editor: Milkdown Crepe preset (`@milkdown/crepe`)
- Initialized via vanilla `<script>` (no `client:load`)
- Draft/Preview mode: Draft = editor + AI panel, Preview = full newsprint published view
- Auto-save on Preview transition
- CSS classes: `.admin-*` in `global.css`
- Mock data until P2C-UI-15 API wiring
```

**Step 3: Commit**

```bash
git add docs/plans/ACTIVE_SPRINT.md frontend/CLAUDE.md
git commit -m "docs: update sprint status and frontend rules for admin editor"
```

---

## Verification Checklist

- [ ] `npm run build` 0 errors
- [ ] `/admin` shows 3 mock drafts with [Edit] links
- [ ] `/admin/edit/[slug]` renders Milkdown WYSIWYG editor
- [ ] Markdown formatting works live (headings, bold, lists, code blocks)
- [ ] [Preview] auto-saves (console.log) + shows full newsprint published page
- [ ] Preview includes masthead, subkicker, divider — identical to reader view
- [ ] [Edit] returns to Draft mode with content preserved
- [ ] [Publish] button shows mock alert
- [ ] Mobile: single column layout, AI panel below
- [ ] 3 themes (dark/light/pink) render correctly
- [ ] All commits follow `feat:`/`docs:` convention
