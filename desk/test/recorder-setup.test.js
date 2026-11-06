'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { RecorderSetup, diskCaps, MAX_CAPS, GUIDANCE, GiB } = require('../src/recorder-setup');

function fixture(context, free = 100 * GiB) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'uncle-recorder-'));
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return { root, setup: new RecorderSetup(root, { freeBytes: () => free, clock: () => 1234 }) };
}

test('fresh home, Yes, No and restart never start recording', context => {
  const { root, setup } = fixture(context);
  assert.equal(setup.status().choice, null);
  assert.equal(setup.status().enabled, false);
  assert.deepEqual(fs.readdirSync(root), []);
  assert.equal(setup.choose(true).choice, true);
  const restarted = new RecorderSetup(root);
  assert.equal(restarted.status().choice, true);
  assert.equal(restarted.status().enabled, false);
  assert.equal(setup.choose(false).choice, false);
  assert.equal(restarted.status().choice, false);
  assert.equal(fs.statSync(setup.file).mode & 0o777, 0o600);
  assert.deepEqual(fs.readdirSync(root), ['recorder-consent.json']);
});

test('unreadable, invalid and older choices fail closed', context => {
  const { setup } = fixture(context);
  for (const saved of ['{', '{}', '{"version":1,"choice":"yes","enabled":true}', '{"version":2,"choice":true}']) {
    fs.writeFileSync(setup.file, saved);
    assert.equal(setup.status().choice, null);
    assert.equal(setup.status().enabled, false);
  }
  fs.writeFileSync(setup.file, '{"version":1,"choice":true,"enabled":true}');
  assert.equal(setup.status().enabled, false);
  assert.throws(() => setup.choose('yes'), /Yes or No/);
});

test('a leftover temporary choice cannot block a new No', context => {
  const { setup } = fixture(context);
  fs.writeFileSync(setup.file + '.tmp', 'interrupted write');
  assert.equal(setup.choose(false).choice, false);
  assert.equal(setup.status().enabled, false);
});

test('choice writes reject symlinks without changing outside files', context => {
  const { root, setup } = fixture(context);
  const outside = path.join(root, 'do-not-touch.txt');
  fs.writeFileSync(outside, 'untouched');
  fs.symlinkSync(outside, setup.file);
  assert.equal(setup.status().choice, null);
  assert.throws(() => setup.choose(true), /not safe/);
  assert.equal(fs.readFileSync(outside, 'utf8'), 'untouched');
});

test('caps shrink with free disk, never grow beyond HANDS caps', () => {
  for (const free of [-1, NaN, Infinity, 0, 5 * GiB, 10 * GiB]) assert.equal(diskCaps(free).total, 0);
  assert.deepEqual(diskCaps(100 * GiB), MAX_CAPS);
  assert.equal(diskCaps(30 * GiB).total, 4 * GiB);
  assert.equal(diskCaps(30 * GiB).daily, GiB);
  let previous = 0;
  for (let size = 0; size <= 200; size++) {
    const caps = diskCaps(size * GiB);
    assert.ok(caps.total >= previous && caps.total <= MAX_CAPS.total);
    assert.ok(caps.daily <= MAX_CAPS.daily && caps.daily <= caps.total);
    assert.ok(caps.keep <= MAX_CAPS.keep && caps.keep <= caps.total);
    assert.equal(caps.minFree, MAX_CAPS.minFree);
    assert.equal(caps.ageMs, MAX_CAPS.ageMs);
    previous = caps.total;
  }
});

test('disk check errors leave no room for recording', context => {
  const { root } = fixture(context);
  const setup = new RecorderSetup(root, { freeBytes: () => { throw Error('disk unavailable'); } });
  assert.equal(setup.status().caps.total, 0);
  assert.equal(setup.status().enabled, false);
});

test('guidance names the responsible app and warns about private pictures', () => {
  const text = GUIDANCE.join('\n');
  for (const words of ['Premonition', 'Input Monitoring', 'Screen & System Audio Recording', 'No sound', 'private things']) assert.ok(text.includes(words));
});

test('only the app window can save recording consent', () => {
  const main = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
  const start = main.indexOf("{ const own = (e)");
  const end = main.indexOf("ipcMain.handle('safety:get'", start);
  const handlers = new Map(), sender = {}, writes = [];
  vm.runInNewContext(main.slice(start, end) + '}', {
    ui: { webContents: sender }, process: { platform: 'darwin' },
    ipcMain: { handle: (name, handler) => handlers.set(name, handler) },
    recorderSetup: { status: () => ({ enabled: false }), choose: value => writes.push(value) }
  });
  const choose = handlers.get('recorder:choose');
  assert.throws(() => choose({ sender: {} }, true), /choice in Glim/);
  assert.throws(() => choose(null, true), /choice in Glim/);
  assert.deepEqual(writes, []);
  choose({ sender }, false);
  assert.deepEqual(writes, [false]);
  assert.equal(handlers.get('recorder:status')({ sender: {} }), null);
});
