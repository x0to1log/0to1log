type TagStyle = 'canonical' | 'display';

interface NormalizeProductTagsOptions {
  style: TagStyle;
  maxCount?: number;
}

interface ProductTagSource {
  tags?: string[] | null;
  tags_ko?: string[] | null;
}

function normalizeCanonicalTag(tag: string): string {
  return tag
    .trim()
    .replace(/^#+/, '')
    .toLowerCase()
    .replace(/[_\s]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function normalizeDisplayTag(tag: string): string {
  return tag
    .trim()
    .replace(/^#+/, '')
    .replace(/\s+/g, ' ');
}

export function normalizeProductTags(
  input: unknown,
  options: NormalizeProductTagsOptions,
): string[] {
  if (!Array.isArray(input)) return [];

  const maxCount = options.maxCount ?? 3;
  const seen = new Set<string>();
  const output: string[] = [];

  for (const item of input) {
    if (typeof item !== 'string') continue;
    const tag = options.style === 'canonical'
      ? normalizeCanonicalTag(item)
      : normalizeDisplayTag(item);
    if (!tag) continue;

    const key = tag.toLocaleLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    output.push(tag);
    if (output.length >= maxCount) break;
  }

  return output;
}

export function resolveLocalizedProductTags(
  source: ProductTagSource,
  locale: 'en' | 'ko',
): string[] {
  const canonicalTags = normalizeProductTags(source.tags ?? [], { style: 'canonical' });
  if (locale === 'ko') {
    const koreanTags = normalizeProductTags(source.tags_ko ?? [], { style: 'display' });
    if (koreanTags.length > 0) return koreanTags;
  }
  return canonicalTags;
}
