const TYPE_DELAY_MS = 90;
const DELETE_DELAY_MS = 55;
const HOLD_DELAY_MS = 1200;
const NEXT_DELAY_MS = 320;
const START_DELAY_MS = 220;
const MOBILE_RESUME_DELAY_MS = 260;

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function prefersCoarsePointer(): boolean {
  return window.matchMedia('(pointer: coarse)').matches;
}

function parseHints(value: string | undefined): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : [];
  } catch {
    return [];
  }
}

function attachAnimatedPlaceholder(input: HTMLInputElement): void {
  const hints = parseHints(input.dataset.placeholderHints);
  const fallback = input.getAttribute('placeholder') || '';
  if (prefersReducedMotion() || hints.length === 0) {
    input.placeholder = fallback;
    return;
  }

  let hintIndex = 0;
  let charIndex = 0;
  let deleting = false;
  let timer: number | null = null;
  const resumeDelayMs = prefersCoarsePointer() ? MOBILE_RESUME_DELAY_MS : 0;

  function clearTimer(): void {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function shouldAnimate(): boolean {
    return document.activeElement !== input && input.value.trim() === '';
  }

  function step(): void {
    if (!shouldAnimate()) {
      clearTimer();
      return;
    }

    const currentHint = hints[hintIndex] || fallback;
    if (!deleting) {
      charIndex += 1;
      input.placeholder = currentHint.slice(0, charIndex);

      if (charIndex >= currentHint.length) {
        deleting = true;
        timer = window.setTimeout(step, HOLD_DELAY_MS);
        return;
      }

      timer = window.setTimeout(step, TYPE_DELAY_MS);
      return;
    }

    charIndex -= 1;
    input.placeholder = currentHint.slice(0, Math.max(charIndex, 0));

    if (charIndex <= 0) {
      deleting = false;
      hintIndex = (hintIndex + 1) % hints.length;
      timer = window.setTimeout(step, NEXT_DELAY_MS);
      return;
    }

    timer = window.setTimeout(step, DELETE_DELAY_MS);
  }

  function stopAnimation(): void {
    clearTimer();
    input.placeholder = fallback;
  }

  function startAnimation(): void {
    clearTimer();
    if (!shouldAnimate()) return;
    charIndex = 0;
    deleting = false;
    input.placeholder = '';
    timer = window.setTimeout(step, START_DELAY_MS);
  }

  function scheduleResume(): void {
    clearTimer();
    if (!shouldAnimate()) return;
    if (resumeDelayMs === 0) {
      startAnimation();
      return;
    }
    input.placeholder = fallback;
    timer = window.setTimeout(startAnimation, resumeDelayMs);
  }

  input.addEventListener('pointerdown', stopAnimation);
  input.addEventListener('touchstart', stopAnimation, { passive: true });
  input.addEventListener('focus', stopAnimation);
  input.addEventListener('input', () => {
    if (input.value.trim() !== '') {
      stopAnimation();
    }
  });
  input.addEventListener('blur', () => {
    if (input.value.trim() === '') {
      scheduleResume();
    }
  });

  startAnimation();
}

function initHandbookSearchHints(): void {
  document.querySelectorAll<HTMLInputElement>('[data-placeholder-hints]').forEach((input) => {
    if (input.dataset.hintsInitialized === 'true') return;
    input.dataset.hintsInitialized = 'true';
    attachAnimatedPlaceholder(input);
  });
}

document.addEventListener('astro:page-load', initHandbookSearchHints);
initHandbookSearchHints();
