'use strict';
// SWITCH-ON 2026-11-05: the header and the chat read ONE brain phase; a message is held (never bounced) while the brain starts or is off.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const B = require('../renderer/brainstate');
const { watchdogRecovering } = require('../src/startlog');

test('Ben\'s bug: header "Warming up…" and the chat reply come from the same phase', () => {
  const p = B.phase({ gw: { state: 'warming' }, startedAt: 0 });   // gwIsStarting() was false here, so the chat said "off"
  assert.strictEqual(p, 'starting'); assert.strictEqual(B.label(p), 'Warming up…');
  assert.match(B.heldLine(p), /warming up.*answer as soon as/i); assert.doesNotMatch(B.heldLine(p), /off/i);
});
test('phases: ready, starting (Turn on pressed / watchdog restarting), off, asleep', () => {
  const now = 1e9;
  assert.strictEqual(B.phase({ gw: { state: 'ready' } }), 'ready');
  assert.strictEqual(B.phase({ gw: { state: 'down' }, startedAt: now - 30000, now }), 'starting');
  assert.strictEqual(B.phase({ gw: { state: 'down' }, startedAt: now - 200000, now }), 'off');
  assert.strictEqual(B.phase({ gw: { state: 'down' }, why: { kind: 'memory', restarting: true }, now }), 'starting');
  assert.strictEqual(B.phase({ gw: { state: 'down' }, why: { kind: 'memory', restarting: false }, now }), 'off');
  assert.strictEqual(B.phase({ gw: { state: 'ready' }, asleep: true }), 'asleep');
});
test('starting path: the message is held and handed over exactly once when the brain is ready', () => {
  const h = new B.Held();
  assert.ok(h.hold('t1', 'what is on my calendar?'));
  assert.ok(!h.hold('t1', 'what is on my calendar?'), 'the same message is not held twice');
  assert.deepStrictEqual(h.take('starting'), []); assert.deepStrictEqual(h.take('off'), []);
  const got = h.take('ready'); assert.strictEqual(got.length, 1); assert.strictEqual(got[0].text, 'what is on my calendar?');
  assert.deepStrictEqual(h.take('ready'), []);
});
test('off path: Glim says off only when truly off, keeps the message, and sends it after Turn on', () => {
  const h = new B.Held(); const p = B.phase({ gw: { state: 'down' }, now: 1e9 });
  assert.strictEqual(p, 'off'); assert.match(B.heldLine(p), /off right now.*kept your message/i);
  h.hold('t1', 'hi Glim');
  assert.strictEqual(B.phase({ gw: { state: 'down' }, startedAt: 1e9, now: 1e9 + 1000 }), 'starting');
  assert.deepStrictEqual(h.take(B.phase({ gw: { state: 'warming' } })), []);
  assert.strictEqual(h.take(B.phase({ gw: { state: 'ready' } }))[0].text, 'hi Glim');
});
test('the watchdog log says when it is restarting the brain by itself', () => {
  const now = new Date(2026, 10, 5, 15, 25, 0).getTime();
  const log = (l) => '2026-11-05 15:24:25 TRIPPED: pressure level 4\nstopped big\n' + l;
  assert.ok(watchdogRecovering(log('2026-11-05 15:24:28 recovery: waiting for 120s of normal memory pressure'), now));
  assert.ok(watchdogRecovering(log('2026-11-05 15:24:28 recovery: memory calm; running serve.sh --autostart'), now));
  assert.ok(!watchdogRecovering(log('2026-11-05 15:24:28 recovery: assistant restarted'), now));
  assert.ok(!watchdogRecovering(log('2026-11-05 15:24:28 recovery: stopped or started by hand; exiting'), now));
  assert.ok(!watchdogRecovering(log('2026-11-05 15:24:28 recovery: 4 restarts in 6 h already; waiting until fewer than 4 before trying again'), now));
  assert.ok(!watchdogRecovering(log('2026-11-05 14:00:00 recovery: waiting for 120s of normal memory pressure'), now), 'stale');
});
test('app.js uses the one phase for the header and the bounced-message line (no second source)', () => {
  const s = fs.readFileSync(path.join(__dirname, '..', 'renderer', 'app.js'), 'utf8');
  assert.ok(!/I\\u2019m off right now\. Press Turn on below, then ask me again/.test(s), 'the old bounce line is gone');
  assert.match(s, /BrainState\.label\(brainPhase\(\)\)/);
  assert.match(s, /holdMessage\(lastSent\.threadId, lastSent\.text\)/);
  assert.match(s, /if \(gw\.state === 'ready'\) flushHeld\(\)/);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'renderer', 'index.html'), 'utf8'), /<script src="brainstate\.js"><\/script>\s*<script src="app\.js">/);
});
