/**
 * Inline handbook term popup.
 *
 * Reads term data from #handbook-terms-data JSON embed,
 * attaches click handlers to .handbook-term spans,
 * and shows a popup with persona-adapted content.
 */

interface TermData {
  term: string;
  korean_name: string;
  difficulty: string;
  categories: string[];
  definition: string;
  plain_explanation: string;
  technical_description: string;
  example_analogy: string;
}

function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function getPersona(): string {
  try {
    return localStorage.getItem('handbook-persona') || 'learner';
  } catch {
    return 'learner';
  }
}

function getPopupContent(data: TermData, persona: string): { primary: string; secondary: string } {
  // Persona mapping from spec section 8:
  // Beginner/Learner → plain_explanation + example_analogy
  // Expert → technical_description + plain_explanation
  if (persona === 'expert') {
    return {
      primary: data.technical_description || data.plain_explanation || data.definition,
      secondary: data.plain_explanation || '',
    };
  }
  // beginner + learner
  return {
    primary: data.plain_explanation || data.definition,
    secondary: data.example_analogy || '',
  };
}

function getLocale(): string {
  return document.documentElement.lang || 'en';
}

function buildPopupHtml(data: TermData, persona: string): string {
  const locale = getLocale();
  const { primary, secondary } = getPopupContent(data, persona);
  const diffLabel = data.difficulty || '';
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
  if (primary) html += `<p>${esc(primary)}</p>`;
  if (secondary && secondary !== primary) html += `<p class="handbook-popup-secondary">${esc(secondary)}</p>`;
  html += `</div>`;
  html += `<div class="handbook-popup-footer">`;
  if (diffLabel) html += `<span class="handbook-popup-difficulty handbook-popup-difficulty--${diffLabel}">${diffLabel}</span>`;
  if (catLabels) html += `<span class="handbook-popup-categories">${esc(catLabels)}</span>`;
  html += `<a href="/${locale}/handbook/" class="handbook-popup-link">${learnMoreText}</a>`;
  html += `</div>`;
  html += `</div>`;
  return html;
}

function positionPopup(popup: HTMLElement, anchor: HTMLElement): void {
  const rect = anchor.getBoundingClientRect();
  const scrollY = window.scrollY;
  const scrollX = window.scrollX;

  // Position below the term by default
  popup.style.position = 'absolute';
  popup.style.left = `${rect.left + scrollX}px`;
  popup.style.top = `${rect.bottom + scrollY + 8}px`;

  // After rendering, check if popup overflows viewport
  requestAnimationFrame(() => {
    const popupRect = popup.getBoundingClientRect();

    // If overflows right, shift left
    if (popupRect.right > window.innerWidth - 16) {
      popup.style.left = `${window.innerWidth - popupRect.width - 16 + scrollX}px`;
    }

    // If overflows bottom, show above
    if (popupRect.bottom > window.innerHeight) {
      popup.style.top = `${rect.top + scrollY - popupRect.height - 8}px`;
    }

    // Ensure not off-screen left
    if (popupRect.left < 16) {
      popup.style.left = `${16 + scrollX}px`;
    }
  });
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

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePopup();
  });

  // Close on click outside
  document.addEventListener('click', (e) => {
    if (!activePopup) return;
    const target = e.target as HTMLElement;
    if (activePopup.contains(target) || target.closest('.handbook-term')) return;
    closePopup();
  });

  // Bind click handlers on .handbook-term spans
  document.querySelectorAll<HTMLElement>('.handbook-term').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const slug = el.dataset.slug || '';
      const data = termsData[slug];
      if (!data) return;

      // Toggle if same popup
      if (activePopup && activePopup.dataset.forSlug === slug) {
        closePopup();
        return;
      }

      closePopup();

      const persona = getPersona();
      const html = buildPopupHtml(data, persona);
      const container = document.createElement('div');
      container.innerHTML = html;
      const popup = container.firstElementChild as HTMLElement;
      popup.dataset.forSlug = slug;

      document.body.appendChild(popup);
      activePopup = popup;

      positionPopup(popup, el);

      // Close button inside popup
      popup.querySelector('.handbook-popup-close')?.addEventListener('click', closePopup);
    });
  });
}

document.addEventListener('astro:page-load', initHandbookPopup);
