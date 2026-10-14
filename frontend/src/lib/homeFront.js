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
 * Index of the term of the day among `count` terms (issue number % count).
 * @returns {number|null}
 */
export function termIndex(now, count) {
  return count > 0 ? (issueNumber(now) ?? 0) % count : null;
}

/**
 * @param {{ news: Array<{slug:string, published_at:string|null}>, term?: object|null, now?: Date }} input
 * news must be ordered by published_at desc. term is the already-chosen term of the day.
 */
export function selectFrontPage({ news, term = null, now = new Date() }) {
  const today = kstDay(now);
  const lead = news[0] ?? null;
  const leadDay = lead ? kstDay(lead.published_at) : null;
  const second = news[1] ?? null;
  const also = second && leadDay && kstDay(second.published_at) === leadDay ? second : null;
  const todayCount = news.filter((n) => kstDay(n.published_at) === today).length;

  return { lead, also, todayCount, term };
}
