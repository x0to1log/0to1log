# Handbook Pipeline & Content Quality Audit

> **작성일:** 2026-03-31
> **목적:** 핸드북 파이프라인이 생성한 용어 콘텐츠의 강점/약점 분석 + 품질 기준 수립
> **분석 범위:** published 138개 중 24개 샘플링 (3/18~3/29, 기술/비즈니스/브랜드 혼합)

---

## 1. 파이프라인 강점

### 1-1. 구조화된 다단계 생성 (4-call + self-critique)
- KO Basic → EN Basic + KO Advanced 병렬 → EN Advanced 순서로 분리
- 각 call이 독립적이라 한 쪽 실패가 전체를 망치지 않음
- self-critique loop(score < 75 → 재생성)가 최소 품질 보장

### 1-2. 10개 용어 유형별 depth guide
- algorithm_model, infrastructure_tool, business_industry 등 10개 분류
- 각 유형에 맞는 심화 요구사항이 프롬프트에 주입됨
- 예: algorithm_model → Big O 복잡도 + 수식 유도 필수, infrastructure_tool → 아키텍처 다이어그램 + 벤치마크 필수

### 1-3. 외부 컨텍스트 주입 (Tavily + Exa)
- Tavily 검색으로 최신 정보를 reference materials로 제공
- Exa deep search로 10000자 분량의 full-text 리서치 → 심화 콘텐츠에 사실적 근거 제공
- 이 덕분에 3/25 이후 용어들이 구체적 벤치마크, 논문 인용, 실제 제품 사례를 포함

### 1-4. 이중 난이도 × 이중 언어 구조
- Basic(입문) / Advanced(시니어) 분리 → 타겟 독자 명확
- KO / EN 각각 독립 생성 → 번역체가 아닌 자연스러운 각 언어 콘텐츠
- Basic 11개 섹션, Advanced 11개 섹션으로 표준화

### 1-5. 3/25 이후 콘텐츠 품질 도약
- **Basic**: 30초 요약 + 비유+메커니즘 + 놀라운 예시 + 기술 비교표 + 직군별 활용 포인트
- **Advanced**: 실제 수식(LaTeX) + 아키텍처 비교표(FPS, 메모리 등 수치) + 15줄+ 프로덕션 코드
- 대표 우수 사례: FlashAttention-4, grouped-query attention, supply chain vulnerability, multi-hop retrieval

---

## 2. 약점 — 콘텐츠 품질

### 2-1. 구세대 vs 신세대 품질 격차 (P0)

3/25 기준으로 파이프라인이 크게 개선되었으나, **이전에 생성된 published 용어들이 현재 기준 미달**.

| 구분 | 3/18~3/22 (구세대) | 3/25~3/29 (신세대) |
|------|-------------------|-------------------|
| Basic 평균 길이 | ~1,850자 | ~3,250자 |
| Advanced 평균 길이 | ~4,700자 | ~9,800자 |
| 30초 요약 | 없음 | 있음 |
| 비교표 스타일 | "높음/낮음" 추상적 | 구체적 기술/수치 비교 |
| 예시 | 일반적 (자율주행차, 스마트폰) | 구체적 제품/서비스명 |
| Advanced 수식 | 거의 없음 | LaTeX 수식 포함 |
| Self-critique 흔적 | 없음 | 있음 |

**구세대 대표 사례:**
- `embedding` (basic 1739자, adv 4809자) — 핵심 용어인데 가장 빈약
- `reinforcement learning` (basic 1849자, adv 4996자) — 금지 예시(자율주행차) 사용, 수식 잘림
- `NVIDIA Blackwell` (basic 1746자, adv 4682자) — "높음 vs 보통" 비교표, Advanced가 정의 반복

### 2-2. 비기술 용어 혼입 (P0)

핸드북에 부적합한 비즈니스 버즈워드가 published 상태로 존재.

| 용어 | 문제 |
|------|------|
| actionable intelligence | 기술 용어 아님. Advanced에 가짜 수식 `f(Data Collection, ...)` |
| AI-driven efficiencies | 기술 용어 아님. Advanced가 Basic 내용 반복 |
| ecosystem integration | Advanced에 허위 레퍼런스 (CollectiveOS, Gardener Assimilation Protocol) |
| warping operation | 독립 용어 아님. Image warping, GPU warp, NVIDIA Warp 등 다른 개념 혼합 |
| gaming industry, collaboration | 일반 명사. 기술 핸드북 항목으로 부적절 |

**원인:** 뉴스 추출 단계에서 "AI/IT 관련 용어"의 기준이 느슨함.

### 2-3. Hallucination (허위 정보) (P0)

| 용어 | 허위 내용 |
|------|----------|
| stereo matching | 정의에 "열역학의 '스테레오'와 혼동하지 않도록" — 열역학에 스테레오 개념 없음 |
| ecosystem integration | "CollectiveOS(2025)", "Gardener Assimilation Protocol" — 실존하지 않는 시스템 |
| actionable intelligence | `Actionable Intelligence = f(Data Collection, ...)` — 학술적 근거 없는 가짜 수식 |

### 2-4. 단일 뉴스 소스 과도 의존 (P1)

3/29 생성된 13개 용어가 **전부** IQuest-Coder-V1 (arxiv 2603.16733) 인용.
- stereo matching, supervised fine-tuning, warping operation, mixture of experts, agentic model, recurrent mechanism 등
- 같은 날 뉴스에서 추출된 용어들이 같은 컨텍스트를 공유하는 구조적 문제
- Tavily/Exa 검색 결과가 해당 논문에 편중되면 모든 용어가 같은 레퍼런스를 씀

### 2-5. 중복 용어 (P2)

| 그룹 | 중복 용어들 | 비고 |
|------|-----------|------|
| 진화 알고리즘 | evolutionary search, variation operator | 같은 날짜, 80% 내용 동일 |
| 에이전트 AI | agentic model, agentic AI | 유사 개념 |
| 추론 성능 | inference latency, inference cost | 병합 가능 |

### 2-6. 카테고리 분류 오류 (P2)

- `stereo matching` → categories에 `frontend-ux` 포함 (컴퓨터 비전인데)
- `warping operation` → `ai-ml`만 (너무 광범위)

---

## 3. 약점 — 파이프라인 구조

### 3-1. quality_scores 미기록 (P1)
최근 4개 용어(3/29) 모두 `handbook_quality_scores` 테이블에 점수 없음.
- 스코어링 단계가 skip되거나 저장 로직에 버그 가능성
- 품질 추적/트렌드 분석 불가능

### 3-2. 용어 적합성 필터 부재 (P1)
뉴스에서 추출된 용어가 핸드북에 적합한지 판단하는 게이트가 없음.
- 현재: confidence score ≥ 0.7이면 자동 생성
- 필요: "이 용어가 기술 핸드북에 독립 항목으로 적합한가?" 판단

### 3-3. 구세대 용어 재생성 메커니즘 없음 (P1)
파이프라인이 개선되어도 기존 용어는 업데이트되지 않음.
- 138개 published 중 3/25 이전 생성분이 상당수
- 재생성 트리거 (관리자 일괄 또는 자동)가 없음

### 3-4. 레퍼런스 다양성 제어 없음 (P2)
같은 날짜 뉴스에서 추출된 용어들이 동일한 Tavily/Exa 검색 결과를 공유.
- 결과: 모든 용어가 같은 논문/제품을 인용하는 편향

---

## 4. 품질 기준 (안)

### 4-1. 용어 적합성 기준 (Gate: 추출 후, 생성 전)

핸드북 항목으로 적합한 용어:
- [ ] 기술적 정의가 명확히 존재하는 개념 (학술 논문, 공식 문서에서 정의됨)
- [ ] 일반 비즈니스 용어가 아님 ("efficiency", "collaboration" 등 제외)
- [ ] 기존 용어와 70% 이상 내용 중복이 아님
- [ ] 독립 항목으로 2000자+ 심화 설명이 가능한 깊이

### 4-2. Basic 콘텐츠 최소 기준

| 항목 | 기준 |
|------|------|
| 총 길이 | ≥ 2500자 (KO), ≥ 4000자 (EN) |
| 30초 요약 | 필수, 비유 + 한계 + 화살표(→) 한줄 요약 포함 |
| 비교표 | 2개 이상의 **실제 기술/제품명** 비교 (높음/낮음 금지) |
| 예시 | 금지 목록 사용 없음 (자율주행차, 스마트폰 얼굴인식, 음성비서) |
| 실제 사용처 | 검증 가능한 제품/서비스명 3개+ |

### 4-3. Advanced 콘텐츠 최소 기준

| 항목 | 기준 |
|------|------|
| 총 길이 | ≥ 7000자 (KO), ≥ 12000자 (EN) |
| 수식 | 유형에 따라 LaTeX 수식 1개+ (algorithm_model, concept_theory, metric_measure) |
| 코드 | 15줄+ 프로덕션 수준, 에러 핸들링 포함 |
| 비교표 | 구체적 수치 (FPS, 메모리, 정확도 등) 포함 |
| 레퍼런스 | 검증 가능한 URL 3개+ (논문, 공식 문서, GitHub) |
| Basic 중복 | Basic과 동일 비유/예시 재사용 금지 |

### 4-4. Hallucination 체크 기준

- [ ] 정의에 "~와 혼동하지 않도록" 류의 문구가 있으면 해당 개념 실존 여부 확인
- [ ] Advanced의 레퍼런스 URL이 실제 접근 가능한지 HEAD 체크
- [ ] 비교표의 제품/모델명이 실존하는지 확인
- [ ] 수식이 학술적 근거가 있는지 (가짜 수식 = `f(A, B, C)` 형태 경고)

---

## 5. 구세대 용어 재생성 우선순위

### Tier 1: 핵심 용어인데 빈약 (즉시 재생성)
- embedding, reinforcement learning, NVIDIA Blackwell, agentic access management

### Tier 2: 비기술 용어 (archived 전환)
- actionable intelligence, AI-driven efficiencies, warping operation, gaming industry, collaboration

### Tier 3: Hallucination 수정 (정의/Advanced 부분 수정)
- stereo matching (열역학 문구 삭제 + 카테고리 수정)
- ecosystem integration (CollectiveOS 등 허위 레퍼런스 삭제)

### Tier 4: 중복 병합
- variation operator → evolutionary search에 통합
- 중복 판단 기준: slugA의 Advanced 내용이 slugB와 60%+ 유사하면 병합 후보

---

## 6. 다음 단계 (태스크)

| ID | 제목 | 우선도 | 내용 |
|----|------|--------|------|
| HQ-01 | Hallucination 즉시 수정 | P0 | stereo matching 정의, ecosystem integration adv 수정 |
| HQ-02 | 비기술 용어 archived 처리 | P0 | Tier 2 목록 archived 전환 |
| HQ-03 | 구세대 핵심 용어 재생성 | P1 | Tier 1 목록 4개를 현재 파이프라인으로 regenerate |
| HQ-04 | 용어 적합성 필터 추가 | P1 | 추출 후 생성 전 게이트: 비기술 용어 자동 차단 |
| HQ-05 | quality_scores 저장 버그 수정 | P1 | 최근 용어에 점수 미기록 원인 파악 + 수정 |
| HQ-06 | 콘텐츠 최소 기준 코드화 | P2 | 4-2, 4-3 기준을 파이프라인 post-check로 구현 |
| HQ-07 | 레퍼런스 다양성 제어 | P2 | 같은 batch에서 동일 URL 인용 비율 제한 |
| HQ-08 | 중복 용어 병합 | P2 | Tier 4 목록 처리 |
