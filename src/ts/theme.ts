/**
 * Light / dark theme. The initial theme is set before first paint by an inline
 * script in base.html (saved choice, else the system preference); this module
 * adds the toggle button and remembers the choice.
 */
import { element, storage } from './util/dom';

export type Theme = 'light' | 'dark';

const root = document.documentElement;

const ICONS =
  '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>' +
  '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 1.5v2.5M12 20v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M1.5 12H4M20 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8"/></svg>';

export function currentTheme(): Theme {
  return root.dataset['theme'] === 'dark' ? 'dark' : 'light';
}

/** Add the sun/moon button to the navigation; `onChange` runs after a switch. */
export function initThemeToggle(onChange: (theme: Theme) => void): void {
  const nav = document.querySelector('.site-header .nav-links');
  if (!nav) return;

  const button = element('button', 'theme-toggle', { type: 'button' });
  button.innerHTML = ICONS; // the icon shown is the theme you switch to (CSS)

  const updateLabel = (): void => {
    const text = currentTheme() === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
    button.setAttribute('aria-label', text);
    button.title = text;
  };

  button.addEventListener('click', () => {
    const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark';
    root.dataset['theme'] = next;
    storage.set('theme', next);
    updateLabel();
    onChange(next);
  });

  updateLabel();
  nav.append(button);
}
