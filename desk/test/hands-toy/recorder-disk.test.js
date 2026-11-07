'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { EventEmitter } = require('node:events');
const { PassThrough } = require('node:stream');
const { Retention, GiB, DEFAULTS } = require('../../src/hands-toy/retention');
const source = fs.readFileSync(require.resolve('../../src/hands-toy/recorder'), 'utf8');

function fixture(context, initialFree = 20 * GiB, options = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-disk-'));
  const intervals = [], children = [];
  let free = initialFree;
  const module = { exports: {} };
  const spawn = () => {
    const child = new EventEmitter();
    child.stdio = Array.from({ length: 5 }, () => new PassThrough());
    child.stdin = child.stdio[0]; child.stdin.resume(); child.stderr = child.stdio[2];
    child.finish = (code = 0, signal = null) => {
      if (child.closed) return;
      child.closed = true;
      child.stdio[3].end(); child.stdio[4].end();
      setImmediate(() => child.emit('close', code, signal));
    };
    child.stdin.once('finish', () => child.finish());
    child.kill = signal => { child.finish(null, signal); return true; };
    children.push(child);
    return child;
  };
  vm.runInNewContext(source, {
    module, exports: module.exports, Buffer, process, console, setTimeout, clearTimeout, setImmediate,
    setInterval(callback, milliseconds) { const timer = { callback, milliseconds, unref() {} }; intervals.push(timer); return timer; },
    clearInterval(timer) { if (timer) timer.cleared = true; },
    require(name) {
      if (name === 'node:child_process') return { ...require(name), spawn, execFileSync: () => JSON.stringify({ screen: true, input: true }) };
      if (name === './retention') return { Retention, GiB };
      if (name === './encoder-proof') return require('../../src/hands-toy/encoder-proof');
      return require(name);
    }
  });
  const recorder = new module.exports.Recorder({ root, fake: true, ...options, retentionOptions: { freeBytes: () => free } });
  context.after(async () => { await recorder.off(); fs.rmSync(root, { recursive: true, force: true }); });
  const add = (id, bytes = 32, extra = {}) => {
    const files = [id + '.fake'];
    fs.writeFileSync(path.join(root, files[0]), Buffer.alloc(bytes, 7));
    return recorder.retention.register({ id, session: id, files, app: 'fake', action: 'test', ...extra });
  };
  return { recorder, root, add, children, intervals, setFree(value) { free = value; } };
}

test('external low disk pauses ON without deleting untrained or keep-set data', async context => {
  const { recorder, root, add, children, setFree } = fixture(context);
  add('untrained'); add('audit', 32, { audit: true });
  const before = fs.readFileSync(recorder.retention.index);
  setFree(5.9 * GiB);
  await recorder.on();
  assert.equal(children.length, 0);
  assert.equal(recorder.status().enabled, true);
  assert.equal(recorder.status().paused, true);
  assert.equal(recorder.status().reason, 'low disk — paused, will resume');
  assert.equal(JSON.parse(fs.readFileSync(recorder.stateFile)).enabled, true);
  assert.equal(recorder.retention.status().clips, 2);
  assert.deepEqual(fs.readFileSync(recorder.retention.index), before);
  assert.equal(fs.existsSync(path.join(root, 'retention.log')), false);
  setFree(0);
  await recorder.retryDisk();
  assert.equal(recorder.retention.status().clips, 2);
  assert.equal(fs.existsSync(path.join(root, 'untrained.fake')), true);
});

test('disk wait resumes only at minFree plus 1 GiB and reports hysteresis as paused', async context => {
  const { recorder, children, setFree } = fixture(context, 5 * GiB);
  await recorder.on();
  for (const available of [10 * GiB, 11 * GiB - 1]) {
    setFree(available); await recorder.retryDisk();
    assert.equal(children.length, 0);
    assert.equal(recorder.status().paused, true);
  }
  setFree(11 * GiB); await recorder.retryDisk();
  assert.equal(children.length, 1);
  assert.equal(recorder.enabled, true);
  assert.equal(recorder.status().paused, false);
  assert.equal(recorder.status().reason, '');
  await recorder.retryDisk();
  assert.equal(children.length, 1);
});

test('explicit OFF cancels disk recovery and a new Recorder never starts itself', async context => {
  const { recorder, children, root, setFree } = fixture(context, 5 * GiB);
  await recorder.on(); await recorder.off();
  setFree(20 * GiB); await recorder.retryDisk();
  assert.equal(children.length, 0);
  assert.equal(recorder.enabled, false);
  assert.equal(JSON.parse(fs.readFileSync(recorder.stateFile)).enabled, false);
  fs.writeFileSync(recorder.stateFile, JSON.stringify({ enabled: true }));
  const { Recorder } = require('../../src/hands-toy/recorder');
  const restarted = new Recorder({ root, fake: true, retentionOptions: { freeBytes: () => 20 * GiB } });
  assert.equal(restarted.enabled, false);
  assert.equal(restarted.activeSegment, undefined);
  await restarted.retryDisk();
  assert.equal(restarted.enabled, false);
});

for (const trigger of ['monitor', 'write', 'finalize']) {
  test(`low disk during ${trigger} retains the current untrained clip and ON state`, async context => {
    const { recorder, root, children, intervals, setFree } = fixture(context);
    await recorder.on();
    const clip = recorder.pending;
    children[0].stdio[3].write(Buffer.from('encoded-head'));
    children[0].stdio[4].write(Buffer.from('encoded-detail'));
    setFree(5 * GiB);
    if (trigger === 'monitor') intervals.find(timer => timer.milliseconds === 250).callback();
    if (trigger === 'write') children[0].stdio[3].write(Buffer.from('refused-tail'));
    if (trigger === 'finalize') children[0].finish();
    await recorder.segmentDone;
    const retained = recorder.retention.data.clips[clip.id];
    assert.equal(retained.spent, false);
    assert.equal(retained.keepReason, 'untrained');
    assert.equal(recorder.retention.status().clips, 1);
    assert.equal(fs.readFileSync(path.join(root, clip.files[0]), 'utf8'), 'encoded-head');
    assert.equal(fs.existsSync(path.join(root, 'retention.log')), false);
    assert.equal(recorder.enabled, true);
    assert.equal(recorder.status().paused, true);
    assert.equal(recorder.status().reason, 'low disk — paused, will resume');
    assert.equal(JSON.parse(fs.readFileSync(recorder.stateFile)).enabled, true);
  });
}

test('critical disk reclaims only judged-trained non-keep clips, oldest first', context => {
  const { recorder, root, add, setFree } = fixture(context);
  const retention = recorder.retention, now = Date.now();
  retention.caps.keep = 128;
  add('old', 32, { createdMs: now - 3000 });
  add('new', 32, { createdMs: now - 1000 });
  add('kept', 32);
  assert.throws(() => retention.finishSleep({ judged: false, trainedIds: ['old', 'new', 'kept'] }), /judged/);
  retention.finishSleep({ judged: true, trainedIds: ['old', 'new', 'kept'], losses: { kept: 10 } });
  add('audit', 96, { audit: true }); add('untrained', 32);
  assert.equal(retention.data.clips.old.keepReason, null);
  assert.ok(retention.data.clips.kept.keepReason);
  for (const available of [5.9 * GiB, 2 * GiB]) {
    setFree(available); assert.equal(retention.sweep().clips, 5);
    assert.equal(fs.existsSync(retention.log), false);
  }
  setFree(2 * GiB - 1); retention.sweep();
  const removed = fs.readFileSync(retention.log, 'utf8').trim().split('\n').map(JSON.parse).filter(row => row.state === 'deleted');
  assert.deepEqual(removed.map(row => row.clipId), ['old', 'new']);
  assert.ok(removed.every(row => row.reason === 'spent' && row.trigger === 'critical free-space backstop'));
  for (const id of ['kept', 'audit', 'untrained']) assert.ok(fs.existsSync(path.join(root, id + '.fake')));
  assert.equal(retention.status().clips, 3);
});

test('OFF during a disk abort keeps the partial clip but cannot resume it', async context => {
  const { recorder, children, setFree } = fixture(context);
  await recorder.on();
  const clip = recorder.pending;
  children[0].stdio[3].write(Buffer.from('keep-this-head'));
  setFree(GiB);
  children[0].stdio[3].write(Buffer.from('refused-tail'));
  await recorder.off();
  assert.equal(recorder.retention.data.clips[clip.id].spent, false);
  assert.equal(JSON.parse(fs.readFileSync(recorder.stateFile)).enabled, false);
  setFree(20 * GiB); await recorder.retryDisk();
  assert.equal(recorder.enabled, false);
  assert.equal(children.length, 1);
});

test('native source and encoder signal exits during a disk abort preserve the clip', async context => {
  const { recorder, children, setFree } = fixture(context, 20 * GiB, {
    fake: false, releaseApproved: true, nativeHelper: '/fake/native-helper'
  });
  await recorder.on();
  const clip = recorder.pending;
  assert.equal(children.length, 2);
  children[0].stdio[3].write(Buffer.from('native-encoded-head'));
  setFree(GiB);
  children[0].stdio[3].write(Buffer.from('refused-tail'));
  await recorder.segmentDone;
  assert.equal(recorder.retention.data.clips[clip.id].spent, false);
  assert.equal(recorder.enabled, true);
  assert.equal(recorder.status().recordingBen, false);
  assert.equal(recorder.status().reason, 'low disk — paused, will resume');
});

test('disk recovery does not resume a manual pause or bypass a daily cap', async context => {
  const { recorder, children, setFree } = fixture(context, 5 * GiB);
  await recorder.on();
  recorder.retention.caps.daily = 0;
  setFree(20 * GiB); await recorder.retryDisk();
  assert.equal(children.length, 0);
  recorder.retention.caps.daily = DEFAULTS.daily;
  recorder.diskPaused = false; recorder.reason = '';
  await recorder.retryDisk();
  assert.equal(children.length, 0);
});

test('bounded disk shutdown keeps the partial clip even when child close never arrives', async context => {
  const { recorder, children, intervals, setFree } = fixture(context);
  await recorder.on();
  const clip = recorder.pending, owned = recorder.activeSegment;
  children[0].stdio[3].write(Buffer.from('partial-before-timeout'));
  children[0].stdin.removeAllListeners('finish');
  children[0].kill = () => true;
  setFree(5 * GiB);
  intervals.find(timer => timer.milliseconds === 250).callback();
  owned.timers.find(timer => timer._idleTimeout === recorder.shutdownMs)._onTimeout();
  owned.timers.find(timer => timer._idleTimeout === recorder.shutdownMs * 2)._onTimeout();
  await recorder.segmentDone;
  assert.equal(recorder.retention.data.clips[clip.id].spent, false);
  assert.equal(recorder.retention.data.clips[clip.id].truncated, true);
  assert.equal(recorder.enabled, true);
  assert.equal(recorder.status().reason, 'low disk — paused, will resume');
  assert.equal(recorder.activeSegment, null);
});

test('critical reclamation stops as soon as the 2 GiB floor is restored', context => {
  const { recorder, root, add } = fixture(context);
  const retention = recorder.retention;
  retention.caps.keep = 64;
  add('first', 32, { createdMs: Date.now() - 2000 }); add('second', 32);
  retention.finishSleep({ judged: true, trainedIds: ['first', 'second'] });
  add('audit', 64, { audit: true });
  retention.freeBytes = () => 2 * GiB - 1 + (fs.existsSync(path.join(root, 'first.fake')) ? 0 : 32);
  assert.equal(retention.sweep().clips, 2);
  assert.ok(retention.data.clips.second);
});

test('total-cap and seven-day deletion and daily admission limits remain in force', context => {
  const { recorder, add } = fixture(context);
  const retention = recorder.retention;
  assert.equal(DEFAULTS.total, 12 * GiB);
  assert.equal(DEFAULTS.daily, 3 * GiB);
  assert.equal(DEFAULTS.ageMs, 7 * 86400000);
  add('old', 32, { createdMs: Date.now() - DEFAULTS.ageMs - 1000 });
  add('recent', 32); add('overflow', 32);
  retention.caps.total = 32;
  assert.equal(retention.sweep().clips, 1);
  const removed = fs.readFileSync(retention.log, 'utf8').trim().split('\n').map(JSON.parse).filter(row => row.state === 'deleted');
  assert.ok(removed.some(row => row.reason === 'expired'));
  assert.ok(removed.some(row => row.reason === 'over-cap'));
  retention.caps.total = 1024; retention.caps.daily = 96;
  assert.throws(() => add('daily-overflow'), /disk backstop/);
  assert.equal(retention.status().dailyBytes, 96);
});
