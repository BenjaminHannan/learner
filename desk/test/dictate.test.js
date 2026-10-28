'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { EventEmitter } = require('node:events');
const { Dictation } = require('../src/dictate');
const T = require('../renderer/dictate');
const P = require('../renderer/platform');

function fake() {
  const c = new EventEmitter();
  c.stdout = new EventEmitter(); c.stderr = new EventEmitter();
  c.written = []; c.ended = false;
  c.stdin = { destroyed: false, write: (s) => { c.written.push(JSON.parse(s)); }, end: () => { c.ended = true; }, on: () => {} };
  c.killed = false; c.kill = () => { c.killed = true; };
  c.say = (o) => c.stdout.emit('data', JSON.stringify(o) + '\n');
  return c;
}
function mk(o) {
  const h = fake(), events = []; let args = null;
  const d = new Dictation({ spawn: (cmd, a) => { args = [cmd, a]; return h; }, helper: '/x/deskhelper', onEvent: (e) => events.push(e), ...o });
  return { h, d, events, args: () => args, states: () => events.filter((e) => e.type === 'state').map((e) => e.state + (e.reason ? ':' + e.reason : '')) };
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

test('merge: existing text, partials and finals', () => {
  assert.strictEqual(T.merge('', [], ''), '');
  assert.strictEqual(T.merge('Hello', [], ''), 'Hello');
  assert.strictEqual(T.merge('Hello', [], 'wor'), 'Hello wor');
  assert.strictEqual(T.merge('Hello ', ['big world'], ''), 'Hello big world', 'no double space after trailing space');
  assert.strictEqual(T.merge('Note:\n', ['buy milk'], 'and eggs'), 'Note:\nbuy milk and eggs', 'newline counts as space');
  assert.strictEqual(T.merge('', ['one', '  ', 'two'], ' three '), 'one two three', 'blank finals are skipped, parts trimmed');
});

test('merge: a partial replaces the previous partial; a final commits and clears it', () => {
  let st = T.begin('Dear Bob,');
  st = T.apply(st, { type: 'partial', text: 'I' });
  st = T.apply(st, { type: 'partial', text: 'I would like' });
  assert.strictEqual(T.text(st), 'Dear Bob, I would like');
  st = T.apply(st, { type: 'final', text: 'I would like a meeting.' });
  assert.strictEqual(T.text(st), 'Dear Bob, I would like a meeting.');
  st = T.apply(st, { type: 'partial', text: 'Thursday' });
  assert.strictEqual(T.text(st), 'Dear Bob, I would like a meeting. Thursday');
  st = T.apply(st, { type: 'final', text: 'Thursday works' });
  st = T.apply(st, { type: 'level', level: 0.5 });
  assert.strictEqual(T.text(st), 'Dear Bob, I would like a meeting. Thursday works');
  assert.strictEqual(T.text(T.apply(T.begin('x'), { type: 'final', text: '' })), 'x');
});

test('platform: dictation is Mac only', () => {
  assert.strictEqual(P.features('darwin').dictate, true);
  assert.strictEqual(P.features('win32').dictate, false);
  assert.strictEqual(P.features('linux').dictate, false);
});

test('dictation: spawns `dictate`, goes listening on ready and forwards partial / final / level', () => {
  const { h, d, events, args, states } = mk();
  d.start();
  assert.deepStrictEqual(args(), ['/x/deskhelper', ['dictate']]);
  assert.deepStrictEqual(states(), ['connecting']);
  h.say({ ready: true }); h.say({ partial: 'hel' }); h.say({ level: 0.3 });
  h.stdout.emit('data', '{"final":"hello wor'); h.stdout.emit('data', 'ld"}\nnot json\n');
  assert.deepStrictEqual(states(), ['connecting', 'listening']);
  assert.deepStrictEqual(events.filter((e) => e.type !== 'state'), [{ type: 'partial', text: 'hel' }, { type: 'level', level: 0.3 }, { type: 'final', text: 'hello world' }]);
  d.close();
});

test('dictation: stop asks the helper to flush, keeps the final that follows, then ends on exit', () => {
  const { h, d, events, states } = mk();
  d.start(); h.say({ ready: true });
  d.stop();
  assert.deepStrictEqual(h.written, [{ stop: true }]);
  h.say({ final: 'last words' });
  assert.ok(events.some((e) => e.type === 'final' && e.text === 'last words'));
  assert.strictEqual(d.state, 'listening');
  h.emit('close', 0);
  assert.deepStrictEqual(states(), ['connecting', 'listening', 'ended:stopped']);
  assert.ok(h.ended);
  d.stop(); assert.strictEqual(h.written.length, 1, 'a second stop does nothing');
});

test('dictation: close sends quit and ends at once; EOF-style exit while listening is an error', () => {
  const a = mk(); a.d.start(); a.h.say({ ready: true });
  a.d.close();
  assert.deepStrictEqual(a.h.written, [{ quit: true }]);
  assert.strictEqual(a.d.state, 'ended');
  const b = mk(); b.d.start(); b.h.say({ ready: true });
  b.h.emit('close', 1);
  const err = b.events.find((e) => e.type === 'error');
  assert.ok(err && err.fatal && /unexpectedly/.test(err.message));
  assert.strictEqual(b.d.state, 'ended');
});

test('dictation: permission errors carry a kind and a clear message', () => {
  const { h, d, events } = mk();
  d.start(); h.say({ error: 'mic-denied' });
  const e = events.find((x) => x.type === 'error');
  assert.strictEqual(e.kind, 'mic-denied'); assert.match(e.message, /Microphone/);
  assert.strictEqual(d.state, 'ended');
  const s = mk(); s.d.start(); s.h.say({ error: 'speech-denied' });
  assert.match(s.events.find((x) => x.type === 'error').message, /Speech Recognition/);
  const u = mk(); u.d.start(); u.h.say({ error: 'speech recognizer unavailable' });
  assert.match(u.events.find((x) => x.type === 'error').message, /speech recognizer unavailable/);
});

test('dictation: spawn failure and ENOENT end with a message', () => {
  const ev = [];
  const d = new Dictation({ spawn: () => { throw new Error('no'); }, helper: 'x', onEvent: (e) => ev.push(e) });
  d.start();
  assert.ok(ev.some((e) => e.type === 'error' && e.fatal)); assert.strictEqual(d.state, 'ended');
  const { h, d: d2, events } = mk(); d2.start(); h.emit('error', { code: 'ENOENT' });
  assert.match(events.find((e) => e.type === 'error').message, /not installed/);
});

test('dictation: stops after silence, and speech keeps it alive', async () => {
  const { h, d, states } = mk({ silenceMs: 60, maxMs: 5000 });
  d.start(); h.say({ ready: true });
  await wait(35); h.say({ partial: 'hi' }); await wait(35); h.say({ level: 0.5 }); await wait(35);
  h.say({ level: 0.02 }); // background noise below the gate does not count
  assert.strictEqual(d.state, 'listening');
  await wait(80);
  assert.deepStrictEqual(h.written, [{ stop: true }]);
  h.emit('close', 0);
  assert.deepStrictEqual(states().slice(-1), ['ended:silence']);
});

test('dictation: stops at the total time limit even while speaking', async () => {
  const { h, d, states } = mk({ silenceMs: 1000, maxMs: 70 });
  d.start(); h.say({ ready: true });
  const iv = setInterval(() => h.say({ partial: 'blah' }), 15);
  await wait(110); clearInterval(iv);
  assert.deepStrictEqual(h.written, [{ stop: true }]);
  h.emit('close', 0);
  assert.deepStrictEqual(states().slice(-1), ['ended:limit']);
});

test('dictation: a helper that ignores stop is cut off', async () => {
  const { h, d } = mk();
  d.start(); h.say({ ready: true });
  d.stop();
  d._end(); // what the 1.5 s fallback timer does
  assert.strictEqual(d.state, 'ended');
  d.close(); // idempotent
});

test('dictation: a final flushed after the helper exits is kept; it ends on close, not exit', () => {
  const { h, d, events, states } = mk();
  d.start(); h.say({ ready: true });
  d.stop();
  h.emit('exit', 0);
  assert.strictEqual(d.state, 'listening', 'exit alone does not end it: stdout may still hold data');
  h.say({ final: 'flushed late' });
  h.emit('close', 0);
  assert.ok(events.some((e) => e.type === 'final' && e.text === 'flushed late'));
  assert.deepStrictEqual(states().slice(-1), ['ended:stopped']);
});
