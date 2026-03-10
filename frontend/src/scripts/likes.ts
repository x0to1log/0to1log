function initLikes(): void {
  const btn = document.querySelector<HTMLButtonElement>('[data-like-btn]');
  if (!btn || btn.dataset.likeInit === 'true') return;
  btn.dataset.likeInit = 'true';

  btn.addEventListener('click', async () => {
    const postId = btn.dataset.postId;
    if (!postId) return;

    try {
      const res = await fetch('/api/user/likes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: postId, type: btn.dataset.contentType || 'news' }),
      });

      if (res.status === 401) {
        window.location.href = `/login?redirectTo=${encodeURIComponent(window.location.pathname)}`;
        return;
      }

      if (!res.ok) return;

      const data = await res.json();
      const liked = data.liked;

      btn.dataset.liked = liked ? 'true' : 'false';
      btn.classList.toggle('newsprint-engage-btn--active', liked);

      const svg = btn.querySelector('svg');
      if (svg) svg.setAttribute('fill', liked ? 'currentColor' : 'none');

      const countEl = btn.querySelector('[data-like-count]');
      if (countEl) countEl.textContent = String(data.count);
    } catch {
      // Silently fail
    }
  });
}

document.addEventListener('astro:page-load', initLikes);
