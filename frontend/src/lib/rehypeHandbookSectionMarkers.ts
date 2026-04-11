import type { Root, Element, ElementContent } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Rehype plugin: shape specific handbook sections for custom styling.
 *
 * Two operations on Advanced handbook bodies:
 *
 * 1. §5 프로덕션 함정 / Production Pitfalls → `ul.hb-section-pitfalls`
 *    §6 업계 대화 / Industry Communication → `ul.hb-section-dialogue`
 *    Basic "대화에서는 이렇게" / "How It Sounds in Conversation"
 *    also → `ul.hb-section-dialogue` (same quote-card layout).
 *    (simple class injection so CSS can target the list)
 *
 * 2. §4 트레이드오프 / Tradeoffs → wraps `적합/부적합` into a 2-column grid.
 *    Input shape (produced by the advisor prompt):
 *      <p>이럴 때 적합:</p>
 *      <ul>...</ul>
 *      <p>이럴 때 부적합:</p>
 *      <ul>...</ul>
 *    Output shape:
 *      <div class="hb-tradeoffs-grid">
 *        <section class="hb-tradeoffs-grid__panel hb-tradeoffs-grid__panel--good">
 *          <h3 class="hb-tradeoffs-grid__label">이럴 때 적합</h3>
 *          <ul>...</ul>
 *        </section>
 *        <section class="hb-tradeoffs-grid__panel hb-tradeoffs-grid__panel--bad">
 *          <h3 class="hb-tradeoffs-grid__label">이럴 때 부적합</h3>
 *          <ul>...</ul>
 *        </section>
 *      </div>
 *    The grid flips to a single column below 768px via CSS.
 *    If the expected p/ul/p/ul shape isn't found, the content is left
 *    untouched (graceful degradation for older generations).
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
    patterns: [
      /업계\s*대화/,
      /대화에서는/,
      /Industry\s+Communication/i,
      /How\s+It\s+Sounds/i,
    ],
  },
];

const TRADEOFFS_H2_PATTERNS = [/트레이드오프/, /tradeoffs?/i];
const GOOD_LABEL_PATTERNS = [/^이럴\s*때\s*적합/, /^suitable\b/i];
const BAD_LABEL_PATTERNS = [/^이럴\s*때\s*부적합/, /^unsuitable\b/i];

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

function stripTrailingColon(text: string): string {
  return text.replace(/[\s:：]+$/u, '');
}

/**
 * Walks forward siblings after the tradeoffs h2 looking for the
 * p/ul/p/ul pattern. Returns true if the wrap was applied.
 */
function wrapTradeoffsGrid(parent: Element, h2Index: number): boolean {
  const siblings = parent.children;
  let goodLabelIdx = -1;
  let goodListIdx = -1;
  let badLabelIdx = -1;
  let badListIdx = -1;

  for (let i = h2Index + 1; i < siblings.length; i++) {
    const el = siblings[i];
    if (el.type !== 'element') continue;
    const tag = (el as Element).tagName;
    if (tag === 'h2') break; // next section — stop

    if (tag === 'p') {
      const text = extractText(el as Element).trim();
      if (goodLabelIdx < 0 && GOOD_LABEL_PATTERNS.some((p) => p.test(text))) {
        goodLabelIdx = i;
      } else if (badLabelIdx < 0 && BAD_LABEL_PATTERNS.some((p) => p.test(text))) {
        badLabelIdx = i;
      }
    } else if (tag === 'ul' || tag === 'ol') {
      if (goodLabelIdx >= 0 && goodListIdx < 0 && badLabelIdx < 0) {
        goodListIdx = i;
      } else if (badLabelIdx >= 0 && badListIdx < 0) {
        badListIdx = i;
      }
    }
  }

  // Need all 4 parts in the expected order
  if (goodLabelIdx < 0 || goodListIdx < 0 || badLabelIdx < 0 || badListIdx < 0) {
    return false;
  }
  if (
    !(goodLabelIdx < goodListIdx && goodListIdx < badLabelIdx && badLabelIdx < badListIdx)
  ) {
    return false;
  }

  // Preserve the original label text (KO or EN, whichever the source had)
  const goodLabelText = stripTrailingColon(
    extractText(siblings[goodLabelIdx] as Element).trim(),
  );
  const badLabelText = stripTrailingColon(
    extractText(siblings[badLabelIdx] as Element).trim(),
  );
  const goodList = siblings[goodListIdx] as Element;
  const badList = siblings[badListIdx] as Element;

  const wrapper: Element = {
    type: 'element',
    tagName: 'div',
    properties: { className: ['hb-tradeoffs-grid'] },
    children: [
      {
        type: 'element',
        tagName: 'section',
        properties: {
          className: ['hb-tradeoffs-grid__panel', 'hb-tradeoffs-grid__panel--good'],
        },
        children: [
          {
            type: 'element',
            tagName: 'h3',
            properties: { className: ['hb-tradeoffs-grid__label'] },
            children: [{ type: 'text', value: goodLabelText }],
          },
          goodList,
        ],
      },
      {
        type: 'element',
        tagName: 'section',
        properties: {
          className: ['hb-tradeoffs-grid__panel', 'hb-tradeoffs-grid__panel--bad'],
        },
        children: [
          {
            type: 'element',
            tagName: 'h3',
            properties: { className: ['hb-tradeoffs-grid__label'] },
            children: [{ type: 'text', value: badLabelText }],
          },
          badList,
        ],
      },
    ],
  };

  // Replace the 4 original elements with a single wrapper
  siblings.splice(goodLabelIdx, badListIdx - goodLabelIdx + 1, wrapper);
  return true;
}

export default function rehypeHandbookSectionMarkers() {
  return (tree: Root) => {
    // Pass 1: wrap §4 tradeoffs into a 2-column grid.
    visit(tree, 'element', (node: Element, index, parent) => {
      if (node.tagName !== 'h2' || !parent || index === undefined) return;
      const text = extractText(node).trim();
      if (TRADEOFFS_H2_PATTERNS.some((p) => p.test(text))) {
        wrapTradeoffsGrid(parent as Element, index);
      }
    });

    // Pass 2: tag §5/§6 lists with marker classes (existing behavior).
    visit(tree, 'element', (node: Element, index, parent) => {
      if (node.tagName !== 'h2' || !parent || index === undefined) return;

      const text = extractText(node).trim();
      const marker = MARKERS.find((m) => m.patterns.some((p) => p.test(text)));
      if (!marker) return;

      const siblings = (parent as Element).children;
      for (let i = index + 1; i < siblings.length; i++) {
        const sibling = siblings[i];
        if (sibling.type !== 'element') continue;
        const el = sibling as Element;
        if (el.tagName === 'h2') return;
        if (el.tagName === 'ul' || el.tagName === 'ol') {
          addClass(el, marker.className);
          return;
        }
      }
    });
  };
}
