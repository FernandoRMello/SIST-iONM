# Design system SIST-iONM

## Objetivo

O frontend permanece server-side com FastAPI, Jinja2, CSS e JavaScript local. Não há React, Tailwind, CDN, fonte remota ou pacote Node. A identidade visual usa azul-marinho, teal, superfícies claras e componentes `ui-*` reutilizáveis.

## Arquivos centrais

| Arquivo | Responsabilidade |
|---|---|
| `app/shared/web/static/css/tokens.css` | Cores, tipografia, espaçamento, raios, sombras, tempos, breakpoints e camadas. |
| `reset.css` | Normalização, foco visível e preferência de movimento reduzido. |
| `layout.css` | Shell, sidebar, topbar, conteúdo, drawer e chat lateral. |
| `components.css` | Botões, campos, cards, badges, tabelas, paginação, feedback, cabeçalhos e empty states. |
| `utilities.css` | Acessibilidade visual, impressão, texto auxiliar e ocultação de valores. |
| `executive.css` | Dashboard, BI, login e erros. |
| `portal.css` | Feed, chat, perfil e organograma. |
| `administration.css` | CRUD, configurações e permissões. |
| `crm.css` | Pipeline, card da oportunidade, pedidos e compras. |
| `finance.css` | Financeiro, comissões e relatórios. |

## Tokens principais

- Marca: `--color-navy-950`, `--color-navy-900`, `--color-teal-700`, `--color-teal-600`.
- Superfícies: `--color-canvas`, `--color-surface`, `--color-surface-subtle`.
- Semântica: `--color-success`, `--color-warning`, `--color-error`, `--color-info` e variantes `*-soft`.
- Espaçamento: `--space-1` (4 px) até `--space-12` (48 px).
- Raios: `--radius-sm` (8 px), `--radius-md` (10 px), `--radius-lg` (12 px).
- Breakpoints de referência: 480, 768, 1024 e 1280 px.
- Foco: `--focus-ring`; nunca remover `:focus-visible` sem substituição equivalente.

## Macros Jinja

Definidas em `app/shared/web/templates/components/macros.html`:

```jinja2
icon(name, size=20, label=none, class_name='')
page_header(title, description=none, eyebrow=none)
stat_card(label, value, icon_name=none, tone='neutral', context=none, sensitive=false)
status_badge(label, tone='neutral')
empty_state(title, description, icon_name='search', action_href=none, action_label=none)
pagination(page, total_pages, base_url)
form_field(name, label, value='', field_type='text', required=false, error=none, help_text=none, autocomplete=none)
data_table_shell(title=none, description=none, table_id=none)
```

Use `call page_header(...)` quando a página tiver ações. Valores financeiros devem usar `money-sensitive`. Estados nunca podem depender apenas de cor: mantenha texto como “Probabilidade: 67%” e “Status: Aberto”.

## JavaScript local

| Arquivo | Responsabilidade |
|---|---|
| `app-shell.js` | Sidebar, drawer mobile, perfil, preferência de menu e ocultação de valores. |
| `navigation.js` | Busca e navegação por teclado no menu. |
| `forms.js` | Confirmações e disclosures acessíveis. |
| `tables.js` | Filtro somente sobre a página de dados já renderizada. |
| `feedback.js` | Impressão e alternância de senha. |
| `app/static/chat_realtime.js` | WebSocket, reconexão limitada, contatos e mensagens por DOM seguro. |

Não usar handlers inline, `innerHTML`, `insertAdjacentHTML`, `eval` ou `document.write`. Ações novas devem usar `data-action`, `data-disclosure`, `data-confirm` ou um listener local.

## Contrato de uma página

```jinja2
{% extends "base.html" %}
{% from "components/macros.html" import page_header %}
{% block title %}Título{% endblock %}
{% block page_styles %}<link rel="stylesheet" href="/assets/css/modulo.css?v={{ asset_version }}">{% endblock %}
{% block page_scripts %}<script src="/assets/js/modulo.js?v={{ asset_version }}" defer></script>{% endblock %}
{% block content %}...{% endblock %}
```

Todo controle precisa de label, nome preservado para o backend, foco visível e estado vazio. Tabelas largas ficam em `.ui-table-wrapper`. Em 767 px ou menos, ações primárias ocupam a largura disponível e grids passam para uma coluna.

## Assets e cache

`ASSET_VERSION` em `app/main.py` é incluído nas URLs `/assets/*`. Altere a versão a cada release que modificar CSS, JS ou sprite. Somente assets com `?v=` recebem cache imutável de um ano; HTML usa `no-store`.
