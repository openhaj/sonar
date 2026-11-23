/** The #filter input hides the rows of `table.data` that don't contain its text. */

export function initFilter(): void {
  const input = document.querySelector<HTMLInputElement>('input#filter');
  if (!input) return;
  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();
    for (const row of document.querySelectorAll<HTMLTableRowElement>('table.data tbody tr')) {
      row.hidden = !(row.textContent ?? '').toLowerCase().includes(query);
    }
  });
}
