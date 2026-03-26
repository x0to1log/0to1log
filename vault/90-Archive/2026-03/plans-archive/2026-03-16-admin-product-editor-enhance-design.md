# Admin Product Editor 강화 — 설계

> Date: 2026-03-16
> Status: Approved
> Feature: AI 원클릭 등록 강화 + 미리보기 + 프롬프트 품질

---

## 1. AI Generate from URL 강화

**현재:** tagline EN/KO + description EN/KO (4개)
**변경:** 아래 필드 모두 한 번에 생성, 없으면 null

| 필드 | 생성 방식 |
|------|----------|
| tagline EN/KO | AI (BAD/GOOD 예시 기반 프롬프트) |
| description EN/KO | AI |
| pricing | AI (페이지에서 추론, 불확실하면 null) |
| platform | AI (다운로드 링크/API docs에서 추론, 없으면 []) |
| korean_support | AI (한국어 UI/문서 존재 여부, 불확실하면 false) |
| tags | AI (3-5개 키워드 추출, 없으면 []) |
| logo_url | Clearbit → Google Favicon fallback. 둘 다 실패하면 null |

### 프롬프트 변경

`backend/services/agents/product_advisor.py`의 `GENERATE_FROM_URL_SYSTEM` 전면 리라이트:
- 모델: gpt-4o-mini → gpt-4o
- BAD/GOOD 예시 패턴 포함
- Tavily: `include_raw_content=True`, content 4000자
- temperature: 0.5 → 0.6, max_tokens: 1024 → 1500
- 반환 JSON에 pricing, platform, korean_support, tags 추가

### Apply 로직 변경

AI Panel의 "Apply" 버튼이 새 필드들도 에디터에 채움:
- pricing → select dropdown
- platform → comma-separated input
- korean_support → checkbox
- tags → comma-separated input
- logo_url → input + preview

### Logo URL 자동 수집

`generate_from_url` 결과에 logo_url이 없을 때:
1. 제품 URL에서 도메인 추출
2. `https://logo.clearbit.com/{domain}` 시도 (HEAD 요청으로 200 확인)
3. 실패 시 `https://www.google.com/s2/favicons?domain={domain}&sz=128` fallback
4. 둘 다 실패하면 null

---

## 2. 에디터 미리보기 (Preview Tabs)

에디터 콘텐츠 영역 아래, "More fields" 위에 프리뷰 섹션 배치:

```
[기본 필드: name, tagline, description...]
─────────────────────────────────────────
[📇 Card]  [📄 Detail]    ← 탭
─────────────────────────────────────────
  실시간 프리뷰 영역
─────────────────────────────────────────
<details> More fields </details>
```

### Card 탭
- ProductCard 실제 HTML 구조 렌더링
- thumbnail: demo_media[0] > thumbnail_url > category gradient fallback
- name, tagline, pricing badge, view count
- 필드 수정 시 JS로 실시간 반영

### Detail 탭
- 축약된 상세 페이지 레이아웃
- Header: logo + name + tagline
- Description: markdown → HTML 렌더 (간이 변환)
- Sidebar: pricing, platform, korean_support, tags
- 필드 수정 시 JS로 실시간 반영

---

## 3. 영향 범위

| 파일 | 변경 |
|------|------|
| `backend/services/agents/product_advisor.py` | 프롬프트 리라이트 + logo 수집 + 반환 필드 확장 |
| `frontend/src/pages/admin/products/edit/[slug].astro` | AI Apply 확장 + 미리보기 탭 UI + JS |
| `frontend/src/styles/global.css` | 미리보기 CSS |

### 변경 없음
- DB 스키마 (기존 필드 활용)
- API 엔드포인트 구조 (기존 `/api/admin/products/ai/generate` 재사용)
- 공개 페이지 (products index, detail)
