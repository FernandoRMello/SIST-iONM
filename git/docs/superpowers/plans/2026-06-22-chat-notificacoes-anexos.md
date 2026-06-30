# Chat Notifications and Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar badges de mensagens confiáveis quando o chat estiver oculto e persistir leituras por usuário/sala.

**Architecture:** O SQLite registra o último ID lido por usuário e sala; o contexto calcula não lidas. O cliente decide se uma sala está realmente visível antes de suprimir o badge e marca leitura ao abri-la.

**Tech Stack:** FastAPI, SQLite, WebSocket, JavaScript, pytest.

## Global Constraints

- Servidor local executa com um processo WebSocket.
- Upload continua limitado a 10 MiB e formatos autorizados.
- Mensagens usam DOM seguro, sem HTML dinâmico.

---

### Task 1: Persistência de leitura

**Files:**
- Modify: `app/main.py`
- Create: `tests/web/test_chat_notifications.py`

**Interfaces:**
- Produces: `mark_room_read(user_id: int, room_id: int)`, `unread_room_counts(user_id: int) -> dict[int, int]`, POST `/chat/read/{room_id}`.

- [ ] **Step 1: Escrever testes falhando**

```python
def test_opening_room_persists_last_read_message(admin_client, legacy_test_state):
    response = admin_client.post(f"/chat/read/{room_id}")
    assert response.json() == {"ok": True, "room_id": room_id, "unread": 0}
```

Cobrir também acesso negado e contagem no `/chat/context`.

- [ ] **Step 2: Executar RED**

Run: `python -m pytest tests/web/test_chat_notifications.py -q`
Expected: 404/ausência de `unread`.

- [ ] **Step 3: Implementar schema e helpers**

Criar `chat_read_state` em `init_portal_modules`, calcular `COUNT(cm.id)` acima de `last_read_message_id` apenas para salas acessíveis e fazer upsert parametrizado ao marcar leitura.

- [ ] **Step 4: Executar GREEN**

Run: `python -m pytest tests/web/test_chat_notifications.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "feat: persist chat unread state"`

### Task 2: Visibilidade real e badges

**Files:**
- Modify: `app/static/chat_realtime.js`
- Modify: `tests/web/test_portal_pages.py`
- Create: `tests/js/chat-notifications.test.js`

**Interfaces:**
- Produces: `isConversationVisible(roomId)`, `notificationKey(payload)`, `markRead(roomId)`.

- [ ] **Step 1: Escrever RED**

```js
assert.equal(api.isConversationVisible(4, { panelOpen: false, currentRoomId: 4, fullRoomId: 0 }), false);
assert.equal(api.isConversationVisible(4, { panelOpen: true, currentRoomId: 4, fullRoomId: 0 }), true);
```

- [ ] **Step 2: Rodar RED**

Run: `node --test tests/js/chat-notifications.test.js`
Expected: módulo/função ausente.

- [ ] **Step 3: Implementar filtro de visibilidade**

Expor helpers testáveis, carregar `data.unread`, incrementar sino/contato quando oculto e chamar `/chat/read/{room}` ao abrir sala. Fechar/minimizar não apaga `currentRoomId`, mas deixa de suprimir notificação.

- [ ] **Step 4: Rodar GREEN e regressão**

Run: `node --test tests/js/chat-notifications.test.js && python -m pytest tests/web/test_portal_pages.py tests/web/test_chat_delivery.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "fix: notify hidden chat conversations"`

