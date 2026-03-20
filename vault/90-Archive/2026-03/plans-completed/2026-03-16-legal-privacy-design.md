---
title: "Legal & Privacy 구현 설계"
date: 2026-03-16
tags:
  - design
  - legal
  - privacy
  - cookie
---

# Legal & Privacy 구현 설계

Privacy Policy, Terms of Service, Cookie Consent 배너, Footer 링크를 한 번에 구현하는 설계.

> **참조:** [[Legal-&-Compliance]] (허브), [[Privacy-Policy]], [[Terms-of-Service]], [[Cookie-Consent]]

---

## 1. 페이지 & 라우팅

### 신규 페이지

| 페이지 | 경로 | 렌더링 |
|---|---|---|
| Privacy Policy EN | `/en/privacy/` | SSR (`prerender = false`) |
| Privacy Policy KO | `/ko/privacy/` | SSR |
| Terms of Service EN | `/en/terms/` | SSR |
| Terms of Service KO | `/ko/terms/` | SSR |

### 파일 구조

```
frontend/src/pages/
  ├── en/
  │   ├── privacy/index.astro
  │   └── terms/index.astro
  └── ko/
      ├── privacy/index.astro
      └── terms/index.astro
```

### 설계 결정

- **SSR (`prerender = false`)** — 프로젝트 전체 관례에 맞춤. 모든 기존 페이지가 `prerender = false` 사용. 법률 문서는 동적 데이터 불필요하지만 관례 일관성 우선
- **DB 미사용** — 정책 본문은 Astro 파일에 직접 작성
- **i18n 구조** — 기존 `/en/`, `/ko/` 명시적 구조 유지 (Astro 내장 i18n 미사용)
- **레이아웃** — `MainLayout.astro` 사용. 별도 법률 전용 레이아웃 불필요
- **SEO** — `Head.astro`로 canonical + hreflang 자동 처리. 각 페이지에서 `slug` prop 전달 필수 (`slug="privacy/"`, `slug="terms/"`)
- **meta description** — 법률 페이지 전용 description 설정 (기본값 대신 "Privacy Policy for 0to1log" 등)

---

## 2. Footer 변경

### 현재

```
About · Portfolio(조건부) · RSS
```

### 변경 후

```
About · Privacy · Terms · Portfolio(조건부) · RSS
```

### 변경 파일

`frontend/src/components/Footer.astro`

```typescript
const links = [
  { en: 'About', ko: 'About', href: '/en/about/', koHref: '/ko/about/' },
  { en: 'Privacy', ko: 'Privacy', href: '/en/privacy/', koHref: '/ko/privacy/' },
  { en: 'Terms', ko: 'Terms', href: '/en/terms/', koHref: '/ko/terms/' },
  ...(showPortfolio ? [{ en: 'Portfolio', ko: 'Portfolio', href: '/portfolio/' }] : []),
  { en: 'RSS', ko: 'RSS', href: '/rss.xml' },
];
```

---

## 3. Cookie Consent 배너

### 동작 흐름

```
페이지 로드
  → localStorage.cookieConsent 확인
    → 'accepted'  → GA4 + Clarity 로드, 배너 미표시
    → 'declined'  → analytics 차단, 배너 미표시
    → 없음        → 배너 표시, analytics 차단 (opt-in 기본)
      → [Accept All]     → 'accepted' 저장, GA4 + Clarity 즉시 로드, 배너 닫기
      → [Only Essential] → 'declined' 저장, 배너 닫기
```

### 컴포넌트

**신규 파일:** `frontend/src/components/CookieConsent.astro`

- 화면 하단 고정 (`position: fixed; bottom: 0`)
- 기존 newsprint 디자인 토큰 사용
- 3테마(light/dark/pink) 대응
- `<script>` 블록으로 인터랙션 처리 (`client:load` 금지)
- CSP nonce 적용: `nonce={Astro.locals.cspNonce || ''}`

### 배치

`MainLayout.astro`에서 Footer 아래에 삽입:

```astro
<Footer locale={locale} pathname={pathname} />
<CookieConsent locale={locale} />
```

### 다국어 텍스트

| | EN | KO |
|---|---|---|
| 메시지 | We use cookies for analytics to improve your experience. | 사용자 경험 개선을 위해 분석용 쿠키를 사용합니다. |
| 버튼 1 | Accept All | 모두 수락 |
| 버튼 2 | Only Essential | 필수만 |
| 링크 | Learn more | 자세히 보기 |

텍스트는 `src/i18n/index.ts`에 추가.

### 버튼 스타일

- **Accept All** — primary 스타일 (강조)
- **Only Essential** — secondary/text 스타일 (비강조)

---

## 4. Analytics Consent 게이팅

### 현재 상태

GA4 + Clarity가 `MainLayout.astro` (lines 74~94)에서 `<script is:inline>` 블록으로 **무조건** 로드. GDPR/KPIPA 위반 상태.

> **참고:** `frontend/src/scripts/analytics.ts`는 dead code (meta 태그 기반이지만 실제 meta 태그가 렌더링되지 않음). 이 파일은 삭제한다.

### 변경 방식

**MainLayout.astro**에서 기존 GA4/Clarity 인라인 스크립트를 제거하고, consent 기반 조건부 로드로 교체:

```astro
<!-- Analytics: consent 기반 조건부 로드 -->
<script is:inline nonce={nonce} define:vars={{ gaId, clarityId }}>
  (function() {
    var consent = localStorage.getItem('cookieConsent');
    if (consent !== 'accepted') return;

    // GA4
    if (gaId) {
      var gs = document.createElement('script');
      gs.src = 'https://www.googletagmanager.com/gtag/js?id=' + gaId;
      gs.async = true;
      document.head.appendChild(gs);
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', gaId);
    }

    // Clarity
    if (clarityId) {
      (function(c,l,a,r,i,t,y){
        c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
        t=l.createElement(r);t.async=1;t.src='https://www.clarity.ms/tag/'+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
      })(window,document,'clarity','script',clarityId);
    }
  })();
</script>
```

### Cookie Consent 수락 시 즉시 로드

배너에서 "Accept All" 클릭 시, **페이지 새로고침 없이** 즉시 활성화:

1. `gaId`와 `clarityId`를 CookieConsent 컴포넌트에 `data-ga-id`, `data-clarity-id` 속성으로 전달
2. CookieConsent의 `<script>` 블록에서 수락 시 동일한 GA4/Clarity 초기화 로직을 동적 실행

```astro
<div id="cookie-consent" data-ga-id={gaId} data-clarity-id={clarityId}>
  ...
</div>
```

### ViewTransitions 대응

프로젝트가 `<ViewTransitions />`를 사용하므로:

1. CookieConsent 배너의 `<script>` 블록은 `DOMContentLoaded` 대신 `astro:page-load` 이벤트를 사용하여 클라이언트 사이드 네비게이션 후에도 정상 초기화
2. **중복 초기화 방지** — ViewTransitions 페이지 전환 시 DOM은 교체되지만 `window` 상태는 유지됨. MainLayout 인라인 스크립트가 재실행될 때 GA4/Clarity가 이미 로드된 경우 중복 초기화를 방지해야 함:
   - GA4: `if (window.dataLayer && window.dataLayer.length > 0) return;`
   - Clarity: `if (window.clarity) return;`

---

## 5. 변경 파일 요약

| 파일 | 변경 내용 |
|---|---|
| `frontend/src/pages/en/privacy/index.astro` | **신규** — EN Privacy Policy |
| `frontend/src/pages/ko/privacy/index.astro` | **신규** — KO Privacy Policy |
| `frontend/src/pages/en/terms/index.astro` | **신규** — EN Terms of Service |
| `frontend/src/pages/ko/terms/index.astro` | **신규** — KO Terms of Service |
| `frontend/src/components/CookieConsent.astro` | **신규** — Cookie Consent 배너 |
| `frontend/src/components/Footer.astro` | Privacy + Terms 링크 추가 |
| `frontend/src/scripts/analytics.ts` | **삭제** — dead code |
| `frontend/src/layouts/MainLayout.astro` | GA4/Clarity 인라인 스크립트를 consent 기반으로 교체 + CookieConsent 컴포넌트 삽입 |
| `frontend/src/i18n/index.ts` | Cookie Consent 다국어 텍스트 추가 |

---

## 6. 미구현 (YAGNI)

- 쿠키 설정 재변경 UI (설정 페이지 or Footer 링크) — GDPR Art.7(3) 동의 철회 용이성 요건 있으나, 현재 EU 트래픽 미미. 트래픽 증가 시 Footer "Cookie Settings" 링크로 최소 구현 검토
- 카테고리별 쿠키 토글 (필수/분석/광고 개별 선택) — Phase 3 AdSense 추가 시 검토
- 정책 본문 CMS 관리 — 변경 빈도 낮아 불필요

---

## Related

- [[Legal-&-Compliance]] — 법률 허브
- [[Privacy-Policy]] — 개인정보처리방침 정책 내용
- [[Terms-of-Service]] — 이용약관 정책 내용
- [[Cookie-Consent]] — 쿠키 동의 정책 내용
- [[Phase-Flow]] — Phase별 구현 범위
