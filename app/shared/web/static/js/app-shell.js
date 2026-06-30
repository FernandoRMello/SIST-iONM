(() => {
  const shell = document.querySelector('[data-shell]');
  if (!shell) return;

  const sidebar = document.getElementById('primary-sidebar');
  const backdrop = document.querySelector('.ui-backdrop');
  const menuButton = document.querySelector('[data-action="toggle-sidebar"]');
  const profileButton = document.querySelector('[data-action="toggle-profile"]');
  const profileMenu = document.getElementById('profile-menu');
  const preferenceKey = 'sist-ionm:sidebar-collapsed';

  const readPreference = () => {
    try { return localStorage.getItem(preferenceKey) === 'true'; } catch { return false; }
  };
  const storePreference = (value) => {
    try { localStorage.setItem(preferenceKey, String(value)); } catch { /* private mode */ }
  };

  const setSidebarOpen = (open) => {
    sidebar?.classList.toggle('ui-sidebar--open', open);
    if (backdrop) backdrop.hidden = !open;
    menuButton?.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('ui-scroll-locked', open);
  };

  const setCollapsed = (collapsed) => {
    shell.classList.toggle('ui-shell--collapsed', collapsed);
    sidebar?.classList.toggle('ui-sidebar--collapsed', collapsed);
    storePreference(collapsed);
  };

  const setProfileOpen = (open) => {
    if (profileMenu) profileMenu.hidden = !open;
    profileButton?.setAttribute('aria-expanded', String(open));
  };

  setCollapsed(readPreference());

  document.addEventListener('click', (event) => {
    const actionTarget = event.target.closest('[data-action]');
    if (actionTarget) {
      const action = actionTarget.dataset.action;
      if (action === 'toggle-sidebar') setSidebarOpen(!sidebar?.classList.contains('ui-sidebar--open'));
      if (action === 'close-sidebar') setSidebarOpen(false);
      if (action === 'toggle-collapse') setCollapsed(!shell.classList.contains('ui-shell--collapsed'));
      if (action === 'toggle-profile') setProfileOpen(profileMenu?.hidden ?? true);
      if (action === 'toggle-money') document.body.classList.toggle('hide-money');
    }

    const chatTarget = event.target.closest('[data-chat-action]');
    if (chatTarget && window.SistIonmChat) {
      const chatAction = chatTarget.dataset.chatAction;
      const handlers = {
        notifications: 'toggleNotifications',
        general: 'openGeneral',
        minimize: 'minimize',
        close: 'close',
      };
      const handler = handlers[chatAction];
      if (handler && typeof window.SistIonmChat[handler] === 'function') window.SistIonmChat[handler]();
    }

    if (profileMenu && !profileMenu.hidden && !event.target.closest('.ui-profile-menu')) setProfileOpen(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    setSidebarOpen(false);
    setProfileOpen(false);
    menuButton?.focus();
  });
})();
