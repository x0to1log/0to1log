---
title: "Pipeline Bilingual Generation Idea"
date: 2026-03-14
tags:
  - pipeline
  - architecture
  - future
status: idea
---

# Pipeline Bilingual Generation Idea

> [!abstract] 요약
> EN 생성 후 KO 번역하는 현재 구조 대신, **각 페르소나 생성 시 EN+KO를 한 쿼리에서 동시에 뽑는** 구조로 변경하는 아이디어.

## 현재 구조 (3 calls)

1. **Call 1**: expert EN + analysis + fact_pack + metadata → `gpt-4o`
2. **Call 2**: learner + beginner EN (expert 기반 파생) → `gpt-4o`
3. **Call 3**: 전체 EN→KO 번역 → `gpt-4o`

## 제안 구조 (3 calls)

1. **Call 1**: expert ==EN + KO== 동시 생성 (고품질 집중)
2. **Call 2**: learner ==EN + KO== (expert 기반 파생)
3. **Call 3**: beginner ==EN + KO== (expert 기반 파생)

## 기대 효과

- KO 번역이 "후처리"가 아니라 생성 시점에 나오므로 **번역 압축 문제 감소** (현재 `too short` 에러 원인)
- 각 페르소나가 전용 호출을 갖게 돼서 **품질 집중 가능**

## 우려 사항

- **출력 토큰 부담**: expert EN만 5000-7000자 + KO 4000자+ → 한 호출에 10000자+ 출력. `max_tokens=16384`으로 빠듯할 수 있음
- **부분 실패 시 재시도 비용**: EN은 통과했는데 KO가 짧으면 둘 다 재시도
- **리팩터링 규모 큼**: `pipeline.py`, `business.py`, `translate.py`, 프롬프트 전부 변경

## 선행 조건

- [[AI-News-Pipeline-Overview|파이프라인 대시보드]] 먼저 구축 → 변경 전후 비용/품질 비교 데이터 확보
- 충분한 baseline 데이터 수집 후 실험

## 관련 노트

- [[AI-News-Pipeline-Overview]]
- [[Quality-Gates-&-States]]
