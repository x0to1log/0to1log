import assert from 'node:assert/strict';
import { formatPipelineError } from '../src/lib/admin/pipelineError.js';

const validationMessage = `1 validation error for ResearchPost
content_original
  Value error, Content too short: 5498 chars (min 6000) [type=value_error, input_value='## 1. What Happened', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error`;

assert.equal(
  formatPipelineError(validationMessage),
  'Research post too short: 5498 / 6000 chars.',
  'Validation errors should collapse into a concise content-length message',
);

assert.equal(
  formatPipelineError('Something else broke'),
  'Something else broke',
  'Unknown errors should pass through unchanged',
);

assert.equal(
  formatPipelineError('   '),
  '',
  'Blank errors should stay blank',
);

console.log('admin-pipeline-error.test.mjs passed');
