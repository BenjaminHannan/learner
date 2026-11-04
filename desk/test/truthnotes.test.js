'use strict';
// Always-on v2 phase 5: every thought is a `maybe` note until 2 independent websites settle it; only confirmed notes and
// corrections reach memory (which the nightly sleep reads).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const T = require('../src/truthnotes');
const { createMemory } = require('../src/memory');

const results = (...sites) => sites.map((s, i) => ({ title: 'Result ' + i, url: 'https://' + s + '/page' + i, snippet: 'snippet ' + i }));
function rig(o) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'truth-'));
  const mem = createMemory(dir); const saved = [];
  const tn = new T.TruthNotes({ dir, search: async () => o.results, judge: async (c, r) => o.judge(r), save: (text, topic) => { saved.push({ text, topic }); return mem.save(text, topic); } });
  return { dir, mem, saved, tn };
}

test('siteOf / parseResults: independence means different sites', () => {
  assert.strictEqual(T.siteOf('https://en.wikipedia.org/wiki/X'), 'wikipedia.org');
  assert.strictEqual(T.siteOf('https://www.nasa.gov/a'), 'nasa.gov');
  assert.strictEqual(T.siteOf('https://news.bbc.co.uk/x'), 'bbc.co.uk');
  const r = T.parseResults('1. Black hole - Wikipedia\n   https://en.wikipedia.org/wiki/Black_hole\n   A black hole is a region...\n2. NASA\n   https://science.nasa.gov/bh\n   Black holes are...');
  assert.strictEqual(r.length, 2); assert.strictEqual(r[1].url, 'https://science.nasa.gov/bh');
});

test('`maybe` notes never reach the sleep candidates (nor memory)', async () => {
  const r = rig({ results: results('a.com', 'a.com', 'a.com'), judge: () => ({ verdict: 'supports' }) });
  const n = r.tn.add('Black holes have an event horizon.', { topic: 'black holes' });
  assert.strictEqual(n.status, 'maybe');
  assert.deepStrictEqual(r.tn.sleepCandidates(), []);
  assert.strictEqual(r.mem.list().length, 0, 'memory (what sleep reads) is untouched by add()');
  await r.tn.check(n);   // three results from ONE site: not independent
  assert.strictEqual(n.status, 'maybe'); assert.deepStrictEqual(r.tn.sleepCandidates(), []); assert.strictEqual(r.saved.length, 0);
  await r.tn.check(n); await r.tn.check(n);
  assert.strictEqual(n.status, 'unsure', 'unsettled after 3 tries'); assert.deepStrictEqual(r.tn.sleepCandidates(), []); assert.strictEqual(r.mem.list().length, 0);
});

test('2 independent supporting sites -> confirmed -> saved to memory and a sleep candidate', async () => {
  const r = rig({ results: results('wikipedia.org', 'en.wikipedia.org', 'nasa.gov'), judge: () => ({ verdict: 'supports' }) });
  const n = r.tn.add('Black holes have an event horizon.', { topic: 'black holes' });
  await r.tn.check(n);
  assert.strictEqual(n.status, 'confirmed');
  assert.deepStrictEqual(n.sources.map((s) => s.site), ['wikipedia.org', 'nasa.gov']);
  assert.strictEqual(r.saved.length, 1); assert.strictEqual(r.mem.list().length, 1);
  assert.deepStrictEqual(r.tn.sleepCandidates().map((c) => c.kind), ['confirmed']);
});

test('2 independent contradicting sites -> wrong, kept as a correction "I thought X; actually Y"', async () => {
  const r = rig({ results: results('a.org', 'b.edu'), judge: () => ({ verdict: 'contradicts', correction: 'the Sun is a G-type star' }) });
  const n = r.tn.add('The Sun is a red dwarf.', { topic: 'stars' });
  await r.tn.check(n);
  assert.strictEqual(n.status, 'wrong');
  assert.strictEqual(n.correction, 'I thought The Sun is a red dwarf; actually the Sun is a G-type star');
  assert.deepStrictEqual(r.tn.sleepCandidates(), [{ id: n.id, text: n.correction, kind: 'correction', sources: n.sources }]);
  assert.strictEqual(r.saved[0].topic, 'correction');
  assert.deepStrictEqual(r.tn.counts(), { maybe: 0, confirmed: 0, wrong: 1, unsure: 0 });
});

test('Ben can settle a note; private text and duplicates are never stored; a stopped check changes nothing', async () => {
  const r = rig({ results: results('a.org', 'b.org'), judge: () => ({ verdict: 'supports' }) });
  assert.strictEqual(r.tn.add('my bank account number is 1234'), null);
  const n = r.tn.add('Water boils at 100 C at sea level.');
  assert.strictEqual(r.tn.add('water boils at 100 c at sea level.'), null);
  const ctl = new AbortController(); ctl.abort();
  await r.tn.check(n, ctl.signal); assert.strictEqual(n.status, 'maybe'); assert.strictEqual(n.tries, 0);
  r.tn.benSays(n.id, false, 'it boils at 100 C only at 1 atm');
  assert.strictEqual(n.status, 'wrong');
  const again = new T.TruthNotes({ dir: r.dir });   // persisted
  assert.strictEqual(again.counts().wrong, 1);
});

test('the lexical fallback judge only ever supports or shrugs', () => {
  assert.strictEqual(T.lexicalJudge('Black holes have an event horizon', { title: 'Event horizon', snippet: 'Every black hole has an event horizon' }).verdict, 'supports');
  assert.strictEqual(T.lexicalJudge('Black holes have an event horizon', { title: 'Cats', snippet: 'Cats purr' }).verdict, 'unclear');
});

test('main: Mote claims and loop notes go to the truth check as maybe (never straight to memory); chat stops a check', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /function aoNote\(text\) \{ try \{ if \(aoTruth\) aoTruth\.add\(text, \{ from: 'noticed' \}\); \}/);
  assert.doesNotMatch(m, /memory\.save\(text, 'noticed'\)/);
  assert.match(m, /for \(const c of kept\) getTruth\(\)\.add\(c,/);
  assert.match(m, /aoPool\.stopAll\('chat'\); aoStopChecks\(\);/);
  // the only memory.save in the always-on block is the truth check's (confirmed notes and corrections)
  const block = m.slice(m.indexOf('// ---- Always-on Premonition'), m.indexOf('function registerIpc() {'));
  assert.deepStrictEqual(block.match(/memory\.save\([^)]*\)/g), ['memory.save(text, topic)']);
});
