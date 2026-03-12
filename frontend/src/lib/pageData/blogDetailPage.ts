import { BLOG_CATEGORIES } from '../categories';
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
      .eq('locale', locale)
      .in('category', BLOG_CATEGORIES);

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

  if (post && publicSupabase) {
    const authSupabase = !previewMode && locals.user && locals.accessToken
      ? getAuthorizedSupabase(locals.accessToken)
      : null;
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';
    const definitionField = getDefinitionField(locale);

    const [
      sidebarRes,
      nextRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
      bookmarkRes,
      likeRes,
      hbTermsRes,
    ] = await Promise.all([
      publicSupabase
        .from('blog_posts')
        .select('title, slug, category, published_at')
        .eq('status', 'published')
        .eq('locale', locale)
        .in('category', BLOG_CATEGORIES)
        .order('published_at', { ascending: false })
        ,
      post.published_at
        ? publicSupabase
            .from('blog_posts')
            .select('title, slug, category')
            .eq('status', 'published')
            .eq('locale', locale)
            .in('category', BLOG_CATEGORIES)
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
      publicSupabase
        .from('handbook_terms')
        .select(`term, slug, korean_name, categories, ${definitionField}`)
        .eq('status', 'published'),
    ]);

    sidebarRows = sidebarRes.data ?? [];
    nextPost = nextRes.data ?? null;
    pairedSlug = pairedRes.data?.slug ?? null;
    likeCount = likeCountRes.count ?? 0;
    commentCount = commentCountRes.count ?? 0;
    isBookmarked = !!bookmarkRes.data;
    isLiked = !!likeRes.data;

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
  const rawContent = post ? (post.content || '') : '';
  const htmlContent = rawContent ? await renderMd(rawContent) : '';
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
