const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../renderer/app.js'), 'utf8');
const extract = (start, end) => source.slice(source.indexOf(start), source.indexOf(end));

function setup(initial, wide = true, options = {}) {
  const records = initial.map((entry) => ({ items: [], ...entry }));
  const calls = [];
  const elements = new Map();
  function element(tag, className, text) {
    return { tag, className, children: [], attributes: {}, dataset: {}, set textContent(value) { this.text = value; this.children = []; }, get textContent() { return this.text; }, append(...children) { this.children.push(...children); }, setAttribute(name, value) { this.attributes[name] = value; }, focus() { context.document.activeElement = this; }, querySelectorAll() { return this.children.flatMap((child) => [child, ...child.querySelectorAll()]).filter((child) => child.dataset.navFocus); }, text };
  }
  const get = (selector) => {
    if (!elements.has(selector)) elements.set(selector, element(selector));
    return elements.get(selector);
  };
  const classes = new Set(wide ? ['drawer-open'] : []);
  const context = {
    desk: { threads: { list: async () => records, load: async (id) => { if (options.load) await options.load(id); const found = records.find((entry) => entry.id === id); if (found) context.backend = id; return found; }, create: async () => { calls.push('create'); const entry = { id: 'created', title: 'Glim', items: [] }; records.unshift(entry); context.backend = entry.id; return entry; } }, settings: { get: async () => ({}) }, agent: { stop: () => calls.push('stop'), send: () => calls.push('send') }, helpers: { list: async () => [], run: async () => calls.push('run'), pause: async () => calls.push('pause'), remove: async () => calls.push('delete') } },
    document: { body: { classList: { add: (name) => classes.add(name), remove: (name) => classes.delete(name), contains: (name) => classes.has(name) } } },
    window: { matchMedia: () => ({ matches: wide }) }, localStorage: { getItem() { return context.saved || options.saved; }, setItem(key, value) { context.saved = value; } }, confirm: () => true,
    $: get, el: element, input: element('input'), BrowserPanel: { threadChanged() {} },
    withHistory: options.history || (async (entry) => entry), paintTitle() {}, renderThread() {}, setRunning() {}, lastBCard() {}, upsertBCard() {}, onApproval() {}, onAsk() {}, refreshMood() {}, paintSegs() {}, paintAgents() {}, statusText: (entry) => entry.status, sparkName: (entry) => entry.title || 'Mote'
  };
  vm.createContext(context);
  vm.runInContext(`let thread = null, running = false, settings = {}, errorUntil = 0, doneUntil = 0;\n${options.actualHistory ? extract('  const HIST_ITEMS =', '  let navigationQueue =') : ''}\n${extract('  let navigationQueue =', '  function ago(ts)')}\n${extract('  const isCall =', '  // ---------- agents')}\n${extract('  let returningToGlim =', '  // links in answers')}\nthis.navigation = { openThread, backToGlim, loadThreads, restoreNavigation, helpers: (list) => { navigationHelpers = list; }, current: () => thread };`, context);
  return { navigation: context.navigation, calls, get, classes, context, records };
}

test('Mote to latest Glim uses the existing chat without stopping work', async () => {
  const app = setup([{ id: 'latest', title: 'Latest' }, { id: 'older', title: 'Older' }, { id: 'mote', title: 'Schoolwork', helper: 'helper' }]);
  await app.navigation.openThread('mote');
  await app.navigation.backToGlim();
  assert.equal(app.navigation.current().id, 'latest');
  assert.deepEqual(app.calls, []);
});

test('only a Mote creates one Glim even for concurrent Back clicks', async () => {
  const app = setup([{ id: 'mote', title: 'Schoolwork', helper: 'helper' }]);
  await app.navigation.openThread('mote');
  await Promise.all([app.navigation.backToGlim(), app.navigation.backToGlim()]);
  assert.equal(app.navigation.current().id, 'created');
  assert.deepEqual(app.calls, ['create']);
});

test('the list shows Glim and every Mote, and each button opens its view', async () => {
  const app = setup([{ id: 'one', title: 'Latest chat' }, { id: 'two', title: 'Earlier chat' }, { id: 'mote1', title: 'Schoolwork', helper: 'h1' }, { id: 'mote2', title: 'Reading', helper: 'h2' }]);
  app.navigation.helpers([{ id: 'h1', threadId: 'mote1', name: 'Schoolwork', status: 'idle' }, { id: 'h2', threadId: 'mote2', name: 'Reading', status: 'idle' }]);
  await app.navigation.loadThreads();
  const buttons = [...app.get('#mainList').children, ...app.get('#agentList').children].map((row) => row.children[0]);
  assert.deepEqual(buttons.map((button) => button.children[0].text), ['Glim', 'Earlier chat', 'Schoolwork', 'Reading']);
  for (const [button, id] of buttons.map((button, i) => [button, ['one', 'two', 'mote1', 'mote2'][i]])) {
    await button.onclick(); assert.equal(app.navigation.current().id, id);
  }
  await app.get('#btnBackGlim').onclick(); assert.equal(app.navigation.current().id, 'one');
  assert.deepEqual(app.calls, []);
});

test('deferred history and subsequent intent leave backend and view aligned', async () => {
  let release, started;
  const blocked = new Promise((resolve) => { release = resolve; });
  const entered = new Promise((resolve) => { started = resolve; });
  const app = setup([{ id: 'one' }, { id: 'two' }], true, { history: async (entry) => { if (entry.id === 'one') { started(); await blocked; } return entry; } });
  const first = app.navigation.openThread('one'); await entered;
  const second = app.navigation.openThread('two'); release(); await Promise.all([first, second]);
  assert.equal(app.navigation.current().id, 'two'); assert.equal(app.context.backend, 'two'); assert.equal(app.context.saved, 'two');
});

test('Mote status and controls use helper data and preserve focus', async () => {
  const app = setup([{ id: 'glim' }, { id: 'mote', helper: 'h' }]);
  app.navigation.helpers([{ id: 'h', threadId: 'mote', name: 'Long Mote name', status: 'running', paused: true }]);
  await app.navigation.loadThreads();
  const row = app.get('#agentList').children[0];
  assert.equal(row.children[0].children[1].text, 'running · read-only');
  assert.deepEqual(row.children[1].children.map((entry) => entry.text), ['Run now', 'Resume', 'Delete']);
  row.children[1].children[0].focus(); await app.navigation.loadThreads();
  assert.equal(app.context.document.activeElement.dataset.navFocus, 'helper:h:Run now');
  await app.get('#agentList').children[0].children[0].onclick(); assert.deepEqual(app.calls, []);
});

test('created fallback persists in a narrow window', async () => {
  const app = setup([{ id: 'mote', helper: 'h' }], false);
  await app.navigation.openThread('mote');
  await app.navigation.backToGlim(); assert.equal(app.context.saved, 'created'); assert.equal(app.context.backend, 'created');
});

test('restart restores a Mote and falls back when the selection was deleted', async () => {
  const entries = [{ id: 'glim' }, { id: 'mote', helper: 'h' }];
  const restored = setup(entries, true, { saved: 'mote' });
  await restored.navigation.restoreNavigation(false); assert.equal(restored.navigation.current().id, 'mote');
  const deleted = setup([entries[0]], true, { saved: 'mote' });
  await deleted.navigation.restoreNavigation(false); assert.equal(deleted.navigation.current().id, 'glim'); assert.equal(deleted.context.saved, 'glim');
});

test('history loads cannot leave the backend on an older thread', async () => {
  let release, started;
  const blocked = new Promise((resolve) => { release = resolve; });
  const entered = new Promise((resolve) => { started = resolve; });
  let delayed = false;
  const app = setup([{ id: 'new', updated: 2 }, { id: 'old', updated: 1, items: [{ t: 'user', text: 'old' }] }, { id: 'mote', helper: 'h' }], true, { actualHistory: true, load: async (id) => { if (id === 'old' && !delayed) { delayed = true; started(); await blocked; } } });
  const first = app.navigation.openThread('new'); await entered;
  const second = app.navigation.openThread('mote'); release(); await Promise.all([first, second]);
  assert.equal(app.context.backend, 'mote'); assert.equal(app.navigation.current().id, 'mote');
});
