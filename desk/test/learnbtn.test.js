'use strict';
// Learn button (replaced the toolbar's Browser button): wiring + the pure study logic + the renderer script in a tiny fake DOM.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const { LearnButton, COUNT, FOREVER } = require('../src/learnbutton');

const root = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');

test('the toolbar has a Learn button and no Browser button', () => {
  const html = read('renderer/index.html');
  const bar = html.slice(html.indexOf('<header id="topbar">'), html.indexOf('</header>'));
  assert.ok(!/id="btnBrowser"/.test(html), '#btnBrowser is gone');
  assert.match(bar, /<button id="btnLearn" class="tb-btn"/);
  assert.match(bar, /id="learnPop"/); assert.match(bar, /id="learnStop"/); assert.match(bar, /id="learnShowBrowser"/); assert.match(bar, /id="learnViewQuiz"/);
  // Ben Nov 4: no idle popup with its own text box; Learn mode lives in the chat box
  for (const gone of ['learnTopic"', 'learnStart', 'learnIdle', 'e.g. enzyme kinetics']) assert.ok(!html.includes(gone), gone + ' is gone');
  assert.match(read('renderer/learnbtn.js'), /What should Glim learn about\?/);
  assert.match(read('renderer/learnbtn.js'), /Enter to start learning · Esc to cancel/);
  assert.ok(html.indexOf('<script src="panel.js">') < html.indexOf('<script src="learnbtn.js">'));
  for (const f of ['renderer/panel.js', 'renderer/app.js', 'renderer/learnbtn.js']) assert.ok(!/btnBrowser/.test(read(f)), f);
});

test('Start = Learn mode with lifetime forever (hours 0, like "until I stop them"); Stop stops every Mote it started', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lb-'));
  const calls = { start: [], stop: [] }, views = [];
  const mk = () => new LearnButton({ dir, startLearn: (t, n, h) => { calls.start.push([t, n, h]); return { ok: true, ids: ['h1', 'h2', 'h3'], topic: t }; }, stopMote: (id) => calls.stop.push(id), onChange: (v) => views.push(v) });
  const b = mk();
  assert.strictEqual(FOREVER, 0);
  assert.deepStrictEqual(b.start('  enzyme   kinetics '), { ok: true, learning: true, topic: 'enzyme kinetics', since: b.cur.since, count: 3, by: 'ben', partial: null });
  assert.deepStrictEqual(calls.start, [['enzyme kinetics', COUNT, 0]]);
  assert.strictEqual(views.pop().topic, 'enzyme kinetics');
  // survives a restart, then Stop
  const b2 = mk();
  assert.deepStrictEqual(b2.view().topic, 'enzyme kinetics');
  assert.deepStrictEqual(b2.stop(), { ok: true, learning: false, stopped: 'enzyme kinetics' });
  assert.deepStrictEqual(calls.stop, ['h1', 'h2', 'h3']);
  assert.deepStrictEqual(mk().view(), { learning: false });
  assert.ok(b.start('').error);
});

test('main.js serves learn:start through startLearn and stops Motes with helpers.stop; startLearn hands back ids', () => {
  const m = read('main.js');
  assert.match(m, /h\('learn:start', \(topic\) => getLearnBtn\(\)\.start\(topic\)\)/);
  assert.match(m, /h\('learn:stop', \(\) => getLearnBtn\(\)\.stop\(\)\)/);
  assert.match(m, /LearnButton\)\(\{ dir: app\.getPath\('userData'\), startLearn, stopMote: \(id\) => helpers\.stop\(id\)/);
  assert.match(m, /return \{ ok: made\.length > 0, count: made\.length, topic, error, ids \};/);
  // hours 0 means no end time in startLearn
  assert.match(m, /const until = hrs \? Date\.now\(\) \+ hrs \* 3600000 : 0/);
  const p = read('preload.js');
  assert.match(p, /learn: \{ state: inv\('learn:state'\), start: inv\('learn:start'\), stop: inv\('learn:stop'\), quiz: inv\('learn:quiz'\) \}/);
});

test('the browser panel can still open: by itself when Glim browses, and from Show browser', () => {
  const p = read('renderer/panel.js');
  assert.match(p, /desk\.onBrowserShow\(async \(ev\) => \{ await ctx\.switchThread\(ev\.threadId\); show\(ev\.key\); \}\)/);
  assert.match(p, /show, close, toggle, isOpen/);
});

// ---- the renderer script itself, in a minimal fake DOM
function fakeDom() {
  const els = {};
  const mk = (id) => { const e = { id, hidden: false, disabled: false, readOnly: false, value: '', textContent: '', innerHTML: '', title: '', placeholder: '', attrs: {}, cls: new Set(), listeners: {}, focused: 0,
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, focus() { this.focused++; }, dispatchEvent() {},
    addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
    key(k) { const ev = { key: k, defaultPrevented: false, stopped: false, preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; } }; for (const f of this.listeners.keydown || []) f(ev); return ev; } };
    e.classList = { toggle: (c, on) => (on ? e.cls.add(c) : e.cls.delete(c)), add: (c) => e.cls.add(c), remove: (c) => e.cls.delete(c), contains: (c) => e.cls.has(c) }; return e; };
  for (const id of ['btnLearn', 'learnPop', 'learnErr', 'learnLabel', 'learnBusy', 'learnTopicNow', 'learnStop', 'learnShowBrowser', 'input', 'btnSend', 'hint', 'sleepBar', 'box']) els[id] = mk(id);
  els.learnPop.hidden = true; els.learnErr.hidden = true; els.sleepBar.hidden = true;
  els.input.placeholder = 'Ask Glim to do something…'; els.hint.textContent = 'Enter to send · Shift+Enter for a new line'; els.btnSend.innerHTML = '<svg>send</svg><span class="sr">Send</span>'; els.btnSend.title = 'Send (Enter)';
  const document = { querySelector: (s) => (s === '#composer .box' ? els.box : els[s.replace(/^#/, '')]), addEventListener() {} };
  return { els, document };
}
function load(deskOver) {
  const { els, document } = fakeDom();
  const calls = { start: [], stop: 0, toggle: 0, restore: 0 };
  const desk = { learn: { state: async () => ({ learning: false }), start: async (t) => { calls.start.push(t); return { ok: true, learning: true, topic: t }; }, stop: async () => { calls.stop++; return { ok: true, learning: false }; } }, onLearn: () => {}, ...(deskOver || {}) };
  const window = { desk, BrowserPanel: { toggle: () => calls.toggle++ } };
  vm.runInNewContext(read('renderer/learnbtn.js'), { window, document, setTimeout: (f) => f(), Event: class { constructor(t) { this.type = t; } } });
  window.LearnButton.restore = () => calls.restore++;
  return { els, calls, LB: window.LearnButton, desk };
}
const click = (e) => e.onclick({ stopPropagation() {} });
test('renderer: Learn turns the chat box into the Learn box (green, new placeholder and hint, focus), no popup', () => {
  const { els, LB } = load();
  click(els.btnLearn);
  assert.strictEqual(LB.composing(), true);
  assert.strictEqual(els.learnPop.hidden, true, 'no popover while idle');
  assert.ok(els.box.cls.has('learning')); assert.ok(els.btnSend.cls.has('learn'));
  assert.strictEqual(els.input.placeholder, 'What should Glim learn about?');
  assert.strictEqual(els.hint.textContent, 'Enter to start learning · Esc to cancel');
  assert.ok(els.input.focused > 0);
});
test('renderer: Enter in learn mode calls desk.learn.start with the text, never a chat message; success leaves learn mode and shows Learning', async () => {
  const { els, calls, LB } = load();
  click(els.btnLearn);
  els.input.value = '  the French revolution ';
  await LB.submitTopic();
  assert.deepStrictEqual(calls.start, ['the French revolution']);
  assert.strictEqual(LB.composing(), false);
  assert.strictEqual(els.input.value, '');
  assert.ok(!els.box.cls.has('learning'));
  assert.strictEqual(els.input.placeholder, 'Ask Glim to do something…');
  assert.strictEqual(els.learnLabel.textContent, 'Learning: the French revolution');
  // while learning, Learn opens the small busy popover: Stop, View quiz, Show browser
  click(els.btnLearn); assert.strictEqual(els.learnPop.hidden, false); assert.strictEqual(LB.composing(), false);
  els.learnShowBrowser.onclick(); assert.strictEqual(calls.toggle, 1);
  await els.learnStop.onclick();
  assert.strictEqual(calls.stop, 1); assert.strictEqual(els.learnLabel.textContent, 'Learn');
});
test('app.js routes Enter / Send to learn mode first (no chat send, no steer), and Esc cancels learn mode before it stops a run', () => {
  const app = read('renderer/app.js');
  const sub = app.slice(app.indexOf('async function submit(force) {'));
  assert.match(sub.split('\n')[1], /LearnButton\.composing\(\)\) return LearnButton\.submitTopic\(\)/, 'the first line of submit()');
  const esc = app.slice(app.indexOf("if (e.key === 'Escape') {\n      if (!$('#screenModal')"));
  assert.ok(esc.indexOf('LearnButton.cancel()') > 0 && esc.indexOf('LearnButton.cancel()') < esc.indexOf('else if (running)'));
  assert.match(app, /LearnButton\.restore = \(\) =>/);
  assert.match(app, /if \(window\.LearnButton && LearnButton\.composing\(\)\) LearnButton\.cancel\(\); input\.placeholder = 'Glim is asleep/, 'sleep ends learn mode');
});
test('renderer: an empty topic nudges and stays in learn mode; an error shows in the errline and stays', async () => {
  const { els, calls, LB } = load({ learn: { state: async () => ({ learning: false }), start: async () => ({ error: 'Glim is asleep.' }), stop: async () => ({}) } });
  click(els.btnLearn);
  await LB.submitTopic();
  assert.strictEqual(LB.composing(), true); assert.match(els.hint.textContent, /Type a topic first/);
  els.input.value = 'volcanoes';
  await LB.submitTopic();
  assert.strictEqual(LB.composing(), true); assert.strictEqual(els.learnErr.hidden, false); assert.strictEqual(els.learnErr.textContent, 'Glim is asleep.');
  assert.strictEqual(els.input.value, 'volcanoes', 'the text stays');
  assert.deepStrictEqual(calls.start, []);
});
test('renderer: Esc and a second Learn click restore the box exactly; typed text stays both ways', () => {
  const { els, calls, LB } = load();
  const before = { p: els.input.placeholder, h: els.hint.textContent, s: els.btnSend.innerHTML, t: els.btnSend.title };
  els.input.value = 'half a thought';
  click(els.btnLearn);
  const ev = els.input.key('Escape');
  assert.ok(ev.stopped, 'the chat does not see this Esc (it would stop a running task)');
  assert.strictEqual(LB.composing(), false);
  assert.deepStrictEqual({ p: els.input.placeholder, h: els.hint.textContent, s: els.btnSend.innerHTML, t: els.btnSend.title }, before);
  assert.ok(!els.box.cls.has('learning')); assert.ok(!els.btnSend.cls.has('learn'));
  assert.strictEqual(els.input.value, 'half a thought'); assert.strictEqual(calls.restore, 1);
  click(els.btnLearn); click(els.btnLearn);
  assert.strictEqual(LB.composing(), false); assert.strictEqual(els.input.placeholder, before.p); assert.strictEqual(els.input.value, 'half a thought');
  // Esc outside learn mode is left alone
  assert.strictEqual(els.input.key('Escape').stopped, false);
});
test('renderer: learn mode is not entered while Glim is asleep (a short note instead)', () => {
  const { els, LB } = load();
  els.sleepBar.hidden = false;
  click(els.btnLearn);
  assert.strictEqual(LB.composing(), false); assert.strictEqual(els.learnErr.hidden, false);
});
