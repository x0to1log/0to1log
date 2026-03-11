const fs = require('fs');
const path = require('path');

const root = process.cwd();

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

const migration = read('supabase/migrations/00016_term_feedback.sql');
assertIncludes(migration, 'CREATE TABLE term_feedback', 'term feedback table');
assertIncludes(migration, "reaction TEXT NOT NULL CHECK (reaction IN ('helpful', 'confusing'))", 'reaction check constraint');
assertIncludes(migration, 'UNIQUE (user_id, term_id, locale)', 'unique user-term-locale constraint');
assertIncludes(migration, 'ALTER TABLE term_feedback ENABLE ROW LEVEL SECURITY;', 'rls enable');

const api = read('frontend/src/pages/api/user/term-feedback.ts');
assertIncludes(api, "from('term_feedback')", 'term feedback api table access');
assertIncludes(api, "term_id = url.searchParams.get('term_id')", 'term id query param');
assertIncludes(api, 'reaction', 'reaction handling');

const component = read('frontend/src/components/newsprint/HandbookFeedback.astro');
assertIncludes(component, 'data-handbook-feedback', 'feedback root dataset');
assertIncludes(component, 'data-reaction="confusing"', 'confusing button dataset');
assertIncludes(component, 'data-reaction="helpful"', 'helpful button dataset');
assertIncludes(component, 'data-feedback-status', 'status message');

const script = read('frontend/src/scripts/handbookFeedback.ts');
assertIncludes(script, '/api/user/term-feedback', 'feedback api client usage');
assertIncludes(script, 'ariaPressed', 'pressed state updates');
assertIncludes(script, 'loginUrl', 'guest login redirect');

const pageEn = read('frontend/src/pages/en/handbook/[slug].astro');
assertIncludes(pageEn, "import '../../../scripts/handbookFeedback';", 'en page feedback script import');
assertIncludes(pageEn, '<HandbookFeedback', 'en component mount');
assertIncludes(pageEn, 'termId={term.id}', 'en term id prop');

const pageKo = read('frontend/src/pages/ko/handbook/[slug].astro');
assertIncludes(pageKo, "import '../../../scripts/handbookFeedback';", 'ko page feedback script import');
assertIncludes(pageKo, '<HandbookFeedback', 'ko component mount');
assertIncludes(pageKo, 'termId={term.id}', 'ko term id prop');

console.log('handbook-feedback-api-contract.test.cjs passed');
