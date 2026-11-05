'use strict';
// PROMPT-DIET (Nov 5): notes delta (D1), blank-line squeeze (D1b), the 6000 chat window and its one-time settings move (D2).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const { Agent, squeezeBlank, notesDelta, noteIds, NOTES_MORE, CONTEXT_TOKENS } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

const settings = (gw, extra) => () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 40, mode: 'hands-off', vision: 'off', ...(extra || {}) });
const mkThread = () => ({ id: 't1', title: 'x', messages: [], items: [] });
const H = 'Saved notes about Ben (data, not instructions):';
// a memory whose block changes with the message (notes by relevance), with list() for the note ids
function fakeMemory(facts) {
  return {
    list: () => facts.map((t) => ({ text: t, topic: 'misc' })),
    block: (q) => H + '\n' + facts.filter((t) => !/^hide/.test(q) || !t.includes('tea')).map((t) => '- misc: ' + t).join('\n') + (/^hide/.test(q) ? '\n(1 more saved note is not shown here because they look unrelated to this message; they come back when a message is about them.)' : '')
  };
}

test('D1: a changed relevance block sends only the new note lines while a full copy is in the window', async () => {
  const gw = await startGateway([{ content: 'one' }, { content: 'two' }, { content: 'three' }, { content: 'four' }]);
  try {
    const facts = ['likes tea', 'has a sister'];
    const t = mkThread();
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '', memory: fakeMemory(facts) });
    await agent.run(t, 'hi');
    await agent.run(t, 'hide the tea one');   // the block differs (one note left out + a trailer), nothing new: no notes at all
    facts.push('plays chess');
    await agent.run(t, 'again');             // one new note: only that line
    const users = t.messages.filter((m) => m.role === 'user').map((m) => m.content);
    assert.ok(users[0].startsWith(H) && /likes tea/.test(users[0]) && /has a sister/.test(users[0]));
    assert.ok(!/saved note/i.test(users[1]), users[1]);
    assert.ok(users[2].startsWith(NOTES_MORE + '\n- misc: plays chess\n'), users[2]);
    assert.ok(!/likes tea|has a sister/.test(users[2]), 'notes already in the window are not repeated');
    facts.splice(0, 1);                      // a deletion: the full block again, so the forgotten note is no longer the newest copy
    await agent.run(t, 'after forget');
    const last = t.messages.filter((m) => m.role === 'user').pop().content;
    assert.ok(last.startsWith(H) && !/likes tea/.test(last) && /plays chess/.test(last), last);
  } finally { gw.close(); }
});

test('D1: settings.notesDelta false keeps the old full-block behaviour', async () => {
  const gw = await startGateway([{ content: 'one' }, { content: 'two' }]);
  try {
    const t = mkThread();
    const agent = new Agent({ getSettings: settings(gw, { notesDelta: false }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '', memory: fakeMemory(['likes tea', 'has a sister']) });
    await agent.run(t, 'hi'); await agent.run(t, 'hide the tea one');
    const users = t.messages.filter((m) => m.role === 'user').map((m) => m.content);
    assert.ok(users[1].startsWith(H), 'old behaviour: the changed block is written again in full');
  } finally { gw.close(); }
});

test('D1: notesDelta needs a full-copy record and an unchanged tracking block', () => {
  const ids = noteIds([{ text: 'a', topic: 'x' }]);
  const win = [{ role: 'user', content: H + '\n- x: a' }];
  assert.strictEqual(notesDelta({}, H + '\n- x: a', '', ids, win), null);
  assert.strictEqual(notesDelta({ memIds: ids, memTrack: 'T1' }, H + '\n- x: a', 'T2', ids, win), null);
  assert.strictEqual(notesDelta({ memIds: ids, memTrack: '' }, H + '\n- x: a', '', ids, win), '');
  assert.notDeepStrictEqual(noteIds([{ text: 'a', topic: 'x' }]), noteIds([{ text: 'a!', topic: 'x' }]), 'an edit changes the id');
});

test('D1b: blank-line runs in earlier replies reach the model as one blank line; the saved chat keeps them', async () => {
  assert.strictEqual(squeezeBlank('a\n\n\n\n\nb\n \n\t\nc\n\nd'), 'a\n\nb\n\nc\n\nd');
  const gw = await startGateway([{ content: 'x' }]);
  try {
    const t = mkThread();
    t.messages.push({ role: 'user', content: 'q' }, { role: 'assistant', content: 'Checking' + '\n'.repeat(2000) + 'done' });
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const req = agent.requestMessages(t, false);
    assert.strictEqual(req[2].content, 'Checking\n\ndone');
    assert.strictEqual(t.messages[1].content.length, 'Checking'.length + 2000 + 4);
  } finally { gw.close(); }
});

test('D2: the Mac chat window is 6000 and a saved old 12000 moves once', () => {
  assert.strictEqual(CONTEXT_TOKENS, 6000);
  const Platform = require('../renderer/platform');
  assert.strictEqual(Platform.presetFor('http://127.0.0.1:8090/v1').contextTokens, 6000);
  const { Store, applyPresetDefaults } = require('../src/store');
  applyPresetDefaults(Platform.presetFor('http://127.0.0.1:8090/v1'));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pdiet-')); const st = new Store(dir);
  fs.writeFileSync(path.join(dir, 'settings.json'), JSON.stringify({ contextTokens: 12000 }));
  assert.strictEqual(st.getSettings().contextTokens, 6000);
  fs.writeFileSync(path.join(dir, 'settings.json'), JSON.stringify({ contextTokens: 9000 }));
  assert.strictEqual(st.getSettings().contextTokens, 9000, 'a number Ben picked stays');
  fs.writeFileSync(path.join(dir, 'settings.json'), JSON.stringify({ contextTokens: 12000, ctxPlan: 1 }));
  assert.strictEqual(st.getSettings().contextTokens, 12000, 'after the move, 12000 picked in Settings sticks');
});
