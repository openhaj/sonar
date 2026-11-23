/**
 * Script of the POSIX tracker's pages, bundled into static/js/tracker.js by
 * the site's main.py (step posix). Loaded with `defer` after Chart.js.
 */
import { initCharts } from './charts';
import { initFilter } from './filter';
import { initSortableTables } from './sort';

initSortableTables();
initFilter();
initCharts();
