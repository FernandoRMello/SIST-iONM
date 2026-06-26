# Custos Fixos Recorrentes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar cadastros categorizados de custos fixos que geram automaticamente e sem duplicidade contas mensais em `A pagar`.

**Architecture:** O novo domínio `app/features/finance` concentra calendário, persistência e geração recorrente. `app/main.py` mantém apenas inicialização de schema e rotas finas durante a transição do monólito; a tela financeira consome os serviços do domínio e preserva o design system atual.

**Tech Stack:** Python 3, FastAPI, SQLite compatível com futura migração PostgreSQL, Jinja2, CSS existente e pytest.

## Global Constraints

- Recorrência mensal.
- Geração automática idempotente.
- Vencimento em dia não existente usa o último dia do mês.
- Sábado, domingo ou feriado cadastrado move o vencimento para o próximo dia útil.
- Exclusão física somente sem histórico; com histórico, exclusão lógica.
- Alterações não modificam contas já geradas.
- Administradores e financeiros mantêm o acesso atual.

---

### Task 1: Calendário financeiro

**Files:**
- Create: `app/features/finance/__init__.py`
- Create: `app/features/finance/calendar.py`
- Test: `tests/features/test_recurring_costs.py`

**Interfaces:**
- Produces: `calculate_due_date(period: str, due_day: int, holidays: set[date]) -> date`.

- [ ] Escrever testes para mês curto, sábado, domingo e feriado consecutivo.
- [ ] Executar `python -m pytest tests/features/test_recurring_costs.py -q` e confirmar falha por módulo ausente.
- [ ] Implementar `calculate_due_date`, validando competência `YYYY-MM` e dia de 1 a 31.
- [ ] Reexecutar o teste e confirmar aprovação.

### Task 2: Schema, repositório e geração idempotente

**Files:**
- Create: `app/features/finance/recurring_costs.py`
- Modify: `app/main.py`
- Test: `tests/features/test_recurring_costs.py`

**Interfaces:**
- Consumes: `calculate_due_date`.
- Produces: `generate_due_recurring_costs(connection, today_date, actor_user_id) -> dict`.
- Produces tabelas `cost_categories`, `recurring_costs`, `recurring_cost_occurrences`, `business_holidays` e `recurring_cost_runs`.

- [ ] Escrever testes de geração, vigência, prevenção de duplicidade e preservação de valores históricos.
- [ ] Executar os testes e confirmar falhas pela ausência de tabelas/serviço.
- [ ] Adicionar schema, índices e referência opcional em `payables`.
- [ ] Implementar geração transacional por competência com restrição única `(recurring_cost_id, period)`.
- [ ] Executar os testes e confirmar aprovação.

### Task 3: CRUD seguro de categorias e custos recorrentes

**Files:**
- Create: `app/features/finance/routes.py`
- Modify: `app/main.py`
- Test: `tests/web/test_recurring_cost_pages.py`

**Interfaces:**
- Produces rotas `/finance/cost-categories/*` e `/finance/recurring-costs/*`.
- Exclusão retorna remoção física sem uso ou estado `Excluído` com histórico.

- [ ] Escrever testes web para criar, editar, pausar, reativar e excluir custos e categorias.
- [ ] Executar os testes e confirmar `404` nas rotas ausentes.
- [ ] Implementar validação, autorização, mensagens e redirects para `segment=costs&cost_tab=...`.
- [ ] Executar os testes e confirmar aprovação.

### Task 4: Interface financeira categorizada

**Files:**
- Modify: `app/templates/finance.html`
- Modify: `app/shared/web/static/css/finance.css`
- Modify: `app/main.py`
- Test: `tests/web/test_recurring_cost_pages.py`
- Test: `tests/web/test_finance_pages.py`

**Interfaces:**
- Consumes listas de categorias, custos recorrentes, feriados, favorecidos e centros de custo.
- Produces subabas `Lançamentos variáveis`, `Custos fixos recorrentes` e `Categorias`.

- [ ] Escrever testes de contrato para subabas, campos em listas e ações de manutenção.
- [ ] Executar testes e confirmar falhas por marcação ausente.
- [ ] Renderizar somente a subaba solicitada, com formulários compactos, tabelas leves e confirmações de exclusão.
- [ ] Exibir origem recorrente nas contas em `A pagar`.
- [ ] Executar os testes financeiros e confirmar aprovação.

### Task 5: Automação, indicadores e documentação

**Files:**
- Modify: `app/main.py`
- Modify: `docs/file-map.md`
- Modify: `docs/bug-audit.md`
- Test: `tests/web/test_recurring_cost_pages.py`
- Test: `tests/web/test_executive_pages.py`

**Interfaces:**
- Consumes: `generate_due_recurring_costs`.
- Produces geração diária segura no primeiro acesso financeiro e inclusão em `A pagar`, Dashboard e BI por meio da tabela `payables`.

- [ ] Escrever teste que simula competência não gerada e confirma geração automática antes da leitura financeira.
- [ ] Executar o teste e confirmar ausência da conta.
- [ ] Integrar execução automática protegida por idempotência e registrar execuções/falhas.
- [ ] Atualizar documentação dos arquivos, tabelas e regras.
- [ ] Executar suíte completa, Ruff, testes JavaScript e `git diff --check`.

