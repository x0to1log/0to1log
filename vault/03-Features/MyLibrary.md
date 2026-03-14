---
title: MyLibrary
tags:
  - features
  - tier-2
  - library
source: docs/01_Project_Overview.md
---

# MyLibrary (내 서재)

사용자의 북마크, 읽기 기록, 저장 콘텐츠를 통합 관리하는 개인 서재.

## 주요 기능

- 북마크: 뉴스/블로그/용어 저장
- 읽기 기록: 최근 읽은 콘텐츠 히스토리
- 오프라인 읽기 (Phase 5 앱 확장 시)

## URL 구조

- `/library/` → 나의 서재

> [!info] DB 설계
> 북마크/읽기기록은 polymorphic `item_type` (`'news'`/`'blog'`/`'term'`)로 통합 관리. 단일 테이블에서 모든 콘텐츠 타입의 저장/기록을 처리.

## Related

- [[Daily-Dual-News]] — 북마크 대상 뉴스 콘텐츠
- [[IT-Blog]] — 북마크 대상 블로그 콘텐츠
- [[Database-Schema-Overview]] — 북마크/읽기기록 테이블 설계
