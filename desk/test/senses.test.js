'use strict';
// Always-on senses (src/senses.js): consent, sampling only what is on, persistent state, private text dropped. Fakes only.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/senses');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'senses-'));
const fakeSamplers = () => { const calls = { screen: 0, windows: 0 }; return { calls, samplers: { screen: async () => { calls.screen++; return 'Docs: chapter 3 notes ' + calls.screen; }, windows: async () => { calls.windows++; return 'Front app: Notes. ' + calls.windows; } } }; };

test('every sense is off by default and the card is needed', () => {
  const c = S.loadConsent(tmp());
  for (const id of S.IDS) assert.strictEqual(c.senses[id], false, id);
  assert.strictEqual(S.needsConsent(c), true);
});

test('every sense off => zero sampling calls, and pushes of off senses are ignored', async () => {
  const dir = tmp(), f = fakeSamplers(); let t = 1000;
  const st = new S.AlwaysOnState(dir, { now: () => t });
  const s = new S.Senses({ consent: S.defaults(), state: st, samplers: f.samplers, now: () => t });
  for (let i = 0; i < 10; i++) { t += 60000; await s.sample(); }
  assert.deepStrictEqual(f.calls, { screen: 0, windows: 0 });
  assert.deepStrictEqual(s.calls, { screen: 0, windows: 0 });
  assert.strictEqual(s.push('hearing', 'hello there'), null);
  assert.strictEqual(s.push('chats', 'hi'), null);
  assert.strictEqual(st.inbox.length, 0);
  // the global switch off also silences an enabled sense
  const c = S.defaults(); c.senses.screen = true; c.on = false; s.setConsent(c);
  t += 60000; await s.sample();
  assert.strictEqual(f.calls.screen, 0);
});

test('only the senses that are on are sampled, at most every 20 s, and repeats are not stored', async () => {
  const dir = tmp(), f = fakeSamplers(); let t = 1000;
  const st = new S.AlwaysOnState(dir, { now: () => t });
  const c = S.defaults(); c.senses.windows = true;
  const s = new S.Senses({ consent: c, state: st, samplers: f.samplers, now: () => t });
  await s.sample(); t += 5000; await s.sample();
  assert.deepStrictEqual(f.calls, { screen: 0, windows: 1 });
  t += 20000; await s.sample();
  assert.strictEqual(f.calls.windows, 2); assert.strictEqual(st.inbox.length, 2);
  assert.strictEqual(st.add('windows', st.inbox[1].text), null); // same text again: not stored
});

test('consent is saved and reloaded; Remember my choice stops the card', () => {
  const dir = tmp();
  const c = S.defaults(); c.senses.screen = true; c.senses.hearing = true; c.remember = true; c.decidedAt = 5;
  S.saveConsent(dir, c);
  const back = S.loadConsent(dir);
  assert.strictEqual(back.senses.screen, true); assert.strictEqual(back.senses.hearing, true); assert.strictEqual(back.senses.windows, false);
  assert.strictEqual(S.needsConsent(back), false);
  const raw = JSON.parse(fs.readFileSync(path.join(dir, 'senses.json'), 'utf8'));
  assert.strictEqual(raw.remember, true);
  // junk values are not "on"
  fs.writeFileSync(path.join(dir, 'senses.json'), JSON.stringify({ senses: { screen: 'yes', web: 1 }, remember: true }));
  const j = S.loadConsent(dir); assert.strictEqual(j.senses.screen, false); assert.strictEqual(j.senses.web, false);
});

test('missing macOS permissions are named for the chosen senses only', () => {
  const c = S.defaults(); c.senses.screen = true; c.senses.hearing = true;
  const m = S.missingPerms(c, { screenRecording: false, accessibility: false, microphone: true });
  assert.deepStrictEqual(m.map((x) => x.sense), ['screen']);
});

test('the state file survives a restart (inbox, focus, last-spoke time, read cursor)', () => {
  const dir = tmp(); let t = 10000;
  const a = new S.AlwaysOnState(dir, { now: () => t });
  a.add('screen', 'Chemistry lab report draft'); t += 10; a.add('hearing', 'remind me about the lab at 3');
  a.markRead(); t += 10; a.add('chats', 'what is due tomorrow');
  a.setFocus('photosynthesis'); a.spoke();
  const b = new S.AlwaysOnState(dir, { now: () => t });
  assert.strictEqual(b.inbox.length, 3);
  assert.strictEqual(b.focus.topic, 'photosynthesis');
  assert.strictEqual(b.lastSpokeAt, t);
  assert.deepStrictEqual(b.fresh().map((x) => x.sense), ['chats']);
});

test('the inbox keeps the last N entries, each clipped', () => {
  const dir = tmp(); let t = 0;
  const a = new S.AlwaysOnState(dir, { now: () => ++t, max: 5 });
  for (let i = 0; i < 9; i++) a.add('screen', 'line ' + i + ' ' + 'x'.repeat(2000));
  assert.strictEqual(a.inbox.length, 5);
  assert.ok(a.inbox.every((x) => x.text.length <= S.MAX_TEXT));
  assert.match(a.inbox[0].text, /^line 4/);
});

test('private observations are dropped before storage: password, keychain, bank sign-in, codes', async () => {
  const dir = tmp(); let t = 1;
  const a = new S.AlwaysOnState(dir, { now: () => ++t });
  const bad = [
    'Enter your password to continue',
    'Keychain Access — login keychain',
    'Chase Online Banking — Sign in to your account',
    'Bank of America | Log In | Online ID',
    'Your verification code is 482913',
    'Routing number 021000021',
    'ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234'
  ];
  for (const b of bad) assert.strictEqual(a.add('screen', b), null, b);
  assert.strictEqual(a.inbox.length, 0);
  assert.strictEqual(a.dropped, bad.length);
  const file = path.join(dir, S.STATE_FILE);
  if (fs.existsSync(file)) { const raw = fs.readFileSync(file, 'utf8'); assert.ok(!/password|Chase|482913/i.test(raw)); }
  assert.ok(a.add('screen', 'AP Chemistry: kinetics worksheet due Friday'));
  // and through the sampler path too
  const c = S.defaults(); c.senses.screen = true;
  const s = new S.Senses({ consent: c, state: a, now: () => (t += 30000), samplers: { screen: async () => 'Wells Fargo sign in — account balance' } });
  await s.sample();
  assert.strictEqual(a.inbox.length, 1);
});

test('a sampler that returns something other than words is ignored', async () => {
  const dir = tmp(); let t = 0;
  const a = new S.AlwaysOnState(dir, { now: () => (t += 30000) });
  const c = S.defaults(); c.senses.screen = true;
  const s = new S.Senses({ consent: c, state: a, now: () => (t += 30000), samplers: { screen: async () => Buffer.from([1, 2, 3]) } });
  await s.sample();
  assert.strictEqual(a.inbox.length, 0);
});

test('windowsText turns helper JSON into words without ids or coordinates', () => {
  const t = S.windowsText({ front: 'Notes', windows: [{ app: 'Notes', title: 'Lab plan' }, { app: 'Safari', title: '' }] }, { app: 'Notes', elements: [{ id: 3, role: 'AXTextArea', title: 'Body', value: 'Step 1: weigh', frame: [1, 2, 3, 4] }] });
  assert.match(t, /Front app: Notes\. Open: Notes — Lab plan; Safari\./);
  assert.match(t, /In Notes: Body: Step 1: weigh/);
  assert.ok(!/AXTextArea|\[3\]/.test(t));
});

test('Ben Nov 4 "just give it": no start-up card; an undecided consent starts with every sense on and remembered; a remembered choice is kept', () => {
  assert.strictEqual(S.ASK_AT_START, false, 'one switch brings the card back');
  const r = S.startConsent(S.loadConsent(tmp()), 42);
  assert.strictEqual(r.granted, true);
  for (const id of ['screen', 'windows', 'hearing', 'chats', 'web']) assert.strictEqual(r.consent.senses[id], true, id);
  assert.deepStrictEqual(S.IDS.slice().sort(), ['chats', 'hearing', 'screen', 'web', 'windows']);
  assert.strictEqual(r.consent.remember, true); assert.strictEqual(r.consent.on, true); assert.strictEqual(r.consent.decidedAt, 42);
  assert.strictEqual(S.needsConsent(r.consent), false, 'so the card is not shown');
  // a choice Ben already remembered (e.g. hearing off) is never overwritten
  const mine = S.defaults(); mine.senses.screen = true; mine.remember = true; mine.decidedAt = 5;
  assert.deepStrictEqual(S.startConsent(mine, 99), { consent: S.normalize(mine), granted: false });
  // the old behaviour is one flag away
  assert.strictEqual(S.startConsent(S.defaults(), 1, true).granted, false);
  // main.js uses it before the Senses are made and saves the given consent; Settings > Senses still has every switch
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /const sc = SensesMod\.startConsent\(SensesMod\.loadConsent\(aoDir\(\)\)\);[^\n]*\n  if \(sc\.granted\) \{ try \{ SensesMod\.saveConsent\(aoDir\(\), sc\.consent\); \}/);
  assert.match(m, /aoSenses = new SensesMod\.Senses\(\{ consent: sc\.consent,/);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'renderer/senses.js'), 'utf8'), /function settingsUi\(\)/);
});
