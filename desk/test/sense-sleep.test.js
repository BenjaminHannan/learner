'use strict';
// Sleep for the senses (design section 9, toy track T4): features-only store, anchored practice, 2-of-3 gate, echo guard, seatbelt.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/sense-sleep');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sense-sleep-'));
const vec = (n, seed = 1) => Array.from({ length: n }, (_, i) => Math.sin(i * 0.37 + seed));
const T0 = Date.parse('2026-11-04T15:00:00Z');
const ENC = { eye: 'siglip2-base-p16-256@last/pool2x2', ear: 'whisper-small@enc/pool4' };
const CAT = { dog: 'pets', cat: 'pets', wolf: 'wild', bear: 'wild', car: 'road', bus: 'road' };
const categoryOf = (t) => { const m = /\b(dog|cat|wolf|bear|car|bus)s?\b/i.exec(t || ''); return m ? CAT[m[1].toLowerCase()] : null; };
const word = (t) => (/\b(dog|cat|wolf|bear|car|bus)s?\b/i.exec(t || '') || [])[1];
const agree = (a, b) => !!word(a) && word(a) === word(b);

test('float16 round trip keeps features to ~3 significant digits', () => {
  const v = [0, 1, -1, 0.1234, -3.75, 1000.5, 1e-5, 65000];
  const back = S.decodeF16(S.encodeF16(v));
  v.forEach((x, i) => assert.ok(Math.abs(back[i] - x) <= Math.max(1e-3 * Math.abs(x), 1e-4), x + ' -> ' + back[i]));
});

test('only encoder features and short text are stored: raw media fields are refused, private text dropped', () => {
  const dir = tmp(), st = new S.FeatureStore(dir, { isPrivate: (t) => /password/i.test(t) });
  for (const bad of [{ image: 'x' }, { audio: [1, 2] }, { png: 'b64' }, { wav: 'b64' }, { pixels: [1] }])
    assert.throws(() => st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8) }, ...bad }), /raw media/);
  assert.throws(() => st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8), jpeg: 'x' } }), /raw media/);
  assert.throws(() => st.add({ t: T0, eye: { encoder: ENC.eye, vec: Buffer.from([1, 2]) } }), /number array/);
  assert.throws(() => st.add({ t: T0, eye: { encoder: ENC.eye, vec: [1, NaN] } }), /non-finite/);
  assert.throws(() => st.add({ t: T0, eye: { vec: vec(8) } }), /encoder id/);
  assert.deepStrictEqual(st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8) }, text: { screen: 'Enter your password' } }), { stored: false, reason: 'private' });
  const r = st.add({ t: T0, clip: 'yt:abc', frame: 2, eye: { encoder: ENC.eye, vec: vec(16), shape: [4, 4] }, ear: { encoder: ENC.ear, vec: vec(8, 2) }, text: { soundTag: '[dog barks]' }, ctx: { category: 'pets' } });
  assert.strictEqual(r.stored, true);
  const recs = st.records('2026-11-04');
  assert.strictEqual(recs.length, 1);
  assert.deepStrictEqual(Object.keys(recs[0]).sort(), ['clip', 'ctx', 'ear', 'eye', 'frame', 'id', 'source', 't', 'text']);
  const back = st.vector('2026-11-04', recs[0].ear);
  assert.ok(Math.abs(back[3] - vec(8, 2)[3]) < 1e-3);
  // on disk: one .bin of float16 (16 + 8 values x 2 bytes) + one index line, nothing else
  assert.deepStrictEqual(fs.readdirSync(path.join(dir, S.DIR)).sort(), ['features-2026-11-04.bin', 'features-2026-11-04.jsonl']);
  assert.strictEqual(fs.statSync(path.join(dir, S.DIR, 'features-2026-11-04.bin')).size, 48);
});

test('daily caps hold (records and bytes)', () => {
  const st = new S.FeatureStore(tmp(), { maxRecords: 3, maxBytes: 100 });
  for (let i = 0; i < 3; i++) assert.strictEqual(st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8) } }).stored, true);
  assert.strictEqual(st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8) } }).reason, 'day full (records)');
  const st2 = new S.FeatureStore(tmp(), { maxBytes: 20 });
  assert.strictEqual(st2.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(16) } }).reason, 'day full (bytes)');
});

function day(dir) {
  const st = new S.FeatureStore(dir);
  const add = (o) => st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8) }, ear: { encoder: ENC.ear, vec: vec(8, 3) }, ...o });
  add({ text: { subtitle: 'the dog is barking at the mailman' }, ctx: { category: 'pets' } });   // ear speech
  add({ text: { soundTag: '[wolf howls]' }, ctx: { category: 'wild' } });                        // ear sound
  add({ text: { screen: 'BUS 42 to Downtown' }, ctx: { category: 'road' } });                   // eye reading
  add({ text: { soundTag: '[dog barks]' }, ctx: { category: 'wild' } });                         // fails the logic check (dog is not wild)
  add({ text: { caption: 'maybe a bear' }, ctx: { category: 'wild' } });                         // a maybe never trains
  add({ text: {}, ctx: { category: 'pets' } });                                                  // no text
  st.add({ t: T0, eye: { encoder: 'old-encoder', vec: vec(8) }, text: { screen: 'car park' } });  // stale encoder
  return st.records('2026-11-04');
}

test('anchored practice: routing, logic check, maybe never trains, stale encoder features are skipped', () => {
  const recs = day(tmp());
  const p = S.buildPractice(recs, { categoryOf, encoders: ENC });
  assert.deepStrictEqual(p.ear.map((x) => [x.kind, x.label]), [['speech', 'the dog is barking at the mailman'], ['sound', 'wolf howls']]);
  assert.deepStrictEqual(p.eye.map((x) => [x.kind, x.label]), [['reading', 'BUS 42 to Downtown']]);
  assert.strictEqual(p.stats.rejected_logic, 2);
  assert.strictEqual(p.stats.stale, 1);
  assert.ok([...p.eye, ...p.ear].every((x) => x.from === 'text'));
  // an injected logic check (the real Nanbeige check) can veto anything
  assert.strictEqual(S.buildPractice(recs, { logicCheck: () => false, encoders: ENC }).ear.length, 0);
});

test('echo guard: without text the senses never teach each other unless the 2-of-3 rule is switched on', () => {
  const st = new S.FeatureStore(tmp());
  for (let i = 0; i < 30; i++) st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8, i) }, ear: { encoder: ENC.ear, vec: vec(8, i) }, ctx: { category: 'wild' } });
  const recs = st.records('2026-11-04');
  const guesses = Object.fromEntries(recs.map((r) => [r.id, { eye: 'a dog', ear: 'a dog' }]));   // the shared wolf->dog mistake
  for (const twoOfThree of [false, true]) {
    const p = S.buildPractice(recs, { categoryOf, agree, guesses, twoOfThree, encoders: ENC });
    assert.strictEqual(p.eye.length + p.ear.length, 0, 'twoOfThree=' + twoOfThree);
  }
  const p = S.buildPractice(recs, { categoryOf, agree, guesses, twoOfThree: true, encoders: ENC });
  assert.strictEqual(p.maybe.length, 30, 'senses agreeing against the title become maybes');
});

test('2-of-3: the odd sense learns only through a direction that proved >= 80 % right on the day\'s text-anchored clips', () => {
  const build = (earRight) => {
    const st = new S.FeatureStore(tmp()), guesses = {};
    // 25 clips with a sound tag where the rule fires for the ear (eye fits the title, ear does not)
    for (let i = 0; i < 25; i++) {
      const r = st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8, i) }, ear: { encoder: ENC.ear, vec: vec(8, i) }, text: { soundTag: i < earRight ? '[wolf howls]' : '[bear growls]' }, ctx: { category: 'wild' } });
      guesses[r.id] = { eye: 'a wolf', ear: 'a car' };
    }
    // 10 clips with no text where the rule would teach the ear
    for (let i = 0; i < 10; i++) {
      const r = st.add({ t: T0, eye: { encoder: ENC.eye, vec: vec(8, 100 + i) }, ear: { encoder: ENC.ear, vec: vec(8, 100 + i) }, ctx: { category: 'wild' } });
      guesses[r.id] = { eye: 'a wolf', ear: 'a bus' };
    }
    return S.buildPractice(st.records('2026-11-04'), { categoryOf, agree, guesses, twoOfThree: true, encoders: ENC });
  };
  const good = build(23);   // 23/25 = 92 %
  assert.strictEqual(good.stats.gate.open.ear, true);
  assert.strictEqual(good.ear.filter((x) => x.kind === '2of3').length, 10);
  assert.ok(good.ear.filter((x) => x.kind === '2of3').every((x) => x.label === 'a wolf' && x.from === 'eye'));
  const bad = build(15);    // 15/25 = 60 %
  assert.strictEqual(bad.stats.gate.open.ear, false);
  assert.strictEqual(bad.ear.filter((x) => x.kind === '2of3').length, 0);
  assert.strictEqual(bad.stats.gate.open.eye, false, 'a direction with < 20 measured cases stays shut');
});

test('seatbelt: any fixed test dropping > 2 points, or a missing score, undoes the night', () => {
  const b = { V1: 67.6, A1: 30.2, VID1: 56.7 };
  assert.strictEqual(S.decideNight(b, { V1: 66.0, A1: 35, VID1: 55.0 }).keep, true);
  assert.strictEqual(S.decideNight(b, { V1: 65.5, A1: 40, VID1: 60 }).keep, false);
  assert.match(S.decideNight(b, { V1: 65.5, A1: 40, VID1: 60 }).reason, /V1 dropped 2.1/);
  assert.strictEqual(S.decideNight(b, { V1: 70, A1: 40 }).keep, false, 'VID1 missing after');
  assert.strictEqual(S.decideNight({ V1: 67.6 }, { V1: 67.6, A1: 1 }).keep, true, 'tests not measured before are not judged');
});

test('ledger: manifest by reference, rollback quarantines the night so it is never replayed, kept days are pinned', () => {
  const dir = tmp(), recs = day(dir), L = new S.NightLedger(dir), st = new S.FeatureStore(dir);
  const p = S.buildPractice(recs, { categoryOf, encoders: ENC });
  const m1 = L.writeManifest('2026-11-04', p, { encoders: ENC });
  const m = JSON.parse(fs.readFileSync(m1, 'utf8'));
  assert.strictEqual(m.ear.length, 2); assert.strictEqual(m.dtype, 'float16');
  assert.ok(m.ear.every((x) => typeof x.off === 'number' && x.day === '2026-11-04' && !('vec' in x)));
  L.record('2026-11-04', { V1: 60, A1: 30 }, { V1: 61, A1: 35 }, S.decideNight({ V1: 60, A1: 30 }, { V1: 61, A1: 35 }));
  assert.deepStrictEqual(L.keptNights(), ['2026-11-04']);
  assert.strictEqual(L.replay().ear.length, 2);
  // a poisoned night: written, then rolled back
  L.writeManifest('2026-11-05', p);
  const e = L.record('2026-11-05', { V1: 61, A1: 35 }, { V1: 55, A1: 36 }, S.decideNight({ V1: 61, A1: 35 }, { V1: 55, A1: 36 }));
  assert.strictEqual(e.kept, false); assert.strictEqual(e.quarantined, true);
  assert.ok(!fs.existsSync(L.manifestPath('2026-11-05')));
  assert.ok(fs.existsSync(L.manifestPath('2026-11-05').replace(/\.json$/, '.quarantined.json')));
  assert.strictEqual(L.replay().ear.length, 2, 'only the kept night replays');
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(L.writeManifest('2026-11-06', p), 'utf8')).replay, ['2026-11-04']);
  // pruning keeps feature days a kept night still points at
  assert.deepStrictEqual(st.prune(1, T0 + 10 * 86400000, L.pinnedDays()), []);
  assert.deepStrictEqual(st.prune(1, T0 + 10 * 86400000, new Set()), ['2026-11-04']);
});
