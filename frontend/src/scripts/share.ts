function initShare(): void {
  // New dropdown share pattern
  const wrappers = document.querySelectorAll<HTMLElement>('.newsprint-share-wrapper');
  wrappers.forEach((wrapper) => {
    if (wrapper.dataset.shareInit === 'true') return;
    wrapper.dataset.shareInit = 'true';

    const toggleBtn = wrapper.querySelector<HTMLButtonElement>('[data-share-toggle]');
    const dropdown = wrapper.querySelector<HTMLElement>('.newsprint-share-dropdown');
    if (!toggleBtn || !dropdown) return;

    const url = dropdown.dataset.shareUrl || window.location.href;
    const title = dropdown.dataset.shareTitle || document.title;

    // Mobile: use native share API directly, skip dropdown
    const isMobile = window.matchMedia('(max-width: 767px)').matches;

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (isMobile && navigator.share) {
        navigator.share({ title, url }).catch(() => {});
        return;
      }
      const isOpen = dropdown.style.display !== 'none';
      dropdown.style.display = isOpen ? 'none' : '';
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!wrapper.contains(e.target as Node)) {
        dropdown.style.display = 'none';
      }
    });

    // Native share
    const nativeBtn = dropdown.querySelector<HTMLButtonElement>('[data-share-native]');
    if (nativeBtn) {
      if (navigator.share) {
        nativeBtn.style.display = '';
        nativeBtn.addEventListener('click', () => {
          navigator.share({ title, url }).catch(() => {});
          dropdown.style.display = 'none';
        });
      } else {
        nativeBtn.style.display = 'none';
      }
    }

    // X (Twitter)
    const xBtn = dropdown.querySelector<HTMLButtonElement>('[data-share-x]');
    xBtn?.addEventListener('click', () => {
      window.open(
        `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
      dropdown.style.display = 'none';
    });

    // LinkedIn
    const liBtn = dropdown.querySelector<HTMLButtonElement>('[data-share-linkedin]');
    liBtn?.addEventListener('click', () => {
      window.open(
        `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
      dropdown.style.display = 'none';
    });

    // Copy URL
    const copyBtn = dropdown.querySelector<HTMLButtonElement>('[data-share-copy]');
    const toast = dropdown.querySelector<HTMLElement>('.newsprint-share-toast');
    copyBtn?.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(url);
        if (toast) {
          toast.classList.add('visible');
          setTimeout(() => toast.classList.remove('visible'), 2000);
        }
      } catch {
        /* clipboard not available */
      }
      dropdown.style.display = 'none';
    });
  });

  // Legacy: keep old share bar working if present elsewhere
  const bars = document.querySelectorAll<HTMLElement>('.newsprint-share-bar');
  bars.forEach((bar) => {
    if (bar.dataset.shareInit === 'true') return;
    bar.dataset.shareInit = 'true';

    const url = bar.dataset.shareUrl || window.location.href;
    const title = bar.dataset.shareTitle || document.title;

    const nativeBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--native');
    if (nativeBtn) {
      if (navigator.share) {
        nativeBtn.style.display = 'inline-flex';
        nativeBtn.addEventListener('click', () => {
          navigator.share({ title, url }).catch(() => {});
        });
      } else {
        nativeBtn.style.display = 'none';
      }
    }

    const xBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--x');
    xBtn?.addEventListener('click', () => {
      window.open(
        `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
    });

    const liBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--linkedin');
    liBtn?.addEventListener('click', () => {
      window.open(
        `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
    });

    const copyBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--copy');
    const toast = bar.querySelector<HTMLElement>('.newsprint-share-toast');
    copyBtn?.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(url);
        if (toast) {
          toast.classList.add('visible');
          setTimeout(() => toast.classList.remove('visible'), 2000);
        }
      } catch {
        /* clipboard not available */
      }
    });
  });
}

document.addEventListener('astro:page-load', initShare);
