/**
 * Night: the full moon, with its real maria and craters. The disc is painted
 * once per size on an offscreen canvas, then drawn each frame with a glow that
 * grows when the cursor comes close.
 */
import { rand, TAU } from '../util/math';
import { CRATERS, MARIA, TYCHO, type Spot } from './data';
import { orb, proximity, view, type Frame, type Layer } from './view';

/** A soft spot, foreshortened toward the limb (the moon is a sphere). */
function paintSpot(g: CanvasRenderingContext2D, r: number, [x, y, size]: Spot, inner: string, outer: string): void {
  const rho = Math.min(0.98, Math.hypot(x, y));
  const squash = Math.max(Math.sqrt(1 - rho * rho), 0.25);
  g.save();
  g.translate(x * r, y * r);
  g.rotate(Math.atan2(y, x));
  g.scale(squash, 1);
  const gradient = g.createRadialGradient(0, 0, 0, 0, 0, size * r);
  gradient.addColorStop(0, inner);
  gradient.addColorStop(0.6, inner);
  gradient.addColorStop(1, outer);
  g.fillStyle = gradient;
  g.beginPath();
  g.arc(0, 0, size * r, 0, TAU);
  g.fill();
  g.restore();
}

function offscreen(size: number, r: number, dpr: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const g = canvas.getContext('2d');
  if (!g) throw new Error('2D canvas unavailable');
  g.scale(dpr, dpr);
  g.translate(r, r);
  return [canvas, g];
}

function paintMoon(r: number, dpr: number): HTMLCanvasElement {
  const size = Math.ceil(r * 2 * dpr);
  const [canvas, g] = offscreen(size, r, dpr);

  // disc with limb darkening
  const disc = g.createRadialGradient(-r * 0.15, -r * 0.15, r * 0.1, 0, 0, r);
  disc.addColorStop(0, '#f6f3ec');
  disc.addColorStop(0.75, '#e4e0d6');
  disc.addColorStop(1, '#bdb8ad');
  g.fillStyle = disc;
  g.beginPath();
  g.arc(0, 0, r, 0, TAU);
  g.fill();
  g.save();
  g.beginPath();
  g.arc(0, 0, r, 0, TAU);
  g.clip();

  // maria: opaque on their own layer, laid down once at low alpha, so that
  // overlapping blobs merge into even plains
  const [maria, mg] = offscreen(size, r, dpr);
  for (const spot of MARIA) paintSpot(mg, r, spot, 'rgba(105, 110, 125, 1)', 'rgba(105, 110, 125, 0)');
  g.save();
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.globalAlpha = 0.5;
  g.drawImage(maria, 0, 0);
  g.restore();

  // highland texture
  for (let i = 0; i < 260; i++) {
    const angle = rand(0, TAU);
    const distance = Math.sqrt(Math.random()) * r;
    g.fillStyle = Math.random() < 0.5 ? 'rgba(90, 90, 100, 0.07)' : 'rgba(255, 255, 255, 0.08)';
    g.beginPath();
    g.arc(Math.cos(angle) * distance, Math.sin(angle) * distance, (rand(0.3, 1.4) * r) / 40, 0, TAU);
    g.fill();
  }

  // Tycho's ray system: thin, faint, fading out
  const [tx, ty] = [TYCHO[0] * r, TYCHO[1] * r];
  g.lineWidth = Math.max(0.4, r * 0.01);
  for (let i = 0; i < 22; i++) {
    const angle = (i / 22) * TAU + rand(-0.1, 0.1);
    const length = r * rand(0.25, 0.85);
    const ex = tx + Math.cos(angle) * length;
    const ey = ty + Math.sin(angle) * length;
    const ray = g.createLinearGradient(tx, ty, ex, ey);
    ray.addColorStop(0, 'rgba(255, 255, 255, 0.22)');
    ray.addColorStop(1, 'rgba(255, 255, 255, 0)');
    g.strokeStyle = ray;
    g.beginPath();
    g.moveTo(tx, ty);
    g.lineTo(ex, ey);
    g.stroke();
  }

  for (const crater of CRATERS) {
    const colour = crater.bright ? '255, 255, 255' : '95, 98, 110';
    const alpha = crater.bright ? 0.95 : 0.6;
    paintSpot(g, r, crater.spot, `rgba(${colour}, ${alpha})`, `rgba(${colour}, 0)`);
  }
  g.restore();
  return canvas;
}

let image: HTMLCanvasElement | null = null;

export const moon: Layer = {
  resize() {
    image = paintMoon(orb().r, view.dpr);
  },

  draw({ ctx }: Frame) {
    const m = orb();
    const near = proximity(m.x, m.y, 260);
    const glow = ctx.createRadialGradient(m.x, m.y, m.r * 0.8, m.x, m.y, m.r * (3 + near * 1.5));
    glow.addColorStop(0, `rgba(200, 220, 255, ${0.25 + near * 0.2})`);
    glow.addColorStop(1, 'rgba(200, 220, 255, 0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(m.x, m.y, m.r * 5, 0, TAU);
    ctx.fill();
    if (image) ctx.drawImage(image, m.x - m.r, m.y - m.r, m.r * 2, m.r * 2);
  },
};
