/**
 * Boats of several kinds sailing on the footer waves from time to time. Each
 * is an SVG silhouette (bow pointing right) moved by CSS animations; colours
 * come from the stylesheet (.boat-<kind> .hull, .win, ...).
 */
import { reduceMotion } from './env';
import { element, removeAfterAnimation } from './util/dom';
import { pick, rand } from './util/math';

interface BoatModel {
  readonly viewBox: readonly [width: number, height: number];
  /** Display width in pixels on a wide screen. */
  readonly width: number;
  /** Slower than average (> 1) or faster (< 1). */
  readonly pace: number;
  readonly svg: string;
}

const windows = (count: number, x0: number, step: number, y: number, w: number, h: number): string =>
  Array.from({ length: count }, (_, i) => `<rect class="win" x="${x0 + i * step}" y="${y}" width="${w}" height="${h}"/>`).join('');

const CONTAINER_COLOURS = ['#c8553d', '#2f6db3', '#e0a33a', '#3d8b5a', '#c8553d', '#7a5ab8', '#2f6db3', '#e0a33a'];

const BOATS = {
  sailboat: {
    viewBox: [80, 70], width: 64, pace: 1,
    svg:
      '<rect class="mast" x="39" y="4" width="2" height="48"/>' +
      '<path class="sail" d="M42 6 L42 48 L72 48 Z"/>' +
      '<path class="sail alt" d="M38 12 L38 48 L14 48 Z"/>' +
      '<path class="hull" d="M4 50 L78 50 L68 64 L12 64 Z"/>',
  },
  fishing: {
    viewBox: [90, 60], width: 76, pace: 1,
    svg:
      '<rect class="mast" x="19" y="6" width="2" height="34"/>' +
      '<path class="rope" d="M20 8 L4 30"/>' +
      '<path class="flag" d="M21 6 L29 9 L21 12 Z"/>' +
      '<rect class="cabin" x="46" y="22" width="24" height="18" rx="2"/>' +
      windows(2, 50, 10, 27, 5, 5) +
      '<path class="hull" d="M2 40 L88 40 L80 54 L8 54 Z"/>',
  },
  ferry: {
    viewBox: [140, 60], width: 120, pace: 1,
    svg:
      '<rect class="funnel" x="62" y="2" width="12" height="16"/>' +
      '<rect class="stripe" x="62" y="6" width="12" height="4"/>' +
      '<path class="cabin" d="M40 16 H96 V26 H40 Z M20 26 H112 V38 H20 Z"/>' +
      windows(9, 26, 9.5, 29, 5, 4) +
      windows(5, 46, 10, 19, 5, 4) +
      '<path class="hull" d="M2 38 L138 34 L128 54 L10 54 Z"/>',
  },
  cargo: {
    viewBox: [170, 60], width: 150, pace: 1.4,
    svg:
      '<rect class="cabin" x="10" y="10" width="18" height="26"/>' +
      '<rect class="win" x="13" y="14" width="12" height="3"/>' +
      '<rect class="funnel" x="14" y="3" width="8" height="7"/>' +
      CONTAINER_COLOURS.map((colour, i) => {
        const tall = i % 3 === 1;
        return `<rect class="box" x="${34 + i * 15}" y="${tall ? 16 : 24}" width="14" height="${tall ? 20 : 12}" fill="${colour}"/>`;
      }).join('') +
      '<path class="hull" d="M2 36 L168 36 L156 54 L12 54 Z"/>',
  },
  skiff: {
    viewBox: [56, 44], width: 46, pace: 1,
    svg:
      '<path class="rope" d="M25 25 L52 4"/>' +
      '<path class="line" d="M52 4 Q54 18 53 34"/>' +
      '<circle class="person" cx="21" cy="17" r="3"/><path class="person" d="M17 15 H25 L23 13 H19 Z"/>' +
      '<rect class="person" x="19" y="20" width="5" height="10" rx="1"/>' +
      '<path class="hull" d="M2 30 L54 30 L47 40 L9 40 Z"/>',
  },
  rowboat: {
    viewBox: [50, 36], width: 40, pace: 1.2,
    svg:
      '<circle class="person" cx="24" cy="10" r="3"/><rect class="person" x="22" y="13" width="4" height="8" rx="1"/>' +
      '<path class="rope" d="M10 30 L34 16"/>' +
      '<path class="hull" d="M2 21 L48 21 L42 32 L8 32 Z"/>',
  },
} satisfies Record<string, BoatModel>;

type BoatKind = keyof typeof BOATS;
const KINDS = Object.keys(BOATS) as BoatKind[];

/** At most this many boats on the water at once. */
const MAX_BOATS = 2;

function launch(waves: Element): void {
  const kind = pick(KINDS);
  const model: BoatModel = BOATS[kind];
  const [vw, vh] = model.viewBox;
  const width = innerWidth < 700 ? model.width * 0.7 : model.width;

  const boat = element('div', `boat boat-${kind}${Math.random() < 0.5 ? ' rtl' : ''}`);
  boat.style.setProperty('--w', `${width}px`);
  boat.style.animationDuration = `${rand(38, 60) * model.pace}s`;
  boat.innerHTML =
    `<div class="boat-bob" style="animation-delay:${-rand(0, 4)}s">` +
    `<svg viewBox="0 0 ${vw} ${vh}" width="${width}" height="${(width * vh) / vw}">${model.svg}</svg></div>`;
  removeAfterAnimation(boat);
  waves.append(boat);
}

export function initBoats(): void {
  const waves = document.querySelector('.waves');
  if (!waves || reduceMotion) return;
  const sail = (): void => {
    if (waves.querySelectorAll('.boat').length < MAX_BOATS) launch(waves);
    setTimeout(sail, rand(12000, 28000));
  };
  setTimeout(sail, rand(1500, 4000));
}
