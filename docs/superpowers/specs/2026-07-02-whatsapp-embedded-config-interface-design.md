# Configuração do Embedded Signup dentro do aplicativo

Data: 2 de julho de 2026  
Status: aprovado para planejamento

## Objetivo

Permitir que um administrador configure o Embedded Signup da Meta diretamente no wizard `Administração → WhatsApp Business`, sem depender de edição manual do arquivo `.env`.

## Interface

O wizard terá uma seção `Conexão Embedded Signup` com:

- Meta App ID;
- Embedded Signup Config ID;
- Redirect URI;
- Meta Client Secret;
- botão `Salvar configuração`;
- indicador de configuração completa ou pendente.

O Client Secret será aceito somente para alteração. Depois de salvo, a interface mostrará apenas estado mascarado e nunca devolverá o valor em texto claro.

## Persistência e segurança

Os seguintes campos serão persistidos em `whatsapp_settings`:

- `embedded_app_id`;
- `embedded_config_id`;
- `embedded_redirect_uri`;
- `embedded_client_secret_encrypted`.

O Client Secret usará o novo `WhatsAppSecurityEngine` baseado em Fernet. A aplicação não registrará o segredo em logs, mensagens de erro, sessão ou HTML.

Em produção, `WHATSAPP_SECRET_KEY` continuará obrigatório para descriptografar credenciais.

## Precedência

A configuração salva na interface será o caminho normal.

Variáveis de ambiente equivalentes continuarão aceitas como override operacional:

1. valor definido no ambiente;
2. valor salvo pela interface;
3. valor ausente.

A interface indicará quando um valor efetivo está vindo do ambiente, sem exibir seu conteúdo sensível.

## Fluxo

1. Administrador salva os quatro campos.
2. O backend valida campos obrigatórios e formato absoluto HTTPS da Redirect URI.
3. O wizard apresenta o estado da configuração.
4. `Conectar com Meta` resolve os valores efetivos.
5. Se houver pendências, retorna ao wizard com mensagem específica.
6. Se estiver completo, cria sessão com `state` hasheado e redireciona à Meta.

Ambiente local poderá usar `http://127.0.0.1` para testes, mas produção exigirá HTTPS.

## Compatibilidade

- configurações existentes de phone number, WABA, access token, app secret e verify token serão preservadas;
- instalações com `.env` continuarão funcionando;
- o schema SQLite será atualizado de forma incremental;
- a futura migração PostgreSQL deverá reproduzir os novos campos via Alembic.

## Testes

- administrador visualiza e salva os campos;
- usuário não administrador recebe `403`;
- Client Secret não aparece no HTML;
- atualização sem novo segredo preserva o anterior;
- botão usa configuração da interface sem `.env`;
- `.env` substitui o valor salvo quando definido;
- configuração incompleta bloqueia o início;
- Redirect URI inválida é rejeitada;
- produção exige HTTPS;
- regressões existentes do wizard e webhook continuam aprovadas.

