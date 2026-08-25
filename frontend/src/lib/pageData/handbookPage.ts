import { supabase } from '../supabase';
import { getHandbookCategories } from '../handbookCategories';

// =============================================================================
// Types
// =============================================================================

export interface HandbookTermCard {
  id: string;
  term: string;
  slug: string;
  korean_name: string | null;
  definition_ko: string | null;
  definition_en: string | null;
  categories: string[];
  is_favourite: boolean;
}

export interface HandbookPageData {
  allTerms: HandbookTermCard[];
  termsByCategory: Record<string, HandbookTermCard[]>;
  totalTerms: number;
  error: string | null;
}

export interface HandbookCategoryPageData {
  terms: HandbookTermCard[];
  totalTerms: number;
  error: string | null;
}

// =============================================================================
// Helpers
// =============================================================================

function getTermCardColumns(locale: 'en' | 'ko'): string {
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';
  return `id, term, slug, korean_name, definition:${definitionField}, categories, is_favourite`;
}

function toTermCard(row: any, locale: 'en' | 'ko'): HandbookTermCard {
  return {
    id: row.id,
    term: row.term,
    slug: row.slug,
    korean_name: row.korean_name ?? null,
    definition_ko: locale === 'ko' ? row.definition ?? null : null,
    definition_en: locale === 'en' ? row.definition ?? null : null,
    categories: (row.categories as string[]) ?? [],
    is_favourite: row.is_favourite ?? false,
  };
}

// =============================================================================
// List page — all terms
// =============================================================================

export async function getHandbookPageData(
  locale: 'en' | 'ko',
): Promise<HandbookPageData> {
  if (!supabase) {
    return { allTerms: [], termsByCategory: {}, totalTerms: 0, error: null };
  }

  const { data, error } = await supabase
    .from('handbook_terms')
    .select(getTermCardColumns(locale))
    .eq('status', 'published')
    .order('term')
    .limit(500);

  if (error) {
    return { allTerms: [], termsByCategory: {}, totalTerms: 0, error: error.message };
  }

  const allTerms = (data ?? []).map((row) => toTermCard(row, locale));

  // Group by category in the canonical order from handbookCategories
  const categoryOrder = getHandbookCategories();
  const termsByCategory: Record<string, HandbookTermCard[]> = {};

  for (const slug of categoryOrder) {
    termsByCategory[slug] = [];
  }

  for (const term of allTerms) {
    for (const cat of term.categories) {
      if (termsByCategory[cat]) {
        termsByCategory[cat].push(term);
      }
    }
  }

  return { allTerms, termsByCategory, totalTerms: allTerms.length, error: null };
}

// =============================================================================
// Category page — single category
// =============================================================================

export async function getHandbookCategoryPageData(
  locale: 'en' | 'ko',
  categorySlug: string,
): Promise<HandbookCategoryPageData> {
  if (!supabase) {
    return { terms: [], totalTerms: 0, error: null };
  }

  const { data, error } = await supabase
    .from('handbook_terms')
    .select(getTermCardColumns(locale))
    .eq('status', 'published')
    .contains('categories', [categorySlug])
    .order('term')
    .limit(200);

  if (error) {
    return { terms: [], totalTerms: 0, error: error.message };
  }

  const terms = (data ?? []).map((row) => toTermCard(row, locale));

  return { terms, totalTerms: terms.length, error: null };
}
