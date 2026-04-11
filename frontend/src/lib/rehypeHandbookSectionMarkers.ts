import type { Root, Element, ElementContent } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Rehype plugin: add CSS classes to specific handbook sections based on
 * heading text, so CSS can target them without relying on auto-generated IDs
 * (we don't use rehype-slug).
 *
 * For each matching h2, the plugin walks forward through siblings (stopping
 * at the next h2) and tags the first `ul`/`ol` it finds with the marker
 * class. This lets CSS style `.hb-section-pitfalls > li` as warning callouts
 * (or `.hb-section-dialogue > li` as quote cards) without any heading-text
 * CSS selector gymnastics.
 *
 * Currently targets:
 * - Advanced §5 프로덕션 함정 / Production Pitfalls → `.hb-section-pitfalls`
 * - Advanced §6 업계 대화 맥락 / Industry Communication → `.hb-section-dialogue`
 *
 * Extend the MARKERS list to add more sections later.
 */

interface SectionMarker {
  className: string;
  patterns: RegExp[];
}

const MARKERS: SectionMarker[] = [
  {
    className: 'hb-section-pitfalls',
    patterns: [/프로덕션\s*함정/, /production\s*pitfalls/i],
  },
  {
    className: 'hb-section-dialogue',
    patterns: [/업계\s*대화/, /Industry\s+Communication/i],
  },
];

function extractText(node: Element | ElementContent): string {
  if (node.type === 'text') return node.value;
  if (node.type !== 'element') return '';
  let out = '';
  for (const child of (node as Element).children) {
    out += extractText(child);
  }
  return out;
}

function addClass(node: Element, className: string): void {
  const existing = node.properties?.className;
  const classes = Array.isArray(existing)
    ? (existing as string[])
    : typeof existing === 'string'
    ? existing.split(/\s+/).filter(Boolean)
    : [];
  if (!classes.includes(className)) classes.push(className);
  node.properties = { ...(node.properties || {}), className: classes };
}

export default function rehypeHandbookSectionMarkers() {
  return (tree: Root) => {
    visit(tree, 'element', (node: Element, index, parent) => {
      if (node.tagName !== 'h2' || !parent || index === undefined) return;

      const text = extractText(node).trim();
      const marker = MARKERS.find((m) => m.patterns.some((p) => p.test(text)));
      if (!marker) return;

      // Walk forward siblings until next h2, find first list and tag it
      const siblings = (parent as Element).children;
      for (let i = index + 1; i < siblings.length; i++) {
        const sibling = siblings[i];
        if (sibling.type !== 'element') continue;
        const el = sibling as Element;
        if (el.tagName === 'h2') return; // hit next section without finding a list
        if (el.tagName === 'ul' || el.tagName === 'ol') {
          addClass(el, marker.className);
          return;
        }
      }
    });
  };
}
