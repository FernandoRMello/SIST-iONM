# Navegação persistente e imagens no chat — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar apenas o conteúdo central ao navegar pelo menu e renderizar anexos de imagem dentro das mensagens sem interromper o chat.

**Architecture:** Um módulo progressivo controla apenas links `data-nav-item`, analisa a resposta HTML, sincroniza assets e estado visual, substitui `#main-content` e mantém fallback para navegação completa. O chat identifica imagens por extensão validada no servidor e usa a mesma representação segura no JavaScript e no Jinja.

**Tech Stack:** FastAPI, Jinja2, JavaScript sem framework, CSS modular, pytest, Node `--test`.

## Global Constraints

- Somente links do menu lateral são interceptados.
- Formulários, downloads, links de detalhe e ações rápidas continuam tradicionais.
- Menu, topbar e chat não são recriados; o WebSocket deve permanecer conectado.
- PNG, JPG/JPEG, WebP e GIF recebem miniatura; SVG e HTML continuam bloqueados.
- Falha de rede, autenticação ou asset sempre usa navegação tradicional.
- Não adicionar dependências frontend.

---

### Task 1: Núcleo da navegação progressiva

**Files:**
- Create: `app/shared/web/static/js/shell-navigation.js`
- Create: `tests/js/shell-navigation.test.js`
- Modify: `app/shared/web/templates/layouts/base.html`
- Modify: `tests/web/test_shell_contract.py`

**Interfaces:**
- Produces: `window.SistIonmNavigation.navigate(url, options)` e evento `sistionm:content-updated`.
- Consumes: `data-nav-item`, `#main-content`, `.ui-topbar`, `.ui-navigation` e History API.

- [ ] **Step 1: Escrever testes que falham para elegibilidade e contrato do shell**

Testar com `node:test` que clique primário no mesmo host é aceito e Ctrl/Cmd/Shift, `download`, outro host e alvo diferente de `_self` são recusados. Em pytest, exigir o script versionado no layout.

```js
assert.equal(api.shouldIntercept({ button: 0 }, localAnchor, currentUrl), true);
assert.equal(api.shouldIntercept({ button: 0, ctrlKey: true }, localAnchor, currentUrl), false);
assert.equal(api.shouldIntercept({ button: 0 }, externalAnchor, currentUrl), false);
```

- [ ] **Step 2: Executar RED**

```powershell
node --test tests/js/shell-navigation.test.js
python -m pytest tests/web/test_shell_contract.py -q
```

Esperado: falha porque módulo e referência ainda não existem.

- [ ] **Step 3: Implementar o módulo mínimo**

Implementar `shouldIntercept`, delegação de clique, `fetch` com `credentials: 'same-origin'`, `DOMParser`, validação de shell autenticado, substituição dos filhos de `#main-content`, atualização de título/topbar/breadcrumb/menu, `pushState`, `popstate`, `AbortController`, `aria-busy` e fallback com `location.assign`.

```js
async function navigate(url, { push = true } = {}) {
  const response = await fetch(url, { credentials: 'same-origin', signal });
  const next = new DOMParser().parseFromString(await response.text(), 'text/html');
  if (!response.ok || !next.querySelector('[data-shell]') || !next.querySelector('#main-content')) return fallback(url);
  await syncAssets(next);
  current.replaceChildren(...nextMain.childNodes);
  document.dispatchEvent(new CustomEvent('sistionm:content-updated'));
}
```

- [ ] **Step 4: Executar GREEN**

Rodar os dois comandos do Step 2. Esperado: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/shared/web/static/js/shell-navigation.js app/shared/web/templates/layouts/base.html tests/js/shell-navigation.test.js tests/web/test_shell_contract.py
git commit -m "feat: keep application shell during menu navigation"
```

### Task 2: Assets e inicializadores idempotentes

**Files:**
- Modify: `app/shared/web/static/js/shell-navigation.js`
- Modify: `app/shared/web/static/js/forms.js`
- Modify: `app/shared/web/static/js/tables.js`
- Modify: `tests/js/shell-navigation.test.js`
- Modify: `tests/web/test_component_contract.py`

**Interfaces:**
- Consumes: evento `sistionm:content-updated` da Task 1.
- Produces: `syncAssets(nextDocument)` e inicializadores seguros para conteúdo recém-inserido.

- [ ] **Step 1: Escrever testes que falham para deduplicação e reinicialização**

Exigir que assets com a mesma URL não sejam recarregados, novos estilos sejam aguardados antes da troca e elementos recebam `data-ready` ao registrar listeners.

```python
assert "sistionm:content-updated" in forms_source
assert "dataset.ready" in forms_source
assert "sistionm:content-updated" in tables_source
```

- [ ] **Step 2: Executar RED**

```powershell
python -m pytest tests/web/test_component_contract.py -q
node --test tests/js/shell-navigation.test.js
```

- [ ] **Step 3: Implementar sincronização e inicialização idempotente**

Carregar somente `link[rel="stylesheet"][href]` e `script[src]` ausentes. Marcar assets dinâmicos, aguardar `load/error`, e chamar inicializadores tanto na carga inicial quanto em `sistionm:content-updated`. Cada campo/botão deve usar `data-ready` para não duplicar eventos.

- [ ] **Step 4: Executar GREEN e regressão do shell**

```powershell
python -m pytest tests/web/test_component_contract.py tests/web/test_shell_contract.py -q
node --test tests/js/shell-navigation.test.js
```

- [ ] **Step 5: Commit**

```powershell
git add app/shared/web/static/js tests/js tests/web
git commit -m "fix: initialize dynamic page assets once"
```

### Task 3: Miniaturas de imagem no chat

**Files:**
- Modify: `app/main.py`
- Modify: `app/static/chat_realtime.js`
- Modify: `app/templates/chat.html`
- Modify: `app/shared/web/static/css/layout.css`
- Modify: `app/shared/web/static/css/portal.css`
- Modify: `tests/web/test_chat_delivery.py`
- Modify: `tests/web/test_portal_pages.py`

**Interfaces:**
- Produces: `attachment_is_image` no payload e nas mensagens renderizadas; miniatura dentro de link seguro.
- Consumes: `attachment_path` já validado e persistido.

- [ ] **Step 1: Escrever testes que falham para GIF e miniatura**

Testar upload `.gif`, `attachment_is_image=true`, `<img loading="lazy">` no HTML da tela completa e criação segura de imagem no JavaScript. Confirmar que PDF continua sem miniatura.

- [ ] **Step 2: Executar RED**

```powershell
python -m pytest tests/web/test_chat_delivery.py tests/web/test_portal_pages.py -q
```

- [ ] **Step 3: Implementar detecção e apresentação**

Adicionar `.gif` à whitelist, helper por extensão para preencher `attachment_is_image`, miniatura Jinja e DOM seguro no cliente. Aplicar dimensões máximas, `object-fit: cover`, borda e estado responsivo.

```js
if (message.attachment_is_image) {
  const link = make('a', 'ui-message__image-link');
  const image = make('img', 'ui-message__image');
  image.src = `/${message.attachment_path}`;
  image.alt = 'Imagem anexada';
  image.loading = 'lazy';
  link.append(image);
  article.append(link);
}
```

- [ ] **Step 4: Executar GREEN**

Rodar o comando do Step 2 e `node --check app/static/chat_realtime.js`. Esperado: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/main.py app/static/chat_realtime.js app/templates/chat.html app/shared/web/static/css tests/web
git commit -m "feat: preview chat images inside messages"
```

### Task 4: Documentação e gate completo

**Files:**
- Modify: `docs/file-map.md`
- Modify: `docs/development.md`
- Modify: `docs/bug-audit.md`

**Interfaces:**
- Consumes: contratos finais das Tasks 1–3.
- Produces: instruções de manutenção e verificação para o Dev Junior.

- [ ] **Step 1: Documentar fluxo, fallback e formatos**

Registrar responsabilidade de `shell-navigation.js`, evento de reinicialização, limite de 10 MiB, formatos de imagem e regra de não interceptar formulários.

- [ ] **Step 2: Executar gate completo**

```powershell
python -m pytest tests/web tests/performance tests/characterization tests/features -q
python -m ruff check app tests
Get-ChildItem app -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
node --test tests/js/shell-navigation.test.js
git diff --check
```

Esperado: zero falhas; somente os três avisos de depreciação já conhecidos.

- [ ] **Step 3: Verificar manualmente**

Com sessão autenticada: abrir o chat, navegar Dashboard → Clientes → Pipeline pelo menu e confirmar que o painel permanece aberto; usar Voltar/Avançar; enviar PNG e PDF e comparar miniatura/link.

- [ ] **Step 4: Commit final**

```powershell
git add docs app tests
git commit -m "docs: hand off persistent shell navigation"
```
