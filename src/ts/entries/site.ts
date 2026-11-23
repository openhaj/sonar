/**
 * Bundle loaded on every page (dist/assets/js/site.js): theme toggle,
 * interactive sky and boats.
 */
import { initBoats } from '../boats';
import { initSky } from '../sky';
import { initThemeToggle } from '../theme';

const sky = initSky();
initThemeToggle(() => sky.redraw());
initBoats();
