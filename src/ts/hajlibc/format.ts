/** Formatting helpers for the hajlibc page. */
import { clamp } from '../util/math';

export const percent = (value: number, digits = 1): string => `${value.toFixed(digits)}%`;

export const plural = (n: number, word: string): string => `${n} ${word}${n === 1 ? '' : 's'}`;

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/** Progress bar markup (styled by .meter in style.css). */
export function meter(value: number): string {
  return `<span class="meter"><span style="width:${clamp(value, 0, 100).toFixed(1)}%"></span></span>`;
}
