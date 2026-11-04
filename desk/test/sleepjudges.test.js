'use strict';
// Sleep for the small judges (sleep track T1): the one engine (replay -> update -> seatbelt -> keep or roll back), the poisoned-night
// rollback, the three toy-proven parts (guesser fade rates, think-longer threshold, where to look), the break tracker, the scientist hook.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const SJ = require('../src/sleepjudges');
const { BreakTracker, BreakModel } = require('../src/breaks');
const { Scientist } = require('../src/scientist');
const { Checker } = require('../src/checker');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'judges-'));
function rng(s) { return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const DAY = 86400000, T0 = new Date(2026, 8, 7).getTime();

// a tiny binary judge: one rate p; logs are [{y}]
const ratePart = () => ({
  name: 'rate',
  score(m, log) { let L = 0, S = 0; for (const x of log) { const l = x.y ? -Math.log(m.p) : -Math.log(1 - m.p), li = x.y ? -Math.log(1 - m.p) : -Math.log(m.p); L += l; S += Math.sign(l - li); } return { loss: L / log.length, gap: S / log.length, model: m }; },
  candidates(train) { const all = [].concat(...train); const p = Math.min(0.98, Math.max(0.02, (all.filter((x) => x.y).length + 1) / (all.length + 2))); return [{ model: { p }, tag: 'p ' + p.toFixed(2) }]; },
  deploy: (c) => c.model
});
const day = (r, p, n) => Array.from({ length: n || 60 }, () => ({ y: r() < p ? 1 : 0 }));

test('engine: keeps an update that scores better on the held-out day, rolls back one that scores worse', () => {
  const r = rng(1), logs = { 1: day(r, 0.8), 2: day(r, 0.8) }, st = {};
  const a = SJ.night(ratePart(), st, logs, 1, { p: 0.5 }); assert.strictEqual(a.rec.action, 'first day');
  const b = SJ.night(ratePart(), st, logs, 2, { p: 0.5 });
  assert.strictEqual(b.rec.action, 'kept'); assert.ok(b.model.p > 0.6);
  // a current model that is already right beats a candidate trained on an odd older day -> rolled back, the live model stays
  const st2 = { admitted: [1], fitted: true, start: { p: 0.8 } }, logs2 = { 1: day(r, 0.55), 2: day(r, 0.8) };
  const c = SJ.night(ratePart(), st2, logs2, 2, { p: 0.8 });
  assert.strictEqual(c.rec.action, 'rolled back'); assert.strictEqual(c.model.p, 0.8);
});

test('engine: a poisoned (flipped) night is held, then quarantined when the next day looks like before; it never trains', () => {
  const r = rng(2), logs = {}, st = {}; let live = { p: 0.5 };
  for (let d = 1; d <= 8; d++) {
    logs[d] = day(r, 0.85); if (d === 5) logs[d] = logs[d].map((x) => ({ y: 1 - x.y }));   // every label flipped
    const out = SJ.night(ratePart(), st, logs, d, live); live = out.model;
    if (d === 5) assert.strictEqual(out.rec.action, 'hold');
    if (d === 6) assert.deepStrictEqual(out.rec.decided, { day: 5, admitted: false });
  }
  assert.ok(st.quarantined.includes(5)); assert.ok(!st.admitted.includes(5)); assert.ok(live.p > 0.75, 'still right after the poison');
  // a REAL change (two days in a row that contradict the model) is admitted and learned
  const st2 = {}; let l2 = { p: 0.5 }; const lg = {};
  for (let d = 1; d <= 10; d++) { lg[d] = day(r, d <= 5 ? 0.85 : 0.15); const o = SJ.night(ratePart(), st2, lg, d, l2); l2 = o.model; }
  // (with a judge that has no recency, a FULL reversal is held night after night until the new days outweigh the old ones; the days
  // are kept for training, none is thrown away, and the live model keeps learning online meanwhile)
  assert.ok(st2.admitted.includes(6) && st2.admitted.includes(8), 'the new routine joins training'); assert.strictEqual(st2.quarantined.length, 0, 'no real day is quarantined');
});

// minute rows {t, cat, work, sess, hour, soon} of a day with a work/break rhythm
function minutes(d, work, brk, cat) {
  const rows = []; let m = 540, sess = 0, w = true, left = work;
  while (m < 1380) {
    rows.push({ t: T0 + (d - 1) * DAY + m * 60000, cat: w ? cat(m) : 'other', work: w, sess: w ? sess : -1, hour: Math.floor(m / 60), soon: 0 });
    m++; sess++; left--; if (left <= 0) { w = !w; left = w ? work : brk; sess = 0; }
  }
  for (let i = 0; i < rows.length; i++) if (rows[i].work) for (let j = i + 1; j <= i + 5 && j < rows.length; j++) if (!rows[j].work && rows[j - 1].work) rows[i].soon = 1;
  return rows;
}

test('guesser part: the fade rate is learned per stream from the replay (a routine change -> it fades); runs in seconds', () => {
  const part = SJ.guesserPart(), logs = {}, st = {}, days = [];
  for (let d = 1; d <= 12; d++) logs[d] = minutes(d, d <= 8 ? 50 : 25, d <= 8 ? 10 : 5, (m) => (d <= 8 ? (m < 780 ? 'school' : 'code') : (m < 780 ? 'code' : 'game')));
  let live = { app: null, when: null, idle: null, k: { app: 0.8, when: 0.8, idle: 0.8 } }; const t0 = Date.now();
  // the app's live model = yesterday's model after learning today online (score() replays the day with the online updates)
  for (let d = 1; d <= 12; d++) { const today = part.score(JSON.parse(JSON.stringify(st.start || live)), logs[d]).model; const out = SJ.night(part, st, logs, d, today); live = out.model; days.push(out.rec); }
  const kept = days.filter((x) => x.action === 'kept');
  assert.ok(kept.length >= 6, JSON.stringify(days.map((x) => x.action)));
  const last = days[days.length - 1]; assert.match(last.tag, /keep app [\d.]+, when [\d.]+, idle [\d.]+/);
  assert.ok(Object.values(live.k).some((k) => k < 1), 'after the routine change some stream fades: ' + JSON.stringify(live.k));
  assert.ok(Date.now() - t0 < 30000, 'night replay took ' + (Date.now() - t0) + ' ms');
});

test('think-longer part: the threshold is fitted from logs (extra tries only help unsure first tries); thinkMore explores 10% above it', () => {
  const r = rng(3), logs = {};
  for (let d = 1; d <= 4; d++) logs[d] = Array.from({ length: 40 }, () => { const c = r(), r1 = r() < c ? 1 : 0, rK = r1 || (c < 0.5 && r() < 0.8) ? 1 : 0; return { c, r1, extra: 1, rK, pi: 1 }; });
  const st = {}; let live = SJ.thinkPart().init();
  for (let d = 1; d <= 4; d++) live = SJ.night(SJ.thinkPart(), st, logs, d, live).model;
  assert.ok(live.theta >= 0.3 && live.theta <= 0.7, 'theta ' + live.theta); assert.strictEqual(live.explore, true);
  assert.deepStrictEqual(SJ.thinkMore(live, 0.1), { extra: true, pi: 1 });
  assert.deepStrictEqual(SJ.thinkMore(live, 0.95, () => 0.5), { extra: false, pi: SJ.EPS });
  assert.deepStrictEqual(SJ.thinkMore(live, 0.95, () => 0.05), { extra: true, pi: SJ.EPS });
  assert.deepStrictEqual(SJ.thinkMore(null, 0.99), { extra: true, pi: 1 }, 'before any night: today\'s behaviour (always K tries)');
});

test('where to look: surprise rates per region, the early-wake budget in proportion (floor 2 each)', () => {
  const r = rng(4), logs = {}, st = {}; let live = SJ.wherePart().init();
  for (let d = 1; d <= 5; d++) { logs[d] = []; for (let i = 0; i < 60; i++) { logs[d].push({ r: 'code:terminal', y: r() < 0.4 ? 1 : 0 }); logs[d].push({ r: 'video:youtube', y: r() < 0.02 ? 1 : 0 }); } }
  for (let d = 1; d <= 5; d++) live = SJ.night(SJ.wherePart(), st, logs, d, live).model;
  const a = SJ.wakeAllowance(live, ['code:terminal', 'video:youtube']);
  assert.ok(a['code:terminal'] > 4 * a['video:youtube'], JSON.stringify(a)); assert.ok(a['video:youtube'] >= 2);
  assert.ok(Math.abs(a['code:terminal'] + a['video:youtube'] - 60) < 1e-9);
});

test('break tracker: a minute is labelled "break soon" when input stops within 5 min; breakSoon is null until it has data', () => {
  const rows = [], tr = new BreakTracker({ onRow: (x) => rows.push(x) }); let t = T0 + 9 * 3600000;
  for (let cyc = 0; cyc < 6; cyc++) { for (let i = 0; i < 20; i++) { tr.tick(t, 5, 'code'); t += 60000; } for (let i = 0; i < 5; i++) { tr.tick(t, 120 + i * 60, 'code'); t += 60000; } }
  const work = rows.filter((x) => x.work);
  assert.ok(work.length >= 100); assert.ok(work.filter((x) => x.soon).length >= 6 * 3, 'the last minutes before each break are labelled');
  assert.ok(work.filter((x) => x.sess < 10).every((x) => !x.soon), 'early minutes of a stretch are not');
  const fresh = new BreakTracker(); fresh.tick(t, 1, 'code'); assert.strictEqual(fresh.breakSoon(t), null);
  for (let i = 0; i < 16; i++) { tr.tick(t, 5, 'code'); t += 60000; }
  assert.ok(tr.breakSoon(t + 3 * 60000) > tr.breakSoon(t - 14 * 60000), 'later in a stretch = a break is more likely');
  const m = new BreakModel(tr.toJSON().model); m.decay(0.5); assert.ok(Math.abs(m.n() - tr.model.n() / 2) < 1e-9);
});

test('store: day logs in userData, one night per day, a diary line per part, poison quarantined, logs pruned to 40 days', () => {
  const dir = tmp(); let now = T0 + 22 * 3600000; const J = new SJ.SleepJudges({ dir, now: () => now }); const r = rng(5);
  let live = { p: 0.5 }, lines = [];
  for (let d = 0; d < 45; d++) {
    for (const x of day(r, 0.8, 40)) J.record('rate', { t: now, y: d === 20 ? 1 - x.y : x.y });
    const out = J.run(ratePart(), live); if (out) { live = out.model; lines.push(out.line); }
    assert.strictEqual(J.run(ratePart(), live), null, 'a second run the same night does nothing');
    now += DAY;
  }
  assert.match(lines[1], /^rate: kept \[p 0\.\d\d\], held-out \d\.\d\d -> \d\.\d\d/);
  assert.ok(lines.some((l) => /held \(today contradicts/.test(l))); assert.ok(lines.some((l) => /day \d+ quarantined/.test(l)));
  const J2 = new SJ.SleepJudges({ dir, now: () => now }); assert.strictEqual(J2.state('rate').quarantined.length, 1, 'state survives a restart');
  assert.ok(Object.keys(J2.days('rate')).length <= 40); assert.ok(fs.existsSync(path.join(dir, 'judge-logs', 'rate.jsonl')));
});

test('scientist: a confident first try stops (no extra tries) and logs (c, r1, extra, rK, pi); an unsure one makes all K tries', async () => {
  const fakeBox = { available: () => true, runPython: async () => ({ ok: true, stdout: 'TRUTH\n', stderr: '', exitCode: 0, ms: 2 }) };
  for (const [conf, want] of [[0.9, 1], [0.2, 4]]) {
    const dir = tmp(); let t = 1e12; const now = () => (t += 7); const rows = []; let calls = 0;
    const sci = new Scientist({ dir, checker: new Checker({ dir, now }), now, k: 4, sandbox: fakeBox, pythonOk: true,
      thinkMore: (c) => SJ.thinkMore({ theta: 0.5, explore: true }, c, () => 0.9), onTries: (x) => rows.push(x) });
    sci.startSession();
    const out = await sci.runOne({ ask: async () => { calls++; return JSON.stringify({ guess: calls === 1 ? 'wrong' : 'TRUTH', confidence: conf }); }, signal: new AbortController().signal, gateOk: () => true });
    assert.strictEqual(out.ran, true); assert.strictEqual(calls, want, 'model calls at confidence ' + conf);
    assert.strictEqual(rows.length, 1); assert.strictEqual(rows[0].r1, 0); assert.strictEqual(rows[0].extra, want > 1 ? 1 : 0);
    assert.strictEqual(rows[0].rK, want > 1 ? 1 : null); assert.strictEqual(rows[0].pi, want > 1 ? 1 : SJ.EPS);
  }
});

test('main: the judges run in the nightly jobs (no fixed 0.8 for the guesser), minute logging, wake budget; breakSoon NOT wired', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /const aoNightlyJobs = \[[^\n]*aoJudgesNight\(\)/); assert.ok(!/aoGuesser\.decay\(0\.8\)/.test(m));
  assert.match(m, /aoJudgeMinute\(\)/); assert.match(m, /aoLoop && aoWakeAllowed\(\)\) aoLoop\.wake\(\)/);
  assert.match(m, /logActivity\('sleep-part', \{ part: o\.rec\.part, line: o\.line \}\)/);
  assert.match(m, /thinkMore: \(c\) => JudgesMod\.thinkMore/); assert.match(m, /let aoBreakSoon = \(\) => null;/);
  // no Scientist option of the constructor sits inside a comment (the gameLog option was once swallowed by a trailing comment)
  const sci = m.slice(m.indexOf('const aoScientist = '), m.indexOf('}));', m.indexOf('const aoScientist = ')));
  for (const line of sci.split('\n')) assert.ok(!/\/\/.*\w+: [\w(]/.test(line), 'option inside a comment: ' + line.slice(0, 120));
  assert.match(sci, /gameLog: aoGameLog\(\),[^\n]*\n/);
});
