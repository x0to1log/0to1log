---
title: Pipeline Stage Logging Schema
created: 2026-03-15
tags:
  - operations
  - logging
  - pipeline
  - observability
---

# Pipeline Stage Logging Schema

> 파이프라인: [[AI-News-Pipeline-Design]]
> 운영: [[AI-News-Pipeline-Operations]]
> 모니터링: [[Monitoring-&-Logging]]

파이프라인 1회 실행당 6~8개의 `pipeline_logs` 레코드가 생성된다. 각 레코드는 하나의 스테이지를 나타내며, `debug_meta` JSONB에 퀄리티 검사용 상세 정보를 포함한다.

---

## 스테이지 목록

| pipeline_type | 설명 | LLM 호출 | 횟수/run |
|--------------|------|---------|---------|
| `collect` | Tavily 뉴스 수집 | No | 1 |
| `rank` | LLM 후보 랭킹 | Yes | 1 |
| `facts:{post_type}` | 팩트 추출 | Yes | 1~2 |
| `persona:{post_type}:{name}` | 페르소나 콘텐츠 생성 | Yes | 3~6 |
| `save:{post_type}` | DB 저장 | No | 1~2 |
| `summary` | 실행 요약 | No | 1 |

총 6~8개 (research + business 모두 생성 시 최대).

---

## pipeline_logs 컬럼 활용

| 컬럼 | LLM 스테이지 | 비-LLM 스테이지 |
|------|------------|----------------|
| `tokens_used` | 총 토큰 | — |
| `cost_usd` | USD 비용 | — |
| `model_used` | e.g. `gpt-4o` | — |
| `duration_ms` | 스테이지 소요 시간 | 스테이지 소요 시간 |
| `attempt` | 재시도 횟수 (0-based) | — |
| `post_type` | research / business | research / business |
| `debug_meta` | 상세 JSON (아래 참조) | 상세 JSON (아래 참조) |

---

## debug_meta 스키마 — 스테이지별

### `collect` — 뉴스 수집

```json
{
  "target_date": "2026-03-10",     // null이면 오늘
  "is_backfill": true,
  "mode": "backfill",              // "backfill" 또는 "daily"
  "queries": ["AI artificial intelligence news", ...],
  "date_kwargs": {"start_date": "2026-03-09", "end_date": "2026-03-10"},
  "total_results": 30,             // 중복 제거 전
  "unique_candidates": 18          // 중복 제거 후
}
```

### `rank` — LLM 랭킹

```json
{
  "input_tokens": 1250,
  "output_tokens": 180,
  "llm_input": "[1] GPT-5 Released (https://...)\\n[2] AI Fund...",  // 처음 1000자
  "llm_output": {
    "research": {"title": "GPT-5 Released", "url": "...", "score": 0.9, "reason": "..."},
    "business": {"title": "AI Fund", "url": "...", "score": 0.85, "reason": "..."}
  },
  "candidates_count": 18,
  "attempts": 1
}
```

### `facts:{post_type}` — 팩트 추출

```json
{
  "input_tokens": 3500,
  "output_tokens": 950,
  "llm_input": "Title: GPT-5 Released\\nURL: ...\\n\\n[raw_content 전체 기사, 최대 8000자]",  // 처음 1000자
  "llm_output": {
    "headline": "GPT-5 Released with Major Improvements",
    "headline_ko": "GPT-5 출시, 주요 성능 개선 달성",
    "key_facts": [{"id": "f1", "claim": "...", ...}],
    "numbers": [...],
    "entities": [...],
    "sources": [...],
    "community_summary": "..."
  },
  "attempts": 1
}
```

### `persona:{post_type}:{name}` — 페르소나 생성

```json
{
  "input_tokens": 1800,
  "output_tokens": 4200,
  "attempts": 1,
  "en_length": 4500,              // EN 본문 글자 수
  "ko_length": 3800,              // KO 본문 글자 수
  "en_preview": "## Executive Summary\\nOpenAI has...",  // 처음 500자
  "ko_preview": "## 핵심 요약\\nOpenAI가..."              // 처음 500자
}
```

> [!note] 페르소나 출력 트림
> 페르소나 본문은 길어서 (3000~5000자) 전체를 debug_meta에 저장하면 DB 비대해짐. `en_preview`/`ko_preview`로 500자씩만 저장하고, 전체 본문은 `news_posts` 테이블에서 확인.

### `save:{post_type}` — DB 저장

```json
{
  "slug_base": "2026-03-10-gpt-5-released",
  "locales": ["en", "ko"]
}
```

### `summary` — 실행 요약

```json
{
  "input_tokens": 12000,          // 전체 누적
  "output_tokens": 18000,         // 전체 누적
  "mode": "backfill",
  "target_date": "2026-03-10",
  "batch_id": "2026-03-10",
  "total_posts": 4,
  "total_cost": 0.28,
  "picks": ["research", "business"]
}
```

---

## Run Detail UI 표시

Admin `/admin/pipeline-runs/{runId}` 페이지에서:

- **Run Context 카드**: `collect` 스테이지의 `mode`, `target_date`, `date_kwargs`, `unique_candidates` 표시
- **백필 배지**: `mode === 'backfill'`이면 Hero 영역에 경고 색상 칩 표시
- **Stage Timeline**: 각 스테이지 카드에 input/output 토큰 칩 + debug_meta 펼치기 패널
- **Created Posts**: `pipeline_batch_id`로 `news_posts` 조회하여 생성된 draft 목록 표시

---

## LLM 입출력 트림 정책

| 항목 | 최대 길이 | 이유 |
|------|----------|------|
| `llm_input` | 1000자 | 프롬프트가 길 수 있으므로 요약만 |
| `llm_output` (rank, facts) | 전체 저장 | JSON 구조이고 크기가 작음 |
| `en_preview` / `ko_preview` | 500자 | 페르소나 본문은 news_posts에 전체 저장됨 |

---

## Related
- [[Monitoring-&-Logging]] — 상위 모니터링 전략

## See Also
- [[AI-News-Pipeline-Operations]] — 파이프라인 운영 (04-AI-System)
