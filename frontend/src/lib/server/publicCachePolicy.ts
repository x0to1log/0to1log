export type PublicCacheKind = 'list' | 'detail';

export interface PublicCacheInput {
  kind: PublicCacheKind;
  preview: boolean;
  hasError: boolean;
}

export interface PublicCacheHeaders {
  cacheControl: string;
  vercelCacheControl: string;
  vary?: string;
}

const LIST_CDN_POLICY =
  'public, s-maxage=300, stale-while-revalidate=3600, stale-if-error=86400';
const DETAIL_CDN_POLICY =
  'public, s-maxage=3600, stale-while-revalidate=86400, stale-if-error=604800';

/**
 * Public /en|ko HTML is rendered user-neutral (middleware skips auth there and
 * src/scripts/session.ts hydrates per-user state), so one cached copy serves
 * everyone. Never add `Vary: Cookie`: Vercel refuses to cache such responses,
 * which disabled the CDN from 2026-08 to 2026-10 and exhausted Supabase egress.
 */
export function resolvePublicCachePolicy(input: PublicCacheInput): PublicCacheHeaders {
  if (input.hasError) {
    return { cacheControl: 'no-store', vercelCacheControl: 'no-store' };
  }

  if (input.preview) {
    return {
      cacheControl: 'private, no-store',
      vercelCacheControl: 'private, no-store',
    };
  }

  return {
    cacheControl: 'public, max-age=0, must-revalidate',
    vercelCacheControl: input.kind === 'detail' ? DETAIL_CDN_POLICY : LIST_CDN_POLICY,
  };
}

export function getPublicContentCacheKind(pathname: string): PublicCacheKind | null {
  if (!/^\/(?:en|ko)(?:\/|$)/.test(pathname)) return null;

  const isDetail = /^\/(?:en|ko)\/(?:news|handbook|products|blog)\/(?!category(?:\/|$))[^/]+\/?$/.test(pathname);
  return isDetail ? 'detail' : 'list';
}

export const PUBLIC_CACHE_SECTIONS = ['news', 'handbook', 'blog', 'products', 'home', 'pages'] as const;
export type PublicCacheSection = (typeof PUBLIC_CACHE_SECTIONS)[number];

/** Tags for Vercel-Cache-Tag; /api/revalidate invalidates them by section. */
export function getPublicCacheTags(pathname: string): string[] {
  const segment = pathname.split('/')[2] || '';
  let section: PublicCacheSection;
  if (segment === '') section = 'home';
  else if (segment === 'rss.xml') section = 'news';
  else if ((PUBLIC_CACHE_SECTIONS as readonly string[]).includes(segment)) section = segment as PublicCacheSection;
  else section = 'pages';
  return ['public', section];
}

export function applyPublicCachePolicy(
  response: Response,
  input: PublicCacheInput & { pathname: string },
): Response {
  const policy = resolvePublicCachePolicy(input);
  response.headers.set('Cache-Control', policy.cacheControl);
  response.headers.set('Vercel-CDN-Cache-Control', policy.vercelCacheControl);
  if (policy.vercelCacheControl.startsWith('public')) {
    response.headers.set('Vercel-Cache-Tag', getPublicCacheTags(input.pathname).join(','));
  }
  return response;
}
