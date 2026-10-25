# Claude API Migration — 교체 가능한 LLM 역할을 Claude로

> 상위: [[2026-10-23-handbook-seed-claude]] (시범 결과 → Amy 결정 2026-10-26)
> 상태: **Phase A 완료 (2026-10-26)** — 운영 동작 변화 없음 (`model_overrides` 빈 dict). Phase B는 GPT-6 관찰 종료(10-27) 후

## Phase A 결과 (2026-10-26)

- `get_openai_client()` → `ClaudeRoutingClient(AsyncOpenAI)`. `anthropic` import는 Claude 호출 시점으로 지연 → 패키지가 없어도 OpenAI 경로 정상 (테스트로 확인).
- `core.config.model_for(feature, role)` + `model_overrides` — 호출부 47곳 + 퀴즈 모델 선택부를 기능 키로 교체. 모듈 `settings`를 패치해 모델명만 넣던 테스트 패치 정리.
- strict `json_schema` → `output_config.format` (`claude_json_schema`가 거부 키워드 제거).
- Haiku 5.5 가격 추가 (≤100K, cache read 10% 가정).
- 실호출: Haiku 5.5 + 실제 퀴즈 스키마 구조화 출력 성공 (3 페르소나, 선택지 4개, $0.00035). 같은 클라이언트로 luna 정상.
- 테스트 997 통과.
- 교훈: Python `write_text`가 Windows에서 LF 파일을 CRLF로 바꿈 (이 저장소는 파일별 줄바꿈이 섞여 있음) → 일괄 수정 스크립트는 바이트 단위로 원래 줄바꿈 유지.

**Goal:** 백엔드의 OpenAI 호출 중 교체 가능한 것을 **기능 단위로, 설정 한 줄로** Claude로 옮길 수 있게 하고, 기능마다 A/B를 거쳐 전환한다.

## 배경

- Claude Startups 크레딧 $1,500 (Team $500 11/13 만료, 프로그램 $1,000 4/8 만료) — [[project-claude-credits]].
- 핸드북 시범: 같은 프롬프트로 모델만 바꾸면 sol 판정 점수 하락 + 비용 3.5~6배. 직접 읽어 보면 Claude(Opus)가 내용은 더 깊고, 감점 사유는 프롬프트로 고칠 수 있는 결함 (수준 이탈, 단정, 코드 길이). → **교체 = 모델 + 그 모델용 프롬프트 + A/B 세트.**

## 현재 구조 (2026-10-26 조사)

- OpenAI 호출 ~58곳, 12개 모듈, 전부 `client.get_openai_client()` 경유. `chat.completions.create`만 사용 (+ `embedding.py`의 `embeddings.create`).
- 모델은 역할 4개 (`openai_model_main/light/nano/reasoning`)를 여러 기능이 공유 → 역할 하나를 바꾸면 여러 기능이 한꺼번에 바뀜 (예: `main` = 뉴스 작성 + 핸드북 작성 + 블로그·제품 어드바이저 + weekly).
- strict `json_schema` 사용처: 뉴스 작성 (`schemas/news_writer.py`), 퀴즈 생성 (`schemas/news_quiz.py`), 퀴즈 검증 (`quiz_verifier.py`).
- 샘플링 인자(temperature 등) 사용 없음 (Haiku 5.5가 400으로 거부하는 항목).

## 설계

### Phase A — 기반 (운영 동작 변화 없음)

1. **전역 라우팅:** `get_openai_client()`가 `ClaudeRoutingClient`로 감싼 클라이언트를 반환. `claude-*` 모델만 Anthropic으로, 나머지는 OpenAI 그대로. `embeddings` 등 그 밖의 속성은 OpenAI 클라이언트로 통과.
2. **구조화 출력 변환:** `response_format={"type": "json_schema", ...}` → `output_config.format = {"type": "json_schema", "schema": ...}`. Claude가 거부하는 키워드는 제거 — `minimum`/`maximum`/`multipleOf`, `minLength`/`maxLength`, `maxItems`, `minItems` > 1 (같은 제약은 코드가 이미 다시 검증: 퀴즈 검증·셔플, 인용 치환). 객체의 `additionalProperties: false`는 이미 있음.
3. **기능 단위 모델 설정:** `config.py`에 `model_overrides: dict[str, str]` (기본 빈 dict) + `model_for(feature, role)` — 기능 키가 없으면 지금 역할 기본값. 호출부의 `settings.openai_model_*`를 `model_for("<feature>", "<role>")`로 교체.
4. **가격표:** Haiku 5.5 추가 ($0.10/$0.50, 프롬프트 ≤100K 기준. >100K는 $0.50/$2.50 — 해당 호출 없음, 주석으로 명시).

### 기능 키

| 기능 키 | 기본 역할 | 위치 |
|---|---|---|
| `news.classify` / `news.merge` / `news.rank` | light | `ranking.py` |
| `news.community` | light / nano | `ranking.summarize_community`, `_retranslate_quotes_ko_async`, `comment_relevance` |
| `news.writer` | main | `pipeline_digest._generate_digest` |
| `news.quiz` | light (검증 reasoning) | `pipeline_digest._generate_digest_quizzes`, `quiz_verifier` |
| `news.translate` | light | `pipeline_digest._translate_focus_items_ko` |
| `news.qc` | reasoning | `pipeline_quality._check_digest_quality` |
| `weekly.writer` / `weekly.qc` | main / reasoning | `pipeline.run_weekly_pipeline`, `regenerate_weekly_persona`, `_check_weekly_quality` |
| `handbook.writer` | main | `advisor.generate_term_content`, `run_handbook_advise`, `remediate_handbook_draft_content` |
| `handbook.judge` | reasoning | 비평·품질 판정·deep verify |
| `handbook.light` | nano | 용어 추출·게이트·분류·엔티티 |
| `advisor.handbook` / `advisor.blog` / `advisor.product` | 액션별 | 어드민 AI 어드바이저 |
| `legacy.fact_extractor` / `legacy.persona_writer` | main | 사용처 확인 후 정리 |

### Phase B — 가벼운 역할 → Haiku 5.5 (10/27 이후)

- `news.classify` → `news.merge` → `news.rank` → `news.community` → `news.translate` 순으로 하나씩. 각각 체크포인트 재생 A/B (`ab_daily_models.py` 확장) → 운영 전환 → 2~3일 관찰.
- Haiku 5.5 토크나이저는 같은 글을 ~30% 더 많은 토큰으로 셈 → 비용 비교는 실측으로.

### Phase C — 작성·판정 (B 다음)

- 핸드북 작성 먼저 (운영 영향 없음): Claude용 프롬프트 조정 (Basic 수준 제한, 코드 캡슐 길이, 단정 금지, 캐시 구조: 공통 프롬프트와 용어별 가이드를 별도 블록으로) → 3용어 재시범.
- 뉴스 작성·QC·퀴즈: 기능마다 A/B. 판정 모델을 바꾸면 threshold 70 재보정.

### 범위 밖

- **임베딩** (`embedding.py`): Claude에 임베딩 API 없음 → OpenAI 유지.

## 리스크

| 리스크 | 완화 |
|---|---|
| 크레딧 종료 후 비용 증가 (Claude는 같은 일에 더 길게 씀; 뉴스 월 ~$25 → ~$50~80 추정) | 기능 단위 설정이라 되돌리기 = 설정 한 줄. 4월 전에 비용 재검토 |
| OpenAI flex 50% 할인 없음 (Batch API는 비동기라 아침 실행에 부적합) | 비용 비교에 반영 |
| 구조화 출력의 enum 대소문자 보장 안 됨 (문서 명시) → 뉴스 작성의 인용 URL enum | Phase C에서 URL 대소문자 무시 매칭 확인 후 전환 |
| Claude 거절 (`refusal`, 예: 보안 용어 cyber) | 핸드북은 용어 단위 OpenAI 대체 (구현됨). 뉴스는 Phase C에서 대체 경로 설계 |
| `with_flex_retry`는 OpenAI 예외만 재시도 | Anthropic SDK 자체 재시도 (`max_retries=4`) |
| 한 번에 여러 기능 전환 시 원인 추적 불가 | 기능 하나씩, 전환마다 관찰 |

## 완료 기준

- Phase A: 모든 기존 테스트 통과 (기본값에서 동작 동일) + 라우팅·스키마 변환·`model_for` 테스트 + 실제 Claude 구조화 출력 호출 1회 성공.
- Phase B/C: 기능별 A/B 결과표 + 전환 커밋 + 관찰 기록.
