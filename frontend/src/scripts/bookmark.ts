import { isAuthenticatedUser, openAuthPrompt } from './auth-prompt';

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
      } catch {
        // Silently fail on network errors
      }
    });
  });
}

async function hydrateBookmarks(): Promise<void> {
  if (!isAuthenticatedUser()) return;
  const buttons = document.querySelectorAll<HTMLButtonElement>('.newsprint-bookmark-icon');
  const checks: { btn: HTMLButtonElement; itemType: string; itemId: string }[] = [];
  buttons.forEach((btn) => {
    const itemId = btn.dataset.itemId;
    const itemType = btn.dataset.itemType;
    if (itemId && itemType) checks.push({ btn, itemType, itemId });
  });
  if (checks.length === 0) return;

  try {
    const res = await fetch('/api/user/bookmarks/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: checks.map(c => ({ item_type: c.itemType, item_id: c.itemId })) }),
    });
    if (!res.ok) return;
    const data = await res.json();
    for (const { btn, itemId } of checks) {
      const isBookmarked = data.statuses?.[itemId] ?? false;
      btn.dataset.bookmarked = isBookmarked ? 'true' : 'false';
      btn.classList.toggle('newsprint-bookmark-icon--active', isBookmarked);
      const svg = btn.querySelector('svg');
      if (svg) svg.setAttribute('fill', isBookmarked ? 'currentColor' : 'none');
    }
  } catch { /* silent */ }
}

document.addEventListener('astro:page-load', () => {
  initBookmarks();
  hydrateBookmarks();
});
