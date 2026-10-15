// Display label for news post_type. Single source for cards, headlines, rails, home and article head.
const LABELS = {
  ko: { business: '비즈니스', research: '리서치', weekly: '주간 정리' },
  en: { business: 'Business', research: 'Research', weekly: 'Weekly' },
};

/** @param {'ko'|'en'} locale */
export function postTypeLabel(locale, type) {
  const table = LABELS[locale] ?? LABELS.en;
  return (type && Object.prototype.hasOwnProperty.call(table, type)) ? table[type] : '';
}
