# Handbook Seed 800 — Workspace

> **설계 문서:** [[2026-04-19-handbook-seed-800]]
> **역할:** 이 디렉토리는 Amy + Codex가 신규 800개 용어 후보를 JSONL로 수집하는 워크스페이스.

## 파일

| 파일 | 용도 |
|------|------|
| `_existing.jsonl` | 현재 DB의 published 138개 slug (중복 체크 레퍼런스). `backend/scripts/export_handbook_slugs.py`로 채움 |
| `01-llm-genai.jsonl` ~ `09-safety-ethics.jsonl` | 카테고리별 신규 용어 후보 |

## JSONL 스키마

각 카테고리 파일:
- **첫 줄**: `{"_meta": true, "category": ..., "target": ..., "vocabulary_hint": ..., "reference_style": ...}` — 파서가 스킵
- **이후 각 줄**: 용어 1개 = JSON 객체 1개

### 용어 객체

```json
{
  "term": "Mixture of Experts",
  "aliases": ["MoE"],
  "type": "model_algorithm_family",
  "note": "[2024+] frontier 모델 스케일 기법"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `term` | str | ✅ | 정식 명칭 (영어 권장). Python/도메인 표준 표기 우선 |
| `aliases` | list[str] | — | 약어·변형. 예: `["MoE"]`. 없으면 `[]` |
| `type` | str | ✅ | 아래 13개 term_type 중 하나 |
| `note` | str | — | 1줄 이유/플래그. 2024+ 신규 용어는 `[2024+]` 또는 `[2025+]` 접두어 |

### term_type 13개

| type | 뜻 | 예시 |
|------|----|------|
| `foundational_concept` | 기초 개념 | backpropagation, attention |
| `problem_failure_mode` | 문제·실패 양상 | hallucination, mode collapse |
| `model_algorithm_family` | 모델·알고리즘 계열 | Transformer, MoE, Diffusion |
| `training_optimization_method` | 학습·최적화 기법 | LoRA, RLHF, Adam |
| `retrieval_knowledge_system` | 검색·지식 시스템 | RAG, vector search |
| `system_workflow_pattern` | 시스템·워크플로 패턴 | speculative decoding, agent loop |
| `data_storage_indexing_system` | 데이터 저장·인덱싱 | Pinecone, FAISS, HNSW |
| `protocol_format_data_structure` | 프로토콜·포맷·자료구조 | MCP, GGUF, JSONL |
| `capability_feature_spec` | 모델 기능·스펙 | long context, tool use |
| `metric_benchmark` | 지표·벤치마크 | MMLU, BLEU, pass@1 |
| `product_platform_service` | 제품·플랫폼·서비스 | Claude, Vercel AI SDK |
| `library_framework_sdk` | 라이브러리·SDK | PyTorch, vLLM, LangChain |
| `hardware_runtime_infra` | 하드웨어·런타임 인프라 | H100, TensorRT |

> `volatility` / `intent` / `subtype`은 type에서 자동 도출 (`DEFAULT_VOLATILITY_BY_TYPE` 등) — Amy가 채우지 않음.

## 중복 체크 규칙

신규 용어가 다음과 겹치면 제외:
- `_existing.jsonl`의 `slug` 또는 `term` (정규화: 소문자·공백→하이픈)
- 다른 카테고리 파일의 `term` 또는 `aliases`

## 진행 상황

| # | File | Target | 현재 | 상태 |
|---|------|--------|------|------|
| 01 | `01-llm-genai.jsonl` | 180 | 0 | ⚪ |
| 02 | `02-deep-learning.jsonl` | 130 | 0 | ⚪ |
| 03 | `03-products-platforms.jsonl` | 110 | 0 | ⚪ |
| 04 | `04-ml-fundamentals.jsonl` | 90 | 0 | ⚪ |
| 05 | `05-infra-hardware.jsonl` | 90 | 0 | ⚪ |
| 06 | `06-data-engineering.jsonl` | 70 | 0 | ⚪ |
| 07 | `07-cs-fundamentals.jsonl` | 50 | 0 | ⚪ |
| 08 | `08-math-statistics.jsonl` | 40 | 0 | ⚪ |
| 09 | `09-safety-ethics.jsonl` | 40 | 0 | ⚪ |

현재 라인 수 확인 (bash):
```bash
for f in [0-9]*.jsonl; do echo "$f: $(($(wc -l < "$f") - 1))"; done
```
(첫 줄은 `_meta`라서 -1)

## 셋업 순서

### 1. 기존 138개 슬러그 추출 (1회)

```bash
cd backend && python scripts/export_handbook_slugs.py
```

결과: `_existing.jsonl`에 `{slug, term, term_type, categories, status}` per line 저장.

### 2. 용어 수집 (Codex + Amy)

#### Codex 역할 경계 (중요)

> **Codex는 후보를 제안만 한다. 선택·제거·수정·최종 승인은 Amy 본인이 한다.**

- Codex가 한 라운드에 **최대 50개 후보**를 제시
- Amy가 리뷰해서 채택/거절/수정 후 **Amy 판단으로** `.jsonl`에 append
- Amy가 제안 전량을 그대로 쓰면 E(직접 큐레이션) 취지 무효 → **최소 20~30%는 거르거나 수정**

#### 권장 프롬프트 뼈대 (Codex용)
```
이 카테고리에 2024~2026 시점 AI 용어 중 _existing.jsonl에 없는 것을
스키마대로 50개 "제안"해줘 (append 하지 말 것). 최신성 있는 것 우선.
정의는 하지 말고 term/aliases/type/note만. 내가 검토 후 선택적으로 반영할게.
```

### 3. 검증 & 다음 단계

(별도 플랜 예정) — 스키마·중복 validator → 병렬 생성 → 품질 게이트 → publish
