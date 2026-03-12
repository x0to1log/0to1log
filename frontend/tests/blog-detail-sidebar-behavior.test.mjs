import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const helperPath = path.join(process.cwd(), 'frontend', 'src', 'lib', 'pageData', 'blogSidebar.ts');
assert(fs.existsSync(helperPath), 'Missing shared blog sidebar helper');

const {
  BLOG_DETAIL_ACTIVE_VISIBLE_LIMIT,
  BLOG_SIDEBAR_SUB_VISIBLE_LIMIT,
  BLOG_SIDEBAR_VISIBLE_LIMIT,
  buildBlogSidebarDataset,
  getBlogSidebarCategoryState,
  getBlogSidebarGroupExpanded,
} = await import(pathToFileURL(helperPath).href);

assert(BLOG_SIDEBAR_VISIBLE_LIMIT === 3, 'Default sidebar category limit must stay at 3 posts');
assert(BLOG_SIDEBAR_SUB_VISIBLE_LIMIT === 1, 'Small-note sidebar category limit must stay at 1 post');
assert(BLOG_DETAIL_ACTIVE_VISIBLE_LIMIT === 10, 'Detail sidebar must expand the active category to 10 posts');

function makePosts(prefix, category, count) {
  return Array.from({ length: count }, (_, index) => {
    const number = count - index;
    return {
      title: `${prefix} ${number}`,
      slug: `${prefix.toLowerCase()}-${number}`,
      category,
      publishedAt: `2026-03-${String(number).padStart(2, '0')}T00:00:00.000Z`,
    };
  });
}

const studyPosts = makePosts('Study', 'study', 12);
const activeStudy = getBlogSidebarCategoryState(studyPosts, {
  mode: 'detail',
  category: 'study',
  currentCategory: 'study',
  currentSlug: 'study-1',
});
assert(activeStudy.expanded === true, 'Active detail category must start expanded');
assert(activeStudy.visibleLimit === 10, 'Active detail category must use the 10-post limit');
assert(activeStudy.visiblePosts.length === 10, 'Active detail category must show 10 posts');
assert(
  activeStudy.visiblePosts.some((post) => post.slug === 'study-1'),
  'Active detail category must keep the current post visible even if it is older than the latest 10',
);
assert(
  activeStudy.extraPosts.length === 2,
  'Active detail category must move only the remaining posts into the extra bucket',
);
assert(
  activeStudy.extraPosts.every((post) => post.slug !== 'study-1'),
  'Current detail post must not remain hidden inside the extra bucket',
);

const workNotePosts = makePosts('Work', 'work-note', 12);
const activeWorkNote = getBlogSidebarCategoryState(workNotePosts, {
  mode: 'detail',
  category: 'work-note',
  currentCategory: 'work-note',
  currentSlug: 'work-1',
});
assert(activeWorkNote.visibleLimit === 10, 'Active small-note detail category must override the 1-post limit');
assert(activeWorkNote.visiblePosts.length === 10, 'Active small-note detail category must still show 10 posts');
assert(
  activeWorkNote.visiblePosts.some((post) => post.slug === 'work-1'),
  'Active small-note detail category must keep the current post visible',
);

const projectPosts = makePosts('Project', 'project', 5);
const inactiveProject = getBlogSidebarCategoryState(projectPosts, {
  mode: 'detail',
  category: 'project',
  currentCategory: 'study',
  currentSlug: 'study-1',
});
assert(inactiveProject.expanded === false, 'Inactive detail categories must start collapsed');
assert(inactiveProject.visibleLimit === 3, 'Inactive detail categories must keep the default 3-post limit');

assert(
  getBlogSidebarGroupExpanded(['study', 'project', 'career'], {
    mode: 'detail',
    currentCategory: 'study',
    groupCount: 12,
  }) === true,
  'Detail sidebar must keep the main category group expanded',
);
assert(
  getBlogSidebarGroupExpanded(['work-note', 'daily'], {
    mode: 'detail',
    currentCategory: 'study',
    groupCount: 4,
  }) === true,
  'Detail sidebar must keep non-current groups expanded so category rows stay visible',
);

const baseDataset = buildBlogSidebarDataset(studyPosts);
assert(baseDataset.length === 12, 'Shared sidebar dataset builder must preserve the full published dataset');

const previewDataset = buildBlogSidebarDataset(studyPosts, {
  title: 'Draft current post',
  slug: 'study-draft',
  category: 'study',
  publishedAt: null,
});
assert(previewDataset.length === 13, 'Preview detail sidebar must inject the current unpublished post once');
assert(
  previewDataset.filter((post) => post.slug === 'study-draft').length === 1,
  'Preview detail sidebar must not duplicate the injected current post',
);

const dedupedDataset = buildBlogSidebarDataset(
  [...studyPosts, { title: 'Existing', slug: 'study-1', category: 'study', publishedAt: null }],
  { title: 'Existing', slug: 'study-1', category: 'study', publishedAt: null },
);
assert(
  dedupedDataset.filter((post) => post.slug === 'study-1').length === 1,
  'Shared sidebar dataset builder must dedupe the current post by slug',
);

console.log('blog detail sidebar behavior ok');
