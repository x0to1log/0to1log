---
title: AI News Product
tags:
  - features
  - tier-1
  - tier-2
  - product
source: docs/01_Project_Overview.md
---

# AI News Product

0to1log의 핵심 제품 기능 모음. Tier별로 Phase에 맞춰 단계적 구현.

## Tier 1 — MVP 필수 (Phase 1-2)

| 기능 | 설명 |
|---|---|
| **[[Daily-Dual-News]]** | 매일 2개 AI NEWS: Research(자동) + Business(수동 검수) |
| **[[Persona-System\|Persona-Based RAG-Refine]]** | Business 포스트를 입문자/학습자/현직자 3버전으로 자동 재가공 |
| **멀티 에이전트 시스템** | Ranking → Research/Business → Editorial 4단계 [[AI-News-Pipeline-Overview\|AI 파이프라인]] |
| **관리자 에디터** | 마크다운 편집 + AI 제안 패널 + 페르소나별 탭 전환 리뷰 |
| **Pink Theme 디자인 시스템** | Dark/Light 적응형, Neon Pink 액센트, 반응형 레이아웃 |
| **SEO 기반 설계** | JSON-LD 구조화 데이터, 사이트맵 자동 생성, 메타 태그 최적화 |
| **[[IT-Blog]]** | 학습/프로젝트/커리어 포스팅 독립 운영 |
| **데이터 분석 도구** | GA4 + MS Clarity — 유저 행동 패턴 수집 |

## Tier 2 — 고도화 (Phase 3)

| 기능 | 설명 |
|---|---|
| **AI Semantic Search (Cmd+K)** | pgvector 임베딩 기반 자연어 검색 |
| **Dynamic OG Image** | 카테고리별 미리보기 이미지 자동 생성 |
| **AI Ops Dashboard** | API 비용 모니터링, 모델별 ROI, 프롬프트 버전 관리 |
| **Highlight to Share** | 문장 드래그 → SNS 공유 카드 (바이럴 장치) |
| **[[KPI-Gates-&-Stages\|AARRR 지표 대시보드]]** | GA4 데이터 기반 퍼널 시각화 |


## Related

- [[Daily-Dual-News]] — 핵심 뉴스 기능 상세
- [[Persona-System]] — 페르소나 재가공 시스템
- [[Frontend-Stack]] — 제품이 동작하는 프론트엔드 스택
- [[Phases-Roadmap]] — Tier별 구현 시점
