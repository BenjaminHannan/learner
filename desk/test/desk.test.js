'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const { Store, DEFAULT_SETTINGS, sanitize } = require('../src/store');
const { isBrowserApp, BROWSER_REFUSAL, createScreen } = require('../src/tools/screen');
const { Warmer, buildWarmBody, WARM_MODEL, WARM_HEADER } = require('../src/warm');
const { buildChatBody } = require('../src/llm');
const { SYSTEM_PROMPT, buildTools } = require('../src/prompt');
const { Agent, DANGER_LABELS } = require('../src/agent');
const { PillState } = require('../src/pillstate');
const { ensureCard } = require('../src/cards');
const Guard = require('../renderer/guard');
const Md = require('../renderer/md');
const { startGateway } = require('./helpers');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'desk-t-'));

// ---- settings -----------------------------------------------------------------------------------------
test('every setting has a default; saveSettings clamps, validates and ignores unknown keys', () => {
  const s = new Store(tmp());
  const d = s.getSettings();
  for (const k of ['onboarded', 'uses', 'usesOther', 'gatewayUrl', 'model', 'mode', 'helperMode', 'maxSteps', 'maxParallel', 'vision', 'diaryEnabled', 'diaryPath', 'pythonPath', 'helperPath', 'theme', 'textSize', 'highContrast', 'verify', 'pill', 'openAtLogin', 'keepRunning', 'hotkey']) assert.ok(k in d, k);
  assert.strictEqual(d.verify, true); assert.strictEqual(s.saveSettings({ verify: false }).verify, false); assert.strictEqual(s.saveSettings({ verify: 'x' }).verify, true);
  assert.strictEqual(d.keepRunning, true); assert.strictEqual(d.hotkey, 'Alt+Space'); assert.strictEqual(d.openAtLogin, false);
  const n = s.saveSettings({ maxSteps: 9999, maxParallel: 0, theme: 'neon', textSize: 'l', mode: 'hands-off', evil: 1, gatewayUrl: '  ', hotkey: 'Alt+Space ', vision: true });
  assert.strictEqual(n.maxSteps, 200); assert.strictEqual(n.maxParallel, 1); assert.strictEqual(n.theme, 'system'); assert.strictEqual(n.textSize, 'l');
  assert.strictEqual(n.mode, 'hands-off'); assert.ok(!('evil' in n)); assert.strictEqual(n.gatewayUrl, DEFAULT_SETTINGS.gatewayUrl); assert.strictEqual(n.vision, 'on');
  assert.strictEqual(new Store(s.dir).getSettings().textSize, 'l'); // persisted
  assert.deepStrictEqual(sanitize({ pill: 0, keepRunning: 'x' }), { pill: false, keepRunning: true });
});

// ---- open_app refuses browsers --------------------------------------------------------------------------
test('open_app refuses Safari, Chrome, Firefox, Arc, Edge (use browser_go) and never calls the helper', async () => {
  for (const n of ['Safari', 'safari', 'Safari.app', 'Google Chrome', 'Chrome', 'Firefox', 'Arc', 'Microsoft Edge', 'Brave Browser']) assert.ok(isBrowserApp(n), n);
  for (const n of ['Notes', 'Finder', 'System Settings', 'Spotify', 'Archive Utility']) assert.ok(!isBrowserApp(n), n);
  const s = createScreen(() => ({ helperPath: '/definitely/not/here' }), null, null);
  const r = await s.tools.open_app({ name: 'Safari' }, {});
  assert.strictEqual(r.error, true); assert.strictEqual(r.text, BROWSER_REFUSAL); assert.match(r.text, /browser_go/);
  const ok = await s.tools.open_app({ name: 'Notes' }, {});
  assert.match(ok.text, /not installed/); // went on to the helper path (which is missing here)
});

// ---- warm-up -------------------------------------------------------------------------------------------
test('warm body: same builder, system+tools+tool_choice identical to a real request, tiny and non-streaming', () => {
  const tools = buildTools({ diary: true });
  const warm = buildWarmBody(tools);
  const real = buildChatBody({ model: 'qwen36-auto', messages: [{ role: 'system', content: SYSTEM_PROMPT }, { role: 'user', content: '[Tue 2026-10-27 14:05] hello' }], tools, stream: true });
  assert.strictEqual(warm.model, 'qwen36-fast'); assert.strictEqual(warm.max_tokens, 1); assert.strictEqual(warm.stream, false);
  assert.deepStrictEqual(warm.messages[1], { role: 'user', content: '.' });
  assert.strictEqual(JSON.stringify(warm.messages[0]), JSON.stringify(real.messages[0]));
  assert.strictEqual(JSON.stringify(warm.tools), JSON.stringify(real.tools));
  assert.strictEqual(warm.tool_choice, real.tool_choice);
  assert.deepStrictEqual(Object.keys(warm).filter((k) => !['max_tokens', 'stream', 'model', 'messages'].includes(k)), Object.keys(real).filter((k) => !['stream', 'model', 'messages'].includes(k)));
  assert.ok(!/\d{4}-\d{2}-\d{2}/.test(JSON.stringify(warm.messages[0]))); // no date in the system part
});

test('Warmer: warms when the gateway comes up (poll while down), once; rewarm on demand; sends the warm header; never needs the script', async () => {
  const gw = await startGateway([{ content: 'x' }]);
  const url = gw.url;
  const states = [];
  let settings = { gatewayUrl: 'http://127.0.0.1:1/v1' }; // nothing listens there: down
  const tools = buildTools({ diary: false });
  const w = new Warmer({ getSettings: () => settings, getTools: () => tools, onState: (s) => states.push(s), downMs: 20, upMs: 60 });
  w.start();
  await new Promise((r) => setTimeout(r, 120));
  assert.strictEqual(w.state, 'down'); assert.strictEqual(gw.warms.length, 0);
  settings = { gatewayUrl: url }; // "the model started"
  for (let i = 0; i < 100 && gw.warms.length < 1; i++) await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(gw.warms.length, 1);
  assert.strictEqual(gw.warms[0].headers[WARM_HEADER.toLowerCase()], '1');
  assert.strictEqual(gw.warms[0].body.model, WARM_MODEL);
  assert.deepStrictEqual(gw.warms[0].body.tools, tools);
  assert.strictEqual(gw.warms[0].body.messages[0].content, SYSTEM_PROMPT);
  await new Promise((r) => setTimeout(r, 250));
  assert.strictEqual(gw.warms.length, 1, 'still up: no repeated warming');
  assert.ok(states.includes('warming') && states.at(-1) === 'ready');
  w.rewarm();
  for (let i = 0; i < 100 && gw.warms.length < 2; i++) await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(gw.warms.length, 2);
  assert.strictEqual(gw.requests.length, 0); // warm requests never touch real traffic
  w.stop(); gw.close();
});

// ---- composer guard, markdown --------------------------------------------------------------------------
test('composer guard: catches passwords and codes, leaves normal messages alone', () => {
  for (const t of ['my password is hunter2', 'password: abc123', 'pw is 1234', 'Password = x', 'my gmail password is x', 'my verification code is 123456'])
    assert.ok(Guard.looksLikeSecret(t), t);
  for (const t of ['open gmail and read my mail', 'how do I reset my password?', 'the password manager is nice', 'find me a passport office', 'what is the code of conduct'])
    assert.ok(!Guard.looksLikeSecret(t), t);
});

test('markdown: hides [Action: ...] lines, escapes HTML, keeps real brackets', () => {
  const html = Md.md('Opening it.\n[Action: Click the Continue button]\n  [action: type the email ]\nDone <script>x</script> [1] ok');
  assert.ok(!/Action/i.test(html)); assert.ok(!/<script>/.test(html)); assert.match(html, /Opening it\./); assert.match(html, /\[1\] ok/);
  assert.ok(Md.isActionLine('[Action: Click X]')); assert.ok(!Md.isActionLine('I did [Action: x] earlier'));
  assert.strictEqual(Md.stripActions('a\n[Action: b]\nc'), 'a\nc');
});

// ---- pill state ------------------------------------------------------------------------------------------
test('pill state: priority error > waiting > working > done; done fades after 8 s; error/waiting stay until seen', () => {
  let t = 1000; const changes = [];
  const p = new PillState({ now: () => t, onChange: () => changes.push(1) });
  assert.strictEqual(p.view().visible, false); assert.strictEqual(p.status(), 'idle');
  p.onEvent('main', 'Glim', 't1', { type: 'started' });
  p.onEvent('main', 'Glim', 't1', { type: 'step_start', summary: 'Opened gmail.com' });
  let v = p.view();
  assert.ok(v.visible); assert.strictEqual(v.mood, 'working'); assert.strictEqual(v.line, 'Opened gmail.com');
  p.onEvent('h1', 'site-checker', 'th', { type: 'step_start', summary: 'Searched “x”' });
  p.onEvent('h1', 'site-checker', 'th', { type: 'approval', rid: 'th:s', kind: 'shell', text: 'ls' });
  v = p.view();
  assert.strictEqual(v.status, 'waiting'); assert.strictEqual(v.line, 'Waiting for you'); assert.strictEqual(v.top.name, 'site-checker'); assert.strictEqual(v.others[0].name, 'Glim');
  p.onEvent('main', 'Glim', 't1', { type: 'error', message: 'Gateway error 500' });
  v = p.view();
  assert.strictEqual(v.status, 'error'); assert.strictEqual(v.mood, 'error'); assert.strictEqual(v.line, 'Something went wrong'); assert.strictEqual(v.top.error, 'Gateway error 500');
  p.onEvent('main', 'Glim', 't1', { type: 'done' });
  assert.strictEqual(p.view().status, 'error'); // done does not hide an error
  t += 60000; p.tick(); assert.strictEqual(p.view().status, 'error', 'errors stay until seen');
  p.markSeen('t1'); assert.strictEqual(p.view().status, 'waiting');
  p.onEvent('h1', 'site-checker', 'th', { type: 'resumed' }); assert.strictEqual(p.view().status, 'working');
  p.onEvent('h1', 'site-checker', 'th', { type: 'assistant_end', text: 'Report: all good' });
  p.onEvent('h1', 'site-checker', 'th', { type: 'done' }, { title: 'site-checker' });
  v = p.view(); assert.strictEqual(v.status, 'done'); assert.strictEqual(v.line, 'Done: site-checker');
  t += 7000; p.tick(); assert.ok(p.view().visible);
  t += 2000; p.tick(); assert.strictEqual(p.view().visible, false);
  p.onEvent('main', 'Glim', 't1', { type: 'started' }); p.onEvent('main', 'Glim', 't1', { type: 'done', stopped: true });
  assert.strictEqual(p.view().visible, false, 'a stopped run leaves nothing behind');
  assert.ok(changes.length > 5);
});

// ---- cards -------------------------------------------------------------------------------------------------
test('cards: one browser card per activity group, a new one after Ben speaks again', () => {
  const t = { items: [{ t: 'user', text: 'a' }, { t: 'step' }] };
  const c1 = ensureCard(t, 'browser', 'primary', { url: 'u' });
  t.items.push({ t: 'step' });
  assert.strictEqual(ensureCard(t, 'browser', 'primary'), c1);
  assert.notStrictEqual(ensureCard(t, 'browser', 'other'), c1);
  t.items.push({ t: 'assistant', text: 'done' }, { t: 'user', text: 'b' }, { t: 'step' });
  const c2 = ensureCard(t, 'browser', 'primary');
  assert.notStrictEqual(c2, c1); assert.strictEqual(t.items.filter((i) => i.t === 'browser' && i.key === 'primary').length, 2);
});

test('danger list has a plain-language view', () => { assert.ok(DANGER_LABELS.length >= 8); assert.ok(DANGER_LABELS.every((x) => typeof x === 'string' && x.length > 8)); });

// ---- text contrast (WCAG AA) ------------------------------------------------------------------------------
test('theme tokens: all text pairs are at least 4.5:1 in dark and light (and high contrast)', () => {
  const css = fs.readFileSync(path.join(__dirname, '..', 'renderer', 'theme.css'), 'utf8');
  const hex = (h) => { h = h.replace('#', ''); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); };
  const lum = (h) => { const [r, g, b] = hex(h).map((c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const grab = (block) => { const o = {}; for (const m of block.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)) o[m[1]] = m[2]; return o; };
  const dark = grab(css.slice(css.indexOf(':root'), css.indexOf('@media')));
  const light = { ...dark, ...grab(css.slice(css.indexOf('@media'), css.indexOf('html.ts-s'))) };
  for (const [name, t] of [['dark', dark], ['light', light]]) {
    for (const bg of ['bg', 'surface', 'raised', 'bubble']) {
      for (const fg of ['text', 'text2', 'faint', 'accent-text']) assert.ok(ratio(t[fg], t[bg]) >= 4.5, name + ' ' + fg + ' on ' + bg + ' = ' + ratio(t[fg], t[bg]).toFixed(2));
    }
    for (const fg of ['danger', 'ok']) for (const bg of ['bg', 'surface', 'raised']) assert.ok(ratio(t[fg], t[bg]) >= 4.5, name + ' ' + fg + ' on ' + bg + ' = ' + ratio(t[fg], t[bg]).toFixed(2));
    assert.ok(ratio(t['on-accent'], t.accent) >= 4.5, name + ' on-accent');
    assert.ok(ratio(t['on-danger'], t.danger) >= 4.5, name + ' on-danger');
  }
});

test('sleep settings: defaults, HH:MM validation, idle minutes clamp', () => {
  const s = new Store(tmp());
  const d = s.getSettings();
  assert.strictEqual(d.autoSleep, true); assert.strictEqual(d.sleepFrom, '23:00'); assert.strictEqual(d.sleepTo, '08:00'); assert.strictEqual(d.sleepIdleMin, 120); assert.strictEqual(d.sleepAdapt, true); assert.strictEqual(d.wakeAt, false); assert.strictEqual(d.sleepPauseGlims, true); assert.strictEqual(d.sleepDuration, 'morning'); assert.strictEqual(d.sleepCheckinMins, 60); assert.strictEqual(d.sleepApp, '');
  const n = s.saveSettings({ sleepFrom: '9:05', sleepTo: '25:00', sleepIdleMin: 99999, autoSleep: 1 });
  assert.strictEqual(n.sleepFrom, '09:05'); assert.strictEqual(n.sleepTo, '08:00'); assert.strictEqual(n.sleepIdleMin, 720); assert.strictEqual(n.autoSleep, true);
});
