import { localField } from '../handbookUtils';
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { getAuthorizedSupabase, getPublicSupabase, type DetailPageContext } from './shared';

// Question-style labels for collapsed sections — maps section keyword to curiosity question
const QUESTION_MAP_KO: Record<string, string> = {
  '어디서': '실제로 어디서 쓰여요?',
  '주의': '자주 하는 실수가 뭐예요?',
  '대화': '회의에서 어떻게 말해요?',
  '함께': '다음에 뭘 공부하면 좋아요?',
};
const QUESTION_MAP_EN: Record<string, string> = {
  'where': 'Where is it actually used?',
  'precaution': 'What mistakes do people make?',
  'communication': 'How do you talk about it?',
  'related': 'What should I learn next?',
};

/**
 * Wrap handbook basic HTML sections 5-8 in a collapsible block.
 * Splits at the 5th <h2> tag — first 4 sections stay visible, rest go into <details>.
 * Collapsed sections show question-style labels to drive curiosity clicks.
 */
function wrapLearnMore(html: string, locale: string): string {
  if (!html) return html;
  const h2Pattern = /<h2[\s>]/gi;
  const matches: number[] = [];
  let m: RegExpExecArray | null;
  while ((m = h2Pattern.exec(html)) !== null) {
    matches.push(m.index);
  }
  // Need at least 5 h2s to split (4 core + 1+ learn more)
  if (matches.length < 5) return html;
  const splitIndex = matches[4]; // 5th h2 (0-indexed: 4)
  const corePart = html.slice(0, splitIndex);
  const learnMorePart = html.slice(splitIndex);

  const questionMap = locale === 'ko' ? QUESTION_MAP_KO : QUESTION_MAP_EN;
  const bulbIcon = '<svg class="learn-more-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>';
  const summaryLabel = locale === 'ko'
    ? `이런 것도 궁금하지 않으세요? ${bulbIcon}`
    : `Curious about more? ${bulbIcon}`;

  // Extract section titles and convert to question-style labels
  const titlePattern = /<h2[^>]*>(.*?)<\/h2>/gi;
  const questions: string[] = [];
  let tm: RegExpExecArray | null;
  while ((tm = titlePattern.exec(learnMorePart)) !== null) {
    const rawTitle = tm[1].replace(/<[^>]+>/g, '').trim();
    // Find matching keyword and use question version
    const titleLower = rawTitle.toLowerCase();
    const keyword = Object.keys(questionMap).find(k => titleLower.includes(k));
    questions.push(keyword ? questionMap[keyword] : rawTitle);
  }

  const questionsHtml = questions.length > 0
    ? `<ul class="learn-more-questions">${questions.map(q => `<li class="learn-more-question">${q}</li>`).join('')}</ul>`
    : '';

  return `${corePart}<details class="handbook-learn-more"><summary><div class="learn-more-header"><span class="learn-more-chevron">▶</span> ${summaryLabel}</div>${questionsHtml}</summary>${learnMorePart}</details>`;
}

interface HandbookDetailPageContext extends DetailPageContext {
  previewLevel?: string | null;
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

  const levelHtmlMap: Record<string, string> = {};
  let relatedArticles: any[] = [];
  let relatedTerms: any[] = [];
  let sameCategoryTerms: any[] = [];
  let isBookmarked = false;
  let learningStatus: string | null = null;
  let learningProgressId: string | null = null;
  let handbookTermsJson: Record<string, { term: string; korean_name: string; categories: string[]; definition: string }> = {};

  if (publicSupabase && term) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;

    // Build handbook terms map for inline linking (exclude self to prevent self-link)
    const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';
    const hbTermsRes = await publicSupabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, categories, ${definitionField}`)
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
        categories: entry.categories || [],
        definition: (entry as any)[definitionField] || '',
      };
    }
    const hasTerms = handbookTermsMap.size > 0;
    const renderMd = hasTerms
      ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
      : (md: string) => renderMarkdown(md);

    // Run markdown rendering and DB queries in parallel — they don't depend on each other
    const [basicHtml, advancedHtml, articlesRes, recentNewsRes, relatedRes, sameCatRes, bmRes, lpRes] = await Promise.all([
      bodyBasic ? renderMd(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderMd(bodyAdvanced) : Promise.resolve(''),
      publicSupabase
        .from('news_posts')
        .select('title, slug, category, published_at')
        .eq('status', 'published')
        .eq('locale', locale)
        .contains('tags', [term.term.toLowerCase()])
        .limit(3),
      // Pre-fetch recent news for backfill (avoids sequential query later)
      publicSupabase
        .from('news_posts')
        .select('title, slug, category, published_at')
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

    if (basicHtml) levelHtmlMap.basic = wrapLearnMore(basicHtml, locale);
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
      bodyBasic ? renderMarkdown(bodyBasic) : Promise.resolve(''),
      bodyAdvanced ? renderMarkdown(bodyAdvanced) : Promise.resolve(''),
    ]);
    if (basicHtml) levelHtmlMap.basic = wrapLearnMore(basicHtml, locale);
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
  };
}
