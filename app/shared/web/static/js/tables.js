(() => {
  function filterTable(input) {
    const tableId = input.dataset.tableSearch;
    const table = tableId ? document.getElementById(tableId) : null;
    if (!table) return;

    const term = input.value.trim().toLocaleLowerCase('pt-BR');
    let visibleRows = 0;
    table.querySelectorAll('tbody tr').forEach((row) => {
      const matches = row.textContent.toLocaleLowerCase('pt-BR').includes(term);
      row.hidden = !matches;
      if (matches) visibleRows += 1;
    });

    const feedback = document.querySelector(`[data-table-no-results="${tableId}"]`);
    if (feedback) {
      feedback.hidden = visibleRows > 0;
      feedback.textContent = visibleRows ? '' : 'Nenhum registro encontrado nesta página.';
    }
  }

  function init() {
    document.querySelectorAll('[data-table-search]').forEach((input) => {
      input.addEventListener('input', () => filterTable(input));
    });
  }

  window.addEventListener('DOMContentLoaded', init);
})();
