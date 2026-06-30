# Perfis, Permissões e RH Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar perfis configuráveis, permissões especiais e um módulo inicial de RH com colaboradores, regras de comissão/benefícios e folha mensal rastreável.

**Architecture:** Adicionar domínios focados em `app/features/access_control/` e `app/features/hr/`, mantendo `app/main.py` como montagem de rotas enquanto o monólito é migrado. O novo modelo de permissões convive com `role_permissions`: rotas novas usam permissões por código e rotas antigas continuam protegidas por regras existentes.

**Tech Stack:** FastAPI, Jinja2, SQLite compatível/PostgreSQL-friendly SQL, Pytest, Ruff, design system `ui-*`.

## Global Constraints

- Somente usuários com permissão `access.manage` podem criar perfis e alterar permissões.
- O usuário `fernando.mello` e qualquer perfil `Admin` do sistema não podem perder acesso administrativo por acidente.
- Permissões novas devem ter fallback seguro: se não houver modelo novo inicializado, somente `role == "admin"` pode administrar.
- Dados de folha, salário, benefícios e comissão exigem permissões especiais de RH.
- Folha aprovada/paga não deve ser apagada; ajustes futuros serão por novos itens.
- Cada tarefa deve começar por teste falhando e terminar com commit.

---

## File Structure

- Create `app/features/access_control/repository.py`: schema, seed, perfis, permissões e checagem por código.
- Create `app/features/access_control/routes.py`: telas admin de perfis e matriz de permissões.
- Create `app/templates/access_profiles.html`: UI de perfis configuráveis.
- Create `tests/features/test_access_control_repository.py`: contratos do modelo novo.
- Create `tests/web/test_access_control.py`: rotas, criação e bloqueios.
- Create `app/features/hr/repository.py`: schema de colaboradores, regras, folha e cálculos.
- Create `app/features/hr/routes.py`: telas RH e ações de folha.
- Create `app/templates/hr_employees.html`, `app/templates/hr_payroll.html`, `app/templates/hr_rules.html`: UI inicial RH.
- Create `tests/features/test_hr_repository.py`: cálculos de comissão/benefícios/folha.
- Create `tests/web/test_hr_module.py`: rotas, permissões e criação de usuário a partir de colaborador.
- Modify `app/main.py`: inicializar schemas e montar routers; integrar helper de permissão.
- Modify `app/shared/web/templates/layouts/base.html`: menu Perfis/RH.
- Modify `docs/development.md`, `docs/file-map.md`, `docs/bug-audit.md`, `docs/versions.md`: handoff.

## Task 1: Access control repository and seed

**Files:**
- Create: `app/features/access_control/repository.py`
- Test: `tests/features/test_access_control_repository.py`

**Interfaces:**
- Produces:
  - `AccessControlRepository.init_schema() -> None`
  - `AccessControlRepository.ensure_seed_data() -> None`
  - `AccessControlRepository.profiles() -> list[dict]`
  - `AccessControlRepository.create_profile(name: str, description: str, is_system: bool = False) -> int`
  - `AccessControlRepository.assign_profile(user_id: int, profile_id: int, assigned_by_user_id: int) -> None`
  - `AccessControlRepository.user_has_permission(user_id: int, code: str, legacy_role: str | None = None) -> bool`

- [ ] Write failing repository tests for seed profiles, permission lookup and user assignment.
- [ ] Run targeted tests and confirm failure because module does not exist.
- [ ] Implement schema and seed permissions for `access.manage`, `users.manage`, `whatsapp.configure`, `hr.view`, `hr.manage`, `hr.payroll.view`, `hr.payroll.process`, `hr.payroll.approve`, `hr.payroll.pay`, `finance.sensitive.view`.
- [ ] Run targeted tests and confirm pass.
- [ ] Commit `feat: add configurable access control repository`.

## Task 2: Access control admin UI and user assignment

**Files:**
- Create: `app/features/access_control/routes.py`
- Create: `app/templates/access_profiles.html`
- Modify: `app/main.py`
- Modify: `app/shared/web/templates/layouts/base.html`
- Modify: `app/templates/settings.html`
- Test: `tests/web/test_access_control.py`

**Interfaces:**
- Consumes Task 1.
- Produces:
  - `GET /admin/access-profiles`
  - `POST /admin/access-profiles`
  - `POST /admin/access-profiles/permissions`
  - `POST /settings/users/{user_id}/profiles`

- [ ] Write failing web tests proving admin can create a profile, assign permissions, assign it to a user, and non-admin receives `403`.
- [ ] Run targeted tests and confirm failure.
- [ ] Mount router with an admin/permission guard.
- [ ] Render profile creation, permission matrix and assignment controls.
- [ ] Keep old `/admin/permissions` working.
- [ ] Run targeted tests and existing administration tests.
- [ ] Commit `feat: manage configurable access profiles`.

## Task 3: HR repository and payroll calculation engine

**Files:**
- Create: `app/features/hr/repository.py`
- Test: `tests/features/test_hr_repository.py`

**Interfaces:**
- Produces:
  - `HRRepository.init_schema() -> None`
  - `HRRepository.create_employee(...) -> int`
  - `HRRepository.create_commission_rule(...) -> int`
  - `HRRepository.create_benefit_rule(...) -> int`
  - `HRRepository.generate_payroll_period(period: str, created_by_user_id: int) -> int`
  - `HRRepository.payroll_items(period_id: int) -> list[dict]`

- [ ] Write failing feature tests for employee creation, fixed benefit, sale-total commission and payroll items.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement HR tables and calculation helpers using existing `orders`, `receivables` and opportunity item totals where available.
- [ ] Generate base salary, benefit and commission items for active employees.
- [ ] Run targeted tests and confirm pass.
- [ ] Commit `feat: add hr payroll repository`.

## Task 4: HR web module

**Files:**
- Create: `app/features/hr/routes.py`
- Create: `app/templates/hr_employees.html`
- Create: `app/templates/hr_rules.html`
- Create: `app/templates/hr_payroll.html`
- Modify: `app/main.py`
- Modify: `app/shared/web/templates/layouts/base.html`
- Test: `tests/web/test_hr_module.py`

**Interfaces:**
- Consumes Tasks 1 and 3.
- Produces:
  - `GET /hr/employees`
  - `POST /hr/employees`
  - `POST /hr/employees/{employee_id}/create-user`
  - `GET /hr/rules`
  - `POST /hr/commission-rules`
  - `POST /hr/benefit-rules`
  - `GET /hr/payroll`
  - `POST /hr/payroll/generate`
  - `POST /hr/payroll/{period_id}/approve`
  - `POST /hr/payroll/{period_id}/pay`

- [ ] Write failing web tests for permission gate, employee creation, linked user creation, rule creation and payroll generation.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement routes with permission codes: `hr.view`, `hr.manage`, `hr.payroll.process`, `hr.payroll.approve`, `hr.payroll.pay`.
- [ ] Render UI using `ui-card`, `ui-admin-form`, `ui-table`.
- [ ] Run targeted tests and existing render smoke tests.
- [ ] Commit `feat: add hr employee and payroll module`.

## Task 5: Documentation and full gate

**Files:**
- Modify: `docs/development.md`
- Modify: `docs/file-map.md`
- Modify: `docs/bug-audit.md`
- Modify: `docs/versions.md`

- [ ] Document access profiles, special permissions, HR tables and payroll flow.
- [ ] Run full gate:
  - `python -m pytest tests\web tests\performance tests\characterization tests\features -q`
  - `python -m ruff check app tests`
  - `node --check app\static\chat_realtime.js`
  - `node --test tests\js\shell-navigation.test.js`
  - `node --test tests\js\chat-notifications.test.js`
  - `node --test tests\js\profile-avatar-editor.test.js`
  - `git diff --check`
- [ ] Commit `docs: hand off access profiles and hr module`.

## Self-review

- Spec coverage: Fase 2 and Fase 3 acceptance criteria are represented by tasks.
- Scope control: Advanced deletion, exports and multi-step payroll adjustments are documented as future enhancements; initial payroll is generated and statused.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: repositories and route paths are named before use and reused consistently.
