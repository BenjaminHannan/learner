'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { isAuthPopup } = require('../src/tools/browser');

test('sign-in popups (Google, Apple, Microsoft, GitHub login) get a real window; other popups open in place', () => {
  assert.strictEqual(isAuthPopup('https://accounts.google.com/v3/signin/accountchooser?display=popup'), true);
  assert.strictEqual(isAuthPopup('https://appleid.apple.com/auth/authorize?client_id=x'), true);
  assert.strictEqual(isAuthPopup('https://login.microsoftonline.com/common/oauth2'), true);
  assert.strictEqual(isAuthPopup('https://github.com/login/oauth/authorize'), true);
  assert.strictEqual(isAuthPopup('https://github.com/anthropics'), false);
  assert.strictEqual(isAuthPopup('http://accounts.google.com/'), false);
  assert.strictEqual(isAuthPopup('https://accounts.google.com.evil.example/'), false);
  assert.strictEqual(isAuthPopup('not a url'), false);
});
