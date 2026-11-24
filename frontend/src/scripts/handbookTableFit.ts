/**
 * Handbook tables that do not fit their column.
 *
 * Korean text wraps between words (word-break: keep-all), so a table cannot get narrower than its
 * longest word per column, and on a phone some tables end up wider than the screen. CSS cannot say
 * "break inside a word only if the table does not fit otherwise": allowing it for every table makes
 * the browser squeeze columns that had room. So this measures each table in its normal state and
 * marks only the ones that overflow; global.css lets those break inside words.
 *
 * Without this script a wide table simply scrolls sideways, as before.
 */
function fitTables(): void {
  const tables = document.querySelectorAll<HTMLTableElement>('#handbook-body table');
  if (tables.length === 0) return;
  // Measure every table loose first (one layout pass), then mark.
  tables.forEach((table) => table.removeAttribute('data-fit'));
  const overflowing = Array.from(tables).filter((table) => table.scrollWidth - table.clientWidth > 1);
  overflowing.forEach((table) => table.setAttribute('data-fit', 'tight'));
}

let queued = false;
function queueFit(): void {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    queued = false;
    fitTables();
  });
}

let lastWidth = window.innerWidth;

fitTables();
document.addEventListener('astro:page-load', queueFit);
// The level switch replaces the body's HTML and then announces it with this event.
window.addEventListener('reading-content-changed', queueFit);
window.addEventListener('resize', () => {
  // Phone browsers fire resize when the address bar slides; only a width change matters here.
  if (window.innerWidth === lastWidth) return;
  lastWidth = window.innerWidth;
  queueFit();
});
// Web fonts arriving later change the width of every word.
document.fonts?.ready.then(queueFit).catch(() => {});
