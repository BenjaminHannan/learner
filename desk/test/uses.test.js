'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const Uses = require('../renderer/uses');
const { Store, DEFAULT_SETTINGS, sanitize } = require('../src/store');
const { Helpers, parseSchedule } = require('../src/helpers');
const { Agent } = require('../src/agent');
const { SYSTEM_PROMPT, buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'desk-uses-'));

test('there are 8 uses with unique ids, a title, an example and a welcome chip each', () => {
  assert.strictEqual(Uses.USES.length, 8);
  assert.strictEqual(new Set(Uses.IDS).size, 8);
  for (const u of Uses.USES) { assert.ok(u.title && u.example && u.chip, u.id); assert.ok(!/\s{2,}/.test(u.title)); }
  for (const t of ['Email monitoring', 'Morning briefing', 'Price and deal tracking', 'School and deadline reminders', 'Research and summaries', 'Calendar and planning', 'Tidy files and downloads', 'News or topic watch'])
    assert.ok(Uses.USES.some((u) => u.title === t), t);
});

test('use -> Glim template: recurring uses give a valid schedule and a safe, monitoring-only task', () => {
  const recurring = Uses.IDS.filter((id) => Uses.templateFor(id));
  assert.deepStrictEqual(recurring, ['email', 'briefing', 'deals', 'school', 'news']);
  assert.deepStrictEqual(['research', 'calendar', 'files'].map(Uses.templateFor), [null, null, null]);
  assert.strictEqual(Uses.templateFor('nope'), null);
  const email = Uses.templateFor('email'), brief = Uses.templateFor('briefing');
  assert.strictEqual(email.name, 'Email watch'); assert.strictEqual(email.every, '30m'); assert.strictEqual(email.at, undefined);
  assert.strictEqual(brief.at, '08:00'); assert.strictEqual(brief.every, undefined);
  const names = new Set();
  for (const id of recurring) {
    const t = Uses.templateFor(id);
    const s = parseSchedule(t);            // the same parser agent_start uses: must accept it and not be one-off
    assert.notStrictEqual(s.kind, 'once', id);
    assert.ok(t.label && t.name.length <= 40 && t.task.length > 80, id);
    assert.match(t.task, /Never send, reply, post, buy, pay, delete, move or change anything without asking Ben first/, id);
    assert.match(t.task, /Monitoring only/, id);
    assert.ok(!names.has(t.name), 'unique name ' + t.name); names.add(t.name);
  }
  const copy = Uses.templateFor('email'); copy.name = 'x'; assert.strictEqual(Uses.templateFor('email').name, 'Email watch'); // a copy, not the table
});

test('a template creates a real Glim through Helpers.add (the agent_start path), with no model call', () => {
  const dir = tmp(); const store = new Store(dir); let ran = 0;
  const m = new Helpers({ file: path.join(dir, 'helpers.json'), store, runner: async () => { ran++; return { report: 'r' }; }, now: () => new Date(2026, 9, 27, 14, 0).getTime() });
  const t = Uses.templateFor('briefing');
  const v = m.add({ name: t.name, task: t.task, every: t.every, at: t.at });
  assert.strictEqual(v.name, 'Morning briefing'); assert.strictEqual(v.schedule, 'daily 08:00');
  assert.strictEqual(new Date(v.next).getHours(), 8); assert.strictEqual(ran, 0); // daily Glims wait for 08:00
  assert.strictEqual(m.list().length, 1);
  assert.throws(() => m.add({ name: t.name, task: t.task, at: t.at }), /already exists/);
});

test('cleanUses / chipsFor / usesLine', () => {
  assert.deepStrictEqual(Uses.cleanUses(['news', 'email', 'bogus', 'email']), ['email', 'news']);
  assert.deepStrictEqual(Uses.cleanUses('email'), []);
  assert.deepStrictEqual(Uses.chipsFor([]), Uses.DEFAULT_CHIPS);
  const c = Uses.chipsFor(['deals', 'school']);
  assert.strictEqual(c.length, 4); assert.strictEqual(c[0], 'Track the price of something for me'); assert.strictEqual(c[1], 'What is due this week?');
  assert.strictEqual(Uses.chipsFor(Uses.IDS).length, 4);
  assert.strictEqual(Uses.usesLine([], ''), '');
  assert.strictEqual(Uses.usesLine(['email', 'briefing'], '  game   news '), '[Background, not a request: Ben mostly wants Glims for email monitoring, morning briefing, game news. Do not start Glims unless he asks.]');
});

test('settings: onboarded / uses / usesOther defaults, validation and persistence', () => {
  const s = new Store(tmp());
  const d = s.getSettings();
  assert.strictEqual(d.onboarded, false); assert.deepStrictEqual(d.uses, []); assert.strictEqual(d.usesOther, '');
  assert.strictEqual(DEFAULT_SETTINGS.onboarded, false);
  const n = s.saveSettings({ onboarded: 1, uses: ['news', 'zzz', 'email', 'email'], usesOther: '  watch   my\nteam  ' });
  assert.strictEqual(n.onboarded, true); assert.deepStrictEqual(n.uses, ['email', 'news']); assert.strictEqual(n.usesOther, 'watch my team');
  assert.strictEqual(sanitize({ usesOther: 'x'.repeat(500) }).usesOther.length, 200);
  assert.deepStrictEqual(sanitize({ uses: 'email' }), { uses: [] });
  assert.deepStrictEqual(sanitize({ onboarded: 'no' }), { onboarded: true }); // truthy string, like every other bool
  assert.deepStrictEqual(new Store(s.dir).getSettings().uses, ['email', 'news']);
  fs.writeFileSync(s.settingsFile, JSON.stringify({ uses: ['email', 5, 'bogus'] }));
  assert.deepStrictEqual(s.getSettings().uses, ['email']); // a hand-edited file cannot smuggle junk in
  assert.strictEqual(s.getSettings().onboarded, false);
});

test('settings: a damaged settings.json falls back to the last good copy, so setup does not come back', () => {
  const s = new Store(tmp());
  s.saveSettings({ onboarded: true, permsSeen: true });
  s.saveSettings({ theme: 'dark' });
  fs.writeFileSync(s.settingsFile, '{"onboarded": tru'); // a write cut off by a quit or a crash
  const g = s.getSettings();
  assert.strictEqual(g.onboarded, true); assert.strictEqual(g.permsSeen, true);
  s.saveSettings({ textSize: 'large' }); // the next save heals the file
  assert.strictEqual(JSON.parse(fs.readFileSync(s.settingsFile, 'utf8')).onboarded, true);
  const n = new Store(tmp()); fs.writeFileSync(n.settingsFile, 'garbage');
  assert.strictEqual(n.getSettings().onboarded, false); // nothing good anywhere: defaults, as before
});

test('picks reach the model only in the first user message beside the date; prompt and tools stay constant', async () => {
  const before = JSON.stringify([SYSTEM_PROMPT, buildTools({ diary: true })]);
  assert.ok(!/mostly wants Glims for/.test(before));
  const gw = await startGateway([{ content: 'ok' }, { content: 'ok again' }]);
  try {
    const mk = () => new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 5, mode: 'hands-off', vision: 'off', uses: ['email'], usesOther: 'game news' }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = { id: 't1', title: 'x', messages: [], items: [] };
    const a = mk();
    await a.run(t, 'hello'); await a.run(t, 'again');
    const users = gw.requests[1].messages.filter((m) => m.role === 'user');
    assert.match(users[0].content, /^\[\w{3} \d{4}-\d{2}-\d{2} \d\d:\d\d\] \[If this needs tools[^\]]*\] \[Background, not a request: Ben mostly wants Glims for email monitoring, game news. Do not start Glims unless he asks.\] hello$/);
    assert.ok(!/mostly wants Glims for/.test(users[1].content));
    assert.ok(!/mostly wants Glims for/.test(gw.requests[0].messages[0].content), 'not in the system prompt');
    assert.strictEqual(JSON.stringify(gw.requests[0].tools), JSON.stringify(gw.requests[1].tools));
    assert.strictEqual(JSON.stringify([SYSTEM_PROMPT, buildTools({ diary: true })]), before);
  } finally { gw.close(); }
});
