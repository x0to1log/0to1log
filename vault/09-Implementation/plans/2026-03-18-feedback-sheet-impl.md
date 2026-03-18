# Feedback Bottom Sheet — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 핸드북 "?" 버튼 클릭 시 반응 버튼 + 텍스트 메시지를 보낼 수 있는 Bottom Sheet 구현

**Architecture:** 기존 `handbookFeedback.ts`를 확장하여 Bottom Sheet UI를 동적 생성. DB에 `message` 컬럼 추가. API에 message 필드 추가. "?" 버튼은 기존 toggle 동작 대신 sheet open 트리거로 변경.

**Tech Stack:** Astro v5 + CSS Custom Properties + Supabase

---

## Task 1: DB 마이그레이션 — message 컬럼 추가

**Files:**
- Create: `supabase/migrations/00029_term_feedback_message.sql`

- [ ] **Step 1: 마이그레이션 파일 작성**

```sql
-- 00029_term_feedback_message.sql
-- Add optional message field to term_feedback for detailed user feedback
ALTER TABLE term_feedback ADD COLUMN IF NOT EXISTS message TEXT;
```

- [ ] **Step 2: 커밋**

```
feat(db): add message column to term_feedback
```

---

## Task 2: API 업데이트 — message 수신/저장

**Files:**
- Modify: `frontend/src/pages/api/user/term-feedback.ts`

- [ ] **Step 1: POST 핸들러에 message 필드 추가**

body 디스트럭처링에 `message` 추가:
```ts
const { term_id, locale, reaction, message } = body;
```

upsert 데이터에 `message` 추가:
```ts
const { error } = await supabase
  .from('term_feedback')
  .upsert({
    user_id: locals.user.id,
    term_id,
    locale,
    reaction,
    message: message || null,
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,term_id,locale' });
```

response에 `message` 포함:
```ts
return jsonResponse({ reaction, message: message || null });
```

- [ ] **Step 2: GET 핸들러에 message 반환 추가**

select에 `message` 추가:
```ts
const { data } = await supabase
  .from('term_feedback')
  .select('reaction, message')
  ...
```

response:
```ts
return jsonResponse({ reaction: data?.reaction || null, message: data?.message || null });
```

- [ ] **Step 3: 빌드 검증**

---

## Task 3: CSS — Bottom Sheet 스타일

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Bottom Sheet 스타일 추가**

핸드북 피드백 섹션 근처(`.handbook-feedback` 이후)에 추가:

```css
/* --- Feedback Bottom Sheet --- */
.feedback-sheet-backdrop {
  position: fixed;
  inset: 0;
  z-index: 400;
  background: rgba(0, 0, 0, 0.3);
  opacity: 0;
  pointer-events: none;
  transition: opacity 200ms ease;
}

.feedback-sheet-backdrop--open {
  opacity: 1;
  pointer-events: auto;
}

.feedback-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 410;
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  padding: 1.25rem 1.5rem calc(1.25rem + env(safe-area-inset-bottom));
  transform: translateY(100%);
  transition: transform 250ms ease;
  max-width: 480px;
  margin: 0 auto;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
}

.feedback-sheet--open {
  transform: translateY(0);
}

.feedback-sheet-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.5rem;
  line-height: 1;
  font-size: 1.1rem;
}

.feedback-sheet-close:hover {
  color: var(--color-text-primary);
}

.feedback-sheet-title {
  font-family: var(--font-ui);
  font-size: 0.9rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: var(--color-text-primary);
}

.feedback-sheet-reactions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.feedback-sheet-reaction {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  font-family: var(--font-ui);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 150ms ease;
}

.feedback-sheet-reaction:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.feedback-sheet-reaction.is-selected {
  border-color: var(--color-accent);
  background: var(--color-accent-subtle);
  color: var(--color-accent);
  font-weight: 600;
}

.feedback-sheet-textarea {
  width: 100%;
  min-height: 4rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-input-surface);
  color: var(--color-text-primary);
  font-family: var(--font-ui);
  font-size: 0.82rem;
  resize: vertical;
  transition: border-color 150ms ease;
}

.feedback-sheet-textarea:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-accent-glow);
}

.feedback-sheet-textarea::placeholder {
  color: var(--color-text-muted);
}

.feedback-sheet-submit {
  width: 100%;
  margin-top: 0.75rem;
  padding: 0.55rem 1rem;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: var(--color-bg-primary);
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 150ms ease;
}

.feedback-sheet-submit:hover {
  opacity: 0.9;
}

.feedback-sheet-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.feedback-sheet-success {
  text-align: center;
  padding: 1.5rem 0;
  font-family: var(--font-ui);
  font-size: 0.9rem;
  color: var(--color-success);
  font-weight: 600;
}

@media (min-width: 768px) {
  .feedback-sheet {
    left: 50%;
    right: auto;
    bottom: 1.5rem;
    transform: translateX(-50%) translateY(1rem);
    opacity: 0;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
  }

  .feedback-sheet--open {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
  }
}
```

---

## Task 4: JS — Bottom Sheet 로직

**Files:**
- Modify: `frontend/src/scripts/handbookFeedback.ts`

- [ ] **Step 1: Sheet HTML 동적 생성 함수 추가**

`initHandbookFeedback()` 상단에 sheet 생성 로직:

```ts
function createFeedbackSheet(locale: string): { backdrop: HTMLElement; sheet: HTMLElement } {
  const isKo = locale === 'ko';

  const backdrop = document.createElement('div');
  backdrop.className = 'feedback-sheet-backdrop';

  const sheet = document.createElement('div');
  sheet.className = 'feedback-sheet';
  sheet.innerHTML = `
    <button class="feedback-sheet-close" aria-label="Close">&times;</button>
    <h3 class="feedback-sheet-title">${isKo ? '이 설명에 대한 피드백' : 'Feedback on this explanation'}</h3>
    <div class="feedback-sheet-reactions">
      <button type="button" class="feedback-sheet-reaction" data-reaction="helpful">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
        ${isKo ? '도움됐어요' : 'Helpful'}
      </button>
      <button type="button" class="feedback-sheet-reaction" data-reaction="confusing">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.75-2.5 2-2.5 4"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/></svg>
        ${isKo ? '헷갈려요' : 'Confusing'}
      </button>
    </div>
    <textarea class="feedback-sheet-textarea" placeholder="${isKo ? '추가 의견을 남겨주세요 (선택)' : 'Additional comments (optional)'}" maxlength="500"></textarea>
    <button type="button" class="feedback-sheet-submit" disabled>${isKo ? '보내기' : 'Send'}</button>
  `;

  document.body.appendChild(backdrop);
  document.body.appendChild(sheet);
  return { backdrop, sheet };
}
```

- [ ] **Step 2: "?" 버튼 클릭 → sheet open 트리거로 변경**

기존 confusing 버튼의 click 핸들러를 교체:
- `data-reaction="confusing"` 버튼 클릭 시 → `openFeedbackSheet()` 호출
- `data-reaction="helpful"` 버튼은 기존 동작 유지 (바로 API 호출)

```ts
// confusing 버튼은 sheet 열기로 변경
if (btn.dataset.reaction === 'confusing') {
  btn.addEventListener('click', () => openFeedbackSheet());
  return; // 기존 toggle 로직 건너뜀
}
```

- [ ] **Step 3: Sheet 내부 인터랙션**

```ts
function openFeedbackSheet() {
  if (!isAuthenticated) { openAuthPrompt(); return; }

  const { backdrop, sheet } = createFeedbackSheet(locale);
  let selectedReaction: string | null = existingReaction;

  // 기존 반응 복원
  if (selectedReaction) {
    sheet.querySelector(`[data-reaction="${selectedReaction}"]`)?.classList.add('is-selected');
    (sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement).disabled = false;
  }

  // 기존 메시지 복원
  // (GET API에서 message도 가져옴)

  // 반응 버튼 클릭
  sheet.querySelectorAll('.feedback-sheet-reaction').forEach(rb => {
    rb.addEventListener('click', () => {
      sheet.querySelectorAll('.feedback-sheet-reaction').forEach(r => r.classList.remove('is-selected'));
      rb.classList.add('is-selected');
      selectedReaction = (rb as HTMLElement).dataset.reaction || null;
      (sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement).disabled = false;
    });
  });

  // 보내기
  sheet.querySelector('.feedback-sheet-submit')?.addEventListener('click', async () => {
    if (!selectedReaction) return;
    const submitBtn = sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement;
    const textarea = sheet.querySelector('.feedback-sheet-textarea') as HTMLTextAreaElement;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-spinner"></span>' + (locale === 'ko' ? '보내는 중...' : 'Sending...');

    try {
      await fetch('/api/user/term-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term_id: termId,
          locale,
          reaction: selectedReaction,
          message: textarea.value.trim() || null,
        }),
      });

      // 성공 표시
      sheet.querySelector('.feedback-sheet-title')!.remove();
      sheet.querySelector('.feedback-sheet-reactions')!.remove();
      sheet.querySelector('.feedback-sheet-textarea')!.remove();
      submitBtn.remove();
      const success = document.createElement('div');
      success.className = 'feedback-sheet-success';
      success.textContent = locale === 'ko' ? '감사합니다! 피드백이 전달되었습니다.' : 'Thank you! Your feedback has been sent.';
      sheet.querySelector('.feedback-sheet-close')!.after(success);

      // StickyActions 버튼 상태도 동기화
      updateStickyButtons(selectedReaction);

      setTimeout(() => closeFeedbackSheet(backdrop, sheet), 1500);
    } catch {
      submitBtn.disabled = false;
      submitBtn.textContent = locale === 'ko' ? '보내기' : 'Send';
    }
  });

  // 닫기
  const close = () => closeFeedbackSheet(backdrop, sheet);
  backdrop.addEventListener('click', close);
  sheet.querySelector('.feedback-sheet-close')?.addEventListener('click', close);

  // 열기 애니메이션
  requestAnimationFrame(() => {
    backdrop.classList.add('feedback-sheet-backdrop--open');
    sheet.classList.add('feedback-sheet--open');
  });
}

function closeFeedbackSheet(backdrop: HTMLElement, sheet: HTMLElement) {
  backdrop.classList.remove('feedback-sheet-backdrop--open');
  sheet.classList.remove('feedback-sheet--open');
  setTimeout(() => { backdrop.remove(); sheet.remove(); }, 250);
}
```

- [ ] **Step 4: 빌드 검증**

---

## Task 5: 빌드 + 커밋

- [ ] **Step 1:** `cd frontend && npm run build` 통과
- [ ] **Step 2:** 커밋

```
feat(handbook): add feedback bottom sheet with reaction buttons and text message
```

---

## 수정 파일 요약

| 파일 | 변경 |
|------|------|
| `supabase/migrations/00029_term_feedback_message.sql` | 새 파일: message 컬럼 |
| `frontend/src/pages/api/user/term-feedback.ts` | message 수신/저장/반환 |
| `frontend/src/scripts/handbookFeedback.ts` | Bottom Sheet 생성/열기/닫기/제출 |
| `frontend/src/styles/global.css` | Bottom Sheet CSS |

## 검증

1. `npm run build` 통과
2. 핸드북 상세 → "?" 버튼 클릭 → Bottom Sheet 슬라이드 업
3. 반응 버튼 선택 → 보내기 활성화
4. 텍스트 입력 (선택) → 보내기 → "감사합니다!" → 자동 닫기
5. 비로그인 → "?" 클릭 → 로그인 프롬프트
6. 모바일/데스크톱 모두 확인
