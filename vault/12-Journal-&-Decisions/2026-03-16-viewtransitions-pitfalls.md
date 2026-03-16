---
title: "Astro Islands + ViewTransitions 실전 함정들"
date: 2026-03-16
tags:
  - journal
  - astro
  - viewtransitions
  - islands
  - frontend
  - debugging
---

# Astro Islands + ViewTransitions 실전 함정들

오늘 CookieConsent 배너 작업을 하면서 [[Frontend-Stack]]의 ViewTransitions 동작 방식을 제대로 파고들었다. 정리해두지 않으면 나중에 또 같은 함정에 빠질 것 같아서 기록.

## 배경

현재 프로젝트는 어드민 페이지를 제외한 모든 페이지에 `<ViewTransitions />`를 활성화해두고 있다. 덕분에 페이지 전환이 SPA처럼 부드럽지만, 그 이면에는 MPA와 SPA 사이의 묘한 중간 지점에서 오는 함정들이 숨어있다.

핵심 원칙은 하나다: **DOM은 교체되지만 `window` 상태는 유지된다.**

---

## 함정 1: `is:inline` 스크립트와 리스너 누적

`is:inline` 속성이 붙은 `<script>` 블록은 VT 페이지 이동 시마다 다시 실행된다. 일반 Astro `<script>` 블록과 달리 번들링·중복 제거가 적용되지 않기 때문이다.

문제는 그 안에서 `addEventListener('astro:page-load', fn)`을 호출하면, 페이지를 이동할 때마다 동일한 핸들러가 `window`에 계속 쌓인다는 것이다. 3번 이동하면 리스너가 3개, 10번이면 10개.

```js
// 나쁜 패턴
document.addEventListener('astro:page-load', () => {
  initSomething();
});
```

**해결책**: `window.__flag` 가드로 최초 1회만 등록한다.

```js
// 올바른 패턴
if (!window.__myListenerRegistered) {
  window.__myListenerRegistered = true;
  document.addEventListener('astro:page-load', () => {
    initSomething();
  });
}
```

---

## 함정 2: 애널리틱스 스크립트 중복 로드 (GA4 / Clarity)

MainLayout의 인라인 스크립트에는 쿠키 동의 후 GA4와 Clarity를 동적으로 로드하는 로직이 있다. VT 이동 시마다 이 스크립트가 재실행되면서, 사용자가 이미 동의한 상태라면 GA4를 또 로드하려는 시도가 생긴다.

스크립트 태그가 이미 `<head>`에 존재해도, 자바스크립트로 동적으로 `<script>` 태그를 append하면 일부 브라우저에서 재실행이 발생하거나 전역 객체가 꼬일 수 있다.

**해결책**: 전역 객체 존재 여부를 먼저 확인한다.

```js
// GA4
if (!window.gtag) {
  loadGoogleAnalytics();
}

// Clarity
if (!window.clarity) {
  loadClarity();
}
```

---

## 함정 3: `DOMContentLoaded`는 VT 이후에 발화하지 않는다

일반 MPA에서 초기화 코드를 `DOMContentLoaded`에 걸어두는 것은 자연스러운 패턴이다. 하지만 ViewTransitions 이후의 페이지 이동은 전체 HTML을 새로 파싱하는 것이 아니라 DOM을 부분 교체하는 방식이므로, `DOMContentLoaded`가 다시 발화하지 않는다.

최초 진입 시에는 발화하지만, 이후 VT를 통한 이동에서는 침묵한다.

**해결책**: `astro:page-load` 이벤트를 사용한다. 이 이벤트는 최초 로드와 VT 이후 모두에서 발화한다.

```js
// 나쁜 패턴 — VT 이후 동작 안 함
document.addEventListener('DOMContentLoaded', init);

// 올바른 패턴
document.addEventListener('astro:page-load', init);
```

---

## 함정 4: `astro:after-swap` vs `astro:page-load` 타이밍 차이

두 이벤트의 타이밍을 구분하는 것이 중요하다.

| 이벤트 | 발화 시점 | 용도 |
|---|---|---|
| `astro:after-swap` | DOM 교체 직후, 페인트 이전 | 테마·다크모드 복원, 레이아웃 시프트 방지 |
| `astro:page-load` | DOM 준비 완료, 페인트 이후 | 일반 초기화, 이벤트 바인딩 |

테마 복원처럼 **깜빡임 없이** 적용되어야 하는 것은 `astro:after-swap`에, 나머지 일반적인 초기화는 `astro:page-load`에 넣는 것이 원칙이다.

```js
// 테마 복원 — 페인트 전에 적용해야 깜빡임 없음
document.addEventListener('astro:after-swap', () => {
  applyTheme(localStorage.getItem('theme'));
});

// 일반 초기화 — DOM 준비 후
document.addEventListener('astro:page-load', () => {
  initComponents();
});
```

---

## 오늘의 실전 사례: CookieConsent 배너

CookieConsent 배너는 위 함정들을 모두 만나는 좋은 예제였다.

- 배너 표시 로직: `astro:page-load`로 이동 (함정 3 해결)
- 리스너 등록: `window.__cookieConsentListenerReady` 가드 추가 (함정 1 해결)
- GA4/Clarity 로드: `!window.gtag`, `!window.clarity` 가드 추가 (함정 2 해결)
- 배너 숨김 상태 복원: `astro:after-swap`에서 처리 고려 (함정 4 참조)

---

## 프로젝트 규칙 재확인

[[Frontend-Stack]]에 명시된 대로, `.astro` 파일에서 `client:load` 디렉티브는 금지다. Island 수화가 필요한 경우 명시적으로 다른 디렉티브를 쓰거나, 순수 `<script>` 블록으로 처리한다. 이 규칙과 위의 VT 함정들을 함께 이해하면 Astro의 스크립트 실행 모델 전체가 하나의 그림으로 연결된다.

---

## 정리

ViewTransitions는 UX를 크게 향상시키지만, `window`와 DOM의 생명주기가 분리된다는 점을 항상 염두에 두어야 한다. `is:inline` 스크립트는 "매 이동마다 재실행"이라고 기억하고, 모든 초기화 코드는 `DOMContentLoaded` 대신 `astro:page-load`로 작성하는 것을 습관으로 삼자.
