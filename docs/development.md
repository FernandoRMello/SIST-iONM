# Desenvolvimento e execução local

## Estado desta entrega

O frontend das 18 telas está modularizado e testado. A aplicação executável ainda usa o monólito `app/main.py` e SQLite em `data/overpriceon_web.db`. PostgreSQL e extração backend por domínio são a próxima etapa; não apontar este build para produção compartilhada como se o cutover já estivesse concluído.

## Requisitos

- Linux/Ubuntu ou Windows;
- Python 3.13;
- Git;
- navegador moderno.

## Instalação

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
cp .env.example .env
```

Defina `SIST_IONM_SESSION_SECRET` com pelo menos 32 caracteres aleatórios. Em ambiente de produção, use HTTPS e `SIST_IONM_ENVIRONMENT=production` para cookie `Secure`.

## Execução

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acesse `http://IP_DO_SERVIDOR:8000/`. Para uso apenas na própria máquina, prefira `--host 127.0.0.1`.

## Verificação

```bash
python -m pytest tests/web tests/performance tests/characterization tests/features -q
python -m ruff check app tests
python -m mypy app/core scripts
```

O comando de mypy é reservado ao backend modular quando `app/core` e `scripts` estiverem presentes. No estado atual, o contrato principal é pytest + Ruff dos testes + sintaxe dos JavaScripts.

`app/main.py` possui exceções Ruff transitórias apenas para one-liners legados (`E701`/`E702`) e assinaturas FastAPI com `File(...)` (`B008`). Não copie esse padrão para módulos novos; as exceções serão removidas com a extração por domínio.

```bash
node --check app/static/chat_realtime.js
node --test tests/js/shell-navigation.test.js
node --test tests/js/chat-notifications.test.js
node --test tests/js/profile-avatar-editor.test.js
git diff --check
```

## Navegação pelo menu e chat persistente

Os links do menu lateral atualizam apenas o conteúdo central. Para validar manualmente:

1. Abra o chat e mantenha uma conversa selecionada.
2. Navegue por Dashboard, Clientes e Pipeline usando somente o menu lateral.
3. Confirme que o painel e os badges do chat permanecem no mesmo estado.
4. Use Voltar e Avançar e confira título, breadcrumb e item ativo.
5. Envie uma imagem e um PDF; a imagem deve aparecer como miniatura e o PDF como link.

PNG, JPG/JPEG, GIF e WebP são imagens inline. Todos os anexos mantêm o limite de 10 MiB. Se a navegação dinâmica falhar, o sistema recarrega a página normalmente.

## Verificação de colaboração

1. Abra uma conversa privada, minimize o painel e envie mensagem pelo outro usuário: sino e avatar do remetente devem aumentar.
2. Abra a conversa: o badge deve zerar e permanecer lido após atualizar a página.
3. No Feed, alterne 👍 para 👎 e repita 👎: os estados esperados são dislike e depois sem reação.
4. Confirme foto ou inicial em posts e comentários.
5. No Perfil, selecione uma imagem, arraste, aplique zoom e salve; o arquivo final deve ser JPEG 512 × 512.

O WebSocket em memória exige um único worker. Para múltiplos workers, planeje pub/sub compartilhado antes do deploy.

## WhatsApp Business Cloud API

A integração fica em **Administração → WhatsApp Business** e exige usuário `admin`.

Passos mínimos:

1. Configure uma URL pública HTTPS para o servidor Ubuntu/local.
2. No painel da Meta, habilite WhatsApp Business Platform para o número atual.
3. No wizard, informe `phone_number_id`, `whatsapp_business_account_id`, `access_token`, `app_secret` e a URL pública do webhook.
4. Gere ou informe o `verify_token` e cadastre-o na Meta junto com a callback URL `/integrations/whatsapp/webhook`.
5. Use “Testar conexão” somente com um número permitido pela janela/template da Meta.
6. Ative a integração após a Meta validar o webhook.

Defina `WHATSAPP_SECRET_KEY` no `.env` com pelo menos 32 caracteres aleatórios. Essa chave protege os segredos salvos no banco; se ela for perdida, será necessário reenviar token e app secret pelo wizard. Não copie tokens reais para commits, prints ou logs.

O webhook público aceita:

- `GET /integrations/whatsapp/webhook` para verificação da Meta;
- `POST /integrations/whatsapp/webhook` para eventos assinados com `X-Hub-Signature-256`.

Primeiro contato recebe triagem conservadora e a conversa aparece no chat interno como `WhatsApp · nome/telefone`. Dados financeiros ou pedidos não devem ser enviados automaticamente sem vínculo seguro entre telefone e cliente.

## Banco de desenvolvimento

- Nunca teste escrita diretamente em `data/overpriceon_web.db`.
- Os fixtures copiam o banco para diretório temporário.
- SHA-256 do baseline inicial: `64F39752F02FA53580D87E6EF0E61A3441BE7FC0C31EB6DD5117A1F7A9E4DE18`.
- SHA-256 observado antes e depois da entrega de importação, em 22/06/2026: `7A2503EC5457F08B2BB569C97A42FAF813C44E5870218672A7683D1AA5BB3DCF`.
- O hash do banco em uso muda quando o servidor local grava dados. Capture e compare o hash dentro da janela da operação que estiver auditando; não restaure um hash histórico sobre dados ativos.
- Antes de migração ou importação, faça cópia offline e valide contagens/valores.

## Importação por Excel

Nas telas **Clientes** e **Fornecedores**, baixe primeiro o modelo oficial e envie somente arquivos `.xlsx`. Nome e CPF/CNPJ são obrigatórios; o documento identifica se o registro deve ser criado ou atualizado.

- limite por arquivo: 5 MiB;
- limite por planilha: 5.000 linhas de dados;
- linhas vazias são ignoradas;
- duplicidades na mesma planilha são reportadas e ignoradas;
- clientes podem ser importados por usuário autenticado;
- fornecedores exigem perfil administrador.

A importação ocorre em uma única transação. Testes automatizados usam cópias temporárias do banco e nunca devem apontar para o arquivo de uso corrente.

## Fluxo recomendado ao Dev Junior

1. Leia `docs/file-map.md` e `docs/design-system.md`.
2. Crie teste de regressão para a mudança.
3. Altere somente o módulo visual e a rota em escopo.
4. Não renomeie campos de formulário sem alterar e testar o backend.
5. Não adicione CDN, handler inline ou HTML dinâmico para conteúdo do usuário.
6. Atualize `ASSET_VERSION` quando modificar assets em uma release.
7. Rode o gate e registre decisões em documentação.

Consulte também `docs/bug-audit.md` e `docs/performance.md`.
As versões verificadas estão em `docs/versions.md`.
