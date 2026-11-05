'use strict';
// The periphery (SWITCH-ON 2026-11-05): focus on one screen, still know what is going on in the other windows / displays.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const S = require('../src/senses');

function rig(o) {
  o = o || {};
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'peri-')); const clock = { t: 1e9 }; const now = () => clock.t;
  const state = new S.AlwaysOnState(dir, { now });
  const c = S.defaults(); for (const id of (o.on || ['screen', 'windows'])) c.senses[id] = true;
  const w = { open: 'T3 Code — beautiful-model; Safari — Wikipedia', glances: 0, items: o.items };
  const senses = new S.Senses({ consent: c, state, now, changeOnly: !!o.changeOnly, samplers: {
    screen: async () => 'front window words ' + clock.t, windows: async () => 'Front app: T3 Code. Open: ' + w.open + '.',
    periphery: async () => { w.glances++; return { items: w.items || [{ app: 'Safari', title: 'Photosynthesis - Wikipedia', text: 'Photosynthesis is the process plants use to turn light into chemical energy', how: 'window', display: 'main' }] }; } } });
  return { state, senses, clock, w };
}
test('a periphery line is stored, labelled as periphery (not the focus), and bounded', async () => {
  const r = rig(); await r.senses.sample();
  const p = r.state.inbox.find((x) => x.sense === 'periphery');
  assert.ok(p, 'stored'); assert.match(p.text, /^Periphery \(background windows, low detail; not what Ben is focused on\): Safari — Photosynthesis/);
  assert.ok(p.text.length <= 1000);
  const long = S.peripheryText({ items: Array.from({ length: 5 }, (_, i) => ({ app: 'App' + i, title: 'T'.repeat(200), text: 'x'.repeat(900) })) });
  assert.ok(long.length < 1300); assert.ok(!/x{151}/.test(long), 'each window keeps ~150 characters');
});
test('cost: every 3 minutes, or 30 s after the open windows change; never while the screen sense is off', async () => {
  const r = rig(); await r.senses.sample(); assert.strictEqual(r.w.glances, 1);
  r.clock.t += 25000; await r.senses.sample(); assert.strictEqual(r.w.glances, 1, 'not due yet');
  r.w.open = 'T3 Code — beautiful-model; Notes — Groceries'; r.clock.t += 21000; await r.senses.sample(); assert.strictEqual(r.w.glances, 2, 'a background window changed');
  r.clock.t += 60000; await r.senses.sample(); assert.strictEqual(r.w.glances, 2);
  r.clock.t += 180000; await r.senses.sample(); assert.strictEqual(r.w.glances, 3, '3 minutes passed');
  const off = rig({ on: ['windows'] }); await off.senses.sample(); assert.strictEqual(off.w.glances, 0);
  const co = rig({ changeOnly: true }); await co.senses.sample(); assert.strictEqual(co.w.glances, 1, 'change-only intake too');
});
test('private windows are dropped one by one, exactly like the screen sense', async () => {
  const r = rig({ items: [{ app: '1Password', title: 'Vault', text: 'password hunter2' }, { app: 'Safari', title: 'Chase - Online Banking login', text: 'account balance' }, { app: 'Notes', title: 'Groceries', text: 'milk eggs bread' }] });
  await r.senses.sample();
  const p = r.state.inbox.find((x) => x.sense === 'periphery');
  assert.match(p.text, /Notes — Groceries: "milk eggs bread"/); assert.doesNotMatch(p.text, /1Password|hunter2|Chase|balance/);
});
test('the chat hook: "what\'s in my other window?" carries the periphery line', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const re = new RegExp(/const OTHER_WINDOW_ASK = (\/.*\/i);/.exec(m)[1].slice(1, -2), 'i');
  for (const q of ["what's in my other window?", 'What is on my other screen', 'what am I looking at in the background window', 'summarize the second monitor']) assert.ok(re.test(q), q);
  for (const q of ['open a new window', 'what is on my screen?', 'hello']) assert.ok(!re.test(q), q);
  assert.match(m, /const msgs = withPeriphery\(msgs0\);/);
  assert.match(m, /periphery: store\.getSettings\(\)\.periphery === false \? null : async \(\) => \{[^\n]*\['glance', '--per', '150', '--max', '5'\]/);
});

test('no glance while the Mac is locked (front app loginwindow)', async () => {
  const r = rig(); r.w.open = 'x'; const orig = r.senses.o.samplers.windows; r.senses.o.samplers.windows = async () => 'Front app: loginwindow. Open: TextEdit — note.';
  await r.senses.sample(); assert.strictEqual(r.w.glances, 0); r.senses.o.samplers.windows = orig;
});
