# 프론트엔드 개발 가이드

**스택:** Astro v5 + Tailwind CSS v4 + Vercel

상세 스펙: `docs/04_Frontend_Spec.md`

---

## Astro 규칙

- Astro v5 기본 출력 동작 유지. 필요시 페이지별 SSR opt-in 사용.
- `[slug].astro` 같은 동적 라우트에서 DB 기반 렌더링 필요할 때만 `export const prerender = false` 사용.
- `.astro` 파일에서 `client:load` 사용 금지. 대신 일반 `<script>` 블록 사용.
- `MainLayout.astro`에서 FOUC 방지: `<script is:inline>` 초기 실행.
- Astro 내장 i18n 라우팅 사용 금지. 로케일 구조는 `/en/`, `/ko/` 아래 명시적으로 유지.

---

## Tailwind v4

- `@tailwindcss/vite` 사용. `@astrojs/tailwind` 사용 금지.
- 테마 토큰은 `src/styles/global.css`에 `@theme`, `[data-theme]` CSS 변수로 유지.
- 지원 테마: `light` (기본), `dark`, `pink`.
- 폰트는 `global.css`에 정의된 `--font-*` CSS 변수 사용. 블로그 섹션은 IBM Plex Sans 별도 로드 가능.

---

## i18n (다국어)

- 영어(EN)가 정식 버전. `hreflang x-default`는 `/en/`로 지정.
- `/portfolio/`, `/admin/`은 로케일 중립적으로 유지.
- 번역은 `src/i18n/index.ts`에 저장.

---

## 네이밍

**공개 제품 라벨:**
- `AI News`
- `IT Blog`
- `Handbook`
- `Library`

**내부/관리자 라벨:**
- `News` (뉴스)
- `Blog` (블로그)
- `Handbook` (용어집)

---

## 보안

- `/api/revalidate`는 서버 전용. `REVALIDATE_SECRET` Bearer 검증 필수.
- 클라이언트 코드에서 직접 리밸리데이션 호출 금지.
- 프론트엔드에서 Supabase Service Role Key 사용 금지. 프론트엔드는 anon key만 사용.
- CSP는 미들웨어에서 동적 설정 (요청 nonce 포함). `script-src 'unsafe-inline'` 제거 유지.
- 모든 `<script is:inline>` 추가 시 `nonce={Astro.locals.cspNonce || ''}` 포함 필수.
- CSP 변경 후 렌더링된 HTML 검증 (소스 파일 아님). 모든 `<script>` 태그가 요청 nonce 포함 필요 (Astro 생성 모듈 스크립트 포함).
- `style-src 'unsafe-inline'` 허용 유지 (Astro 인라인 스타일, Milkdown용).
- `data-*` 속성으로 액세스 토큰을 DOM에 노출 금지. 관리 페이지는 서버 측 API 라우트 사용.

---

## SEO

- `Head.astro`는 `PUBLIC_SITE_URL` 기반 절대 canonical & hreflang URLs 생성.
- `astro.config.mjs` `site`는 `PUBLIC_SITE_URL`과 일치 유지.

---

## 관리자 에디터

- `.astro` 파일에서 `client:load` 사용 금지. 일반 `<script>` 블록 사용.
- 관리자 CSS는 `global.css`의 `.admin-*` 선택자 아래 유지.

---

## 빌드

```bash
cd frontend && npm run build   # 0 에러로 통과 필수
```

---

## 개발 워크플로우

### 로컬 실행

```bash
cd frontend
npm install
npm run dev
```

Astro 앱은 `http://localhost:4321`에서 실행됩니다.

### 코드 품질

```bash
npm run check        # Astro & TypeScript 타입 체크
npm run build        # 빌드 검증
npm run lint         # 린트 (설정되어 있으면)
```

---

## 라우팅

### 페이지 경로

```
src/pages/
├── [lang]/news/           AI News 뉴스 페이지
├── [lang]/handbook/       AI Handbook 용어집
├── [lang]/blog/           IT Blog 블로그
├── [lang]/products/       AI Products 제품
├── [lang]/library/        User Library 개인 라이브러리
├── portfolio/             포트폴리오 (로케일 중립)
└── admin/                 관리 대시보드 (로케일 중립)
```

---

## 컴포넌트 구조

```
src/components/
├── layouts/              페이지 레이아웃
│   ├── MainLayout.astro
│   ├── AdminLayout.astro
│   └── ...
├── sections/             섹션 (뉴스 카드, 용어 목록 등)
│   ├── NewsCard.astro
│   ├── GlossaryList.astro
│   └── ...
├── ui/                   재사용 가능한 UI 컴포넌트
│   ├── Button.astro
│   ├── Modal.astro
│   └── ...
└── ...
```

---

## 컴포넌트 패턴

### Astro 컴포넌트 (서버 렌더링)

```astro
---
// 로직
const props = Astro.props;
const data = await fetchData();
---

<div>
  <h1>{data.title}</h1>
</div>

<style>
  /* Astro가 스코핑된 CSS 생성 */
  h1 { color: blue; }
</style>
```

### 상호작용 필요 시 (클라이언트 사이드)

```astro
---
// 서버 로직
---

<div id="interactive">
  <!-- HTML -->
</div>

<script>
  // 클라이언트 JavaScript (일반 <script>, client:load 아님)
  document.getElementById('interactive').addEventListener('click', () => {
    console.log('Clicked');
  });
</script>
```

---

## 환경 변수

**필수 (`.env` 파일):**

```
PUBLIC_SITE_URL=https://0to1log.vercel.app
PUBLIC_SUPABASE_URL=https://xxx.supabase.co
PUBLIC_SUPABASE_ANON_KEY=eyJxxx...

FASTAPI_URL=http://localhost:8000
CRON_SECRET=your-secret-here
REVALIDATE_SECRET=your-secret-here
```

**선택사항:**
- `PUBLIC_GA4_ID` — Google Analytics 4 ID
- `PUBLIC_CLARITY_ID` — Microsoft Clarity ID

---

## 배포 (Vercel)

### 자동 배포

- `main` 브랜치 푸시 → Vercel 자동 배포
- Vercel 대시보드에서 배포 상태 확인

### 환경 변수

Vercel 프로젝트 설정에서 `.env` 값들을 환경 변수로 추가.

### 미리보기

- PR 생성 → 자동으로 미리보기 URL 생성
- 병합 전에 미리보기에서 검증

---

## 금지 패턴

### ❌ client:load 사용 금지

```astro
<!-- BAD -->
<MyComponent client:load />

<!-- GOOD -->
<MyComponent />
<!-- 필요하면 <script is:inline> 사용 -->
```

### ❌ hardcoded 환경 값

```astro
<!-- BAD -->
const url = "https://hardcoded.example.com";

<!-- GOOD -->
const url = import.meta.env.PUBLIC_SITE_URL;
```

### ❌ Service Key 노출

```ts
// BAD
export const supabaseKey = import.meta.env.SUPABASE_SERVICE_KEY;

// GOOD
// 프론트엔드는 PUBLIC_SUPABASE_ANON_KEY만 사용
export const supabaseKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
```

---

## 참고 자료

- **Astro 공식 문서:** https://docs.astro.build
- **Tailwind CSS v4:** https://tailwindcss.com/docs
- **Supabase 인증:** https://supabase.com/docs/auth
- **Vercel 배포:** https://vercel.com/docs
