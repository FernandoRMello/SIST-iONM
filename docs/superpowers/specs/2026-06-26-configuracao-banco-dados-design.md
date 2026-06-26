# Configuração de banco de dados na plataforma — Design

Data: 2026-06-26

## Objetivo

Criar em **Configurações** uma área dedicada ao banco de dados para permitir que um administrador configure, teste e prepare uma conexão PostgreSQL de forma profissional, sem expor credenciais e sem misturar essa responsabilidade com usuários, e-mail, WhatsApp ou RH.

A tela deve facilitar implantação em servidor local/Linux Ubuntu, troca futura de banco, diagnóstico de conexão e operação de backup.

## Escopo aprovado

- Manter SQLite como modo legado/local atual.
- Introduzir PostgreSQL como destino configurável pela plataforma.
- Permitir cadastrar host, porta, nome do banco, usuário, senha, SSL e observações operacionais.
- Permitir testar conexão antes de salvar/ativar.
- Permitir preparar o ambiente quando o usuário informado tiver permissão suficiente.
- Mascarar a senha depois de salva; senha vazia em edição preserva a senha anterior.
- Informar que a troca efetiva do banco exige reinício do servidor local para evitar conexões abertas usando datasource antigo.
- Exibir status do banco atual, banco configurado e última tentativa de conexão/preparo.
- Manter backup/exportação em Configurações, com preparação para banco ativo.

Fora deste primeiro ciclo:

- Migração completa de dados SQLite → PostgreSQL.
- Conversão total do runtime para SQLAlchemy/Alembic.
- Alta disponibilidade, réplica, cluster ou failover.
- Gerenciamento remoto de serviços PostgreSQL do servidor.

## Arquitetura

### 1. Domínio de administração de banco

Criar um módulo focado, por exemplo:

```text
app/features/database_admin/
  repository.py
  service.py
  routes.py
```

Responsabilidades:

- `repository.py`: persistir configurações operacionais no banco atual.
- `service.py`: validar configuração, montar DSN seguro, testar conexão PostgreSQL e preparar estrutura mínima.
- `routes.py`: expor tela e ações administrativas.

Enquanto o runtime principal ainda usa `DB_PATH` SQLite em `app/main.py`, esse módulo funcionará como preparação profissional para cutover PostgreSQL. Ele não deve prometer troca quente de banco em execução.

### 2. Persistência da configuração

Adicionar tabela administrativa no banco atual:

```text
database_connections
  id
  name
  engine
  host
  port
  database_name
  username
  password_encrypted
  ssl_mode
  status
  is_active_candidate
  last_test_status
  last_test_message
  last_test_at
  last_prepare_status
  last_prepare_message
  last_prepare_at
  updated_by_user_id
  created_at
  updated_at
```

Somente PostgreSQL será configurável na UI neste ciclo. SQLite aparece como banco atual/legado, mas não como novo destino editável.

### 3. Segurança de credenciais

As credenciais precisam seguir o padrão já usado no módulo WhatsApp:

- senha criptografada em repouso;
- senha nunca renderizada de volta no HTML;
- senha vazia preserva segredo existente;
- logs e mensagens de erro não devem incluir senha;
- rotas disponíveis apenas para administrador;
- testes devem validar que a senha salva não aparece na resposta da página.

O ideal é reutilizar helpers já existentes de criptografia/mascaramento, se estiverem adequados e desacopláveis. Se estiverem presos ao WhatsApp, extrair para utilitário compartilhado sem alterar comportamento existente.

### 4. Teste de conexão

O botão **Testar conexão** deve:

1. Receber os campos do formulário.
2. Montar conexão PostgreSQL com timeout curto.
3. Executar uma consulta simples, como `SELECT 1`.
4. Registrar status, data/hora e mensagem operacional curta.
5. Retornar para a tela com feedback.

Mensagens devem ser úteis para operação, mas seguras. Exemplo:

- “Conexão realizada com sucesso.”
- “Falha de autenticação.”
- “Servidor não encontrado ou porta indisponível.”
- “Banco informado não existe.”

Não renderizar stack trace na interface.

### 5. Preparar ambiente

O botão **Preparar ambiente** deve ser separado de **Testar conexão**, porque exige permissões maiores.

Neste primeiro ciclo, preparar ambiente significa:

- abrir conexão PostgreSQL;
- criar tabela de controle da plataforma, por exemplo `sist_ionm_schema_status`;
- registrar versão/base de preparo;
- executar verificações mínimas de permissão;
- deixar mensagem clara quando o usuário não tiver permissão de `CREATE`.

Como o schema completo do sistema ainda é SQLite/SQL direto, a preparação não deve criar uma estrutura parcial enganosa de todos os módulos. O texto da tela deve deixar claro: “prepara o destino para migração/cutover PostgreSQL; a migração completa será etapa posterior”.

### 6. Tela em Configurações

Adicionar seção visual em `settings.html`:

- card “Banco de dados”;
- status do banco atual;
- formulário PostgreSQL;
- botões:
  - Salvar configuração;
  - Testar conexão;
  - Preparar ambiente;
- painel de resultado:
  - último teste;
  - último preparo;
  - alerta de reinício para ativação futura;
- bloco “Backup” pode permanecer na tela, mas deve referenciar que atualmente exporta o SQLite ativo.

Campos recomendados:

- Nome da conexão;
- Host;
- Porta;
- Banco;
- Usuário;
- Senha;
- SSL mode: `prefer`, `require`, `disable`;
- Observações.

### 7. Fluxo operacional esperado

```text
Admin abre Configurações
  → Banco de dados
    → preenche PostgreSQL
      → Testar conexão
        → se OK, Salvar configuração
          → Preparar ambiente
            → se OK, ambiente pronto para etapa futura de migração/cutover
```

Nenhuma ação deste ciclo deve apagar banco atual ou migrar dados automaticamente.

## Permissões

Usar controle administrativo já existente. O ideal é introduzir permissão especial futura:

- `system.database.manage`

No primeiro ciclo, se a matriz de permissões já permitir adicionar essa permissão com baixo risco, ela deve ser criada. Caso contrário, restringir a `admin` mantendo documentação do ponto de evolução.

## Tratamento de erros

- Falhas de conexão não quebram a página.
- Erros ficam em mensagem operacional segura.
- Senhas e DSNs completos nunca aparecem no HTML.
- A tela deve diferenciar:
  - configuração salva;
  - conexão testada;
  - ambiente preparado;
  - ativação pendente/requer reinício.

## Testes

### Testes de unidade/serviço

- montar DSN PostgreSQL sem vazar senha em representação textual;
- preservar senha anterior quando campo vier vazio;
- mascarar credenciais na visualização;
- classificar erros comuns de conexão;
- preparar ambiente executa consulta/tabela de controle quando conexão é válida.

### Testes web

- somente administrador acessa e altera configuração;
- página de Configurações exibe seção “Banco de dados”;
- senha salva não aparece no HTML;
- POST de teste registra status;
- POST de preparo registra status;
- botões e textos deixam claro que troca efetiva exige reinício.

### Regressão

- backup/exportação atual continua funcionando;
- Configurações de usuários/e-mail continuam funcionando;
- WhatsApp e RH não perdem suas tabelas/rotas.

## Documentação

Atualizar:

- `docs/development.md`: como configurar PostgreSQL pela tela;
- `docs/file-map.md`: novos arquivos do módulo;
- `docs/bug-audit.md` ou changelog equivalente: registrar evolução operacional;
- se necessário, `docs/versions.md`: confirmar dependências PostgreSQL usadas.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Admin achar que a troca é imediata | Texto explícito: ativação/cutover exige reinício e etapa posterior |
| Vazamento de senha | criptografia, máscara, teste web contra renderização do segredo |
| Preparar schema parcial gerar falsa segurança | criar apenas tabela de controle e comunicar que migração completa é etapa posterior |
| Usuário sem permissão no PostgreSQL | teste/preparo com mensagem específica |
| Quebrar backup SQLite atual | manter rotas existentes e cobrir com regressão |

## Critério de pronto

- Configurações tem seção “Banco de dados”.
- Admin consegue salvar PostgreSQL sem expor senha.
- Admin consegue testar conexão e registrar resultado.
- Admin consegue preparar ambiente básico quando permissões permitem.
- Tela informa claramente status e necessidade de reinício/cutover.
- Testes passam: web, features, performance/characterization relevantes e lint.
