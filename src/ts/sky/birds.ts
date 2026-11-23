/**
 * Day: birds drawn as simple "v" shapes. They cruise left to right,
 * alternating flapping and gliding, and drift away from the cursor with a few
 * extra wing beats (no panic).
 */
import { reduceMotion } from '../env';
import { rand, TAU } from '../util/math';
import { isNarrow, pointer, view, type Frame, type Layer } from './view';

interface Bird {
  x: number;
  y: number;
  cruiseY: number;
  vx: number;
  vy: number;
  size: number;
  phase: number; // wing beat
  cycle: number; // flap / glide cycle, in seconds
}

const CRUISE_SPEED = 1.2;
const MAX_SPEED = 3.2;
const FEAR_RADIUS = 170;
const FLAP_SECONDS = 2.5;
const CYCLE_SECONDS = 4.5;

let birds: Bird[] = [];

function newBird(x: number): Bird {
  const y = rand(view.height * 0.08, view.height * 0.5);
  return { x, y, cruiseY: y, vx: rand(1.0, 1.4), vy: 0, size: rand(6, 9), phase: rand(0, TAU), cycle: rand(0, 6) };
}

/** Update one bird; returns how alarmed it is (0..1). */
function fly(b: Bird, dt: number): number {
  let alarm = 0;
  const dx = b.x - pointer.x;
  const dy = b.y - pointer.y;
  const distance = Math.hypot(dx, dy);
  if (distance < FEAR_RADIUS && distance > 0.1) {
    alarm = 1 - distance / FEAR_RADIUS;
    b.vx += (dx / distance) * alarm * 0.14 * dt;
    b.vy += (dy / distance) * alarm * 0.14 * dt;
  }
  b.vx += (CRUISE_SPEED - b.vx) * 0.01 * dt; // back to cruising speed
  b.vy += (b.cruiseY - b.y) * 0.0004 * dt; // back to cruising height
  b.vy *= Math.pow(0.97, dt);
  const speed = Math.hypot(b.vx, b.vy);
  if (speed > MAX_SPEED) {
    b.vx *= MAX_SPEED / speed;
    b.vy *= MAX_SPEED / speed;
  }
  b.x += b.vx * dt;
  b.y += b.vy * dt;
  if (b.x > view.width + 30) Object.assign(b, newBird(-30));
  if (b.x < -40) b.x = view.width + 30;

  b.cycle = (b.cycle + dt / 60) % CYCLE_SECONDS;
  if (isFlapping(b, alarm)) b.phase += (0.17 + alarm * 0.12) * dt;
  return alarm;
}

/** Flapping part of the cycle; a disturbed bird keeps flapping. */
function isFlapping(b: Bird, alarm: number): boolean {
  return b.cycle < FLAP_SECONDS || alarm > 0.2;
}

export const birdLayer: Layer = {
  resize() {
    const count = isNarrow() ? 5 : 9;
    if (birds.length !== count) birds = Array.from({ length: count }, () => newBird(rand(0, view.width)));
  },

  draw({ ctx, dt }: Frame) {
    ctx.strokeStyle = 'rgba(30, 58, 96, 0.75)';
    ctx.lineWidth = 1.6;
    ctx.lineJoin = 'round';
    for (const b of birds) {
      const alarm = reduceMotion ? 0 : fly(b, dt);
      const wing = isFlapping(b, alarm) ? Math.sin(b.phase) * b.size * 0.4 : b.size * 0.12;
      const x = b.x - pointer.parallaxX * 8;
      const y = b.y - pointer.parallaxY * 6;
      ctx.beginPath();
      ctx.moveTo(x - b.size, y - wing);
      ctx.lineTo(x, y + b.size * 0.2);
      ctx.lineTo(x + b.size, y - wing);
      ctx.stroke();
    }
  },
};
