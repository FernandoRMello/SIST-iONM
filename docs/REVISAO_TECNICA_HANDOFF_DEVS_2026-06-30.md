# SIST-iONM — resumo técnico e handoff para revisão

Data da revisão: 30 de junho de 2026  
Versão declarada: 2.6.0  
Branch analisada: `master`  
Último commit funcional analisado: `d09c66b feat: add recurring fixed costs`

## 1. Objetivo deste documento

Este documento entrega à equipe de desenvolvimento:

- um resumo do sistema e do que foi implementado;
- a situação real de cada módulo;
- uma auditoria aprofundada da integração WhatsApp;
- riscos funcionais, de segurança, arquitetura e operação;
- uma sequência recomendada de revisão e evolução;
- critérios objetivos para considerar o sistema pronto para homologação e produção.

As classificações utilizadas são:

- **Entregue**: existe implementação e regressão automatizada;
- **Parcial**: existe estrutura funcional, mas falta fechar o fluxo produtivo;
- **Projetado**: há especificação ou interface, sem operação completa;
- **Não implementado**: não existe no código atual.

## 2. Resumo executivo

O SIST-iONM evoluiu de um arquivo monolítico para uma aplicação FastAPI com frontend Jinja modularizado e domínios novos em `app/features`. A interface, os principais cadastros, o financeiro, o chat, o RH, os perfis de acesso, o wizard do WhatsApp e as rotinas de custos estão cobertos por testes.

O sistema ainda não deve ser tratado como pronto para produção compartilhada pelos seguintes motivos:

1. o runtime principal continua usando SQLite e grande parte das regras permanece em `app/main.py`;
2. a configuração PostgreSQL testa e prepara uma conexão, mas não realiza o cutover do sistema;
3. a integração WhatsApp possui wizard, webhook e persistência, porém não fecha o envio automático nem o Embedded Signup;
4. o fluxo de WhatsApp Web por pareamento de dispositivo via QR não existe;
5. segredos, jobs externos, observabilidade, CSRF, rate limiting e deploy Ubuntu precisam de endurecimento;
6. o ambiente virtual local `.venv` está inválido no workspace analisado e deve ser recriado.

Prioridade recomendada: estabilizar WhatsApp oficial e infraestrutura antes de ampliar automações ou adicionar mais telas.

## 3. Arquitetura atual

### Backend

- Python 3.13;
- FastAPI;
- templates Jinja2;
- SQLite ativo em `data/overpriceon_web.db`;
- SQL parametrizado, predominantemente direto;
- módulos extraídos em `app/features`;
- aproximadamente 2.630 linhas ainda concentradas em `app/main.py`;
- repositório WhatsApp com aproximadamente 684 linhas.

### Frontend

- shell compartilhado com menu lateral e barra superior;
- navegação central parcial sem recarregar todo o shell;
- CSS separado por domínio;
- componentes e tokens visuais compartilhados;
- JavaScript local, sem framework SPA;
- layout responsivo e impressão para documentos de RH.

### Infraestrutura

- alvo documentado: Linux/Ubuntu;
- execução atual validada principalmente em Windows;
- PostgreSQL, SQLAlchemy e Alembic estão fixados nas dependências;
- a aplicação ainda não opera sobre PostgreSQL;
- não há containerização, pipeline CI/CD ou observabilidade de produção completos.

## 4. Entregas realizadas

### 4.1 Interface e navegação — entregue

- redesenho minimalista das telas;
- shell persistente com menu, topbar, usuário, notificações e chat;
- carregamento parcial do conteúdo central;
- cards, formulários, tabelas e botões padronizados;
- campos importantes convertidos de texto livre para listas;
- estados vazios, paginação e contratos de acessibilidade.

### 4.2 CRM e operação — entregue

- clientes;
- fornecedores;
- vendedores;
- produtos;
- oportunidades e R.O.;
- pedidos;
- compras;
- vínculo entre colaboradores, usuários e vendedores;
- importação de clientes e fornecedores por planilha, com modelo.

### 4.3 Chat interno — entregue com pontos de evolução

- chat geral e conversas individuais;
- atualização em tempo real por WebSocket;
- notificações por usuário;
- anexos;
- imagens exibidas dentro da mensagem;
- painel flutuante fixo;
- correções de altura e área de digitação;
- integração visual com o shell.

Melhorias ainda recomendadas:

- armazenamento externo para anexos;
- antivírus e varredura de conteúdo;
- thumbnails e otimização de imagens;
- retenção e expurgo;
- paginação/cursor para históricos longos;
- Redis pub/sub para múltiplas instâncias.

### 4.4 Feed e perfil — entregue

- avatar do autor;
- reações de gostei e não gostei;
- comentários;
- upload e ajuste da foto de perfil dentro da moldura.

### 4.5 Perfis e permissões — entregue como base

- perfis configuráveis;
- permissões por módulo e ação;
- associação usuário-perfil;
- permissões especiais para financeiro, RH e WhatsApp;
- telas administrativas.

Revisar:

- garantir que todas as rotas antigas em `app/main.py` consultem o serviço central de autorização;
- eliminar verificações baseadas somente em nomes de papel como `admin` ou `financeiro`;
- criar matriz automatizada de rota × permissão.

### 4.6 RH — entregue como primeira versão

- colaboradores;
- vínculo com usuário e vendedor;
- cargo, departamento, contrato e salário;
- regras de benefício, comissão, desconto e encargo;
- folha CLT;
- demonstrativo de comissionados;
- impressão;
- aprovação, pagamento e reabertura;
- editar e excluir colaboradores, regras e competências.

Revisar com especialista contábil:

- INSS, FGTS, IRRF, férias, 13º, afastamentos e rescisões;
- arredondamentos e vigência das tabelas legais;
- eSocial;
- separação rigorosa entre cálculo gerencial e folha legal;
- trilha de auditoria imutável.

### 4.7 Financeiro e BI — entregue com evolução necessária

- contas a receber;
- contas a pagar;
- inclusão da folha, benefícios, comissões, descontos e encargos no passivo;
- custos variáveis;
- custos fixos recorrentes;
- categorias administráveis;
- calendário de feriados;
- geração automática mensal;
- recomposição de competências quando o servidor ficou desligado;
- proteção contra duplicidade;
- Dashboard e BI Gerencial;
- impressão do BI.

Revisar:

- conciliação bancária;
- competência versus caixa;
- centros de custo hierárquicos;
- plano de contas;
- baixa parcial;
- estorno e auditoria;
- projeções separadas de obrigações efetivamente lançadas.

### 4.8 Administração do banco — parcial

- tela administrativa para PostgreSQL;
- salvar configuração;
- testar conexão;
- preparar tabela de controle;
- histórico de testes.

Ainda não entregue:

- migração completa do schema e dados;
- troca do runtime para PostgreSQL;
- Alembic como fonte única das migrações;
- backup e restore PostgreSQL;
- rollback de cutover;
- pool de conexões e health checks.

## 5. WhatsApp: situação atual

### 5.1 Decisão arquitetural vigente

O código atual usa como direção principal a **WhatsApp Business Platform/Cloud API oficial da Meta**.

O QR implementado é um QR/short link para o cliente iniciar uma conversa. Ele não pareia a plataforma como um dispositivo do WhatsApp Web.

Não existem no projeto:

- `whatsapp-web.js`;
- Baileys;
- Venom;
- sessão Chromium;
- armazenamento de sessão de WhatsApp Web;
- pareamento da aplicação como dispositivo adicional via QR.

Portanto, qualquer apresentação do sistema deve evitar a frase “WhatsApp Web integrado”. A descrição correta hoje é: **fundação de integração com a API oficial da Meta, ainda incompleta para produção**.

### 5.2 Componentes implementados — entregue como fundação

Arquivos:

- `app/features/whatsapp/client.py`;
- `app/features/whatsapp/repository.py`;
- `app/features/whatsapp/routes.py`;
- `app/features/whatsapp/security.py`;
- `app/features/whatsapp/service.py`;
- `app/templates/whatsapp_settings.html`.

Recursos existentes:

- wizard exclusivo para administradores;
- configuração manual de IDs e credenciais;
- segredo mascarado após salvamento;
- verify token armazenado por hash;
- validação `X-Hub-Signature-256`;
- deduplicação por `provider_message_id`;
- persistência de contatos, conversas e mensagens;
- espelhamento de mensagem recebida em sala do chat interno;
- triagem inicial;
- setores;
- regras por palavra-chave;
- consulta restrita de pedidos e faturas por cliente vinculado;
- início do Embedded Signup;
- geração de QR/short link oficial;
- teste de envio de texto.

### 5.3 Lacunas críticas encontradas

#### WA-001 — resposta automática não é enviada

Severidade: **crítica funcional**

`handle_inbound_message()` calcula `auto_reply`, mas a rota do webhook apenas retorna contadores. Não há chamada a `MetaWhatsAppClient.send_text()` para enviar a triagem ou a regra automática ao cliente.

Impacto:

- o webhook recebe a mensagem;
- o sistema calcula o texto;
- o cliente não recebe a resposta;
- testes atuais validam o cálculo, não o ciclo real.

Correção esperada:

- persistir um job de saída idempotente;
- responder HTTP 200 rapidamente à Meta;
- enviar em worker;
- salvar `provider_message_id` de saída;
- registrar tentativa, entrega, leitura e falha;
- aplicar retry com backoff e dead-letter queue.

#### WA-002 — Embedded Signup não conclui o onboarding

Severidade: **crítica funcional**

O callback:

- valida `state`;
- armazena `code`, `status` e `error`;
- marca a sessão como concluída.

Ele não:

- troca o código por token;
- obtém WABA e `phone_number_id`;
- registra o número;
- configura ou confirma webhook;
- salva os ativos retornados;
- trata expiração, cancelamento e reentrada;
- valida sucesso antes de marcar a sessão como concluída.

Correção esperada:

- implementar o fluxo oficial completo;
- manter sessão com expiração e uso único;
- armazenar estado detalhado;
- concluir configuração somente após validar os ativos;
- registrar erros sem segredos;
- oferecer “retomar configuração”.

#### WA-003 — “ativar” não controla o webhook

Severidade: **alta**

O webhook processa mensagens assinadas mesmo quando `whatsapp_settings.enabled` está como `Não`.

Correção:

- definir comportamento de desativação;
- quando desativado, confirmar recebimento sem processar automações;
- registrar métrica e motivo;
- manter verificação do webhook separada da ativação operacional.

#### WA-004 — integração é somente de entrada para o chat interno

Severidade: **alta**

Mensagem do WhatsApp entra no chat interno, mas uma resposta digitada pelo atendente no chat interno não é enviada ao WhatsApp.

Também não há indicação robusta na interface de que a sala é um canal externo.

Correção:

- criar adaptador de saída por canal;
- detectar sala `room_type='whatsapp'`;
- enviar pela Meta antes de confirmar a mensagem;
- mostrar estados enviando, enviada, entregue, lida e falhou;
- bloquear anexos não suportados;
- respeitar janela de atendimento e templates.

#### WA-005 — mídia não está implementada

Severidade: **alta**

Tipos diferentes de texto são normalizados apenas como `[image]`, `[document]`, etc. O arquivo não é baixado, validado, armazenado nem exibido.

Faltam:

- endpoint de mídia da Meta;
- download autenticado;
- MIME real e tamanho;
- allowlist;
- antivírus;
- armazenamento privado;
- URL temporária;
- envio de imagem, documento, áudio e vídeo;
- associação com anexos do chat interno.

#### WA-006 — triagem não guarda respostas nem encaminha de fato

Severidade: **alta**

A máquina de estados pergunta nome, origem e setor, porém:

- não salva o nome informado;
- não salva empresa/cidade;
- não interpreta 1, 2, 3 ou 4;
- não atualiza `department_id`;
- não atribui `assigned_user_id`;
- `target_department_id` das regras não é aplicado à conversa;
- não existe fila operacional por setor.

Correção:

- definir estados e transições explícitos;
- persistir respostas estruturadas;
- validar opções;
- encaminhar para setor e responsável;
- permitir retorno, timeout e reinício;
- notificar o atendente atribuído.

#### WA-007 — notificações em tempo real não são disparadas

Severidade: **alta**

`mirror_to_chat()` insere diretamente em `chat_messages`, mas não usa o mecanismo de broadcast/notificação do chat. A mensagem pode aparecer após recarregar sem avisar o responsável em tempo real.

Correção:

- criar serviço único para gravação e publicação de mensagens;
- disparar WebSocket/notificação após commit;
- usar outbox para não perder eventos;
- testar usuário atribuído, setor e contadores.

#### WA-008 — janela de atendimento e templates ausentes

Severidade: **alta**

O cliente atual envia somente texto livre. Não há:

- controle da janela de atendimento;
- templates aprovados;
- idioma e parâmetros;
- sincronização de templates;
- fallback quando texto livre é recusado;
- classificação e custo de mensagens.

Correção:

- guardar `last_inbound_at` e expiração da janela;
- permitir texto livre somente quando aplicável;
- criar catálogo de templates;
- implementar mensagens de utilidade para fatura/pedido;
- registrar erro síncrono e falha assíncrona.

#### WA-009 — status de mensagem não é processado

Severidade: **alta**

O normalizador ignora eventos `statuses`. Não há atualização de enviada, entregue, lida ou falha.

Correção:

- normalizar todos os status relevantes;
- atualizar mensagem pelo ID da Meta;
- registrar código e descrição segura do erro;
- atualizar a interface em tempo real;
- métricas de entrega.

#### WA-010 — chamadas externas síncronas e sem resiliência

Severidade: **alta para escala**

O cliente usa `urllib.request` síncrono. Não há:

- pool HTTP;
- retry;
- backoff;
- circuit breaker;
- fila;
- timeout por operação;
- idempotency/outbox;
- dead-letter queue.

Uma chamada lenta pode bloquear worker da aplicação.

Recomendação:

- cliente HTTP assíncrono ou worker dedicado;
- fila Redis/RQ, Celery, Dramatiq ou solução equivalente;
- outbox no banco;
- retry somente para erros recuperáveis;
- circuit breaker e métricas.

#### WA-011 — criptografia de segredos inadequada

Severidade: **crítica de segurança**

`encrypt_secret()` usa XOR com fluxo determinístico derivado de SHA-256:

- sem nonce aleatório;
- sem autenticação;
- sem detecção de adulteração;
- mesma chave e mesmo texto geram o mesmo resultado.

Além disso, `_master_key()` possui fallback fixo no código:

`sist-ionm-local-whatsapp-secret`

Impacto:

- se a variável de ambiente não estiver definida, qualquer pessoa com o código pode descriptografar tokens;
- ciphertext pode ser alterado sem validação de integridade.

Correção:

- remover fallback em ambientes não locais;
- falhar no startup quando segredo obrigatório não existir;
- usar AES-GCM/Fernet ou secret manager;
- chave por ambiente;
- rotação e versionamento de chave;
- nunca armazenar token em logs ou sessão;
- revisar também o módulo de configuração de banco.

#### WA-012 — ausência de CSRF e rate limiting

Severidade: **alta**

Rotas administrativas usam sessão e POST, mas não possuem token CSRF. O webhook e o teste de envio não possuem rate limiting.

Correção:

- CSRF em todos os formulários que alteram estado;
- validação Origin/Referer como defesa adicional;
- rate limit no login, webhook e ações de teste;
- limites de tamanho do corpo;
- `429 Retry-After`;
- proteção de abuso por usuário e IP.

#### WA-013 — dados brutos e retenção

Severidade: **média/alta**

`raw_payload_json` armazena payload bruto sem política de retenção, minimização ou anonimização.

Correção:

- definir finalidade e prazo;
- evitar duplicar PII desnecessária;
- criptografar dados sensíveis em repouso;
- controlar acesso;
- registrar consulta e exportação;
- implementar expurgo conforme LGPD.

#### WA-014 — schema e concorrência

Severidade: **média/alta**

- SQLite limita escrita concorrente;
- faltam foreign keys declaradas;
- faltam índices para fila, status, setor, responsável e datas;
- repositório abre várias conexões por mensagem;
- etapas de contato, conversa, mensagem e chat não formam uma única transação;
- uma falha intermediária pode gerar estado parcial.

Correção:

- migrar para PostgreSQL;
- constraints e índices;
- transação por evento;
- outbox;
- migrations Alembic;
- testes concorrentes.

#### WA-015 — API Graph fixa e ciclo de atualização

Severidade: **média**

O padrão está em `v23.0`. A versão precisa ser validada contra o ciclo de suporte da Meta no momento do deploy.

Correção:

- registrar versão homologada e data de fim de suporte;
- teste automatizado de compatibilidade;
- atualizar por ambiente;
- não permitir valor arbitrário sem validação;
- acompanhar changelog e janela de migração.

## 6. WhatsApp Web, QR e Coexistence

### Situação atual

O pedido original de “conectar a plataforma como dispositivo pelo QR do WhatsApp Web” não foi implementado.

Não é recomendado adicionar automação não oficial de navegador como caminho principal. Esse modelo:

- depende de protocolo/sessão não contratual;
- pode quebrar após atualizações;
- exige armazenamento sensível de sessão;
- cria risco de bloqueio;
- dificulta suporte, auditoria e escala.

### Caminho recomendado para revisão

Em 2026 existe um caminho oficial que deve ser avaliado pela equipe: **WhatsApp Business App Coexistence via Embedded Signup**. O objetivo é manter o mesmo número no aplicativo WhatsApp Business e na Cloud API, quando a conta e o fluxo forem elegíveis.

Isso não significa parear o SIST-iONM como um navegador do WhatsApp Web. É um onboarding oficial da Meta.

Recomendação:

1. não implementar Baileys, `whatsapp-web.js`, Venom ou Chromium em produção;
2. criar um spike isolado de Coexistence;
3. validar elegibilidade do número atual, conta empresarial e app Meta;
4. configurar Embedded Signup para o modo correto;
5. testar histórico, contatos, mensagens do app e Cloud API;
6. documentar limitações e plano de reversão;
7. somente depois integrar ao wizard principal.

Se a Coexistence não estiver disponível para a conta atual, escolher explicitamente entre:

- migrar o número para Cloud API;
- manter WhatsApp Business App separado;
- usar outro número para a plataforma;
- contratar BSP oficial.

## 7. Melhorias gerais prioritárias

### P0 — bloquear falsa percepção de produção

- exibir no wizard WhatsApp o estado “Fundação técnica / não operacional” enquanto WA-001 e WA-002 não forem concluídos;
- remover qualquer texto que sugira automação ativa;
- impedir ativação sem teste de entrada e saída;
- recriar `.venv` e validar lock;
- documentar que PostgreSQL ainda não é o banco ativo.

### P1 — fechar WhatsApp oficial

- completar Embedded Signup;
- enviar respostas automáticas;
- criar saída do chat interno para WhatsApp;
- status de entrega;
- mídia;
- triagem real e atribuição;
- janela de atendimento e templates;
- outbox, fila, retry e DLQ;
- segredos com criptografia autenticada.

### P2 — banco e arquitetura

- migrar SQLite para PostgreSQL;
- mover regras restantes de `app/main.py` para domínios;
- Alembic obrigatório;
- unidade de trabalho/transações;
- repositories com contratos;
- índices, constraints e auditoria.

### P3 — segurança

- CSRF;
- rate limiting;
- 2FA para administradores;
- Argon2id aplicado a todas as senhas legadas;
- rotação de sessão;
- secret manager;
- logs estruturados sem PII;
- backup criptografado;
- SAST, dependency audit e SBOM.

### P4 — operação e qualidade

- Docker/Compose para desenvolvimento e homologação;
- pipeline CI com lint, testes e migração;
- ambiente de staging;
- health/readiness checks;
- métricas Prometheus/OpenTelemetry;
- rastreamento de jobs;
- alertas de webhook, fila e falhas Meta;
- testes E2E com conta/número Meta de teste;
- teste de carga do webhook e chat.

### P5 — produto

- inbox omnichannel dedicada;
- fila por setor;
- SLA e prioridade;
- tags;
- notas internas;
- responsável atual e histórico;
- busca por telefone/cliente/pedido;
- respostas rápidas;
- templates;
- dashboard de atendimento;
- consentimento, opt-in e opt-out;
- exportação e exclusão LGPD.

## 8. Organização recomendada do código

Estrutura-alvo:

```text
app/
  features/
    whatsapp/
      domain/
        entities.py
        triage.py
        policies.py
      application/
        inbound.py
        outbound.py
        assignments.py
        templates.py
      infrastructure/
        meta_client.py
        repository.py
        media_store.py
        queue.py
      web/
        admin_routes.py
        webhook_routes.py
        schemas.py
```

Separações obrigatórias:

- webhook não deve executar automação pesada;
- cliente Meta não deve decidir regra de negócio;
- chat interno não deve gravar mensagens por caminhos diferentes;
- triagem deve ser máquina de estados testável;
- persistência de saída e publicação devem usar outbox;
- segredos devem vir de infraestrutura, não do domínio.

## 9. Plano sugerido para a equipe

### Sprint 0 — reprodução e baseline

- recriar `.venv` pelo `requirements.lock`;
- executar testes;
- subir em Ubuntu;
- inventariar variáveis de ambiente;
- criar conta/número Meta de teste;
- registrar decisões de Coexistence;
- abrir ADRs para WhatsApp, PostgreSQL e filas.

Saída:

- ambiente reproduzível;
- riscos confirmados;
- backlog aceito;
- documentação de credenciais sem segredos.

### Sprint 1 — segurança e onboarding

- criptografia autenticada;
- remoção de fallback de chave;
- CSRF e rate limiting;
- Embedded Signup completo;
- expiração de sessão;
- status confiável do wizard.

### Sprint 2 — mensageria de saída

- outbox;
- worker;
- envio automático;
- resposta do atendente;
- persistência outbound;
- retries e DLQ;
- status enviado/entregue/lido/falhou.

### Sprint 3 — triagem e atendimento

- dados estruturados;
- setor e responsável;
- notificações em tempo real;
- fila de atendimento;
- SLA;
- respostas rápidas.

### Sprint 4 — mídia e templates

- download/upload de mídia;
- armazenamento privado;
- antivírus;
- templates;
- janela de atendimento;
- opt-in/opt-out.

### Sprint 5 — PostgreSQL e produção

- migrações;
- carga e rollback;
- observabilidade;
- staging;
- backup/restore;
- teste de carga;
- homologação.

## 10. Critérios de aceite para WhatsApp

O módulo só deve ser declarado operacional quando:

- Embedded Signup termina com WABA e número válidos;
- webhook público HTTPS é verificado;
- assinatura inválida é rejeitada;
- evento duplicado não duplica mensagem nem resposta;
- mensagem recebida aparece em tempo real para o setor correto;
- triagem salva nome, origem e setor;
- resposta automática chega ao aparelho;
- atendente responde pelo SIST-iONM;
- texto, imagem e documento funcionam;
- janela de atendimento e templates são respeitados;
- status enviado, entregue, lido e falhou são refletidos;
- retry não duplica envio;
- falha vai para DLQ e gera alerta;
- segredos não aparecem em HTML, logs ou banco em texto claro;
- desativação impede automação;
- testes E2E usam número Meta controlado;
- política LGPD e retenção está documentada.

## 11. Gate técnico recomendado

```powershell
python -m pytest tests\features tests\web tests\performance tests\characterization -q
python -m ruff check app tests
python -m mypy app
python -m pip check
node --check app\static\chat_realtime.js
node --test tests\js\shell-navigation.test.js
node --test tests\js\chat-notifications.test.js
node --test tests\js\profile-avatar-editor.test.js
git diff --check
```

Adicionar ao CI:

- `pip-audit`;
- secret scanning;
- Bandit ou Semgrep;
- coverage mínima para domínio WhatsApp;
- testes de migration upgrade/downgrade;
- teste de webhook concorrente;
- teste E2E Meta em ambiente protegido.

## 12. Evidências e limitações desta revisão

Evidências locais:

- `docs/versions.md`;
- `docs/development.md`;
- `docs/file-map.md`;
- `docs/bug-audit.md`;
- código em `app/features/whatsapp`;
- testes em `tests/features/test_whatsapp_*` e `tests/web/test_whatsapp_integration.py`;
- histórico Git até `d09c66b`.

Limitações:

- não foi usado um número Meta real nesta auditoria;
- o fluxo Embedded Signup não pôde ser concluído sem credenciais;
- a elegibilidade de Coexistence depende da conta Meta e deve ser validada no painel oficial;
- o `.venv` presente no workspace não inicia porque não localiza `pyvenv.cfg`;
- existe um ZIP não rastreado na raiz, pertencente ao usuário, que não foi alterado;
- versões da Graph API e políticas Meta devem ser reconfirmadas no início da implementação.

## 13. Referências para a equipe

- Meta WhatsApp Business Platform — coleção oficial Postman:  
  <https://www.postman.com/meta/whatsapp-business-platform/overview>
- Meta WhatsApp Cloud API — coleção oficial Postman:  
  <https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api>
- Meta Embedded Signup:  
  <https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview>
- Meta Cloud API:  
  <https://developers.facebook.com/docs/whatsapp/cloud-api/overview>
- Especificação interna de WhatsApp, perfis e RH:  
  `docs/superpowers/specs/2026-06-25-whatsapp-perfis-rh-design.md`
- Plano interno do Embedded Signup e automações:  
  `docs/superpowers/plans/2026-06-25-whatsapp-embedded-signup-automacoes.md`

## 14. Decisão recomendada

Manter a Cloud API oficial como núcleo. Revisar o requisito “WhatsApp Web por QR” como “manter o número também no WhatsApp Business App”, avaliando **Coexistence oficial via Embedded Signup**.

Não incorporar automação não oficial de WhatsApp Web ao core produtivo. Se a equipe quiser estudá-la, o estudo deve ficar em repositório e ambiente isolados, sem dados reais, sem compartilhar banco ou credenciais com o SIST-iONM e sem compromisso de produção.

