/**
 * Chart data written by app/generate.py (ChartData) into a
 * <script type="application/json" id="chart-data"> element of the page.
 */
export interface ChartPoint {
  readonly version: string;
  readonly done: number;
  readonly total: number;
}

export interface ChartData {
  readonly labels: readonly string[];
  readonly percent: readonly number[];
  /** Per category, one point per version. */
  readonly categories: Readonly<Record<string, readonly ChartPoint[]>>;
}
