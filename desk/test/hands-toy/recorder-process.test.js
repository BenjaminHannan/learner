'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EventEmitter } = require('node:events');
const { prepare, MAX_BYTES } = require('../../src/hands-toy/recorder-process');

function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-process-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'executable');
  fs.writeFileSync(file, 'fixture', { mode: 0o700 });
  return file;
}

function fake(pid = 123) { const child = new EventEmitter(); child.pid = pid; return child; }
function finish(child, code = 0, signal = null) { child.emit('spawn'); child.emit('exit', code, signal); child.emit('close', code, signal); }

test('stable launch copies arguments and options and detaches evidence', async t => {
  const file = fixture(t), prepared = await prepare(file), child = fake();
  const args = ['--capture'], options = { env: { NAME: 'original' }, stdio: ['pipe', 'pipe'] };
  let actual;
  const owner = prepared.launch((...input) => { actual = input; return child; }, args, options);
  args[0] = 'changed'; options.env.NAME = 'changed'; options.stdio.push('ignore');
  assert.equal(actual[0], file); assert.deepEqual(actual[1], ['--capture']);
  assert.equal(actual[2].env.NAME, 'original'); assert.deepEqual(actual[2].stdio, ['pipe', 'pipe']);
  assert.ok(Object.isFrozen(actual[1]) && Object.isFrozen(actual[2].env) && Object.isFrozen(actual[2].stdio));
  assert.equal(owner.child, child); assert.equal(await owner.evidence(), null);
  finish(child);
  const proof = await owner.evidence();
  assert.deepEqual(proof, { pid: 123, command: file, args: ['--capture'], sha256: require('node:crypto').createHash('sha256').update('fixture').digest('hex'), ownedLaunch: true, exitCode: 0, signal: null, closeObserved: true });
  proof.args[0] = 'changed'; assert.deepEqual((await owner.evidence()).args, ['--capture']);
});

test('rejects missing, non-executable, oversized, relative, and symlink identities', async t => {
  const file = fixture(t);
  await assert.rejects(prepare('relative')); await assert.rejects(prepare(file + '-missing'));
  fs.chmodSync(file, 0o600); await assert.rejects(prepare(file));
  fs.chmodSync(file, 0o700); fs.truncateSync(file, MAX_BYTES + 1); await assert.rejects(prepare(file));
  const link = file + '-link'; fs.symlinkSync(file, link); await assert.rejects(prepare(link));
});

test('identity drift before, during, or after launch refuses evidence', async t => {
  for (const when of ['before', 'during', 'after']) {
    const file = fixture(t), prepared = await prepare(file), child = fake();
    if (when === 'before') fs.writeFileSync(file, 'changed');
    const owner = prepared.launch(() => { if (when === 'during') fs.writeFileSync(file, 'changed'); return child; }, [], {});
    finish(child); if (when === 'after') fs.writeFileSync(file, 'changed');
    assert.equal(await owner.evidence(), null, when);
  }
});

test('requires owned spawn, matching pid, exit and clean close', async t => {
  const prepared = await prepare(fixture(t));
  for (const scenario of ['error', 'nonzero', 'signal', 'no-close', 'no-spawn', 'pid-change', 'close-mismatch']) {
    const child = fake(), owner = prepared.launch(() => child, [], {});
    if (scenario === 'error') child.emit('error', Error('failed'));
    if (scenario !== 'no-spawn') child.emit('spawn');
    if (scenario === 'pid-change') child.pid = 124;
    const code = scenario === 'nonzero' ? 1 : scenario === 'signal' ? null : 0;
    const signal = scenario === 'signal' ? 'SIGTERM' : null;
    child.emit('exit', code, signal);
    if (scenario !== 'no-close') child.emit('close', scenario === 'close-mismatch' ? 1 : code, signal);
    assert.equal(await owner.evidence(), null, scenario);
  }
  assert.throws(() => prepared.launch(() => { throw Error('pre-spawn'); }, [], {}), /pre-spawn/);
});

test('shell and overridden executable identity never produce direct evidence', async t => {
  const prepared = await prepare(fixture(t));
  for (const options of [{ shell: true }, { shell: '/bin/sh' }, { argv0: '/different-executable' }]) {
    const child = fake();
    const owner = prepared.launch(() => child, [], options);
    finish(child);
    assert.equal(await owner.evidence(), null);
  }
});

test('argv rejects holes and accessors without evaluating or launching them', async t => {
  const prepared = await prepare(fixture(t));
  let reads = 0, launches = 0;
  const accessor = [];
  Object.defineProperty(accessor, 0, { get() { reads++; return '--capture'; }, enumerable: true });
  for (const args of [new Array(1), accessor, ['bad\0argument']]) {
    assert.throws(() => prepared.launch(() => { launches++; return fake(); }, args), /invalid launch/);
  }
  assert.equal(reads, 0);
  assert.equal(launches, 0);
});
