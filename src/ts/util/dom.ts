/** DOM helpers. */

/** Create an element with a class and optional attributes. */
export function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = '',
  attributes: Record<string, string> = {},
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (className) el.className = className;
  for (const [name, value] of Object.entries(attributes)) el.setAttribute(name, value);
  return el;
}

/** Remove `el` once its own CSS animation ends (not a child's). */
export function removeAfterAnimation(el: HTMLElement): void {
  el.addEventListener('animationend', (event) => {
    if (event.target === el) el.remove();
  });
}

/** Escape a string for use inside HTML text or attributes. */
export function escapeHtml(value: unknown): string {
  return String(value ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

/** localStorage that never throws (private mode, blocked storage). */
export const storage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage unavailable: the value just isn't remembered */
    }
  },
};
