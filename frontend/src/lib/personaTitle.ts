/**
 * Resolve which title/excerpt to display based on user persona.
 *
 * Background:
 * - news_posts.title and news_posts.excerpt are the canonical (expert-tone) versions.
 * - For learner persona, the backend pipeline saves separate beginner-friendly versions
 *   into guide_items.title_learner and guide_items.excerpt_learner.
 * - When the viewer is a learner (or anonymous, since default persona is 'learner'),
 *   we display the learner-specific text in list cards, detail headers, and SEO/OG meta.
 * - Anonymous viewers (search engine crawlers, SNS preview bots) get the learner version
 *   automatically because the default persona is 'learner' — this aligns with our
 *   discovery strategy of targeting non-developer professionals.
 *
 * Falls back gracefully:
 * - Old posts without guide_items → use canonical title/excerpt
 * - Posts with empty title_learner → use canonical
 * - Expert persona → always use canonical
 */
export interface PersonaResolvableContent {
  title?: string | null;
  title_learner?: string | null;
  excerpt?: string | null;
  guide_items?: {
    title_learner?: string;
    excerpt_learner?: string;
    [key: string]: any;
  } | null;
}

export interface ResolvedDisplay {
  title: string;
  excerpt: string;
}

export function resolveDisplayTitleExcerpt(
  post: PersonaResolvableContent | null | undefined,
  persona: string | null | undefined,
): ResolvedDisplay {
  if (!post) return { title: '', excerpt: '' };

  const canonicalTitle = post.title || '';
  const canonicalExcerpt = post.excerpt || '';

  if (persona === 'learner') {
    const learnerTitle = post.title_learner || post.guide_items?.title_learner;
    if (learnerTitle) {
      return {
        title: learnerTitle,
        excerpt: post.guide_items?.excerpt_learner || canonicalExcerpt,
      };
    }
  }

  return { title: canonicalTitle, excerpt: canonicalExcerpt };
}

/**
 * Effective persona for the current request.
 * - Logged-in user: their profile setting (or 'learner' default)
 * - Anonymous: 'learner' (matches our discovery strategy)
 */
export function getEffectivePersona(profile: { persona?: string | null } | null | undefined): string {
  return profile?.persona || 'learner';
}
