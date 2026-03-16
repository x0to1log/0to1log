---
title: Cookie Consent
tags:
  - operations
  - legal
  - cookie
---

# Cookie Consent (쿠키 동의)

## 쿠키 분류

| 분류 | 쿠키 | 필수 여부 |
|---|---|---|
| **필수 (Strictly Necessary)** | Supabase Auth 세션 토큰 | 동의 불필요 |
| **분석 (Analytics)** | GA4 (`_ga`, `_gid`), Clarity | 동의 필요 |
| **광고 (Advertising)** | AdSense (Phase 3 중반+) | 동의 필요 |

## 구현 방식

- **자체 구현** — 단순 배너 + localStorage 저장
- 비용 $0, Solo 프로젝트에 적합
- 페이지 하단에 쿠키 동의 배너 표시
- **Accept All / Only Essential** 패턴
  - Accept All → `localStorage.cookieConsent = 'accepted'` → GA4/Clarity 로드
  - Only Essential → `localStorage.cookieConsent = 'declined'` → GA4/Clarity 차단
- 미선택 시 기본값: analytics 차단 (GDPR opt-in 준수)
- 구현 시점: **Phase 2**
- 트래픽 증가 시 전문 도구(CookieBot 등) 검토

## Related

- [[Legal-&-Compliance]] — 법률 허브
- [[Privacy-Policy]] — 개인정보처리방침 (배너에서 "자세히 보기" 링크)
