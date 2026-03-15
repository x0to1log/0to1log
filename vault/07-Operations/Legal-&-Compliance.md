---
title: Legal & Compliance
tags:
  - operations
  - legal
  - compliance
---

# Legal & Compliance

수익화(AdSense, Affiliate) 전에 반드시 갖춰야 하는 법률/컴플라이언스 정책. 사용자 신뢰와 플랫폼 승인의 기반이다.

## Privacy Policy (개인정보처리방침)

> [!important] AdSense 승인 필수 조건
> Google AdSense 신청 시 Privacy Policy 페이지가 없으면 자동 거절된다.

### 수집하는 데이터

| 수집 도구 | 수집 데이터 | 용도 |
|---|---|---|
| **GA4** | 페이지 조회, 트래픽 소스, engagement time, 이벤트 (persona_switch, share 등) | 사용자 행동 분석, AARRR 측정 |
| **MS Clarity** | 히트맵, 세션 리플레이, 분노 클릭, 스크롤 depth | UX 개선 |
| **Supabase Auth** | 이메일, OAuth 프로필 (Google/GitHub) | 인증, 어드민 접근 제어 |
| **Vercel Analytics** | Web Vitals, 페이지 성능 | 성능 모니터링 |

### 법적 근거

| 법률 | 적용 대상 | 핵심 요구사항 |
|---|---|---|
| **한국 개인정보보호법 (KPIPA)** | 한국 사용자 | 개인정보처리방침 공개 필수, 수집 항목·목적·보유기간 명시 |
| **EU GDPR** | EU 사용자 (EN 글로벌 서비스) | 명시적 동의(opt-in), 데이터 삭제 요청권, DPO 지정 (소규모 면제) |

### 호스팅

- URL: `/en/privacy/` + `/ko/privacy/`
- Astro 정적 페이지로 구현
- **Footer에 "Privacy" 링크로 상시 노출**
- 구현 시점: Phase 2

---

## Terms of Service (이용약관)

### 핵심 조항

| 조항 | 내용 |
|---|---|
| **AI 생성 콘텐츠 면책** | AI 파이프라인이 생성한 뉴스/용어집은 참고 자료이며, 정확성을 보장하지 않음 |
| **서비스 중단 가능성** | Solo 프로젝트로 사전 고지 없이 서비스가 중단될 수 있음 |
| **UGC 책임** | 댓글(Phase 4 커뮤니티)의 내용은 작성자 책임 |
| **지적재산권** | 사이트 콘텐츠의 무단 복제/재배포 금지 |

### 구현 시점

- Phase 2: 기본 이용약관 페이지 생성 (`/en/terms/`, `/ko/terms/`)
- Phase 4: 커뮤니티/구독 관련 조항 추가

---

## Cookie Consent (쿠키 동의)

### 쿠키 분류

| 분류 | 쿠키 | 필수 여부 |
|---|---|---|
| **필수 (Strictly Necessary)** | Supabase Auth 세션 토큰 | 동의 불필요 |
| **분석 (Analytics)** | GA4 (`_ga`, `_gid`), Clarity | 동의 필요 |
| **광고 (Advertising)** | AdSense (Phase 3 중반+) | 동의 필요 |

### 구현 방식

- **자체 구현** — 단순 배너 + localStorage 저장
- 비용 $0, Solo 프로젝트에 적합
- 페이지 하단에 쿠키 동의 배너 표시
- "동의" 클릭 시 `localStorage.cookieConsent = 'accepted'` 저장
- 미동의 시 GA4/Clarity 스크립트 로드 차단
- 구현 시점: **Phase 2**
- 트래픽 증가 시 전문 도구(CookieBot 등) 검토

---

## Affiliate 고지 (광고 표시)

> [!important] 법적 필수
> 한국 공정위 「추천·보증 등에 관한 표시·광고 심사지침」 + 미국 FTC 16 CFR Part 255에 따라, 경제적 이해관계가 있는 추천은 반드시 고지해야 한다.

### 고지 대상

- AI Products 페이지에서 `affiliate_url`이 설정된 제품의 "사이트 방문" 링크
- `is_sponsored = true`인 제품의 Featured 노출

### 고지 방식

> [!note] 원칙
> 광고/제휴 고지는 **해당 제품에만** 표시한다. 페이지 전체 고지는 하지 않는다.

| 유형 | 고지 위치 | 문구 예시 |
|---|---|---|
| **Affiliate 링크** | 해당 제품 카드 또는 상세 페이지 CTA 근처 | "이 링크를 통해 가입하면 소정의 수수료를 받을 수 있습니다" |
| **Sponsored 제품** | 해당 제품의 Featured 카드에 라벨 | "Sponsored" 또는 "광고" 배지 |

### DB 연결

- `ai_products.affiliate_url` — NULL이 아니면 affiliate 고지 대상
- `ai_products.is_sponsored` — true이면 Sponsored 라벨 표시

---

## 저작권 정책

### AI 생성 콘텐츠

| 콘텐츠 유형 | 저작권 상태 | 정책 |
|---|---|---|
| AI 뉴스 (Research/Business) | AI 생성물 — 저작권 불명확 | 사이트 콘텐츠로 게시, 제3자 무단 복제 금지 명시 |
| 핸드북 용어집 | AI 생성 + 사람 검수 | 동일 |
| 블로그 | 사람 작성 | 저작권 보호 |

### 뉴스 원문 인용

- Tavily API로 수집한 원문은 **요약·재가공**하여 사용 (원문 전체 게재 아님)
- 원문 출처 링크를 항상 포함 — fair use / 공정 이용 범위 내
- 원문 저작권자의 삭제 요청 시 즉시 대응 (DMCA takedown 정책)

### 라이선스

- **All Rights Reserved** — 모든 콘텐츠 무단 복제/재배포 금지
- Footer에 `© 2026 0to1log. All rights reserved.` 표기
- Premium 콘텐츠와의 충돌 방지 (CC 라이선스 미적용)

---

## AdSense 승인 체크리스트

AdSense 신청 전 반드시 충족해야 하는 항목:

- [ ] Privacy Policy 페이지 존재 (`/privacy/`)
- [ ] Terms of Service 페이지 존재 (`/terms/`)
- [ ] 충분한 콘텐츠 (==30개+ 포스트==)
- [ ] 명확한 네비게이션 (메뉴, 사이트맵)
- [ ] 오리지널 콘텐츠 (AI 생성이라도 고유한 가치 제공)
- [ ] 사이트 연령 6개월+ (일부 지역)
- [ ] Cookie consent 메커니즘 작동
- [ ] `ads.txt` 파일 설정

---

## Phase별 법률 Scope

| Phase | 필요 항목 | 시급도 |
|---|---|---|
| **Phase 1b~2** | Privacy Policy + Cookie Consent (GA4/Clarity 이미 사용 중) | ==높음== |
| **Phase 2 후반** | Terms of Service (콘텐츠 축적 후) | 중 |
| **Phase 3 초반** | Affiliate 고지 (AI Products Affiliate 시작 전) | 높음 |
| **Phase 3 중반** | AdSense 관련 (ads.txt, 승인 체크리스트) | 중 |
| **Phase 4** | 구독 환불 정책, 커뮤니티 가이드라인 | 중 |

> [!warning] 현재 상태
> GA4 + MS Clarity가 이미 활성화되어 있다면, Privacy Policy와 Cookie Consent는 **지금 당장** 필요하다. 법적 리스크가 낮은 초기 트래픽 단계이지만, 습관적으로 미루면 AdSense 신청 시 급하게 만들게 된다.

## Related
- [[Security]] — CSP 설정, 인증 보안
- [[Monetization-Roadmap]] — 수익화 단계와 법률 요건 연결

## See Also
- [[Business-Strategy]] — 비즈니스 의사결정 원칙 (06-Business)
