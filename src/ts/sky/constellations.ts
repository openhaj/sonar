/**
 * Night: real constellations, at their real place on a sky map (right
 * ascension horizontally, east on the left; declination from +90° at the top
 * to -45°). Positions and shapes share one scale, so sizes and distances are
 * true to the sky. The map is wider than the screen and turns slowly, like the
 * real sky, so every constellation passes by. The one closest to the cursor is
 * drawn with its lines, and named in a small label.
 */
import { reduceMotion } from '../env';
import { element } from '../util/dom';
import { rand, TAU } from '../util/math';
import { CONSTELLATIONS, type ConstellationData, type Segment, type Star } from './data';
import { pointer, view, type Frame, type Layer } from './view';

type Vec3 = readonly [number, number, number];

interface ProjectedStar {
  /** Offset from the constellation centre, in radians on the tangent plane. */
  readonly x: number;
  readonly y: number;
  readonly mag: number;
  readonly phase: number;
}

interface Constellation {
  readonly name: string;
  readonly lines: readonly Segment[];
  readonly stars: readonly ProjectedStar[];
  /** Centre on the sky, in degrees. */
  readonly ra: number;
  readonly dec: number;
  /** Highlight, eased from 0 to 1. */
  hover: number;
}

/** Right ascension at the left edge of the screen on load (Gemini / Orion side). */
const ORIGIN_RA = 150;
/** Declination range shown, top to bottom. */
const DEC_TOP = 90;
const DEC_SPAN = 135;

/* ----- projection ----- */

const DEG = Math.PI / 180;
const dot = (u: Vec3, v: Vec3): number => u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
const cross = (u: Vec3, v: Vec3): Vec3 => [
  u[1] * v[2] - u[2] * v[1],
  u[2] * v[0] - u[0] * v[2],
  u[0] * v[1] - u[1] * v[0],
];
const normalize = (v: Vec3): Vec3 => {
  const length = Math.hypot(...v);
  return [v[0] / length, v[1] / length, v[2] / length];
};
const toVector = ([ra, dec]: Star): Vec3 => {
  const a = ra * 15 * DEG;
  const d = dec * DEG;
  return [Math.cos(d) * Math.cos(a), Math.cos(d) * Math.sin(a), Math.sin(d)];
};

/**
 * Gnomonic projection around the constellation's own centre: true shape,
 * north up, east to the left as seen from the ground.
 */
function project(data: ConstellationData): Constellation {
  const vectors = data.stars.map(toVector);
  const sum = vectors.reduce<Vec3>((s, v) => [s[0] + v[0], s[1] + v[1], s[2] + v[2]], [0, 0, 0]);
  const centre = normalize(sum);
  const east = normalize([-centre[1], centre[0], 0]);
  const north = cross(centre, east);

  const raw = vectors.map((v, i) => {
    const k = dot(v, centre);
    return { x: -dot(v, east) / k, y: -dot(v, north) / k, mag: data.stars[i]?.[2] ?? 6 };
  });
  const xs = raw.map((p) => p.x);
  const ys = raw.map((p) => p.y);
  const midX = (Math.min(...xs) + Math.max(...xs)) / 2;
  const midY = (Math.min(...ys) + Math.max(...ys)) / 2;

  return {
    name: data.name,
    lines: data.lines,
    stars: raw.map((p) => ({ x: p.x - midX, y: p.y - midY, mag: p.mag, phase: rand(0, TAU) })),
    ra: ((Math.atan2(centre[1], centre[0]) / DEG) + 360) % 360,
    dec: Math.asin(centre[2]) / DEG,
    hover: 0,
  };
}

const constellations: readonly Constellation[] = CONSTELLATIONS.map(project);

/* ----- label ----- */

// A small fixed label in the bottom-left corner: always readable, never over
// the content.
const label = element('div', 'sky-label', { 'aria-hidden': 'true' });
document.body.append(label);
let labelled: Constellation | null = null;

function showLabel(c: Constellation | null): void {
  if (c === labelled) return;
  labelled = c;
  if (c) label.textContent = `✦ ${c.name}`;
  label.classList.toggle('show', c !== null);
}

/* ----- layer ----- */

/** Sky rotation, in pixels. */
let turn = 0;

interface Placement {
  readonly c: Constellation;
  readonly x: number;
  readonly y: number;
}

/** Map scale: the declination range fills the height, 360° at least the width. */
function pixelsPerDegree(): number {
  return Math.max((view.height * 0.85) / DEC_SPAN, view.width / 360);
}

function place(dt: number): Placement[] {
  const pxPerDeg = pixelsPerDegree();
  const skyWidth = 360 * pxPerDeg;
  const top = view.height * 0.06;
  if (!reduceMotion) turn = (turn + 0.09 * dt) % skyWidth;

  const placements: Placement[] = [];
  for (const c of constellations) {
    const base = ((((ORIGIN_RA - c.ra) / 360) % 1) + 1) % 1 * skyWidth + turn;
    const y = top + (DEC_TOP - c.dec) * pxPerDeg - pointer.parallaxY * 22;
    for (const wrap of [-1, 0, 1]) {
      const x = (base % skyWidth) + wrap * skyWidth - pointer.parallaxX * 30;
      if (x > -0.2 * view.width && x < 1.2 * view.width) placements.push({ c, x, y });
    }
  }
  return placements;
}

function closestTo(placements: readonly Placement[]): Constellation | null {
  if (!pointer.onPage) return null;
  let best: Constellation | null = null;
  let bestDistance = Infinity;
  for (const { c, x, y } of placements) {
    const d = Math.hypot(x - pointer.x, y - pointer.y);
    if (d < bestDistance) {
      bestDistance = d;
      best = c;
    }
  }
  return best;
}

export const constellationLayer: Layer = {
  draw({ ctx, t, dt }: Frame) {
    const placements = place(dt);
    const focused = closestTo(placements);
    showLabel(focused);
    for (const c of constellations) c.hover += ((c === focused ? 1 : 0) - c.hover) * Math.min(1, 0.08 * dt);

    const scale = pixelsPerDegree() / DEG; // star offsets are in radians

    for (const { c, x, y } of placements) {
      const points = c.stars.map((s) => ({ x: x + s.x * scale, y: y + s.y * scale, star: s }));

      if (c.hover > 0.01) {
        ctx.strokeStyle = `rgba(150, 195, 255, ${0.55 * c.hover})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const [from, to] of c.lines) {
          const a = points[from];
          const b = points[to];
          if (!a || !b) continue;
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
        }
        ctx.stroke();
      }

      for (const { x: px, y: py, star } of points) {
        const twinkle = reduceMotion ? 1 : 0.85 + 0.15 * Math.sin(t * 0.0015 + star.phase);
        const r = Math.max(0.8, 2.6 - star.mag * 0.42) * (1 + c.hover * 0.25);
        const alpha = Math.min(1, (1.15 - star.mag * 0.14) * twinkle + c.hover * 0.3);
        const glow = ctx.createRadialGradient(px, py, 0, px, py, r * 4);
        glow.addColorStop(0, `rgba(200, 220, 255, ${alpha * 0.35})`);
        glow.addColorStop(1, 'rgba(200, 220, 255, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(px, py, r * 4, 0, TAU);
        ctx.fill();
        ctx.fillStyle = `rgba(248, 251, 255, ${alpha})`;
        ctx.beginPath();
        ctx.arc(px, py, r, 0, TAU);
        ctx.fill();
      }
    }
  },

  hide() {
    showLabel(null);
  },
};
