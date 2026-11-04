'use strict';
// T6: the watcher (src/watcher.js), a tiny net beside the guesser, trained only in sleep, with the seatbelt and rollback.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const W = require('../src/watcher');
const { rng } = require('../src/tinynet');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'watcher-'));
const T0 = new Date(2026, 10, 4, 15, 0, 0).getTime();

// a synthetic day of rows: chat pings with Ben's name are the useful moments; group-chat pings without it, app flicker and static are not
function synthDay(seed, seconds, poison) {
  const r = rng(seed), rows = [];
  let app = 'code';
  for (let s = 0; s < seconds; s++) {
    if (r() < 1 / 300) app = ['code', 'browser', 'video', 'chat'][Math.floor(r() * 4)];
    const row = { t: T0 + s * 1000, app: r() < 0.01 ? 'other' : app, screen: app === 'video' ? 'video' : app === 'code' ? 'code' : 'reading', sound: 'quiet',
      diff: r() * 0.1, level: 0.1, fErr: 0, fDead: 0, fName: 0, fQ: 0, seen: 0, kl: r() < 0.05 ? r() * 3 : 0.01, y: 0 };
    rows.push(row);
  }
  for (let s = 30; s < seconds - 10; s += 60 + Math.floor(r() * 120)) {
    const useful = r() < 0.4;
    for (let k = 0; k < 3; k++) Object.assign(rows[s + k], { screen: 'chat', diff: 0.4, fName: useful ? 1 : 0, fQ: 1, y: useful ? 1 : 0 });
  }
  const vec = W.vectors(rows);
  return { day: 'd' + seed, items: rows.map((row, i) => ({ x: vec[i], y: poison && r() < poison ? 1 - row.y : row.y, next: W.SCREEN.indexOf((rows[i + 1] || row).screen), sur: row.kl, t: row.t })) };
}

test('the featurizer stores numbers only, flags keywords and notices a repeated screen', () => {
  const f = new W.Featurizer();
  const a = f.row({ t: T0, app: 'code', screenText: 'TypeError: x is undefined', soundText: '', kl: 0.2 });
  assert.strictEqual(a.fErr, 1); assert.strictEqual(a.screen, 'error'); assert.strictEqual(a.seen, 0);
  assert.ok(!Object.values(a).some((v) => typeof v === 'string' && v.length > 12), 'no text is kept in a row');
  f.row({ t: T0 + 1000, app: 'code', screenText: 'const a = 1;', soundText: '' });
  const c = f.row({ t: T0 + 2000, app: 'code', screenText: 'TypeError: x is undefined', soundText: '' });
  assert.strictEqual(c.seen, 1, 'the same error text again within 10 min is a repeat');
  const d = f.row({ t: T0 + 3000, app: 'chat', screenText: 'Ben, are you coming to the meeting tomorrow?', soundText: '' });
  assert.strictEqual(d.fName, 1); assert.strictEqual(d.fDead, 1); assert.strictEqual(d.fQ, 1);
  assert.strictEqual(W.vectors([a, c, d])[0].length, W.N);
});

test('with no model it only logs: no score, never wakes', () => {
  const dir = tmp(); let now = T0;
  const w = new W.Watcher({ dir, now: () => now });
  for (let i = 0; i < 70; i++) { now += 1000; const r = w.observe({ app: 'code', screenText: 'x' + (i % 3), kl: 0 }); assert.strictEqual(r.wake, false); assert.strictEqual(r.score, null); }
  w.flush();
  const f = fs.readdirSync(path.join(dir, 'watcher')).find((n) => n.startsWith('rows-'));
  assert.ok(f, 'rows were logged');
});

test('night 1: kept only when it beats the guesser surprise on held-out; then it wakes on the useful kind and not on look-alikes', () => {
  const dir = tmp(); let now = T0 + 86400000;
  const w = new W.Watcher({ dir, now: () => now, cfg: { steps: 800 } });
  const res = w.nightly({ days: [synthDay(1, 7200)] });
  assert.strictEqual(res.kept, true, JSON.stringify(res));
  assert.strictEqual(res.against, 'guesser surprise');
  assert.ok(res.apLatest.cand > res.apLatest.old);
  assert.ok(fs.existsSync(path.join(dir, 'watcher', 'model.json')));
  // a fresh watcher loads it from disk
  const w2 = new W.Watcher({ dir, now: () => now }); assert.ok(w2.ready());
  const quiet = []; for (let i = 0; i < 40; i++) { now += 1000; quiet.push(w2.observe({ app: 'code', screenText: 'const a = ' + (i % 2), kl: 0 })); }
  now += 1000; const spam = w2.observe({ app: 'code', screenText: 'group chat: anyone up for lunch?', kl: 0 });
  now += 15000; const ping = w2.observe({ app: 'code', screenText: 'Ben can you look at this?', kl: 0 });
  assert.ok(ping.score > spam.score, 'a direct question to Ben scores above group-chat spam');
  assert.ok(ping.score > Math.max(...quiet.map((q) => q.score)));
  assert.ok(quiet.filter((q) => q.wake).length <= 1, 'quiet coding does not keep waking the brain');
});

test('seatbelt: a 60%-poisoned night is rolled back; a clean night may be kept; rollback() restores the previous model', () => {
  const dir = tmp(); let now = T0 + 86400000;
  const w = new W.Watcher({ dir, now: () => now, cfg: { steps: 800 } });
  const d1 = synthDay(1, 7200), d2 = synthDay(2, 7200);
  assert.strictEqual(w.nightly({ days: [d1] }).kept, true);
  now += 86400000; const before = JSON.stringify(w.model.toJSON());
  // "caught" (the toy's registered rule) = rolled back, OR kept but harmless on a clean fresh day
  const { averagePrecision } = require('../src/tinynet');
  const fresh = synthDay(9, 3600), apOf = (net) => averagePrecision(fresh.items.map((i) => net.forward(i.x).o[0]), fresh.items.map((i) => i.y));
  const apBefore = apOf(w.model);
  const bad = w.nightly({ days: [d1, synthDay(3, 7200, 0.6)] });
  if (!bad.kept) assert.strictEqual(JSON.stringify(w.model.toJSON()), before, 'the model is unchanged after a rejected night');
  else assert.ok(apOf(w.model) >= apBefore - 0.05, 'a kept poisoned night must be harmless: ' + apOf(w.model) + ' vs ' + apBefore);
  // an INVERTED night (every label wrong) is never kept
  now += 86400000; const before2 = JSON.stringify(w.model.toJSON());
  const inv = w.nightly({ days: [d1, synthDay(4, 7200, 1)] });
  assert.strictEqual(inv.kept, false, JSON.stringify(inv)); assert.strictEqual(JSON.stringify(w.model.toJSON()), before2);
  now += 86400000; const good = w.nightly({ days: [d1, d2] });
  if (good.kept) { const prevJ = JSON.parse(fs.readFileSync(path.join(dir, 'watcher', 'model.prev.json'), 'utf8')); assert.ok(w.rollback()); assert.strictEqual(JSON.stringify(w.model.toJSON()), JSON.stringify(prevJ.net)); }
  const log = fs.readFileSync(path.join(dir, 'watcher', 'nightly.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.ok(log.length >= 3 && log.every((l) => typeof l.kept === 'boolean' || l.kind === 'watcher-rollback'));
});

test('labels come from what happened: a tick that read the seconds + a 👍 later = useful; a tick with nothing = not useful', () => {
  const dir = tmp(); let now = T0;
  const w = new W.Watcher({ dir, now: () => now });
  for (let i = 0; i < 120; i++) { now += 1000; w.observe({ app: 'chat', screenText: i === 50 ? 'Ben are you there?' : 'group chat ' + Math.floor(i / 10), kl: 0 }); }
  w.tickRead(T0, T0 + 60000, null, false);              // the first minute: the tick said nothing
  w.tickRead(T0 + 60001, T0 + 120000, 'say:abc', null);  // the second minute: it said something...
  w.outcome('say:abc', true);                            // ...and Ben gave it a 👍
  const days = w.labelledDays();
  assert.strictEqual(days.length, 1);
  const pos = days[0].items.filter((i) => i.y), neg = days[0].items.filter((i) => !i.y);
  assert.ok(pos.length >= 1 && neg.length > 10);
  assert.ok(pos.every((i) => i.t > T0 + 60000), 'only seconds from the useful tick are positive');
  assert.strictEqual(w.nightly().kept, false, 'too few useful moments: nothing is trained');
});
