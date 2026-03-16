---
title: "Handbook 병렬 스프린트 운영 — main 브랜치에서 충돌 없이 두 스프린트 동시 진행"
tags:
  - project-management
  - sprint
  - workflow
  - handbook
  - news-pipeline
date: 2026-03-16
---

# Handbook 병렬 스프린트 운영

## 배경

News Pipeline v2 스프린트가 진행 중인 상태에서 Handbook H1 스프린트를 병렬로 시작했다. 프로젝트는 [[Phase-Flow]]에 정의된 대로 main-only 워크플로우를 사용한다. 피처 브랜치 없이 두 스프린트를 같은 브랜치에서 동시에 운영한 셈인데, 결과적으로 충돌 없이 완료됐다.

## 두 스프린트의 성격 차이

| | News Pipeline v2 | Handbook H1 |
|---|---|---|
| 성격 | 백엔드 집중 | 프론트엔드 집중 |
| 주요 파일 | `services/pipeline.py`, `agents/`, `routers/news.py` | `pages/handbook/`, `components/handbook/`, `services/advisor.py` |
| DB 테이블 | `news_posts`, `pipeline_runs` | `handbook_terms` |
| 태스크 수 | 진행 중 | 8개 완료 |

Pipeline은 뉴스 수집·처리·저장 흐름을 다루는 서비스 레이어였고, Handbook은 용어 페이지 렌더링과 어드민 에디터, AI 어드바이저 기능이었다. 건드리는 파일 집합이 사실상 겹치지 않았다.

## 왜 충돌이 없었나

### 1. 파일 경계가 명확했다

두 스프린트가 공유하는 파일이 거의 없었다. Pipeline 쪽은 `backend/services/pipeline.py`와 `backend/agents/` 디렉토리를, Handbook 쪽은 `frontend/pages/handbook/`과 `backend/services/advisor.py`를 각각 독점했다. 같은 디렉토리에 있는 파일이라도 `services/pipeline.py`와 `services/advisor.py`는 완전히 독립된 모듈이었다.

### 2. DB 테이블이 분리되어 있었다

`handbook_terms`는 Pipeline이 전혀 건드리지 않는 테이블이다. 마이그레이션 충돌이나 RLS 정책 간섭이 발생할 여지가 없었다.

### 3. [[ACTIVE_SPRINT]]가 두 스프린트를 나란히 추적했다

단일 파일에서 두 스프린트의 태스크 상태를 함께 관리하니 어느 태스크가 `doing`인지 한눈에 보였다. 세션마다 무엇을 켜야 하는지 명확했다.

### 4. "태스크 1개만 doing" 규칙이 컨텍스트 스위칭을 막았다

[[Implementation-Plan]]의 워크플로우 규칙 — 한 번에 하나만 `doing`으로 전환 — 덕분에 한 세션에서 두 스프린트를 뒤섞지 않았다. Pipeline 태스크를 하는 세션과 Handbook 태스크를 하는 세션이 자연스럽게 분리됐다.

## Handbook H1 완료 내용

8개 태스크를 모두 완료했다:

- 용어 목록 페이지 (`/handbook`)
- 용어 상세 페이지 (`/handbook/[slug]`)
- 카테고리 필터 페이지 (`/handbook/category/[cat]`)
- 어드민 에디터 (신규 등록 / 수정)
- AI 어드바이저 4개 액션 (정의 생성, 예시 생성, 관련 용어 추천, 전체 초안)

이후 Handbook Quality 스프린트(유효성 검사, 벌크 작업, 소프트 딜리트, 4-dot 인디케이터)로 자연스럽게 이어졌다.

## 교훈

**솔로 프로젝트에서 브랜치 격리는 과대평가되어 있다.**

팀 프로젝트에서 피처 브랜치가 필요한 이유는 여러 사람이 같은 파일을 동시에 수정하기 때문이다. 혼자 작업할 때는 파일 경계만 깔끔하면 main 브랜치에서 두 스프린트를 병렬로 운영해도 충돌이 발생하지 않는다.

핵심 조건을 정리하면:

1. 두 스프린트가 건드리는 파일 집합이 겹치지 않을 것
2. DB 테이블이 독립적일 것
3. [[ACTIVE_SPRINT]]에 태스크 경계(파일 목록 포함)가 명시되어 있을 것
4. 세션 내에서 한 번에 하나의 컨텍스트만 유지할 것

이 조건이 성립하면 브랜치 생성·병합 오버헤드 없이 병렬 진행이 가능하다. 다음 Phase에서 비슷한 상황이 생기면 같은 방식을 적용할 것.

## 관련 문서

- [[ACTIVE_SPRINT]] — 병렬 스프린트 태스크 추적
- [[Phase-Flow]] — main-only 워크플로우 정책
- [[Implementation-Plan]] — "태스크 1개만 doing" 규칙
- [[2026-03-16-news-pipeline-v3-decision]] — Pipeline v3 의사결정 기록
