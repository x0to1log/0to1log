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
  term_full: string;
  categories: string[];
  summary: string;
  definition: string;
  basic_plain: string;
}

function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function getLocale(): string {
  return document.documentElement.lang || 'en';
}

function getActivePersona(): string {
  // News/blog: data-persona on persona switcher
  const personaBtn = document.querySelector('.persona-switcher-btn--active, .persona-float-btn--active[data-persona]');
  if (personaBtn) return personaBtn.getAttribute('data-persona') || 'learner';

  // Handbook: data-level on level switcher (basic→learner, advanced→expert)
  const levelBtn = document.querySelector('.handbook-level-btn--active');
  if (levelBtn) {
    const level = levelBtn.getAttribute('data-level');
    return level === 'advanced' ? 'expert' : 'learner';
  }

  return 'learner';
}

/** Extract first section content from basic body markdown (before second ##) */
function extractFirstSection(md: string): string {
  if (!md) return '';
  const stripped = md.replace(/^##\s+[^\n]*\n+/, '');
  const nextHeading = stripped.indexOf('\n##');
  const section = nextHeading > 0 ? stripped.slice(0, nextHeading).trim() : stripped.trim();
  return section;
}

/** Lightweight markdown → HTML for popup (handles ###, **, - lists) */
function miniMd(md: string): string {
  const lines = md.split('\n');
  let html = '';
  let inList = false;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      if (inList) { html += '</ul>'; inList = false; }
      continue;
    }

    // Inline formatting: **bold**
    const fmt = (s: string) => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // ### heading
    if (line.startsWith('### ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<div class="handbook-popup-subhead">${fmt(line.slice(4))}</div>`;
      continue;
    }

    // - bullet list
    if (line.startsWith('- ')) {
      if (!inList) { html += '<ul class="handbook-popup-list">'; inList = true; }
      html += `<li>${fmt(line.slice(2))}</li>`;
      continue;
    }

    // Regular paragraph
    if (inList) { html += '</ul>'; inList = false; }
    html += `<p>${fmt(line)}</p>`;
  }

  if (inList) html += '</ul>';
  return html;
}

function buildPopupHtml(data: TermData, slug: string): string {
  const locale = getLocale();
  const persona = getActivePersona();
  const isLearner = persona === 'learner';
  const catLabel = (data.categories && data.categories.length > 0)
    ? data.categories[0].replace(/-/g, ' ').toUpperCase()
    : (locale === 'ko' ? '용어집' : 'GLOSSARY');
  const learnMoreText = locale === 'ko' ? '자세히 보기 →' : 'Full entry →';

  let html = `<div class="handbook-popup${isLearner ? ' handbook-popup--learner' : ''}" role="dialog" aria-describedby="handbook-popup-desc">`;

  html += `<div class="handbook-popup-header">`;
  html += `<span class="handbook-popup-cat">${esc(catLabel)}</span>`;
  html += `<button class="handbook-popup-close" type="button" aria-label="Close">`;
  html += `<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">`;
  html += `<line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/>`;
  html += `</svg>`;
  html += `</button>`;
  html += `</div>`;

  // Title row: always show term, add korean_name only for KO locale
  html += `<div class="handbook-popup-title-row">`;
  html += `<span class="handbook-popup-term">${esc(data.term)}</span>`;
  if (locale === 'ko' && data.korean_name) {
    html += `<span class="handbook-popup-korean">${esc(data.korean_name)}</span>`;
  }
  html += `</div>`;

  // term_full (shown for both personas)
  if (data.term_full && data.term_full !== data.term) {
    html += `<div class="handbook-popup-fullname">${esc(data.term_full)}</div>`;
  }

  html += `<div class="handbook-popup-rule"></div>`;

  // Body: learner gets summary (preferred) or basic first section; expert gets definition.
  // Definition is intentionally NOT a learner fallback — it's technical and breaks learner UX.
  html += `<div class="handbook-popup-content" id="handbook-popup-desc">`;
  if (isLearner) {
    if (data.summary) {
      html += `<p>${esc(data.summary).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</p>`;
    } else if (data.basic_plain) {
      const section = extractFirstSection(data.basic_plain);
      html += miniMd(section);
    }
  } else if (data.definition) {
    html += `<p>${esc(data.definition).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</p>`;
  }
  html += `</div>`;

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
      // A primary term inside a §7 related-terms row is the anchor
      // of a wrapping <a class="hb-related-terms__row-link">. Skip
      // the popup and let the row's <a> navigate directly — the row
      // reads as a single clickable entry to that term's page. Non-
      // primary .handbook-term spans (e.g., terms mentioned inside
      // the description) still fall through to the popup path.
      if (termSpan.dataset.primaryTerm === 'true') {
        return;
      }
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
