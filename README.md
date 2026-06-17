# OverpriceON Web Local V1 - FIX4 CLEAN

Esta versão foi reestruturada em base limpa para evitar os problemas de rota.

## Correções principais

- Removida definitivamente qualquer rota genérica no caminho principal.
- Cadastros agora ficam somente em `/cadastros/...`.
- `/settings`, `/finance`, `/opportunities`, `/orders`, `/commissions` e `/reports/sellers` são rotas próprias.
- Sem `@app.context_processor`.
- Função `seller_metrics` incluída.
- Endpoint `/favicon.ico` incluído.
- BAT usa `python -m uvicorn`.

## Como iniciar

Dê dois cliques em:

```text
iniciar_overpriceon.bat
```

## Acesso

Local:

```text
http://127.0.0.1:8000
```

Rede:

```text
http://IP_DO_SERVIDOR:8000
```

## Usuário inicial

- Usuário: fernando.mello
- Senha: conforme definida no projeto

## Observação

Extraia em uma pasta nova, não por cima da versão anterior.

## FIX5 - Usuários editáveis

Adicionado:
- editar usuário;
- alterar senha;
- alterar perfil;
- vincular/desvincular vendedor;
- ativar/desativar usuário;
- proteção para não desativar nem remover o perfil admin do usuário `fernando.mello`.

## FIX6 - Otimização para smartphone

Melhorias:
- menu lateral retrátil no celular;
- botão "Menu" fixo no topo;
- layout responsivo;
- cards e KPIs adaptados para telas pequenas;
- formulários em uma coluna;
- botões maiores para toque;
- tabelas com rolagem horizontal;
- fonte de inputs ajustada para evitar zoom automático no iPhone;
- manifest básico para criar atalho na tela inicial.

## FIX7 - Correção da tela R.O / Oportunidades

Correção:
- Ajustado template `opportunities.html`.
- Corrigido erro `TypeError: 'builtin_function_or_method' object is not iterable`.
- Causa: no Jinja, `o.items` era interpretado como método interno do dicionário, não como a lista de itens da R.O.
- Solução: alterado para `o['items']`.

## FIX8 - Dashboard, R.O fornecedor e impressão

Melhorias:
- Dashboard com KPIs mais vivos e escala de cor por probabilidade.
- Linha de oportunidade com cor: vermelho, laranja, amarelo e verde.
- Valor total da proposta no dashboard.
- Botão para ocultar/mostrar valores sensíveis como banco.
- Campo de formas de pagamento desejadas na R.O.
- PDF de R.O para fornecedor com cliente, produtos, valor negociado, overprice, comissão e forma de pagamento desejada.
- Botões de impressão em Pedidos e Relatórios de Vendedores.
- CSS de impressão para relatórios mais limpos.

## FIX9 - BI Gerencial

Adicionado:
- rota `/bi-gerencial`;
- BI em HTML conectado ao SQLite;
- KPIs de valores em proposta, a receber, a pagar, overprice ponderado, comissão e LL projetado;
- simulação do LL aplicado em fontes de investimento;
- recomendação de produtos para focar;
- recomendação de clientes por probabilidade e overprice ponderado;
- botão de ocultar/mostrar valores;
- impressão do BI.

## FIX10 - BI restrito e LL automático

Alterações:
- BI Gerencial exclusivo para o usuário `fernando.mello`.
- Link do BI aparece somente para `fernando.mello`.
- Removido campo manual de capital aplicado.
- Simulação de investimento usa automaticamente o `LL projetado`.

## V2 Portal CRM

Nova estrutura inspirada em CRM corporativo:
- Feed inicial estilo rede social interna;
- Chat integrado básico;
- Perfil individual do usuário;
- Organograma;
- Administração de permissões por perfil;
- Cards de oportunidade com comentários, anotações e documentos;
- Produtos com descrição detalhada e tabelas 1/2/3;
- Compras no Backoffice;
- Menu reestruturado por frentes: Portal, CRM, Produtos, Backoffice e Gestão.

## SIST-iONM V2.1

Alterações:
- Sistema renomeado para SIST-iONM.
- Barra lateral ocultável/recolhível.
- Ícones nos menus.
- Administração reforçada com usuários, e-mail individual e SMTP individual.
- Configuração de e-mail por perfil para envio/disparo de orçamento.
- Permissões por perfil mantidas.

## SIST-iONM V2.2

Ajustes:
- Menu lateral recolhível agora possui rolagem interna para acessar todos os itens.
- Chat suspenso global em todas as telas.
- Foto de perfil com upload.
- Chat exibe foto/avatar do usuário.
- Pipeline com alternância Lista/Kanban.
- Kanban com movimentação por clique: voltar/avançar etapa.

## SIST-iONM V2.3 - Chat em tempo real

Ajustes:
- Chat geral em tempo real via WebSocket.
- Chat privado usuário ↔ usuário.
- Seletor de destinatário no chat suspenso.
- Mensagens aparecem sem atualizar a página.
- Chat completo também opera em tempo real.
- Usuários podem ser escolhidos diretamente para conversa individual.

## SIST-iONM V2.4 - Chat estilo WhatsApp

Ajustes:
- Mensagens do usuário logado ficam à direita.
- Mensagens dos outros usuários ficam à esquerda.
- Bolhas de conversa com cores diferentes.
- Ajuste visual no chat suspenso e no chat completo.

## SIST-iONM V2.5 - Produtos dentro do card

Correção:
- Card da oportunidade agora carrega a lista de produtos ativos.
- Adicionado formulário dentro do card para incluir produto na oportunidade.
- Campos: produto, quantidade, preço de venda unitário e comissão do vendedor.
- Tabela do card passa a mostrar fornecedor, venda, overprice e comissão.

## SIST-iONM V2.6 - Chat suspenso estilo Bitrix

Ajustes:
- Chat suspenso redesenhado para ficar mais próximo do Bitrix24.
- Barra lateral direita com ícones de contatos.
- Painel de chat sobreposto com lista de contatos e conversa.
- Seleção de chat geral ou conversa individual.
- Notificações em tempo real por WebSocket.
- Badge de mensagens não lidas no sino, no contato e no chat geral.
- Pisca visual na barra lateral quando chegar nova mensagem.
