'use strict';
// SECURE-LOGIN (Ben 2026-11-05): logins come through the app's private form, never chat. Marks S2, S5, S6, S7 (docs/secure-login/MARKS.md).
// Everything here is in memory (MemoryBox): no keychain, no userData.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const L = require('../src/logins');
const F = require('../src/loginform');
const { SafetyLevels } = require('../src/safety-levels');
const { SYSTEM_PROMPT, TOOL_DEFS, buildTools } = require('../src/prompt');
const Kit = require('../src/agentkit');
const { Agent, asksForSecret } = require('../src/agent');

const PW = 'Sx-' + Math.random().toString(36).slice(2, 10) + '-9q!';
const tick = () => new Promise((r) => setImmediate(r));
function rig(o) {
  o = o || {};
  const store = new L.LoginStore({ box: new L.MemoryBox() });
  const opened = [], notes = [], closed = [];
  let away = !!o.away;
  const ask = new F.LoginAsk({ store, waitMs: o.waitMs == null ? 2000 : o.waitMs, isAway: () => away,
    open: (f) => { opened.push(f); return { show: () => {}, close: () => closed.push(f.token) }; },
    notify: (title, body, onClick) => notes.push({ title, body, onClick }) });
  return { store, ask, opened, notes, closed, setAway: (v) => { away = v; } };
}

test('resolveOrigin: the open page wins for the same site or a subdomain; https only; bare words match the page', () => {
  assert.strictEqual(F.resolveOrigin('google.com', 'https://accounts.google.com/signin?x=1'), 'https://accounts.google.com');
  assert.strictEqual(F.resolveOrigin('', 'https://dresden.schoology.com/home'), 'https://dresden.schoology.com');
  assert.strictEqual(F.resolveOrigin('schoology', 'https://dresden.schoology.com/home'), 'https://dresden.schoology.com');
  assert.strictEqual(F.resolveOrigin('https://x.com/login', 'https://accounts.google.com/'), 'https://x.com');
  assert.strictEqual(F.resolveOrigin('http://x.com', ''), null);
  assert.strictEqual(F.resolveOrigin('', 'http://127.0.0.1:8080/'), null);
  assert.strictEqual(F.resolveOrigin('', ''), null);
});

test('S3 logic: Ben here -> one app form opens; Save goes to the store; the waiting call reads {saved:true, site} and no secret', async () => {
  const R = rig();
  const p = R.ask.ask({ site: 'accounts.google.com', reason: 'to read your webmail', pageUrl: 'https://accounts.google.com/signin' });
  await tick();
  assert.strictEqual(R.opened.length, 1); assert.strictEqual(R.opened[0].host, 'accounts.google.com'); assert.strictEqual(R.opened[0].focus, true);
  assert.ok(!('password' in R.opened[0]) && !JSON.stringify(R.opened[0]).includes(PW));
  const p2 = R.ask.ask({ pageUrl: 'https://accounts.google.com/x' });   // S5: same site again while open -> joins, no 2nd window
  await tick();
  assert.strictEqual(R.opened.length, 1);
  const s = await R.ask.submit(R.opened[0].token, 'ben@example.org', PW);
  assert.deepStrictEqual(s, { ok: true, host: 'accounts.google.com' });
  const [r, r2] = await Promise.all([p, p2]);
  assert.deepStrictEqual(r, { saved: true, site: 'accounts.google.com', state: 'saved' }); assert.strictEqual(r2.saved, true);
  assert.deepStrictEqual(R.closed, [R.opened[0].token]);
  const login = await R.store.forPage('https://accounts.google.com/signin');
  assert.strictEqual(login.password, PW); assert.strictEqual(login.user, 'ben@example.org');
  const m = F.modelResult(r);
  assert.ok(m.text.startsWith('{"saved":true,"site":"accounts.google.com"}'));
  assert.ok(!JSON.stringify(m).includes(PW) && !JSON.stringify(m).includes('ben@example.org'));
  // S4 logic: saved now -> no form at all
  const r3 = await R.ask.ask({ pageUrl: 'https://accounts.google.com/signin' });
  assert.deepStrictEqual(r3, { saved: true, site: 'accounts.google.com', state: 'already' }); assert.strictEqual(R.opened.length, 1);
});

test('Cancel -> {saved:false}; a stale or foreign token saves nothing; an empty password is refused and the form stays', async () => {
  const R = rig();
  const p = R.ask.ask({ pageUrl: 'https://x.com/login' }); await tick();
  assert.strictEqual((await R.ask.submit('nope', 'u', PW)).ok, false);
  const bad = await R.ask.submit(R.opened[0].token, 'u', '');
  assert.strictEqual(bad.ok, false); assert.strictEqual(R.closed.length, 0);
  R.ask.cancel(R.opened[0].token);
  assert.deepStrictEqual(await p, { saved: false, site: 'x.com', state: 'cancelled' });
  assert.strictEqual(R.store.item('https://x.com'), null);
  // closing the window with its own button = Cancel (no throw on a gone token)
  const p2 = R.ask.ask({ pageUrl: 'https://x.com/login' }); await tick();
  R.ask.closed(R.opened[1].token); R.ask.closed(R.opened[1].token);
  assert.strictEqual((await p2).state, 'cancelled');
});

test('S5: Ben away or a Mote -> queued at once, ONE notification, no window; asking again adds nothing; Cancel stops Mote re-asks', async () => {
  const R = rig({ away: true });
  const r1 = await R.ask.ask({ pageUrl: 'https://accounts.google.com/signin', reason: 'webmail check' });
  assert.deepStrictEqual(r1, { saved: false, site: 'accounts.google.com', state: 'queued' });
  assert.strictEqual(R.opened.length, 0); assert.strictEqual(R.notes.length, 1); assert.match(R.notes[0].body, /accounts\.google\.com/);
  const r2 = await R.ask.ask({ pageUrl: 'https://accounts.google.com/signin', helper: true });
  assert.strictEqual(r2.state, 'queued'); assert.strictEqual(R.notes.length, 1); assert.strictEqual(R.opened.length, 0);
  assert.match(F.modelResult(r1).text, /End this run now/); assert.match(F.modelResult(r1).text, /Never ask for the password in chat/);
  // Ben clicks the notification -> the form opens (once)
  R.notes[0].onClick(); R.notes[0].onClick();
  assert.strictEqual(R.opened.length, 1);
  R.ask.cancel(R.opened[0].token);
  // a Mote asking the same site again soon after Cancel: nothing new (no form, no notification)
  const r3 = await R.ask.ask({ pageUrl: 'https://accounts.google.com/signin', helper: true });
  assert.strictEqual(r3.state, 'declined'); assert.strictEqual(R.notes.length, 1); assert.strictEqual(R.opened.length, 1);
  // Ben back + the main chat asks for that site: the form does open again (it is his own ask)
  R.setAway(false);
  const p4 = R.ask.ask({ pageUrl: 'https://accounts.google.com/signin' }); await tick();
  assert.strictEqual(R.opened.length, 2);
  await R.ask.submit(R.opened[1].token, 'ben', PW);
  assert.strictEqual((await p4).saved, true);
});

test('a Mote queues while Ben is here too (never puts a window in front of him); openQueued shows it without focus when he is back', async () => {
  const R = rig({ away: false });
  const r = await R.ask.ask({ pageUrl: 'https://mail.example.org/', helper: true });
  assert.strictEqual(r.state, 'queued'); assert.strictEqual(R.opened.length, 0); assert.strictEqual(R.notes.length, 1);
  assert.deepStrictEqual(R.ask.pending(), [{ host: 'mail.example.org', open: false, queued: true }]);
  R.ask.openQueued(null, false);
  assert.strictEqual(R.opened.length, 1); assert.strictEqual(R.opened[0].focus, false);
  // and the main chat waiting on an open form that Ben leaves: 'waiting', the form stays open
  const R2 = rig({ waitMs: 30 });
  const w = await R2.ask.ask({ pageUrl: 'https://y.org/' });
  assert.strictEqual(w.state, 'waiting'); assert.strictEqual(R2.closed.length, 0);
});

test('S2: every model-visible result is {saved, site} + a fixed hint; none holds the password, even after a save', async () => {
  L.addSecret(PW);
  for (const st of ['saved', 'already', 'cancelled', 'declined', 'queued', 'waiting', 'badsite', 'failed']) {
    const m = F.modelResult({ saved: st === 'saved' || st === 'already', site: 'x.com', state: st });
    const head = JSON.parse(m.text.split('\n')[0]);
    assert.deepStrictEqual(Object.keys(head), ['saved', 'site']);
    assert.ok(!JSON.stringify(m).includes(PW));
    assert.ok(!/(give|tell|send|share|type) (me )?(the|your) password/i.test(m.text), st);
  }
  // the Agent's tool runner around ask_login: the result, the events and the thread hold no secret (and a slip is scrubbed)
  const evs = [];
  const a = new Agent({ getSettings: () => ({ mode: 'ask-first' }), tools: { ask_login: async () => ({ ...F.modelResult({ saved: true, site: 'x.com', state: 'saved' }), summary: 'slip ' + PW }) },
    emit: (e) => evs.push(e), approve: async () => { throw new Error('ask_login must never ask for approval'); }, askUser: async () => '', safety: new SafetyLevels() });
  const th = { id: 't', messages: [], items: [] };
  const r = await a.runTool({ id: '1', name: 'ask_login', arguments: '{"site":"x.com"}' }, th, new AbortController().signal);
  assert.match(r.text, /^\{"saved":true,"site":"x\.com"\}/);
  assert.ok(!JSON.stringify([r, evs, th]).includes(PW));
});

test('S6: ask_login is never refused or approval-gated at any safety level; browser_sign_in keeps its rows', () => {
  const lv = new SafetyLevels();
  for (const level of ['free', 'ask', 'never']) {
    lv.set([{ cat: 'passwords', level }, { cat: 'browse', level }], { source: 'settings' });
    const c = lv.check('ask_login', { site: 'x.com' }, { pageUrl: 'https://www.chase.com/' });
    assert.strictEqual(c.cat, null); assert.ok(!c.refuse); assert.notStrictEqual(c.level, 'ask');
  }
  assert.strictEqual(new SafetyLevels().check('browser_sign_in', {}, { pageUrl: 'https://dresden.schoology.com/' }).level, 'free');
});

test('S7: prompts say saved login -> browser_sign_in, none -> ask_login, never a password in chat; the chat self-check is on', () => {
  assert.ok(!/passwords in chat are fine/i.test(SYSTEM_PROMPT));
  assert.ok(!/ask him for it/i.test(SYSTEM_PROMPT));
  assert.match(SYSTEM_PROMPT, /never ask Ben for a password in chat/);
  assert.match(SYSTEM_PROMPT, /None saved: ask_login/);
  assert.ok(TOOL_DEFS.ask_login); assert.ok(buildTools({}).some((t) => t.function.name === 'ask_login'));
  assert.ok(Kit.dietTools(buildTools({})).some((t) => t.function.name === 'ask_login'));   // a web task keeps it
  assert.match(Kit.dietSystem(SYSTEM_PROMPT), /None saved: ask_login/);
  assert.match(L.say.noLogin('x.com'), /call ask_login/); assert.match(L.say.noLogin('x.com'), /Never ask for the password in chat/);
  const agentSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'agent.js'), 'utf8');
  assert.match(agentSrc, /const SECRET_RECHECK = true;/);
  assert.ok(!/type the password Ben gave you, or ask him for it/.test(agentSrc));
  assert.ok(asksForSecret('Please provide your Google account email/username and password so I can continue the monitoring report.'));   // the Mote reply of 2026-11-05
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /ask_login: async \(x, ctx\) => \{/);
  assert.match(main, /const r = await LoginFormMod\.signInWithAsk\(\{ br: b, store: glimLogins\(\), askFor: \(url, site, why\) => loginAskFor\(isHelper, url, site, why, ctx\) \}\);/);
  assert.match(main, /ipcMain\.handle\('loginform:save', \(e, token, user, password\) => \(formSender\(e, token\)/);
});

test('the password-in-chat self-check sends a reply that asks for a password back once, pointing to ask_login', async () => {
  const { startGateway } = require('./helpers');
  const gw = await startGateway([{ content: 'Please provide your Google account email and password so I can continue.' }, { content: 'The sign-in is waiting for you in the private form.' }]);
  try {
    const a = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 40, mode: 'hands-off', vision: 'off', verify: false, thinkCapSecs: 0 }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = { id: 't1', title: 'x', messages: [], items: [] };
    await a.run(t, 'check my webmail');
    assert.strictEqual(gw.requests.length, 2);
    const last = gw.requests[1].messages.at(-1).content;
    assert.match(last, /never ask Ben for a password or login details in chat/); assert.match(last, /ask_login/);
  } finally { gw.close(); }
});
