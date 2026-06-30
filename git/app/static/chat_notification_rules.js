(function createChatNotificationRules(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SistIonmChatRules = api;
})(typeof window !== 'undefined' ? window : undefined, () => {
  function isConversationVisible(roomId, state) {
    const target = Number(roomId);
    const floatingVisible = Boolean(state.panelOpen)
      && Number(state.currentRoomId) === target;
    const fullVisible = Number(state.fullRoomId) === target;
    return floatingVisible || fullVisible;
  }

  function notificationKey(payload, generalRoomId) {
    if (Number(payload.room_id) === Number(generalRoomId)) return 'general';
    return `user:${payload.message.user_id}`;
  }

  return { isConversationVisible, notificationKey };
});
