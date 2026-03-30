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
| **Beehiiv (뉴스레터)** | 이메일 주소 | 뉴스레터 발송 (제3자: Beehiiv 서비스) |

## Do Not Track (DNT) 대응

> [!important] CalOPPA 필수 요구사항
> Privacy Policy에 DNT 신호 대응 방법을 반드시 명시해야 한다.

- 0to1log는 DNT 신호를 **존중**한다
- Cookie Consent가 opt-in 기본값이므로, 동의 전까지 GA4/Clarity를 로드하지 않음 → DNT와 동일 효과
- Privacy Policy 페이지에 아래 문구 삽입 필요:

> **EN:** "Our site honors Do Not Track (DNT) signals. When we detect a DNT signal, we do not load analytics cookies (Google Analytics, Microsoft Clarity) unless you have explicitly accepted them through our cookie consent banner."
> **KO:** "본 사이트는 Do Not Track(DNT) 신호를 존중합니다. DNT 신호가 감지되면 쿠키 동의 배너에서 명시적으로 수락하지 않는 한 분석용 쿠키(Google Analytics, Microsoft Clarity)를 로드하지 않습니다."

## 뉴스레터 이메일 수집

- 수집 경로: 사이트 내 구독 폼 (헤더 봉투 모달 + 뉴스 상세 하단)
- 데이터 보관: 0to1log 자체 DB에 저장하지 않음, Beehiiv 서비스에서 관리
- 수신 거부: Beehiiv가 모든 이메일 하단에 unsubscribe 링크 자동 포함
- Privacy Policy 페이지에 뉴스레터 수집 사실을 명시해야 함

## 법적 근거

| 법률 | 적용 대상 | 핵심 요구사항 |
|---|---|---|
| **한국 개인정보보호법 (KPIPA)** | 한국 사용자 | 개인정보처리방침 공개 필수, 수집 항목·목적·보유기간 명시 |
| **EU GDPR** | EU 사용자 (EN 글로벌 서비스) | 명시적 동의(opt-in), 데이터 삭제 요청권, DPO 지정 (소규모 면제) |
| **CalOPPA** | 전 세계 (CA 사용자 접속 가능 시) | Privacy Policy 공개 필수, DNT 대응 명시, 매출/유저 기준 없음 |
| **CAN-SPAM** | 상업 이메일 발송 시 | 수신거부 링크, 물리적 주소, 10일 내 opt-out 처리 |

## 호스팅

- URL: `/en/privacy/` + `/ko/privacy/`
- Astro 정적 페이지로 구현
- **Footer에 "Privacy" 링크로 상시 노출**
- 구현 시점: Phase 2

## Related

- [[Legal-&-Compliance]] — 법률 허브
- [[Cookie-Consent]] — 쿠키 동의 메커니즘
- [[Security]] — CSP 설정, 인증 보안
