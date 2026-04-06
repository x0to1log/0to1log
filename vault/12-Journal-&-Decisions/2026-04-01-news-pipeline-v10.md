# 결정: AI 뉴스 파이프라인 v10 — gpt-5 전환 + CP 재설계 + 품질 관리 체계

> 날짜: 2026-04-01
> 맥락: gpt-4.1 deprecation 대비 + CP 품질 불안정 근본 해결 + 코드 기반 품질 관리 도입
> 세션: 2026-03-31~04-01 작업

---

## 배경

v9에서 파이프라인 구조(다중 소스, 코드 citation, classify/merge 분리)는 안정됐지만, 세 가지 근본 과제가 남아있었다:

1. **gpt-4.1 deprecation 리스크** — OpenAI가 gpt-5 시리즈로 이동 중. 프로젝트 Allowed models에서 gpt-4.1이 제한될 가능성.
2. **CP(Community Pulse) 품질 불안정** — Writer가 raw comment를 직접 선별+요약+포맷하면서 저품질 인용, 섹션 누락, 포맷 불일치 반복.
3. **품질 관리의 한계** — LLM 채점만으로는 구조적 규칙 위반(CP 누락, 빈 섹션, 포맷 오류)을 잡지 못함.

---

## 결정 A: Community Pulse 파이프라인 재설계

### A1. Community Summarizer 단계 추가

community 수집과 Writer 사이에 `community_summarize` 단계를 추가하여 역할 분리.

```
Before: community → rank → enrich → write (Writer가 raw comment 선별+포맷)
After:  community → community_summarize → rank → enrich → write
                    gpt-5-mini 배치 1회, ~$0.001
```

- Summarizer: top 5 코멘트 → {sentiment, quotes(0-2), key_point} 추출
- source_label: 코드가 결정적으로 파싱 ("HN 342↑ · 89 comments")
- Writer: 정제된 데이터만 받아서 포맷+KO 번역. Rule 15 단순화.
- Summarizer에 원본 제목 전달 → 무관한 스레드 null 반환 (2중 방어)

### A2. Entity-First Search

기존 6개 키워드 검색이 HN Algolia에서 0 결과를 반환하는 문제 해결.

- 타이틀에서 고유명사/버전 패턴 추출 → 2-3 단어 짧은 쿼리
- 선택적 부스트: 버전 패턴(GPT-5.4) +40, 긴 고유명사(Atlassian) +20
- Foreign entity 패널티: 무관한 스레드 감점 (-8/entity, max -30)
- target_date 기준 7일 시간 필터

### A3. Brave Discussions 통합

Reddit 키워드 검색을 Brave Web Search의 discussions 기능으로 교체.

- Brave가 주제 기반으로 Reddit 스레드 발견 → permalink 추출 → Reddit API 1회로 코멘트 fetch
- ALLOWED_SUBREDDITS 확장 (ai_agents, aiwars, fintech, legaltech, europe)
- freshness=pw 시간 필터

### A4. CP 포맷 강제

- Writer Rule 15: "MUST be a single ## top-level section, NEVER ###/####"
- CHECKLIST #9: 레벨 + 위치 + 인용 3가지 검증
- `_strip_empty_sections()` 코드 후처리로 빈 섹션 제거

---

## 결정 B: gpt-5 모델 전환

### B1. 단계별 마이그레이션

한번에 전부 바꿔서 실패했던 이전 시도의 교훈을 반영, 단계별로 검증.

1. `build_completion_kwargs` — gpt-5 파라미터 호환 (max_completion_tokens, temperature 제거)
2. `compat_create_kwargs` — 직접 API 호출의 gpt-5 호환 래핑 (28곳)
3. merge 프롬프트 — system→user 데이터 분리 (gpt-5에서 빈 응답 방지)

### B2. reasoning_effort=low + 3x 토큰 헤드룸

gpt-5는 reasoning 모델이라 추론 토큰이 max_completion_tokens를 소진하면 빈 응답 반환 (openai-python #2546, 커뮤니티 보고).

- `reasoning_effort: "low"` 자동 추가 → 추론 토큰 절약
- `max_completion_tokens`를 원래 값의 3x → 추론+출력 합산에 여유
- `_apply_gpt5_compat()`로 두 함수(build + compat) 통일 처리

### B3. 4단계 모델 체계

```
openai_model_main      = gpt-5       # Writer digest, weekly
openai_model_light     = gpt-5-mini  # classify, merge, ranking, community_summarize
openai_model_nano      = gpt-5-nano  # 핸드북 advisor (경량 작업)
openai_model_reasoning = gpt-5-mini  # quality scoring, advisor 추론
```

`.env`에서 모델명만 바꾸면 코드 변경 없이 전환/롤백 가능.

---

## 결정 C: 코드 기반 품질 관리 체계

### C1. 구조 감점 시스템

LLM 채점(주관적 품질)에 코드 감점(구조적 규칙 위반)을 합산.

```
최종 점수 = LLM 점수(0-100) - 코드 감점(0-30)
```

| 체크 | 감점 | 방식 |
|---|---|---|
| CP 데이터 있는데 섹션 없음 | -15/locale | 코드 (community_summary_map vs 출력 비교) |
| CP가 ###/####로 존재 | -5/locale | 코드 (정규식) |
| EN/KO 섹션 수 불일치 ≥2 | -5 | 코드 (카운트) |
| 빈 인용 [](URL) | -5 | 코드 (정규식) |
| Supporting 3문단 미만 | -5/item (max -10) | 코드 (줄 수) |

### C2. Quality scoring 모델 안정화

- gpt-5-nano → 채점 불가 (0점 반환)
- gpt-5-mini → 극단적 감점 (36점, content[:12000] 잘림 + calibration 없음)
- 해결: content 16K + calibration 지시 + gpt-5-mini(reasoning) → 90점

### C3. 빈 섹션 + Bold 깨짐 코드 후처리

Writer 출력 후처리 체인:
1. `_strip_empty_sections()` — 헤더만 있고 내용 없는 `##` 섹션 제거 (Rule 11)
2. `_fix_bold_spacing()` — `**text **` → `**text**` (gpt-5가 닫는 `**` 앞에 공백 넣는 버그)

### C4. 중국어 소스 필터링

수집 단계에서 중국어 콘텐츠 2중 필터:
1. 도메인 리스트 — landiannews.com, 36kr.com 등 11개 주요 중국어 사이트
2. CJK 문자 감지 — title에 중국어 문자(U+4E00-U+9FFF)가 포함되면 자동 필터 (한국어 U+AC00-D7AF는 영향 없음)

### C5. KO 인용 번역 강화

gpt-5가 KO 콘텐츠에 영어 인용을 그대로 남기는 문제:
- Rule 15 (4): "NEVER leave English quotes in Korean content" 강화
- CHECKLIST #9 (d): "In ko, are ALL quotes in Korean?" 검증 추가

---

## 비용 영향

| 항목 | v9 (gpt-4.1) | v10 (gpt-5) |
|---|---|---|
| community_summarize | ~$0.001 | ~$0.001 (동일) |
| classify+merge+ranking | ~$0.015 | ~$0.020 (3x 헤드룸) |
| Writer digest | ~$0.28 | 측정 필요 (gpt-5) |
| Quality scoring | ~$0.002 | ~$0.003 (calibration 추가) |
| Brave API | $0 | $0 (무료 tier) |

---

## 교훈

### 14. gpt-5는 reasoning 모델이다 — 파라미터가 다르다

gpt-4.1에서 당연했던 `max_tokens`, `temperature`가 gpt-5에서는 작동하지 않는다. `max_completion_tokens`(추론+출력 합산), `reasoning_effort`, temperature 미지원 — 이 세 가지를 한 곳(`_apply_gpt5_compat`)에서 처리해야 코드 전체가 안전하다.

### 15. 빈 응답의 근본 원인: 추론이 토큰을 먹는다

gpt-5가 빈 응답을 반환하는 건 버그가 아니라 설계 — 추론 토큰이 max_completion_tokens를 소진하면 출력에 쓸 토큰이 없다. `reasoning_effort: "low"` + 3x 헤드룸이 해결책.

### 16. system에 데이터를 넣으면 gpt-5가 무시한다

gpt-4.1은 system prompt에 50개 후보 데이터를 넣어도 temperature=0.1로 결정적으로 처리했다. gpt-5는 temperature=1(고정)이라 system의 데이터를 "할 일이 없다"고 판단할 수 있다. system=규칙, user=데이터로 분리해야 안정적.

### 17. 품질 관리는 LLM만으로 부족하다

LLM은 "분석이 얕은가", "언어가 자연스러운가" 같은 주관적 판단에 강하지만, "CP 섹션이 있는가", "EN/KO 섹션 수가 같은가" 같은 결정적 규칙은 코드가 100% 정확하다. 둘을 합산하면 실질적 품질 관리가 된다.

### 18. 채점 모델이 바뀌면 트렌드가 깨진다

같은 콘텐츠를 gpt-4.1-mini(85점)와 gpt-5-mini(36점)가 전혀 다르게 채점한다. 채점 모델 변경 시 calibration 지시와 content 잘림 한도를 반드시 조정해야 한다.

### 19. LLM 출력은 코드로 후처리해야 안전하다

gpt-5가 생성하는 마크다운은 미묘한 결함이 있다 — `**text **` 공백, 빈 `##` 섹션, KO에 영어 인용 잔류. 프롬프트로 100% 방지는 불가능하므로 코드 후처리(_strip_empty_sections, _fix_bold_spacing)가 방어선 역할을 한다.

### 20. 수집 소스 언어 필터링은 도메인 리스트만으로 부족하다

Tavily/Exa가 영어 쿼리로 검색해도 중국어 사이트가 섞인다. 도메인 리스트는 새 사이트가 나오면 놓치므로, title의 CJK 문자 감지를 추가하면 언어와 무관하게 자동 필터링된다.

## 결정 D: v10 후속 개선 (2026-04-02~06)

### D1. CP 데이터 news item에서 분리

CP 데이터를 개별 뉴스 item 안에 섞어 넣으면 Writer가 본문에도 CP를 녹이고 별도 섹션에도 써야 해서 EN/KO quote가 혼합됨.

해결: 뉴스 items (CP 없음) + 마지막에 별도 CP 블록으로 전달. Writer가 `## Community Pulse` 섹션에서만 CP 사용.

### D2. Summarizer quotes_ko 직접 생성

Writer에 KO 번역을 맡기면 gpt-5가 영어 인용을 그대로 남기는 문제 반복.

해결: Summarizer가 `quotes` (EN 원문) + `quotes_ko` (한국어 번역)를 동시 생성. Writer에는 `Quote (EN)` / `Quote (KO)` 라벨로 전달하여 EN Writer는 EN 인용, KO Writer는 KO 인용만 사용.

### D3. [BODY] 마커로 소제목/본문 분리

gpt-5가 `###` 소제목 뒤에 줄바꿈 없이 본문을 이어쓰는 문제. 스켈레톤에 빈 줄을 넣어도 무시.

해결: 스켈레톤에 `[BODY]` 마커를 넣어 Writer가 반드시 사용하게 하고, `_clean_writer_output`에서 `[BODY]` → 줄바꿈으로 치환. `[LEAD]`/`[SUPPORTING]` 후처리와 동일한 패턴.

### D4. KO 스켈레톤 강화

KO 스켈레톤이 EN보다 `###` 예시가 부족해서 gpt-5가 KO 소제목을 영어로 쓰는 경향.

해결: Business KO에 Industry & Biz, New Tools `###` 예시 추가 (1→3개). Research KO `### WildWorld Dataset` → 한국어 제목화. KO CP 인용 예시 2개로 확장.

### D5. NQ-09 이벤트 중복 감점

같은 이벤트(e.g. Gemma 4 출시)가 매일 다른 URL로 수집되어 3일 연속 헤드라인 반복. URL 기반 중복 제거는 "같은 이벤트의 다른 기사"를 못 잡음.

해결: 최근 2일 published 제목을 classify 프롬프트에 전달. Rule 8: "같은 이벤트면 -30 score 감점. 새로운 관점/중대 업데이트만 허용."

### D6. 기타 안정화

- Writer 소스 입력 12K → 12K chars 상한 유지 (비용 35% 감소)
- Quality scoring content 잘림 16K → 20K (Research Expert 18K에서 Why It Matters 누락 방지)
- Digest retry 2→3회 (Expert 빈 응답 실패율 대응)
- Weekly pipeline: `summary` → `last_error` (컬럼 불일치), `korean_term` → `korean_name`, `upsert` → `select+update/insert`, stage별 로깅
- 중국어 소스: 도메인 리스트 + CJK 문자 감지 2중 필터
- GitHub 프로필 URL community 검색 스킵
- `maybeSingle()` → `limit(1)` (Python Supabase SDK 호환)

---

## 교훈 (추가)

### 21. CP 데이터는 뉴스 본문과 분리해서 전달해야 한다

Writer가 본문에도 CP를 녹이고 별도 섹션에도 쓰려면 역할이 모호해지고 EN/KO quote가 섞인다. "뉴스 = 사실, CP = 반응, 인사이트 = 해석"으로 역할을 분리하면 안정적.

### 22. 번역은 번역 담당이 해야 한다

Writer에게 "KO에서 영어 인용을 번역해라"고 시키면 gpt-5가 일관되게 안 따른다. Summarizer가 EN/KO를 동시에 생성하면 Writer는 가져다 쓰기만 하면 돼.

### 23. 스켈레톤에 마커를 넣으면 LLM이 따라한다

`[BODY]`, `[LEAD]` 같은 마커를 스켈레톤에서 보여주면 gpt-5가 높은 확률로 따라 쓴다. 코드 후처리에서 제거/치환하면 최종 출력은 깨끗. 프롬프트 규칙보다 효과적.

### 24. URL 기반 중복 제거로는 같은 이벤트의 다른 기사를 못 잡는다

Gemma 4가 3일 연속 헤드라인에 등장한 건 매일 다른 사이트가 같은 소식을 재보도하기 때문. 최근 발행 제목을 classify에 전달하는 "이벤트 단위 중복 감점"이 필요.

---

## 품질 추이

| 날짜 | Research | Business | CP | 비고 |
|------|----------|----------|-----|------|
| 3/27 (v9, gpt-4.1) | 95 | 95 | B 1/4, R 0/4 | baseline |
| 4/1 (v10 초기, gpt-5) | 61 | 59 | B 4/4, R 0/4 | 채점 모델 문제 |
| 4/1 (v10 안정화) | 89 | 87 | B 4/4, R 4/4 | calibration + 구조 감점 0 |
| 4/2 (v10.1) | 89 | 90 | B 4/4, R 4/4 | quotes_ko + CP 분리 적용 |
| **4/6 (v10.2)** | **96** | **91** | 0/8 (토론 없음) | [BODY] 마커 + NQ-09 이벤트 중복 감점 |

---

## 남은 과제

- **NQ-15**: Learner 콘텐츠 재설계 — "Expert의 쉬운 버전"이 아닌 학습자 관점 재구성
- **핸드북 nano 연결**: advisor에서 `openai_model_light` → `openai_model_nano` 전환
- **NQ-23**: semaphore 동시성 제어 + URL canonicalization
- **NQ-24**: 테스트 전면 재작성

## Related

- [[2026-03-30-news-pipeline-v9]] — v9 journal (다중 소스 + 코드 citation)
- [[ACTIVE_SPRINT]] — GPT5-01~05, NQ-09 태스크
