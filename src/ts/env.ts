/** Facts about the page the script runs in, read once at load. */

export const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * URL of this bundle (dist/assets/js/site.js): other assets are resolved from
 * it, so the site works under any sub-path. Must be read while the script
 * executes, hence at module load.
 */
const scriptUrl = (document.currentScript as HTMLScriptElement | null)?.src ?? location.href;

/** Resolve a path relative to assets/js/. */
export function assetUrl(path: string): string {
  return new URL(path, scriptUrl).href;
}
