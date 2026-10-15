/**
 * Keep only the handbook terms a page actually links to.
 *
 * Detail pages embed term data for the inline popup (handbook-popup.ts).
 * Embedding the whole index made it ~700 KB of an ~840 KB page while a
 * typical article references fewer than 10 terms. The popup reads
 * `.handbook-term[data-slug]` spans and `/handbook/<slug>` links, and
 * navigates to the term page when a slug has no embedded data.
 */
const TERM_SLUG_PATTERNS = [
  /data-slug="([^"]+)"/g,
  /\/handbook\/([^/"?#\s]+)/g,
];

export function pickReferencedTerms<T>(
  terms: Record<string, T>,
  htmlParts: Array<string | null | undefined>,
): Record<string, T> {
  const referenced = new Set<string>();
  for (const html of htmlParts) {
    if (!html) continue;
    for (const pattern of TERM_SLUG_PATTERNS) {
      for (const match of html.matchAll(pattern)) referenced.add(match[1]);
    }
  }

  const picked: Record<string, T> = {};
  for (const slug of referenced) {
    if (slug in terms) picked[slug] = terms[slug];
  }
  return picked;
}
