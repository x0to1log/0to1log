# News Quality Review Skill — Design Doc

> **작성일:** 2026-03-30
> **목적:** backfill된 특정 날짜의 뉴스 드래프트를 독자 관점에서 리뷰하는 Claude 스킬
> **스킬 이름:** `0to1-news-quality`
> **스킬 경로:** `~/.claude/skills/0to1-news-quality/`

---

## 배경

뉴스 파이프라인 backfill 후 매번 반복되는 워크플로우:
1. Claude에게 "이 날짜 뉴스 가져와서 봐줘" 요청
2. Claude가 DB에서 draft 포스트 fetch
3. 내용 읽고 학습자/현직자 관점에서 피드백
4. 피드백 기반으로 프롬프트/파이프라인 개선 (별도 작업)

**문제:** 매번 리뷰 기준을 처음부터 설명해야 하고, 관점이 일관되지 않음.

**해결:** 리뷰 기준(루브릭)을 스킬에 내장하여 일관된 피드백을 자동으로 받기.

---

## 스킬 구조

```
~/.claude/skills/0to1-news-quality/
├── SKILL.md              # 워크플로우 + 피드백 출력 형식
├── scripts/
│   └── fetch_posts.py    # 날짜별 draft 포스트 fetch → JSON 출력
└── references/
    └── review-rubric.md  # 4관점 리뷰 루브릭
```

---

## 컴포넌트 설계

### 1. fetch_posts.py

**역할:** Supabase에서 특정 날짜의 뉴스 드래프트를 가져와 JSON으로 출력

**실행:**
```bash
source backend/.venv/Scripts/activate && python ~/.claude/skills/0to1-news-quality/scripts/fetch_posts.py 2026-03-25
```
- `backend/.venv`를 사용 (CLAUDE.md venv 정책 준수)
- `supabase`, `python-dotenv`는 이미 backend 의존성에 포함

**데이터 소스:**
- `backend/.env`에서 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 읽기
- `news_posts` 테이블: `pipeline_batch_id = {date}` 조건
- `post_type IN ('research', 'business')` — `weekly`는 별도 편집 프로덕트이므로 제외

**SELECT 컬럼:**
```
id, title, post_type, locale, status, content_expert, content_learner,
quality_score, fact_pack, source_urls
```

**출력:**
```json
[
  {
    "title": "AI Research Digest — 2026-03-25",
    "post_type": "research",
    "locale": "ko",
    "status": "draft",
    "content_expert": "...",
    "content_learner": "...",
    "quality_score": 85,
    "fact_pack": { "quality_breakdown": { "expert": {...}, "learner": {...} } },
    "source_urls": ["https://..."]
  },
  {
    "title": "AI Research Digest — 2026-03-25",
    "post_type": "research",
    "locale": "en",
    "status": "draft",
    "content_expert": "...",
    "content_learner": "...",
    "quality_score": 87,
    "fact_pack": { "quality_breakdown": { "expert": {...}, "learner": {...} } },
    "source_urls": ["https://..."]
  }
]
```

**에러 처리:**
- `.env` 없음 → 에러 메시지 + `backend/.env` 경로 안내
- 해당 날짜 포스트 없음 → 빈 배열 + `"No posts found for {date}"`
- Supabase 연결 실패 → 에러 메시지 + URL/KEY 확인 안내

### 2. review-rubric.md

**4관점 리뷰 루브릭 (가중치 순):**

#### 학습자 관점 — content_learner 리뷰용 (가중치: HIGH)
- 나열식 서술 ("X가 출시되었다") 없이 "왜 중요한지" 맥락이 있는가
- 읽고 나서 구체적으로 배운 게 있는가 (실질적 학습 가치)
- 용어 설명: 이미 잘 되고 있으므로 가볍게만 체크

#### 현직자 관점 — content_expert 리뷰용 (가중치: HIGH)
- 기술/제품이 실무에 어떻게 적용될지 연결이 있는가
- 수치/벤치마크: 이미 잘 되고 있으므로 가볍게만 체크

#### 시각/톤 — 전체 공통 (가중치: MEDIUM)
- AI가 쓴 티나는 어색한 표현 (과잉 수식어, 틀에 박힌 문구)
- 마크다운 문법이 렌더링 안 되고 그대로 노출되는 곳
- ko/en 각각의 언어에 맞는 자연스러운 문체인지

#### 팩트 정확성 — 전체 공통 (가중치: LOW)
- citation URL이 유효해 보이는가
- 수치/날짜가 상식적으로 맞는가

### 3. SKILL.md

**트리거:** `/news-quality`, "뉴스 퀄리티 체크", "backfill 리뷰"

**워크플로우:**
1. 날짜 파라미터 확인 (없으면 물어보기)
2. `fetch_posts.py {date}` 실행 (backend/.venv 사용)
3. 포스트가 없으면 안내 후 종료
4. `review-rubric.md` 읽어서 기준 로드
5. 포스트를 locale별로 그룹핑 (ko 먼저, en 다음)
6. 각 포스트의 content_learner → 학습자 관점 리뷰, content_expert → 현직자 관점 리뷰
7. 시각/톤, 팩트 정확성은 양쪽 모두 체크
8. content_learner 또는 content_expert가 null이면 "미생성" 표시, 피드백 생략
9. 이슈 없는 관점은 생략

**자동 점수 표시 규칙:**
- `quality_score > 0` → 점수 표시
- `quality_score = 0` → "자동 점수: 미측정 (스킵됨)" 표시
- `quality_score = null` → "자동 점수: 없음" 표시
- 존재하는 post_type만 표시

**피드백 출력 형식:**
```
## 2026-03-25 뉴스 리뷰

자동 점수: research 85/100, business 78/100

---

### [ko] research

**입문자용 (content_learner):**
학습자 관점:
- "Why It Matters" 섹션에서 DPO의 이점을 나열만 하고
  왜 이게 중요한지 맥락이 없음 (2번째 문단)

**전문가용 (content_expert):**
현직자 관점:
- 전반적으로 실무 연결이 잘 되어 있음. 이슈 없음.

시각/톤:
- "이러한 발전은 매우 의미 있는 것으로..." — AI 특유의 과잉 수식어

### [en] research

**입문자용 (content_learner):**
(이슈 없음)

**전문가용 (content_expert):**
(이슈 없음)

### [ko] business
...
```

---

## 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 판정 시스템 (PUBLISH/REGENERATE) | **없음** | 피드백만 제공, 판단은 사용자가 함 |
| fetch 방식 | **Python 스크립트** | 매번 curl 짜는 토큰 낭비 방지, deterministic |
| 루브릭 위치 | **references 파일** | SKILL.md를 가볍게 유지, 루브릭만 독립 수정 가능 |
| 기준 가중치 | **루브릭에 명시** | "잘 되고 있는 것"은 가볍게만 → 토큰 절약 |
| locale 순서 | **ko 먼저, en 다음** | ko가 주 리뷰 대상, en은 보통 잘 나옴 |
| weekly 제외 | **fetch에서 필터** | 별도 편집 프로덕트, 루브릭이 다름 |
| content persona 네이밍 | **입문자용/전문가용** | 리뷰 관점(학습자/현직자)과의 혼동 방지 |
| venv | **backend/.venv** | CLAUDE.md 정책 준수, 의존성 이미 포함 |

---

## 향후 확장 가능

- 루브릭 기준 추가/삭제 → `references/review-rubric.md` 수정
- fetch 범위 변경 → `scripts/fetch_posts.py` 수정
- 피드백 형식 변경 → `SKILL.md` 수정
- published 포스트 리뷰 지원 추가 가능
- weekly 포스트용 별도 루브릭 추가 가능

---

## Related

- [[2026-03-26-news-quality-check-overhaul]] — 품질 체크 시스템 설계
- [[2026-03-29-news-pipeline-v7]] — 파이프라인 v7 결정 로그
