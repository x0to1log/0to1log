function initBookmarks(): void {
  const buttons = document.querySelectorAll<HTMLButtonElement>('.newsprint-bookmark-icon');

  buttons.forEach((btn) => {
    // Prevent duplicate listeners on ViewTransition re-runs
    if (btn.dataset.bookmarkInit === 'true') return;
    btn.dataset.bookmarkInit = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const itemId = btn.dataset.itemId;
      const itemType = btn.dataset.itemType;
      if (!itemId || !itemType) return;

      try {
        const res = await fetch('/api/user/bookmarks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_type: itemType, item_id: itemId }),
        });

        if (res.status === 401) {
          window.location.href = `/login?redirectTo=${encodeURIComponent(window.location.pathname)}`;
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

document.addEventListener('astro:page-load', initBookmarks);
