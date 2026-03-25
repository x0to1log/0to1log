# 결정: Research 뉴스 큐레이션 품질 강화

> 날짜: 2026-03-25
> 맥락: 2026-03-24 파이프라인 run 결과 research digest가 하드웨어/산업 기사로 채워지는 문제 진단 후 전면 개선

---

## 문제

Research digest가 "AI 리서치 엔지니어에게 유용한 기술 브리프"가 아니라 "하드웨어/산업 뉴스에 research 라벨을 붙인 글"이 되고 있었다.

2026-03-24 run에서 research로 분류된 3건:
- Arm AI 칩 발표
- LG Display 저전력 LCD 양산
- Cognex 제조업 AI 비전 설문

→ 모델/코드/논문이 아닌 산업 뉴스가 전부 papers 서브카테고리로 들어감.

### 근본 원인 3가지

1. **수집 소스 편향** — Tavily(뉴스 검색)만 사용. arXiv 논문, HuggingFace 모델, GitHub 리포를 직접 수집하지 않아 후보 풀에 research 소재 자체가 부족
2. **분류 기준 모호** — "papers: breakthrough results" 같은 넓은 정의. 네거티브 가이드 없음
3. **강제 할당량** — "3-5건 선택" 룰이 기준 미달 기사를 억지로 research에 밀어넣음

---

## 결정

### A. 수집 다변화 — 4개 소스 병렬 수집

| 소스 | 대상 | 수집 범위 | 방식 |
|------|------|----------|------|
| Tavily | 일반 뉴스 (기존) | 2일 | 5개 쿼리 (research 2개 추가) |
| HuggingFace Daily Papers | 커뮤니티 큐레이션 논문 | 1일 (매일 큐레이션됨) | `GET /api/daily_papers?date=` → 상위 10개 |
| arXiv API | 최신 논문 (cs.AI, cs.CL, cs.LG) | 1일 (하루 제출량 충분) | `submittedDate` 필터 → 상위 10개 |
| GitHub Search | 트렌딩 ML 리포 | 3일 (star 축적 필요) | `topic:` 태그 필터 → 상위 10개 + README excerpt |

`collect_news()`에서 `asyncio.gather()`로 병렬 수집, URL 기준 dedup.
예상 후보: 45-55개/일 (기존 ~30개).

#### Backfill 지원

4개 소스 모두 `target_date`를 받아서 해당 날짜 기준으로 수집. backfill 시 현재 날짜 데이터가 섞이지 않음.

#### 발행 URL 제외 (반복 방지)

- `news_posts.source_urls`에서 최근 **3일** 내 발행된 URL을 조회
- 수집 단계에서 해당 URL을 후보에서 제외 → 4개 소스 모두 적용
- GitHub 3일 + DB lookback 3일로 통일

### B. 분류 프롬프트 강화

1. **Research 진입 조건**: 기술 산출물(모델 가중치/코드/논문) 기반으로 한정
2. **Litmus test**: "이 기사의 메인 주제가 모델/코드/논문인가?" + "리서치 엔지니어가 기술적으로 배우는 게 있는가?"
3. **NOT Research 리스트**: 하드웨어 발표, 설문, 전략, 코드 없는 제품 출시 → Business로
4. **open_source 기준**: AI/ML 관련 필수, awesome-* 리스트 제외
5. **0-5 룰**: 기준 미달 시 빈 리스트 허용, 억지 채움 금지

### C. 글쓰기 입력 개선

1. **출처 인용 형식 변경**: `[1](URL)` 번호제 → `[Source Title](URL)` 명시적 인용. arXiv/GitHub 예시 포함
2. **커뮤니티 반응 주입**: 분류 후 상위 3건에 Reddit/HN 반응 수집, 글쓰기 입력에 포함
3. **GitHub raw_content 보강**: description만 → README 앞 1000자 병렬 fetch

### D. 품질 체크 싱크

- Research: `Technical Outlook` → `Why It Matters`
- Business: `Action Items` → `Strategic Decisions`
- 실제 expert 섹션과 일치하도록 수정

### E. 프롬프트 감사 (PROMPT-AUDIT-01 부분 해결)

- `prompts_news_pipeline.py` P0 C2 (citation 매핑) — 해결
- `prompts_advisor.py` P0 C1 (URL hallucination 방지) — "Do NOT fabricate URLs" 추가
- `prompts_advisor.py` P1 H3 (score 해석) — Review 프롬프트에 점수 가이드 추가
- `prompts_handbook_types.py` P1 H3/H4 — 기존에 이미 충족

---

## 결과 (2026-03-25 run 기준)

분류 정확도 대폭 개선:
- Research papers 3건 모두 실제 arXiv 논문 (SpecEyes, ABot-PhysWorld, AutoGaze)
- 벤치마크 수치, 파라미터 수 포함
- Business 5건 모두 적절 (OpenAI 인력확충, Amazon Trainium, NVIDIA GTC 등)

남은 과제:
- LLM & SOTA Models 섹션이 비어 있음 (해당 일자 모델 릴리즈 없어 정상 — 0-5 룰 작동)
- Open Source 품질 약함 → GitHub topic 필터 + 분류 규칙 추가 적용 완료

### ruff + pytest

- `ruff check .` — All checks passed
- `pytest tests/ -v` — 64 passed (테스트를 새 수집 구조에 맞게 업데이트)

---

## 영향 받는 파일

- `backend/services/news_collection.py` — 4개 소스 수집, backfill target_date, 발행 URL 제외
- `backend/services/agents/prompts_news_pipeline.py` — 분류/글쓰기 프롬프트
- `backend/services/agents/prompts_advisor.py` — URL hallucination 방지, score 해석
- `backend/services/agents/ranking.py` — classify_candidates (변경 없음, 프롬프트만 변경)
- `backend/services/pipeline.py` — 커뮤니티 수집 스테이지, 발행 URL 조회, 품질 체크 싱크
- `backend/core/config.py` — import 순서 정리 (ruff E402)
- `backend/tests/test_news_collection.py` — 새 수집기 mock 추가
- `backend/tests/test_ranking.py` — dedup assertion 수정

## Related

- [[ACTIVE_SPRINT]] — COMMUNITY-01, PROMPT-AUDIT-01
- [[AI-News-Pipeline-Design]] — 파이프라인 설계 원본
- [[2026-03-18-prompt-audit-fixes]] — P0 C2 (citation) 이 세션에서 해결
