# Handbook Advanced Quality System 설계

> **작성일:** 2026-03-18
> **목적:** 핸드북 심화(Advanced) 콘텐츠의 품질을 "시니어 엔지니어가 참고할 수 있는 수준"으로 끌어올리기
> **현재 문제:** 심화 콘텐츠가 기술 블로그 수준에 머무르고, 용어 유형에 관계없이 동일한 프롬프트로 생성

---

## 1. 핵심 문제 분석

### 현재 한계
- LLM이 **모르는 건 프롬프트로 아무리 지시해도 못 씀** (knowledge cutoff)
- 10개 용어 유형에 대해 **하나의 프롬프트**로 심화 콘텐츠 생성 → 깊이가 일률적
- **퀄리티 검증 없음** — 얕은 콘텐츠가 그대로 저장됨
- **Self-critique 없음** — one-shot 생성 후 끝

### 목표 수준
- 기초: 중학생도 이해 가능 (현재 적절)
- 심화: **미드~시니어 개발자가 레퍼런스로 참고할 수 있는 깊이**

---

## 2. 용어 유형 분류 체계 (10 Types)

| # | 유형 | 예시 | 심화의 깊이를 만드는 것 |
|---|------|------|----------------------|
| 1 | **알고리즘/모델** | BERT, Transformer, GAN | 코드, 수식 유도, 복잡도 분석, 수렴 조건 |
| 2 | **인프라/도구** | Docker, Kubernetes, CUDA | 아키텍처 다이어그램, 실전 설정, 트러블슈팅, 벤치마크 |
| 3 | **비즈니스/산업** | Funding Round, AI 생태계 | 시장 데이터, 사례 분석, 의사결정 프레임워크 |
| 4 | **개념/이론** | Overfitting, Bias-Variance | 수학적 직관, 시각적 설명, trade-off 분석 |
| 5 | **제품/브랜드** | GPT-5.4, Claude, Midjourney | 경쟁 제품 비교, 가격/API 스펙, 버전 히스토리, 벤치마크 |
| 6 | **메트릭/지표** | AUC, F1, BLEU, Perplexity | 공식 유도, 메트릭 선택 기준, 오용 사례 |
| 7 | **기법/방법론** | Data Augmentation, Prompt Engineering | 변형 비교, 조합 효과, 실패 패턴, 적용 조건 |
| 8 | **데이터 구조/포맷** | Parquet, B-Tree, ONNX | 내부 구조, 복잡도 분석, 포맷 간 벤치마크, 마이그레이션 |
| 9 | **프로토콜/표준** | OAuth 2.0, HTTP/3, gRPC | 핸드셰이크 흐름, 보안 모델, RFC 참조, 버전 비교 |
| 10 | **아키텍처 패턴** | Microservices, CQRS, RAG | 트레이드오프 분석, 마이그레이션 전략, 장애 사례 |

### 분류 방법
- **gpt-4o-mini 1회 호출** (~$0.001): 용어명 + 카테고리 → 10개 유형 중 택 1
- 프롬프트에 10개 유형 + 예시만 넣으면 됨 (짧음)
- 유형별 전용 심화 프롬프트를 선택하는 라우팅 역할

---

## 3. 새 파이프라인 흐름

```
용어 입력 (term + korean_name + categories)
     │
     ├──── ① Tavily 검색 (~$0.01)              ─┐
     └──── ② gpt-4o-mini 유형 분류 (~$0.001)    ─┤  병렬
                                                  ↓
     ③ 유형별 전용 심화 프롬프트 선택
        + Tavily 결과를 Reference Materials로 주입
                    ↓
     ④ gpt-4o로 심화 콘텐츠 생성 (기존 Call 3-4)
                    ↓
     ⑤ Self-critique (gpt-4o, ~$0.04)
        "시니어 엔지니어 관점에서 부족한 점은?"
        → 부족하면 보강 지시 + 재생성
                    ↓
     ⑥ 퀄리티 체크 (gpt-4o-mini, ~$0.02)
        유형별 기준으로 점수 매기기 (0-100)
        → 기준 미달 시 warning 첨부
                    ↓
     ⑦ 저장
```

### 기존 흐름과 비교

```
기존:  용어 → Call 1-4 → 저장
신규:  용어 → Tavily+분류(병렬) → 유형별 프롬프트 → 생성 → 자기검증 → 퀄리티 체크 → 저장
```

---

## 4. Tavily 검색 통합

### 모든 용어에 필수 적용
- LLM knowledge cutoff 극복 (최신 제품/벤치마크)
- 실제 URL로 참조 링크 신뢰도 향상
- 정량적 데이터 (벤치마크 수치, 가격 등) 확보

### Context 전달 형식
```
## Reference Materials (from web search)

### [1] Title
URL: https://...
Content snippet...

### [2] Title
URL: https://...
Content snippet...

---
위 자료를 fact source로 활용하되, 레퍼런스 스타일로 작성하세요.
수치와 벤치마크는 위 자료에서 인용하세요.
참조 링크(refs) 섹션에는 위 URL을 우선 사용하세요.
```

### Tavily 호출 설정
- `search_depth`: "advanced" (더 정확한 결과)
- `max_results`: 5
- `include_raw_content`: false (snippet만, 토큰 절약)
- 비용: 월간 크레딧으로 무료 사용 중

### 향후 확장 가능 소스
| 소스 | 효과 | 비용 | 우선순위 |
|------|------|------|---------|
| Tavily | 일반 검색, 블로그, 뉴스 | 무료 (크레딧) | **P0 (필수)** |
| arxiv API | 논문 abstract | 무료 | P1 |
| GitHub API | 코드 예시, README | 무료 | P1 |
| Papers with Code | 벤치마크 리더보드 | 무료 | P2 |

---

## 5. Self-Critique 단계

### 목적
- LLM이 자기 출력을 검토하고 부족한 부분을 보강
- "시니어 엔지니어가 읽었을 때 부족하다고 느낄 부분"을 식별

### 프롬프트 구조 (요약)
```
당신은 시니어 ML 엔지니어입니다. 아래 심화 설명을 읽고:
1. 깊이가 부족한 섹션을 지적하세요
2. 추가해야 할 구체적 내용을 제안하세요
3. 코드가 프로덕션 수준인지 평가하세요
4. 이 용어 유형({type})에 맞는 깊이가 충분한지 판단하세요
```

### 동작
- critique 결과에 "부족" 판정이 있으면 → 보강 지시를 포함한 재생성 1회
- 재생성 후에는 추가 critique 없음 (무한 루프 방지)
- 비용: ~$0.04/용어 (gpt-4o 1회)

---

## 6. 퀄리티 체크

### 유형별 적응형 기준
10개 유형 전부를 프롬프트에 넣지 않음. LLM에게 "이 용어의 유형은 {type}이다" + 해당 유형의 깊이 기준만 전달.

### 점수 체계
- 0-100점
- 60점 미만: warning 첨부 + 어드민에서 확인 필요 표시
- 80점 이상: 자동 발행 후보 (AUTOPUB-01과 연결)

### 비용
- gpt-4o-mini 1회: ~$0.02/용어

---

## 7. 비용 분석

### 용어당 비용 비교

| 단계 | 현재 | 추가 | 합계 |
|------|------|------|------|
| 기초 생성 (Call 1-2) | ~$0.16 | 0 | $0.16 |
| 심화 생성 (Call 3-4) | ~$0.16 | 0 | $0.16 |
| Tavily 검색 | 0 | ~$0.01 | $0.01 |
| 유형 분류 (mini) | 0 | ~$0.001 | $0.001 |
| Self-critique | 0 | ~$0.04 | $0.04 |
| 퀄리티 체크 (mini) | 0 | ~$0.02 | $0.02 |
| **합계** | **~$0.32** | **~$0.07** | **~$0.39** |

추가 비용: **+$0.07/용어 (22% 증가)**
월간 (5용어/일): **+$10.50** → $48 → $58.50

---

## 8. 구현 순서

### Phase 1: Tavily + 유형 분류 (기반)
1. Tavily 검색 함수 추가 (`advisor.py`)
2. 유형 분류 프롬프트 + gpt-4o-mini 호출
3. 병렬 실행 (`asyncio.gather`)
4. Tavily 결과를 심화 프롬프트 context에 주입

### Phase 2: 유형별 프롬프트 (핵심)
5. 10개 유형별 심화 프롬프트 작성 (새 파일 `prompts_handbook_types.py`)
6. 유형 → 프롬프트 라우팅 로직
7. 기존 `GENERATE_ADVANCED_PROMPT` 대체

### Phase 3: Self-Critique + 퀄리티 (검증)
8. Self-critique 프롬프트 + 재생성 로직
9. 퀄리티 체크 프롬프트 + 점수 저장
10. 어드민 핸드북 목록에 퀄리티 점수 배지

---

## 9. 수정 파일 (예상)

| 파일 | 변경 |
|------|------|
| `backend/services/agents/advisor.py` | Tavily 호출, 유형 분류, self-critique, 퀄리티 체크 통합 |
| `backend/services/agents/prompts_handbook_types.py` | **신규** — 10개 유형별 심화 프롬프트 |
| `backend/services/agents/prompts_advisor.py` | 기존 심화 프롬프트를 유형별로 라우팅하도록 변경 |
| `backend/services/pipeline.py` | 핸드북 파이프라인에 유형 분류 + Tavily 병렬 호출 추가 |

---

## Related

- [[Handbook-Prompt-Redesign]] — 기존 프롬프트 아키텍처 v2
- [[2026-03-15-handbook-quality-design]] — 기초/심화 섹션 구조
- [[2026-03-17-news-pipeline-v4-design]] — 뉴스 v4 (article_context 패턴 참조)
