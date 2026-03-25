---
title: "SEO 메타 태그 완성 + GA4 Data API 연동 + Site Analytics 개선"
date: 2026-03-25
type: journal
tags: [seo, ga4, analytics, admin]
---

# 2026-03-25 세션 — SEO + GA4 + Analytics

## 한 일

### 1. SEO 메타 태그 전체 페이지 적용
- 모든 페이지에 `description` prop 추가 → `Head.astro`에서 meta description, OG tags, canonical, Twitter card 자동 생성
- 숫자("95개+ 용어") 하드코딩 제거 — 2주 내 300개+ seed 예정이므로
- 이름("Amy Domin Kim") description에서 제거
- 대상 파일: homepage, handbook index/detail, news index/detail, blog index/detail, products index/detail, about (EN + KO 모두)

### 2. GA4 Data API 연동 준비
- Google Cloud 서비스 계정 생성 + JSON 키 발급
- GA4 속성에 서비스 계정 뷰어 권한 부여
- Railway `GA4_CREDENTIALS_JSON` + `GA4_PROPERTY_ID` 환경변수 설정
- 백엔드 `admin_ga4.py` 라우터 작성 (pageviews, sessions, top pages, traffic sources, countries)
- 프론트엔드 `/api/admin/ga4-analytics` proxy 작성
- **아직 배포 안 됨** — push 후 Railway 재배포 필요

### 3. Site Analytics 페이지 개선
- 탭 순서: Traffic → News → Handbook → Blog (Traffic이 기본)
- News 탭 추가: Total/Published/Draft stat 카드 + By Category/Locale/Type 칩 + Recent Posts
- Brief 카드 3개로 확장 (News, Handbook, Blog) — 3-column grid
- News brief 카드: indigo 테마 색상 (`#6366f1`)

### 4. 비즈니스 분석 세션 (별도 컨텍스트에서 진행)
- 6가지 축 검증 완료 → [[2026-03-25-Business-Reality-Check]]
- 포지셔닝 확정 → [[2026-03-25-business-pivot-decision]]
- Weekly Recap 파이프라인 = 다음 스프린트 최우선

## 배운 것

### Meta Description vs OG Tags vs Canonical vs Twitter Card
- **Meta description**: 구글 검색 결과 설명 텍스트 → 클릭률에 직접 영향
- **OG tags**: 카톡/슬랙/긱뉴스 등에 링크 공유 시 미리보기 카드
- **Canonical URL**: 같은 페이지 여러 URL → SEO 점수 분산 방지
- **Twitter card**: X에서 링크 공유 시 미리보기 카드
- 사이트맵이 "문을 여는 것"이라면, 이 태그들은 "간판을 다는 것"

### GA4 Data API 구조
- `GA4_PROPERTY_ID` (숫자) ≠ `PUBLIC_GA4_ID` (G-XXXXXXXX 측정 ID)
- 서비스 계정 JSON 키를 환경변수로 전달 → `google.oauth2.service_account.Credentials`로 인증
- `BetaAnalyticsDataClient` → `run_report()` → dimensions + metrics 조합

## 커밋

- `fix(seo): add meta description, OG tags, canonical, Twitter cards to all pages`

## 다음 할 일

- [ ] 백엔드 push → Railway 재배포 → GA4 데이터 확인
- [ ] 뉴스레터 서비스 가입 (Buttondown)
- [ ] Weekly Recap 파이프라인 설계 시작
