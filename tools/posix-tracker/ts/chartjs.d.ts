/**
 * The part of Chart.js (loaded from a CDN as the global `Chart`, see
 * templates/base.html) that the tracker uses.
 */

export interface TooltipItem {
  readonly dataIndex: number;
  readonly dataset: { readonly label?: string };
  readonly parsed: { readonly y: number };
}

export interface Dataset {
  label?: string;
  data: (number | null)[];
  borderColor?: string;
  backgroundColor?: string | string[];
  borderWidth?: number;
  tension?: number;
  fill?: boolean;
  barPercentage?: number;
  categoryPercentage?: number;
}

interface Axis {
  beginAtZero?: boolean;
  max?: number;
  ticks?: { color?: string };
  grid?: { color?: string };
}

export interface ChartConfig {
  type: 'line' | 'bar' | 'doughnut';
  data: { labels: string[]; datasets: Dataset[] };
  options?: {
    responsive?: boolean;
    maintainAspectRatio?: boolean;
    animation?: boolean;
    scales?: { x?: Axis; y?: Axis };
    plugins?: {
      legend?: { labels?: { color?: string } };
      tooltip?: {
        callbacks?: {
          title?: (items: readonly TooltipItem[]) => string;
          label?: (item: TooltipItem) => string;
        };
      };
    };
  };
}

export interface ChartInstance {
  destroy(): void;
}

export type ChartConstructor = new (canvas: HTMLCanvasElement, config: ChartConfig) => ChartInstance;

declare global {
  interface Window {
    Chart?: ChartConstructor;
  }
}
