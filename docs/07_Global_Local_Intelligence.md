# 🌍 0to1log — Global-Local Intelligence Strategy

> **문서 버전:** v1.6  
> **최종 수정:** 2026-03-05  
> **작성자:** Amy (Solo)  
> **상태:** Planning  
> **상위 문서:** `01_Project_Overview.md`  
> **문서 역할:** 구현 코드 명세가 아닌 전략 계약서 (상위 방향/운영 원칙/품질 기준 정의)

---

### v1.6 변경 이력

| 항목 | v1.5 | v1.6 | 이유 |
|---|---|---|---|
| 생성 순서 전제 | EN-KO 락/검증 중심 | EN 선행 생성 + `translation_group_id` 전파 + 참조 누락 시 `hold` 규칙 명문화 | 참조 누락/FK 오류 예방 |

### v1.5 변경 이력

| 항목 | v1.4 | v1.5 | 이유 |
|---|---|---|---|
| EN-KO 정합성 | `is_major_update` 기반 stale 제어 중심 | KO 생성 시 EN revision lock + 재검증 규칙 추가 | 비동기 Race Condition 방지 |
| 인터페이스 보강 | source/version/sync 필드 중심 | `locked_en_revision_id`, `localization_job_id` 후보 추가 | 동기화 추적/복구 용이성 강화 |

---

## 1. 비전 & 포지셔닝

### 슬로건
**Global-to-Local Insight Bridge**

### 핵심 포지셔닝

| 대상 | 제공 가치 | 문제 해결 |
|---|---|---|
| **한국 사용자** | 영문 원천 뉴스 + 커뮤니티 반응을 한국어로 해석한 인사이트 | 영어 접근 장벽으로 인한 정보 비대칭 해소 |
| **글로벌 사용자** | 빠르게 핵심만 파악할 수 있는 고밀도 큐레이션 | 정보 과잉 속에서 중요한 신호 선별 |

### 단순 번역 모델과의 차별점 (ADR)

> **결정:** 0to1log는 "번역 블로그"가 아니라 "해석+판단 기반 인텔리전스 미디어"로 운영한다.
>
> **차별점:**
> - 원문 요약만 제공하지 않고, 왜 중요한지(Why it matters)와 실무 적용 포인트(Actionable takeaways)를 함께 제공
> - 커뮤니티 반응(HN/Reddit)까지 반영해 뉴스의 실제 온도(체감도)를 함께 전달
> - 한국 시장 맥락과 글로벌 관점을 분리 운영하여 독자별 읽기 가치를 최적화

---

## 2. 콘텐츠 가치 구조 (3-Layer)

| Layer | 정의 | 필수 산출물 |
|---|---|---|
| **Layer 1: 사실 요약** | 출처 기반 핵심 사실 정리 | 핵심 주장, 근거 링크, 발표 주체 |
| **Layer 2: 해석/의미** | 기술/시장 맥락에서 의미 해석 | Why it matters, 제한점/리스크 |
| **Layer 3: 실행 인사이트** | 독자가 바로 적용 가능한 판단/행동 제시 | Action items, 의사결정 체크포인트 |

> **운영 원칙:** 번역 자체는 가치의 시작점일 뿐이며, 최종 가치는 해석과 판단에서 발생한다.

---

## 3. 소싱 전략 — The Pulse of AI

### Multi-Source Retrieval

| 소스 | 역할 | 기대 신호 |
|---|---|---|
| **Tavily** | 공식 발표, 기술 블로그, 뉴스 수집 | 발표 사실/사양/출처 링크 |
| **Hacker News** | 엔지니어 커뮤니티 반응 수집 | 기술적 반론, 운영 관점, 업보트 기반 관심도 |
| **Reddit** | 실무 체감/트러블슈팅 수집 | 현업 이슈, 사용성 피드백, 한계 사례 |

### 커뮤니티 정량 신호 계약

| 신호 | 정의 | 소스 |
|---|---|---|
| `score` | 게시물 추천/업보트 절대값 | HN, Reddit |
| `comments` | 댓글 수 | HN, Reddit |
| `age_normalized_velocity` | 시간 경과 대비 반응 증가 속도 | HN 중심 |
| `upvote_ratio` | 업보트 비율 | Reddit |
| `subreddit_weight` | 서브레딧 신뢰/전문성 가중치 | Reddit |
| `sentiment_polarity` | 반응 감성 극성(-1.0 ~ 1.0) | 공통 |
| `controversy_index` | 찬반 분산/논쟁도 | 공통 |

### 주제 선정 원칙

- 단순 최신순이 아닌 **최신성 + 커뮤니티 반응 + 신뢰도 가중치** 기반으로 우선순위를 정한다.
- 동일 이슈는 소스 간 중복 클러스터링으로 묶고, 대표 이슈 단위로 발행 후보를 만든다.
- 커뮤니티 반응은 정성 텍스트만 사용하지 않고 `community_signals` 기반 정량 점수를 함께 반영한다.
- 저신뢰/낮은 근거 이슈는 후보에서 제외하거나 `hold` 상태로 보류한다.

---

## 4. Dual-Path Intelligence 운영 모델

### 개념 흐름

```text
영문 원천 수집
  → Core Analysis (영문 기준 구조화 분석)
  → EN Draft 생성
  → EN 품질 게이트(자동)
       ├─ pass + Trigger Mode=instant (Tier B 기본): KO Localization Draft 즉시 생성
       ├─ pass + Trigger Mode=debounced (Tier A 기본): 10분 Wait Window 후 KO Draft 생성
       └─ hold/needs_review: KO 생성 금지 → EN 수동 검수 후 재판정
  → (선택) Trigger Mode=manual_confirm (confirm_to_localize ON): 관리자 최종확정 후 KO 생성
  → EN 수정 이벤트 발생 시 `is_major_update=true`이면 KO = stale 전환
  → EN 수정 이벤트 발생 시 `is_major_update=false`이면 stale 미전환(기존 KO 유지)
  → KO 재생성 큐 처리 후 재검수
```

### 채널별 최종화 원칙

| 채널 | 목표 독자 | 강조 포인트 | 톤 | 기준 원본 여부 |
|---|---|---|---|---|
| **EN** | 바쁜 글로벌 개발자/빌더 | 핵심 신호 압축, 맥락 연결, 빠른 판단 지원 | 간결하고 밀도 높은 요약 중심 | **Canonical** |
| **KO** | 영어 뉴스 접근이 부담되는 한국 사용자 | 한국 시장/제품/비용 체감 맥락 | 명료하고 친절한 설명 중심 | **Localized Derivative** |

> **핵심:** KO/EN은 동일 원문을 쓰더라도 "같은 문장 번역"이 아니라 "같은 사실의 다른 독자 최적화"를 지향한다.

> **EN-Canonical 운영 ADR:**
> - EN is the canonical source language.
> - KO is a localized derivative anchored to EN versioning.
> - Trigger mode is tier-dependent (`A=debounced`, `B=instant`).
> - EN `hold`/`needs_review` 상태에서는 KO 생성을 금지한다.
> - EN 수정 시 KO stale 전환은 `is_major_update=true`인 경우에만 수행한다.

---

## 5. 품질 게이트 (Quality Gate)

### 발행 전 필수 조건

| 항목 | 최소 기준 | 미달 시 |
|---|---|---|
| 출처 수 | 핵심 주장에 대해 최소 2개 출처 또는 1개 1차 출처(공식) | `hold` |
| 근거 링크 | 핵심 주장/수치에 근거 링크 필수 | `needs_review` |
| 사실성 | 사실성 점수 기준 이상 | `hold` |
| 맥락성 | "왜 중요한가"와 "한계/리스크" 포함 | `needs_review` |
| 실행가능성 | 독자 행동으로 연결되는 인사이트 포함 | `needs_review` |
| 언어 동기화 일관성 | KO는 EN 기준 포스트 버전(`source_post_version`) 참조 필수 | `needs_review` |

### 품질 게이트 상태값

| 상태 | 의미 | 후속 동작 |
|---|---|---|
| `pass` | 발행/후속 로컬라이즈 가능 | publish 또는 KO draft 생성 트리거 |
| `hold` | 근거/품질 부족 | 자동 발행 금지, 재수집/재분석 |
| `needs_review` | 고위험/애매 항목 존재 | 사람 검수 후 발행 결정 |
| `stale` | EN 원본 수정으로 KO와 버전 불일치 발생 | KO 재생성 큐 이동 + 재검수 후 재발행 |

> `stale`는 발행 품질의 문제라기보다 EN-KO 간 **동기화 불일치 상태**를 나타내는 운영 상태다.
> `stale` 상태의 KO는 publish 금지이며, 재생성/재검수 완료 전까지 `in_sync`로 복귀할 수 없다.

### EN-KO 버전 락 (Version Lock) 규칙

- KO 생성 시작 시 `source_post_id`의 `en_revision_id`를 읽고 잠금(`FOR UPDATE`)한다.
- KO 생성 완료 직전 EN revision 재검증이 실패하면 KO 결과를 폐기하고 재생성 큐로 이동한다.
- KO publish는 `source_post_version == EN current version`일 때만 허용한다.

### EN 선행 생성 & 참조 전제

- EN 원본 row 생성이 완료된 뒤에만 KO 파생 생성을 시작한다.
- KO 생성 시 `source_post_id`는 EN row를 참조해야 하며, 미참조 상태 저장은 허용하지 않는다.
- `translation_group_id`는 EN row에서 발급하고 KO row는 해당 값을 전파받아 사용한다.
- EN 참조 누락/불일치가 감지되면 KO 생성은 `hold`로 전환하고 재시도 큐로 보낸다.

### Human-in-the-loop 지점

- 법적/정책 리스크가 있는 인용
- 상충되는 출처로 결론이 갈리는 이슈
- 높은 파급력(시장/보안/규제) 주제

### EN 상태별 KO 처리 규칙 (확장 매트릭스)

| EN 상태 | KO draft 생성 | KO publish | Trigger Mode | Wait Window | Re-sync Required | 후속 동작 |
|---|---|---|---|---|---|---|
| `pass` | 허용 | 수동/티어 규칙 | `instant` 또는 `debounced` | `instant=0초`, `debounced=600초(기본)` | 아니오 | `source_post_version` 연결 |
| `needs_review` | 금지 | 금지 | n/a | n/a | 아니오 | EN 검수 완료 후 재판정 |
| `hold` | 금지 | 금지 | n/a | n/a | 아니오 | 재수집/재분석 |
| `stale` (EN major 수정 발생) | 재생성 큐로 이동 | 금지 | 기존 모드 유지(재평가 가능) | 기존값 또는 운영 재설정 | 예 | KO 재검수 후 재발행 |

### 운영 옵션: `confirm_to_localize`

- 기본값: `OFF`
- 의미: EN `pass` 직후 자동 KO 생성을 하지 않고, 관리자 최종확정 시점에 KO 생성 트리거
- 사용 권장: 고파급 이슈(Tier A), EN 미세 수정 빈도가 높은 기간, 비용 절감 집중 운영 시

### 운영 옵션: EN 수정 분류 (`is_major_update`)

- 기본값: `false`
- 의미: EN 수정 시 KO stale 전환/재생성 큐 투입 여부를 제어하는 단순 플래그
- 규칙:
  - `is_major_update=true`: KO를 `stale`로 전환하고 재생성 큐에 넣는다.
  - `is_major_update=false`: KO는 `in_sync`를 유지하고 재생성하지 않는다.
- 권장 운영: 수정 시 `major_update_note`(짧은 사유 텍스트) 함께 기록

---

## 6. 콘텐츠 티어링 전략 (효율 + 품질)

| 티어 | 범위 | 품질 수준 | 언어 운영 | 기본 Trigger Mode |
|---|---|---|---|---|
| **Tier A (핵심 이슈)** | 고파급 뉴스/분석 | 고품질 심층 분석 + 검수 강화 | EN/KO 모두 publish 전 수동 검수 필수 | `debounced` (10분 Wait Window) |
| **Tier B (다이제스트)** | 일일 요약/보조 이슈 | 압축 요약 + 실무 포인트 | EN 우선 운영, KO는 draft 자동 생성까지만 자동화 + publish 전 수동/경량 검수 | `instant` |

> **리소스 원칙:** 모든 글을 동일한 고비용 파이프라인으로 처리하지 않는다. 핵심 이슈에 품질 자원을 집중한다.

---

## 7. SEO/i18n 전략 원칙

- 기본 언어는 **영어(EN)**로 운영한다.
- URL은 언어별로 명확히 분리한다: `/en/log/[slug]`, `/ko/log/[slug]`
- `x-default`는 `/en/`을 가리킨다.
- `hreflang` (`ko`, `en`, `x-default`)과 canonical을 일관되게 설정한다.
- EN/KO는 상호 `hreflang` 페어링을 유지한다.
- 각 언어 페이지는 자기 canonical을 유지한다.
- locale sitemap을 운영하여 검색엔진이 언어별 페이지를 명확히 인식하도록 한다.
- 자동 강제 번역/자동 리다이렉트 남용을 지양하고, 언어 스위처 중심 UX를 기본으로 한다.

---

## 8. 거버넌스 & 리스크 관리

### 저작권/인용 정책

- 원문 기사 본문 전재는 지양한다.
- 요약/해석 중심으로 작성하고, 출처 링크를 명시한다.
- 커뮤니티 반응은 최소 인용 원칙을 적용한다.

### 환각/오인 리스크 대응

- 출처 없는 단정 문장은 발행 금지
- 수치/비용/성능 주장에는 근거 링크 필수
- 불확실한 정보는 "가정" 또는 "관측"으로 명시

### Prompt Cultural Tuning

| 채널 | 작성 가이드 |
|---|---|
| **EN** | 증거 우선, 과장 금지, 리스크/한계 명시, 짧고 밀도 높은 서술 |
| **KO** | 번역투 금지, 자연스러운 한국어 문장, 국내 맥락(시장/비용/도입 현실) 연결 |

공통 가드레일:
- 근거 없는 단정 금지
- 수치/비용 주장은 출처 링크 필수
- 의견과 사실을 문장에서 분리 표기

### 댓글 언어 정책

- 기본: 댓글은 locale 분리 노출(`ko`, `en`)
- 확장: "글로벌 베스트 반응 요약 카드"는 선택 기능(수동/주간 큐레이션)으로 운영
- 리스크: 민감/저품질 코멘트 자동 확대 노출 금지, 커뮤니티 인용 최소화 유지

---

## 9. KPI 프레임워크

### KO 채널 KPI

- 접근성: 한국어 콘텐츠 소비 시작률
- 체류: 평균 읽기 시간, 완독률
- 재방문: 주간 재방문율
- 공유: 공유 이벤트율

### EN 채널 KPI

- 큐레이션 소비율: 요약 카드 클릭률/완독률
- 재방문율: 7일/28일 재방문
- 탐색 효율: 검색/내부 이동 비율

### Cross-lingual 검색 KPI (신규)

- `Cross-lingual Recall@K`: 한국어/영어 쿼리 상호 검색 시 관련 문서 회수율
- `Locale-aware nDCG@K`: 현재 locale 우선순위를 반영한 검색 정렬 품질
- `Language-mismatch bounce rate`: 언어 불일치 결과 클릭 후 이탈률

### 공통 운영 KPI

- 품질 게이트 통과율 (`pass` 비율)
- 발행 후 수정률 (정정/수정 비중)
- 소스 다양성 지표 (단일 소스 편중 방지)
- KO draft 생성 지연 p95 (`localization_latency_sec`)
- KO `stale` 전환율 및 stale 해소 SLA(재동기화 완료 시간)

> KPI 목표값은 초기 운영 단계에서 "초기 타겟"으로 설정하고, 2~4주 단위로 재조정한다.

---

## 10. 로드맵 (전략 단계)

| 단계 | 운영 방식 | 목표 |
|---|---|---|
| **Stage 0** | EN canonical 정착 + KO 로컬라이즈 실험 | 트리거/동기화/품질 게이트 검증 |
| **Stage 1** | EN-first 티어 기반 이중언어 운영 | 효율/품질 균형 확립 |
| **Stage 2** | KPI 충족 시 EN 확대 + KO 정밀화 | 글로벌 확장 본격화 |

---

## 11. 중요 인터페이스/타입 후보 (문서 계약 레벨)

> 아래 항목은 **향후 반영 후보**이며, 본 문서에서는 방향만 정의한다.

### 데이터 모델 후보

| 필드 | 타입(예시) | 목적 |
|---|---|---|
| `posts.locale` | `text` (`ko`/`en`) | 언어 버전 구분 |
| `posts.translation_group_id` | `uuid`/`text` | 동일 콘텐츠 언어군 묶음 |
| `posts.source_post_id` | `uuid`/`text` | KO가 참조하는 EN 원본 포스트 ID |
| `posts.source_post_version` | `text`/`int` | KO가 참조한 EN 기준 버전 |
| `posts.en_revision_id` | `uuid`/`text` | EN 원본 리비전 식별 |
| `posts.locked_en_revision_id` | `uuid`/`text` | KO 생성 트랜잭션에서 잠근 EN 리비전 값 |
| `posts.localization_job_id` | `uuid`/`text` | KO 로컬라이즈 작업 단위 추적 ID |
| `posts.is_major_update` | `boolean` (기본 `false`) | EN 수정이 KO 재동기화를 유발할 major 변경인지 표시 |
| `posts.major_update_note` | `text` | major 변경 사유/범위 기록 (운영 로그) |
| `posts.sync_status` | `text` (`in_sync`/`stale`/`pending`) | EN-KO 동기화 상태 |
| `posts.trigger_mode` | `text` (`instant`/`debounced`/`manual_confirm`) | KO 생성 트리거 방식 |
| `posts.localization_wait_sec` | `int` (기본 `600`) | 디바운스 대기 시간 |
| `posts.localization_trigger_at` | `timestamptz` | EN pass 시 KO 생성 트리거 시각 기록 |
| `posts.localization_generated_at` | `timestamptz` | KO draft 실제 생성 시각 |
| `posts.localization_latency_sec` | `int` | EN pass → KO draft 생성 지연 측정 |
| `posts.source_attributions` | `jsonb` | 출처/인용 메타데이터 |
| `posts.community_signals` | `jsonb` | HN/Reddit 정량 반응 신호 저장 |
| `posts.quality_score` | `numeric` | 품질 게이트 점수 저장 |
| `posts.publish_gate_status` | `text` (`pass`/`hold`/`needs_review`/`stale`) | 발행/동기화 상태 제어 |

### 라우팅/검색 인터페이스 후보

- locale-aware route: `/en/log/[slug]`, `/ko/log/[slug]`
- `x-default -> /en/`
- locale-aware semantic search: 언어 필터 + 교차 추천 규칙
- 검색 평가 메타:
  - `search_eval.cross_lingual_recall_at_k`
  - `search_eval.locale_ndcg_at_k`

### 운영 인터페이스 후보

- 품질 게이트 상태값: `pass`, `hold`, `needs_review`, `stale`
- 동기화 상태값(`sync_status`): `in_sync`, `pending`, `stale`
- 발행 티어 값: `A`, `B`
- 로컬라이즈 운영 옵션: `confirm_to_localize` (`on`/`off`)
- EN 수정 분류 옵션: `is_major_update` (`true`/`false`)

---

## 12. 기존 문서와의 연결

| 문서 | 반영 포인트 |
|---|---|
| `03_Backend_AI_Spec.md` | 다국어 스키마/파이프라인/품질 게이트 상태값/커뮤니티 신호 반영 |
| `04_Frontend_Spec.md` | locale 라우팅, 언어 스위처, SEO 태그/hreflang, 댓글 locale 정책 반영 |
| `05_Infrastructure.md` | locale sitemap, 모니터링 지표, stale 해소 SLA/운영비 추적 반영 |
| `06_Business_Strategy.md` | KO/EN 채널 KPI와 비즈니스 목표 정합화 |

---

## 13. 성공 기준 (문서 기준)

1. 본 문서가 "번역 중심"이 아닌 "해석+큐레이션 중심" 운영 원칙을 명확히 정의한다.
2. 소싱/품질게이트/SEO/i18n/KPI/로드맵이 하나의 운영 체계로 연결되어 있다.
3. 03/04/05/06 문서 개편 시 필요한 인터페이스 후보가 누락 없이 제시되어 있다.
4. EN canonical 및 `x-default -> /en/` 정책이 유지된다.
5. Trigger Policy가 `instant`/`debounced`/`manual_confirm` 3모드로 명시된다.
6. Tier 기본 트리거가 `A=debounced(10분)`, `B=instant`로 명시된다.
7. EN `hold`/`needs_review` 상태에서 KO 생성 금지 규칙이 유지된다.
8. EN 수정 시 `is_major_update=true`일 때만 KO `stale` 전환 + 재생성 큐 규칙이 적용된다.
9. `stale`가 발행 품질이 아닌 동기화 불일치 상태로 정의된다.
10. Cross-lingual 검색 KPI(Recall@K, nDCG@K, mismatch bounce)가 문서에 포함된다.
11. 커뮤니티 정량 신호(`community_signals`)와 활용 목적이 명시된다.
12. KO publish 자동화는 기본 비활성(검수 후 발행) 정책이 명시된다.
13. EN major 수정 시 `major_update_note` 기록 권장 정책이 명시된다.
14. KO 생성/발행 시 EN revision lock 및 `source_post_version` 정합성 검증 규칙이 명시된다.
