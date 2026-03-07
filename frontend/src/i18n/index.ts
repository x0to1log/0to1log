export type Locale = 'en' | 'ko';

export const defaultLocale: Locale = 'en';
export const locales: Locale[] = ['en', 'ko'];

export function getLocaleFromPath(path: string): Locale {
  const match = path.match(/^\/(en|ko)\//);
  return (match?.[1] as Locale) || defaultLocale;
}

export const t: Record<Locale, Record<string, string>> = {
  en: {
    'nav.log': 'Log',
    'nav.portfolio': 'Portfolio',
    'home.title': 'AI News & Insights',
    'home.subtitle': 'From Zero to One, Every Day',
    'log.title': 'Log',
    'log.empty': 'No posts yet. Check back soon!',
    'log.error': 'The press encountered a difficulty. Please try again shortly.',
    'post.back': 'Back to Log',
    'post.notfound': 'This article could not be found in our archives.',
    'error.retry': 'Return to front page',
  },
  ko: {
    'nav.log': '로그',
    'nav.portfolio': '포트폴리오',
    'home.title': 'AI 뉴스 & 인사이트',
    'home.subtitle': '매일, 제로에서 원으로',
    'log.title': '로그',
    'log.empty': '아직 포스트가 없습니다. 곧 돌아올게요!',
    'log.error': '기사를 불러오는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.',
    'post.back': '로그로 돌아가기',
    'post.notfound': '해당 기사를 보관소에서 찾을 수 없습니다.',
    'error.retry': '첫 페이지로 돌아가기',
  },
};
