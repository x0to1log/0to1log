# 홈페이지 리디자인 — 설계 스펙

> Status: Approved (2026-03-19)
> Pattern: Split Hero + 계층화된 콘텐츠 섹션

## 배경 및 목적

현재 홈페이지는 뉴스·용어집·블로그 섹션이 같은 무게로 나열되어 있어 "이 사이트가 뭘 하는 곳인지"가 첫눈에 들어오지 않음. 신규 방문자에게 가치 제안(what / who / why / CTA)을 명확히 전달하는 구조로 개편.

## 현재 구조 (변경 전)

```
Section A: HomeMasthead (다크 브랜드 헤더 — 제목·날짜·스태프 라인)
Hero:       HomeHeroCard (news[0])
Section B:  Latest AI News (HomeNewsCard ×3)
Section C:  Glossary Spotlight (HomeTermCard ×6)
Section D:  From the Blog (BlogFeaturedCard + 리스트)
Section E:  Featured AI Products (HomeProductCard ×n)
Section F:  처음 읽는 분께 / Start Here (하드코딩 4-카드)
```

## 변경 후 구조

```
[1] SplitHero (HomeMasthead + HomeHeroCard 를 대체하는 새 컴포넌트)
[2] Latest AI News (기존 Section B — 헤드라인 1개 크게 + 서브 3개로 개선)
[3] Glossary | AI Products (2열 나란히 — 기존 Section C + E 재배치)
[4] From the Blog (기존 Section D 유지)
[5] Start Here → 제거 (Section F: Hero에 가치제안 + CTA가 들어가므로 중복)
```

---

## 설계 상세

### [1] SplitHero 컴포넌트 (`HomeSplitHero.astro`)

**역할**: 기존 `HomeMasthead`와 `HomeHeroCard`를 합쳐서 대체하는 신규 컴포넌트.
`ko/index.astro`에서 `HomeMasthead` + `HomeHeroCard` import를 제거하고 `HomeSplitHero`로 교체.

**레이아웃**: 2열 (left `1.2fr` · right `1fr`), 모바일에서 세로 스택 (왼쪽 copy 먼저, 오른쪽 snapshot 그 아래)

**배경**: 다크 (`#1a1a2e`) → CSS 토큰 `--color-hero-bg`로 추가 (`global.css` `@theme` 블록). 라이트/다크/핑크 테마 모두 동일 값 적용 (Hero는 항상 다크).

#### 좌측 — 가치 제안 + CTA
- 브랜드명: `0TO1LOG` (소형 letter-spacing 캡션, 섹션 상단)
- Audience kicker: "AI를 따라가고 싶은 개발자·기획자를 위한" (소형, muted)
- 헤드카피 (대형 bold):
  > "AI 뉴스 읽고, 용어 쌓고, 함께 해석하는 곳"
- 서브카피: "빠르게 바뀌는 AI 흐름을 구독하고, 모르는 용어는 즉시 찾고, 내 아카이브를 쌓는 플랫폼" (소형, muted)
- CTA 버튼 2개:
  - Primary: `AI 뉴스 읽기 →` (흰 배경, 검은 텍스트)
  - Secondary: `용어집 보기` (border-only, muted)

#### 우측 — Today's snapshot
- "TODAY" 레이블 (tiny, muted)
- 오늘의 헤드라인 카드 (`news[0]` — `getHomePageData()`에서 가져온 값 재사용, 추가 쿼리 없음)
- "TRENDING TERMS" 레이블
- 트렌딩 용어 카드 2개: `is_favourite = true` 기준 상위 2개 (기존 `terms` 배열 앞 2개 재사용)
  - 데이터 없으면 섹션 전체 숨김

**Props**:
```ts
interface Props {
  locale: 'ko' | 'en';
  heroNews: NewsArticle | null;
  trendingTerms: HandbookTerm[];
}
```

---

### [2] Latest AI News

- 기존 Section B 구조 유지, 레이아웃만 개선
- 섹션 헤더: `LATEST AI NEWS` + `전체 보기 →` 링크 (기존 `HomeSectionHeader` 재사용)
- **헤드라인 카드** (`news[0]` — Hero와 동일 데이터, 별도 쿼리 없음): 기존 `HomeHeroCard`를 섹션 내부로 이동하거나, `HomeNewsCard`에 `featured` prop 추가
- **서브 카드** 3개 (`news[1..3]`): 기존 `HomeNewsCard` 재사용

> **참고**: 현재 `HomeHeroCard`는 섹션 밖 단독 렌더링이었으나, 리디자인 후에는 Section [2] 내부로 편입됨.

---

### [3] Glossary | AI Products (2열)

기존 Section C (Glossary)와 Section E (AI Products)를 한 섹션으로 합쳐서 나란히 배치.

**레이아웃**: `display: grid; grid-template-columns: 1fr 1fr;` (구분선으로 좌우 분리)

#### 좌 — Glossary
- 섹션 헤더: `GLOSSARY` + `전체 →` (`HomeSectionHeader` 재사용)
- `HomeTermCard` 3개 (`terms[0..2]` — 기존 `is_favourite = true` 순 배열 재사용)

#### 우 — AI Products
- 섹션 헤더: `AI PRODUCTS` + `전체 →` (`HomeSectionHeader` 재사용)
- `HomeProductCard` 3개 (`featuredProducts[0..2]` — 기존 배열 재사용)
- 기존 `HomeProductCard`의 로고 플레이스홀더 동작 유지 (logoUrl 없으면 이름 첫 글자 박스)

---

### [4] From the Blog

기존 Section D 구조 그대로 유지.
- `BlogFeaturedCard` (blog[0]) + 리스트 (blog[1..3])
- 데이터 없으면 섹션 전체 숨김 (기존 조건부 렌더링 유지)

---

### [5] Start Here 제거

기존 Section F (`home-section home-start-here`)는 삭제.
- 이유: 새 SplitHero에 가치제안 + CTA가 포함되므로 중복
- `global.css`의 `.home-start-here*` 셀렉터도 함께 제거

---

## 데이터 요구사항

기존 `getHomePageData(locale)` 반환값을 그대로 활용. 추가 쿼리 없음.

| 섹션 | 데이터 변수 | 항목 수 | 비고 |
|------|-------------|---------|------|
| Hero 오늘 뉴스 | `news[0]` | 1 | Hero와 Section B가 동일 데이터 공유 |
| Hero 트렌딩 용어 | `terms[0..1]` | 2 | `is_favourite = true` 기준 (기존 쿼리 그대로) |
| Latest News 헤드라인 | `news[0]` | 1 | 추가 쿼리 없음, Hero와 동일 변수 |
| Latest News 서브 | `news[1..3]` | 3 | 기존 `moreNews` 변수 그대로 |
| Glossary | `terms[0..2]` | 3 | 기존 `terms` 배열 앞 3개 |
| AI Products | `featuredProducts[0..2]` | 3 | 기존 배열 앞 3개 |
| Blog | `blog[0..3]` | 1+3 | 기존 `featuredBlog` + `recentBlog` |

---

## 구현 파일

| 파일 | 변경 유형 |
|------|-----------|
| `frontend/src/components/home/HomeSplitHero.astro` | 신규 생성 |
| `frontend/src/pages/ko/index.astro` | 수정 (import 교체, 섹션 재배치) |
| `frontend/src/pages/en/index.astro` | 수정 (동일) |
| `frontend/src/styles/global.css` | 수정 (CSS 토큰 추가, `.home-start-here*` 제거) |
| `frontend/src/components/home/HomeMasthead.astro` | 삭제 또는 미사용 (SplitHero로 대체) |
| `frontend/src/components/home/HomeHeroCard.astro` | Section B로 편입, 또는 `HomeNewsCard featured` prop으로 통합 |

---

## 비고

- `en/index.astro`는 `ko/index.astro`와 동일 구조 — 동일 변경 적용
- Hero 배경 `#1a1a2e`는 `--color-hero-bg` 토큰으로 추가, 테마 무관 고정값
- 블로그 섹션 레이아웃은 3-column 그리드로 변경하지 않음 — 기존 `BlogFeaturedCard + 리스트` 유지
- `HomeMasthead`의 삭제 여부는 구현 단계에서 결정 (다른 페이지에서 사용 여부 확인 필요)
