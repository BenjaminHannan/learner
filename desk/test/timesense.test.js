'use strict';
// Task B, feeling time: timestamps everywhere, time-ago in the loop prompt, the WHEN guesser + time-surprise, time questions.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const TS = require('../src/timesense');
const G = require('../src/guesser');
const Senses = require('../src/senses');
const AO = require('../src/alwayson');
const DiaryAO = require('../src/diary-ao');
const { TruthNotes } = require('../src/truthnotes');
const { requestTokens } = require('../src/context-budget');

const at = (d, h, m) => new Date(2026, 10, d, h, m || 0, 0).getTime();   // November 2026 (2 = Mon)
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'ts-'));

test('time words: clock, time-ago, unknown', () => {
  const now = at(4, 14, 5);
  assert.strictEqual(TS.clockWords(now), 'Wed 4 Nov, 14:05');
  assert.strictEqual(TS.ago(now - 20000, now), 'just now');
  assert.strictEqual(TS.ago(now - 4 * 60000, now), '4 min ago');
  assert.strictEqual(TS.ago(now - 150 * 60000, now), '2.5 h ago');
  assert.strictEqual(TS.ago(now - 3 * 86400000, now), '3 days ago');
  for (const bad of [null, undefined, 0, NaN, 'x', -5]) assert.strictEqual(TS.ago(bad, now), 'time unknown');
  assert.strictEqual(TS.timeOf({ text: 'old' }), null);
  assert.strictEqual(TS.timeOf({ t: '2026-11-04T10:00:00Z' }), Date.parse('2026-11-04T10:00:00Z'));
  assert.strictEqual(TS.timeOf({ settledAt: 5 }), 5);
});

test('every new record type carries a timestamp (observation, surprise, wonder, activity, truth note, timeline row, sleep candidate)', async () => {
  const dir = tmp(); let t = at(4, 10);
  const st = new Senses.AlwaysOnState(dir, { now: () => t });
  assert.ok(Number.isFinite(st.add('screen', 'hello world').t));
  assert.ok(Number.isFinite(st.addSurprise({ stream: 'app', what: 'Ben opened Steam', kl: 2 }).t));
  assert.ok(Number.isFinite(st.addWonder('why is the sky blue', 'test').t));
  st.logActivity('note', { status: 'confirmed' }); assert.ok(Number.isFinite(st.activity[0].t));
  const tn = new TruthNotes({ dir, now: () => t, search: async () => [{ title: 'a', url: 'https://a.org/1', snippet: '' }, { title: 'b', url: 'https://b.org/1', snippet: '' }], judge: async () => ({ verdict: 'supports' }), save: () => ({ ok: true }) });
  const n = tn.add('Octopuses have three hearts.'); assert.ok(Number.isFinite(n.t));
  t += 60000; await tn.check(n);
  const h = DiaryAO.sleepHandoff({ truth: tn, surprises: st.surprises });
  assert.strictEqual(h.confirmed.length, 1); assert.strictEqual(h.confirmed[0].t, t, 'sleep candidate stamped with its settle time');
  assert.ok(h.surprises.every((s) => Number.isFinite(s.t)));
});

test('old records without a timestamp load fine and show as "time unknown" (never a crash)', () => {
  const dir = tmp();
  fs.writeFileSync(path.join(dir, Senses.STATE_FILE), JSON.stringify({ inbox: [{ sense: 'screen', text: 'an old line' }, { sense: 'screen', text: 'a bad time', t: 'soon' }], surprises: [{ what: 'old surprise' }, null], wonder: [{ text: 'old wonder' }, { nope: 1 }], activity: [{ kind: 'said' }, 7] }));
  const st = new Senses.AlwaysOnState(dir, { now: () => at(4, 12) });
  assert.strictEqual(st.inbox.length, 2); assert.strictEqual(st.inbox[0].t, null);
  assert.strictEqual(st.surprises.length, 1); assert.strictEqual(st.wonder.length, 1); assert.strictEqual(st.activity.length, 1);
  assert.ok(st.add('screen', 'a new line'), 'adding after a timeless row works');
  const msgs = AO.buildMessages(st.inbox, st.summary(), { now: at(4, 12) });
  assert.match(msgs[1].content, /\[screen, time unknown\] an old line/);
  assert.doesNotMatch(msgs[1].content, /Invalid|NaN/);
  assert.strictEqual(TS.answerTimeQuestion('how long ago did I see an old line?', st.inbox.slice(0, 2)), null, 'time questions skip timeless rows');
});

test('the loop prompt shows the clock and time-ago, and stays well inside the context budget', () => {
  const now = at(4, 14, 5);
  const fresh = Array.from({ length: 12 }, (_, i) => ({ t: now - (12 - i) * 60000, sense: 'screen', text: ('Screen words ' + i + ' ').repeat(40) }));
  const base = AO.buildMessages(fresh, 'No current focus.', { now });
  const extra = { now, likely: 'Usually at this time: code 62%, browser 21%.', recall: Array.from({ length: 9 }, (_, i) => '(seen 3 h ago, same shape) ' + 'x'.repeat(300) + i), patterns: Array.from({ length: 4 }, () => 'Pattern (seen 6×): ' + 'y'.repeat(400)) };
  const full = AO.buildMessages(fresh, 'No current focus.', extra);
  const u = full[1].content;
  assert.match(u, /\nNow: Wed 4 Nov, 14:05\. Usually at this time: code 62%/);   // E1: the clock moved to the end (prefix reuse)
  assert.match(u, /\[screen, 13:53\] Screen words 0 .* \(12 min ago\)/);
  assert.strictEqual((u.match(/^- \(seen 3 h ago/gm) || []).length, 5, 'at most 5 recalled memories');
  assert.strictEqual((u.match(/^- Pattern/gm) || []).length, 2, 'at most 2 patterns');
  const added = requestTokens(full) - requestTokens(base);
  assert.ok(added <= 700, 'time + recall + patterns add ' + added + ' tokens');
  assert.ok(requestTokens(full) + 220 <= 8192 - 2048, 'whole loop request ' + requestTokens(full) + ' tokens');
  // the AlwaysOn loop passes its context() through to the prompt
  const st = new Senses.AlwaysOnState(tmp(), { now: () => now });
  const senses = new Senses.Senses({ consent: { ...Senses.defaults(), senses: { ...Senses.defaults().senses, screen: true } }, state: st, now: () => now });
  st.add('screen', 'Maya texted: practice moved to 5pm');
  let seen = null;
  const loop = new AO.AlwaysOn({ senses, state: st, now: () => now, ask: async (m) => { seen = m; return '{"say":null,"note":null,"learn":null,"why":"x"}'; }, context: () => ({ recall: ['(seen 2 days ago, same shape) Sam emailed: meeting moved to 3pm'] }) });
  return loop.tick().then(() => { assert.match(seen[1].content, /Related memories \(data\):\n- \(seen 2 days ago, same shape\) Sam emailed/); assert.match(seen[1].content, /\(just now\)/); });
});

// a scripted fortnight: weekdays code 9-17, games 19-22; weekend browser
function routine(g) {
  for (let d = 2; d <= 13; d++) {
    const wd = new Date(2026, 10, d).getDay();
    for (let h = 8; h < 23; h++) for (let m = 0; m < 60; m += 5) {
      const cat = wd === 0 || wd === 6 ? 'browser' : h < 9 ? 'browser' : h < 17 ? 'code' : h < 19 ? 'browser' : 'game';
      g.observe('app', cat, at(d, h, m));
    }
  }
}
test('time-surprise: a game at an unusual hour is a bigger surprise than the same game at its usual hour', () => {
  const g = new G.Guesser({ when: true, cooldownMs: 0 });
  routine(g);
  const saved = JSON.parse(JSON.stringify(g.toJSON()));
  const fork = () => new G.Guesser({ when: true, cooldownMs: 0, saved: JSON.parse(JSON.stringify(saved)) });
  // the same step (browser -> game) on Tuesday 17 Nov: at 20:00 (its usual time) and at 10:00 (never seen then)
  const a = fork(); a.observe('app', 'browser', at(17, 19, 55)); const usual = a.observe('app', 'game', at(17, 20, 0));
  const b = fork(); b.observe('app', 'browser', at(17, 9, 55)); const odd = b.observe('app', 'game', at(17, 10, 0));
  assert.ok(odd.whenKl > 5 * usual.whenKl, 'when-surprise ' + odd.whenKl + ' vs ' + usual.whenKl);
  assert.ok(odd.kl > usual.kl, 'total surprise ' + odd.kl + ' vs ' + usual.kl);
  assert.ok(odd.unusualTime && !usual.unusualTime);
  // "what is likely at this time"
  const lk = fork().likelyNow(at(17, 10, 30)); assert.strictEqual(lk.top[0][0], 'code');
  assert.match(TS.likelyWords(fork().when, at(17, 20, 30)), /^Usually at this time: game \d+%/);
  // the big-surprise listener hears that it is about the time
  const big = []; const c = new G.Guesser({ when: true, cooldownMs: 0, saved: JSON.parse(JSON.stringify(saved)), onBig: (s) => big.push(s) });
  c.observe('app', 'browser', at(17, 9, 55)); c.observe('app', 'game', at(17, 10, 0));
  assert.ok(big.some((s) => s.unusualTime), JSON.stringify(big));
  // without o.when the guesser is unchanged (older callers); a saved when-model is carried through untouched
  const plain = new G.Guesser({ saved }); assert.strictEqual(plain.when, null); assert.deepStrictEqual(plain.toJSON().when, saved.when);
  // sleep retunes it like the rest: counts x 0.8
  const d = fork(); const before = d.when.how[String(TS.hourOfWeek(at(10, 20)))].slice(); d.decay(0.8);
  const after = d.when.how[String(TS.hourOfWeek(at(10, 20)))]; assert.ok(after.every((v, i) => v <= before[i] + 1e-12) && after.some((v, i) => v < before[i]));
});

test('staying in one app is counted again only every 10 minutes (the 1 s tick does not flood the hour buckets)', () => {
  const w = new TS.WhenModel(G.APP_CATS);
  let n = 0; for (let s = 0; s < 3600; s++) if (w.observe('code', at(4, 10) + s * 1000)) n++;
  assert.strictEqual(n, 6);
});

test('time questions on a scripted day: "what happened right before X", "how long ago did I…"', () => {
  const day = [
    [8, 5, 'Front app: Mail. Open: Mail — Inbox.'], [8, 40, 'Mom texted: dinner at 7 tonight'], [9, 10, 'Front app: Terminal. Open: Terminal — npm run build.'],
    [11, 30, 'Error: Cannot find module left-pad'], [11, 42, 'Front app: Safari. Open: Safari — Stack Overflow.'], [13, 0, 'Front app: Steam. Open: Steam — Counter-Strike 2.'],
    [15, 20, 'Jordan texted: practice moved to 6pm'], [16, 0, 'Front app: Notes. Open: Notes — chem lab.']
  ].map(([h, m, text]) => ({ t: at(4, h, m), text }));
  const now = at(4, 17, 0);
  let a = TS.answerTimeQuestion('What happened right before I opened Steam?', day, now);
  assert.strictEqual(a.kind, 'before'); assert.match(a.before.text, /Stack Overflow/); assert.match(a.answer, /78 min earlier/);
  a = TS.answerTimeQuestion('what happened just after the left-pad error?', day, now);
  assert.match(a.after.text, /Stack Overflow/);
  a = TS.answerTimeQuestion('How long ago did Jordan text about practice?', day, now);
  assert.strictEqual(a.kind, 'ago'); assert.match(a.answer, /^That was 1\.5 h ago \(Wed 4 Nov, 15:20\)/);
  assert.strictEqual(TS.answerTimeQuestion('how long ago did I play the violin?', day, now), null, 'nothing matches -> no answer, not a guess');
  assert.ok(TS.isTimeAsk('how long ago did I open Steam?') && TS.isTimeAsk('what happened right before the error') && !TS.isTimeAsk('what is a black hole'));
});
