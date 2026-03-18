/**
 * Rehype plugin that wraps handbook terms in article text with
 * <span class="handbook-term" data-slug="..." data-term="...">
 * for inline popup functionality.
 *
 * Only marks the first occurrence of each term. Skips headings, links, and code.
 */
import { visit } from 'unist-util-visit';
import type { Root, Element, Text } from 'hast';

export interface TermEntry {
  slug: string;
  term: string; // display name (for data attribute)
}

/** Map of lowercase term/alias → TermEntry */
export type TermsMap = Map<string, TermEntry>;

const SKIP_TAGS = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'code', 'pre']);

export default function rehypeHandbookTerms(termsMap: TermsMap) {
  return () => (tree: Root) => {
    if (!termsMap || termsMap.size === 0) return;

    // Build regex from all term keys (sorted by length desc for greedy match)
    const keys = Array.from(termsMap.keys()).sort((a, b) => b.length - a.length);
    const escaped = keys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    // Use Unicode-aware boundaries instead of \b (which doesn't work for Korean/CJK).
    // Lookbehind: not preceded by Latin or Korean letter (prevents partial word match).
    // Lookahead: not followed by Latin letter (Korean particles like 을/의/에서 are allowed).
    const pattern = new RegExp(
      `(?<![a-zA-Z\\uAC00-\\uD7AF])(${escaped.join('|')})(?![a-zA-Z])`,
      'gi',
    );

    const matched = new Set<string>(); // track slugs already matched

    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || index === null || index === undefined) return;
      const parentEl = parent as Element;

      // Skip text inside headings, links, code
      if (parentEl.tagName && SKIP_TAGS.has(parentEl.tagName)) return;

      // Check ancestor chain for skip tags
      // (visit doesn't give full ancestry, but parent check covers most cases)

      const text = node.value;
      const parts: (Text | Element)[] = [];
      let lastIndex = 0;

      let match: RegExpExecArray | null;
      pattern.lastIndex = 0;

      while ((match = pattern.exec(text)) !== null) {
        const matchedText = match[0];
        const entry = termsMap.get(matchedText.toLowerCase());
        if (!entry) continue;

        // Only first occurrence per term
        if (matched.has(entry.slug)) continue;
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
      return [visit.SKIP, index! + parts.length];
    });
  };
}
