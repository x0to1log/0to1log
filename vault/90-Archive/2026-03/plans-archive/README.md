# Plan Files Archive (2026-03-03)

## 아카이브 대상 및 사유

### A. 미구현 기능 (향후 phase 예정)
**21개 파일** | 실제 구현 시작 전의 설계 및 스키마

#### AI Products (15개)
- 2026-03-15: `ai-products-design.md`, `ai-products-schema.md`, `category-nav-mobile-*.md`
- 2026-03-16: `admin-product-editor-enhance-*.md`, `product-detail-content-v3.md`, `product-detail-enhance-*.md`, `product-detail-redesign-v2.md`, `product-recommendation-plan.md`, `products-populate-plan.md`, `products-redesign-*.md`
- 2026-03-19: `ai-product-likes-design.md`, `product-detail-redesign-*.md`
- 2026-03-24: `product-search-corpus.md`, `products-content-enrichment.md`

#### Factcheck (2개)
- 2026-03-15: `factcheck-design.md`, `factcheck-impl.md`

#### Other Unstarted (4개)
- 2026-03-16: `theme-palette-refinement.md`
- 2026-03-19: `tag-system-improvements.md`
- 2026-03-20: `blog-category-system-design.md`, `blog-category-system-plan.md`

### B. 완료된 설계 (의사결정 참조용만 필요)
**11개 파일** | 설계 의도는 vault 핵심 문서에 흡수됨

- 2026-03-16: `prompt-architecture-v2-impl.md`, `prompt-audit-checklist.md`
- 2026-03-17: `floating-persona-switcher-design.md`, `floating-persona-switcher-impl.md`
- 2026-03-18: `admin-feedback-*.md`, `feedback-sheet-impl.md`, `frontend-design-*.md`, `unified-content-feedback-*.md`

### C. 구현 완료/통합됨
**8개 파일** | 코드에 반영되고 추가 참조 불필요

**UI/UX (2026-03-19~20, 4개):**
- `admin-editor-shared-extract.md`, `homepage-redesign-*.md`, `home-news-carousel-impl.md`

**코드 리뷰/버그픽스 (2026-03-24, 4개):**
- `astro-type-errors.md`, `code-review-bugfix*.md` (3개)

---

## 유지되는 파일들 (17개)

### 현재 진행 중 (6개)
- `2026-03-25-direct-fastapi-ai-calls.md` — Vercel timeout 회피
- `2026-03-25-quality-score-fix.md` — 점수 관리
- `2026-03-25-security-hardening-round2.md` — 보안
- `2026-03-25-weekly-recap-design.md` + `plan.md` — 주간 요약
- `2026-03-26-README-design.md` — 프로젝트 문서
- `2026-03-26-news-quality-check-overhaul.md` — 품질 체크 재작성

### 참조 기준 (7개)
- `2026-03-15-handbook-quality-design.md` — 핸드북 품질 기준 (진행 중)
- `2026-03-16-auto-publish-roadmap.md` — 다음 phase
- `2026-03-16-handbook-redesign-*.md` — 핸드북 UX (진행 중)
- `2026-03-16-weekly-digest-design.md` — 현재 구현 중
- `2026-03-18-handbook-advanced-quality-design.md` — 참조
- `2026-03-18-prompt-audit-*.md` (2개) — 진행 중

### 스프린트 추적 (1개)
- `ACTIVE_SPRINT.md` — 현재 스프린트 (매일 업데이트)

---

## 아카이브 시점
**2026-03-26** — News Pipeline v4 Quality Stabilization (NP4-Q) 96% 완료 기점에서 정리.

## 복구 방법
필요 시 파일명으로 이 폴더에서 검색:
```bash
find vault/90-Archive/2026-03/plans-archive/ -name "*<keyword>*"
```
