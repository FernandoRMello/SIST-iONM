# WhatsApp Embedded Signup e Automações Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o módulo WhatsApp atual com conexão oficial via Meta Embedded Signup, regras automáticas, consultas seguras e QR Code/short link oficial para clientes iniciarem conversa.

**Architecture:** Reusar `app/features/whatsapp/` já existente e adicionar unidades pequenas: configuração Embedded Signup, sessões com `state` seguro, regras de automação, respostas seguras e QR codes oficiais. O `app/main.py` continua apenas montando o router e inicializando schema, enquanto a lógica permanece em módulos testáveis.

**Tech Stack:** FastAPI, Jinja2, SQLite compatível, Python stdlib crypto/HMAC/urllib, testes Pytest, Ruff, design system atual `ui-*`.

## Global Constraints

- Não implementar WhatsApp Web via QR Code como integração principal.
- Usar Meta WhatsApp Business Cloud API e Embedded Signup oficial.
- Manter o wizard manual já criado.
- Somente `admin` pode configurar WhatsApp, Embedded Signup, QR codes e regras automáticas.
- Nenhum token, `app_secret`, code, `state` ou payload sensível pode ser renderizado em texto claro.
- Toda rota state-changing exige validação no servidor.
- Toda nova produção deve nascer de teste falhando primeiro.
- Mensagens automáticas não podem retornar pedidos/faturas se o contato não estiver vinculado com segurança a um cliente.
- Preservar webhook seguro com `X-Hub-Signature-256`.

---

## File Structure

- Modify `app/features/whatsapp/repository.py`: schema e persistência para sessões Embedded Signup, regras e QR codes.
- Modify `app/features/whatsapp/routes.py`: rotas admin para iniciar/callback Embedded Signup, CRUD simples de regras, QR codes e status.
- Modify `app/features/whatsapp/service.py`: engine de automações e consultas seguras.
- Modify `app/features/whatsapp/client.py`: métodos para trocar/capturar dados de Embedded Signup e gerenciar QR codes via boundary fakeável.
- Modify `app/templates/whatsapp_settings.html`: botão `Conectar com Meta`, formulário de automações, QR codes e status.
- Modify `app/shared/web/static/css/administration.css`: pequenos ajustes visuais se necessário.
- Modify `.env.example`: variáveis Meta App ID, Config ID, redirect URI e client secret/app secret.
- Modify `docs/development.md`, `docs/file-map.md`, `docs/bug-audit.md`, `docs/versions.md`: operação e handoff.
- Modify tests:
  - `tests/features/test_whatsapp_service.py`
  - `tests/web/test_whatsapp_integration.py`

---

## Task 1: Embedded Signup schema and state security

**Files:**
- Modify: `app/features/whatsapp/repository.py`
- Modify: `app/features/whatsapp/security.py`
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Produces:
  - `WhatsAppSettingsRepository.create_embedded_signup_session(started_by_user_id: int, state_token_hash: str) -> int`
  - `WhatsAppSettingsRepository.complete_embedded_signup_session(state_token_hash: str, provider_payload_json: str) -> bool`
  - `WhatsAppSettingsRepository.find_embedded_signup_session(state_token_hash: str) -> dict | None`
  - `hash_state_token(token: str) -> str`

- [ ] **Step 1: Write failing test**

Add to `tests/features/test_whatsapp_service.py`:

```python
from app.features.whatsapp.security import hash_state_token


def test_embedded_signup_session_is_completed_by_state_hash(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    state_hash = hash_state_token("state-token-123")

    session_id = repository.create_embedded_signup_session(
        started_by_user_id=1,
        state_token_hash=state_hash,
    )
    completed = repository.complete_embedded_signup_session(
        state_token_hash=state_hash,
        provider_payload_json='{"phone_number_id":"123"}',
    )
    session = repository.find_embedded_signup_session(state_hash)

    assert session_id > 0
    assert completed is True
    assert session["status"] == "completed"
    assert "phone_number_id" in session["provider_payload_json"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests\features\test_whatsapp_service.py::test_embedded_signup_session_is_completed_by_state_hash -q
```

Expected: FAIL because `hash_state_token` or repository methods do not exist.

- [ ] **Step 3: Implement minimal code**

In `app/features/whatsapp/security.py`:

```python
def hash_state_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

In `WhatsAppSettingsRepository.init_schema()` create:

```sql
CREATE TABLE IF NOT EXISTS whatsapp_embedded_signup_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_by_user_id INTEGER,
    state_token_hash TEXT UNIQUE,
    status TEXT,
    provider_payload_json TEXT,
    created_at TEXT,
    completed_at TEXT
)
```

Add the three repository methods with parameterized SQL and ISO timestamps.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests\features\test_whatsapp_service.py::test_embedded_signup_session_is_completed_by_state_hash -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/features/whatsapp/security.py app/features/whatsapp/repository.py tests/features/test_whatsapp_service.py
git commit -m "feat: track whatsapp embedded signup sessions"
```

## Task 2: Embedded Signup admin start and callback

**Files:**
- Modify: `app/features/whatsapp/routes.py`
- Modify: `app/templates/whatsapp_settings.html`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Consumes Task 1.
- Produces:
  - `POST /admin/integrations/whatsapp/embedded/start`
  - `GET /admin/integrations/whatsapp/embedded/callback`

- [ ] **Step 1: Write failing tests**

Add to `tests/web/test_whatsapp_integration.py`:

```python
def test_admin_can_start_embedded_signup_without_exposing_state(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/admin/integrations/whatsapp/embedded/start",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "state=" in response.headers["location"]
    assert "client_id=" in response.headers["location"]
    page = admin_client.get("/admin/integrations/whatsapp")
    assert "state-token" not in page.text


def test_embedded_signup_callback_rejects_unknown_state(admin_client: TestClient) -> None:
    response = admin_client.get(
        "/admin/integrations/whatsapp/embedded/callback",
        params={"state": "unknown", "code": "code-123"},
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests\web\test_whatsapp_integration.py::test_admin_can_start_embedded_signup_without_exposing_state tests\web\test_whatsapp_integration.py::test_embedded_signup_callback_rejects_unknown_state -q
```

Expected: FAIL with 404.

- [ ] **Step 3: Implement start route**

In `routes.py`, read:

```python
META_EMBEDDED_SIGNUP_APP_ID
META_EMBEDDED_SIGNUP_CONFIG_ID
META_EMBEDDED_SIGNUP_REDIRECT_URI
```

Create a random state with `secrets.token_urlsafe(32)`, persist only `hash_state_token(state)`, then redirect to:

```text
https://www.facebook.com/dialog/oauth?client_id=...&redirect_uri=...&state=...&config_id=...
```

If env vars are missing, redirect back to wizard after recording operational error in settings.

- [ ] **Step 4: Implement callback route**

Callback must:

- hash received `state`;
- require existing pending session;
- reject unknown state with `403`;
- persist provider payload JSON with code/status only;
- never render code/state;
- redirect to wizard.

- [ ] **Step 5: Add UI button**

In `whatsapp_settings.html`, add:

```html
<form method="post" action="/admin/integrations/whatsapp/embedded/start">
  <button class="ui-button ui-button--primary" type="submit">Conectar com Meta</button>
</form>
```

- [ ] **Step 6: Run tests to verify pass**

Run same targeted command. Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add app/features/whatsapp/routes.py app/templates/whatsapp_settings.html tests/web/test_whatsapp_integration.py
git commit -m "feat: start whatsapp embedded signup"
```

## Task 3: Automation rule persistence and admin UI

**Files:**
- Modify: `app/features/whatsapp/repository.py`
- Modify: `app/features/whatsapp/routes.py`
- Modify: `app/templates/whatsapp_settings.html`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Produces:
  - `WhatsAppSettingsRepository.automation_rules() -> list[dict]`
  - `WhatsAppSettingsRepository.create_automation_rule(...) -> int`
  - `POST /admin/integrations/whatsapp/automation-rules`

- [ ] **Step 1: Write failing test**

Add:

```python
def test_admin_can_create_whatsapp_automation_rule(admin_client: TestClient, legacy_test_state: LegacyTestState) -> None:
    response = admin_client.post(
        "/admin/integrations/whatsapp/automation-rules",
        data={
            "name": "Financeiro",
            "trigger_type": "keyword",
            "trigger_value": "fatura,boleto",
            "response_type": "safe_finance_lookup",
            "response_text": "Vou consultar suas faturas.",
            "target_department_id": "2",
            "is_active": "Sim",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    page = admin_client.get("/admin/integrations/whatsapp")
    assert "Financeiro" in page.text
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM whatsapp_automation_rules").fetchone()[0]
    assert count == 1
```

- [ ] **Step 2: Run test to verify fail**

Run:

```powershell
python -m pytest tests\web\test_whatsapp_integration.py::test_admin_can_create_whatsapp_automation_rule -q
```

Expected: FAIL with 404 or missing table.

- [ ] **Step 3: Implement schema**

Create `whatsapp_automation_rules` with fields from spec and `created_by_user_id`.

- [ ] **Step 4: Implement repository and route**

Use parameterized SQL. Empty `name` or `trigger_value` returns `400`.

- [ ] **Step 5: Implement UI**

Add card to wizard with:

- name;
- trigger type;
- trigger value;
- response type;
- response text;
- department;
- active checkbox;
- table of existing rules.

- [ ] **Step 6: Run test to verify pass**

Run targeted test. Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add app/features/whatsapp/repository.py app/features/whatsapp/routes.py app/templates/whatsapp_settings.html tests/web/test_whatsapp_integration.py
git commit -m "feat: manage whatsapp automation rules"
```

## Task 4: Safe automation engine for inbound messages

**Files:**
- Modify: `app/features/whatsapp/service.py`
- Modify: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Consumes automation rules from Task 3.
- Produces:
  - `resolve_automation_reply(repository: WhatsAppSettingsRepository, contact: dict, content: str) -> str`

- [ ] **Step 1: Write failing tests**

Add:

```python
def test_finance_keyword_without_client_returns_safe_handoff(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990000", "Cliente")
    repository.create_automation_rule(
        name="Financeiro",
        trigger_type="keyword",
        trigger_value="fatura,boleto",
        response_type="safe_finance_lookup",
        response_text="",
        target_department_id=None,
        is_active=True,
        created_by_user_id=1,
    )

    reply = resolve_automation_reply(repository, contact, "quero minha fatura")

    assert "preciso confirmar seu cadastro" in reply


def test_human_keyword_routes_to_attendant(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990001", "Cliente")

    reply = resolve_automation_reply(repository, contact, "falar com atendente")

    assert "encaminhar para um atendente" in reply
```

- [ ] **Step 2: Run tests to verify fail**

Run:

```powershell
python -m pytest tests\features\test_whatsapp_service.py::test_finance_keyword_without_client_returns_safe_handoff tests\features\test_whatsapp_service.py::test_human_keyword_routes_to_attendant -q
```

Expected: FAIL because function does not exist.

- [ ] **Step 3: Implement engine**

Rules:

- lowercase match on comma-separated keywords;
- `human_handoff` returns handoff message;
- `safe_finance_lookup` without `client_id` returns safe confirmation message;
- `safe_order_lookup` without `client_id` returns same safe confirmation;
- default returns current triage reply.

- [ ] **Step 4: Wire into `handle_inbound_message`**

After contact/conversation exists, if the contact already has triage state beyond first contact or content matches a rule, return automation reply. Do not query financial tables until linked `client_id` exists.

- [ ] **Step 5: Run tests to verify pass**

Run targeted tests and existing WhatsApp service tests. Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add app/features/whatsapp/service.py app/features/whatsapp/repository.py tests/features/test_whatsapp_service.py
git commit -m "feat: automate safe whatsapp replies"
```

## Task 5: Safe client-linked finance/order lookup

**Files:**
- Modify: `app/features/whatsapp/service.py`
- Modify: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Produces:
  - `WhatsAppSettingsRepository.open_receivables_for_client(client_id: int) -> list[dict]`
  - `WhatsAppSettingsRepository.recent_orders_for_client(client_id: int) -> list[dict]`

- [ ] **Step 1: Write failing tests**

Add tests that create minimal `clients`, `orders` and finance rows in temp DB, link `whatsapp_contacts.client_id`, then assert:

```python
assert "PED-QA-0001" in reply
assert "R$" in reply
```

Also assert another client's order is not included.

- [ ] **Step 2: Run tests to verify fail**

Run targeted lookup tests. Expected: FAIL.

- [ ] **Step 3: Implement repository queries**

Use parameterized SQL:

- `receivables.client_id=? AND status!='Recebido'`;
- `orders` joined through opportunities/client where available;
- limit each response to 5 rows.

- [ ] **Step 4: Implement response formatting**

Format concise WhatsApp text, no HTML:

```text
Encontrei 2 lançamento(s):
- PED-2026-0001 · R$ 1.234,00 · vence 2026-07-10
```

- [ ] **Step 5: Run tests to verify pass**

Run targeted service tests. Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add app/features/whatsapp/service.py app/features/whatsapp/repository.py tests/features/test_whatsapp_service.py
git commit -m "feat: answer linked whatsapp finance and order queries"
```

## Task 6: Official QR code and short link management

**Files:**
- Modify: `app/features/whatsapp/client.py`
- Modify: `app/features/whatsapp/repository.py`
- Modify: `app/features/whatsapp/routes.py`
- Modify: `app/templates/whatsapp_settings.html`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Produces:
  - `MetaWhatsAppClient.create_qr_code(...) -> dict`
  - `WhatsAppSettingsRepository.save_qr_code(...) -> int`
  - `POST /admin/integrations/whatsapp/qr-codes`

- [ ] **Step 1: Write failing test**

Use monkeypatch fake client:

```python
def test_admin_can_generate_official_whatsapp_qr_code(admin_client: TestClient, monkeypatch) -> None:
    _save_valid_whatsapp_settings(admin_client)

    class FakeMetaClient:
        def create_qr_code(self, **kwargs):
            return {"code": "QR123", "deep_link_url": "https://wa.me/message/QR123"}

    monkeypatch.setattr("app.features.whatsapp.routes.MetaWhatsAppClient", FakeMetaClient)
    response = admin_client.post(
        "/admin/integrations/whatsapp/qr-codes",
        data={"name": "Atendimento", "prefilled_message": "Olá, vim pelo site"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    page = admin_client.get("/admin/integrations/whatsapp")
    assert "https://wa.me/message/QR123" in page.text
```

- [ ] **Step 2: Run test to verify fail**

Run targeted test. Expected: FAIL with 404 or missing method.

- [ ] **Step 3: Implement client boundary**

Add method using Meta endpoint for QR codes/short links. Keep fake-friendly signature:

```python
def create_qr_code(self, *, api_version, phone_number_id, access_token, prefilled_message) -> dict:
```

- [ ] **Step 4: Implement repository/table and route**

Persist `name`, `code`, `short_link`, `prefilled_message`, `is_active`, user and timestamps.

- [ ] **Step 5: Implement UI**

Add card with form and existing QR code table.

- [ ] **Step 6: Run test to verify pass**

Run targeted test. Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add app/features/whatsapp/client.py app/features/whatsapp/repository.py app/features/whatsapp/routes.py app/templates/whatsapp_settings.html tests/web/test_whatsapp_integration.py
git commit -m "feat: manage official whatsapp qr codes"
```

## Task 7: Docs and full verification

**Files:**
- Modify: `.env.example`
- Modify: `docs/development.md`
- Modify: `docs/file-map.md`
- Modify: `docs/bug-audit.md`
- Modify: `docs/versions.md`

**Interfaces:**
- Consumes all prior tasks.

- [ ] **Step 1: Update environment docs**

Add:

```text
META_EMBEDDED_SIGNUP_APP_ID=
META_EMBEDDED_SIGNUP_CONFIG_ID=
META_EMBEDDED_SIGNUP_REDIRECT_URI=
META_EMBEDDED_SIGNUP_CLIENT_SECRET=
```

- [ ] **Step 2: Update handoff docs**

Document:

- WhatsApp Web QR remains out of production core;
- Embedded Signup setup;
- automation rule behavior;
- safe lookup constraints;
- QR/short link is for customer initiation.

- [ ] **Step 3: Run full gate**

```powershell
python -m pytest tests\web tests\performance tests\characterization tests\features -q
python -m ruff check app tests
node --check app\static\chat_realtime.js
node --test tests\js\shell-navigation.test.js
node --test tests\js\chat-notifications.test.js
node --test tests\js\profile-avatar-editor.test.js
git diff --check
```

Expected:

- pytest all pass;
- Ruff all checks passed;
- Node tests pass;
- diff check has no output.

- [ ] **Step 4: Commit**

```powershell
git add .env.example docs app tests
git commit -m "docs: hand off whatsapp embedded signup automation"
```

## Self-review

- Spec coverage: Embedded Signup, wizard button, webhook preservation, automation rules, safe responses, linked lookups and official QR/short links are covered.
- Scope control: Fase 2 perfis/permissões and Fase 3 RH are intentionally not implemented in this plan; they need separate plans.
- Placeholder scan: no placeholder markers or vague implementation-only steps intentionally remain.
- Type consistency: repository, service and client names are introduced before use and match route/test expectations.
