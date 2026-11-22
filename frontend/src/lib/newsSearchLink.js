// frontend/src/lib/newsSearchLink.js
// Carries the news list's search text to a story link as ?q=, so the article can highlight it
// and show its find box. Pure string work; no DOM, no I/O.

/**
 * @param {string} href story link, e.g. "/ko/news/some-slug/" (may already have a query or hash)
 * @param {string} [query] the search text as typed; empty or blank removes q
 * @returns {string} the same link with q set to the trimmed query, or without q
 */
export function withFindQuery(href, query) {
  const hashAt = href.indexOf('#');
  const hash = hashAt >= 0 ? href.slice(hashAt) : '';
  const beforeHash = hashAt >= 0 ? href.slice(0, hashAt) : href;
  const queryAt = beforeHash.indexOf('?');
  const path = queryAt >= 0 ? beforeHash.slice(0, queryAt) : beforeHash;
  const params = new URLSearchParams(queryAt >= 0 ? beforeHash.slice(queryAt + 1) : '');

  const text = (query ?? '').trim();
  if (text) params.set('q', text);
  else params.delete('q');

  const search = params.toString();
  return path + (search ? `?${search}` : '') + hash;
}
