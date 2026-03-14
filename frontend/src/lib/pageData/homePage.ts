import { supabase } from '../supabase';
import { getSiteContents } from '../siteContent';

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
}

export async function getHomePageData(locale: 'en' | 'ko'): Promise<HomePageData> {
  if (!supabase) {
    return { news: [], terms: [], blog: [], siteContent: {} };
  }

  const [newsRes, termsRes, blogRes, sc] = await Promise.all([
    supabase
      .from('news_posts')
      .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('created_at', { ascending: false })
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
  ]);

  let terms: HomeHandbookTerm[] = (termsRes.data ?? []) as HomeHandbookTerm[];

  // Fill with recent terms if we have fewer than 6 favourites
  if (terms.length < 6) {
    const existingIds = terms.map((t) => t.id);
    const needed = 6 - terms.length;
    const fallbackQuery = supabase
      .from('handbook_terms')
      .select('id, term, slug, korean_name, definition_en, definition_ko, categories, is_favourite')
      .eq('status', 'published')
      .order('published_at', { ascending: false })
      .limit(needed);

    if (existingIds.length > 0) {
      fallbackQuery.not('id', 'in', `(${existingIds.join(',')})`);
    }

    const fallbackRes = await fallbackQuery;
    terms = [...terms, ...((fallbackRes.data ?? []) as HomeHandbookTerm[])];
  }

  return {
    news: (newsRes.data ?? []) as HomeNewsPost[],
    terms,
    blog: (blogRes.data ?? []) as HomeBlogPost[],
    siteContent: sc,
  };
}
