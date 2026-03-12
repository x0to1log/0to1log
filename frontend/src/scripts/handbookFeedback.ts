import { openAuthPrompt } from './auth-prompt';

function resolveRedirect(root: HTMLElement): string {
  return root.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function initHandbookFeedback(): void {
  const root = document.querySelector<HTMLElement>('[data-handbook-feedback]');
  if (!root || root.dataset.feedbackInit === 'true') return;
  root.dataset.feedbackInit = 'true';

  const termId = root.dataset.termId;
  const locale = root.dataset.locale;
  const isAuthenticated = root.dataset.authenticated === 'true';
  const previewMode = root.dataset.previewMode === 'true';
  const helpfulMessage = root.dataset.thanksHelpful || 'Thanks for the feedback.';
  const confusingMessage = root.dataset.thanksConfusing || 'Thanks for the feedback.';
  const errorMessage = root.dataset.error || 'Failed to save feedback.';
  const status = root.querySelector<HTMLElement>('[data-feedback-status]');
  const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-reaction]'));

  if (!termId || !locale || buttons.length === 0) return;

  const setSelectedReaction = (selectedReaction: string | null) => {
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

  const loadExistingReaction = async () => {
    if (!isAuthenticated) return;
    try {
      const response = await fetch(`/api/user/term-feedback?term_id=${encodeURIComponent(termId)}&locale=${encodeURIComponent(locale)}`);
      if (!response.ok) return;
      const data = await response.json();
      setSelectedReaction(data.reaction ?? null);
    } catch {
      // keep silent; feedback is a progressive enhancement
    }
  };

  buttons.forEach((button) => {
    button.addEventListener('click', async () => {
      const reaction = button.dataset.reaction;
      if (!reaction) return;
      if (previewMode) return;

      if (!isAuthenticated) {
        openAuthPrompt({ action: 'feedback', redirectTo: resolveRedirect(root) });
        return;
      }

      button.disabled = true;
      setStatus('');

      try {
        const response = await fetch('/api/user/term-feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            term_id: termId,
            locale,
            reaction,
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

        setSelectedReaction(reaction);
        setStatus(reaction === 'helpful' ? helpfulMessage : confusingMessage);
      } catch {
        setStatus(errorMessage);
      } finally {
        button.disabled = false;
      }
    });
  });

  void loadExistingReaction();
}

document.addEventListener('astro:page-load', initHandbookFeedback);
