# Mapa de arquivos para manutenção

## Estrutura atual

```text
app/main.py                         aplicação legada, rotas e regras ainda monolíticas
app/features/catalog_import/       importação Excel de clientes e fornecedores
app/features/access_control/       perfis configuráveis, permissões especiais e atribuição a usuários
app/features/hr/                   colaboradores, vendedores vinculados, regras e folha mensal
app/templates/                      templates originais + WhatsApp + Perfis + RH
app/shared/web/templates/layouts/   shell principal
app/shared/web/templates/components macros Jinja
app/shared/web/templates/errors/    páginas 400/403/404/500
app/shared/web/static/css/           design system e módulos visuais
app/shared/web/static/js/            comportamento progressivo
app/shared/web/static/js/shell-navigation.js navegação central com shell persistente
app/static/chat_notification_rules.js regras testáveis de visibilidade e badge
app/features/profile_avatar/        validação e normalização de fotos de perfil
app/features/whatsapp/              integração WhatsApp Business Cloud API, wizard admin, webhook e triagem
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

## Campos e relações padronizadas

- A topbar contém uma busca global visualmente preparada (`data-global-search`), ainda sem engine funcional. Ela serve como reserva de UX para uma busca futura sem alterar o fluxo atual.
- Em RH, `job_title` é select com cargos comuns para reduzir variação textual. O campo continua postando `job_title` para preservar compatibilidade.
- Em RH, `contract_type` é select baseado em tipos aceitos pelo módulo de folha e demonstrativos.
- Em Financeiro → Custos, o favorecido agora pode vir de `suppliers` ou `sellers`. O schema atual ainda grava o nome final em `costs.vendor`, evitando migração nesta etapa; o formulário mantém `vendor` como fallback manual.
- Campos livres continuam permitidos apenas quando não há cadastro relacionado ou quando o texto realmente é descritivo, como observações, documento e descrição.

## Navegação persistente do shell

`shell-navigation.js` intercepta exclusivamente links `data-nav-item` do menu. Ele mantém menu, topbar e chat montados, troca `#main-content`, sincroniza título, breadcrumb, histórico e assets específicos e emite `sistionm:content-updated`.

Scripts que ligam eventos a elementos de página devem ser idempotentes: execute na carga tradicional e no evento `sistionm:content-updated`, marcando cada elemento com `data-ready`. Formulários, downloads e links fora do menu não devem ser interceptados. Qualquer falha na resposta ou em assets deve voltar à navegação tradicional.

No chat, `attachment_is_image` é calculado no backend. PNG, JPG/JPEG, WebP e GIF são exibidos como miniaturas; os demais formatos permanecem como links.

## Colaboração e identidade

- `chat_read_state` persiste o último ID lido por usuário/sala; `/chat/context` restaura contadores e `/chat/read/{room_id}` confirma leitura.
- `feed_reactions` guarda uma única reação `like` ou `dislike` por usuário/publicação. Repetir remove; selecionar a oposta substitui.
- Posts e comentários recebem `avatar_path` na consulta e usam a inicial como fallback.
- `profile-avatar-editor.js` controla moldura, arraste e zoom; `app/features/profile_avatar/service.py` nunca confia no arquivo do navegador e gera JPEG RGB 512 × 512.

## Integração WhatsApp Business

| Arquivo | Responsabilidade |
|---|---|
| `app/features/whatsapp/security.py` | máscara de segredos, hash do verify token, criptografia local e validação `X-Hub-Signature-256` |
| `app/features/whatsapp/repository.py` | tabelas de configuração, contatos, conversas, mensagens, setores, triagem, Embedded Signup, regras, QR codes e consultas vinculadas |
| `app/features/whatsapp/service.py` | normalização de payloads Meta, idempotência, triagem inicial, automações seguras e espelhamento no chat |
| `app/features/whatsapp/client.py` | envio de texto e geração de QR/short link pela Cloud API oficial da Meta |
| `app/features/whatsapp/routes.py` | wizard admin, Embedded Signup, regras, QR codes, teste de conexão e webhook público |
| `app/templates/whatsapp_settings.html` | wizard `Administração → WhatsApp Business` |

Somente `admin` pode acessar e alterar a integração. `access_token`, `app_secret` e `verify_token` não são renderizados em texto claro após o salvamento. O POST do webhook valida assinatura HMAC antes de processar mensagens. Mensagens recebidas são deduplicadas por `provider_message_id` e espelhadas em uma sala interna `WhatsApp · contato`.

O Embedded Signup oficial usa `POST /admin/integrations/whatsapp/embedded/start` e callback `GET /admin/integrations/whatsapp/embedded/callback`; o `state` é persistido como hash em `whatsapp_embedded_signup_sessions`.

As regras ficam em `whatsapp_automation_rules`. A engine aceita palavra-chave, encaminhamento humano, resposta fixa, consulta segura de faturas e consulta segura de pedidos. Faturas vêm de `receivables.client_id`; pedidos vêm de `orders.client_id` quando existir ou de `orders → opportunities.client_id` no schema legado. O limite de resposta é 5 linhas.

QR/short links oficiais ficam em `whatsapp_qr_codes` e são criados por `MetaWhatsAppClient.create_qr_code()`. Não existe conexão de WhatsApp Web por QR como dispositivo de produção neste módulo.

## Perfis de acesso configuráveis

| Arquivo | Responsabilidade |
|---|---|
| `app/features/access_control/repository.py` | schema, seeds de perfis/permissões, matriz e checagem `user_has_permission()` |
| `app/features/access_control/routes.py` | tela admin de perfis, matriz de permissões e atribuição de perfis a usuários |
| `app/templates/access_profiles.html` | criação de perfis e edição da matriz de permissões especiais |
| `app/templates/settings.html` | exibe e salva perfis configuráveis por usuário |
| `tests/features/test_access_control_repository.py` | contratos do repositório de acesso |
| `tests/web/test_access_control.py` | contratos HTTP de perfis e atribuição |

O modelo novo usa `access_profiles`, `access_permissions`, `access_profile_permissions` e `user_access_profiles`. O papel legado `admin` permanece como fallback seguro para não bloquear administração durante a migração.

## RH, comissões, benefícios e folha

| Arquivo | Responsabilidade |
|---|---|
| `app/features/hr/repository.py` | schema de colaboradores, vínculo com vendedores, criação/edição/exclusão de regras, folha, histórico, descontos/encargos e resumos |
| `app/features/hr/routes.py` | rotas de colaboradores, criação de usuário, editar/apagar registros, regras, folha e documentos imprimíveis |
| `app/templates/hr_employees.html` | cadastro/edição/exclusão de colaboradores, marcação de vendedor/representante e vínculo com usuário |
| `app/templates/hr_rules.html` | criação/edição/exclusão de regras de comissão, benefícios, descontos e encargos |
| `app/templates/hr_payroll.html` | geração, reabertura, exclusão, revisão, aprovação, pagamento e atalhos de impressão |
| `app/templates/hr_payroll_print.html` | folha de pagamento CLT imprimível, com proventos, descontos, encargos e líquido |
| `app/templates/hr_payment_statement.html` | demonstrativo de representantes/PJ/comissionados, com base de cálculo, comissão, benefício e valor a pagar |
| `app/static/css/hr-documents.css` | estilos de impressão dos documentos de RH |
| `tests/features/test_hr_repository.py` | cálculo de salário, benefício, comissão, descontos, encargos e vínculo vendedor |
| `tests/web/test_hr_module.py` | permissões, rotas, criação de usuário e documentos do módulo RH |

As permissões usadas pelo RH são `hr.view`, `hr.manage`, `hr.payroll.view`, `hr.payroll.process`, `hr.payroll.approve` e `hr.payroll.pay`. `hr.manage` controla edição/exclusão de colaboradores e regras; `hr.payroll.process` controla geração, reabertura e exclusão de competências de folha. A geração de folha cria itens rastreáveis e o pagamento grava histórico.

Quando um colaborador é marcado como vendedor/representante, `HRRepository.create_employee()` sincroniza o registro na tabela `sellers` e grava `hr_employees.seller_id`. Ao criar o usuário a partir do colaborador, o mesmo `seller_id` é aplicado em `users.seller_id`. Essa é a regra padrão: não duplicar pessoa em RH e Cadastros; o colaborador é o cadastro mestre, e o vendedor é a projeção comercial necessária para pedidos, comissões e relatórios.

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
