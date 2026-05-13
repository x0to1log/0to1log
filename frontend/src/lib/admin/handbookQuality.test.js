import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildLatestHandbookQualityBySlug,
  handbookQualityBadgeClass,
  handbookQualityLabel,
} from './handbookQuality.js';

test('buildLatestHandbookQualityBySlug combines latest score rows and gate logs', () => {
  const bySlug = buildLatestHandbookQualityBySlug(
    [
      {
        term_slug: 'context-window',
        score: 91,
        breakdown: { level: 'basic' },
        created_at: '2026-05-12T00:00:00Z',
      },
      {
        term_slug: 'context-window',
        score: 84,
        breakdown: { level: 'advanced' },
        created_at: '2026-05-12T00:00:01Z',
      },
      {
        term_slug: 'context-window',
        score: 79,
        breakdown: { level: 'advanced' },
        created_at: '2026-05-11T00:00:00Z',
      },
    ],
    [
      {
        pipeline_type: 'handbook.seed_generate',
        status: 'success',
        created_at: '2026-05-12T00:00:02Z',
        debug_meta: {
          slug: 'context-window',
          quality_gate: {
            status: 'admin_ready',
            issue_counts: { high: 0, medium: 0, low: 0 },
          },
          remediation_status: 'applied',
          remediation_issues: [],
        },
      },
    ],
  );

  assert.equal(bySlug['context-window'].score, 84);
  assert.equal(bySlug['context-window'].advancedScore, 84);
  assert.equal(bySlug['context-window'].basicScore, 91);
  assert.equal(bySlug['context-window'].qualityGateStatus, 'admin_ready');
  assert.equal(bySlug['context-window'].remediationStatus, 'applied');
  assert.equal(bySlug['context-window'].issueCount, 0);
});

test('buildLatestHandbookQualityBySlug surfaces remediation issues from latest log', () => {
  const bySlug = buildLatestHandbookQualityBySlug(
    [],
    [
      {
        pipeline_type: 'handbook.seed_generate',
        status: 'success',
        created_at: '2026-05-12T00:00:00Z',
        debug_meta: {
          slug: 'structured-outputs',
          quality_gate: {
            status: 'blocked_for_publish',
            issue_counts: { high: 2, medium: 1, low: 0 },
          },
          remediation_issues: [
            {
              code: 'invalid_code_fence',
              severity: 'high',
              section: 'body_advanced_en',
              message: 'Invalid Python code fence.',
            },
          ],
        },
      },
    ],
  );

  const summary = bySlug['structured-outputs'];
  assert.equal(summary.qualityGateStatus, 'blocked_for_publish');
  assert.equal(summary.highIssueCount, 2);
  assert.equal(summary.mediumIssueCount, 1);
  assert.equal(summary.issues[0].code, 'invalid_code_fence');
});

test('handbook quality label and badge prefer gate status over score', () => {
  assert.equal(
    handbookQualityLabel({ qualityGateStatus: 'blocked_for_publish', score: 95 }),
    'Blocked',
  );
  assert.equal(
    handbookQualityBadgeClass({ qualityGateStatus: 'blocked_for_publish', score: 95 }),
    'admin-quality-badge admin-quality-badge--low',
  );
  assert.equal(
    handbookQualityLabel({ qualityGateStatus: 'admin_ready', score: 84 }),
    'Ready',
  );
  assert.equal(
    handbookQualityBadgeClass({ qualityGateStatus: 'admin_ready', score: 84 }),
    'admin-quality-badge admin-quality-badge--high',
  );
});
