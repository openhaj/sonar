/**
 * Shape of window.HAJLIBC_DATA, written to data.js by tools/hajlibc/pages.py.
 * Every section is null when its input was not generated.
 */

export interface Counts {
  readonly done: number;
  readonly total: number;
}

export interface PosixVersion {
  readonly name: string;
  readonly commit: string | null;
  readonly percent: number;
  readonly totals: Readonly<Record<string, Counts>>;
  readonly headers: { readonly total: number; readonly present: number; readonly complete: number };
}

export interface PosixSummary {
  readonly generated: string;
  readonly categories: Readonly<Record<string, string>>;
  readonly versions: readonly PosixVersion[];
}

export interface RepoInfo {
  readonly url: string;
  readonly commit: string;
  readonly commit_short: string;
  readonly commit_date: string;
  readonly commit_subject: string;
  readonly branch: string;
  readonly latest_release: string | null;
  readonly latest_release_date: string | null;
  readonly releases: number;
  readonly commits: number;
  readonly sources: { readonly c: number; readonly asm: number; readonly headers: number };
}

export interface HeaderSummary {
  readonly header: string;
  readonly slug: string;
  readonly required: number;
  readonly present: number;
  readonly verified: number;
  readonly failing: number;
  readonly missing: number;
  readonly untested: number;
  readonly unbuilt: number;
}

/** blåsix's run: statuses of the tests, verdicts on the interfaces. */
export interface TestSummary {
  readonly target: string;
  readonly libc: string;
  readonly mode: string;
  readonly generated: string;
  /** tests per status: pass fail skip unimplemented crash timeout error (+ unavailable units) */
  readonly summary: Readonly<Record<string, number>>;
  readonly total: number;
  readonly checks: number;
  readonly functions: number;
  readonly interfaces: number;
  /** interfaces per verdict: verified failing missing broken unbuilt untested */
  readonly verdicts: Readonly<Record<string, number>>;
  readonly headers: readonly HeaderSummary[];
}

export interface Ratio {
  readonly found: number;
  readonly hit: number;
  readonly percent: number;
}

export interface CategoryCoverage {
  readonly name: string;
  readonly slug: string;
  readonly files: number;
  readonly lines: Ratio;
  readonly functions: Ratio;
  readonly branches: Ratio;
}

export interface CoverageSummary {
  readonly generated: string;
  readonly files: number;
  readonly lines: Ratio;
  readonly functions: Ratio;
  readonly branches: Ratio;
  readonly categories: readonly CategoryCoverage[];
}

export interface DocsSummary {
  readonly declarations: number;
  readonly headers: readonly { readonly name: string; readonly slug: string; readonly brief: string; readonly count: number }[];
}

export interface HajlibcData {
  readonly generated?: string;
  readonly repo?: RepoInfo | null;
  readonly posix?: PosixSummary | null;
  readonly tests?: TestSummary | null;
  readonly coverage?: CoverageSummary | null;
  readonly docs?: DocsSummary | null;
}

declare global {
  interface Window {
    HAJLIBC_DATA?: HajlibcData;
  }
}
