# Integração WhatsApp Business Cloud API

## Objetivo

Integrar o número atual do WhatsApp Business da empresa ao SIST-iONM usando a API oficial da Meta, permitindo atendimento híbrido: triagem automática, consulta segura aos dados internos e encaminhamento para setores/usuários dentro do chat da plataforma.

## Escopo desta primeira entrega

- Usar WhatsApp Business Platform / Cloud API oficial da Meta.
- Receber mensagens por webhook público HTTPS.
- Validar o webhook de verificação da Meta.
- Validar assinatura de eventos recebidos antes de processar mensagens.
- Identificar contato pelo telefone WhatsApp.
- Se for primeiro contato, perguntar nome e origem/cidade/empresa.
- Criar ou atualizar um contato externo vinculado ao cliente quando possível.
- Criar conversa espelhada no chat interno do SIST-iONM.
- Criar setores internos configuráveis para triagem inicial:
  - Comercial;
  - Financeiro;
  - Pedidos;
  - Suporte.
- Permitir que um atendente responda pelo SIST-iONM e a mensagem seja enviada ao WhatsApp.
- Permitir respostas automáticas básicas para consultas de cliente:
  - faturas/contas a receber;
  - pedidos;
  - compras/status de compra quando houver vínculo seguro;
  - encaminhamento humano quando a consulta não for reconhecida.

## Fora do escopo inicial

- Automação por WhatsApp Web, QR Code ou bibliotecas não oficiais.
- IA generativa respondendo sozinha sem regras e sem revisão.
- Campanhas ativas de marketing.
- Envio de templates fora da janela de atendimento, exceto preparação estrutural.
- Múltiplos números simultâneos.
- Call center com filas avançadas, SLA e relatórios completos.

## Referências oficiais

- Meta WhatsApp Business Platform: `https://developers.facebook.com/documentation/business-messaging/whatsapp/about-the-platform`
- Cloud API Get Started: `https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started`
- Webhooks: `https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview/`
- Messages API: `https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages`
- Pricing: `https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing`

## Pré-requisitos operacionais

O usuário deve configurar no painel da Meta:

- Meta App com WhatsApp habilitado.
- WhatsApp Business Account associado ao número atual.
- `phone_number_id`.
- `whatsapp_business_account_id`.
- token de acesso permanente ou token de sistema com permissões necessárias.
- `app_secret` para validação de assinatura.
- `verify_token` criado pela empresa para validação do webhook.
- URL pública HTTPS apontando para o servidor Ubuntu/local publicado por túnel ou domínio.

Nenhum segredo deve ser commitado. Todos os valores sensíveis devem ficar em `.env` ou no mecanismo de secrets do servidor.

## Configuração esperada

Variáveis de ambiente:

```text
WHATSAPP_ENABLED=false
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_WABA_ID=
WHATSAPP_APP_SECRET=
WHATSAPP_API_VERSION=v23.0
WHATSAPP_WEBHOOK_PATH=/integrations/whatsapp/webhook
```

Em desenvolvimento, `WHATSAPP_ENABLED=false` mantém as rotas presentes, mas impede envio real para a Meta. O webhook pode ser testado com payloads assinados em testes automatizados.

## Arquitetura

Criar um domínio `app/features/whatsapp/` isolado do monólito principal, mantendo o `app/main.py` apenas como ponto de montagem das rotas enquanto a extração completa por domínio ainda não foi concluída.

```text
app/features/whatsapp/
  __init__.py
  config.py          leitura segura de variáveis de ambiente
  security.py        validação do verify token e X-Hub-Signature-256
  client.py          envio de mensagens pela Cloud API
  repository.py      persistência de contatos, conversas, mensagens e setores
  service.py         triagem, estado da conversa e consulta ao banco
  routes.py          webhook GET/POST e endpoints internos de atendimento
  schemas.py         normalização de payloads recebidos
```

## Fluxo de entrada

1. Meta chama `GET /integrations/whatsapp/webhook` com parâmetros de verificação.
2. Sistema compara `hub.verify_token` com `WHATSAPP_VERIFY_TOKEN`.
3. Se válido, responde o `hub.challenge`.
4. Meta chama `POST /integrations/whatsapp/webhook` com evento de mensagem.
5. Sistema valida `X-Hub-Signature-256` usando `WHATSAPP_APP_SECRET`.
6. Sistema normaliza o payload recebido e ignora eventos duplicados pelo `message_id`.
7. Sistema procura contato por telefone.
8. Se não existir ou estiver incompleto, entra no fluxo de triagem.
9. Se existir e a intenção for reconhecida, consulta dados internos permitidos.
10. Se precisar de humano, cria/atualiza conversa interna e notifica setor/responsável.

## Fluxo de primeiro contato

Estado inicial:

```text
unknown_contact
```

Mensagens:

1. “Olá! Sou o assistente da SIST-iONM. Para começar, qual é o seu nome?”
2. Após capturar nome: “Obrigado, {nome}. Você fala de qual empresa/cidade?”
3. Após capturar origem: “Como posso te ajudar? 1 Comercial, 2 Financeiro, 3 Pedidos, 4 Suporte.”

O sistema deve salvar progresso em `whatsapp_triage_states` para continuar a conversa mesmo se a pessoa responder alguns minutos depois.

## Setores

Tabela de setores:

```text
whatsapp_departments
```

Campos mínimos:

- `id`;
- `name`;
- `description`;
- `is_active`;
- `default_user_id`;
- `created_at`;
- `updated_at`.

O setor selecionado cria uma atribuição em `whatsapp_assignments`. Se não houver responsável padrão, a conversa fica visível para administradores.

## Consultas automáticas

As consultas automáticas devem ser conservadoras. O sistema só responde dados específicos quando o telefone estiver vinculado a um cliente ou quando houver confirmação suficiente por documento/e-mail em etapa futura.

Consultas iniciais:

- “faturas”, “boleto”, “contas”, “financeiro”: retorna resumo de contas a receber em aberto do cliente vinculado.
- “pedido”, “pedidos”, “compra”: retorna últimos pedidos do cliente vinculado.
- “atendente”, “humano”, “suporte”: encaminha para setor.

Se não houver vínculo seguro:

```text
Encontrei sua solicitação, mas preciso confirmar seu cadastro antes de mostrar informações financeiras ou pedidos. Vou encaminhar para um atendente.
```

## Modelo de dados

```text
whatsapp_contacts
  id
  phone_e164
  display_name
  profile_name
  origin
  client_id
  first_seen_at
  last_seen_at
  created_at
  updated_at

whatsapp_conversations
  id
  contact_id
  chat_room_id
  department_id
  assigned_user_id
  status
  last_message_at
  created_at
  updated_at

whatsapp_messages
  id
  conversation_id
  provider_message_id
  direction
  sender_label
  content
  message_type
  media_path
  raw_payload_json
  status
  created_at

whatsapp_triage_states
  contact_id
  state
  context_json
  updated_at

whatsapp_departments
  id
  name
  description
  is_active
  default_user_id
  created_at
  updated_at

whatsapp_assignments
  id
  conversation_id
  department_id
  user_id
  assigned_at
  closed_at
```

## Integração com chat interno

Cada conversa WhatsApp ativa deve possuir uma sala interna vinculada em `chat_rooms`.

Nome sugerido da sala:

```text
WhatsApp · {nome ou telefone}
```

Mensagens recebidas do WhatsApp aparecem no chat como mensagens de origem externa, com destaque visual discreto. Respostas de usuários internos enviadas nessa sala podem ser encaminhadas para o WhatsApp quando a sala estiver vinculada a `whatsapp_conversations`.

Para evitar envio acidental, a primeira versão deve usar um botão explícito:

```text
Enviar também no WhatsApp
```

Depois de validado, pode virar comportamento padrão por sala.

## Segurança

- Validar assinatura `X-Hub-Signature-256` em todos os POSTs do webhook.
- Rejeitar payloads acima de limite definido.
- Persistir payload bruto somente quando necessário para auditoria e sem expor em tela comum.
- Não logar token, app secret, número completo com dados financeiros ou payload sensível.
- Nunca responder dados financeiros se o contato não estiver vinculado com segurança a um cliente.
- Usar queries parametrizadas.
- Aplicar rate limit por telefone e por IP no webhook quando houver camada Redis/Nginx disponível.
- Anexos e mídia do WhatsApp devem seguir a mesma regra de segurança dos anexos do chat: extensão permitida, limite de tamanho e nome físico aleatório.

## Escalabilidade

O webhook deve responder rápido. Operações mais lentas, como download de mídia, consultas complexas ou envio de múltiplas respostas, devem ser preparadas para fila assíncrona.

Na primeira versão local, o processamento pode ser síncrono com limites curtos. Para produção com volume, migrar para:

- Redis ou fila equivalente para jobs de envio/consulta;
- controle de idempotência por `provider_message_id`;
- backoff em falhas da API da Meta;
- dead-letter para mensagens que falharam após múltiplas tentativas.

## Tratamento de erros

- Assinatura inválida: `403`.
- Verify token inválido: `403`.
- Evento duplicado: responder `200` sem reprocessar.
- Meta API indisponível: registrar falha, marcar mensagem como `failed` e permitir reenvio manual.
- Contato sem vínculo seguro: encaminhar humano em vez de expor dados.
- Setor inexistente/inativo: encaminhar para administradores.

## Testes esperados

- Verificação GET do webhook com token válido e inválido.
- POST rejeita assinatura inválida.
- POST aceita payload assinado e cria contato/conversa/mensagem.
- Primeiro contato avança pelos estados nome → origem → setor.
- Mensagem duplicada não cria registro duplicado.
- Consulta financeira sem `client_id` não expõe valores.
- Consulta financeira com `client_id` retorna apenas dados daquele cliente.
- Resposta interna gera chamada para cliente Meta fake nos testes.
- Configuração `WHATSAPP_ENABLED=false` bloqueia envio real.

## Plano de entrega recomendado

1. Fundação segura do webhook e configuração por `.env`.
2. Persistência de contatos/conversas/mensagens.
3. Triagem de primeiro contato.
4. Espelhamento no chat interno.
5. Envio manual de resposta para WhatsApp.
6. Consultas automáticas conservadoras.
7. Tela administrativa de setores e atribuições.
8. Documentação de instalação Ubuntu/Nginx/HTTPS/Meta App.

## Critério de aceite

A entrega é considerada pronta quando:

- O webhook oficial da Meta valida a URL pública.
- Uma mensagem enviada ao número atual aparece dentro do SIST-iONM.
- Um primeiro contato recebe perguntas de nome e origem.
- A conversa pode ser encaminhada para setor.
- Um atendente consegue responder pelo sistema e a resposta chega ao WhatsApp.
- Consultas automáticas não vazam dados quando o telefone não está vinculado.
- Testes automatizados cobrem webhook, segurança, triagem e envio.
