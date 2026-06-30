# Feed: reações e identidade dos autores

Data: 22/06/2026

## Objetivo

Adicionar reações positivas e negativas mutuamente exclusivas e exibir a foto de quem publicou ou comentou.

## Modelo de dados

Criar `feed_reactions` com:

- `post_id`;
- `user_id`;
- `reaction`, limitado a `like` ou `dislike`;
- `created_at`;
- restrição única `(post_id, user_id)`.

Os registros existentes de `feed_likes` serão migrados como `like` de modo idempotente. A tabela antiga será mantida temporariamente para compatibilidade, mas novas gravações usarão `feed_reactions`.

## Regras de reação

- Sem reação + 👍: cria `like`.
- Sem reação + 👎: cria `dislike`.
- 👍 + 👎 ou 👎 + 👍: atualiza a reação existente.
- Repetir a mesma reação: remove o voto.
- Cada usuário possui no máximo uma reação por publicação.

A alteração será feita por POST. A resposta redirecionará para o Feed e manterá compatibilidade com o carregamento tradicional.

## Interface

Cada publicação terá dois botões compactos:

- `👍 Curtir · N`;
- `👎 Não curtir · N`.

Os emojis serão renderizados por entidades HTML, com rótulos acessíveis completos. O estado selecionado terá `aria-pressed="true"` e contraste visual além da cor.

Publicações e comentários usarão `avatar_path` do perfil. Quando não houver foto, será exibida a inicial atual. A imagem terá texto alternativo vazio porque o nome adjacente já identifica o autor.

## Consultas e desempenho

A rota carregará contagens agregadas de like/dislike e a reação do usuário autenticado na mesma consulta, evitando N+1. Posts e comentários incluirão `avatar_path` nos joins existentes.

## Erros e segurança

- Reação inválida retorna 400.
- Post inexistente retorna 404.
- Rota exige sessão autenticada.
- Queries permanecem parametrizadas.
- Conteúdo do usuário continua escapado pelo Jinja.

## Testes

- Alternância like → dislike → removido.
- Restrição de uma reação por usuário/post.
- Contagens e `aria-pressed` no HTML.
- Foto do autor em publicação e comentário, com fallback por inicial.
- Consulta do Feed permanece dentro do orçamento definido.

