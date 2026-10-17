# 용어 상세 A+B(사전 표제어 + 개념 지도) Implementation Plan

**Status:** done (2026-10-17) — 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** ready (2026-10-17)

**Goal:** `/ko|en/handbook/[slug]/`을 "경로 줄 → 표제어(+품사 줄) → 뜻풀이 + 먹색 판 → 함께 볼 말 → 난이도·본문(옆에 세로 액션 막대) → 개념 지도 → 최근 뉴스에서 → 참고 자료 …" 한 단 지면으로 바꾼다. 오른쪽 레일(검색·저장/공유·목차·연관 개념·최근 뉴스)과 "AI 용어집" 대형 마스트헤드는 없앤다.

**Architecture:**
- 라벨·품사 줄·편집 순서는 순수 모듈 `lib/handbookFacets.js`, 개념 지도 좌표·라벨 맞춤은 순수 모듈 `lib/conceptMap.js`가 맡는다(단위 테스트 `handbook-facets.test.mjs` 하나로 둘 다 검사).
- `handbookDetailPage.ts`는 facet 3열을 더 읽고, 연관 용어를 `related_term_slugs` 순서로 정렬하고, "최신 뉴스 3개" fallback 쿼리를 없앤다(쿼리 1개 감소).
- `NewsprintShell`에 `crumbItems?: string[]`를 더해 경로 줄에 분야 라벨을 보인다(주지 않으면 기존 호수·날짜).
- 새 컴포넌트 4개(`components/handbook/HandbookEntryHead|HandbookXref|HandbookConceptMap|HandbookNewsMentions.astro`)와 2단으로 재스타일한 `HandbookHeroCard`가 화면을 그린다. 액션은 기사 상세와 같은 인라인 `StickyReadingActions variant="term"`이다.
- 레벨 전환 스크립트의 이중 바인딩을 `dataset.levelReady` 가드로 막는다.
- `HandbookSectionNav`(목차)와 그 CSS, 레일 검색 CSS를 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-17-handbook-term-entry-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**. 특히 `publicTermIndex.ts`는 이번 작업에서 건드리지 않는다(`handbookDetailPage.ts`가 import만 한다).
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), `HandbookHeroCard.astro`(`/\*\*(.+?)\*\*/g`, 주석의 `\n`), CSS 테스트 정규식, EN 파생 스크립트.
- Astro 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `→`, `…`, `—`는 **문자 그대로** 쓴다(이 계획의 코드 블록도 전부 문자 그대로다).
- 줄바꿈·인코딩
  - `frontend/src/lib/pageData/handbookDetailPage.ts`는 **전부 CRLF**다. Edit 도구로만 고친다(sed/bash 금지). 고친 뒤 `tr -cd '\r' < 파일 | wc -c`와 `wc -l < 파일`이 같아야 한다.
  - `frontend/src/components/newsprint/NewsprintShell.astro`는 **UTF-8 BOM**으로 시작한다. Edit 도구로만 고친다(Write로 통째 교체 금지). 고친 뒤 `head -c3 파일 | od -c`가 `357 273 277`이어야 한다.
  - `global.css`, 용어 상세 페이지 2개, `HandbookHeroCard.astro`, 테스트 파일들은 LF다. CSS 규칙은 줄 번호가 아니라 셀렉터/주석으로 찾는다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버 때문에 `npm run build`가 EPERM/EMFILE로 실패하면 재시도하지 말고 보고한다. (사전 검증에서 dev 서버를 켠 채 빌드하자 dev 쪽이 EMFILE로 500을 냈다. 빌드 뒤에는 dev 서버를 다시 켠다.)

**지켜야 할 것**
- 상세 HTML은 CDN에 캐시된다. 새로 `Astro.locals.user`/세션 의존 렌더를 넣지 않는다. 북마크는 현행처럼 `isBookmarked` 없이(=`false`) 렌더하고 클라이언트가 채운다.
- `#handbook-body`는 레벨 전환 때 `innerHTML`로 교체되고, `handbook-popup.ts`는 `.newsprint-prose a[href*="/handbook/"]`를 가로챈다. 그래서 함께 볼 말·개념 지도·최근 뉴스는 **prose 밖**에 둔다.
- 관리자 편집 미리보기(`admin/handbook/edit/[slug].astro`)가 `.handbook-detail-title`/`-subtitle`/`-meta`와 `HandbookSideRail`을 쓴다. 전역 규칙은 고치지 않고 새 크기는 `.handbook-entry …`로 범위를 좁힌다. `HandbookSideRail.astro`, `.handbook-detail-meta` CSS는 지우지 않는다.
- `ReadingActionsRail`(블로그 사용), `.newsprint-rail-stack` CSS(`detail-rail-actions-placement` 테스트가 고정)는 남긴다.
- 테스트 기준선(2026-10-17, 계획 작성 시 측정): **PASS 77 / FAIL 20**(`handbook-popup-render.test.ts`는 러너 대상 아님).
  - 기준선 FAIL 20개: admin-live-preview, admin-v1-structure, article-deck-font, auth-prompt-library-preview, blog-section-heading-font, blog-sidebar-categories, blog-sidebar-layout, blog-title-fonts, comments-admin-delete-contract, content-feedback-contract, csp-inline-scripts, detail-rail-copy, handbook-detail-table-overflow, handbook-search-recognition, log-list-created-order, navigation-shell-copy, news-fact-pack-structure, product-detail-scenarios-theme, public-slug-visibility, sticky-reading-actions-structure.
  - 이번 작업과 닿는 기존 실패: `sticky-reading-actions-structure`(`data-reading-action="helpful"` 단언에서 먼저 실패 — 우리가 바꾸는 59–60행까지 가지 못한다), `admin-live-preview`(블로그 편집 페이지 단언에서 먼저 실패), `handbook-detail-table-overflow`(WebKit 스크롤바 CSS), `content-feedback-contract`(jest 문법). 작업 뒤에도 **같은 메시지**로 실패해야 정상이다.
  - 완료 후 기대값: 신규 2개 PASS → **PASS 79 / FAIL 20, 신규 FAIL 0**. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.

**현재 코드**
- `pages/{ko,en}/handbook/[slug].astro`(449/454줄, LF). 두 파일은 locale·문구와 EN의 `isEnFallback` 안내만 다르다.
  - 대형 마스트헤드 `NewsprintShell masthead="AI 용어집" … subkicker=[…]`, `header` 안 `.handbook-detail-meta`(분야) + `h1.handbook-detail-title`(KO는 `span.handbook-detail-korean`) + `p.handbook-detail-subtitle`
  - `HandbookHeroCard`(정의 + "뉴스에서는 이렇게" 3줄, 회색 카드) → `.newsprint-divider` → 난이도 스위처/`#level-data`/`#level-float` → `.reading-actions-layout`(수정자 없음) 안에 본문·참고 자료·`[data-reading-end]`·학습 체크·피드백·관리자·이전/다음
  - `slot="rail"`: 레일 검색 폼(`.newsprint-rail-search`), `ReadingActionsRail`(안에 `HandbookSectionNav`, `HandbookSideRail`)
  - 스크립트: `initLevelSwitcher()`를 **직접 호출 + `astro:page-load`**로 두 번 부른다(ViewTransitions는 첫 로드에도 page-load를 쏜다) → 클릭 리스너·`onSessionReady`가 두 번 붙는다.
- `lib/pageData/handbookDetailPage.ts`(CRLF): mentions 쿼리(`.or(tags.cs…,title.ilike…)`, `.limit(5)`) + **최신 뉴스 3개 쿼리**(fallback) + 연관 용어 `.in('slug', related_term_slugs)`(DB 순서) + 같은 분야 `.overlaps(...).limit(5)`. 반환 필드명은 `relatedArticles`, `relatedTerms`, `sameCategoryTerms`.
- DB(운영, 114개): `related_term_slugs`가 있는 용어는 16개뿐이고 미발행 slug(`dpo`, `bert`)를 가리키는 것도 있다(`.in()`이 빠뜨린다 → `orderBySlugs`가 무시). `term_type` null 25개(그중 `facet_volatility`는 전부 기본값 `'stable'`). `facet_intent`에 operate/apply/defend가 실제로 있다.
- `components/handbook/`(서가 작업에서 생김)와 `lib/handbookShelves.js`의 `termNames(term, locale)`(KO: `korean_name`이 있고 `term`과 다르면 그것, 아니면 `term`)를 그대로 쓴다.
- 기사 상세 끝 블록이 쓰는 `.news-end-title`(Hahmlet 700, 위 2px 먹선)을 끝 블록 `h2`에 그대로 쓴다.
- 홈 키워드 판/오늘의 용어 판 규칙(밝은 테마 먹색 `--color-text-primary` 면, 다크 `--color-bg-tertiary`)을 뜻풀이 판에 따른다.
- 글꼴: `--font-heading`=Hahmlet(600/700만 로드), `--font-masthead`=Newsreader(500만 로드).

**스펙 해석(실행자가 임의로 바꾸지 않는다)**
- 개념 지도 기하·라벨 맞춤은 별도 `lib/conceptMap.js`에 둔다(스펙이 허용). 테스트는 스펙 이름대로 `handbook-facets.test.mjs` 하나다.
- 표시 이름은 `termNames(t, locale).name` 하나로 통일한다(함께 볼 말, 개념 지도 노드, **개념 지도 중심**). 스펙의 "KO `korean_name || term`"과 같은 결과다(`korean_name === term`이면 어차피 같다).
- 경로 줄: `crumbItems`가 있으면 `<span class="newsprint-crumb-items">`에 `join(' · ')` 한 줄로 렌더한다. 빈 배열이면 back 링크만 보인다(분야 없는 용어, 404/503 화면).
- 품사 줄: `entryGrammar`는 모르는 쓰임 값을 버리고 중복을 없앤다. 쓰임끼리는 `·`(공백 없음), 세 묶음 사이는 ` · `다. 예: `검색·지식 시스템 · 만들 때·이해할 때 · 변화 중인 개념`.
- 뜻풀이 판: 정의와 판 중 하나만 있으면 `handbook-hero-card--solo`(1단). 판 제목의 `role="heading" aria-level="2"`. `backUrl` prop과 링크 마크업은 그대로 둔다(미사용).
- 다크 판 규칙은 scoped style에서 `:global([data-theme="dark"]) .handbook-hero-card__plate`로 쓴다(Astro scoped 셀렉터는 `html[data-theme]`에 cid가 없어 `:global` 없이는 안 걸린다).
- `.newsprint-divider`는 함께 볼 말과 난이도 사이에 그대로 둔다.
- 개념 지도 SVG(`viewBox="0 0 560 320"`, 폭 100%, 최대 560px)
  - 중심 (280,160), 타원 rx 125 / ry 108, 중심 원 r 58, 노드 점 r 6, 노드 라벨 17(viewBox 단위). 375px 폭(본문 327px)에서 라벨은 약 9.9px로 보인다.
  - 노드: 12시부터 시계방향 균등 분할, 최대 6개. 앵커는 위/아래 정중앙 `middle`, 오른쪽 반 `start`, 왼쪽 반 `end`.
  - 라벨 폭은 em으로 **보수적으로** 추정한다: 한글/CJK와 `…` 1, 대문자·숫자 0.7, 공백 0.3, 그 밖 0.56(실측 Hahmlet보다 넓게 잡음).
  - 라벨 예산: 옆 노드는 점에서 12 떨어진 곳부터 viewBox 안쪽 여백 8까지, 위/아래 노드는 가운데 정렬 최대 320. 넘치면 **뒤에서부터 잘라 `…`를 붙인다**(잘린 끝의 공백·`·,(/-`는 지운다). 예: 오른쪽 노드의 "벡터 데이터베이스 인덱스" → "벡터 데이터베…". 전체 이름은 `aria-label`과 바로 위 "함께 볼 말"에 남는다.
  - 중심 라벨(원 안 사용 폭 100): 한 줄로 15 이상이면 한 줄(최대 20), 아니면 공백에서 두 줄로 나눈 후보 중 글자가 가장 큰 것, 그래도 11 미만이면 11로 두고 줄마다 `…`로 자른다. 예: "RRF" 20, "상호 순위 융합" 15 한 줄, "자기지도 사전학습 과제" 15 두 줄(자기지도 / 사전학습 과제), "Self-Supervised Pretext Tasks" 11 두 줄.
  - 링크 그룹: `<svg role="group" aria-labelledby=제목>`, 노드마다 `<a href aria-label=이름>`, 선과 중심은 `aria-hidden="true"`.
- 최근 뉴스 날짜는 서버에서 `toLocaleDateString(…, { year: 'numeric', month: 'short', day: 'numeric' })`(KO "2026년 7월 23일")로 쓴다. 유형 라벨이 없으면 빈 칸(격자 유지).
- 레벨 스위처는 용어집 첫 화면과 같은 패턴(직접 호출 + `astro:page-load`, `dataset.levelReady` 가드)이다. 가드를 `_levelObserver.disconnect()`보다 **먼저** 둔다(두 번째 호출이 관찰자를 끊지 않게).
- CSS 정리 범위: `.handbook-toc*`(목차 전용)와 `.newsprint-rail-search`(레일 검색 폼 전용, 두 용어 상세 페이지만 사용) 규칙만 지운다. `.handbook-search-sticky--detail` 데스크톱 숨김은 남긴다(스펙: 데스크톱 용어 상세에는 검색창 없음).

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`+`supabase/` 복제본(node_modules는 junction)에 Task 1–4를 이 문서의 코드 그대로 적용했다. 복제본 기준선은 실제 repo와 이름 기준 동일(PASS 77 / FAIL 20).
- 각 Step 2는 적힌 메시지로 실패, 통과 확인 Step은 PASS. 전체 **PASS 79 / FAIL 20**, 실패 20개의 첫 오류 메시지가 기준선과 동일(경로만 다름). `sticky-reading-actions-structure`는 helpful/confusing 단언을 뺀 임시 사본으로 돌려 handbook 새 단언 4줄이 통과함을 따로 확인했다(그 뒤의 기존 CSS 단언에서 실패 — 기준선과 같은 문제).
- `astro build` "Complete!"(Task 3 후, Task 4 후 두 번).
- dev 서버(운영 데이터) 렌더: `/ko|en/handbook/rrf/` 200 — 경로 줄 "← AI 용어집 데이터 엔지니어링 · LLM · 생성AI", 품사 줄 "검색·지식 시스템 · 만들 때·이해할 때 · 변화 중인 개념", 함께 볼 말 = 하이브리드 검색 · BM25 · 벡터 검색 · 리랭킹(편집 순서), 개념 지도 노드 4개, 뉴스 언급 없음 → 섹션 없음. `/ko/handbook/recurrent-mechanism/`(연관 없음·`term_type` null·뉴스 없음) 200 — 품사 줄 없음, "→ 같은 분야" 5개, 개념 지도 5개, 판 없음 → `--solo`. `/ko/handbook/supply-chain-attack/`(연관 없음·뉴스 없음) 200. `/ko/handbook/bm25/` 최근 뉴스 1건. 없는 slug 404. 서버 로그 오류 0.
- 브라우저: 1200px 다크·375px 라이트에서 가로 넘침 0(`scrollWidth === innerWidth`), 개념 지도 텍스트 bbox가 전부 viewBox 안, 375px 헤드워드 38.4px, 뜻풀이 1단, 하단 액션 바 `position: fixed`, 기초→심화 클릭 시 본문 교체·`levelReady="true"`.

---

## Task 1: 라벨·품사 줄·편집 순서·개념 지도 순수 함수 (TDD)

**Files:**
- Create: `frontend/src/lib/handbookFacets.js`, `frontend/src/lib/conceptMap.js`
- Test: `frontend/tests/handbook-facets.test.mjs`(새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/handbook-facets.test.mjs
// Term detail: facet labels, entry grammar line, editorial order, concept map geometry and label fitting.
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const load = (p) => import(pathToFileURL(path.join(here, p)).href);
const { termTypeLabel, intentLabel, volatilityLabel, entryGrammar, orderBySlugs } = await load('../src/lib/handbookFacets.js');
const { CONCEPT_MAP, conceptMapNodes, labelEm, fitLabel, nodeLabel, centerLabel } = await load('../src/lib/conceptMap.js');

// label maps: all 13 backend TERM_TYPES, KO/EN; unknown values -> ''
const TERM_TYPES = [
  'foundational_concept', 'problem_failure_mode', 'model_algorithm_family', 'training_optimization_method',
  'retrieval_knowledge_system', 'system_workflow_pattern', 'data_storage_indexing_system',
  'protocol_format_data_structure', 'capability_feature_spec', 'metric_benchmark',
  'product_platform_service', 'library_framework_sdk', 'hardware_runtime_infra',
];
for (const v of TERM_TYPES) {
  assert.ok(termTypeLabel('ko', v), `ko label for ${v}`);
  assert.ok(termTypeLabel('en', v), `en label for ${v}`);
}
assert.equal(termTypeLabel('ko', 'retrieval_knowledge_system'), '검색·지식 시스템');
assert.equal(termTypeLabel('en', 'problem_failure_mode'), 'Failure mode');
assert.equal(termTypeLabel('ko', 'concept'), '');
assert.equal(termTypeLabel('ko', null), '');
assert.equal(termTypeLabel('ko', 'toString'), '', 'prototype keys are not labels');

for (const v of ['understand', 'compare', 'build', 'debug', 'evaluate', 'operate', 'apply', 'defend']) {
  assert.ok(intentLabel('ko', v) && intentLabel('en', v), `intent label ${v}`);
}
assert.equal(intentLabel('ko', 'understand'), '이해할 때');
assert.equal(intentLabel('en', 'build'), 'When building');
assert.equal(intentLabel('en', 'explore'), '');

assert.equal(volatilityLabel('ko', 'stable'), '안정된 개념');
assert.equal(volatilityLabel('ko', 'fast-changing'), '빠르게 바뀌는 개념');
assert.equal(volatilityLabel('en', 'evolving'), 'Evolving');
assert.equal(volatilityLabel('en', 'volatile'), '');

// entryGrammar: type · intents(·) · volatility; nothing without a known type
assert.equal(
  entryGrammar('ko', { term_type: 'retrieval_knowledge_system', facet_intent: ['build', 'understand'], facet_volatility: 'evolving' }),
  '검색·지식 시스템 · 만들 때·이해할 때 · 변화 중인 개념',
);
assert.equal(
  entryGrammar('en', { term_type: 'metric_benchmark', facet_intent: ['evaluate'], facet_volatility: 'stable' }),
  'Metric / benchmark · When evaluating · Stable',
);
assert.equal(entryGrammar('ko', { term_type: null, facet_intent: null, facet_volatility: 'stable' }), '', 'unclassified: no lone "안정된 개념"');
assert.equal(entryGrammar('ko', { term_type: 'mystery', facet_volatility: 'stable' }), '');
assert.equal(entryGrammar('ko', { term_type: 'metric_benchmark', facet_intent: [], facet_volatility: null }), '지표·벤치마크');
assert.equal(entryGrammar('en', { term_type: 'metric_benchmark', facet_intent: ['explore', 'compare', 'compare'] }), 'Metric / benchmark · When comparing');
assert.equal(entryGrammar('ko', {}), '');

// orderBySlugs: editorial order, missing slugs skipped, unlisted rows dropped
const rows = [{ slug: 'bm25' }, { slug: 're-ranking' }, { slug: 'hybrid-search' }, { slug: 'stray' }];
assert.deepEqual(
  orderBySlugs(rows, ['hybrid-search', 'dpo', 'bm25', 're-ranking', 'bm25']).map((r) => r.slug),
  ['hybrid-search', 'bm25', 're-ranking'],
);
assert.deepEqual(orderBySlugs(null, ['a']), []);
assert.deepEqual(orderBySlugs(rows, null), []);

// conceptMapNodes: 12 o'clock first, clockwise, anchors by half, 0..6 nodes
const geo = { cx: 280, cy: 160, rx: 125, ry: 108 };
assert.deepEqual(conceptMapNodes(0, geo), []);
assert.deepEqual(conceptMapNodes(1, geo), [{ x: 280, y: 52, anchor: 'middle' }]);
assert.deepEqual(conceptMapNodes(4, geo), [
  { x: 280, y: 52, anchor: 'middle' },
  { x: 405, y: 160, anchor: 'start' },
  { x: 280, y: 268, anchor: 'middle' },
  { x: 155, y: 160, anchor: 'end' },
]);
const six = conceptMapNodes(6, geo);
assert.equal(six.length, 6);
assert.deepEqual(six.map((n) => n.anchor), ['middle', 'start', 'start', 'middle', 'end', 'end']);
assert.deepEqual(six[1], { x: 388.3, y: 106, anchor: 'start' });
assert.deepEqual(six[4], { x: 171.7, y: 214, anchor: 'end' });
assert.equal(conceptMapNodes(9, geo).length, 6, 'at most 6 nodes');
assert.deepEqual(conceptMapNodes(5, geo).map((n) => n.anchor), ['middle', 'start', 'start', 'end', 'end']);

// labels never leave the viewBox
assert.equal(labelEm('RAG 검색'), 4.4);
assert.equal(fitLabel('하이브리드 검색', 8), '하이브리드 검색');
assert.equal(fitLabel('벡터 데이터베이스 인덱스', 7), '벡터 데이터…');
const right = nodeLabel('벡터 데이터베이스 인덱스', { x: 405, y: 160, anchor: 'start' });
assert.deepEqual(right, { x: 417, y: 166, text: '벡터 데이터베…' });
const left = nodeLabel('하이브리드 검색', { x: 155, y: 160, anchor: 'end' });
assert.deepEqual(left, { x: 143, y: 166, text: '하이브리드 검색' });
assert.deepEqual(nodeLabel('BM25', { x: 280, y: 52, anchor: 'middle' }), { x: 280, y: 38, text: 'BM25' });
assert.deepEqual(nodeLabel('BM25', { x: 280, y: 268, anchor: 'middle' }), { x: 280, y: 296, text: 'BM25' });
const { width, margin, fontSize } = CONCEPT_MAP;
for (const n of conceptMapNodes(6, CONCEPT_MAP)) {
  const label = nodeLabel('Retrieval-Augmented Generation Pipeline', n);
  const w = labelEm(label.text) * fontSize;
  const [x0, x1] = n.anchor === 'start' ? [label.x, label.x + w] : n.anchor === 'end' ? [label.x - w, label.x] : [label.x - w / 2, label.x + w / 2];
  assert.ok(x0 >= margin && x1 <= width - margin, `label inside the viewBox (${n.anchor} ${x0}..${x1})`);
}

// centre label: shrinks, then wraps at a space, then cuts
assert.deepEqual(centerLabel('RRF'), { fontSize: 20, lines: [{ text: 'RRF', y: 167 }] });
assert.deepEqual(centerLabel('상호 순위 융합'), { fontSize: 15, lines: [{ text: '상호 순위 융합', y: 165.3 }] });
assert.deepEqual(centerLabel('자기지도 사전학습 과제'), {
  fontSize: 15,
  lines: [{ text: '자기지도', y: 156.8 }, { text: '사전학습 과제', y: 173.8 }],
});
assert.deepEqual(centerLabel('Self-Supervised Pretext Tasks').lines.map((l) => l.text), ['Self-Supervised', 'Pretext Tasks']);
const long = centerLabel('Supercalifragilisticexpialidocious');
assert.equal(long.fontSize, CONCEPT_MAP.centerMinFont);
assert.ok(long.lines[0].text.endsWith('…') && labelEm(long.lines[0].text) * long.fontSize <= CONCEPT_MAP.centerRadius * 2 - 16);

console.log('handbook-facets.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/handbook-facets.test.mjs`
Expected: FAIL `ERR_MODULE_NOT_FOUND`(`handbookFacets.js` 없음).

- [ ] **Step 3: `handbookFacets.js` 작성** (Write 도구로)

```js
// frontend/src/lib/handbookFacets.js
// Pure helpers for the term detail page: facet labels, the entry "grammar" line, editorial order. No I/O.

// backend/services/agents/prompts_handbook_types.py TERM_TYPES (all 13)
const TERM_TYPE_LABELS = {
  ko: {
    foundational_concept: '기초 개념',
    problem_failure_mode: '문제·실패 유형',
    model_algorithm_family: '모델·알고리즘',
    training_optimization_method: '학습·최적화 기법',
    retrieval_knowledge_system: '검색·지식 시스템',
    system_workflow_pattern: '시스템·워크플로 패턴',
    data_storage_indexing_system: '데이터 저장·색인',
    protocol_format_data_structure: '프로토콜·형식',
    capability_feature_spec: '기능·사양',
    metric_benchmark: '지표·벤치마크',
    product_platform_service: '제품·플랫폼',
    library_framework_sdk: '라이브러리·프레임워크',
    hardware_runtime_infra: '하드웨어·인프라',
  },
  en: {
    foundational_concept: 'Foundational concept',
    problem_failure_mode: 'Failure mode',
    model_algorithm_family: 'Model / algorithm',
    training_optimization_method: 'Training method',
    retrieval_knowledge_system: 'Retrieval system',
    system_workflow_pattern: 'Workflow pattern',
    data_storage_indexing_system: 'Data storage / indexing',
    protocol_format_data_structure: 'Protocol / format',
    capability_feature_spec: 'Capability / feature',
    metric_benchmark: 'Metric / benchmark',
    product_platform_service: 'Product / platform',
    library_framework_sdk: 'Library / framework',
    hardware_runtime_infra: 'Hardware / infra',
  },
};

// INTENT_VALUES (understand/compare/build/debug/evaluate) + operate/apply/defend found in the DB
const INTENT_LABELS = {
  ko: {
    understand: '이해할 때',
    compare: '비교할 때',
    build: '만들 때',
    debug: '고칠 때',
    evaluate: '평가할 때',
    operate: '운영할 때',
    apply: '적용할 때',
    defend: '방어할 때',
  },
  en: {
    understand: 'When learning',
    compare: 'When comparing',
    build: 'When building',
    debug: 'When debugging',
    evaluate: 'When evaluating',
    operate: 'When operating',
    apply: 'When applying',
    defend: 'When defending',
  },
};

const VOLATILITY_LABELS = {
  ko: { stable: '안정된 개념', evolving: '변화 중인 개념', 'fast-changing': '빠르게 바뀌는 개념' },
  en: { stable: 'Stable', evolving: 'Evolving', 'fast-changing': 'Fast-changing' },
};

function pick(tables, locale, value) {
  const table = tables[locale] ?? tables.en;
  return typeof value === 'string' && Object.prototype.hasOwnProperty.call(table, value) ? table[value] : '';
}

/** @param {'ko'|'en'} locale */
export function termTypeLabel(locale, value) {
  return pick(TERM_TYPE_LABELS, locale, value);
}

/** @param {'ko'|'en'} locale */
export function intentLabel(locale, value) {
  return pick(INTENT_LABELS, locale, value);
}

/** @param {'ko'|'en'} locale */
export function volatilityLabel(locale, value) {
  return pick(VOLATILITY_LABELS, locale, value);
}

/**
 * "유형 · 쓰임 · 변화 정도". Empty unless term_type has a label: migration 00047 defaults
 * facet_volatility to 'stable', so an unclassified term must not show "안정된 개념" alone.
 * Intents are joined with '·' (unknown values dropped, duplicates removed).
 */
export function entryGrammar(locale, { term_type, facet_intent, facet_volatility } = {}) {
  const type = termTypeLabel(locale, term_type);
  if (!type) return '';
  const intents = [...new Set((Array.isArray(facet_intent) ? facet_intent : []).map((v) => intentLabel(locale, v)).filter(Boolean))];
  return [type, intents.join('·'), volatilityLabel(locale, facet_volatility)].filter(Boolean).join(' · ');
}

/**
 * Rows in the editorial order of `slugs`. Slugs without a row (unpublished) are skipped,
 * rows whose slug is not listed are dropped, duplicates appear once.
 */
export function orderBySlugs(rows, slugs) {
  const bySlug = new Map((rows || []).map((row) => [row.slug, row]));
  const seen = new Set();
  const out = [];
  for (const slug of slugs || []) {
    if (seen.has(slug)) continue;
    seen.add(slug);
    const row = bySlug.get(slug);
    if (row) out.push(row);
  }
  return out;
}
```

- [ ] **Step 4: `conceptMap.js` 작성** (Write 도구로. `'…'`는 U+2026 문자 그대로)

```js
// frontend/src/lib/conceptMap.js
// Pure geometry and label fitting for the term concept map (server-rendered SVG). No I/O.
// Widths are estimated in em: Hangul/CJK and '…' 1, uppercase/digits 0.7, space 0.3, other 0.56
// (conservative for Hahmlet), so labels stay inside the viewBox even at 375px.

export const CONCEPT_MAP = {
  width: 560,
  height: 320,
  cx: 280,
  cy: 160,
  rx: 125,
  ry: 108,
  centerRadius: 58,
  nodeRadius: 6,
  fontSize: 17, // node labels, viewBox units
  labelGap: 12, // node centre -> side label
  margin: 8, // labels never cross this inner edge of the viewBox
  middleBudget: 320, // max width of a top/bottom label
  centerMaxFont: 20,
  centerMinFont: 11,
  centerOneLineMin: 15, // below this the centre label tries two lines
  maxNodes: 6,
};

const round = (v) => Math.round(v * 10) / 10;

function charEm(ch) {
  const c = ch.codePointAt(0);
  if (ch === ' ') return 0.3;
  if (ch === '…') return 1;
  if (
    (c >= 0x1100 && c <= 0x11ff) ||
    (c >= 0x2e80 && c <= 0x9fff) ||
    (c >= 0xac00 && c <= 0xd7af) ||
    (c >= 0xf900 && c <= 0xfaff) ||
    (c >= 0xff00 && c <= 0xffef)
  ) return 1;
  if ((c >= 0x41 && c <= 0x5a) || (c >= 0x30 && c <= 0x39)) return 0.7;
  return 0.56;
}

/** Estimated width of `text` in em. */
export function labelEm(text) {
  let w = 0;
  for (const ch of String(text ?? '')) w += charEm(ch);
  return Math.round(w * 100) / 100;
}

/**
 * `text` when it fits `maxEm`; otherwise the longest prefix (trailing spaces and ` ·,(/-` removed)
 * that fits together with '…'.
 */
export function fitLabel(text, maxEm) {
  const s = String(text ?? '').trim();
  if (labelEm(s) <= maxEm) return s;
  let chars = [...s];
  while (chars.length > 1) {
    chars = chars.slice(0, -1);
    let head = chars.join('');
    while (head && ' ·,(/-'.includes(head[head.length - 1])) head = head.slice(0, -1);
    if (head && labelEm(`${head}…`) <= maxEm) return `${head}…`;
  }
  return `${chars[0] ?? ''}…`;
}

/**
 * Node positions on an ellipse: 12 o'clock first, clockwise, equal angles; at most 6 nodes.
 * anchor: 'middle' straight above/below the centre, 'start' on the right half, 'end' on the left half.
 */
export function conceptMapNodes(count, { cx, cy, rx, ry }) {
  const n = Math.max(0, Math.min(CONCEPT_MAP.maxNodes, Math.floor(Number(count) || 0)));
  const nodes = [];
  for (let i = 0; i < n; i += 1) {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const cos = Math.cos(angle);
    const anchor = Math.abs(cos) < 1e-6 ? 'middle' : cos > 0 ? 'start' : 'end';
    nodes.push({ x: round(cx + rx * cos), y: round(cy + ry * Math.sin(angle)), anchor });
  }
  return nodes;
}

/**
 * Label position and text for a node. Side labels may use the space up to the viewBox margin;
 * top/bottom labels are centred above/below the dot and limited to `middleBudget`.
 */
export function nodeLabel(name, node, map = CONCEPT_MAP) {
  const { width, cy, fontSize, labelGap, margin, middleBudget, nodeRadius } = map;
  let x = node.x;
  let y;
  let budget;
  if (node.anchor === 'middle') {
    budget = Math.min(middleBudget, 2 * (Math.min(node.x, width - node.x) - margin));
    y = node.y < cy ? node.y - nodeRadius - 8 : node.y + nodeRadius + 8 + Math.round(fontSize * 0.8);
  } else {
    x = node.anchor === 'start' ? node.x + labelGap : node.x - labelGap;
    budget = node.anchor === 'start' ? width - margin - x : x - margin;
    y = node.y + Math.round(fontSize * 0.35);
  }
  return { x: round(x), y: round(y), text: fitLabel(name, budget / fontSize) };
}

/**
 * Centre label inside the ink circle (usable width = 2r - 16).
 * One line when it fits at >= centerOneLineMin; otherwise the two-line split (at a space) with the
 * largest font; font capped at centerMaxFont; below centerMinFont each line is cut with '…'.
 */
export function centerLabel(text, map = CONCEPT_MAP) {
  const { cy, centerRadius, centerMaxFont, centerMinFont, centerOneLineMin } = map;
  const maxWidth = centerRadius * 2 - 16;
  const s = String(text ?? '').trim();
  const words = s.split(' ').filter(Boolean);
  const fontFor = (lines) => Math.min(centerMaxFont, Math.floor(maxWidth / Math.max(0.01, ...lines.map(labelEm))));

  let lines = [s];
  let font = fontFor(lines);
  if (font < centerOneLineMin && words.length > 1) {
    let best = null;
    for (let i = 1; i < words.length; i += 1) {
      const candidate = [words.slice(0, i).join(' '), words.slice(i).join(' ')];
      const f = fontFor(candidate);
      if (!best || f > best.font) best = { lines: candidate, font: f };
    }
    if (best.font > font) ({ lines, font } = best);
  }
  if (font < centerMinFont) {
    font = centerMinFont;
    lines = lines.map((line) => fitLabel(line, maxWidth / font));
  }
  const lineHeight = Math.round(font * 1.15);
  const first = cy - ((lines.length - 1) * lineHeight) / 2 + font * 0.35;
  return { fontSize: font, lines: lines.map((line, i) => ({ text: line, y: round(first + i * lineHeight) })) };
}
```

- [ ] **Step 5: 통과 확인** — `node frontend/tests/handbook-facets.test.mjs` → `handbook-facets.test.mjs passed`

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/handbookFacets.js frontend/src/lib/conceptMap.js frontend/tests/handbook-facets.test.mjs
git commit -m "feat: add handbook facet labels and concept map geometry helpers"
```

---

## Task 2: 상세 데이터 — facet 열, 연관 용어 순서, 최신 뉴스 fallback 제거 (TDD)

**Files:**
- Modify: `frontend/src/lib/pageData/handbookDetailPage.ts`(**CRLF → Edit 도구만**), `frontend/tests/public-detail-query-contract.test.cjs`
- Test: `frontend/tests/handbook-term-entry.test.cjs`(새 파일. Task 3·4에서 단언을 더한다)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/lib/pageData/handbookDetailPage.ts frontend/tests/public-detail-query-contract.test.cjs`
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/handbook-term-entry.test.cjs
// Term detail A+B: crumb shell, entry head, two-column hero, see-also, inline actions, concept map, news mentions.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// data
const data = read('lib/pageData/handbookDetailPage.ts');
const columns = data.slice(data.indexOf('HANDBOOK_DETAIL_PUBLIC_COLUMNS = ['), data.indexOf("].join(', ')"));
for (const c of ['term_type', 'facet_intent', 'facet_volatility']) {
  assert(columns.includes(`'${c}'`), `detail columns include ${c}`);
}
assert.strictEqual((data.match(/\.from\('news_posts'\)/g) || []).length, 1, 'one news query: real mentions only (latest-news fallback removed)');
assert(!/recentNewsRes|backfill/.test(data), 'fallback query and assignment removed');
assert(/\.or\(`tags\.cs\.\{\$\{term\.term\.toLowerCase\(\)\}\},title\.ilike\.%\$\{term\.term\}%`\)[\s\S]{0,120}\.limit\(5\)/.test(data), 'mentions query unchanged (max 5)');
assert(data.includes('relatedArticles = articlesRes.data ?? [];'), 'no mentions -> empty list');
assert(data.includes("import { orderBySlugs } from '../handbookFacets.js';"), 'imports orderBySlugs');
assert(data.includes('relatedTerms = orderBySlugs(relatedRes.data ?? [], term.related_term_slugs ?? []);'), 'related terms follow related_term_slugs order');

console.log('handbook-term-entry.test.cjs passed');
```

`public-detail-query-contract.test.cjs`(Edit 도구): handbook 필드 루프의 닫는 `}` 바로 다음, 즉

```js
  assert.match(handbook, new RegExp(`\\b${field}\\b`), `handbook detail contract must retain ${field}`);
}
```

뒤에 다음을 넣는다.

```js
for (const field of ['term_type', 'facet_intent', 'facet_volatility']) {
  assert.match(handbook, new RegExp(`'${field}'`), `handbook detail contract must include entry facet ${field}`);
}
```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
```
Expected: 둘 다 FAIL. 앞은 "detail columns include term_type", 뒤는 "handbook detail contract must include entry facet term_type".

- [ ] **Step 3: `handbookDetailPage.ts` 수정** (Edit 도구로만, 5곳)
  1. import 추가: `import { localField } from '../handbookUtils';` 바로 다음 줄에
     ```ts
     import { orderBySlugs } from '../handbookFacets.js';
     ```
  2. 열 추가: `'hero_news_context_en', 'references_ko', 'references_en', 'related_term_slugs',` 다음 줄(`].join(', ');` 앞)에
     ```ts
       'term_type', 'facet_intent', 'facet_volatility',
     ```
  3. fallback 쿼리 삭제: mentions 쿼리의 `.limit(5),` 바로 뒤의 주석 `// Pre-fetch recent news for backfill (avoids sequential query later)`부터 그 쿼리의 `.limit(3),`까지 8줄을 지운다. `term.related_term_slugs?.length` 줄은 남긴다.
  4. 구조 분해: `[articlesRes, recentNewsRes, relatedRes, sameCatRes]` → `[articlesRes, relatedRes, sameCatRes]`
  5. 대입 교체:
     ```ts
         // Use tag-matched articles, fall back to recent news
         relatedArticles = (articlesRes.data?.length ? articlesRes.data : recentNewsRes.data) ?? [];

         relatedTerms = relatedRes.data ?? [];
     ```
     →
     ```ts
         // Only news that actually mentions the term (no latest-news filler).
         relatedArticles = articlesRes.data ?? [];

         // .in() returns rows in DB order; show them in the editor's related_term_slugs order.
         relatedTerms = orderBySlugs(relatedRes.data ?? [], term.related_term_slugs ?? []);
     ```

Run: `tr -cd '\r' < frontend/src/lib/pageData/handbookDetailPage.ts | wc -c; wc -l < frontend/src/lib/pageData/handbookDetailPage.ts` → 두 숫자가 같다(199).

- [ ] **Step 4: 통과 확인**

Run:
```bash
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/handbook-facets.test.mjs
node frontend/tests/public-error-cache-policy.test.cjs
```
Expected: 모두 PASS.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/pageData/handbookDetailPage.ts frontend/tests/handbook-term-entry.test.cjs frontend/tests/public-detail-query-contract.test.cjs
git commit -m "feat: load term facets, keep related term order and drop latest-news filler"
```

---

## Task 3: 용어 상세 화면 (Shell crumb·컴포넌트·판·페이지·CSS·테스트 갱신·목차 삭제)

**Files:**
- Create: `frontend/src/components/handbook/HandbookEntryHead.astro`, `HandbookXref.astro`, `HandbookConceptMap.astro`, `HandbookNewsMentions.astro`(모두 `frontend/src/components/handbook/`)
- Modify:
  - `frontend/src/components/newsprint/NewsprintShell.astro`(**BOM → Edit 도구만**)
  - `frontend/src/components/newsprint/HandbookHeroCard.astro`(전체 교체)
  - `frontend/src/pages/ko/handbook/[slug].astro`, `frontend/src/pages/en/handbook/[slug].astro`(전체 교체)
  - `frontend/src/styles/global.css`(새 블록 추가만. 옛 CSS 삭제는 Task 4)
  - `frontend/tests/handbook-term-entry.test.cjs`, `frontend/tests/handbook-v2.test.cjs`, `frontend/tests/detail-rail-actions-placement.test.cjs`, `frontend/tests/sticky-reading-actions-structure.test.cjs`
- Delete (`git rm`): `frontend/src/components/newsprint/HandbookSectionNav.astro`

- [ ] **Step 0: 상태·사용처 확인**

Run:
```bash
git status --short -- frontend/src/components/newsprint/NewsprintShell.astro frontend/src/components/newsprint/HandbookHeroCard.astro "frontend/src/pages/ko/handbook/[slug].astro" "frontend/src/pages/en/handbook/[slug].astro" frontend/src/styles/global.css
grep -rn "HandbookSectionNav\|HandbookHeroCard\|newsprint-rail-search" frontend/src --include=*.astro --include=*.ts --include=*.js
```
Expected: status 출력 없음. grep은 두 용어 상세 페이지와 `HandbookSectionNav.astro`/`HandbookHeroCard.astro` 자신만 나온다. 다른 파일이 나오면 멈추고 보고한다.

- [ ] **Step 1: 실패하는 단언 추가** (Edit 도구로)

`handbook-term-entry.test.cjs`의 `console.log('handbook-term-entry.test.cjs passed');` **바로 위**에 넣는다. 블록과 `console.log` 줄 사이에는 빈 줄 한 줄을 둔다.

```js
// shell: crumb items replace issue/date only when given
const shell = read('components/newsprint/NewsprintShell.astro');
assert(/crumbItems\?: string\[\];/.test(shell), 'shell: optional crumbItems prop');
assert(shell.includes('{crumbItems ? (') && shell.includes("crumbItems.join(' · ')"), 'shell: crumb items joined with " · "');
assert(shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'shell: default crumb keeps issue/date');

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/[slug].astro`);
  assert(/<NewsprintShell[\s\S]*?compact[\s\S]*?rail=\{false\}[\s\S]*?crumbItems=\{crumbItems\}/.test(page), `${locale}: compact shell, no rail, crumb items`);
  assert(page.includes('backHref={`/${locale}/handbook/`}'), `${locale}: crumb back link to the glossary`);
  assert(page.includes(locale === 'ko' ? 'backLabel="AI 용어집"' : 'backLabel="AI Glossary"'), `${locale}: crumb label`);
  assert(page.includes('getHandbookCategoryLabel(locale, cat)'), `${locale}: crumb items are field labels`);
  assert(!/HandbookSideRail|HandbookSectionNav|ReadingActionsRail|slot="rail"|newsprint-rail-search|masthead=|subkicker=|handbook-detail-meta/.test(page), `${locale}: rail, masthead and field line removed`);
  for (const c of ['<HandbookEntryHead ', '<HandbookXref ', '<HandbookConceptMap ', '<HandbookNewsMentions ']) {
    assert(page.includes(c), `${locale}: uses ${c.trim()}`);
  }

  // inline actions: direct first child of the article layout, before __body (CSS > and order rely on it)
  const layoutAt = page.indexOf('<div class="reading-actions-layout reading-actions-layout--article">');
  const actionsAt = page.indexOf('<StickyReadingActions', layoutAt);
  const bodyAt = page.indexOf('<div class="reading-actions-layout__body">', layoutAt);
  assert(layoutAt > 0 && actionsAt > layoutAt && actionsAt < bodyAt, `${locale}: actions sit before the body inside the article layout`);
  assert(/<StickyReadingActions\s+locale=\{locale\}\s+variant="term"[\s\S]*?itemType="term"[\s\S]*?\/>/.test(page), `${locale}: term actions`);
  assert(!/<StickyReadingActions[^/]*placement=/.test(page), `${locale}: inline placement (default)`);

  // order: entry -> hero -> see also -> switcher -> body -> concept map -> news -> references -> reading end
  const order = ['<HandbookEntryHead ', '<HandbookHeroCard', '<HandbookXref ', 'class="switcher-bar"', 'id="handbook-body"', '<HandbookConceptMap ', '<HandbookNewsMentions ', '<HandbookReferences ', '<div data-reading-end>', 'class="handbook-bottom-nav"'].map((s) => page.indexOf(s));
  assert(order.every((i, n) => i > 0 && (n === 0 || i > order[n - 1])), `${locale}: block order`);
  const proseToMap = page.slice(page.indexOf('id="handbook-body"'), page.indexOf('<HandbookConceptMap '));
  assert(proseToMap.includes('</div>') && proseToMap.includes(')}'), `${locale}: end blocks sit outside #handbook-body`);

  // level switcher: bound once per page, scroll + progress events kept
  assert(page.includes("switcher.dataset.levelReady === 'true'") && page.includes("switcher.dataset.levelReady = 'true';"), `${locale}: level switcher double-binding guard`);
  assert(page.includes("document.addEventListener('astro:page-load', initLevelSwitcher);") && /\n  initLevelSwitcher\(\);\n/.test(page), `${locale}: page-load + immediate init`);
  assert.strictEqual((page.match(/onSessionReady\(\(session\) =>/g) || []).length, 1, `${locale}: saved level applied from one place`);
  assert(page.includes("document.querySelector('.handbook-detail-title')?.scrollIntoView") && page.includes("new Event('reading-content-changed')"), `${locale}: scroll target + progress event kept`);
}
const en = read('pages/en/handbook/[slug].astro');
assert(en.indexOf("t[locale]['handbook.translationPending']") > 0 && en.indexOf("t[locale]['handbook.translationPending']") < en.indexOf('<HandbookEntryHead '), 'en: translation notice between crumb and entry');
assert(!fs.existsSync(path.join(src, 'components/newsprint/HandbookSectionNav.astro')), 'section nav deleted');

// components
const head = read('components/handbook/HandbookEntryHead.astro');
for (const s of ["'표제어'", "'Entry'", '<header class="handbook-entry">', '<h1 class="handbook-detail-title">', 'class="handbook-detail-korean"', 'class="handbook-detail-subtitle"', 'entryGrammar(locale, term)', '{grammar && <p class="handbook-entry-gram">{grammar}</p>}']) {
  assert(head.includes(s), `entry head: ${s}`);
}
const xref = read('components/handbook/HandbookXref.astro');
for (const s of ['→ 함께 볼 말', '→ See also', '→ 같은 분야', '→ Same field', '<nav class="handbook-xref" aria-label={copy.aria}>', '<span class="handbook-xref-label">', 'termNames(t, locale).name']) {
  assert(xref.includes(s), `xref: ${s}`);
}
const map = read('components/handbook/HandbookConceptMap.astro');
for (const s of ["'개념 지도'", "'Concept map'", '.slice(0, 6)', 'conceptMapNodes(items.length', '<a class="handbook-concept-map-node" href={l.href} aria-label={l.name}>', '<g class="handbook-concept-map-center" aria-hidden="true">', 'role="group"', '{links.length > 0 && (', '<h2 class="news-end-title"']) {
  assert(map.includes(s), `concept map: ${s}`);
}
assert(!map.includes('role="img"'), 'concept map is a group of links, not an image');
const news = read('components/handbook/HandbookNewsMentions.astro');
for (const s of ["'최근 뉴스에서'", "'In recent news'", 'postTypeLabel(locale, a.post_type)', '{articles.length > 0 && (', 'articles.slice(0, 5)', '<h2 class="news-end-title"']) {
  assert(news.includes(s), `news mentions: ${s}`);
}
const hero = read('components/newsprint/HandbookHeroCard.astro');
for (const s of ['뉴스에서는 이렇게 쓰여요', 'How the news uses it', 'role="heading" aria-level="2"', 'handbook-hero-card--solo', 'class="handbook-hero-card__plate"', ':global([data-theme="dark"]) .handbook-hero-card__plate']) {
  assert(hero.includes(s), `hero: ${s}`);
}
assert(/:global\(\[data-theme="dark"\]\) \.handbook-hero-card__plate \{[^}]*var\(--color-bg-tertiary\)/.test(hero), 'hero: dark plate uses bg-tertiary');
assert(/@media \(max-width: 767px\) \{\s*\.handbook-hero-card \{\s*grid-template-columns: minmax\(0, 1fr\);/.test(hero), 'hero: one column on mobile');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/font-size:\s*3rem/.test(rule('.handbook-entry .handbook-detail-title')), 'headword ~3rem');
assert(/font-weight:\s*600/.test(rule('.handbook-entry .handbook-detail-korean')) && rule('.handbook-entry .handbook-detail-korean').includes('var(--font-heading)'), 'Korean name in Hahmlet 600');
assert(rule('.handbook-entry .handbook-detail-subtitle').includes('var(--font-masthead)'), 'full name in Newsreader');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.handbook-entry')), 'entry closes with a 2px ink rule');
assert(rule('.handbook-entry-gram').includes('var(--color-text-secondary)'), 'grammar line style');
assert(/width:\s*100%/.test(rule('.handbook-concept-map-svg')) && /height:\s*auto/.test(rule('.handbook-concept-map-svg')), 'concept map scales to the column');
assert(rule('[data-theme="dark"] .handbook-concept-map-center circle').includes('var(--color-bg-tertiary)'), 'dark centre circle uses bg-tertiary');
assert(rule('.handbook-concept-map-node:focus-visible').includes('outline'), 'map links show focus');
const mobileAt = css.indexOf('/* Handbook term entry: mobile */');
assert(mobileAt > 0, 'term entry mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.handbook-entry \.handbook-detail-title\s*\{[^}]*font-size:\s*2\.4rem/.test(mobile), 'mobile headword 2.4rem');
assert(/\.handbook-news-mentions a\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto/.test(mobile), 'mobile news rows wrap');
```

`handbook-v2.test.cjs`(Edit 도구): 
- `assert(!/handbook-detail-meta[\s\S]{0,400}<span style=/.test(page), `${p} meta spans have no inline styles`);`
  →
  ```js
    assert(!page.includes('handbook-detail-meta') && page.includes('crumbItems={crumbItems}'), `${p} field labels moved to the crumb`);
  ```
- `rule('.handbook-detail-meta')` accent 단언, `learning-check`·`level-data`·`onSessionReady`·`data-admin-only`·레벨 버튼 단언, `.handbook-toc__title` 단언은 **이번 Step에서는 그대로** 둔다(목차 CSS는 Task 4에서 지운다).

`detail-rail-actions-placement.test.cjs`(Edit 도구): 
```js
assertIncludes(handbookEn, '<ReadingActionsRail', 'handbook EN right rail action wrapper');
assertIncludes(handbookKo, '<ReadingActionsRail', 'handbook KO right rail action wrapper');
```
→
```js
if (handbookEn.includes('<ReadingActionsRail')) throw new Error('handbook EN has no right rail');
if (handbookKo.includes('<ReadingActionsRail')) throw new Error('handbook KO has no right rail');
assertIncludes(handbookEn, '<StickyReadingActions', 'handbook EN inline term actions');
assertIncludes(handbookKo, '<StickyReadingActions', 'handbook KO inline term actions');
```
(블로그 단언과 `.newsprint-rail-stack {` CSS 단언은 그대로 둔다.)

`sticky-reading-actions-structure.test.cjs`(Edit 도구): 59–60행
```js
assertIncludes(handbookEn, '<ReadingActionsRail', 'handbook EN rail action wrapper');
assertIncludes(handbookKo, '<ReadingActionsRail', 'handbook KO rail action wrapper');
```
→
```js
assertIncludes(handbookEn, '<StickyReadingActions', 'handbook EN inline term actions');
assertIncludes(handbookKo, '<StickyReadingActions', 'handbook KO inline term actions');
assertIncludes(handbookEn, '<div class="reading-actions-layout reading-actions-layout--article">', 'handbook EN article action layout');
assertIncludes(handbookKo, '<div class="reading-actions-layout reading-actions-layout--article">', 'handbook KO article action layout');
```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/handbook-v2.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/sticky-reading-actions-structure.test.cjs
```
Expected:
- `handbook-term-entry`: FAIL "shell: optional crumbItems prop"
- `handbook-v2`: FAIL "pages/ko/handbook/[slug].astro field labels moved to the crumb"
- `detail-rail-actions-placement`: FAIL "handbook EN has no right rail"
- `sticky-reading-actions-structure`: 기준선과 같은 "Missing helpful action marker" (이 테스트는 우리 단언 전에 실패한다)

- [ ] **Step 3: `NewsprintShell.astro`에 `crumbItems`** (Edit 도구로만, 2곳. BOM 유지)
  1. Props와 구조 분해:
     ```astro
       backLabel?: string;
     }

     const { locale, masthead = '', editionLabel, subkicker, publishedAt, rail = true, compact = false, backHref, backLabel } = Astro.props;
     ```
     →
     ```astro
       backLabel?: string;
       /** compact only: shown instead of the issue/date, joined with ' · ' (e.g. handbook fields) */
       crumbItems?: string[];
     }

     const { locale, masthead = '', editionLabel, subkicker, publishedAt, rail = true, compact = false, backHref, backLabel, crumbItems } = Astro.props;
     ```
  2. crumb 본문:
     ```astro
           <a href={backHref ?? `/${locale}/news/`}>← {backLabel ?? (isKo ? 'AI 뉴스' : 'AI News')}</a>
           <span>{issueLabel(locale, issueNumber(displayDate))}</span>
           <span data-local-date data-date-iso={browserDateIso} data-date-locale={browserLocale}>{dateLabel}</span>
         </nav>
     ```
     →
     ```astro
           <a href={backHref ?? `/${locale}/news/`}>← {backLabel ?? (isKo ? 'AI 뉴스' : 'AI News')}</a>
           {crumbItems ? (
             crumbItems.length > 0 && <span class="newsprint-crumb-items">{crumbItems.join(' · ')}</span>
           ) : (
             <>
               <span>{issueLabel(locale, issueNumber(displayDate))}</span>
               <span data-local-date data-date-iso={browserDateIso} data-date-locale={browserLocale}>{dateLabel}</span>
             </>
           )}
         </nav>
     ```

Run: `head -c3 frontend/src/components/newsprint/NewsprintShell.astro | od -c | head -1` → `357 273 277`.

- [ ] **Step 4: `HandbookEntryHead.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/handbook/HandbookEntryHead.astro
// Term detail: dictionary headword block — label, headword (+ Korean name on KO), full name, grammar line.
// h1 keeps .handbook-detail-title: the level switcher scrolls back to it.
import { entryGrammar } from '../../lib/handbookFacets.js';

interface EntryTerm {
  term: string;
  korean_name?: string | null;
  term_full?: string | null;
  term_type?: string | null;
  facet_intent?: string[] | null;
  facet_volatility?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  term: EntryTerm;
}

const { locale, term } = Astro.props;
const isKo = locale === 'ko';
const label = isKo ? '표제어' : 'Entry';
const grammar = entryGrammar(locale, term);
const fullName = term.term_full && term.term_full !== term.term ? term.term_full : '';
---

<header class="handbook-entry">
  <p class="handbook-entry-label">{label}</p>
  <h1 class="handbook-detail-title">
    {term.term}{isKo && term.korean_name && <span class="handbook-detail-korean">{term.korean_name}</span>}
  </h1>
  {fullName && <p class="handbook-detail-subtitle">{fullName}</p>}
  {grammar && <p class="handbook-entry-gram">{grammar}</p>}
</header>
```

- [ ] **Step 5: `HandbookXref.astro` 작성** (Write 도구로. `→`는 문자 그대로)

```astro
---
// frontend/src/components/handbook/HandbookXref.astro
// Term detail: "→ 함께 볼 말" — curated related terms (editorial order), else same-field terms.
import { termNames } from '../../lib/handbookShelves.js';

interface XrefTerm {
  slug: string;
  term: string;
  korean_name?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  relatedTerms: XrefTerm[];
  sameCategoryTerms: XrefTerm[];
}

const { locale, relatedTerms, sameCategoryTerms } = Astro.props;
const isKo = locale === 'ko';
const curated = relatedTerms.length > 0;
const items = curated ? relatedTerms : sameCategoryTerms;
const copy = curated
  ? (isKo ? { label: '→ 함께 볼 말', aria: '함께 볼 말' } : { label: '→ See also', aria: 'See also' })
  : (isKo ? { label: '→ 같은 분야', aria: '같은 분야' } : { label: '→ Same field', aria: 'Same field' });
---

{items.length > 0 && (
  <nav class="handbook-xref" aria-label={copy.aria}>
    <span class="handbook-xref-label">{copy.label}</span>
    <ul class="handbook-xref-list">
      {items.map((t) => (
        <li><a href={`/${locale}/handbook/${t.slug}/`}>{termNames(t, locale).name}</a></li>
      ))}
    </ul>
  </nav>
)}
```

- [ ] **Step 6: `HandbookConceptMap.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/handbook/HandbookConceptMap.astro
// Term detail end block: server-rendered concept map. Ink circle = this term, up to 6 linked terms around it
// (curated related terms, else same-field terms). A group of links, not an image. Lives outside
// #handbook-body / .newsprint-prose (the level switch replaces that innerHTML; the popup script owns prose links).
import { termNames } from '../../lib/handbookShelves.js';
import { CONCEPT_MAP, centerLabel, conceptMapNodes, nodeLabel } from '../../lib/conceptMap.js';

interface MapTerm {
  slug: string;
  term: string;
  korean_name?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  term: MapTerm;
  relatedTerms: MapTerm[];
  sameCategoryTerms: MapTerm[];
}

const { locale, term, relatedTerms, sameCategoryTerms } = Astro.props;
const isKo = locale === 'ko';
const heading = isKo ? '개념 지도' : 'Concept map';
const items = (relatedTerms.length > 0 ? relatedTerms : sameCategoryTerms).slice(0, 6);
const { width, height, cx, cy, rx, ry, centerRadius, nodeRadius, fontSize } = CONCEPT_MAP;
const nodes = conceptMapNodes(items.length, { cx, cy, rx, ry });
const center = centerLabel(termNames(term, locale).name);
const links = items.map((item, i) => {
  const name = termNames(item, locale).name;
  return { href: `/${locale}/handbook/${item.slug}/`, name, node: nodes[i], label: nodeLabel(name, nodes[i]) };
});
---

{links.length > 0 && (
  <section class="handbook-concept-map" aria-labelledby="handbook-concept-map-title">
    <h2 class="news-end-title" id="handbook-concept-map-title">{heading}</h2>
    <svg
      class="handbook-concept-map-svg"
      viewBox={`0 0 ${width} ${height}`}
      role="group"
      aria-labelledby="handbook-concept-map-title"
    >
      <g aria-hidden="true">
        {links.map((l) => (
          <line class="handbook-concept-map-edge" x1={cx} y1={cy} x2={l.node.x} y2={l.node.y} />
        ))}
      </g>
      <g class="handbook-concept-map-center" aria-hidden="true">
        <circle cx={cx} cy={cy} r={centerRadius} />
        <text text-anchor="middle" font-size={center.fontSize}>
          {center.lines.map((line) => <tspan x={cx} y={line.y}>{line.text}</tspan>)}
        </text>
      </g>
      {links.map((l) => (
        <a class="handbook-concept-map-node" href={l.href} aria-label={l.name}>
          <circle cx={l.node.x} cy={l.node.y} r={nodeRadius} />
          <text x={l.label.x} y={l.label.y} text-anchor={l.node.anchor} font-size={fontSize}>{l.label.text}</text>
        </a>
      ))}
    </svg>
  </section>
)}
```

- [ ] **Step 7: `HandbookNewsMentions.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/handbook/HandbookNewsMentions.astro
// Term detail end block: news that actually mentions the term (max 5). Nothing when there are none.
import { postTypeLabel } from '../../lib/postType.js';

interface Mention {
  title: string;
  slug: string;
  published_at?: string | null;
  post_type?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  articles: Mention[];
}

const { locale, articles } = Astro.props;
const isKo = locale === 'ko';
const heading = isKo ? '최근 뉴스에서' : 'In recent news';
const formatDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString(isKo ? 'ko-KR' : 'en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '';
---

{articles.length > 0 && (
  <section class="handbook-news-mentions" aria-labelledby="handbook-news-mentions-title">
    <h2 class="news-end-title" id="handbook-news-mentions-title">{heading}</h2>
    <ul>
      {articles.slice(0, 5).map((a) => (
        <li>
          <a href={`/${locale}/news/${a.slug}/`}>
            <span class="handbook-news-mentions-type">{postTypeLabel(locale, a.post_type)}</span>
            <span class="handbook-news-mentions-title">{a.title}</span>
            {a.published_at && <time class="handbook-news-mentions-date" datetime={a.published_at}>{formatDate(a.published_at)}</time>}
          </a>
        </li>
      ))}
    </ul>
  </section>
)}
```

- [ ] **Step 8: `HandbookHeroCard.astro` 전체 교체** (Read 후 **Write 도구로**. 정규식·주석에 백슬래시가 있다. props는 그대로)

```astro
---
/**
 * HandbookHeroCard — level-independent block shown above the Basic/Advanced switcher.
 *
 * Two columns: the definition (left) and an ink plate "뉴스에서는 이렇게 쓰여요" with up to
 * 3 news-context lines (right; bg-tertiary in the dark theme). Without lines the definition takes
 * the full width; on mobile the plate sits under the definition.
 *
 * Plans: vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md §4,
 *        vault/09-Implementation/plans/2026-10-17-handbook-term-entry.md
 */

interface Props {
  definition: string | null;
  newsContext: string | null;   // raw \n-separated lines
  locale: 'ko' | 'en';
  backUrl?: string | null;
}

const { definition, newsContext, locale, backUrl = null } = Astro.props;

// Parse news context defensively (may be empty, may have stray whitespace)
const lines = (newsContext || '')
  .split('\n')
  .map(l => l.trim())
  .filter(Boolean)
  .slice(0, 3);

const hasContext = lines.length > 0;
const heading = locale === 'ko' ? '뉴스에서는 이렇게 쓰여요' : 'How the news uses it';
const backLabel = locale === 'ko' ? '기사로 돌아가기' : 'Back to the article';
---

{(definition || hasContext) && (
  <aside
    class={`handbook-hero-card${definition && hasContext ? '' : ' handbook-hero-card--solo'}`}
    aria-label={locale === 'ko' ? '핵심 요약' : 'Key summary'}
  >
    {definition && (
      <p
        class="handbook-hero-card__definition"
        set:html={definition.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}
      />
    )}
    {hasContext && (
      <div class="handbook-hero-card__plate">
        <div class="handbook-hero-card__heading" role="heading" aria-level="2">{heading}</div>
        <ul class="handbook-hero-card__news-list">
          {lines.map(line => (
            <li class="handbook-hero-card__news-line">{line}</li>
          ))}
        </ul>
      </div>
    )}
    {backUrl && (
      <a href={backUrl} class="handbook-hero-card__back">{backLabel}</a>
    )}
  </aside>
)}

<style>
  .handbook-hero-card {
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
    gap: 1.5rem;
    align-items: start;
    margin: 1.25rem 0 1.25rem;
  }
  .handbook-hero-card--solo {
    grid-template-columns: minmax(0, 1fr);
  }
  .handbook-hero-card__definition {
    font-size: 1.08rem;
    line-height: 1.75;
    margin: 0;
    color: var(--color-text-primary);
  }
  /* Same rules as the home keyword plate: ink in light themes, bg-tertiary in dark */
  .handbook-hero-card__plate {
    padding: 0.9rem 1.15rem 0.6rem;
    border-radius: 2px;
    background: var(--color-text-primary);
    color: var(--color-bg-primary);
  }
  :global([data-theme="dark"]) .handbook-hero-card__plate {
    background: var(--color-bg-tertiary);
    color: var(--color-text-primary);
  }
  .handbook-hero-card__heading {
    font-size: 0.72rem;
    font-weight: 600;
    opacity: 0.75;
    margin: 0 0 0.35rem;
  }
  .handbook-hero-card__news-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .handbook-hero-card__news-line {
    font-size: 0.9rem;
    line-height: 1.6;
    padding: 0.4rem 0;
    border-bottom: 1px dotted color-mix(in srgb, currentColor 35%, transparent);
  }
  .handbook-hero-card__news-line:last-child {
    border-bottom: none;
  }
  .handbook-hero-card__back {
    display: inline-block;
    margin-top: 0.5rem;
    font-size: 0.8125rem;
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid currentColor;
  }
  .handbook-hero-card__back:hover {
    color: var(--color-accent-hover);
  }
  @media (max-width: 767px) {
    .handbook-hero-card {
      grid-template-columns: minmax(0, 1fr);
      gap: 1rem;
    }
  }
</style>
```

- [ ] **Step 9: `pages/ko/handbook/[slug].astro` 전체 교체** (Read 후 Write 도구로)

바뀌는 점: import(레일 3종 제거, 새 컴포넌트 4개 + `StickyReadingActions`), `crumbItems` 계산, 마스트헤드 → compact Shell, `header`/분야 줄 → `<HandbookEntryHead>`, `<HandbookXref>`, 인라인 액션 + `--article` 레이아웃, 끝 블록 2개, `slot="rail"` 삭제, `initLevelSwitcher` 가드. 나머지 마크업·스크립트는 현행 그대로다.

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getHandbookCategoryLabel } from '../../../lib/handbookCategories';
import { levelLabels } from '../../../lib/handbookUtils';
import { getHandbookDetailPageData } from '../../../lib/pageData/handbookDetailPage';
import NewsprintShell from '../../../components/newsprint/NewsprintShell.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';
import HandbookHeroCard from '../../../components/newsprint/HandbookHeroCard.astro';
import HandbookReferences from '../../../components/newsprint/HandbookReferences.astro';
import HandbookEntryHead from '../../../components/handbook/HandbookEntryHead.astro';
import HandbookXref from '../../../components/handbook/HandbookXref.astro';
import HandbookConceptMap from '../../../components/handbook/HandbookConceptMap.astro';
import HandbookNewsMentions from '../../../components/handbook/HandbookNewsMentions.astro';
import PreviewReadonlyBanner from '../../../components/common/PreviewReadonlyBanner.astro';
import StickyReadingActions from '../../../components/common/StickyReadingActions.astro';
import ReadingProgressBar from '../../../components/common/ReadingProgressBar.astro';
import ContentFeedback from '../../../components/common/ContentFeedback.astro';

const locale = 'ko';
const { slug } = Astro.params;
const pageSlug = slug ?? '';
const previewRequested = Astro.url.searchParams.get('preview') === '1';
const previewMode = previewRequested && !!Astro.locals.isAdmin;
const previewLevel = Astro.url.searchParams.get('previewLevel');

const {
  term,
  termError,
  definition,
  levelHtmlMap,
  activeLevel,
  htmlContent,
  showLevelSwitcher,
  relatedArticles,
  relatedTerms,
  sameCategoryTerms,
  handbookTermsJson,
  // Level-independent redesign fields (2026-04-10)
  heroNewsContext,
  references,
} = await getHandbookDetailPageData({
  locale,
  slug: pageSlug,
  previewMode,
  locals: Astro.locals,
  previewLevel,
});

if (termError) {
  Astro.response.status = 503;
} else if (!term) {
  Astro.response.status = 404;
}

const user = Astro.locals.user;
const pageTitle = term
  ? (term.korean_name ? `${term.term} (${term.korean_name})` : term.term)
  : t[locale]['handbook.notfound'];
const pageDescription = definition ? definition.slice(0, 150) : '';
const crumbItems: string[] = (term?.categories || [])
  .map((cat: string) => getHandbookCategoryLabel(locale, cat))
  .filter((label: string | null): label is string => Boolean(label));
---

<MainLayout
  title={`${pageTitle} · AI 용어집`}
  description={pageDescription}
  locale={locale}
  slug={`handbook/${pageSlug}/`}
  previewMode={previewMode}
  needsKatex={true}
>
  <NewsprintShell
    locale={locale}
    compact
    rail={false}
    backHref={`/${locale}/handbook/`}
    backLabel="AI 용어집"
    crumbItems={crumbItems}
  >
    <form class="handbook-detail-search handbook-search-sticky handbook-search-sticky--detail" action={`/${locale}/handbook/`} method="get">
      <input
        type="text"
        name="q"
        aria-label={t[locale]['handbook.search']}
        placeholder={t[locale]['handbook.search']}
        class="handbook-search-input"
      />
    </form>

    {termError ? (
      <NewsprintNotice
        variant="error"
        message={t[locale]['handbook.error']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : !term ? (
      <NewsprintNotice
        variant="notfound"
        message={t[locale]['handbook.notfound']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : (
      <article>
        {previewMode && (
          <>
            <!-- Admin preview -->
            <PreviewReadonlyBanner locale={locale} />
          </>
        )}
        <HandbookEntryHead locale={locale} term={term} />

        <HandbookHeroCard
          definition={definition}
          newsContext={heroNewsContext}
          locale={locale}
        />

        <HandbookXref locale={locale} relatedTerms={relatedTerms} sameCategoryTerms={sameCategoryTerms} />

        <div class="newsprint-divider"></div>

        {showLevelSwitcher && (
          <div class="switcher-bar">
            <div class="switcher-bar-line"></div>
            <span class="switcher-bar-label">난이도</span>
            <div class="handbook-level-switcher">
              {(['basic', 'advanced'] as const).filter((level) => levelHtmlMap[level]).map((level) => (
                <button
                  type="button"
                  class={`handbook-level-btn ${level === activeLevel ? 'handbook-level-btn--active' : ''}`}
                  data-level={level}
                >
                  {levelLabels[locale]?.[level] || level}
                </button>
              ))}
            </div>
            <div class="switcher-bar-line"></div>
          </div>
        )}
        {showLevelSwitcher && (
          <template id="level-data" data-map={JSON.stringify(levelHtmlMap)}></template>
        )}

        {showLevelSwitcher ? (
          <div class="persona-float" id="level-float" aria-hidden="true">
            <a href={`/${locale}/handbook/`} class="persona-float-btn persona-float-btn--link">
              {t[locale]['handbook.back']}
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="margin-left:0.35em;flex-shrink:0;"><line x1="2" y1="4" x2="14" y2="4"/><line x1="2" y1="8" x2="14" y2="8"/><line x1="2" y1="12" x2="14" y2="12"/></svg>
            </a>
            {(['basic', 'advanced'] as const).filter((level) => levelHtmlMap[level]).map((level) => (
              <button
                type="button"
                class={`persona-float-btn ${level === activeLevel ? 'persona-float-btn--active' : ''}`}
                data-level={level}
              >
                {levelLabels[locale]?.[level] || level}
              </button>
            ))}
          </div>
        ) : (
          <div class="persona-float persona-float--back" aria-label={t[locale]['handbook.back']}>
            <a href={`/${locale}/handbook/`} class="persona-float-btn persona-float-btn--link">
              {t[locale]['handbook.back']}
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="margin-left:0.35em;flex-shrink:0;"><line x1="2" y1="4" x2="14" y2="4"/><line x1="2" y1="8" x2="14" y2="8"/><line x1="2" y1="12" x2="14" y2="12"/></svg>
            </a>
          </div>
        )}

        <div class="reading-actions-layout reading-actions-layout--article">
          <StickyReadingActions
            locale={locale}
            variant="term"
            title={pageTitle}
            shareUrl={`${import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com'}/${locale}/handbook/${pageSlug}/`}
            itemId={term.id}
            itemType="term"
            previewMode={previewMode}
            isAuthenticated={!!user}
            articleRedirect={`/${locale}/handbook/${pageSlug}/`}
          />
          <div class="reading-actions-layout__body">
            {htmlContent && (
              <div class="newsprint-prose newsprint-prose--no-dropcap" id="handbook-body">
                <Fragment set:html={htmlContent} />
              </div>
            )}
            <HandbookConceptMap locale={locale} term={term} relatedTerms={relatedTerms} sameCategoryTerms={sameCategoryTerms} />
            <HandbookNewsMentions locale={locale} articles={relatedArticles} />
            <HandbookReferences references={references} locale={locale} />
            <div data-reading-end></div>
            {!previewMode && (
              <div class="handbook-action-bar" data-auth-only hidden>
                <button class="learning-check" data-term-id={term.id} data-status="none">
                  학습 완료 표시
                </button>
              </div>
            )}

            <ContentFeedback
              sourceType="handbook"
              sourceId={term.id}
              locale={locale}
              isAuthenticated={!!user}
              loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
              previewMode={previewMode}
            />

            {!previewMode && (
              <div class="newsprint-admin-actions" data-toolbar-id={term.id} data-toolbar-api="/api/admin/handbook/status" data-admin-only hidden={!Astro.locals.isAdmin}>
                <a href={`/admin/handbook/edit/${pageSlug}`} class="newsprint-admin-action-btn">Edit</a>
                <button type="button" class="newsprint-admin-action-btn newsprint-admin-action-btn--unpublish">Unpublish</button>
              </div>
            )}

            <nav class="handbook-bottom-nav" aria-label="핸드북 내비게이션">
              <a href={`/${locale}/handbook/`} class="handbook-nav-link">
                {t[locale]['handbook.back']}
              </a>
            </nav>
          </div>
        </div>
      </article>
      <ReadingProgressBar locale="ko" />
    )}
  </NewsprintShell>
  {Object.keys(handbookTermsJson).length > 0 && (
    <script type="application/json" id="handbook-terms-data" set:html={JSON.stringify(handbookTermsJson)} />
  )}
</MainLayout>

<script>
  import '../../../scripts/bookmark';
  import '../../../scripts/share';
  import '../../../scripts/handbook-popup';
  import '../../../scripts/contentFeedback';
  import '../../../scripts/code-toggle';
  import { onSessionReady, type SessionInfo } from '../../../scripts/session';

  // 조회수 증가 (모든 방문자 — 로그인 불필요)
  function trackView(): void {
    if (document.body.dataset.previewMode === 'true') return;
    const tid = document.querySelector('[data-term-id]')?.getAttribute('data-term-id');
    if (!tid) return;
    const url = import.meta.env.PUBLIC_SUPABASE_URL;
    const key = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) return;
    fetch(`${url}/rest/v1/rpc/increment_handbook_view_count`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: key, Authorization: `Bearer ${key}` },
      body: JSON.stringify({ term_id: tid }),
    }).catch(() => {});
  }

  function applyLearningState(checkBtn: HTMLButtonElement, id: string | undefined, status: string): void {
    if (id) checkBtn.dataset.learningId = id;
    checkBtn.dataset.status = status;
    checkBtn.classList.toggle('learning-check--done', status === 'learned');
    checkBtn.textContent = status === 'learned' ? '학습 완료' : '학습 완료 표시';
  }

  function initHandbookUserFeatures(session: SessionInfo): void {
    if (document.body.dataset.previewMode === 'true' || !session.authenticated) return;
    const checkBtn = document.querySelector('.learning-check') as HTMLButtonElement | null;
    const termId = checkBtn?.dataset.termId;
    if (!checkBtn || !termId) return;

    fetch('/api/user/reading-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_type: 'term', item_id: termId }),
    }).catch(() => {});

    // Records the read and returns the row, so the learned toggle works on first visit.
    fetch('/api/user/learning-progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ term_id: termId }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((row: { id?: string; status?: string } | null) => {
        if (row?.id) applyLearningState(checkBtn, row.id, row.status || 'read');
      })
      .catch(() => {});

    checkBtn.addEventListener('click', async () => {
      const lpId = checkBtn.dataset.learningId;
      const currentStatus = checkBtn.dataset.status;
      if (!lpId || checkBtn.disabled) return;

      checkBtn.disabled = true;
      const prevText = checkBtn.textContent;
      checkBtn.textContent = '...';

      const newStatus = currentStatus === 'learned' ? 'read' : 'learned';
      try {
        const res = await fetch(`/api/user/learning-progress?id=${lpId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        });
        if (!res.ok) {
          checkBtn.textContent = prevText;
          checkBtn.disabled = false;
          return;
        }

        applyLearningState(checkBtn, undefined, newStatus);
      } catch {
        checkBtn.textContent = prevText;
      } finally {
        checkBtn.disabled = false;
      }
    });
  }

  function initAdminActions(): void {
    if (document.body.dataset.previewMode === 'true') return;
    const actions = document.querySelector('.newsprint-admin-actions') as HTMLElement | null;
    if (!actions) return;

    const btn = actions.querySelector('.newsprint-admin-action-btn--unpublish');
    btn?.addEventListener('click', async () => {
      if (!confirm('이 용어를 비공개로 전환할까요?')) return;

      const id = actions.dataset.toolbarId;
      const api = actions.dataset.toolbarApi;
      if (!id || !api) return;

      try {
        const res = await fetch(api, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, action: 'unpublish' }),
        });

        if (res.ok) {
          const editLink = actions.querySelector('a') as HTMLAnchorElement | null;
          window.location.href = editLink?.href || '/admin';
        } else {
          const err = await res.json().catch(() => ({ error: 'Unknown error' }));
          alert(`비공개 전환 실패: ${err.error || err.detail}`);
        }
      } catch {
        alert('비공개 전환 실패: 네트워크 오류');
      }
    });
  }

  let _levelObserver: IntersectionObserver | null = null;

  function initLevelSwitcher(): void {
    const switcher = document.querySelector<HTMLElement>('.handbook-level-switcher');
    // astro:page-load also fires on the first load, right after the direct call below: bind once per page.
    if (!switcher || switcher.dataset.levelReady === 'true') return;
    switcher.dataset.levelReady = 'true';
    if (_levelObserver) { _levelObserver.disconnect(); _levelObserver = null; }

    const template = document.getElementById('level-data') as HTMLTemplateElement | null;
    if (!template) return;
    const map: Record<string, string> = JSON.parse(template.dataset.map || '{}');
    const prose = document.getElementById('handbook-body');
    const floatEl = document.getElementById('level-float');
    if (!prose) return;

    let userPicked = false;

    function setActiveLevel(level: string, { scroll = true } = {}) {
      if (!map[level]) return;
      prose!.innerHTML = map[level];
      switcher!.querySelectorAll('.handbook-level-btn').forEach(b =>
        b.classList.toggle('handbook-level-btn--active',
          (b as HTMLElement).dataset.level === level));
      floatEl?.querySelectorAll('.persona-float-btn').forEach(b =>
        b.classList.toggle('persona-float-btn--active',
          (b as HTMLElement).dataset.level === level));
      if (scroll) document.querySelector('.handbook-detail-title')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // 본문 높이 변경 → 프로그레스바 재계산
      requestAnimationFrame(() => window.dispatchEvent(new Event('reading-content-changed')));
    }

    switcher.addEventListener('click', (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('.handbook-level-btn');
      if (btn) { userPicked = true; setActiveLevel(btn.dataset.level!); }
    });

    // Cached HTML starts on 'basic'; apply the signed-in reader's saved level (once per page).
    onSessionReady((session) => {
      const saved = session.handbookLevel;
      const active = switcher.querySelector<HTMLElement>('.handbook-level-btn--active')?.dataset.level;
      if (!userPicked && saved && saved !== active && map[saved]) setActiveLevel(saved, { scroll: false });
    });

    if (floatEl) {
      floatEl.addEventListener('click', (e) => {
        const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('.persona-float-btn');
        if (btn) { userPicked = true; setActiveLevel(btn.dataset.level!); }
      });

      let hasShownOnce = false;
      _levelObserver = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) {
          floatEl.classList.add('persona-float--visible');
          floatEl.removeAttribute('aria-hidden');
          if (!hasShownOnce) {
            hasShownOnce = true;
            floatEl.classList.add('persona-float--pulse');
            floatEl.addEventListener('animationend', () =>
              floatEl.classList.remove('persona-float--pulse'), { once: true });
          }
        } else {
          floatEl.classList.remove('persona-float--visible');
          floatEl.setAttribute('aria-hidden', 'true');
        }
      }, { threshold: 0.1 });

      _levelObserver.observe(switcher);
    }
  }

  document.addEventListener('astro:page-load', trackView);
  document.addEventListener('astro:page-load', () => onSessionReady(initHandbookUserFeatures));
  document.addEventListener('astro:page-load', initAdminActions);
  document.addEventListener('astro:page-load', initLevelSwitcher);
  initLevelSwitcher();
</script>
```

- [ ] **Step 10: `pages/en/handbook/[slug].astro` 전체 교체** — Step 9의 KO 파일에서 **아래 14곳만** 바꾼 내용이다(Read 후 Write 도구로). 그 밖의 줄은 한 글자도 다르지 않아야 한다(스크립트 안의 한국어 주석 `// 본문 높이 변경 → 프로그레스바 재계산`도 현행 EN처럼 그대로 둔다).

| # | KO | EN |
|---|---|---|
| 1 | `const locale = 'ko';` | `const locale = 'en';` |
| 2 | `const user = Astro.locals.user;` + 3줄 `pageTitle`(korean_name 괄호) | `const isEnFallback = term && !term.definition_en && term.definition_ko;` / `const user = Astro.locals.user;` / `const pageTitle = term ? term.term : t[locale]['handbook.notfound'];` |
| 3 | ``title={`${pageTitle} · AI 용어집`}`` | ``title={`${pageTitle} · AI Glossary`}`` |
| 4 | `backLabel="AI 용어집"` | `backLabel="AI Glossary"` |
| 5 | (미리보기 블록 `)}` 다음, `<HandbookEntryHead` 앞) 없음 | 현행 EN의 `{isEnFallback && (<div style="padding: 0.5rem 1rem; …">{t[locale]['handbook.translationPending']}</div>)}` 5줄 그대로 |
| 6 | `난이도` | `Difficulty` |
| 7 | 버튼 글자 `학습 완료 표시` | `Mark as Learned` |
| 8 | `aria-label="핸드북 내비게이션"` | `aria-label="Handbook navigation"` |
| 9 | `<ReadingProgressBar locale="ko" />` | `<ReadingProgressBar locale="en" />` |
| 10 | `// 조회수 증가 (모든 방문자 — 로그인 불필요)` | `// Increment view count (all visitors — no auth required)` |
| 11 | `'학습 완료' : '학습 완료 표시'` | `'Learned' : 'Mark as Learned'` |
| 12 | `confirm('이 용어를 비공개로 전환할까요?')` | `confirm('Unpublish this term?')` |
| 13 | ``alert(`비공개 전환 실패: ${err.error || err.detail}`)`` | ``alert(`Unpublish failed: ${err.error || err.detail}`)`` |
| 14 | `alert('비공개 전환 실패: 네트워크 오류')` | `alert('Unpublish failed: network error')` |

기계적으로 만들려면 아래 스크립트를 **scratchpad에** Write 도구로 저장해 `node <scratchpad>/derive-en.cjs frontend`로 돌린다(repo에 커밋하지 않는다). 각 치환이 정확히 1번 일치하지 않으면 멈춘다.

```js
// usage: node derive-en.cjs <frontendDir>
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
let s = fs.readFileSync(path.join(dir, 'src/pages/ko/handbook/[slug].astro'), 'utf8');
const pairs = [
  ["const locale = 'ko';", "const locale = 'en';"],
  [
    "const user = Astro.locals.user;\nconst pageTitle = term\n  ? (term.korean_name ? `${term.term} (${term.korean_name})` : term.term)\n  : t[locale]['handbook.notfound'];",
    "const isEnFallback = term && !term.definition_en && term.definition_ko;\nconst user = Astro.locals.user;\nconst pageTitle = term ? term.term : t[locale]['handbook.notfound'];",
  ],
  ['title={`${pageTitle} · AI 용어집`}', 'title={`${pageTitle} · AI Glossary`}'],
  ['backLabel="AI 용어집"', 'backLabel="AI Glossary"'],
  [
    "        )}\n        <HandbookEntryHead locale={locale} term={term} />",
    "        )}\n        {isEnFallback && (\n          <div style=\"padding: 0.5rem 1rem; background: var(--color-bg-secondary); border: 1px solid var(--color-border); margin-bottom: 1rem; font-size: 0.85rem; color: var(--color-text-muted);\">\n            {t[locale]['handbook.translationPending']}\n          </div>\n        )}\n        <HandbookEntryHead locale={locale} term={term} />",
  ],
  ['<span class="switcher-bar-label">난이도</span>', '<span class="switcher-bar-label">Difficulty</span>'],
  ['                  학습 완료 표시\n', '                  Mark as Learned\n'],
  ['aria-label="핸드북 내비게이션"', 'aria-label="Handbook navigation"'],
  ['<ReadingProgressBar locale="ko" />', '<ReadingProgressBar locale="en" />'],
  ['// 조회수 증가 (모든 방문자 — 로그인 불필요)', '// Increment view count (all visitors — no auth required)'],
  ["status === 'learned' ? '학습 완료' : '학습 완료 표시'", "status === 'learned' ? 'Learned' : 'Mark as Learned'"],
  ["confirm('이 용어를 비공개로 전환할까요?')", "confirm('Unpublish this term?')"],
  ['alert(`비공개 전환 실패: ${err.error || err.detail}`)', 'alert(`Unpublish failed: ${err.error || err.detail}`)'],
  ["alert('비공개 전환 실패: 네트워크 오류')", "alert('Unpublish failed: network error')"],
];
for (const [from, to] of pairs) {
  const n = s.split(from).length - 1;
  if (n !== 1) throw new Error(`expected exactly one match (${n}): ${from.slice(0, 60)}`);
  s = s.replace(from, () => to);
}
fs.writeFileSync(path.join(dir, 'src/pages/en/handbook/[slug].astro'), s);
console.log('en page derived');
```

Run: `diff "frontend/src/pages/ko/handbook/[slug].astro" "frontend/src/pages/en/handbook/[slug].astro"` → 위 표의 14곳만 나온다.

- [ ] **Step 11: CSS 추가** (Edit 도구로) — `global.css`의 `/* --- Handbook category page --- */` 주석 **바로 위**에 다음 블록을 넣는다(블록 끝의 빈 줄 한 줄 포함). 서가 작업의 `/* Handbook index: mobile */` 블록 뒤, 분야 페이지 블록 앞이다.

```css
/* Handbook term entry: headword, see-also, concept map, news mentions (scoped so the admin preview keeps its look) */
.handbook-entry {
  padding: 0.25rem 0 1rem;
  border-bottom: 2px solid var(--color-text-primary);
}

.handbook-entry-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0 0 0.4rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent);
}

.handbook-entry-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.handbook-entry .handbook-detail-title {
  font-size: 3rem;
  line-height: 1.1;
  letter-spacing: -0.04em;
  overflow-wrap: anywhere;
}

.handbook-entry .handbook-detail-korean {
  font-family: var(--font-heading);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--color-text-secondary);
  margin-left: 0.6rem;
}

.handbook-entry .handbook-detail-subtitle {
  font-family: var(--font-masthead);
  font-weight: 500;
  font-size: 1.1rem;
  color: var(--color-text-muted);
  margin: 0.35rem 0 0;
}

.handbook-entry-gram {
  margin: 0.6rem 0 0;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}

.handbook-xref {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 0.9rem;
  margin: 0 0 1rem;
}

.handbook-xref-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-accent);
}

.handbook-xref-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem 1rem;
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.handbook-xref-list a {
  font-family: var(--font-heading);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-primary);
  text-decoration: underline;
  text-decoration-color: var(--color-border);
  text-underline-offset: 3px;
}

.handbook-xref-list a:hover {
  color: var(--color-accent);
  text-decoration-color: currentColor;
}

.handbook-concept-map-svg {
  display: block;
  width: 100%;
  max-width: 560px;
  height: auto;
  margin: 0.75rem auto 0;
}

.handbook-concept-map-edge {
  stroke: var(--color-border);
  stroke-width: 1.5;
}

.handbook-concept-map-center circle {
  fill: var(--color-text-primary);
}

.handbook-concept-map-center text {
  fill: var(--color-bg-primary);
  font-family: var(--font-heading);
  font-weight: 700;
}

[data-theme="dark"] .handbook-concept-map-center circle {
  fill: var(--color-bg-tertiary);
}

[data-theme="dark"] .handbook-concept-map-center text {
  fill: var(--color-text-primary);
}

.handbook-concept-map-node circle {
  fill: var(--color-bg-primary);
  stroke: var(--color-accent);
  stroke-width: 2;
}

.handbook-concept-map-node text {
  fill: var(--color-text-primary);
  font-family: var(--font-heading);
  font-weight: 600;
}

.handbook-concept-map-node:hover text,
.handbook-concept-map-node:focus-visible text {
  fill: var(--color-accent);
}

.handbook-concept-map-node:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.handbook-news-mentions ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.handbook-news-mentions li {
  padding: 0.65rem 0;
  border-bottom: 1px dotted var(--color-border);
}

.handbook-news-mentions a {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: baseline;
  color: inherit;
  text-decoration: none;
}

.handbook-news-mentions-type {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-accent);
}

.handbook-news-mentions-title {
  font-family: var(--font-heading);
  font-size: 0.98rem;
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: -0.025em;
  transition: color 150ms ease;
}

.handbook-news-mentions a:hover .handbook-news-mentions-title {
  color: var(--color-accent);
}

.handbook-news-mentions-date {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Handbook term entry: mobile */
@media (max-width: 767px) {
  .handbook-entry .handbook-detail-title {
    font-size: 2.4rem;
  }

  .handbook-entry .handbook-detail-korean {
    font-size: 1.2rem;
  }

  .handbook-news-mentions a {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.2rem 0.75rem;
  }

  .handbook-news-mentions-title {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
```

- [ ] **Step 12: 목차 컴포넌트 삭제**

```bash
git rm frontend/src/components/newsprint/HandbookSectionNav.astro
grep -rn "HandbookSectionNav" frontend/src frontend/tests --include=*.astro --include=*.ts --include=*.js --include=*.cjs --include=*.mjs
```
Expected: grep은 `handbook-term-entry.test.cjs`의 부정 단언 줄만 나온다(`global.css`의 목차 주석은 Task 4에서 지운다).

- [ ] **Step 13: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/handbook-facets.test.mjs
node frontend/tests/handbook-v2.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/public-error-cache-policy.test.cjs
node frontend/tests/reading-actions-layout-regression.test.cjs
node frontend/tests/reading-actions-editorial-subtle.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/newsprint-local-date.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/hreflang-alt-slug.test.cjs
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/sticky-reading-actions-structure.test.cjs
node frontend/tests/admin-live-preview.test.cjs
node frontend/tests/handbook-detail-table-overflow.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 세 테스트를 뺀 모두 PASS(`newsprint-local-date`는 출력 없이 종료 코드 0), 빌드 "Complete!".
- `sticky-reading-actions-structure`는 "Missing helpful action marker", `admin-live-preview`는 "src/pages/admin/blog/edit/[slug].astro must sync preview state into URL history", `handbook-detail-table-overflow`는 "…compact horizontal scrollbar size on WebKit browsers" — 기준선과 **같은 메시지**여야 한다.

- [ ] **Step 14: 커밋**

```bash
git add frontend/src/components/handbook/HandbookEntryHead.astro frontend/src/components/handbook/HandbookXref.astro frontend/src/components/handbook/HandbookConceptMap.astro frontend/src/components/handbook/HandbookNewsMentions.astro frontend/src/components/newsprint/NewsprintShell.astro frontend/src/components/newsprint/HandbookHeroCard.astro "frontend/src/pages/ko/handbook/[slug].astro" "frontend/src/pages/en/handbook/[slug].astro" frontend/src/styles/global.css frontend/tests/handbook-term-entry.test.cjs frontend/tests/handbook-v2.test.cjs frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/sticky-reading-actions-structure.test.cjs
git commit -m "feat: handbook term entry with headword, see-also, concept map and inline actions"
```

(`git rm`으로 stage된 `HandbookSectionNav.astro` 삭제가 함께 커밋된다.)

---

## Task 4: 쓰지 않게 된 CSS 정리 (TDD)

**Files:**
- Modify: `frontend/src/styles/global.css`, `frontend/tests/handbook-term-entry.test.cjs`, `frontend/tests/handbook-v2.test.cjs`

- [ ] **Step 1: 다른 사용처 확인**

Run:
```bash
grep -rn "handbook-toc\|newsprint-rail-search" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "handbook-toc\|newsprint-rail-search" frontend/tests
```
Expected:
- 첫 grep: 결과 없음(Task 3에서 페이지·컴포넌트가 더 이상 쓰지 않는다). 결과가 있으면 멈추고 보고한다.
- 둘째 grep: `handbook-term-entry.test.cjs`의 부정 단언 1줄과 `handbook-v2.test.cjs` 47행 `rule('.handbook-toc__title')` 1줄. 후자는 Step 4에서 지운다.

- [ ] **Step 2: 실패하는 단언 추가** (Edit 도구로) — `handbook-term-entry.test.cjs`의 `console.log('handbook-term-entry.test.cjs passed');` **바로 위**에 넣는다. 블록과 `console.log` 줄 사이에는 빈 줄 한 줄을 둔다.

```js
// unused CSS removed (Task 4): the TOC was page-only, the rail search lived in the removed rail
for (const gone of ['.handbook-toc', 'HandbookSectionNav', '.newsprint-rail-search']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('  .handbook-search-sticky--detail {\n    display: none;'), 'desktop still hides the main-column search');
```

Run: `node frontend/tests/handbook-term-entry.test.cjs`
Expected: FAIL "unused CSS removed: .handbook-toc".

- [ ] **Step 3: CSS 삭제** (Edit 도구로). 정확히 아래 세 구간만 지운다.
  1. **레일 검색 기본 규칙**: `.newsprint-rail-stack { … }` 바로 다음의
     ```css
     .newsprint-rail-search {
       display: none;
     }

     ```
     (빈 줄 포함) — 뒤의 `@media (min-width: 1024px) {`는 남긴다.
  2. **레일 검색 데스크톱 규칙**: 같은 `@media (min-width: 1024px)` 블록 안의
     ```css
       /* Rail search: show on desktop */
       .newsprint-rail-search {
         display: block;
         margin-bottom: 0.75rem;
       }

     ```
     (빈 줄 포함) — 바로 뒤의 `/* Hide main-column search on desktop (detail pages only) */`와 `.handbook-search-sticky--detail { display: none; }`는 **남긴다**.
  3. **목차**: `/* ================================================================\n   HandbookSectionNav — client-side TOC in the side rail.` 주석 시작부터 `@media (max-width: 1024px) {\n  .handbook-toc {\n    display: none;\n  }\n}` 블록과 그 뒤 빈 줄까지(91줄). 바로 뒤의 `/* ===…\n   §6 Industry dialogue blockquote` 주석과 앞의 `.newsprint-prose .hb-related-terms__row-link …` 규칙은 **남긴다**.

Run: `grep -n "handbook-toc\|newsprint-rail-search\|HandbookSectionNav" frontend/src/styles/global.css` → 결과 없음.

- [ ] **Step 4: `handbook-v2.test.cjs`에서 목차 단언 삭제** (Edit 도구로)
  - 지울 줄: `assert(!rule('.handbook-toc__title').includes('uppercase'), 'toc title not uppercase');`
  - `rule('.handbook-section-label')` 단언은 남긴다.

- [ ] **Step 5: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/handbook-v2.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/product-filter-bar-mobile-sticky.test.cjs
node frontend/tests/news-article-find-structure.test.cjs
node frontend/tests/theme-palette.test.cjs
node frontend/tests/font-roles.test.cjs
cd frontend && npm run build
```
Expected: 모두 PASS, 빌드 "Complete!".

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/handbook-term-entry.test.cjs frontend/tests/handbook-v2.test.cjs
git commit -m "chore: remove handbook TOC and rail search CSS"
```

---

## Task 5: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름으로** 기준선(PASS 77 / FAIL 20)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선 20개와 같아야 한다(신규 FAIL 0). 실패 테스트의 첫 오류 메시지도 기준선과 같은지 본다.
  - 새 테스트 2개(`handbook-facets`, `handbook-term-entry`)는 PASS여야 한다 → PASS 79 / FAIL 20.
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × ≥1024px·375px × ko/en
  - 대상: `/…/handbook/rrf/`(연관 4, 판 있음), `/…/handbook/recurrent-mechanism/`(연관 없음 → 같은 분야, 품사 줄 없음, 뉴스 없음, 판 없음), `/…/handbook/supply-chain-attack/`(연관 없음, 뉴스 없음), `/ko/handbook/bm25/`(최근 뉴스 1건), `/ko/handbook/self-supervised-pretext-tasks/`(긴 중심 라벨 두 줄)
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`)
  - 개념 지도 텍스트가 viewBox 밖으로 나가지 않는지: `[...document.querySelectorAll('.handbook-concept-map-svg text')].map(t => t.getBBox())`의 x·x+width가 0–560 안
  - 대비 검사: 품사 줄, 표제어 라벨, 판 본문(다크 포함), 개념 지도 중심 글자(다크 포함), 최근 뉴스 날짜
  - ≥1024px: 본문 오른쪽 세로 액션 막대(sticky), 뜻풀이 2단. 375px: 뜻풀이 1단(판이 정의 아래), 함께 볼 말 줄바꿈, 하단 액션 바, 헤드워드 2.4rem
  - EN 번역 대기 용어(`definition_en` 없음)가 있으면 안내가 경로 줄과 표제어 사이에 보이는지
- [ ] 직접 클릭
  - 기초↔심화 전환: 본문 교체, 표제어로 스크롤, 한 번 클릭에 한 번만 바뀌는지(이중 바인딩 없음). 로그인 상태에서 저장된 레벨이 한 번만 적용되는지
  - 본문 용어 팝업(prose 안 링크), 저장 버튼(로그인/비로그인 안내), 공유 메뉴(데스크톱 왼쪽, 모바일 위로 열림)
  - 함께 볼 말·개념 지도 노드 클릭 → 해당 용어 상세로 이동(ViewTransitions 이동 뒤에도 레벨 스위처·액션 동작)
  - 경로 줄 "← AI 용어집" → 용어집 첫 화면
  - 학습 체크, 피드백, 관리자 버튼(관리자 로그인 시), 이전/다음
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 6: 문서

- [ ] 스펙 [[2026-10-17-handbook-term-entry-design]] Status를 `implemented (2026-10-17)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (2026-10-17)`로 바꾸고, 문서 끝에 "실행 결과"(커밋 해시, 테스트 이름 비교 결과, 매트릭스 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-HANDBOOK-INDEX` 항목 다음에 추가한다.
  `- [x] **REDESIGN-HANDBOOK-TERM** — 용어 상세를 사전 표제어(A) + 개념 지도(B)로: 경로 줄(분야 crumb), 표제어·품사 줄(유형·쓰임·변화 정도), 뜻풀이 + 먹색 판 2단, 함께 볼 말(편집 순서), 인라인 세로 액션, 개념 지도 SVG, 실제 언급 뉴스만, 레일·목차·마스트헤드 제거 — [[2026-10-17-handbook-term-entry-design]], [[2026-10-17-handbook-term-entry]]`
- [ ] `grep -rln "HandbookSectionNav\|handbook-toc\|HandbookSideRail\|연관 개념\|ReadingActionsRail" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획은 빼고, 용어 상세의 현재 구조를 설명하는 노트만 최소한으로 고친다(`HandbookSideRail`은 관리자 미리보기용으로 남았다는 점 유지).
- [ ] 알려진 한계를 실행 결과에 적는다: 개념 지도 관계 설명 없음(데이터 없음), 375px에서 지도 라벨 약 9.9px, 연관 용어가 있는 용어는 16/114뿐(나머지는 같은 분야 fallback, 순서는 DB 임의), mentions 필터 이스케이프(`,(){`)는 별도 후보.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-17-handbook-term-entry-design.md vault/09-Implementation/plans/2026-10-17-handbook-term-entry.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record handbook term entry redesign"
  ```

---

## 실행 결과 (2026-10-17)

- 커밋: `aefdee45` 라벨·개념 지도 계산, `40d68023` facet 컬럼·연관 순서·최신 뉴스 채우기 제거, `7ab1c1b8` 표제어·함께 볼 말·개념 지도·인라인 액션, `647deae5` 목차·레일 검색 CSS 삭제, `92b4b367` 한글명이 표제어와 같으면 숨김(브라우저 검증 중 발견: BM25 BM25).
- 테스트: 실패 목록이 기준선과 이름 기준 동일, 신규 FAIL 0. 빌드 성공. 계획 단계에서 scratch 복사본 + 운영 데이터 렌더로 사전 검증.
- 브라우저 클릭 검증(/ko/handbook/rrf/): 기초→심화 본문 교체, 용어 팝업(BM25), 저장 버튼 1개, 공유 메뉴 열림, 개념 지도 노드 4개 링크·aria-label, 함께 볼 말이 편집 순서(하이브리드 검색·BM25·벡터 검색·리랭킹). 레일·목차 없음.
- 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en, 대상 rrf·recurrent-mechanism(연관·유형·뉴스 없음 → 품사 줄 없음, 같은 분야)·bm25(뉴스 1건) — 가로 넘침 0, 대비 미달 0, 개념 지도 텍스트 잘림 0.
- 데이터 사실: 발행 114개 중 related_term_slugs가 있는 용어는 16개 → 대부분 "같은 분야" 지도.
