---
title: Admin Dashboard
tags:
  - features
  - tier-1
  - admin
  - mvp
source: docs/04_Frontend_Spec.md
---

# Admin Dashboard

콘텐츠 관리 + AI 파이프라인 제어를 위한 관리자 전용 인터페이스.

## 사이드바 구조

| 메뉴 | 역할 |
|---|---|
| **Dashboard** | 파이프라인 상태, 최근 발행, 비용 모니터링 개요 |
| **News** | AI NEWS 에디터 — Research/Business 관리, AI 제안 패널, 페르소나별 탭 전환 리뷰 |
| **Blog** | IT 블로그 에디터 — 마크다운 편집 + AI 어드바이저 |
| **Handbook** | AI 용어집 에디터 — 용어 CRUD + AI body 생성 + 일괄 발행/아카이브 |
| **Settings** | 사이트 설정, API 키, 프롬프트 버전 관리 |

## 에디터 공통 패턴

- ==마크다운 에디터==: Milkdown (Crepe) 기반 WYSIWYG
- ==AI Advisor 패널==: 각 에디터 옆에 AI 제안/수정 사이드 패널
- ==`esc()` 함수==: HTML attribute 이스케이프 공통 유틸리티

## URL 구조

- `/admin/` → 대시보드
- `/admin/news/` → 뉴스 관리
- `/admin/blog/` → 블로그 관리
- `/admin/handbook/` → 용어집 관리

## 파이프라인 제어

- 수동 파이프라인 트리거 (Research / Business 개별 실행)
- 파이프라인 실행 로그 조회 (`/admin/pipeline-runs/[runId]`)
- 실패 시 부분 재개 (Partial Resume) 지원

> [!note] 인증
> Admin 페이지는 Supabase Auth 세션 쿠키 기반 인증. RLS로 `admin` 역할 검증.

## Related

- [[Daily-Dual-News]] — News 에디터에서 관리하는 콘텐츠
- [[IT-Blog]] — Blog 에디터에서 관리하는 콘텐츠
- [[Handbook]] — Handbook 에디터 상세 (데이터 모델, 피드백, 검증)
- [[AI-News-Pipeline-Overview]] — Admin에서 트리거하는 파이프라인
- [[Frontend-Stack]] — Admin이 동작하는 프론트엔드 스택
