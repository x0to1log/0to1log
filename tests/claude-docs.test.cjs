const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(process.cwd(), filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const rootDoc = read('CLAUDE.md');
assert(rootDoc.includes('# 0to1log'), 'Root CLAUDE.md must keep the project title');
assert(rootDoc.includes('현재 스프린트는 `docs/plans/ACTIVE_SPRINT.md` 기준'), 'Root CLAUDE.md must contain the current sprint rule');
assert(rootDoc.includes('Backend Python virtualenv는 `backend/.venv`만 사용'), 'Root CLAUDE.md must contain the backend venv rule');

const frontendDoc = read('frontend/CLAUDE.md');
assert(frontendDoc.includes('# Frontend Rules'), 'Frontend CLAUDE.md must keep its title');
assert(frontendDoc.includes('## Astro 규칙'), 'Frontend CLAUDE.md must contain the Astro rules section');
assert(frontendDoc.includes('## Right Rail'), 'Frontend CLAUDE.md must contain the Right Rail section');
assert(frontendDoc.includes('## Admin Editor'), 'Frontend CLAUDE.md must contain the Admin Editor section');
assert(frontendDoc.includes('--font-article-heading'), 'Frontend CLAUDE.md must document the article heading font token');

const backendDoc = read('backend/CLAUDE.md');
assert(backendDoc.includes('# Backend Rules'), 'Backend CLAUDE.md must keep its title');
assert(backendDoc.includes('Virtualenv policy: use `backend/.venv` only'), 'Backend CLAUDE.md must document backend virtualenv policy');
assert(backendDoc.includes('Admin 라우트는 `Depends(require_admin)` 필수'), 'Backend CLAUDE.md must document admin auth rule');
assert(backendDoc.includes('Cron 라우트는 `x-cron-secret` 헤더 검증 필수'), 'Backend CLAUDE.md must document cron auth rule');
