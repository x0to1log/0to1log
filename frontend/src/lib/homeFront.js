// frontend/src/lib/homeFront.js
// Pure selection for the home front page (lead, sibling, earlier, keyword plate). No I/O.
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
 * Keyword plate text for the lead story: tags[0] small over tags[1] big;
 * one tag -> big only; no tags -> the lead's KST date as MM.DD.
 * @returns {{small: string|null, big: string}|null}
 */
export function frontKeyword(lead) {
  if (!lead) return null;
  const tags = (Array.isArray(lead.tags) ? lead.tags : [])
    .map((t) => (typeof t === 'string' ? t.trim() : ''))
    .filter(Boolean);
  if (tags.length >= 2) return { small: tags[0], big: tags[1] };
  if (tags.length === 1) return { small: null, big: tags[0] };
  const day = kstDay(lead.published_at);
  return day ? { small: null, big: `${day.slice(5, 7)}.${day.slice(8, 10)}` } : null;
}

/**
 * @param {{ news: Array<{slug:string, post_type?:string|null, published_at:string|null, tags?:string[]|null}>, term?: object|null, now?: Date }} input
 * news must be ordered by published_at desc. term is the already-chosen term of the day.
 */
export function selectFrontPage({ news, term = null, now = new Date() }) {
  const today = kstDay(now);
  const lead = news[0] ?? null;
  const leadDay = lead ? kstDay(lead.published_at) : null;
  const sibling = leadDay
    ? news.find((n, i) => i > 0 && kstDay(n.published_at) === leadDay && n.post_type !== lead.post_type) ?? null
    : null;
  const earlier = leadDay
    ? news.filter((n) => {
        const day = kstDay(n.published_at);
        return day !== null && day < leadDay;
      }).slice(0, 2)
    : [];
  const todayCount = news.filter((n) => kstDay(n.published_at) === today).length;

  return {
    lead,
    leadIsToday: leadDay !== null && leadDay === today,
    sibling,
    earlier,
    todayCount,
    term,
    keyword: frontKeyword(lead),
  };
}
