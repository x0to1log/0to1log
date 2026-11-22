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

/** KST calendar day (YYYY-MM-DD) → UTC ISO range [start, end). null for bad input. */
export function deskDayRange(day) {
  if (typeof day !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const start = new Date(`${day}T00:00:00+09:00`);
  if (Number.isNaN(start.getTime()) || kstDay(start) !== day) return null;
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
  return { start: start.toISOString(), end: end.toISOString() };
}

/** How many days the list shows before the "more" button. */
export const RECENT_DAYS = 14;

/**
 * Oldest KST day (YYYY-MM-DD) still shown before "more".
 * @param {string[]} days distinct days that have entries, newest first
 * @returns {string|null}
 */
export function recentCutoff(days) {
  // ── Amy 결정 지점 (Task 1 Step 5) ──────────────────────────────────────
  // 기본 제안: 발행된 날 RECENT_DAYS개까지가 "최근"이다(달력 날짜가 아니다).
  if (days.length === 0) return null;
  return days[Math.min(days.length, RECENT_DAYS) - 1];
}

/**
 * Adds month dividers and an `older` flag to buildDeskRows() output. Pure; input untouched.
 * @param {Array<{kind: 'weekly'|'day', day: string}>} entries newest first
 * @returns {Array<object>} same entries plus {kind: 'month', month: 'YYYY-MM', older}
 */
export function addListBreaks(entries) {
  const cutoff = recentCutoff([...new Set(entries.map((entry) => entry.day))]);
  const out = [];
  let month = entries[0]?.day.slice(0, 7);
  for (const entry of entries) {
    const older = cutoff !== null && entry.day < cutoff;
    const entryMonth = entry.day.slice(0, 7);
    if (entryMonth !== month) {
      out.push({ kind: 'month', month: entryMonth, older });
      month = entryMonth;
    }
    out.push({ ...entry, older });
  }
  return out;
}

/** "2026년 10월" / "October 2026" for a YYYY-MM month. */
export function monthLabel(month, locale) {
  return new Date(`${month}-15T12:00:00+09:00`).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'long',
  });
}
