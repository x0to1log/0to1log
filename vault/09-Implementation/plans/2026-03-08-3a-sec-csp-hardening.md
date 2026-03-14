# 3A-SEC: CSP Hardening & Production Security Checklist

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** CSP `script-src 'unsafe-inline'` 제거 + analytics 스크립트 외부화 + production 보안 점검

**Architecture:** Astro의 `is:inline` 스크립트 중 정적 콘텐츠(FOUC 방지)는 SHA-256 해시 기반 CSP로 전환하고, 동적 콘텐츠(GA4/Clarity `define:vars`)는 번들 외부 스크립트로 전환한다. `style-src 'unsafe-inline'`은 인라인 style 속성이 광범위하게 사용되어 제거 비용 대비 보안 이득이 낮으므로 이번 스프린트에서 제외한다.

**Tech Stack:** Astro v5, Vercel, CSP SHA-256 hashes, rehype-sanitize

---

## 현재 상태 분석

### `unsafe-inline`이 필요한 인라인 스크립트 목록

| # | 파일 | 유형 | 내용 | 전략 |
|---|------|------|------|------|
| 1 | `MainLayout.astro:35-48` | `is:inline` (정적) | FOUC 방지: localStorage → data-theme 설정 | SHA-256 해시 |
| 2 | `MainLayout.astro:51-58` | `is:inline` (정적) | ViewTransitions 후 테마 복원 | SHA-256 해시 |
| 3 | `MainLayout.astro:66-71` | `is:inline define:vars` (동적) | GA4 gtag 초기화 | 외부 스크립트로 전환 |
| 4 | `MainLayout.astro:76-82` | `is:inline define:vars` (동적) | Clarity 초기화 | 외부 스크립트로 전환 |
| 5 | `MainLayout.astro:65` | `is:inline src=` (외부) | GA4 gtag.js 로더 | 도메인 허용으로 충분 (변경 불필요) |
| 6 | `preview/*.astro` | `is:inline` (정적) | 테마 강제 설정 (개발용) | SHA-256 해시 (선택) |

### Nonce vs Hash 판단

- **Nonce 불가**: MainLayout은 prerendered + SSR 페이지 모두에서 사용됨. prerendered 페이지에서는 미들웨어가 실행되지 않아 nonce 주입 불가.
- **Hash 적합**: FOUC 스크립트는 내용이 빌드마다 동일(환경변수 없음). SHA-256 해시가 안정적.
- **외부화**: `define:vars` 스크립트는 환경변수에 따라 내용이 바뀌므로 해시 불가 → 번들 스크립트로 전환.

### 의도적 제외 항목

| 항목 | 이유 |
|------|------|
| `style-src 'unsafe-inline'` 제거 | 코드베이스 전반의 `style=""` 속성 의존. 제거 시 대규모 CSS 리팩토링 필요. 인라인 스타일의 XSS 위험은 인라인 스크립트 대비 현저히 낮음. |
| Admin preview `marked.parse()` 미새니타이즈 | admin-only 화면에서 admin이 자신의 콘텐츠를 미리보기하는 것. 공개 렌더링(`renderMarkdown`)은 이미 `rehype-sanitize` 적용 완료. |

---

## Task 1: Analytics 스크립트 외부화

**목적:** GA4/Clarity 초기화를 `define:vars` 인라인에서 번들 외부 스크립트로 전환하여 `unsafe-inline` 의존 제거.

**Files:**
- Create: `frontend/src/scripts/analytics.ts`
- Modify: `frontend/src/layouts/MainLayout.astro:62-83`

**Step 1: analytics.ts 작성**

```typescript
// frontend/src/scripts/analytics.ts
// GA4 initialization
const gaId = document.querySelector<HTMLMetaElement>('meta[name="ga4-id"]')?.content;
if (gaId) {
  (window as any).dataLayer = (window as any).dataLayer || [];
  function gtag(..._args: any[]) {
    (window as any).dataLayer.push(arguments);
  }
  gtag('js', new Date());
  gtag('config', gaId);
}

// Clarity initialization
const clarityId = document.querySelector<HTMLMetaElement>('meta[name="clarity-id"]')?.content;
if (clarityId) {
  (function (c: any, l: Document, a: string, r: string, i: string) {
    c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
    const t = l.createElement(r) as HTMLScriptElement;
    t.async = true;
    t.src = 'https://www.clarity.ms/tag/' + i;
    const y = l.getElementsByTagName(r)[0];
    y.parentNode!.insertBefore(t, y);
  })(window, document, 'clarity', 'script', clarityId);
}
```

**Step 2: MainLayout.astro 수정**

`<body>` 태그 직후의 GA4/Clarity 블록(현재 62~83행)을 다음으로 교체:

```astro
  <body style={`min-height: 100vh; display: flex; flex-direction: column; background-color: var(--color-bg-primary); color: var(--color-text-primary); margin: 0;`}>
    {gaId && <meta name="ga4-id" content={gaId} />}
    {clarityId && <meta name="clarity-id" content={clarityId} />}
    {gaId && <script is:inline src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`} async></script>}
    <script src="../scripts/analytics.ts"></script>
```

제거 대상 (기존 코드):
- `<script is:inline define:vars={{ gaId }}>...</script>` 블록 전체
- `<script is:inline define:vars={{ clarityId }}>...</script>` 블록 전체

유지 대상:
- `<script is:inline src={...gtag.js...}>` — 이 태그는 `src` 속성이 있는 외부 스크립트이므로 도메인 허용만으로 충분.

**Step 3: 빌드 검증**

```bash
cd frontend && npm run build
# Expected: 0 errors

# define:vars 인라인 스크립트 잔존 확인
grep -r "define:vars" src/layouts/MainLayout.astro
# Expected: 0 results
```

**Step 4: Commit**

```bash
git add frontend/src/scripts/analytics.ts frontend/src/layouts/MainLayout.astro
git commit -m "refactor: externalize GA4/Clarity scripts for CSP unsafe-inline removal"
```

---

## Task 2: FOUC 스크립트 SHA-256 해시 계산

**목적:** FOUC 방지 인라인 스크립트의 SHA-256 해시를 계산하여 CSP에 등록 준비.

**Files:**
- Read: `frontend/src/layouts/MainLayout.astro` (빌드 후 출력 확인용)

**Step 1: 빌드 후 인라인 스크립트 내용 추출**

```bash
cd frontend && npm run build
```

빌드 후 `dist/` 의 HTML 파일에서 `<script>` 태그 내용을 확인한다. Astro의 `is:inline` 출력은 소스와 동일하므로, 소스 기준으로 해시를 계산한다.

**FOUC 스크립트 1** (MainLayout:36-47, 줄바꿈 포함):
```
(function() {
      var stored = localStorage.getItem('theme');
      if (stored === 'midnight') { stored = 'pink'; localStorage.setItem('theme', stored); }
      var tc = { dark: '#241F1C', light: '#F4F1EA', pink: '#FFF0F3' };
      if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
      } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
      }
      var m = document.querySelector('meta[name="theme-color"]');
      if (m) m.setAttribute('content', tc[stored || 'dark'] || tc.dark);
    })();
```

**FOUC 스크립트 2** (MainLayout:52-57):
```
document.addEventListener('astro:after-swap', function() {
      var stored = localStorage.getItem('theme');
      if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
      }
    });
```

**Step 2: SHA-256 해시 계산**

```bash
# 빌드된 HTML에서 실제 스크립트 내용 추출 후 해시 계산
# 또는 Node.js로 직접 계산:
cd frontend && node -e "
const crypto = require('crypto');

const fouc1 = \`(function() {
      var stored = localStorage.getItem('theme');
      if (stored === 'midnight') { stored = 'pink'; localStorage.setItem('theme', stored); }
      var tc = { dark: '#241F1C', light: '#F4F1EA', pink: '#FFF0F3' };
      if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
      } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
      }
      var m = document.querySelector('meta[name=\"theme-color\"]);
      if (m) m.setAttribute('content', tc[stored || 'dark'] || tc.dark);
    })();\`;

const fouc2 = \`document.addEventListener('astro:after-swap', function() {
      var stored = localStorage.getItem('theme');
      if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
      }
    });\`;

console.log('FOUC1:', crypto.createHash('sha256').update(fouc1).digest('base64'));
console.log('FOUC2:', crypto.createHash('sha256').update(fouc2).digest('base64'));
"
```

**중요:** 해시는 `<script>` 태그 내부의 정확한 텍스트(줄바꿈/공백 포함)로 계산해야 함. 빌드 출력의 실제 HTML에서 추출하여 검증한다.

**Step 3: 해시 기록**

계산된 해시를 기록해둔다 (Task 3에서 CSP에 반영).

---

## Task 3: CSP 정책 업데이트

**목적:** `vercel.json`의 CSP에서 `script-src 'unsafe-inline'`을 제거하고, SHA-256 해시로 대체.

**Files:**
- Modify: `frontend/vercel.json:17-18`

**Step 1: CSP 값 업데이트**

현재:
```
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://*.clarity.ms
```

변경 후:
```
script-src 'self' 'sha256-<FOUC1_HASH>' 'sha256-<FOUC2_HASH>' https://www.googletagmanager.com https://*.clarity.ms
```

`<FOUC1_HASH>`와 `<FOUC2_HASH>`는 Task 2에서 계산한 Base64 값으로 대체.

**Step 2: 빌드 검증**

```bash
cd frontend && npm run build
# Expected: 0 errors
```

**Step 3: 로컬 동작 검증**

```bash
cd frontend && npm run preview
# 브라우저에서 확인:
# 1. 페이지 로드 시 FOUC(흰색 깜빡임) 없이 테마 적용
# 2. 테마 토글 동작 정상
# 3. 브라우저 DevTools Console에 CSP 위반 에러 없음
# 4. GA4/Clarity 스크립트 로드 정상 (Network 탭)
```

**주의:** `npm run preview`는 `vercel.json` 헤더를 적용하지 않음. CSP 위반 검증은 Vercel 배포 후 또는 로컬에서 CSP 헤더를 수동 설정하여 확인해야 한다. 대안으로 빌드된 HTML을 열어 inline 스크립트가 정확히 2개(FOUC)만 남았는지 확인한다.

```bash
# 빌드 출력에서 인라인 스크립트 수 확인
grep -c "<script>" dist/en/index.html || true
# Expected: FOUC 스크립트 2개 + analytics 외부 스크립트 참조만 존재
# define:vars 인라인 0개
```

**Step 4: Commit**

```bash
git add frontend/vercel.json
git commit -m "fix: replace CSP unsafe-inline with SHA-256 hashes for FOUC scripts"
```

---

## Task 4: Production 보안 점검 체크리스트

**목적:** 배포 전 보안 상태 전수 점검.

**Files:**
- Read-only 점검 (수정 필요 시 별도 수정)

**Step 1: 보안 헤더 확인**

`vercel.json`에 다음 헤더가 모두 존재하는지 확인:

| 헤더 | 기대값 |
|------|--------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `unsafe-inline` 없음 (script-src) |

**Step 2: 의존성 보안 감사**

```bash
# Frontend
cd frontend && npm audit --production
# Expected: 0 critical, 0 high

# Backend
cd backend && .venv/Scripts/pip.exe audit 2>/dev/null || .venv/Scripts/python.exe -m pip_audit
# 또는 수동 확인: pip list → 알려진 취약점 체크
```

**Step 3: 인증/권한 체크**

```bash
# Admin 라우트 보호 확인
grep -n "prerender = false" frontend/src/pages/admin/*.astro frontend/src/pages/admin/**/*.astro
# Expected: admin 페이지 모두 SSR (prerender = false)

# 미들웨어 가드 확인
grep -n "startsWith.*admin" frontend/src/middleware.ts
# Expected: /admin/* 경로 가드 존재

# Backend admin 검증
grep -n "require_admin" backend/routers/admin.py
# Expected: 모든 admin 엔드포인트에 의존성 주입
```

**Step 4: 환경변수 노출 확인**

```bash
# .env 파일 gitignore 확인
grep ".env" frontend/.gitignore backend/.gitignore .gitignore
# Expected: .env 패턴 존재

# 퍼블릭 환경변수 확인 (PUBLIC_ 접두어만 클라이언트 노출 허용)
grep -r "import.meta.env\." frontend/src/ --include="*.astro" --include="*.ts" | grep -v "PUBLIC_" | grep -v "CRON_SECRET\|FASTAPI_URL\|REVALIDATE_SECRET" | grep -v "node_modules"
# 서버 전용 env가 클라이언트 코드에 노출되지 않는지 확인
```

**Step 5: Markdown 새니타이즈 확인**

```bash
# 공개 렌더링 파이프라인에 rehype-sanitize 적용 확인
grep -n "rehypeSanitize" frontend/src/lib/markdown.ts
# Expected: 존재

# set:html 사용처 확인 (XSS 위험)
grep -rn "set:html" frontend/src/ --include="*.astro"
# 각 사용처가 새니타이즈된 데이터만 받는지 수동 확인
```

**Step 6: CORS 확인**

```bash
grep -n "CORSMiddleware\|allow_origins" backend/main.py
# Expected: 프로덕션 도메인만 허용 (wildcard * 아님)
```

**Step 7: 결과 기록**

점검 결과를 커밋 메시지에 요약 기록.

```bash
git commit --allow-empty -m "chore: production security checklist passed (3A-SEC)

Verified:
- CSP unsafe-inline removed from script-src
- Security headers complete (XFO, XCTO, RP, CSP)
- Markdown sanitization via rehype-sanitize
- Admin route protection (middleware + backend require_admin)
- No .env file exposure
- CORS restricted to production domain"
```

---

## Task 5: 문서 업데이트 + 최종 검증

**목적:** IMPLEMENTATION_PLAN 상태 갱신 + 전체 빌드/테스트 통과 확인.

**Files:**
- Modify: `docs/IMPLEMENTATION_PLAN.md` (Current Status Snapshot 갱신)
- Modify: `docs/plans/ACTIVE_SPRINT.md` (3A-SEC 태스크 추가 + 완료 처리)
- Modify: `frontend/CLAUDE.md` (CSP 관련 주석 업데이트)

**Step 1: 전체 빌드/테스트**

```bash
cd frontend && npm run build
# Expected: 0 errors

cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
# Expected: 54+ tests pass
```

**Step 2: 잔존 확인**

```bash
# unsafe-inline 잔존 (script-src에서만)
grep "unsafe-inline" frontend/vercel.json
# Expected: style-src에만 존재, script-src에는 없음

# define:vars 잔존
grep "define:vars" frontend/src/layouts/MainLayout.astro
# Expected: 0 results
```

**Step 3: IMPLEMENTATION_PLAN 갱신**

Current Status Snapshot의 `다음 메인라인 스프린트` 업데이트:
```markdown
- **완료된 단계:** 2B-OPS, 2C-EXP, 2D-INT, 3A-SEC
- **다음 메인라인 스프린트:** Phase 3 Intelligence 선택 대기
```

**Step 4: frontend/CLAUDE.md CSP 주석 갱신**

현재:
```
- `vercel.json` CSP: `script-src 'self' 'unsafe-inline'` 허용 (초기 FOUC 방지용 → 추후 nonce 방식으로 개선 가능)
```

변경:
```
- `vercel.json` CSP: `script-src 'self' 'sha256-...'` (FOUC 방지 스크립트 해시). `unsafe-inline` 제거 완료. FOUC 스크립트 내용 변경 시 해시 재계산 필요.
```

**Step 5: Commit**

```bash
git add docs/ frontend/CLAUDE.md
git commit -m "docs: update status for 3A-SEC completion"
```

---

## 의존성 순서

```
Task 1 (analytics 외부화) → Task 2 (해시 계산) → Task 3 (CSP 업데이트)
Task 3 완료 후 → Task 4 (보안 점검) → Task 5 (문서 + 최종 검증)
```

## 3A Gate

- [ ] `vercel.json` CSP `script-src`에 `'unsafe-inline'` 없음
- [ ] FOUC 방지 스크립트가 SHA-256 해시로 허용됨
- [ ] GA4/Clarity가 번들 외부 스크립트로 로드됨
- [ ] `npm run build` 0 error
- [ ] `pytest` 전체 통과
- [ ] 보안 점검 체크리스트 통과
- [ ] 문서 상태 갱신 완료
