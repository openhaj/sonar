/** Night: a field of faint twinkling stars, with depth-based parallax. */
import { reduceMotion } from '../env';
import { rand, TAU } from '../util/math';
import { pointer, view, type Frame, type Layer } from './view';

interface FieldStar {
  x: number; // 0..1 of the viewport
  y: number;
  r: number;
  depth: number; // 0 (far) .. 1 (near): parallax and brightness
  phase: number;
  speed: number;
}

let stars: FieldStar[] = [];

export const starfield: Layer = {
  resize() {
    const count = Math.min(280, Math.round((view.width * view.height) / 5000));
    stars = Array.from({ length: count }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: rand(0.3, 1.2),
      depth: rand(0.2, 0.9),
      phase: rand(0, TAU),
      speed: rand(0.6, 2),
    }));
  },

  draw({ ctx, t }: Frame) {
    for (const s of stars) {
      const x = s.x * view.width - pointer.parallaxX * 22 * s.depth;
      const y = s.y * view.height - pointer.parallaxY * 16 * s.depth;
      const twinkle = reduceMotion ? 0.8 : 0.55 + 0.45 * Math.sin(t * 0.001 * s.speed + s.phase);
      ctx.fillStyle = `rgba(225, 236, 255, ${twinkle * (0.25 + 0.55 * s.depth)})`;
      ctx.beginPath();
      ctx.arc(x, y, s.r, 0, TAU);
      ctx.fill();
    }
  },
};
