import { initOAuthButtons } from './auth-oauth';

type AuthAction = 'library' | 'bookmark' | 'like' | 'feedback' | 'comment';

interface AuthPromptDetail {
  action?: AuthAction;
  redirectTo?: string;
  title?: string;
  body?: string;
}

interface PromptCopyMap {
  fallback: { title: string; body: string };
  actions: Record<AuthAction, { title: string; body: string }>;
}

function getPromptRoot(): HTMLElement | null {
  return document.querySelector<HTMLElement>('[data-auth-prompt]');
}

function readPromptCopy(): PromptCopyMap | null {
  const copyEl = document.getElementById('auth-prompt-copy');
  if (!copyEl?.textContent) return null;

  try {
    return JSON.parse(copyEl.textContent) as PromptCopyMap;
  } catch {
    return null;
  }
}

function resolveDefaultRedirect(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

export function isAuthenticatedUser(): boolean {
  return document.body.dataset.authenticated === 'true';
}

export function openAuthPrompt(detail: AuthPromptDetail = {}): void {
  window.dispatchEvent(new CustomEvent<AuthPromptDetail>('auth-prompt:open', { detail }));
}

export function openAuthPromptFromElement(element: HTMLElement): void {
  openAuthPrompt({
    action: (element.dataset.authAction as AuthAction | undefined) || undefined,
    redirectTo: element.dataset.authRedirect || resolveDefaultRedirect(),
    title: element.dataset.authTitle,
    body: element.dataset.authBody,
  });
}

function closeAuthPrompt(): void {
  const root = getPromptRoot();
  if (!root) return;

  root.hidden = true;
  root.setAttribute('aria-hidden', 'true');
  root.dataset.open = 'false';
  document.body.classList.remove('auth-prompt-open');
}

function renderPrompt(detail: AuthPromptDetail): void {
  const root = getPromptRoot();
  const copy = readPromptCopy();
  if (!root || !copy) return;

  const titleEl = root.querySelector<HTMLElement>('[data-auth-prompt-title]');
  const bodyEl = root.querySelector<HTMLElement>('[data-auth-prompt-body]');
  const oauthRoot = root.querySelector<HTMLElement>('[data-oauth-root]');
  const action = detail.action && copy.actions[detail.action] ? detail.action : undefined;
  const actionCopy = action ? copy.actions[action] : copy.fallback;

  if (titleEl) titleEl.textContent = detail.title || actionCopy.title;
  if (bodyEl) bodyEl.textContent = detail.body || actionCopy.body;
  if (oauthRoot) oauthRoot.dataset.redirectTo = detail.redirectTo || resolveDefaultRedirect();

  root.hidden = false;
  root.setAttribute('aria-hidden', 'false');
  root.dataset.open = 'true';
  document.body.classList.add('auth-prompt-open');

  window.requestAnimationFrame(() => {
    const firstButton = root.querySelector<HTMLButtonElement>('[data-provider]');
    firstButton?.focus();
  });
}

function initAuthPrompt(): void {
  const root = getPromptRoot();
  if (!root || root.dataset.authPromptInit === 'true') return;
  root.dataset.authPromptInit = 'true';

  initOAuthButtons(root);

  window.addEventListener('auth-prompt:open', (event) => {
    const customEvent = event as CustomEvent<AuthPromptDetail>;
    renderPrompt(customEvent.detail || {});
  });

  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;

    const trigger = target.closest<HTMLElement>('[data-auth-gate]');
    if (trigger) {
      event.preventDefault();
      openAuthPromptFromElement(trigger);
      return;
    }

    const closeTarget = target.closest<HTMLElement>('[data-auth-prompt-close]');
    if (closeTarget) {
      event.preventDefault();
      closeAuthPrompt();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && root.dataset.open === 'true') {
      closeAuthPrompt();
    }
  });
}

document.addEventListener('DOMContentLoaded', initAuthPrompt);
document.addEventListener('astro:page-load', initAuthPrompt);
