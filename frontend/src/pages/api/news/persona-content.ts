import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../../../lib/markdown';
import { getDefinitionField } from '../../../lib/pageData/shared';

export const prerender = false;

function applySourceCitations(html: string): string {
  if (!html) return html;
  return html.replace(/\[\[(\d+)\]\]/g, (_match, index) =>
    `<sup class="newsprint-citation"><a href="#source-card-${index}">${index}</a></sup>`
  );
}

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get('slug');
  const locale = url.searchParams.get('locale') as 'en' | 'ko' | null;
  const persona = url.searchParams.get('persona');

  if (!slug || !locale || !persona || !['expert', 'learner'].includes(persona)) {
    return new Response(JSON.stringify({ error: 'Missing slug, locale, or persona' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
  );

  const contentColumn = persona === 'expert' ? 'content_expert' : 'content_learner';
  const definitionField = getDefinitionField(locale);

  const [postRes, termsRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select(`${contentColumn}, guide_items`)
      .eq('slug', slug)
      .eq('locale', locale)
      .eq('status', 'published')
      .single(),
    supabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, ${definitionField}`)
      .eq('status', 'published')
      .limit(200),
  ]);

  if (!postRes.data?.[contentColumn]) {
    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const termsMap: TermsMap = new Map();
  for (const entry of (termsRes.data || [])) {
    const termEntry = { slug: entry.slug, term: entry.term };
    termsMap.set(entry.term.toLowerCase(), termEntry);
    if (entry.korean_name) termsMap.set(entry.korean_name.toLowerCase(), termEntry);
  }

  const renderMd = termsMap.size > 0
    ? (md: string) => renderMarkdownWithTerms(md, termsMap)
    : (md: string) => renderMarkdown(md);

  const html = applySourceCitations(await renderMd(postRes.data[contentColumn]));

  const guideItems = postRes.data.guide_items || {};
  const sources = guideItems[`sources_${persona}`] || null;

  return new Response(JSON.stringify({ html, sources }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
};
