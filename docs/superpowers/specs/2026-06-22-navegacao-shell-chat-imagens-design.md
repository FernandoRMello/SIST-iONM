# Navegação persistente do shell e imagens no chat

Data: 22/06/2026

## Objetivo

Manter menu lateral, topbar e chat montados durante a navegação pelo menu principal, substituindo somente o conteúdo central. Exibir anexos de imagem diretamente nas mensagens, com abertura da imagem completa por clique.

## Escopo

- Interceptar somente links com `data-nav-item` no menu lateral.
- Manter formulários, downloads, links de tabelas, links de detalhe e ações rápidas com navegação tradicional.
- Preservar o estado visual do menu e a conexão WebSocket do chat entre páginas.
- Atualizar conteúdo central, título do documento, título da topbar, breadcrumb, URL e item ativo.
- Suportar os controles Voltar e Avançar do navegador.
- Exibir miniaturas para PNG, JPG/JPEG, WebP e GIF.
- Manter documentos e demais formatos permitidos como links de anexo.

## Arquitetura

### Navegação progressiva

Um módulo isolado `shell-navigation.js` observará cliques no menu por delegação de eventos. O módulo somente assumirá cliques primários, sem teclas modificadoras, em links HTTP do mesmo host. A URL será solicitada com `fetch` e credenciais da mesma origem.

A resposta HTML será analisada com `DOMParser`. Antes da troca, o módulo verificará a presença de `#main-content` e do shell autenticado. Uma resposta de login, uma resposta sem o contrato esperado ou uma falha de rede acionará `window.location.assign()`, preservando o comportamento tradicional.

Os estilos específicos encontrados na resposta serão carregados antes da troca do conteúdo. Scripts de página ainda não presentes serão carregados uma única vez. Após a substituição, o módulo emitirá `sistionm:content-updated`, permitindo inicializadores idempotentes em `forms.js` e `tables.js`.

O shell permanecerá intacto. Somente `#main-content` terá seus filhos substituídos. O título da topbar e o breadcrumb serão atualizados em seus elementos existentes; o menu receberá `aria-current="page"` e `.is-active` de acordo com a resposta. O chat lateral, seus badges, o painel aberto e os sockets não serão recriados.

### Histórico e concorrência

Uma navegação concluída usará `history.pushState`. O evento `popstate` fará a mesma atualização sem adicionar nova entrada. Durante a solicitação, `#main-content` receberá `aria-busy="true"` e uma classe de carregamento.

Cada nova navegação abortará a solicitação anterior com `AbortController`. Somente a resposta mais recente poderá alterar a tela. Ao concluir, o conteúdo receberá foco para leitores de tela e navegação por teclado.

### Inicialização das telas

`forms.js` e `tables.js` continuarão funcionando na carga tradicional e também responderão a `sistionm:content-updated`. Cada elemento marcado terá `data-ready` para impedir listeners duplicados. `feedback.js` já usa delegação no documento e não exige reinicialização.

O carregamento tradicional continua sendo o contrato principal do servidor. A navegação progressiva é uma melhoria opcional: sem JavaScript, todas as URLs continuam funcionais.

## Imagens no chat

O backend aceitará GIF além dos formatos de imagem já permitidos, mantendo o limite de 10 MiB, nome físico aleatório, autorização da sala antes da leitura e bloqueio de formatos ativos como SVG e HTML.

Na montagem segura da mensagem, `chat_realtime.js` verificará a extensão do caminho controlado pelo servidor. Para PNG, JPG/JPEG, WebP e GIF, criará um link seguro contendo uma miniatura com carregamento preguiçoso. O clique abrirá o arquivo em nova aba com `rel="noopener"`. Outros anexos continuarão como `Abrir anexo`.

O template Jinja da tela completa aplicará a mesma regra por uma informação booleana `attachment_is_image` preparada pelo backend. Nenhum HTML fornecido por usuário será executado ou inserido dinamicamente.

## Estados e tratamento de erros

- Navegação em andamento: conteúdo central com `aria-busy="true"` e feedback visual discreto.
- Resposta inválida, redirecionamento para login ou falha de rede: navegação tradicional para a URL solicitada.
- Asset específico com falha: navegação tradicional, evitando tela parcialmente inicializada.
- Arquivo de imagem inválido por extensão ou tamanho: resposta de erro já apresentada no status acessível do chat.
- Imagem que não puder ser renderizada: o link continua acessível e pode ser aberto diretamente.

## Acessibilidade e segurança

- Links continuam links reais com `href`.
- Foco vai para `#main-content` após uma troca bem-sucedida.
- `aria-current`, breadcrumb e título são mantidos sincronizados.
- Não são interceptados Ctrl/Cmd+clique, Shift+clique, clique do meio, links externos ou downloads.
- Conteúdo das mensagens permanece construído por DOM seguro e `textContent`.
- SVG, HTML, JavaScript e executáveis não são aceitos como anexos de chat.
- A dívida conhecida de CSRF por token permanece registrada no workstream de identidade/backend.

## Testes

- Contrato do shell para presença e carregamento versionado de `shell-navigation.js`.
- Testes JavaScript do módulo com DOM mínimo para interceptação, atualização central, histórico, fallback e preservação dos nós do shell/chat.
- Regressão dos inicializadores idempotentes de formulários e tabelas.
- Contrato do chat para miniatura segura de imagem e link comum para documentos.
- Teste HTTP para upload GIF permitido, limite de tamanho, nome aleatório e entrega em tempo real.
- Gate completo: pytest, Ruff, sintaxe de todos os JavaScripts e `git diff --check`.

## Fora de escopo

- Reescrever o sistema como SPA em React/Vue.
- Interceptar submissões de formulário ou todos os links internos.
- Persistir rascunhos de formulários durante a troca de página.
- Galeria, edição, compressão ou processamento de imagens no servidor.
- Alterar autenticação, sessão, banco de dados ou rotas públicas.
