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
  const catLabels = (data.categories || []).join(' · ');
  const learnMoreText = locale === 'ko' ? '자세히 보기' : 'Learn more';

  let html = `<div class="handbook-popup" role="dialog" aria-describedby="handbook-popup-desc">`;
  html += `<div class="handbook-popup-header">`;
  html += `<span class="handbook-popup-term">${esc(data.term)}</span>`;
  if (data.korean_name) {
    html += ` <span class="handbook-popup-korean">${esc(data.korean_name)}</span>`;
  }
  html += `<button class="handbook-popup-close" type="button" aria-label="Close">&times;</button>`;
  html += `</div>`;
  html += `<div class="handbook-popup-content" id="handbook-popup-desc">`;
  if (data.definition) html += `<p>${esc(data.definition)}</p>`;
  html += `</div>`;
  html += `<div class="handbook-popup-footer">`;
  if (catLabels) html += `<span class="handbook-popup-categories">${esc(catLabels)}</span>`;
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

function initHandbookPopup(): void {
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
  });

  document.addEventListener('click', (e) => {
    if (!activePopup) return;
    const target = e.target as HTMLElement;
    if (
      activePopup.contains(target) ||
      target.closest('.handbook-term') ||
      target.closest('a[href*="/handbook/"]')
    ) return;
    closePopup();
  });

  // Source 1: .handbook-term spans
  document.querySelectorAll<HTMLElement>('.handbook-term').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const slug = el.dataset.slug || '';
      showPopup(slug, el);
    });
  });

  // Source 2: <a href="/handbook/*"> links inside prose content
  document.querySelectorAll<HTMLAnchorElement>('.newsprint-prose a[href*="/handbook/"]').forEach(link => {
    const slug = extractSlugFromHref(link.getAttribute('href') || '');
    if (!slug || !termsData[slug]) return; // no popup data → let it navigate normally

    link.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      showPopup(slug, link);
    });
  });
}

document.addEventListener('astro:page-load', initHandbookPopup);
