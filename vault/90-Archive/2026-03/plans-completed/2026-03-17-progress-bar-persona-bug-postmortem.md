# 버그 포스트모템: ReadingProgressBar + 페르소나 탭

날짜: 2026-03-17

---

## Bug 1 — ReadingProgressBar 간헐적 미작동

### 증상
- 뉴스 / 블로그 / 용어집 상세 페이지에서 링크로 이동 시 프로그레스 바가 0%로 멈추거나 전혀 작동하지 않음
- 새로고침하면 정상 작동하는 경우도 있어 간헐적으로 발생

### 근본 원인 A — `astro:page-load` race condition (주요 원인)

Astro의 `<script>` (모듈 스크립트)는 Vite가 `<script type="module">`로 번들링하므로 **defer 실행**된다.
`astro:page-load` 이벤트는 DOMContentLoaded 직후에 발생하는데, 최초 페이지 로드 시
**`astro:page-load`가 모듈 스크립트 평가보다 먼저 실행**될 수 있다.

```
[최초 로드 시 타이밍]
DOMContentLoaded
  ↓
astro:page-load 발생  ← 이벤트 소실 (아직 리스너 미등록)
  ↓
<script type="module"> 평가
  → document.addEventListener('astro:page-load', initProgress) 등록  ← 너무 늦음
```

결과: `initProgress()` 최초 로드에서 호출 안 됨 → 프로그레스 바 0%로 고정.
이후 스크롤해도 스크롤 리스너가 등록되지 않아 업데이트 안 됨.

**참고**: 이미 `astro:page-load` 리스너 + 즉시 호출 이중 패턴을 쓰는 선례가 있음.
→ `NewsprintCategoryFilter.astro`: `initCategoryFilter()` 를 리스너 등록 후 즉시 직접 호출.

### 근본 원인 B — `rect.height === 0` 조기 종료 후 재시도 없음

`initProgress()` 마지막에 `updateProgress()` 를 즉시 호출한다.
이 시점에 브라우저 레이아웃이 완료되지 않았으면 `article.getBoundingClientRect().height === 0` →
함수가 조기 `return`. 이후 **스크롤 이벤트가 없으면 재시도하지 않음**.

결과: 이미지가 늦게 로드되거나 레이아웃 시프트가 있는 긴 아티클에서 바가 0%로 고정.

### 수정 (커밋: `fix(progress-bar): resolve race condition and layout retry`)

**파일**: `frontend/src/components/common/ReadingProgressBar.astro`

```diff
- document.addEventListener('astro:page-load', initProgress);
+ document.addEventListener('astro:page-load', initProgress);
+ initProgress();  // 최초 로드 race condition 해결
```

```diff
  function updateProgress() {
    const rect = article.getBoundingClientRect();
-   if (rect.height === 0) { ticking = false; return; }
+   if (rect.height === 0) { ticking = false; requestAnimationFrame(updateProgress); return; }
```

---

## Bug 2 — AI 뉴스 페르소나 전환 탭 미표시

### 증상
- 뉴스 상세 페이지에서 "초보자 / 학습자 / 전문가" 전환 탭이 전혀 표시되지 않음
- 파이프라인을 여러 번 돌려도 동일 현상

### 근본 원인 — Pydantic v2 동적 속성 무시

`backend/services/pipeline.py`의 `_generate_post()` 함수에서:

```python
# 버그 코드 (Pydantic v2가 _personas 속성을 무시)
fact_pack._personas = {}
# ... 루프 내에서 fact_pack._personas[key] = value 로 채웠지만 ...
# 함수 반환 전 fact_pack._personas 를 읽으면 항상 {}
```

**Pydantic v2**는 모델 인스턴스에 동적으로 추가한 underscore prefix 속성(`_personas`)을
자동으로 삭제한다 (validator/field로 선언되지 않은 동적 속성은 무시).

결과: 페르소나 생성 루프가 정상 실행되어도 `personas` 딕셔너리가 비어 있어
`content_beginner / content_learner / content_expert` 가 DB에 저장되지 않음.

반면 `_generate_digest()` 는 처음부터 **로컬 딕셔너리** `personas: dict = {}` 를 사용해 정상 작동.

### 프론트엔드 조건

```typescript
// newsDetailPage.ts:236
const hasPersonaContent = post.content_beginner || post.content_learner || post.content_expert;
// ...
// NewsprintArticleLayout.astro:125
const showPersonaSwitcher = personaHtmlMap && Object.keys(personaHtmlMap).length > 1;
```

2개 이상의 페르소나 콘텐츠가 있어야 탭 렌더링. 저장 실패 → `length === 0` → 탭 숨김.

### 수정

**백엔드**: `fact_pack._personas = {}` → `personas: dict[str, PersonaOutput] = {}` (로컬 변수)
커밋 `dd43b4a` (2026-03-16) 에서 수정 완료.

**프론트엔드**: 변경 불필요. 백엔드 수정 후 파이프라인 재실행하면 DB 채워지고 탭 자동 표시.

**기존 게시글 복구**: 파이프라인 재실행 필요. 재실행 전까지 기존 게시글에는 탭 미표시.

---

## 교훈

| 교훈 | 적용 범위 |
|------|-----------|
| Astro 모듈 스크립트 + `astro:page-load`: 리스너 등록 후 즉시 직접 호출 병행 | 모든 `astro:page-load` 패턴 |
| `getBoundingClientRect()` 결과가 0일 때 무조건 return 금지 — rAF 재시도 필요 | 레이아웃 의존 계산 |
| Pydantic v2: 동적 속성(`_` prefix) 무시 → 항상 로컬 변수 사용 | FastAPI/PydanticAI 전체 |
