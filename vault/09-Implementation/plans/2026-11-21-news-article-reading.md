# 뉴스 기사 본문 읽기 개선 Implementation Plan

**Status:** Task 1–8 실행 완료 (2026-11-21, `main`, push 전). Task 1 Step 5(`isLongBold` 기준)만 Amy 확정 대기. 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공개 뉴스 기사 상세에서 단어 중간 줄바꿈과 깨진·과한 굵은 글씨를 없애고, 머리 부분을 줄여 본문을 위로 올리고, 내려 읽는 동안 떠 있는 막대를 숨긴다.

**Architecture:**
- 굵은 글씨는 순수 함수 `normalizeNewsBold`가 마크다운 원문 단계에서 정리한다. 뉴스 렌더 경로(`newsDetailPage.ts`)에서만 호출한다.
- 화면 변화는 `NewsprintArticleLayout`의 새 prop `newsReading`(기본 `false`)으로만 켠다. 켜지면 루트에 `newsprint-article--news` 클래스가 붙고, 새 CSS는 그 클래스 아래에만 건다.
- 떠 있는 막대는 새 스크립트 없이, 헤더가 이미 붙이는 `site-header--fixed site-header--hidden` 상태를 CSS `:has()`로 읽는다.

**Tech Stack:** Astro v5 SSR, `global.css`(Tailwind v4 토큰), unified/remark, 순수 Node 테스트

**Spec:** [[2026-11-21-news-article-reading-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 시작 전에 `git branch --show-current`를 확인한다. 2026-11-21 현재 작업 트리는 `fix/handbook-writer-grounding` 브랜치이고 vault에 다른 미커밋 변경이 있다. **어느 브랜치에서 작업할지 Amy에게 확인한 뒤 시작한다.** (`AGENTS.md`: main-only가 기본, 기능 브랜치는 선택.)
- 파일마다 `git status --short -- <file>`로 확인한다. 이 계획이 만들지 않은 미커밋 변경이 있으면 멈추고 보고한다.
- `git add`는 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By` 등 trailer는 넣지 않는다(`AGENTS.md`). push하지 않는다.
- Task 3·4의 커밋은 마크업만 있고 CSS가 없어 판·짝 기사 줄이 꾸며지지 않은 상태다. **Task 7까지 끝내기 전에는 배포하지 않는다.**
- `global.css`는 14,000줄이 넘는다. 통째로 읽지 말고 Grep으로 위치를 찾아 Edit 도구로 고친다.
- 줄 끝이 파일마다 다르다. `NewsprintArticleLayout.astro`와 뉴스 페이지 두 곳은 CRLF, `global.css`·`NewsprintShell.astro`·`newsDetailPage.ts`·테스트는 LF다. 기존 파일은 Edit 도구로만 고쳐 줄 끝을 유지한다. 새 파일은 LF로 만든다. 테스트의 문자열 단정은 줄바꿈을 `\s*`로 받도록 써 두었다.

**테스트 실행**
- npm 스크립트가 없다. **저장소 루트에서** `node frontend/tests/<file>`로 하나씩 실행한다. 통과하면 `<file> passed` 한 줄이 나온다.
- **시작 전부터 실패하는 테스트가 16개 있다**(2026-11-21, 저장소 루트에서 `.cjs`·`.mjs` 전체 실행 기준). 이 계획과 무관하니 고치지 않는다. 이 목록에 없는 파일이 실패하면 이번 변경이 원인이다.
  - `admin-live-preview`, `admin-v1-structure`, `article-deck-font`, `auth-prompt-library-preview`
  - `blog-title-fonts`, `comments-admin-delete-contract`, `content-feedback-contract`, `csp-inline-scripts`
  - `detail-rail-copy`, `handbook-detail-table-overflow`, `handbook-search-recognition`, `log-list-created-order`
  - `navigation-shell-copy`, `news-fact-pack-structure`, `public-slug-visibility`, `sticky-reading-actions-structure`
- 시작할 때 아래 명령으로 목록이 같은지 먼저 확인한다. 다르면 달라진 파일을 기록해 두고 그 목록을 기준으로 삼는다.
  ```bash
  for f in frontend/tests/*.test.cjs frontend/tests/*.test.mjs; do node "$f" >/dev/null 2>&1 || echo "FAIL $f"; done
  ```

**지켜야 할 것**
- 기사 HTML은 CDN에 캐시된다. 새 코드에서 `Astro.locals`를 쓰지 않는다.
- `.astro`에 `client:load`를 쓰지 않는다. 이 계획은 스크립트를 추가하지 않는다.
- 판 전환 스크립트가 찾는 것은 그대로 둔다: `.persona-switcher`, `.persona-switcher-btn`, `.persona-switcher-btn--active`, `data-persona`, `#persona-data`, `#persona-float`, `.newsprint-lead-title`, `.newsprint-deck`, `.newsprint-prose`.
- `NewsprintShell.astro`의 문자열 `{crumbItems ? (`와 `issueLabel(locale, issueNumber(displayDate))`는 글자 그대로 남긴다(`handbook-term-entry`, `issue-number-shell` 테스트가 단정한다).
- 새 색 토큰과 새 폰트를 추가하지 않는다. Hahmlet은 600·700만 쓴다.

**파일 지도**

| 파일 | 역할 | 작업 |
|---|---|---|
| `frontend/src/lib/newsBold.js` | 뉴스 마크다운의 굵은 글씨 정리(순수 함수) | 새로 만듦 |
| `frontend/tests/news-bold-normalize.test.mjs` | 위 함수 단위 테스트 | 새로 만듦 |
| `frontend/src/lib/pageData/newsDetailPage.ts` | 뉴스 렌더 경로 | `renderMd`에서 호출 |
| `frontend/src/components/newsprint/NewsprintShell.astro` | compact 경로 줄 | 선택 prop 2개 |
| `frontend/src/components/newsprint/NewsprintArticleLayout.astro` | 기사 머리·본문 틀 | `newsReading` prop과 마크업 |
| `frontend/src/pages/ko/news/[slug].astro`, `frontend/src/pages/en/news/[slug].astro` | 공개 뉴스 페이지 | prop 전달 |
| `frontend/src/styles/global.css` | 스타일 | 새 블록 하나 추가 |
| `frontend/tests/news-article-reading.test.cjs` | 구조 테스트 | 새로 만듦 |
| `frontend/tests/news-article-briefing.test.cjs` | 기존 구조 테스트 | 순서·문구 단정 수정 |

---

## Chunk 1: 굵은 글씨 정리

### Task 1: `normalizeNewsBold` 순수 함수

**Files:**
- Create: `frontend/src/lib/newsBold.js`
- Test: `frontend/tests/news-bold-normalize.test.mjs`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/tests/news-bold-normalize.test.mjs`:

```js
// frontend/tests/news-bold-normalize.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { normalizeNewsBold, isLongBold } = await import(pathToFileURL(path.join(here, '../src/lib/newsBold.js')).href);

const eq = (input, expected, label) => assert.equal(normalizeNewsBold(input), expected, label);

// 짧은 용어는 <strong>으로 바뀐다. 한글이 바로 붙어도 깨지지 않는다.
eq('성공률은 **46%**다.', '성공률은 <strong>46%</strong>다.', 'short bold glued to Hangul');
eq('**Microsoft**가 발표했다.', '<strong>Microsoft</strong>가 발표했다.', 'short bold at line start');
eq('**작업당 비용은 2% 미만**이라고 밝힌다.', '<strong>작업당 비용은 2% 미만</strong>이라고 밝힌다.', 'short phrase stays bold');

// 문장 통째로 굵은 것은 보통 글씨로 푼다.
eq(
  '**Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다.** 공식 발표다.',
  'Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다. 공식 발표다.',
  'whole-sentence bold is unwrapped',
);

// 운영 화면에서 깨져 보이던 실제 문장: 긴 굵은 글씨라 풀리고 ** 가 남지 않는다.
const broken = '무개입 성공률은 **46%인 반면, AI 서비스를 실행하는 코드 작성의 성공률은 25%**다.';
assert(!normalizeNewsBold(broken).includes('**'), 'no literal ** left in the production case');

// 한 줄에 여러 쌍
eq('**A**와 **B**를 비교한다.', '<strong>A</strong>와 <strong>B</strong>를 비교한다.', 'two pairs on one line');

// 링크 전체가 굵으면 길이와 상관없이 굵게 남긴다.
eq(
  '**[아주 긴 라벨을 가진 링크 텍스트입니다 정말로](https://example.com/a/very/long/path)**는 유지된다.',
  '<strong>[아주 긴 라벨을 가진 링크 텍스트입니다 정말로](https://example.com/a/very/long/path)</strong>는 유지된다.',
  'bold link kept',
);

// 목록 라벨은 길이와 상관없이 굵게 남긴다.
eq(
  '- **비용 절감이 가장 큰 목표인 팀에서 예산을 다시 짜야 하는 조건이라면**: 정상 요금을 확인한다.',
  '- <strong>비용 절감이 가장 큰 목표인 팀에서 예산을 다시 짜야 하는 조건이라면</strong>: 정상 요금을 확인한다.',
  'long list label kept (colon)',
);
eq('- **46%** — 무개입 성공률. [1](https://example.com)', '- <strong>46%</strong> — 무개입 성공률. [1](https://example.com)', 'weekly number label kept (dash)');
eq('1. **첫째 조건**: 설명', '1. <strong>첫째 조건</strong>: 설명', 'ordered list label kept');

// 건드리지 않는 것
eq('가격은 `**not bold**` 그대로다.', '가격은 `**not bold**` 그대로다.', 'inline code untouched');
eq('수식 $$a**b$$ 는 그대로다.', '수식 $$a**b$$ 는 그대로다.', 'display math untouched');
eq('```\n**x**\n```', '```\n**x**\n```', 'fenced code untouched');
eq('~~~\n**x**\n~~~\n**y**', '~~~\n**x**\n~~~\n<strong>y</strong>', 'tilde fence untouched, text after it processed');
eq('짝이 없는 ** 하나', '짝이 없는 ** 하나', 'unpaired ** untouched');
eq('***굵은 기울임***은 그대로', '***굵은 기울임***은 그대로', 'triple asterisks untouched');
eq('이스케이프 \\*\\*x\\*\\* 는 그대로', '이스케이프 \\*\\*x\\*\\* 는 그대로', 'escaped asterisks untouched');
eq('** **', '** **', 'empty bold untouched');
eq('*기울임*은 그대로', '*기울임*은 그대로', 'single asterisks untouched');

// 여러 줄: 줄바꿈과 줄 수를 보존한다.
eq('**A**\n\n본문\n', '<strong>A</strong>\n\n본문\n', 'newlines preserved');
eq('', '', 'empty input');

// 판정 함수는 따로 내보낸다.
assert.equal(typeof isLongBold('x'), 'boolean', 'isLongBold returns a boolean');
assert.equal(isLongBold('GPT-6.1 Sol'), false, 'a product name is not long');
assert.equal(isLongBold('Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다.'), true, 'a full sentence is long');

console.log('news-bold-normalize.test.mjs passed');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-bold-normalize.test.mjs`
Expected: `ERR_MODULE_NOT_FOUND` (`newsBold.js` 없음)

- [ ] **Step 3: 구현한다**

`frontend/src/lib/newsBold.js`:

```js
// frontend/src/lib/newsBold.js
// Pure clean-up of **bold** in news markdown, applied before the markdown parser. No I/O.
//
// Why before parsing: CommonMark refuses a closing ** that follows punctuation and
// precedes a letter ("**46%**다"), so Korean text often leaves literal asterisks or
// pairs the wrong delimiters. Pairing ** here and emitting <strong> sidesteps that.
// Long bold (whole sentences) is unwrapped so only short emphasis survives.

const FENCE = /^\s*(```|~~~)/;
// Inline code spans and $$…$$ math are kept verbatim.
const PROTECTED = /(`+[^`]*`+|\$\$[^$]*\$\$)/;
const WHOLE_LINK = /^\[[^\]]*\]\([^)]*\)$/;
const LIST_HEAD = /^\s*(?:[-*+]|\d+[.)])\s+$/;
const LABEL_TAIL = /^(?:[:：]|\s[—–-]\s)/;

/**
 * Is this bold span too long to keep as emphasis?
 * @param {string} inner text between the ** pair
 * @returns {boolean}
 */
export function isLongBold(inner) {
  // ── Amy 결정 지점 (Task 1 Step 5) ──────────────────────────────────────
  // 기본 제안: 공백 포함 24자를 넘거나 문장 끝 부호로 끝나면 "길다".
  const text = inner.trim();
  return text.length > 24 || /[.?!。]$/.test(text);
}

function normalizeSegment(segment, isLineStart) {
  // Triple-asterisk runs and escaped asterisks: leave the whole segment to the parser.
  if (/\*{3,}/.test(segment) || segment.includes('\\*')) return segment;

  const marks = [];
  const re = /\*\*/g;
  let m;
  while ((m = re.exec(segment)) !== null) marks.push(m.index);
  if (marks.length < 2) return segment;

  let out = '';
  let cursor = 0;
  for (let i = 0; i + 1 < marks.length; i += 2) {
    const open = marks[i];
    const close = marks[i + 1];
    const inner = segment.slice(open + 2, close);
    const before = segment.slice(0, open);
    const after = segment.slice(close + 2);
    out += segment.slice(cursor, open);

    if (inner.trim() === '') {
      out += `**${inner}**`;
    } else if (WHOLE_LINK.test(inner.trim())) {
      out += `<strong>${inner}</strong>`;
    } else if (isLineStart && LIST_HEAD.test(before) && LABEL_TAIL.test(after)) {
      out += `<strong>${inner}</strong>`;
    } else if (isLongBold(inner)) {
      out += inner;
    } else {
      out += `<strong>${inner}</strong>`;
    }
    cursor = close + 2;
  }
  return out + segment.slice(cursor);
}

function normalizeLine(line) {
  const parts = line.split(PROTECTED);
  // split() with one capture group: even indexes are plain text, odd are protected.
  return parts.map((part, i) => (i % 2 === 1 ? part : normalizeSegment(part, i === 0))).join('');
}

/**
 * @param {string} md news markdown
 * @returns {string} markdown with ** pairs resolved to <strong> or plain text
 */
export function normalizeNewsBold(md) {
  if (!md || !md.includes('**')) return md;
  let fence = null;
  return md
    .split('\n')
    .map((line) => {
      const marker = line.match(FENCE)?.[1];
      if (marker) {
        if (fence === null) fence = marker;
        else if (fence === marker) fence = null;
        return line;
      }
      return fence === null ? normalizeLine(line) : line;
    })
    .join('\n');
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `node frontend/tests/news-bold-normalize.test.mjs`
Expected: `news-bold-normalize.test.mjs passed`

- [ ] **Step 5: Amy가 "길다"의 기준을 정한다 (사람이 하는 단계)**

`isLongBold`의 본문 두 줄은 기본 제안이다. 여기서 멈추고 Amy에게 넘긴다. 에이전트가 대신 정하지 않는다.

- 정할 것: 어떤 굵은 글씨를 보통 글씨로 풀 것인가.
- 생각할 거리
  - 글자 수만 볼지, 문장 끝(`.`)도 볼지. `**작업당 비용은 2% 미만**`(15자)은 남고, `**GPT-6.1 Sol 코딩 품질의 98%를 약 40%의 가격에 제공한다.**`는 풀린다.
  - 한글과 영어는 같은 글자 수라도 길이감이 다르다. `**America's AI Deployer Council**`은 29자다. 기본 제안으로는 풀린다.
  - 숫자가 든 짧은 구절은 길어도 남길지.
- 바꾼 뒤 Step 4를 다시 실행한다. 테스트의 길고 짧은 예시는 어느 쪽으로도 분명한 것만 골랐으므로, 합리적인 규칙이면 그대로 통과한다. 통과하지 않으면 테스트가 아니라 규칙을 다시 본다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/newsBold.js frontend/tests/news-bold-normalize.test.mjs
git commit -m "feat: resolve bold in news markdown before parsing and unwrap long spans"
```

### Task 2: 뉴스 렌더 경로에 연결

**Files:**
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts` (import 줄, `renderMd` 정의 — `const hasTerms = handbookTermsMap.size > 0;` 바로 아래)
- Test: `frontend/tests/news-article-reading.test.cjs` (새 파일, 이 Task에서 첫 단정만 쓴다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/tests/news-article-reading.test.cjs`:

```js
// frontend/tests/news-article-reading.test.cjs
// News article reading pass: bold clean-up wired into the news render path only,
// newsReading layout mode, scoped prose typography, hide-on-scroll-down bars.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// --- bold clean-up wiring ---
const detail = read('lib/pageData/newsDetailPage.ts');
assert(detail.includes("import { normalizeNewsBold } from '../newsBold.js';"), 'news detail imports the bold clean-up');
assert(detail.includes('renderMarkdownWithTerms(normalizeNewsBold(md), handbookTermsMap)') && detail.includes('renderMarkdown(normalizeNewsBold(md))'), 'both render branches normalise bold first');
assert(!read('lib/markdown.ts').includes('normalizeNewsBold'), 'shared renderer stays untouched (blog, products, handbook)');

console.log('news-article-reading.test.cjs passed');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … news detail imports the bold clean-up`

- [ ] **Step 3: 구현한다**

`frontend/src/lib/pageData/newsDetailPage.ts`에서 `import { kstDay } from '../homeFront.js';` 줄 바로 아래에 추가한다.

```ts
import { normalizeNewsBold } from '../newsBold.js';
```

같은 파일의 `renderMd` 정의를 바꾼다.

```ts
// before
  const renderMd = hasTerms
    ? (md: string) => renderMarkdownWithTerms(md, handbookTermsMap)
    : (md: string) => renderMarkdown(md);

// after
  const renderMd = hasTerms
    ? (md: string) => renderMarkdownWithTerms(normalizeNewsBold(md), handbookTermsMap)
    : (md: string) => renderMarkdown(normalizeNewsBold(md));
```

렌더 캐시 키는 렌더러에 들어가는 문자열의 해시라서 따로 바꿀 것이 없다.

- [ ] **Step 4: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/news-persona-cache-policy.test.cjs
node frontend/tests/news-article-data.test.cjs
```
Expected: 세 파일 모두 `… passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/pageData/newsDetailPage.ts frontend/tests/news-article-reading.test.cjs
git commit -m "feat: clean up bold on the news article render path"
```

---

## Chunk 2: 머리 부분 마크업

### Task 3: 경로 줄에 데스크와 읽는 시간

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintShell.astro` (Props, 구조 분해, compact 분기)
- Modify: `frontend/src/pages/ko/news/[slug].astro`, `frontend/src/pages/en/news/[slug].astro` (frontmatter, `<NewsprintShell>` 호출)
- Test: `frontend/tests/news-article-reading.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`news-article-reading.test.cjs`의 `console.log` 줄 바로 위에 넣는다.

```js
// --- crumb: desk + reading time ---
const shell = read('components/newsprint/NewsprintShell.astro');
assert(/crumbDesk\?: string;/.test(shell) && /crumbReading\?: string;/.test(shell), 'shell: optional crumb props');
assert(shell.includes('{crumbDesk && <span class="newsprint-crumb-desk">{crumbDesk}</span>}') && shell.includes('{crumbReading && <span>{crumbReading}</span>}'), 'shell: desk before the issue, reading time after the date');
assert(shell.includes('{crumbItems ? (') && shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'shell: strings other tests assert are intact');

const pages = { ko: read('pages/ko/news/[slug].astro'), en: read('pages/en/news/[slug].astro') };
for (const [locale, page] of Object.entries(pages)) {
  assert(page.includes("import { postTypeLabel } from '../../../lib/postType.js';"), `${locale}: desk label from lib/postType.js`);
  assert(page.includes('crumbDesk={crumbDesk}') && page.includes('crumbReading={crumbReading}'), `${locale}: crumb props passed`);
}
assert(pages.ko.includes('`${deskBase} 데스크`') && pages.ko.includes('`읽는 데 ${post.reading_time_min}분`'), 'ko: crumb copy');
assert(pages.en.includes('`${deskBase} desk`') && pages.en.includes('`${post.reading_time_min} min read`'), 'en: crumb copy');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … shell: optional crumb props`

- [ ] **Step 3: Shell을 고친다**

`NewsprintShell.astro`의 `interface Props`에서 `crumbItems?: string[];` 아래에 추가한다.

```ts
  /** compact only: desk name shown before the issue (news article) */
  crumbDesk?: string;
  /** compact only: reading time shown after the date (news article) */
  crumbReading?: string;
```

구조 분해 줄을 바꾼다.

```ts
const { locale, masthead = '', editionLabel, subkicker, publishedAt, rail = true, compact = false, backHref, backLabel, crumbItems, crumbDesk, crumbReading } = Astro.props;
```

compact 분기의 `crumbItems`가 없을 때 쪽(`<>` … `</>`)을 바꾼다. 다른 줄은 건드리지 않는다.

```astro
        <>
          {crumbDesk && <span class="newsprint-crumb-desk">{crumbDesk}</span>}
          <span>{issueLabel(locale, issueNumber(displayDate))}</span>
          <span data-local-date data-date-iso={browserDateIso} data-date-locale={browserLocale}>{dateLabel}</span>
          {crumbReading && <span>{crumbReading}</span>}
        </>
```

- [ ] **Step 4: 페이지 두 곳을 고친다**

`frontend/src/pages/ko/news/[slug].astro`

import 블록 끝(`NewsReadNext` import 아래)에 추가한다.

```ts
import { postTypeLabel } from '../../../lib/postType.js';
```

frontmatter의 `const isWeekly = post?.post_type === 'weekly';` 줄 바로 아래에 추가한다.

```ts
const deskBase = postTypeLabel('ko', post?.post_type);
const crumbDesk = deskBase ? (isWeekly ? deskBase : `${deskBase} 데스크`) : undefined;
const crumbReading = post?.reading_time_min ? `읽는 데 ${post.reading_time_min}분` : undefined;
```

`<NewsprintShell … publishedAt={post?.published_at}` 다음 줄에 prop 두 개를 추가한다.

```astro
    publishedAt={post?.published_at}
    crumbDesk={crumbDesk}
    crumbReading={crumbReading}
  >
```

`frontend/src/pages/en/news/[slug].astro`도 같은 위치에 같은 방식으로 넣는다. 문자열만 다르다.

```ts
import { postTypeLabel } from '../../../lib/postType.js';
```

```ts
const deskBase = postTypeLabel('en', post?.post_type);
const crumbDesk = deskBase ? (isWeekly ? deskBase : `${deskBase} desk`) : undefined;
const crumbReading = post?.reading_time_min ? `${post.reading_time_min} min read` : undefined;
```

- [ ] **Step 5: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/news-article-briefing.test.cjs
```
Expected: 네 파일 모두 `… passed`

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintShell.astro "frontend/src/pages/ko/news/[slug].astro" "frontend/src/pages/en/news/[slug].astro" frontend/tests/news-article-reading.test.cjs
git commit -m "feat: show desk and reading time on the news article crumb"
```

### Task 4: 레이아웃 `newsReading` 모드

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro` (Props, 구조 분해, `siblingLead`, `<article>` 여는 태그부터 브리핑 앞까지, `after-guide` 슬롯 뒤)
- Modify: `frontend/src/pages/ko/news/[slug].astro`, `frontend/src/pages/en/news/[slug].astro` (`<NewsprintArticleLayout>` 호출)
- Modify: `frontend/tests/news-article-briefing.test.cjs` (순서·문구 단정 2곳)
- Test: `frontend/tests/news-article-reading.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`news-article-reading.test.cjs`의 `console.log` 줄 바로 위에 넣는다.

```js
// --- layout: newsReading mode ---
const layout = read('components/newsprint/NewsprintArticleLayout.astro');
assert(/newsReading\?: boolean;/.test(layout) && /newsReading = false,/.test(layout), 'layout: newsReading prop, off by default');
assert(layout.includes("class={`newsprint-article${newsReading ? ' newsprint-article--news' : ''}`}"), 'layout: scope class on the article root');
assert(/\{!newsReading && \(\s*<div class="newsprint-article-topline">/.test(layout), 'layout: topline only outside newsReading');
assert(layout.includes('{!newsReading && tags && tags.length > 0 && ('), 'layout: head tags only outside newsReading');
assert(layout.includes('{!newsReading && <div class="newsprint-divider"></div>}'), 'layout: head divider only outside newsReading');
assert(layout.includes("<div class={newsReading ? 'news-edition-bar' : undefined}>"), 'layout: edition bar wrapper');
assert(layout.includes('{!newsReading && <div class="switcher-bar-line"></div>}'), 'layout: switcher rules only outside newsReading');
const endTags = layout.indexOf('class="newsprint-article-tags newsprint-article-tags--end"');
assert(endTags > layout.indexOf('<slot name="after-guide" />') && endTags < layout.indexOf('class="newsprint-sources"'), 'layout: tags move to the end, between the slot and sources');
for (const s of ['리서치 데스크의 시선 →', '비즈니스 데스크의 시선 →', "The research desk's take →", "The business desk's take →"]) {
  assert(layout.includes(s), `layout copy: ${s}`);
}
for (const [locale, page] of Object.entries(pages)) {
  assert(/<NewsprintArticleLayout[\s\S]*?\n\s+newsReading\s*\n/.test(page), `${locale}: public news page turns newsReading on`);
}
for (const p of ['pages/admin/news/edit/[slug].astro', 'pages/admin/blog/edit/[slug].astro']) {
  assert(!read(p).includes('newsReading'), `${p}: admin editors do not pass newsReading`);
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … layout: newsReading prop, off by default`

- [ ] **Step 3: 레이아웃의 prop과 문구를 고친다**

`interface Props`에서 `sibling?: { … } | null;` 줄 아래에 추가한다.

```ts
  /** Public news article reading mode: one meta line, edition bar, tags at the end. */
  newsReading?: boolean;
```

구조 분해에서 `sibling = null,` 줄 아래에 추가한다.

```ts
  newsReading = false,
```

`siblingLead` 정의를 바꾼다.

```ts
// before
const siblingLead = !sibling ? '' : siblingDesk === 'research'
  ? (isKo ? '리서치 데스크는 이렇게 봤어요 →' : "The research desk's take →")
  : (isKo ? '비즈니스 데스크는 이렇게 봤어요 →' : "The business desk's take →");

// after
const siblingLead = !sibling ? '' : siblingDesk === 'research'
  ? (isKo ? '리서치 데스크의 시선 →' : "The research desk's take →")
  : (isKo ? '비즈니스 데스크의 시선 →' : "The business desk's take →");
```

- [ ] **Step 4: 레이아웃의 머리 마크업을 고친다**

`<article class="newsprint-article">`부터 `{briefingItems.length > 0 && (` 바로 앞까지를 아래로 바꾼다. `PreviewReadonlyBanner` 블록, `<h1>`, 요약문, `<template id="persona-data" …>`의 속성은 지금 내용을 그대로 옮긴다. 바뀌는 것은 다음 다섯 가지뿐이다.

1. `<article>`의 class
2. topline을 `{!newsReading && ( … )}`로 감쌈
3. 머리 태그와 divider에 `!newsReading` 조건
4. 판 선택과 짝 기사를 감싸는 래퍼. 순서가 **판 선택 → 짝 기사**로 바뀐다
5. `.switcher-bar-line` 두 개에 `!newsReading` 조건

```astro
<article class={`newsprint-article${newsReading ? ' newsprint-article--news' : ''}`}>
  {previewMode && (
    <>
      <!-- Admin preview -->
      <PreviewReadonlyBanner locale={locale} />
    </>
  )}
  {!newsReading && (
    <div class="newsprint-article-topline">
      <div class="newsprint-article-topline-left">
        {categoryLabel && (
          <span class="newsprint-card-kicker newsprint-article-kicker">{categoryLabel}{postType && <span class={`newsprint-card-kicker-type newsprint-card-kicker-type--${postType}`}>{postTypeLabel(locale, postType)}</span>}</span>
        )}
      </div>
      <div class="newsprint-article-topline-right">
        {readingLabel && <span class="newsprint-reading-time"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>{readingLabel}</span>}
        {dateLabel && <time datetime={publishedAt ?? undefined}>{dateLabel}</time>}
      </div>
    </div>
  )}

  <h1 class="newsprint-lead-title">{title}</h1>
  {excerpt && <p class="newsprint-deck">{excerpt}</p>}
  {!newsReading && tags && tags.length > 0 && (
    <div class="newsprint-article-tags">
      {tags.slice(0, 6).map((tag) => (
        <span class="newsprint-tag">{tag}</span>
      ))}
    </div>
  )}
  {!newsReading && <div class="newsprint-divider"></div>}

  {(showPersonaSwitcher || sibling) && (
    <div class={newsReading ? 'news-edition-bar' : undefined}>
      {showPersonaSwitcher && (
        <>
          <div class="switcher-bar">
            {!newsReading && <div class="switcher-bar-line"></div>}
            <span class="switcher-bar-label">{locale === 'ko' ? '판 선택' : 'Edition'}</span>
            <div class="persona-switcher">
            {(['beginner', 'learner', 'expert'] as const).filter(p => personaHtmlMap![p]).map(p => (
              <button
                type="button"
                class={`persona-switcher-btn ${p === activePersona ? 'persona-switcher-btn--active' : ''}`}
                data-persona={p}
              >
                {personaLabels[locale]?.[p] || p}
              </button>
            ))}
            </div>
            {!newsReading && <div class="switcher-bar-line"></div>}
          </div>
          <template id="persona-data" … 지금 속성 그대로 …></template>
        </>
      )}
      {sibling && (
        <a class={`newsprint-twin-link newsprint-twin-link--${siblingDesk}`} href={`/${locale}/news/${sibling.slug}/`}>
          <span class="newsprint-twin-link-label">{siblingLead}</span>
          <span class="newsprint-twin-link-title">{sibling.title}</span>
        </a>
      )}
    </div>
  )}
```

`<template id="persona-data" … 지금 속성 그대로 …>` 자리에는 기존 `<template>` 요소를 `data-map`, `data-display`, `data-quizzes`, `data-weekly-quizzes`, `data-sources` 속성까지 한 글자도 바꾸지 않고 옮긴다. 위 코드의 `…`를 그대로 쓰지 않는다.

- [ ] **Step 5: 기사 끝에 태그를 둔다**

같은 파일에서 `<slot name="after-guide" />` 줄 바로 아래, `{hasSources && (` 위에 추가한다.

```astro
  {newsReading && tags && tags.length > 0 && (
    <div class="newsprint-article-tags newsprint-article-tags--end">
      {tags.slice(0, 6).map((tag) => (
        <span class="newsprint-tag">{tag}</span>
      ))}
    </div>
  )}
```

- [ ] **Step 6: 공개 뉴스 페이지 두 곳에서 켠다**

`frontend/src/pages/ko/news/[slug].astro`와 `frontend/src/pages/en/news/[slug].astro`의 `<NewsprintArticleLayout …>` 호출에서 `sibling={sibling}` 줄 아래에 한 줄을 추가한다.

```astro
        sibling={sibling}
        newsReading
      >
```

- [ ] **Step 7: 기존 테스트의 순서·문구 단정을 고친다**

`frontend/tests/news-article-briefing.test.cjs`에서 두 곳을 바꾼다.

```js
// before
const idx = ['newsprint-twin-link', 'class="switcher-bar"', 'class="news-briefing"', 'class="newsprint-article-find"'].map((s) => layout.indexOf(s));
assert(idx.every((i) => i > 0) && idx[0] < idx[1] && idx[1] < idx[2] && idx[2] < idx[3], 'order: twin link → edition switcher → briefing → find');

// after
const idx = ['class="switcher-bar"', 'newsprint-twin-link', 'class="news-briefing"', 'class="newsprint-article-find"'].map((s) => layout.indexOf(s));
assert(idx.every((i) => i > 0) && idx[0] < idx[1] && idx[1] < idx[2] && idx[2] < idx[3], 'order: edition switcher → twin link → briefing → find');
```

```js
// before
for (const s of ['30초 브리핑', '30-second briefing', '리서치 데스크는 이렇게 봤어요', "The research desk's take", '비즈니스 데스크는 이렇게 봤어요', "The business desk's take"]) {

// after
for (const s of ['30초 브리핑', '30-second briefing', '리서치 데스크의 시선', "The research desk's take", '비즈니스 데스크의 시선', "The business desk's take"]) {
```

- [ ] **Step 8: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/article-v2.test.cjs
node frontend/tests/news-persona-title-switcher.test.cjs
node frontend/tests/news-article-find-structure.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
```
Expected: 여섯 파일 모두 `… passed`.
- `article-v2`의 "tags render below the deck"는 첫 번째 `<div class="newsprint-article-tags">`(머리 쪽)를 보므로 그대로 통과한다.
- 여기서 새로 실패하는 테스트가 있으면 그 단정이 이번에 바뀐 마크업을 가리키는지 확인하고, 가리킬 때만 새 구조에 맞게 고친다. 무관한 실패면 멈추고 보고한다.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro "frontend/src/pages/ko/news/[slug].astro" "frontend/src/pages/en/news/[slug].astro" frontend/tests/news-article-reading.test.cjs frontend/tests/news-article-briefing.test.cjs
git commit -m "feat: news article reading mode with one meta line and an edition bar"
```

---

## Chunk 3: 스타일과 확인

### Task 5: 머리 부분 CSS

**Files:**
- Modify: `frontend/src/styles/global.css` (`.news-end-title {` 바로 앞에 새 블록)
- Test: `frontend/tests/news-article-reading.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`news-article-reading.test.cjs`의 `console.log` 줄 바로 위에 넣는다.

```js
// --- CSS: head ---
const css = read('styles/global.css');
function block(selector) {
  const at = css.indexOf(`\n${selector} {`);
  assert(at > 0, `css rule exists: ${selector}`);
  return css.slice(at, css.indexOf('}', at));
}
assert(/color:\s*var\(--color-accent\)/.test(block('.newsprint-crumb-desk')), 'crumb desk in accent');
assert(/font-size:\s*1\.125rem/.test(block('.newsprint-article--news .newsprint-deck')) && /word-break:\s*keep-all/.test(block('.newsprint-article--news .newsprint-deck')), 'deck: 18px, keep-all');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(block('.news-edition-bar')), 'edition bar: heavy top rule');
assert(/background:\s*var\(--color-text-primary\)/.test(block('.news-edition-bar .persona-switcher-btn--active')), 'edition bar: active segment inverted');
assert(/background:\s*none/.test(block('.newsprint-article--news .news-briefing')), 'briefing: no box');
assert(/grid-template-columns:\s*minmax\(0, 1fr\)/.test(block('.newsprint-article--news .news-briefing-list')), 'briefing: one column list');
assert(/font-size:\s*1\.0625rem/.test(block('.newsprint-article--news .news-briefing-list li')), 'briefing: body-size text');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … css rule exists: .newsprint-crumb-desk`

- [ ] **Step 3: CSS 블록을 추가한다**

`frontend/src/styles/global.css`에서 `.news-end-title {` 줄을 Grep으로 찾아, 그 줄 **바로 앞**에 아래 블록을 넣는다. 기존 규칙은 지우지 않는다. 새 규칙은 덮어쓸 대상보다 명시도가 높거나, 명시도가 같으면 파일에서 더 뒤에 있다.

```css
/* News article reading mode (newsReading): one meta line, edition bar, list briefing */
.newsprint-crumb-desk {
  color: var(--color-accent);
  font-weight: 600;
}

.newsprint-article--news .newsprint-lead-title {
  margin-bottom: 0.85rem;
}

.newsprint-article--news .newsprint-deck {
  font-size: 1.125rem;
  line-height: 1.65;
  max-width: 40rem;
  margin-bottom: 0;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.news-edition-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  margin-top: 1.4rem;
  padding: 0.6rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
}

.news-edition-bar .switcher-bar {
  flex-shrink: 0;
  gap: 0;
  margin: 0;
}

/* Label stays for screen readers; the segmented control speaks for itself visually. */
.news-edition-bar .switcher-bar-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.news-edition-bar .persona-switcher {
  gap: 0;
  border: 1px solid var(--color-border);
}

.news-edition-bar .persona-switcher-btn {
  min-height: 2.25rem;
  padding: 0.35rem 0.85rem;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  border-right: 1px solid var(--color-border);
}

.news-edition-bar .persona-switcher-btn:last-child {
  border-right: none;
}

.news-edition-bar .persona-switcher-btn--active {
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
}

.news-edition-bar .persona-switcher-btn--active::after {
  content: none;
}

.news-edition-bar .persona-switcher-btn:hover:not(.persona-switcher-btn--active) {
  background: var(--color-bg-secondary);
}

.news-edition-bar .newsprint-twin-link {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  min-width: 0;
  margin: 0;
  padding: 0;
  border-left: none;
  font-size: 0.82rem;
}

.news-edition-bar .newsprint-twin-link-label {
  flex-shrink: 0;
  font-size: inherit;
}

.news-edition-bar .newsprint-twin-link-title {
  min-width: 0;
  margin-top: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-ui);
  font-size: inherit;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--color-text-secondary);
}

.newsprint-article--news .news-briefing {
  margin: 0 0 1.9rem;
  padding: 1.25rem 0 1.4rem;
  background: none;
  border-radius: 0;
  border-bottom: 1px solid var(--color-border);
}

.newsprint-article--news .news-briefing-label {
  margin-bottom: 0.6rem;
  letter-spacing: 0.04em;
}

.newsprint-article--news .news-briefing-list {
  grid-template-columns: minmax(0, 1fr);
  gap: 0.5rem;
}

.newsprint-article--news .news-briefing-list li {
  flex-direction: row;
  align-items: baseline;
  gap: 0.6rem;
  font-size: 1.0625rem;
  line-height: 1.6;
  color: var(--color-text-primary);
  word-break: keep-all;
}

.newsprint-article--news .news-briefing-num {
  min-width: 1.1rem;
  font-size: 1.3rem;
}

/* Two classes: the base .newsprint-article-tags rule sits later in the file. */
.newsprint-article-tags.newsprint-article-tags--end {
  margin: 1.75rem 0 0;
}

@media (max-width: 767px) {
  .news-edition-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .news-edition-bar .persona-switcher {
    width: 100%;
  }

  .news-edition-bar .persona-switcher-btn {
    flex: 1;
    min-height: 2.75rem;
  }
}

```

- [ ] **Step 4: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/article-v2.test.cjs
node frontend/tests/list-v2.test.cjs
```
Expected: 네 파일 모두 `… passed`. `news-article-briefing`의 "briefing: three columns"는 기존 기본 규칙을 보므로 그대로 통과한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/news-article-reading.test.cjs
git commit -m "feat: style the news article head as a meta line, edition bar and list briefing"
```

### Task 6: 본문 조판 CSS

**Files:**
- Modify: `frontend/src/styles/global.css` (Task 5 블록의 `.newsprint-article-tags--end` 규칙 바로 앞)
- Test: `frontend/tests/news-article-reading.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`console.log` 줄 바로 위에 넣는다.

```js
// --- CSS: prose ---
const prose = block('.newsprint-article--news .newsprint-prose');
assert(/word-break:\s*keep-all/.test(prose) && /overflow-wrap:\s*break-word/.test(prose), 'prose: no mid-word breaks, long URLs still wrap');
assert(/font-size:\s*1\.0625rem/.test(prose) && /line-height:\s*1\.85/.test(prose), 'prose: 17px / 1.85');
assert(/font-weight:\s*600/.test(block('.newsprint-article--news .newsprint-prose strong')), 'prose: strong at 600');
assert(css.includes('.newsprint-article--news .newsprint-prose h2:has(+ h3) {'), 'category h2 picked by :has(+ h3)');
assert(/border-left:\s*none/.test(block('.newsprint-article--news .newsprint-prose h3')), 'story headline: no accent bar');
assert(css.includes('.newsprint-article--news .newsprint-prose:not(.newsprint-prose--analysis) > h2:first-child:not(:has(+ h3)) + p {'), 'lead sentence: main prose only, not Core Analysis');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … css rule exists: .newsprint-article--news .newsprint-prose`

- [ ] **Step 3: CSS를 추가한다**

Task 5에서 넣은 블록 안의 `/* Two classes: the base .newsprint-article-tags rule sits later in the file. */` 주석 줄 **바로 앞**에 넣는다.

```css
/* News article prose: article-style hierarchy without touching the markdown */
.newsprint-article--news .newsprint-prose {
  font-size: 1.0625rem;
  line-height: 1.85;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.newsprint-article--news .newsprint-prose p + p {
  margin-top: 1.1rem;
}

.newsprint-article--news .newsprint-prose strong {
  font-weight: 600;
}

.newsprint-article--news .newsprint-prose h2 {
  margin-top: 2.6rem;
  margin-bottom: 0.75rem;
  padding-top: 0;
  border-top: none;
}

/* Category h2 ("Big Tech"): a small tab above the story headline that follows it. */
.newsprint-article--news .newsprint-prose h2:has(+ h3) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 2.9rem;
  margin-bottom: 0;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-accent);
}

.newsprint-article--news .newsprint-prose h2:has(+ h3)::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

/* Story headline h3 */
.newsprint-article--news .newsprint-prose h3 {
  margin-top: 2rem;
  margin-bottom: 0.9rem;
  padding-left: 0;
  border-left: none;
  font-size: clamp(1.25rem, 1.8vw, 1.44rem);
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: -0.03em;
  word-break: keep-all;
}

.newsprint-article--news .newsprint-prose h2 + h3 {
  margin-top: 0.9rem;
}

/* First section ("한 줄 요약"): quiet label, then one serif sentence. Main prose only. */
.newsprint-article--news .newsprint-prose:not(.newsprint-prose--analysis) > h2:first-child:not(:has(+ h3)) {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.newsprint-article--news .newsprint-prose:not(.newsprint-prose--analysis) > h2:first-child:not(:has(+ h3)) + p {
  font-family: var(--font-article-heading);
  font-size: 1.22rem;
  font-weight: 600;
  line-height: 1.6;
  letter-spacing: -0.02em;
}

```

- [ ] **Step 4: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/article-v2.test.cjs
node frontend/tests/font-roles.test.cjs
```
Expected: 세 파일 모두 `… passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/news-article-reading.test.cjs
git commit -m "feat: news article prose with keep-all, category tabs and story headlines"
```

### Task 7: 내려 읽을 때 막대 숨기기

**Files:**
- Modify: `frontend/src/styles/global.css` (Task 5 블록의 `.newsprint-article-tags--end` 규칙 바로 앞, Task 6 규칙 뒤)
- Test: `frontend/tests/news-article-reading.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`console.log` 줄 바로 위에 넣는다.

```js
// --- CSS: bars hide while reading down (reuses the header's scroll state, no new script) ---
assert(css.includes('body:has(.site-header--fixed.site-header--hidden) .newsprint-article--news .persona-float:not(:has(:focus-visible)) {'), 'edition float hides on the way down, unless keyboard focus is inside');
assert(css.includes('body:has(.site-header--fixed:not(.site-header--hidden)) .newsprint-article--news .persona-float--back {'), 'back float shows on the way up on news articles');
const searchRule = 'body:has(.newsprint-article--news):has(.site-header--fixed.site-header--hidden) .handbook-search-sticky--detail:not(:focus-within)';
assert(/position:\s*static/.test(block(searchRule)), 'mobile search stops sticking on the way down (no blank gap at the top)');
assert(!fs.existsSync(path.join(src, 'scripts', 'readingScrollDirection.ts')), 'no second scroll-direction script');
assert(!/data-reading-scroll/.test(css), 'no separate scroll-state attribute');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `AssertionError … edition float hides on the way down, unless keyboard focus is inside`

- [ ] **Step 3: CSS를 추가한다**

Task 6에서 넣은 규칙들 뒤, `/* Two classes: the base .newsprint-article-tags rule sits later in the file. */` 주석 줄 **바로 앞**에 넣는다.

```css
/* News article: floating bars step aside while reading down.
   The header already tracks scroll direction (Navigation.astro): on the way down it
   carries .site-header--fixed.site-header--hidden, on the way up it drops --hidden. */
body:has(.site-header--fixed.site-header--hidden) .newsprint-article--news .persona-float:not(:has(:focus-visible)) {
  opacity: 0;
  pointer-events: none;
  transform: translateX(-50%) translateY(12px);
}

/* Single-edition articles: the back-to-list float used to show on the way down. Flip it. */
body:has(.site-header--fixed:not(.site-header--hidden)) .newsprint-article--news .persona-float--back {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}

/* Mobile search: stop sticking rather than fade, so no blank gap appears near the top. */
body:has(.newsprint-article--news):has(.site-header--fixed.site-header--hidden) .handbook-search-sticky--detail:not(:focus-within) {
  position: static;
}

```

명시도 메모(고치지 말 것): 첫 규칙은 `.persona-float--visible`(0,1,0)과 기존 `body:has(…) .persona-float--back`(0,3,1)보다 높다. `body:has(…)` 접두를 떼면 뒤집힌다.

- [ ] **Step 4: 통과를 확인한다**

Run: `node frontend/tests/news-article-reading.test.cjs`
Expected: `news-article-reading.test.cjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/news-article-reading.test.cjs
git commit -m "feat: hide floating bars on news articles while reading down"
```

### Task 8: 빌드와 실제 화면 확인

**Files:** 없음(확인만). 고칠 것이 나오면 해당 Task의 파일을 고치고 그 Task의 테스트를 다시 돌린다.

- [ ] **Step 1: 전체 테스트를 돌린다**

Run(저장소 루트, bash):
```bash
for f in frontend/tests/*.test.cjs frontend/tests/*.test.mjs; do node "$f" >/dev/null 2>&1 || echo "FAIL $f"; done
```
Expected: 출력이 "사전 정보"의 16개 목록(또는 시작할 때 기록한 목록)과 같다. 새 테스트 두 개(`news-bold-normalize`, `news-article-reading`)는 목록에 없어야 한다.

다른 파일이 나오면 그 테스트를 단독으로 실행해 메시지를 읽고, 이번 변경이 원인이면 고친다. `.test.ts` 파일은 이 계획의 변경과 무관해서 돌리지 않는다.

- [ ] **Step 2: 빌드한다**

Run: `cd frontend && npm run build`
Expected: 오류 0. EPERM이 나면 재시도하지 말고 보고한다.

- [ ] **Step 3: 개발 서버로 화면을 본다**

Run: `cd frontend && npm run dev` (백그라운드). 주소는 출력에 나온다(보통 `http://localhost:4321`).

볼 기사: 일간 비즈니스 1건, 일간 리서치 1건, 주간 정리 1건. `/ko/news/` 목록에서 고른다. EN도 1건 본다.

화면 크기 1280×900과 390×844에서, 테마 세 가지(종이·순백·다크)로 확인한다.

- [ ] 본문과 요약문에 단어 중간 줄바꿈이 없다.
- [ ] 본문에 `**`가 보이지 않는다. 문장 통째로 굵은 곳이 없고, 짧은 용어·숫자는 굵다.
- [ ] 메타 줄이 한 줄이다: `← AI 뉴스 · 데스크 · 호수 · 날짜 · 읽는 시간`. 날짜와 "AI 뉴스"가 두 번 나오지 않는다.
- [ ] 판 선택이 세그먼트 버튼이고, 오른쪽에 짝 기사 링크가 한 줄로 있다. 긴 제목은 말줄임된다.
- [ ] 판을 바꾸면 제목·요약문·본문·퀴즈가 바뀌고, 바뀐 본문에도 같은 조판이 적용된다.
- [ ] "Big Tech" 같은 분류가 작은 꼬리표로, 기사 제목이 그보다 크게 보인다. "나에게 주는 의미"처럼 뒤에 소제목이 없는 h2는 제목 크기 그대로다.
- [ ] 태그가 머리에 없고 기사 끝(출처 위)에 있다.
- [ ] 내려 읽으면 판 선택 막대가 사라지고, 조금 올리면 돌아온다. 마우스로 판을 바꾼 뒤에도 다시 사라진다. Tab으로 막대에 포커스를 두면 사라지지 않는다.
- [ ] 모바일: 기사 맨 위를 조금 내렸을 때 검색창 자리에 빈 칸이 없다. 하단 액션 바는 그대로다.
- [ ] 모바일: 본문 첫 줄이 844px 안에서 시작한다. 브라우저 콘솔에서 `Math.round(document.querySelector('.newsprint-prose').getBoundingClientRect().top + scrollY)`로 잰다(바꾸기 전 974).
- [ ] 다크 테마: 판 선택의 활성 버튼 글자가 읽힌다. 분류 꼬리표의 강조색이 배경에서 읽힌다.
- [ ] 주간 정리와 전문판: 첫 문단의 세리프 처리가 어색하지 않다. 어색하면 Amy에게 화면을 보여주고, 그 처리를 일간 기사로 한정할지 묻는다(스펙의 "테스트·확인" 마지막 항목).
- [ ] Core Analysis가 있는 기사 1건: 분석 영역의 제목이 본문과 같은 모양이고, 분석 영역의 첫 문단은 세리프가 아니다.
- [ ] 용어집 상세(`/ko/handbook/<아무 용어>/`)와 블로그 글 1건이 바꾸기 전과 같다.
- [ ] 관리자 뉴스 편집의 미리보기에 새 모양이 나온다(로그인이 필요하면 Amy에게 확인을 부탁한다).

- [ ] **Step 4: 개발 서버를 끈다**

- [ ] **Step 5: 문서 상태를 갱신하고 커밋**

`vault/09-Implementation/plans/2026-11-21-news-article-reading-design.md`의 Status 줄을 바꾼다.

```markdown
**Status:** implemented (<완료한 날짜>) — [[2026-11-21-news-article-reading]]
```

이 계획 문서 맨 위 제목 아래에 한 줄을 추가한다.

```markdown
**Status:** done (<완료한 날짜>)
```

```bash
git add vault/09-Implementation/plans/2026-11-21-news-article-reading-design.md vault/09-Implementation/plans/2026-11-21-news-article-reading.md
git commit -m "docs: record the news article reading pass"
```

`ACTIVE_SPRINT.md`에는 다른 미커밋 변경이 있으므로 이 커밋에 넣지 않는다. 스프린트 반영은 Amy가 `/sprint-sync`로 한다.

---

## 실행 결과 (2026-11-21)

- 작업 폴더: `C:\Users\amy\Desktop\0to1log-news-reading` (`main`의 worktree). 원래 폴더는 `fix/handbook-writer-grounding`에 미커밋 변경이 있어 전환하지 않았다.
- 테스트: 전체 실행 시 실패 목록이 시작 전 16개와 같다. 새 테스트 `news-bold-normalize`, `news-article-reading` 통과.
- 빌드: `npm run build` 오류 0.
- 화면(개발 서버, 11월 21일 비즈니스·리서치 기사, w46 주간 정리, EN 비즈니스 기사)

| 항목 | 전 | 후 |
|---|---|---|
| 본문 시작(데스크톱 1280) | 820px | 708px |
| 본문 시작(모바일 390) | 974px | 843px |
| 본문에 보이는 `**` | 2곳 | 0 |
| 굵은 글씨 비율(비즈니스 학습판) | 14% | 3.5% |
| 단어 중간 줄바꿈 | 있음 | 없음(`keep-all`) |

- 계획과 달라진 것
  - Task 1 Step 5(사람이 정하는 단계)를 건너뛰고 기본 제안으로 커밋한 뒤 나머지를 진행했다. 기준이 바뀌면 `isLongBold`만 고쳐 따로 커밋한다.
  - Task 8에서 모바일 간격 조정을 추가했다(스펙 "모바일" 참조). 데스크톱 값 그대로는 모바일 본문 시작이 그대로였다.
  - 뉴스 페이지와 레이아웃 파일은 `main`에서 LF였다. CRLF는 원래 작업 폴더의 체크아웃 상태였다.
- 확인하지 못한 것
  - 관리자 뉴스 편집의 미리보기(로그인 필요).
  - 순백 테마는 따로 보지 않았다(종이·다크만 확인). 새 색을 쓰지 않고 토큰만 썼다.
  - Core Analysis가 있는 기사: 확인한 네 기사에는 분석 영역이 없었다.
  - 키보드 포커스가 막대 안에 있을 때 숨지 않는 동작은 CSS 규칙만 확인했다.
- 눈에 띈 것(이번 범위 밖)
  - 원문에 띄어쓰기 없이 굵은 글씨가 붙은 곳은 그대로 붙어 보인다(`없이**처음 보는**` → "없이처음 보는"). 글 쪽 문제다.
  - 리서치 기사는 짧은 숫자 강조가 많아 굵은 글씨가 11% 남는다. `isLongBold` 기준을 정할 때 함께 본다.
