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
    'home.subtitle': 'From Void to Value',
    'log.title': 'Log',
    'log.empty': 'No posts yet. Check back soon!',
    'log.error': 'The press encountered a difficulty. Please try again shortly.',
    'post.back': 'Back to Log',
    'post.notfound': 'This article could not be found in our archives.',
    'error.retry': 'Return to front page',
    'nav.handbook': 'Handbook',
    'handbook.title': 'Tech Handbook',
    'handbook.subtitle': 'CS · AI · Infra',
    'handbook.empty': 'No terms yet.',
    'handbook.error': 'Failed to load terms. Please try again shortly.',
    'handbook.back': 'Back to Handbook',
    'handbook.notfound': 'Term not found.',
    'handbook.allCategories': 'All',
    'handbook.search': 'Search terms...',
    'handbook.searchNoResults': 'No matching terms found.',
    'handbook.relatedArticles': 'Related Articles',
    'handbook.relatedTerms': 'Related Terms',
    'handbook.translationPending': 'Translation in progress',
  },
  ko: {
    'nav.log': '로그',
    'nav.portfolio': '포트폴리오',
    'home.title': 'AI 뉴스 & 인사이트',
    'home.subtitle': '가치를 담는 기록',
    'log.title': '로그',
    'log.empty': '아직 포스트가 없습니다. 곧 돌아올게요!',
    'log.error': '기사를 불러오는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.',
    'post.back': '로그로 돌아가기',
    'post.notfound': '해당 기사를 보관소에서 찾을 수 없습니다.',
    'error.retry': '첫 페이지로 돌아가기',
    'nav.handbook': '핸드북',
    'handbook.title': '기술 핸드북',
    'handbook.subtitle': 'CS · AI · Infra',
    'handbook.empty': '아직 용어가 없습니다.',
    'handbook.error': '용어를 불러오는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.',
    'handbook.back': '핸드북으로 돌아가기',
    'handbook.notfound': '해당 용어를 찾을 수 없습니다.',
    'handbook.allCategories': '전체',
    'handbook.search': '용어 검색...',
    'handbook.searchNoResults': '일치하는 용어가 없습니다.',
    'handbook.relatedArticles': '관련 기사',
    'handbook.relatedTerms': '관련 개념',
    'handbook.translationPending': '번역 준비 중',
  },
};
