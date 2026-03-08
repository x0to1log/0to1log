import type { Locale } from '../i18n/index';

export type CategorySlug = 'ai-news' | 'study' | 'career' | 'project';
export type LegacyCategorySlug = CategorySlug | 'tech';

const CATEGORY_LABELS: Record<CategorySlug, Record<Locale, string>> = {
  'ai-news': { en: 'AI News', ko: 'AI 뉴스' },
  study: { en: 'Study', ko: '서재' },
  career: { en: 'Career', ko: '커리어' },
  project: { en: 'Project', ko: '프로젝트' },
};

const CATEGORY_COLOR_VARS: Record<CategorySlug, string> = {
  'ai-news': 'var(--color-cat-ainews)',
  study: 'var(--color-cat-study)',
  career: 'var(--color-cat-career)',
  project: 'var(--color-cat-project)',
};

export function normalizeCategorySlug(category?: string | null): string | null {
  if (!category) return null;
  return category === 'tech' ? 'study' : category;
}

export function getCategoryLabel(locale: Locale, category?: string | null): string | null {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) return null;
  return CATEGORY_LABELS[normalized as CategorySlug]?.[locale] ?? normalized;
}

export function getCategoryColorVar(category?: string | null): string {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) return 'var(--color-border)';
  return CATEGORY_COLOR_VARS[normalized as CategorySlug] ?? 'var(--color-border)';
}

export function getDefaultCategories(): CategorySlug[] {
  return ['ai-news', 'study', 'project', 'career'];
}
