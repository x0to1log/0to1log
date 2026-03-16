import type { Locale } from '../i18n/index';

export type HandbookCategorySlug =
  | 'ai-ml'
  | 'db-data'
  | 'backend'
  | 'frontend-ux'
  | 'network'
  | 'security'
  | 'os-core'
  | 'devops'
  | 'performance'
  | 'web3'
  | 'ai-business';

const HANDBOOK_CATEGORY_LABELS: Record<HandbookCategorySlug, Record<Locale, string>> = {
  web3: {
    en: 'Decentralization / Web3',
    ko: '탈중앙화 / Web3',
  },
  'ai-ml': {
    en: 'AI/ML & Algorithms',
    ko: 'AI/ML & 알고리즘',
  },
  performance: {
    en: 'Performance / Cost Management',
    ko: '성능 / 비용 관리',
  },
  devops: {
    en: 'DevOps / Operations',
    ko: 'DevOps / 운영',
  },
  'frontend-ux': {
    en: 'Frontend & UX/UI',
    ko: '프론트엔드 & UX/UI',
  },
  backend: {
    en: 'Backend / Service Architecture',
    ko: '백엔드 / 서비스 아키텍처',
  },
  security: {
    en: 'Security / Access Control',
    ko: '보안 / 접근 제어',
  },
  'db-data': {
    en: 'DB / Data Infrastructure',
    ko: 'DB / 데이터 인프라',
  },
  network: {
    en: 'Network / Communication',
    ko: '네트워크 / 통신',
  },
  'os-core': {
    en: 'OS / Core Principles',
    ko: 'OS / 핵심 원리',
  },
  'ai-business': {
    en: 'AI Industry & Business',
    ko: 'AI 산업 & 비즈니스',
  },
};

export function getHandbookCategoryLabel(locale: Locale, category?: string | null): string | null {
  if (!category) return null;
  return HANDBOOK_CATEGORY_LABELS[category as HandbookCategorySlug]?.[locale] ?? category;
}

export function getHandbookCategories(): HandbookCategorySlug[] {
  return Object.keys(HANDBOOK_CATEGORY_LABELS) as HandbookCategorySlug[];
}

export function getHandbookCategoryLabels(locale: Locale, categories?: string[] | null): string[] {
  if (!categories?.length) return [];
  return categories
    .map((cat) => HANDBOOK_CATEGORY_LABELS[cat as HandbookCategorySlug]?.[locale] ?? cat)
    .filter(Boolean) as string[];
}
