---
title: HB-QM Sprint Close (Handbook Quality & Content Migration) — 보류 종료
date: 2026-10-19
tags:
  - journal
  - sprint-close
  - handbook
---

# HB-QM Sprint Close — 보류 종료

> **기간:** 2026-04-10 ~ 2026-10-19 (보드 마지막 갱신 2026-04-22)
> **종료 사유:** 게이트(HB-MIGRATE-138, HB-SEED-800, HQ-01/02/11) 전부 핸드북 작업인데, 핸드북 파이프라인이 2026-05-24 이후 호출 0건으로 정지. 그 사이 실제 작업은 뉴스 파이프라인(beginner 페르소나, 퀴즈 분리, Supabase egress)과 GPT-6 전환으로 이동. → 게이트 미통과 상태로 **보류 종료** (Amy 결정 2026-10-19).
> **원본 보드:** [[ACTIVE_SPRINT-HB-QM-2026-10-19]] (`vault/90-Archive/2026-10/plans-archive/`, 읽기 전용)
> **다음 스프린트:** [[ACTIVE_SPRINT|NP-GPT6]]

## 스프린트 중 출하 (mid-sprint ship)
- NP-HARDEN (04-15~16), HB-MEASURE Phase 1 (04-16), **뉴스 파이프라인 v11** (04-18~21: rubric v2, quality gates, CP URL plumbing, rerun_from=quality)
- GPT-5 마이그레이션 완료 (04-19)
- Weekly content v2, weekly consolidation (04-19)
- **NQ-44 beginner 페르소나** (05-13~05-22: daily/weekly beginner, quiz-only 생성 분리, `d518a95a` 등)
- **NQ-34 QC 근거 admin 노출** (`cee54c6a`, `dda773c9`, `8fbcbb36`)
- 사이트 리디자인 (10-14~10-18, 다른 트랙) → 새 보드로 이관

## 종료(무효화)된 과제
| Task | 사유 |
|---|---|
| NP-OBSERVE-01~06 | 2026-04 관찰 기한 경과. GPT-6 전환 측정 도구로 대체 |
| NQ-30 | auto-publish threshold → GPT-6 Task 1.7 gate (cap 플래그 + 70)로 대체 (`1a1a0b1f`, `88ebb50c`) |
| NQ-31, NQ-32, NQ-33, NQ-35, NQ-42 | 4~5월 관찰·검증 과제, 기한 경과 |

## 보류 백로그로 이동 (새 보드 "보류 백로그")
- 핸드북: HB-MIGRATE-138, HB-SEED-01~50, HB-SEED-PROMPT-01, HB-MEASURE-02~04, HQ-01/02/03/06/07/08/11/12/13, HB-QUALITY-01~04, HB-UX-06
- 유령: README-01, UA-02~07, WEBHOOK-USER-01a~e
- OPTIONAL: COMMUNITY-01, HANDBOOK-LEVEL-LINK-01, QUALITY-HYBRID-01, PERF-TERMS-CACHE-01

## 교훈
- 보드가 6개월간 실제 작업과 어긋났다 (4/22 이후 커밋 438개). 세션 종료 시 sprint sync를 건너뛴 결과. → 큰 작업 전환(핸드북 → 뉴스) 시점에 스프린트를 바로 재정의했어야 했다.
- "doing" 상태로 6개월 남은 과제(HB-MEASURE-02, 커밋 0)는 보드 신뢰도를 떨어뜨린다. ghost 판정 규칙(14일 + 커밋 0)을 실제로 적용할 것.
