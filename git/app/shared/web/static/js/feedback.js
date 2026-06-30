(() => {
  document.addEventListener('click', (event) => {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    if (target.dataset.action === 'print') window.print();
    if (target.dataset.action === 'toggle-password') {
      const input = document.getElementById(target.getAttribute('aria-controls'));
      if (!input) return;
      const revealing = input.type === 'password';
      input.type = revealing ? 'text' : 'password';
      target.setAttribute('aria-label', revealing ? 'Ocultar senha' : 'Mostrar senha');
    }
  });
})();
