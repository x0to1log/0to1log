import { isAuthenticatedUser, openAuthPrompt } from './auth-prompt';

function resolveRedirect(button: HTMLButtonElement): string {
  return button.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function initLikes(): void {
  const btn = document.querySelector<HTMLButtonElement>('[data-like-btn]');
  if (!btn || btn.dataset.likeInit === 'true') return;
  btn.dataset.likeInit = 'true';

  btn.addEventListener('click', async () => {
    if (btn.dataset.previewMode === 'true') return;
    const postId = btn.dataset.postId;
    if (!postId) return;

    if (!isAuthenticatedUser()) {
      openAuthPrompt({ action: 'like', redirectTo: resolveRedirect(btn) });
      return;
    }

    try {
      const res = await fetch('/api/user/likes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: postId, type: btn.dataset.contentType || 'news' }),
      });

      if (res.status === 401) {
        openAuthPrompt({ action: 'like', redirectTo: resolveRedirect(btn) });
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

async function hydrateLikes(): Promise<void> {
  const btn = document.querySelector<HTMLButtonElement>('[data-like-btn]');
  if (!btn) return;
  const postId = btn.dataset.postId;
  const contentType = btn.dataset.contentType || 'news';
  if (!postId) return;

  try {
    const res = await fetch(`/api/user/likes/status?post_id=${postId}&type=${contentType}`);
    if (!res.ok) return;
    const data = await res.json();
    btn.dataset.liked = data.liked ? 'true' : 'false';
    btn.classList.toggle('newsprint-engage-btn--active', data.liked);
    const svg = btn.querySelector('svg');
    if (svg) svg.setAttribute('fill', data.liked ? 'currentColor' : 'none');
    const countEl = btn.querySelector('[data-like-count]');
    if (countEl && data.count != null) countEl.textContent = String(data.count);
  } catch { /* silent */ }
}

document.addEventListener('astro:page-load', () => {
  initLikes();
  hydrateLikes();
});
