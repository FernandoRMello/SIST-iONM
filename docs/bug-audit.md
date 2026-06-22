# Auditoria de bugs, segurança e acessibilidade

Data da auditoria: 18/06/2026.

Escopo: 18 templates Jinja, shell compartilhado, JavaScript local, rotas de renderização, paginação, consultas críticas e banco SQLite-fonte. As correções abaixo possuem regressão automatizada; itens apenas suspeitos não são declarados como corrigidos.

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

## Verificações transversais

- 18 templates sem handlers JavaScript inline, assets remotos, emojis de navegação ou senha preenchida.
- JavaScript sem `eval`, `document.write`, `insertAdjacentHTML` ou `.innerHTML`.
- Labels, estados não dependentes apenas de cor, foco visível, `aria-live` no chat e navegação responsiva.
- Banco-fonte preservado: SHA-256 `64F39752F02FA53580D87E6EF0E61A3441BE7FC0C31EB6DD5117A1F7A9E4DE18`.

## Dívidas conhecidas, não declaradas como corrigidas

- Migração para PostgreSQL, CSRF por token, Argon2 e rate limit do login pertencem ao próximo workstream de backend/identidade.
- O fallback local da sessão existe para desenvolvimento; em servidor compartilhado é obrigatório definir `SIST_IONM_SESSION_SECRET` com pelo menos 32 caracteres.
- Permanecem três avisos de depreciação de framework: integração `TestClient/httpx` e uso de `on_event`; serão tratados na modularização do ciclo de vida.

## Comandos de verificação

```powershell
python -m pytest tests\web tests\performance tests\characterization -q
python -m ruff check tests\web tests\performance tests\characterization
node --check app\static\chat_realtime.js
git diff --check
```
