import { isAuthenticatedUser } from './auth-prompt';

interface ContentStatusTarget {
  button: HTMLButtonElement;
  itemType: string;
  itemId: string;
  key: string;
}

interface ContentStatusResponse {
  bookmarks?: Record<string, boolean>;
  reads?: Record<string, boolean>;
}

let lastSignature = '';

function collectTargets(): ContentStatusTarget[] {
  const targets = new Map<string, ContentStatusTarget>();
  document.querySelectorAll<HTMLButtonElement>('.newsprint-bookmark-icon').forEach((button) => {
    const itemId = button.dataset.itemId;
    const itemType = button.dataset.itemType;
    if (!itemId || !itemType) return;
    const key = `${itemType}:${itemId}`;
    if (!targets.has(key)) targets.set(key, { button, itemType, itemId, key });
  });
  return [...targets.values()];
}

function applyBookmarkState(button: HTMLButtonElement, bookmarked: boolean): void {
  button.dataset.bookmarked = bookmarked ? 'true' : 'false';
  button.classList.toggle('newsprint-bookmark-icon--active', bookmarked);
  button.setAttribute('aria-label', bookmarked ? 'Remove bookmark' : 'Add bookmark');
  button.querySelector('svg')?.setAttribute('fill', bookmarked ? 'currentColor' : 'none');
}

function applyReadState(button: HTMLButtonElement, read: boolean): void {
  const card = button.closest<HTMLElement>('.newsprint-card, .handbook-card, .blog-list-item');
  if (!card) return;
  if (card.classList.contains('blog-list-item')) {
    card.classList.toggle('blog-list-item--read', read);
    return;
  }
  card.classList.toggle('newsprint-card--read', read);
}

export async function hydrateContentStatus(): Promise<void> {
  if (!isAuthenticatedUser()) return;

  const targets = collectTargets();
  if (targets.length === 0) return;
  const signature = targets.map((target) => target.key).sort().join('|');
  if (signature === lastSignature) return;
  lastSignature = signature;

  try {
    const response = await fetch('/api/user/content-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: targets.map((target) => ({ item_type: target.itemType, item_id: target.itemId })),
      }),
    });
    if (!response.ok) {
      lastSignature = '';
      return;
    }

    const data = await response.json() as ContentStatusResponse;
    for (const target of targets) {
      applyBookmarkState(target.button, data.bookmarks?.[target.key] === true);
      applyReadState(target.button, data.reads?.[target.key] === true);
    }
  } catch {
    lastSignature = '';
  }
}

function resetAndHydrate(): void {
  lastSignature = '';
  void hydrateContentStatus();
}

document.addEventListener('astro:page-load', resetAndHydrate);
window.addEventListener('content-status:refresh', () => void hydrateContentStatus());
