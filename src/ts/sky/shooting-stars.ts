/**
 * Night: a shooting star every few seconds. Clicking right on its head (it is
 * hard on purpose) bursts it into sparks and triggers the easter egg.
 */
import { reduceMotion } from '../env';
import { makeAWish } from '../easter-egg';
import { currentTheme } from '../theme';
import { rand, TAU } from '../util/math';
import { view, type Frame, type Layer } from './view';

interface ShootingStar {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number; // 1 -> 0
}

interface Spark {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  hue: number;
}

/** Length of the trail, in frames of travel. */
const TAIL = 28;
/** How close to the head a click must land, in pixels. */
const CATCH_RADIUS = 12;

let star: ShootingStar | null = null;
let nextAt = 4000;
let sparks: Spark[] = [];

function launch(): ShootingStar {
  const direction = Math.random() < 0.5 ? 1 : -1;
  return {
    x: direction > 0 ? rand(view.width * 0.05, view.width * 0.5) : rand(view.width * 0.5, view.width * 0.95),
    y: rand(view.height * 0.02, view.height * 0.3),
    vx: direction * rand(5.5, 7),
    vy: rand(2, 3),
    life: 1,
  };
}

function burst(x: number, y: number): void {
  for (let i = 0; i < 40; i++) {
    const angle = rand(0, TAU);
    const speed = rand(1, 4);
    sparks.push({ x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 1, hue: rand(190, 230) });
  }
}

addEventListener('pointerdown', (event) => {
  if (!star || currentTheme() !== 'dark') return;
  if (Math.hypot(event.clientX - star.x, event.clientY - star.y) > CATCH_RADIUS) return;
  star = null;
  nextAt = performance.now() + 6000;
  burst(event.clientX, event.clientY);
  makeAWish();
});

export const shootingStars: Layer = {
  draw({ ctx, t, dt }: Frame) {
    if (reduceMotion) return;
    if (!star && t > nextAt) star = launch();
    if (!star) return;

    const s = star;
    const alpha = Math.min(1, s.life * 2.5, (1 - s.life) * 12);
    const endX = s.x - s.vx * TAIL;
    const endY = s.y - s.vy * TAIL;
    const trail = ctx.createLinearGradient(s.x, s.y, endX, endY);
    trail.addColorStop(0, `rgba(255, 255, 255, ${alpha})`);
    trail.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.strokeStyle = trail;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
    ctx.beginPath();
    ctx.arc(s.x, s.y, 1.8, 0, TAU);
    ctx.fill();

    s.x += s.vx * dt;
    s.y += s.vy * dt;
    s.life -= 0.006 * dt;
    if (s.life <= 0 || s.x > view.width + 200 || s.x < -200) {
      star = null;
      nextAt = t + rand(4000, 9000);
    }
  },
};

/** Sparks of a caught star: drawn in every theme until they fade. */
export const sparkLayer: Layer = {
  draw({ ctx, dt }: Frame) {
    if (sparks.length === 0) return;
    for (const p of sparks) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 0.04 * dt;
      p.vx *= 0.98;
      p.life -= 0.015 * dt;
      ctx.fillStyle = `hsla(${p.hue}, 90%, 85%, ${Math.max(0, p.life)})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.8, 0, TAU);
      ctx.fill();
    }
    sparks = sparks.filter((p) => p.life > 0);
  },
};
