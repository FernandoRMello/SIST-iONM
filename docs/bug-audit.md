# Auditoria de bugs, segurança e acessibilidade

Data da auditoria: 22/06/2026.

Escopo: 19 templates Jinja, shell compartilhado, JavaScript local, rotas de renderização, paginação, consultas críticas, integração WhatsApp e banco SQLite-fonte. As correções abaixo possuem regressão automatizada; itens apenas suspeitos não são declarados como corrigidos.

## Bugs corrigidos

| ID | Severidade | Superfície | Reprodução e causa raiz | Correção | Regressão |
|---|---|---|---|---|---|
| BUG-001 | Alta | Chat | Mensagens e contatos eram montados com `innerHTML`, `insertAdjacentHTML` e handlers inline. Conteúdo de usuário atravessava uma API de HTML dinâmico, ampliando risco de XSS. | Construção exclusiva por DOM seguro e `textContent`; eventos ligados por `addEventListener`. | `tests/web/test_portal_pages.py::test_chat_script_uses_safe_dom_and_bounded_reconnection` |
| BUG-002 | Média | WebSocket do chat | O chat completo apenas atualizava estado; não ligava o formulário nem tratava abertura, erro, fechamento e reconexão. | Ciclo completo de conexão, status `aria-live`, reconexão exponencial limitada a 30 s e envio pelo formulário. | `tests/web/test_portal_pages.py::test_chat_script_uses_safe_dom_and_bounded_reconnection` |
| BUG-003 | Média | Chat | Após o redesenho inicial, anexos e contexto visual da conversa deixavam de aparecer. | Anexo seguro em nova aba, contato ativo e cabeçalho da conversa restaurados. | `tests/web/test_portal_pages.py::test_chat_script_preserves_conversation_context_and_attachments` |
| BUG-004 | Baixa | Layout do chat | A janela declarava linhas de grid sem `display: grid`, deixando a organização dependente de CSS legado. | Grid explicitamente ativado no módulo `portal.css`. | `tests/web/test_portal_pages.py::test_chat_window_uses_the_declared_grid_layout` |
| BUG-005 | Alta | Configurações SMTP | A senha SMTP armazenada era enviada ao template e renderizada no atributo `value`. | Consulta de visualização exclui `smtp_password`; o campo nunca recebe valor. | `tests/web/test_administration_pages.py::test_settings_never_render_stored_smtp_password` |
| BUG-006 | Média | Configurações SMTP | Salvar o formulário com senha vazia apagava o segredo existente. | Valor vazio preserva a senha persistida; somente entrada não vazia substitui o segredo. | `tests/web/test_administration_pages.py::test_blank_smtp_password_preserves_existing_secret` |
| BUG-007 | Média | Criação de usuário | O formulário coletava e-mail, mas o backend o descartava e não criava `user_profiles`. | E-mail persistido em `users` e perfil inicial criado no mesmo fluxo. | `tests/web/test_administration_pages.py::test_creating_user_persists_email_and_profile` |
| BUG-008 | Alta (desempenho) | Dashboard e pipeline | Cada oportunidade executava `opp_summary()`, gerando duas consultas adicionais por registro. Com 21 registros, as páginas chegaram a 47/48 consultas. | Agregações SQL em lote, KPI agregado e lista limitada/paginada. | `tests/performance/test_query_budget.py::test_page_query_count_does_not_grow_with_rows` |
| BUG-009 | Média (desempenho) | Listagens | CRUD, chat, finanças e relatórios carregavam conjuntos completos sem limite. | Paginação normalizada, padrão 25 e máximo 100; chat/API retornam página limitada. | `tests/performance/test_pagination.py` |
| BUG-010 | Média (desempenho) | Assets | CSS/JS estáticos não tinham versão nem política de cache segura para atualização. | Cache-buster em todos os assets e `Cache-Control: public, max-age=31536000, immutable` somente quando versionados. | `tests/performance/test_pagination.py::test_versioned_assets_are_cached_but_html_is_private` |
| BUG-011 | Média | Respostas web | Não havia CSP, proteção contra framing, `nosniff`, política de referenciador ou restrição de APIs do navegador. | Headers defensivos aplicados pelo middleware; HTML autenticado e público usa `no-store`. | `tests/web/test_accessibility_contract.py::test_html_responses_include_baseline_security_headers` |
| BUG-012 | Média | Design system | `style.css` legado ainda controlava chat lateral e ocultação de valores, criando duas fontes visuais e risco de conflito. | Regras migradas para `layout.css`, `components.css` e `utilities.css`; arquivo e referência removidos. | `tests/web/test_accessibility_contract.py::test_shared_shell_uses_no_legacy_stylesheet_or_navigation_emoji` |
| BUG-013 | Alta (estabilidade) | SQLite | `with sqlite3.Connection` confirmava/abortava transações, mas não fechava o handle; a suíte com cobertura expôs centenas de `ResourceWarning`. | `db()` agora é um context manager explícito e fecha a conexão em `finally`. | `tests/performance/test_connection_lifecycle.py` |
| BUG-014 | Alta (usabilidade) | Chat flutuante | O contêiner da conversa mantinha altura mínima pelo conteúdo; mensagens empurravam o formulário para fora do painel recortado. | A linha de mensagens pode encolher e rolar, mantendo o compositor sempre dentro do painel. | `tests/web/test_accessibility_contract.py::test_floating_chat_keeps_the_message_composer_inside_the_panel` |
| BUG-015 | Média | Notificações do chat | O sino acumulava notificações por sala, enquanto os contatos eram identificados por usuário e seus badges não recebiam chave. | Notificação privada é associada a `user:<remetente>` e zerada ao abrir esse contato. | `tests/web/test_portal_pages.py::test_chat_notifications_are_assigned_to_the_sender_contact` |
| BUG-016 | Alta (segurança) | Anexos do chat | O endpoint legado aceitava qualquer extensão, sem limite, preservava o nome fornecido e não publicava a mensagem em tempo real. | Lista segura de formatos, máximo de 10 MiB, nome físico aleatório, autorização antes do upload e broadcast/notificação unificados. | `tests/web/test_chat_delivery.py` |
| BUG-017 | Média (desempenho/UX) | Navegação | Cada clique do menu recriava todo o shell e interrompia o estado vivo do chat. | Navegação progressiva troca somente o conteúdo central, sincroniza histórico/assets e usa recarga completa como fallback. | `tests/js/shell-navigation.test.js` + `tests/web/test_shell_contract.py` |
| BUG-018 | Média (usabilidade) | Imagens no chat | Anexos de imagem apareciam apenas como link genérico. | PNG, JPG/JPEG, WebP e GIF recebem miniatura segura e clicável dentro da mensagem. | `tests/web/test_chat_delivery.py::test_full_chat_renders_image_thumbnail_but_keeps_documents_as_links` |
| BUG-019 | Alta (comunicação) | Notificações do chat | A última sala selecionada era tratada como visível mesmo com painel fechado/minimizado, descartando o badge. | Visibilidade real, leitura persistente e restauração de contadores pelo contexto. | `tests/web/test_chat_notifications.py` + `tests/js/chat-notifications.test.js` |
| BUG-020 | Média (integridade) | Feed | Like legado era GET e não havia reação negativa nem exclusividade formal. | POST com tabela única, restrição por usuário/post e alternância like/dislike/remover. | `tests/web/test_feed_reactions.py` |
| BUG-021 | Alta (segurança) | Avatar | Upload de perfil confiava na extensão, não limitava tamanho e preservava metadados/conteúdo original. | Pillow valida conteúdo, limita pixels/tamanho, corrige EXIF e regrava JPEG 512 × 512 com nome aleatório. | `tests/features/test_profile_avatar_service.py` + `tests/web/test_profile_avatar.py` |
| BUG-022 | Alta (segurança) | WhatsApp Business | Integrações externas poderiam expor tokens, aceitar webhooks falsos ou duplicar mensagens se fossem acopladas direto ao chat. | Wizard admin-only, segredos mascarados/criptografados, verify token hasheado, validação `X-Hub-Signature-256` e deduplicação por `provider_message_id`. | `tests/features/test_whatsapp_security.py` + `tests/features/test_whatsapp_service.py` + `tests/web/test_whatsapp_integration.py` |
| BUG-023 | Alta (privacidade) | WhatsApp automações | Respostas automáticas de fatura/pedido poderiam vazar dados se um telefone não confirmado pedisse informações financeiras. | Regras automáticas só consultam faturas/pedidos quando `whatsapp_contacts.client_id` está vinculado; sem vínculo, retornam confirmação cadastral e encaminhamento humano. | `tests/features/test_whatsapp_service.py::test_finance_keyword_without_client_returns_safe_handoff` + testes de isolamento por cliente |
| BUG-024 | Média (operação) | WhatsApp Embedded Signup/QR | A configuração manual não cobria Embedded Signup oficial nem QR/short link de início de conversa. | Botão “Conectar com Meta”, callback com `state` hasheado e geração de QR/short link oficial; WhatsApp Web por QR continua fora do core produtivo. | `tests/web/test_whatsapp_integration.py` |
| BUG-025 | Alta (segurança) | Perfis e RH | Perfis rígidos no código impediam liberar telas/ações específicas sem alterar backend e expunham risco de folha sem permissão granular. | Modelo `access_profiles` + permissões especiais; RH usa `hr.*`/`users.manage` e mantém fallback seguro para `admin`. | `tests/features/test_access_control_repository.py` + `tests/web/test_access_control.py` + `tests/web/test_hr_module.py` |
| BUG-026 | Média (integridade) | RH/Vendedores | O colaborador vendedor podia ser cadastrado separadamente em RH e em Cadastros, quebrando vínculo de usuário, comissão, benefício e relatórios. | Colaborador marcado como vendedor sincroniza `sellers`, grava `hr_employees.seller_id` e propaga o mesmo vínculo para `users.seller_id` ao criar usuário. | `tests/features/test_hr_repository.py::test_seller_employee_is_synced_with_sellers_catalog` + `tests/web/test_hr_module.py::test_seller_employee_creates_seller_and_user_link` |
| BUG-027 | Média (operação) | Folha de pagamento | A folha não separava documentos CLT de demonstrativos de representantes e não exibia descontos, encargos, base de cálculo e líquido de forma imprimível. | Regras de desconto/encargo, resumo líquido por colaborador, folha CLT imprimível e demonstrativo de comissionados com base, comissão, benefício e valor a pagar. | `tests/features/test_hr_repository.py::test_clt_payroll_generates_discounts_charges_and_net_summary` + `tests/web/test_hr_module.py::test_payroll_print_and_commission_statement_pages` |
| BUG-028 | Alta (integridade) | Folha de pagamento | Comissões e benefícios podiam entrar zerados quando a base vinha do schema real `orders → opportunities → opportunity_items`, porque o cálculo tentava ler colunas resumidas inexistentes em `orders`. Benefício sobre comissão também era calculado antes da comissão. | Cálculo de folha agora usa fallback por itens de oportunidade, respeita escopo individual por `seller_id`, calcula comissão antes dos benefícios e permite benefício percentual sobre comissão. | `tests/features/test_hr_repository.py::test_payroll_uses_legacy_orders_items_for_seller_commission_and_benefit` |
| BUG-029 | Média (gestão) | Dashboard/BI Gerencial | “A pagar” somava apenas status `Aberto` e o BI não mostrava detalhamento dos compromissos, deixando vencidos/agendados fora da leitura executiva. | Helper único para compromissos abertos/vencidos/inadimplentes/agendados; dashboard e BI usam a mesma soma e o BI exibe tabela “Compromissos a pagar”. | `tests/web/test_executive_pages.py::test_dashboard_and_bi_include_overdue_payables` |

## Verificações transversais

- 25 templates sem handlers JavaScript inline, assets remotos, emojis de navegação ou senha preenchida.
- JavaScript sem `eval`, `document.write`, `insertAdjacentHTML` ou `.innerHTML`.
- Labels, estados não dependentes apenas de cor, foco visível, `aria-live` no chat e navegação responsiva.
- Banco-fonte não é usado pelos testes; a referência corrente deve ser conferida em `docs/development.md`.

## Dívidas conhecidas, não declaradas como corrigidas

- Migração para PostgreSQL, CSRF por token, Argon2 e rate limit do login pertencem ao próximo workstream de backend/identidade.
- O fallback local da sessão existe para desenvolvimento; em servidor compartilhado é obrigatório definir `SIST_IONM_SESSION_SECRET` com pelo menos 32 caracteres.
- Permanecem três avisos de depreciação de framework: integração `TestClient/httpx` e uso de `on_event`; serão tratados na modularização do ciclo de vida.

## Comandos de verificação

```powershell
python -m pytest tests\web tests\performance tests\characterization tests\features -q
python -m ruff check app tests
node --check app\static\chat_realtime.js
node --test tests\js\shell-navigation.test.js
node --test tests\js\chat-notifications.test.js
node --test tests\js\profile-avatar-editor.test.js
git diff --check
```
