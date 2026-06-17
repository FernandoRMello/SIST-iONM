# SIST-iONM — Modularização por Domínio e PostgreSQL

**Data:** 2026-06-17  
**Versão de origem:** `SIST-iONM_V2_6_CHAT_BITRIX_NOTIFICACOES`  
**Status:** desenho aprovado  
**Responsáveis pela continuidade:** equipe interna e Dev Junior

## 1. Objetivo

Transformar a versão atual do SIST-iONM em um monólito modular FastAPI organizado por domínio, preservando as telas, URLs e fluxos funcionais existentes. A aplicação passará a utilizar PostgreSQL, migrações Alembic, testes automatizados e implantação reproduzível em Ubuntu com Docker Compose.

A entrega também deve documentar a localização, responsabilidade e relação entre os arquivos para permitir que um Dev Junior instale, compreenda e evolua o sistema com segurança.

## 2. Escopo aprovado

- Usar a pasta `SIST-iONM_V2_6_CHAT_BITRIX_NOTIFICACOES` como versão de origem.
- Preservar a interface, as URLs e os fluxos de negócio atuais.
- Organizar o código por domínio/feature, não somente por camada técnica.
- Substituir SQLite por PostgreSQL em execução normal.
- Migrar todos os dados do SQLite atual para PostgreSQL.
- Implantar em servidor Linux/Ubuntu com Docker Compose.
- Adicionar segurança, testes, logs, migrações e documentação operacional.
- Iniciar controle de versão Git e impedir o versionamento de dados, ambientes virtuais e segredos.

## 3. Fora de escopo

- Redesenhar a identidade visual ou os fluxos das telas.
- Dividir o sistema em microsserviços.
- Criar aplicativo móvel nativo.
- Adicionar funcionalidades comerciais que não existam na versão de origem.
- Substituir Jinja2 por um framework SPA.

## 4. Diagnóstico da versão de origem

### 4.1 Tecnologias encontradas

- Python instalado: `3.13.7`.
- FastAPI: `0.115.6`.
- Uvicorn: `0.32.1`.
- Jinja2: `3.1.4`.
- python-multipart: `0.0.17`.
- ItsDangerous: `2.2.0`.
- ReportLab: `4.2.5`.
- OpenPyXL: `3.1.5`.
- Banco: SQLite em `data/overpriceon_web.db`.

### 4.2 Estado estrutural

- O arquivo `app/main.py` possui mais de 2.100 linhas e concentra inicialização, banco, autenticação, autorização, regras de negócio, relatórios, PDFs, uploads, chat, WebSockets e rotas HTTP.
- Não há suíte de testes, migrações de banco, configuração por ambiente ou histórico Git anterior.
- A raiz do workspace contém 21 cópias/pacotes de versões. Algumas versões possuem o mesmo código Python e alterações apenas em templates ou arquivos estáticos.
- O README da versão atual é acumulativo e ainda apresenta nomes de versões antigas em alguns trechos.

### 4.3 Estado do banco atual

- Tamanho auditado: 167.936 bytes.
- `PRAGMA integrity_check`: `ok`.
- 24 tabelas de aplicação.
- Nenhuma chave estrangeira declarada.
- Há dados de usuários, mensagens, oportunidades, produtos, fornecedores, histórico e configurações a preservar.
- Datas, estados booleanos e valores monetários estão majoritariamente armazenados como texto ou `REAL`.

### 4.4 Riscos encontrados

- Chave de sessão e credenciais iniciais fixas no código.
- Credenciais SMTP armazenadas sem criptografia.
- Uploads com validação insuficiente e exposição direta pelo servidor estático.
- Autorização repetida manualmente nas rotas.
- Banco importado por substituição direta do arquivo em execução.
- Ausência de CSRF nos formulários mutáveis.
- Ausência de autenticação robusta nas conexões WebSocket.
- Operações relacionadas executadas sem uma fronteira transacional explícita.
- Ausência de constraints, relacionamentos e índices relacionais no banco.

As credenciais encontradas no código de origem devem ser consideradas comprometidas e trocadas durante a implantação.

## 5. Abordagens consideradas

### 5.1 Monólito modular por domínio — escolhida

Mantém uma implantação única e separa responsabilidades por áreas do negócio. Minimiza o risco da migração, mantém o uso simples para a equipe e permite extrair serviços no futuro somente se houver necessidade comprovada.

### 5.2 Separação global por camadas — rejeitada

Pastas globais de routers, services e repositories são fáceis no início, mas misturam arquivos de todos os domínios e tornam mudanças de uma feature dispersas pelo repositório.

### 5.3 Reescrita ou microsserviços — rejeitada

Elevaria o custo operacional, exigiria observabilidade e coordenação distribuída e aumentaria o risco de perda de comportamento sem benefício proporcional ao porte atual.

## 6. Arquitetura escolhida

```text
sist-ionm/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── shared/
│   │   ├── documents/
│   │   ├── storage/
│   │   └── web/
│   └── modules/
│       ├── identity/
│       ├── portal/
│       ├── chat/
│       ├── catalog/
│       ├── crm/
│       ├── sales/
│       ├── finance/
│       ├── reporting/
│       └── administration/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── characterization/
│   └── migration/
├── scripts/
├── deploy/
├── docs/
├── pyproject.toml
├── compose.yaml
├── .env.example
└── README.md
```

### 6.1 Regra interna dos módulos

Cada módulo conterá somente os arquivos necessários dentre estes:

- `router.py`: contrato HTTP, leitura de formulário, respostas e redirecionamentos.
- `service.py`: casos de uso, regras de negócio e fronteiras transacionais.
- `repository.py`: consultas e persistência SQLAlchemy específicas do domínio.
- `models.py`: modelos SQLAlchemy pertencentes ao domínio.
- `schemas.py`: contratos Pydantic de entrada e saída.
- `dependencies.py`: dependências FastAPI específicas do domínio, quando existirem.
- `templates/<dominio>/`: templates Jinja2 da feature.
- `static/<dominio>/`: JavaScript ou CSS exclusivo da feature.

Routers não executarão SQL nem conterão cálculos de negócio. Repositórios não conhecerão `Request`, templates ou regras de apresentação. Serviços não dependerão de detalhes de HTML.

### 6.2 Responsabilidade dos domínios

| Domínio | Responsabilidade |
|---|---|
| `identity` | Login, sessão, usuários, perfis, papéis e permissões |
| `portal` | Feed, perfil público e organograma |
| `chat` | Salas, mensagens, notificações e WebSockets |
| `catalog` | Produtos e fornecedores |
| `crm` | Clientes, oportunidades, itens, notas e documentos |
| `sales` | Pedidos, fechamentos comerciais e comissões |
| `finance` | Recebíveis, pagáveis, custos e lançamentos financeiros |
| `reporting` | BI, relatórios de vendedores, PDFs e exportações |
| `administration` | Configurações, e-mail, backup, restauração e informações do servidor |

### 6.3 Fluxo de uma requisição

```text
Nginx
  → router FastAPI
  → autenticação/autorização e validação
  → service do domínio
  → repository do domínio
  → sessão SQLAlchemy
  → PostgreSQL
```

Erros esperados serão convertidos em exceções de domínio. Um handler central escolherá entre resposta HTML, redirecionamento ou JSON sem expor stack traces ao usuário.

## 7. Aplicação FastAPI

`app/main.py` exporá uma função `create_app()` e a instância ASGI. O arquivo será responsável somente por:

1. carregar configurações;
2. configurar logs e middlewares;
3. registrar handlers de erro;
4. montar assets compartilhados;
5. incluir os routers dos domínios;
6. registrar os eventos de ciclo de vida.

A criação de tabelas e dados padrão não ocorrerá no `startup`. Estrutura será responsabilidade do Alembic; dados iniciais serão criados por comandos administrativos explícitos.

## 8. PostgreSQL e modelo de persistência

### 8.1 Decisões

- SQLAlchemy 2 será a camada de persistência.
- Psycopg 3 será o driver PostgreSQL.
- Alembic será a única forma de alterar schema após a baseline.
- Valores monetários usarão `NUMERIC`, nunca ponto flutuante.
- Datas e horários usarão tipos `DATE` e `TIMESTAMP WITH TIME ZONE` conforme o significado.
- Estados Sim/Não serão convertidos para booleanos quando forem verdadeiramente binários.
- Status permanecerão strings com constraints, evitando enums PostgreSQL rígidos nesta fase.
- Relacionamentos terão chaves estrangeiras e políticas `RESTRICT`, `SET NULL` ou `CASCADE` definidas por caso de uso.
- Consultas frequentes por status, data, usuário, oportunidade e pedido receberão índices explícitos.

### 8.2 Transações

Cada caso de uso mutável terá uma transação controlada pelo serviço. Exemplo: converter oportunidade em pedido, criar fechamento e lançar contas será uma operação atômica. Falha em qualquer etapa fará rollback integral.

### 8.3 Migração SQLite para PostgreSQL

O processo será implementado em `scripts/migrate_sqlite_to_postgres.py` e seguirá esta ordem:

1. abrir o SQLite original em modo somente leitura;
2. executar verificação de integridade;
3. auditar registros órfãos e valores incompatíveis;
4. aplicar a baseline Alembic em um PostgreSQL vazio;
5. carregar tabelas na ordem de dependência, preservando IDs;
6. converter datas, booleanos e valores numéricos;
7. preservar hashes de senha legados para atualização gradual;
8. ajustar sequences PostgreSQL após preservar IDs;
9. comparar contagens por tabela;
10. validar relacionamentos, usuários, totais financeiros e amostras funcionais;
11. gerar relatório JSON sem dados sensíveis;
12. concluir a transação somente se todas as validações passarem.

O SQLite não será alterado nem removido. A migração poderá ser repetida em um PostgreSQL vazio e recusará execução sobre banco com dados, salvo opção administrativa explícita.

## 9. Segurança

- `SESSION_SECRET`, conexão PostgreSQL, chave de criptografia e demais segredos virão de variáveis de ambiente.
- `.env` nunca será versionado; `.env.example` conterá somente nomes e exemplos não sensíveis.
- Não haverá usuário ou senha padrão no código.
- Um comando administrativo criará o primeiro usuário administrador.
- Novas senhas usarão Argon2. Hashes PBKDF2 legados serão aceitos temporariamente e atualizados para Argon2 após login válido.
- Comparações de credenciais usarão funções resistentes a timing attacks.
- Formulários mutáveis terão token CSRF.
- Cookies de sessão terão `HttpOnly`, `SameSite` e configuração `Secure` controlada pelo ambiente.
- Permissões serão verificadas por dependências FastAPI reutilizáveis.
- WebSockets validarão sessão e acesso à sala antes do `accept`.
- Uploads terão limite de tamanho, extensões e MIME types permitidos, nome aleatório e armazenamento fora da rota estática pública.
- Downloads privados passarão por endpoint autenticado e autorizado.
- Credenciais SMTP serão criptografadas em repouso com chave externa ao banco.
- Logs mascararão senhas, tokens, cookies e credenciais SMTP.
- Importações de backup exigirão perfil administrativo, validação de formato e confirmação operacional.

## 10. Tratamento de erros e observabilidade

- Exceções de domínio representarão `not found`, conflito, validação, acesso negado e regra de negócio.
- Erros inesperados receberão identificador de correlação e serão registrados com contexto técnico seguro.
- Usuários receberão mensagens compreensíveis, sem detalhes internos.
- Logs serão estruturados e enviados para `stdout`, permitindo coleta pelo Docker.
- Nginx e aplicação terão endpoints de saúde separados.
- A auditoria de ações administrativas e financeiras será mantida no banco.
- O servidor usará timezone `America/Sao_Paulo`; timestamps persistidos serão normalizados para UTC quando representarem instantes.

## 11. Implantação em Ubuntu

### 11.1 Serviços Docker Compose

- `web`: aplicação FastAPI em imagem Python 3.13 slim, executada por usuário sem privilégios.
- `db`: PostgreSQL com volume persistente e health check.
- `nginx`: proxy reverso e ponto de entrada da rede local.
- `migrate`: serviço executado sob demanda para aplicar Alembic antes da atualização da aplicação.

O PostgreSQL não publicará porta na rede do servidor. Apenas os containers autorizados acessarão a rede interna do banco.

### 11.2 Persistência

- Volume do PostgreSQL.
- Volume de uploads privados.
- Volume de PDFs e exportações.
- Diretório de backups fora do volume principal do banco.

### 11.3 Operação

- Health checks e política de reinício automático.
- Script de instalação idempotente para Ubuntu.
- Backup com `pg_dump`, retenção documentada e teste de restauração.
- Atualização com backup, migração Alembic, subida dos serviços e smoke test.
- Rollback de aplicação documentado; migrações destrutivas exigirão estratégia expand/contract.

## 12. Estratégia de testes

### 12.1 Caracterização

Antes de extrair cada domínio, testes registrarão o comportamento observável das rotas e funções críticas atuais. Esses testes permitirão refatorar sem alterar os fluxos aprovados.

### 12.2 Pirâmide de testes

- Unitários: serviços, cálculos, autorização e conversões.
- Integração: repositories contra PostgreSQL real descartável.
- HTTP: rotas, formulários, sessões, CSRF e respostas.
- WebSocket: autenticação, autorização, mensagens e desconexão.
- Migração: fixture SQLite representativa migrada e validada.
- Smoke: login, dashboard, oportunidade, pedido, financeiro, relatório e chat após deploy.

### 12.3 Critérios de qualidade

- Cobertura mínima geral: 80%.
- Cobertura mínima em autenticação, autorização e regras financeiras: 90%.
- Ruff sem erros.
- Verificação estática de tipos sem erros nos módulos novos.
- Testes e build Docker executados antes de integrar cada etapa.

## 13. Dependências

Versões candidatas consultadas no registro oficial PyPI em 2026-06-17:

| Pacote | Origem | Candidata |
|---|---:|---:|
| FastAPI | 0.115.6 | 0.137.1 |
| Uvicorn | 0.32.1 | 0.49.0 |
| Jinja2 | 3.1.4 | 3.1.6 |
| python-multipart | 0.0.17 | 0.0.32 |
| ItsDangerous | 2.2.0 | 2.2.0 |
| ReportLab | 4.2.5 | 4.5.1 |
| OpenPyXL | 3.1.5 | 3.1.5 |
| SQLAlchemy | ausente | 2.0.51 |
| Alembic | ausente | 1.18.4 |
| Psycopg | ausente | 3.3.4 |
| pydantic-settings | ausente | 2.14.1 |
| pytest | ausente | 9.1.0 |

As candidatas não serão adotadas cegamente. O lock final registrará apenas combinações aprovadas pelos testes, pelo build e pela execução com Python 3.13.

## 14. Documentação para manutenção

- `README.md`: propósito, requisitos e início rápido.
- `docs/architecture.md`: limites de domínio, dependências e fluxo da aplicação.
- `docs/file-map.md`: mapa de arquivos, responsabilidades e pontos de extensão.
- `docs/database.md`: entidades, relacionamentos, constraints e migrações.
- `docs/setup-ubuntu.md`: preparação e instalação do servidor.
- `docs/development.md`: ambiente local, comandos, testes e padrões.
- `docs/migration-guide.md`: execução e validação SQLite → PostgreSQL.
- `docs/runbook.md`: deploy, backup, restauração, logs e incidentes.
- `docs/decisions/`: registros curtos das decisões arquiteturais e justificativas.

Os documentos registrarão decisões e justificativas verificáveis, sem depender de conhecimento informal ou de raciocínio não documentado da equipe.

## 15. Sequência de migração do código

1. Criar proteção do repositório, configuração, testes base e aplicação factory.
2. Criar schema PostgreSQL, Alembic e infraestrutura de testes.
3. Construir e validar a migração do SQLite.
4. Extrair `identity` e centralizar segurança.
5. Extrair `catalog` e `crm`.
6. Extrair `sales` e `finance`.
7. Extrair `portal` e `chat`.
8. Extrair `reporting` e `administration`.
9. Reorganizar templates e assets sem alterar a apresentação.
10. Finalizar Docker Compose, Nginx, backup e documentação.
11. Executar migração ensaiada, testes completos e homologação.

Cada etapa deverá terminar com software executável e testes verdes. A extração será incremental; não haverá uma reescrita única do arquivo monolítico.

## 16. Critérios de aceitação

- As URLs e os fluxos atuais continuam disponíveis.
- `app/main.py` contém somente composição da aplicação e possui no máximo 100 linhas.
- Nenhum router executa SQL ou cálculo de negócio.
- Execução normal não importa `sqlite3` nem depende do arquivo SQLite.
- PostgreSQL mantém os dados após reinício dos containers.
- A migração preserva todas as linhas válidas e produz relatório de validação.
- Chaves estrangeiras, constraints e índices essenciais existem no PostgreSQL.
- Não há credenciais ou chaves reais nos arquivos versionados.
- Uploads e downloads privados exigem validação e autorização.
- Testes, lint, tipos e build Docker passam nos comandos documentados.
- Cobertura atende aos limites definidos.
- Um Dev Junior consegue iniciar o ambiente local e instalar no Ubuntu seguindo apenas a documentação.
- Backup e restauração PostgreSQL são executados e comprovados em ambiente de teste.

## 17. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Comportamento oculto no monólito | Testes de caracterização antes de cada extração |
| Dados órfãos no SQLite | Auditoria prévia, relatório e regras explícitas de correção |
| Upgrade simultâneo de muitas bibliotecas | Atualizações em pequenos grupos com lock e testes |
| Quebra de templates ao mover arquivos | Preservar nomes de contexto e adicionar testes HTTP/renderização |
| Incompatibilidade de hashes antigos | Verificação legada isolada e rehash gradual após login |
| Migração irreversível | SQLite somente leitura, backup PostgreSQL e ensaio completo |
| Complexidade para o Dev Junior | Convenções repetíveis, mapa de arquivos e comandos documentados |

## 18. Decisão final

A solução será um monólito modular por domínio, com PostgreSQL, SQLAlchemy, Alembic e implantação Docker Compose em Ubuntu. A mudança será incremental, test-first e orientada à preservação do comportamento atual. Microsserviços e redesenho de interface ficam explicitamente adiados até existir necessidade comprovada.
