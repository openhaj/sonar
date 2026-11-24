/**
 * Source listing of a coverage page: the [data-next-miss] button (or the
 * key n) jumps to the next run of lines never executed (.ln.miss) below the
 * top of the window, and wraps around at the end of the file.
 */

export function initSourceNavigation(): void {
  const link = document.querySelector<HTMLAnchorElement>('[data-next-miss]');
  if (!link) return;
  // first line of each run of lines never executed
  const starts = [...document.querySelectorAll<HTMLElement>('.source .ln.miss')].filter(
    (line) => !line.previousElementSibling?.classList.contains('miss'),
  );
  if (!starts.length) {
    link.hidden = true;
    return;
  }
  const jump = (): void => {
    // a line scrolled to sits scroll-margin-top below the top: the next one is below that
    const margin = parseFloat(getComputedStyle(starts[0] as Element).scrollMarginTop) || 0;
    const next = starts.find((line) => line.getBoundingClientRect().top > margin + 2) ?? starts[0];
    if (!next) return;
    history.replaceState(null, '', `#${next.id}`);
    next.scrollIntoView({ block: 'start' });
    next.classList.remove('flash');
    void next.offsetWidth; // restart the animation
    next.classList.add('flash');
  };
  link.addEventListener('click', (event) => {
    event.preventDefault();
    jump();
  });
  document.addEventListener('keydown', (event) => {
    const target = event.target as Element | null;
    if (event.key !== 'n' || event.ctrlKey || event.metaKey || event.altKey) return;
    if (target?.closest('input, textarea, select, [contenteditable]')) return;
    jump();
  });
}
