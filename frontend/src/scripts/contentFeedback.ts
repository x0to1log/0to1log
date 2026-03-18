import { openAuthPrompt } from './auth-prompt';

/* ── Types & Reason config ────────────────────────────── */

type SourceType = 'news' | 'handbook' | 'blog' | 'product';

interface ReasonOption {
  value: string;
  ko: string;
  en: string;
}

const REASONS: Record<SourceType, ReasonOption[]> = {
  news: [
    { value: 'inaccurate', ko: '부정확함', en: 'Inaccurate' },
    { value: 'hard_to_understand', ko: '이해하기 어려움', en: 'Hard to understand' },
    { value: 'too_shallow', ko: '깊이가 부족함', en: 'Too shallow' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  handbook: [
    { value: 'confusing', ko: '설명이 혼란스러움', en: 'Confusing explanation' },
    { value: 'lacks_examples', ko: '예시가 부족함', en: 'Lacks examples' },
    { value: 'outdated', ko: '정보가 오래됨', en: 'Outdated information' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  blog: [
    { value: 'not_helpful', ko: '도움 안 됨', en: 'Not helpful' },
    { value: 'lacks_depth', ko: '내용이 부족함', en: 'Lacks depth' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  product: [
    { value: 'inaccurate_info', ko: '정보가 부정확함', en: 'Inaccurate info' },
    { value: 'not_useful', ko: '유용하지 않음', en: 'Not useful' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
};

/* ── Helpers ───────────────────────────────────────────── */

function resolveRedirect(root: HTMLElement): string {
  return root.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

/* ── Bottom Sheet ─────────────────────────────────────── */

function createReasonSheet(
  sourceType: SourceType,
  locale: string,
  existingReason: string | null,
  existingMessage: string | null,
): HTMLElement {
  const isKo = locale === 'ko';
  const reasons = REASONS[sourceType];

  const sheet = document.createElement('div');
  sheet.className = 'feedback-sheet';
  sheet.setAttribute('role', 'dialog');
  sheet.setAttribute('aria-label', isKo ? '피드백 보내기' : 'Send feedback');

  const reasonsHtml = reasons
    .map((r) => {
      const checked = r.value === existingReason ? ' checked' : '';
      const label = isKo ? r.ko : r.en;
      return `<label class="feedback-sheet-reason"><input type="radio" name="feedback-reason" value="${r.value}"${checked} /><span>${label}</span></label>`;
    })
    .join('\n');

  sheet.innerHTML = `
    <button class="feedback-sheet-close" aria-label="${isKo ? '닫기' : 'Close'}">&times;</button>
    <h3 class="feedback-sheet-title">${isKo ? '어떤 점이 아쉬웠나요?' : 'What could be better?'}</h3>
    <div class="feedback-sheet-reasons">
      ${reasonsHtml}
    </div>
    <textarea class="feedback-sheet-textarea" placeholder="${isKo ? '추가 의견이 있다면... (선택사항)' : 'Additional comments (optional)'}" maxlength="500">${existingMessage ?? ''}</textarea>
    <button type="button" class="feedback-sheet-submit"${existingReason ? '' : ' disabled'}>${isKo ? '제출하기' : 'Submit'}</button>
  `;

  return sheet;
}

function openReasonSheet(opts: {
  sourceType: SourceType;
  sourceId: string;
  locale: string;
  existingReason: string | null;
  existingMessage: string | null;
  onSuccess: (reason: string, message: string | null) => void;
}): void {
  const { sourceType, sourceId, locale, existingReason, existingMessage, onSuccess } = opts;
  const isKo = locale === 'ko';

  // backdrop
  const backdrop = document.createElement('div');
  backdrop.className = 'feedback-sheet-backdrop';
  document.body.appendChild(backdrop);

  // sheet
  const sheet = createReasonSheet(sourceType, locale, existingReason, existingMessage);
  document.body.appendChild(sheet);

  let selectedReason: string | null = existingReason;

  // reason radio change
  sheet.querySelectorAll<HTMLInputElement>('input[name="feedback-reason"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      selectedReason = radio.value;
      (sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement).disabled = false;
    });
  });

  // submit
  sheet.querySelector('.feedback-sheet-submit')?.addEventListener('click', async () => {
    if (!selectedReason) return;
    const submitBtn = sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement;
    const textarea = sheet.querySelector('.feedback-sheet-textarea') as HTMLTextAreaElement;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="btn-spinner"></span>${isKo ? '제출 중...' : 'Submitting...'}`;

    try {
      const messageValue = textarea.value.trim() || null;
      const res = await fetch('/api/user/content-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: sourceType,
          source_id: sourceId,
          locale,
          reaction: 'negative',
          reason: selectedReason,
          message: messageValue,
        }),
      });

      if (!res.ok) {
        submitBtn.disabled = false;
        submitBtn.textContent = isKo ? '제출하기' : 'Submit';
        return;
      }

      // success UI
      const title = sheet.querySelector('.feedback-sheet-title');
      const reasons = sheet.querySelector('.feedback-sheet-reasons');
      const ta = sheet.querySelector('.feedback-sheet-textarea');
      title?.remove();
      reasons?.remove();
      ta?.remove();
      submitBtn.remove();

      const success = document.createElement('div');
      success.className = 'feedback-sheet-success';
      success.textContent = isKo ? '감사합니다! 피드백이 전달되었습니다.' : 'Thank you! Your feedback has been sent.';
      sheet.querySelector('.feedback-sheet-close')!.after(success);

      onSuccess(selectedReason, messageValue);
      setTimeout(() => close(), 1500);
    } catch {
      submitBtn.disabled = false;
      submitBtn.textContent = isKo ? '제출하기' : 'Submit';
    }
  });

  // close helpers
  function close() {
    backdrop.classList.remove('feedback-sheet-backdrop--open');
    sheet.classList.remove('feedback-sheet--open');
    setTimeout(() => {
      backdrop.remove();
      sheet.remove();
    }, 250);
  }
  backdrop.addEventListener('click', close);
  sheet.querySelector('.feedback-sheet-close')?.addEventListener('click', close);
  document.addEventListener('keydown', function esc(e) {
    if (e.key === 'Escape') {
      close();
      document.removeEventListener('keydown', esc);
    }
  });

  // open animation
  requestAnimationFrame(() => {
    backdrop.classList.add('feedback-sheet-backdrop--open');
    sheet.classList.add('feedback-sheet--open');
  });
}

/* ── Main init ────────────────────────────────────────── */

function initContentFeedback(): void {
  document.querySelectorAll<HTMLElement>('[data-content-feedback]').forEach((root) => {
    if (root.dataset.feedbackInit === 'true') return;
    root.dataset.feedbackInit = 'true';

    const sourceType = root.dataset.sourceType as SourceType | undefined;
    const sourceId = root.dataset.sourceId;
    const locale = root.dataset.locale;
    const isAuthenticated = root.dataset.authenticated === 'true';
    const previewMode = root.dataset.previewMode === 'true';
    const thanksMessage = root.dataset.thanks || 'Thanks for the feedback.';
    const errorMessage = root.dataset.error || 'Failed to save feedback.';
    const status = root.querySelector<HTMLElement>('[data-feedback-status]');
    const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-reaction]'));

    if (!sourceType || !sourceId || !locale || buttons.length === 0) return;

    let currentReaction: string | null = null;
    let currentReason: string | null = null;
    let currentMessage: string | null = null;

    const setSelectedReaction = (selectedReaction: string | null) => {
      currentReaction = selectedReaction;
      buttons.forEach((button) => {
        const isSelected = button.dataset.reaction === selectedReaction;
        button.classList.toggle('is-selected', isSelected);
        button.ariaPressed = isSelected ? 'true' : 'false';
      });
    };

    const setStatus = (message: string) => {
      if (status) {
        status.textContent = message;
        status.hidden = !message;
      }
    };

    const loadExistingFeedback = async () => {
      if (!isAuthenticated) return;
      try {
        const params = new URLSearchParams({
          source_type: sourceType,
          source_id: sourceId,
          locale,
        });
        const response = await fetch(`/api/user/content-feedback?${params.toString()}`);
        if (!response.ok) return;
        const data = await response.json();
        setSelectedReaction(data.reaction ?? null);
        currentReason = data.reason ?? null;
        currentMessage = data.message ?? null;
      } catch {
        // silent — progressive enhancement
      }
    };

    buttons.forEach((button) => {
      button.addEventListener('click', async () => {
        const reaction = button.dataset.reaction;
        if (!reaction || previewMode) return;

        if (!isAuthenticated) {
          openAuthPrompt({ action: 'feedback', redirectTo: resolveRedirect(root) });
          return;
        }

        // "negative" → open bottom sheet with reason radios
        if (reaction === 'negative') {
          openReasonSheet({
            sourceType,
            sourceId,
            locale,
            existingReason: currentReason,
            existingMessage: currentMessage,
            onSuccess: (reason, message) => {
              currentReason = reason;
              currentMessage = message;
              setSelectedReaction('negative');
              setStatus(thanksMessage);
            },
          });
          return;
        }

        // "positive" → immediate POST
        button.disabled = true;
        setStatus('');

        try {
          const response = await fetch('/api/user/content-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              source_type: sourceType,
              source_id: sourceId,
              locale,
              reaction: 'positive',
            }),
          });

          if (response.status === 401) {
            openAuthPrompt({ action: 'feedback', redirectTo: resolveRedirect(root) });
            return;
          }

          if (!response.ok) {
            setStatus(errorMessage);
            return;
          }

          setSelectedReaction('positive');
          setStatus(thanksMessage);
        } catch {
          setStatus(errorMessage);
        } finally {
          button.disabled = false;
        }
      });
    });

    void loadExistingFeedback();
  });
}

document.addEventListener('astro:page-load', initContentFeedback);
