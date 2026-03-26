# Product 상세페이지 리디자인 v2 — Clean Editorial 단일 컬럼

> Date: 2026-03-16
> Status: Approved

## 결정 사항

- 단일 컬럼 레이아웃 (Sidebar 제거)
- 비주얼 먼저 (Media Gallery → Hero)
- Features/Use Cases: 심플 ✦/→ 리스트
- 카드에서 로고 제거 (상세페이지에서만 표시)

## 페이지 흐름

1. Media Gallery (풀폭)
2. Hero — 로고(80px) + 이름 + 태그라인 + CTA + pricing
3. Meta Chips — platform, korean, category(링크) 가로 칩
4. Key Features — ✦ 심플 리스트
5. Description — 마크다운
6. Use Cases — → 심플 리스트
7. Similar Tools — 4개 카드 그리드
8. FAQ — 아코디언
9. Bottom CTA — Visit Site 반복

## 파일 변경

- `ProductDetail.astro` — 전면 재구성
- `ProductCard.astro` — 로고 제거
- `global.css` — sidebar CSS 제거 + 새 스타일
