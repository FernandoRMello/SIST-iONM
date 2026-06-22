# Importação de Clientes e Fornecedores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar importação transacional `.xlsx` e modelos para os cadastros de clientes e fornecedores.

**Architecture:** Um serviço puro em `app/features/catalog_import` conhece os dois schemas permitidos, gera/valida workbooks e faz upsert por documento normalizado. As rotas FastAPI permanecem finas e o template CRUD apenas apresenta download, upload e feedback.

**Tech Stack:** Python 3.13, FastAPI 0.137.1, openpyxl 3.1.5, SQLite atual, Jinja2, pytest.

## Global Constraints

- Aceitar somente `.xlsx`, até 5 MiB e 5.000 linhas.
- Nunca escrever no banco-fonte durante testes.
- Clientes seguem permissão atual; fornecedores exigem admin.
- Documento existente atualiza; novo documento insere.
- Erro estrutural ou de banco não deixa escrita parcial.

---

### Task 1: Serviço de planilha e persistência

**Files:**
- Create: `app/features/__init__.py`
- Create: `app/features/catalog_import/__init__.py`
- Create: `app/features/catalog_import/service.py`
- Test: `tests/features/test_catalog_import_service.py`

**Interfaces:**
- Produces: `build_template(table) -> bytes`, `parse_workbook(table, content) -> list[dict]`, `import_rows(connection, table, rows) -> ImportResult`.

- [ ] Escrever testes falhando para modelos, cabeçalhos, limites, duplicidade e upsert.
- [ ] Rodar `python -m pytest tests/features/test_catalog_import_service.py -q` e confirmar RED.
- [ ] Implementar schemas permitidos, parser read-only/data-only, normalização e transação.
- [ ] Rodar o teste e confirmar GREEN.

### Task 2: Rotas, permissões e interface CRUD

**Files:**
- Modify: `app/main.py`
- Modify: `app/templates/crud.html`
- Modify: `app/shared/web/static/css/administration.css`
- Test: `tests/web/test_catalog_import.py`

**Interfaces:**
- Consumes: serviço da Task 1.
- Produces: `GET /cadastros/{table}/import-template`, `POST /cadastros/{table}/import` e feedback de sessão `catalog_import_feedback`.

- [ ] Escrever testes falhando de download, importação HTTP, permissão e visibilidade dos controles.
- [ ] Rodar `python -m pytest tests/web/test_catalog_import.py -q` e confirmar RED.
- [ ] Implementar rotas finas, limite do upload, feedback e bloco visual acessível.
- [ ] Rodar testes da feature, web, performance e caracterização.
- [ ] Rodar Ruff, sintaxe JS, `git diff --check` e verificar que o banco-fonte não foi escrito pelo teste.
- [ ] Commitar `feat: import clients and suppliers from Excel`.

## Self-review

- O escopo cobre somente clientes/fornecedores e não cria um importador genérico inseguro.
- O serviço não depende de request, sessão ou template.
- Todos os limites, campos obrigatórios, permissões, comportamento de duplicados e rollback estão definidos sem placeholders.
