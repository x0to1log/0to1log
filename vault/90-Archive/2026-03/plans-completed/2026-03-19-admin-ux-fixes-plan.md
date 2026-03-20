# Admin UX Fixes — 지금 + 나중에 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 에디터 Delete 버튼 Danger Zone 분리(지금) + INLINE-POPUP-01 한국어 매칭 최종 검증(지금) + 나중에 할 Admin P2 개선 및 COMMUNITY-01 계획

**Architecture:**
- Delete 버튼: 3개 에디터의 topbar에서 분리 → 에디터 하단 Danger Zone 섹션으로 이동, confirm() 가드 강화
- INLINE-POPUP-01: `rehypeHandbookTerms.ts` 정규식 최종 검증 + `sanitizeSchemaWithTerms` data-* 속성 허용 확인
- 나중에: COMMUNITY-01 설계/구현, Admin P2(에디터 구조 통일, 필터 UX)

**Tech Stack:** Astro v5, TypeScript, rehype, global.css (`.admin-btn-danger`, `.admin-danger-zone`)

---

## 지금 작업 (NOW)

---

## Chunk 1: Delete 버튼 Danger Zone 분리 `[EDITOR-DANGER-01]`

### 대상 파일
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro` — topbar HTML, danger zone HTML, JS handler
- Modify: `frontend/src/pages/admin/edit/[slug].astro` (news editor) — 동일
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro` — 동일
- Modify: `frontend/src/styles/global.css` — `.admin-danger-zone` 스타일 추가

### 현재 상태 파악

현재 3개 에디터 모두 topbar right에 Delete 버튼이 Publish 바로 옆에 있음:

```astro
<!-- blog editor line 147-151, news editor line 134-137, handbook editor line 103-106 -->
<button id="btn-publish-draft" class="admin-btn admin-btn-primary">Publish</button>
{!isNew && <button id="btn-delete" class="admin-btn-danger">Delete</button>}
```

### Task 1: global.css — danger zone 스타일 추가

- [ ] **Step 1: `global.css` 읽기** — `.admin-btn-danger` 스타일 위치 확인 (약 line 3588)

- [ ] **Step 2: danger zone 스타일 추가**

```css
/* Danger zone — 에디터 하단 */
.admin-danger-zone {
  margin-top: 3rem;
  padding: 1rem 1.25rem;
  border: 1px solid rgba(168, 82, 75, 0.25);
  border-radius: 6px;
  background: rgba(168, 82, 75, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.admin-danger-zone__label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}
.admin-danger-zone__label strong {
  display: block;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.15rem;
}
```

위치: `.admin-btn-danger:hover {}` 블록 바로 아래에 추가.

- [ ] **Step 3: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: 0 errors

---

### Task 2: Blog 에디터 — Delete 분리

파일: `frontend/src/pages/admin/blog/edit/[slug].astro`

- [ ] **Step 1: 현재 topbar Delete 버튼 제거**

변경 전 (line ~150):
```astro
<button id="btn-publish-draft" class="admin-btn admin-btn-primary" type="button">Publish</button>
{!isNew && <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>}
```

변경 후:
```astro
<button id="btn-publish-draft" class="admin-btn admin-btn-primary" type="button">Publish</button>
```

- [ ] **Step 2: 에디터 콘텐츠 영역 하단에 danger zone 추가**

에디터 폼이 끝나는 지점(`</div> <!-- admin-editor-content 닫힘 -->`) 직전에:
```astro
{!isNew && (
  <div class="admin-danger-zone">
    <div class="admin-danger-zone__label">
      <strong>Danger Zone</strong>
      이 글을 영구 삭제합니다. 복구할 수 없습니다.
    </div>
    <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>
  </div>
)}
```

Note: `id="btn-delete"`는 유지 — JS 핸들러가 이 ID를 찾음.

- [ ] **Step 3: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 3: News 에디터 — Delete 분리

파일: `frontend/src/pages/admin/edit/[slug].astro`

- [ ] **Step 1: topbar Delete 버튼 제거** (line ~137)

변경 전:
```astro
<button id="btn-publish-draft" class="admin-btn admin-btn-primary" type="button">Publish</button>
{!isNew && <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>}
```

변경 후:
```astro
<button id="btn-publish-draft" class="admin-btn admin-btn-primary" type="button">Publish</button>
```

- [ ] **Step 2: 에디터 하단 danger zone 추가**

`admin-editor-content` div 닫히기 전, form 끝난 직후:
```astro
{!isNew && (
  <div class="admin-danger-zone">
    <div class="admin-danger-zone__label">
      <strong>Danger Zone</strong>
      이 글을 영구 삭제합니다. 복구할 수 없습니다.
    </div>
    <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>
  </div>
)}
```

- [ ] **Step 3: 빌드 확인**

---

### Task 4: Handbook 에디터 — Delete 분리

파일: `frontend/src/pages/admin/handbook/edit/[slug].astro`

- [ ] **Step 1: topbar Delete 버튼 제거** (line ~106)

변경 전:
```astro
<button id="btn-publish" class="admin-btn admin-btn-primary" type="button">Publish</button>
{term && <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>}
```

변경 후:
```astro
<button id="btn-publish" class="admin-btn admin-btn-primary" type="button">Publish</button>
```

- [ ] **Step 2: 핸드북 에디터는 form 기반이므로 form 끝나는 지점 바로 뒤에 danger zone 추가**

`</form>` 태그 바로 뒤:
```astro
{term && (
  <div class="admin-danger-zone">
    <div class="admin-danger-zone__label">
      <strong>Danger Zone</strong>
      이 용어를 영구 삭제합니다. 복구할 수 없습니다.
    </div>
    <button id="btn-delete" class="admin-btn-danger" type="button">Delete</button>
  </div>
)}
```

- [ ] **Step 3: 빌드 확인**

---

### Task 5: 전체 빌드 + 수동 검증

- [ ] **빌드**
```bash
cd frontend && npm run build 2>&1 | grep -E "error|warning|built" | tail -10
```

- [ ] **수동 체크리스트:**
  - [ ] Blog 에디터 열기 → topbar에 Delete 없음 확인
  - [ ] 페이지 스크롤 하단 → Danger Zone 박스 + Delete 버튼 확인
  - [ ] Delete 클릭 → confirm 다이얼로그 (JS 핸들러에 이미 구현됨) → 취소 시 삭제 안 됨
  - [ ] News 에디터, Handbook 에디터 동일 확인
  - [ ] 신규 아이템 (`isNew=true`) → Danger Zone 없음 확인

- [ ] **커밋**
```bash
git add frontend/src/pages/admin/blog/edit/[slug].astro \
        frontend/src/pages/admin/edit/[slug].astro \
        frontend/src/pages/admin/handbook/edit/[slug].astro \
        frontend/src/styles/global.css
git commit -m "feat: move Delete button to danger zone in all 3 editors"
```

---

## Chunk 2: INLINE-POPUP-01 — 한국어 매칭 검증 및 수정

### 현재 상태

`frontend/src/lib/rehypeHandbookTerms.ts` (line 33-36):
```typescript
const pattern = new RegExp(
  `(?<![a-zA-Z\\uAC00-\\uD7AF])(${escaped.join('|')})(?![a-zA-Z])`,
  'gi',
);
```

- lookbehind: 한국어 포함 ✓
- lookahead: ASCII 알파벳만 (`a-zA-Z`) — 한국어 제외 ← 부분적

`frontend/src/lib/markdown.ts` (line 35-41):
```typescript
const sanitizeSchemaWithTerms = {
  ...sanitizeSchema,
  attributes: {
    ...sanitizeSchema.attributes,
    span: [...(sanitizeSchema.attributes?.span || []), 'dataSlug', 'dataTerm'],
  },
};
```
`dataSlug`, `dataTerm` → hast property name 형식 (올바름)

### Task 6: 정규식 lookahead에 한국어 추가

lookahead가 한국어 다음에 오는 경우를 처리하지 않음. 예: "에이전트모델" → "에이전트"가 잘못 매칭될 수 있음.

단, 한국어 조사("를", "이", "가" 등)가 term 바로 뒤에 오는 경우 이것도 한국어 문자이므로 lookahead에 한국어를 추가하면 조사 앞 term도 매칭 안 됨 → 오히려 더 깨짐.

**올바른 접근:** lookahead는 현재 상태 유지 (한국어 다음 매칭 허용). 대신 lookbehind + lookahead 조합이 실제로 동작하는지 확인.

- [ ] **Step 1: 간단한 unit test 작성으로 regex 동작 검증**

`frontend/src/lib/__tests__/rehypeHandbookTerms.test.ts` 생성:

```typescript
import { describe, it, expect } from 'vitest';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkRehype from 'remark-rehype';
import rehypeStringify from 'rehype-stringify';
import rehypeHandbookTerms, { type TermsMap } from '../rehypeHandbookTerms';

async function render(md: string, termsMap: TermsMap): Promise<string> {
  const processor = unified()
    .use(remarkParse)
    .use(remarkRehype)
    .use(rehypeHandbookTerms(termsMap))
    .use(rehypeStringify);
  return String(await processor.process(md));
}

const testMap: TermsMap = new Map([
  ['에이전트', { slug: 'agent', term: 'Agent' }],
  ['딥러닝', { slug: 'deep-learning', term: 'Deep Learning' }],
  ['ai', { slug: 'ai', term: 'AI' }],
]);

describe('rehypeHandbookTerms', () => {
  it('공백 뒤 한국어 용어 매칭', async () => {
    const html = await render('에이전트가 작동합니다.', testMap);
    expect(html).toContain('class="handbook-term"');
    expect(html).toContain('data-slug="agent"');
  });

  it('문단 시작 한국어 용어 매칭', async () => {
    const html = await render('딥러닝은 기계학습의 한 방법입니다.', testMap);
    expect(html).toContain('data-slug="deep-learning"');
  });

  it('영어 대소문자 매칭', async () => {
    const html = await render('AI 모델을 사용합니다.', testMap);
    expect(html).toContain('data-slug="ai"');
  });

  it('조사 없이 끝나는 경우', async () => {
    const html = await render('사용하는 에이전트', testMap);
    expect(html).toContain('data-slug="agent"');
  });

  it('첫 번째 등장만 마킹 (중복 제외)', async () => {
    const html = await render('에이전트와 에이전트를 비교합니다.', testMap);
    const count = (html.match(/data-slug="agent"/g) || []).length;
    expect(count).toBe(1);
  });
});
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**
```bash
cd frontend && npx vitest run src/lib/__tests__/rehypeHandbookTerms.test.ts 2>&1
```

Note: 테스트가 모두 통과하면 regex는 이미 올바르게 동작 중. 실패하는 케이스를 기준으로 fix.

- [ ] **Step 3: 실패 케이스 있을 경우 regex 수정**

한국어 term이 매칭 안 될 경우:
- lookbehind에 Korean 범위가 있으면 공백 없이 붙은 이전 텍스트가 있을 때 막힘 → 정상 동작
- 실제 문제라면 lookahead에서 Korean 조사를 명시적으로 허용 (현재 이미 허용됨)
- **sanitize 문제 의심 시**: `sanitizeSchemaWithTerms`에서 `'dataSlug'` → `'data-slug'`로 변경 시도

- [ ] **Step 4: 테스트 전체 통과 확인**
```bash
cd frontend && npx vitest run src/lib/__tests__/rehypeHandbookTerms.test.ts 2>&1
```
Expected: all pass

- [ ] **Step 5: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 6: 커밋**
```bash
git add frontend/src/lib/__tests__/rehypeHandbookTerms.test.ts \
        frontend/src/lib/rehypeHandbookTerms.ts
git commit -m "test: verify INLINE-POPUP-01 Korean term matching + fix if needed"
```

- [ ] **Step 7: ACTIVE_SPRINT 업데이트**
  - `INLINE-POPUP-01` 체크 `[x]` + 상태 `done` 으로 변경
  - `Current Doing` 표 업데이트

---

## 나중에 작업 (LATER)

> 아래 계획은 우선순위 낮음. 지금 작업 완료 후 별도 스프린트에서 진행.

---

## Chunk 3: COMMUNITY-01 — 커뮤니티 반응 수집

**언제:** INLINE-POPUP-01 완료 후, DIGEST-03 기반 위에서

**목적:** 선정된 뉴스 상위 2-3건에 대해 Reddit/HN 커뮤니티 반응을 수집하여 다이제스트 컨텍스트에 추가

**파일:**
- Modify: `backend/app/pipeline/news_collection.py` — `collect_community_reactions()` 함수 추가
- Modify: `backend/app/pipeline/pipeline.py` — 다이제스트 생성 전 커뮤니티 반응 수집 단계 추가
- Modify: `backend/app/pipeline/prompts_news_pipeline.py` — 다이제스트 프롬프트에 reactions 컨텍스트 주입

**핵심 의사결정 (구현 전 결정 필요):**
- 데이터 소스: Tavily search ("site:reddit.com {title}") vs HN Algolia API vs 둘 다
- 비용 기준: 상위 몇 건까지 수집할지 (2건 권장, API 비용 고려)
- 저장 방식: `news_posts` 테이블에 JSON 컬럼 추가 vs 별도 테이블

**구현 스케치:**
```python
async def collect_community_reactions(title: str, url: str) -> dict:
    """Tavily로 Reddit/HN 반응 검색 → LLM 요약"""
    search_results = await tavily_client.search(
        query=f'site:reddit.com OR site:news.ycombinator.com "{title}"',
        max_results=5,
    )
    if not search_results.results:
        return {}
    # gpt-4o-mini로 반응 요약
    summary = await summarize_reactions(search_results.results, title)
    return {"summary": summary, "sources": [r.url for r in search_results.results[:3]]}
```

**완료 기준:** 다이제스트에 커뮤니티 반응 요약 포함 + 비용 기록

---

## Chunk 4: Admin P2 — 에디터 구조 개선

**언제:** 기존 기능 안정화 후. 우선순위: P2 (중요하지만 긴박하지 않음)

**목적:** 3개 에디터(blog/news/handbook) 정보 구조 부분적 통일

**접근:** 완전한 통일 대신 공통 topbar 컴포넌트 추출

**파일:**
- Create: `frontend/src/components/admin/EditorTopbar.astro` — 공통 topbar
- Modify: 3개 에디터 — EditorTopbar 컴포넌트 사용

**핵심 props:**
```typescript
interface Props {
  backUrl: string;
  backLabel: string;
  status: string;
  isNew: boolean;
  contentType: 'blog' | 'news' | 'handbook';
  publishBtnId: string;
}
```

**완료 기준:** 3개 에디터 topbar가 동일한 컴포넌트에서 렌더링됨

---

## Chunk 5: Admin P2 — 필터 UX 개선

**언제:** P2, 나중에

**목적:** 리스트 페이지(news/blog/handbook) 필터 UI 통일 — 현재 각 페이지마다 상이

**파일:**
- Create: `frontend/src/components/admin/ListFilter.astro` — 공통 필터 컴포넌트
- Modify: 3개 리스트 페이지

---

## Chunk 6: PROMPT-AUDIT-01

**설계 참조:** `vault/09-Implementation/plans/2026-03-18-prompt-audit-fixes.md`

**구현 스코프:**
- P0: URL hallucination 방지, citation-소스 매핑
- P1: 토큰 비효율 제거, few-shot 예시
- P2: 일관성, 반복 제거

**파일:** `backend/app/pipeline/prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`

---

## 의존성 순서

```
[지금]
EDITOR-DANGER-01 (Delete 버튼 분리) — 독립 ✓
INLINE-POPUP-01 검증 — 독립 ✓

[나중]
COMMUNITY-01 → DIGEST-04 (프론트엔드 검증)
PROMPT-AUDIT-01 — 독립
Admin P2 개선 — 독립
WEEKLY-01 (COMMUNITY-01 안정화 후)
AUTOPUB-01 (퀄리티 데이터 축적 후)
```
