# Feed Reactions and Avatars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar 👍/👎 exclusivos e fotos de autores em posts e comentários.

**Architecture:** `feed_reactions` substitui novas gravações em `feed_likes`, com migração idempotente. A rota do feed agrega contagens, reação atual e avatar em consultas SQL sem N+1.

**Tech Stack:** FastAPI, SQLite, Jinja2, CSS, pytest.

## Global Constraints

- Um usuário possui no máximo uma reação por post.
- Repetir reação remove; reação oposta substitui.
- Reações são POST e possuem rótulos acessíveis.

---

### Task 1: Modelo e endpoint de reação

**Files:**
- Modify: `app/main.py`
- Create: `tests/web/test_feed_reactions.py`
- Modify: `tests/characterization/test_route_inventory.py`

**Interfaces:**
- Produces: POST `/feed/reaction/{post_id}/{reaction}` para `like|dislike`.

- [ ] **Step 1: Escrever testes RED**

```python
def test_reaction_toggles_and_switches(admin_client, db):
    admin_client.post(f"/feed/reaction/{post_id}/like")
    admin_client.post(f"/feed/reaction/{post_id}/dislike")
    assert reaction == "dislike"
    admin_client.post(f"/feed/reaction/{post_id}/dislike")
    assert reaction is None
```

Testar reação inválida 400 e post inexistente 404.

- [ ] **Step 2: Executar RED**

Run: `python -m pytest tests/web/test_feed_reactions.py -q`
Expected: rota ausente.

- [ ] **Step 3: Implementar schema, migração e endpoint**

Criar tabela com `UNIQUE(post_id,user_id)` e `CHECK(reaction IN ('like','dislike'))`; copiar `feed_likes` com `INSERT OR IGNORE`; implementar delete/update/insert parametrizados.

- [ ] **Step 4: Executar GREEN**

Run: `python -m pytest tests/web/test_feed_reactions.py tests/characterization/test_route_inventory.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "feat: add exclusive feed reactions"`

### Task 2: Interface e avatares

**Files:**
- Modify: `app/main.py`
- Modify: `app/templates/feed.html`
- Modify: `app/shared/web/static/css/portal.css`
- Modify: `tests/web/test_portal_pages.py`
- Modify: `tests/performance/test_query_budget.py`

**Interfaces:**
- Consumes: `likes_count`, `dislikes_count`, `current_reaction`, `avatar_path`.

- [ ] **Step 1: Escrever testes RED**

Exigir entidades `&#128077;`/`&#128078;`, `aria-pressed`, dois contadores e imagens de autor em post/comentário.

- [ ] **Step 2: Executar RED**

Run: `python -m pytest tests/web/test_portal_pages.py tests/performance/test_query_budget.py -q`
Expected: contratos ausentes.

- [ ] **Step 3: Implementar consulta e template**

Agregar reações via subconsultas correlacionadas ou CTE único, incluir `up.avatar_path`, renderizar `<form method="post">` e fallback de inicial.

- [ ] **Step 4: Executar GREEN**

Run: comando do Step 2. Expected: PASS e orçamento mantido.

- [ ] **Step 5: Commit**

`git commit -am "feat: show feed reactions and author photos"`

