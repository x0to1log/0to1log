import { getArticleFocusItems } from '../articleRail';
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { getAuthorizedSupabase, getDefinitionField, getPublicSupabase, type DetailPageContext } from './shared';

interface NewsDetailPageContext extends DetailPageContext {
  previewPersona?: string | null;
}

function hostnameLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return 'Source';
  }
}

function normalizeSourceCards(post: any): Array<{
  id: string;
  title: string;
  publisher: string;
  url: string;
  published_at: string;
  evidence_snippet: string;
  claim_ids: string[];
}> {
  const cards = Array.isArray(post?.source_cards) ? post.source_cards : [];
  if (cards.length > 0) {
    return cards.map((card: any, index: number) => ({
      id: card.id || `src-${index + 1}`,
      title: card.title || hostnameLabel(card.url || ''),
      publisher: card.publisher || hostnameLabel(card.url || ''),
      url: card.url || '',
      published_at: card.published_at || '',
      evidence_snippet: card.evidence_snippet || '',
      claim_ids: Array.isArray(card.claim_ids) ? card.claim_ids : [],
    }));
  }

  const urls = Array.isArray(post?.source_urls) ? post.source_urls : [];
  return urls.map((url: string, index: number) => ({
    id: `src-${index + 1}`,
    title: hostnameLabel(url),
    publisher: hostnameLabel(url),
    url,
    published_at: '',
    evidence_snippet: '',
    claim_ids: [],
  }));
}

function applySourceCitations(html: string): string {
  if (!html) return html;
  return html.replace(/\[\[(\d+)\]\]/g, (_match, index) => {
    return `<sup class="newsprint-citation"><a href="#source-card-${index}">${index}</a></sup>`;
  });
}

export async function getNewsDetailPageData({
  locale,
  slug,
  previewMode,
  locals,
  previewPersona = null,
}: NewsDetailPageContext) {
  const pageSlug = slug;
  const publicSupabase = getPublicSupabase();
  const previewSupabase = previewMode ? getAuthorizedSupabase(locals.accessToken) : null;
  const detailSupabase = previewSupabase || publicSupabase;

  let post: any = null;
  let postError: string | null = null;

  if (detailSupabase && slug) {
    let query = detailSupabase
      .from('news_posts')
      .select('*')
      .eq('slug', pageSlug)
      .eq('locale', locale);

    if (!previewMode) {
      query = query.eq('status', 'published');
    }

    const { data, error } = await query.single();

    if (error && error.code !== 'PGRST116') {
      postError = error.message;
    } else {
      post = data;
    }
  }

  let focusItems: string[] = [];
  let articleData: any = undefined;
  let nextPost: { title: string; slug: string; category: string | null } | null = null;
  let pairedSlug: string | null = null;
  let similarPosts: { post_id: string; slug: string; title: string; category: string; post_type?: string | null }[] = [];
  let isBookmarked = false;
  let isLiked = false;
  let likeCount = 0;
  let commentCount = 0;
  let handbookTermsMap: TermsMap = new Map();
  let handbookTermsJson: Record<string, any> = {};
  let analysisHtml = '';
  let availablePersonas: string[] = [];
  let factPack: Array<{ id: string; claim: string; why_it_matters: string; source_ids: string[]; confidence: string }> = [];
  let sourceCards: Array<{ id: string; title: string; publisher: string; url: string; published_at: string; evidence_snippet: string; claim_ids: string[] }> = [];

  if (post && publicSupabase) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';
    const definitionField = getDefinitionField(locale);

    // Fire FastAPI call early — don't await, collect result later during markdown rendering
    const similarPostsPromise = (import.meta.env.FASTAPI_URL && post.id)
      ? fetch(
          `${import.meta.env.FASTAPI_URL}/api/recommendations/similar?post_id=${post.id}&locale=${locale}`,
          { signal: AbortSignal.timeout(1500) },
        ).then(res => res.ok ? res.json() : []).catch(() => [])
      : Promise.resolve([]);

    // Pre-fetch backfill candidates alongside DB queries (avoids sequential query later)
    const [
      nextRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
      bookmarkRes,
      likeRes,
      hbTermsRes,
      backfillRes,
    ] = await Promise.all([
      post.published_at
        ? publicSupabase
            .from('news_posts')
            .select('title, slug, category')
            .eq('status', 'published')
            .eq('locale', locale)
            .lt('published_at', post.published_at)
            .order('published_at', { ascending: false })
            .limit(1)
            .single()
        : Promise.resolve({ data: null }),
      post.translation_group_id
        ? (previewMode && previewSupabase ? previewSupabase : publicSupabase)
            .from('news_posts')
            .select('slug')
            .eq('translation_group_id', post.translation_group_id)
            .eq('locale', pairedLocale)
            .single()
        : Promise.resolve({ data: null }),
      publicSupabase
        .from('news_likes')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
      publicSupabase
        .from('news_comments')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
      authSupabase
        ? authSupabase
            .from('user_bookmarks')
            .select('id')
            .eq('user_id', locals.user.id)
            .eq('item_type', 'news')
            .eq('item_id', post.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
      authSupabase
        ? authSupabase
            .from('news_likes')
            .select('id')
            .eq('user_id', locals.user.id)
            .eq('post_id', post.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
      publicSupabase
        .from('handbook_terms')
        .select(`term, slug, korean_name, term_full, categories, ${definitionField}, body_basic_ko, body_basic_en`)
        .eq('status', 'published')
        .limit(200),
      post.category
        ? publicSupabase
            .from('news_posts')
            .select('id, slug, title, category, post_type')
            .eq('status', 'published')
            .eq('locale', locale)
            .eq('category', post.category)
            .neq('id', post.id)
            .order('published_at', { ascending: false })
            .limit(3)
        : Promise.resolve({ data: null }),
    ]);

    nextPost = nextRes.data ?? null;
    pairedSlug = pairedRes.data?.slug ?? null;
    likeCount = likeCountRes.count ?? 0;
    commentCount = commentCountRes.count ?? 0;
    isBookmarked = !!bookmarkRes.data;
    isLiked = !!likeRes.data;

    focusItems = (post.focus_items && post.focus_items.length > 0)
      ? post.focus_items
      : getArticleFocusItems(locale, post.category);

    const hbTerms = hbTermsRes.data ?? [];
    for (const entry of hbTerms) {
      const termEntry = { slug: entry.slug, term: entry.term };
      handbookTermsMap.set(entry.term.toLowerCase(), termEntry);
      if (entry.korean_name) handbookTermsMap.set(entry.korean_name.toLowerCase(), termEntry);
      handbookTermsJson[entry.slug] = {
        term: entry.term,
        korean_name: entry.korean_name || '',
        term_full: (entry as Record<string, any>).term_full || '',
        categories: entry.categories || [],
        definition: (entry as Record<string, any>)[definitionField] || '',
        basic_plain: locale === 'ko'
          ? (entry as Record<string, any>).body_basic_ko || ''
          : (entry as Record<string, any>).body_basic_en || '',
      };
    }

    articleData = post.published_at
      ? { datePublished: post.published_at, dateModified: post.updated_at || post.published_at, image: post.og_image_url }
      : undefined;

    factPack = Array.isArray(post.fact_pack) ? post.fact_pack : [];
    sourceCards = normalizeSourceCards(post);

    // Collect FastAPI result (was running in parallel with DB queries + termsMap build)
    similarPosts = await similarPostsPromise;
    if (similarPosts.length === 0 && backfillRes.data?.length) {
      similarPosts = backfillRes.data.map((p: any) => ({ post_id: p.id, slug: p.slug, title: p.title, category: p.category, post_type: p.post_type }));
    }
  }

  const hasTerms = handbookTermsMap.size > 0;
  const renderMd = hasTerms
    ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
    : (md: string) => renderMarkdown(md);

  const userPersona = previewMode ? null : locals.profile?.persona;
  let activePersona: string | null = null;
  let personaHtmlMap: Record<string, string> = {};
  let rawContent = '';

  if (post) {
    const hasPersonaContent = post.content_learner || post.content_expert;
    if (hasPersonaContent) {
      const personaKey = previewMode ? (previewPersona || 'learner') : (userPersona || 'learner');
      const contentMap: Record<string, string> = {
        learner: post.content_learner || '',
        expert: post.content_expert || '',
      };
      rawContent = contentMap[personaKey] || post.content_learner || '';
      activePersona = contentMap[personaKey] ? personaKey : 'learner';

      // Render only active persona + analysis (inactive loads on demand via API)
      // In preview mode, render all personas so admin can see both tabs
      const renderEntries: [string, string][] = [];
      if (previewMode) {
        for (const [key, md] of Object.entries(contentMap)) {
          if (md) renderEntries.push([key, md]);
        }
      } else if (contentMap[personaKey]) {
        renderEntries.push([personaKey, contentMap[personaKey]]);
      }
      if (post.content_analysis) renderEntries.push(['__analysis', post.content_analysis]);

      const rendered = await Promise.all(
        renderEntries.map(async ([key, md]) => [key, applySourceCitations(await renderMd(md))] as const),
      );
      for (const [key, html] of rendered) {
        if (key === '__analysis') analysisHtml = html;
        else personaHtmlMap[key] = html;
      }

      // Track which personas are available (for tab button rendering)
      availablePersonas = Object.keys(contentMap).filter(k => contentMap[k]);
    } else {
      rawContent = post.content_original || '';
    }
  }

  // Reuse already-rendered persona HTML instead of re-rendering the same markdown
  const htmlContent = activePersona
    ? personaHtmlMap[activePersona] || ''
    : (rawContent ? applySourceCitations(await renderMd(rawContent)) : '');
  const hasPersonaSwitcher = Object.keys(personaHtmlMap).length > 1;

  // Extract actually-matched term slugs from rendered HTML
  const allRenderedHtml = [htmlContent, analysisHtml, ...Object.values(personaHtmlMap)].join('');
  const matchedSlugs: string[] = [];
  const slugRegex = /data-slug="([^"]+)"/g;
  let slugMatch: RegExpExecArray | null;
  const seenSlugs = new Set<string>();
  while ((slugMatch = slugRegex.exec(allRenderedHtml)) !== null) {
    const s = slugMatch[1];
    if (!seenSlugs.has(s)) {
      seenSlugs.add(s);
      matchedSlugs.push(s);
    }
  }
  const relatedTerms = matchedSlugs
    .filter(s => handbookTermsJson[s])
    .slice(0, 3)
    .map(s => ({
      slug: s,
      term: handbookTermsJson[s].term as string,
      koreanName: handbookTermsJson[s].korean_name as string,
      definition: handbookTermsJson[s].definition as string,
    }));

  // Build persona-specific source cards map for tab switching
  const personaSourceCardsMap: Record<string, typeof sourceCards> = {};
  try {
    const guideItems = post?.guide_items || {};
    for (const pname of ['expert', 'learner']) {
      const psrc = guideItems[`sources_${pname}`];
      if (Array.isArray(psrc) && psrc.length > 0) {
        personaSourceCardsMap[pname] = normalizeSourceCards({
          source_cards: psrc,
          source_urls: post?.source_urls,
        });
      }
    }
  } catch {
    // Fallback: persona sources unavailable, sourceCards (default) will be used
  }

  return {
    post,
    postError,
    focusItems,
    articleData,
    nextPost,
    pairedSlug,
    similarPosts,
    isBookmarked: previewMode ? false : isBookmarked,
    isLiked: previewMode ? false : isLiked,
    likeCount,
    commentCount,
    handbookTermsJson,
    hasTerms,
    relatedTerms,
    htmlContent,
    analysisHtml,
    factPack,
    sourceCards,
    activePersona,
    availablePersonas,
    personaHtmlMap,
    personaSourceCardsMap,
    hasPersonaSwitcher,
    applySourceCitations,
  };
}
