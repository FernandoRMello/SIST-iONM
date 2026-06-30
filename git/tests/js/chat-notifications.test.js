const assert = require('node:assert/strict');
const test = require('node:test');

const rules = require('../../app/static/chat_notification_rules.js');

test('selected room is not visible while floating panel is minimized', () => {
  assert.equal(rules.isConversationVisible(4, {
    panelOpen: false,
    currentRoomId: 4,
    fullRoomId: 0,
  }), false);
});

test('selected room is visible in open panel or full chat page', () => {
  assert.equal(rules.isConversationVisible(4, {
    panelOpen: true,
    currentRoomId: 4,
    fullRoomId: 0,
  }), true);
  assert.equal(rules.isConversationVisible(4, {
    panelOpen: false,
    currentRoomId: 0,
    fullRoomId: 4,
  }), true);
});

test('private notification key belongs to sender', () => {
  assert.equal(rules.notificationKey({ room_id: 9, message: { user_id: 7 } }, 1), 'user:7');
  assert.equal(rules.notificationKey({ room_id: 1, message: { user_id: 7 } }, 1), 'general');
});
