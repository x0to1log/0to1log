import { normalizeCategorySlug } from './categories';

type Locale = 'en' | 'ko';

const focusMap: Record<Locale, Record<string, string[]>> = {
  en: {
    'ai-news': [
      'What changed today',
      'Why it matters right now',
      'What to watch next',
    ],
    study: [
      'What concept to understand',
      'What to remember from this note',
      'What to try after reading',
    ],
    career: [
      'What decision matters here',
      'What signal is worth noticing',
      'What to apply in actual work',
    ],
    project: [
      'What was built in this step',
      'What tradeoff appeared',
      'What to improve next',
    ],
    'work-note': [
      'What moved in this work session',
      'What blocker or decision matters',
      'What to do next',
    ],
    daily: [
      'What stood out today',
      'What it made me notice',
      'What I want to carry forward',
    ],
  },
  ko: {
    'ai-news': [
      '오늘 무엇이 달라졌는가',
      '지금 왜 중요해졌는가',
      '다음엔 무엇을 지켜볼 것인가',
    ],
    study: [
      '어떤 개념을 이해해야 하는가',
      '이 노트에서 무엇을 기억할 것인가',
      '읽고 나서 무엇을 시도할 것인가',
    ],
    career: [
      '어떤 판단이 중요해졌는가',
      '어떤 신호를 읽어야 하는가',
      '실무에 무엇을 적용할 것인가',
    ],
    project: [
      '이번 단계에서 무엇을 만들었는가',
      '어떤 트레이드오프가 드러났는가',
      '다음에는 무엇을 개선할 것인가',
    ],
    'work-note': [
      '이번 작업에서 무엇이 움직였는가',
      '어떤 막힘이나 결정이 중요했는가',
      '다음에 바로 이어서 할 일은 무엇인가',
    ],
    daily: [
      '오늘 유난히 남은 장면은 무엇인가',
      '그 일이 내게 무엇을 보이게 했는가',
      '내일로 가져갈 감각은 무엇인가',
    ],
  },
};

export function getArticleFocusItems(locale: Locale, category?: string | null): string[] {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) {
    return locale === 'ko'
      ? ['포착한 변화', '실무 영향', '다음에 볼 지점']
      : ['Key shift', 'Practical impact', 'Next point to watch'];
  }

  return (
    focusMap[locale][normalized] ??
    (locale === 'ko'
      ? ['포착한 변화', '실무 영향', '다음에 볼 지점']
      : ['Key shift', 'Practical impact', 'Next point to watch'])
  );
}
