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
  const verdict = (key: string): number => tests.verdicts[key] ?? 0;
  const failing = count('fail') + count('crash') + count('timeout') + count('error');

  fill.text.set(
    'tests-intro',
    `${plural(tests.total, 'test')} (${tests.checks} checks) on the ${tests.interfaces} interfaces ` +
      `${tests.target} requires, run by blåsix - ${failing ? `${failing} failing` : 'none failing'}, ` +
      `${verdict('missing')} interfaces not implemented yet, ${shortDate(tests.generated)}.`,
  );

  const tiles: readonly [string, number, string, string][] = [
    ['v-verified', verdict('verified'), 'verified', 'present, tests ran and every one passed'],
    ['v-failing', verdict('failing'), 'failing', 'a test failed'],
    ['v-missing', verdict('missing'), 'interfaces not implemented', 'not declared by the header or not defined by the library'],
    ['v-untested', verdict('untested') + verdict('unbuilt') + verdict('broken'), 'no result', 'untested, or its tests did not build'],
    ['pass', count('pass'), 'tests passed', 'every check passed'],
    ['fail', failing, 'tests failed', 'fail, crash, timeout or error'],
    ['skip', count('skip'), 'tests skipped', 'could not run here (environment)'],
    ['unimplemented', count('unimplemented'), 'tests not implemented', 'could not run: the libc lacks what it needs'],
  ];
  fill.html.set(
    'tests-tiles',
    tiles
      .map(([cls, value, label, help]) => `<div class="tile ${cls}" title="${esc(help)}"><b>${value}</b><span>${esc(label)}</span></div>`)
      .join(''),
  );

  const rows = tests.headers
    .map((h) => {
      const share = h.required ? (100 * h.verified) / h.required : 0;
      return (
        `<tr><td><a href="tests/${esc(h.slug)}.html"><code>${esc(h.header)}</code></a></td>` +
        `<td class="num">${h.verified} / ${h.required}</td><td>${meter(share)}</td></tr>`
      );
    })
    .join('');
  fill.html.set(
    'tests-headers',
    `<table class="mini"><tbody>${rows}</tbody></table>` +
      `<p class="muted small">Verified: present, and every test of it ran and passed.</p>`,
  );
}

function fillCoverage(fill: Fill, coverage: CoverageSummary): void {
  fill.text.set('cov-total', percent(coverage.lines.percent));
  fill.width.set('cov-total', coverage.lines.percent);
  fill.text.set(
    'cov-detail',
    `${coverage.lines.hit} of ${coverage.lines.found} lines of the ${coverage.files} files of the library ` +
      `run by the tests · functions ${percent(coverage.functions.percent, 0)} · branches ${percent(coverage.branches.percent, 0)}`,
  );
  const rows = [...coverage.categories]
    .sort((a, b) => b.lines.found - a.lines.found)
    .slice(0, 10)
    .map(
      (c) =>
        `<tr><td><a href="coverage/${esc(c.slug)}.html"><code>${esc(c.name)}</code></a></td>` +
        `<td class="num">${percent(c.lines.percent, 0)}</td><td>${meter(c.lines.percent)}</td></tr>`,
    )
    .join('');
  const more = coverage.categories.length > 10 ? `<p class="muted small">The ${coverage.categories.length - 10} smaller categories are in the report.</p>` : '';
  fill.html.set('cov-dirs', `<table class="mini"><tbody>${rows}</tbody></table>${more}`);
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
