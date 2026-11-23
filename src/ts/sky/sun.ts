/** Day: the sun, whose rays slowly turn and reach for the cursor. */
import { reduceMotion } from '../env';
import { TAU } from '../util/math';
import { orb, proximity, type Frame, type Layer } from './view';

const RAYS = 12;

export const sun: Layer = {
  draw({ ctx, t }: Frame) {
    const s = orb();
    const near = proximity(s.x, s.y, 300);

    const glow = ctx.createRadialGradient(s.x, s.y, s.r * 0.5, s.x, s.y, s.r * (4 + near * 2));
    glow.addColorStop(0, `rgba(255, 226, 130, ${0.55 + near * 0.25})`);
    glow.addColorStop(1, 'rgba(255, 226, 130, 0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r * 6, 0, TAU);
    ctx.fill();

    const rotation = reduceMotion ? 0 : t * 0.0002;
    const start = s.r * 1.3;
    ctx.strokeStyle = `rgba(255, 205, 90, ${0.55 + near * 0.35})`;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    for (let i = 0; i < RAYS; i++) {
      const angle = rotation + (i * TAU) / RAYS;
      const length = s.r * (0.45 + near * 0.5) * (i % 2 ? 0.7 : 1);
      ctx.beginPath();
      ctx.moveTo(s.x + Math.cos(angle) * start, s.y + Math.sin(angle) * start);
      ctx.lineTo(s.x + Math.cos(angle) * (start + length), s.y + Math.sin(angle) * (start + length));
      ctx.stroke();
    }

    ctx.fillStyle = '#ffd35c';
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, TAU);
    ctx.fill();
  },
};
