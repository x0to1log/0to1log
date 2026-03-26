# AI 제품 상세페이지 리디자인 설계

**날짜:** 2026-03-19
**상태:** 승인됨
**범위:** `frontend/src/components/products/ProductDetail.astro` + CSS

---

## 배경

현재 상세페이지는 단일 컬럼으로 섹션이 나열되어 있고, Media Gallery가 맨 위에 있어 제품 이름보다 이미지를 먼저 보게 된다. 섹션 순서도 "Key Features → Pricing → About" 순서라 스토리 흐름이 어색하다. Toolify 스타일을 참고해 재구성.

---

## 확정된 디자인 결정

### 1. 레이아웃: C타입 (Hero 2컬럼 + 본문 단일 컬럼)

**Hero 영역 2컬럼 구조 (C-1 패턴):**

```
┌─────────────────────────────────┬───────────────┐
│ (flex: 3)                       │ (flex: 1)     │
│ 제품 이름 (name_original)        │ 로고 이미지    │
│ name_ko (작게, KO 페이지만)      │ (흰 배경 박스) │
│ tagline                         │               │
│                                 │ platform 칩들 │
│ [Freemium 뱃지] [Visit Site ↗]  │ [✓ 한국어]    │
│                                 │ 👁 12.4k      │
└─────────────────────────────────┴───────────────┘
```

- **로고 없을 때 우측 컬럼 fallback:** 로고 슬롯 대신 카테고리 아이콘 또는 첫 글자 이니셜을 흰 배경 박스에 표시
- **모바일 fallback:** `@media (max-width: 639px)`에서 `flex-direction: column` — 이름·tagline·CTA가 먼저, 로고+메타가 아래
- **본문은 단일 컬럼 유지** — 콘텐츠가 빈약한 제품이 많아 사이드바가 어색해질 수 있음

### 2. Media Gallery 위치: Hero 아래

- **변경 전:** Media Gallery → Hero
- **변경 후:** Hero → Tags 행 → Media Gallery
- 이유: 제품을 처음 접하는 방문자는 이름·설명을 먼저 읽고 싶음. Gallery 없는 제품도 Hero~본문 흐름이 자연스러움.

### 3. 섹션 순서: 스토리 흐름

아래 순서가 최종 확정. "이게 뭐야? → 어떤 게 좋아? → 언제 쓰지? → 어떻게 시작하지? → 얼마야?" 순서.

```
① Hero (2컬럼 C-1)
② Tags 행 (Hero 바로 아래)
③ Media Gallery (demo_media 있을 때만)
④ About / 소개 (htmlDescription — 마크다운 렌더링 결과)
⑤ Key Features (features / features_ko 배열, ✦ 리스트)
⑥ Use Cases (use_cases / use_cases_ko 배열, → 리스트)
⑦ Getting Started (getting_started / getting_started_ko 배열, 번호 단계)
⑧ Pricing 상세 (pricing_detail / pricing_detail_ko 마크다운 테이블)
⑨ Related News (relatedNews 배열, 있을 때만)
⑩ Similar Tools (alternatives 배열 4개 카드)
⑪ FAQ (데이터 기반 템플릿 자동 생성)
⑫ Bottom CTA
```

**데이터 매핑 명확화:**
- About = `htmlDescription` prop (서버에서 마크다운 → HTML 렌더링된 결과, `set:html` 사용)
- Key Features = `product.features` (KO이면 `product.features_ko` 우선)
- Use Cases = `product.use_cases` (KO이면 `product.use_cases_ko` 우선)
- Getting Started = `product.getting_started` (KO이면 `product.getting_started_ko` 우선)
- Pricing 상세 = `product.pricing_detail` (KO이면 `product.pricing_detail_ko` 우선)

### 4. Tags 행 분리

- **현재:** platform·tags·stats·category가 `.product-detail-meta` 안에 혼합
- **변경:**
  - Hero 우측 컬럼: platform 칩 + 한국어 뱃지 + view_count/like_count stats
  - `.product-detail-tags-row` (새 CSS 클래스): `primary_category` 링크 칩 + `tags` 칩들 → Hero 아래 별도 행
- **`.product-detail-meta` 삭제** (기존 메타 행 전체 제거, 역할 분산)

---

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/components/products/ProductDetail.astro` | Hero 2컬럼 구조 재작성, 섹션 순서 변경, Tags 행 분리, Meta Chips 제거 |
| `frontend/src/styles/global.css` | `.product-detail-hero` 2컬럼 CSS, `.product-detail-hero-left/right` 스타일, `.product-detail-tags-row` 신규, 모바일 breakpoint |

---

## 변경하지 않는 것

- DB 스키마 (추가 컬럼 없음)
- 각 섹션의 내용·데이터 자체
- FAQ 템플릿 로직
- Related News 쿼리 로직
- Similar Tools 로직
- Admin 에디터

---

## 완료 기준

- [ ] Hero 영역이 2컬럼 (left flex:3 / right flex:1)으로 렌더링됨
- [ ] 로고 없을 때 우측에 이니셜 또는 카테고리 아이콘이 흰 배경 박스에 표시됨
- [ ] Media Gallery가 Tags 행 아래에 위치함
- [ ] 섹션 순서가 아래와 같이 렌더링됨 (spec의 ①-⑫ 순서가 기준, 현재 코드의 순서와 다름):
  `About → Key Features → Use Cases → Getting Started → Pricing 상세 → Related News → Similar Tools → FAQ`
- [ ] Tags 행(`.product-detail-tags-row`)이 Hero 아래 별도 행으로 표시됨
- [ ] 모바일(`max-width: 639px`)에서 Hero가 단일 컬럼으로 fallback됨 (이름 먼저, 로고 아래)
- [ ] `npm run build` 오류 없음
