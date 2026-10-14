import type { AstroCookies } from 'astro';

/**
 * Readable (non-httpOnly) marker that a session cookie exists.
 * It carries no credential; it only tells client code whether calling
 * /api/user/me is worthwhile, so anonymous page views stay function-free.
 */
export const SESSION_HINT_COOKIE = 'sb-session-hint';

const HINT_MAX_AGE = 604800; // matches the refresh-token cookie

export function setSessionHint(cookies: AstroCookies, secure: boolean): void {
  cookies.set(SESSION_HINT_COOKIE, '1', {
    path: '/',
    httpOnly: false,
    secure,
    sameSite: 'lax',
    maxAge: HINT_MAX_AGE,
  });
}

/** Set the hint only when missing, so steady-state responses carry no Set-Cookie. */
export function ensureSessionHint(cookies: AstroCookies, secure: boolean): void {
  if (!cookies.get(SESSION_HINT_COOKIE)?.value) setSessionHint(cookies, secure);
}

export function clearSessionHint(cookies: AstroCookies): void {
  cookies.delete(SESSION_HINT_COOKIE, { path: '/' });
}
