# NQ-19: 파이프라인 체크포인트 시스템 설계

> **상태:** 설계 확정 대기
> **목표:** 각 파이프라인 단계 결과를 DB에 저장, 임의 지점부터 재실행 가능. 어드민 UI에서 "이 단계부터 재실행" 버튼.

---

## 현재 문제

파이프라인 모든 단계가 메모리에서만 흘러감:
- Writer 출력이 불만족 → 전체 재실행 (수집부터 다시)
- CP 스팸 → 전체 재실행
- merge 과묶기 → 전체 재실행
- 재실행마다 수집 결과가 달라져서 기존에 잘 나온 쪽도 영향받음

## 해결: 체크포인트 저장 + 재실행 API

---

## DB 테이블

```sql
CREATE TABLE pipeline_checkpoints (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(run_id, stage)
);

-- RLS: service_role만 접근 (백엔드 전용)
ALTER TABLE pipeline_checkpoints ENABLE ROW LEVEL SECURITY;
```

### 단계별 저장 데이터

| stage | data 내용 | 예상 크기 |
|-------|----------|----------|
| `collect` | `{candidates: [{url, title, snippet, source, raw_content}]}` | ~250KB |
| `classify` | `{research_picks: [...], business_picks: [...]}` | ~2KB |
| `merge` | `{research: [ClassifiedGroup], business: [ClassifiedGroup]}` | ~5KB |
| `community` | `{community_map: {url: text}}` | ~10KB |
| `rank` | `{research: [ranked groups], business: [ranked groups]}` | ~5KB |
| `enrich` | `{enriched_map: {url: [{url, title, content}]}}` | ~175KB |

**총 ~450KB/run, 월 ~13MB** — Supabase 무료 티어에서도 여유.

---

## 재실행 흐름

### 재실행 시작 지점별 동작

```
from_stage=write:
  DB에서 enrich 체크포인트 로드 → write 실행 (category 파라미터로 research/business 선택 가능)

from_stage=community:
  DB에서 merge 체크포인트 로드 → community → rank → enrich → write

from_stage=merge:
  DB에서 classify 체크포인트 로드 → merge → community → rank → enrich → write

from_stage=classify:
  DB에서 collect 체크포인트 로드 → classify → merge → community → rank → enrich → write

from_stage=collect:
  처음부터 전체 실행 (기존과 동일)
```

### 백엔드 API

```
POST /api/admin/pipeline/rerun
Body: {
  "run_id": "uuid",
  "from_stage": "write",          // collect|classify|merge|community|write
  "category": "research"          // optional — write 단계만. null이면 둘 다
}
```

- 기존 `generate_news_digest()` 함수를 리팩토링해서 시작 지점을 파라미터로 받음
- 새 pipeline_run을 생성하되 `run_key`에 `rerun-` 접두사
- 각 단계 실행 전에 해당 체크포인트를 DB에서 로드

---

## 구현 순서

### Task 1: Supabase에 pipeline_checkpoints 테이블 생성
- SQL migration 실행
- RLS 정책 설정

### Task 2: pipeline.py에 체크포인트 저장 로직 추가
- 각 단계 완료 후 `_save_checkpoint(supabase, run_id, stage, data)` 호출
- upsert (UNIQUE 제약조건 활용)
- `_load_checkpoint(supabase, run_id, stage)` 로드 함수

### Task 3: pipeline.py 재실행 로직
- `generate_news_digest()`에 `from_stage` + `source_run_id` 파라미터 추가
- from_stage가 지정되면 이전 단계를 스킵하고 체크포인트에서 로드
- category 파라미터로 research/business 선택적 digest 생성

### Task 4: 백엔드 API 엔드포인트
- `POST /api/admin/pipeline/rerun` 추가
- admin 인증 필수
- BackgroundTasks로 비동기 실행

### Task 5: 어드민 UI
- pipeline-runs 상세 페이지에 "이 단계부터 재실행" 드롭다운/버튼
- category 선택 옵션 (write 단계 재실행 시)
- 재실행 후 새 run으로 리다이렉트

---

## 주의사항

### 직렬화/역직렬화
- ClassifiedGroup, ClassifiedCandidate 등 Pydantic 모델 → `.model_dump()` / `.model_validate()`
- raw_content는 문자열이라 JSON 직렬화 문제 없음
- community_map은 `dict[str, str]`이라 그대로 저장

### 체크포인트 정리
- 30일 이상 된 체크포인트 자동 삭제 (cron 또는 DB function)
- 또는 pipeline_runs CASCADE 삭제에 의존 (ON DELETE CASCADE 설정됨)

### 비용 영향
- 체크포인트 저장: INSERT/UPSERT 6회/run — DB 비용 무시 수준
- 재실행 시 LLM 비용: 재실행하는 단계부터만 발생
  - write부터: ~$0.22 (digest 비용만)
  - community부터: ~$0.23 (community 무료 + rank $0.001 + enrich 무료 + digest)
  - 전체: ~$0.45 (기존과 동일)
