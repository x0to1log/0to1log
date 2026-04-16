---
title: News Pipeline Prompt Failure Measurement
date: 2026-04-16
parent_spec: 2026-04-15-news-pipeline-hardening-design.md
parent_plan: 2026-04-15-news-pipeline-hardening-phase2-plan.md
script: backend/scripts/measure_prompt_failures.py
---

# News Pipeline Prompt Failure Measurement (지난 14일)

## Sample
- 총 digest 수: **60** (4 digest/day × ~15일 — research/business × en/ko)
- auto_publish_eligible=true 비율: **8 / 60 (13.3%)** — 대부분 draft에 머무름

## Score 분포

| Bucket | Count | % |
|---|---|---|
| 90+ | 26 | 43% |
| 80-89 | 18 | 30% |
| 70-79 | 12 | 20% |
| <70 | 4 | 7% |

대부분 양호하지만 60% 가량이 90 미만 → 개선 여지 있음.

## Per-category 평균 점수

| Category | Mean | Min | Max | Sample N |
|---|---|---|---|---|
| **raw_llm.frontload** | **83.8** | **49** | 97 | 36 |
| raw_llm.expert_body | 94.6 | 76 | 100 | 36 |
| raw_llm.learner_body | 93.8 | 89 | 100 | 36 |
| llm.frontload (capped/0-20) | 16.8 | 10 | 19 | 36 |
| llm.expert_body (capped/0-20) | 19.1 | 15 | 20 | 36 |
| llm.learner_body (capped/0-20) | 18.8 | 18 | 20 | 36 |
| deterministic.locale | 10.0 | 10 | 10 | 36 |
| deterministic.structure | 15.0 | 15 | 15 | 36 |
| deterministic.traceability | 14.6 | 14 | 15 | 36 |

**핵심 발견**: `raw_llm.frontload`이 평균 83.8로 **다른 모든 카테고리보다 11~12점 낮음**. min=49까지 떨어짐 (가장 큰 분산).

## 가장 자주 flagged된 issue category Top 10

| Rank | Category | Count |
|---|---|---|
| 1 | **clarity** | **56** |
| 2 | **overclaim** | **48** |
| 3 | locale | 38 |
| 4 | source | 32 |
| 5 | accessibility | 26 |
| 6 | structure | 20 |
| 7 | calibration | 6 |
| 8 | language | 2 |
| 9 | actionability | 2 |

## 가장 자주 flagged된 scope Top 5

| Rank | Scope | Count | % of total |
|---|---|---|---|
| 1 | **frontload** | **106** | **46%** |
| 2 | ko | 42 | 18% |
| 3 | en | 28 | 12% |
| 4 | expert_body | 14 | 6% |
| 5 | frontload\|en\|ko | 8 | 3% |

`frontload` 단일 scope에 전체 이슈의 **46%**가 집중.

## Issue Severity

- minor: 204 (89%)
- major: 26 (11%)

## 🎯 Cross-tab: scope × category (Top 10 — 결정의 핵심)

| Rank | Scope + Category | Count |
|---|---|---|
| 1 | **frontload + overclaim** | **38** |
| 2 | **frontload + clarity** | **30** |
| 3 | **ko + locale** | **28** |
| 4 | frontload + source | 14 |
| 5 | en + clarity | 12 |
| 6 | frontload + accessibility | 8 |
| 7 | frontload + structure | 8 |
| 8 | en + source | 6 |
| 9 | en + accessibility | 6 |
| 10 | frontload + locale | 4 |

## Few-shot 타겟 결정

기준: 평균 점수가 낮은 카테고리(raw_llm.frontload, mean=83.8) ∩ issue 빈도가 높은 cross-tab 조합.

**Top 2 (Few-shot 추가 대상):**

### 1. 🎯 **Frontload — overclaim + clarity** (38 + 30 = 68건, scope의 46%)
- **타겟 프롬프트**: `prompts_news_pipeline.py`의 daily digest **frontload prompt** (헤드라인 / excerpt / focus_items 생성)
- **문제**:
  - overclaim — 사실보다 과장된 표현 ("판도 변경", "시대의 종말" 등)
  - clarity — 모호하거나 일반적인 표현 ("주요 발표가 있었다", "흥미로운 동향")
- **Few-shot 디자인**: 한 쌍의 ✅ 사실/구체 vs ❌ 과장/모호 헤드라인 예시

### 2. 🎯 **ko + locale** (28건)
- **타겟 프롬프트**: `_build_persona_system_prompt`의 한국어 본문 작성 규칙
- **문제**: 영어 직역, 어색한 어순, 외래어 과다, 한국어 헤딩 누락 등
- **Few-shot 디자인**: ✅ 자연스러운 한국어 vs ❌ 직역 한 쌍

### 3. 후보 (Top 2 결정 후 여유 있으면)
- `frontload + source` (14건) — frontload에서 source 누락
- `en + clarity` (12건) — 영어 본문도 clarity 이슈가 있음

## 결정

- **타겟 1**: Frontload prompt — overclaim + clarity (38+30=68건, 가장 큰 단일 실패 모드)
- **타겟 2**: ko persona content — locale (28건, 다른 scope)
- 두 타겟이 **서로 다른 scope**라 Few-shot이 충돌 없이 들어감
- 토큰 예산: 각 +80~100 토큰, 합계 +200 토큰 이내 (Phase 3 토큰 다이어트 -250 토큰 목표 안에서 흡수)

## 다음 단계
→ Phase 2 plan Task 7 진행: 위 두 프롬프트 식별 후 ✅/❌ 예시 한 쌍씩 추가
