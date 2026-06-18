(() => {
  const state = { contextLoaded: false, currentUserId: null, generalRoomId: null, currentRoomId: null, users: [], ws: null, notifyWs: null, unread: {}, reconnectAttempt: 0, suspended: false };
  const byId = (id) => document.getElementById(id);
  const make = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
  const wsUrl = (path) => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`;
  const statusNode = () => byId('chatConnectionStatus');
  const setStatus = (text, tone = '') => { const node = statusNode(); if (!node) return; node.setAttribute('aria-live', 'polite'); node.textContent = text; node.dataset.tone = tone; };
  const reconnectDelay = () => Math.min(1000 * (2 ** state.reconnectAttempt++), 30000);

  function avatar(user, fallback) {
    if (user?.avatar_path) { const img = make('img'); img.src = `/${user.avatar_path}`; img.alt = ''; return img; }
    return make('span', '', String(user?.full_name || user?.username || fallback || '?').slice(0, 1).toUpperCase());
  }

  function messageNode(message) {
    const mine = Number(message.user_id) === Number(state.currentUserId);
    const article = make('article', `ui-message msg ${mine ? 'is-mine mine' : 'other'}`);
    const author = make('div', 'msg-author');
    author.append(avatar(message, message.username), make('strong', '', message.full_name || message.username || 'Usuário'));
    article.append(author, make('p', '', message.content || ''));
    if (message.attachment_path) {
      const attachment = make('a', 'ui-message__attachment', 'Abrir anexo');
      attachment.href = `/${message.attachment_path}`;
      attachment.target = '_blank';
      attachment.rel = 'noopener';
      article.append(attachment);
    }
    article.append(make('small', '', message.created_at || ''));
    return article;
  }

  function appendMessage(message) {
    ['bitrixChatMessages', 'fullChatMessages'].forEach((id) => { const box = byId(id); if (!box) return; box.append(messageNode(message)); box.scrollTop = box.scrollHeight; });
  }

  function updateBadges() {
    const total = Object.values(state.unread).reduce((sum, value) => sum + Number(value || 0), 0);
    const badge = byId('chatTotalBadge');
    if (badge) { badge.textContent = total; badge.hidden = total === 0; }
    document.querySelectorAll('[data-room-badge]').forEach((node) => { const value = state.unread[node.dataset.roomBadge] || 0; node.textContent = value; node.hidden = value === 0; });
  }

  async function loadContext() {
    if (state.contextLoaded) return true;
    const response = await fetch('/chat/context');
    if (!response.ok) return false;
    const data = await response.json();
    if (!data.ok) return false;
    Object.assign(state, { currentUserId: data.current_user_id, generalRoomId: data.general_room_id, users: data.users || [], contextLoaded: true });
    renderContacts(); connectNotifications(); return true;
  }

  function contactButton(user, rail = false) {
    const button = make('button', rail ? 'rail-contact' : 'bitrix-contact');
    button.type = 'button'; button.dataset.userId = user.id; button.title = user.full_name || user.username;
    button.addEventListener('click', () => openUser(user.id));
    if (rail) button.append(avatar(user), make('span', 'rail-contact-badge', '0'));
    else { const info = make('span', 'contact-info'); info.append(make('b', '', user.full_name || user.username), make('small', '', user.role || 'Usuário')); button.append(make('span', 'contact-avatar'), info, make('span', 'contact-badge', '0')); button.querySelector('.contact-avatar').append(avatar(user)); }
    return button;
  }

  function renderContacts() {
    const rail = byId('railContacts'); const list = byId('bitrixContactsList');
    if (!rail || !list) return;
    rail.replaceChildren(...state.users.map((user) => contactButton(user, true)));
    list.replaceChildren(...state.users.map((user) => contactButton(user, false)));
    const search = byId('bitrixChatSearch');
    if (search && !search.dataset.ready) { search.dataset.ready = '1'; search.addEventListener('input', () => document.querySelectorAll('#bitrixContactsList .bitrix-contact').forEach((button) => { button.hidden = !button.textContent.toLocaleLowerCase('pt-BR').includes(search.value.toLocaleLowerCase('pt-BR')); })); }
  }

  function setActiveContact(target) {
    document.querySelectorAll('.bitrix-contact').forEach((button) => button.classList.remove('active'));
    const selector = target === 'general'
      ? '#bitrixGeneralContact'
      : `.bitrix-contact[data-user-id="${target}"]`;
    document.querySelector(selector)?.classList.add('active');
  }

  function setConversationHeader(title, subtitle) {
    const titleNode = byId('bitrixChatTitle');
    const subtitleNode = byId('bitrixChatSubtitle');
    if (titleNode) titleNode.textContent = title;
    if (subtitleNode) subtitleNode.textContent = subtitle;
  }

  async function loadMessages(roomId) {
    const response = await fetch(`/chat/messages/${roomId}`); if (!response.ok) return;
    const data = await response.json(); if (!data.ok) return;
    ['bitrixChatMessages', 'fullChatMessages'].forEach((id) => { const box = byId(id); if (box) box.replaceChildren(...(data.messages || []).map(messageNode)); });
  }

  function connectRoom(roomId) {
    state.currentRoomId = Number(roomId); state.suspended = false;
    if (state.ws) state.ws.close();
    const socket = new WebSocket(wsUrl(`/ws/chat/${roomId}`)); state.ws = socket;
    socket.onopen = () => { state.reconnectAttempt = 0; setStatus('Conectado', 'success'); };
    socket.onmessage = (event) => appendMessage(JSON.parse(event.data));
    socket.onerror = () => setStatus('Falha de conexão', 'error');
    socket.onclose = () => { if (state.suspended || state.currentRoomId !== Number(roomId)) return; setStatus('Reconectando…', 'warning'); setTimeout(() => connectRoom(roomId), reconnectDelay()); };
  }

  function connectNotifications() {
    if (state.notifyWs?.readyState === WebSocket.OPEN) return;
    const socket = new WebSocket(wsUrl('/ws/notify')); state.notifyWs = socket;
    socket.onopen = () => setStatus('Conectado', 'success');
    socket.onmessage = (event) => { const payload = JSON.parse(event.data); if (payload?.type !== 'chat_message' || Number(payload.room_id) === Number(state.currentRoomId)) return; const key = Number(payload.room_id) === Number(state.generalRoomId) ? 'general' : String(payload.room_id); state.unread[key] = (state.unread[key] || 0) + 1; updateBadges(); };
    socket.onerror = () => setStatus('Notificações indisponíveis', 'error');
    socket.onclose = () => setTimeout(connectNotifications, reconnectDelay());
  }

  async function openGeneral() { if (!await loadContext()) return; document.body.classList.add('bitrix-chat-open'); setActiveContact('general'); setConversationHeader('Chat geral', 'Todos os usuários'); state.unread.general = 0; updateBadges(); await loadMessages(state.generalRoomId); connectRoom(state.generalRoomId); }
  async function openUser(userId) { if (!await loadContext()) return; const response = await fetch(`/chat/private-room/${userId}`); const data = await response.json(); if (!data.ok) return; const user = state.users.find((item) => Number(item.id) === Number(userId)); document.body.classList.add('bitrix-chat-open'); setActiveContact(userId); setConversationHeader(user?.full_name || user?.username || 'Usuário', 'Conversa individual'); await loadMessages(data.room_id); connectRoom(data.room_id); }
  function send(content) { if (!content || state.ws?.readyState !== WebSocket.OPEN) return false; state.ws.send(JSON.stringify({ content })); return true; }
  function bindForm(formId, inputId) { const form = byId(formId); if (!form || form.dataset.ready) return; form.dataset.ready = '1'; form.addEventListener('submit', (event) => { event.preventDefault(); const input = byId(inputId); const value = input?.value.trim(); if (send(value)) input.value = ''; }); }
  async function connectFullChat(roomId) { await loadContext(); bindForm('fullChatForm', 'fullChatInput'); await loadMessages(roomId); connectRoom(roomId); }
  async function init() { await loadContext(); bindForm('bitrixChatForm', 'bitrixChatInput'); const room = Number(byId('fullChatRoomId')?.value || 0); if (room) connectFullChat(room); }
  function close() { state.suspended = true; state.ws?.close(); document.body.classList.remove('bitrix-chat-open'); }
  function minimize() { document.body.classList.remove('bitrix-chat-open'); }
  function toggleNotifications() { document.body.classList.contains('bitrix-chat-open') ? minimize() : openGeneral(); }
  window.SistIonmChat = { init, openGeneral, openUser, close, minimize, toggleNotifications, connectFullChat };
  window.addEventListener('DOMContentLoaded', init);
})();
