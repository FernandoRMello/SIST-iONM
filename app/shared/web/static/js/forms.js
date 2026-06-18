(() => {
  function confirmAction(event) {
    const target = event.currentTarget;
    const message = target.dataset.confirm || 'Confirma esta ação?';
    if (!window.confirm(message)) event.preventDefault();
  }

  function toggleDisclosure(button) {
    const targetId = button.getAttribute('aria-controls');
    const target = targetId ? document.getElementById(targetId) : null;
    if (!target) return;

    const willOpen = target.hidden;
    target.hidden = !willOpen;
    button.setAttribute('aria-expanded', String(willOpen));
    if (willOpen) {
      target.querySelector('input, select, textarea, button, a')?.focus();
    } else {
      button.focus();
    }
  }

  function init() {
    document.querySelectorAll('[data-confirm]').forEach((element) => {
      const eventName = element.matches('form') ? 'submit' : 'click';
      element.addEventListener(eventName, confirmAction);
    });

    document.querySelectorAll('[data-disclosure]').forEach((button) => {
      button.addEventListener('click', () => toggleDisclosure(button));
    });
  }

  window.addEventListener('DOMContentLoaded', init);
})();
