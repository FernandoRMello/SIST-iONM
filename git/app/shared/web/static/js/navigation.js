(() => {
  const search = document.querySelector('[data-nav-search]');
  if (!search) return;

  const items = [...document.querySelectorAll('[data-nav-item]')];
  const groups = [...document.querySelectorAll('[data-nav-group]')];

  search.addEventListener('input', () => {
    const term = search.value.trim().toLocaleLowerCase('pt-BR');
    items.forEach((item) => {
      item.hidden = Boolean(term) && !item.dataset.navLabel.includes(term);
    });
    groups.forEach((group) => {
      group.hidden = !group.querySelector('[data-nav-item]:not([hidden])');
    });
  });

  search.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowDown') return;
    const visibleItem = items.find((item) => !item.hidden);
    if (visibleItem) {
      event.preventDefault();
      visibleItem.focus();
    }
  });

  document.querySelector('.ui-navigation')?.addEventListener('click', () => {
    document.querySelector('[data-action="close-sidebar"]')?.click();
  });
})();
