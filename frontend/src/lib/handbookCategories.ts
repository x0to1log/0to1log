import type { Locale } from '../i18n/index';

export type HandbookCategorySlug =
  | 'products-platforms'
  | 'llm-genai'
  | 'deep-learning'
  | 'ml-fundamentals'
  | 'data-engineering'
  | 'infra-hardware'
  | 'safety-ethics'
  | 'cs-fundamentals'
  | 'math-statistics';

const HANDBOOK_CATEGORIES: Record<
  HandbookCategorySlug,
  { label: Record<Locale, string>; description: Record<Locale, string> }
> = {
  'products-platforms': {
    label: {
      en: 'Products & Platforms',
      ko: '제품 · 플랫폼',
    },
    description: {
      en: 'Specific models, companies, frameworks, tools',
      ko: '특정 모델, 기업, 프레임워크, 도구',
    },
  },
  'llm-genai': {
    label: {
      en: 'LLM & Generative AI',
      ko: 'LLM · 생성AI',
    },
    description: {
      en: 'Large language models, generative AI, agents, RLHF, multimodal',
      ko: '대형 언어 모델, 생성AI, 에이전트, RLHF, 멀티모달',
    },
  },
  'deep-learning': {
    label: {
      en: 'Deep Learning',
      ko: '딥러닝',
    },
    description: {
      en: 'Neural network architectures, training techniques, vision, audio',
      ko: '신경망 아키텍처, 학습 기법, 비전, 오디오',
    },
  },
  'ml-fundamentals': {
    label: {
      en: 'ML Fundamentals',
      ko: 'ML 기초',
    },
    description: {
      en: 'Classical ML algorithms, learning theory, evaluation methods',
      ko: '전통 ML 알고리즘, 학습 이론, 평가 방법',
    },
  },
  'data-engineering': {
    label: {
      en: 'Data Engineering',
      ko: '데이터 엔지니어링',
    },
    description: {
      en: 'Data pipelines, storage, processing, formats',
      ko: '데이터 파이프라인, 저장소, 처리, 포맷',
    },
  },
  'infra-hardware': {
    label: {
      en: 'Infra & Hardware',
      ko: '인프라 · 하드웨어',
    },
    description: {
      en: 'GPU, cloud, MLOps, deployment, optimization',
      ko: 'GPU, 클라우드, MLOps, 배포, 최적화',
    },
  },
  'safety-ethics': {
    label: {
      en: 'AI Safety & Ethics',
      ko: 'AI 안전 · 윤리',
    },
    description: {
      en: 'AI safety, security, alignment, regulation, fairness',
      ko: 'AI 안전, 보안, 정렬, 규제, 공정성',
    },
  },
  'cs-fundamentals': {
    label: {
      en: 'CS Fundamentals',
      ko: 'CS 기초',
    },
    description: {
      en: 'Programming, data structures, algorithms, networking, OS, web basics',
      ko: '프로그래밍, 자료구조, 알고리즘, 네트워크, OS, 웹 기초',
    },
  },
  'math-statistics': {
    label: {
      en: 'Math & Statistics',
      ko: '수학 · 통계',
    },
    description: {
      en: 'Linear algebra, probability, statistics, information theory',
      ko: '선형대수, 확률, 통계, 정보이론',
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
