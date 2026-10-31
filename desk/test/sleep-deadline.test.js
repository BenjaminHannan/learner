'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { WinSleep, CHUNK_BUDGET_S } = require('../src/sleepwin');
const { sleepDeadline, shouldAutoSleep } = require('../src/sleep');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'deadline-'));
  const w = new WinSleep({ root, installer: { installed: () => true, state: () => ({}) },
    privateChecker: { ensureIdle: async () => ({ ok: true, processStopped: true }) },
    hooks: { resumeModel: async () => ({ ok: true }) } });
  return { w, root };
}
test('a chunk that would cross the deadline is not started', async () => {
  const { w, root } = fixture();
  try {
    let chunks = 0; w.wakeAtMs = Date.now() + (CHUNK_BUDGET_S - 1) * 1000;
    w._chunk = async () => { chunks++; return {}; };
    await w._run(); assert.equal(chunks, 0); assert.equal(w.active, false);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
test('deadline requests the safe stop, waits for the chunk, and skips unchecked candidate promotion', async () => {
  const { w, root } = fixture();
  try {
    let release, skip, deadline, delay;
    w.o.setDeadlineTimer = (fn, ms) => { deadline = fn; delay = ms; return {}; };
    w._chunk = () => new Promise(r => { release = r; });
    w._finishCandidate = async s => { skip = s; w.active = false; };
    assert.equal(w.start({ wakeAt: Date.now() + 1300000 }).ok, true);
    await new Promise(r => setImmediate(r));
    assert.ok(delay > CHUNK_BUDGET_S * 1000);
    deadline();
    assert.ok(fs.existsSync(path.join(root, 'sleep', 'ASSISTANT_RUNNING')));
    assert.equal(w.active, true);
    release({ status: 'stopped', interrupted: true, stop_reason: 'assistant_running' });
    await new Promise(r => setImmediate(r));
    assert.equal(skip, true); assert.equal(w.active, false);
    assert.ok(!fs.existsSync(path.join(root, 'sleep', 'ASSISTANT_RUNNING')));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
test('night cutoff prevents auto sleep at 06:00, including an unclamped settings window', () => {
  const now = new Date(2026, 9, 30, 6, 0);
  const d = shouldAutoSleep({ now, settings: { autoSleep: true, sleepFrom: '23:00', sleepTo: '08:00' } });
  assert.equal(d.sleep, false);
  assert.equal(new Date(sleepDeadline(new Date(2026, 9, 30, 5, 40))).getMinutes(), 45);
});
