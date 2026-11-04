'use strict';
// Track I1: Glim can see (src/eyes.js) + the senses onScreen hook. Fakes only: no Python, no screenshot, no model.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { EventEmitter } = require('events');
const Eyes = require('../src/eyes');
const SenseSleep = require('../src/sense-sleep');
const SensesMod = require('../src/senses');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'eyes-test-'));
const JPEG = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.alloc(1000, 7)]);
const ones = () => SenseSleep.encodeF16(new Float32Array(64 * 768).fill(0.5)).toString('base64');

function fakeWorker(o = {}) {
  return { calls: [], stopped: 0, async encode(file) { this.calls.push(fs.readFileSync(file)); if (o.fail) throw new Error('boom'); return { ok: true, eye: o.eye || Eyes.EYE_ID, shape: [64, 768], f16: ones(), ms: 21 }; }, stop() { this.stopped++; } };
}
function mk(o = {}) {
  const dir = tmp();
  let t = o.t || Date.parse('2026-11-04T15:00:00Z');
  const worker = o.worker || fakeWorker();
  const shots = [];
  const eyes = new Eyes.Eyes({ userData: dir, worker, isPrivate: SensesMod.isPrivate, platform: o.platform || 'darwin', now: () => t,
    on: () => o.on !== false, keepEvidence: () => !!o.evidence, shot: async () => { shots.push(1); return JPEG; } });
  return { dir, eyes, worker, shots, setT: (x) => { t = x; } };
}

test('off by default: no picture, no features, no frame', async () => {
  const { eyes, shots, dir } = mk({ on: false });
  assert.strictEqual(await eyes.look('Some words on screen', 'Front app: Notes.'), null);
  assert.strictEqual(shots.length, 0);
  assert.strictEqual(eyes.framePart(), null);
  assert.ok(!fs.existsSync(path.join(dir, 'sense-sleep')));
});

test('a look stores anchored features, a one-shot frame, and no evidence unless asked', async () => {
  const { eyes, dir, worker } = mk();
  const r = await eyes.look('Chapter 3: Photosynthesis', 'Front app: Preview. Open: Preview — bio.pdf.');
  assert.ok(r.stored);
  assert.strictEqual(worker.calls.length, 1);
  assert.ok(worker.calls[0].equals(JPEG), 'the worker got the screenshot');
  const recs = eyes.store.records('2026-11-04');
  assert.strictEqual(recs.length, 1);
  assert.strictEqual(recs[0].eye.encoder, Eyes.EYE_ID);
  assert.deepStrictEqual(recs[0].eye.shape, [64, 768]);
  assert.strictEqual(recs[0].text.screen, 'Chapter 3: Photosynthesis');
  assert.strictEqual(recs[0].text.title, 'Preview');
  const v = eyes.store.vector('2026-11-04', recs[0].eye);
  assert.strictEqual(v.length, 64 * 768); assert.strictEqual(v[0], 0.5);
  const part = eyes.framePart();
  assert.strictEqual(part.type, 'image_features');
  assert.deepStrictEqual(part.image_features.shape, [64, 768]);
  assert.strictEqual(eyes.framePart(), null, 'the frame is used once');
  assert.ok(!fs.existsSync(path.join(dir, Eyes.EVIDENCE_DIR)), 'no evidence unless keepSenseEvidence');
  // the temp screenshot is gone
  await new Promise((r) => setTimeout(r, 20));
  assert.ok(!fs.readdirSync(os.tmpdir()).some((f) => f.startsWith('premonition-eyes-' + process.pid)));
});

test('private screens and private windows: no picture is taken at all', async () => {
  const { eyes, shots } = mk({ evidence: true });
  assert.deepStrictEqual(await eyes.look('Enter your password', 'Front app: Safari.'), { skipped: 'private' });
  assert.deepStrictEqual(await eyes.look('news', 'Front app: Safari. Open: Safari — Private Browsing.'), { skipped: 'private' });
  assert.deepStrictEqual(await eyes.look('hello', 'Front app: Google Chrome. Open: Google Chrome — New Incognito Tab.'), { skipped: 'private' });
  assert.deepStrictEqual(await eyes.look('Chase account balance and log in', ''), { skipped: 'private' });
  assert.strictEqual(shots.length, 0);
  assert.strictEqual(eyes.status().private, 4);
});

test('evidence: kept when asked, Mac only, pruned to 3 days and the byte cap', async () => {
  const day = 86400000, t0 = Date.parse('2026-11-01T12:00:00Z');
  const { eyes, dir, setT } = mk({ evidence: true, t: t0 });
  await eyes.look('day one words', 'Front app: Notes.');
  const ev = path.join(dir, Eyes.EVIDENCE_DIR);
  assert.ok(fs.existsSync(path.join(ev, '2026-11-01')));
  setT(t0 + 3 * day);   // 2026-11-04: the 11-01 folder is now outside the 3-day window
  await eyes.look('day four words', 'Front app: Notes.');
  assert.ok(!fs.existsSync(path.join(ev, '2026-11-01')), 'older than 3 days: gone');
  assert.ok(fs.existsSync(path.join(ev, '2026-11-04')));
  // byte cap: oldest go first
  const st = new Eyes.EvidenceStore(tmp(), { platform: 'darwin', maxBytes: 2500, now: () => t0 });
  for (let i = 0; i < 4; i++) assert.ok(st.add(JPEG).stored);
  assert.ok(st.bytes() <= 2500);
  assert.strictEqual(st.files().filter((f) => f.file.endsWith('.jpg')).length, 2);
  // Mac only, never private, JPEG only
  assert.strictEqual(new Eyes.EvidenceStore(tmp(), { platform: 'win32' }).add(JPEG).stored, false);
  assert.strictEqual(st.add(JPEG, { private: true }).reason, 'private');
  assert.strictEqual(st.add(Buffer.from('not a picture')).reason, 'not a jpeg');
});

test('a failing worker or a wrong encoder never stores and never throws', async () => {
  const a = mk({ worker: fakeWorker({ fail: true }) });
  assert.ok((await a.eyes.look('words', 'Front app: Notes.')).error);
  const b = mk({ worker: fakeWorker({ eye: 'other-encoder' }) });
  assert.ok((await b.eyes.look('words', 'Front app: Notes.')).error);
  assert.strictEqual(b.eyes.store.records('2026-11-04').length, 0);
});

test('nightly: eye practice manifest from anchored frames, ears never, idempotent, prunes old feature days', async () => {
  const day = 86400000, t0 = Date.parse('2026-11-04T15:00:00Z');
  const { eyes, dir, setT } = mk({ t: t0 });
  await eyes.look('Mitochondria are the powerhouse of the cell', 'Front app: Preview.');
  await eyes.look('maybe a cat', 'Front app: Preview.');   // a maybe never trains
  // an ear record with an anchor: must not reach the manifest (ears off)
  eyes.store.add({ t: t0, source: 'listen', ear: { encoder: 'whisper-small/x', vec: new Float32Array(8).fill(1), shape: [1, 8] }, text: { subtitle: 'hello there' } });
  const r = eyes.nightly({ now: t0 + 3600000 });
  assert.strictEqual(r.manifests.length, 1);
  const m = JSON.parse(fs.readFileSync(path.join(dir, 'sense-sleep', 'practice-2026-11-04.json'), 'utf8'));
  assert.strictEqual(m.dtype, 'float16');
  assert.strictEqual(m.eye.length, 1);
  assert.strictEqual(m.eye[0].label, 'Mitochondria are the powerhouse of the cell');
  assert.deepStrictEqual(m.ear, []);
  assert.deepStrictEqual(m.encoders, { eye: Eyes.EYE_ID });
  assert.strictEqual(eyes.nightly({ now: t0 + 7200000 }).manifests.length, 0, 'one manifest per day');
  setT(t0 + 5 * day);
  const r2 = eyes.nightly({ now: t0 + 5 * day });
  assert.deepStrictEqual(r2.pruned, ['2026-11-04'], 'unpinned feature days older than 3 days are deleted');
});

test('fromDataUrl: JPEG data URLs only', () => {
  assert.ok(Eyes.fromDataUrl('data:image/jpeg;base64,' + JPEG.toString('base64')).equals(JPEG));
  assert.strictEqual(Eyes.fromDataUrl(null), null);
  assert.strictEqual(Eyes.fromDataUrl('data:image/png;base64,AAAA'), null);
});

test('withFrame puts the frame before the last user message, other messages unchanged', () => {
  const part = { type: 'image_features', image_features: { f16: 'x', shape: [64, 768] } };
  const msgs = [{ role: 'system', content: 'sys' }, { role: 'user', content: 'old' }, { role: 'assistant', content: 'a' }, { role: 'user', content: 'What now?' }];
  const out = Eyes.withFrame(msgs, part);
  assert.deepStrictEqual(out.slice(0, 3), msgs.slice(0, 3));
  assert.strictEqual(out[3].content[1], part);
  assert.match(out[3].content[2].text, /What now\?/);
  assert.strictEqual(msgs[3].content, 'What now?', 'the input is not changed');
  assert.strictEqual(Eyes.withFrame(msgs, null), msgs);
});

test('EyesWorker: JSON lines, ready, reply, crash backoff', async () => {
  let spawned = 0; const procs = [];
  const w = new Eyes.EyesWorker({ timeoutMs: 1000, spawn: () => {
    spawned++;
    const p = new EventEmitter(); p.stdout = new EventEmitter(); p.stderr = new EventEmitter();
    p.stdin = { write: (line) => { const j = JSON.parse(line); setImmediate(() => p.stdout.emit('data', Buffer.from(JSON.stringify({ id: j.id, ok: true, eye: Eyes.EYE_ID, shape: [64, 768], f16: 'AA==', ms: 5 }) + '\n'))); }, end() {} };
    p.kill = () => {}; procs.push(p);
    setImmediate(() => p.stdout.emit('data', Buffer.from('{"ready": true}\n')));
    return p;
  } });
  const r = await w.encode('/tmp/x.jpg');
  assert.strictEqual(r.ms, 5);
  procs[0].emit('exit', 1);
  assert.strictEqual(w.proc, null);
  await assert.rejects(w.encode('/tmp/y.jpg'), /not running/);   // backoff: no instant respawn loop
  assert.strictEqual(spawned, 1);
});

test('senses: onScreen fires after a screen read (old pace and change-only), and a throwing listener never breaks sampling', async () => {
  const dir = tmp();
  const seen = [];
  const state = new SensesMod.AlwaysOnState(dir);
  const consent = SensesMod.normalize({ senses: { screen: true, windows: true }, on: true });
  let t = 0;
  const s = new SensesMod.Senses({ consent, state, now: () => (t += 30000), onScreen: (text, win) => { seen.push([text, win]); throw new Error('listener bug'); },
    samplers: { screen: async () => 'Screen words ' + t, windows: async () => 'Front app: Notes.' } });
  const out = await s.sample();
  assert.ok(out.length >= 1);
  assert.strictEqual(seen.length, 1);
  const s2 = new SensesMod.Senses({ consent, state, changeOnly: true, now: () => (t += 30000), onScreen: (text, win) => { seen.push([text, win]); return Promise.reject(new Error('async bug')); },
    samplers: { screen: async () => 'Other words ' + t, windows: async () => 'Front app: Mail.' } });
  await s2.sample();
  assert.strictEqual(seen.length, 2);
  assert.strictEqual(seen[1][1], 'Front app: Mail.', 'change-only passes the cheap look along');
});
