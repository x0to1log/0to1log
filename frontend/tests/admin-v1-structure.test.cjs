const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(source, needle, label) {
  if (!source.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

function run() {
  const sidebar = read('src/components/admin/AdminSidebar.astro');
  assertIncludes(sidebar, "activeSection?: 'posts' | 'handbook' | 'content' | 'settings';", 'admin sidebar settings section');
  assertIncludes(sidebar, '<span>Site Content</span>', 'site content label');
  assertIncludes(sidebar, 'href="/admin/settings"', 'settings nav item');

  const adminIndex = read('src/pages/admin/index.astro');
  assertIncludes(adminIndex, 'Draft Posts', 'posts summary card');
  assertIncludes(adminIndex, 'Published Posts', 'published posts summary card');
  assertIncludes(adminIndex, 'Draft Terms', 'draft terms summary card');
  assertIncludes(adminIndex, 'Site Content', 'site content summary card');
  assertIncludes(adminIndex, 'New Handbook Term', 'handbook quick action');
  assertIncludes(adminIndex, 'Edit Site Content', 'site content quick action');
  assertIncludes(adminIndex, 'Preview', 'post preview action');

  const adminHandbook = read('src/pages/admin/handbook/index.astro');
  assertIncludes(adminHandbook, 'Preview', 'handbook preview action');

  const adminContent = read('src/pages/admin/content.astro');
  [
    'home_title',
    'home_subtitle',
    'home_intro',
    'about_tagline',
    'about_publication_intro',
    'about_publication_detail',
    'about_editor_intro',
    'library_empty_saved',
    'library_empty_read',
    'library_empty_progress',
  ].forEach((key) => assertIncludes(adminContent, key, `site content key ${key}`));

  const migration = fs.readFileSync(path.join(path.resolve(root, '..'), 'supabase/migrations/00010_site_content.sql'), 'utf8');
  [
    'home_title',
    'home_subtitle',
    'home_intro',
    'about_tagline',
    'about_publication_intro',
    'about_publication_detail',
    'about_editor_intro',
    'library_empty_saved',
    'library_empty_read',
    'library_empty_progress',
  ].forEach((key) => assertIncludes(migration, `'${key}'`, `migration seed ${key}`));

  const enHome = read('src/pages/en/index.astro');
  const koHome = read('src/pages/ko/index.astro');
  const aboutEn = read('src/pages/about/index.astro');
  const aboutKo = read('src/pages/ko/about/index.astro');
  const library = read('src/pages/library/index.astro');

  [enHome, koHome, aboutEn, aboutKo, library].forEach((source, index) => {
    assertIncludes(source, 'getSiteContents', `site content fetch usage #${index + 1}`);
  });

  console.log('admin-v1-structure.test: ok');
}

run();
