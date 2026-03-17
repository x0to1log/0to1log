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
    span: [...(sanitizeSchema.attributes?.span || []), 'dataSlug', 'dataTerm'],
  },
};

const cssVarTheme = createCssVariablesTheme({
  name: 'css-variables',
  variablePrefix: '--shiki-',
  variableDefaults: {},
  fontStyle: true,
});

/** Shiki config — matches Astro's shikiConfig in astro.config.mjs */
const shikiOptions = {
  theme: cssVarTheme,
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

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkMath)
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeKatex)
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeShiki, shikiOptions)
  .use(rehypeCodeWindow)
  .use(rehypeStringify);

export async function renderMarkdown(md: string): Promise<string> {
  const result = await processor.process(md);
  return String(result);
}

export { type TermsMap } from './rehypeHandbookTerms';

const termsProcessorCache = new WeakMap<TermsMap, ReturnType<typeof unified>>();

export async function renderMarkdownWithTerms(
  md: string,
  termsMap: TermsMap,
): Promise<string> {
  let termsProcessor = termsProcessorCache.get(termsMap);
  if (!termsProcessor) {
    termsProcessor = unified()
      .use(remarkParse)
      .use(remarkGfm)
      .use(remarkMath)
      .use(remarkRehype, { allowDangerousHtml: true })
      .use(rehypeRaw)
      .use(rehypeKatex)
      .use(rehypeHandbookTerms(termsMap))
      .use(rehypeSanitize, sanitizeSchemaWithTerms)
      .use(rehypeShiki, shikiOptions)
      .use(rehypeCodeWindow)
      .use(rehypeStringify);
    termsProcessorCache.set(termsMap, termsProcessor);
  }

  const result = await termsProcessor.process(md);
  return String(result);
}
