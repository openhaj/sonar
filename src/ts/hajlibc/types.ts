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

export interface HeaderConformance {
  readonly required?: number;
  readonly present?: number;
  readonly tested?: number;
  readonly verified?: number;
}

export interface TestSummary {
  readonly target: string;
  readonly libc: string;
  readonly generated: string;
  readonly summary: Readonly<Record<string, number>>;
  readonly total: number;
  readonly checks: number;
  readonly functions: number;
  readonly interfaces: number;
  readonly probes: Readonly<Record<string, number>>;
  readonly headers: Readonly<Record<string, HeaderConformance>>;
}

export interface CoverageSummary {
  readonly generated: string;
  readonly lines: number;
  readonly hit: number;
  readonly percent: number;
  readonly dirs: Readonly<Record<string, { readonly lines: number; readonly hit: number; readonly percent: number }>>;
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
