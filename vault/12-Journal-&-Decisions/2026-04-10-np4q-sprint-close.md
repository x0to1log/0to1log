---
title: NP4-Q Sprint Close (News Pipeline v4 Quality Stabilization)
date: 2026-04-10
tags:
  - journal
  - sprint-close
  - news-pipeline
---

# NP4-Q Sprint Close — News Pipeline v4 Quality Stabilization

> **기간:** 2026-03-15 ~ 2026-04-10 (27일)
> **commits:** 100+
> **완료율:** 100% (핵심 게이트 전부 통과)
> **다음 스프린트:** HB-QM (Handbook Quality & Content Migration)

---

## 주요 달성

### Pipeline Architecture (v4)

- v4 Pydantic 모델 (2 personas: Expert + Learner, Beginner 제거)
- Skeleton-map 라우팅 (Research/Business × Expert/Learner = 4 skeleton)
- Cron 자동화 + E2E 검증 + Backfill 지원
- News Run + Handbook Run 분리, `pipeline_logs` 로깅, `handbook_quality_scores` 테이블

### 퀄리티 v2

- 0~100 스코어링, Research/Business 기준 분리
- LLM 2차 용어 필터링 (gpt-4o-mini)
- Expert/Learner 양쪽 평가, gpt-4.1-mini, 12000자 truncation
- **QUALITY-CHECK-02** ✅ `b1fcf46`, `3661fd6`

### 직접 FastAPI 호출

- AdminAiConfig 컴포넌트 + 4개 에디터 직접 FastAPI 호출 전환
- Vercel 60s proxy timeout 완전 제거
- **FASTAPI-DIRECT-01** ✅ `c63a5e3`

### 뉴스 품질 v7 (NQ-*)

- **Done (17):** NQ-02 baseline, NQ-03/05/07 KO skeleton + 페르소나 톤 + Action Items, NQ-05b Expert 약어, NQ-06/06b CP 전면 재설계, NQ-08 랭킹 분리, NQ-10 citation 중복, NQ-11 CP MANDATORY, NQ-12 citation 포맷, NQ-13 multi-source enrichment, NQ-14 citation 번호, NQ-16 classify/merge 분리, NQ-17 health check, NQ-18 CP 스팸 필터, NQ-19 체크포인트, NQ-20 Writer 다중 소스, NQ-22 CP 전면 재설계 (Summarizer + Entity Search + Brave Discussions)
- **Remaining (5) → HB-QM 이월:** NQ-09, NQ-15, NQ-21, NQ-23, NQ-24

### 핸드북 재설계 (HB-REDESIGN)

- KO/EN Basic 7섹션 + Advanced 7섹션 (11→7 재작성)
- Hero card + References footer + Sidebar checklist 3개 컴포넌트
- HB-EDITOR-V2: 어드민 에디터 redesign 필드 편집 + JSON live validation
- 8개 샘플 용어 차별화 매트릭스 전부 통과

### 자동화

- **AUTOPUB-01** ✅ — Quality ≥85 자동 발행 + 2h 리뷰 윈도우 (07:00→09:00 KST) + draft 이메일 알림 + 어드민 dot (`76e3f51`, `74b13b5`, `711c05b`, `6b22647`)

### Weekly Recap

백엔드 완료, 프론트 통합만 남음 (→ HB-QM OPTIONAL).

### PROMPT-AUDIT (52개)

- **P0 2개:** citation-소스 매핑 해결, URL hallucination 방지
- **P1 9개:** 섹션 구조 싱크, 토큰 효율, few-shot 개선
- **P2 40개:** rolling 프롬프트 개선 작업에 자연스럽게 흡수 → **별도 track 종료** (2026-04-10)

---

## 파이프라인 진화

| v | 시기 | 주요 변경 | 상태 |
|---|------|-----------|------|
| v2 | 2026-01 | 모듈화, Pydantic, Tavily | ✅ |
| v3 | 2026-03-15 | Daily Digest, 6 페르소나×R/B | ✅ |
| v4 | 2026-03-17 | 2 페르소나, -33% 비용 | ✅ |
| v4.1+ | 2026-03-26 ~ 04-10 | Skeleton-map, 품질 안정화, Weekly Recap, AUTOPUB | ✅ NP4-Q 완료 |

---

## NP4-Q 최종 게이트 (전부 통과)

- [x] v4 core (skeleton-map, 2 personas)
- [x] Weekly Recap 백엔드
- [x] FASTAPI-DIRECT-01 (Admin timeout 회피)
- [x] QUALITY-CHECK-02 (Expert/Learner 양쪽 평가)
- [x] PROMPT-AUDIT P0/P1 배포 (P2는 rolling 흡수)

**ruff/pytest 최종 검증은 HB-QM 게이트로 이월** (HB-MIGRATE-138 완료와 함께 실행).

---

## 설계 참조 (NP4-Q 기간)

- [[2026-03-16-daily-digest-design]] — Daily Digest v3/v4 설계
- [[2026-03-16-weekly-digest-design]] — Weekly Digest 설계
- [[2026-03-17-news-pipeline-v4-design]] — v4 전환
- [[2026-03-18-prompt-audit-fixes]] — 프롬프트 감사 52개
- [[plans/2026-03-25-direct-fastapi-ai-calls]] — FASTAPI-DIRECT
- [[plans/2026-03-26-news-quality-check-overhaul]] — QUALITY-CHECK
- [[plans/2026-03-30-merge-classify-design]] — NQ-16
- [[plans/2026-03-30-multi-source-enrichment]] — NQ-13
- [[plans/2026-03-31-handbook-quality-audit]] — HQ source
- [[plans/2026-04-09-handbook-section-redesign]] — HB-REDESIGN master
- [[2026-04-10-handbook-section-redesign-shipped]] — 회고

---

## Related

- [[2026-03-16-pipeline-evolution-retro]] — 이전 파이프라인 진화 회고
- [[2026-04-10-handbook-section-redesign-shipped]] — 동시 기간 완료 회고

## See Also

- [[Phase-Flow]] — 스프린트 체인 전체 (09-Implementation)
- [[plans/ACTIVE_SPRINT]] — HB-QM 진행 중 (09-Implementation)
