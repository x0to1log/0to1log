/**
 * Rehype plugin that wraps handbook terms in article text with
 * <span class="handbook-term" data-slug="..." data-term="...">
 * for inline popup functionality.
 *
 * Only marks the first occurrence of each term. Skips headings, links, and code.
 * Exception: "관련 용어 / Related Terms" sections link ALL occurrences.
 */
import { visit, SKIP } from 'unist-util-visit';
import type { Root, Element, Text } from 'hast';

export interface TermEntry {
  slug: string;
  term: string; // display name (for data attribute)
}

/** Map of lowercase term/alias → TermEntry */
export type TermsMap = Map<string, TermEntry>;

const SKIP_TAGS = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'code', 'pre']);

// Section headers where ALL term occurrences should be linked (not just first)
// '함께' covers "함께 알면 좋은 용어" (KO related-terms heading)
const ALWAYS_LINK_KEYWORDS = ['관련', 'related', '함께'];

export default function rehypeHandbookTerms(termsMap: TermsMap) {
  return () => (tree: Root) => {
    if (!termsMap || termsMap.size === 0) return;

    // Build regex from all term keys (sorted by length desc for greedy match)
    const keys = Array.from(termsMap.keys()).sort((a, b) => b.length - a.length);
    const escaped = keys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const pattern = new RegExp(
      `(?<![a-zA-Z\\uAC00-\\uD7AF])(${escaped.join('|')})(?![a-zA-Z])`,
      'gi',
    );

    const matched = new Set<string>(); // track slugs already matched

    // Build parent map for ancestor chain lookup.
    // Visit ALL node types (not just 'element') so root's children are included,
    // enabling us to walk up to the document root and find h2 siblings there.
    const parentMap = new Map<any, any>();
    visit(tree, (node: any) => {
      if (node.children) {
        for (const child of node.children) {
          parentMap.set(child, node);
        }
      }
    });

    function hasSkipAncestor(node: any): boolean {
      let current = node;
      while (current) {
        const p = parentMap.get(current);
        if (!p) break;
        if (p.tagName && SKIP_TAGS.has(p.tagName)) return true;
        current = p;
      }
      return false;
    }

    /**
     * Walk up the ancestor chain from textParent, checking each ancestor's
     * preceding siblings for an h2 that matches ALWAYS_LINK_KEYWORDS.
     * This correctly handles text inside <p>, <li>, <strong>, etc.
     * Returns true when the nearest enclosing h2 is a "related terms" heading.
     */
    function isInRelatedSection(textParent: Element): boolean {
      let current: any = textParent;
      while (current) {
        const ancestor = parentMap.get(current);
        if (!ancestor) break;
        const siblings: any[] = ancestor.children || [];
        const pos = siblings.indexOf(current);
        for (let i = pos - 1; i >= 0; i--) {
          const sib = siblings[i];
          if (sib?.type === 'element' && sib.tagName === 'h2') {
            const hText = (sib.children || [])
              .filter((c: any) => c.type === 'text')
              .map((c: any) => c.value as string)
              .join('')
              .toLowerCase();
            return ALWAYS_LINK_KEYWORDS.some(kw => hText.includes(kw));
          }
        }
        current = ancestor;
      }
      return false;
    }

    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || index === null || index === undefined) return;
      const parentEl = parent as Element;

      // Skip text inside headings, links, code (check full ancestor chain)
      if (parentEl.tagName && SKIP_TAGS.has(parentEl.tagName)) return;
      if (hasSkipAncestor(node)) return;

      const inRelated = isInRelatedSection(parentEl);

      const text = node.value;
      const parts: (Text | Element)[] = [];
      let lastIndex = 0;

      let match: RegExpExecArray | null;
      pattern.lastIndex = 0;

      while ((match = pattern.exec(text)) !== null) {
        const matchedText = match[0];
        const entry = termsMap.get(matchedText.toLowerCase());
        if (!entry) continue;

        // In "related terms" section: always link. Elsewhere: first occurrence only.
        if (!inRelated && matched.has(entry.slug)) continue;
        matched.add(entry.slug);

        // Text before the match
        if (match.index > lastIndex) {
          parts.push({ type: 'text', value: text.slice(lastIndex, match.index) });
        }

        // The wrapped term
         parts.push({
           type: 'element',
           tagName: 'span',
           properties: {
             className: ['handbook-term'],
             'data-slug': entry.slug,
             'data-term': entry.term,
           },
           children: [{ type: 'text', value: matchedText }],
         } as Element);

        lastIndex = match.index + matchedText.length;
      }

      if (parts.length === 0) return; // no matches in this text node

      // Remaining text after last match
      if (lastIndex < text.length) {
        parts.push({ type: 'text', value: text.slice(lastIndex) });
      }

      // Replace the text node with the parts
      const siblings = (parent as Element).children;
      siblings.splice(index!, 1, ...parts);

      // Return SKIP to avoid revisiting newly inserted nodes
      return [SKIP, index! + parts.length] as any;
    });
  };
}
