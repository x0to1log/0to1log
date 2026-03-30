---
title: Legal & Compliance
tags:
  - operations
  - legal
  - compliance
---

# Legal & Compliance

수익화(AdSense, Affiliate) 전에 반드시 갖춰야 하는 법률/컴플라이언스 정책. 사용자 신뢰와 플랫폼 승인의 기반이다.

## 정책 문서

| 문서 | 설명 |
|---|---|
| [[Privacy-Policy]] | 개인정보처리방침 — 수집 데이터, 법적 근거, 호스팅 |
| [[Terms-of-Service]] | 이용약관 — AI 콘텐츠 면책, 서비스 중단, UGC, 지적재산권 |
| [[Cookie-Consent]] | 쿠키 동의 — 쿠키 분류, Accept All / Only Essential 배너 |
| [[Affiliate-Disclosure]] | 제휴 고지 — 고지 대상, 방식, DB 연결 |
| [[Copyright-Policy]] | 저작권 정책 — AI 생성 콘텐츠, 뉴스 인용, 라이선스 |

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

| Phase | 비즈니스 이벤트 | 필요 법적 조치 | 적용 법률 | 상태 |
|---|---|---|---|---|
| **Phase 2 (현재)** | 이메일 회원가입 + 분석 쿠키 | ① 회원가입 동의 체크박스 | 한국 PIPA | ❌ |
| | | ② Privacy Policy DNT 대응 명시 | CalOPPA | ❌ |
| | | ③ Privacy Policy에 뉴스레터 수집 명시 | CalOPPA, PIPA | ❌ |
| **Phase 3 초** | 뉴스레터 시작 (Beehiiv) | ④ 이메일 수신 동의 (선택) | CAN-SPAM, 정보통신망법 | ❌ |
| | | ⑤ 모든 이메일에 수신거부 링크 | CAN-SPAM | ✅ Beehiiv 자동 |
| | | ⑥ 발신자 물리적 주소 표기 | CAN-SPAM | ⚠️ Beehiiv 설정 확인 필요 |
| **Phase 3 중** | Affiliate 링크 시작 | ⑦ 개별 제품에 Affiliate 고지 | FTC Endorsement | ❌ |
| | | ⑧ AI 생성 리뷰 고지 | FTC 2026 신규 | ❌ |
| | | ⑨ 한국어 이해관계 고지 | 한국 공정위 | ❌ |
| **Phase 3 중** | Google AdSense | ⑩ Privacy Policy에 광고 쿠키 추가 | GDPR, CalOPPA | — |
| | | ⑪ Cookie Consent 카테고리 분리 (필수/분석/광고) | GDPR | — |
| | | ⑫ AdSense 프로그램 정책 준수 + ads.txt | Google TOS | — |
| **Phase 3 후** | 댓글/UGC 기능 | ⑬ DMCA Agent 등록 (미국 저작권청, $6) | DMCA | — |
| | | ⑭ DMCA 고지/삭제 절차 페이지 | DMCA Safe Harbor | — |
| | | ⑮ 반복 침해자 계정 정지 정책 | DMCA | — |
| | | ⑯ Terms of Service에 UGC 라이선스 조항 | 저작권법 | — |
| **Phase 4** | Premium 구독 (Polar/Stripe) | ⑰ 결제 약관 + 환불 정책 | 한국 전자상거래법 | — |
| | | ⑱ 자동 갱신 고지 + 온라인 해지 용이성 | 캘리포니아 ARL | — |
| | | ⑲ 개인정보 제3자 제공 동의 (Stripe/Polar) | PIPA 제17조 | — |
| **Phase 5** | 네이티브 앱 (Expo) | ⑳ App Store/Play Store Privacy Labels | Apple/Google 정책 | — |
| | | ㉑ 인앱 결제 환불 정책 | 각 플랫폼 규정 | — |

> [!warning] 적용 법률 주의사항
> - **CalOPPA**: 매출/유저 수 기준 없이 캘리포니아 사용자가 접속 가능한 **모든 사이트**에 적용
> - **CCPA/CPRA**: 현재 미적용 (매출 $26.6M 이상, 또는 CA 주민 10만명+ 중 하나 충족 시 적용)
> - **CAN-SPAM 물리적 주소**: 모든 상업 이메일에 실제 주소 필수 (PO Box 가능). 벌금 건당 최대 $51,744
> - **FTC 2026 신규**: AI로 작성/보강한 제품 리뷰는 AI 사용 사실을 affiliate 고지와 함께 명시 필수
> - **캘리포니아 ARL**: 자동 갱신 구독은 결제 전 명확히 고지 + 온라인 해지 필수 ("이메일로 해지" = 위반)

---

## Related

- [[Security]] — CSP 설정, 인증 보안
- [[Monetization-Roadmap]] — 수익화 단계와 법률 요건 연결

## See Also

- [[Business-Strategy]] — 비즈니스 의사결정 원칙 (06-Business)
