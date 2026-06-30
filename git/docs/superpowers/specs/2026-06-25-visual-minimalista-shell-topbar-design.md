# Visual minimalista, shell com topbar útil e telas menos poluídas

## Objetivo

Redesenhar a camada visual do SIST-iONM para ficar mais limpa, profissional e confortável de usar em tela cheia ou notebook. A mudança deve reduzir peso visual, melhorar leitura, aproveitar melhor o espaço central e preparar uma barra superior mais útil sem perder o menu lateral, o chat, as notificações e os atalhos principais.

## Problemas observados

- Gradientes e sombras deixam a interface mais pesada do que o necessário.
- Cards, inputs e botões ocupam muita altura, fazendo as telas parecerem apertadas.
- Algumas páginas têm excesso de elementos competindo visualmente.
- A topbar atual mostra contexto, mas ainda não funciona como área forte de navegação e ação.
- O menu lateral está funcional, mas visualmente dominante.
- O centro da tela precisa ficar mais limpo e com melhor respiro.
- O chat e notificações precisam continuar persistentes e fixos.

## Direção visual aprovada

### Estilo geral

- Fundo neutro, claro e menos azulado.
- Menos gradientes; usar cor sólida na maior parte dos componentes.
- Sombras mais discretas, reservadas apenas para popovers, chat e elementos flutuantes.
- Cards com borda sutil, menos padding e menor altura.
- Cantos levemente arredondados, porém sem aparência “inflada”.
- Tipografia com hierarquia clara: título, subtítulo, seção, campo e tabela.
- Tabelas com cabeçalho mais limpo, linhas mais compactas e hover discreto.

### Inputs, selects e formulários

- Altura padrão menor para campos: aproximadamente 38-40px, mantendo acessibilidade.
- Labels menores e com peso visual moderado.
- Espaçamento interno consistente.
- Inputs e selects com borda clara, foco visível e sem sombra forte.
- Formulários longos devem ser organizados em grupos lógicos.
- Campos relacionados devem ficar próximos, mas com respiro suficiente.
- Evitar campos abertos quando houver lista conhecida ou cadastro relacionado.

### Botões

- Botões primários com cor sólida, sem gradiente.
- Botões secundários com fundo branco/neutro e borda sutil.
- Menos altura e sombra.
- Ação principal por tela deve ficar clara.
- Atalhos globais devem morar na topbar quando fizer sentido.

## Shell e navegação

### Menu lateral

Manter o menu lateral atual, porém mais discreto:

- reduzir contraste pesado do gradiente;
- diminuir sombra;
- links com estado ativo mais limpo;
- grupos com menos ruído;
- preservar busca no menu;
- preservar modo recolhido.

### Barra superior

Criar uma topbar mais forte e útil:

- manter breadcrumb/título, porém mais compacto;
- adicionar área preparada para busca global futura;
- manter atalhos principais como “Novo cliente” e “Nova R.O.”;
- manter notificações;
- manter perfil do usuário;
- manter integração com chat/notificações;
- em telas menores, esconder textos longos e preservar ícones/ações essenciais.

### Chat, notificações e usuário

- Chat rail continua fixo.
- Badges continuam visíveis.
- Sino e perfil continuam fixos na topbar.
- Topbar não deve sobrepor ou quebrar o chat flutuante.
- Navegação central continua trocando apenas o conteúdo, sem desmontar shell e chat.

## Layout central

- Reduzir padding vertical exagerado.
- Usar largura central mais bem distribuída.
- Melhorar espaçamento entre cabeçalho, cards e tabelas.
- Evitar telas com “muitos blocos grudados”.
- Em dashboards, cards devem ser mais horizontais, leves e escaneáveis.
- Em formulários, priorizar grupos compactos e coerentes.

## Relações e campos que serão revisados

Esta etapa visual também deve preparar a revisão dos campos abertos. A implementação deve identificar e corrigir campos que deveriam ser lista ou vínculo.

### Revisões prioritárias

- RH:
  - cargo;
  - departamento;
  - tipo de contrato;
  - status;
  - colaborador vendedor;
  - comissão padrão;
  - benefício e regras de comissão.

- Financeiro:
  - categoria de custo;
  - centro de custo;
  - fornecedor/vendedor em custos;
  - status de contas;
  - vínculo com pedido quando existir.

- Configurações/usuários:
  - perfil legado;
  - perfis configuráveis;
  - vendedor vinculado;
  - status.

- CRM/Pedidos:
  - cliente;
  - fornecedor;
  - vendedor;
  - status;
  - produtos;
  - condições relacionadas a pedido/oportunidade.

## Critérios de aceite

- Interface visualmente mais limpa e menos pesada.
- Cards e campos ocupam menos altura.
- Topbar fica mais útil, com espaço para busca global futura.
- Menu lateral permanece, mas mais discreto.
- Chat, notificações e perfil continuam fixos e funcionais.
- Conteúdo central ganha mais respiro e melhor aproveitamento.
- Nenhum template pode usar CDN, handler inline ou asset remoto.
- Nenhum teste de acessibilidade, shell, navegação ou renderização deve quebrar.
- A mudança deve preservar as rotas e formulários existentes.

## Fora do escopo desta etapa

- Implementar busca global funcional completa.
- Trocar completamente para navegação horizontal.
- Remover o menu lateral.
- Reescrever regras de negócio.
- Criar novo módulo de cadastro de departamentos/cargos, salvo se já existir base pronta e a mudança for simples.

## Plano de implementação posterior

1. Ajustar tokens visuais globais.
2. Refinar `layout.css` para topbar, menu lateral e conteúdo central.
3. Refinar `components.css` para cards, botões, inputs, selects e tabelas.
4. Ajustar CSS de módulos que estiverem destoando: administração, CRM, financeiro, portal e RH.
5. Revisar templates com formulários mais poluídos.
6. Corrigir campos abertos prioritários para selects quando os dados já existirem.
7. Atualizar testes visuais/contratos, se necessário.
8. Rodar gate completo.

## Riscos e cuidados

- Reduzir altura dos campos sem perder acessibilidade.
- Não esconder informações importantes em telas menores.
- Não quebrar a navegação persistente do shell.
- Não interferir no painel de chat.
- Evitar mexer em muitas regras de negócio junto com o redesenho visual.
