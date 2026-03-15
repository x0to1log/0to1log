# AI News Pipeline — 설계

> 비전: [[AI-News-Feature-Design]]
> 콘텐츠 구조: [[AI-News-Content-Structure]]
> 운영: [[AI-News-Pipeline-Operations]]
> 상태: 설계 확정, 구현 대기

---

## 파이프라인 전체 흐름

```mermaid
flowchart TD
    CRON["⏰ Cron Trigger (매일 아침)"] --> COLLECT["1. 뉴스 수집\nTavily API"]
    ADMIN_BTN["👤 Admin 수동 실행\n(target_date 지정 가능)"] --> COLLECT
    COLLECT --> RANK["2. LLM 랭킹\nresearch 1건 + business 1건 선정"]
    RANK --> HAS_R{"research \n 뉴스 있나?"}

    HAS_R -->|Yes| REACT_R["3a. 커뮤니티 반응 수집\n(Research)"]
    HAS_R -->|No| SKIP_R["Research skip"]

    RANK --> REACT_B["3b. 커뮤니티 반응 수집\n(Business)"]

    REACT_R --> GEN_R["4~5. Research 포스트 생성\n(팩트 추출 → 3 페르소나)"]
    REACT_B --> GEN_B["4~5. Business 포스트 생성\n(팩트 추출 → 3 페르소나)"]

    GEN_R --> SAVE_R["6. draft로 저장"]
    GEN_B --> SAVE_B["6. draft로 저장"]
    SKIP_R --> DONE["✅ 파이프라인 완료"]
    SAVE_R --> DONE
    SAVE_B --> DONE

    DONE --> ADMIN["👤 Admin 검토 → 발행"]
```

## 포스트 1건 생성 상세 흐름

Research와 Business 모두 동일한 구조. 포스트 1건당 4 LLM 호출.

```mermaid
flowchart TD
    START["뉴스 원문 + Tavily 컨텍스트\n+ 커뮤니티 반응"] --> FACTS["Call 1: 팩트 추출\n→ 구조화된 JSON"]

    FACTS --> EXPERT["Call 2: 현직자(Expert)\nEN+KO 동시 생성"]
    FACTS --> LEARNER["Call 3: 학습자(Learner)\nEN+KO 동시 생성"]
    FACTS --> BEGINNER["Call 4: 입문자(Beginner)\nEN+KO 동시 생성"]

    EXPERT --> MERGE["결과 병합"]
    LEARNER --> MERGE
    BEGINNER --> MERGE

    MERGE --> SAVE["news_posts에\ndraft로 저장"]
```

## 데이터 흐름

```mermaid
flowchart LR
    subgraph 수집
        TAVILY["Tavily API"] --> CANDIDATES["뉴스 후보 ~20건"]
    end

    subgraph 선정
        CANDIDATES --> LLM_RANK["LLM 랭킹"]
        LLM_RANK --> R_PICK["Research 1건"]
        LLM_RANK --> B_PICK["Business 1건"]
    end

    subgraph 반응수집
        R_PICK --> TAVILY_R["Tavily 반응\nReddit/HN/X"]
        B_PICK --> TAVILY_B["Tavily 반응\nReddit/HN/X"]
    end

    subgraph "포스트 생성 (×2)"
        TAVILY_R --> FACT_EX["팩트 추출 JSON"]
        TAVILY_B --> FACT_EX
        FACT_EX --> P_EXP["현직자 EN+KO"]
        FACT_EX --> P_LRN["학습자 EN+KO"]
        FACT_EX --> P_BGN["입문자 EN+KO"]
    end

    subgraph 저장
        P_EXP --> DB["news_posts\n(draft)"]
        P_LRN --> DB
        P_BGN --> DB
    end

    DB --> ADMIN["Admin 검토\n→ 발행"]
```

---

## 수집 & 선정

- **소스**: Tavily API (AI 관련 키워드 검색)
  - 기본: `days=2` (오늘+어제)
  - 백필: `start_date` / `end_date` 지정 (admin이 `target_date` 선택 시)
  - `include_raw_content=True`로 뉴스 원문 전체 수집
- **선정**: LLM이 후보 뉴스를 랭킹
  - **Research**: 기술/논문/모델 중심 1건
  - **Business**: 시장/투자/전략 중심 1건
- **커뮤니티 반응**: 선정된 뉴스에 대해 Tavily로 Reddit, Hacker News, X 등의 반응 추가 수집 → 팩트 추출에 입력

---

## 콘텐츠 생성 — 전략 C: 팩트 추출 → 3개 독립

### 포스트 1건당 LLM 호출 구조

| 순서 | 호출 | 입력 | 출력 |
|------|------|------|------|
| Call 1 | **팩트 추출** | 뉴스 원문 + Tavily 컨텍스트 + 커뮤니티 반응 | 구조화된 팩트 JSON (핵심 사실, 수치, 출처, 반응 요약) |
| Call 2 | **현직자(Expert)** | 팩트 JSON | Expert EN+KO 동시 출력 (JSON) |
| Call 3 | **학습자(Learner)** | 팩트 JSON | Learner EN+KO 동시 출력 (JSON) |
| Call 4 | **입문자(Beginner)** | 팩트 JSON | Beginner EN+KO 동시 출력 (JSON) |

### 왜 이 전략인가

- **팩트 일관성**: 모든 페르소나가 같은 구조화된 팩트에서 출발 → 수치/사실 불일치 방지
- **독립 품질**: 각 페르소나가 독립적으로 작성됨 → "파생 = 축약" 문제 없음
- **팩트 재활용**: 추출된 팩트를 프론트엔드(출처 카드, 커뮤니티 반응 표시)에도 활용
