/**
 * Client-side session hydration.
 *
 * Public /en|ko pages are CDN-cached and rendered user-neutral, so the
 * logged-in state (nav, admin controls, persona defaults) is applied here
 * after load. Only browsers carrying the non-httpOnly hint cookie call
 * /api/user/me, so anonymous visitors and crawlers cost no function call.
 */

export interface SessionInfo {
  authenticated: boolean;
  isAdmin: boolean;
  displayName: string;
  avatarUrl: string | null;
  persona: string | null;
  handbookLevel: string | null;
}

export const SESSION_HINT_COOKIE = 'sb-session-hint';
const CACHE_KEY = 'session-cache-v1';
const CACHE_TTL_MS = 2 * 60 * 1000;

const GUEST: SessionInfo = {
  authenticated: false,
  isAdmin: false,
  displayName: '',
  avatarUrl: null,
  persona: null,
  handbookLevel: null,
};

let current: SessionInfo = GUEST;

function hasHintCookie(): boolean {
  return document.cookie.split(';').some((part) => part.trim().startsWith(`${SESSION_HINT_COOKIE}=`));
}

function clearHintCookie(): void {
  document.cookie = `${SESSION_HINT_COOKIE}=; Max-Age=0; path=/`;
}

function readCache(): SessionInfo | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { at: number; session: SessionInfo };
    if (Date.now() - parsed.at > CACHE_TTL_MS) return null;
    return parsed.session;
  } catch {
    return null;
  }
}

function writeCache(session: SessionInfo): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), session }));
  } catch { /* storage unavailable */ }
}

export function clearSessionCache(): void {
  try {
    sessionStorage.removeItem(CACHE_KEY);
  } catch { /* storage unavailable */ }
}

async function resolveSession(): Promise<SessionInfo> {
  if (!hasHintCookie()) {
    clearSessionCache();
    return GUEST;
  }

  const cached = readCache();
  if (cached) return cached;

  try {
    const res = await fetch('/api/user/me', { credentials: 'same-origin' });
    if (res.status === 401) {
      clearHintCookie();
      clearSessionCache();
      return GUEST;
    }
    if (!res.ok) return GUEST;
    const session = { ...GUEST, ...(await res.json() as Partial<SessionInfo>), authenticated: true };
    writeCache(session);
    return session;
  } catch {
    return GUEST;
  }
}

function setVisible(selector: string, visible: boolean): void {
  document.querySelectorAll<HTMLElement>(selector).forEach((el) => {
    el.hidden = !visible;
  });
}

function applyAvatar(session: SessionInfo): void {
  const slot = document.querySelector<HTMLElement>('[data-auth-avatar]');
  if (!slot) return;
  slot.replaceChildren();
  if (!session.authenticated) return;
  if (session.avatarUrl) {
    const img = document.createElement('img');
    img.src = session.avatarUrl;
    img.alt = session.displayName;
    slot.append(img);
  } else {
    slot.textContent = session.displayName ? session.displayName.charAt(0).toUpperCase() : '?';
  }
}

function applySession(session: SessionInfo): void {
  const body = document.body;
  body.dataset.authenticated = session.authenticated ? 'true' : 'false';
  setVisible('[data-auth-only]', session.authenticated);
  setVisible('[data-guest-only]', !session.authenticated);
  setVisible('[data-admin-only]', session.isAdmin);
  applyAvatar(session);

  const toggle = document.querySelector<HTMLElement>('[data-user-menu-toggle]');
  const label = session.authenticated ? toggle?.dataset.labelUser : toggle?.dataset.labelGuest;
  if (toggle && label) toggle.setAttribute('aria-label', label);
}

export function getSession(): SessionInfo {
  return current;
}

/** Run `callback` once the session for the current page is known. */
export function onSessionReady(callback: (session: SessionInfo) => void): void {
  if (document.body.dataset.sessionReady === 'true') {
    callback(current);
    return;
  }
  document.addEventListener('session:ready', () => callback(current), { once: true });
}

async function hydrateSession(): Promise<void> {
  const session = await resolveSession();
  // Uncached pages rendered for a known user (library, settings) already
  // carry the right markup; never downgrade them if the hint cookie is gone.
  const ssrUser = document.body.dataset.ssrSession === 'true';
  if (session.authenticated || !ssrUser) {
    current = session;
    applySession(session);
  } else {
    current = { ...GUEST, authenticated: true };
  }
  document.body.dataset.sessionReady = 'true';
  document.dispatchEvent(new CustomEvent<SessionInfo>('session:ready', { detail: current }));
}

document.addEventListener('astro:page-load', () => void hydrateSession());
