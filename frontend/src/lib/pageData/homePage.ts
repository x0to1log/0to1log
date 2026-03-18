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

  const [newsRes, termsRes, blogRes, sc, featuredProducts, fallbackRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .limit(4),

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

  return {
    news: (newsRes.data ?? []) as HomeNewsPost[],
    terms,
    blog: (blogRes.data ?? []) as HomeBlogPost[],
    siteContent: sc,
    featuredProducts,
  };
}
