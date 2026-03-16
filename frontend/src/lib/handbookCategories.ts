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

const HANDBOOK_CATEGORIES: Record<
  HandbookCategorySlug,
  { label: Record<Locale, string>; description: Record<Locale, string> }
> = {
  web3: {
    label: {
      en: 'Decentralization / Web3',
      ko: '탈중앙화 / Web3',
    },
    description: {
      en: 'Blockchain, smart contracts, decentralization, tokens',
      ko: '블록체인, 스마트 컨트랙트, 탈중앙화, 토큰',
    },
  },
  'ai-ml': {
    label: {
      en: 'AI/ML & Algorithms',
      ko: 'AI/ML & 알고리즘',
    },
    description: {
      en: 'ML models, neural networks, training, AI algorithms',
      ko: 'ML 모델, 신경망, 학습, AI 알고리즘',
    },
  },
  performance: {
    label: {
      en: 'Performance / Cost Management',
      ko: '성능 / 비용 관리',
    },
    description: {
      en: 'Optimization, caching, cost management, scaling',
      ko: '최적화, 캐싱, 비용 관리, 확장성',
    },
  },
  devops: {
    label: {
      en: 'DevOps / Operations',
      ko: 'DevOps / 운영',
    },
    description: {
      en: 'CI/CD, containers, orchestration, monitoring',
      ko: 'CI/CD, 컨테이너, 오케스트레이션, 모니터링',
    },
  },
  'frontend-ux': {
    label: {
      en: 'Frontend & UX/UI',
      ko: '프론트엔드 & UX/UI',
    },
    description: {
      en: 'UI frameworks, rendering, user experience, accessibility',
      ko: 'UI 프레임워크, 렌더링, 사용자 경험, 접근성',
    },
  },
  backend: {
    label: {
      en: 'Backend / Service Architecture',
      ko: '백엔드 / 서비스 아키텍처',
    },
    description: {
      en: 'Server architecture, APIs, microservices, messaging',
      ko: '서버 아키텍처, API, 마이크로서비스, 메시징',
    },
  },
  security: {
    label: {
      en: 'Security / Access Control',
      ko: '보안 / 접근 제어',
    },
    description: {
      en: 'Authentication, encryption, access control, vulnerabilities',
      ko: '인증, 암호화, 접근 제어, 취약점',
    },
  },
  'db-data': {
    label: {
      en: 'DB / Data Infrastructure',
      ko: 'DB / 데이터 인프라',
    },
    description: {
      en: 'Databases, data infrastructure, indexing, storage',
      ko: '데이터베이스, 데이터 인프라, 인덱싱, 스토리지',
    },
  },
  network: {
    label: {
      en: 'Network / Communication',
      ko: '네트워크 / 통신',
    },
    description: {
      en: 'Protocols, DNS, load balancing, CDN',
      ko: '프로토콜, DNS, 로드 밸런싱, CDN',
    },
  },
  'os-core': {
    label: {
      en: 'OS / Core Principles',
      ko: 'OS / 핵심 원리',
    },
    description: {
      en: 'Operating systems, memory, processes, file systems',
      ko: '운영체제, 메모리, 프로세스, 파일 시스템',
    },
  },
  'ai-business': {
    label: {
      en: 'AI Industry & Business',
      ko: 'AI 산업 & 비즈니스',
    },
    description: {
      en: 'AI industry trends, business applications, market analysis',
      ko: 'AI 산업 트렌드, 비즈니스 응용, 시장 분석',
    },
  },
};

export function getHandbookCategoryLabel(locale: Locale, category?: string | null): string | null {
  if (!category) return null;
  return HANDBOOK_CATEGORIES[category as HandbookCategorySlug]?.label[locale] ?? category;
}

export function getHandbookCategories(): HandbookCategorySlug[] {
  return Object.keys(HANDBOOK_CATEGORIES) as HandbookCategorySlug[];
}

export function getHandbookCategoryLabels(locale: Locale, categories?: string[] | null): string[] {
  if (!categories?.length) return [];
  return categories
    .map((cat) => HANDBOOK_CATEGORIES[cat as HandbookCategorySlug]?.label[locale] ?? cat)
    .filter(Boolean) as string[];
}

export function getHandbookCategoryDescription(locale: Locale, category: string): string | null {
  return HANDBOOK_CATEGORIES[category as HandbookCategorySlug]?.description[locale] ?? null;
}
