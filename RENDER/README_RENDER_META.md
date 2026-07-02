# Pacote Render - Integração Meta / WhatsApp

Esta pasta contém uma cópia dos arquivos do SIST-iONM relacionados à integração com a Meta/WhatsApp Embedded Signup.

## Arquivos copiados

- `app/features/whatsapp/`
  - Rotas, repositório, serviço, cliente e camada DDD inicial do WhatsApp.
- `app/templates/whatsapp_settings.html`
  - Tela administrativa de configuração da integração.
- `app/main.py`
  - Aplicação FastAPI principal.
- `requirements.lock`
  - Dependências usadas no deploy.
- `.env.example`
  - Modelo geral de variáveis.
- `render-env.example`
  - Modelo específico para configurar o Render.

## Variáveis que devem ser configuradas no Render

Configure no painel:

`Render -> Service -> Environment`

```env
SIST_IONM_ENVIRONMENT=production
META_EMBEDDED_SIGNUP_APP_ID=28013144484936275
META_EMBEDDED_SIGNUP_CONFIG_ID=1542064997375425
META_EMBEDDED_SIGNUP_REDIRECT_URI=https://ionmtec.onrender.com/admin/integrations/whatsapp/embedded/callback
META_EMBEDDED_SIGNUP_CLIENT_SECRET=COLOQUE_AQUI_O_CLIENT_SECRET_DA_META
WHATSAPP_SECRET_KEY=COLOQUE_AQUI_UMA_CHAVE_FORTE_E_UNICA
```

Nunca suba `META_EMBEDDED_SIGNUP_CLIENT_SECRET` ou `WHATSAPP_SECRET_KEY` reais para o Git.

## Redirect URI

No painel da Meta, cadastre exatamente:

```text
https://ionmtec.onrender.com/admin/integrations/whatsapp/embedded/callback
```

O fluxo precisa começar e terminar no mesmo ambiente.

Correto:

```text
Inicia no Render -> Callback no Render
```

Evite:

```text
Inicia no localhost -> Callback no Render
```

Isso quebra o `state` de segurança do OAuth.

## Config ID atual

```text
1542064997375425
```

Esse valor deve ser o `Configuration ID` criado em:

```text
Meta Developers -> App -> Facebook Login for Business -> Configurations
```

