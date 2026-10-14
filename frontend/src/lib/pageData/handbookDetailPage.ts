import { localField } from '../handbookUtils';
import { renderMarkdown, renderMarkdownWithTerms, renderHandbookMarkdown, type TermsMap } from '../markdown';
import { fetchPublicTermIndex } from './publicTermIndex';
import { getAuthorizedSupabase, getPublicSupabase, type DetailPageContext } from './shared';

interface HandbookDetailPageContext extends DetailPageContext {
  previewLevel?: string | null;
}

export interface ReferenceItem {
  title: string;
  authors?: string;
  year?: number;
  venue?: string;
  type: 'paper' | 'docs' | 'code' | 'blog' | 'wiki' | 'book';
  url: string;
  tier: 'primary' | 'secondary';
  annotation: string;
}

interface HandbookTermJsonEntry {
  term: string;
  korean_name: string;
  term_full: string;
  categories: string[];
  summary: string;
  definition: string;
  basic_plain: string;
}

export const HANDBOOK_DETAIL_PUBLIC_COLUMNS = [
  'id', 'status', 'term', 'slug', 'korean_name', 'term_full', 'categories',
  'definition_ko', 'definition_en', 'body_basic_ko', 'body_basic_en',
  'body_advanced_ko', 'body_advanced_en', 'hero_news_context_ko',
  'hero_news_context_en', 'references_ko', 'references_en', 'related_term_slugs',
].join(', ');

export async function getHandbookDetailPageData({
  locale,
  slug,
  previewMode,
  locals,
  previewLevel = null,
}: HandbookDetailPageContext) {
  const pageSlug = slug;
  const publicSupabase = getPublicSupabase();
  const previewSupabase = previewMode ? getAuthorizedSupabase(locals.accessToken) : null;
  const detailSupabase = previewSupabase || publicSupabase;

  let term: any = null;
  let termError: string | null = null;

  if (detailSupabase && slug) {
    let query = detailSupabase
      .from('handbook_terms')
      .select(HANDBOOK_DETAIL_PUBLIC_COLUMNS)
      .eq('slug', pageSlug);

    if (!previewMode) {
      query = query.eq('status', 'published');
    }

    const { data, error } = await query.single();

    if (error && error.code !== 'PGRST116') {
      termError = error.message;
    } else {
      term = data;
    }
  }

  const definition = term ? localField(term, 'definition', locale) : '';
  const bodyBasic = term ? localField(term, 'body_basic', locale) : '';
  const bodyAdvanced = term ? localField(term, 'body_advanced', locale) : '';

  // Level-independent fields (2026-04-10 redesign).
  // Text fields use localField (KO fallback). references is JSONB so direct access with manual fallback.
  const heroNewsContext = term ? localField(term, 'hero_news_context', locale) : '';
  const references: ReferenceItem[] | null = term
    ? ((locale === 'ko' ? term.references_ko : term.references_en)
       ?? (locale === 'ko' ? term.references_en : term.references_ko)
       ?? null)
    : null;

  const levelHtmlMap: Record<string, string> = {};
  let relatedArticles: any[] = [];
  let relatedTerms: any[] = [];
  let sameCategoryTerms: any[] = [];
  let handbookTermsJson: Record<string, HandbookTermJsonEntry> = {};

  if (publicSupabase && term) {
    // Start the page queries first; they don't depend on the term index.
    // Per-user state (bookmark, learning progress) is hydrated client-side so
    // this HTML stays CDN-cacheable.
    const queriesPromise = Promise.all([
      publicSupabase
        .from('news_posts')
        .select('title, slug, category, published_at, post_type')
        .eq('status', 'published')
        .eq('locale', locale)
        .or(`tags.cs.{${term.term.toLowerCase()}},title.ilike.%${term.term}%`)
        .order('published_at', { ascending: false })
        .limit(5),
      // Pre-fetch recent news for backfill (avoids sequential query later)
      publicSupabase
        .from('news_posts')
        .select('title, slug, category, published_at, post_type')
        .eq('status', 'published')
        .eq('locale', locale)
        .order('published_at', { ascending: false })
        .limit(3),
      term.related_term_slugs?.length
        ? publicSupabase
            .from('handbook_terms')
            .select('term, slug, korean_name')
            .eq('status', 'published')
            .in('slug', term.related_term_slugs)
        : Promise.resolve({ data: null }),
      term.categories?.length
        ? publicSupabase
            .from('handbook_terms')
            .select('term, slug, korean_name')
            .eq('status', 'published')
            .neq('slug', pageSlug)
            .overlaps('categories', term.categories)
            .limit(5)
        : Promise.resolve({ data: null }),
    ]);

    // Build handbook terms map for inline linking (exclude self to prevent self-link)
    const handbookTerms = (await fetchPublicTermIndex(publicSupabase, locale))
      .filter((entry) => entry.slug !== pageSlug);

    const handbookTermsMap: TermsMap = new Map();
    for (const entry of handbookTerms) {
      const termEntry = { slug: entry.slug, term: entry.term };
      handbookTermsMap.set(entry.term.toLowerCase(), termEntry);
      if (entry.korean_name) handbookTermsMap.set(entry.korean_name.toLowerCase(), termEntry);
      handbookTermsJson[entry.slug] = {
        term: entry.term,
        korean_name: entry.korean_name || '',
        term_full: entry.term_full || '',
        categories: entry.categories || [],
        summary: entry.summary || '',
        definition: entry.definition || '',
        basic_plain: entry.basic_plain || '',
      };
    }
    const hasTerms = handbookTermsMap.size > 0;
    const renderMd = hasTerms
      ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
      : (md: string) => renderHandbookMarkdown(md);

    // Both Basic and Advanced go through renderMd so auto-linkification of
    // other handbook terms fires in both bodies (otherwise Advanced §7
    // related-terms links would never become clickable popups).
    const [basicHtml, advancedHtml, [articlesRes, recentNewsRes, relatedRes, sameCatRes]] = await Promise.all([
      bodyBasic ? renderMd(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderMd(bodyAdvanced) : Promise.resolve(''),
      queriesPromise,
    ]);

    if (basicHtml) levelHtmlMap.basic = basicHtml;
    if (advancedHtml) levelHtmlMap.advanced = advancedHtml;

    // Use tag-matched articles, fall back to recent news
    relatedArticles = (articlesRes.data?.length ? articlesRes.data : recentNewsRes.data) ?? [];

    relatedTerms = relatedRes.data ?? [];
    sameCategoryTerms = sameCatRes.data ?? [];
  } else {
    // No term found — still render markdown if bodies exist
    const [basicHtml, advancedHtml] = await Promise.all([
      bodyBasic ? renderHandbookMarkdown(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderHandbookMarkdown(bodyAdvanced) : Promise.resolve(''),
    ]);
    if (basicHtml) levelHtmlMap.basic = basicHtml;
    if (advancedHtml) levelHtmlMap.advanced = advancedHtml;
  }

  // Saved reader level is applied client-side (session.ts) to keep HTML cacheable.
  const preferredLevel = previewMode ? (previewLevel || 'basic') : 'basic';
  const activeLevel = levelHtmlMap[preferredLevel] ? preferredLevel : (levelHtmlMap.basic ? 'basic' : 'advanced');
  const htmlContent = levelHtmlMap[activeLevel] || '';
  const showLevelSwitcher = Object.keys(levelHtmlMap).length > 1;

  return {
    term,
    termError,
    definition,
    levelHtmlMap,
    activeLevel,
    htmlContent,
    showLevelSwitcher,
    handbookTermsJson,
    relatedArticles,
    relatedTerms,
    sameCategoryTerms,
    // Level-independent redesign fields (2026-04-10)
    heroNewsContext,
    references,
  };
}
