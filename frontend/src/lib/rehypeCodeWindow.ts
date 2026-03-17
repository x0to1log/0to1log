import type { Root, Element, ElementContent } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Rehype plugin: wraps Shiki-highlighted <pre> blocks in a macOS-style
 * code window with header (dots + language label + copy button).
 * Must run AFTER rehypeShiki in the pipeline.
 */
export default function rehypeCodeWindow() {
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
        // copy button
        {
          type: 'element',
          tagName: 'button',
          properties: { className: ['code-copy-btn'], 'data-code-copy': '' },
          children: [{ type: 'text', value: 'Copy' }],
        },
      ];

      const header: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['code-window-header'] },
        children: headerChildren,
      };

      const wrapper: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['code-window'] },
        children: [header, node],
      };

      (parent as Element).children[index] = wrapper;
    });
  };
}
