# Custos fixos recorrentes

Data: 26 de junho de 2026  
Status: aprovado para planejamento

## Objetivo

Organizar os custos da empresa separando lançamentos variáveis de compromissos fixos recorrentes. Um custo fixo ativo deve gerar automaticamente, em cada competência mensal, uma conta real em `A pagar`, com categoria e histórico auditável.

## Escopo

O segmento `Financeiro → Custos` terá três áreas:

1. **Lançamentos variáveis**: custos avulsos já realizados ou previstos.
2. **Custos fixos recorrentes**: cadastros-matriz que originam contas mensais.
3. **Categorias**: classificação administrável dos custos fixos e variáveis.

O trabalho inclui a integração dos compromissos gerados com `A pagar`, Dashboard e BI Gerencial.

## Modelo funcional

### Custos fixos recorrentes

Cada cadastro terá:

- descrição;
- categoria;
- favorecido, vinculado aos fornecedores ou vendedores existentes quando aplicável;
- centro de custo;
- valor vigente;
- dia de vencimento;
- data inicial;
- data final opcional;
- forma de pagamento;
- conta bancária;
- observações;
- status: ativo, pausado ou excluído;
- usuário e data da criação e da última alteração.

Ações disponíveis:

- criar;
- editar;
- pausar;
- reativar;
- excluir.

Uma edição afeta somente competências futuras ainda não geradas. Contas já geradas preservam descrição, categoria, favorecido, valor e vencimento registrados no momento da geração.

### Geração automática

Um processo automático verifica custos fixos ativos e gera uma conta em `A pagar` para cada competência mensal devida.

A geração será idempotente. A combinação entre custo recorrente e competência será única, impedindo contas duplicadas mesmo se o processo for executado mais de uma vez.

O processo:

1. seleciona custos ativos cuja vigência inclua a competência;
2. verifica se a conta daquela competência já existe;
3. calcula o vencimento pelo dia configurado;
4. ajusta o vencimento para o próximo dia útil quando cair em sábado, domingo ou feriado cadastrado;
5. cria a conta em `A pagar` com referência ao cadastro recorrente e à competência;
6. registra o resultado da execução para auditoria.

Se o dia escolhido não existir no mês, será usado o último dia do mês antes do ajuste para dia útil.

A automação também será executada de forma segura na inicialização e no primeiro acesso financeiro do dia, para que uma indisponibilidade temporária do servidor não deixe competências sem geração. A restrição única continuará sendo a proteção definitiva contra duplicidade.

### Feriados

O financeiro poderá manter uma lista de feriados com data, descrição e abrangência. Sem feriado cadastrado, o sistema ajustará apenas sábados e domingos.

### Categorias

O financeiro poderá:

- criar;
- editar;
- excluir;
- consultar categorias ativas e inativas.

O botão `Excluir` estará disponível nos registros criados pelo usuário. A exclusão seguirá estas regras:

- categoria nunca utilizada: exclusão física;
- categoria já utilizada: exclusão lógica, deixando de aparecer em novos cadastros e mantendo o histórico;
- custo recorrente sem contas geradas: exclusão física;
- custo recorrente com contas geradas: exclusão lógica, interrompendo novas gerações e preservando os lançamentos anteriores;
- conta a pagar sem baixa: poderá ser excluída conforme as permissões financeiras;
- conta paga: permanecerá auditável e não será removida fisicamente.

Assim, o usuário sempre tem a ação de exclusão, mas o sistema protege registros financeiros já utilizados.

## Arquitetura

O domínio financeiro ganhará unidades separadas para:

- repositório de categorias;
- repositório de custos recorrentes;
- serviço de calendário e dias úteis;
- serviço idempotente de geração mensal;
- rotas e validações do módulo;
- integração de leitura com contas a pagar e indicadores.

As regras não ficarão nos templates. Templates apenas exibem dados e enviam comandos; validação, recorrência, exclusão e geração ficam no serviço de domínio.

Enquanto a extração completa de `app/main.py` não estiver concluída, as novas regras serão implementadas em `app/features/finance/`, com rotas finas conectadas à aplicação atual. Isso evita aumentar o monólito e prepara a migração para PostgreSQL.

## Dados

Serão criadas as tabelas:

- `cost_categories`;
- `recurring_costs`;
- `recurring_cost_occurrences`;
- `business_holidays`;
- `recurring_cost_runs`.

`payables` receberá referências opcionais ao custo recorrente, à ocorrência e à competência. A ocorrência vincula de forma imutável o cadastro-matriz à conta gerada.

Restrições importantes:

- categoria com nome único entre registros ativos;
- uma ocorrência por custo recorrente e competência;
- valor maior que zero;
- dia de vencimento entre 1 e 31;
- data final igual ou posterior à inicial;
- favorecido e categoria válidos;
- exclusões e mudanças de status com usuário e data.

As migrações serão compatíveis com o banco atual e preparadas para PostgreSQL.

## Interface

As novas áreas seguirão o design system minimalista existente:

- subabas compactas dentro de `Custos`;
- formulário dividido em identificação, recorrência e pagamento;
- campos de categoria, favorecido, centro de custo, forma de pagamento e conta bancária como listas;
- tabelas com status, próximo vencimento e ações;
- filtros por categoria, status, centro de custo e favorecido;
- confirmação explícita antes de excluir;
- mensagem clara quando a exclusão for convertida em preservação histórica;
- indicação da origem recorrente na tabela de `A pagar`.

## Permissões e auditoria

Administradores e usuários financeiros autorizados poderão administrar custos e categorias. Visualização, criação, edição, exclusão e geração respeitarão as permissões do módulo financeiro.

Serão auditados:

- criação e alteração;
- pausa e reativação;
- exclusão física ou lógica;
- geração de ocorrências;
- falhas de geração;
- exclusão ou baixa da conta gerada.

## Tratamento de erros

- falha em um custo não interrompe a geração dos demais;
- cada falha fica registrada com causa e competência;
- cadastro inválido não é processado;
- nova tentativa pode ser feita sem duplicar contas;
- concorrência entre processos é resolvida pela restrição única no banco;
- mensagens exibidas ao usuário não expõem detalhes internos do banco.

## Testes e critérios de aceite

Devem existir testes para:

- criação, edição, pausa, reativação e exclusão de custo recorrente;
- criação, edição e exclusão de categorias;
- exclusão física de item sem uso;
- exclusão lógica de item com histórico;
- geração automática mensal;
- prevenção de duplicidade;
- vigência inicial e final;
- último dia em meses curtos;
- ajuste de sábado, domingo e feriado;
- preservação de contas antigas após edição do cadastro;
- inclusão da conta gerada em `A pagar`, Dashboard e BI;
- filtros e permissões;
- recuperação após falha ou período de servidor indisponível;
- compatibilidade das páginas financeiras existentes.

O recurso será aceito quando um custo fixo ativo gerar automaticamente uma única conta por competência, os totais financeiros forem atualizados e todas as ações de manutenção estiverem disponíveis sem perda do histórico.

## Fora do escopo

- recorrência semanal, trimestral, semestral ou anual;
- reajuste automático por índice econômico;
- integração bancária para débito automático;
- importação em massa de contratos recorrentes;
- calendário público de feriados por API externa.
