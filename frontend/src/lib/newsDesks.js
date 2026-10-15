// frontend/src/lib/newsDesks.js
// Pure grouping for the news list "two desks" page: one row per KST day
// (business | date | research), weekly recaps as their own entries. No I/O.
import { kstDay } from './homeFront.js';
import { issueLabel, issueNumber } from './issue.js';

const deskOf = (type) => (type === 'research' ? 'research' : 'business');
const newestFirst = (a, b) => String(b.published_at).localeCompare(String(a.published_at));

/**
 * @param {Array<{post_type?: string|null, published_at: string|null}>} posts daily + weekly, any order
 * @param {Date} [now]
 * @returns {Array<
 *   {kind: 'weekly', day: string, post: object} |
 *   {kind: 'day', day: string, showDate: boolean, isToday: boolean, business: object|null, research: object|null}
 * >} newest KST day first; a day's weekly recaps come before its rows
 */
export function buildDeskRows(posts, now = new Date()) {
  const today = kstDay(now);
  const byDay = new Map();
  for (const post of posts) {
    const day = kstDay(post.published_at);
    if (!day) continue;
    if (!byDay.has(day)) byDay.set(day, { weekly: [], business: [], research: [] });
    const bucket = byDay.get(day);
    if (post.post_type === 'weekly') bucket.weekly.push(post);
    else bucket[deskOf(post.post_type)].push(post);
  }

  const entries = [];
  for (const day of [...byDay.keys()].sort().reverse()) {
    const { weekly, business, research } = byDay.get(day);
    for (const post of weekly.sort(newestFirst)) entries.push({ kind: 'weekly', day, post });
    business.sort(newestFirst);
    research.sort(newestFirst);
    const rows = Math.max(business.length, research.length);
    for (let i = 0; i < rows; i += 1) {
      entries.push({
        kind: 'day',
        day,
        showDate: i === 0,
        isToday: day === today,
        business: business[i] ?? null,
        research: research[i] ?? null,
      });
    }
  }
  return entries;
}

/** Date spine labels for a KST day (YYYY-MM-DD). */
export function deskDateParts(day, locale) {
  const noon = new Date(`${day}T12:00:00+09:00`);
  return {
    short: `${day.slice(5, 7)}.${day.slice(8, 10)}`,
    weekday: noon.toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', { timeZone: 'Asia/Seoul', weekday: 'short' }),
    issue: issueLabel(locale, issueNumber(noon)),
  };
}
