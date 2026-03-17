# Floating Persona Switcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 원래 페르소나 탭이 뷰포트 밖으로 나갔을 때, 화면 하단 중앙에 동일한 탭이 플로팅으로 등장해 언제든 페르소나 전환 가능하게 함.

**Architecture:** `IntersectionObserver`로 원래 `.persona-switcher` 이탈 감지 → `.persona-float` 표시/숨김. 클릭 시 원래 탭과 플로팅 탭 양쪽 active 상태 동기화. 기존 `newsprint:article-content-updated` 이벤트 재활용.

**Tech Stack:** Astro v5, TypeScript, CSS custom properties, IntersectionObserver API

---

### Task 1: CSS — `.persona-float` 스타일 추가

**Files:**
- Modify: `frontend/src/styles/global.css` (line 694 이후, `.persona-switcher` 블록 바로 뒤)

**Step 1: CSS 추가**

line 694 (`.blog-shell .persona-switcher-btn` 블록) 바로 뒤에 삽입:

```css
/* Floating persona switcher */
.persona-float {
  position: fixed;
  bottom: calc(5.75rem + env(safe-area-inset-bottom) + 0.75rem);
  left: 50%;
  transform: translateX(-50%) translateY(12px);
  z-index: 89;
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  background: color-mix(in srgb, var(--color-bg-primary) 85%, transparent);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  opacity: 0;
  pointer-events: none;
  transition: opacity 200ms ease, transform 250ms ease;
  white-space: nowrap;
}

.persona-float--visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}

.persona-float-btn {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  padding: 0.55rem 1.1rem;
  background: transparent;
  border: none;
  border-right: 1px solid var(--color-border);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: background 150ms ease, color 150ms ease;
  min-height: 44px;
}

.persona-float-btn:last-child {
  border-right: none;
}

.persona-float-btn--active {
  background: var(--color-accent-subtle, rgba(0, 0, 0, 0.06));
  color: var(--color-text-primary);
  font-weight: 600;
}

.persona-float-btn:hover:not(.persona-float-btn--active) {
  background: var(--color-accent-subtle, rgba(0, 0, 0, 0.03));
}

@keyframes persona-float-pulse {
  0%, 100% { box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12); }
  50% { box-shadow: 0 2px 20px color-mix(in srgb, var(--color-accent) 40%, transparent); }
}

.persona-float--pulse {
  animation: persona-float-pulse 600ms ease 1;
}

@media (min-width: 1024px) {
  .persona-float {
    bottom: 2rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .persona-float {
    transition: opacity 0ms;
  }
  .persona-float--pulse {
    animation: none;
  }
}
```

**Step 2: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `[build] Complete!` (0 errors)

---

### Task 2: HTML — 플로팅 pill 마크업 추가

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`

**Step 1: 플로팅 pill HTML 추가**

line 289 (`</>` 닫는 태그, `showPersonaSwitcher` 블록 끝) 바로 뒤, line 291 (`<div class="reading-actions-layout"`) 바로 앞에 삽입:

```astro
  {showPersonaSwitcher && (
    <div class="persona-float" id="persona-float" aria-hidden="true">
      {(['beginner', 'learner', 'expert'] as const).filter(p => personaHtmlMap![p]).map(p => (
        <button
          type="button"
          class={`persona-float-btn ${p === activePersona ? 'persona-float-btn--active' : ''}`}
          data-persona={p}
        >
          {personaLabels[locale]?.[p] || p}
        </button>
      ))}
    </div>
  )}
```

**Step 2: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `[build] Complete!`

---

### Task 3: JS — `initPersonaSwitcher` 리팩터링

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro` (line 479–534의 `<script>` 블록)

**Step 1: 기존 `<script>` 블록의 `initPersonaSwitcher` 함수 전체를 아래로 교체**

```typescript
  let _personaObserver: IntersectionObserver | null = null;

  function initPersonaSwitcher() {
    if (_personaObserver) { _personaObserver.disconnect(); _personaObserver = null; }

    const template = document.getElementById('persona-data') as HTMLTemplateElement | null;
    if (!template) return;
    const map: Record<string, string> = JSON.parse(template.dataset.map || '{}');
    const prose = document.querySelector('.newsprint-prose');
    const switcher = document.querySelector<HTMLElement>('.persona-switcher');
    const floatEl = document.getElementById('persona-float');
    if (!prose || !switcher) return;

    function setActivePersona(p: string) {
      if (!map[p]) return;
      prose!.innerHTML = map[p];

      switcher!.querySelectorAll('.persona-switcher-btn').forEach(b =>
        b.classList.toggle('persona-switcher-btn--active',
          (b as HTMLElement).dataset.persona === p));

      floatEl?.querySelectorAll('.persona-float-btn').forEach(b =>
        b.classList.toggle('persona-float-btn--active',
          (b as HTMLElement).dataset.persona === p));

      document.dispatchEvent(new CustomEvent('newsprint:article-content-updated', {
        detail: { root: prose, persona: p },
      }));
    }

    switcher.addEventListener('click', (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('.persona-switcher-btn');
      if (btn) setActivePersona(btn.dataset.persona!);
    });

    if (floatEl) {
      floatEl.addEventListener('click', (e) => {
        const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('.persona-float-btn');
        if (btn) setActivePersona(btn.dataset.persona!);
      });

      let hasShownOnce = false;
      _personaObserver = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) {
          floatEl.classList.add('persona-float--visible');
          floatEl.removeAttribute('aria-hidden');
          if (!hasShownOnce) {
            hasShownOnce = true;
            floatEl.classList.add('persona-float--pulse');
            floatEl.addEventListener('animationend', () =>
              floatEl.classList.remove('persona-float--pulse'), { once: true });
          }
        } else {
          floatEl.classList.remove('persona-float--visible');
          floatEl.setAttribute('aria-hidden', 'true');
        }
      }, { threshold: 0.1 });

      _personaObserver.observe(switcher);
    }
  }
```

`document.addEventListener('astro:page-load', initPersonaSwitcher)` 뒤에 `initPersonaSwitcher()` 직접 호출도 추가:

```typescript
  document.addEventListener('astro:page-load', initPersonaSwitcher);
  document.addEventListener('astro:page-load', initQuiz);
  initPersonaSwitcher();
```

**Step 2: 빌드 확인**
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `[build] Complete!`

---

### Task 4: 커밋 및 푸시

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro \
        frontend/src/styles/global.css
git commit -m "feat(persona): add floating bottom pill that appears on scroll"
git push
```

---

## 검증 체크리스트

- [ ] 뉴스 상세 페이지에서 원래 탭 위치를 스크롤로 지나치면 플로팅 pill 등장
- [ ] 최초 등장 시 pulse 애니메이션 1회 실행
- [ ] 스크롤 올려서 원래 탭이 보이면 플로팅 pill 사라짐
- [ ] 플로팅 탭 클릭 → 페르소나 전환 + 원래 탭 active 동기화
- [ ] 원래 탭 클릭 → 플로팅 탭 active 동기화
- [ ] 모바일: 플로팅 pill이 액션 바 위에 위치
- [ ] 데스크탑: 플로팅 pill이 화면 하단 중앙에 위치
- [ ] `prefers-reduced-motion` 시 애니메이션 없이 동작
