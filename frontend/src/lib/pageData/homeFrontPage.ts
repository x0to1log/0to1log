// frontend/src/lib/pageData/homeFrontPage.ts
// Lean data for the home front page: 1 news query + the shared term of the day (count + 1 row).
import { supabase } from '../supabase';
import { selectFrontPage } from '../homeFront.js';
import { fetchTermOfDay } from './termOfDay';

export interface HomeFrontNews {
  title: string;
  slug: string;
  post_type: string | null;
  published_at: string | null;
  excerpt: string | null;
  reading_time_min: number | null;
  tags: string[] | null;
}

export interface HomeFrontTerm {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
}

export interface HomeFrontPageData {
  lead: HomeFrontNews | null;
  leadIsToday: boolean;
  sibling: HomeFrontNews | null;
  earlier: HomeFrontNews[];
  todayCount: number;
  term: HomeFrontTerm | null;
  keyword: { small: string | null; big: string } | null;
}

const EMPTY: HomeFrontPageData = { lead: null, leadIsToday: false, sibling: null, earlier: [], todayCount: 0, term: null, keyword: null };

export async function getHomeFrontPageData(locale: 'en' | 'ko', now = new Date()): Promise<HomeFrontPageData> {
  if (!supabase) return EMPTY;

  const [newsRes, termOfDay] = await Promise.all([
    supabase
      .from('news_posts')
      .select('title, slug, post_type, published_at, excerpt, reading_time_min, tags')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .order('post_type', { ascending: true }) // same-day stories share 00:00Z; keep the lead stable across cache refreshes
      .limit(6),
    fetchTermOfDay(supabase, locale, now),
  ]);

  if (newsRes.error) console.warn('[homeFrontPage] news query failed', newsRes.error.message);
  const news = newsRes.error ? [] : ((newsRes.data ?? []) as HomeFrontNews[]);
  const term = termOfDay.term as HomeFrontTerm | null;

  return selectFrontPage({ news, term, now }) as HomeFrontPageData;
}
