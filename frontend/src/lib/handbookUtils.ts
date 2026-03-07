import type { Locale } from '../i18n/index';

/** Pick a bilingual field value with KO fallback */
export function localField(term: Record<string, any>, field: string, locale: Locale): string {
  return term[`${field}_${locale}`] || term[`${field}_ko`] || '';
}

/** Difficulty badge color */
export function difficultyColor(difficulty?: string | null): string {
  switch (difficulty) {
    case 'beginner': return 'var(--color-cat-ainews)';
    case 'intermediate': return 'var(--color-cat-study)';
    case 'advanced': return 'var(--color-cat-career)';
    default: return 'var(--color-border)';
  }
}

/** Difficulty label */
export function difficultyLabel(locale: Locale, difficulty?: string | null): string {
  const labels: Record<string, Record<Locale, string>> = {
    beginner:     { en: 'Beginner',     ko: '입문' },
    intermediate: { en: 'Intermediate', ko: '중급' },
    advanced:     { en: 'Advanced',     ko: '고급' },
  };
  if (!difficulty) return '';
  return labels[difficulty]?.[locale] ?? difficulty;
}
