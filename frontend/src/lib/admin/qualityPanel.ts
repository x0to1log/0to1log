/**
 * Normalize fact_pack from news_posts row into a shape the QualityPanel UI
 * can render without branching at each element. Handles two data eras:
 *   - legacy (v10, Apr 19 and earlier): aggregate scores only, no per-call breakdowns
 *   - v11 (Apr 20+): aggregate + 3 per-QC-call sub-score breakdowns with evidence
 */

export interface SubScore {
  evidence: string;
  score: number;  // 0-10, clamped
}

export type SubScoreCategory = Record<string, SubScore>;
export type Breakdown = Record<string, SubScoreCategory>;

export interface QualityIssue {
  severity: 'major' | 'minor';
  scope: string;
  category: string;
  message: string;
}

export interface NormalizedQuality {
  score: number | null;
  autoPublishEligible: boolean;
  isLegacy: boolean;
  aggregates: {
    weightedLlm: { expert_body: number; learner_body: number; frontload: number };
    rawLlm:      { expert_body: number; learner_body: number; frontload: number };
    deterministic: { structure: number; traceability: number; locale: number };
  };
  breakdowns: {
    expert: Breakdown | null;
    learner: Breakdown | null;
    frontload: Breakdown | null;
  };
  issues: QualityIssue[];
  capsApplied: string[];
  structuralPenalty: number;
  structuralWarnings: string[];
  urlValidationFailed: boolean;
  urlValidationFailures: unknown[];
}

const ZERO_AGG = { expert_body: 0, learner_body: 0, frontload: 0 };
const ZERO_DET = { structure: 0, traceability: 0, locale: 0 };

function clampSubScore(raw: unknown): SubScore {
  if (!raw || typeof raw !== 'object') return { evidence: '', score: 0 };
  const obj = raw as Record<string, unknown>;
  const evidence = typeof obj.evidence === 'string' ? obj.evidence : '';
  const rawScore = typeof obj.score === 'number' ? obj.score : 0;
  const score = Math.max(0, Math.min(10, Math.round(rawScore)));
  return { evidence, score };
}

function normalizeBreakdown(raw: unknown): Breakdown | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  if (Object.keys(obj).length === 0) return null;
  const out: Breakdown = {};
  for (const [categoryKey, categoryVal] of Object.entries(obj)) {
    if (!categoryVal || typeof categoryVal !== 'object') continue;
    const subs: SubScoreCategory = {};
    for (const [subKey, subVal] of Object.entries(categoryVal as Record<string, unknown>)) {
      subs[subKey] = clampSubScore(subVal);
    }
    if (Object.keys(subs).length > 0) out[categoryKey] = subs;
  }
  return Object.keys(out).length > 0 ? out : null;
}

function normalizeIssues(raw: unknown): QualityIssue[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === 'object')
    .map((x) => ({
      severity: x.severity === 'major' ? 'major' : 'minor',
      scope: typeof x.scope === 'string' ? x.scope : '',
      category: typeof x.category === 'string' ? x.category : '',
      message: typeof x.message === 'string' ? x.message : '',
    }));
}

export function normalizeQualityData(factPack: unknown): NormalizedQuality {
  const fp = (factPack && typeof factPack === 'object') ? factPack as Record<string, unknown> : {};

  const qb = (fp.quality_breakdown && typeof fp.quality_breakdown === 'object')
    ? fp.quality_breakdown as Record<string, Record<string, number>>
    : {};

  const expert   = normalizeBreakdown(fp.expert_breakdown);
  const learner  = normalizeBreakdown(fp.learner_breakdown);
  const frontload = normalizeBreakdown(fp.frontload_breakdown);

  const isLegacy = expert === null && learner === null && frontload === null;

  return {
    score: typeof fp.quality_score === 'number' ? fp.quality_score : null,
    autoPublishEligible: fp.auto_publish_eligible === true,
    isLegacy,
    aggregates: {
      weightedLlm:   { ...ZERO_AGG, ...(qb.llm || {}) },
      rawLlm:        { ...ZERO_AGG, ...(qb.raw_llm || {}) },
      deterministic: { ...ZERO_DET, ...(qb.deterministic || {}) },
    },
    breakdowns: { expert, learner, frontload },
    issues: normalizeIssues(fp.quality_issues),
    capsApplied: Array.isArray(fp.quality_caps_applied) ? fp.quality_caps_applied as string[] : [],
    structuralPenalty: typeof fp.structural_penalty === 'number' ? fp.structural_penalty : 0,
    structuralWarnings: Array.isArray(fp.structural_warnings) ? fp.structural_warnings as string[] : [],
    urlValidationFailed: fp.url_validation_failed === true,
    urlValidationFailures: Array.isArray(fp.url_validation_failures) ? fp.url_validation_failures : [],
  };
}

/** Admin-quality class for a 0-10 sub-score — theme-aware via CSS vars. */
export function scoreColorClass(score: number): string {
  if (score >= 8) return 'admin-quality-subscore-score admin-quality-subscore-score--high';
  if (score >= 4) return 'admin-quality-subscore-score admin-quality-subscore-score--mid';
  return 'admin-quality-subscore-score admin-quality-subscore-score--low';
}

/** Human label + class for severity chip — theme-aware via CSS vars. */
export function severityLabel(s: 'major' | 'minor'): { label: string; className: string } {
  return s === 'major'
    ? { label: 'Major', className: 'admin-quality-severity admin-quality-severity--major' }
    : { label: 'Minor', className: 'admin-quality-severity admin-quality-severity--minor' };
}
