/**
 * Regression test for the 2026-04-30 incident: clicking "Save & re-run quality"
 * before opening the Expert tab in the business editor sent content_expert='',
 * which the backend's `'' || null` then nulled out, then QC scored the row as
 * "KO body missing" (major locale issue) — score dropped 84→69.
 *
 * Two layers of defense (each tested below):
 *
 *   Layer 1 (frontend): the editor page must NOT include content_expert /
 *     content_learner in the saveBody if the corresponding lazy-loaded editor
 *     is null. This test covers the saveBody-construction logic by mirroring
 *     the conditional gate from the editor page.
 *
 *   Layer 2 (backend): /api/admin/posts/save must treat empty-string content_*
 *     as "no change" rather than nulling the column. This test mirrors the
 *     row-construction logic from save.ts.
 */
import assert from 'node:assert/strict';

// --- Layer 1 mirror: saveBody construction (mirrors [slug].astro:699-716) ---
function buildBusinessSaveBody({ beginnerEditor, learnerEditor, expertEditor }) {
  const saveBody = {};
  if (beginnerEditor) {
    saveBody.content_beginner = beginnerEditor.getMarkdown();
  }
  if (learnerEditor) {
    saveBody.content_learner = learnerEditor.getMarkdown();
  }
  if (expertEditor) {
    saveBody.content_expert = expertEditor.getMarkdown();
  }
  return saveBody;
}

// Both editors loaded → both fields included
{
  const body = buildBusinessSaveBody({
    beginnerEditor: { getMarkdown: () => 'B content' },
    learnerEditor: { getMarkdown: () => 'L content' },
    expertEditor: { getMarkdown: () => 'E content' },
  });
  assert.equal(body.content_beginner, 'B content', 'beginner content sent when editor loaded');
  assert.equal(body.content_learner, 'L content', 'learner content sent when editor loaded');
  assert.equal(body.content_expert, 'E content', 'expert content sent when editor loaded');
}

// Expert editor null (lazy not initialized) → content_expert MUST NOT be sent
{
  const body = buildBusinessSaveBody({
    learnerEditor: { getMarkdown: () => 'L content' },
    expertEditor: null,
  });
  assert.equal(body.content_learner, 'L content', 'learner still sent');
  assert.equal('content_expert' in body, false, 'content_expert OMITTED when editor null');
}

// Both editors null → neither field sent
{
  const body = buildBusinessSaveBody({ beginnerEditor: null, learnerEditor: null, expertEditor: null });
  assert.equal('content_beginner' in body, false, 'content_beginner OMITTED when editor null');
  assert.equal('content_learner' in body, false, 'content_learner OMITTED when editor null');
  assert.equal('content_expert' in body, false, 'content_expert OMITTED when editor null');
}

// --- Layer 2 mirror: backend row construction (mirrors save.ts:48-61) ---
function buildBackendRow({ content_beginner, content_learner, content_expert }) {
  const row = {};
  if (content_beginner !== undefined && content_beginner !== '') row.content_beginner = content_beginner;
  if (content_learner !== undefined && content_learner !== '') row.content_learner = content_learner;
  if (content_expert !== undefined && content_expert !== '') row.content_expert = content_expert;
  return row;
}

// Field absent (Layer 1 properly omitted) → no key set, existing DB value preserved
{
  const row = buildBackendRow({});
  assert.equal('content_expert' in row, false, 'absent field → no key in row → DB preserved');
}

// Empty string (Layer 1 bypass — defense in depth) → still treated as no-change
{
  const row = buildBackendRow({ content_beginner: '', content_expert: '' });
  assert.equal('content_beginner' in row, false, 'empty-string beginner field preserves DB');
  assert.equal('content_expert' in row, false, 'empty-string field → no key in row → DB preserved');
}

// Genuine content → field set for update
{
  const row = buildBackendRow({ content_beginner: 'beginner content', content_expert: 'real content' });
  assert.equal(row.content_beginner, 'beginner content', 'beginner non-empty content updates');
  assert.equal(row.content_expert, 'real content', 'non-empty content → field updated');
}

// Whitespace-only content (edge case) — still updated. Editors typically don't
// produce pure-whitespace; if they do, that's a separate UX issue, not data loss.
{
  const row = buildBackendRow({ content_expert: '   ' });
  assert.equal(row.content_expert, '   ', 'whitespace-only still updates (not the wipe vector)');
}

console.log('admin-posts-save-empty-content.test.mjs passed');
