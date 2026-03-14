---
title: Migration Log
tags:
  - meta
---

# Migration Log

| Date | From | To | Reason |
|------|------|----|--------|
| 2026-03-14 | `*.md.md` (37 files) | `*.md` | 이중 확장자 수정 |
| 2026-03-14 | `QUICK-DECISIONS.md` | `99-Reference/QUICK-DECISIONS.md` | 루트 정리, Reference 레이어로 이동 |
| 2026-03-14 | `_MOC.md` (root) | `90-Archive/2026-03/_MOC-old.md` | Features Map 내용을 `03-Features/_MOC.md`로 흡수 후 아카이브 |
| 2026-03-14 | — | `00-INDEX.md` 재작성 | 루트 대시보드 + 전체 레이어 MOC 링크 |
| 2026-03-14 | — | `_MOC.md` × 12 레이어 생성 | 01~09, 11, 12, 99 레이어 MOC 허브 노트 |
| 2026-03-14 | `System-Architecture.md` | wikilink 수정 | `Backend-API`→`Backend-Stack`, `Database-Schema`→`Database-Schema-Overview` |
| 2026-03-14 | `Persona-System.md` | wikilink 수정 | `AI-NEWS-Business`, `Database-Schema`, `Component-Library`, `AARRR-Metrics` → 실제 파일명 |
| 2026-03-14 | vault root: `00-INDEX.md`, `CURRENT-SPRINT.md`, `Structure_example.md`, `_migration-log.md` | `00-Root/` | 루트 정리, 00-Root 레이어 폴더 생성 |
| 2026-03-14 | `AI-News-Product.md` | wikilink 수정 | 테이블 내 `\|` 이스케이프 3건 (Persona-System, AI-Pipeline-Overview, KPI-Gates-&-Stages) |
| 2026-03-14 | — | `03-Features/Admin.md` 작성 | Admin Dashboard 기능 노트 |
| 2026-03-14 | `docs/02_Content_Strategy.md` | vault 변환 | Content-Strategy, Prompt-Guides, AI-News-Page-Layouts, Gamification-UI 작성 + Persona-System, Community-&-Gamification 보강 |
| 2026-03-14 | `docs/03_Backend_AI_Spec.md` | vault 변환 | Backend-Stack, Database-Schema-Overview, AI-Pipeline-Overview, Quality-Gates-&-States, Cost-Model-&-Stage-AB, Checklists-&-DoD 작성 + System-Architecture, Prompt-Guides 보강 |
| 2026-03-14 | `docs/04_Frontend_Spec.md` | vault 변환 | Design-System, Component-States, Mobile-UX, Animations-&-Transitions, Accessibility, Phase-Flow 작성 + Frontend-Stack, AI-News-Page-Layouts 보강 |
| 2026-03-14 | `Persona-System.md`, `_MOC-old.md` | wikilink 수정 | RAG/content_*/Business-Analyst-Agent → 실제 형식, AI-NEWS-Research/Business → Writing 접미사 |
| 2026-03-14 | `docs/05_Infrastructure.md` | vault 변환 | Infrastructure-Topology, Deployment-Pipeline, Security, Monitoring-&-Logging, Backup-&-Recovery-Playbook 작성 + Cost-Model-&-Stage-AB 보강 |
| 2026-03-14 | `docs/06_Business_Strategy.md` | vault 변환 | Business-Strategy, Monetization-Roadmap, KPI-Gates-&-Stages, SEO-&-GEO-Strategy, Growth-Loop-&-Viral 작성 |
| 2026-03-14 | `docs/07_Global_Local_Intelligence.md` | vault 변환 | Global-Local-Intelligence 작성 + Quality-Gates-&-States 보강 (발행 품질 게이트, EN-KO version lock) |
| 2026-03-14 | `docs/08_Handbook.md` | vault 변환 | Handbook 작성 (03-Features) + Handbook-Content-Rules 작성 (05-Content) |
| 2026-03-14 | `docs/IMPLEMENTATION_PLAN.md` | vault 변환 | Implementation-Plan 작성 (09-Implementation) + Checklists-&-DoD 보강 (태스크 DoD 규칙, 문서 운영 검증) |
| 2026-03-14 | `docs/03_Backend_AI_Spec.md` v3.3→v4.0 | vault v4 반영 | AI-Pipeline-Overview (순차 흐름 + 번역), Quality-Gates-&-States (재시도 테이블), Prompt-Guides (Expert-First Cascade), Cost-Model-&-Stage-AB (번역 비용 포함) 업데이트 |
| 2026-03-14 | `docs/plans/*` (29 files + 2 sprint files) | `vault/09-Implementation/plans/` | 설계/계획/스프린트 문서를 vault로 이전. CLAUDE.md workflow를 vault 기준으로 변경 |
