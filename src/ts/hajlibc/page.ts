/**
 * Fills projects/hajlibc/index.html from window.HAJLIBC_DATA (data.js).
 *
 * The page marks what to fill with attributes:
 *   data-fill="key"        text content
 *   data-fill-html="key"   HTML content (built here, values escaped)
 *   data-width="key"       a bar width, in percent
 *   data-needs="section"   hidden when the section has no data
 *   data-missing="section" shown when it has none (how to generate it)
 */
import { escapeHtml as esc } from '../util/dom';
import { meter, percent, plural, shortDate } from './format';
import type { CoverageSummary, DocsSummary, HajlibcData, PosixSummary, RepoInfo, TestSummary } from './types';

type Section = 'posix' | 'tests' | 'coverage' | 'docs';

/** What to put in the page, by data-* key. */
class Fill {
  readonly text = new Map<string, string>();
  readonly html = new Map<string, string>();
  readonly width = new Map<string, number>();

  apply(root: ParentNode): void {
    for (const el of root.querySelectorAll<HTMLElement>('[data-fill]')) {
      const value = this.text.get(el.dataset['fill'] ?? '');
      if (value !== undefined) el.textContent = value;
    }
    for (const el of root.querySelectorAll<HTMLElement>('[data-fill-html]')) {
      const value = this.html.get(el.dataset['fillHtml'] ?? '');
      if (value !== undefined) el.innerHTML = value;
    }
    for (const el of root.querySelectorAll<HTMLElement>('[data-width]')) {
      const value = this.width.get(el.dataset['width'] ?? '');
      if (value !== undefined) el.style.width = `${value}%`;
    }
  }
}

/* ----- sections ----- */

function fillRepo(fill: Fill, repo: RepoInfo): void {
  fill.text.set('release', repo.latest_release ?? '-');
  fill.text.set('release-date', shortDate(repo.latest_release_date));
  fill.text.set('commit', repo.commit_short);
  fill.text.set('commit-info', `${repo.branch} · ${shortDate(repo.commit_date)}`);
  fill.text.set('commits', plural(repo.commits, 'commit'));
  fill.text.set('releases', plural(repo.releases, 'release'));
  fill.text.set('sources', plural(repo.sources.c + repo.sources.asm, 'file'));
  fill.text.set('sources-detail', `${repo.sources.c} C · ${repo.sources.asm} asm · ${repo.sources.headers} headers`);
}

function fillPosix(fill: Fill, posix: PosixSummary): void {
  const versions = posix.versions;
  const dev = versions[versions.length - 1];
  if (!dev) return;
  const releases = versions.filter((v) => v.name !== 'dev');
  const latest = releases[releases.length - 1];

  fill.text.set('posix-dev', percent(dev.percent));
  fill.width.set('posix-dev', dev.percent);
  fill.text.set(
    'posix-dev-label',
    `of POSIX.1-2024 on the development branch (weighted), ` +
      `${dev.headers.present} of ${dev.headers.total} headers provided, ${dev.headers.complete} complete`,
  );
  if (latest) {
    const delta = dev.percent - latest.percent;
    const since = Math.abs(delta) >= 0.01 ? ` · ${delta > 0 ? '+' : ''}${delta.toFixed(2)} points since` : '';
    fill.text.set('posix-release', `Latest release v${latest.name}: ${percent(latest.percent)}${since}`);
  }

  fill.html.set(
    'posix-cats',
    Object.entries(posix.categories)
      .map(([key, label]) => {
        const t = dev.totals[key] ?? { done: 0, total: 0 };
        const share = t.total ? (100 * t.done) / t.total : 0;
        return `<div class="cat"><span>${esc(label)}</span><span class="num">${t.done} / ${t.total}</span>${meter(share)}</div>`;
      })
      .join(''),
  );

  const highest = Math.max(...versions.map((v) => v.percent), 1);
  fill.html.set(
    'posix-history',
    versions
      .map(
        (v) =>
          `<div class="col" title="${esc(v.name)}: ${percent(v.percent, 2)}">` +
          `<span class="val">${percent(v.percent, 0)}</span>` +
          `<span class="bar" style="height:${((100 * v.percent) / highest).toFixed(1)}%"></span>` +
          `<span class="lbl">${esc(v.name === 'dev' ? 'dev' : `v${v.name}`)}</span></div>`,
      )
      .join(''),
  );
}

function fillTests(fill: Fill, tests: TestSummary): void {
  const s = tests.summary;
  const count = (key: string): number => s[key] ?? 0;
  const failing = count('fail') + count('crash') + count('timeout') + count('error');
  const notBuilt = count('unavailable');

  fill.text.set(
    'tests-intro',
    `${plural(tests.total, 'test')} (${tests.checks} checks) on ${plural(tests.functions, 'function')}, ` +
      `run by blåsix against ${tests.target} - ${failing ? `${failing} failing` : 'all passing'}` +
      `${notBuilt ? `, ${notBuilt} not built` : ''}, ${shortDate(tests.generated)}.`,
  );

  const tiles: readonly [string, number, string][] = [
    ['pass', count('pass'), 'pass'],
    ['fail', failing, 'fail'],
    ['skip', count('skip'), 'skip'],
    ['interfaces', tests.interfaces, 'required interfaces'],
    ['present', tests.probes['present'] ?? 0, 'interfaces present'],
  ];
  fill.html.set(
    'tests-tiles',
    tiles.map(([cls, value, label]) => `<div class="tile ${cls}"><b>${value}</b><span>${label}</span></div>`).join(''),
  );

  const rows = Object.entries(tests.headers)
    .map(([header, c]) => {
      const required = c.required ?? 0;
      const verified = c.verified ?? 0;
      const share = required ? (100 * verified) / required : 0;
      return `<tr><td><code>${esc(header)}</code></td><td class="num">${verified} / ${required}</td><td>${meter(share)}</td></tr>`;
    })
    .join('');
  fill.html.set(
    'tests-headers',
    `<table class="mini"><tbody>${rows}</tbody></table>` +
      `<p class="muted small">Verified: present and passing all its tests.</p>`,
  );
}

function fillCoverage(fill: Fill, coverage: CoverageSummary): void {
  fill.text.set('cov-total', percent(coverage.percent));
  fill.width.set('cov-total', coverage.percent);
  fill.text.set('cov-detail', `${coverage.hit} of ${coverage.lines} lines executed by the tests`);
  const rows = Object.entries(coverage.dirs)
    .sort((a, b) => b[1].lines - a[1].lines)
    .map(([dir, d]) => `<tr><td><code>${esc(dir)}/</code></td><td class="num">${percent(d.percent, 0)}</td><td>${meter(d.percent)}</td></tr>`)
    .join('');
  fill.html.set('cov-dirs', `<table class="mini"><tbody>${rows}</tbody></table>`);
}

function fillDocs(fill: Fill, docs: DocsSummary): void {
  fill.text.set(
    'docs-intro',
    `${docs.declarations} documented declarations in ${plural(docs.headers.length, 'header')}, ` +
      `extracted from the comments of the headers.`,
  );
  fill.html.set(
    'docs-headers',
    docs.headers
      .map(
        (h) =>
          `<a class="chip" href="docs/${esc(h.slug)}.html" title="${esc(h.brief)}">` +
          `<code>&lt;${esc(h.name)}&gt;</code><span>${h.count}</span></a>`,
      )
      .join(''),
  );
}

/* ----- init ----- */

export function initHajlibcPage(): void {
  const main = document.querySelector('main.hajlibc');
  if (!main) return;

  const data: HajlibcData = window.HAJLIBC_DATA ?? {};
  const fill = new Fill();

  if (data.repo) {
    fillRepo(fill, data.repo);
    const facts = document.getElementById('facts');
    if (facts) facts.hidden = false;
  }
  if (data.posix) fillPosix(fill, data.posix);
  if (data.tests) fillTests(fill, data.tests);
  if (data.coverage) fillCoverage(fill, data.coverage);
  if (data.docs) fillDocs(fill, data.docs);
  if (data.generated) {
    const from = data.repo ? ` from hajlibc ${data.repo.commit_short} (“${data.repo.commit_subject}”)` : '';
    fill.text.set('generated', `Generated ${shortDate(data.generated)}${from}.`);
  }

  fill.apply(main);

  const available: Record<Section, boolean> = {
    posix: (data.posix?.versions.length ?? 0) > 0,
    tests: Boolean(data.tests),
    coverage: Boolean(data.coverage),
    docs: Boolean(data.docs),
  };
  const has = (name: string | undefined): boolean => name !== undefined && name in available && available[name as Section];
  for (const el of main.querySelectorAll<HTMLElement>('[data-needs]')) el.hidden = !has(el.dataset['needs']);
  for (const el of main.querySelectorAll<HTMLElement>('[data-missing]')) el.hidden = has(el.dataset['missing']);
}
