# Mapa de arquivos para manutenção

## Estrutura atual

```text
app/main.py                         aplicação legada, rotas e regras ainda monolíticas
app/features/catalog_import/       importação Excel de clientes e fornecedores
app/templates/                      18 templates compatíveis
app/shared/web/templates/layouts/   shell principal
app/shared/web/templates/components macros Jinja
app/shared/web/templates/errors/    páginas 400/403/404/500
app/shared/web/static/css/           design system e módulos visuais
app/shared/web/static/js/            comportamento progressivo
app/shared/web/static/js/shell-navigation.js navegação central com shell persistente
app/shared/web/static/icons/         sprite SVG local
app/static/chat_realtime.js          cliente WebSocket
tests/characterization/              inventário e preservação de rotas/render
tests/web/                           contratos visuais, segurança e acessibilidade
tests/performance/                   budgets de consulta, paginação e cache
```

## Mapa das 18 telas

| Template | Rotas principais | Contexto Jinja principal | CSS/JS específico | Teste principal |
|---|---|---|---|---|
| `base.html` | todas | `user`, `cfg`, `current_path`, `can_view_bi`, `asset_version` | CSS base, `app-shell.js`, `navigation.js`, chat | `test_shell_contract.py` |
| `login.html` | `GET/POST /login` | `error` | `executive.css`, `feedback.js` | `test_executive_pages.py` |
| `dashboard.html` | `/` | `kpis`, `opps` | `executive.css` | executivo + query budget |
| `bi_gerencial.html` | `/bi-gerencial` | cenários, recomendações, pipeline e focos | `executive.css`, `feedback.js` | executivo/render |
| `feed.html` | `/feed`, `/feed/post`, like/comment | `posts`, `comments_by_post` | `portal.css` | `test_portal_pages.py` |
| `chat.html` | `/chat`, privados e mensagens | `rooms`, `users`, `messages`, `room_id`, `pager` | `portal.css`, `chat_realtime.js` | portal + performance |
| `profile.html` | `/profile`, save/avatar | `profile`, `departments` | `portal.css` | portal |
| `orgchart.html` | `/orgchart` | `departments`, `people` | `portal.css` | portal |
| `crud.html` | `/cadastros/{table}`, edit/save/delete e importação | `table`, `meta`, `rows`, `edit`, `pager`, `import_feedback` | `administration.css`, forms/tables | administração + paginação/importação |
| `settings.html` | `/settings` e usuários/e-mail/backup | `users`, `sellers`, `edit_user`, `role_emails` | `administration.css`, forms/tables | administração |
| `permissions.html` | `/admin/permissions` | `rows` | `administration.css`, forms/tables | administração |
| `opportunities.html` | `/opportunities`, create/move | `opps`, `kanban`, `statuses`, cadastros, `pager` | `crm.css`, `forms.js` | `test_crm_pages.py` + budget |
| `opportunity_card.html` | `/opportunities/{id}/card` e ações | `o`, `comments`, `notes`, `docs`, `products` | `crm.css` | CRM |
| `orders.html` | `/orders`, closing | `orders`, `status_fiscal`, `status_finance` | `crm.css`, `feedback.js` | CRM |
| `purchases.html` | `/backoffice/purchases` | `rows`, `suppliers` | `crm.css`, `tables.js` | CRM |
| `finance.html` | `/finance?segment=...` | `segment`, `rows`, `total`, `orders`, `pager` | `finance.css` | financeiro + paginação |
| `commissions.html` | `/commissions` | `rows` | `finance.css`, `tables.js` | `test_finance_pages.py` |
| `seller_reports.html` | `/reports/sellers` e review | `report`, `sellers`, `pager` | `finance.css`, feedback/tables | financeiro + paginação |

## Linha de raciocínio para alterações

1. Localize rota e chaves de contexto em `app/main.py`.
2. Escreva ou ajuste primeiro o teste do módulo correspondente.
3. Preserve URL, método, nomes de campos e valores de status.
4. Reuse macros e classes `ui-*`; não reintroduza CSS global de página.
5. Qualquer lista potencialmente grande usa `pagination_values()` e o macro `pagination()`.
6. Mensagens e dados de usuário entram no DOM por `textContent`, nunca por HTML dinâmico.
7. Rode o teste específico, depois `tests/web`, `tests/performance` e `tests/characterization`.
8. Confira o SHA-256 do banco-fonte antes de entregar.

## Navegação persistente do shell

`shell-navigation.js` intercepta exclusivamente links `data-nav-item` do menu. Ele mantém menu, topbar e chat montados, troca `#main-content`, sincroniza título, breadcrumb, histórico e assets específicos e emite `sistionm:content-updated`.

Scripts que ligam eventos a elementos de página devem ser idempotentes: execute na carga tradicional e no evento `sistionm:content-updated`, marcando cada elemento com `data-ready`. Formulários, downloads e links fora do menu não devem ser interceptados. Qualquer falha na resposta ou em assets deve voltar à navegação tradicional.

No chat, `attachment_is_image` é calculado no backend. PNG, JPG/JPEG, WebP e GIF são exibidos como miniaturas; os demais formatos permanecem como links.

## Importação de clientes e fornecedores

| Arquivo | Responsabilidade |
|---|---|
| `app/features/catalog_import/service.py` | esquema das colunas, geração do modelo `.xlsx`, validação, normalização do documento e transação de inclusão/atualização |
| `app/main.py` | autorização, upload limitado, download do modelo e feedback via sessão |
| `app/templates/crud.html` | botões, formulário progressivo e resumo do processamento |
| `tests/features/test_catalog_import_service.py` | regras de planilha e persistência |
| `tests/web/test_catalog_import.py` | rotas, permissões, download, upload e apresentação |

O documento normalizado é a chave de atualização. O serviço cria novos registros, atualiza os existentes e ignora duplicidades dentro da mesma planilha. Erros estruturais impedem qualquer escrita.

## Próxima organização por domínio

O frontend está modular, mas as rotas e regras ainda permanecem em `app/main.py`. O próximo workstream deve extrair `identity`, `portal`, `crm`, `orders`, `finance`, `administration` e `reporting`, criar repositórios SQLAlchemy/PostgreSQL e manter este mapa como contrato de apresentação.
