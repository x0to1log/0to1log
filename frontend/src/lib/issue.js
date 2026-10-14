// frontend/src/lib/issue.js
// Newspaper-style issue number: day 1 = first published news (KST).
// Deterministic, no DB access. Used by NewsprintShell's kicker.

/** First published news date in KST (news_posts, 2026-03-18). */
export const ISSUE_EPOCH = '2026-03-18';

const DAY_MS = 24 * 60 * 60 * 1000;
const kstDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
});

function dayIndex(ymd) {
  const [y, m, d] = ymd.split('-').map(Number);
  return Date.UTC(y, m - 1, d) / DAY_MS;
}

/** @returns {number|null} 1-based issue number for the KST calendar day of `date` */
export function issueNumber(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return null;
  const diff = dayIndex(kstDate.format(date)) - dayIndex(ISSUE_EPOCH);
  return Math.max(1, diff + 1);
}

/** @param {'ko'|'en'} locale */
export function issueLabel(locale, n) {
  if (n == null) return '';
  return locale === 'ko' ? `제${n}호` : `No. ${n}`;
}
