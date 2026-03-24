/**
 * Inline handbook term popup.
 *
 * Two trigger sources:
 * 1. `.handbook-term` spans (legacy inline markup)
 * 2. `<a href="/handbook/*">` links inside `.newsprint-prose` (auto-linked terms)
 *
 * Reads term data from #handbook-terms-data JSON embed,
 * shows a popup with the term definition + "Learn more" link to full page.
 */

interface TermData {
  term: string;
  korean_name: string;
  categories: string[];
  definition: string;
}

function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function getLocale(): string {
  return document.documentElement.lang || 'en';
}

function buildPopupHtml(data: TermData, slug: string): string {
  const locale = getLocale();
  const catLabel = (data.categories && data.categories.length > 0)
    ? data.categories[0].replace(/-/g, ' ').toUpperCase()
    : (locale === 'ko' ? '용어집' : 'GLOSSARY');
  const learnMoreText = locale === 'ko' ? '전체 항목 보기 →' : 'Full entry →';

  let html = `<div class="handbook-popup" role="dialog" aria-describedby="handbook-popup-desc">`;

  html += `<div class="handbook-popup-header">`;
  html += `<span class="handbook-popup-cat">${esc(catLabel)}</span>`;
  html += `<button class="handbook-popup-close" type="button" aria-label="Close">`;
  html += `<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">`;
  html += `<line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/>`;
  html += `</svg>`;
  html += `</button>`;
  html += `</div>`;

  html += `<div class="handbook-popup-title-row">`;
  html += `<span class="handbook-popup-term">${esc(data.term)}</span>`;
  if (data.korean_name) {
    html += `<span class="handbook-popup-korean">${esc(data.korean_name)}</span>`;
  }
  html += `</div>`;

  html += `<div class="handbook-popup-rule"></div>`;

  if (data.definition) {
    html += `<div class="handbook-popup-content" id="handbook-popup-desc">`;
    html += `<p>${esc(data.definition).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</p>`;
    html += `</div>`;
  }

  html += `<div class="handbook-popup-footer">`;
  html += `<a href="/${locale}/handbook/${slug}/" class="handbook-popup-link">${learnMoreText}</a>`;
  html += `</div>`;

  html += `</div>`;
  return html;
}

function positionPopup(popup: HTMLElement, anchor: HTMLElement): void {
  const rect = anchor.getBoundingClientRect();
  const scrollY = window.scrollY;
  const scrollX = window.scrollX;

  popup.style.position = 'absolute';
  popup.style.left = `${rect.left + scrollX}px`;
  popup.style.top = `${rect.bottom + scrollY + 8}px`;

  requestAnimationFrame(() => {
    const popupRect = popup.getBoundingClientRect();

    if (popupRect.right > window.innerWidth - 16) {
      popup.style.left = `${window.innerWidth - popupRect.width - 16 + scrollX}px`;
    }

    if (popupRect.bottom > window.innerHeight) {
      popup.style.top = `${rect.top + scrollY - popupRect.height - 8}px`;
    }

    if (popupRect.left < 16) {
      popup.style.left = `${16 + scrollX}px`;
    }
  });
}

/** Extract slug from a handbook URL path like /ko/handbook/slug/ or /handbook/slug/ */
function extractSlugFromHref(href: string): string {
  const match = href.match(/\/handbook\/([^/]+)\/?$/);
  return match ? match[1] : '';
}

let _popupAbort: AbortController | null = null;

function initHandbookPopup(): void {
  // Tear down previous listeners to prevent duplicates on SPA navigation
  if (_popupAbort) _popupAbort.abort();
  _popupAbort = new AbortController();
  const { signal } = _popupAbort;

  const dataEl = document.getElementById('handbook-terms-data');
  if (!dataEl) return;

  let termsData: Record<string, TermData>;
  try {
    termsData = JSON.parse(dataEl.textContent || '{}');
  } catch {
    return;
  }

  if (Object.keys(termsData).length === 0) return;

  let activePopup: HTMLElement | null = null;

  function closePopup(): void {
    if (activePopup) {
      activePopup.remove();
      activePopup = null;
    }
  }

  function showPopup(slug: string, anchor: HTMLElement): void {
    const data = termsData[slug];
    if (!data) return;

    if (activePopup && activePopup.dataset.forSlug === slug) {
      closePopup();
      return;
    }

    closePopup();

    const html = buildPopupHtml(data, slug);
    const container = document.createElement('div');
    container.innerHTML = html;
    const popup = container.firstElementChild as HTMLElement;
    popup.dataset.forSlug = slug;

    document.body.appendChild(popup);
    activePopup = popup;

    positionPopup(popup, anchor);

    popup.querySelector('.handbook-popup-close')?.addEventListener('click', closePopup);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePopup();
  }, { signal });

  // Single delegated click handler — works for dynamically swapped content
  // Use capture: true so this handler runs BEFORE Astro's View Transitions router,
  // which also uses { capture: true } to intercept <a> link clicks for soft navigation.
  // Without capture, VT navigates to /handbook/slug/ (no locale prefix → 404) before
  // our popup handler gets a chance to preventDefault.
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;

    // Source 1: .handbook-term spans
    const termSpan = target.closest<HTMLElement>('.handbook-term');
    if (termSpan) {
      e.preventDefault();
      e.stopPropagation();
      const slug = termSpan.dataset.slug || '';
      showPopup(slug, termSpan);
      return;
    }

    // Source 2: <a href="/handbook/*"> links inside prose content
    const termLink = target.closest<HTMLAnchorElement>('.newsprint-prose a[href*="/handbook/"]');
    if (termLink) {
      const slug = extractSlugFromHref(termLink.getAttribute('href') || '');
      if (slug) {
        e.preventDefault();
        e.stopPropagation();
        if (termsData[slug]) {
          showPopup(slug, termLink);
        } else {
          // Term not in local data — navigate to locale-prefixed handbook page
          window.location.href = `/${getLocale()}/handbook/${slug}/`;
        }
        return;
      }
    }

    // Click outside — close popup
    if (activePopup && !activePopup.contains(target)) {
      closePopup();
    }
  }, { signal, capture: true });
}

document.addEventListener('astro:page-load', initHandbookPopup);
