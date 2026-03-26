# AI 제품 찜하기(Likes) 기능 설계

**날짜:** 2026-03-19
**상태:** 대기 중 (구현 예정)
**우선순위:** 제품 데이터 보강 완료 후 진행 권장
**범위:** DB + Backend + Frontend (인증 연동)

---

## 기능 개요

로그인한 사용자가 AI 제품에 하트(♥)를 눌러 찜하고, "나의 서재"에서 찜한 제품 목록을 확인할 수 있다.

---

## DB 변경

### 1. `ai_product_likes` 테이블 신규 생성

```sql
CREATE TABLE ai_product_likes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  product_id  uuid NOT NULL REFERENCES ai_products(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, product_id)
);
```

- `UNIQUE (user_id, product_id)` — 중복 찜 방지 (upsert 패턴 가능)

### 2. RLS 정책

```sql
ALTER TABLE ai_product_likes ENABLE ROW LEVEL SECURITY;

-- 자신의 찜만 조회
CREATE POLICY "user can read own likes"
  ON ai_product_likes FOR SELECT
  USING (auth.uid() = user_id);

-- 자신의 찜만 추가
CREATE POLICY "user can insert own likes"
  ON ai_product_likes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- 자신의 찜만 삭제
CREATE POLICY "user can delete own likes"
  ON ai_product_likes FOR DELETE
  USING (auth.uid() = user_id);
```

### 3. `ai_products.like_count` 자동 업데이트 트리거

```sql
CREATE OR REPLACE FUNCTION update_product_like_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE ai_products SET like_count = like_count + 1 WHERE id = NEW.product_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE ai_products SET like_count = GREATEST(like_count - 1, 0) WHERE id = OLD.product_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_product_like_count
AFTER INSERT OR DELETE ON ai_product_likes
FOR EACH ROW EXECUTE FUNCTION update_product_like_count();
```

### 4. 마이그레이션 파일

`supabase/migrations/00026_ai_product_likes.sql`

---

## API (Supabase 직접 호출 방식)

별도 FastAPI 엔드포인트 없이 **Supabase 클라이언트를 프론트엔드에서 직접 호출**.
RLS가 인증을 보장하므로 백엔드 추가 불필요.

### 찜 추가

```typescript
// upsert 패턴 — 이미 찜했으면 무시
const { error } = await supabase
  .from('ai_product_likes')
  .upsert({ user_id: userId, product_id: productId });
```

### 찜 취소

```typescript
const { error } = await supabase
  .from('ai_product_likes')
  .delete()
  .eq('user_id', userId)
  .eq('product_id', productId);
```

### 찜 여부 확인 (상세페이지 로드 시)

```typescript
const { data } = await supabase
  .from('ai_product_likes')
  .select('id')
  .eq('product_id', productId)
  .maybeSingle();
const isLiked = data !== null;
```

### 찜 목록 조회 (서재)

```typescript
const { data } = await supabase
  .from('ai_product_likes')
  .select(`
    product_id,
    ai_products (
      id, slug, name, name_ko, tagline, tagline_ko,
      logo_url, thumbnail_url, demo_media,
      pricing, platform, korean_support,
      primary_category, view_count, like_count, tags
    )
  `)
  .order('created_at', { ascending: false });
```

---

## 프론트엔드 변경

### 1. 하트 버튼 컴포넌트

**파일:** `frontend/src/components/products/ProductLikeButton.astro` (또는 순수 JS)

- 상세페이지 Hero 우측 컬럼에 배치 (사이트 방문 버튼 아래)
- 카드에는 썸네일 우측 하단에 작은 하트 아이콘 오버레이

**동작:**
1. 로그인 상태 확인 (`supabase.auth.getSession()`)
2. 비로그인 → 클릭 시 로그인 페이지로 이동 또는 toast 메시지
3. 로그인 → **Optimistic update** (즉시 UI 반영) → 서버 요청 → 실패 시 롤백

**UI 상태:**
- 기본: `♡ 찜하기` (outlined heart)
- 찜됨: `♥ 찜됨` (filled heart, accent color)
- 로딩: 버튼 비활성화

### 2. 상세페이지 (`ProductDetail.astro`)

Hero 오른쪽 컬럼, 사이트 방문 버튼 아래에 추가:

```html
<button class="product-like-btn" id="product-like-btn" data-product-id={product.id}>
  <svg>...</svg>
  <span id="like-label">찜하기</span>
  <span id="like-count">{product.like_count}</span>
</button>
```

서버사이드 초기 상태: 로그인 여부를 SSR에서 확인하여 초기 `isLiked` 상태 설정

### 3. 제품 카드 (`ProductCard.astro`)

썸네일 영역에 하트 아이콘 오버레이 (hover 시 표시, 찜된 경우 항상 표시):

```html
<button class="product-card-like" data-product-id={productId} aria-label="찜하기">
  <svg>...</svg>
</button>
```

카드에서 찜 상태는 **페이지 로드 후 JS로 일괄 확인** (N+1 쿼리 방지를 위해 한 번에 조회)

### 4. 찜 목록 일괄 로드 (제품 목록 페이지)

```typescript
// 로그인한 경우 페이지 로드 시 1번 쿼리로 전체 찜 목록 확인
const { data: likedIds } = await supabase
  .from('ai_product_likes')
  .select('product_id');

const likedSet = new Set(likedIds?.map(l => l.product_id));
// 각 카드의 data-product-id와 대조하여 하트 상태 적용
```

### 5. 나의 서재 (`/ko/library/`, `/en/library/`)

기존 서재 페이지에 "찜한 AI 도구" 섹션 추가:

```
나의 서재
├── 저장한 뉴스 (기존)
└── 찜한 AI 도구 (신규)
    ├── [ProductCard] ChatGPT
    ├── [ProductCard] Cursor
    └── ...
```

- `fetchLikedProducts(userId, locale)` 함수 추가 (`productsPage.ts`)
- 찜한 제품 없으면 "아직 찜한 도구가 없습니다" + 제품 탐색 링크

---

## 인증 연동

- Supabase Auth 기반 (기존 뉴스 북마크와 동일 패턴)
- 비로그인 사용자: 하트 버튼 표시하되 클릭 시 "로그인이 필요합니다" toast
- SSR에서 `locals.session` (또는 `Astro.locals.user`)으로 초기 로그인 상태 확인
- 찜 상태 초기값은 SSR에서 결정, 이후 변경은 클라이언트 JS

---

## 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `supabase/migrations/00026_ai_product_likes.sql` | 신규 | 테이블 + RLS + 트리거 |
| `frontend/src/components/products/ProductDetail.astro` | 수정 | 하트 버튼 추가 (Hero 우측) |
| `frontend/src/components/products/ProductCard.astro` | 수정 | 하트 오버레이 추가 |
| `frontend/src/lib/pageData/productsPage.ts` | 수정 | `fetchLikedProducts()` 함수 추가 |
| `frontend/src/scripts/productLike.ts` | 신규 | 찜 토글 로직 + Optimistic update |
| `frontend/src/pages/ko/library/index.astro` | 수정 | 찜한 제품 섹션 추가 |
| `frontend/src/pages/en/library/index.astro` | 수정 | 찜한 제품 섹션 추가 |
| `frontend/src/styles/global.css` | 수정 | `.product-like-btn`, `.product-card-like` CSS |
| `frontend/src/i18n/index.ts` | 수정 | 찜 관련 번역 키 추가 |

---

## 완료 기준

- [ ] 로그인 사용자가 상세페이지에서 하트 클릭 → 즉시 UI 반영 + DB 저장
- [ ] 같은 제품 다시 클릭 → 찜 취소 (toggle)
- [ ] 비로그인 클릭 → 로그인 유도 메시지
- [ ] 제품 목록 페이지에서 찜된 제품 카드에 하트 채워짐
- [ ] 나의 서재 → "찜한 AI 도구" 섹션에 목록 표시
- [ ] `like_count`가 찜/취소에 따라 실시간 증감
- [ ] 중복 찜 불가 (DB unique constraint)
- [ ] RLS — 다른 사용자의 찜 목록 접근 불가

---

## 구현 순서 권장

1. DB 마이그레이션 (테이블 + RLS + 트리거)
2. `productLike.ts` 스크립트 (찜 토글 핵심 로직)
3. 상세페이지 하트 버튼
4. 제품 카드 하트 오버레이 + 목록 페이지 일괄 상태 로드
5. 나의 서재 섹션 추가
