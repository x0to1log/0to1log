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
  | 'web3';

const HANDBOOK_CATEGORY_LABELS: Record<HandbookCategorySlug, Record<Locale, string>> = {
  'ai-ml':        { en: 'AI/ML & Algorithm',              ko: 'AI/ML & 알고리즘' },
  'db-data':      { en: 'DB / Data Infra',                ko: 'DB / 데이터 인프라' },
  'backend':      { en: 'Backend / Service Architecture',  ko: '백엔드 / 서비스 아키텍처' },
  'frontend-ux':  { en: 'Frontend & UX/UI',               ko: '프론트엔드 & UX/UI' },
  'network':      { en: 'Network / Communication',         ko: '네트워크 / 통신' },
  'security':     { en: 'Security / Access Control',       ko: '보안 / 접근 제어' },
  'os-core':      { en: 'OS / Core Principle',             ko: 'OS / 핵심 원리' },
  'devops':       { en: 'DevOps / Operation',              ko: 'DevOps / 운영' },
  'performance':  { en: 'Performance / Cost Mgt',          ko: '성능 / 비용 관리' },
  'web3':         { en: 'Decentralization / Web3',         ko: '탈중앙화 / Web3' },
};

export function getHandbookCategoryLabel(locale: Locale, category?: string | null): string | null {
  if (!category) return null;
  return HANDBOOK_CATEGORY_LABELS[category as HandbookCategorySlug]?.[locale] ?? category;
}

export function getHandbookCategories(): HandbookCategorySlug[] {
  return Object.keys(HANDBOOK_CATEGORY_LABELS) as HandbookCategorySlug[];
}
