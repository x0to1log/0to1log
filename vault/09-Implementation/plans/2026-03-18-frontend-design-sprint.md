# Frontend Design Sprint — UI/UX 품질 개선

> **생성:** 2026-03-18
> **목표:** UI/UX 감사 결과 기반 디자인 시스템 정교화 + 사용자 경험 개선
> **범위:** 프론트엔드 CSS/컴포넌트 품질 (기능 추가 X, 기존 디자인 다듬기 O)

---

## UI/UX 감사 결과 요약

| 영역 | 점수 | 핵심 이슈 |
|------|------|-----------|
| 타이포그래피 | **A+** | 변경 불필요. clamp() 기반 fluid, Playfair+Lora+Pretendard |
| 컬러 시스템 | **A+** | 변경 불필요. 4테마 모두 AAA+ 명암비 |
| 레이아웃 | **A** | 3-column 헤더, 2fr+1fr 본문 그리드 — 양호 |
| 모바일 반응형 | **A** | mobile-first, touch 최적화 — 양호 |
| 마이크로 인터랙션 | **A** | 뉴스프린트 필터, 150ms 통일 — 양호 |
| 접근성 | **A-** | 드롭다운 키보드 네비게이션 부재 |
| 컴포넌트 일관성 | **B+** | border-radius 혼재, hover 패턴 불일치, 버튼 사이즈 시스템 없음 |
| 스페이싱 | **B** | **최대 약점.** 토큰 없이 ad-hoc 값 난무 |
| CSS 아키텍처 | **B-** | 10,686줄 단일 파일, 분리 필요 |

---

## 개선 태스크

### Tier 1: Quick Win (높은 효과, 낮은 노력)

#### T1-1. Border-radius 토큰화
- **현재:** `0, 2, 3, 4, 6, 8px` 혼재 (체계 없음)
- **목표:** 3단계 토큰으로 통일
  ```css
  --radius-sm: 4px;   /* 배지, pill, 태그 */
  --radius-md: 8px;   /* 카드, 입력, 버튼 */
  --radius-lg: 12px;  /* 모달, 큰 섹션 */
  ```
- **작업:** global.css에서 border-radius 값을 토큰으로 교체
- **파일:** `frontend/src/styles/global.css`

#### T1-2. 카드 hover 패턴 통일
- **현재:** 카드마다 hover가 다름 (bg 변경, border 변경, title color만 변경)
- **목표:** 공통 hover 패턴 1개로 통일
  ```css
  [hover] → background: var(--color-bg-hover) + title color: var(--color-accent)
  ```
- **파일:** `frontend/src/styles/global.css`

#### T1-3. 터치 타겟 44px 보장
- **현재:** 필터 탭, 카테고리 pill 등 일부 요소가 44px 미만
- **목표:** 모든 인터랙티브 요소에 `min-height: 44px` 보장
- **파일:** `frontend/src/styles/global.css`

### Tier 2: Medium Effort (구조 개선)

#### T2-1. 스페이싱 토큰 시스템 도입
- **현재:** `0.35rem, 0.45rem, 0.65rem, 0.85rem` 등 ad-hoc 값
- **목표:** 4px 기반 스케일 토큰 정의 + 점진적 교체
  ```css
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --space-12: 3rem;    /* 48px */
  ```
- **접근:** 한 번에 전체 교체 X → 새 코드부터 토큰 사용, 기존은 점진적 교체
- **파일:** `frontend/src/styles/global.css`

#### T2-2. 버튼 사이즈 시스템
- **현재:** 페이지마다 padding 직접 지정
- **목표:** sm/md/lg 3단계 시스템
  ```css
  .btn-sm { padding: var(--space-1) var(--space-3); font-size: 0.8rem; }
  .btn-md { padding: var(--space-2) var(--space-4); font-size: 0.875rem; }
  .btn-lg { padding: var(--space-3) var(--space-6); font-size: 1rem; }
  ```
- **파일:** `frontend/src/styles/global.css`

#### T2-3. 드롭다운 키보드 네비게이션
- **현재:** 프로필 드롭다운에 화살표 키/Escape 미지원
- **목표:** WAI-ARIA Menu 패턴 적용 (ArrowUp/Down/Escape)
- **파일:** `frontend/src/components/Navigation.astro`

### ~~Tier 3: Long-term (구조적 리팩터 — 이번 스프린트 범위 외)~~ → 별도 스프린트

---

## 1차 스프린트 완료 (2026-03-18)

- [x] T1-1. Border-radius 토큰화 (~120개 값 교체)
- [x] T1-2. 카드 hover 패턴 통일 (accent-subtle + title accent)
- [x] T1-3. 터치 타겟 44px 보장 (theme/lang toggle, avatar, bookmark, code-copy)
- [x] T2-1. 스페이싱 토큰 시스템 도입 (--space-1~12)
- [x] T2-2. 버튼 사이즈 시스템 (--sm/--lg + 마이크로 버튼 상향)
- [x] T2-3. 드롭다운 키보드 네비게이션 (Arrow/Escape + aria-expanded)

---

## 2차 UI/UX 감사 결과 (2026-03-18)

> 1차에서 해결되지 않은 39개 이슈 중 우선순위 높은 10개를 2차 스프린트로 등록.

### Phase A: Quick Fix (CSS 수정만)

#### T4-1. Z-index 스케일 정리
- **현재:** 1~9999 무질서 (9999, 1000, 900, 200, 120, 105, 100, 89 등 충돌)
- **목표:** 10단계 체계: 100(float) → 200(sticky) → 300(header) → 400(toolbar) → 500(search) → 600(popup) → 700(dropdown) → 800(overlay) → 900(modal) → 1000(toast)
- **파일:** `frontend/src/styles/global.css`

#### T4-2. select hover + focus 보완
- **현재:** `.admin-select:hover` 없음, focus에 box-shadow 없음
- **목표:** hover border-color + focus box-shadow 추가
- **파일:** `frontend/src/styles/global.css`

#### T4-3. admin-feedback-dismiss focus-visible 추가
- **현재:** hover만 있고 :focus-visible 없음
- **파일:** `frontend/src/styles/global.css`

#### T4-4. 테마 전환 smooth transition
- **현재:** 즉시 snap
- **목표:** `background-color 0.2s, color 0.2s` 전환 (prefers-reduced-motion 존중)
- **파일:** `frontend/src/styles/global.css`

### Phase B: 컴포넌트 수준

#### T4-5. Save 버튼 로딩 spinner
- **현재:** "Saving..." 텍스트만
- **목표:** 텍스트 + inline spinner SVG (기존 `ai-spin` 애니메이션 재활용)
- **파일:** 어드민 에디터 공통 패턴

#### T4-6. 비밀번호 인라인 검증
- **현재:** submit 후에만 검증
- **목표:** 입력 시 실시간 "✓ 일치" / "✗ 불일치" 표시
- **파일:** `frontend/src/pages/admin/settings.astro`

#### T4-7. admin input focus에 accent glow 추가
- **현재:** border-color만 변경
- **목표:** `box-shadow: 0 0 0 2px var(--color-accent-glow)` 추가
- **파일:** `frontend/src/styles/global.css`

### Phase C: 가독성 + 정리

#### T4-8. 블로그 본문 max-width 제한
- **현재:** 넓은 화면에서 줄이 너무 길어질 수 있음
- **목표:** `.blog-prose { max-width: 42rem; }` + `orphans: 3; widows: 3;`
- **파일:** `frontend/src/styles/global.css`

#### T4-9. 인라인 style="" → CSS 클래스 교체 (settings 페이지)
- **현재:** `style="display:none;"` 산재
- **목표:** `.is-hidden { display: none; }` 유틸리티 클래스 사용
- **파일:** `frontend/src/pages/admin/settings.astro`, `global.css`

#### T4-10. 스크롤바 스타일 통일
- **현재:** 영역별로 scrollbar 색상/크기 제각각
- **목표:** 공통 scrollbar 토큰
- **파일:** `frontend/src/styles/global.css`

---

## 2차 스프린트 완료 기준

- [ ] z-index가 10단계 체계로 정리됨
- [ ] admin select/input에 hover + focus glow 적용
- [ ] 테마 전환이 0.2s로 부드럽게 전환됨
- [ ] Save 버튼에 로딩 spinner 표시
- [ ] 비밀번호 폼에 실시간 일치 여부 표시
- [ ] 블로그 본문 줄 길이 제한 적용
- [ ] `npm run build` 통과

---

## 참조

- **주 CSS 파일:** `frontend/src/styles/global.css`
- **네비게이션:** `frontend/src/components/Navigation.astro`
- **Settings:** `frontend/src/pages/admin/settings.astro`
- **레이아웃:** `frontend/src/layouts/MainLayout.astro`
