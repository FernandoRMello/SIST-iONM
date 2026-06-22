# Desempenho e capacidade

## Gargalo medido

Dashboard e pipeline chamavam `opp_summary()` para cada oportunidade. Com 21 oportunidades, a instrumentação observou 47 consultas no dashboard e 48 no pipeline. O custo crescia linearmente e cada consulta abria uma conexão SQLite própria.

## Correções

- `opportunity_summaries()` agrega itens, margens e comissões em lote.
- `opportunity_kpis()` calcula KPIs sem materializar todas as oportunidades.
- Dashboard usa três grupos de consulta com contagem estável.
- Pipeline consulta metadados, total e uma página de oportunidades; crescimento de linhas não aumenta o número de consultas.
- CRUD, pipeline, chat, finanças e relatório de vendedores usam página padrão 25 e máximo 100.
- Endpoint `/chat/messages/{room_id}` retorna mensagens e metadados de paginação sem N+1.
- Financeiro consulta somente o segmento ativo: `receivables`, `payables` ou `costs`.
- Toda conexão SQLite é fechada deterministicamente ao sair de `db()`.
- Assets versionados usam cache imutável; HTML usa `no-store`.

## Limites e projeção

Os testes inserem mais 20 oportunidades e exigem os mesmos budgets: dashboard até 6 consultas, pipeline até 8 e chat até 8. Isso sustenta crescimento de 10x no número de registros sem crescimento correspondente na quantidade de round-trips por página. O volume transferido fica limitado pelo `page_size`.

Ainda não é um benchmark de concorrência. A migração para PostgreSQL deve adicionar pool de conexões, índices para joins/filtros e medição de latência p95. Não criar índices por intuição; validar com `EXPLAIN ANALYZE` após o cutover.

## Paginação

`pagination_values(total, page, page_size)`:

- normaliza página negativa para 1;
- usa 25 quando o tamanho é inválido;
- limita a 100;
- ajusta páginas acima do último resultado;
- retorna `page`, `page_size`, `total` e `pages`.

O macro Jinja `pagination()` preserva query strings existentes no `base_url`.

## Método e comandos

```powershell
python -m pytest tests\performance -q
python -m pytest tests\performance\test_query_budget.py -q
python -m pytest tests\performance\test_pagination.py -q
```

Critérios: contagem de consultas não cresce com linhas extras, uma página não renderiza mais registros que o limite e a origem SQLite permanece inalterada.
