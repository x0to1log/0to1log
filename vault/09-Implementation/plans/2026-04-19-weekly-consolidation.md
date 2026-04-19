# Weekly News Consolidation — Dead Code Removal + Admin Fix + Daily Parity

> **Sprint fit**: HB-QM sprint 중 mid-sprint 정리 작업 (weekly feature 잔여 gap 일괄 해소)
> **Related**: [[2026-04-19-weekly-content-v2]] — weekly quiz 도입 세션 (이 문서는 그 세션에서 발견된 잔여 이슈 정리)
> **Discovery 세션**: 2026-04-19 w13 frontend JSON 노출 버그 → admin coverage 조사 → dead code 스윕
> **작성**: 2026-04-19

---

## Goal

Weekly news 기능의 "반쯤 완성된" 상태를 해소하고 Daily와의 데이터 모델 정합성 확보.

3가지 문제를 한 PR로 정리:
1. **Dead code** (one_liner/action_item/critical_gotcha/rotating_item) — pipeline이 더 이상 안 쓰지만 models/advisor/frontend에 여전히 참조 남아있음
2. **Admin post_type 드롭다운 corruption** — weekly 포스트 편집 시 post_type이 null로 덮어씌워짐
3. **Weekly excerpt/focus_items 부재** — Daily는 LLM이 생성하지만 Weekly는 NULL → 리스트 카드·SEO 메타·사이드 rail이 비거나 fallback 사용

---

## Scope (5 Workstreams)

| # | 워크스트림 | 규모 | 의존성 |
|---|---|---|---|
| **A** | Dead code 완전 제거 (PromptGuideItems 포함) | 8 파일 | 독립 |
| **B** | Admin `post_type` 드롭다운 'weekly' 옵션 추가 | 1 파일 | 독립 |
| **C** | Weekly excerpt + focus_items LLM 생성 (daily 패턴 일치) | 2 파일 | 독립 |
| **D** | 기존 W13/W14/W15 백필 | 0 파일 (운영) | C 완료 |
| **E** | 기존 daily `guide_items` 잔여 키 JSONB 정리 | 0 파일 (DB 작업) | A 완료 |

**한 PR**로 묶음 — 전부 "weekly 정합성" 단일 intent.

---

## Workstream A — Dead Code 완전 제거

### 제거 대상
- `guide_items.one_liner`
- `guide_items.action_item`
- `guide_items.critical_gotcha`
- `guide_items.rotating_item`
- `PromptGuideItems` 클래스 (4개 제거 후 `quiz_poll`만 남는데 실제로 안 쓰임 → 클래스 전체 삭제)

### 수정 파일

**Backend (5)**
| 파일 | 변경 |
|---|---|
| `backend/models/common.py` | `PromptGuideItems` 클래스 완전 삭제 |
| `backend/models/posts.py` | `PromptGuideItems` import 제거 / `Optional[PromptGuideItems]` → `Optional[dict]` 교체 (line 5, 45, 69) |
| `backend/services/agents/prompts_advisor.py` | 4개 digest_type × 4 필드 = 16개 suggestion 문자열 제거 (line 51-72) |
| `backend/services/agents/advisor.py` | Advisor 출력 스키마에서 4필드 관련 로직 제거 (grep로 확인 후 결정) |
| `backend/openapi.json` | `PromptGuideItems` 스키마 제거 (FastAPI 재생성 또는 수동 삭제) |

**Frontend (2)**
| 파일 | 변경 |
|---|---|
| `frontend/src/components/newsprint/NewsprintArticleLayout.astro` | `interface GuideItems`에서 4필드 제거 (line 15-21) / `hasGuideItems` 조건 단순화 (line 137) / 4개 render 블록 제거 (line 396-422) |
| `frontend/src/pages/admin/edit/[slug].astro` | Advisor 패널 "Apply" 버튼 4개 + 처리 로직 제거 (grep `data-apply="one_liner"` 등으로 위치 찾기) |

**Vault docs (2)**
| 파일 | 변경 |
|---|---|
| `vault/02-Architecture/Database-Schema-Overview.md` line 34 | "5블록 guide_items" → 실제 구조 반영 |
| `vault/04-AI-System/Quality-Gates-&-States.md` line 31 | `PromptGuideItems` 블록 목록 업데이트 |

**건드리지 않음** (CLAUDE.md 금지):
- `docs/03_Backend_AI_Spec.md` (legacy spec)
- `vault/90-Archive/` (read-only)

### DB 영향
스키마 변경 없음. `guide_items` JSONB 잔여 키는 Workstream E에서 정리.

### 위험도
🟢 낮음. 기계적 삭제가 대부분. 회귀 포인트 = Advisor 패널 레이아웃 (버튼 4개 제거해도 UI 깨지지 않는지 빌드 검증).

---

## Workstream B — Admin `post_type` 드롭다운 fix

### 현재 문제
[edit/\[slug\].astro:180-184](../../../frontend/src/pages/admin/edit/[slug].astro) 드롭다운에 `weekly` 옵션 없음 → weekly 포스트 편집 시 `—`(empty) 기본 선택 → Save 시 `post_type = null`로 덮어씀.

### 수정안

```astro
<option value="" selected={!post?.post_type}>—</option>
<option value="research" selected={post?.post_type === 'research'}>Research</option>
<option value="business" selected={post?.post_type === 'business'}>Business</option>
<option value="weekly"
        selected={post?.post_type === 'weekly'}
        disabled={post?.post_type !== 'weekly'}>Weekly</option>
```

`disabled={post?.post_type !== 'weekly'}` 의미:
- 기존 weekly 편집: 옵션 선택된 상태, 활성 → 저장 시 'weekly' 그대로
- 다른 타입 편집: 옵션 회색, 선택 불가 → weekly 변환 실수 차단
- 신규 포스트: `post?.post_type === undefined` → 비활성 → 수동 weekly 생성 불가

### Save 엔드포인트
`save.ts` 수정 불필요 ([posts/save.ts:53-54](../../../frontend/src/pages/api/admin/posts/save.ts) `row.post_type = post_type || null` 로직은 이미 'weekly' 문자열 통과시킴).

### 회귀 검증
- [ ] 기존 weekly 포스트 편집 → save → DB post_type 여전히 'weekly'
- [ ] content/guide_items/quiz 보존
- [ ] research/business 편집 시 weekly 옵션 회색
- [ ] 신규 포스트에서 weekly 선택 불가
- [ ] 드롭다운 UI 레이아웃 회귀 없음

### 위험도
🟢 매우 낮음. 순수 UI 2-3줄.

---

## Workstream C — Weekly excerpt + focus_items LLM 생성

Daily 패턴을 weekly로 이식. 지난 `weekly_quiz_ko` 버그 교훈 적용 (KO adapter input에 번역 원본 포함 필수).

### C.1 Prompt 변경

**`WEEKLY_EXPERT_PROMPT` & `WEEKLY_LEARNER_PROMPT` JSON 출력 확장**

두 필드 추가:
```json
{
  "excerpt": "(English) 1-2 sentences that make readers click. MUST differ from the body's 'This Week in One Line' section",
  "focus_items": ["Exactly 3 bullets, EN 5-12 words each. P1=what shifted this week, P2=why it matters, P3=what to watch next week"]
}
```

페르소나별 가이드:
- Expert: strategic decision lens — 어떤 shift/impact에 focus
- Learner: plain language, non-specialist accessible

Constraints에 추가:
- `excerpt` MUST differ from "## This Week in One Line" body
- `focus_items` exactly 3 items (가드 함수가 이 외는 drop)

**`WEEKLY_KO_ADAPT_PROMPT` 번역 필드 추가**

JSON 출력에 두 필드 추가:
```json
{
  "excerpt_ko": "Korean translation of excerpt",
  "focus_items_ko": ["Korean translations of focus_items in SAME order"]
}
```

프롬프트에 marker 지시 추가:
> The user message may end with `---ENGLISH META (JSON, translate to excerpt_ko + focus_items_ko)---` followed by JSON. Translate those fields 1:1.

### C.2 Pipeline `_gen_weekly_persona` — KO adapter input 확장

[pipeline.py:2018-2032](../../../backend/services/pipeline.py) 지역 수정.

기존 `weekly_quiz` marker 패턴을 유지하면서 excerpt/focus_items도 append:

```python
import json as _json
en_content = en_data.get("en", "")
en_quiz = en_data.get("weekly_quiz") or []
en_excerpt = en_data.get("excerpt") or ""
en_focus = en_data.get("focus_items") or []

ko_input_parts = [en_content]
if en_quiz:
    ko_input_parts.append(
        "---ENGLISH WEEKLY QUIZ (JSON, translate to weekly_quiz_ko)---\n"
        + _json.dumps(en_quiz, ensure_ascii=False, indent=2)
    )
if en_excerpt or en_focus:
    meta = {"excerpt": en_excerpt, "focus_items": en_focus}
    ko_input_parts.append(
        "---ENGLISH META (JSON, translate to excerpt_ko + focus_items_ko)---\n"
        + _json.dumps(meta, ensure_ascii=False, indent=2)
    )
ko_input = "\n\n".join(ko_input_parts)
# Use ko_input instead of en_content in KO adapter user message
```

### C.3 Pipeline `run_weekly_pipeline` — row 저장 로직

Daily의 저장 패턴을 따름. locale 루프 안에서:

```python
# Locale-appropriate key selection
excerpt_key = "excerpt" if locale == "en" else "excerpt_ko"
focus_key = "focus_items" if locale == "en" else "focus_items_ko"

# Canonical = expert's, Learner fallback
excerpt = (expert_data.get(excerpt_key) or learner_data.get(excerpt_key) or "").strip()
excerpt_learner = (learner_data.get(excerpt_key) or "").strip()

# focus_items: prefer expert (locale-level, not per-persona — matches daily)
focus_raw = expert_data.get(focus_key) or learner_data.get(focus_key) or []
focus_items = _validate_focus_items(focus_raw)  # guard (see C.4)

row = {
    ...,
    "excerpt": excerpt or None,
    "focus_items": focus_items,
    ...
}
locale_guide["excerpt_learner"] = excerpt_learner
```

### C.4 검증 가드

신규 헬퍼 `_validate_focus_items(lst)`:
- Non-list → `[]`
- 길이 != 3 → `[]` (부분적 허용은 혼란)
- 각 item 문자열 변환 + strip
- 빈 문자열 포함 → `[]`

Excerpt는 `.strip()` + 1000자 이상 절단 (LLM runaway 방어).

실패 시 `None` / `[]` 반환. 발행 막지 않음 (weekly_quiz와 동일 방침).

### C.5 회귀 포인트
- marker 텍스트가 `---ENGLISH WEEKLY QUIZ---`와 `---ENGLISH META---`로 분리 — LLM이 혼동 안 하도록 구분 명확
- `WEEKLY_KO_ADAPT_PROMPT` 기존 필드(`headline_ko`, `ko`, `weekly_quiz_ko`) 보존 확인
- `guide_items.excerpt_learner` 키는 daily가 이미 쓰므로 frontend 변경 없음 ([NewsprintArticleLayout.astro](../../../frontend/src/components/newsprint/NewsprintArticleLayout.astro) 이미 read)

### 위험도
🟡 중간. 3자 간 계약 (EN expert/learner prompts + KO adapter input/prompt)이라 한 자리 놓치면 KO 쪽 empty (weekly_quiz 때 겪은 패턴). 완화책 = D에서 명시적 KO 필드 검증.

---

## Workstream D — 기존 Weekly 3개 백필

### 실행 조건
A + B + C 전부 main merge & Railway 재배포 완료 후.

### 실행 방식

로컬 Python으로 순차 실행 (병렬은 `pipeline_runs` 경쟁 조건 여지):

```python
import asyncio
from services.pipeline import run_weekly_pipeline

for wk in ['2026-W13', '2026-W14', '2026-W15']:
    result = asyncio.run(run_weekly_pipeline(week_id=wk))
    print(f'{wk}: {result.status} errors={result.errors}')
```

### 검증 (각 주차 × 2 locale = 6 rows 각각)

```python
for slug, locale in [
    ('2026-w13-weekly-digest', 'en'), ('2026-w13-weekly-digest-ko', 'ko'),
    ('2026-w14-weekly-digest', 'en'), ('2026-w14-weekly-digest-ko', 'ko'),
    ('2026-w15-weekly-digest', 'en'), ('2026-w15-weekly-digest-ko', 'ko'),
]:
    post = sb.table('news_posts').select('*').eq('slug', slug).eq('locale', locale).single().execute().data
    assert post['excerpt'], f'{slug} {locale}: excerpt empty'
    assert post['focus_items'] and len(post['focus_items']) == 3, f'{slug} {locale}: focus_items invalid'
    assert post['content_analysis'] is None, f'{slug} {locale}: content_analysis not null'
    gi = post['guide_items']
    assert gi.get('weekly_quiz_expert') and len(gi['weekly_quiz_expert']) == 3
    assert gi.get('weekly_quiz_learner') and len(gi['weekly_quiz_learner']) == 3
    assert gi.get('excerpt_learner'), f'{slug} {locale}: excerpt_learner empty'
```

### 브라우저 검증
- `/ko/news/2026-w13-weekly-digest-ko/` 방문
- 리스트 카드 요약 노출 확인
- 사이드바 focus_items 3개 노출 확인
- "핵심 분석" 섹션 없음 (content_analysis null — 이전 fix 반영)
- 퀴즈 3문제 렌더 확인

### 비용
- LLM: 3 × ~$0.15 = **~$0.45**
- 시간: ~8분

### 위험도
🟢 낮음. draft overwrite 패턴 두 번 이상 검증됨. 실패해도 단독 재시도 가능.

---

## Workstream E — 기존 daily JSONB 잔여 키 정리

A에서 frontend가 참조를 끊었지만, 기존 daily 포스트 `guide_items` JSONB에 NULL로 남은 dead 키들 일괄 제거.

### SQL

```sql
UPDATE news_posts
SET guide_items = guide_items
    - 'one_liner'
    - 'action_item'
    - 'critical_gotcha'
    - 'rotating_item'
WHERE guide_items ?| array['one_liner','action_item','critical_gotcha','rotating_item'];
```

### 영향
- 값은 모두 NULL이라 소실 없음
- 영향 row 수 예상: daily 포스트 전량 (~수백 건 추정)
- 프론트엔드 동작 변화 없음 (A에서 이미 참조 제거)

### 위험도
🟢 매우 낮음. JSONB key 단순 제거.

### 타이밍
A 완료 + 배포 확인 후. D와 병행 가능.

---

## Rollout Sequence

1. **로컬 개발** (순서 무관): A, B, C 구현
2. **단위 테스트 + 빌드 검증**:
   - Backend: `ruff check backend/` + `pytest tests/ -v`
   - Frontend: `npm run build`
3. **Commit 전략** — 한 PR, 여러 commit으로 분리:
   - `chore(cleanup): remove dead guide_items fields (one_liner/action_item/critical_gotcha/rotating_item)` (A backend)
   - `chore(cleanup): remove dead field render blocks + advisor UI` (A frontend)
   - `docs(vault): update schema docs to reflect removed guide_items fields` (A vault)
   - `fix(admin): add weekly option to post_type dropdown to prevent corruption` (B)
   - `feat(weekly): add excerpt + focus_items prompts matching daily pattern` (C prompts)
   - `feat(weekly): save excerpt + focus_items in pipeline, feed to KO adapter` (C pipeline)
4. **Push to main** — Railway/Vercel auto-redeploy
5. **Railway 배포 완료 확인** — commit hash vs deployed version
6. **Workstream D 실행** — W13/W14/W15 순차 백필 + 검증 스크립트
7. **Workstream E 실행** — JSONB cleanup SQL 1회
8. **최종 브라우저 검증** — W13/W14/W15 각 페이지 + admin weekly 편집 + daily admin advisor 패널

---

## Testing Strategy

### Automated (PR 전 완료)
- `ruff check backend/`
- `pytest tests/ -v` (기존 test_weekly_quiz_shuffle.py 포함 모두 pass)
- `npm run build` (frontend 0 error)

### Manual (PR 전)
- Admin edit 폼 열기 — daily 포스트: advisor 패널에 4필드 suggestion 버튼 사라짐 확인
- Admin edit 폼 열기 — weekly 포스트: post_type 드롭다운 'Weekly' 선택된 상태
- Admin edit 폼 열기 — research 포스트: 'Weekly' 옵션 회색/선택 불가

### Post-deploy (D + E 후)
- 브라우저: W13/W14/W15 페이지 3개, daily 포스트 샘플 1개
- DB 검증 스크립트 (Workstream D 참조)

---

## Risks & Mitigations

| 리스크 | 확률 | 완화책 |
|---|---|---|
| C의 KO adapter가 `weekly_quiz_ko` 마커와 `META` 마커 혼동 | 중 | 마커 텍스트 명확히 구분 + 프롬프트에서 둘 다 명시 + D 검증이 각 필드 체크 |
| A에서 `admin/edit/[slug].astro`의 advisor UI 삭제 시 레이아웃 깨짐 | 저 | 빌드 검증 + 수동 확인 체크리스트 |
| B의 `disabled` 속성이 보안 아닌 UI hint — 개발자가 DevTools로 해제 가능 | 저 | 실제 보안은 DB CHECK constraint가 담당 (이미 `post_type IN (...)`로 제한). UI는 실수 방지용 |
| D 재실행으로 quality score 변동 → auto_publish 기준 통과/미통과 변화 | 저 | 모두 draft 상태에서 재실행 → 상태 보존 |
| E의 SQL이 daily 외 포스트에도 적용될 가능성 | 저 | WHERE 조건 유지, 실행 전 `SELECT COUNT(*)` 먼저 |

---

## Out of Scope

- **Advisor 파이프라인 부활** — "dead field를 pipeline에서 다시 채우도록" 결정은 거부됨 (Q1에서 (a) 완전 제거 선택)
- **Weekly admin 풀 편집 UI** — week_numbers / week_tool / week_terms / weekly_quiz 편집 폼은 추후 필요 시 별도 plan (Q2에서 (a) 최소 선택)
- **docs/03_Backend_AI_Spec.md 업데이트** — CLAUDE.md 금지 조항
- **Auto-publish 자동화** — 기존 `AUTO-PUB-01` 태스크 별개

---

## Post-Implementation Actions

- `ACTIVE_SPRINT.md`에 신규 태스크 `CONSOL-A` ~ `CONSOL-E` 추가 (또는 mid-sprint ship 섹션에 완료 기록)
- 본 plan 문서를 `vault/90-Archive/2026-04/plans-completed/`로 이동

---

## References

- [[2026-04-19-weekly-content-v2]] — weekly quiz 도입 세션 (선행 plan)
- `project_weekly_editorial.md` (memory) — editorial direction (catch-up reader, 자동화 친화)
- [Daily pipeline_digest.py:382-466](../../../backend/services/pipeline_digest.py) — excerpt/focus_items daily 구현 참조
