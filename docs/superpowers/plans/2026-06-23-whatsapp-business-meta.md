# WhatsApp Business Meta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an official Meta WhatsApp Business integration with admin-only setup wizard, secure webhook, conservative triage, and internal chat mirroring.

**Architecture:** Add a focused `app/features/whatsapp/` domain for config, security, persistence, Meta client and triage logic. Keep `app/main.py` as the route mount/bootstrap point while the backend is still monolithic. Store operational settings in SQLite now, with encrypted/hashed secrets and a future-safe boundary for PostgreSQL.

**Tech Stack:** FastAPI, Jinja2, SQLite compatibility, Python stdlib crypto/HMAC, HTTPX-compatible client boundary using `urllib.request` for zero new runtime dependency, current SIST-iONM design system.

## Global Constraints

- Use the official Meta WhatsApp Business Cloud API, not WhatsApp Web automation.
- Only `admin` users may view, save, test, activate or deactivate WhatsApp settings.
- Do not commit or render `access_token`, `app_secret` or `verify_token` in clear text.
- Validate `X-Hub-Signature-256` for webhook POST requests.
- New behavior must be covered by failing tests before implementation.
- Preserve existing chat, shell navigation and static asset patterns.
- Do not expose customer financial/order data unless the WhatsApp phone is securely linked to a client.

---

## File Structure

- Create `app/features/whatsapp/__init__.py`: package marker.
- Create `app/features/whatsapp/security.py`: secret masking, reversible local encryption, verify-token hashing, webhook signature validation.
- Create `app/features/whatsapp/client.py`: minimal Meta Cloud API client and fake-friendly interface.
- Create `app/features/whatsapp/repository.py`: SQL helpers for settings, contacts, conversations, messages, departments and triage states.
- Create `app/features/whatsapp/service.py`: wizard status, inbound message triage, chat room mirroring, safe automatic responses.
- Create `app/features/whatsapp/routes.py`: `APIRouter` for admin wizard and webhook.
- Create `app/templates/whatsapp_settings.html`: admin-only wizard UI.
- Modify `app/main.py`: import and mount router, initialize tables, bump `ASSET_VERSION`.
- Modify `app/shared/web/templates/layouts/base.html`: add admin menu item.
- Modify `app/shared/web/static/css/administration.css`: wizard layout polish.
- Modify `.env.example`: add WhatsApp variables and encryption key guidance.
- Modify `docs/file-map.md`, `docs/development.md`, `docs/bug-audit.md`, `docs/versions.md`: handoff notes.
- Add tests:
  - `tests/features/test_whatsapp_security.py`
  - `tests/features/test_whatsapp_service.py`
  - `tests/web/test_whatsapp_integration.py`

---

## Task 1: Security primitives and setting model

**Files:**
- Create: `app/features/whatsapp/security.py`
- Create: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_security.py`

**Interfaces:**
- Produces:
  - `mask_secret(value: str | None) -> str`
  - `hash_verify_token(token: str) -> str`
  - `verify_token_matches(token: str, stored_hash: str) -> bool`
  - `encrypt_secret(value: str, master_key: str) -> str`
  - `decrypt_secret(value: str, master_key: str) -> str`
  - `valid_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool`
  - `WhatsAppSettingsRepository`

- [ ] Write failing tests for masking, hashing, encryption roundtrip and HMAC signature validation.
- [ ] Run `python -m pytest tests/features/test_whatsapp_security.py -q`; expected failure because modules do not exist.
- [ ] Implement minimal `security.py` with stdlib `hmac`, `hashlib`, `base64`, and XOR stream derived from SHA-256 for local reversible encryption.
- [ ] Implement repository methods for table creation and settings persistence using an injected sqlite connection.
- [ ] Run `python -m pytest tests/features/test_whatsapp_security.py -q`; expected pass.
- [ ] Commit `feat: add whatsapp security primitives`.

## Task 2: Admin wizard routes and template

**Files:**
- Create: `app/features/whatsapp/routes.py`
- Create: `app/templates/whatsapp_settings.html`
- Modify: `app/main.py`
- Modify: `app/shared/web/templates/layouts/base.html`
- Modify: `app/shared/web/static/css/administration.css`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Consumes security/repository from Task 1.
- Produces:
  - router mounted under `/admin/integrations/whatsapp`
  - admin GET wizard page
  - admin POST save settings
  - admin POST generate verify token
  - admin POST test connection
  - admin POST toggle enabled

- [ ] Write failing tests proving non-admin gets `403`, admin sees the wizard, secrets are not rendered, saving credentials updates status, and the menu includes WhatsApp only for admins.
- [ ] Run `python -m pytest tests/web/test_whatsapp_integration.py -q`; expected failure.
- [ ] Implement routes with server-side `require_admin`.
- [ ] Implement template using current `ui-admin-*` and `ui-*` components.
- [ ] Add menu item under Administração.
- [ ] Add CSS only if existing administration classes are not enough.
- [ ] Run `python -m pytest tests/web/test_whatsapp_integration.py -q`; expected pass.
- [ ] Commit `feat: add whatsapp admin setup wizard`.

## Task 3: Webhook verification and inbound persistence

**Files:**
- Create: `app/features/whatsapp/service.py`
- Modify: `app/features/whatsapp/routes.py`
- Modify: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_service.py`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Produces:
  - `normalize_inbound_payload(payload: dict) -> list[InboundWhatsAppMessage]`
  - `handle_inbound_message(message: InboundWhatsAppMessage) -> WhatsAppInboundResult`

- [ ] Write failing tests for GET webhook valid/invalid token, POST invalid signature, POST valid signed payload, and duplicate provider message id.
- [ ] Run targeted tests; expected failure.
- [ ] Implement table creation for contacts, conversations, messages, triage states, departments and settings.
- [ ] Implement GET verification and POST signature validation.
- [ ] Persist inbound messages idempotently by `provider_message_id`.
- [ ] Run targeted tests; expected pass.
- [ ] Commit `feat: receive whatsapp webhook messages`.

## Task 4: First-contact triage and safe automatic responses

**Files:**
- Modify: `app/features/whatsapp/service.py`
- Modify: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Consumes inbound persistence from Task 3.
- Produces triage states: `ask_name`, `ask_origin`, `choose_department`, `assigned`.

- [ ] Write failing tests for unknown contact receiving name prompt, origin prompt, department selection, and safe refusal for financial data without linked client.
- [ ] Run targeted tests; expected failure.
- [ ] Implement triage state machine and default department seed.
- [ ] Implement conservative intent recognition for finance/orders/human support.
- [ ] Run targeted tests; expected pass.
- [ ] Commit `feat: triage whatsapp first contacts`.

## Task 5: Meta client and manual send boundary

**Files:**
- Create: `app/features/whatsapp/client.py`
- Modify: `app/features/whatsapp/routes.py`
- Modify: `app/features/whatsapp/service.py`
- Test: `tests/features/test_whatsapp_service.py`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Produces:
  - `MetaWhatsAppClient.send_text(phone_number_id: str, access_token: str, to_phone: str, message: str) -> dict`
  - admin test route that accepts a test phone and message.

- [ ] Write failing tests using a fake Meta client for successful test send and failed send status.
- [ ] Run targeted tests; expected failure.
- [ ] Implement Meta client boundary without logging secrets.
- [ ] Implement wizard test route with fake-client injection for tests.
- [ ] Run targeted tests; expected pass.
- [ ] Commit `feat: add whatsapp meta send client`.

## Task 6: Internal chat mirroring

**Files:**
- Modify: `app/features/whatsapp/service.py`
- Modify: `app/features/whatsapp/repository.py`
- Modify: `app/main.py` if chat helpers need a small exported hook.
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Consumes chat tables.
- Produces a linked `chat_room_id` per WhatsApp conversation and an internal `chat_messages` entry for inbound messages.

- [ ] Write failing tests proving inbound WhatsApp creates/reuses a chat room named `WhatsApp · ...` and inserts a visible internal chat message.
- [ ] Run targeted tests; expected failure.
- [ ] Implement room creation/reuse and message insertion.
- [ ] Run targeted tests; expected pass.
- [ ] Commit `feat: mirror whatsapp messages into chat`.

## Task 7: Documentation and final verification

**Files:**
- Modify: `.env.example`
- Modify: `docs/file-map.md`
- Modify: `docs/development.md`
- Modify: `docs/bug-audit.md`
- Modify: `docs/versions.md`

**Interfaces:**
- Consumes all completed implementation tasks.

- [ ] Update `.env.example` with WhatsApp variables and clear security notes.
- [ ] Update docs with wizard path, setup steps, security caveats and testing notes.
- [ ] Run:
  - `python -m pytest tests/web tests/performance tests/characterization tests/features -q`
  - `python -m ruff check app tests`
  - `node --check app/static/chat_realtime.js`
  - `node --test tests/js/shell-navigation.test.js`
  - `node --test tests/js/chat-notifications.test.js`
  - `node --test tests/js/profile-avatar-editor.test.js`
  - `git diff --check`
- [ ] Commit `docs: hand off whatsapp business integration`.

## Self-review

- Spec coverage: webhook, admin wizard, triage, sectors, safe data access, chat mirroring and docs are covered.
- Placeholder scan: no placeholder markers or vague implementation-only steps intentionally remain.
- Type consistency: all public names introduced in earlier tasks are consumed by later tasks with the same spelling.
