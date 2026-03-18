const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

describe('Content Feedback — Contract Tests', () => {
  // API
  test('content-feedback API exists with GET/POST/DELETE', () => {
    const api = fs.readFileSync(path.join(root, 'src/pages/api/user/content-feedback.ts'), 'utf8');
    expect(api).toContain('export const GET');
    expect(api).toContain('export const POST');
    expect(api).toContain('export const DELETE');
    expect(api).toContain("from('content_feedback')");
    expect(api).toContain('source_type');
    expect(api).toContain('source_id');
  });

  test('API validates reason per source_type', () => {
    const api = fs.readFileSync(path.join(root, 'src/pages/api/user/content-feedback.ts'), 'utf8');
    expect(api).toContain('VALID_REASONS');
    expect(api).toContain('inaccurate');
    expect(api).toContain('confusing');
    expect(api).toContain('not_helpful');
    expect(api).toContain('inaccurate_info');
  });

  // Component
  test('ContentFeedback.astro has correct data attributes', () => {
    const comp = fs.readFileSync(path.join(root, 'src/components/common/ContentFeedback.astro'), 'utf8');
    expect(comp).toContain('data-content-feedback');
    expect(comp).toContain('data-source-type');
    expect(comp).toContain('data-source-id');
    expect(comp).toContain('data-reaction="positive"');
    expect(comp).toContain('data-reaction="negative"');
  });

  // Script
  test('contentFeedback.ts calls content-feedback API', () => {
    const script = fs.readFileSync(path.join(root, 'src/scripts/contentFeedback.ts'), 'utf8');
    expect(script).toContain('/api/user/content-feedback');
    expect(script).toContain('source_type');
    expect(script).toContain('initContentFeedback');
    expect(script).toContain('REASONS');
  });

  // Pages mount the component — handbook and products import directly
  const directPages = [
    'src/pages/ko/handbook/[slug].astro',
    'src/pages/en/handbook/[slug].astro',
    'src/pages/ko/products/[slug].astro',
    'src/pages/en/products/[slug].astro',
  ];

  directPages.forEach((pagePath) => {
    test(`${pagePath} imports ContentFeedback and contentFeedback script`, () => {
      const content = fs.readFileSync(path.join(root, pagePath), 'utf8');
      expect(content).toContain('ContentFeedback');
      expect(content).toContain('contentFeedback');
    });
  });

  // News and blog pages import contentFeedback script but ContentFeedback component lives in layout
  const layoutDelegatedPages = [
    'src/pages/ko/news/[slug].astro',
    'src/pages/en/news/[slug].astro',
    'src/pages/ko/blog/[slug].astro',
    'src/pages/en/blog/[slug].astro',
  ];

  layoutDelegatedPages.forEach((pagePath) => {
    test(`${pagePath} imports contentFeedback script`, () => {
      const content = fs.readFileSync(path.join(root, pagePath), 'utf8');
      expect(content).toContain('contentFeedback');
    });
  });

  test('NewsprintArticleLayout imports and renders ContentFeedback', () => {
    const layout = fs.readFileSync(
      path.join(root, 'src/components/newsprint/NewsprintArticleLayout.astro'),
      'utf8',
    );
    expect(layout).toContain('ContentFeedback');
  });

  test('BlogArticleLayout imports and renders ContentFeedback', () => {
    const layout = fs.readFileSync(
      path.join(root, 'src/components/blog/BlogArticleLayout.astro'),
      'utf8',
    );
    expect(layout).toContain('ContentFeedback');
  });

  // Old system removed
  test('old term-feedback system is removed', () => {
    expect(fs.existsSync(path.join(root, 'src/pages/api/user/term-feedback.ts'))).toBe(false);
    expect(fs.existsSync(path.join(root, 'src/components/newsprint/HandbookFeedback.astro'))).toBe(false);
    expect(fs.existsSync(path.join(root, 'src/scripts/handbookFeedback.ts'))).toBe(false);
  });

  // StickyReadingActions no longer has feedback buttons
  test('StickyReadingActions term variant has no feedback buttons', () => {
    const sticky = fs.readFileSync(path.join(root, 'src/components/common/StickyReadingActions.astro'), 'utf8');
    expect(sticky).not.toContain('data-handbook-feedback');
    expect(sticky).not.toContain('data-reaction="helpful"');
    expect(sticky).not.toContain('data-reaction="confusing"');
  });

  // Admin archive API uses content_feedback
  test('admin archive API uses content_feedback table', () => {
    const archive = fs.readFileSync(path.join(root, 'src/pages/api/admin/feedback/archive.ts'), 'utf8');
    expect(archive).toContain("from('content_feedback')");
    expect(archive).not.toContain("from('term_feedback')");
  });

  // CSS
  test('CSS uses content-feedback classes', () => {
    const css = fs.readFileSync(path.join(root, 'src/styles/global.css'), 'utf8');
    expect(css).toContain('.content-feedback');
    expect(css).toContain('.content-feedback-btn--positive');
    expect(css).toContain('.content-feedback-btn--negative');
    expect(css).toContain('.feedback-sheet-reasons');
    expect(css).not.toContain('.handbook-feedback');
  });

  // Admin dashboard
  test('admin feedback page queries content_feedback', () => {
    const admin = fs.readFileSync(path.join(root, 'src/pages/admin/feedback/index.astro'), 'utf8');
    expect(admin).toContain('content_feedback');
    expect(admin).not.toContain('term_feedback');
  });
});
