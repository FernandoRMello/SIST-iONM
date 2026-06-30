const assert = require('node:assert/strict');
const test = require('node:test');

const editor = require('../../app/shared/web/static/js/profile-avatar-editor.js');

test('cover scale fills the square frame', () => {
  assert.equal(editor.coverScale(1000, 500, 300, 1), 0.6);
  assert.equal(editor.coverScale(500, 1000, 300, 1), 0.6);
  assert.ok(Math.abs(editor.coverScale(500, 500, 300, 1.5) - 0.9) < 1e-9);
});

test('offset is clamped so no empty area enters frame', () => {
  assert.equal(editor.clampOffset(200, 600, 300), 150);
  assert.equal(editor.clampOffset(-200, 600, 300), -150);
  assert.equal(editor.clampOffset(40, 600, 300), 40);
});
