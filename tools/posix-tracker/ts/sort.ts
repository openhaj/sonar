/**
 * Sortable tables: clicking a `table.data th[data-sort]` header sorts the rows
 * by that column ("number" or "string"), toggling the direction. A cell's
 * `data-value` wins over its text; "3 / 7" sorts as 3/7.
 */

type SortType = 'number' | 'string';

function parseNumber(raw: string): number {
  const text = raw.trim();
  const fraction = /^(\d+)\s*\/\s*(\d+)$/.exec(text);
  if (fraction) return Number(fraction[1]) / Math.max(1, Number(fraction[2]));
  const value = parseFloat(text);
  return Number.isNaN(value) ? 0 : value;
}

function cellValue(row: HTMLTableRowElement, column: number): string {
  const cell = row.cells[column];
  if (!cell) return '';
  return cell.dataset['value'] ?? cell.textContent ?? '';
}

function sortBy(th: HTMLTableCellElement): void {
  const table = th.closest('table');
  const body = table?.tBodies[0];
  const headerRow = th.parentElement;
  if (!body || !headerRow) return;

  const column = th.cellIndex;
  const type: SortType = th.dataset['sort'] === 'number' ? 'number' : 'string';
  const direction = th.dataset['dir'] === 'asc' ? 'desc' : 'asc';
  for (const other of headerRow.querySelectorAll<HTMLElement>('th')) {
    if (other !== th) delete other.dataset['dir'];
  }
  th.dataset['dir'] = direction;

  const rows = Array.from(body.rows);
  rows.sort((a, b) => {
    const x = cellValue(a, column);
    const y = cellValue(b, column);
    const order = type === 'number' ? parseNumber(x) - parseNumber(y) : x.localeCompare(y);
    return direction === 'asc' ? order : -order;
  });
  body.append(...rows);
}

export function initSortableTables(): void {
  for (const th of document.querySelectorAll<HTMLTableCellElement>('table.data th[data-sort]')) {
    th.addEventListener('click', () => sortBy(th));
  }
}
