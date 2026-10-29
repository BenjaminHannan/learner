'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createMemory } = require('../src/memory');

function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}
function setup(memory) {
  const nodes = {};
  function el(tag) {
    const node = { value: '', style: {}, children: [], listeners: {}, scrollHeight: 128,
      setAttribute() {}, append(...children) { this.children.push(...children); },
      addEventListener(name, fn) { this.listeners[name] = fn; }, setSelectionRange() {} };
    Object.defineProperty(node, 'id', { set(id) { nodes[id] = node; } });
    return node;
  }
  const source = fs.readFileSync(path.join(__dirname, '../renderer/app.js'), 'utf8');
  const start = source.indexOf('  let memRefresh = () => {};');
  const end = source.indexOf('  // Keeping track of:', start);
  const document = { activeElement: null };
  const context = { el, document, desk: { memory }, setInterval() {}, $: () => ({ hidden: true }) };
  vm.runInNewContext(source.slice(start, end) + '\nthis.build = memUi; this.refresh = () => memRefresh();', context);
  context.build();
  return { nodes, document, refresh: context.refresh };
}

test('memory saves changes made during a write and waits before opening', async () => {
  const first = deferred(), writes = []; let opened = 0;
  const ui = setup({ read: async () => ({ text: '' }), write: v => { writes.push(v); return writes.length === 1 ? first.promise : Promise.resolve({ ok: true }); }, open: async () => { opened++; return { ok: true }; } });
  const ta = ui.nodes.memText; ui.document.activeElement = ta;
  ta.value = 'first'; ta.listeners.input();
  const save = ui.nodes.memSave.onclick();
  ta.value = 'second'; ta.listeners.input();
  const open = ui.nodes.memShow.onclick();
  assert.equal(opened, 0);
  first.resolve({ ok: true });
  await Promise.all([save, open]);
  assert.deepEqual(writes, ['first', 'second']);
  assert.equal(opened, 1);
  assert.equal(ui.nodes.memNote.textContent, 'Saved');
});

test('memory does not open after a failed save', async () => {
  let opened = 0;
  const ui = setup({ write: async () => ({ ok: false, error: 'disk full' }), open: async () => { opened++; } });
  ui.nodes.memText.value = 'draft'; ui.nodes.memText.listeners.input();
  await ui.nodes.memShow.onclick();
  assert.equal(opened, 0);
  assert.match(ui.nodes.memNote.textContent, /disk full/);
});

test('memory ignores stale refreshes after a save or a newer refresh', async () => {
  const reads = [];
  const ui = setup({ read: () => { const d = deferred(); reads.push(d); return d.promise; }, write: async () => ({ ok: true }) });
  const old = ui.refresh();
  ui.nodes.memText.value = 'new'; ui.nodes.memText.listeners.input();
  await ui.nodes.memSave.onclick();
  reads[0].resolve({ text: 'old' }); await old;
  assert.equal(ui.nodes.memText.value, 'new');
  const earlier = ui.refresh(), later = ui.refresh();
  reads[2].resolve({ text: 'latest' }); await later;
  reads[1].resolve({ text: 'stale' }); await earlier;
  assert.equal(ui.nodes.memText.value, 'latest');
});

test('discarding an unsaved draft refreshes agent additions and preserves handwritten text', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-memory-ui-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const memory = createMemory(root);
  const baseline = '- Prefers short answers\n';
  memory.write(baseline);
  const ui = setup({ read: async () => memory.read(), write: async (v, base) => memory.write(v, base) });
  const ta = ui.nodes.memText;
  await ui.refresh();
  assert.equal(ta.value, baseline);
  ta.value = '- unsaved typing'; ta.listeners.input();
  memory.save('Ben takes Spanish 2 in 5th period', 'classes');
  await ui.refresh();
  assert.equal(ta.value, '- unsaved typing');
  assert.match(memory.read().text, /Prefers short answers/);
  assert.match(memory.read().text, /Spanish 2/);
  ta.value = baseline; ta.listeners.input();
  await ta.listeners.blur();
  await ui.refresh();
  assert.match(ta.value, /Spanish 2/);
  assert.match(ta.value, /Prefers short answers/);
  assert.match(memory.read().text, /Prefers short answers/);
  ta.value = ''; ta.listeners.input();
  await ta.listeners.blur();
  assert.equal(memory.read().text, '');
  memory.save('Ben takes Spanish 2 in 5th period', 'classes');
  await ui.refresh();
  assert.match(ta.value, /Spanish 2/);
  assert.match(ta.value, /topic: classes/);
});

test('blur saves preserve a concurrent model append, including typing during the write', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-memory-ui-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const memory = createMemory(root), first = deferred(), writes = [];
  memory.write('- Prefers short answers\n');
  const ui = setup({ read: async () => memory.read(), write: (v, base) => {
    writes.push({ v, base });
    const result = memory.write(v, base);
    return writes.length === 1 ? first.promise.then(() => result) : Promise.resolve(result);
  } });
  await ui.refresh();
  const ta = ui.nodes.memText;
  ta.value = '- Prefers clear answers\n'; ta.listeners.input();
  memory.save('Ben takes Spanish 2 in 5th period', 'classes');
  const saving = ta.listeners.blur();
  ta.value = '- Prefers detailed answers\n'; ta.listeners.input();
  first.resolve(); await saving;
  assert.equal(writes.length, 2);
  assert.match(memory.read().text, /Prefers detailed answers/);
  assert.match(memory.read().text, /Spanish 2/);
  assert.equal(ta.value, memory.read().text);
  assert.equal(ui.nodes.memNote.textContent, 'Saved');
  assert.equal(ui.nodes.memConflict.hidden, true);
});

test('conflicting model edits keep both snapshots and require explicit combined-draft save', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-memory-ui-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const memory = createMemory(root);
  const base = '- AP Chem is 3rd period | topic: classes | id: m1 | updated: 2026-10-01\n';
  memory.write(base);
  const ui = setup({ read: async () => memory.read(), write: async (v, expected) => memory.write(v, expected) });
  await ui.refresh();
  const ta = ui.nodes.memText;
  ta.value = base.replace('3rd', '5th'); ta.listeners.input();
  const draft = ta.value;
  memory.save('AP Chem is 4th period', 'classes');
  const current = memory.read().text;
  assert.equal(await ta.listeners.blur(), false);
  assert.equal(memory.read().text, current);
  assert.equal(ta.value, draft);
  assert.equal(ui.nodes.memSavedText.value, current);
  assert.equal(ui.nodes.memConflict.hidden, false);
  assert.match(ui.nodes.memNote.textContent, /Not saved.*changed/);
  // Repeated autosave cannot silently turn the old draft into an overwrite.
  assert.equal(await ta.listeners.blur(), false);
  ta.value = base; ta.listeners.input();
  await ui.refresh();
  assert.equal(ta.value, base); // a conflict keeps the draft even if it matches the old baseline again
  ta.value = current + '- Confirm the class period tomorrow\n'; ta.listeners.input();
  assert.equal(await ui.nodes.memCombine.onclick(), true);
  assert.equal(memory.read().text, ta.value);
  assert.match(memory.read().text, /4th period/);
  assert.equal(ui.nodes.memConflict.hidden, true);
});

test('a second conflicting edit during recovery is checked again and keeps the combined draft', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-memory-ui-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const memory = createMemory(root);
  memory.write('initial');
  const ui = setup({ read: async () => memory.read(), write: async (v, expected) => memory.write(v, expected) });
  await ui.refresh();
  ui.nodes.memText.value = 'local draft'; ui.nodes.memText.listeners.input();
  memory.write('first remote edit');
  await ui.nodes.memSave.onclick();
  ui.nodes.memText.value = 'combined draft'; ui.nodes.memText.listeners.input();
  memory.write('second remote edit');
  assert.equal(await ui.nodes.memCombine.onclick(), false);
  assert.equal(memory.read().text, 'second remote edit');
  assert.equal(ui.nodes.memText.value, 'combined draft');
  assert.equal(ui.nodes.memSavedText.value, 'second remote edit');
  assert.equal(ui.nodes.memConflict.hidden, false);
});

test('keeping the saved version resolves a conflict without rewriting the file', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-memory-ui-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const memory = createMemory(root);
  memory.write('initial');
  const ui = setup({ read: async () => memory.read(), write: async (v, expected) => memory.write(v, expected) });
  await ui.refresh();
  ui.nodes.memText.value = 'draft'; ui.nodes.memText.listeners.input();
  memory.write('changed elsewhere');
  await ui.nodes.memSave.onclick();
  await ui.nodes.memKeepSaved.onclick();
  assert.equal(ui.nodes.memText.value, 'changed elsewhere');
  assert.equal(memory.read().text, 'changed elsewhere');
  assert.equal(ui.nodes.memConflict.hidden, true);
});
