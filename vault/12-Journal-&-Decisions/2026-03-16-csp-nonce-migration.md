---
title: "CSP Nonce 마이그레이션 여정"
date: 2026-03-16
tags:
  - journal
  - security
  - csp
  - astro
  - phase-3a-sec
---

# CSP Nonce 마이그레이션 여정

> 날짜: 2026-03-16
> 관련 Phase: [[Phase-Flow]] → Phase 3A-SEC (2026-03-08~09)
> 관련 문서: [[Security]]

---

## 왜 이 글을 쓰는가

오늘 Cookie Consent 배너 작업을 하면서 CSP nonce 패턴이 현장에서 어떻게 작동하는지 다시 한 번 체감했다. 배너의 인라인 스크립트에 nonce를 붙이고, GA4 동적 로딩이 `strict-dynamic` 덕분에 별도 허용 없이 신뢰를 이어받는 것을 직접 확인했다. 이 패턴이 처음부터 이렇게 자연스럽지는 않았다. 3A-SEC 마이그레이션 당시의 과정을 기록해 둔다.

---

## Before: `unsafe-inline` 시대

마이그레이션 전 CSP 헤더는 대략 이런 모습이었다.

```
Content-Security-Policy:
  script-src 'self' 'unsafe-inline' https://www.googletagmanager.com ...
```

`unsafe-inline`은 편하다. `<script>` 태그에 아무것도 추가하지 않아도 된다. Astro의 `is:inline` 스크립트도, 작은 초기화 코드도 그냥 통과한다.

하지만 XSS 공격자가 어떻게든 인라인 스크립트를 주입하면 CSP가 아무런 방어를 못 한다는 게 문제다. CSP를 쓰는 핵심 이유인 "신뢰하지 않는 스크립트 차단"이 `unsafe-inline` 하나로 무너진다.

---

## 결정: nonce 기반으로 전환

Phase 3A-SEC에서 다음 목표를 세웠다.

1. `unsafe-inline` 제거
2. 요청마다 무작위 nonce 발급 → 해당 요청의 인라인 스크립트만 허용
3. `strict-dynamic` 추가 → nonce로 신뢰받은 스크립트가 동적으로 로드하는 스크립트도 신뢰

### 미들웨어 nonce 생성

Astro v5 미들웨어(`src/middleware.ts`)에서 요청마다 nonce를 생성하고 `Astro.locals.cspNonce`에 주입했다.

```ts
const nonce = crypto.randomUUID().replace(/-/g, '');
ctx.locals.cspNonce = nonce;
```

그리고 응답 헤더에 이 nonce를 포함한 CSP를 설정했다.

```
script-src 'nonce-{nonce}' 'strict-dynamic' 'self' ...
```

---

## 마이그레이션 작업: 인라인 스크립트 전수 교체

가장 손이 많이 간 부분이었다. 프로젝트 전체에서 `is:inline` 스크립트와 수동 `<script>` 태그를 찾아서 nonce를 붙여야 했다.

**변경 패턴:**

```astro
<!-- 변경 전 -->
<script is:inline>
  // 초기화 코드
</script>

<!-- 변경 후 -->
<script is:inline nonce={Astro.locals.cspNonce || ''}>
  // 초기화 코드
</script>
```

Astro의 번들된 `<script>` (is:inline 없는 것)는 Astro가 자동으로 nonce를 주입해 주므로 건드리지 않았다. 문제는 `is:inline`으로 직접 작성한 스크립트들이었다.

---

## `strict-dynamic`이 필요한 이유

GA4(gtag.js) 같은 서드파티 스크립트는 동적으로 `<script>` 태그를 DOM에 삽입한다.

```js
// gtag 초기화 패턴
(function(w,d,s,l,i){
  var f=d.getElementsByTagName(s)[0], j=d.createElement(s);
  j.src='https://www.googletagmanager.com/gtag/js?id='+i;
  f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','G-XXXXXXXX');
```

이 동적으로 생성된 `<script>` 태그에는 nonce가 없다. `strict-dynamic` 없이는 CSP가 이 스크립트를 차단한다.

`strict-dynamic`을 추가하면 "nonce로 신뢰받은 스크립트가 생성하는 스크립트는 자동으로 신뢰"한다. 즉, nonce를 가진 gtag 초기화 인라인 스크립트가 동적으로 로드하는 `gtag/js`는 별도 허용 없이 실행된다.

---

## Web Interface Guidelines 감사 결과

Phase 3A-SEC 기간 중 Web Interface Guidelines 감사를 함께 진행했다. 발견된 주요 이슈 5개:

| 번호 | 이슈 | 심각도 |
|------|------|--------|
| 1 | Open Redirect — 외부 URL로 리다이렉트 허용 | P0 |
| 2 | `<html lang>` 속성 누락 (KO 페이지) | P1 |
| 3 | `color-scheme` 메타 태그 미설정 | P2 |
| 4 | 버튼 로딩 상태 처리 부재 | P2 |
| 5 | 기타 접근성 속성 누락 | P3 |

CSP 자체와는 별개이지만, 보안 감사의 일환으로 함께 처리했다.

---

## 오늘 Cookie Consent에서 이 패턴을 다시 봤다

Cookie Consent 배너 스크립트를 작성할 때 이 패턴이 그대로 적용됐다.

- 배너의 인라인 스크립트 → `nonce={Astro.locals.cspNonce || ''}` 추가
- 동의 후 GA4 동적 로드 → 배너 스크립트가 nonce를 가지고 있으므로 `strict-dynamic`이 GA4 로딩을 허용
- 별도로 `https://www.googletagmanager.com`을 CSP에 추가할 필요 없음

처음에 이 구조를 설계할 때는 "이게 제대로 작동할까?" 의문이 있었는데, 오늘 실제로 동작하는 것을 보며 확신이 생겼다.

---

## 배운 것

1. **`unsafe-inline`은 기술 부채다.** 당장 편하지만 CSP의 핵심 가치를 무너뜨린다. 초기에 nonce 구조로 시작하는 게 맞다.

2. **`strict-dynamic`은 필수다.** 실제 웹앱에서 동적 스크립트 없이 작동하는 경우는 드물다. GA4, 채팅 위젯, 기타 서드파티가 모두 동적 로딩에 의존한다.

3. **마이그레이션 비용은 한 번이다.** 기존 코드베이스에 nonce를 붙이는 작업이 번거롭지만, 이후 새 스크립트를 추가할 때는 습관처럼 `nonce={Astro.locals.cspNonce || ''}`를 붙이게 된다.

4. **Astro의 번들 스크립트는 자동 처리된다.** `is:inline` 없는 `<script>` 태그는 Astro가 nonce를 자동 주입한다. `is:inline`만 수동으로 처리하면 된다.

---

## Related

- [[Phase-Flow]] — Phase 3A-SEC 위치 확인
- [[Security]] — 프로젝트 보안 설계 전반
- [[2026-03-16-news-pipeline-v3-decision]] — 같은 날 작성된 다른 결정 기록
