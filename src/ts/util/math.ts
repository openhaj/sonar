/** Small numeric helpers shared by the animations. */

export const TAU = Math.PI * 2;

/** Uniform random number in [min, max). */
export function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Pick one element of a non-empty array. */
export function pick<T>(items: readonly T[]): T {
  const item = items[Math.floor(Math.random() * items.length)];
  if (item === undefined) throw new RangeError('pick() on an empty array');
  return item;
}
