# Admin Editor Shared Code Extraction

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3개 어드민 에디터(News/Blog/Handbook)에서 ~750줄의 중복 코드를 2개의 공유 TypeScript 모듈로 추출해 DRY 원칙을 적용한다.

**Architecture:** 두 모듈로 분리 — `adminEditorUtils.ts`는 순수 유틸리티(esc, showFeedback, 버튼 관리)를, `adminEditorPreview.ts`는 iframe 프리뷰 전체 로직을 담는 팩토리 함수로 구성한다. 각 에디터의 `<script>` 블록에서 import해서 사용하며, 로컬 중복 함수는 모두 삭제한다.

**Tech Stack:** TypeScript, Vite (Astro v5 `<script>` 블록은 Vite가 번들링해 ESM import 지원)

---

## 파일 구조

**신규 생성:**
- `frontend/src/scripts/adminEditorUtils.ts` — esc, showFeedback, createButtonManager
- `frontend/src/scripts/adminEditorPreview.ts` — createPreviewManager factory

**수정:**
- `frontend/src/pages/admin/edit/[slug].astro` (News)
- `frontend/src/pages/admin/blog/edit/[slug].astro` (Blog)
- `frontend/src/pages/admin/handbook/edit/[slug].astro` (Handbook)

---

## Chunk 1: adminEditorUtils

### Task 1: adminEditorUtils.ts 생성

**Files:**
- Create: `frontend/src/scripts/adminEditorUtils.ts`

- [x] **Step 1: 파일 생성**

```typescript
// frontend/src/scripts/adminEditorUtils.ts

// ─── HTML escape ─────────────────────────────────────────────────────────────

export function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML.replace(/"/g, '&quot;');
}

// ─── Feedback toast ───────────────────────────────────────────────────────────
// Requires: <div id="admin-feedback" class="admin-feedback admin-feedback--toast" hidden></div>
// All 3 editors share id="admin-feedback" (Handbook was fixed in Stage 1).

let _feedbackTimer = 0;

export function showFeedback(message: string, isError = false): void {
  const el = document.getElementById('admin-feedback');
  if (!el) return;
  el.textContent = message;
  el.className = `admin-feedback admin-feedback--toast admin-feedback--${isError ? 'error' : 'success'}`;
  el.setAttribute('role', isError ? 'alert' : 'status');
  el.setAttribute('aria-live', isError ? 'assertive' : 'polite');
  el.setAttribute('aria-atomic', 'true');
  el.hidden = false;
  clearTimeout(_feedbackTimer);
  _feedbackTimer = window.setTimeout(() => { el.hidden = true; }, 3000);
}

// ─── Button manager ───────────────────────────────────────────────────────────
// Usage:
//   const btnManager = createButtonManager([btnSave, btnPreview, ...].filter(Boolean));
//   btnManager.begin(btnSave, 'Saving...');
//   btnManager.restore();

export function createButtonManager(buttons: HTMLButtonElement[]) {
  const _defaultLabels = new Map<HTMLButtonElement, string>();
  buttons.forEach((b) => _defaultLabels.set(b, b.textContent || ''));
  let _isPending = false;

  function setLabel(btn: HTMLButtonElement | null, label: string): void {
    if (!btn) return;
    if (label.includes('...') || label.includes('…')) {
      btn.innerHTML = `<span class="btn-spinner"></span>${label}`;
    } else {
      btn.textContent = label;
    }
  }

  function begin(btn: HTMLButtonElement | null, label: string): void {
    buttons.forEach((b) => {
      b.disabled = true;
      b.textContent = _defaultLabels.get(b) || b.textContent || '';
    });
    setLabel(btn, label);
    _isPending = true;
  }

  function restore(): void {
    buttons.forEach((b) => {
      b.disabled = false;
      b.textContent = _defaultLabels.get(b) || b.textContent || '';
    });
    _isPending = false;
  }

  return { begin, restore, setLabel, get isPending() { return _isPending; } };
}
```

- [x] **Step 2: 빌드 확인 (파일만 있고 아직 사용 안 해도 됨)**

```bash
cd frontend && npm run build
```
Expected: `Complete!` (에러 없음)

---

### Task 2: News 에디터에 utils 적용

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

현재 상태 이해:
- `feedbackTimer` 변수: 322~327 라인, `<script>` 최상단 (DOMContentLoaded 바깥)
- `showFeedback`: 552~565 라인 → 삭제하고 import로 교체
- `esc`: 1374~1378 라인 → 삭제하고 import로 교체
- `restoreActionButtons/setButtonLabel/beginAction`: 390~414 라인 → 삭제
- `managedButtons/defaultButtonLabels/isActionPending`: 378~388 라인 → createButtonManager로 교체
- 피드백 HTML: `<span id="admin-feedback-msg">` 제거 필요

- [x] **Step 1: `<script>` 블록 상단에 import 추가**

`import { Crepe } from '@milkdown/crepe';` 아래 줄에 추가:
```typescript
import { esc, showFeedback, createButtonManager } from '../../../scripts/adminEditorUtils';
```

- [x] **Step 2: `feedbackTimer` 변수 삭제**

`<script>` 블록 최상단의 `let feedbackTimer = 0;` 줄 삭제 (모듈 내부로 이동됨)

- [x] **Step 3: HTML 피드백 요소 단순화**

```html
<!-- Before -->
<div id="admin-feedback" class="admin-feedback admin-feedback--toast" hidden>
  <span id="admin-feedback-msg"></span>
</div>

<!-- After -->
<div id="admin-feedback" class="admin-feedback admin-feedback--toast" hidden></div>
```

- [x] **Step 4: `managedButtons` 세팅을 `createButtonManager`로 교체**

DOMContentLoaded 내부, 버튼 변수 선언 직후 (378~388 라인 범위):

```typescript
// Before (삭제):
const managedButtons = [btnSave, btnPreview, btnPublish, btnPublishDraft, btnDelete, btnEdit]
  .filter((button): button is HTMLButtonElement => button instanceof HTMLButtonElement);
const defaultButtonLabels = new Map<HTMLButtonElement, string>();
managedButtons.forEach((button) => {
  defaultButtonLabels.set(button, button.textContent || '');
});
let isActionPending = false;

// After (추가):
const btnManager = createButtonManager(
  [btnSave, btnPreview, btnPublish, btnPublishDraft, btnDelete, btnEdit]
    .filter((b): b is HTMLButtonElement => b instanceof HTMLButtonElement),
);
```

- [x] **Step 5: 로컬 함수 3개 삭제**

390~414 라인의 `restoreActionButtons`, `setButtonLabel`, `beginAction` 함수 본체 삭제

- [x] **Step 6: 호출 사이트 교체 — 버튼 관리**

파일 내 전체 치환:
- `restoreActionButtons()` → `btnManager.restore()`
- `beginAction(` → `btnManager.begin(`
- `setButtonLabel(` → `btnManager.setLabel(`
- `isActionPending` → `btnManager.isPending`

- [x] **Step 7: 로컬 `showFeedback` 함수 삭제 (552~565 라인)**

- [x] **Step 8: `showFeedback` 호출 사이트 시그니처 변환**

News 에디터의 `showFeedback` 시그니처가 `(type, message)` → `(message, isError?)` 로 변경됨.

파일 내 전체 치환:
- `showFeedback('success', ` → `showFeedback(` (뒤따르는 `)` 그대로)
- `showFeedback('error', ` → `showFeedback(` + 인수 끝에 `, true)` 추가

> 주의: `showFeedback('error', msg)` → `showFeedback(msg, true)` 로 바꿔야 함.
> 에디터에서 'success'/'error' 두 종류만 사용 중이므로 변환이 단순함.
> 각 라인을 직접 수정하는 게 실수가 없음. grep 결과 기준 수정 대상 라인:
> 614, 616, 717, 757, 770, 783, 789, 810, 823, 829, 848, 851,
> 1005, 1039, 1040, 1041, 1042, 1052, 1121, 1385, 1416

- [x] **Step 9: 로컬 `esc` 함수 삭제 (1374~1378 라인)**

- [x] **Step 10: 빌드 확인**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

---

### Task 3: Blog 에디터에 utils 적용

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

News 에디터와 동일한 패턴. Blog 에디터 기준 라인 번호:
- `feedbackTimer` 변수: `<script>` 최상단
- `restoreActionButtons/setButtonLabel/beginAction`: 395~419
- `managedButtons/defaultButtonLabels/isActionPending`: 383~393
- `showFeedback`: 555~568
- `esc`: 1398~1402

- [x] **Step 1: import 추가** (Blog 경로: `'../../../scripts/adminEditorUtils'`)

- [x] **Step 2: `feedbackTimer` 삭제**

- [x] **Step 3: HTML 피드백 요소에서 `<span id="admin-feedback-msg">` 제거**

- [x] **Step 4: `createButtonManager` 교체** (383~393 라인)

- [x] **Step 5: 로컬 함수 3개 삭제** (395~419 라인)

- [x] **Step 6: 버튼 관리 호출 사이트 치환**
- `restoreActionButtons()` → `btnManager.restore()`
- `beginAction(` → `btnManager.begin(`
- `setButtonLabel(` → `btnManager.setLabel(`
- `isActionPending` → `btnManager.isPending`

- [x] **Step 7: 로컬 `showFeedback` 삭제** (555~568 라인)

- [x] **Step 8: `showFeedback` 호출 사이트 변환**

Blog 수정 대상 라인 (grep 기준): 612~1470 사이 `showFeedback('success',` / `showFeedback('error',` 전체.

- [x] **Step 9: 로컬 `esc` 삭제** (1398~1402 라인)

- [x] **Step 10: 빌드 확인**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

---

### Task 4: Handbook 에디터에 utils 적용

**Files:**
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

Handbook은 이미 `showFeedback(message, isError=false)` 시그니처를 사용 중이므로 **호출 사이트 변환 불필요**.
피드백 HTML도 이미 단일 div (Stage 1에서 `#admin-feedback`로 정규화됨).

- [x] **Step 1: import 추가**

`<script>` 블록 최상단 (Handbook은 Milkdown import가 있는 곳):
```typescript
import { esc, showFeedback, createButtonManager } from '../../../scripts/adminEditorUtils';
```

- [x] **Step 2: `feedbackTimer` 변수 삭제**

Handbook 스크립트 상단의 `let feedbackTimer = 0;` (또는 이에 해당하는 타입 선언) 삭제

- [x] **Step 3: `managedButtons/defaultButtonLabels/isActionPending` 교체**

Handbook 에디터에서 해당 변수 선언부 찾아 `createButtonManager` 팩토리로 교체.

- [x] **Step 4: `restoreActionButtons/setButtonLabel/beginAction` 삭제 + 호출 사이트 치환**

- [x] **Step 5: 로컬 `showFeedback` 삭제 (1628~1638 라인)**

- [x] **Step 6: 로컬 `esc` 삭제 (826~830 라인)**

- [x] **Step 7: 빌드 확인 + Chunk 1 커밋**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

```bash
git add frontend/src/scripts/adminEditorUtils.ts \
        frontend/src/pages/admin/edit/[slug].astro \
        frontend/src/pages/admin/blog/edit/[slug].astro \
        frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "refactor: extract shared editor utils (esc, showFeedback, buttonManager)"
```

---

## Chunk 2: adminEditorPreview

### Task 5: adminEditorPreview.ts 생성

**Files:**
- Create: `frontend/src/scripts/adminEditorPreview.ts`

- [x] **Step 1: 파일 생성**

```typescript
// frontend/src/scripts/adminEditorPreview.ts
//
// 사용법:
//   const preview = createPreviewManager({
//     previewFrame, previewShell, previewLoading, previewLoadingText,
//     draftRoot, previewRoot,
//     basePath: '/admin/edit',
//     getCurrentSlug: () => currentSlug,
//     buildPreviewUrl: () => buildPreviewUrl(),
//     onRestoreButtons: () => btnManager.restore(),
//     onPreviewReady: () => showFeedback('Preview updated.'),
//   });
//   previewFrame?.addEventListener('load', preview.onFrameLoad);

export interface PreviewManagerConfig {
  previewFrame: HTMLIFrameElement | null;
  previewShell: HTMLElement | null;
  previewLoading: HTMLElement | null;
  previewLoadingText: HTMLElement | null;
  draftRoot: HTMLElement | null;
  previewRoot: HTMLElement | null;
  /** e.g. '/admin/edit', '/admin/blog/edit', '/admin/handbook/edit' */
  basePath: string;
  getCurrentSlug: () => string;
  /** 에디터별 프리뷰 URL 생성 로직 (locale, level 등 포함) */
  buildPreviewUrl: () => string;
  onRestoreButtons: () => void;
  onPreviewReady?: () => void;
}

export function createPreviewManager(config: PreviewManagerConfig) {
  let _resizeObserver: ResizeObserver | null = null;
  let _resizeCleanup: (() => void) | null = null;
  let _announceReady = false;
  let _enteredFromEditor = false;

  function isPreviewLocation(): boolean {
    return new URL(window.location.href).searchParams.get('mode') === 'preview';
  }

  function getEditorUrl(mode: 'draft' | 'preview', slugOverride?: string): string {
    const slug = slugOverride ?? config.getCurrentSlug();
    const url = new URL(window.location.href);
    if (slug) url.pathname = `${config.basePath}/${slug}`;
    if (mode === 'preview') {
      url.searchParams.set('mode', 'preview');
    } else {
      url.searchParams.delete('mode');
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function setPreviewShellLoading(loading: boolean, message = 'Loading live preview...'): void {
    config.previewShell?.classList.toggle('admin-preview-frame-shell--loading', loading);
    if (config.previewLoading) config.previewLoading.hidden = !loading;
    if (config.previewLoadingText) config.previewLoadingText.textContent = message;
    if (config.previewFrame) config.previewFrame.setAttribute('aria-busy', loading ? 'true' : 'false');
  }

  function disconnectPreviewResize(): void {
    _resizeObserver?.disconnect();
    _resizeObserver = null;
    if (_resizeCleanup) {
      _resizeCleanup();
      _resizeCleanup = null;
    }
  }

  function syncPreviewFrameHeight(): void {
    if (!config.previewFrame?.contentDocument) return;
    const doc = config.previewFrame.contentDocument;
    const nextHeight = Math.max(
      doc.body?.scrollHeight || 0,
      doc.body?.offsetHeight || 0,
      doc.documentElement?.scrollHeight || 0,
      doc.documentElement?.offsetHeight || 0,
    );
    if (nextHeight > 0) {
      const current = parseInt(config.previewFrame.style.height || '0');
      if (Math.abs(nextHeight - current) > 4) {
        config.previewFrame.style.height = `${Math.max(nextHeight, 720)}px`;
      }
    }
  }

  function attachPreviewAutoResize(): void {
    if (!config.previewFrame?.contentDocument) return;
    disconnectPreviewResize();
    const doc = config.previewFrame.contentDocument;
    const win = config.previewFrame.contentWindow;
    const scheduleResize = () => window.requestAnimationFrame(() => syncPreviewFrameHeight());

    _resizeObserver = new ResizeObserver(() => scheduleResize());
    if (doc.body) _resizeObserver.observe(doc.body);
    if (doc.documentElement) _resizeObserver.observe(doc.documentElement);
    doc.querySelectorAll('img').forEach((img) => {
      if (!img.complete) img.addEventListener('load', scheduleResize, { once: true });
    });
    if (win) {
      const handleResize = () => scheduleResize();
      win.addEventListener('resize', handleResize);
      _resizeCleanup = () => win.removeEventListener('resize', handleResize);
    }
    scheduleResize();
    window.setTimeout(scheduleResize, 120);
    window.setTimeout(scheduleResize, 420);
    window.setTimeout(scheduleResize, 1200);
  }

  function showPreviewMode(pushHistory = false): void {
    if (config.draftRoot) config.draftRoot.style.display = 'none';
    if (config.previewRoot) config.previewRoot.style.display = 'block';
    if (pushHistory && !isPreviewLocation()) {
      history.pushState({ mode: 'preview' }, '', getEditorUrl('preview'));
      _enteredFromEditor = true;
    }
  }

  function showDraftMode(replaceHistory = false): void {
    if (config.draftRoot) config.draftRoot.style.display = '';
    if (config.previewRoot) config.previewRoot.style.display = 'none';
    if (replaceHistory && isPreviewLocation()) {
      history.replaceState({ mode: 'draft' }, '', getEditorUrl('draft'));
    }
    _enteredFromEditor = false;
    setPreviewShellLoading(false);
    config.onRestoreButtons();
  }

  function loadPreviewFrame(previewUrl: string, options: { announce?: boolean; pushHistory?: boolean } = {}): void {
    if (!config.previewFrame) return;
    _announceReady = options.announce === true;
    setPreviewShellLoading(true);
    showPreviewMode(options.pushHistory === true);
    config.previewFrame.src = previewUrl;
  }

  function syncModeFromLocation(): void {
    if (!isPreviewLocation()) {
      showDraftMode(false);
      return;
    }
    const previewUrl = config.buildPreviewUrl();
    if (!previewUrl) {
      showDraftMode(true);
      return;
    }
    showPreviewMode(false);
    const targetHref = new URL(previewUrl, window.location.origin).toString();
    const currentHref = config.previewFrame?.src
      ? new URL(config.previewFrame.src, window.location.origin).toString()
      : '';
    if (!currentHref || currentHref !== targetHref) {
      loadPreviewFrame(previewUrl, { announce: false, pushHistory: false });
    }
  }

  /** previewFrame 'load' 이벤트에 직접 연결:
   *  previewFrame?.addEventListener('load', preview.onFrameLoad);
   */
  function onFrameLoad(): void {
    attachPreviewAutoResize();
    setPreviewShellLoading(false);
    config.onRestoreButtons();
    if (_announceReady) {
      config.onPreviewReady?.();
      _announceReady = false;
    }
  }

  return {
    isPreviewLocation,
    getEditorUrl,
    setPreviewShellLoading,
    disconnectPreviewResize,
    attachPreviewAutoResize,
    showPreviewMode,
    showDraftMode,
    loadPreviewFrame,
    syncModeFromLocation,
    onFrameLoad,
    get enteredFromEditor() { return _enteredFromEditor; },
  };
}
```

- [x] **Step 2: 빌드 확인**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

---

### Task 6: News 에디터에 preview manager 적용

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

삭제 대상 (이미 Chunk 1에서 import 추가됨):
- `disconnectPreviewResize` (440~447)
- `syncPreviewFrameHeight` (449~467)
- `attachPreviewAutoResize` (469~494)
- `showPreviewMode` (496~503)
- `showDraftMode` (505~514)
- `loadPreviewFrame` (516~522)
- `syncModeFromLocation` (524~540)
- `setPreviewShellLoading` (416~421)
- `isPreviewLocation` (423~425)
- `getEditorUrl` (427~438)
- 변수: `previewEnteredFromEditor`, `previewResizeObserver`, `previewWindowResizeCleanup`, `announcePreviewReady`

- [x] **Step 1: import에 `createPreviewManager` 추가**

```typescript
import { esc, showFeedback, createButtonManager } from '../../../scripts/adminEditorUtils';
import { createPreviewManager } from '../../../scripts/adminEditorPreview';
```

- [x] **Step 2: 위 변수/함수 10개 모두 삭제**

- [x] **Step 3: `btnManager` 생성 직후 `createPreviewManager` 호출 추가**

```typescript
const preview = createPreviewManager({
  previewFrame,
  previewShell,
  previewLoading,
  previewLoadingText,
  draftRoot: draftMode,
  previewRoot: previewMode as HTMLElement | null,
  basePath: '/admin/edit',
  getCurrentSlug: () => currentSlug,
  buildPreviewUrl,
  onRestoreButtons: () => btnManager.restore(),
  onPreviewReady: () => showFeedback('Preview updated.'),
});
```

- [x] **Step 4: 기존 `previewFrame?.addEventListener('load', ...)` 블록 교체**

```typescript
// Before (삭제):
previewFrame?.addEventListener('load', () => {
  attachPreviewAutoResize();
  setPreviewShellLoading(false);
  restoreActionButtons();
  if (announcePreviewReady) {
    showFeedback('Preview updated.');
    announcePreviewReady = false;
  }
});

// After:
previewFrame?.addEventListener('load', preview.onFrameLoad);
```

- [x] **Step 5: 함수 호출 사이트 교체**

| 기존 | 변경 |
|------|------|
| `isPreviewLocation()` | `preview.isPreviewLocation()` |
| `getEditorUrl(mode)` | `preview.getEditorUrl(mode)` |
| `getEditorUrl(mode, slug)` | `preview.getEditorUrl(mode, slug)` |
| `setPreviewShellLoading(` | `preview.setPreviewShellLoading(` |
| `showPreviewMode(` | `preview.showPreviewMode(` |
| `showDraftMode(` | `preview.showDraftMode(` |
| `loadPreviewFrame(` | `preview.loadPreviewFrame(` |
| `syncModeFromLocation()` | `preview.syncModeFromLocation()` |
| `previewEnteredFromEditor` | `preview.enteredFromEditor` |

- [x] **Step 6: 빌드 확인**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

---

### Task 7: Blog 에디터에 preview manager 적용

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

News와 동일 패턴. Blog 고유 차이점:
- `basePath: '/admin/blog/edit'`
- `getCurrentSlug: () => currentSlug`
- `buildPreviewUrl`는 이미 에디터에 있는 Blog 전용 함수 (locale 포함) 그대로 사용
- `previewRoot: previewMode as HTMLElement | null`

- [x] **Step 1~5**: News 에디터와 동일 순서로 진행. basePath만 다름.

- [x] **Step 6: 빌드 확인**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

---

### Task 8: Handbook 에디터에 preview manager 적용

**Files:**
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

Handbook 고유 차이점:
- `basePath: '/admin/handbook/edit'`
- `buildPreviewUrl`는 level-aware URL 생성 (`?previewLevel=...`) — 에디터에 있는 기존 함수 사용
- `previewRoot: previewMode as HTMLElement | null`

- [x] **Step 1~5**: News 에디터와 동일 순서로 진행.

- [x] **Step 6: 빌드 확인 + Chunk 2 전체 커밋**

```bash
cd frontend && npm run build
```
Expected: `Complete!`

```bash
git add frontend/src/scripts/adminEditorPreview.ts \
        frontend/src/pages/admin/edit/[slug].astro \
        frontend/src/pages/admin/blog/edit/[slug].astro \
        frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "refactor: extract shared editor preview manager to adminEditorPreview.ts"
```

---

## 완료 기준

- [x] `npm run build` 에러 없음
- [x] 3개 에디터 각각에서 Save, Preview, Publish, Delete 동작 확인
- [x] `adminEditorUtils.ts` + `adminEditorPreview.ts` 2개 파일 생성됨
- [x] 각 에디터 `<script>`에서 중복 함수 코드가 사라지고 import로 대체됨
- [x] 추출 후 3개 에디터 합산 약 750줄 감소 확인

## 예상 결과

| 파일 | 변경 전 | 변경 후 |
|------|---------|---------|
| adminEditorUtils.ts | (없음) | +75줄 (신규) |
| adminEditorPreview.ts | (없음) | +140줄 (신규) |
| News 에디터 | ~1453줄 | ~1150줄 (−303) |
| Blog 에디터 | ~1476줄 | ~1170줄 (−306) |
| Handbook 에디터 | ~1856줄 | ~1550줄 (−306) |
| **합계** | **4785줄** | **~4085줄 (−700줄)** |
