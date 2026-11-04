'use strict';
// Always-on v2 phase 1: where Glim's unprompted words go, the ear icon, 👍 / 👎, and never while Ben types.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const V = require('../src/glimvoice');
const { PillState } = require('../src/pillstate');
const read = (f) => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('route: notched -> notch, no notch -> pill, "Use the notch" off -> a macOS notification', () => {
  assert.strictEqual(V.route({ useNotch: true, notched: true }), 'notch');
  assert.strictEqual(V.route({ useNotch: true, notched: false }), 'pill');
  assert.strictEqual(V.route({ useNotch: false, notched: true }), 'notification');
  assert.strictEqual(V.route({ useNotch: false, notched: false }), 'notification');
  assert.strictEqual(V.route({ useNotch: true, notched: false, pillOn: false }), 'notification');
});

function rig(o) {
  let t = 1e6, typing = false; const got = { notch: [], pill: [], notification: [], chat: [] }, outcomes = [];
  const v = new V.Voice({ now: () => t, typing: () => typing, where: () => (o && o.where) || 'notch',
    outlets: { notch: (m) => got.notch.push(m), pill: (m) => got.pill.push(m), notification: (m) => got.notification.push(m), chat: (m) => got.chat.push(m) },
    onOutcome: (m, k) => outcomes.push(k) });
  return { v, got, outcomes, adv: (ms) => { t += ms; }, type: (b) => { typing = b; } };
}

test('the notch-off setting routes a message to a notification (and it is kept in chat)', () => {
  const r = rig({ where: V.route({ useNotch: false, notched: true }) });
  r.v.offer('Your quiz starts in 10 minutes.');
  assert.strictEqual(r.got.notification.length, 1); assert.strictEqual(r.got.notch.length, 0); assert.strictEqual(r.got.chat.length, 1);
});

test('nothing is delivered while Ben is typing; it goes out after a pause, or is dropped after 2 minutes', () => {
  const r = rig();
  r.type(true); r.v.offer('hello');
  for (let i = 0; i < 30; i++) { r.adv(1000); r.v.pump(); }
  assert.strictEqual(r.got.notch.length, 0, 'held while typing');
  r.type(false); r.adv(1000); r.v.pump();
  assert.strictEqual(r.got.notch.length, 0, 'still inside the quiet gap right after typing');
  r.adv(V.QUIET_MS); r.v.pump();
  assert.strictEqual(r.got.notch.length, 1, 'delivered after the pause');
  r.type(true); r.v.offer('second');
  for (let i = 0; i < 125; i++) { r.adv(1000); r.v.pump(); }
  r.type(false); r.adv(10000); r.v.pump();
  assert.strictEqual(r.got.notch.length, 1, 'dropped, not delivered late');
  assert.strictEqual(r.v.stats.droppedTyping, 1);
});

test('👍 / 👎 / "not now" in chat / ignored for 10 minutes all become outcomes, once each', () => {
  const r = rig();
  const a = r.v.offer('a'); r.v.feedback(a.id, 'up'); r.v.feedback(a.id, 'down');
  const b = r.v.offer('b'); r.v.feedback(b.id, 'down');
  r.v.offer('c'); r.v.onBenChat('not now please');
  r.v.offer('d'); r.v.onBenChat('oh thanks, what is it?');
  r.v.offer('e'); r.adv(V.IGNORE_MS + 1); r.v.sweep();
  assert.deepStrictEqual(r.outcomes, ['up', 'down', 'notnow', 'reply', 'ignored']);
  for (const w of ['shh', 'Later.', 'stop', 'not now']) assert.ok(V.NOT_NOW.test(w), w);
  assert.ok(!V.NOT_NOW.test('what is the capital of France'));
});

test('status icon: resting, learning with Motes and score, thinking, surprised; hover detail', () => {
  const now = 5e6;
  assert.strictEqual(V.statusIcon({ now }).icon, '😴');
  const l = V.statusIcon({ now, learning: { topic: 'black holes', levels: [{ level: 1, pct: 81 }] }, motes: 3 });
  assert.strictEqual(l.icon, '📚'); assert.strictEqual(l.text, '📚 3'); assert.strictEqual(l.detail, '📚 black holes · Lv1 81% · 3 Motes');
  assert.strictEqual(V.statusIcon({ now, thinking: true, learning: { topic: 'x' } }).icon, '💭');
  assert.strictEqual(V.statusIcon({ now, thinking: true, surprisedAt: now - 1000 }).icon, '😲');
  assert.strictEqual(V.statusIcon({ now, surprisedAt: now - V.SURPRISE_SHOW_MS - 1 }).icon, '😴');
  assert.match(V.statusIcon({ now, motes: 2, gauge: 'red' }).detail, /memory tight/);
});

test('the pill shows a say with its id, keeps it ~45 s, then lets it go', () => {
  let t = 0; const p = new PillState({ now: () => t, showHelpers: () => false });
  p.say({ id: 'say-1', text: 'You have seen this error 3 times. Want help?' });
  const v = p.view(); assert.ok(v.visible); assert.strictEqual(v.top.say.id, 'say-1'); assert.strictEqual(v.top.key, 'glim-say');
  t += 30000; p.tick(); assert.ok(p.view().visible);
  t += 20000; p.tick(); assert.strictEqual(p.view().visible, false);
});

test('wiring: pill buttons, chat 👍/👎 row, Settings toggle, main routes through the voice and feeds chat replies back', () => {
  const pj = read('renderer/pill.js'), m = read('main.js'), app = read('renderer/app.js'), html = read('renderer/pill.html');
  assert.match(pj, /'👎 Not now'/); assert.match(pj, /P\.act\('aoSay', \{ id: t\.say\.id, kind: 'up'/);
  assert.match(html, /id="ear"/);
  assert.match(app, /key: 'useNotch', type: 'toggle', label: 'Use the notch'/);
  assert.match(app, /aoRow\(ev\.sayId\)/);
  assert.match(m, /function aoSay\(text, d\) \{ aoVoice\.offer\(/);
  assert.match(m, /aoVoice\.onBenChat\(text\)/);
  assert.match(m, /case 'aoSay':/);
  assert.match(m, /v\.ear = aoEar\(\)/);
  assert.strictEqual(require('../src/store').DEFAULT_SETTINGS.useNotch, true);
});

test('UI2: a proactive message in the chat rates with the same outline thumb icons as a normal reply (no emoji)', () => {
  const app = require('fs').readFileSync(require('path').join(__dirname, '../renderer/app.js'), 'utf8');
  const ao = app.slice(app.indexOf('function aoRow('), app.indexOf('function onAssistantEnd('));
  assert.ok(!/👍|👎/.test(ao), 'no emoji');
  assert.match(ao, /b\.innerHTML = svg\(THUMB\)/);
  assert.match(ao, /'rate-b ao-b' \+ \(kind === 'down' \? ' down' : ''\)/);
  assert.match(ao, /mk\('up', 'Good time to tell me'\), mk\('down', 'Not now'\)/);
  const rate = app.slice(app.indexOf('function rateRow('), app.indexOf('function aoRow('));
  assert.match(rate, /b\.innerHTML = svg\(THUMB\)/);
});
