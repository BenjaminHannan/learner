'use strict';
// Wiring checks that need no Electron: IPC channels, preload wrappers, agent options and the memory API behind them.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createMemory } = require('../src/memory');
const { defaultSummary } = require('../src/agent');

const root = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');

test('main.js creates the memory after the Store, passes it to the Agent and handles the memory channels', () => {
  const m = read('main.js');
  assert.ok(m.indexOf('store = new Store(') < m.indexOf('memory = createMemory(app.getPath(\'userData\'))'));
  assert.match(m, /new Agent\(\{\s*memory,/);
  assert.strictEqual((m.match(/new Agent\(/g) || []).length, 1); // helpers use the same createAgent, so they get memory too
  for (const ch of ['memory:list', 'memory:add', 'memory:edit', 'memory:delete']) assert.ok(m.includes("h('" + ch + "'"), ch);
});

test('preload exposes desk.memory.{list,add,edit,remove} on the matching channels', () => {
  const p = read('preload.js');
  assert.match(p, /memory: \{ list: inv\('memory:list'\), add: inv\('memory:add'\), edit: inv\('memory:edit'\), remove: inv\('memory:delete'\), reveal: inv\('memory:reveal'\) \}/);
});

test('the memory API behind the channels: add, list, edit, delete, refusals', () => {
  const m = createMemory(fs.mkdtempSync(path.join(os.tmpdir(), 'wire-')));
  const a = m.add({ text: 'AP Chem is 3rd period', topic: 'classes' });
  assert.ok(a.ok); assert.strictEqual(m.list().length, 1);
  const e = m.edit(a.fact.id, { text: 'AP Chem is 4th period' });
  assert.ok(e.ok); assert.strictEqual(m.list()[0].text, 'AP Chem is 4th period'); assert.strictEqual(m.list()[0].topic, 'classes');
  const bad = m.add({ text: 'my password is hunter2' });
  assert.ok(!bad.ok && /Not saved/.test(bad.error));
  assert.ok(!m.edit(a.fact.id, { text: 'password: hunter2' }).ok);
  assert.strictEqual(m.list()[0].text, 'AP Chem is 4th period');
  assert.ok(m.delete(a.fact.id).ok); assert.strictEqual(m.list().length, 0);
});

test('summaries for memory and verify steps; icons exist in the renderer', () => {
  assert.strictEqual(defaultSummary('memory_save', { fact: 'AP Chem is 3rd period' }), 'Remembered: AP Chem is 3rd period');
  assert.strictEqual(defaultSummary('memory_forget', { match: 'chem' }), 'Forgot: chem');
  assert.strictEqual(defaultSummary('verify', {}), 'Checking its work');
  const a = read('renderer/app.js');
  assert.match(a, /verify: 'check'/); assert.match(a, /memory_save: 'bookmark'/); assert.match(a, /memory_forget: 'bookmark'/); assert.match(a, /\n\s+bookmark: '</);
});
