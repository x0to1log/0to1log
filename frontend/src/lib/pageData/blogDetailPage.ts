import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { buildBlogSidebarDataset, toSidebarPost } from './blogSidebar';
import { getAuthorizedSupabase, getDefinitionField, getPublicSupabase, type DetailPageContext } from './shared';

export async function getBlogDetailPageData({ locale, slug, previewMode, locals }: DetailPageContext) {
  const pageSlug = slug;
  const publicSupabase = getPublicSupabase();
  const previewSupabase = previewMode ? getAuthorizedSupabase(locals.accessToken) : null;
  const detailSupabase = previewSupabase || publicSupabase;

  let post: any = null;
  let postError: string | null = null;

  if (detailSupabase && slug) {
    let query = detailSupabase
      .from('blog_posts')
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

  let sidebarRows: any[] = [];
  let articleData: any = undefined;
  let nextPost: { title: string; slug: string; category: string | null } | null = null;
  let pairedSlug: string | null = null;
  let isBookmarked = false;
  let isLiked = false;
  let likeCount = 0;
  let commentCount = 0;
  let handbookTermsMap: TermsMap = new Map();
  let handbookTermsJson: Record<string, any> = {};
  let htmlContent = '';

  if (post && publicSupabase) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';
    const definitionField = getDefinitionField(locale);
    const summaryField = locale === 'ko' ? 'summary_ko' : 'summary_en';

    const rawContent = post.content || '';

    // Track 1: terms fetch → termsMap build → markdown render (chained)
    // Runs in parallel with Track 2 DB queries so render time overlaps with I/O.
    const renderTrack = (async () => {
      const hbTermsRes = await publicSupabase
        .from('handbook_terms')
        .select(`term, slug, korean_name, term_full, categories, ${summaryField}, ${definitionField}, body_basic_ko, body_basic_en`)
        .eq('status', 'published')
        .limit(200);

      const tMap: TermsMap = new Map();
      const tJson: Record<string, any> = {};
      for (const entry of hbTermsRes.data ?? []) {
        const termEntry = { slug: entry.slug, term: entry.term };
        tMap.set(entry.term.toLowerCase(), termEntry);
        if (entry.korean_name) tMap.set(entry.korean_name.toLowerCase(), termEntry);
        tJson[entry.slug] = {
          term: entry.term,
          korean_name: entry.korean_name || '',
          term_full: (entry as Record<string, any>).term_full || '',
          categories: entry.categories || [],
          summary: (entry as Record<string, any>)[summaryField] || '',
          definition: (entry as Record<string, any>)[definitionField] || '',
          basic_plain: locale === 'ko'
            ? (entry as Record<string, any>).body_basic_ko || ''
            : (entry as Record<string, any>).body_basic_en || '',
        };
      }

      const renderFn = tMap.size > 0
        ? (md: string) => renderMarkdownWithTerms(md, tMap)
        : (md: string) => renderMarkdown(md);
      const html = rawContent ? await renderFn(rawContent) : '';
      return { termsMap: tMap, termsJson: tJson, html };
    })();

    // Track 2: remaining DB queries (unchanged, all parallel)
    const [
      sidebarRes,
      nextRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
      bookmarkRes,
      likeRes,
    ] = await Promise.all([
      publicSupabase
        .from('blog_posts')
        .select('title, slug, category, published_at')
        .eq('status', 'published')
        .eq('locale', locale)
        .order('published_at', { ascending: false })
        ,
      post.published_at
        ? publicSupabase
            .from('blog_posts')
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
            .from('blog_posts')
            .select('slug')
            .eq('translation_group_id', post.translation_group_id)
            .eq('locale', pairedLocale)
            .single()
        : Promise.resolve({ data: null }),
      publicSupabase
        .from('blog_likes')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
      publicSupabase
        .from('blog_comments')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
      authSupabase
        ? authSupabase
            .from('user_bookmarks')
            .select('id')
            .eq('user_id', locals.user.id)
            .eq('item_type', 'blog')
            .eq('item_id', post.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
      authSupabase
        ? authSupabase
            .from('blog_likes')
            .select('id')
            .eq('user_id', locals.user.id)
            .eq('post_id', post.id)
            .maybeSingle()
        : Promise.resolve({ data: null }),
    ]);

    // Await render track (likely already done by now)
    const renderResult = await renderTrack;
    handbookTermsMap = renderResult.termsMap;
    handbookTermsJson = renderResult.termsJson;
    htmlContent = renderResult.html;

    sidebarRows = sidebarRes.data ?? [];
    nextPost = nextRes.data ?? null;
    pairedSlug = pairedRes.data?.slug ?? null;
    likeCount = likeCountRes.count ?? 0;
    commentCount = commentCountRes.count ?? 0;
    isBookmarked = !!bookmarkRes.data;
    isLiked = !!likeRes.data;

    articleData = post.published_at
      ? { datePublished: post.published_at, dateModified: post.updated_at || post.published_at, image: post.og_image_url }
      : undefined;
  }

  const hasTerms = handbookTermsMap.size > 0;
  const sidebarPosts = buildBlogSidebarDataset(
    sidebarRows.map((item) => toSidebarPost(item)),
    post
      ? toSidebarPost({
          title: post.title,
          slug: post.slug,
          category: post.category,
          published_at: post.published_at,
        })
      : null,
  );

  return {
    post,
    postError,
    recentPosts: sidebarRows,
    articleData,
    nextPost,
    pairedSlug,
    isBookmarked: previewMode ? false : isBookmarked,
    isLiked: previewMode ? false : isLiked,
    likeCount,
    commentCount,
    handbookTermsJson,
    hasTerms,
    htmlContent,
    sidebarPosts,
  };
}
