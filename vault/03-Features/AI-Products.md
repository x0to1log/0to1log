# AI Products — 기능 개요

> 상태: 설계 완료 (2026-03-15)
> 담당: Amy (solo)
> 관련 문서:
> - 설계: `vault/09-Implementation/plans/2026-03-15-ai-products-design.md`
> - DB 스키마: `vault/09-Implementation/plans/2026-03-15-ai-products-schema.md`
> - 카테고리 분류: [[AI-Products-Categories]]
> - UX 레이아웃: [[AI-Products-Page-Layouts]]

---

## 개요

AI Products는 다양한 AI 도구와 서비스를 큐레이션하는 페이지다.
단순한 링크 모음(디렉토리)이 아니라, 각 도구에 에디토리얼 설명을 붙인 **큐레이션 매거진** 형식.

AI를 처음 접하는 초보자가 방문했을 때 **"대단한 사이트를 발견했다"**는 감동을 줄 수 있는 경험을 목표로 한다.

---

## 핵심 콘셉트

- **디렉토리 + 큐레이션 블로그의 혼합**: 링크 모음이면서, 각 제품마다 에디토리얼 설명 포함
- **AI 창작 도구 중심**: 이미지/영상/음성/텍스트 생성 도구에 집중
- **초보자 친화**: 카테고리마다 "이게 뭔지" 바로 알 수 있는 설명 제공
- **DB 기반 콘텐츠 관리**: Supabase `ai_products` 테이블로 관리, 어드민에서 추가/수정

---

## 타겟 유저

- AI 도구에 관심이 생긴 비개발자/일반인
- AI 창작(그림, 영상, 음악)을 시작하고 싶은 크리에이터
- "요즘 AI로 뭘 만들 수 있지?" 궁금한 입문자

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| Hero 섹션 | Featured 제품 3~5개 대형 카드 노출 |
| 카테고리 탐색 | 7개 카테고리별 에디토리얼 설명 + 제품 카드 |
| 제품 상세 페이지 | 미디어 갤러리 + 에디토리얼 설명 + 가격 정보 |
| 언어 전환 | `/en/products/` ↔ `/ko/products/` |
| 메인 페이지 연동 | featured 상위 5개를 홈 페이지에 노출 |
| 한국어 지원 표시 | 한국어 사용 가능 여부 배지 |

---

## URL 구조

```
/en/products/           → 전체 목록 (EN)
/en/products/[slug]/    → 상세 페이지 (EN)
/ko/products/           → 전체 목록 (KO)
/ko/products/[slug]/    → 상세 페이지 (KO)
```

---

## Navigation 반영

```
헤더 navItems에 추가:
EN: "AI Products" → /en/products/
KO: "AI 제품군" → /ko/products/
```

## Related
- [[Daily-Dual-News]] — 뉴스 큐레이션과 연결
- [[Admin]] — 어드민에서 제품 관리

## See Also
- [[AI-Products-Page-Layouts]] — UI 레이아웃 설계 (08-Design)
