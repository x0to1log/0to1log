import { supabase } from '../supabase';

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
    return { allTerms: [], totalTerms: 0, error: null };
  }

  const { data, error } = await supabase
    .from('handbook_terms')
    .select(getTermCardColumns(locale))
    .eq('status', 'published')
    .order('term')
    .limit(500);

  if (error) {
    return { allTerms: [], totalTerms: 0, error: error.message };
  }

  const allTerms = (data ?? []).map((row) => toTermCard(row, locale));

  return { allTerms, totalTerms: allTerms.length, error: null };
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
