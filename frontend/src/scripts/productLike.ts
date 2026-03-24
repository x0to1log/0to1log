import { isAuthenticatedUser, openAuthPrompt } from './auth-prompt';

function resolveRedirect(button: HTMLButtonElement): string {
  return button.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

// ── Detail page heart button ────────────────────────────────────────────────

function applyLikeState(btn: HTMLButtonElement, liked: boolean, likeCount?: number): void {
  btn.dataset.liked = liked ? 'true' : 'false';
  btn.classList.toggle('product-like-btn--active', liked);

  const svg = btn.querySelector('svg');
  if (svg) svg.setAttribute('fill', liked ? 'currentColor' : 'none');

  const label = btn.querySelector<HTMLElement>('#like-label');
  if (label) {
    const locale = document.documentElement.lang || 'ko';
    label.textContent = liked
      ? (locale === 'ko' ? '찜됨' : 'Liked')
      : (locale === 'ko' ? '찜하기' : 'Like');
  }

  if (likeCount !== undefined) {
    const countEl = btn.querySelector<HTMLElement>('#like-count');
    if (countEl) countEl.textContent = likeCount.toLocaleString();
  }
}

function initProductLikeBtn(): void {
  const btn = document.querySelector<HTMLButtonElement>('#product-like-btn');
  if (!btn || btn.dataset.productLikeInit === 'true') return;
  btn.dataset.productLikeInit = 'true';

  btn.addEventListener('click', async () => {
    const productId = btn.dataset.productId;
    if (!productId) return;

    if (!isAuthenticatedUser()) {
      openAuthPrompt({ action: 'product_like', redirectTo: resolveRedirect(btn) });
      return;
    }

    const wasLiked = btn.dataset.liked === 'true';

    // Optimistic update
    applyLikeState(btn, !wasLiked);
    btn.disabled = true;

    try {
      const res = await fetch('/api/user/product-likes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId }),
      });

      if (res.status === 401) {
        applyLikeState(btn, wasLiked); // rollback
        openAuthPrompt({ action: 'product_like', redirectTo: resolveRedirect(btn) });
        return;
      }

      if (!res.ok) {
        applyLikeState(btn, wasLiked); // rollback
        return;
      }

      const data = await res.json() as { liked: boolean; like_count: number };
      applyLikeState(btn, data.liked, data.like_count);
    } catch {
      applyLikeState(btn, wasLiked); // rollback on network error
    } finally {
      btn.disabled = false;
    }
  });
}

// ── Card heart buttons (batch state load) ───────────────────────────────────

async function loadCardLikeStates(): Promise<void> {
  if (!isAuthenticatedUser()) return;

  const cardBtns = document.querySelectorAll<HTMLButtonElement>('.product-card-like');
  if (cardBtns.length === 0) return;

  try {
    const res = await fetch('/api/user/product-likes');
    if (!res.ok) return;

    const data = await res.json() as { likedIds: string[] };
    const likedSet = new Set(data.likedIds);

    cardBtns.forEach((btn) => {
      const productId = btn.dataset.productId;
      if (!productId) return;
      const liked = likedSet.has(productId);
      btn.dataset.liked = liked ? 'true' : 'false';
      btn.classList.toggle('product-card-like--active', liked);
      const svg = btn.querySelector('svg');
      if (svg) svg.setAttribute('fill', liked ? 'currentColor' : 'none');
    });
  } catch {
    // Silently fail — card hearts just won't show liked state
  }
}

function initCardLikeButtons(): void {
  const cardBtns = document.querySelectorAll<HTMLButtonElement>('.product-card-like');

  cardBtns.forEach((btn) => {
    if (btn.dataset.cardLikeInit === 'true') return;
    btn.dataset.cardLikeInit = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const productId = btn.dataset.productId;
      if (!productId) return;

      if (!isAuthenticatedUser()) {
        openAuthPrompt({ action: 'product_like', redirectTo: resolveRedirect(btn) });
        return;
      }

      const wasLiked = btn.dataset.liked === 'true';

      // Optimistic update
      btn.dataset.liked = (!wasLiked) ? 'true' : 'false';
      btn.classList.toggle('product-card-like--active', !wasLiked);
      const svgOpt = btn.querySelector('svg');
      if (svgOpt) svgOpt.setAttribute('fill', !wasLiked ? 'currentColor' : 'none');
      btn.disabled = true;

      try {
        const res = await fetch('/api/user/product-likes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: productId }),
        });

        if (res.status === 401) {
          // rollback
          btn.dataset.liked = wasLiked ? 'true' : 'false';
          btn.classList.toggle('product-card-like--active', wasLiked);
          if (svgOpt) svgOpt.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
          openAuthPrompt({ action: 'product_like', redirectTo: resolveRedirect(btn) });
          return;
        }

        if (!res.ok) {
          // rollback
          btn.dataset.liked = wasLiked ? 'true' : 'false';
          btn.classList.toggle('product-card-like--active', wasLiked);
          if (svgOpt) svgOpt.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
        } else {
          const data = await res.json() as { liked: boolean };
          btn.dataset.liked = data.liked ? 'true' : 'false';
          btn.classList.toggle('product-card-like--active', data.liked);
          if (svgOpt) svgOpt.setAttribute('fill', data.liked ? 'currentColor' : 'none');
        }
      } catch {
        // rollback
        btn.dataset.liked = wasLiked ? 'true' : 'false';
        btn.classList.toggle('product-card-like--active', wasLiked);
        if (svgOpt) svgOpt.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function init(): void {
  initProductLikeBtn();
  initCardLikeButtons();
  loadCardLikeStates();
}

document.addEventListener('astro:page-load', init);
