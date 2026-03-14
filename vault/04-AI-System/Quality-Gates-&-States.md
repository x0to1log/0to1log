---
title: Quality Gates & States
tags:
  - ai-system
  - quality
  - validation
source:
  - docs/03_Backend_AI_Spec.md
  - docs/07_Global_Local_Intelligence.md
---

# Quality Gates & States

PydanticAI 스키마 검증 + 에러 핸들링 + 재시도 정책.

## PydanticAI 검증 스키마

모든 OpenAI API 출력은 Supabase 저장 전 PydanticAI로 검증. 스키마 위치: `backend/models/`

### 보조 스키마

| 모델 | 역할 |
|---|---|
| **QuizPoll** | 퀴즈 question/options/answer/explanation |
| **PromptGuideItems** | 5블록: one_liner, action_item, critical_gotcha, rotating_item, quiz_poll |
| **RelatedNews** | big_tech / industry_biz / new_tools (각 Optional) |
| **NewsRankingResult** | research_pick + business_main_pick + related_picks |

### 메인 출력 스키마

| 스키마 | 에이전트 | 핵심 필드 |
|---|---|---|
| **ResearchPost** | Research Engineer | `has_news`, `content_original`, `no_news_notice`, `guide_items` |
| **BusinessPost** | Business Analyst | `fact_pack`, `source_cards`, `content_analysis`, `content_beginner/learner/expert` (각 min 5,000자), `guide_items`, `related_news` |
| **EditorialFeedback** | Editorial | accuracy/readability/seo/tone (1~10), `overall_verdict` |

### 교차 검증 규칙

- `ResearchPost`: `has_news=True` → `content_original` 필수
- `ResearchPost`: `has_news=False` → `no_news_notice` 필수
- `news_temperature`: 1~5 범위

### Editorial 판정 기준

| 조건 | 판정 |
|---|---|
| 모든 항목 7점+ & critical_issues 없음 | `publish_ready` |
| 어느 항목 5점 미만 OR critical_issues 1개+ | `needs_revision` |
| 어느 항목 3점 미만 | `major_rewrite` |

## 에러 핸들링 & 재시도

### 파이프라인 체인별 정책

| 단계 | 실패 원인 | 재시도 | 실패 시 동작 |
|---|---|---|---|
| **Tavily 수집** | API 타임아웃, 429 | 30초 후 1회 | 해당 쿼리 스킵 |
| **Ranking (4o-mini)** | 타임아웃, 잘못된 JSON | 60초 후 1회 | 랭킹 없이 Admin 전달 |
| **Research EN (4o)** | 타임아웃, JSON 오류 | 60초 후 2회 | "뉴스 없음" 대체 발행 |
| **Business Expert (4o)** | 타임아웃, JSON 오류 | 60초 후 2회 | 스킵, 로그 기록 |
| **Business Derive (4o)** | 타임아웃, JSON 오류 | 60초 후 2회 | 스킵, 로그 기록 |
| **번역 (4o)** | 타임아웃, JSON 오류 | 60초 후 2회 | EN만 저장, KO 누락 로그 |
| **Editorial (4o)** | 타임아웃, JSON 오류 | 60초 후 1회 | 검수 없이 draft, "수동 검수 필요" 태그 |
| **PydanticAI 검증** | 스키마 불일치 | 없음 | 에러 포함 재생성 1회 |
| **Supabase 저장** | 연결 실패, 중복 slug | 10초 후 2회 | 실패 로그 + Admin 알림 |

> [!note] v4 변경
> Business를 Expert/Derive 2행으로 분리, 번역 행 추가. 섹션별 재시도·recovery pass·partial artifact 제거 — 포스트 전체 단위 재시도로 단순화.

### 재시도 유틸리티

`with_retry(max_retries, delay_seconds, backoff)` 데코레이터 — ==지수 백오프== 패턴.

### PydanticAI 검증 실패 자동 재생성

`generate_with_validation_retry()`:
1. 1차 생성 → PydanticAI 검증
2. 실패 시 에러 내용을 assistant 메시지에 포함하여 ==재생성 1회==
3. 2차도 실패 시 예외 raise

### Admin 알림

`notify_admin_on_failure()`: 파이프라인 실패 시 `admin_notifications` 테이블에 저장. Phase 3에서 이메일 알림 업그레이드 가능.

## 발행 품질 게이트 (Content Quality Gate)

EN-KO 이중 언어 발행 시 콘텐츠 품질/동기화를 제어하는 게이트. PydanticAI 스키마 검증과는 별도로, 사실성·출처·언어 정합성을 판단한다.

### 발행 전 필수 조건

| 항목 | 최소 기준 | 미달 시 |
|---|---|---|
| 출처 수 | 핵심 주장 최소 2개 출처 또는 1개 1차 출처(공식) | `hold` |
| 근거 링크 | 핵심 주장/수치에 근거 링크 필수 | `needs_review` |
| 사실성 | 사실성 점수 기준 이상 | `hold` |
| 맥락성 | "왜 중요한가"와 "한계/리스크" 포함 | `needs_review` |
| 실행가능성 | 독자 행동으로 연결되는 인사이트 포함 | `needs_review` |
| 언어 동기화 | KO는 EN 기준 `source_post_version` 참조 필수 | `needs_review` |

### 게이트 상태값

| 상태 | 의미 | 후속 동작 |
|---|---|---|
| `pass` | 발행/후속 로컬라이즈 가능 | publish 또는 KO draft 트리거 |
| `hold` | 근거/품질 부족 | 자동 발행 금지, 재수집/재분석 |
| `needs_review` | 고위험/애매 항목 | 사람 검수 후 결정 |
| `stale` | EN 원본 수정으로 KO 버전 불일치 | KO 재생성 큐 + 재검수 |

> [!note] `stale` 정의
> `stale`는 발행 품질이 아닌 ==EN-KO 동기화 불일치 상태==. `stale` KO는 publish 금지, 재생성/재검수 완료 전까지 `in_sync` 복귀 불가.

### EN-KO Version Lock 규칙

- KO 생성 시작 시 `source_post_id`의 `en_revision_id`를 잠금(`FOR UPDATE`)
- KO 생성 완료 직전 EN revision 재검증 실패 시 → KO 폐기, 재생성 큐 이동
- KO publish는 `source_post_version == EN current version`일 때만 허용

### EN 선행 생성 & 참조 전제

- EN row 생성 완료 후에만 KO 파생 생성 시작
- KO의 `source_post_id`는 반드시 EN row 참조 (미참조 저장 금지)
- `translation_group_id`는 EN row에서 발급 → KO row 전파
- EN 참조 누락/불일치 감지 시 KO 생성은 `hold` 전환 + 재시도 큐

### EN 상태별 KO 처리 매트릭스

| EN 상태 | KO draft 생성 | KO publish | Trigger Mode | Wait Window | Re-sync | 후속 동작 |
|---|---|---|---|---|---|---|
| `pass` | 허용 | 수동/티어 규칙 | `instant`/`debounced` | instant=0초·debounced=600초 | 아니오 | `source_post_version` 연결 |
| `needs_review` | 금지 | 금지 | n/a | n/a | 아니오 | EN 검수 완료 후 재판정 |
| `hold` | 금지 | 금지 | n/a | n/a | 아니오 | 재수집/재분석 |
| `stale` | 재생성 큐 이동 | 금지 | 기존 모드 유지 | 기존값/운영 재설정 | 예 | KO 재검수 후 재발행 |

### 운영 옵션

**`confirm_to_localize`** (기본: OFF)
- EN `pass` 직후 자동 KO 생성 대신 관리자 최종확정 시 트리거
- 권장: 고파급 이슈(Tier A), EN 미세 수정 빈도 높은 기간, 비용 절감 운영

**`is_major_update`** (기본: false)
- `true`: KO → `stale` 전환 + 재생성 큐
- `false`: KO `in_sync` 유지, 재생성 미발생
- 권장: 수정 시 `major_update_note` 사유 텍스트 함께 기록

### Human-in-the-loop 지점

- 법적/정책 리스크 인용
- 상충 출처로 결론 갈리는 이슈
- 높은 파급력(시장/보안/규제) 주제

## Handbook AI 검증

### Generate 검증 게이트

`GenerateTermResult`에 `Field(min_length=...)` 적용:

| 필드 | 최소 길이 |
|---|---|
| `definition_ko/en` | 80자 |
| `body_basic_ko/en` | 2,000자 |
| `body_advanced_ko/en` | 3,000자 |

- 검증 실패 시 `success: false` + `validation_warnings: list[str]` 반환 (결과 데이터는 그대로 포함)
- Frontend에서 warning 토스트 표시

### Pipeline 용어 배치 중복 체크

`_extract_and_create_terms()`에서 추출된 용어를 `in_()` 배치 쿼리로 한 번에 DB 존재 확인 → 이미 있는 용어는 스킵.

## Related

- [[AI-News-Pipeline-Overview]] — 검증이 적용되는 파이프라인
- [[Prompt-Guides]] — 검증 대상 프롬프트 출력
- [[Database-Schema-Overview]] — 검증 후 저장되는 스키마
- [[Backend-Stack]] — 에러 핸들링이 동작하는 백엔드
- [[Global-Local-Intelligence]] — 발행 품질 게이트의 전략 문서
