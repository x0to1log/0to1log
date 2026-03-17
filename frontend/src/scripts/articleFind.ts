function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function clearHighlights(root: HTMLElement): void {
  const marks = Array.from(root.querySelectorAll<HTMLElement>('mark[data-article-find-hit="true"]'));
  marks.forEach((mark) => {
    const text = document.createTextNode(mark.textContent || '');
    mark.replaceWith(text);
    text.parentElement?.normalize();
  });
}

function collectTextNodes(root: HTMLElement): Text[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || !node.textContent?.trim()) {
        return NodeFilter.FILTER_REJECT;
      }
      if (parent.closest('mark[data-article-find-hit="true"]')) {
        return NodeFilter.FILTER_REJECT;
      }
      if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName)) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const nodes: Text[] = [];
  let current = walker.nextNode();
  while (current) {
    nodes.push(current as Text);
    current = walker.nextNode();
  }
  return nodes;
}

function highlightText(root: HTMLElement, query: string): number {
  clearHighlights(root);

  if (!query) {
    return 0;
  }

  const escaped = escapeRegExp(query);
  const nodes = collectTextNodes(root);
  let totalMatches = 0;

  nodes.forEach((node) => {
    const text = node.textContent || '';
    const regex = new RegExp(escaped, 'gi');
    const matches = Array.from(text.matchAll(regex));

    if (matches.length === 0) {
      return;
    }

    totalMatches += matches.length;

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;

    matches.forEach((match) => {
      const start = match.index ?? 0;
      const matchText = match[0];

      if (start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)));
      }

      const mark = document.createElement('mark');
      mark.dataset.articleFindHit = 'true';
      mark.className = 'newsprint-article-find-hit';
      mark.textContent = matchText;
      fragment.appendChild(mark);

      lastIndex = start + matchText.length;
    });

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    node.parentNode?.replaceChild(fragment, node);
  });

  return totalMatches;
}

function initArticleFind(): void {
  const root = document.querySelector<HTMLElement>('[data-article-find-root]');
  const input = document.getElementById('article-find') as HTMLInputElement | null;
  const countEl = document.querySelector<HTMLElement>('[data-article-find-count]');

  if (!root || !input || !countEl || root.dataset.articleFindReady === 'true') {
    return;
  }

  root.dataset.articleFindReady = 'true';

  function syncQuery(query: string): void {
    const url = new URL(window.location.href);
    if (query) {
      url.searchParams.set('q', query);
    } else {
      url.searchParams.delete('q');
    }
    history.replaceState(null, '', url.toString());
  }

  function updateCount(query: string, matches: number): void {
    if (!query) {
      countEl.textContent = '';
      return;
    }

    if (matches === 0) {
      countEl.textContent = countEl.dataset.emptyLabel || '';
      return;
    }

    const label = matches === 1 ? countEl.dataset.resultLabel : countEl.dataset.resultsLabel;
    countEl.textContent = `${matches} ${label || ''}`.trim();
  }

  function applyFind(options?: { syncUrl?: boolean; scroll?: boolean }): void {
    const query = input.value.trim();
    const matches = highlightText(root, query);

    updateCount(query, matches);

    if (options?.syncUrl) {
      syncQuery(query);
    }

    if (options?.scroll && query && matches > 0) {
      root
        .querySelector<HTMLElement>('mark[data-article-find-hit="true"]')
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => applyFind({ syncUrl: true, scroll: true }), 200);
  });

  document.addEventListener('newsprint:article-content-updated', () => {
    applyFind({ syncUrl: false, scroll: false });
  });

  if (input.value.trim()) {
    requestAnimationFrame(() => applyFind({ syncUrl: false, scroll: true }));
  }
}

document.addEventListener('astro:page-load', initArticleFind);
initArticleFind();
