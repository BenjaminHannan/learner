'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('fs'), path = require('path'), os = require('os');
const { execFileSync } = require('child_process');
const G = require('../src/grading');
const root = path.resolve(__dirname, '../..');
test('Python and Node use byte-identical shared grading contract', () => {
  const result = JSON.parse(execFileSync(process.env.PYTHON_FOR_TEST || 'python3', ['-c', 'from sleepmlx.grading import binding; import json; print(json.dumps(binding()))'], { cwd: root, env: { ...process.env, PYTHONPATH: root } }));
  assert.deepEqual(result, G.binding);
});
test('development and packaged resources/app or app.asar resolve the same contract', () => {
  for (const app of ['app', 'app.asar']) {
    const staging = fs.mkdtempSync(path.join(os.tmpdir(), 'grading-package-'));
    try {
      const src = path.join(staging, 'resources', app, 'src'), py = path.join(staging, 'resources', 'sleepmlx');
      fs.mkdirSync(src, { recursive: true }); fs.mkdirSync(py);
      fs.copyFileSync(path.join(root, 'desk/src/grading.js'), path.join(src, 'grading.js'));
      for (const name of ['__init__.py', 'grading.py', 'grading-contract.json']) fs.copyFileSync(path.join(root, 'sleepmlx', name), path.join(py, name));
      assert.deepEqual(require(path.join(src, 'grading.js')).binding, G.binding);
      const value = JSON.parse(execFileSync(process.env.PYTHON_FOR_TEST || 'python3', ['-c', 'from sleepmlx.grading import binding; import json; print(json.dumps(binding()))'], { cwd: staging, env: { ...process.env, PYTHONPATH: path.dirname(py) } }));
      assert.deepEqual(value, G.binding);
    } finally { fs.rmSync(staging, { recursive: true, force: true }); }
  }
});

test('missing or malformed contract disables new admission without breaking app module startup', () => {
  for (const layout of ['desk', 'resources/app', 'resources/app.asar']) for (const raw of [null, '{', '{"version":true}']) {
    const staging = fs.mkdtempSync(path.join(os.tmpdir(), 'grading-unavailable-'));
    try {
      const src = path.join(staging, layout, 'src'), resourceRoot = path.resolve(src, '../..');
      fs.cpSync(path.join(root, 'desk/src'), src, { recursive: true });
      if (raw !== null) { fs.mkdirSync(path.join(resourceRoot, 'sleepmlx'), { recursive: true }); fs.writeFileSync(path.join(resourceRoot, 'sleepmlx/grading-contract.json'), raw); }
      const grader = require(path.join(src, 'grading.js'));
      assert.equal(grader.available, false); assert.equal(grader.current({}), false); assert.match(grader.error, /unavailable/);
      const { WinSleep } = require(path.join(src, 'sleepwin.js'));
      assert.equal(typeof WinSleep, 'function');
      const candidates = require(path.join(src, 'sleep-candidates.js'));
      assert.equal(candidates.validVerdict({ ok: true, processStopped: true, checkId: '123e4567-e89b-42d3-a456-426614174000', general_n: 8, general_on: 8, general_off: 8, held_n: 1, held_on: 1, held_off: 1 }, 1), false);
      const macRoot = path.join(staging, 'synthetic-mac'); fs.mkdirSync(path.join(macRoot, 'sleep'), { recursive: true });
      fs.writeFileSync(path.join(macRoot, 'sleep', 'adapter.gguf'), 'legacy');
      fs.writeFileSync(path.join(macRoot, 'sleep', 'adapter.gguf.json'), JSON.stringify({ base_hf_id: 'LiquidAI/LFM3-1.7B', served: { ok: true } }));
      const mac = new WinSleep({ root: macRoot, platform: 'darwin', installer: { state: () => ({}) } });
      assert.equal(mac.currentLora(), ''); assert.ok(fs.existsSync(path.join(macRoot, 'sleep', 'adapter.gguf')));
      assert.equal(typeof require(path.join(src, 'runtime/builtin.js')).Builtin, 'function');
    } finally { fs.rmSync(staging, { recursive: true, force: true }); }
  }
});

test('Python and Node agree on complete current decisions, malformed counts and held bounds', () => {
  const good = { ...G.binding, ok: true, general_n: 8, general_on: 8, general_off: 8, held_n: 1, held_on: 1, held_off: 1 };
  const cases = [[good, 1], [{ ...good, ok: false, general_on: 0 }, 1], [{ ...good, general_on: true }, 1],
    [{ ...good, general_on: null }, 1], [{ ...good, ok: 1 }, 1], [{ ...good, ok: false }, 1],
    [{ ...good, general_on: 0 }, 1], [{ ...good, held_n: 13, held_on: 13, held_off: 13 }, 13],
    [{ ...good, held_n: 0, held_on: 0, held_off: 0 }, 0], [{ ...good, failure_kind: 'adapter_load' }, 1],
    [{ ...good, held_n: 9 }, 1], [{ ...good, pending: true }, 1], [{ ...good, grader: 'strict-3' }, 1]];
  const expected = cases.map(([verdict, count]) => G.validDecision(verdict, count));
  const actual = JSON.parse(execFileSync(process.env.PYTHON_FOR_TEST || 'python3', ['-c', 'import json,sys; from sleepmlx.grading import valid_decision; print(json.dumps([valid_decision(v,n) for v,n in json.load(sys.stdin)]))'], { input: JSON.stringify(cases), cwd: root, env: { ...process.env, PYTHONPATH: root } }));
  assert.deepEqual(actual, expected); assert.deepEqual(expected, [true, true, false, false, false, false, false, false, false, false, false, false, false]);
  for (const pending of [[], {}, 0, '', null, true]) {
    const verdict = { ...good, pending };
    assert.equal(G.validDecision(verdict, 1), false);
    const value = JSON.parse(execFileSync(process.env.PYTHON_FOR_TEST || 'python3', ['-c', 'import json,sys; from sleepmlx.grading import valid_decision; print(json.dumps(valid_decision(json.load(sys.stdin),1)))'], { input: JSON.stringify(verdict), cwd: root, env: { ...process.env, PYTHONPATH: root } }));
    assert.equal(value, false);
  }
});
