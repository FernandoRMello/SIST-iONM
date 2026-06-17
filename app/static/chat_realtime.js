
(function(){
  const state = { contextLoaded:false,currentUserId:null,generalRoomId:null,currentRoomId:null,users:[],rooms:[],ws:null,notifyWs:null,unread:{} };

  function escapeHtml(value){ return String(value || "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }
  function wsUrl(path){ const proto = window.location.protocol === "https:" ? "wss" : "ws"; return `${proto}://${window.location.host}${path}`; }

  function avatarHtml(user, fallback){
    const label = escapeHtml((user && (user.full_name || user.username)) || fallback || "?");
    if (user && user.avatar_path) return `<img src="/${escapeHtml(user.avatar_path)}" alt="${label}">`;
    return `<span>${label.slice(0,1).toUpperCase()}</span>`;
  }

  function renderMessage(msg){
    const mine = Number(msg.user_id) === Number(state.currentUserId);
    const name = escapeHtml(msg.full_name || msg.username || "Usuário");
    const content = escapeHtml(msg.content || "");
    const date = escapeHtml(msg.created_at || "");
    const avatar = msg.avatar_path ? `<img src="/${escapeHtml(msg.avatar_path)}" alt="">` : `<span>${name.slice(0,1).toUpperCase()}</span>`;
    return `<div class="msg ${mine ? "mine" : "other"}"><div class="msg-author">${avatar}<strong>${name}</strong></div><p>${content}</p><small>${date}</small></div>`;
  }

  function updateBadges(){
    const total = Object.values(state.unread).reduce((a,b)=>a+Number(b||0),0);
    const totalBadge = document.getElementById("chatTotalBadge");
    if(totalBadge){ totalBadge.textContent = total; totalBadge.style.display = total > 0 ? "grid" : "none"; }
    document.querySelectorAll("[data-room-badge]").forEach(el => {
      const key = el.getAttribute("data-room-badge");
      const v = state.unread[key] || 0;
      el.textContent = v; el.style.display = v > 0 ? "grid" : "none";
    });
  }

  function roomKey(roomId){ return Number(roomId) === Number(state.generalRoomId) ? "general" : String(roomId); }

  async function loadContext(){
    if(state.contextLoaded) return true;
    const res = await fetch("/chat/context");
    if(!res.ok) return false;
    const data = await res.json();
    if(!data.ok) return false;
    state.currentUserId = data.current_user_id;
    state.generalRoomId = data.general_room_id;
    state.users = data.users || [];
    state.rooms = data.rooms || [];
    state.contextLoaded = true;
    renderContacts();
    connectNotifications();
    return true;
  }

  function renderContacts(){
    const rail = document.getElementById("railContacts");
    const list = document.getElementById("bitrixContactsList");
    if(!rail || !list) return;
    rail.innerHTML = ""; list.innerHTML = "";
    state.users.forEach(u => {
      const label = escapeHtml(u.full_name || u.username);
      rail.insertAdjacentHTML("beforeend", `<button class="rail-contact" data-user-id="${u.id}" onclick="SistIonmChat.openUser(${u.id})" title="${label}">${avatarHtml(u,label)}<span class="rail-contact-badge" data-user-rail-badge="${u.id}">0</span></button>`);
      list.insertAdjacentHTML("beforeend", `<button class="bitrix-contact" data-user-id="${u.id}" onclick="SistIonmChat.openUser(${u.id})"><span class="contact-avatar">${avatarHtml(u,label)}</span><span class="contact-info"><b>${label}</b><small>${escapeHtml(u.role || "Usuário")}</small></span><span class="contact-badge" data-user-badge="${u.id}">0</span></button>`);
    });

    const search = document.getElementById("bitrixChatSearch");
    if(search && !search.dataset.ready){
      search.dataset.ready = "1";
      search.addEventListener("input", function(){
        const term = this.value.toLowerCase();
        document.querySelectorAll("#bitrixContactsList .bitrix-contact").forEach(btn => {
          btn.style.display = btn.textContent.toLowerCase().includes(term) ? "flex" : "none";
        });
      });
    }
  }

  function setActiveContact(target){
    document.querySelectorAll(".bitrix-contact").forEach(btn => btn.classList.remove("active"));
    if(target === "general"){
      const g = document.getElementById("bitrixGeneralContact");
      if(g) g.classList.add("active");
      return;
    }
    const btn = document.querySelector(`.bitrix-contact[data-user-id="${target}"]`);
    if(btn) btn.classList.add("active");
  }

  async function loadMessages(roomId){
    const box = document.getElementById("bitrixChatMessages");
    if(!box) return;
    const res = await fetch(`/chat/messages/${roomId}`);
    if(!res.ok) return;
    const data = await res.json();
    if(!data.ok) return;
    box.innerHTML = "";
    (data.messages || []).forEach(msg => box.insertAdjacentHTML("beforeend", renderMessage(msg)));
    box.scrollTop = box.scrollHeight;
  }

  function connectRoom(roomId){
    state.currentRoomId = roomId;
    if(state.ws) state.ws.close();
    state.ws = new WebSocket(wsUrl(`/ws/chat/${roomId}`));
    state.ws.onmessage = event => {
      const msg = JSON.parse(event.data);
      const box = document.getElementById("bitrixChatMessages");
      if(box){
        box.insertAdjacentHTML("beforeend", renderMessage(msg));
        box.scrollTop = box.scrollHeight;
      }
    };
  }

  function connectNotifications(){
    if(state.notifyWs && state.notifyWs.readyState === WebSocket.OPEN) return;
    state.notifyWs = new WebSocket(wsUrl("/ws/notify"));
    state.notifyWs.onmessage = event => {
      const payload = JSON.parse(event.data);
      if(!payload || payload.type !== "chat_message") return;
      const key = roomKey(payload.room_id);
      if(Number(payload.room_id) !== Number(state.currentRoomId)){
        state.unread[key] = (state.unread[key] || 0) + 1;
        updateBadges();
        flashRail();
      }
    };
  }

  function flashRail(){
    const rail = document.getElementById("bitrixChatRail");
    if(!rail) return;
    rail.classList.add("has-new-message");
    setTimeout(()=>rail.classList.remove("has-new-message"), 1300);
  }

  async function openGeneral(){
    await loadContext();
    document.body.classList.add("bitrix-chat-open");
    setActiveContact("general");
    document.getElementById("bitrixChatTitle").textContent = "Chat geral";
    document.getElementById("bitrixChatSubtitle").textContent = "Todos os usuários";
    state.unread.general = 0;
    updateBadges();
    await loadMessages(state.generalRoomId);
    connectRoom(state.generalRoomId);
  }

  async function openUser(userId){
    await loadContext();
    const res = await fetch(`/chat/private-room/${userId}`);
    const data = await res.json();
    if(!data.ok) return;
    const user = state.users.find(u => Number(u.id) === Number(userId));
    const label = user ? (user.full_name || user.username) : "Usuário";
    document.body.classList.add("bitrix-chat-open");
    setActiveContact(userId);
    document.getElementById("bitrixChatTitle").textContent = label;
    document.getElementById("bitrixChatSubtitle").textContent = "Conversa individual";
    state.unread[String(data.room_id)] = 0;
    updateBadges();
    await loadMessages(data.room_id);
    connectRoom(data.room_id);
  }

  function send(content){
    if(!state.ws || state.ws.readyState !== WebSocket.OPEN || !content) return false;
    state.ws.send(JSON.stringify({content}));
    return true;
  }

  function setupForm(){
    const form = document.getElementById("bitrixChatForm");
    if(!form || form.dataset.ready) return;
    form.dataset.ready = "1";
    form.addEventListener("submit", e => {
      e.preventDefault();
      const input = document.getElementById("bitrixChatInput");
      const value = input ? input.value.trim() : "";
      if(send(value) && input) input.value = "";
    });
  }

  async function init(){ await loadContext(); setupForm(); }
  function close(){ document.body.classList.remove("bitrix-chat-open"); }
  function minimize(){ document.body.classList.remove("bitrix-chat-open"); }
  function toggleNotifications(){ document.body.classList.contains("bitrix-chat-open") ? minimize() : openGeneral(); }

  window.SistIonmChat = { init, openGeneral, openUser, close, minimize, toggleNotifications, connectFullChat:function(roomId){ state.currentRoomId = roomId; } };
  window.addEventListener("DOMContentLoaded", init);
})();
