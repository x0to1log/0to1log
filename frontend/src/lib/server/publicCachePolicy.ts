export type PublicCacheKind = 'list' | 'detail';

export interface PublicCacheInput {
  kind: PublicCacheKind;
  authenticated: boolean;
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

export function resolvePublicCachePolicy(input: PublicCacheInput): PublicCacheHeaders {
  if (input.hasError) {
    return { cacheControl: 'no-store', vercelCacheControl: 'no-store' };
  }

  if (input.authenticated || input.preview) {
    return {
      cacheControl: 'private, no-store',
      vercelCacheControl: 'private, no-store',
    };
  }

  return {
    cacheControl: 'public, max-age=0, must-revalidate',
    vercelCacheControl: input.kind === 'detail' ? DETAIL_CDN_POLICY : LIST_CDN_POLICY,
    vary: 'Cookie',
  };
}

export function getPublicContentCacheKind(pathname: string): PublicCacheKind | null {
  if (!/^\/(?:en|ko)(?:\/|$)/.test(pathname)) return null;

  const isDetail = /^\/(?:en|ko)\/(?:news|handbook|products|blog)\/(?!category(?:\/|$))[^/]+\/?$/.test(pathname);
  return isDetail ? 'detail' : 'list';
}

export function applyPublicCachePolicy(response: Response, input: PublicCacheInput): Response {
  const policy = resolvePublicCachePolicy(input);
  response.headers.set('Cache-Control', policy.cacheControl);
  response.headers.set('Vercel-CDN-Cache-Control', policy.vercelCacheControl);

  if (policy.vary) {
    const existing = response.headers.get('Vary');
    const values = new Set(
      `${existing || ''},${policy.vary}`
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean),
    );
    response.headers.set('Vary', Array.from(values).join(', '));
  }

  return response;
}
