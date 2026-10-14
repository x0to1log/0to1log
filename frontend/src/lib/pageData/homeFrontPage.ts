// frontend/src/lib/pageData/homeFrontPage.ts
// Lean data for the home "오늘의 1면" strip: 1 news query + 1 term query.
import { supabase } from '../supabase';
import { selectFrontPage, termIndex } from '../homeFront.js';

export interface HomeFrontNews {
  title: string;
  slug: string;
  post_type: string | null;
  published_at: string | null;
  excerpt: string | null;
  reading_time_min: number | null;
}

export interface HomeFrontTerm {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
}

export interface HomeFrontPageData {
  lead: HomeFrontNews | null;
  also: HomeFrontNews | null;
  todayCount: number;
  term: HomeFrontTerm | null;
}

const EMPTY: HomeFrontPageData = { lead: null, also: null, todayCount: 0, term: null };

export async function getHomeFrontPageData(locale: 'en' | 'ko', now = new Date()): Promise<HomeFrontPageData> {
  if (!supabase) return EMPTY;
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';

  const [newsRes, countRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select('title, slug, post_type, published_at, excerpt, reading_time_min')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .order('post_type', { ascending: true }) // same-day stories share 00:00Z; keep the lead stable across cache refreshes
      .limit(6),
    supabase
      .from('handbook_terms')
      .select('slug', { count: 'exact', head: true })
      .eq('status', 'published'),
  ]);

  if (newsRes.error) console.warn('[homeFrontPage] news query failed', newsRes.error.message);
  if (countRes.error) console.warn('[homeFrontPage] term count query failed', countRes.error.message);
  const news = newsRes.error ? [] : ((newsRes.data ?? []) as HomeFrontNews[]);

  let term: HomeFrontTerm | null = null;
  const total = countRes.error ? 0 : (countRes.count ?? 0);
  const i = termIndex(now, total);
  if (i !== null) {
    const termRes = await supabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, definition:${definitionField}`)
      .eq('status', 'published')
      .order('slug', { ascending: true })
      .range(i, i)
      .maybeSingle();
    if (termRes.error) console.warn('[homeFrontPage] term query failed', termRes.error.message);
    else term = (termRes.data ?? null) as HomeFrontTerm | null;
  }

  return selectFrontPage({ news, term, now }) as HomeFrontPageData;
}
