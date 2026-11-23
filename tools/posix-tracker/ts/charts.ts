/**
 * Charts of the overview and versions pages. The data comes from the page
 * (<script type="application/json" id="chart-data">); each chart is drawn
 * only if its <canvas> is on the page.
 */
import type { ChartConfig, ChartConstructor, Dataset, TooltipItem } from './chartjs';
import type { ChartData } from './types';

// Catppuccin Mocha, as the tracker's stylesheet
const TEXT = '#cdd6f4';
const GRID = 'rgba(205, 214, 244, 0.06)';
const MAUVE = '#cba6f7';
const MAUVE_FILL = 'rgba(203, 166, 247, 0.2)';
const GREEN = '#a6e3a1';
const SURFACE = '#45475a';
/** One colour per version (cycled). */
const VERSION_COLOURS = [
  '#89b4fa', '#a6e3a1', '#f9e2af', '#fab387', '#cba6f7',
  '#f5c2e7', '#94e2d5', '#f38ba8', '#eba0ac', '#74c7ec',
] as const;

const legend = { labels: { color: TEXT } };

function readData(): ChartData | null {
  const script = document.getElementById('chart-data');
  if (!script?.textContent) return null;
  return JSON.parse(script.textContent) as ChartData;
}

function draw(Chart: ChartConstructor, id: string, config: ChartConfig): void {
  const canvas = document.getElementById(id);
  if (canvas instanceof HTMLCanvasElement) new Chart(canvas, config);
}

/** Weighted progress over the releases. */
function historyConfig(data: ChartData): ChartConfig {
  return {
    type: 'line',
    data: {
      labels: [...data.labels],
      datasets: [{
        label: 'Total weighted %', data: [...data.percent],
        borderColor: MAUVE, backgroundColor: MAUVE_FILL, tension: 0.3, fill: true,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: { x: { ticks: { color: TEXT } }, y: { beginAtZero: true, max: 100, ticks: { color: TEXT } } },
      plugins: { legend },
    },
  };
}

/** Latest release: implemented vs remaining (weighted). */
function overviewConfig(data: ChartData): ChartConfig {
  const latest = data.percent[data.percent.length - 1] ?? 0;
  return {
    type: 'doughnut',
    data: {
      labels: ['Implemented (weighted)', 'Remaining'],
      datasets: [{ data: [latest, 100 - latest], backgroundColor: [GREEN, SURFACE], borderWidth: 0 }],
    },
    options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend } },
  };
}

/**
 * Symbols done per category, one bar per version. Each category is a
 * section of the x axis, separated from the next by an empty label.
 */
function categoriesConfig(data: ChartData): ChartConfig {
  const categories = Object.keys(data.categories);
  const labels: string[] = [];
  const position = new Map<number, string>(); // label index -> category
  categories.forEach((category, i) => {
    position.set(labels.length, category);
    labels.push(category);
    if (i < categories.length - 1) labels.push(''); // gap
  });

  const datasets: Dataset[] = data.labels.map((version, i) => {
    const values: (number | null)[] = labels.map(() => null);
    for (const [index, category] of position) {
      values[index] = data.categories[category]?.find((p) => p.version === version)?.done ?? 0;
    }
    return {
      label: version, data: values,
      backgroundColor: VERSION_COLOURS[i % VERSION_COLOURS.length] ?? MAUVE,
      barPercentage: 0.8, categoryPercentage: 0.7,
    };
  });

  return {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {
        x: { ticks: { color: TEXT }, grid: { color: GRID } },
        y: { beginAtZero: true, ticks: { color: TEXT }, grid: { color: GRID } },
      },
      plugins: {
        legend,
        tooltip: {
          callbacks: {
            // the category, also when hovering a gap
            title: (items: readonly TooltipItem[]) => position.get(items[0]?.dataIndex ?? -1) ?? '',
            label: (item: TooltipItem) => `${item.dataset.label ?? ''}: ${item.parsed.y} done`,
          },
        },
      },
    },
  };
}

export function initCharts(): void {
  const Chart = window.Chart;
  const data = readData();
  if (!Chart || !data) return; // CDN unreachable, or a page without charts
  draw(Chart, 'overviewChart', overviewConfig(data));
  draw(Chart, 'historyChart', historyConfig(data));
  draw(Chart, 'versionsChart', historyConfig(data));
  draw(Chart, 'categoriesChart', categoriesConfig(data));
}
