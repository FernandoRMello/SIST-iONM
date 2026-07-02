# WhatsApp Embedded Signup App Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir configurar App ID, Config ID, Redirect URI e Client Secret do Embedded Signup diretamente no wizard administrativo.

**Architecture:** `WhatsAppSettingsRepository` persiste a configuração e executa migração incremental do SQLite. O router resolve valores efetivos com precedência do ambiente, enquanto o template recebe somente campos públicos, origem e estado mascarado do segredo.

**Tech Stack:** Python 3.13, FastAPI, SQLite, Jinja2, Fernet e pytest.

## Global Constraints

- Somente administradores podem consultar ou alterar a configuração.
- Client Secret nunca retorna em texto claro.
- `WHATSAPP_SECRET_KEY` é obrigatório em produção.
- Variáveis de ambiente substituem valores persistidos.
- Produção exige Redirect URI HTTPS.
- Instalações existentes não perdem dados.

---

### Task 1: Persistência e migração incremental

**Files:**
- Modify: `app/features/whatsapp/repository.py`
- Test: `tests/features/test_whatsapp_service.py`

**Interfaces:**
- Produces: `save_embedded_signup_config(...)`.
- Produces: quatro colunas novas em `whatsapp_settings`.

- [ ] Criar teste que inicializa banco legado, salva configuração e confirma preservação do segredo quando o campo fica vazio.
- [ ] Executar o teste e confirmar falha por método/coluna ausente.
- [ ] Implementar migração via `PRAGMA table_info` e persistência parametrizada.
- [ ] Reexecutar o teste e confirmar aprovação.

### Task 2: Rota, segurança e precedência

**Files:**
- Modify: `app/features/whatsapp/routes.py`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Produces: `POST /admin/integrations/whatsapp/embedded/config`.
- Consumes: `WhatsAppSecurityEngine`.
- Embedded start resolve ambiente antes do banco.

- [ ] Criar testes para salvar, mascarar, bloquear não administrador, usar banco sem `.env`, validar URL e aplicar override.
- [ ] Executar testes e confirmar falhas esperadas.
- [ ] Implementar validação, criptografia e resolução efetiva.
- [ ] Reexecutar testes e confirmar aprovação.

### Task 3: Wizard e documentação

**Files:**
- Modify: `app/templates/whatsapp_settings.html`
- Modify: `docs/development.md`
- Test: `tests/web/test_whatsapp_integration.py`

**Interfaces:**
- Consumes: `embedded_config`, `embedded_config_sources` e `embedded_client_secret_status`.

- [ ] Criar contrato de renderização dos quatro campos e indicador de origem.
- [ ] Executar teste e confirmar falha por marcação ausente.
- [ ] Adicionar seção compacta e atualizar instruções.
- [ ] Executar testes WhatsApp, suíte web afetada, Ruff e `git diff --check`.

