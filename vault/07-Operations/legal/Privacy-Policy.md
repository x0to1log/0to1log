---
title: Privacy Policy
tags:
  - operations
  - legal
  - privacy
---

# Privacy Policy (개인정보처리방침)

> [!important] AdSense 승인 필수 조건
> Google AdSense 신청 시 Privacy Policy 페이지가 없으면 자동 거절된다.

## 수집하는 데이터

| 수집 도구 | 수집 데이터 | 용도 |
|---|---|---|
| **GA4** | 페이지 조회, 트래픽 소스, engagement time, 이벤트 (persona_switch, share 등) | 사용자 행동 분석, AARRR 측정 |
| **MS Clarity** | 히트맵, 세션 리플레이, 분노 클릭, 스크롤 depth | UX 개선 |
| **Supabase Auth** | 이메일, OAuth 프로필 (Google/GitHub) | 인증, 어드민 접근 제어 |
| **Vercel Analytics** | Web Vitals, 페이지 성능 | 성능 모니터링 |

## 법적 근거

| 법률 | 적용 대상 | 핵심 요구사항 |
|---|---|---|
| **한국 개인정보보호법 (KPIPA)** | 한국 사용자 | 개인정보처리방침 공개 필수, 수집 항목·목적·보유기간 명시 |
| **EU GDPR** | EU 사용자 (EN 글로벌 서비스) | 명시적 동의(opt-in), 데이터 삭제 요청권, DPO 지정 (소규모 면제) |

## 호스팅

- URL: `/en/privacy/` + `/ko/privacy/`
- Astro 정적 페이지로 구현
- **Footer에 "Privacy" 링크로 상시 노출**
- 구현 시점: Phase 2

## Related

- [[Legal-&-Compliance]] — 법률 허브
- [[Cookie-Consent]] — 쿠키 동의 메커니즘
- [[Security]] — CSP 설정, 인증 보안
