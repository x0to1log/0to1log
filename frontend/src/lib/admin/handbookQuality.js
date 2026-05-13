const EMPTY_COUNTS = Object.freeze({ high: 0, medium: 0, low: 0 });

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function timestamp(value) {
  const time = Date.parse(value || '');
  return Number.isFinite(time) ? time : 0;
}

function scoreLevel(row) {
  const breakdown = asObject(row?.breakdown);
  const level = typeof breakdown.level === 'string' ? breakdown.level.toLowerCase() : '';
  return level === 'basic' || level === 'advanced' ? level : 'overall';
}

function normalizeIssue(raw) {
  const issue = asObject(raw);
  return {
    code: typeof issue.code === 'string' ? issue.code : 'unknown_issue',
    severity: ['high', 'medium', 'low'].includes(issue.severity) ? issue.severity : 'low',
    section: typeof issue.section === 'string' ? issue.section : '',
    locale: typeof issue.locale === 'string' ? issue.locale : '',
    message: typeof issue.message === 'string' ? issue.message : '',
    suggestion: typeof issue.suggestion === 'string' ? issue.suggestion : '',
  };
}

function ensureSummary(out, slug) {
  if (!out[slug]) {
    out[slug] = {
      slug,
      score: null,
      basicScore: null,
      advancedScore: null,
      scoreCreatedAt: null,
      qualityGateStatus: '',
      qualityGate: null,
      remediationStatus: '',
      issues: [],
      issueCount: 0,
      highIssueCount: 0,
      mediumIssueCount: 0,
      lowIssueCount: 0,
      latestLogCreatedAt: null,
      latestPipelineType: '',
      latestLogStatus: '',
      warnings: [],
    };
  }
  return out[slug];
}

export function buildLatestHandbookQualityBySlug(scoreRows = [], logRows = []) {
  const out = {};
  const scoreSeenAt = {};
  const logSeenAt = {};

  for (const row of asArray(scoreRows)) {
    const slug = typeof row?.term_slug === 'string' ? row.term_slug : '';
    const score = typeof row?.score === 'number' ? row.score : null;
    if (!slug || score === null) continue;

    const summary = ensureSummary(out, slug);
    const level = scoreLevel(row);
    const seenKey = `${slug}:${level}`;
    const createdAt = row.created_at || '';
    if ((scoreSeenAt[seenKey] || 0) > timestamp(createdAt)) continue;
    scoreSeenAt[seenKey] = timestamp(createdAt);

    if (level === 'basic') {
      summary.basicScore = score;
    } else if (level === 'advanced') {
      summary.advancedScore = score;
    } else if (summary.score === null) {
      summary.score = score;
    }

    summary.score = summary.advancedScore ?? summary.score ?? summary.basicScore;
    summary.scoreCreatedAt = createdAt || summary.scoreCreatedAt;
  }

  for (const row of asArray(logRows)) {
    const meta = asObject(row?.debug_meta);
    const slug = typeof meta.slug === 'string' ? meta.slug : '';
    if (!slug) continue;
    const hasQualityMeta = meta.quality_gate || meta.remediation_issues || meta.remediation_status;
    if (!hasQualityMeta) continue;

    const createdAt = row.created_at || '';
    if ((logSeenAt[slug] || 0) > timestamp(createdAt)) continue;
    logSeenAt[slug] = timestamp(createdAt);

    const summary = ensureSummary(out, slug);
    const gate = asObject(meta.quality_gate);
    const counts = { ...EMPTY_COUNTS, ...asObject(gate.issue_counts) };
    const issues = asArray(meta.remediation_issues).map(normalizeIssue);

    summary.qualityGate = Object.keys(gate).length > 0 ? gate : null;
    summary.qualityGateStatus = typeof gate.status === 'string' ? gate.status : '';
    summary.remediationStatus = typeof meta.remediation_status === 'string' ? meta.remediation_status : '';
    summary.issues = issues;
    summary.highIssueCount = Number(counts.high || 0);
    summary.mediumIssueCount = Number(counts.medium || 0);
    summary.lowIssueCount = Number(counts.low || 0);
    summary.issueCount = summary.highIssueCount + summary.mediumIssueCount + summary.lowIssueCount;
    if (summary.issueCount === 0) summary.issueCount = issues.length;
    summary.latestLogCreatedAt = createdAt || null;
    summary.latestPipelineType = typeof row?.pipeline_type === 'string' ? row.pipeline_type : '';
    summary.latestLogStatus = typeof row?.status === 'string' ? row.status : '';
    summary.warnings = asArray(meta.warnings).filter((item) => typeof item === 'string');
  }

  return out;
}

export function handbookQualityLabel(summary) {
  const gate = summary?.qualityGateStatus || '';
  if (gate === 'admin_ready') return 'Ready';
  if (gate === 'needs_remediation') return 'Needs fix';
  if (gate === 'blocked_for_publish') return 'Blocked';
  if (typeof summary?.score === 'number') return `Q${summary.score}`;
  return 'No QC';
}

export function handbookQualityBadgeClass(summary) {
  const gate = summary?.qualityGateStatus || '';
  if (gate === 'admin_ready') return 'admin-quality-badge admin-quality-badge--high';
  if (gate === 'needs_remediation') return 'admin-quality-badge admin-quality-badge--mid';
  if (gate === 'blocked_for_publish') return 'admin-quality-badge admin-quality-badge--low';

  const score = typeof summary?.score === 'number' ? summary.score : null;
  if (score === null) return 'admin-quality-badge admin-quality-badge--muted';
  if (score >= 80) return 'admin-quality-badge admin-quality-badge--high';
  if (score >= 60) return 'admin-quality-badge admin-quality-badge--mid';
  return 'admin-quality-badge admin-quality-badge--low';
}
