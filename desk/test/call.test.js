'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { EventEmitter } = require('node:events');
const { Call, Chunker, cleanForSpeech, isFiller } = require('../src/call');

// A fake `deskhelper call`: tests push JSON lines into it and read what the Call wrote to its stdin.
function fake() {
  const c = new EventEmitter();
  c.stdout = new EventEmitter(); c.stderr = new EventEmitter();
  c.written = [];
  c.stdin = { destroyed: false, write: (s) => { c.written.push(JSON.parse(s)); }, end: () => {}, on: () => {} };
  c.killed = false; c.kill = () => { c.killed = true; };
  c.say = (o) => c.stdout.emit('data', JSON.stringify(o) + '\n');
  c.sent = (k) => c.written.filter((m) => k in m);
  return c;
}
function mk(ask) {
  const h = fake(), events = [];
  const call = new Call({ spawn: () => h, helper: '/x/deskhelper', ask, onEvent: (e) => events.push(e) });
  call.start(); h.say({ ready: true });
  return { h, call, events, states: () => events.filter((e) => e.type === 'state').map((e) => e.state) };
}
const tick = () => new Promise((r) => setImmediate(r));

test('call: chunker cuts sentences as tokens arrive and flushes the rest', () => {
  const ck = new Chunker(), got = [];
  for (const d of ['Sure, I can ', 'help with that. The weather ', 'in Paris is 3.5 degrees warmer. ', 'Bye']) got.push(...ck.push(d));
  assert.deepStrictEqual(got, ['Sure, I can help with that.', 'The weather in Paris is 3.5 degrees warmer.']);
  assert.deepStrictEqual(ck.flush(), ['Bye']);
  assert.deepStrictEqual(new Chunker().push('Short. Ok. '), [], 'under ~20 chars is held until more arrives');
  assert.deepStrictEqual(new Chunker().push('A line that is long enough\nnext'), ['A line that is long enough']);
});

test('call: code blocks are held back and never spoken', () => {
  const ck = new Chunker(), got = [];
  for (const d of ['Here is the fix for you. ``', '`js\nconsole.log(1);\n', '```\nThat should do it now. ']) got.push(...ck.push(d));
  got.push(...ck.flush());
  assert.deepStrictEqual(got, ['Here is the fix for you.', 'That should do it now.']);
});

test('call: markdown, emoji and urls are stripped before speaking', () => {
  assert.strictEqual(cleanForSpeech('## Title\n- **Bold** and _soft_ text 😀'), 'Title Bold and soft text');
  assert.strictEqual(cleanForSpeech('See [the docs](https://x.io/a?b=1) or https://example.com/page.'), 'See the docs or a link.');
  assert.strictEqual(cleanForSpeech('Run `ls -la` now'), 'Run ls -la now');
  assert.strictEqual(cleanForSpeech('```\ncode\n```'), '');
  assert.strictEqual(cleanForSpeech('🎉🎉'), '');
});

test('call: filler and tiny utterances are ignored', async () => {
  const asked = [];
  const { h, call } = mk(async (t) => { asked.push(t); });
  for (const t of ['uh', 'Um.', '', 'a', 'hmm uh']) h.say({ final: t });
  await tick();
  assert.deepStrictEqual(asked, []);
  assert.strictEqual(isFiller('uh huh'), true); assert.strictEqual(isFiller('what time is it'), false);
  h.say({ final: 'what time is it' }); await tick();
  assert.deepStrictEqual(asked, ['what time is it']);
  call.hangup();
});

test('call: streamed reply goes to the helper sentence by sentence, in order, and state follows', async () => {
  let release;
  const { h, call, states } = mk(async (t, { onDelta }) => {
    onDelta('It is half past three. '); onDelta('You have a call at four, '); onDelta('so leave soon. Bye!');
    await new Promise((r) => { release = r; }); // still "streaming"
  });
  h.say({ final: 'what time is it' }); await tick();
  assert.deepStrictEqual(h.sent('say').map((m) => m.say), ['It is half past three.', 'You have a call at four, so leave soon.']);
  assert.strictEqual(call.state, 'thinking');
  h.say({ speaking: true }); assert.strictEqual(call.state, 'speaking');
  release(); await tick();
  assert.deepStrictEqual(h.sent('say').map((m) => m.say).pop(), 'Bye!', 'the tail is flushed at the end');
  assert.strictEqual(call.state, 'speaking');
  h.say({ speaking: false }); assert.strictEqual(call.state, 'listening');
  assert.ok(states().includes('thinking') && states().includes('speaking'));
});

test('call: "One sec." is said once when a tool runs', async () => {
  const { h, call } = mk(async () => { await new Promise((r) => setTimeout(r, 20)); });
  h.say({ final: 'open my notes please' }); await tick();
  call.toolStarted(); call.toolStarted();
  assert.deepStrictEqual(h.sent('say').map((m) => m.say), ['One sec.']);
  call.hangup();
});

test('call: talking over Glim sends stop, aborts the ask and the new utterance is the next turn', async () => {
  const signals = [], asked = [];
  const { h, call } = mk(async (t, { signal, onDelta }) => {
    asked.push(t); signals.push(signal);
    if (asked.length === 1) { onDelta('This will be a rather long answer. '); await new Promise((r) => setTimeout(r, 30)); }
  });
  h.say({ final: 'tell me a story' }); await tick();
  h.say({ speaking: true });
  h.say({ partial: 'wait' });
  assert.strictEqual(h.sent('stop').length, 0, 'one word alone does not interrupt');
  h.say({ partial: 'wait stop that' });
  assert.strictEqual(h.sent('stop').length, 1);
  assert.strictEqual(signals[0].aborted, true);
  assert.strictEqual(call.state, 'listening');
  h.say({ final: 'wait stop that' }); await tick();
  assert.deepStrictEqual(asked, ['tell me a story', 'wait stop that']);
  assert.strictEqual(signals[1].aborted, false);
  assert.strictEqual(h.sent('say').length, 1, 'the aborted answer says nothing more');
});

test('call: a bargein event from the helper stops speech too, but not for filler', async () => {
  const { h, call } = mk(async (t, { onDelta }) => { onDelta('Here comes a fairly long reply. '); await new Promise((r) => setTimeout(r, 30)); });
  h.say({ final: 'hello there glim' }); await tick(); h.say({ speaking: true });
  h.say({ partial: 'um' }); h.say({ bargein: true });
  assert.strictEqual(h.sent('stop').length, 0);
  h.say({ partial: 'hold on' }); h.say({ bargein: true });
  assert.ok(h.sent('stop').length >= 1);
  assert.strictEqual(call.state, 'listening');
});

test('call: an early bargein with a single weak word like "the" does not cancel the answer', async () => {
  const { h } = mk(async (t, { onDelta }) => { onDelta('Here comes a fairly long reply. '); await new Promise((r) => setTimeout(r, 30)); });
  h.say({ final: 'hello there glim' }); await tick(); h.say({ speaking: true });
  h.say({ partial: 'the' }); h.say({ bargein: true });
  assert.strictEqual(h.sent('stop').length, 0);
  h.say({ partial: 'wait' }); h.say({ bargein: true });
  assert.ok(h.sent('stop').length >= 1);
});

test('call: hangup sends quit and ends', () => {
  const { h, call, states } = mk(async () => {});
  call.hangup();
  assert.deepStrictEqual(h.sent('quit'), [{ quit: true }]);
  assert.strictEqual(call.state, 'ended');
  assert.strictEqual(states().pop(), 'ended');
});

test('call: mute is passed to the helper and partials are dropped while muted', () => {
  const { h, call, events } = mk(async () => {});
  call.setMuted(true);
  assert.deepStrictEqual(h.sent('mute'), [{ mute: true }]);
  const n = events.length; h.say({ partial: 'secret words here' });
  assert.strictEqual(events.length, n);
});

test('call: the helper dying ends the call with an error', () => {
  const { h, call, events } = mk(async () => {});
  h.emit('exit', 1);
  assert.strictEqual(call.state, 'ended');
  const err = events.find((e) => e.type === 'error');
  assert.ok(err && err.fatal && /stopped/.test(err.message));
});

test('call: permission errors explain where to switch it on', () => {
  const { h, call, events } = mk(async () => {});
  h.say({ error: 'mic-denied' });
  const err = events.find((e) => e.type === 'error');
  assert.strictEqual(err.kind, 'mic-denied'); assert.match(err.message, /Privacy & Security > Microphone/);
  assert.strictEqual(call.state, 'ended');
});

test('call: a missing helper ends with a plain message, and an ask failure is spoken but not fatal', async () => {
  const h = fake(), events = [];
  const c = new Call({ spawn: () => h, helper: 'x', ask: async () => { throw new Error('Gateway error 500'); }, onEvent: (e) => events.push(e) });
  c.start(); h.say({ ready: true }); h.say({ final: 'how are you doing' }); await tick();
  assert.deepStrictEqual(h.sent('say').map((m) => m.say), ['Sorry, something went wrong.']);
  assert.ok(events.some((e) => e.type === 'error' && e.fatal === false));
  assert.notStrictEqual(c.state, 'ended');
  const h2 = fake(), ev2 = [];
  const c2 = new Call({ spawn: () => h2, helper: 'x', ask: async () => {}, onEvent: (e) => ev2.push(e) });
  c2.start(); h2.emit('error', Object.assign(new Error('x'), { code: 'ENOENT' }));
  assert.strictEqual(c2.state, 'ended'); assert.match(ev2.find((e) => e.type === 'error').message, /not installed/);
});
