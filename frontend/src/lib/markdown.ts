import { createHash } from 'node:crypto';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import rehypeShiki from '@shikijs/rehype';
import { createCssVariablesTheme } from 'shiki';
import rehypeStringify from 'rehype-stringify';
import rehypeHandbookTerms, { type TermsMap } from './rehypeHandbookTerms';
import rehypeCodeWindow from './rehypeCodeWindow';
import rehypeHandbookSectionMarkers from './rehypeHandbookSectionMarkers';
import remarkConvertInlineMathDollars from './remarkConvertInlineMathDollars';
import { visit } from 'unist-util-visit';

/** Strip <del> tags — LLM uses ~~ for approximate values, not strikethrough. */
function rehypeStripDel() {
  return (tree: any) => {
    visit(tree, 'element', (node: any, _index: any, parent: any) => {
      if (node.tagName === 'del' && parent?.children) {
        const idx = parent.children.indexOf(node);
        if (idx !== -1) {
          parent.children.splice(idx, 1, ...node.children);
        }
      }
    });
  };
}

const katexTagNames = [
  'math', 'semantics', 'annotation', 'mrow', 'mi', 'mo', 'mn',
  'msup', 'msub', 'mfrac', 'mtext', 'mspace', 'msqrt', 'mroot',
  'mtable', 'mtr', 'mtd', 'munder', 'mover', 'munderover', 'menclose',
];

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames || []), ...katexTagNames],
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code || []), 'className'],
    span: [...(defaultSchema.attributes?.span || []), 'className', 'style', 'aria-hidden'],
    div: [...(defaultSchema.attributes?.div || []), 'className', 'style', 'aria-hidden'],
    annotation: [...(defaultSchema.attributes?.annotation || []), 'encoding'],
    math: [...(defaultSchema.attributes?.math || []), 'xmlns'],
  },
};

const sanitizeSchemaWithTerms = {
  ...sanitizeSchema,
  attributes: {
    ...sanitizeSchema.attributes,
    span: [...(sanitizeSchema.attributes?.span || []), 'data-slug', 'data-term'],
  },
};

const cssVarTheme = createCssVariablesTheme({
  name: 'css-variables',
  variablePrefix: '--shiki-',
  variableDefaults: {},
  fontStyle: true,
});

// Restrict Shiki to commonly used languages (24 instead of 332 bundled).
// Reduces cold-start initialization by ~200-400ms. Unsupported languages
// fall back to plain text rendering.
const SHIKI_LANGS = [
  'javascript', 'typescript', 'python', 'bash', 'shell',
  'json', 'html', 'css', 'markdown', 'yaml', 'toml',
  'sql', 'go', 'rust', 'java', 'kotlin', 'swift',
  'c', 'cpp', 'csharp', 'ruby', 'php', 'text',
];

/** Shiki config — matches Astro's shikiConfig in astro.config.mjs */
const shikiOptions = {
  theme: cssVarTheme,
  langs: SHIKI_LANGS,
  transformers: [
    {
      name: 'language-label',
      pre(this: any, node: any) {
        const lang = this?.options?.lang;
        if (lang) {
          node.properties ??= {};
          node.properties['data-language'] = lang;
        }
      },
    },
  ],
};

// ---------------------------------------------------------------------------
// Render cache — avoids re-rendering identical content across requests.
// Map preserves insertion order; oldest entry is evicted when limit is reached.
// ---------------------------------------------------------------------------
const htmlCache = new Map<string, string>();
const CACHE_MAX = 150;

function contentHash(input: string): string {
  return createHash('md5').update(input).digest('hex');
}

function getCachedOrRender(
  cacheKey: string,
  renderFn: () => Promise<string>,
): Promise<string> {
  const cached = htmlCache.get(cacheKey);
  if (cached !== undefined) return Promise.resolve(cached);
  return renderFn().then((html) => {
    if (htmlCache.size >= CACHE_MAX) {
      htmlCache.delete(htmlCache.keys().next().value!);
    }
    htmlCache.set(cacheKey, html);
    return html;
  });
}

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })
  .use(remarkMath, { singleDollarTextMath: false })
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeStripDel)
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeKatex)
  .use(rehypeShiki, shikiOptions as any)
  .use(rehypeCodeWindow)
  .use(rehypeStringify);

export async function renderMarkdown(md: string): Promise<string> {
  return getCachedOrRender(contentHash(md), async () => String(await processor.process(md)));
}

// Handbook-specific processor: block math ($$...$$) only
// singleDollarTextMath disabled to avoid currency conflicts ($/hour, $10/GB).
// remarkConvertInlineMathDollars runs BEFORE remarkMath to rewrite math-looking
// $X$ pairs as $$X$$ so inline LaTeX still renders without re-enabling
// singleDollarTextMath (currency stays untouched because the classifier
// recognizes only LaTeX patterns).
// Code blocks are collapsible by default — Advanced readers opt into seeing
// long code dumps instead of scrolling past them.
// rehypeHandbookSectionMarkers tags §5 pitfalls list for CSS callout styling.
const handbookProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })
  .use(remarkConvertInlineMathDollars)
  .use(remarkMath, { singleDollarTextMath: false })
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeStripDel)
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeKatex)
  .use(rehypeShiki, shikiOptions as any)
  .use(rehypeHandbookSectionMarkers)
  .use(rehypeCodeWindow, { collapsible: true })
  .use(rehypeStringify);

/**
 * LLM output for §4 trade-offs puts `이럴 때 적합:` / `이럴 때 부적합:`
 * (or `Suitable:` / `Unsuitable:`) on a line by itself, but CommonMark
 * treats an unindented non-blank line after a list item as lazy list
 * continuation, so "부적합:" gets swallowed into the last `<li>` and the
 * two bullet lists merge into one. Force a blank line on both sides of
 * these labels before parsing so they become standalone paragraphs and
 * the p/ul/p/ul shape survives into hast for the trade-offs grid plugin.
 */
const TRADEOFFS_LABEL_RE =
  /^[ \t]*((?:이럴\s*때\s*[부]?적합|(?:Un)?suitable)\s*[:：])[ \t]*$/gim;

function normalizeTradeoffsLabels(md: string): string {
  return md.replace(TRADEOFFS_LABEL_RE, '\n$1\n');
}

export async function renderHandbookMarkdown(md: string): Promise<string> {
  return getCachedOrRender('hb:' + contentHash(md), async () =>
    String(await handbookProcessor.process(normalizeTradeoffsLabels(md))),
  );
}

export { type TermsMap } from './rehypeHandbookTerms';

const termsProcessorCache = new WeakMap<TermsMap, any>();

export async function renderMarkdownWithTerms(
  md: string,
  termsMap: TermsMap,
): Promise<string> {
  // Cache key: content hash + termsMap fingerprint (slug list hash)
  const slugs = [...new Set([...termsMap.values()].map((v) => v.slug))].sort().join(',');
  const cacheKey = contentHash(md) + ':' + contentHash(slugs);

  return getCachedOrRender(cacheKey, async () => {
    let termsProcessor = termsProcessorCache.get(termsMap);
    if (!termsProcessor) {
      termsProcessor = unified()
        .use(remarkParse)
        .use(remarkGfm, { singleTilde: false })
        .use(remarkConvertInlineMathDollars)
        .use(remarkMath, { singleDollarTextMath: false })
        .use(remarkRehype, { allowDangerousHtml: true })
        .use(rehypeRaw)
        .use(rehypeStripDel)
        .use(rehypeHandbookTerms(termsMap))
        .use(rehypeSanitize, sanitizeSchemaWithTerms)
        .use(rehypeKatex)
        .use(rehypeShiki, shikiOptions as any)
        .use(rehypeCodeWindow)
        .use(rehypeStringify);
      termsProcessorCache.set(termsMap, termsProcessor);
    }

    return String(await termsProcessor.process(md));
  });
}
