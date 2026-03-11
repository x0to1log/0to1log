const fs = require('fs');
const path = require('path');
const css = fs.readFileSync(path.join(process.cwd(), 'frontend/src/styles/global.css'), 'utf8');

function expectIncludes(snippet, label) {
  if (!css.includes(snippet)) {
    console.error(`Missing ${label}`);
    process.exit(1);
  }
}

expectIncludes('.blog-shell .newsprint-comments-title', 'blog comment title override');
expectIncludes('.blog-shell .newsprint-comment-input', 'blog comment input override');
expectIncludes('.blog-shell .newsprint-comment-login-input', 'blog login input override');
expectIncludes('font-family: var(--font-blog-body);', 'blog body font usage');
expectIncludes('font-family: var(--font-blog-ui);', 'blog ui font usage');

console.log('blog-comment-font overrides present');
