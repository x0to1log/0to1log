// frontend/src/scripts/productCatalog.ts
// Products catalog (/ko|en/products/) modes. Rows are rendered once on the server; this only shows/hides them.
// - default: jump bar + picks + every field (six rows each)
// - field (?cat=id, "See all"): that field only, every row, full description, "also used for this" clones
// - search (?q=): every field expanded, rows whose data-search-text contains the query
// Bundled module (not is:inline): runs on every astro:page-load; #products-top carries the binding guard.

const DEBOUNCE_MS = 150;

function initProductCatalog(): void {
  const root = document.getElementById('products-top');
  const input = document.getElementById('product-search') as HTMLInputElement | null;
  if (!root || !input || root.dataset.catalogReady === 'true') return;
  if (!root.classList.contains('product-catalog')) return;
  root.dataset.catalogReady = 'true';

  const sections = Array.from(root.querySelectorAll<HTMLElement>('section.product-cat'));
  // Original rows, collected once: clones added to the "also" lists later are never filtered.
  const rows = Array.from(root.querySelectorAll<HTMLElement>('.product-cat-list > li.product-row'));
  const browse = Array.from(root.querySelectorAll<HTMLElement>('.product-catalog-jump, .product-picks'));
  const backButton = root.querySelector<HTMLButtonElement>('.product-catalog-back');
  const noResults = document.getElementById('product-search-no-results');
  const alsoLabel = root.dataset.alsoLabel || '{k}';
  const fieldIds = new Set(sections.map((section) => section.dataset.category || ''));
  let lastSeeAll: HTMLButtonElement | null = null;
  let timer: number | undefined;

  const show = (el: Element | null, visible: boolean) => {
    if (el) (el as HTMLElement).hidden = !visible;
  };
  const part = (section: HTMLElement, selector: string) => section.querySelector<HTMLElement>(selector);

  function clearAlso(): void {
    root!.querySelectorAll<HTMLElement>('.product-cat-also').forEach((box) => {
      box.hidden = true;
      box.querySelector('ol')?.replaceChildren();
    });
  }

  function showDefault(): void {
    clearAlso();
    browse.forEach((el) => show(el, true));
    sections.forEach((section) => {
      section.hidden = false;
      delete section.dataset.expanded;
      show(part(section, '.product-cat-lede'), true);
      show(part(section, '.product-cat-desc'), false);
      show(part(section, '.product-cat-all'), true);
    });
    rows.forEach((row) => { row.hidden = false; });
    show(backButton, false);
    show(noResults, false);
  }

  function showField(id: string): void {
    showDefault();
    const target = sections.find((section) => section.dataset.category === id);
    if (!target) return;
    browse.forEach((el) => show(el, false));
    sections.forEach((section) => { section.hidden = section !== target; });
    target.dataset.expanded = '';
    show(part(target, '.product-cat-lede'), false);
    show(part(target, '.product-cat-desc'), true);
    show(part(target, '.product-cat-all'), false);

    const box = part(target, '.product-cat-also');
    const list = box?.querySelector('ol');
    const also = rows.filter((row) => (
      row.dataset.category !== id
      && (row.dataset.secondaryCategories || '').split(',').includes(id)
    ));
    if (box && list && also.length > 0) {
      also.forEach((row) => {
        const copy = row.cloneNode(true) as HTMLElement;
        copy.removeAttribute('data-overflow');
        copy.removeAttribute('hidden');
        list.appendChild(copy);
      });
      const title = box.querySelector('h3');
      if (title) title.textContent = alsoLabel.replace('{k}', String(also.length));
      box.hidden = false;
    }
    show(backButton, true);
  }

  function showSearch(query: string): void {
    showDefault();
    clearAlso();
    browse.forEach((el) => show(el, false));
    const visibleBySection = new Map<HTMLElement, number>();
    rows.forEach((row) => {
      const match = (row.dataset.searchText || '').includes(query);
      row.hidden = !match;
      const section = row.closest<HTMLElement>('section.product-cat');
      if (section && match) visibleBySection.set(section, (visibleBySection.get(section) || 0) + 1);
    });
    let total = 0;
    sections.forEach((section) => {
      const count = visibleBySection.get(section) || 0;
      total += count;
      section.hidden = count === 0;
      section.dataset.expanded = '';
      show(part(section, '.product-cat-lede'), false);
      show(part(section, '.product-cat-all'), false);
    });
    show(noResults, total === 0);
    show(backButton, true);
  }

  function setParams(update: (params: URLSearchParams) => void): void {
    const url = new URL(window.location.href);
    update(url.searchParams);
    history.replaceState(history.state, '', url.toString());
  }

  function applyQuery(): void {
    window.clearTimeout(timer);
    const raw = input!.value.trim();
    if (raw) {
      setParams((params) => { params.set('q', raw); params.delete('cat'); });
      showSearch(raw.toLowerCase());
    } else {
      setParams((params) => { params.delete('q'); params.delete('cat'); });
      showDefault();
    }
  }

  input.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(applyQuery, DEBOUNCE_MS);
  });

  // Enter: filter in place. Capture phase + stopImmediatePropagation so ProductSearchBar's own
  // submit handler (detail pages: go to the list) never reloads this page.
  input.form?.addEventListener('submit', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    applyQuery();
  }, true);

  root.querySelectorAll<HTMLButtonElement>('.product-cat-all').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.dataset.category || '';
      if (!fieldIds.has(id)) return;
      lastSeeAll = button;
      window.clearTimeout(timer);
      input!.value = '';
      setParams((params) => { params.delete('q'); params.set('cat', id); });
      showField(id);
      const section = sections.find((s) => s.dataset.category === id);
      section?.scrollIntoView({ block: 'start' });
      section?.querySelector<HTMLElement>('.product-cat-title')?.focus({ preventScroll: true });
    });
  });

  backButton?.addEventListener('click', () => {
    window.clearTimeout(timer);
    input!.value = '';
    setParams((params) => { params.delete('q'); params.delete('cat'); });
    showDefault();
    const returnTo = lastSeeAll && lastSeeAll.isConnected ? lastSeeAll : null;
    lastSeeAll = null;
    if (returnTo) returnTo.focus();
    else root!.scrollIntoView({ block: 'start' });
  });

  const params = new URLSearchParams(window.location.search);
  const initialQuery = (params.get('q') || '').trim();
  const initialField = params.get('cat') || '';
  if (initialQuery) {
    input.value = initialQuery;
    showSearch(initialQuery.toLowerCase());
  } else if (initialField && fieldIds.has(initialField)) {
    showField(initialField);
  }
}

document.addEventListener('astro:page-load', initProductCatalog);
initProductCatalog();
