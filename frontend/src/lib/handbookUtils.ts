import type { Locale } from '../i18n/index';

/** Pick a bilingual field value with KO fallback */
export function localField(term: Record<string, any>, field: string, locale: Locale): string {
  return term[`${field}_${locale}`] || term[`${field}_ko`] || '';
}

/** Level labels for basic/advanced switcher */
export const levelLabels: Record<Locale, Record<string, string>> = {
  en: { basic: 'Basic', advanced: 'Advanced' },
  ko: { basic: '기초', advanced: '심화' },
};
