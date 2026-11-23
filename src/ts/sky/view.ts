/** State shared by every layer of the sky: viewport, pointer, sun/moon spot. */

/** What a layer gets each frame. `dt` is in 60 fps frames (1 = 16.7 ms). */
export interface Frame {
  readonly ctx: CanvasRenderingContext2D;
  readonly t: number;
  readonly dt: number;
}

/** One thing drawn on the sky canvas. */
export interface Layer {
  /** The viewport changed size (also called once at start). */
  resize?(): void;
  draw(frame: Frame): void;
  /** Called instead of draw() while the layer's scene is not shown. */
  hide?(): void;
}

/** Canvas size in CSS pixels, and the device pixel ratio used. */
export const view = { width: 0, height: 0, dpr: 1 };

export const isNarrow = (): boolean => view.width < 700;

const OFF_PAGE = -1e4;

/** Raw cursor position, and a smoothed parallax offset in [-1, 1]. */
export const pointer = {
  x: OFF_PAGE,
  y: OFF_PAGE,
  parallaxX: 0,
  parallaxY: 0,
  targetX: 0,
  targetY: 0,
  get onPage(): boolean {
    return this.x > OFF_PAGE / 2;
  },
};

export function trackPointer(): void {
  addEventListener(
    'pointermove',
    (event) => {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      pointer.targetX = (event.clientX / view.width) * 2 - 1;
      pointer.targetY = (event.clientY / view.height) * 2 - 1;
    },
    { passive: true },
  );
  document.addEventListener('pointerleave', () => {
    pointer.x = pointer.y = OFF_PAGE;
    pointer.targetX = pointer.targetY = 0;
  });
}

/** Move the parallax offset a little toward the cursor. */
export function easeParallax(dt: number): void {
  const k = Math.min(1, 0.05 * dt);
  pointer.parallaxX += (pointer.targetX - pointer.parallaxX) * k;
  pointer.parallaxY += (pointer.targetY - pointer.parallaxY) * k;
}

/** Distance from the cursor to a point, normalized to [0, 1] within `range` (1 = on it). */
export function proximity(x: number, y: number, range: number): number {
  return Math.max(0, 1 - Math.hypot(x - pointer.x, y - pointer.y) / range);
}

export interface Disc {
  readonly x: number;
  readonly y: number;
  readonly r: number;
}

/** Where the sun or the moon is: top right, with a little parallax. */
export function orb(): Disc {
  return {
    x: view.width * (isNarrow() ? 0.82 : 0.88) - pointer.parallaxX * 14,
    y: view.height * 0.15 - pointer.parallaxY * 10,
    r: isNarrow() ? 28 : 40,
  };
}
