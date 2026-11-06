'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const entry = fs.readFileSync(path.join(__dirname, '../../recorder-entry.js'), 'utf8');
test('normal Premonition launch keeps the installed chat entry', () => {
  const loaded = [];
  vm.runInNewContext(entry, { process: { argv: ['Premonition'] }, require: name => loaded.push(name) });
  assert.deepEqual(loaded, ['./main']);
});
test('recorder role never loads chat or model startup', () => {
  const loaded = []; let ran = false;
  vm.runInNewContext(entry, { process: { argv: ['Premonition', '--glim-recorder-host'] }, require: name => {
    loaded.push(name); return { run() { ran = true; } };
  } });
  assert.equal(ran, true);
  assert.deepEqual(loaded, ['./src/hands-toy/premonition-host']);
});
test('native capture role refuses to load capture without lead release', () => {
  const loaded = []; let exit = null;
  vm.runInNewContext(entry, {
    console: { error() {} },
    process: { argv: ['Premonition', '--glim-recorder-native', '--capture'], exit: code => { exit = code; } },
    require: name => {
      loaded.push(name);
      if (name === 'node:path') return path;
      if (name === 'node:os') return { homedir: () => '/fake-home' };
      if (name === 'node:fs') return { readFileSync() { throw Error('no release'); } };
      throw Error('native code must not load');
    }
  });
  assert.equal(exit, 1);
  assert.ok(loaded.every(x => x.startsWith('node:')));
});
test('canary byte search rejects secrets even when native result claims PASS', () => {
  const os = require('node:os');
  const { verifyCanary } = require('../../tools/hands-recorder/verify-canary');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'glim-canary-verifier-'));
  const fakeClips = fs.mkdtempSync(path.join(os.tmpdir(), 'glim-fake-clips-'));
  fs.writeFileSync(path.join(root, 'result.json'), JSON.stringify({ status: 'PASS', normalControl: true, secureCanaryTyped: true }));
  fs.writeFileSync(path.join(fakeClips, 'canary.events'), 'HandsFakePass7x93');
  const report = verifyCanary(root, [fakeClips]);
  assert.equal(report.status, 'INCOMPLETE/FAIL');
  assert.equal(report.hits.length, 1);
});
