// frontend/src/lib/homeFront.js
// Pure selection for the home "오늘의 1면" strip. No I/O.
import { issueNumber } from './issue.js';

const kstFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
});

/** @returns {string|null} YYYY-MM-DD of the KST calendar day */
export function kstDay(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : kstFormat.format(date);
}

/**
 * @param {{ news: Array<{slug:string, published_at:string|null}>, terms: Array<{slug:string}>, now?: Date }} input
 * news must be ordered by published_at desc.
 */
export function selectFrontPage({ news, terms, now = new Date() }) {
  const today = kstDay(now);
  const lead = news[0] ?? null;
  const leadDay = lead ? kstDay(lead.published_at) : null;
  const second = news[1] ?? null;
  const also = second && leadDay && kstDay(second.published_at) === leadDay ? second : null;
  const todayCount = news.filter((n) => kstDay(n.published_at) === today).length;

  let term = null;
  if (terms.length > 0) {
    const sorted = [...terms].sort((a, b) => a.slug.localeCompare(b.slug));
    term = sorted[(issueNumber(now) ?? 0) % sorted.length];
  }
  return { lead, also, todayCount, term };
}
