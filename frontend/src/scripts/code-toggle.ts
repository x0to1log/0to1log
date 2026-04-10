/**
 * Code window collapse/expand toggle.
 *
 * Active on handbook Advanced pages where rehypeCodeWindow({ collapsible: true })
 * adds [data-code-toggle] buttons. Single delegated listener handles all
 * .code-window--collapsible instances on the page.
 *
 * Newsprint pages without collapsible code windows are unaffected — the
 * selector simply never matches.
 */
document.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (!target.matches('[data-code-toggle]')) return;

  const win = target.closest('.code-window--collapsible');
  if (!win) return;

  const isCollapsed = win.classList.toggle('code-window--collapsed');
  target.textContent = isCollapsed ? '펼치기 ▾' : '접기 ▴';
});
