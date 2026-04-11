import { localField } from '../handbookUtils';
import { renderMarkdown, renderMarkdownWithTerms, renderHandbookMarkdown, type TermsMap } from '../markdown';
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
  definition: string;
  basic_plain: string;
}

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
      .select('*')
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
  let isBookmarked = false;
  let learningStatus: string | null = null;
  let learningProgressId: string | null = null;
  let handbookTermsJson: Record<string, HandbookTermJsonEntry> = {};

  if (publicSupabase && term) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;

    // Build handbook terms map for inline linking (exclude self to prevent self-link)
    const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';
    const hbTermsRes = await publicSupabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, term_full, categories, ${definitionField}, body_basic_ko, body_basic_en`)
      .eq('status', 'published')
      .neq('slug', pageSlug)  // exclude self
      .limit(200);

    const handbookTermsMap: TermsMap = new Map();
    for (const entry of hbTermsRes.data ?? []) {
      const termEntry = { slug: entry.slug, term: entry.term };
      handbookTermsMap.set(entry.term.toLowerCase(), termEntry);
      if (entry.korean_name) handbookTermsMap.set(entry.korean_name.toLowerCase(), termEntry);
      handbookTermsJson[entry.slug] = {
        term: entry.term,
        korean_name: entry.korean_name || '',
        term_full: (entry as any).term_full || '',
        categories: entry.categories || [],
        definition: (entry as any)[definitionField] || '',
        basic_plain: locale === 'ko'
          ? (entry as any).body_basic_ko || ''
          : (entry as any).body_basic_en || '',
      };
    }
    const hasTerms = handbookTermsMap.size > 0;
    const renderMd = hasTerms
      ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
      : (md: string) => renderHandbookMarkdown(md);

    // Run markdown rendering and DB queries in parallel — they don't depend on each other.
    // Both Basic and Advanced go through renderMd so auto-linkification of
    // other handbook terms fires in both bodies (otherwise Advanced §7
    // related-terms links would never become clickable popups).
    const [basicHtml, advancedHtml, articlesRes, recentNewsRes, relatedRes, sameCatRes, bmRes, lpRes] = await Promise.all([
      bodyBasic ? renderMd(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderMd(bodyAdvanced) : Promise.resolve(''),
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
      authSupabase
        ? authSupabase
            .from('user_bookmarks')
            .select('id')
            .eq('user_id', locals.user.id)
            .eq('item_type', 'term')
            .eq('item_id', term.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
      authSupabase
        ? authSupabase
            .from('learning_progress')
            .select('id, status')
            .eq('user_id', locals.user.id)
            .eq('term_id', term.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
    ]);

    if (basicHtml) levelHtmlMap.basic = basicHtml;
    if (advancedHtml) levelHtmlMap.advanced = advancedHtml;

    // Use tag-matched articles, fall back to recent news
    relatedArticles = (articlesRes.data?.length ? articlesRes.data : recentNewsRes.data) ?? [];

    relatedTerms = relatedRes.data ?? [];
    sameCategoryTerms = sameCatRes.data ?? [];
    isBookmarked = !!bmRes.data;
    learningStatus = lpRes.data?.status ?? null;
    learningProgressId = lpRes.data?.id ?? null;
  } else {
    // No term found — still render markdown if bodies exist
    const [basicHtml, advancedHtml] = await Promise.all([
      bodyBasic ? renderHandbookMarkdown(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderHandbookMarkdown(bodyAdvanced) : Promise.resolve(''),
    ]);
    if (basicHtml) levelHtmlMap.basic = basicHtml;
    if (advancedHtml) levelHtmlMap.advanced = advancedHtml;
  }

  const preferredLevel = previewMode ? (previewLevel || 'basic') : (locals.profile?.handbook_level || 'basic');
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
    isBookmarked: previewMode ? false : isBookmarked,
    learningStatus: previewMode ? null : learningStatus,
    learningProgressId: previewMode ? null : learningProgressId,
    // Level-independent redesign fields (2026-04-10)
    heroNewsContext,
    references,
  };
}
