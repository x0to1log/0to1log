---
title: IT Blog
tags:
  - features
  - tier-1
  - blog
  - mvp
source: docs/01_Project_Overview.md
---

# IT Blog

수동 작성 포스팅. AI 뉴스와 ==독립 관리==. Admin에서 별도 섹션(Blog)으로 운영.

## 카테고리

| 카테고리 | AI 워크플로우 | 설명 |
|---|---|---|
| **학습 (Study)** | Type A (Multi-Targeting) | PyTorch, SQL 등 원리 설명, 코드 공유 |
| **커리어 (Career)** | Type B (Authentic Voice) | 성장 서사, 동기부여 — 작성자 목소리 유지 |
| **프로젝트 (Project)** | Type B (Authentic Voice) | 아키텍처 설계, 트러블슈팅 — 작성자 목소리 유지 |

## URL 구조

- `/en/blog/` → EN 블로그 리스트
- `/en/blog/[slug]` → EN 블로그 상세
- `/ko/blog/` → KO 블로그 리스트
- `/ko/blog/[slug]` → KO 블로그 상세

> [!info] DB 분리 운영
> `blog_posts` 테이블로 독립 관리. 워크플로우가 다르므로(파이프라인 자동 vs 수동 작성) AI News와 테이블 분리. 좋아요/댓글도 `blog_likes`/`blog_comments`로 분리. 북마크/읽기기록은 polymorphic `item_type` (`'news'`/`'blog'`/`'term'`)로 통합.

## Related
- [[Admin]] — Blog 에디터 관리

## See Also
- [[Content-Strategy]] — 블로그 콘텐츠 전략 (05-Content)
