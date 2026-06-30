# Professional Redesign, UI Structure, and Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all 18 Jinja surfaces with a corporate-premium design system, faster navigation, reusable accessible components, bounded query growth, and a verified bug baseline while preserving routes and business behavior.

**Architecture:** Keep FastAPI/Jinja2 server rendering and progressively replace the monolithic template/assets with `app/shared/web`. Characterization tests protect current behavior; page groups migrate only after the shell and shared components pass. PostgreSQL cutover and full backend domain extraction continue in subsequent internal plans within the same final release.

**Tech Stack:** Python 3.13, FastAPI 0.137.1, Jinja2 3.1.6, pytest 9.1.0, vanilla CSS, local SVG sprite, progressive JavaScript.

## Global Constraints

- Preserve all existing URLs and valid business flows.
- Cover all 18 existing template files and every route variation they serve.
- Use the approved corporate-premium navy/teal visual language.
- Keep FastAPI/Jinja2; do not add React, Tailwind, Node.js, CDNs, remote fonts, or external icons.
- Remove emoji navigation icons and inline JavaScript handlers.
- Support 1280, 1024, 768, 390, and 360 px layouts.
- Meet WCAG AA contrast, visible focus, semantic labels, and non-color status cues.
- Load local JavaScript with `defer` or `type="module"`.
- Use TDD for behavior and characterization tests before changing existing behavior.
- Keep the application executable after every task.
- Do not rewrite Git history or alter/delete the source SQLite database.

---

## Target Structure

    app/shared/web/
      templates/layouts/base.html
      templates/components/macros.html
      templates/errors/{400,403,404,500}.html
      static/css/{tokens,reset,layout,components,utilities}.css
      static/css/{portal,crm,finance,administration}.css
      static/js/{app-shell,navigation,tables,forms,feedback}.js
      static/icons/sprite.svg
    tests/characterization/
    tests/web/
    tests/performance/

### Task 1: Establish Template, Route, and Render Characterization

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/characterization/test_template_inventory.py`
- Create: `tests/characterization/test_route_inventory.py`
- Create: `tests/characterization/test_render_smoke.py`

**Interfaces:**
- Consumes: `app.main.app`, copied SQLite fixture, existing templates.
- Produces: `legacy_client`, exact 18-template inventory, exact HTTP/WebSocket inventory, anonymous render contracts.

- [ ] **Step 1: Add isolated client fixture**

Implement `legacy_client(tmp_path, monkeypatch)` that copies `data/overpriceon_web.db` to `tmp_path`, monkeypatches `app.main.DB_PATH`, opens `TestClient(app)`, and never writes the source database.

- [ ] **Step 2: Add exact inventory tests**

Assert the template set equals: `base.html`, `bi_gerencial.html`, `chat.html`, `commissions.html`, `crud.html`, `dashboard.html`, `feed.html`, `finance.html`, `login.html`, `opportunities.html`, `opportunity_card.html`, `orders.html`, `orgchart.html`, `permissions.html`, `profile.html`, `purchases.html`, `seller_reports.html`, `settings.html`.

Assert the HTTP route set equals the 59 application method/path pairs recorded in the existing foundation plan and WebSockets equal `/ws/chat/{room_id}` and `/ws/notify`.

- [ ] **Step 3: Add render smoke tests**

Assert `/login` returns 200 with named username/password inputs. Parameterize `/`, `/feed`, `/chat`, `/profile`, `/orgchart`, `/opportunities`, `/orders`, `/finance`, `/settings`; each anonymous request must return 303 with `Location: /login`.

- [ ] **Step 4: Verify baseline**

Run: `python -m pytest tests/characterization -q`.

Expected: all pass and SHA-256 of `data/overpriceon_web.db` is unchanged.

- [ ] **Step 5: Commit**

Run: `git add tests && git commit -m "test: establish UI render characterization baseline"`.

### Task 2: Create Design Tokens and Static Asset Contract

**Files:**
- Create: `app/shared/__init__.py`
- Create: `app/shared/web/__init__.py`
- Create: `app/shared/web/static/css/tokens.css`
- Create: `app/shared/web/static/css/reset.css`
- Create: `app/shared/web/static/css/layout.css`
- Create: `app/shared/web/static/css/components.css`
- Create: `app/shared/web/static/css/utilities.css`
- Create: `tests/web/test_design_contract.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: approved palette/spacing/type/radius/focus constraints.
- Produces: `/assets/*` mount and stable `ui-*` classes.

- [ ] **Step 1: Write failing token tests**

Assert all five CSS files exist and `tokens.css` contains exact tokens `--color-navy-950: #081426`, `--color-teal-600: #0f8b8d`, `--color-canvas: #f4f7fb`, `--color-text: #172033`, `--space-1: 4px`, `--space-6: 24px`. Assert combined CSS contains `:focus-visible` and `prefers-reduced-motion`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/web/test_design_contract.py -q`.

Expected: FAIL because shared CSS is absent.

- [ ] **Step 3: Implement CSS foundation**

Implement exact design tokens, local font stack, 4–48 px spacing, 8/10/12 px radii, semantic colors, sidebar widths and responsive breakpoints. `reset.css` normalizes elements; `layout.css` owns shell/grid/drawer; `components.css` owns buttons/fields/cards/badges/tables/pagination/feedback; `utilities.css` owns accessibility/print helpers.

- [ ] **Step 4: Mount shared assets**

Define `SHARED_STATIC_DIR = BASE_DIR / "app" / "shared" / "web" / "static"` and mount `/assets` once. Keep `/static` during migration.

- [ ] **Step 5: Run GREEN and commit**

Run `python -m pytest tests/web/test_design_contract.py tests/characterization -q`, then `git add app tests && git commit -m "feat: add corporate design-system foundation"`.

### Task 3: Add Local SVG Icons and Shared Jinja Components

**Files:**
- Create: `app/shared/web/static/icons/sprite.svg`
- Create: `app/shared/web/templates/components/macros.html`
- Create: `tests/web/test_component_contract.py`
- Modify: `app/main.py` template loader.

**Interfaces:**
- Produces macros `icon`, `page_header`, `stat_card`, `status_badge`, `empty_state`, `pagination`, `form_field`, `data_table_shell`.

- [ ] **Step 1: Write failing component tests**

Parse sprite XML and require symbols: dashboard, feed, chat, user, orgchart, clients, pipeline, orders, money, products, finance, suppliers, purchases, bi, sellers, settings, permissions, search, plus, menu, bell, eye, eye-off, logout, close, arrow-left, arrow-right. Assert all eight macro declarations exist and icons support both `aria-hidden` and accessible labels.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/web/test_component_contract.py -q`.

- [ ] **Step 3: Implement sprite/macros/loader**

Use 24×24 symbols with `stroke="currentColor"`. Configure Jinja `ChoiceLoader` with legacy and shared template roots. Do not move page templates yet.

- [ ] **Step 4: Run GREEN and commit**

Run `python -m pytest tests/web/test_component_contract.py tests/characterization -q`, then commit `feat: add reusable Jinja components and local icons`.

### Task 4: Redesign Application Shell and Navigation

**Files:**
- Create: `app/shared/web/templates/layouts/base.html`
- Create: `app/shared/web/static/js/app-shell.js`
- Create: `app/shared/web/static/js/navigation.js`
- Create: `tests/web/test_shell_contract.py`
- Modify: `app/templates/base.html`
- Modify: `app/main.py` render context.

**Interfaces:**
- Produces sidebar, active route, mobile drawer, breadcrumb, menu search, quick actions, profile menu, page asset blocks, chat mount.

- [ ] **Step 1: Write failing shell tests**

Assert links to all five base styles, deferred local scripts, no inline event attributes, no navigation emojis, `aria-current="page"`, skip link, `main-content`, mobile menu `aria-controls`/`aria-expanded`, quick links to `/opportunities` and `/cadastros/clients`, and logout `/logout`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/web/test_shell_contract.py -q`.

- [ ] **Step 3: Implement semantic shell**

Group navigation: Visão geral, Relacionamento, Operação, Financeiro, Administração. Use SVG macro and permission checks. Keep `app/templates/base.html` as compatibility template extending shared layout and preserving `title`, `content`, `public` blocks.

- [ ] **Step 4: Implement progressive JS**

`app-shell.js` owns sidebar/mobile/profile/money preferences/Escape/focus restoration. `navigation.js` owns menu filtering and keyboard focus. Bind only through `data-action`; persist only non-sensitive preferences.

- [ ] **Step 5: Run GREEN and commit**

Run `python -m pytest tests/web/test_shell_contract.py tests/characterization -q`, then commit `feat: redesign accessible application shell`.

### Task 5: Redesign Executive and Public Surfaces

**Files:**
- Modify: `app/templates/dashboard.html`
- Modify: `app/templates/bi_gerencial.html`
- Modify: `app/templates/login.html`
- Create: `app/shared/web/templates/errors/400.html`
- Create: `app/shared/web/templates/errors/403.html`
- Create: `app/shared/web/templates/errors/404.html`
- Create: `app/shared/web/templates/errors/500.html`
- Create: `app/shared/web/static/js/feedback.js`
- Create: `tests/web/test_executive_pages.py`

**Interfaces:**
- Consumes existing dashboard/BI/login contexts unchanged.
- Produces KPI hierarchy, responsive recent opportunities, professional login and safe error pages.

- [ ] **Step 1: Write RED contracts**

Assert six stat cards, one primary Nova R.O. action, text + color probability, `data-action="toggle-money"`, explicit BI section headings, login labels/autocomplete/password toggle/no remote assets, and error templates with optional correlation ID and safe navigation.

- [ ] **Step 2: Run RED, implement, run GREEN**

Run `python -m pytest tests/web/test_executive_pages.py -q`; implement while preserving Jinja keys/actions; rerun with `tests/characterization`.

- [ ] **Step 3: Commit**

Commit `feat: redesign executive, login, and error surfaces`.

### Task 6: Redesign Portal, Chat, Profile, and Organization

**Files:**
- Modify: `app/templates/feed.html`
- Modify: `app/templates/chat.html`
- Modify: `app/templates/profile.html`
- Modify: `app/templates/orgchart.html`
- Modify: `app/static/chat_realtime.js`
- Create: `app/shared/web/static/css/portal.css`
- Create: `tests/web/test_portal_pages.py`

- [ ] **Step 1: Write RED contracts**

Require page headers, labels, attachment controls, empty states, local icons, no inline handlers. Require WebSocket open/close/error handling, capped reconnect, `textContent` for user messages, and `aria-live` connection status.

- [ ] **Step 2: Run RED, implement, run GREEN**

Feed uses composer/cards; chat uses conversation sidebar/panel/status; profile separates identity/contact/preferences; orgchart includes hierarchy + table fallback. Preserve endpoints/field names. Run portal + characterization tests.

- [ ] **Step 3: Commit**

Commit `feat: redesign portal and realtime communication`.

### Task 7: Redesign CRUD and Administration

**Files:**
- Modify: `app/templates/crud.html`
- Modify: `app/templates/settings.html`
- Modify: `app/templates/permissions.html`
- Create: `app/shared/web/static/js/forms.js`
- Create: `app/shared/web/static/js/tables.js`
- Create: `app/shared/web/static/css/administration.css`
- Create: `tests/web/test_administration_pages.py`

- [ ] **Step 1: Write RED contracts**

Require toolbar/search, labeled form section, empty state, accessible row actions, sectioned settings, empty SMTP password values, labeled permission matrix and confirmation marker for destructive actions.

- [ ] **Step 2: Run RED, implement, run GREEN**

Use macros and `data-table`, `data-confirm`, `data-disclosure`. `forms.js` owns drawer/disclosure/focus/confirmation; `tables.js` enhances current-page data only. Remove stored SMTP password from template context. Run administration + characterization tests.

- [ ] **Step 3: Commit**

Commit `feat: redesign CRUD and administration surfaces`.

### Task 8: Redesign CRM, Orders, and Purchases

**Files:**
- Modify: `app/templates/opportunities.html`
- Modify: `app/templates/opportunity_card.html`
- Modify: `app/templates/orders.html`
- Modify: `app/templates/purchases.html`
- Create: `app/shared/web/static/css/crm.css`
- Create: `tests/web/test_crm_pages.py`

- [ ] **Step 1: Write RED contracts**

Require list/Kanban pressed/current state, non-color probability, next action, labeled movement controls, preserved product fields, distinct fiscal/financial statuses, shared purchase form/table.

- [ ] **Step 2: Run RED, implement, run GREEN**

Preserve all URLs, names, Jinja keys, PDFs and status values. Opportunity detail order: summary, products, communication, documents, history. Run CRM + characterization tests.

- [ ] **Step 3: Commit**

Commit `feat: redesign CRM and operational surfaces`.

### Task 9: Redesign Finance, Commissions, and Seller Reports

**Files:**
- Modify: `app/templates/finance.html`
- Modify: `app/templates/commissions.html`
- Modify: `app/templates/seller_reports.html`
- Create: `app/shared/web/static/css/finance.css`
- Create: `tests/web/test_finance_pages.py`

- [ ] **Step 1: Write RED contracts**

Require labeled receivable/payable/cost segments, totals, one add-cost action, empty states, commission filter hooks/non-color statuses, seller report filters/summary/results/review/print utilities.

- [ ] **Step 2: Run RED, implement, run GREEN**

Preserve forms/values. Use semantic sections, shared tables/badges/totals and print utilities. Render only the selected finance segment when query parameter exists; default to receivables. Run finance + characterization tests.

- [ ] **Step 3: Commit**

Commit `feat: redesign financial and reporting surfaces`.

### Task 10: Bound Queries, Paginate Lists, and Cache Assets

**Files:**
- Create: `tests/performance/test_query_budget.py`
- Create: `tests/performance/test_pagination.py`
- Modify: `app/main.py`
- Modify: templates with list pagination.

**Interfaces:**
- Produces bounded dashboard/opportunity/chat query counts and pagination `{page,page_size,total,pages}`.

- [ ] **Step 1: Write RED performance tests**

Instrument `q`; assert dashboard/opportunity/chat counts do not grow linearly. Assert default page size 25, maximum 100, negative page normalizes to 1.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/performance -q`.

- [ ] **Step 3: Implement bulk aggregates/pagination/cache**

Replace per-row opportunity summaries with joined grouped aggregates. Add tested `pagination_values(total, page, page_size)`. Apply to CRUD, opportunities, chat history, finance, seller reports. Cache only versioned `/assets/` responses for one year; authenticated HTML uses `no-store`.

- [ ] **Step 4: Run GREEN and commit**

Run performance + web + characterization tests; commit `perf: bound queries and paginate rendered lists`.

### Task 11: Complete Cross-Template Bug and Accessibility Audit

**Files:**
- Create: `tests/web/test_accessibility_contract.py`
- Create: `docs/bug-audit.md`
- Modify: templates/assets required by evidence.
- Remove: `app/static/style.css` only after no references remain.

- [ ] **Step 1: Write cross-template tests**

Assert 18 templates have no inline handlers, remote assets, password values or navigation emojis; use local assets and page blocks. Assert JavaScript has no `eval`, `document.write`, or message-content `innerHTML`.

- [ ] **Step 2: Run RED and fix evidenced failures with regression tests**

For each bug record ID, surface, reproduction, root cause, fix, regression test, verification command. Do not call speculative issues fixed.

- [ ] **Step 3: Remove legacy CSS and run GREEN**

Delete legacy CSS only after `rg -n "/static/style.css|style.css" app/templates app/shared` has no matches. Run web + performance + characterization tests and Ruff.

- [ ] **Step 4: Commit**

Commit `fix: complete UI bug and accessibility audit`.

### Task 12: Document and Verify the UI Workstream

**Files:**
- Create: `docs/design-system.md`
- Create: `docs/performance.md`
- Create or update: `docs/file-map.md`
- Update: `docs/development.md`

- [ ] **Step 1: Document the system**

Document tokens, macro signatures, JS responsibilities, responsive breakpoints, page-to-template/route/context/style/script/test map, performance method and exact commands.

- [ ] **Step 2: Run automated gate**

Run `python -m pytest --cov=app --cov-report=term-missing -q`, `python -m ruff check app tests`, `python -m mypy app/core scripts`, `git diff --check`.

Expected: zero failures/errors.

- [ ] **Step 3: Verify preservation**

Verify source SQLite SHA-256 matches pre-work baseline and exact route inventory passes.

- [ ] **Step 4: Manual visual acceptance**

User validates login, dashboard, sidebar, mobile menu, opportunity, finance, settings, chat and print at agreed widths. Record defects, add regression tests where automatable, fix, and rerun gate. Do not use a blocked alternate browser automation surface.

- [ ] **Step 5: Commit**

Commit `docs: hand off professional UI and performance system`.

## Completion Gate

Complete only when all 18 templates use the new system, routes are preserved, source SQLite is unchanged, local assets load, inline handlers/emojis are gone, query-growth tests pass, automated checks are green, and the user accepts the visual checklist. PostgreSQL/domain/deployment plans then continue toward the single final release.
