# SIST-iONM — Redesign Profissional, Otimização e Auditoria das 18 Telas

**Data:** 2026-06-17

**Versão de origem:** `SIST-iONM_V2_6_CHAT_BITRIX_NOTIFICACOES`

**Direção visual:** corporativo premium

**Estratégia frontend:** FastAPI + Jinja2 + CSS/JavaScript próprios, sem SPA ou dependências externas
**Status:** desenho aprovado em conversa

## 1. Objetivo

Redesenhar integralmente as 18 superfícies HTML do SIST-iONM, profissionalizar a estrutura por domínio, reduzir o número de cliques para tarefas recorrentes, melhorar a velocidade das páginas e corrigir bugs funcionais, visuais e de segurança encontrados durante a auditoria.

A entrega será uma única versão homologável. A implementação interna será incremental para preservar as URLs, regras de negócio e dados atuais.

## 2. Escopo

O escopo cobre os 18 templates existentes e todas as variações de rota que eles atendem:

1. `base.html`: shell autenticado, sidebar, topbar, navegação e chat global.
2. `login.html`: autenticação.
3. `dashboard.html`: painel comercial.
4. `bi_gerencial.html`: inteligência gerencial.
5. `feed.html`: portal/feed interno.
6. `chat.html`: chat completo.
7. `profile.html`: perfil do usuário.
8. `orgchart.html`: organograma.
9. `crud.html`: clientes, fornecedores, produtos e vendedores.
10. `opportunities.html`: pipeline e lista de oportunidades.
11. `opportunity_card.html`: card completo da oportunidade.
12. `orders.html`: pedidos e fechamento.
13. `purchases.html`: compras.
14. `commissions.html`: comissões.
15. `finance.html`: recebíveis, pagáveis e custos.
16. `seller_reports.html`: relatórios de vendedores.
17. `settings.html`: configurações e usuários.
18. `permissions.html`: permissões por perfil.

Também estão no escopo os assets compartilhados, chat em tempo real, relatórios/PDFs ligados às telas, consultas usadas para renderização, instalação local e documentação técnica.

## 3. Restrições

- Preservar as URLs existentes.
- Preservar os fluxos e regras de negócio válidos.
- Manter renderização server-side com FastAPI e Jinja2.
- Não introduzir React, SPA, Tailwind, Node.js ou CDN.
- Não depender de fontes, ícones ou scripts externos.
- Manter compatibilidade com desktop, tablet e celular.
- Continuar a arquitetura modular por domínio aprovada anteriormente.
- Não reescrever o histórico Git sem autorização específica.
- Não alterar nem apagar o SQLite de origem durante a migração.

## 4. Diagnóstico visual e estrutural

### 4.1 Interface atual

- CSS monolítico com 647 linhas organizadas como correções incrementais por versão.
- Tokens visuais insuficientes e valores de cor/espaçamento repetidos.
- Emojis usados como ícones de navegação.
- Eventos JavaScript inline nos templates.
- Sidebar sem estado ativo consistente e com alta densidade de opções.
- Tabelas largas que dependem principalmente de rolagem horizontal no celular.
- Componentes semelhantes com marcação e comportamento inconsistentes.
- Hierarquia visual variável entre dashboard, BI, cadastros e administração.
- Chat global visualmente forte, competindo com o conteúdo principal.
- Estados vazios, carregamento, erro e confirmação pouco padronizados.

### 4.2 Estrutura atual

- `app/main.py` concentra rotas, persistência, regras, autenticação, relatórios e WebSockets.
- Templates ficam em uma pasta única e não possuem macros/componentes compartilhados.
- `style.css` e `chat_realtime.js` acumulam responsabilidades.
- Consultas de resumo executam buscas repetidas por item em alguns fluxos.
- Listagens não possuem paginação server-side consistente.
- Instalação e dependências estão em transição para `pyproject.toml` e lock reproduzível.

## 5. Abordagens avaliadas

### 5.1 Design system próprio sobre Jinja2 — escolhida

Preserva a aplicação server-side, reduz riscos e produz assets leves. Macros Jinja, CSS modular e JavaScript progressivo tornam os componentes reutilizáveis sem exigir outra plataforma de frontend.

### 5.2 Tailwind com etapa de build — rejeitada

Entregaria consistência visual, mas adicionaria Node.js, compilação e conhecimento operacional desnecessários para o contexto atual.

### 5.3 React/SPA — rejeitada

Exigiria reescrever o frontend, criar APIs adicionais e manter dois contratos de aplicação. O custo e risco não se justificam para a meta desta entrega.

## 6. Linguagem visual

### 6.1 Personalidade

O sistema deve parecer uma ferramenta corporativa confiável e contemporânea: sóbria, clara e rápida. O visual não deve imitar um dashboard genérico nem usar gradientes decorativos em excesso.

### 6.2 Paleta

```css
--color-navy-950: #081426;
--color-navy-900: #0d1d33;
--color-navy-800: #142a46;
--color-teal-600: #0f8b8d;
--color-teal-500: #14a3a5;
--color-blue-600: #2563eb;
--color-surface: #ffffff;
--color-canvas: #f4f7fb;
--color-text: #172033;
--color-muted: #667085;
--color-border: #dfe6ef;
--color-success: #16865b;
--color-warning: #b76a00;
--color-danger: #c63d4f;
--color-info: #2563eb;
```

Teal representa ação principal e progresso. Azul é reservado a informação e links. Verde, amarelo e vermelho comunicam significado semântico, não decoração.

### 6.3 Tipografia e espaçamento

- Stack local: `Inter`, `Segoe UI`, `Roboto`, `Helvetica Neue`, Arial, sans-serif; nenhuma fonte será baixada.
- Escala tipográfica: 12, 14, 16, 20, 24 e 32 px.
- Escala espacial: 4, 8, 12, 16, 24, 32 e 48 px.
- Altura mínima de controles: 40 px no desktop e 44 px no touch.
- Texto normal com contraste WCAG AA mínimo de 4,5:1.
- Títulos com line-height 1,2; corpo com line-height entre 1,45 e 1,6.

### 6.4 Forma e profundidade

- Raios: 8 px para inputs, 10 px para botões, 12 px para cards e 999 px apenas para badges.
- Sombras discretas e usadas somente para elevação real, como dropdown, drawer e chat.
- Cards comuns usam borda e superfície; não usam sombras grandes.
- Uma ação primária por região visual.

## 7. Shell e navegação

### 7.1 Sidebar

- Largura expandida de 256 px e recolhida de 72 px.
- Identidade SIST-iONM no topo com estado compacto legível.
- Grupos: Visão geral, Relacionamento, Operação, Financeiro e Administração.
- Item ativo baseado na rota atual.
- Ícones SVG locais de 20 px com `aria-hidden` quando decorativos.
- Labels e tooltips acessíveis no modo recolhido.
- Preferência de recolhimento salva em `localStorage`.
- Mobile usa drawer com backdrop, bloqueio de scroll e fechamento por Escape.

### 7.2 Topbar

- Breadcrumb e título contextual.
- Busca rápida de destinos de menu, acionável por teclado.
- Ações rápidas “Nova R.O.” e “Novo cliente”.
- Notificações e perfil em controles separados.
- Menu de perfil com identificação, configurações permitidas e logout.

### 7.3 Chat global

- Rail visualmente reduzido e alinhado aos tokens.
- Badge de não lidas permanece visível sem animações contínuas.
- Painel usa drawer lateral no desktop e tela quase integral no mobile.
- Estados de conexão, reconexão e erro são explícitos.
- Chat não deve reduzir a área clicável nem sobrepor ações principais.

## 8. Design system e componentes

Os componentes serão implementados como macros Jinja, partials, classes CSS e módulos JavaScript progressivos.

### 8.1 Componentes estruturais

- `page_header`: breadcrumb, título, descrição e ações.
- `content_section`: agrupamento semântico com título opcional.
- `toolbar`: busca, filtros, ações e contagem de resultados.
- `split_layout`: conteúdo principal e painel de contexto.
- `drawer` e `modal`: edição rápida e confirmações.

### 8.2 Dados

- `stat_card`: ícone, label, valor e contexto/tendência.
- `data_table`: ordenação declarativa, cabeçalho fixo e responsividade.
- `pagination`: primeira/anterior/próxima/última e total.
- `status_badge`: mapeamento semântico único.
- `progress_bar`: probabilidade e evolução.
- `empty_state`: mensagem, explicação e ação.

### 8.3 Formulários e feedback

- `form_field`, `form_section` e `form_actions`.
- Labels sempre visíveis; placeholder não substitui label.
- Ajuda e erro associados por `aria-describedby`.
- `alert`, `toast`, `skeleton`, `spinner` e erro inline.
- Estados default, hover, focus-visible, active, disabled, loading e error.
- Confirmação obrigatória para ações destrutivas.

## 9. Redesign por superfície

### 9.1 Base e login

- Shell elimina handlers inline e expõe navegação acessível.
- Login usa layout institucional em duas zonas no desktop e card único no mobile.
- Mensagens de erro não deslocam abruptamente o formulário.
- Campo de senha permite exibir/ocultar e informa estado de Caps Lock quando disponível.

### 9.2 Dashboard e BI

- KPIs organizados por prioridade: pipeline, resultado e compromissos.
- Valores sensíveis usam controle acessível com estado persistido na sessão do navegador.
- Tabelas exibem somente colunas essenciais; detalhes ficam em link/contexto.
- BI mantém impressão, mas separa cenário, indicadores e recomendações.
- Gráficos serão CSS/SVG local quando agregarem informação; não haverá biblioteca externa.

### 9.3 Portal, perfil, organograma e chat

- Feed ganha composer claro, cards de publicação e estados vazios.
- Perfil separa identidade, contato e preferências.
- Organograma usa hierarquia visual e fallback tabular acessível.
- Chat completo possui lista de conversas, cabeçalho contextual e mensagens com melhor leitura.

### 9.4 Cadastros

- `crud.html` serve clientes, fornecedores, produtos e vendedores por configuração declarativa.
- Busca e filtros ficam na toolbar.
- Formulário usa drawer no desktop e seção expansível no mobile.
- Tabela possui ações contextuais e não exibe IDs técnicos como entrada primária quando houver seleção por nome.

### 9.5 CRM e oportunidades

- Alternância lista/Kanban permanece.
- Colunas do Kanban usam cabeçalho compacto, contagem e valor agregado.
- Card apresenta cliente, status, probabilidade, valor e próxima ação.
- Movimentação não depende apenas de cor ou setas sem label.
- Card completo da oportunidade usa seções: resumo, produtos, comunicação, documentos e histórico.

### 9.6 Pedidos, compras, financeiro e comissões

- Pedidos usam cards/linhas com status fiscal e financeiro claramente separados.
- Compras compartilha toolbar e tabela do design system.
- Financeiro possui abas ou segmentos para receber, pagar e custos sem carregar conteúdo duplicado.
- Totais permanecem visíveis em barra-resumo.
- Comissões apresenta período, situação, vendedor e valor com filtros server-side.

### 9.7 Relatórios e administração

- Relatórios de vendedor separam filtros, resumo, tabela e avaliação.
- Configurações são divididas em navegação lateral interna: empresa, usuários, e-mail, impressão e dados.
- Senhas SMTP nunca retornam preenchidas no HTML.
- Permissões usam matriz legível com cabeçalho fixo e agrupamento por módulo.

## 10. Estrutura de arquivos

```text
app/
├── core/
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── logging.py
│   └── security.py
├── shared/
│   └── web/
│       ├── templates/
│       │   ├── layouts/
│       │   ├── components/
│       │   └── errors/
│       └── static/
│           ├── css/
│           │   ├── tokens.css
│           │   ├── reset.css
│           │   ├── layout.css
│           │   ├── components.css
│           │   └── utilities.css
│           ├── js/
│           │   ├── app-shell.js
│           │   ├── navigation.js
│           │   ├── tables.js
│           │   ├── forms.js
│           │   └── feedback.js
│           └── icons/
│               └── sprite.svg
└── modules/
    ├── identity/
    ├── portal/
    ├── chat/
    ├── catalog/
    ├── crm/
    ├── sales/
    ├── finance/
    ├── reporting/
    └── administration/
```

Cada módulo poderá possuir `router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`, `templates/<dominio>/` e `static/<dominio>/`. Arquivos serão criados somente quando houver responsabilidade real; não haverá pastas vazias para aparentar arquitetura.

## 11. Otimização de acesso e desempenho

### 11.1 Frontend

- JavaScript próprio carregado com `defer` ou `type="module"`.
- Remoção de handlers inline e inicialização por `data-*`.
- CSS base compartilhado e CSS específico carregado somente quando necessário.
- SVG sprite local para evitar dezenas de arquivos e emojis inconsistentes.
- Assets com versão de cache e headers apropriados.
- Imagens com dimensões explícitas, lazy loading e thumbnails.
- DOM reduzido em tabelas e Kanban por paginação.
- Animações limitadas a opacity/transform e respeitando `prefers-reduced-motion`.

### 11.2 Backend e banco

- Eliminar N+1 em dashboard, oportunidades, pedidos, relatórios e chat.
- Agregar KPIs em consultas dedicadas.
- Paginação server-side com limite padrão de 25 e máximo de 100 registros.
- Filtros validados e preservados na URL.
- Índices em status, datas, relacionamentos e campos de busca realmente usados.
- Cache curto para configurações e permissões, com invalidação explícita após alteração.
- Transações para operações compostas.
- Conexões gerenciadas por sessão/unidade de trabalho após o cutover PostgreSQL.

### 11.3 Metas mensuráveis

- Resposta server-side de páginas comuns: até 500 ms em ambiente local aquecido.
- Dashboard: até 800 ms com base de homologação.
- Primeira carga sem assets externos.
- Mudanças de layout cumulativas minimizadas por dimensões declaradas.
- Listagens limitadas a 100 registros por resposta.
- Nenhuma consulta SQL executada dentro de loop de renderização.

## 12. Auditoria e correção de bugs

### 12.1 Funcionais

- Verificar as 67 rotas registradas e os dois endpoints WebSocket.
- Testar login, logout, sessão e expiração.
- Testar CRUDs, oportunidade, pedido, fechamento e lançamentos.
- Testar filtros, paginação, impressão, exportação e PDFs.
- Testar chat geral/privado, notificações, reconexão e acesso à sala.
- Testar backup/importação somente com fluxo seguro e validado.

### 12.2 Segurança e consistência

- Remover chave de sessão e credenciais fixas do código de execução.
- Não reescrever histórico Git nesta entrega sem nova autorização.
- Retirar regras de acesso ligadas a username específico.
- Centralizar autorização por perfil/permissão.
- Adicionar CSRF aos formulários mutáveis.
- Validar uploads, nomes, tamanho e MIME type.
- Não expor arquivos privados por mount estático irrestrito.
- Criptografar credenciais SMTP e nunca renderizá-las de volta.
- Trocar mutações via GET por POST onde houver compatibilidade de fluxo.

### 12.3 Visual e acessibilidade

- Detectar overflow, sobreposição e elementos inacessíveis em 1280, 1024, 768, 390 e 360 px.
- Garantir navegação por teclado e foco visível.
- Verificar labels, nomes acessíveis e mensagens associadas.
- Não depender somente de cor para status.
- Validar impressão das telas que oferecem esse recurso.

## 13. Erros, estados e logs

- Exceções de domínio para não encontrado, conflito, validação, autorização e regra de negócio.
- Páginas 400, 403, 404, 409, 422 e 500 coerentes com o design system.
- Erros inesperados com identificador de correlação e log estruturado.
- Mensagens amigáveis sem stack trace ou conteúdo sensível.
- Rollback transacional em falhas de operações compostas.
- Estados vazios e indisponibilidade de serviço não devem quebrar o layout.

## 14. Estratégia de testes

- Caracterização do comportamento atual antes de mover cada rota.
- TDD para bugs, serviços, componentes com comportamento e otimizações.
- Testes unitários para regras, filtros, paginação e autorização.
- Testes de integração com PostgreSQL para repositories e transações.
- Testes HTTP para as 18 superfícies e variações de permissão.
- Testes de HTML para semântica, labels, links, assets e ausência de handlers inline.
- Testes de WebSocket para autenticação, sala e reconexão.
- Smoke test com login, dashboard, oportunidade, pedido, financeiro, relatório e chat.
- Checklist visual manual no navegador aberto pelo usuário, pois a automação do navegador interno bloqueou o endereço local nesta sessão.

## 15. Estratégia de entrega única

A versão será entregue de uma vez, porém o trabalho seguirá gates internos:

1. caracterização e baseline;
2. design system e shell;
3. componentes e templates compartilhados;
4. migração das 18 superfícies;
5. modularização de rotas/serviços/repositories;
6. otimização de consultas e paginação;
7. correção de bugs e segurança;
8. PostgreSQL, deploy e documentação;
9. verificação completa e homologação visual.

Nenhum gate intermediário será apresentado como entrega final. A aplicação permanecerá executável ao fim de cada gate.

## 16. Critérios de aceitação

- As 18 superfícies e suas variações usam o novo design system.
- Todas as URLs atuais permanecem disponíveis ou possuem redirecionamento explícito documentado.
- Sidebar, topbar, busca de menu, atalhos e chat funcionam em desktop e mobile.
- Emojis de navegação são substituídos por SVGs locais.
- Templates não contêm handlers JavaScript inline.
- Formulários possuem labels, erros associados e foco visível.
- Listagens grandes têm busca, filtros e paginação server-side.
- Consultas N+1 identificadas são eliminadas.
- Metas de resposta local são verificadas com medição repetível.
- Credenciais e chaves não permanecem no código de execução ou HTML.
- Testes, Ruff, tipos e build passam sem erros.
- Rotas e WebSockets possuem testes de regressão.
- Impressão e PDFs continuam funcionais.
- Documentação explica arquitetura, arquivos, desenvolvimento, instalação e operação.
- O Dev Junior consegue localizar uma tela, sua rota, serviço, repository, template, assets e testes sem consultar o arquivo monolítico original.

## 17. Documentação da entrega

- `README.md`: instalação e início rápido.
- `docs/architecture.md`: módulos e fluxo.
- `docs/design-system.md`: tokens, componentes e exemplos.
- `docs/file-map.md`: localização e responsabilidade de arquivos.
- `docs/performance.md`: medições, consultas e limites.
- `docs/bug-audit.md`: bugs reproduzidos, testes e correções.
- `docs/development.md`: ambiente, testes e convenções.
- `docs/setup-ubuntu.md`: deploy local em Ubuntu.
- `docs/runbook.md`: backup, restauração, logs e incidentes.
- `docs/decisions/`: decisões técnicas e justificativas.

## 18. Decisão final

O SIST-iONM será redesenhado como uma aplicação corporativa premium, server-rendered e orientada por componentes, preservando FastAPI/Jinja2 e todas as rotas relevantes. As 18 superfícies serão incluídas na mesma entrega, enquanto a execução será internamente faseada, test-first e sustentada pela modularização por domínio, otimização de consultas, PostgreSQL e documentação completa.
