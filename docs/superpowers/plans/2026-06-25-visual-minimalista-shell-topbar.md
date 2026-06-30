# Visual Minimalista Shell Topbar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implantar um visual minimalista e profissional, com topbar mais útil, menu lateral discreto, formulários menos poluídos e campos abertos prioritários convertidos em listas/vínculos.

**Architecture:** A mudança preserva o shell persistente existente e atua primeiro nos tokens/CSS globais, depois nos templates principais e por fim nos campos que podem usar dados já disponíveis. O design system continua baseado em CSS local (`tokens.css`, `layout.css`, `components.css`) e templates Jinja, sem CDN ou dependências novas.

**Tech Stack:** FastAPI, Jinja2, CSS local, JavaScript local, pytest, Ruff, Node test runner.

## Global Constraints

- Fundo neutro, claro e menos azulado.
- Menos gradientes; usar cor sólida na maior parte dos componentes.
- Sombras discretas, reservadas a popovers, chat e elementos flutuantes.
- Campos com altura aproximada de 38-40px, mantendo acessibilidade.
- Manter menu lateral atual, modo recolhido, chat rail, notificações e usuário fixos.
- Topbar deve preparar uma busca global futura, sem implementar busca funcional completa.
- Não usar CDN, handler inline, asset remoto ou HTML dinâmico inseguro.
- Preservar rotas e nomes de campos existentes sempre que possível.

---

## File Structure

- Modify `app/shared/web/static/css/tokens.css`: paleta, sombras, raios, topbar e largura central.
- Modify `app/shared/web/static/css/layout.css`: shell, sidebar, topbar, busca futura, conteúdo central e chat compatibility.
- Modify `app/shared/web/static/css/components.css`: botões, cards, campos, tabelas e feedbacks.
- Modify `app/shared/web/templates/layouts/base.html`: inserir placeholder de busca global na topbar e ajustar estrutura sem quebrar chat.
- Modify module CSS files when needed:
  - `app/shared/web/static/css/administration.css`
  - `app/shared/web/static/css/crm.css`
  - `app/shared/web/static/css/executive.css`
  - `app/shared/web/static/css/finance.css`
  - `app/shared/web/static/css/portal.css`
- Modify templates with open fields:
  - `app/templates/hr_employees.html`
  - `app/templates/finance.html`
  - `app/templates/settings.html`
- Modify route contexts when required:
  - `app/features/hr/routes.py`
  - `app/main.py`
- Add/modify tests:
  - `tests/web/test_shell_contract.py`
  - `tests/web/test_accessibility_contract.py`
  - `tests/web/test_hr_module.py`
  - `tests/web/test_finance_pages.py`
  - `tests/characterization/test_render_smoke.py`
- Update docs:
  - `docs/file-map.md`
  - `docs/development.md`
  - `docs/bug-audit.md`

---

### Task 1: Fase A — Auditoria testável dos campos e relações

**Files:**
- Modify: `tests/web/test_hr_module.py`
- Modify: `tests/web/test_finance_pages.py`
- Modify: `tests/web/test_shell_contract.py`
- Modify: `docs/file-map.md`

**Interfaces:**
- Consumes: rendered HTML from `/hr/employees`, `/finance?segment=costs`, `/`.
- Produces: regression tests that enforce select/list behavior and topbar search placeholder.

- [ ] **Step 1: Write failing tests for desired UI contracts**

Add tests asserting:

```python
def test_hr_employee_form_uses_list_fields_for_known_domains(admin_client):
    response = admin_client.get("/hr/employees")
    assert response.status_code == 200
    assert 'id="employee-job"' in response.text
    assert "<select" in response.text
    assert "Vendedor" in response.text
    assert "Representante" in response.text


def test_finance_cost_form_links_vendor_to_existing_catalogs(admin_client):
    response = admin_client.get("/finance?segment=costs")
    assert response.status_code == 200
    assert 'id="cost-party-type"' in response.text
    assert 'id="cost-supplier-id"' in response.text
    assert 'id="cost-seller-id"' in response.text
```

Add a shell test asserting:

```python
def test_topbar_prepares_global_search_without_functional_dependency(admin_client):
    response = admin_client.get("/")
    assert response.status_code == 200
    assert 'data-global-search' in response.text
    assert 'placeholder="Buscar no sistema"' in response.text
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests\web\test_hr_module.py::test_hr_employee_form_uses_list_fields_for_known_domains tests\web\test_finance_pages.py::test_finance_cost_form_links_vendor_to_existing_catalogs tests\web\test_shell_contract.py::test_topbar_prepares_global_search_without_functional_dependency -q
```

Expected: FAIL because job title is currently text input, finance cost party uses text input, and topbar has no global search placeholder.

- [ ] **Step 3: Document audit findings**

Update `docs/file-map.md` with a concise “Campos e relações padronizadas” section covering:

- RH cargo as select for common roles.
- Finance cost party split into supplier/seller lists.
- Topbar search placeholder is visual/preparatory only.

- [ ] **Step 4: Commit audit tests/docs**

```powershell
git add tests\web\test_hr_module.py tests\web\test_finance_pages.py tests\web\test_shell_contract.py docs\file-map.md
git commit -m "test: audit minimalist shell and field relationships"
```

---

### Task 2: Fase B — Design system minimalista

**Files:**
- Modify: `app/shared/web/static/css/tokens.css`
- Modify: `app/shared/web/static/css/layout.css`
- Modify: `app/shared/web/static/css/components.css`
- Modify: `tests/web/test_accessibility_contract.py`
- Modify: `tests/web/test_shell_contract.py`

**Interfaces:**
- Consumes: existing class names `ui-shell`, `ui-sidebar`, `ui-topbar`, `ui-card`, `ui-field__control`, `ui-button`, `ui-table`.
- Produces: minimal visual tokens and compact components without changing template contracts.

- [ ] **Step 1: Write failing CSS contract test**

Add assertions that:

```python
def test_minimalist_design_tokens_reduce_visual_weight() -> None:
    tokens = (SHARED_CSS / "tokens.css").read_text(encoding="utf-8")
    components = (SHARED_CSS / "components.css").read_text(encoding="utf-8")
    layout = (SHARED_CSS / "layout.css").read_text(encoding="utf-8")

    assert "--color-canvas: #f7f8fa;" in tokens
    assert "--shadow-sm: 0 1px 2px" in tokens
    assert "min-height: 40px;" in components
    assert "data-global-search" not in layout
    assert "background: var(--color-sidebar);" in layout
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests\web\test_accessibility_contract.py::test_minimalist_design_tokens_reduce_visual_weight -q
```

Expected: FAIL due current heavier tokens and gradients.

- [ ] **Step 3: Implement minimal tokens/components**

Change:

- canvas to `#f7f8fa`;
- surface subtle to a softer neutral;
- shadows to subtle 1-2px and 8-18px only;
- add `--color-sidebar`;
- reduce `ui-button`, `ui-field__control`, `ui-card`, table padding.

- [ ] **Step 4: Run visual contract tests**

Run:

```powershell
python -m pytest tests\web\test_accessibility_contract.py tests\web\test_shell_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app\shared\web\static\css\tokens.css app\shared\web\static\css\layout.css app\shared\web\static\css\components.css tests\web\test_accessibility_contract.py tests\web\test_shell_contract.py
git commit -m "style: introduce minimalist design system"
```

---

### Task 3: Fase C — Topbar forte e templates principais mais limpos

**Files:**
- Modify: `app/shared/web/templates/layouts/base.html`
- Modify: `app/shared/web/static/css/layout.css`
- Modify: `app/shared/web/static/css/executive.css`
- Modify: `app/shared/web/static/css/administration.css`
- Modify: `tests/web/test_shell_contract.py`
- Modify: `tests/characterization/test_render_smoke.py`

**Interfaces:**
- Consumes: shell navigation JS expects `data-nav-item`, `#main-content`, page assets.
- Produces: topbar search placeholder and compact central layout.

- [ ] **Step 1: Write failing shell/topbar tests**

Extend shell contract:

```python
def test_topbar_keeps_actions_profile_chat_and_global_search(admin_client):
    response = admin_client.get("/")
    assert response.status_code == 200
    assert 'class="ui-global-search"' in response.text
    assert 'data-global-search' in response.text
    assert 'data-chat-action="notifications"' in response.text
    assert 'data-action="toggle-profile"' in response.text
    assert 'href="/cadastros/clients"' in response.text
    assert 'href="/opportunities"' in response.text
```

- [ ] **Step 2: Run and verify fail**

Run:

```powershell
python -m pytest tests\web\test_shell_contract.py::test_topbar_keeps_actions_profile_chat_and_global_search -q
```

Expected: FAIL because global search markup does not exist.

- [ ] **Step 3: Implement topbar search markup and CSS**

In `base.html`, add:

```html
<label class="ui-global-search">
  <span class="ui-visually-hidden">Buscar no sistema</span>
  {{ icon('search', 17) }}
  <input type="search" placeholder="Buscar no sistema" autocomplete="off" data-global-search disabled>
</label>
```

In `layout.css`, style it as compact disabled/prepared search.

- [ ] **Step 4: Run render/shell tests**

Run:

```powershell
python -m pytest tests\web\test_shell_contract.py tests\characterization\test_render_smoke.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app\shared\web\templates\layouts\base.html app\shared\web\static\css\layout.css app\shared\web\static\css\executive.css app\shared\web\static\css\administration.css tests\web\test_shell_contract.py tests\characterization\test_render_smoke.py
git commit -m "style: refine shell topbar and main templates"
```

---

### Task 4: Fase D — Campos abertos prioritários para listas/vínculos

**Files:**
- Modify: `app/features/hr/routes.py`
- Modify: `app/templates/hr_employees.html`
- Modify: `app/main.py`
- Modify: `app/templates/finance.html`
- Modify: `tests/web/test_hr_module.py`
- Modify: `tests/web/test_finance_pages.py`

**Interfaces:**
- Consumes: existing form field names where possible.
- Produces:
  - HR job title select still posts `job_title`.
  - Finance costs post optional `supplier_id`/`seller_id` and human display still works.

- [ ] **Step 1: Write failing tests**

Use the tests from Task 1 as regression targets and add persistence check:

```python
def test_cost_form_persists_supplier_or_seller_link(admin_client, legacy_test_state):
    response = admin_client.post(
        "/finance/costs/add",
        data={
            "order_id": "",
            "description": "Custo vínculo QA",
            "category": "Serviços",
            "cost_center": "Operacional",
            "amount": "100",
            "date": "2026-06-25",
            "party_type": "supplier",
            "supplier_id": str(legacy_test_state.ids["supplier_id"]),
            "seller_id": "",
            "document": "DOC-QA",
            "billable": "Não",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
```

- [ ] **Step 2: Run tests and verify fail**

Run:

```powershell
python -m pytest tests\web\test_hr_module.py::test_hr_employee_form_uses_list_fields_for_known_domains tests\web\test_finance_pages.py::test_finance_cost_form_links_vendor_to_existing_catalogs tests\web\test_finance_pages.py::test_cost_form_persists_supplier_or_seller_link -q
```

Expected: FAIL until templates/routes are updated.

- [ ] **Step 3: Update HR route/template**

In `app/features/hr/routes.py`, pass common options:

```python
"job_titles": ["Vendedor", "Representante", "Analista", "Financeiro", "RH", "TI", "Gestor", "Diretoria"],
"contract_types": ["CLT", "PJ", "Representante", "Estágio", "Autônomo", "Sócio", "Outro"],
```

In `hr_employees.html`, replace job text input with select named `job_title`.

- [ ] **Step 4: Update finance costs context/template/post**

In `/finance`, pass `suppliers` and `sellers` for segment `costs`.
In `finance.html`, replace `vendor` free text with:

- `party_type` select;
- `supplier_id` select;
- `seller_id` select.

In `/finance/costs/add`, derive `vendor` text from selected supplier/seller to preserve current schema.

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests\web\test_hr_module.py tests\web\test_finance_pages.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add app\features\hr\routes.py app\templates\hr_employees.html app\main.py app\templates\finance.html tests\web\test_hr_module.py tests\web\test_finance_pages.py
git commit -m "feat: standardize priority form relationships"
```

---

### Task 5: Fase E — Testes completos e documentação

**Files:**
- Modify: `docs/development.md`
- Modify: `docs/file-map.md`
- Modify: `docs/bug-audit.md`

**Interfaces:**
- Consumes: completed Tasks 1-4.
- Produces: documented visual system and field relation conventions.

- [ ] **Step 1: Update docs**

Document:

- visual minimalista;
- topbar search is preparatory;
- HR select/vendedor relation;
- finance costs supplier/seller relation;
- validation commands.

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest tests\web tests\performance tests\characterization tests\features -q
python -m ruff check app tests
node --check app\static\chat_realtime.js
node --test tests\js\shell-navigation.test.js
node --test tests\js\chat-notifications.test.js
node --test tests\js\profile-avatar-editor.test.js
git diff --check
```

Expected: all exit 0.

- [ ] **Step 3: Commit docs/final polish**

```powershell
git add docs\development.md docs\file-map.md docs\bug-audit.md
git commit -m "docs: document minimalist shell and field relationships"
```

---

## Self-Review Notes

- Spec coverage: all requested phases A-E are represented by tasks.
- Scope guard: no functional global search implementation; only placeholder.
- No new dependency or CDN.
- TDD path is included per task.
- Field relation changes are limited to HR job titles and finance cost supplier/seller links, the safest high-value fields already backed by existing data.
