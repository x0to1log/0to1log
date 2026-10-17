# 용어 상세 재설계 (A 사전 표제어 + B 개념 지도) — Design Spec

**Status:** approved (2026-10-17)
**Mockup:** `.superpowers/brainstorm/term/term-v1.html` (A안 + B안 개념 지도)
**관련:** [[2026-10-16-news-article-briefing-design]], [[2026-10-17-handbook-index-shelves-design]]

## 배경

- 용어 상세(`/ko|en/handbook/[slug]/`)는 모든 용어 위에 "AI 용어집" 큰 마스트헤드와 킥커·subkicker 줄을 반복한다.
- 오른쪽 레일(검색, 저장·공유, 목차, 연관 개념, 최근 뉴스)이 본문 폭을 좁힌다.
- 시안 A(사전 표제어) / B(개념 지도) / C(학습 단계) 중 **A에 B의 개념 지도를 끝 블록으로 섞은 안**을 골랐다.
- 기사 상세(B+C)와 같은 "경로 줄 + 한 단 + 세로 액션 막대" 결을 따른다.

## 화면 구성 (위에서 아래로)

1. **경로 줄**: `NewsprintShell compact rail={false}`
   - 새 optional prop `crumbItems?: string[]`를 추가한다. 주면 crumb의 호수·날짜 대신 이 항목들을 ` · `로 렌더한다. 주지 않으면 기존 compact 동작(호수·날짜) 그대로다.
   - 용어 상세: `backHref="/{locale}/handbook/"`, `backLabel` = "AI 용어집" / "AI Glossary", `crumbItems` = 분야 라벨들(`getHandbookCategoryLabel`)
   - 기존 `.handbook-detail-meta` 분야 줄은 crumb로 옮기고 **용어 상세 마크업에서만** 제거한다.
     - CSS 규칙은 관리자 편집 미리보기(`admin/handbook/edit/[slug].astro`)가 쓰므로 유지한다.
   - EN 페이지의 번역 대기 안내(`isEnFallback`, `t.en['handbook.translationPending']`)는 경로 줄과 표제어 사이에 그대로 둔다.
2. **표제어 영역** `header.handbook-entry`
   - 작은 점 라벨: "표제어" / "Entry"
   - 표제어: `h1.handbook-detail-title`(클래스 유지 — 레벨 전환 스크립트가 스크롤 대상으로 쓴다). `term`, Hahmlet 700, 약 3rem(모바일 2.4rem)
   - 한글명: `span.handbook-detail-korean`(KO만, 현행처럼). Hahmlet 600, 약 1.5rem, 표제어와 같은 줄 baseline 정렬
   - 풀네임: `p.handbook-detail-subtitle`(`term_full`). Newsreader, muted
   - **품사 줄** `p.handbook-entry-gram`: `유형 · 쓰임 · 변화 정도`
     - 유형: `term_type` 라벨
     - 쓰임: `facet_intent` 각 값 라벨을 `·`로 연결
     - 변화 정도: `facet_volatility` 라벨
     - **`term_type`이 알려진 값(라벨이 있는 값)일 때만 줄을 렌더한다.** 그때 쓰임·변화 정도 중 값이 있는 것을 덧붙인다.
       - 마이그레이션 00047이 `facet_volatility` 기본값을 `'stable'`로 두므로, 미분류 용어에 "안정된 개념"만 단독으로 보이는 것을 막기 위해서다.
   - 아래쪽 2px 먹선
3. **뜻풀이 + 뉴스 용례**: `HandbookHeroCard`를 2단 구성으로 재스타일한다(scoped style 수정).
   - props는 그대로다(`backUrl`도 유지, 미사용 상태 그대로).
   - 판 제목 문자열만 "뉴스에서는 이렇게 쓰여요" / "How the news uses it"로 바꾼다.
   - 판 제목의 `role="heading" aria-level`은 `2`로 바꾼다(h1 다음 단계).
   - 왼쪽: 정의(현행 `**bold**` 변환 유지). 번호 매긴 ①② 뜻풀이는 하지 않는다(정의가 한 덩어리 문장이라서).
   - 오른쪽 먹색 판: "뉴스에서는 이렇게 쓰여요" / "How the news uses it" + `hero_news_context` 앞 3줄(현행 로직)
     - 다크 테마는 `--color-bg-tertiary` 면이다(홈 키워드 판과 같은 규칙).
     - 판이 비면 왼쪽 단이 전체 폭을 쓴다.
   - 모바일은 1단이다(판은 정의 아래).
4. **→ 함께 볼 말** `nav.handbook-xref` (`aria-label`)
   - 라벨 `<span>`(제목 태그 아님) "→ 함께 볼 말" / "→ See also" + 연관 용어 링크(표시 이름: KO `korean_name || term`, EN `term`)
   - 순서는 **`related_term_slugs`의 편집 순서**다(쿼리 결과를 이 순서로 재정렬).
   - 연관 용어가 없으면 현행 fallback(같은 분야 5개)을 쓰고 라벨은 "같은 분야" / "Same field"다. 둘 다 없으면 렌더하지 않는다.
5. **난이도 전환 + 본문**: 현행 마크업과 스크립트를 유지한다.
   - `.switcher-bar`, `.handbook-level-btn[data-level]`, `#level-data`, `#level-float`, `#handbook-body`
   - 용어 하이라이트·팝업, 코드 접기, 표 모두 유지
6. **액션(저장·공유)**: 레일 대신 본문 옆 인라인 `StickyReadingActions variant="term"`(placement 기본 inline)
   - 데스크톱 세로 막대, 모바일 하단 바. 마크업은 `NewsprintArticleLayout`과 같은 구조다.
     ```
     <div class="reading-actions-layout reading-actions-layout--article">
       <StickyReadingActions variant="term" ... />        ← 반드시 직접 자식, __body보다 앞
       <div class="reading-actions-layout__body">
         #handbook-body (newsprint-prose) …
         개념 지도 · 최근 뉴스 (prose 밖) …
         참고 자료 · reading-end · 학습 체크 · 피드백 · 관리자 · 이전/다음
       </div>
     </div>
     ```
   - 현재 용어 상세의 `.reading-actions-layout` 래퍼에 `--article` 수정자를 붙이고, 그 첫 자식으로 액션을 넣는다. CSS의 `>` 셀렉터와 `order`가 이 구조를 전제한다.
   - 북마크 훅 `[data-reading-action=bookmark][data-item-type=term]`, 공유 훅은 현행 그대로다.
7. **끝 블록**(본문 다음, 참고 자료 앞)
   - `.reading-actions-layout__body` 안, **`#handbook-body`·`.newsprint-prose` 바깥**에 둔다.
     - `#handbook-body`는 레벨 전환 때마다 `innerHTML`로 교체된다.
     - `handbook-popup.ts`가 `.newsprint-prose a[href*="/handbook/"]` 클릭을 가로챈다.
   - 섹션 제목은 `h2`다(개념 지도, 최근 뉴스에서).
   - **개념 지도 (B)** `section.handbook-concept-map`
     - 제목: "개념 지도" / "Concept map"
     - 서버 렌더 SVG(`viewBox` 고정, 폭 100%). 가운데 먹색 원 + 이 용어 이름, 둘레에 연관 용어 최대 6개
     - 노드 위치는 각도를 균등 분할해 순수 함수로 계산한다. 각 노드는 `<a href>`로 상세 링크다.
     - 관계 설명 텍스트는 없다(데이터 없음).
     - 연관(또는 같은 분야 fallback) 용어가 0개면 섹션을 렌더하지 않는다.
     - 접근성: SVG에 `role="img"`가 아닌 링크 그룹이다. 각 `<a>`에 `aria-label` = 용어 이름. 중심 원은 `aria-hidden`.
   - **최근 뉴스에서** `section.handbook-news-mentions`
     - 이 용어가 실제로 언급된 뉴스만 보여준다(현행 mentions 쿼리, 최대 5).
     - **언급이 없을 때 최신 뉴스 3개로 채우던 fallback은 제거**하고 섹션을 렌더하지 않는다.
     - 각 줄: 유형 라벨(`postTypeLabel`) + 제목 링크 + 날짜
8. 이후 현행 순서 그대로: 참고 자료(`HandbookReferences`) → `[data-reading-end]` → 학습 체크(`.handbook-action-bar[data-auth-only] > .learning-check[data-term-id]`) → 피드백 → 관리자 버튼(`data-admin-only`) → 이전/다음(`.handbook-bottom-nav`)

## 없애는 것

- 오른쪽 레일 전체(레일 검색 폼, `ReadingActionsRail`, `HandbookSectionNav`, `HandbookSideRail`)
  - `HandbookSectionNav`(목차)는 이 페이지 전용이므로 **삭제**한다. 전용 CSS `.handbook-toc*`도 삭제한다(grep 확인 후).
  - `HandbookSideRail`은 관리자 편집 페이지의 숨김 미리보기가 쓰므로 **유지**한다(용어 상세에서만 미사용).
  - `ReadingActionsRail`은 블로그가 쓰므로 유지한다.
- 모바일 sticky 검색(`.handbook-search-sticky--detail`)은 유지한다(데스크톱은 기존대로 숨김).
  - **데스크톱 용어 상세에는 용어 검색창이 없어진다.** 기사 상세와 같은 결정이다. 헤더의 "AI 용어집" 메뉴와 경로 줄의 back 링크로 용어집 첫 화면 검색에 닿는다.

## 데이터

- `HANDBOOK_DETAIL_PUBLIC_COLUMNS`에 `term_type, facet_intent, facet_volatility`를 추가한다(상수 사용 계약 유지).
- 연관 용어: 기존 `.in('slug', related_term_slugs)` 결과를 `related_term_slugs` 순서로 정렬한다. 순수 함수 `orderBySlugs(rows, slugs)`를 쓴다.
- 뉴스 언급
  - 기존 mentions 쿼리는 유지한다.
  - **fallback 최신 3개 쿼리와 대입은 제거**한다. 쿼리 1개 감소.
  - 반환 필드명은 현행을 따른다(구현 시 확인). 언급 없음은 빈 배열이다.
- **새 순수 모듈 `lib/handbookFacets.js`**
  - `termTypeLabel(locale, value)`: 13개 `TERM_TYPES`(backend `prompts_handbook_types.py` 기준 값) KO/EN 라벨. 모르는 값은 ''.
  - `intentLabel(locale, value)`: understand/compare/build/debug/evaluate와 DB에 실제 존재하는 operate/apply/defend까지 라벨을 둔다. 모르는 값은 ''.
  - `volatilityLabel(locale, value)`: stable/evolving/fast-changing
  - `entryGrammar(locale, { term_type, facet_intent, facet_volatility })`
    - `term_type` 라벨이 없으면 ''를 반환한다.
    - 있으면 유형 + (쓰임 라벨들 `·`) + 변화 정도 중 비어 있지 않은 것을 ` · `로 합친다.
- **새 순수 함수 `conceptMapNodes(count, { cx, cy, rx, ry })`** → 각 노드 `{x, y, anchor}`
  - 12시 방향부터 시계방향 균등 분할
  - 텍스트 앵커: 왼쪽 반은 end, 오른쪽 반은 start, 위아래 중앙은 middle
  - `lib/handbookFacets.js` 또는 별도 `lib/conceptMap.js`(구현 시 결정, 단위 테스트 필수)
- 캐시·user-neutral 정책 변경 없음. `publicTermIndex.ts`는 수정하지 않는다(다른 세션).

## 라벨 (KO / EN)

- **유형(term_type)**

  | 값 | KO | EN |
  |---|---|---|
  | foundational_concept | 기초 개념 | Foundational concept |
  | problem_failure_mode | 문제·실패 유형 | Failure mode |
  | model_algorithm_family | 모델·알고리즘 | Model / algorithm |
  | training_optimization_method | 학습·최적화 기법 | Training method |
  | retrieval_knowledge_system | 검색·지식 시스템 | Retrieval system |
  | system_workflow_pattern | 시스템·워크플로 패턴 | Workflow pattern |
  | data_storage_indexing_system | 데이터 저장·색인 | Data storage / indexing |
  | protocol_format_data_structure | 프로토콜·형식 | Protocol / format |
  | capability_feature_spec | 기능·사양 | Capability / feature |
  | metric_benchmark | 지표·벤치마크 | Metric / benchmark |
  | product_platform_service | 제품·플랫폼 | Product / platform |
  | library_framework_sdk | 라이브러리·프레임워크 | Library / framework |
  | hardware_runtime_infra | 하드웨어·인프라 | Hardware / infra |

  (backend `TERM_TYPES` 13개 전부다.)
- **쓰임(facet_intent)**: understand 이해할 때 / When learning, compare 비교할 때 / When comparing, build 만들 때 / When building, debug 고칠 때 / When debugging, evaluate 평가할 때 / When evaluating, operate 운영할 때 / When operating, apply 적용할 때 / When applying, defend 방어할 때 / When defending
- **변화 정도(facet_volatility)**: stable 안정된 개념 / Stable, evolving 변화 중인 개념 / Evolving, fast-changing 빠르게 바뀌는 개념 / Fast-changing
- **UI 문구**

  | 위치 | KO | EN |
  |---|---|---|
  | 표제어 라벨 | 표제어 | Entry |
  | 함께 볼 말 | → 함께 볼 말 | → See also |
  | 같은 분야 | → 같은 분야 | → Same field |
  | 개념 지도 | 개념 지도 | Concept map |
  | 최근 뉴스 | 최근 뉴스에서 | In recent news |
  | 판 | 뉴스에서는 이렇게 쓰여요 | How the news uses it |

## 스크립트 수정

- `initLevelSwitcher` 이중 바인딩 제거
  - 직접 호출과 `astro:page-load` 중 하나만 쓴다. 또는 `dataset.levelReady` 가드를 둔다.
  - `onSessionReady` 적용도 1회만 한다.
- 레벨 전환 시 스크롤 대상(`.handbook-detail-title`), `reading-content-changed` 발행은 유지한다.
- 목차 스크립트는 컴포넌트와 함께 사라진다.
- 조회수 RPC(`trackView`)가 첫 `[data-term-id]`를 읽는 동작은 그대로다.

## 컴포넌트

- 새 파일
  - `components/handbook/HandbookEntryHead.astro`: 표제어, 한글명, 풀네임, 품사 줄
  - `components/handbook/HandbookXref.astro`: 함께 볼 말
  - `components/handbook/HandbookConceptMap.astro`: SVG
  - `components/handbook/HandbookNewsMentions.astro`
- 수정
  - `NewsprintShell.astro`: `crumbItems`
  - `HandbookHeroCard.astro`: 2단 스타일, 다크 판
  - `pages/{ko,en}/handbook/[slug].astro`: 구성 교체, 레일 제거, 인라인 액션, 스크립트 가드
  - `lib/pageData/handbookDetailPage.ts`: 컬럼, 순서 정렬, fallback 뉴스 제거
- 삭제: `components/newsprint/HandbookSectionNav.astro`와 `.handbook-toc*` CSS

## 모바일 (≤767px)

- 순서: 경로 줄 → 표제어(2.4rem) → 품사 줄 → 정의 → 판 → 함께 볼 말(줄바꿈) → 난이도 → 본문 → 개념 지도(폭 100% 축소) → 최근 뉴스 → 참고 자료 … → 하단 액션 바
- 가로 넘침 0이어야 한다. 개념 지도 텍스트가 잘리지 않도록 `viewBox` 여백을 확보한다.

## 테스트

- **새 `handbook-facets.test.mjs`**
  - 라벨 맵 3종(알 수 없는 값은 '')
  - `entryGrammar` 결합·생략
  - `orderBySlugs`(누락 slug 무시, 순서 보존)
  - `conceptMapNodes`(개수, 12시 시작, 앵커 규칙, 1개·6개 경계)
- **새 `handbook-term-entry.test.cjs`**
  - ko/en 페이지: `compact`, `rail={false}`, `crumbItems`, 레일 컴포넌트 import 없음, `StickyReadingActions` 인라인 사용, 새 컴포넌트 4개 사용
  - `handbookDetailPage.ts`: 컬럼에 facets 3개, fallback 최신 뉴스 쿼리 없음, `orderBySlugs` 사용
  - Shell `crumbItems` 분기
  - 레벨 스위처 이중 바인딩 가드
  - 문구 KO/EN, 개념 지도 `<a` 노드와 `aria-label`
  - CSS: 표제어 크기, 품사 줄, 판 다크 규칙, 개념 지도 폭 100%, 모바일 1단
- **갱신**
  - `handbook-v2`
    - 메타 인라인 스타일 단언 → crumb 이동에 맞춰 갱신
    - `rule('.handbook-toc__title')` 단언 삭제(목차 CSS 삭제)
    - `rule('.handbook-detail-meta')` accent 단언 유지(CSS 유지)
    - `learning-check`·`level-data`·`onSessionReady`·`data-admin-only`·레벨 버튼 단언 유지
  - `detail-rail-actions-placement`: 용어 상세의 `<ReadingActionsRail` 단언을 인라인 액션으로 반대 단언한다. 블로그 단언은 유지한다.
  - `sticky-reading-actions-structure`: 59–60행의 handbook 두 페이지 `<ReadingActionsRail` 단언을 `<StickyReadingActions`와 `reading-actions-layout--article` 단언으로 바꾼다(테스트는 이미 다른 이유로 실패 중이므로 이름 기준 비교로 확인).
  - `public-detail-query-contract`: 컬럼 추가 반영(상수 사용 계약 유지)
  - 목차 컴포넌트를 읽는 테스트가 있으면 갱신하거나 삭제한다(grep).
- **유지 확인**: `public-error-cache-policy`, `reading-actions-layout-regression`, `reading-actions-editorial-subtle`, `issue-number-shell`, `hreflang-alt-slug`
- **검증 매트릭스**
  - 종이·순백·다크 × ≥1024px·375px × ko/en
  - 대상 용어: RRF(연관 4, 판 있음), 연관 없는 용어, 뉴스 언급 없는 용어
  - 직접 확인: 기초↔심화 전환(본문 교체·스크롤), 용어 팝업, 저장 버튼, 공유 메뉴, 개념 지도 노드 클릭 이동
  - 가로 넘침 0, 대비 검사
- 전체 테스트는 이름 기준으로 비교한다. 신규 FAIL은 0이어야 한다.

## 범위 밖

- 분야(category) 페이지
- 블로그 상세
- `publicTermIndex.ts`
- 뉴스 mentions 필터 이스케이프(`,(){`) 개선. 기존 이슈로 별도 후보다.
- `code-toggle` EN 라벨
