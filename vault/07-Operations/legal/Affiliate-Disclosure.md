---
title: Affiliate Disclosure
tags:
  - operations
  - legal
  - affiliate
---

# Affiliate 고지 (광고 표시)

> [!important] 법적 필수
> 한국 공정위 「추천·보증 등에 관한 표시·광고 심사지침」 + 미국 FTC 16 CFR Part 255에 따라, 경제적 이해관계가 있는 추천은 반드시 고지해야 한다.

## 고지 대상

- AI Products 페이지에서 `affiliate_url`이 설정된 제품의 "사이트 방문" 링크
- `is_sponsored = true`인 제품의 Featured 노출

## 고지 방식

> [!note] 원칙
> 광고/제휴 고지는 **해당 제품에만** 표시한다. 페이지 전체 고지는 하지 않는다.

| 유형 | 고지 위치 | 문구 예시 |
|---|---|---|
| **Affiliate 링크** | 해당 제품 카드 또는 상세 페이지 CTA 근처 | "이 링크를 통해 가입하면 소정의 수수료를 받을 수 있습니다" |
| **Sponsored 제품** | 해당 제품의 Featured 카드에 라벨 | "Sponsored" 또는 "광고" 배지 |

## AI 생성 리뷰 고지 (FTC 2026 신규)

> [!warning] 2026년부터 시행
> AI로 작성하거나 보강한 제품 리뷰에는 AI 사용 사실을 affiliate 고지와 함께 명시해야 한다.

- 0to1log의 AI Products 설명은 AI 파이프라인이 생성 → 해당됨
- 고지 문구 예시: "이 리뷰는 AI가 작성하였으며, 편집자가 검수하였습니다"
- Affiliate 고지와 같은 위치에 함께 표시

## DB 연결

- `ai_products.affiliate_url` — NULL이 아니면 affiliate 고지 대상
- `ai_products.is_sponsored` — true이면 Sponsored 라벨 표시

## Related

- [[Legal-&-Compliance]] — 법률 허브
- [[AI-Products]] — AI 제품 기능 개요
- [[Monetization-Roadmap]] — 수익화 단계와 법률 요건 연결
