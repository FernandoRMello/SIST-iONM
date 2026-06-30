(function createShellNavigation(root, factory) {
  const api = factory(root);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root?.document) {
    root.SistIonmNavigation = api;
    api.init();
  }
})(typeof window !== 'undefined' ? window : undefined, (root) => {
  let activeController = null;

  function shouldIntercept(event, anchor, currentHref) {
    if (!anchor || event.defaultPrevented || event.button !== 0) return false;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false;
    if (anchor.hasAttribute('download')) return false;
    if (anchor.target && anchor.target.toLowerCase() !== '_self') return false;
    try {
      const target = new URL(anchor.href, currentHref);
      const current = new URL(currentHref);
      return ['http:', 'https:'].includes(target.protocol) && target.origin === current.origin;
    } catch {
      return false;
    }
  }

  function assetUrl(value, pageUrl) {
    return new URL(value, pageUrl).href;
  }

  function missingAssetUrls(existing, candidates, pageUrl) {
    const known = new Set(existing.map((value) => assetUrl(value, pageUrl)));
    const missing = [];
    candidates.forEach((value) => {
      const url = assetUrl(value, pageUrl);
      if (known.has(url)) return;
      known.add(url);
      missing.push(url);
    });
    return missing;
  }

  function existingAssetUrls(documentNode, selector, attribute) {
    return new Set(
      [...documentNode.querySelectorAll(selector)]
        .map((node) => node.getAttribute(attribute))
        .filter(Boolean)
        .map((value) => assetUrl(value, root.location.href)),
    );
  }

  async function loadStyles(nextDocument, pageUrl) {
    const loaded = [...existingAssetUrls(root.document, 'link[rel="stylesheet"][href]', 'href')];
    const candidates = [...nextDocument.querySelectorAll('link[rel="stylesheet"][href]')]
      .map((source) => source.getAttribute('href'));
    const missing = missingAssetUrls(loaded, candidates, pageUrl);
    await Promise.all(missing.map((href) => {
      return new Promise((resolve, reject) => {
        const link = root.document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.dataset.pageAsset = 'true';
        link.addEventListener('load', resolve, { once: true });
        link.addEventListener('error', reject, { once: true });
        root.document.head.append(link);
      });
    }));
  }

  async function loadScripts(nextDocument, pageUrl) {
    const loaded = [...existingAssetUrls(root.document, 'script[src]', 'src')];
    const candidates = [...nextDocument.querySelectorAll('script[src]')]
      .map((source) => source.getAttribute('src'));
    for (const src of missingAssetUrls(loaded, candidates, pageUrl)) {
      await new Promise((resolve, reject) => {
        const script = root.document.createElement('script');
        script.src = src;
        script.dataset.pageAsset = 'true';
        script.addEventListener('load', resolve, { once: true });
        script.addEventListener('error', reject, { once: true });
        root.document.head.append(script);
      });
    }
  }

  function updateShell(nextDocument) {
    const nextTitle = nextDocument.querySelector('.ui-topbar__leading h1')?.textContent || '';
    const currentTitle = root.document.querySelector('.ui-topbar__leading h1');
    const currentCrumb = root.document.querySelector('.ui-breadcrumb strong');
    if (currentTitle) currentTitle.textContent = nextTitle;
    if (currentCrumb) currentCrumb.textContent = nextTitle;
    root.document.title = nextDocument.title;

    const activeHref = nextDocument.querySelector('[data-nav-item][aria-current="page"]')?.getAttribute('href');
    root.document.querySelectorAll('[data-nav-item]').forEach((item) => {
      const active = Boolean(activeHref) && item.getAttribute('href') === activeHref;
      item.classList.toggle('is-active', active);
      if (active) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
  }

  function fallback(url) {
    root.location.assign(url);
    return false;
  }

  async function navigate(url, options = {}) {
    const push = options.push !== false;
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const main = root.document.getElementById('main-content');
    if (!main) return fallback(url);
    main.setAttribute('aria-busy', 'true');
    main.classList.add('ui-content--loading');

    try {
      const response = await root.fetch(url, {
        credentials: 'same-origin',
        headers: { 'X-SIST-iONM-Navigation': 'partial' },
        signal: controller.signal,
      });
      const nextDocument = new root.DOMParser().parseFromString(await response.text(), 'text/html');
      const nextMain = nextDocument.getElementById('main-content');
      if (!response.ok || !nextMain || !nextDocument.querySelector('[data-shell]')) return fallback(url);

      await loadStyles(nextDocument, response.url || url);
      if (controller.signal.aborted) return false;
      const children = [...nextMain.childNodes].map((node) => root.document.importNode(node, true));
      main.replaceChildren(...children);
      updateShell(nextDocument);
      await loadScripts(nextDocument, response.url || url);
      if (push) root.history.pushState({ sistIonm: true }, '', response.url || url);
      root.document.dispatchEvent(new root.CustomEvent('sistionm:content-updated', { detail: { url: response.url || url } }));
      main.focus({ preventScroll: true });
      root.scrollTo({ top: 0, behavior: 'instant' });
      return true;
    } catch (error) {
      if (error?.name === 'AbortError') return false;
      return fallback(url);
    } finally {
      if (activeController === controller) {
        activeController = null;
        main.removeAttribute('aria-busy');
        main.classList.remove('ui-content--loading');
      }
    }
  }

  function init() {
    root.document.addEventListener('click', (event) => {
      const anchor = event.target.closest?.('a[data-nav-item]');
      if (!shouldIntercept(event, anchor, root.location.href)) return;
      event.preventDefault();
      navigate(anchor.href);
    });
    root.addEventListener('popstate', () => navigate(root.location.href, { push: false }));
  }

  return { init, missingAssetUrls, navigate, shouldIntercept };
});
