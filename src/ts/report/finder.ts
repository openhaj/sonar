/**
 * Search boxes and filters of the report pages (tests, coverage, docs).
 *
 * Inside a [data-finder-scope] element:
 *   [data-finder-input]    a search box: keeps the rows whose data-row text
 *                          holds every word typed (lower-case)
 *   [data-filter="attr"]   buttons (data-value, "" = all): keeps the rows
 *                          whose data-<attr> is that value
 *   [data-row]             what is filtered
 *   [data-finder-group]    hidden when none of its rows is left
 *   [data-finder-empty]    shown when no row is left
 *
 * The first scope of the page follows the URL: ?q=strlen&verdict=failing
 * (so a link can open the page already filtered), and keeps it updated.
 */

function words(text: string): string[] {
  return text.trim().toLowerCase().split(/\s+/).filter(Boolean);
}

class Finder {
  private readonly input: HTMLInputElement | null;
  private readonly rows: HTMLElement[];
  private readonly groups: HTMLElement[];
  private readonly empty: HTMLElement | null;
  private readonly active = new Map<string, string>();

  constructor(
    private readonly scope: HTMLElement,
    private readonly followUrl: boolean,
  ) {
    this.input = scope.querySelector<HTMLInputElement>('[data-finder-input]');
    this.rows = [...scope.querySelectorAll<HTMLElement>('[data-row]')];
    this.groups = [...scope.querySelectorAll<HTMLElement>('[data-finder-group]')];
    this.empty = scope.querySelector<HTMLElement>('[data-finder-empty]');

    const params = followUrl ? new URLSearchParams(location.search) : null;
    if (this.input) {
      this.input.value = params?.get('q') ?? this.input.value;
      this.input.addEventListener('input', () => this.apply());
    }
    for (const box of scope.querySelectorAll<HTMLElement>('[data-filter]')) this.bindFilter(box, params);
    this.apply(false);
  }

  private bindFilter(box: HTMLElement, params: URLSearchParams | null): void {
    const attr = box.dataset['filter'];
    if (!attr) return;
    const buttons = [...box.querySelectorAll<HTMLButtonElement>('button[data-value]')];
    const select = (value: string): void => {
      const known = buttons.some((b) => b.dataset['value'] === value);
      const chosen = known ? value : '';
      for (const b of buttons) b.setAttribute('aria-pressed', String((b.dataset['value'] ?? '') === chosen));
      this.active.set(attr, chosen);
    };
    select(params?.get(attr) ?? '');
    box.addEventListener('click', (event) => {
      const button = (event.target as Element).closest<HTMLButtonElement>('button[data-value]');
      if (!button || !box.contains(button)) return;
      const value = button.dataset['value'] ?? '';
      // a second click on the active filter goes back to "all"
      select(this.active.get(attr) === value ? '' : value);
      this.apply();
    });
  }

  private matches(row: HTMLElement, terms: readonly string[]): boolean {
    const text = row.dataset['row'] ?? '';
    if (!terms.every((t) => text.includes(t))) return false;
    for (const [attr, value] of this.active) if (value && row.dataset[attr] !== value) return false;
    return true;
  }

  private apply(updateUrl = true): void {
    const terms = words(this.input?.value ?? '');
    let shown = 0;
    for (const row of this.rows) {
      const keep = this.matches(row, terms);
      row.hidden = !keep;
      if (keep) shown++;
    }
    for (const group of this.groups) group.hidden = !group.querySelector('[data-row]:not([hidden])');
    if (this.empty) this.empty.hidden = shown > 0;
    if (updateUrl && this.followUrl) this.saveUrl();
  }

  private saveUrl(): void {
    const params = new URLSearchParams(location.search);
    const q = this.input?.value.trim() ?? '';
    if (q) params.set('q', q);
    else params.delete('q');
    for (const [attr, value] of this.active) {
      if (value) params.set(attr, value);
      else params.delete(attr);
    }
    const search = params.toString();
    history.replaceState(null, '', `${location.pathname}${search ? `?${search}` : ''}${location.hash}`);
  }

  /** Make sure the element the URL points at (#name) is not filtered out. */
  reveal(target: Element): void {
    if (!this.scope.contains(target)) return;
    const row = target.closest<HTMLElement>('[data-row]');
    if (!row?.hidden) return;
    if (this.input) this.input.value = '';
    for (const box of this.scope.querySelectorAll<HTMLElement>('[data-filter]')) {
      const attr = box.dataset['filter'];
      if (attr) this.active.set(attr, '');
      for (const b of box.querySelectorAll('button[data-value]')) b.setAttribute('aria-pressed', String(b.getAttribute('data-value') === ''));
    }
    this.apply();
  }
}

export function initFinders(): void {
  const finders = [...document.querySelectorAll<HTMLElement>('[data-finder-scope]')].map(
    (scope, i) => new Finder(scope, i === 0),
  );
  const revealHash = (): void => {
    const id = decodeURIComponent(location.hash.slice(1));
    const target = id ? document.getElementById(id) : null;
    if (!target) return;
    for (const f of finders) f.reveal(target);
    target.scrollIntoView();
  };
  window.addEventListener('hashchange', revealHash);
  if (location.hash) revealHash();
}
