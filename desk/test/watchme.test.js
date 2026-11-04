'use strict';
// Watch me once (src/watchme.js): steps from events / frames / narration, the skill card, checked replay with Ben's yes,
// private frames never kept, evidence clips (Mac only, 3 days, size cap), the skill store sleep reads.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const W = require('../src/watchme');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'watchme-'));
const btn = (id, title, x) => ({ id, role: 'button', title, value: '', frame: [x, 100, 100, 30] });
const fr = (t, app, title, els, text) => ({ t, app, title, elements: els, text: text || '' });

// a tiny fake app: Notes Home -[New Note]-> Untitled (field Body); cmd+s saves
function fakeNotes() {
  const s = { app: 'Finder', win: 'Home', body: '', saved: false };
  const look = () => {
    if (s.app !== 'Notes') return { app: s.app, windows: [{ title: 'Desktop' }], elements: [] };
    if (s.win === 'Home') return { app: 'Notes', windows: [{ title: 'Home' }], elements: [btn(0, 'New Note', 40), btn(1, 'Help', 180)] };
    return { app: 'Notes', windows: [{ title: 'Untitled' + (s.saved ? ' (saved)' : '') }], elements: [btn(0, 'Done', 40), { id: 1, role: 'field', title: 'Body', value: s.body, frame: [40, 300, 500, 200] }].concat(s.saved ? [{ id: 2, role: 'label', title: 'Saved', value: '', frame: [40, 520, 60, 20] }] : []) };
  };
  const calls = [];
  const tools = {
    look: async () => { calls.push('look'); return look(); },
    open_app: async (a) => { calls.push('open'); s.app = a.name; return {}; },
    press: async (a) => { calls.push('press'); const e = look().elements.find((x) => x.id === a.id); if (e && e.title === 'New Note') s.win = 'Untitled'; return {}; },
    click: async () => { calls.push('click'); return {}; },
    type: async (a) => { calls.push('type'); s.body += a.text; return {}; },
    key: async (a) => { calls.push('key'); if (a.keys === 'cmd+s' && s.body) s.saved = true; return {}; }
  };
  return { s, look, tools, calls };
}
const asFrame = (t, j) => W.frameFromLook(t, j, '');

// a recorded demo of: open Notes, click New Note, type "milk eggs", cmd+s
function demoRec(withEvents) {
  const n = fakeNotes(); const frames = [];
  frames.push(asFrame(0, n.look()));
  n.s.app = 'Notes'; frames.push(asFrame(2000, n.look()));
  n.s.win = 'Untitled'; frames.push(asFrame(4000, n.look()));
  n.s.body = 'milk'; frames.push(asFrame(5000, n.look()));
  n.s.body = 'milk eggs'; frames.push(asFrame(6000, n.look()));
  n.s.saved = true; frames.push(asFrame(8000, n.look()));
  frames.push(asFrame(9000, n.look()));
  const events = withEvents ? [{ t: 1500, kind: 'app', name: 'Notes' }, { t: 3500, kind: 'click', x: 90, y: 115 }, { t: 4500, kind: 'type', text: 'milk' }, { t: 5500, kind: 'type', text: ' eggs' }, { t: 7500, kind: 'key', keys: 'cmd+s' }] : [];
  const narration = [{ t0: 800, t1: 1800, text: 'first I open Notes' }, { t0: 2500, t1: 3400, text: 'then I click New Note' }, { t0: 4200, t1: 5000, text: 'and I type my list' }];
  return { frames, events, narration };
}
const keys = (card) => card.steps.map((s) => s.do.tool + ':' + JSON.stringify(s.do.args));
const TRUTH = ['open_app:{"name":"Notes"}', 'click:{"label":"New Note"}', 'type:{"text":"milk eggs"}', 'key:{"keys":"cmd+s"}'];

test('watchme: events give the steps; the narration is attached as Ben\'s words', () => {
  const card = W.skillCard(demoRec(true), 'make a shopping note', { id: 'k1' });
  assert.deepStrictEqual(keys(card), TRUTH);
  assert.match(card.steps[0].say, /open Notes/);
  assert.match(card.steps[1].say, /New Note/);
  assert.strictEqual(card.steps[1].expect.title, 'Untitled');
  assert.match(W.cardText(card), /^Skill "make a shopping note"[\s\S]*1\. Open Notes[\s\S]*4\. Press cmd\+s/);
});

test('watchme: without any events the same steps come from the frames and the narration', () => {
  const card = W.skillCard(demoRec(false), 'shopping note', { id: 'k2' });
  assert.deepStrictEqual(keys(card), TRUTH);
  assert.ok(card.how.frames >= 2 && card.how.narration >= 1, JSON.stringify(card.how));
  assert.strictEqual(W.actionsFrom(demoRec(false), { eventsOnly: true }).length, 0);
});

test('watchme: narration parsing for keys and buttons', () => {
  assert.strictEqual(W.narratedKey('now press command S to save'), 'cmd+s');
  assert.strictEqual(W.narratedKey('hit enter'), 'enter');
  assert.strictEqual(W.narratedKey('I like this'), null);
  const f = fr(0, 'X', 'Home', [btn(0, 'Export', 0), btn(1, 'Export As', 200)]);
  assert.strictEqual(W.narratedLabel('then I click Export As here', f).title, 'Export As');
  assert.strictEqual(W.narratedLabel('Export As is nice', f), null);   // no click verb
});

test('watchme: replay asks Ben first, redoes each step and checks the screen after it', async () => {
  const card = W.skillCard(demoRec(true), 'shopping note', { id: 'k3' });
  const no = fakeNotes();
  const r0 = await W.replaySkill(card, no.tools, { confirm: async () => false, wait: async () => {} });
  assert.strictEqual(r0.ok, false); assert.deepStrictEqual(no.calls, []);
  const r1 = await W.replaySkill(card, no.tools, { wait: async () => {} });   // no confirm function: never runs
  assert.strictEqual(r1.ok, false); assert.deepStrictEqual(no.calls, []);
  const n = fakeNotes();
  const r = await W.replaySkill(card, n.tools, { confirm: async () => true, wait: async () => {} });
  assert.strictEqual(r.ok, true, JSON.stringify(r));
  assert.deepStrictEqual(n.s, { app: 'Notes', win: 'Untitled', body: 'milk eggs', saved: true });
});

test('watchme: replay stops at the first step whose screen check fails', async () => {
  const card = W.skillCard(demoRec(true), 'shopping note', { id: 'k4' });
  const n = fakeNotes();
  n.tools.press = async () => ({});          // the button does nothing on this screen
  const r = await W.replaySkill(card, n.tools, { confirm: async () => true, wait: async () => {} });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.failedAt, 2); assert.match(r.why, /window is "Home"/);
  assert.ok(!n.calls.includes('type'), 'nothing after the failed step runs');
});

test('watchme: a private frame or utterance is never kept', async () => {
  let i = 0;
  const looks = [{ app: 'Safari', windows: [{ title: 'Chase online banking sign in' }], elements: [] }, { app: 'Notes', windows: [{ title: 'Home' }], elements: [] }];
  const shots = [];
  const ws = new W.WatchSession({ look: async () => looks[i++ % 2], ocr: async () => '', shot: async () => Buffer.from('jpg'), clips: { put: (id, k, j, text) => { shots.push(text); return 'x'; } }, setInterval: () => 1, clearInterval: () => {} });
  await ws.tick(); await ws.tick();
  assert.strictEqual(ws.rec.frames.length, 1); assert.strictEqual(ws.dropped, 1);
  assert.ok(shots.every((t) => !/banking/i.test(t)));
  ws.heard('my password is hunter2'); ws.heard('now I click Save');
  assert.deepStrictEqual(ws.rec.narration.map((x) => x.text), ['now I click Save']);
});

test('watchme: clips are Mac only, never private, and pruned by age and size', () => {
  const dir = tmp();
  assert.strictEqual(new W.Clips(dir, { platform: 'win32' }).put('s1', 1, Buffer.alloc(10), 'notes'), null);
  let now = 1e12;
  const c = new W.Clips(dir, { platform: 'darwin', capBytes: 25, keepDays: 3, now: () => now });
  assert.strictEqual(c.put('s1', 1, Buffer.alloc(10), 'my password is x'), null);
  assert.ok(c.put('s1', 1, Buffer.alloc(10), 'notes'));
  assert.ok(c.put('s1', 2, Buffer.alloc(10), 'notes'));
  c.put('s1', 3, Buffer.alloc(10), 'notes');                     // 30 bytes > cap 25: the oldest goes
  assert.ok(c.files().reduce((s, f) => s + f.size, 0) <= 25);
  now += 4 * 86400000;                                           // 4 days later: all gone
  assert.strictEqual(c.prune().bytes, 0);
  assert.deepStrictEqual(c.files(), []);
  assert.strictEqual(c.put('../x', 1, Buffer.alloc(1), 'notes'), null);
});

test('watchme: the skill store keeps cards (with their text) for sleep, replaces by name, refuses private ones', () => {
  const dir = tmp(); const st = new W.SkillStore(dir);
  const card = W.skillCard(demoRec(true), 'shopping note', { id: 'k5', created: '2026-11-04T10:00:00Z' });
  assert.ok(st.save(card).ok);
  assert.ok(st.save({ ...card, id: 'k6' }).ok);
  const all = st.list();
  assert.strictEqual(all.length, 1); assert.strictEqual(all[0].id, 'k6');
  assert.match(all[0].text, /1\. Open Notes/);
  assert.strictEqual(st.find('shopping').id, 'k6');
  assert.strictEqual(st.save({ ...card, id: 'k7', name: 'log in with my password' }).ok, false);
  assert.strictEqual(st.save({ ...card, id: 'k8', steps: [] }).ok, false);
  assert.ok(st.remove('k6')); assert.deepStrictEqual(st.list(), []);
});

test('watchme wiring: both round-2 settings default OFF, map to the sleep switches, and main.js refuses Watch me while it is off', () => {
  const { DEFAULT_SETTINGS } = require('../src/store');
  assert.strictEqual(DEFAULT_SETTINGS.watchMe, false); assert.strictEqual(DEFAULT_SETTINGS.benModelSleep, false);
  const { roundTwoEnv } = require('../src/sleep');
  assert.deepStrictEqual(roundTwoEnv(DEFAULT_SETTINGS), { SLEEPMLX_SKILL_CARDS: '0', SLEEPMLX_BEN_MODEL: '0' });
  assert.deepStrictEqual(roundTwoEnv({ watchMe: true, benModelSleep: true }), { SLEEPMLX_SKILL_CARDS: '1', SLEEPMLX_BEN_MODEL: '1' });
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const block = main.slice(main.indexOf('// ---- Watch me once'), main.indexOf('// ---- Watch me once') + 6000);
  assert.strictEqual((block.match(/watchMe !== true\) return \{ error: 'Watch me is off/g) || []).length, 2, 'start and redo check the setting');
  assert.match(block, /replaySkill\(card, tools, \{ confirm \}\)/);
  assert.match(block, /process\.platform === 'darwin' \? new W\.Clips/);
  for (const ch of ['watchme:start', 'watchme:stop', 'watchme:list', 'watchme:redo', 'watchme:remove']) assert.ok(main.includes("h('" + ch + "'"), ch);
});
