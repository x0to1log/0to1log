function initComments(): void {
  const section = document.querySelector<HTMLElement>('.newsprint-comments');
  if (!section || section.dataset.commentInit === 'true') return;
  section.dataset.commentInit = 'true';

  const postId = section.dataset.postId;
  const locale = section.dataset.locale || 'en';
  const loginUrl = section.dataset.loginUrl || '/login';
  if (!postId) return;

  const list = section.querySelector<HTMLElement>('[data-comments-list]');
  const form = section.querySelector<HTMLFormElement>('[data-comment-form]');
  const loginLink = section.querySelector<HTMLElement>('[data-comment-login]');
  const input = section.querySelector<HTMLTextAreaElement>('[data-comment-input]');
  const charcount = section.querySelector<HTMLElement>('[data-comment-charcount]');
  const totalEl = section.querySelector<HTMLElement>('[data-comment-total]');
  const countEl = document.querySelector<HTMLElement>('[data-comment-count]');

  let currentUserId: string | null = null;

  async function loadComments() {
    try {
      const res = await fetch(`/api/user/comments?post_id=${postId}&type=${section.dataset.contentType || 'news'}`);
      if (!res.ok) return;
      const comments = await res.json();
      renderComments(comments);
    } catch {
      // Silently fail
    }
  }

  function renderComments(comments: any[]) {
    if (!list) return;

    if (comments.length === 0) {
      list.innerHTML = '';
      updateCounts(0);
      return;
    }

    list.innerHTML = comments.map((c) => {
      const date = new Date(c.created_at).toLocaleDateString(
        locale === 'ko' ? 'ko-KR' : 'en-US',
        { year: 'numeric', month: 'short', day: 'numeric' }
      );
      const initial = (c.user.display_name || 'A').charAt(0).toUpperCase();
      const canDelete = !!c.can_delete;
      const deleteBtn = canDelete
        ? `<button class="newsprint-comment-delete" data-delete-comment="${c.id}" aria-label="${locale === 'ko' ? '삭제' : 'Delete'}">&times;</button>`
        : '';

      return `<div class="newsprint-comment" data-comment-id="${c.id}">
        <div class="newsprint-comment-header">
          <div class="newsprint-comment-avatar">${
            c.user.avatar_url
              ? `<img src="${c.user.avatar_url}" alt="" width="28" height="28" style="border-radius:50%;">`
              : `<span>${initial}</span>`
          }</div>
          <span class="newsprint-comment-author">${escapeHtml(c.user.display_name || 'Anonymous')}</span>
          <span class="newsprint-comment-date">${date}</span>
          ${deleteBtn}
        </div>
        <div class="newsprint-comment-body">${escapeHtml(c.body)}</div>
      </div>`;
    }).join('');

    updateCounts(comments.length);

    list.querySelectorAll<HTMLButtonElement>('[data-delete-comment]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const confirmMsg = locale === 'ko' ? '이 댓글을 삭제할까요?' : 'Delete this comment?';
        if (!confirm(confirmMsg)) return;

        const commentId = btn.dataset.deleteComment;
        if (!commentId) return;

        try {
          const res = await fetch(`/api/user/comments?id=${commentId}&type=${section.dataset.contentType || 'news'}`, { method: 'DELETE' });
          if (res.ok) {
            const el = list?.querySelector(`[data-comment-id="${commentId}"]`);
            if (el) el.remove();
            const remaining = list?.querySelectorAll('.newsprint-comment').length || 0;
            updateCounts(remaining);
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

  async function checkAuth() {
    try {
      const res = await fetch('/api/user/profile');
      if (res.ok) {
        const profile = await res.json();
        currentUserId = profile.id || null;
        if (form) form.style.display = '';
        if (loginLink) loginLink.style.display = 'none';
      } else {
        if (form) form.style.display = 'none';
        if (loginLink) loginLink.style.display = '';
      }
    } catch {
      if (form) form.style.display = 'none';
      if (loginLink) loginLink.style.display = '';
    }
  }

  if (input && charcount) {
    input.addEventListener('input', () => {
      const len = input.value.length;
      charcount.textContent = len > 0 ? `${len}/2000` : '';
    });
  }

  if (form && input) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = input.value.trim();
      if (!body) return;

      const submitBtn = form.querySelector<HTMLButtonElement>('[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      try {
        const res = await fetch('/api/user/comments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ post_id: postId, body, type: section.dataset.contentType || 'news' }),
        });

        if (res.status === 401) {
          window.location.href = loginUrl;
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

  checkAuth();
  loadComments();
}

document.addEventListener('astro:page-load', initComments);
