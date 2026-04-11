import type { Root, Text, PhrasingContent } from 'mdast';
import { visit, SKIP } from 'unist-util-visit';

/**
 * Decide whether the content inside a $...$ pair looks like LaTeX math.
 *
 * True positives we want to catch (math):
 *   x_i, t^n, P(t_{1:n}), \frac{a}{b}, \sum_{i=1}^{n}, \mathrm{Attn},
 *   τ, θ, π, E=mc^2
 *
 * True negatives we want to leave alone (currency, plain text):
 *   $10, $/시간, $/hour, $50/GB
 *
 * Heuristic order matters: cheaper checks first.
 */
export function looksLikeMath(content: string): boolean {
  // 1. LaTeX command: backslash followed by letters (\frac, \sum, \mathrm, \theta, \mid, ...)
  if (/\\[a-zA-Z]+/.test(content)) return true;

  // 2. Subscript/superscript: _ or ^ followed by a letter, digit, or opening brace
  //    Matches: x_i, t^n, P^{...}, a_1, c^2
  if (/[_^][a-zA-Z0-9{]/.test(content)) return true;

  // 3. Greek letters in Unicode (commonly used in LLM/ML formulas)
  if (/[α-ωΑ-Ω]/.test(content)) return true;

  // 4. Equation pattern: equals sign with letters, short content (avoids matching long prose)
  if (/=/.test(content) && /[a-zA-Z]/.test(content) && content.length < 80) return true;

  return false;
}

/**
 * Match $...$ pairs on a single line. Lazy match: shortest content possible.
 */
const INLINE_MATH_RE = /\$([^$\n]+?)\$/g;

/**
 * Escape HTML attribute / text content special chars (defense in depth — the
 * LaTeX content goes inside a span that rehype-katex parses, but we still
 * escape the few chars that could break HTML structure if KaTeX errors out
 * and the raw content is exposed).
 */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Remark plugin: find math-looking $X$ pairs in text nodes and replace them
 * with mdast `html` nodes containing `<span class="math math-inline">X</span>`.
 *
 * Why direct HTML injection instead of `inlineMath` mdast nodes?
 * remark-rehype only knows the `inlineMath` node type if remark-math has
 * registered the handler for it during the SAME pipeline pass. With
 * singleDollarTextMath:false the handlers don't always activate. Direct
 * HTML injection is more robust: we produce the exact hast structure that
 * rehype-katex looks for (`.math-inline` class), bypassing the handler
 * registration uncertainty.
 *
 * Pipeline:
 *   markdown text "$P(t_{1:n})$"
 *   → this plugin → mdast `html` node `<span class="math math-inline">P(t_{1:n})</span>`
 *   → remarkRehype → hast (html node passes through as raw)
 *   → rehypeRaw → parses the html string into proper hast element
 *   → rehypeSanitize → keeps `<span class>` (allowed in our schema)
 *   → rehypeKatex → finds `.math-inline` and renders KaTeX MathML/HTML
 *
 * Currency-like patterns ($10, $/시간) don't match looksLikeMath() and stay
 * in text nodes as literal text.
 */
export default function remarkConvertInlineMathDollars() {
  return (tree: Root) => {
    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || typeof index !== 'number') return;
      if (!node.value.includes('$')) return;

      // Find all math matches in this text node
      const matches: Array<{ start: number; end: number; content: string }> = [];
      for (const m of node.value.matchAll(INLINE_MATH_RE)) {
        if (m.index === undefined) continue;
        const inner = m[1];
        if (!inner.trim()) continue;
        if (!looksLikeMath(inner)) continue;
        matches.push({
          start: m.index,
          end: m.index + m[0].length,
          content: inner,
        });
      }

      if (matches.length === 0) return;

      // Build replacement nodes: alternating text + html (math span)
      const newNodes: PhrasingContent[] = [];
      let cursor = 0;
      for (const match of matches) {
        if (match.start > cursor) {
          newNodes.push({
            type: 'text',
            value: node.value.slice(cursor, match.start),
          });
        }
        // Inject raw HTML span. rehype-raw parses this into hast,
        // rehype-katex then renders the KaTeX content.
        newNodes.push({
          type: 'html',
          value: `<span class="math math-inline">${escapeHtml(match.content)}</span>`,
        });
        cursor = match.end;
      }
      if (cursor < node.value.length) {
        newNodes.push({
          type: 'text',
          value: node.value.slice(cursor),
        });
      }

      // Replace the original text node with the new sequence
      parent.children.splice(index, 1, ...newNodes);

      // Skip past the inserted nodes so we don't re-visit them
      return [SKIP, index + newNodes.length];
    });
  };
}
