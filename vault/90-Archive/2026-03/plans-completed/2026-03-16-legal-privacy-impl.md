# Legal & Privacy Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Privacy Policy, Terms of Service pages, Cookie Consent banner (Accept All / Only Essential), and Footer links — making the site GDPR/KPIPA compliant for GA4 + Clarity analytics.

**Architecture:** 4 static-content Astro pages (EN/KO × Privacy/Terms) using `MainLayout`, a `CookieConsent.astro` component with `localStorage`-based opt-in gating, and consent-aware analytics loading in `MainLayout.astro`. Dead code `analytics.ts` removed.

**Tech Stack:** Astro v5, Tailwind CSS v4 (CSS variables), CSP nonce, ViewTransitions

**Spec:** `vault/09-Implementation/plans/2026-03-16-legal-privacy-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/i18n/index.ts` | Modify | Add cookie consent i18n keys |
| `frontend/src/components/Footer.astro` | Modify | Add Privacy + Terms links |
| `frontend/src/pages/en/privacy/index.astro` | Create | EN Privacy Policy page |
| `frontend/src/pages/ko/privacy/index.astro` | Create | KO Privacy Policy page |
| `frontend/src/pages/en/terms/index.astro` | Create | EN Terms of Service page |
| `frontend/src/pages/ko/terms/index.astro` | Create | KO Terms of Service page |
| `frontend/src/components/CookieConsent.astro` | Create | Cookie consent banner UI + logic |
| `frontend/src/layouts/MainLayout.astro` | Modify | Replace unconditional analytics with consent-gated loading + add CookieConsent |
| `frontend/src/scripts/analytics.ts` | Delete | Dead code removal |

---

## Task 1: i18n Keys for Cookie Consent

**Files:**
- Modify: `frontend/src/i18n/index.ts`

- [ ] **Step 1: Add EN cookie consent keys**

In `frontend/src/i18n/index.ts`, add these keys to the `en` object after the `products.outroCta` line:

```typescript
    'cookie.message': 'We use cookies for analytics to improve your experience.',
    'cookie.acceptAll': 'Accept All',
    'cookie.onlyEssential': 'Only Essential',
    'cookie.learnMore': 'Learn more',
```

- [ ] **Step 2: Add KO cookie consent keys**

Add to the `ko` object after the `products.outroCta` line:

```typescript
    'cookie.message': '사용자 경험 개선을 위해 분석용 쿠키를 사용합니다.',
    'cookie.acceptAll': '모두 수락',
    'cookie.onlyEssential': '필수만',
    'cookie.learnMore': '자세히 보기',
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/index.ts
git commit -m "feat(i18n): add cookie consent translation keys"
```

---

## Task 2: Footer — Add Privacy & Terms Links

**Files:**
- Modify: `frontend/src/components/Footer.astro`

- [ ] **Step 1: Add Privacy and Terms to the links array**

In `frontend/src/components/Footer.astro`, replace the `links` array (lines 11-15):

```typescript
const links = [
  { en: 'About', ko: 'About', href: '/en/about/', koHref: '/ko/about/' },
  { en: 'Privacy', ko: 'Privacy', href: '/en/privacy/', koHref: '/ko/privacy/' },
  { en: 'Terms', ko: 'Terms', href: '/en/terms/', koHref: '/ko/terms/' },
  ...(showPortfolio ? [{ en: 'Portfolio', ko: 'Portfolio', href: '/portfolio/' }] : []),
  { en: 'RSS', ko: 'RSS', href: '/rss.xml' },
];
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Footer.astro
git commit -m "feat(footer): add Privacy and Terms links"
```

---

## Task 3: Privacy Policy Pages (EN + KO)

**Files:**
- Create: `frontend/src/pages/en/privacy/index.astro`
- Create: `frontend/src/pages/ko/privacy/index.astro`

- [ ] **Step 1: Create EN Privacy Policy page**

Create `frontend/src/pages/en/privacy/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
---

<MainLayout
  title="Privacy Policy"
  description="Privacy Policy for 0to1log — how we collect and use your data."
  locale="en"
  slug="privacy/"
  headerAlwaysVisible={true}
>
  <div class="legal-page">
    <h1 class="legal-title">Privacy Policy</h1>
    <p class="legal-updated">Last updated: March 2026</p>

    <section class="legal-section">
      <h2>1. Introduction</h2>
      <p>0to1log ("we", "us", "our") operates the website <strong>0to1log.com</strong>. This Privacy Policy explains what data we collect, how we use it, and your rights regarding your personal information.</p>
    </section>

    <section class="legal-section">
      <h2>2. Data We Collect</h2>
      <h3>Analytics</h3>
      <p>With your consent, we use <strong>Google Analytics 4</strong> (page views, traffic sources, engagement) and <strong>Microsoft Clarity</strong> (heatmaps, session replays) to understand how visitors use the site and improve the experience. These tools use cookies that are only loaded after you consent.</p>
      <h3>Authentication</h3>
      <p>If you sign in, <strong>Supabase Auth</strong> stores your email and OAuth profile (Google/GitHub) for authentication and access control.</p>
      <h3>Performance</h3>
      <p><strong>Vercel Analytics</strong> collects Web Vitals and page performance metrics.</p>
    </section>

    <section class="legal-section">
      <h2>3. How We Use Your Data</h2>
      <ul>
        <li>Analyze visitor behavior and measure engagement (AARRR metrics)</li>
        <li>Improve user experience based on UX analytics</li>
        <li>Authenticate users and manage access</li>
        <li>Monitor site performance</li>
      </ul>
    </section>

    <section class="legal-section">
      <h2>4. Cookies</h2>
      <p>We use the following categories of cookies:</p>
      <ul>
        <li><strong>Essential:</strong> Supabase Auth session tokens — required for authentication, no consent needed.</li>
        <li><strong>Analytics:</strong> GA4 (<code>_ga</code>, <code>_gid</code>) and Clarity cookies — loaded only with your consent.</li>
      </ul>
      <p>You can manage your cookie preferences via the consent banner shown when you first visit the site.</p>
    </section>

    <section class="legal-section">
      <h2>5. Your Rights</h2>
      <p>Under the <strong>EU General Data Protection Regulation (GDPR)</strong> and the <strong>Korean Personal Information Protection Act (KPIPA)</strong>, you have the right to:</p>
      <ul>
        <li>Access the personal data we hold about you</li>
        <li>Request correction or deletion of your data</li>
        <li>Withdraw consent for analytics cookies at any time</li>
        <li>Object to processing of your data</li>
      </ul>
    </section>

    <section class="legal-section">
      <h2>6. Data Retention</h2>
      <p>Analytics data is retained according to Google Analytics and Microsoft Clarity default retention policies. Authentication data is retained while your account is active.</p>
    </section>

    <section class="legal-section">
      <h2>7. Contact</h2>
      <p>For questions about this Privacy Policy or to exercise your rights, contact us at <a href="mailto:CONTACT_EMAIL">CONTACT_EMAIL</a>.</p>
    </section>
  </div>
</MainLayout>

<style>
  .legal-page {
    max-width: 640px;
    margin: 0 auto;
    padding: 3rem 1.5rem 4rem;
  }
  .legal-title {
    font-family: var(--font-heading);
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  .legal-updated {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 2rem;
  }
  .legal-section {
    margin-bottom: 2rem;
  }
  .legal-section h2 {
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }
  .legal-section h3 {
    font-family: var(--font-heading);
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
    margin-top: 1rem;
  }
  .legal-section p,
  .legal-section li {
    font-family: var(--font-body);
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-text);
  }
  .legal-section ul {
    padding-left: 1.25rem;
    margin-top: 0.5rem;
  }
  .legal-section li {
    margin-bottom: 0.25rem;
  }
  .legal-section a {
    color: var(--color-accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .legal-section code {
    font-size: 0.9em;
    background: var(--color-bg-secondary);
    padding: 0.1rem 0.3rem;
    border-radius: 2px;
  }
</style>
```

- [ ] **Step 2: Create KO Privacy Policy page**

Create `frontend/src/pages/ko/privacy/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
---

<MainLayout
  title="개인정보처리방침"
  description="0to1log 개인정보처리방침 — 수집하는 데이터와 이용 방법을 안내합니다."
  locale="ko"
  slug="privacy/"
  headerAlwaysVisible={true}
>
  <div class="legal-page">
    <h1 class="legal-title">개인정보처리방침</h1>
    <p class="legal-updated">최종 수정: 2026년 3월</p>

    <section class="legal-section">
      <h2>1. 소개</h2>
      <p>0to1log("당사")는 <strong>0to1log.com</strong> 웹사이트를 운영합니다. 본 개인정보처리방침은 당사가 수집하는 데이터, 이용 방법, 그리고 귀하의 개인정보에 대한 권리를 설명합니다.</p>
    </section>

    <section class="legal-section">
      <h2>2. 수집하는 데이터</h2>
      <h3>분석</h3>
      <p>귀하의 동의 하에 <strong>Google Analytics 4</strong>(페이지 조회, 트래픽 소스, 참여도)와 <strong>Microsoft Clarity</strong>(히트맵, 세션 리플레이)를 사용하여 방문자 이용 행태를 분석하고 서비스를 개선합니다. 이 도구들은 동의 후에만 쿠키를 로드합니다.</p>
      <h3>인증</h3>
      <p>로그인 시 <strong>Supabase Auth</strong>가 이메일과 OAuth 프로필(Google/GitHub)을 저장하여 인증 및 접근 제어에 사용합니다.</p>
      <h3>성능</h3>
      <p><strong>Vercel Analytics</strong>가 Web Vitals 및 페이지 성능 지표를 수집합니다.</p>
    </section>

    <section class="legal-section">
      <h2>3. 데이터 이용 목적</h2>
      <ul>
        <li>방문자 행동 분석 및 참여도 측정</li>
        <li>UX 분석 기반 사용자 경험 개선</li>
        <li>사용자 인증 및 접근 관리</li>
        <li>사이트 성능 모니터링</li>
      </ul>
    </section>

    <section class="legal-section">
      <h2>4. 쿠키</h2>
      <p>다음 분류의 쿠키를 사용합니다:</p>
      <ul>
        <li><strong>필수:</strong> Supabase Auth 세션 토큰 — 인증에 필요하며, 동의 불필요.</li>
        <li><strong>분석:</strong> GA4(<code>_ga</code>, <code>_gid</code>)와 Clarity 쿠키 — 동의 후에만 로드.</li>
      </ul>
      <p>최초 방문 시 표시되는 동의 배너에서 쿠키 설정을 관리할 수 있습니다.</p>
    </section>

    <section class="legal-section">
      <h2>5. 귀하의 권리</h2>
      <p><strong>EU 일반개인정보보호법(GDPR)</strong> 및 <strong>한국 개인정보보호법(KPIPA)</strong>에 따라 다음의 권리가 있습니다:</p>
      <ul>
        <li>당사가 보유한 개인정보에 대한 열람 요청</li>
        <li>개인정보의 정정 또는 삭제 요청</li>
        <li>분석 쿠키에 대한 동의 철회</li>
        <li>개인정보 처리에 대한 이의 제기</li>
      </ul>
    </section>

    <section class="legal-section">
      <h2>6. 보유 기간</h2>
      <p>분석 데이터는 Google Analytics 및 Microsoft Clarity의 기본 보유 정책에 따릅니다. 인증 데이터는 계정이 활성 상태인 동안 보유합니다.</p>
    </section>

    <section class="legal-section">
      <h2>7. 연락처</h2>
      <p>본 개인정보처리방침에 대한 문의 또는 권리 행사를 원하시면 <a href="mailto:CONTACT_EMAIL">CONTACT_EMAIL</a>으로 연락해 주세요.</p>
    </section>
  </div>
</MainLayout>

<style>
  .legal-page {
    max-width: 640px;
    margin: 0 auto;
    padding: 3rem 1.5rem 4rem;
  }
  .legal-title {
    font-family: var(--font-heading);
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  .legal-updated {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 2rem;
  }
  .legal-section {
    margin-bottom: 2rem;
  }
  .legal-section h2 {
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }
  .legal-section h3 {
    font-family: var(--font-heading);
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
    margin-top: 1rem;
  }
  .legal-section p,
  .legal-section li {
    font-family: var(--font-body);
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-text);
  }
  .legal-section ul {
    padding-left: 1.25rem;
    margin-top: 0.5rem;
  }
  .legal-section li {
    margin-bottom: 0.25rem;
  }
  .legal-section a {
    color: var(--color-accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .legal-section code {
    font-size: 0.9em;
    background: var(--color-bg-secondary);
    padding: 0.1rem 0.3rem;
    border-radius: 2px;
  }
</style>
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors, routes `/en/privacy/` and `/ko/privacy/` listed in output

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/en/privacy/index.astro frontend/src/pages/ko/privacy/index.astro
git commit -m "feat(legal): add Privacy Policy pages EN/KO"
```

---

## Task 4: Terms of Service Pages (EN + KO)

**Files:**
- Create: `frontend/src/pages/en/terms/index.astro`
- Create: `frontend/src/pages/ko/terms/index.astro`

- [ ] **Step 1: Create EN Terms of Service page**

Create `frontend/src/pages/en/terms/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
---

<MainLayout
  title="Terms of Service"
  description="Terms of Service for 0to1log — usage conditions and policies."
  locale="en"
  slug="terms/"
  headerAlwaysVisible={true}
>
  <div class="legal-page">
    <h1 class="legal-title">Terms of Service</h1>
    <p class="legal-updated">Last updated: March 2026</p>

    <section class="legal-section">
      <h2>1. Acceptance</h2>
      <p>By accessing and using <strong>0to1log.com</strong>, you agree to these Terms of Service. If you do not agree, please discontinue use of the site.</p>
    </section>

    <section class="legal-section">
      <h2>2. AI-Generated Content</h2>
      <p>Parts of this site, including AI News articles and Handbook glossary entries, are generated or assisted by artificial intelligence. While we review content for quality, <strong>we do not guarantee the accuracy, completeness, or timeliness</strong> of AI-generated material. It is provided for informational purposes only.</p>
    </section>

    <section class="legal-section">
      <h2>3. Service Availability</h2>
      <p>0to1log is a solo project. The service may be <strong>interrupted, modified, or discontinued</strong> at any time without prior notice. We do not guarantee uptime or availability.</p>
    </section>

    <section class="legal-section">
      <h2>4. Intellectual Property</h2>
      <p>All content on this site, including text, graphics, and code, is the property of 0to1log unless otherwise noted. <strong>Unauthorized reproduction, distribution, or republication</strong> of site content is prohibited.</p>
    </section>

    <section class="legal-section">
      <h2>5. User-Generated Content</h2>
      <p>If community features are introduced in the future, users will be solely responsible for any content they submit. We reserve the right to remove content that violates these terms.</p>
    </section>

    <section class="legal-section">
      <h2>6. Limitation of Liability</h2>
      <p>0to1log is provided "as is" without warranties of any kind. We shall not be liable for any damages arising from the use or inability to use this service.</p>
    </section>

    <section class="legal-section">
      <h2>7. Changes to Terms</h2>
      <p>We may update these terms at any time. Continued use of the site after changes constitutes acceptance of the revised terms.</p>
    </section>

    <section class="legal-section">
      <h2>8. Contact</h2>
      <p>For questions about these Terms, contact us at <a href="mailto:CONTACT_EMAIL">CONTACT_EMAIL</a>.</p>
    </section>
  </div>
</MainLayout>

<style>
  .legal-page {
    max-width: 640px;
    margin: 0 auto;
    padding: 3rem 1.5rem 4rem;
  }
  .legal-title {
    font-family: var(--font-heading);
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  .legal-updated {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 2rem;
  }
  .legal-section {
    margin-bottom: 2rem;
  }
  .legal-section h2 {
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }
  .legal-section p,
  .legal-section li {
    font-family: var(--font-body);
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-text);
  }
  .legal-section a {
    color: var(--color-accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
</style>
```

- [ ] **Step 2: Create KO Terms of Service page**

Create `frontend/src/pages/ko/terms/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
---

<MainLayout
  title="이용약관"
  description="0to1log 이용약관 — 서비스 이용 조건 및 정책을 안내합니다."
  locale="ko"
  slug="terms/"
  headerAlwaysVisible={true}
>
  <div class="legal-page">
    <h1 class="legal-title">이용약관</h1>
    <p class="legal-updated">최종 수정: 2026년 3월</p>

    <section class="legal-section">
      <h2>1. 동의</h2>
      <p><strong>0to1log.com</strong>에 접속하고 이용함으로써 본 이용약관에 동의하는 것으로 간주됩니다. 동의하지 않을 경우 사이트 이용을 중단해 주세요.</p>
    </section>

    <section class="legal-section">
      <h2>2. AI 생성 콘텐츠</h2>
      <p>본 사이트의 AI 뉴스 기사 및 핸드북 용어집 등 일부 콘텐츠는 인공지능의 도움을 받아 생성됩니다. 품질을 검토하지만, AI 생성 콘텐츠의 <strong>정확성, 완전성 또는 적시성을 보장하지 않습니다</strong>. 정보 참고 목적으로만 제공됩니다.</p>
    </section>

    <section class="legal-section">
      <h2>3. 서비스 가용성</h2>
      <p>0to1log는 1인 프로젝트입니다. 서비스는 사전 고지 없이 <strong>중단, 변경 또는 종료</strong>될 수 있습니다. 서비스의 가동 시간이나 가용성을 보장하지 않습니다.</p>
    </section>

    <section class="legal-section">
      <h2>4. 지적재산권</h2>
      <p>본 사이트의 텍스트, 그래픽, 코드 등 모든 콘텐츠는 별도 표기가 없는 한 0to1log의 자산입니다. 사이트 콘텐츠의 <strong>무단 복제, 배포 또는 재게시</strong>를 금지합니다.</p>
    </section>

    <section class="legal-section">
      <h2>5. 사용자 생성 콘텐츠</h2>
      <p>향후 커뮤니티 기능이 도입될 경우, 사용자가 제출한 콘텐츠에 대한 책임은 전적으로 작성자에게 있습니다. 본 약관을 위반하는 콘텐츠는 삭제될 수 있습니다.</p>
    </section>

    <section class="legal-section">
      <h2>6. 책임 제한</h2>
      <p>0to1log는 어떠한 보증 없이 "있는 그대로" 제공됩니다. 서비스 이용 또는 이용 불가로 인해 발생하는 손해에 대해 책임지지 않습니다.</p>
    </section>

    <section class="legal-section">
      <h2>7. 약관 변경</h2>
      <p>본 약관은 언제든 변경될 수 있습니다. 변경 후 사이트를 계속 이용하면 변경된 약관에 동의한 것으로 간주됩니다.</p>
    </section>

    <section class="legal-section">
      <h2>8. 연락처</h2>
      <p>본 이용약관에 대한 문의는 <a href="mailto:CONTACT_EMAIL">CONTACT_EMAIL</a>으로 연락해 주세요.</p>
    </section>
  </div>
</MainLayout>

<style>
  .legal-page {
    max-width: 640px;
    margin: 0 auto;
    padding: 3rem 1.5rem 4rem;
  }
  .legal-title {
    font-family: var(--font-heading);
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  .legal-updated {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 2rem;
  }
  .legal-section {
    margin-bottom: 2rem;
  }
  .legal-section h2 {
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }
  .legal-section p,
  .legal-section li {
    font-family: var(--font-body);
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-text);
  }
  .legal-section a {
    color: var(--color-accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
</style>
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors, routes `/en/terms/` and `/ko/terms/` listed in output

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/en/terms/index.astro frontend/src/pages/ko/terms/index.astro
git commit -m "feat(legal): add Terms of Service pages EN/KO"
```

---

## Task 5: Cookie Consent Banner Component

**Files:**
- Create: `frontend/src/components/CookieConsent.astro`

- [ ] **Step 1: Create CookieConsent component**

Create `frontend/src/components/CookieConsent.astro`:

```astro
---
import { t } from '../i18n/index';
import type { Locale } from '../i18n/index';

interface Props {
  locale?: Locale;
}

const { locale = 'en' } = Astro.props;
const nonce = Astro.locals.cspNonce || '';
const gaId = import.meta.env.PUBLIC_GA4_ID || '';
const clarityId = import.meta.env.PUBLIC_CLARITY_ID || '';
const privacyHref = locale === 'ko' ? '/ko/privacy/' : '/en/privacy/';
---

<div
  id="cookie-consent"
  data-ga-id={gaId}
  data-clarity-id={clarityId}
  style="display: none; position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999; background-color: var(--color-bg-secondary); border-top: 1px solid var(--color-border); padding: 1rem 1.5rem;"
>
  <div style="max-width: 960px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
    <p style="font-family: var(--font-body); font-size: 0.9rem; color: var(--color-text); margin: 0; flex: 1; min-width: 200px;">
      {t[locale]['cookie.message']}
      <a href={privacyHref} style="color: var(--color-accent); text-decoration: underline; text-underline-offset: 2px; margin-left: 0.25rem;">
        {t[locale]['cookie.learnMore']}
      </a>
    </p>
    <div style="display: flex; gap: 0.5rem; flex-shrink: 0;">
      <button
        id="cookie-essential"
        type="button"
        style="font-family: var(--font-ui); font-size: 0.85rem; padding: 0.5rem 1rem; background: transparent; border: 1px solid var(--color-border); color: var(--color-text-muted); cursor: pointer; border-radius: 2px;"
      >
        {t[locale]['cookie.onlyEssential']}
      </button>
      <button
        id="cookie-accept"
        type="button"
        style="font-family: var(--font-ui); font-size: 0.85rem; padding: 0.5rem 1rem; background: var(--color-text-primary); color: var(--color-bg-primary); border: none; cursor: pointer; border-radius: 2px; font-weight: 600;"
      >
        {t[locale]['cookie.acceptAll']}
      </button>
    </div>
  </div>
</div>

<script is:inline nonce={nonce}>
  (function initCookieConsent() {
    function run() {
      var banner = document.getElementById('cookie-consent');
      if (!banner) return;

      var consent = localStorage.getItem('cookieConsent');
      if (consent) return; // already answered — hide banner

      banner.style.display = 'block';

      var acceptBtn = document.getElementById('cookie-accept');
      var essentialBtn = document.getElementById('cookie-essential');

      if (acceptBtn) {
        acceptBtn.onclick = function() {
          localStorage.setItem('cookieConsent', 'accepted');
          banner.style.display = 'none';
          loadAnalytics();
        };
      }

      if (essentialBtn) {
        essentialBtn.onclick = function() {
          localStorage.setItem('cookieConsent', 'declined');
          banner.style.display = 'none';
        };
      }
    }

    function loadAnalytics() {
      var banner = document.getElementById('cookie-consent');
      if (!banner) return;

      var gaId = banner.getAttribute('data-ga-id');
      var clarityId = banner.getAttribute('data-clarity-id');

      // GA4 — skip if already loaded
      if (gaId && !window.gtag) {
        var gs = document.createElement('script');
        gs.src = 'https://www.googletagmanager.com/gtag/js?id=' + gaId;
        gs.async = true;
        document.head.appendChild(gs);
        window.dataLayer = window.dataLayer || [];
        function gtag(){window.dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', gaId);
      }

      // Clarity
      if (clarityId && !window.clarity) {
        (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src='https://www.clarity.ms/tag/'+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
        })(window,document,'clarity','script',clarityId);
      }
    }

    // astro:page-load fires on initial load AND after ViewTransitions navigation
    // Guard against re-registration on ViewTransitions script re-execution
    if (!window.__cookieConsentInit) {
      window.__cookieConsentInit = true;
      document.addEventListener('astro:page-load', run);
    }
  })();
</script>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CookieConsent.astro
git commit -m "feat(cookie): add CookieConsent banner component"
```

---

## Task 6: MainLayout — Consent-Gated Analytics + CookieConsent Integration

**Files:**
- Modify: `frontend/src/layouts/MainLayout.astro`

- [ ] **Step 1: Add CookieConsent import**

In `frontend/src/layouts/MainLayout.astro`, add import after the existing imports (after line 5):

```typescript
import CookieConsent from '../components/CookieConsent.astro';
```

- [ ] **Step 2: Replace unconditional analytics with consent-gated script**

Replace lines 74-94 (the GA4 + Clarity inline scripts):

```astro
    {gaId && (
      <>
        <script is:inline nonce={nonce} src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`} async></script>
        <script is:inline nonce={nonce} define:vars={{ gaId }}>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', gaId);
        </script>
      </>
    )}

    {clarityId && (
      <script is:inline nonce={nonce} define:vars={{ clarityId }}>
        (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
        })(window,document,"clarity","script",clarityId);
      </script>
    )}
```

With this consent-gated version:

```astro
    <!-- Analytics: consent-gated (GDPR opt-in) -->
    <script is:inline nonce={nonce} define:vars={{ gaId, clarityId }}>
      (function() {
        if (localStorage.getItem('cookieConsent') !== 'accepted') return;

        // GA4 — skip if already loaded (ViewTransitions re-execution guard)
        if (gaId && !window.gtag) {
          var gs = document.createElement('script');
          gs.src = 'https://www.googletagmanager.com/gtag/js?id=' + gaId;
          gs.async = true;
          document.head.appendChild(gs);
          window.dataLayer = window.dataLayer || [];
          function gtag(){window.dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', gaId);
        }

        // Clarity — skip if already loaded
        if (clarityId && !window.clarity) {
          (function(c,l,a,r,i,t,y){
            c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
            t=l.createElement(r);t.async=1;t.src='https://www.clarity.ms/tag/'+i;
            y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
          })(window,document,'clarity','script',clarityId);
        }
      })();
    </script>
```

- [ ] **Step 3: Add CookieConsent component after Footer**

Replace line 107:

```astro
    {!isAdmin && <Footer locale={locale} pathname={Astro.url.pathname} />}
```

With:

```astro
    {!isAdmin && <Footer locale={locale} pathname={Astro.url.pathname} />}
    {!isAdmin && <CookieConsent locale={locale} />}
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/MainLayout.astro
git commit -m "feat(analytics): consent-gate GA4/Clarity loading in MainLayout"
```

---

## Task 7: Delete Dead Code — analytics.ts

**Files:**
- Delete: `frontend/src/scripts/analytics.ts`

- [ ] **Step 1: Verify no imports reference analytics.ts**

Search for any imports of `analytics.ts` in the codebase. The file reads from `meta[name="ga4-id"]` which is never rendered, confirming it's dead code.

Run: `cd frontend && grep -r "analytics" src/ --include="*.astro" --include="*.ts" -l`
Expected: Only `analytics.ts` itself and unrelated admin analytics pages (no imports of this file)

- [ ] **Step 2: Delete the file**

```bash
rm frontend/src/scripts/analytics.ts
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/scripts/analytics.ts
git commit -m "chore: remove dead analytics.ts (GA4/Clarity loads from MainLayout)"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Full build check**

Run: `cd frontend && npm run build`
Expected: 0 errors, all 4 new routes listed (`/en/privacy/`, `/ko/privacy/`, `/en/terms/`, `/ko/terms/`)

- [ ] **Step 2: Dev server manual check**

Run: `cd frontend && npm run dev`

Verify:
1. `/en/privacy/` — EN Privacy Policy renders with heading, sections, correct layout
2. `/ko/privacy/` — KO 개인정보처리방침 renders correctly
3. `/en/terms/` — EN Terms of Service renders correctly
4. `/ko/terms/` — KO 이용약관 renders correctly
5. Footer shows `About · Privacy · Terms · RSS` with correct locale links
6. Cookie consent banner appears at bottom on first visit
7. Clicking "Accept All" → banner disappears, `localStorage.cookieConsent === 'accepted'`
8. Clearing localStorage → banner reappears
9. Clicking "Only Essential" → banner disappears, `localStorage.cookieConsent === 'declined'`
10. GA4/Clarity scripts only load when consent is 'accepted' (check DevTools Network tab)

- [ ] **Step 3: CSP check**

Verify no CSP violations in browser console. All inline scripts must have nonce.

- [ ] **Step 4: Theme check**

Toggle light/dark/pink themes — cookie banner and legal pages should respect all theme variables.

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(legal): address verification issues"
```
