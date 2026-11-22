// frontend/src/scripts/newsDeskMode.ts
// News list: two-desk layout when the "all" tab is active and the search box is empty,
// single-column list otherwise. Rows whose cards are all hidden get data-row-empty.
// Runs after NewsprintCategoryFilter (data-filtered) and newsListSearch (data-search-matched).

// Also runs the "more" button: older entries are folded by CSS until data-expanded is true.
const EXPANDED_KEY = 'news-list-expanded';

function wasExpanded(): boolean {
  try { return sessionStorage.getItem(EXPANDED_KEY) === '1'; } catch { return false; }
}

function expand(root: HTMLElement, moveFocus: boolean): void {
  root.dataset.expanded = 'true';
  try { sessionStorage.setItem(EXPANDED_KEY, '1'); } catch { /* storage blocked: nothing to remember */ }
  // The button disappears once expanded, so hand focus to the first story it revealed.
  if (moveFocus) root.querySelector<HTMLElement>('[data-older="true"] a')?.focus();
}

// View-transition navigations restore scroll before astro:page-load, so the incoming list
// must already be unfolded when it is swapped in (full loads use the inline script in NewsDeskList).
document.addEventListener('astro:before-swap', (event) => {
  if (!wasExpanded()) return;
  const incoming = (event as Event & { newDocument?: Document }).newDocument;
  incoming?.querySelector('.news-desks')?.setAttribute('data-expanded', 'true');
});

function activeFilter(): string {
  const tab = document.querySelector<HTMLElement>(
    '.newsprint-filter-tabs[data-filter-key="post_type"] .newsprint-filter-tab[aria-selected="true"]',
  );
  return tab?.dataset.filter || new URLSearchParams(window.location.search).get('post_type') || 'all';
}

function update(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root) return;
  const search = document.getElementById('news-search') as HTMLInputElement | null;
  const query = (search?.value ?? '').trim();
  root.dataset.mode = activeFilter() === 'all' && !query ? 'desks' : 'list';

  root.querySelectorAll<HTMLElement>('.news-desk-row, .news-desk-weekly').forEach((row) => {
    const hasVisible = Array.from(row.querySelectorAll<HTMLElement>('.newsprint-card')).some(
      (card) => card.dataset.filtered !== 'false' && card.dataset.searchMatched !== 'false',
    );
    if (hasVisible) row.removeAttribute('data-row-empty');
    else row.setAttribute('data-row-empty', 'true');
  });
}

function init(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root || root.dataset.deskModeReady === 'true') return;
  root.dataset.deskModeReady = 'true';
  if (wasExpanded()) expand(root, false);
  root.querySelector<HTMLElement>('[data-news-more]')?.addEventListener('click', () => expand(root, true));
  window.addEventListener('newsprint:filter-change', () => requestAnimationFrame(update));
  window.addEventListener('news:list-updated', update);
  update();
}

document.addEventListener('astro:page-load', init);
init();
