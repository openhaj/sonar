/**
 * The interactive sky: a fixed <canvas> behind the page, drawing the night or
 * the day scene depending on the theme. Each scene is a list of layers.
 */
import { reduceMotion } from '../env';
import { currentTheme } from '../theme';
import { element } from '../util/dom';
import { birdLayer } from './birds';
import { constellationLayer } from './constellations';
import { moon } from './moon';
import { shootingStars, sparkLayer } from './shooting-stars';
import { starfield } from './starfield';
import { sun } from './sun';
import { easeParallax, trackPointer, view, type Layer } from './view';

const NIGHT: readonly Layer[] = [starfield, constellationLayer, shootingStars, moon];
const DAY: readonly Layer[] = [sun, birdLayer];
const ALWAYS: readonly Layer[] = [sparkLayer];
const ALL: readonly Layer[] = [...NIGHT, ...DAY, ...ALWAYS];

export interface Sky {
  /** Draw one frame now (used when animations are off). */
  redraw(): void;
}

export function initSky(): Sky {
  const canvas = element('canvas', 'sky', { 'aria-hidden': 'true' });
  const ctx = canvas.getContext('2d');
  if (!ctx) return { redraw() {} };
  document.body.prepend(canvas);

  const draw = (t: number, dt: number): void => {
    easeParallax(dt);
    ctx.clearRect(0, 0, view.width, view.height);
    const [shown, hidden] = currentTheme() === 'dark' ? [NIGHT, DAY] : [DAY, NIGHT];
    for (const layer of hidden) layer.hide?.();
    for (const layer of [...shown, ...ALWAYS]) layer.draw({ ctx, t, dt });
  };

  const resize = (): void => {
    view.dpr = Math.min(devicePixelRatio || 1, 2);
    view.width = innerWidth;
    view.height = innerHeight;
    canvas.width = view.width * view.dpr;
    canvas.height = view.height * view.dpr;
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    for (const layer of ALL) layer.resize?.();
    if (reduceMotion) draw(0, 0);
  };

  trackPointer();
  addEventListener('resize', resize);
  resize();

  if (reduceMotion) {
    draw(0, 0);
  } else {
    let last = 0;
    const frame = (t: number): void => {
      const dt = last ? Math.min(3, (t - last) / 16.67) : 1; // 1 = one 60 fps frame
      last = t;
      draw(t, dt);
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }

  return { redraw: () => draw(0, 0) };
}
