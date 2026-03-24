import { openAuthPrompt } from './auth-prompt';

function initComments(): void {
  const section = document.querySelector<HTMLElement>('.newsprint-comments');
  if (!section || section.dataset.commentInit === 'true') return;
  section.dataset.commentInit = 'true';

  const postId = section.dataset.postId;
  const locale = section.dataset.locale || 'en';
  const isAuthenticated = section.dataset.authenticated === 'true';
  const contentType = section.dataset.contentType || 'news';
  const previewMode = section.dataset.previewMode === 'true';
  const commentRedirect = section.dataset.commentRedirect || `${window.location.pathname}${window.location.search}#comments`;
  if (!postId) return;

  const list = section.querySelector<HTMLElement>('[data-comments-list]');
  const form = section.querySelector<HTMLFormElement>('[data-comment-form]');
  const loginLink = section.querySelector<HTMLElement>('[data-comment-login]');
  const input = section.querySelector<HTMLTextAreaElement>('[data-comment-input]');
  const charcount = section.querySelector<HTMLElement>('[data-comment-charcount]');
  const totalEl = section.querySelector<HTMLElement>('[data-comment-total]');
  const countEl = document.querySelector<HTMLElement>('[data-comment-count]');

  if (form) form.style.display = !previewMode && isAuthenticated ? '' : 'none';
  if (loginLink) loginLink.style.display = !previewMode && !isAuthenticated ? '' : 'none';

  async function loadComments() {
    try {
      const res = await fetch(`/api/user/comments?post_id=${postId}&type=${contentType}`);
      if (!res.ok) {
        updateCounts(0);
        return;
      }
      const comments = await res.json();
      renderComments(comments);
    } catch {
      updateCounts(0);
    }
  }

  function renderComments(comments: any[]) {
    if (!list) return;

    if (comments.length === 0) {
      list.innerHTML = '';
      updateCounts(0);
      return;
    }

    list.innerHTML = comments.map((comment) => {
      const date = new Date(comment.created_at).toLocaleDateString(
        locale === 'ko' ? 'ko-KR' : 'en-US',
        { year: 'numeric', month: 'short', day: 'numeric' }
      );
      const initial = (comment.user.display_name || 'A').charAt(0).toUpperCase();
      const deleteLabel = locale === 'ko' ? '삭제' : 'Delete';
      const deleteBtn = !previewMode && comment.can_delete
        ? `<button class="newsprint-comment-delete" data-delete-comment="${comment.id}" aria-label="${deleteLabel}">&times;</button>`
        : '';

      return `<div class="newsprint-comment" data-comment-id="${comment.id}">
        <div class="newsprint-comment-header">
          <div class="newsprint-comment-avatar">${
            comment.user.avatar_url
              ? `<img src="${escapeHtml(comment.user.avatar_url)}" alt="" width="28" height="28" style="border-radius:50%;">`
              : `<span>${initial}</span>`
          }</div>
          <span class="newsprint-comment-author">${escapeHtml(comment.user.display_name || 'Anonymous')}</span>
          <span class="newsprint-comment-date">${date}</span>
          ${deleteBtn}
        </div>
        <div class="newsprint-comment-body">${escapeHtml(comment.body)}</div>
      </div>`;
    }).join('');

    updateCounts(comments.length);

    list.querySelectorAll<HTMLButtonElement>('[data-delete-comment]').forEach((button) => {
      button.addEventListener('click', async () => {
        const confirmMsg = locale === 'ko' ? '이 댓글을 삭제할까요?' : 'Delete this comment?';
        if (!window.confirm(confirmMsg)) return;

        const commentId = button.dataset.deleteComment;
        if (!commentId) return;

        try {
          const res = await fetch(`/api/user/comments?id=${commentId}&type=${contentType}`, { method: 'DELETE' });
          if (res.status === 401) {
            openAuthPrompt({ action: 'comment', redirectTo: commentRedirect });
            return;
          }
          if (!res.ok) {
            const msg = locale === 'ko' ? '삭제할 수 없습니다.' : 'Could not delete comment.';
            window.alert(msg);
            return;
          }
          if (res.ok) {
            const el = list.querySelector(`[data-comment-id="${commentId}"]`);
            if (el) el.remove();
            updateCounts(list.querySelectorAll('.newsprint-comment').length);
          }
        } catch {
          // Silently fail
        }
      });
    });
  }

  function updateCounts(count: number) {
    if (totalEl) totalEl.textContent = String(count);
    if (countEl) countEl.textContent = String(count);
  }

  function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  if (input && charcount) {
    input.addEventListener('input', () => {
      const len = input.value.length;
      charcount.textContent = len > 0 ? `${len}/2000` : '';
    });
  }

  if (form && input) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (previewMode) return;
      const body = input.value.trim();
      if (!body) return;

      const submitBtn = form.querySelector<HTMLButtonElement>('[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      try {
        const res = await fetch('/api/user/comments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ post_id: postId, body, type: contentType }),
        });

        if (res.status === 401) {
          openAuthPrompt({ action: 'comment', redirectTo: commentRedirect });
          return;
        }

        if (res.ok) {
          input.value = '';
          if (charcount) charcount.textContent = '';
          await loadComments();
        }
      } catch {
        // Silently fail
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  loadComments();
}

document.addEventListener('astro:page-load', initComments);
