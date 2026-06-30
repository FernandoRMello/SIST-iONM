# Chat: notificações confiáveis e anexos

Data: 22/06/2026

## Objetivo

Garantir que mensagens recebidas em tempo real atualizem o sino e o contato remetente sempre que a conversa não estiver efetivamente visível. Preservar envio de documentos e miniaturas de imagem no chat flutuante e na tela completa.

## Causa raiz observada

O cliente descarta a notificação quando `payload.room_id` coincide com `state.currentRoomId`. Esse estado permanece preenchido depois de minimizar ou fechar o painel. Assim, a mensagem chega pelo WebSocket, mas o badge é ignorado mesmo sem a conversa estar visível.

## Comportamento

- Uma mensagem da sala atualmente visível é apresentada na conversa e não aumenta o contador.
- Uma mensagem recebida com painel fechado ou minimizado aumenta o sino e o badge do remetente.
- Na tela completa de Chat, a sala exibida é considerada visível.
- Abrir a conversa zera o contador correspondente.
- Reconexão recupera contadores persistidos, evitando perda de estado após atualização da página.
- Anexos continuam aceitando apenas formatos autorizados e até 10 MiB.
- PNG, JPG/JPEG, WebP e GIF aparecem como miniatura clicável; documentos aparecem como link.

## Arquitetura

Criar `chat_read_state(user_id, room_id, last_read_message_id)` com chave única por usuário/sala. O contexto inicial do chat retornará contagens não lidas por sala. Ao abrir uma sala, uma rota autenticada atualizará o último ID lido. O evento em tempo real continua responsável pela atualização imediata no navegador.

No cliente, `isConversationVisible(roomId)` verificará duas condições: painel flutuante aberto na sala ou tela completa exibindo a sala. A igualdade simples com `currentRoomId` será removida do filtro de notificação.

O backend continuará publicando um único payload para mensagens de texto e upload. `attachment_is_image` permanece calculado no servidor. O cliente usa somente DOM seguro e `textContent`.

## Limites operacionais

O gerenciador WebSocket em memória é adequado ao servidor Ubuntu local com um processo. Escalonamento para vários workers exigirá Redis/PostgreSQL pub/sub e fica fora deste workstream. A persistência de não lidas, porém, funciona após reconexões e reinícios.

## Erros e segurança

- Acesso à sala é validado antes de ler upload ou marcar leitura.
- Extensão, tamanho e nome físico aleatório permanecem obrigatórios.
- Falha ao marcar leitura não impede abrir mensagens, mas mantém o badge até nova tentativa.
- WebSocket indisponível apresenta status acessível e reconecta com limite exponencial.

## Testes

- Painel minimizado e fechado devem contar mensagem da sala selecionada.
- Sala realmente visível não deve contar a mesma mensagem.
- Badge do remetente e sino devem receber o mesmo incremento.
- Abrir sala deve persistir leitura e zerar o contador.
- Recarregar contexto deve restaurar não lidas.
- Upload de documento e imagem deve publicar o mesmo payload em tempo real.

