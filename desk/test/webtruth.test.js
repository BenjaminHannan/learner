'use strict';
// Option B: web facts are trained on only when 2+ independent domains agree; Glim never states unverified ones as fact.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const webtruth = require('../src/webtruth');
const { createMemory } = require('../src/memory');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');
const { plant, FALSE_CARD, TRUE_CARD } = require('./fixtures/plant-pages');
const cases = require('./fixtures/webtruth-cases.json');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-webtruth-'));
const cardOf = (m, text) => m.list().find((f) => f.text === text);

test('shared cases: registrable domain and claim normalisation', () => {
  for (const [url, want] of cases.domains) assert.equal(webtruth.registrableDomain(url), want, url);
  for (const [text, want] of cases.norm) assert.equal(webtruth.normClaim(text), want, text);
});

test('step 1: a web card carries its source URLs and a verified flag; one site is unverified', () => {
  const dir = tmp(), m = plant(dir);
  const bad = cardOf(m, FALSE_CARD), good = cardOf(m, TRUE_CARD);
  const sb = m.status(bad), sg = m.status(good);
  assert.deepEqual([sb.web, sb.verified, sb.domains], [true, false, ['example.net']]);
  assert.deepEqual(sb.urls, ['https://only-one-site.example.net/ferries']);
  assert.deepEqual([sg.web, sg.verified, sg.domains], [true, true, ['example.com', 'example.org']]);
  assert.deepEqual(m.unverified().map((n) => n.text), [FALSE_CARD]);
  // the ledger row itself records the claim and the source
  const rows = fs.readFileSync(path.join(dir, 'memory-provenance.jsonl'), 'utf8').trim().split('\n').map(JSON.parse).filter((r) => r.type === 'research-note-prepare');
  assert.equal(rows.length, 3);
  assert.ok(rows.every((r) => r.claim_norm && r.attribution.verified === false && r.attribution.source.url));
});

test('step 1: same registrable domain twice, a source without the answer and an unattributed save never verify; a second real domain does', () => {
  const dir = tmp(), m = createMemory(dir);
  const { EvidenceRegistry, attachSourceRead } = require('../src/evidence');
  const save = (fact, url, quote) => {
    const reg = new EvidenceRegistry({ enabled: true });
    const header = 'Page (' + url + ')\n';
    const out = reg.recordRead('browser_read', attachSourceRead({ text: header + quote }, { url, body: quote, bodyStart: header.length, readAt: 1 }), 'c', 8000);
    return m.save(fact, 'card', { research: reg.metadata({ source_read_id: out.readId, source_quote: quote }) });
  };
  const fact = 'Pell Bridge => opened in => 1931';
  save(fact, 'https://en.wikipedia.org/a', 'Pell Bridge opened in 1931 to traffic.');
  const r = save(fact, 'https://de.wikipedia.org/b', 'Pell Bridge opened in 1931 as well.');
  assert.equal(r.provenance.verified, false);                       // wikipedia.org twice is one domain
  // a source whose visible text does not contain the answer cannot back it
  const r2 = save(fact, 'https://other.example.org/c', 'A page about bridges in general, nothing specific.');
  assert.equal(r2.provenance.verified, false);
  // an unattributed research save (no read id) counts for nothing
  const reg = new EvidenceRegistry({ enabled: true });
  m.save(fact, 'card', { research: reg.metadata({}) });
  assert.equal(m.status(cardOf(m, fact)).verified, false);
  // a second real domain verifies, and formatting differences still agree (normalised answer match)
  const r3 = save('pell bridge => Opened In => 1931.', 'https://news.example.com/d', 'The Pell Bridge opened in 1931.');
  assert.equal(r3.provenance.verified, true);
  assert.deepEqual(r3.provenance.domains, ['example.com', 'wikipedia.org']);
});

test('step 1: untagged legacy cards and skill notes default to unverified; Ben-origin notes are not web facts', () => {
  const dir = tmp(), m = createMemory(dir);
  m.write(m.read().text + '- Old Lighthouse => keeper => Pim | topic: card | id: mlegacy1 | updated: 2026-01-01\n- Handwritten fact | topic: card | id: hhand1 | updated: 2026-01-01\n');
  m.save('Ben likes jazz', 'preference');
  const typed = m.add({ text: 'Mira => works at => Larkhouse', topic: 'card' });
  m.save('Rowan => plays => oboe', 'card', { localOrigin: true });
  m.save('Study tip: spaced repetition', 'skill: memory');
  const by = (t) => m.list().find((f) => f.text === t);
  assert.equal(m.status(by('Old Lighthouse => keeper => Pim')).web, true);
  assert.equal(m.status(by('Handwritten fact')).web, false);
  assert.equal(m.status(by('Ben likes jazz')).web, false);
  assert.ok(typed.ok); assert.equal(m.status(by('Mira => works at => Larkhouse')).web, false);
  assert.equal(m.status(by('Rowan => plays => oboe')).web, false);
  assert.equal(m.status(by('Study tip: spaced repetition')).verified, false);
  assert.equal(m.status(by('Study tip: spaced repetition')).web, true);
});

test('a damaged ledger fails closed for Glim-saved notes', () => {
  const dir = tmp(), m = createMemory(dir);
  m.save('Ben likes jazz', 'preference');
  fs.writeFileSync(path.join(dir, 'memory-provenance.jsonl'), '{not json\n');
  assert.equal(m.status(m.list()[0]).web, true);
  assert.equal(m.unverified().length, 1);
});

test('step 3: context tags unverified notes and tells Glim to hedge; verified and personal notes are untouched', () => {
  const dir = tmp(), m = plant(dir);
  m.save('Study tip: spaced repetition', 'skill: memory');
  m.save('Ben likes jazz', 'preference');
  const block = m.block();
  assert.match(block.split('\n')[0], /Never state them as fact/);
  assert.match(block, /\[unverified web note\] skill: memory: Study tip/);
  assert.doesNotMatch(block, /unverified web note\] preference/);
  assert.match(block, /- preference: Ben likes jazz/);
  const m2 = createMemory(tmp()); m2.save('Ben likes jazz', 'preference');
  assert.doesNotMatch(m2.block(), /unverified|Never state/);
});

test('step 3: post-check flags plain assertions of an unverified answer, not hedged attribution or verified facts', () => {
  const m = plant(tmp()), notes = m.unverified();
  const q = 'Where does the Luma Ferry dock?';
  assert.equal(webtruth.assertedClaims('The Luma Ferry docks at Mossbank.', q, notes, false).length, 1);
  assert.equal(webtruth.assertedClaims('It docks at Mossbank.', q, notes, false).length, 1);           // subject only in the question
  assert.equal(webtruth.assertedClaims('One site claims it docks at Mossbank, but I have not confirmed it.', q, notes, false).length, 0);
  assert.equal(webtruth.assertedClaims('One site claims it docks at Mossbank.', q, notes, true).length, 1);   // strict (training): still dropped
  assert.equal(webtruth.assertedClaims('Odile Marsh keeps Tidewick Light.', 'Who keeps Tidewick Light?', notes, false).length, 0);   // verified: not in the list
  assert.equal(webtruth.assertedClaims('I do not know where it docks.', q, notes, false).length, 0);
});

test('step 3: the agent flags a reply that asserts an unverified note, writes the flag, and stays quiet on hedged replies', async () => {
  const dir = tmp(), m = plant(dir);
  for (const [answer, flagged] of [['The Luma Ferry docks at Mossbank.', true], ["One site claims the Luma Ferry docks at Mossbank. I haven't confirmed it.", false]]) {
    const events = [];
    const gw = await startGateway([{ content: answer }]);
    try {
      const agent = new Agent({ memory: m, tools: {}, toolDefs: buildTools({}), emit: (e) => events.push(e),
        getSettings: () => ({ gatewayUrl: gw.url, model: 'm', mode: 'hands-off', verify: false, maxSteps: 4 }) });
      await agent.run({ id: 'chat1', items: [], messages: [] }, 'Where does the Luma Ferry dock?');
    } finally { gw.close(); }
    assert.equal(events.some((e) => e.type === 'unverified_claim'), flagged, answer);
  }
  const lines = fs.readFileSync(path.join(dir, 'unverified-assertions.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].answer_sha256, require('node:crypto').createHash('sha256').update('The Luma Ferry docks at Mossbank.').digest('hex'));
});

test('agent: a save after reading the web is tagged unverified; Ben\'s own "remember" words and web-free saves are local origin', async () => {
  const dir = tmp(), m = createMemory(dir);
  const gw = await startGateway([
    { tool_calls: [{ name: 'browser_read', arguments: {} }] },
    { tool_calls: [{ name: 'memory_save', arguments: { fact: 'Gossip Quay => hosts => Nobody', topic: 'card' } }] },
    { content: 'Done.' }
  ]);
  try {
    const { attachSourceRead } = require('../src/evidence');
    const agent = new Agent({ memory: m, tools: { browser_read: async () => attachSourceRead({ text: 'Page 1 of 1 (https://x.example.net/a)\nGossip' }, { url: 'https://x.example.net/a', body: 'Gossip', bodyStart: 'Page 1 of 1 (https://x.example.net/a)\n'.length, readAt: 1 }) }, toolDefs: buildTools({}),
      getSettings: () => ({ gatewayUrl: gw.url, model: 'm', mode: 'hands-off', verify: false, maxSteps: 8 }) });
    await agent.run({ id: 'w1', items: [], messages: [] }, 'Find out about Gossip Quay.');
  } finally { gw.close(); }
  const st = m.status(m.list()[0]);
  assert.deepEqual([st.web, st.verified], [true, false]);
  const gw2 = await startGateway([{ tool_calls: [{ name: 'memory_save', arguments: { fact: 'Ben => likes => oboe', topic: 'card' } }] }, { content: 'Done.' }]);
  try {
    const agent = new Agent({ memory: m, tools: {}, toolDefs: buildTools({}), getSettings: () => ({ gatewayUrl: gw2.url, model: 'm', mode: 'hands-off', verify: false, maxSteps: 8 }) });
    await agent.run({ id: 'w2', items: [], messages: [] }, 'I like the oboe.');
  } finally { gw2.close(); }
  assert.equal(m.status(m.list().find((f) => /oboe/.test(f.text))).web, false);
});

test('step 4 (JS side): planted pages: the false single-site fact is unverified everywhere Glim can see it, the true one is verified', () => {
  const m = plant(tmp());
  const unv = m.unverified().map((n) => n.text);
  assert.deepEqual(unv, [FALSE_CARD]);
  assert.ok(!unv.includes(TRUE_CARD));
});
