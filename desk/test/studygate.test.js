'use strict';
// Learn study Motes (Nov 4 gap fix): their notes go through the truth check (maybe -> 2 sites -> confirmed / correction) and every
// study step (search, save) passes the quiz drift guard. Fake model (gateway) + fake web; no network.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const SG = require('../src/studygate');
const { TruthNotes } = require('../src/truthnotes');
const { sleepHandoff } = require('../src/diary-ao');
const { Agent } = require('../src/agent');
const { createMemory } = require('../src/memory');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-studygate-'));
// fake web: every query returns the same three sites
const web = (snip) => async () => '1. One\n   https://en.wikipedia.org/wiki/Black_hole\n   ' + snip + '\n2. Two\n   https://www.nasa.gov/bh\n   ' + snip + '\n3. Three\n   https://news.bbc.co.uk/x\n   ' + snip;
const fakeMemory = () => { const saved = []; return { saved, list: () => [], block: () => '', save: (text, topic, opts) => { saved.push({ text, topic, opts }); return { ok: true, fact: { text }, kept: true }; } }; };

test('topicOf reads the stored topic, else the LEARN_MOTE task text', () => {
  assert.equal(SG.topicOf({ learnTopic: 'black holes' }), 'black holes');
  assert.equal(SG.topicOf({ task: 'Go learn: black holes, focusing on the basics. Each run, dig into something new' }), 'black holes');
  assert.equal(SG.topicOf({ task: 'Go learn: tide pools. Each run, dig' }), 'tide pools');
  assert.equal(SG.topicOf({ task: 'Check my email' }), '');
});

test('a study note becomes `maybe` (not memory), then 2 sites confirm it and only then it is saved with its card topic and quote', async () => {
  const dir = tmp();
  try {
    const mem = fakeMemory();
    const truth = new TruthNotes({ dir, search: web('A black hole emits Hawking radiation.'), judge: async () => ({ verdict: 'supports' }), save: (t, tp, o) => mem.save(t, tp, o) });
    const sm = SG.studyMemory({ memory: mem, truth, topic: 'black holes', vocab: () => [] });
    const research = { origin: 'learn-research', attribution: { status: 'attributed', source: { url: 'https://example.org/bh', quote: 'emits Hawking radiation' } } };
    const r = sm.save('Black hole => emits => Hawking radiation', 'card', { research });
    assert.equal(r.ok, true); assert.equal(r.truth, 'maybe');
    assert.equal(mem.saved.length, 0, 'nothing reaches memory before the check');
    assert.equal(truth.counts().maybe, 1);
    assert.deepEqual(sleepHandoff({ truth, surprises: [] }).confirmed, [], 'a maybe never reaches the sleep handoff');
    assert.equal(sm.save('Black hole => emits => Hawking radiation', 'card').ok, false, 'a duplicate waits for its check');
    await truth.check(truth.next());
    assert.equal(truth.notes[0].status, 'confirmed');
    assert.equal(mem.saved.length, 1);
    assert.equal(mem.saved[0].text, 'Black hole => emits => Hawking radiation', 'the exact card words are saved');
    assert.equal(mem.saved[0].topic, 'card');
    assert.equal(mem.saved[0].opts.research.attribution.source.url, 'https://example.org/bh');
    assert.equal(truth.notes[0].text, 'Black hole emits Hawking radiation', 'the web check searched plain words');
    // read paths of memory pass through
    assert.equal(sm.block(), '');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('2 contradicting sites turn a study note into a correction; an unsettled one never reaches memory', async () => {
  const dir = tmp();
  try {
    const mem = fakeMemory();
    const truth = new TruthNotes({ dir, search: web('Black holes are not made of dark matter.'), judge: async () => ({ verdict: 'contradicts', correction: 'black holes are collapsed matter, not dark matter' }), save: (t, tp, o) => mem.save(t, tp, o) });
    const sm = SG.studyMemory({ memory: mem, truth, topic: 'black holes' });
    sm.save('Black holes are made of dark matter', 'skill: black holes', { research: { origin: 'learn-research' } });
    await truth.check(truth.next());
    assert.equal(truth.notes[0].status, 'wrong');
    assert.equal(mem.saved.length, 1);
    assert.equal(mem.saved[0].topic, 'correction');
    assert.match(mem.saved[0].text, /^I thought Black holes are made of dark matter; actually black holes are collapsed matter/);
    assert.equal(mem.saved[0].opts, undefined, 'a correction is our own words, not the quoted page');
    // a note nobody can settle: unsure after 3 tries, never saved
    const t2 = new TruthNotes({ dir: tmp(), search: web('nothing useful'), judge: async () => ({ verdict: 'unclear' }), save: (t, tp, o) => mem.save(t, tp, o) });
    SG.studyMemory({ memory: mem, truth: t2, topic: 'black holes' }).save('Black holes hum in B flat', 'skill: black holes');
    for (let i = 0; i < 3; i++) await t2.check(t2.next() || t2.notes[0]);
    assert.equal(t2.notes[0].status, 'unsure');
    assert.equal(mem.saved.length, 1);
    assert.deepEqual(t2.sleepCandidates(), []);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('drift guard: off-topic saves and searches are refused and counted; confirmed vocabulary lets a sub-topic through', async () => {
  const dir = tmp();
  try {
    const mem = fakeMemory(), drift = [];
    const truth = new TruthNotes({ dir, search: web('x') });
    let vocab = [];
    const o = { topic: 'black holes', vocab: () => vocab, onDrift: (k, t) => drift.push([k, t]) };
    const sm = SG.studyMemory({ ...o, memory: mem, truth });
    const r = sm.save('The best pizza in Naples is margherita', 'skill: black holes');
    assert.equal(r.ok, false); assert.equal(r.drift, true);
    assert.equal(truth.notes.length, 0);
    let ran = 0;
    const search = SG.guardSearch(async () => { ran++; return 'results'; }, o);
    const off = await search({ query: 'cheap pizza delivery' }, {});
    assert.equal(off.error, true); assert.match(off.text, /drifted off the study topic/);
    assert.equal(ran, 0, 'an off-topic search never runs');
    assert.equal(await search({ query: 'black hole event horizon size' }, {}), 'results');
    assert.equal((await search({ query: 'Hawking radiation evaporation rate' }, {})).error, true);
    vocab = ['A black hole emits Hawking radiation and slowly loses mass by evaporation.'];   // what is already confirmed about the topic
    assert.equal(await search({ query: 'Hawking radiation evaporation rate' }, {}), 'results');
    assert.deepEqual(drift.map((d) => d[0]), ['save', 'search', 'search']);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('a Learn study Mote agent (fake model, fake web): its memory_save lands as `maybe`, memory.md stays empty until the check', async () => {
  const dir = tmp();
  const gw = await startGateway([
    { tool_calls: [{ name: 'web_search', arguments: { query: 'football scores tonight' } }] },
    { tool_calls: [{ name: 'web_search', arguments: { query: 'black hole facts' } }] },
    { tool_calls: [{ name: 'memory_save', arguments: { fact: 'A black hole is a region where gravity stops light escaping.', topic: 'skill: black holes' } }] },
    { tool_calls: [{ name: 'memory_save', arguments: { fact: 'Pizza was invented in Naples.', topic: 'skill: black holes' } }] },
    { content: 'Done.' }]);
  try {
    const memory = createMemory(dir);
    const truth = new TruthNotes({ dir, search: web('A black hole is a region of spacetime where gravity is so strong that nothing, not even light, can escape.'), save: (t, tp, o) => (o ? memory.save(t, tp, o) : memory.save(t, tp)) });
    const drift = [];
    const study = { topic: 'black holes', vocab: () => [], onDrift: (k) => drift.push(k) };
    let searched = [];
    const tools = { web_search: SG.guardSearch(async (x) => { searched.push(x.query); return 'Black holes: regions of strong gravity.'; }, study) };
    const agent = new Agent({ learnResearch: true, helperId: 'h1', memory: SG.studyMemory({ ...study, memory, truth }), tools, toolDefs: buildTools({}),
      getSettings: () => ({ gatewayUrl: gw.url, model: 'm', mode: 'hands-off', verify: false, maxSteps: 8 }) });
    const thread = { id: 'learn', items: [], messages: [] };
    await agent.run(thread, 'Go learn: black holes. Each run, dig into something new.');
    assert.deepEqual(searched, ['black hole facts'], 'the off-topic search never ran');
    assert.deepEqual(drift, ['search', 'save']);
    assert.equal(memory.list().length, 0, 'nothing in memory yet');
    assert.equal(truth.notes.length, 1); assert.equal(truth.notes[0].status, 'maybe'); assert.equal(truth.notes[0].from, 'learn');
    assert.ok(thread.messages.some((m) => m.role === 'tool' && /Kept as a maybe note/.test(m.content)));
    // the lexical judge (no model) confirms it from two sites: now it is a saved note
    await truth.check(truth.next());
    assert.equal(truth.notes[0].status, 'confirmed');
    assert.deepEqual(memory.list().map((f) => f.text), ['A black hole is a region where gravity stops light escaping.']);
  } finally { gw.close(); fs.rmSync(dir, { recursive: true, force: true }); }
});
