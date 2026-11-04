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
  assert.match(bar, /id="learnPop"/); assert.match(bar, /What should I learn about\?/);
  assert.match(bar, /id="learnStart"/); assert.match(bar, /id="learnStop"/); assert.match(bar, /id="learnShowBrowser"/);
  assert.ok(html.indexOf('<script src="panel.js">') < html.indexOf('<script src="learnbtn.js">'));
  for (const f of ['renderer/panel.js', 'renderer/app.js', 'renderer/learnbtn.js']) assert.ok(!/btnBrowser/.test(read(f)), f);
});

test('Start = Learn mode with lifetime forever (hours 0, like "until I stop them"); Stop stops every Mote it started', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lb-'));
  const calls = { start: [], stop: [] }, views = [];
  const mk = () => new LearnButton({ dir, startLearn: (t, n, h) => { calls.start.push([t, n, h]); return { ok: true, ids: ['h1', 'h2', 'h3'], topic: t }; }, stopMote: (id) => calls.stop.push(id), onChange: (v) => views.push(v) });
  const b = mk();
  assert.strictEqual(FOREVER, 0);
  assert.deepStrictEqual(b.start('  enzyme   kinetics '), { ok: true, learning: true, topic: 'enzyme kinetics', since: b.cur.since, count: 3, partial: null });
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
  const mk = (id) => ({ id, hidden: false, disabled: false, value: '', textContent: '', title: '', attrs: {}, cls: new Set(), listeners: {},
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, focus() {},
    classList: null, addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); } });
  for (const id of ['btnLearn', 'learnPop', 'learnTopic', 'learnErr', 'learnLabel', 'learnIdle', 'learnBusy', 'learnTopicNow', 'learnStart', 'learnStop', 'learnShowBrowser']) {
    const e = mk(id); e.classList = { toggle: (c, on) => (on ? e.cls.add(c) : e.cls.delete(c)) }; els[id] = e;
  }
  els.learnPop.hidden = true;
  const document = { querySelector: (s) => els[s.replace(/^#/, '')], addEventListener() {} };
  return { els, document };
}
test('renderer: Start sends the topic to desk.learn.start, the label shows Learning, Stop calls desk.learn.stop, Show browser toggles the panel', async () => {
  const { els, document } = fakeDom();
  const calls = { start: [], stop: 0, toggle: 0 };
  const desk = { learn: { state: async () => ({ learning: false }), start: async (t) => { calls.start.push(t); return { ok: true, learning: true, topic: t }; }, stop: async () => { calls.stop++; return { ok: true, learning: false }; } }, onLearn: () => {} };
  const window = { desk, BrowserPanel: { toggle: () => calls.toggle++ } };
  vm.runInNewContext(read('renderer/learnbtn.js'), { window, document, setTimeout });
  els.btnLearn.onclick({ stopPropagation() {} });
  assert.strictEqual(els.learnPop.hidden, false);
  els.learnTopic.value = 'the French revolution';
  await els.learnStart.onclick();
  assert.deepStrictEqual(calls.start, ['the French revolution']);
  assert.strictEqual(els.learnLabel.textContent, 'Learning: the French revolution');
  assert.strictEqual(els.learnBusy.hidden, false);
  await els.learnStop.onclick();
  assert.strictEqual(calls.stop, 1);
  assert.strictEqual(els.learnLabel.textContent, 'Learn');
  els.learnShowBrowser.onclick();
  assert.strictEqual(calls.toggle, 1);
});
