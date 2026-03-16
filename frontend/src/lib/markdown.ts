import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import rehypeStringify from 'rehype-stringify';
import rehypeHandbookTerms, { type TermsMap } from './rehypeHandbookTerms';

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

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkMath)
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeKatex)
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeStringify);

export async function renderMarkdown(md: string): Promise<string> {
  const result = await processor.process(md);
  return String(result);
}

export { type TermsMap } from './rehypeHandbookTerms';

export async function renderMarkdownWithTerms(
  md: string,
  termsMap: TermsMap,
): Promise<string> {
  const termsProcessor = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkMath)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeKatex)
    .use(rehypeHandbookTerms(termsMap))
    .use(rehypeSanitize, sanitizeSchemaWithTerms)
    .use(rehypeStringify);

  const result = await termsProcessor.process(md);
  return String(result);
}
