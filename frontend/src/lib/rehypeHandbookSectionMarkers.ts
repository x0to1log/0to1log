import type { Root, Element, ElementContent } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Rehype plugin: shape specific handbook sections for custom styling.
 *
 * Two operations on handbook bodies:
 *
 * 1. §6 업계 대화 / Industry Communication → `ul.hb-section-dialogue`
 *    Basic "대화에서는 이렇게" / "How It Sounds in Conversation"
 *    also → `ul.hb-section-dialogue` (same quote-card layout).
 *    Simple class injection so CSS can target the list.
 *
 *    (§5 프로덕션 함정 used to get a `.hb-section-pitfalls` tag here too.
 *    The prompt now emits `- ❌ 실수: ... → ✅ 해결: ...` which is the
 *    same shape as Basic "자주 하는 오해", so §5 is rendered as a plain
 *    bullet list with no custom tagging or styling.)
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
    className: 'hb-section-dialogue',
    patterns: [
      /업계\s*대화/,
      /대화에서는/,
      /Industry\s+Communication/i,
      /How\s+It\s+Sounds/i,
    ],
  },
  {
    className: 'hb-related-terms',
    patterns: [
      /함께\s*읽으면/,
      /선행[·ㆍ]/,
      /Related\s+Reading/i,
      /Prerequisites/i,
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
 * Related-terms tag extraction. Matches the ` (TAG)` suffix pattern
 * the advisor prompt produces directly after the bold term name, e.g.
 *   "<strong>Term</strong> (기초) — description"
 *   "<strong>Term</strong> (prerequisite) — description"
 * Both KO friendly-Basic tags (기초/비슷/심화), KO Advanced tags
 * (선행/대안/확장), EN Basic tags (before/similar/next), and EN
 * Advanced tags (prerequisite/alternative/extension) are recognized.
 */
const RELATED_TAG_RE =
  /^\s*\((기초|비슷|심화|선행|대안|확장|before|similar|next|prerequisite|alternative|extension)\)\s*/;

/**
 * Transform a related-terms <li> so the inline `(tag)` marker becomes a
 * leading pill span + a content wrapper. Grid layout in CSS aligns the
 * pills into a fixed-width column so readers can eye-filter by tag.
 *
 * Input (loose list):
 *   <li><p><strong><a>Term</a></strong> (기초) — description</p></li>
 * Output:
 *   <li>
 *     <span class="hb-related-terms__tag" data-tag="기초">기초</span>
 *     <div class="hb-related-terms__content">
 *       <p><strong><a>Term</a></strong> — description</p>
 *     </div>
 *   </li>
 *
 * Leaves the <li> untouched if the tag pattern isn't found (graceful
 * degradation for older generations that didn't emit the tag yet).
 */
function extractRelatedTermTag(li: Element): void {
  // Find the first text node that sits immediately after a <strong>
  // and starts with ` (tag)`. Walk the tree one level deep — the
  // <strong> lives either directly under <li> (tight list) or under
  // a <p> child (loose list).
  const containers: Element[] = [li];
  for (const child of li.children) {
    if (child.type === 'element' && (child as Element).tagName === 'p') {
      containers.push(child as Element);
    }
  }

  for (const container of containers) {
    const kids = container.children;
    for (let i = 0; i < kids.length; i++) {
      const cur = kids[i];
      if (cur.type !== 'element') continue;
      if ((cur as Element).tagName !== 'strong') continue;

      const next = kids[i + 1];
      if (!next || next.type !== 'text') continue;

      const match = (next as { value: string }).value.match(RELATED_TAG_RE);
      if (!match) continue;

      const tag = match[1];
      // Strip the leading ` (tag) ` (or ` (tag)`) from the text node
      (next as { value: string }).value = (next as { value: string }).value.slice(
        match[0].length,
      );

      // Build the pill span
      const pill: Element = {
        type: 'element',
        tagName: 'span',
        properties: {
          className: ['hb-related-terms__tag'],
          'data-tag': tag,
        },
        children: [{ type: 'text', value: tag }],
      };

      // Wrap all existing <li> children in a content div, then prepend
      // the pill so CSS grid puts it in the fixed left column.
      const contentWrap: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['hb-related-terms__content'] },
        children: [...li.children],
      };
      li.children = [pill, contentWrap];
      return;
    }
  }
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

    // Pass 2: tag §6 dialogue lists with marker class.
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
          // Related-terms only: extract tag pills from each <li>.
          if (marker.className === 'hb-related-terms') {
            for (const liChild of el.children) {
              if (liChild.type === 'element' && (liChild as Element).tagName === 'li') {
                extractRelatedTermTag(liChild as Element);
              }
            }
          }
          return;
        }
      }
    });
  };
}
