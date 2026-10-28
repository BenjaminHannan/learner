'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { appBundlePath, paneUrls, combine, openPane, makeDragHandler } = require('../src/perms');

test('appBundlePath walks up to the .app directory', () => {
  assert.strictEqual(appBundlePath('/Applications/Premonition Desk.app/Contents/MacOS/Premonition Desk', '/x/electron'), '/Applications/Premonition Desk.app');
  assert.strictEqual(appBundlePath('/Applications/Premonition Desk.app', '/x'), '/Applications/Premonition Desk.app');
});
test('appBundlePath falls back to the executable in dev', () => {
  assert.strictEqual(appBundlePath('/home/u/desk/node_modules/electron/dist/electron', '/home/u/desk/node_modules/electron/dist/electron'), '/home/u/desk/node_modules/electron/dist/electron');
  assert.strictEqual(appBundlePath('', '/usr/bin/electron'), '/usr/bin/electron');
});
test('pane URLs use the new Settings extension with the old form as fallback', () => {
  assert.strictEqual(paneUrls('accessibility').url, 'x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility');
  assert.strictEqual(paneUrls('screen').url, 'x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture');
  assert.strictEqual(paneUrls('screen').fallback, 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture');
  assert.strictEqual(paneUrls('nope'), null);
});
test('openPane falls back to the old URL when the new one is refused', async () => {
  const seen = [];
  const shell = { openExternal: async (u) => { seen.push(u); if (/PrivacySecurity/.test(u)) throw new Error('nope'); } };
  assert.strictEqual(await openPane(shell, 'accessibility'), true);
  assert.deepStrictEqual(seen.map((u) => u.split(':')[1].split('?')[0]), ['com.apple.settings.PrivacySecurity.extension', 'com.apple.preference.security']);
  assert.strictEqual(await openPane({ openExternal: async () => { throw new Error('x'); } }, 'screen'), false);
  assert.strictEqual(await openPane(shell, 'bogus'), false);
});
test('combine: a row is on only when everything that can answer says yes', () => {
  let c = combine({ accessibility: true, screenRecording: false }, { accessibility: true, screen: true });
  assert.deepStrictEqual(c.rows.map((r) => r.granted), [true, false, null]);
  assert.strictEqual(c.missing, true);
  assert.strictEqual(c.helperTile, true, 'helper says no while the app is allowed: offer the helper tile');
  c = combine({ accessibility: true, screenRecording: true }, { accessibility: true, screen: true });
  assert.strictEqual(c.missing, false); assert.strictEqual(c.helperTile, false);
  c = combine(null, { accessibility: false, screen: true });
  assert.deepStrictEqual(c.rows.map((r) => r.granted), [false, true, null]);
  c = combine({ error: 'no helper' }, {});
  assert.deepStrictEqual(c.rows.map((r) => r.granted), [null, null, null]); assert.strictEqual(c.missing, false);
});
test('drag IPC: only the main window starts a drag, of our own bundle', () => {
  const calls = [];
  const main = { startDrag: (o) => calls.push(o) };
  const other = { startDrag: () => calls.push('evil') };
  const h = makeDragHandler({ getSender: () => main, getFiles: () => ({ app: '/A/Desk.app', helper: '/A/deskhelper' }), getIcon: () => 'icon64' });
  assert.strictEqual(h({ sender: other }, 'app'), false);
  assert.strictEqual(h({ sender: main }, 'app'), true);
  assert.strictEqual(h({ sender: main }, 'helper'), true);
  assert.deepStrictEqual(calls, [{ file: '/A/Desk.app', icon: 'icon64' }, { file: '/A/deskhelper', icon: 'icon64' }]);
  assert.strictEqual(makeDragHandler({ getSender: () => null, getFiles: () => ({}), getIcon: () => null })({ sender: main }, 'app'), false);
  assert.strictEqual(makeDragHandler({ getSender: () => main, getFiles: () => ({ app: '' }), getIcon: () => null })({ sender: main }, 'app'), false);
});
