import { supabase } from '../supabase';
import { getSiteContents } from '../siteContent';
import { fetchHomeFeaturedProducts, type HomeFeaturedProduct } from './productsPage';

export type { HomeFeaturedProduct };

export interface HomeNewsPost {
  id: string;
  title: string;
  slug: string;
  post_type: string | null;
  published_at: string | null;
  tags: string[] | null;
  reading_time_min: number | null;
  excerpt: string | null;
}

export interface HomeHandbookTerm {
  id: string;
  term: string;
  slug: string;
  korean_name: string | null;
  definition_en: string | null;
  definition_ko: string | null;
  categories: string[] | null;
  is_favourite: boolean | null;
}

export interface HomeBlogPost {
  id: string;
  title: string;
  slug: string;
  category: string | null;
  published_at: string | null;
  tags: string[] | null;
  reading_time_min: number | null;
  excerpt: string | null;
}

export interface HomePageData {
  news: HomeNewsPost[];
  terms: HomeHandbookTerm[];
  blog: HomeBlogPost[];
  siteContent: Record<string, string>;
  featuredProducts: HomeFeaturedProduct[];
}

export async function getHomePageData(locale: 'en' | 'ko'): Promise<HomePageData> {
  if (!supabase) {
    return { news: [], terms: [], blog: [], siteContent: {}, featuredProducts: [] };
  }

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const [recentNewsRes, fallbackNewsRes, termsRes, blogRes, sc, featuredProducts, fallbackRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
      .eq('status', 'published')
      .eq('locale', locale)
      .gte('published_at', sevenDaysAgo)
      .order('published_at', { ascending: false })
      .limit(20),

    supabase
      .from('news_posts')
      .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .limit(10),

    supabase
      .from('handbook_terms')
      .select('id, term, slug, korean_name, definition_en, definition_ko, categories, is_favourite')
      .eq('status', 'published')
      .eq('is_favourite', true)
      .limit(6),

    supabase
      .from('blog_posts')
      .select('id, title, slug, category, published_at, tags, reading_time_min, excerpt')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('created_at', { ascending: false })
      .limit(4),

    getSiteContents(['home_title', 'home_subtitle', 'home_intro'], locale),
    fetchHomeFeaturedProducts(),

    // Eagerly fetch fallback terms in parallel (used if fewer than 6 favourites)
    supabase
      .from('handbook_terms')
      .select('id, term, slug, korean_name, definition_en, definition_ko, categories, is_favourite')
      .eq('status', 'published')
      .eq('is_favourite', false)
      .order('published_at', { ascending: false })
      .limit(6),
  ]);

  let terms: HomeHandbookTerm[] = (termsRes.data ?? []) as HomeHandbookTerm[];

  // Fill with recent non-favourite terms if we have fewer than 6 favourites
  if (terms.length < 6) {
    const existingIds = new Set(terms.map((t) => t.id));
    const fallbacks = ((fallbackRes.data ?? []) as HomeHandbookTerm[])
      .filter((t) => !existingIds.has(t.id));
    terms = [...terms, ...fallbacks.slice(0, 6 - terms.length)];
  }

  // 7일치 뉴스가 3개 미만이면 최근 뉴스로 채움
  let news = (recentNewsRes.data ?? []) as HomeNewsPost[];
  if (news.length < 3) {
    const fallbackNews = (fallbackNewsRes.data ?? []) as HomeNewsPost[];
    const existingIds = new Set(news.map((n) => n.id));
    const extras = fallbackNews.filter((n) => !existingIds.has(n.id));
    news = [...news, ...extras].slice(0, 10);
  }

  return {
    news,
    terms,
    blog: (blogRes.data ?? []) as HomeBlogPost[],
    siteContent: sc,
    featuredProducts,
  };
}
