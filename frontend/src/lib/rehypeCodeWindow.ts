import type { Root, Element, ElementContent, Text } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Rehype plugin: wraps Shiki-highlighted <pre> blocks in a macOS-style
 * code window with header (dots + language label + copy button).
 * Must run AFTER rehypeShiki in the pipeline.
 *
 * Options:
 * - collapsible: when true, the code body is collapsed by default.
 *   Header stays visible (dots + lang + line count + toggle button).
 *   Copy button hides in collapsed state. Used by handbookProcessor so
 *   Advanced pages don't dump long code dumps into the reading flow.
 */

interface CodeWindowOptions {
  collapsible?: boolean;
}

/** Recursively concatenate all text nodes under a HAST element. */
function extractText(node: Element | ElementContent): string {
  if (node.type === 'text') return (node as Text).value;
  if (node.type !== 'element') return '';
  let out = '';
  for (const child of (node as Element).children) {
    out += extractText(child);
  }
  return out;
}

function countCodeLines(preNode: Element): number {
  const code = preNode.children.find(
    (c): c is Element => c.type === 'element' && (c as Element).tagName === 'code',
  );
  if (!code) return 0;
  const text = extractText(code).replace(/\n$/, '');
  if (text.length === 0) return 0;
  return text.split('\n').length;
}

export default function rehypeCodeWindow(options: CodeWindowOptions = {}) {
  const { collapsible = false } = options;

  return (tree: Root) => {
    visit(tree, 'element', (node: Element, index, parent) => {
      if (node.tagName !== 'pre' || !parent || index === undefined) return;

      // Shiki v3 uses 'class' (not 'className') in HAST properties
      const cls = node.properties?.class ?? node.properties?.className;
      const classes = typeof cls === 'string' ? cls.split(' ') : Array.isArray(cls) ? cls : [];
      if (!classes.includes('shiki')) return;

      const lang = (node.properties['data-language'] as string) || '';
      delete node.properties['data-language'];

      const headerChildren: ElementContent[] = [
        // 3 dots
        {
          type: 'element',
          tagName: 'span',
          properties: { className: ['code-window-dots'] },
          children: [
            { type: 'element', tagName: 'span', properties: { className: ['dot', 'dot-red'] }, children: [] },
            { type: 'element', tagName: 'span', properties: { className: ['dot', 'dot-yellow'] }, children: [] },
            { type: 'element', tagName: 'span', properties: { className: ['dot', 'dot-green'] }, children: [] },
          ],
        },
        // language label
        {
          type: 'element',
          tagName: 'span',
          properties: { className: ['code-window-lang'] },
          children: lang ? [{ type: 'text', value: lang }] : [],
        },
      ];

      if (collapsible) {
        // Line count label (between language and buttons)
        const lineCount = countCodeLines(node);
        headerChildren.push({
          type: 'element',
          tagName: 'span',
          properties: { className: ['code-window-lines'] },
          children: [{ type: 'text', value: `${lineCount} lines` }],
        });
        // Toggle button (collapse/expand)
        headerChildren.push({
          type: 'element',
          tagName: 'button',
          properties: {
            className: ['code-toggle-btn'],
            'data-code-toggle': '',
            'aria-label': 'Toggle code visibility',
            type: 'button',
          },
          children: [{ type: 'text', value: '펼치기 ▾' }],
        });
      }

      // Copy button (always present; hidden via CSS when collapsed)
      headerChildren.push({
        type: 'element',
        tagName: 'button',
        properties: { className: ['code-copy-btn'], 'data-code-copy': '', type: 'button' },
        children: [{ type: 'text', value: 'Copy' }],
      });

      const header: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['code-window-header'] },
        children: headerChildren,
      };

      const wrapperClasses = ['code-window'];
      if (collapsible) {
        wrapperClasses.push('code-window--collapsible', 'code-window--collapsed');
      }

      const wrapper: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: wrapperClasses },
        children: [header, node],
      };

      (parent as Element).children[index] = wrapper;
    });
  };
}
