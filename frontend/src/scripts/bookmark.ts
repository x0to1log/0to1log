import { isAuthenticatedUser, openAuthPrompt } from './auth-prompt';
import './content-status';

function resolveRedirect(button: HTMLButtonElement): string {
  return button.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function initBookmarks(): void {
  const buttons = document.querySelectorAll<HTMLButtonElement>('.newsprint-bookmark-icon');

  buttons.forEach((btn) => {
    // Prevent duplicate listeners on ViewTransition re-runs
    if (btn.dataset.bookmarkInit === 'true') return;
    btn.dataset.bookmarkInit = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (btn.dataset.previewMode === 'true') return;

      const itemId = btn.dataset.itemId;
      const itemType = btn.dataset.itemType;
      if (!itemId || !itemType) return;

      if (!isAuthenticatedUser()) {
        openAuthPrompt({ action: 'bookmark', redirectTo: resolveRedirect(btn) });
        return;
      }

      try {
        const res = await fetch('/api/user/bookmarks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_type: itemType, item_id: itemId }),
        });

        if (res.status === 401) {
          openAuthPrompt({ action: 'bookmark', redirectTo: resolveRedirect(btn) });
          return;
        }

        if (!res.ok) return;

        const data = await res.json();
        const isBookmarked = data.bookmarked;
        btn.dataset.bookmarked = isBookmarked ? 'true' : 'false';
        btn.classList.toggle('newsprint-bookmark-icon--active', isBookmarked);
        btn.setAttribute('aria-label', isBookmarked ? 'Remove bookmark' : 'Add bookmark');

        const svg = btn.querySelector('svg');
        if (svg) {
          svg.setAttribute('fill', isBookmarked ? 'currentColor' : 'none');
        }

        // Bookmark pop + particle effect on save
        if (isBookmarked && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
          btn.classList.add('bookmark-fill-active');
          btn.addEventListener('animationend', () => btn.classList.remove('bookmark-fill-active'), { once: true });
          const rect = btn.getBoundingClientRect();
          btn.style.position = 'relative';
          for (let i = 0; i < 4; i++) {
            const p = document.createElement('span');
            p.className = 'bookmark-particle';
            p.style.setProperty('--px', (Math.random() * 24 - 12) + 'px');
            p.style.setProperty('--py', -(Math.random() * 18 + 6) + 'px');
            p.style.left = (rect.width / 2 - 2.5) + 'px';
            p.style.top = (rect.height / 2 - 2.5) + 'px';
            btn.appendChild(p);
            p.addEventListener('animationend', () => p.remove());
          }
        }
      } catch {
        // Silently fail on network errors
      }
    });
  });
}

document.addEventListener('astro:page-load', () => {
  initBookmarks();
});
window.addEventListener('content-status:refresh', initBookmarks);
