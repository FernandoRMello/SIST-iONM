const assert = require('node:assert/strict');
const test = require('node:test');

const navigation = require('../../app/shared/web/static/js/shell-navigation.js');

function anchor(href, options = {}) {
  const attributes = new Set(options.attributes || []);
  return {
    href,
    target: options.target || '',
    hasAttribute(name) { return attributes.has(name); },
  };
}

const currentUrl = 'http://127.0.0.1:8000/';

test('intercepts an ordinary same-origin menu click', () => {
  const event = { button: 0, defaultPrevented: false };

  assert.equal(
    navigation.shouldIntercept(event, anchor('http://127.0.0.1:8000/feed'), currentUrl),
    true,
  );
});

test('does not intercept modified or non-primary clicks', () => {
  const link = anchor('http://127.0.0.1:8000/feed');

  for (const event of [
    { button: 1 },
    { button: 0, ctrlKey: true },
    { button: 0, metaKey: true },
    { button: 0, shiftKey: true },
    { button: 0, altKey: true },
    { button: 0, defaultPrevented: true },
  ]) {
    assert.equal(navigation.shouldIntercept(event, link, currentUrl), false);
  }
});

test('does not intercept unsafe navigation targets', () => {
  const event = { button: 0, defaultPrevented: false };

  assert.equal(navigation.shouldIntercept(event, anchor('https://example.com/feed'), currentUrl), false);
  assert.equal(navigation.shouldIntercept(event, anchor('http://127.0.0.1:8000/feed', { target: '_blank' }), currentUrl), false);
  assert.equal(navigation.shouldIntercept(event, anchor('http://127.0.0.1:8000/export', { attributes: ['download'] }), currentUrl), false);
});

test('returns only missing asset URLs without duplicates', () => {
  const missing = navigation.missingAssetUrls(
    ['http://127.0.0.1:8000/assets/css/layout.css?v=1'],
    [
      '/assets/css/layout.css?v=1',
      '/assets/css/crm.css?v=1',
      '/assets/css/crm.css?v=1',
    ],
    currentUrl,
  );

  assert.deepEqual(missing, ['http://127.0.0.1:8000/assets/css/crm.css?v=1']);
});
