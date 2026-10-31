'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Rhythm, learnedWindow, dayOf, median } = require('../src/rhythm');
const { effectiveWindow, shouldAutoSleep, wakeKey, computeWakeAt, shouldAutoWake } = require('../src/sleep');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'rhythm-'));
const at = (h, m, d, mo) => new Date(2026, (mo || 10) - 1, d, m === undefined ? 0 : h, m === undefined ? h : m);
const T = (d, h, m) => new Date(2026, 9, d, h, m || 0);
// feed one day's worth of "active" samples: first and last minute-of-day (last may be after midnight: next calendar day)
function day(r, d, first, last) { // first 'H:MM' on day d; last 'H:MM' on d (>= 4:00) or on d+1 (< 4:00)
  const p = (s, dd) => { const [h, m] = s.split(':').map(Number); return T(dd, h, m); };
  r.record(p(first, d), true);
  const [lh] = last.split(':').map(Number);
  r.record(p(last, lh < 4 ? d + 1 : d), true);
}

test('median: odd, even', () => { assert.strictEqual(median([5, 1, 3]), 3); assert.strictEqual(median([1, 2, 3, 10]), 2.5); });

test('a day runs 04:00 to 04:00: 01:30 belongs to the evening before', () => {
  assert.deepStrictEqual(dayOf(T(10, 1, 30)), { key: '2026-10-09', min: 1530 });
  assert.deepStrictEqual(dayOf(T(10, 3, 59)), { key: '2026-10-09', min: 1679 });
  assert.deepStrictEqual(dayOf(T(10, 4, 0)), { key: '2026-10-10', min: 240 });
  assert.deepStrictEqual(dayOf(T(10, 23, 15)), { key: '2026-10-10', min: 1395 });
});

test('record keeps the first and last active minute per day; inactive samples are ignored', () => {
  const r = new Rhythm(null);
  assert.strictEqual(r.record(T(10, 9, 0), false), false);
  r.record(T(10, 9, 0), true); r.record(T(10, 7, 30), true); r.record(T(10, 22, 10), true); r.record(T(10, 12, 0), true); r.record(T(11, 0, 45), true);
  assert.deepStrictEqual(r.days['2026-10-10'], { first: 450, last: 1485 });
  assert.strictEqual(Object.keys(r.days).length, 1);
});

const NOW = T(20, 12, 0); // midday: every record below is a finished day
const feed = (r, firsts, lasts, d0) => lasts.forEach((l, i) => day(r, (d0 || 1) + i, firsts[i % firsts.length], l));

test('learned: typical evening end and morning start, midnight crossing, evening end rounded up to the half hour', () => {
  const r = new Rhythm(null);
  feed(r, ['7:00'], ['23:10', '23:40', '0:20', '23:50', '0:05', '23:30']); // sorted 1390 1410 1420 1430 1445 1460 -> median 1425 -> 00:00
  assert.deepStrictEqual(r.learned(NOW), { from: '00:00', to: '05:45', days: 6 });
  const q = new Rhythm(null); feed(q, ['6:40'], ['23:05', '23:20', '23:10', '23:35', '23:25']); // median 23:20 -> 23:30
  assert.deepStrictEqual(q.learned(NOW), { from: '23:30', to: '05:45', days: 5 });
});

test('learned: clamps late morning ends to 05:45', () => {
  const a = new Rhythm(null); feed(a, ['9:30'], ['20:00', '21:30', '19:15', '22:00', '21:00']); // median 21:00
  assert.deepStrictEqual(a.learned(NOW), { from: '21:00', to: '05:45', days: 5 });
  const b = new Rhythm(null); feed(b, ['16:00'], ['14:00', '15:00', '13:00', '14:30', '15:30']); // clamps: 18:00 and 14:00
  assert.deepStrictEqual(b.learned(NOW), { from: '18:00', to: '05:45', days: 5 });
  const c = new Rhythm(null); feed(c, ['4:10'], ['23:00', '23:00', '23:00', '23:00', '23:00']); // too early a riser: 05:00
  assert.deepStrictEqual(c.learned(NOW), { from: '23:00', to: '05:00', days: 5 });
});

test('learned: a late night that cannot fit three hours has no window', () => {
  const a = new Rhythm(null); feed(a, ['5:30'], ['3:30', '3:40', '3:20', '3:50', '3:35']); // median 03:35 -> 04:00
  assert.strictEqual(a.learned(NOW), null); // 05:30 is under 3 h after 04:00
  const b = new Rhythm(null); feed(b, ['4:15'], ['1:10', '1:20', '1:00', '1:25', '1:05']); // median 01:10 -> 01:30; 4:15 is 2h45 later -> 05:00 then
  assert.deepStrictEqual(b.learned(NOW), { from: '01:30', to: '05:00', days: 5 });
});

test('learned: thin data gives null, today is not counted, and one odd night does not move the median', () => {
  const r = new Rhythm(null); feed(r, ['7:00'], ['23:30', '23:30', '23:30', '23:30']);
  assert.strictEqual(r.learned(NOW), null);
  assert.strictEqual(r.learned(T(5, 12, 0)), null); // days 1-4 only: the 5th record is on the 5th itself... still unfinished
  r.record(T(20, 9, 0), true);               // today's partial record does not count
  assert.strictEqual(r.learned(NOW), null);
  day(r, 5, '7:00', '3:00');                  // an odd late night is the 5th finished day: median is still 23:30
  assert.deepStrictEqual(r.learned(NOW), { from: '23:30', to: '05:45', days: 5 });
  assert.strictEqual(new Rhythm(null).learned(NOW), null);
  assert.strictEqual(learnedWindow(null, NOW), null);
});

test('learned: the evening in progress is not mistaken for a finished day (01:00 still belongs to yesterday)', () => {
  const r = new Rhythm(null); feed(r, ['7:00'], ['23:30', '23:30', '23:30', '23:30', '23:30'], 1);
  r.record(T(7, 23, 50), true); r.record(T(8, 1, 0), true); // the 7th evening, still going at 01:00 on the 8th
  assert.strictEqual(r.learned(T(8, 1, 5)).days, 5);       // days 1-5 finished + day 6 had no record; the 7th is open
  assert.strictEqual(r.learned(T(8, 5, 0)).days, 6);       // after 04:00 the 7th is finished
});

test('records persist atomically, keep 21 days, and a damaged file is ignored', () => {
  const dir = tmp(), f = path.join(dir, 'rhythm.json');
  const r = new Rhythm(f);
  for (let d = 1; d <= 25; d++) r.record(new Date(2026, 8, d, 9, 0), true);
  const back = new Rhythm(f);
  assert.strictEqual(Object.keys(back.days).length, 21);
  assert.ok(back.days['2026-09-25'] && !back.days['2026-09-04'] && back.days['2026-09-05']);
  assert.deepStrictEqual(fs.readdirSync(dir), ['rhythm.json']); // no .tmp left behind
  fs.writeFileSync(f, '{nope'); assert.deepStrictEqual(new Rhythm(f).days, {});
  fs.writeFileSync(f, JSON.stringify({ days: { '2026-10-01': { first: 'x', last: 5 }, bad: { first: 1, last: 2 }, '2026-10-02': { first: 600, last: 700 } } }));
  assert.deepStrictEqual(Object.keys(new Rhythm(f).days), ['2026-10-02']);
  const same = new Rhythm(f); // a sample inside the known first..last span changes nothing, so nothing is written
  assert.strictEqual(same.record(T(2, 11, 0), true), false); assert.strictEqual(same.record(T(2, 9, 0), true), true);
  assert.strictEqual(new Rhythm(f).days['2026-10-02'].first, 540);
});

// ---- auto-sleep with a learned window ----
const S = { autoSleep: true, sleepAdapt: true, sleepFrom: '23:00', sleepTo: '08:00', sleepIdleMin: 120, wakeAt: false };
const L = { from: '00:30', to: '07:00', days: 8 };
const base = { settings: S, learned: L, now: T(27, 1, 0), idleMs: 121 * 60000, systemIdleMs: 121 * 60000, runActive: false, gatewayBusy: false, windowFocused: false, asleep: false, available: true };
const d = (o) => shouldAutoSleep({ ...base, ...o });

test('effectiveWindow: learned only when sleepAdapt is on and there is one', () => {
  assert.deepStrictEqual(effectiveWindow(S, L), { from: '00:30', to: '07:00', learned: true });
  assert.deepStrictEqual(effectiveWindow(S, null), { from: '23:00', to: '08:00', learned: false });
  assert.deepStrictEqual(effectiveWindow({ ...S, sleepAdapt: false }, L), { from: '23:00', to: '08:00', learned: false });
});

test('auto-sleep follows the learned window, and needs 2 hours of inactivity', () => {
  assert.ok(d({}).sleep); assert.strictEqual(d({}).key, '2026-10-27');
  assert.ok(!d({ now: T(26, 23, 45) }).sleep);                       // inside the Settings window, before the learned one
  assert.strictEqual(d({ now: T(26, 23, 45) }).reason, 'outside the night window');
  assert.ok(d({ now: T(26, 23, 45), settings: { ...S, sleepAdapt: false } }).sleep); // adapt off: the Settings window
  assert.ok(!d({ now: T(27, 7, 30) }).sleep);                        // after the learned end, though Settings run to 08:00
  assert.ok(!d({ now: T(27, 7, 30), learned: null }).sleep);          // no learned window yet: Settings window
  assert.ok(!d({ idleMs: 119 * 60000 }).sleep); assert.ok(!d({ systemIdleMs: 119 * 60000 }).sleep);
  assert.ok(d({ idleMs: 120 * 60000, systemIdleMs: 120 * 60000 }).sleep);
  assert.ok(!d({ settings: { ...S, sleepIdleMin: undefined }, idleMs: 100 * 60000, systemIdleMs: 100 * 60000 }).sleep); // the fallback is 2 h too
  assert.ok(!d({ lastKey: '2026-10-27' }).sleep);                    // Ben woke it tonight: not again
});

test('wake key, wake time and auto-wake use the same effective window', () => {
  const st = S;
  assert.strictEqual(wakeKey({ sleepKey: null, now: T(27, 1, 0), settings: st, learned: L }), '2026-10-27');
  assert.strictEqual(wakeKey({ sleepKey: null, now: T(26, 23, 45), settings: st, learned: L }), null); // not yet night by the learned window
  assert.strictEqual(wakeKey({ sleepKey: null, now: T(26, 23, 45), settings: st }), '2026-10-26');
  assert.strictEqual(computeWakeAt(T(27, 1, 0), 'morning', st, L), T(27, 7, 0).getTime());
  assert.strictEqual(computeWakeAt(T(27, 1, 0), 'morning', st), T(27, 8, 0).getTime());
  const w = (o) => shouldAutoWake({ settings: { ...S, wakeAt: true }, learned: L, now: T(27, 7, 5), asleep: true, startedAuto: true, ...o }).wake;
  assert.ok(w({})); assert.ok(!w({ learned: null }));               // by Settings the night runs to 08:00
});
