import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { fetchPublicTermIndex } from './publicTermIndex';
import { getAuthorizedSupabase, getPublicSupabase, type DetailPageContext } from './shared';
import { pickReferencedTerms } from './termReferences';

export const BLOG_DETAIL_PUBLIC_COLUMNS = [
  'id', 'slug', 'locale', 'status', 'title', 'excerpt', 'category', 'content',
  'published_at', 'updated_at', 'reading_time_min', 'tags', 'og_image_url',
  'translation_group_id', 'focus_items',
].join(', ');

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
      .select(BLOG_DETAIL_PUBLIC_COLUMNS)
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

  let listRows: any[] = [];
  let articleData: any = undefined;
  let pairedSlug: string | null = null;
  let isBookmarked = false;
  let isLiked = false;
  let likeCount = 0;
  let commentCount = 0;
  let handbookTermsMap: TermsMap = new Map();
  let handbookTermsJson: Record<string, any> = {};
  let htmlContent = '';

  if (post && publicSupabase) {
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';

    const rawContent = post.content || '';

    // Track 1: terms fetch → termsMap build → markdown render (chained)
    // Runs in parallel with Track 2 DB queries so render time overlaps with I/O.
    const renderTrack = (async () => {
      const handbookTerms = await fetchPublicTermIndex(publicSupabase, locale);

      const tMap: TermsMap = new Map();
      const tJson: Record<string, any> = {};
      for (const entry of handbookTerms) {
        const termEntry = { slug: entry.slug, term: entry.term };
        tMap.set(entry.term.toLowerCase(), termEntry);
        if (entry.korean_name) tMap.set(entry.korean_name.toLowerCase(), termEntry);
        tJson[entry.slug] = {
          term: entry.term,
          korean_name: entry.korean_name || '',
          term_full: entry.term_full || '',
          categories: entry.categories || [],
          summary: entry.summary || '',
          definition: entry.definition || '',
          basic_plain: entry.basic_plain || '',
        };
      }

      const renderFn = tMap.size > 0
        ? (md: string) => renderMarkdownWithTerms(md, tMap)
        : (md: string) => renderMarkdown(md);
      const html = rawContent ? await renderFn(rawContent) : '';
      return { termsMap: tMap, termsJson: tJson, html };
    })();

    // Track 2: remaining DB queries (all parallel).
    // isBookmarked/isLiked stay false — hydrated client-side so HTML is cacheable.
    const [
      listRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
    ] = await Promise.all([
      // Same window, order and columns as the blog list page (created_at desc, 100 posts), so the
      // episode number and previous/next computed by locatePost() match the list.
      publicSupabase
        .from('blog_posts')
        .select('title, slug, category, published_at')
        .eq('status', 'published')
        .eq('locale', locale)
        .order('created_at', { ascending: false })
        .limit(100),
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
    ]);

    // Await render track (likely already done by now)
    const renderResult = await renderTrack;
    handbookTermsMap = renderResult.termsMap;
    handbookTermsJson = renderResult.termsJson;
    htmlContent = renderResult.html;

    listRows = listRes.data ?? [];
    pairedSlug = pairedRes.data?.slug ?? null;
    likeCount = likeCountRes.count ?? 0;
    commentCount = commentCountRes.count ?? 0;

    articleData = post.published_at
      ? { datePublished: post.published_at, dateModified: post.updated_at || post.published_at, image: post.og_image_url }
      : undefined;
  }

  const hasTerms = handbookTermsMap.size > 0;

  return {
    post,
    postError,
    recentPosts: listRows,
    articleData,
    pairedSlug,
    isBookmarked: previewMode ? false : isBookmarked,
    isLiked: previewMode ? false : isLiked,
    likeCount,
    commentCount,
    handbookTermsJson: pickReferencedTerms(handbookTermsJson, [htmlContent]),
    hasTerms,
    htmlContent,
  };
}
