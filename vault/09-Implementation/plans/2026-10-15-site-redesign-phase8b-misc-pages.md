# 사이트 리디자인 8b단계(기타 페이지 정리) Implementation Plan

**Status:** done (2026-10-15) — 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** about, privacy, terms, 404, library, portfolio, settings 페이지에 남은 V2 위반 스타일을 정리한다. 다음 항목이 대상이다.
- 대문자와 넓은 자간
- 굵기 800/900
- 상자형 활성 탭
- 원형 번호
- 그라디언트
- 그림자
- 필요 없는 inline style

**Architecture:** 대부분 페이지의 scoped `<style>`과 `global.css`의 `.pf-*`, `.library-*`를 수정한다. 레이아웃 구조, 데이터 로딩, 스크립트, 인증 흐름은 바꾸지 않는다. 시안 없이 진행하는 정리 작업이며, 스펙 §7의 8단계에 해당한다.

**Tech Stack:** Astro v5, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

---

## 사전 정보 (실행자 필독)

### 작업 규칙
- 다른 세션과 작업 트리를 공유한다. 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인하고, 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- `git add`는 계획에 적힌 파일만 경로로 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이 들어간 파일은 Write/Edit 도구로 작성한다(Bash heredoc을 쓰면 백슬래시가 사라진다). `global.css`는 LF이고, 수정할 규칙은 셀렉터로 찾는다.
- dev 서버가 떠 있으면 `npm run build`가 EPERM으로 실패할 수 있다. 이때는 재시도를 반복하지 말고 보고한다.

### 유지할 것 (Supabase 세션 인계)
- about, privacy, terms(`/en`, `/ko`)는 CDN 캐시 대상이다. SSR 출력이 사용자 정보에 의존하면 안 된다.
- library, settings, portfolio, 404는 캐시 대상이 아니다. 이 페이지들이 서버에서 `Astro.locals.user`/`profile`을 쓰는 것은 정상이므로 **데이터 로딩은 건드리지 않는다**.
- library는 `ProductCard`를 재사용한다. 제품 카드 스타일은 8a에서 바꾸므로 여기서는 손대지 않는다.
- portfolio의 `.newsprint-tag` 칩은 알약 모양을 유지한다. `list-v2` 테스트가 이를 검사한다.
- library의 탭 패널 inline `display:none`과 탭 전환 스크립트, settings의 폼과 스크립트, `.admin-btn`/`.admin-field` 재사용은 그대로 둔다.

### 테스트
- 계속 통과해야 하는 테스트:
  - `library-blog-items-contract`
  - `handbook-library-copy`
  - `list-v2`
  - `font-roles`
  - `retro-decoration-removed`
  - `theme-palette`
- 이미 실패 중인 `auth-prompt-library-preview`(ENOENT)는 이번 범위가 아니다.
- 기준선은 7단계 종료 시점 PASS 68 / FAIL 23이다. 비교는 이름으로 한다.

---

## Task 1: about · privacy · terms · 404

**Files:**
- Modify:
  - `frontend/src/pages/ko/about/index.astro`, `frontend/src/pages/en/about/index.astro`
  - `frontend/src/pages/{ko,en}/privacy/index.astro`
  - `frontend/src/pages/{ko,en}/terms/index.astro`
  - `frontend/src/pages/404.astro`
- Test: `frontend/tests/misc-pages-v2.test.cjs` (새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/misc-pages-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const style = (f) => (f.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [, ''])[1];

// Task 1
for (const p of ['pages/ko/about/index.astro', 'pages/en/about/index.astro']) {
  const s = style(read(p));
  assert(!/text-transform:\s*uppercase/.test(s), `${p}: no uppercase labels`);
  assert(!/letter-spacing:\s*0\.(1|2)\d*em/.test(s), `${p}: no wide tracking`);
}
for (const p of ['pages/ko/privacy/index.astro', 'pages/en/privacy/index.astro', 'pages/ko/terms/index.astro', 'pages/en/terms/index.astro', 'pages/404.astro']) {
  const s = style(read(p));
  assert(!/text-transform:\s*uppercase/.test(s), `${p}: no uppercase`);
  assert(!/font-weight:\s*(800|900)/.test(s), `${p}: no 800/900 weights (Hahmlet loads 600/700)`);
}

console.log('misc-pages-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/misc-pages-v2.test.cjs`
Expected: FAIL. about의 uppercase 또는 wide tracking에서 실패한다.

- [ ] **Step 3: 수정** (scoped `<style>`만 수정한다. 마크업 텍스트는 바꾸지 않는다)

  **about (ko/en)**
  - `.about-overline`: `text-transform`을 삭제하고 `letter-spacing: 0;`으로 바꾼다. 색은 `color: var(--color-accent); font-weight: 600; font-size: 0.8rem;`로 맞춘다.
  - `.about-title`
    - 지금은 `--font-masthead`(Newsreader) 500이다. 한글 제목이면 Hahmlet으로 대체되므로 `font-family: var(--font-heading); font-weight: 700; letter-spacing: -0.04em;`로 바꾼다.
    - 단, 제목이 영문 브랜드명 "0to1log"라면 masthead를 유지한다(파일에서 텍스트를 확인한다).
  - 장식 문자(ornament)의 `letter-spacing` 0.2em → `0.05em`
  - 단계 번호 원(~:210)
    - `border-radius: 50%`와 배경 원을 제거한다.
    - `font-family: var(--font-heading); font-weight: 700; color: var(--color-accent); background: none; border: none;`로 숫자만 남긴다.
  - 태그 칩(~:254): `background: none; border: none; padding: 0; color: var(--color-text-muted);`
    - 위 규칙 바로 뒤에 다음 규칙을 추가한다.
      ```css
      .about-tag::before {
        content: '#';
        opacity: 0.6;
      }
      ```
    - 클래스명이 다르면 실제 클래스에 맞춘다.
  - 기타 `text-transform: uppercase`와 `letter-spacing ≥ 0.1em`이 남아 있으면 모두 제거한다.

  **privacy / terms (ko/en)**
  - 이미 대부분 V2다. 남은 uppercase와 800/900이 있으면 제거한다.
  - 2px radius 같은 작은 값은 그대로 둔다.

  **404**
  - `.error-404-number`: 숫자만 있으므로 Newsreader를 유지한다. `font-variant-numeric: lining-nums;`가 없으면 추가한다.
  - 홈 링크 버튼(~:117): 상자형이라면 `background: var(--color-text-primary); color: var(--color-bg-primary); border-radius: 4px;`로 사이트의 기본 버튼(홈 CTA)과 맞춘다.
  - uppercase가 있으면 제거한다.

- [ ] **Step 4: 통과 확인** — `node frontend/tests/misc-pages-v2.test.cjs`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/ko/about/index.astro frontend/src/pages/en/about/index.astro frontend/src/pages/ko/privacy/index.astro frontend/src/pages/en/privacy/index.astro frontend/src/pages/ko/terms/index.astro frontend/src/pages/en/terms/index.astro frontend/src/pages/404.astro frontend/tests/misc-pages-v2.test.cjs
git commit -m "feat: soft newsprint about, legal and 404 pages"
```

수정할 필요가 없던 파일은 add 목록에서 빼도 된다.

## Task 2: library · portfolio · settings

**Files:**
- Modify:
  - `frontend/src/styles/global.css` (`.library-*`, `.pf-*`)
  - `frontend/src/pages/settings/index.astro`, `frontend/src/pages/settings/webhooks.astro` (scoped style)
- Test: `frontend/tests/misc-pages-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위)

```js
// Task 2
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
const tab = rule('.library-tab');
assert(!/text-transform:\s*uppercase/.test(tab) && !/font-weight:\s*800/.test(tab), 'library tabs: no uppercase / 800');
assert(css.includes('.library-tab--active::after') || css.includes('.library-tab[aria-selected="true"]::after'), 'active library tab marked by a dot');
assert(!/font-weight:\s*800/.test(rule('.pf-name')), 'portfolio name uses a loaded weight');
assert(!/text-transform:\s*uppercase/.test(rule('.pf-overline')), 'portfolio overline not uppercase');
for (const p of ['pages/settings/index.astro', 'pages/settings/webhooks.astro']) {
  assert(!/text-transform:\s*uppercase/.test(style(read(p))), `${p}: no uppercase labels`);
}
```

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 수정**

  **library (`global.css`)**
  - `.library-tab`
    - 대상 속성: `text-transform`, `font-weight: 800`, `letter-spacing: 0.1em`, 상자형 활성 탭
    - `position: relative; font-weight: 500; letter-spacing: 0; text-transform: none; color: var(--color-text-muted); background: none; border: none; border-radius: 0; padding: 0.5rem 0.1rem 0.7rem;`
  - 활성 탭 규칙: `.library-tab--active` 또는 `[aria-selected="true"]` 중 실제로 쓰는 쪽을 확인한다.
    - `color: var(--color-text-primary); font-weight: 600; background: none; border: none; box-shadow: none;`로 바꾼다.
    - 같은 셀렉터에 `::after`로 4px accent 점을 추가한다. 형식은 뉴스 탭 `.newsprint-filter-tab[aria-selected="true"]::after`와 같다.
  - 탭 컨테이너가 있으면 `gap: 1.2rem; border-bottom: 1px solid var(--color-border);`
  - 미리보기 kicker(~6803): `text-transform`을 삭제하고 `letter-spacing: 0; color: var(--color-accent);`
  - 진행 카드(~7015): `border-radius: 4px; box-shadow: none;`
  - 알약 stat(~7038): `border-radius: 0; background: none; padding: 0;`
  - 그라디언트 진행 막대(~7073): 단색 `background: var(--color-accent);`
  - auth-prompt OAuth 버튼(~6706–6719): `border-radius: 6px;`, 그림자 제거

  **portfolio (`global.css` `.pf-*`)**
  - `.pf-overline`: `text-transform`을 삭제하고 `letter-spacing: 0; color: var(--color-accent); font-weight: 600;`
  - `.pf-name`: `font-weight: 800` → `700`. 폰트가 Hahmlet이 아니면 `font-family: var(--font-heading);`
  - 0.3em 자간(~5875) → `0.05em`
  - 그 밖의 uppercase(~5998, ~6068): `text-transform`을 삭제하고 `letter-spacing: 0;`
  - inset accent box-shadow(~5950, ~6049): 제거하고 `border-left: 2px solid var(--color-accent);`로 대체한다.
  - **`.newsprint-tag` 칩은 건드리지 않는다.**
  - `--reveal`/`--card-i` inline 애니메이션 변수는 유지한다.

  **settings (index/webhooks scoped style)**
  - uppercase 700 라벨(index ~352–358, webhooks ~207–212, ~285–289): `text-transform`을 삭제하고 `letter-spacing: 0;`. 굵기 700은 유지한다.
  - 플랫폼 색 `border-left`(webhooks ~447): 색으로 플랫폼을 구분하는 정보이므로 **유지한다**.
  - radius 6–8px은 유지한다. 폼 컨트롤이라 괜찮다.

- [ ] **Step 4: 통과 확인**
  - 실행: `node frontend/tests/misc-pages-v2.test.cjs`
  - 함께 실행: 사전 정보의 "계속 통과해야 하는 테스트" 전부
  - 마지막으로 `cd frontend && npm run build`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/src/pages/settings/index.astro frontend/src/pages/settings/webhooks.astro frontend/tests/misc-pages-v2.test.cjs
git commit -m "feat: soft newsprint library tabs, portfolio and settings labels"
```

## Task 3: 검증 (컨트롤러)
- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL이 없어야 한다.
- [ ] 브라우저(종이·다크 테마)로 다음 페이지를 확인한다.
  - `/ko/about/`, `/ko/privacy/`, `/ko/terms/`, 404(없는 경로)
  - `/portfolio/`
  - `/library/`, `/settings/` (로그인이 필요하면 게스트 화면만 확인)

## Task 4: 문서
- [ ] ACTIVE_SPRINT에 REDESIGN-P8b를 추가한다.
- [ ] 이 계획에 실행 결과를 적는다.
- [ ] 커밋: `docs: record redesign phase 8b misc pages`

---

## 실행 결과 (2026-10-15)

- 커밋: `27e00b48` about·404, `67463620` 서재·포트폴리오·설정.
- 검증: 전체 테스트 70 PASS / 23 FAIL(실패 목록 기준선과 동일), 빌드 성공, 브라우저 확인.
- 계획 대비: about 제목은 브랜드명 "0to1log"라 Newsreader 유지. privacy·terms·404 숫자는 이미 기준 충족이라 미수정. 포트폴리오 카드 accent 왼쪽 선은 hover에만. 서재 type 배지·index 자간도 함께 정리.
- 후속 후보: 서재 "저장" 하위 토글(`.library-sub-tab`) 활성 상태는 아직 상자형.
