import type { Root, Text } from 'mdast';
import { visit } from 'unist-util-visit';

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
 *
 * Excludes:
 * - Cross-line content (no \n inside)
 * - Empty content ($$  is handled by remark-math directly)
 * - Already-double-dollar (the regex matches single-pair, leaves $$X$$ alone)
 */
const INLINE_DOLLAR_RE = /\$([^$\n]+?)\$/g;

/**
 * Remark plugin: convert math-looking $X$ pairs to $$X$$ inside text nodes.
 *
 * Runs BEFORE remark-math. The downstream parser is configured with
 * singleDollarTextMath: false, so:
 * - $$X$$ pairs we produce → parsed as math (inline if mid-paragraph)
 * - $X$ pairs we leave alone → stay as literal text
 *
 * Currency-like patterns ($10, $/시간) are left alone because they don't
 * match looksLikeMath() heuristics.
 *
 * Why a preprocessor instead of toggling singleDollarTextMath: true?
 * Because that re-introduces the GPU $/시간 currency-vs-math conflict
 * (commit 6b5f1f5 disabled it for that reason). This plugin lets math
 * and currency coexist by classifying content shape, not delimiter shape.
 */
export default function remarkConvertInlineMathDollars() {
  return (tree: Root) => {
    visit(tree, 'text', (node: Text) => {
      if (!node.value.includes('$')) return;

      let changed = false;
      const newValue = node.value.replace(INLINE_DOLLAR_RE, (match, inner) => {
        if (!inner.trim()) return match;
        if (looksLikeMath(inner)) {
          changed = true;
          return `$$${inner}$$`;
        }
        return match;
      });

      if (changed) {
        node.value = newValue;
      }
    });
  };
}
