function initShare(): void {
  const bars = document.querySelectorAll<HTMLElement>('.newsprint-share-bar');
  bars.forEach((bar) => {
    if (bar.dataset.shareInit === 'true') return;
    bar.dataset.shareInit = 'true';

    const url = bar.dataset.shareUrl || window.location.href;
    const title = bar.dataset.shareTitle || document.title;

    // Web Share API button (visible only when supported)
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

    // X (Twitter)
    const xBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--x');
    xBtn?.addEventListener('click', () => {
      window.open(
        `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
    });

    // LinkedIn
    const liBtn = bar.querySelector<HTMLButtonElement>('.newsprint-share-btn--linkedin');
    liBtn?.addEventListener('click', () => {
      window.open(
        `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
        '_blank',
        'noopener,width=550,height=420',
      );
    });

    // Copy URL
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
