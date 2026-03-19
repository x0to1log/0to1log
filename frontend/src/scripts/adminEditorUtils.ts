// ─── HTML escape ─────────────────────────────────────────────────────────────

export function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML.replace(/"/g, '&quot;');
}

// ─── Feedback toast ───────────────────────────────────────────────────────────
// Requires: <div id="admin-feedback" class="admin-feedback admin-feedback--toast" hidden></div>

let _feedbackTimer = 0;

export function showFeedback(message: string, isError = false): void {
  const el = document.getElementById('admin-feedback');
  if (!el) return;
  el.textContent = message;
  el.className = `admin-feedback admin-feedback--toast admin-feedback--${isError ? 'error' : 'success'}`;
  el.setAttribute('role', isError ? 'alert' : 'status');
  el.setAttribute('aria-live', isError ? 'assertive' : 'polite');
  el.setAttribute('aria-atomic', 'true');
  el.hidden = false;
  clearTimeout(_feedbackTimer);
  _feedbackTimer = window.setTimeout(() => { el.hidden = true; }, 3000);
}

// ─── Button manager ───────────────────────────────────────────────────────────
// Usage:
//   const btnManager = createButtonManager([btnSave, btnPreview, ...].filter(Boolean));
//   btnManager.begin(btnSave, 'Saving...');
//   btnManager.restore();

export function createButtonManager(buttons: HTMLButtonElement[]) {
  const _defaultLabels = new Map<HTMLButtonElement, string>();
  buttons.forEach((b) => _defaultLabels.set(b, b.textContent || ''));
  let _isPending = false;

  function setLabel(btn: HTMLButtonElement | null, label: string): void {
    if (!btn) return;
    if (label.includes('...') || label.includes('…')) {
      btn.innerHTML = `<span class="btn-spinner"></span>${label}`;
    } else {
      btn.textContent = label;
    }
  }

  function begin(btn: HTMLButtonElement | null, label: string): void {
    buttons.forEach((b) => {
      b.disabled = true;
      b.textContent = _defaultLabels.get(b) || b.textContent || '';
    });
    setLabel(btn, label);
    _isPending = true;
  }

  function restore(): void {
    buttons.forEach((b) => {
      b.disabled = false;
      b.textContent = _defaultLabels.get(b) || b.textContent || '';
    });
    _isPending = false;
  }

  return { begin, restore, setLabel, get isPending() { return _isPending; } };
}
