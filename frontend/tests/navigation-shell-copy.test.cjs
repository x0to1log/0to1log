const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const navigation = read('src/components/Navigation.astro');
assert(navigation.includes('AI News'), 'Navigation must expose the public AI News label');
assert(navigation.includes('Handbook'), 'Navigation must expose the public Handbook label');
assert(navigation.includes("href: '/library/'"), 'Navigation must include Library in primary navigation');
assert(navigation.includes('site-primary-nav--desktop'), 'Navigation must keep a desktop primary-nav shell');
assert(navigation.includes('site-primary-nav--mobile'), 'Navigation must keep a mobile primary-nav shell');
assert(navigation.includes('data-theme-cycle'), 'Navigation utility drawer must host the theme control');
assert(!navigation.includes('<ThemeToggle'), 'Navigation must no longer render the inline ThemeToggle component');

const i18n = read('src/i18n/index.ts');
assert(i18n.includes("'nav.log': 'AI News'"), 'English nav.log label must be AI News');
assert(i18n.includes("'log.title': 'AI News'"), 'English log.title must be AI News');
assert(i18n.includes("'post.back': 'Back to AI News'"), 'English back copy must point to AI News');

const adminHeader = read('src/components/admin/AdminHeader.astro');
assert(adminHeader.includes("activeTab: 'posts' | 'handbook'"), 'Admin header must use posts/handbook tabs');
assert(adminHeader.includes('Posts'), 'Admin header must expose Posts as the internal label');

const adminIndex = read('src/pages/admin/index.astro');
assert(adminIndex.includes('Post Drafts'), 'Admin dashboard must expose Post Drafts');
