# Configuração de Banco de Dados Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar em Configurações uma área administrativa para cadastrar, testar e preparar conexão PostgreSQL sem expor credenciais.

**Architecture:** Novo módulo `app/features/database_admin/` isola persistência, segurança de segredo, teste de conexão e preparo básico. `app/main.py` apenas monta a rota e passa `DB_PATH`, mantendo SQLite como runtime atual.

**Tech Stack:** FastAPI/Jinja2, SQLite runtime legado, PostgreSQL via `psycopg`, criptografia local com `cryptography`, testes Pytest.

## Global Constraints

- SQLite permanece como banco ativo/local neste ciclo.
- PostgreSQL é destino configurável e preparável, não cutover quente.
- Senha de banco nunca deve ser renderizada no HTML nem aparecer em mensagens.
- Senha vazia em edição preserva a senha anterior.
- Apenas administrador pode alterar/testar/preparar configuração.
- Preparar ambiente cria/verifica apenas estrutura mínima de controle no PostgreSQL.

---

### Task 1: Repositório e proteção de credencial

**Files:**
- Create: `app/features/database_admin/repository.py`
- Create: `app/features/database_admin/security.py`
- Test: `tests/features/test_database_admin_repository.py`

**Interfaces:**
- Produces: `DatabaseSettingsRepository(database_path)`, `save_config(...)`, `get_config_for_view()`, `record_test_result(...)`, `record_prepare_result(...)`.
- Produces: `encrypt_database_password(value, master_key)`, `decrypt_database_password(value, master_key)`, `mask_database_password(encrypted)`.

- [ ] **Step 1: Write failing repository/security tests**

Test persistence, masking, and preserving existing password.

- [ ] **Step 2: Run tests and verify fail**

Run: `python -m pytest tests/features/test_database_admin_repository.py -q`

- [ ] **Step 3: Implement minimal repository/security**

Create schema `database_connections`, save PostgreSQL config, encrypt non-empty password, preserve existing encrypted password when empty, expose view without plaintext.

- [ ] **Step 4: Run tests and verify pass**

Run: `python -m pytest tests/features/test_database_admin_repository.py -q`

### Task 2: Serviço PostgreSQL

**Files:**
- Create: `app/features/database_admin/service.py`
- Test: `tests/features/test_database_admin_service.py`

**Interfaces:**
- Consumes: repository config dict.
- Produces: `DatabaseAdminService.test_connection(config, password) -> OperationResult`.
- Produces: `DatabaseAdminService.prepare_environment(config, password) -> OperationResult`.

- [ ] **Step 1: Write failing service tests**

Use fake connector to validate `SELECT 1`, control-table creation, safe error classification, and DSN not exposing password.

- [ ] **Step 2: Run tests and verify fail**

Run: `python -m pytest tests/features/test_database_admin_service.py -q`

- [ ] **Step 3: Implement service**

Build psycopg connection kwargs, execute `SELECT 1`, create `sist_ionm_schema_status`, return safe messages.

- [ ] **Step 4: Run tests and verify pass**

Run: `python -m pytest tests/features/test_database_admin_service.py -q`

### Task 3: Rotas e tela em Configurações

**Files:**
- Create: `app/features/database_admin/routes.py`
- Modify: `app/main.py`
- Modify: `app/templates/settings.html`
- Test: `tests/web/test_database_admin_settings.py`
- Modify: `tests/web/test_administration_pages.py`

**Interfaces:**
- Consumes: repository and service.
- Produces routes:
  - `POST /settings/database/save`
  - `POST /settings/database/test`
  - `POST /settings/database/prepare`

- [ ] **Step 1: Write failing web tests**

Assert section renders, non-admin is blocked, password is not rendered, save/test/prepare routes record statuses.

- [ ] **Step 2: Run tests and verify fail**

Run: `python -m pytest tests/web/test_database_admin_settings.py tests/web/test_administration_pages.py -q`

- [ ] **Step 3: Implement routes and template section**

Mount router, pass `database_admin` context to `settings.html`, add forms/buttons/status copy.

- [ ] **Step 4: Run tests and verify pass**

Run: `python -m pytest tests/web/test_database_admin_settings.py tests/web/test_administration_pages.py -q`

### Task 4: Documentação e gates finais

**Files:**
- Modify: `docs/development.md`
- Modify: `docs/file-map.md`
- Modify: `docs/bug-audit.md`

- [ ] **Step 1: Document behavior**

Explain that PostgreSQL can be configured/tested/prepared, while cutover/migration is later.

- [ ] **Step 2: Run verification**

Run:

```powershell
python -m pytest tests\features tests\web tests\performance tests\characterization -q
python -m ruff check app tests
node --check app\static\chat_realtime.js
node --test tests\js\shell-navigation.test.js
node --test tests\js\chat-notifications.test.js
node --test tests\js\profile-avatar-editor.test.js
git diff --check
```

- [ ] **Step 3: Commit**

Commit message: `feat: add database settings administration`
