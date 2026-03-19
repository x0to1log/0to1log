// ─── Preview Manager Factory ─────────────────────────────────────────────────
// Manages the preview iframe panel shared by all admin editors.
//
// Usage:
//   const preview = createPreviewManager({
//     editorPath: '/admin/blog/edit/',
//     getSlug: () => slugInput?.value || '',
//     buildPreviewUrl: () => previewUrl || '',
//     btnManager,
//     draftModeEl: draftMode,
//     previewModeEl: previewMode,
//     previewShell, previewLoading, previewLoadingText, previewFrame,
//   });
//   preview.frame.addEventListener('load', () => { preview.attachAutoResize(); preview.setShellLoading(false); });
//   window.addEventListener('popstate', preview.syncFromLocation);

import type { createButtonManager } from './adminEditorUtils';

export interface PreviewManagerConfig {
  editorPath: string;                         // e.g., '/admin/blog/edit/' (trailing slash)
  getSlug: () => string;
  buildPreviewUrl: () => string;
  btnManager: ReturnType<typeof createButtonManager>;
  draftModeEl: HTMLElement | null;
  previewModeEl: HTMLElement | null;
  previewShell: HTMLElement | null;
  previewLoading: HTMLElement | null;
  previewLoadingText: HTMLElement | null;
  previewFrame: HTMLIFrameElement | null;
}

export function createPreviewManager(config: PreviewManagerConfig) {
  const { editorPath, getSlug, buildPreviewUrl, btnManager } = config;
  const { draftModeEl, previewModeEl, previewShell, previewLoading, previewLoadingText, previewFrame } = config;

  let previewEnteredFromEditor = false;
  let previewResizeObserver: ResizeObserver | null = null;
  let previewWindowResizeCleanup: (() => void) | null = null;
  let announcePreviewReady = false;

  function setShellLoading(loading: boolean, message = 'Loading live preview...'): void {
    previewShell?.classList.toggle('admin-preview-frame-shell--loading', loading);
    if (previewLoading) previewLoading.hidden = !loading;
    if (previewLoadingText) previewLoadingText.textContent = message;
    if (previewFrame) previewFrame.setAttribute('aria-busy', loading ? 'true' : 'false');
  }

  function isPreviewLocation(): boolean {
    return new URL(window.location.href).searchParams.get('mode') === 'preview';
  }

  function getEditorUrl(mode: 'draft' | 'preview', slugOverride = getSlug()): string {
    const url = new URL(window.location.href);
    if (slugOverride) url.pathname = `${editorPath}${slugOverride}`;
    if (mode === 'preview') {
      url.searchParams.set('mode', 'preview');
    } else {
      url.searchParams.delete('mode');
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function disconnectResize(): void {
    previewResizeObserver?.disconnect();
    previewResizeObserver = null;
    if (previewWindowResizeCleanup) {
      previewWindowResizeCleanup();
      previewWindowResizeCleanup = null;
    }
  }

  function syncFrameHeight(): void {
    if (!previewFrame?.contentDocument) return;
    const doc = previewFrame.contentDocument;
    const body = doc.body;
    const root = doc.documentElement;
    const nextHeight = Math.max(
      body?.scrollHeight || 0,
      body?.offsetHeight || 0,
      root?.scrollHeight || 0,
      root?.offsetHeight || 0,
    );
    if (nextHeight > 0) {
      const currentHeight = parseInt(previewFrame.style.height || '0');
      if (Math.abs(nextHeight - currentHeight) > 4) {
        previewFrame.style.height = `${Math.max(nextHeight, 720)}px`;
      }
    }
  }

  function attachAutoResize(): void {
    if (!previewFrame?.contentDocument) return;
    disconnectResize();
    const doc = previewFrame.contentDocument;
    const win = previewFrame.contentWindow;
    const scheduleResize = () => window.requestAnimationFrame(() => syncFrameHeight());

    previewResizeObserver = new ResizeObserver(() => scheduleResize());
    if (doc.body) previewResizeObserver.observe(doc.body);
    if (doc.documentElement) previewResizeObserver.observe(doc.documentElement);
    doc.querySelectorAll('img').forEach((image) => {
      if (!image.complete) image.addEventListener('load', scheduleResize, { once: true });
    });
    if (win) {
      const handleResize = () => scheduleResize();
      win.addEventListener('resize', handleResize);
      previewWindowResizeCleanup = () => win.removeEventListener('resize', handleResize);
    }
    scheduleResize();
    window.setTimeout(scheduleResize, 120);
    window.setTimeout(scheduleResize, 420);
    window.setTimeout(scheduleResize, 1200);
  }

  function showPreview(pushHistory = false): void {
    if (draftModeEl) draftModeEl.style.display = 'none';
    if (previewModeEl) previewModeEl.style.display = 'block';
    if (pushHistory && !isPreviewLocation()) {
      history.pushState({ mode: 'preview' }, '', getEditorUrl('preview'));
      previewEnteredFromEditor = true;
    }
  }

  function showDraft(replaceHistory = false): void {
    if (draftModeEl) draftModeEl.style.display = '';
    if (previewModeEl) previewModeEl.style.display = 'none';
    if (replaceHistory && isPreviewLocation()) {
      history.replaceState({ mode: 'draft' }, '', getEditorUrl('draft'));
    }
    previewEnteredFromEditor = false;
    setShellLoading(false);
    btnManager.restore();
  }

  function loadFrame(previewUrl: string, options: { announce?: boolean; pushHistory?: boolean } = {}): void {
    if (!previewFrame) return;
    announcePreviewReady = options.announce === true;
    setShellLoading(true, 'Loading live preview...');
    showPreview(options.pushHistory === true);
    previewFrame.src = previewUrl;
  }

  function syncFromLocation(): void {
    if (!isPreviewLocation()) { showDraft(false); return; }
    const previewUrl = buildPreviewUrl();
    if (!previewUrl) { showDraft(true); return; }
    showPreview(false);
    if (!previewFrame?.src || previewFrame.src !== new URL(previewUrl, window.location.origin).toString()) {
      loadFrame(previewUrl, { announce: false, pushHistory: false });
    }
  }

  return {
    frame: previewFrame,
    setShellLoading,
    isPreviewLocation,
    getEditorUrl,
    attachAutoResize,
    showPreview,
    showDraft,
    loadFrame,
    syncFromLocation,
    get enteredFromEditor() { return previewEnteredFromEditor; },
    get announceReady() { return announcePreviewReady; },
    set announceReady(v: boolean) { announcePreviewReady = v; },
  };
}
