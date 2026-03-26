# AI 팩트 체크 기능 설계 — Quick Check + Deep Verify

> 관련: [[Handbook-Prompt-Redesign]], [[2026-03-15-handbook-quality-design]]

---

## 목적

AI가 생성한 콘텐츠(핸드북 용어, 뉴스 기사)의 기술적 정확성을 에디터에서 바로 검증. 두 단계의 검증 옵션을 제공하여 속도/정확도 트레이드오프를 사용자가 선택.

---

## 2단계 검증

| | Quick Check | Deep Verify |
|---|---|---|
| **방식** | LLM이 콘텐츠를 자체 검증 | LLM이 팩트 추출 → Tavily 웹 검색으로 근거 확인 |
| **속도** | 5~10초 | 20~30초 |
| **비용** | ~$0.02 | ~$0.05 |
| **정확도** | 중 (LLM 자체 지식 한계) | 높 (실제 출처 확인) |
| **출력** | verdict + 설명 | verdict + 설명 + 출처 URL |

### 출력 형식

```
✅ verified — "Transformer는 2017년 Google이 발표"
  → Confirmed: "Attention Is All You Need" paper by Vaswani et al., 2017

⚠️ unclear — "BERT는 GPT보다 성능이 높다"
  → 맥락 의존적. BERT는 NLU 태스크에 강하고, GPT는 NLG에 강함

❌ incorrect — "Attention 메커니즘은 CNN에서 처음 도입"
  → 부정확. Bahdanau et al. (2014)이 RNN/Seq2Seq에서 처음 제안

Overall confidence: medium (2/3 verified)
```

Deep Verify는 각 항목에 출처 URL 추가:
```
✅ verified — "Transformer는 2017년 Google이 발표"
  → [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
```

---

## 적용 범위

### 뉴스 에디터 (`/admin/news/`)

- **백엔드**: `factcheck`, `deepverify` 액션 **이미 구현됨** (`advisor.py` + `prompts_advisor.py`)
- **프론트엔드**: AI 패널에 Quick Check, Deep Verify 버튼 추가만 하면 됨
- 결과 렌더링: 기존 AI 결과 패널에 verdict 카드 형태로 표시

### 핸드북 에디터 (`/admin/handbook/edit/[slug]`)

- **백엔드**: `run_handbook_advise()`에 `factcheck`, `deepverify` 액션 핸들러 추가
  - 기존 뉴스용 프롬프트(`FACTCHECK_SYSTEM_PROMPT`, `DEEPVERIFY_*`)를 핸드북 맥락에 맞게 수정
  - "뉴스 기사"가 아닌 "기술 용어 정의/설명"을 검증하는 맥락으로 조정
- **프론트엔드**: AI 패널에 Quick Check, Deep Verify 버튼 추가
- 결과 렌더링: 뉴스와 동일한 verdict 카드 형태

---

## 구현 파일

| 파일 | 변경 | 에디터 |
|------|------|--------|
| `backend/services/agents/advisor.py` | `run_handbook_advise()`에 factcheck/deepverify 분기 추가 | 핸드북 |
| `backend/services/agents/prompts_advisor.py` | 핸드북용 팩트체크 프롬프트 추가 (또는 기존 재사용) | 핸드북 |
| `backend/models/advisor.py` | `HandbookAdviseRequest.action`에 factcheck/deepverify 추가 | 핸드북 |
| `frontend/.../handbook/edit/[slug].astro` | AI 패널에 버튼 2개 + 결과 렌더링 | 핸드북 |
| `frontend/.../admin/news/edit 관련 파일` | AI 패널에 버튼 2개 추가 (백엔드 이미 있음) | 뉴스 |

---

## SEO 메타

별도 AI 기능 불필요:
- **핸드북**: `definition.slice(0, 150)`이 이미 meta description으로 사용 중
- **뉴스**: Head.astro의 description prop으로 전달 (별도 확인 필요)

---

## Related

- [[AI-Handbook-Pipeline-Overview]]
- [[Handbook-Prompt-Redesign]]
- [[Admin]]
