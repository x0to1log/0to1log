import { getArticleFocusItems } from '../articleRail';
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { getAuthorizedSupabase, getDefinitionField, getPublicSupabase, type DetailPageContext } from './shared';

interface NewsDetailPageContext extends DetailPageContext {
  previewPersona?: string | null;
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

  let recentPosts: any[] = [];
  let focusItems: string[] = [];
  let articleData: any = undefined;
  let nextPost: { title: string; slug: string; category: string | null } | null = null;
  let pairedSlug: string | null = null;
  let similarPosts: { post_id: string; slug: string; title: string; category: string }[] = [];
  let isBookmarked = false;
  let isLiked = false;
  let likeCount = 0;
  let commentCount = 0;
  let handbookTermsMap: TermsMap = new Map();
  let handbookTermsJson: Record<string, any> = {};

  if (post && publicSupabase) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';
    const definitionField = getDefinitionField(locale);

    if (post.pipeline_batch_id) {
      const { data: batchPosts } = await publicSupabase
        .from('news_posts')
        .select('title, slug, category')
        .eq('status', 'published')
        .eq('locale', locale)
        .eq('pipeline_batch_id', post.pipeline_batch_id)
        .neq('slug', pageSlug)
        .order('published_at', { ascending: false })
        .limit(4);

      if (batchPosts?.length) {
        recentPosts = batchPosts;
      }
    }

    if (recentPosts.length === 0) {
      recentPosts = (await publicSupabase
        .from('news_posts')
        .select('title, slug, category')
        .eq('status', 'published')
        .eq('locale', locale)
        .neq('slug', pageSlug)
        .order('published_at', { ascending: false })
        .limit(4)
      ).data ?? [];
    }

    const [
      nextRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
      bookmarkRes,
      likeRes,
      hbTermsRes,
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
        .select(`term, slug, korean_name, categories, ${definitionField}`)
        .eq('status', 'published'),
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

    if (import.meta.env.FASTAPI_URL && post.id) {
      try {
        const res = await fetch(
          `${import.meta.env.FASTAPI_URL}/api/recommendations/similar?post_id=${post.id}&locale=${locale}`,
          { signal: AbortSignal.timeout(3000) },
        );
        if (res.ok) {
          similarPosts = await res.json();
        }
      } catch {
        similarPosts = [];
      }
    }

    const hbTerms = hbTermsRes.data ?? [];
    for (const entry of hbTerms) {
      const termEntry = { slug: entry.slug, term: entry.term };
      handbookTermsMap.set(entry.term.toLowerCase(), termEntry);
      if (entry.korean_name) handbookTermsMap.set(entry.korean_name.toLowerCase(), termEntry);
      handbookTermsJson[entry.slug] = {
        term: entry.term,
        korean_name: entry.korean_name || '',
        categories: entry.categories || [],
        definition: entry[definitionField] || '',
      };
    }

    articleData = post.published_at
      ? { datePublished: post.published_at, dateModified: post.updated_at || post.published_at, image: post.og_image_url }
      : undefined;
  }

  const hasTerms = handbookTermsMap.size > 0;
  const renderMd = hasTerms
    ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
    : (md: string) => renderMarkdown(md);

  const userPersona = previewMode ? null : locals.profile?.persona;
  const isBusinessPost = post?.post_type === 'business';
  let activePersona: string | null = null;
  let personaHtmlMap: Record<string, string> = {};
  let rawContent = '';

  if (post) {
    if (isBusinessPost) {
      const personaKey = previewMode ? (previewPersona || 'learner') : (userPersona || 'learner');
      const contentMap: Record<string, string> = {
        beginner: post.content_beginner || '',
        learner: post.content_learner || '',
        expert: post.content_expert || '',
      };
      rawContent = contentMap[personaKey] || post.content_learner || post.content_beginner || '';
      activePersona = contentMap[personaKey] ? personaKey : (post.content_learner ? 'learner' : 'beginner');

      for (const [key, md] of Object.entries(contentMap)) {
        if (md) personaHtmlMap[key] = await renderMd(md);
      }
    } else {
      rawContent = post.content_original || '';
    }
  }

  const htmlContent = rawContent ? await renderMd(rawContent) : '';
  const hasPersonaSwitcher = isBusinessPost && Object.keys(personaHtmlMap).length > 1;

  return {
    post,
    postError,
    recentPosts,
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
    htmlContent,
    activePersona,
    personaHtmlMap,
    hasPersonaSwitcher,
  };
}
