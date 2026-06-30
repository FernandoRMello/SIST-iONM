# Plataforma WhatsApp, Perfis e RH — Design de Produto e Arquitetura

## Objetivo

Evoluir o SIST-iONM em três frentes integradas:

1. WhatsApp Business oficial com conexão assistida pela Meta, automações e consultas seguras.
2. Módulo central de perfis e permissões configuráveis.
3. Módulo de RH para colaboradores, folha, comissões e benefícios.

O desenho prioriza segurança, escalabilidade local/Ubuntu e manutenção por desenvolvedor júnior, sem acoplar a plataforma a automações não oficiais de WhatsApp Web.

## Decisão sobre WhatsApp Web via QR Code

O QR Code solicitado para conectar a plataforma como dispositivo adicional do WhatsApp Web **não será usado como motor principal** do produto. Esse fluxo depende de sessão de WhatsApp Web/dispositivo, não é o padrão da WhatsApp Business Platform oficial para integrações corporativas, pode quebrar sem aviso e cria risco operacional.

O caminho produtivo será:

- Meta WhatsApp Business Cloud API;
- Embedded Signup oficial para “Conectar com Meta”;
- webhook seguro;
- QR Code oficial apenas para cliente iniciar conversa com a empresa;
- documentação deixando WhatsApp Web/QR como fora do core de produção.

Referências oficiais:

- `https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview`
- `https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users`
- `https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started`
- `https://developers.facebook.com/documentation/business-messaging/whatsapp/qr-codes/`

## Fase 1 — WhatsApp Business oficial

### Escopo

- Manter o wizard manual já criado.
- Adicionar botão `Conectar com Meta`.
- Implementar Embedded Signup oficial.
- Manter webhook seguro com validação `X-Hub-Signature-256`.
- Automatizar mensagens por regras.
- Permitir primeiro contato, triagem, resposta automática e encaminhamento humano.
- Consultar pedidos/faturas somente quando o contato WhatsApp estiver vinculado com segurança a um cliente.
- Criar QR Code/short link oficial para o cliente iniciar conversa com a empresa.

### Fluxo administrativo

Tela:

```text
Administração → Integrações → WhatsApp Business
```

Botões:

- `Conectar com Meta`;
- `Configurar manualmente`;
- `Gerar QR Code para clientes`;
- `Testar conexão`;
- `Ativar/Desativar`.

O botão `Conectar com Meta` deve iniciar o Embedded Signup. Ao concluir o fluxo, o sistema deve capturar e persistir os dados permitidos pela Meta, sem expor tokens em tela.

### Fluxo de automação

Primeiro contato:

1. Saudação.
2. Pergunta nome.
3. Pergunta empresa/cidade/origem.
4. Apresenta setores.
5. Cria ou atualiza contato.
6. Cria conversa interna no chat.

Triagem:

- Comercial;
- Financeiro;
- Pedidos;
- Suporte;
- setor customizável no futuro pelo módulo de permissões/perfis.

Respostas automáticas iniciais:

- `financeiro`, `fatura`, `boleto`, `contas`: consultar recebíveis vinculados ao cliente.
- `pedido`, `pedidos`, `compra`: consultar pedidos vinculados ao cliente.
- `humano`, `atendente`, `suporte`: encaminhar para setor.
- qualquer intenção não reconhecida: responder com menu e encaminhar humano se repetir.

### Segurança de dados

O sistema não deve retornar dados financeiros, pedidos ou documentos se:

- telefone não estiver vinculado a um cliente;
- cliente tiver mais de um possível vínculo;
- solicitação envolver dados sensíveis sem confirmação;
- regra de permissão do módulo bloquear a consulta.

Mensagem padrão nesses casos:

```text
Encontrei sua solicitação, mas preciso confirmar seu cadastro antes de mostrar informações financeiras ou pedidos. Vou encaminhar para um atendente.
```

### Modelo de dados adicional

Além das tabelas WhatsApp já criadas, adicionar:

```text
whatsapp_embedded_signup_sessions
  id
  started_by_user_id
  state_token_hash
  status
  provider_payload_json
  created_at
  completed_at

whatsapp_automation_rules
  id
  name
  trigger_type
  trigger_value
  response_type
  response_text
  target_department_id
  is_active
  created_by_user_id
  created_at
  updated_at

whatsapp_qr_codes
  id
  name
  code
  short_link
  prefilled_message
  is_active
  created_by_user_id
  created_at
  updated_at
```

### Fora do escopo da Fase 1

- Conectar como WhatsApp Web por QR Code.
- Envio de campanhas em massa.
- IA generativa respondendo sem regras.
- Multi-número simultâneo.
- Fila avançada de call center.

## Fase 2 — Perfis e permissões

### Objetivo

Substituir a lógica rígida de perfis fixos por um módulo central configurável, onde administradores possam criar perfis conforme a empresa precisar.

### Escopo

- Criar perfis livremente.
- Atribuir usuários a perfis.
- Controlar acesso por módulo, tela e ação.
- Permitir permissões especiais.
- Integrar criação de usuário ao fluxo de RH e Administração.

### Perfis

Perfis não devem ser fixos no código. O sistema pode nascer com sementes:

- Admin;
- Vendedor;
- Financeiro;
- RH;
- TI;
- Gestor.

Mas o administrador poderá criar outros.

### Permissões controladas

Ações padrão:

- visualizar;
- criar;
- editar;
- excluir;
- aprovar;
- exportar;
- configurar.

Escopos:

- módulo;
- tela;
- funcionalidade;
- registro próprio;
- equipe/departamento;
- todos os registros.

Permissões especiais:

- configurar WhatsApp;
- visualizar folha de pagamento;
- processar folha;
- aprovar folha;
- configurar comissões;
- configurar benefícios;
- visualizar dados financeiros sensíveis;
- gerenciar usuários;
- gerenciar perfis.

### Modelo de dados

```text
access_profiles
  id
  name
  description
  is_system
  is_active
  created_at
  updated_at

access_permissions
  id
  code
  module
  screen
  action
  description

access_profile_permissions
  profile_id
  permission_id
  scope
  enabled

user_access_profiles
  user_id
  profile_id
  assigned_by_user_id
  assigned_at
```

### Compatibilidade

A tabela legada `role_permissions` deve ser migrada gradualmente. Enquanto a migração não for completa, o sistema deve suportar:

- leitura do novo modelo quando existir;
- fallback para `role_permissions` em rotas antigas;
- testes garantindo que telas administrativas e financeiras continuam protegidas.

## Fase 3 — RH, folha, comissões e benefícios

### Objetivo

Criar um módulo de RH para gerenciar colaboradores, vínculo com usuários, regras de remuneração variável, benefícios e folha mensal.

### Escopo

- Cadastro de colaboradores.
- Vínculo com usuário do sistema.
- Cargo e departamento.
- Salário base.
- Tipo de contrato.
- Benefícios.
- Comissões.
- Folha mensal.
- Histórico de pagamentos.
- Criação de usuários a partir do colaborador.
- Atribuição de perfis de visualização/acesso.

### Colaboradores

Campos mínimos:

- nome completo;
- documento;
- e-mail;
- telefone;
- departamento;
- cargo;
- tipo de contrato;
- data de admissão;
- status;
- salário base;
- usuário vinculado;
- gestor responsável;
- observações.

### Tipo de contrato

Valores iniciais:

- CLT;
- PJ;
- Estágio;
- Autônomo;
- Sócio;
- Outro.

Esses valores devem poder ser ampliados no futuro.

### Regras de comissão

Bases:

- lucro;
- venda total.

Formas:

- percentual fixo;
- percentual por faixa;
- individual;
- geral da empresa.

Exemplos:

```text
Vendedor A recebe 5% sobre lucro dos próprios pedidos.
Equipe comercial recebe 1% sobre venda total geral ao bater meta mensal.
Gestor recebe faixa progressiva sobre lucro geral.
```

### Benefícios

Tipos:

- fixo mensal;
- percentual sobre venda individual;
- percentual sobre comissão individual;
- percentual sobre LL individual;
- percentual sobre venda geral da empresa;
- percentual sobre comissão geral;
- percentual sobre LL geral;
- por meta individual;
- por meta geral da empresa.

### Folha mensal

Fluxo:

1. RH cria competência mensal.
2. Sistema calcula salário base, benefícios e comissões.
3. RH revisa lançamentos.
4. Gestor ou Admin aprova.
5. Financeiro marca como pago.
6. Histórico fica imutável, com estorno/ajuste por lançamento complementar.

### Modelo de dados

```text
hr_employees
  id
  user_id
  full_name
  document
  email
  phone
  department_id
  job_title
  contract_type
  admission_date
  status
  base_salary
  manager_user_id
  notes
  created_at
  updated_at

hr_commission_rules
  id
  name
  employee_id
  profile_id
  basis
  calculation_scope
  percentage_type
  fixed_percentage
  is_active
  created_at
  updated_at

hr_commission_tiers
  id
  rule_id
  min_value
  max_value
  percentage

hr_benefit_rules
  id
  name
  employee_id
  profile_id
  benefit_type
  basis
  calculation_scope
  fixed_amount
  percentage
  target_value
  is_active
  created_at
  updated_at

hr_payroll_periods
  id
  period
  status
  created_by_user_id
  approved_by_user_id
  paid_by_user_id
  created_at
  approved_at
  paid_at

hr_payroll_items
  id
  payroll_period_id
  employee_id
  item_type
  description
  basis_amount
  percentage
  amount
  source_type
  source_id
  created_at

hr_payment_history
  id
  payroll_period_id
  employee_id
  amount
  status
  paid_at
  notes
```

### Segurança do módulo RH

Dados de folha são sensíveis. Regras obrigatórias:

- somente perfis autorizados visualizam salário, folha e benefícios;
- vendedor não visualiza folha de outro colaborador;
- alteração de salário, benefício ou comissão exige permissão especial;
- fechamento/aprovação/pagamento exige ações separadas;
- histórico não deve ser apagado fisicamente por usuário comum;
- exportação deve exigir permissão própria.

## Navegação proposta

Menu:

```text
Administração
  Perfis e permissões
  Usuários
  Integrações
    WhatsApp Business

RH
  Colaboradores
  Cargos e departamentos
  Regras de comissão
  Benefícios
  Folha de pagamento
  Histórico de pagamentos
```

## Estratégia de implementação

Implementar em três planos separados:

1. `WhatsApp Embedded Signup e automações`
2. `Perfis e permissões configuráveis`
3. `RH, folha, comissões e benefícios`

Cada plano deve:

- começar por testes de regressão;
- preservar rotas atuais;
- manter fallback de permissões legado até migração completa;
- atualizar documentação;
- rodar o gate completo antes da entrega.

## Critérios de aceite

### Fase 1

- Admin vê botão `Conectar com Meta`.
- Embedded Signup inicia com `state` seguro.
- Callback salva status sem expor segredos.
- Webhook continua validando assinatura.
- Regras automáticas podem ser cadastradas/ativadas/desativadas.
- Mensagem de cliente sem vínculo seguro não retorna dados financeiros.
- QR Code oficial para cliente iniciar conversa é exibido/gerenciado.

### Fase 2

- Admin cria perfis sem alterar código.
- Admin atribui perfis a usuários.
- Permissões por tela/ação são respeitadas no servidor.
- Permissões especiais bloqueiam WhatsApp, folha e financeiro sensível.
- Rotas antigas continuam protegidas.

### Fase 3

- RH cadastra colaborador e cria usuário vinculado.
- RH atribui perfil ao usuário criado.
- Sistema calcula comissão por lucro ou venda total.
- Sistema calcula benefício fixo, individual e geral.
- Folha mensal gera itens rastreáveis.
- Aprovação e pagamento ficam registrados.
- Usuários sem permissão não acessam dados sensíveis.

## Riscos e mitigação

- **WhatsApp Web via QR:** fora do core por risco de instabilidade e não oficialidade. Mitigação: Cloud API + Embedded Signup.
- **Dados sensíveis de RH:** acesso por permissão especial e auditoria.
- **Cálculo incorreto de folha/comissão:** cálculo versionado por competência e testes unitários por regra.
- **Crescimento de regras:** separar engine de cálculo em módulo próprio, com entradas e saídas bem definidas.
- **Migração de permissões:** fallback temporário para `role_permissions` até cobertura completa do novo modelo.
