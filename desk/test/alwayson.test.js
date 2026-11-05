'use strict';
// Always-on loop (src/alwayson.js) with a fake model, fake senses and fake gates: no Python, no network, no timers that fire.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/senses');
const A = require('../src/alwayson');

function rig(o) {
  o = o || {};
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ao-'));
  const clock = { t: 1_000_000 };
  const now = () => clock.t;
  const state = new S.AlwaysOnState(dir, { now });
  const c = S.defaults(); for (const id of (o.on || ['screen', 'chats'])) c.senses[id] = true;
  let n = 0;
  const senses = new S.Senses({ consent: c, state, now, samplers: { screen: async () => 'Screen words ' + (++n), windows: async () => 'Windows ' + n } });
  const gates = { busy: false, pressure: 1, night: false };
  const out = { say: [], note: [], learn: [], asks: 0 };
  let answer = 'answer' in o ? o.answer : (() => '{"say": null, "note": null, "learn": null, "why": "nothing"}');
  const loop = new A.AlwaysOn({ senses, state, now,
    ask: async (messages, signal) => { out.asks++; out.lastMessages = messages; return typeof answer === 'function' ? answer(signal) : answer; },
    deliver: { say: (t) => out.say.push(t), note: (t) => out.note.push(t), learn: (t) => { out.learn.push(t); return true; } },
    gates: { busy: () => gates.busy, pressure: () => gates.pressure, night: () => gates.night },
    evidence: o.evidence === true ? undefined : false,   // the plumbing tests skip the v2 evidence check; its own tests below turn it on
    onDecision: (x) => { (out.decisions = out.decisions || []).push(x); }, onIdle: (x) => { (out.idle = out.idle || []).push(x); },
    setTimer: () => 0, clearTimer: () => {} });
  return { dir, clock, state, senses, gates, out, loop, setAnswer: (a) => { answer = a; } };
}
const SAY = (txt, urgent, important) => JSON.stringify({ important: important || 'deadline', say: txt, note: null, learn: null, urgent: !!urgent, why: 'test' });

test('a normal tick asks the model with the new observations and delivers say / note / learn', async () => {
  const r = rig({ answer: JSON.stringify({ say: 'Your lab report is due at 3.', note: 'Lab report due Friday 3 pm', learn: 'enzyme kinetics', important: 'deadline', why: 'deadline' }) });
  const res = await r.loop.tick();
  assert.strictEqual(res.reason, 'done');
  assert.strictEqual(r.out.asks, 1);
  assert.match(r.out.lastMessages[1].content, /\[screen, \d\d:\d\d\] Screen words 1/);
  assert.deepStrictEqual(r.out.say, ['Your lab report is due at 3.']);
  assert.deepStrictEqual(r.out.note, ['Lab report due Friday 3 pm']);
  assert.deepStrictEqual(r.out.learn, ['enzyme kinetics']);
  assert.strictEqual(r.state.focus.topic, 'enzyme kinetics');
});

test('every sense off => no sampling and no model call', async () => {
  const r = rig({ on: [] });
  for (let i = 0; i < 5; i++) { r.clock.t += 60000; assert.strictEqual((await r.loop.tick()).reason, 'off'); }
  assert.deepStrictEqual(r.senses.calls, { screen: 0, windows: 0 });
  assert.strictEqual(r.out.asks, 0);
});

test('pauses while a chat runs / Ben types, under memory pressure 2+, and in the night window', async () => {
  const r = rig({ answer: SAY('hello') });
  r.gates.busy = true; assert.strictEqual((await r.loop.tick()).reason, 'busy');
  r.gates.busy = false; r.gates.pressure = 2; assert.strictEqual((await r.loop.tick()).reason, 'pressure');
  r.gates.pressure = 4; assert.strictEqual((await r.loop.tick()).reason, 'pressure');
  r.gates.pressure = 1; r.gates.night = true; assert.strictEqual((await r.loop.tick()).reason, 'night');
  assert.strictEqual(r.out.asks, 0); assert.strictEqual(r.out.say.length, 0);
  assert.deepStrictEqual(r.senses.calls, { screen: 0, windows: 0 }); // a paused loop does not even read the screen
  r.gates.night = false; assert.strictEqual((await r.loop.tick()).reason, 'done');
  assert.deepStrictEqual(r.out.say, ['hello']);
});

test('Ben starting to type while the model thinks: the say is not delivered', async () => {
  const r = rig();
  r.setAnswer(() => { r.gates.busy = true; return SAY('Did you mean 42?'); });
  const res = await r.loop.tick();
  assert.strictEqual(res.reason, 'busy');
  assert.strictEqual(r.out.say.length, 0);
});

test('cancel() during the model call drops the tick', async () => {
  const r = rig();
  r.setAnswer((signal) => new Promise((resolve, reject) => { signal.addEventListener('abort', () => reject(new Error('aborted'))); setImmediate(() => r.loop.cancel('typing')); }));
  const res = await r.loop.tick();
  assert.strictEqual(res.reason, 'cancelled');
  assert.strictEqual(r.out.say.length, 0);
});

test('say rate limit: 2 says inside 20 min => 1 delivered; after 20 min the next goes out', async () => {
  const r = rig({ answer: SAY('Tip one') });
  await r.loop.tick();
  r.clock.t += 5 * 60000; r.state.add('chats', 'new thing'); r.setAnswer(SAY('Tip two'));
  await r.loop.tick();
  assert.deepStrictEqual(r.out.say, ['Tip one']);
  assert.strictEqual(r.loop.stats.held, 1);
  r.clock.t += 16 * 60000; r.state.add('chats', 'another thing'); r.setAnswer(SAY('Tip three'));
  await r.loop.tick();
  assert.deepStrictEqual(r.out.say, ['Tip one', 'Tip three']);
});

test('urgent passes the limit only when it reads like a reminder or deadline', async () => {
  const r = rig({ answer: SAY('Tip one') });
  await r.loop.tick();
  r.clock.t += 60000; r.state.add('chats', 'x1'); r.setAnswer(SAY('Look at this cool fact', true));
  await r.loop.tick();
  r.clock.t += 60000; r.state.add('chats', 'x2'); r.setAnswer(SAY('Reminder: your chem quiz starts in 10 minutes', true));
  await r.loop.tick();
  r.clock.t += 60000; r.state.add('chats', 'x3'); r.setAnswer(SAY('Reminder: your chem quiz starts in 10 minutes', false));
  await r.loop.tick();
  assert.deepStrictEqual(r.out.say, ['Tip one', 'Reminder: your chem quiz starts in 10 minutes']);
});

test('malformed JSON => tick skipped, nothing delivered, no crash', async () => {
  for (const bad of ['sure! here you go', '{"say": "hi"', '[1,2]', '{"say": 5, "note": null, "learn": null, "why": "x"}', '', null]) {
    const r = rig({ answer: bad });
    const res = await r.loop.tick();
    assert.strictEqual(res.reason, 'parse', String(bad));
    assert.strictEqual(r.out.say.length + r.out.note.length + r.out.learn.length, 0);
  }
  const r = rig({ answer: () => { throw new Error('gateway down'); } });
  assert.strictEqual((await r.loop.tick()).reason, 'error');
});

test('parseDecision accepts fenced JSON and think blocks', () => {
  const d = A.parseDecision('<think>hmm</think>```json\n{"say": null, "note": "x", "learn": null, "why": "y"}\n```');
  assert.deepStrictEqual(d, { say: null, note: 'x', learn: null, urgent: false, important: 'none', why: 'y' });
});

test('nothing new => no model call, and the wait backs off from 60 s to 5 min', async () => {
  const r = rig({ on: ['chats'] });
  assert.strictEqual(r.loop.delay, 60000);
  for (let i = 0; i < 6; i++) assert.strictEqual((await r.loop.tick()).reason, 'quiet');
  assert.strictEqual(r.out.asks, 0);
  assert.strictEqual(r.loop.delay, 300000);
  r.senses.push('chats', 'Ben wrote: hi');
  await r.loop.tick();
  assert.strictEqual(r.loop.delay, 60000);
});

test('observations already shown are not shown again; the state survives a restart', async () => {
  const r = rig({ on: ['chats'] });
  r.senses.push('chats', 'Ben wrote: the essay is due Monday');
  await r.loop.tick();
  assert.strictEqual(r.out.asks, 1);
  const again = new S.AlwaysOnState(r.dir, { now: () => r.clock.t });
  assert.strictEqual(again.fresh().length, 0);
  assert.strictEqual(again.inbox.length, 1);
});

test('private says and notes from the model are not delivered', async () => {
  const r = rig({ answer: JSON.stringify({ say: 'Your password is hunter2', note: 'Chase online banking login is ben/abc', learn: null, why: 'x' }) });
  await r.loop.tick();
  assert.strictEqual(r.out.say.length, 0); assert.strictEqual(r.out.note.length, 0);
});

test('the same learn topic as the current focus is not restarted', async () => {
  const r = rig({ answer: JSON.stringify({ say: null, note: null, learn: 'Photosynthesis', why: 'x' }) });
  r.state.setFocus('photosynthesis');
  await r.loop.tick();
  assert.strictEqual(r.out.learn.length, 0);
});

test('main.js wires the loop to Ben-first, pressure, the night window and the model chat uses', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /const aoBusy = \(\) => benBusy\(\) \|\| !!\(agent && agent\.running\) \|\| Date\.now\(\) - lastTyping < 15000/);
  assert.match(m, /pressure: \(\) => AlwaysOnMod\.macPressure\(\)/);
  assert.match(m, /night: aoNight/);
  assert.match(m, /if \(aoLoop\) aoLoop\.cancel\('chat'\)/);
  assert.match(m, /model: AlwaysOnMod\.chatModel\(s\)/);
  assert.strictEqual(A.chatModel({ model: 'qwen36', modelFast: 'qwen36-fast' }), 'qwen36-fast');
});

// SWITCH-ON 2026-11-05: quiet unless Glim's own decision marks the moment important
test('speak filter: important "none" or missing = quiet (logged, idle hook fires); important = delivered', async () => {
  const r = rig({ answer: JSON.stringify({ important: 'none', say: 'You are coding in T3 Code.', note: null, learn: null, why: 'focus' }) });
  let x = await r.loop.tick();
  assert.strictEqual(x.quiet, true); assert.deepStrictEqual(r.out.say, []);
  assert.strictEqual(r.out.decisions[0].outcome, 'quiet'); assert.strictEqual(r.out.decisions[0].important, 'none');
  assert.strictEqual(r.out.idle.length, 1);
  r.setAnswer(JSON.stringify({ say: 'Hi Ben.', note: null, learn: null, why: 'no field' }));
  r.clock.t += 60000; x = await r.loop.tick();
  assert.deepStrictEqual(r.out.say, []); assert.strictEqual(r.out.decisions[1].outcome, 'quiet');
  r.setAnswer(JSON.stringify({ important: 'bogus', say: 'Hi Ben.', note: null, learn: null, why: 'x' }));
  r.clock.t += 60000; await r.loop.tick(); assert.deepStrictEqual(r.out.say, []);
  r.setAnswer(SAY('Your battery is at 4%; plug in now.', true, 'urgent'));
  r.clock.t += 60000; x = await r.loop.tick();
  assert.deepStrictEqual(r.out.say, ['Your battery is at 4%; plug in now.']); assert.strictEqual(r.out.decisions[3].outcome, 'said');
  assert.strictEqual(r.out.idle.length, 3, 'a tick that spoke does not start a study');
});
test('speak filter: an important say still obeys the 20-minute limit and the meter (it can hold, never force)', async () => {
  const r = rig({ answer: SAY('Quiz at 3.', false, 'deadline') });
  await r.loop.tick(); r.clock.t += 60000; r.setAnswer(SAY('Quiz at 3, again.', false, 'stuck'));
  await r.loop.tick();
  assert.strictEqual(r.out.say.length, 1); assert.strictEqual(r.out.decisions[1].outcome, 'held-limit');
});
test('a quiet tick (nothing new) also fires the idle hook', async () => {
  const r = rig(); await r.loop.tick(); const n = r.out.idle.length; await r.loop.tick();
  assert.ok(r.out.idle.length >= n);
});

// speak filter v2 (MARKS A-v2): "important" counts only with evidence in the tick's observations
test('v2 evidence: a chat ABOUT deadlines is not a deadline; a concrete due time is', async () => {
  const E = A.evidenceFor, o = (sense, text) => ({ sense, text });
  assert.ok(!E('deadline', [o('screen', 'Ben asked Glim to start a school audit and list all assignments, exams and deadlines')]));
  assert.ok(E('deadline', [o('screen', 'Lab Report 4 - Due today at 3:45 PM. Not submitted.')]));
  assert.ok(E('deadline', [o('screen', 'Meeting with Mr. Phipps starts in 5 minutes')]));
  assert.ok(E('urgent', [o('screen', 'Battery 4% - your Mac will sleep soon')]));
  assert.ok(!E('urgent', [o('screen', 'Activity Monitor: python3.12 12.8 GB')]));
  assert.ok(E('asked', [o('chats', 'Ben wrote: Glim, tell me when the build finishes')]));
  assert.ok(!E('asked', [o('screen', 'You asked why I knew about AP')]), 'only Ben\'s own words count');
  const err = o('screen', "TypeError: Cannot read properties of undefined (reading 'map') at App.jsx:42");
  assert.ok(!E('stuck', [err])); assert.ok(E('stuck', [err, err, err])); assert.ok(E('stuck', [], { stuck: true }));
  assert.ok(!E('deadline', [o('periphery', 'Periphery (...): Calendar: exam starts in 5 minutes')]), 'the periphery alone is not evidence');
});
test('v2: an unbacked "important" is quiet, logged with what the brain claimed; parse fixes', async () => {
  const r = rig({ evidence: true, answer: JSON.stringify({ important: 'deadline', say: 'Ben, that sounds deadline-relevant.', note: null, learn: null, why: 'x' }) });
  await r.loop.tick(); assert.deepStrictEqual(r.out.say, []);
  assert.strictEqual(r.out.decisions[0].outcome, 'quiet'); assert.strictEqual(r.out.decisions[0].claimed, 'deadline');
  for (const say of ['null', 'None — nothing to add.', 'Nothing urgent to interrupt right now.']) assert.strictEqual(A.parseDecision(JSON.stringify({ important: 'none', say, note: null, learn: null, why: 'x' })).say, null, say);
  assert.ok(A.parseDecision('{"say": "hi", "note": null, "learn": null}'), 'a missing why is allowed');
});
