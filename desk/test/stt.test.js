'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { EventEmitter } = require('node:events');
const { Stt, scriptPath, candidates, MISSING } = require('../src/stt');

function fakeChild() {
  const c = new EventEmitter();
  c.stdout = new EventEmitter(); c.stderr = new EventEmitter();
  c.stdin = { destroyed: false, ended: false, end() { this.ended = true; }, on() {} };
  c.killed = false; c.kill = () => { c.killed = true; };
  return c;
}
function mk(o = {}) {
  const spawned = [], kids = [];
  const stt = new Stt({
    home: '/h', devRoot: '/repo', resourcesPath: '', env: {}, exists: () => true, hasMlx: async () => true,
    spawn: (cmd, args, opts) => { const c = fakeChild(); spawned.push({ cmd, args, opts }); kids.push(c); return c; },
    ...o
  });
  return { stt, spawned, kids };
}
const tick = () => new Promise((r) => setImmediate(r));

test('stt: nothing starts until ensure() (lazy)', () => { const { spawned } = mk(); assert.strictEqual(spawned.length, 0); });

test('stt: spawn arguments, env, port parsing', async () => {
  const { stt, spawned, kids } = mk();
  const p = stt.ensure(); await tick(); await tick();
  assert.strictEqual(spawned.length, 1);
  assert.strictEqual(spawned[0].cmd, '/h/learner-ops/stt/.venv/bin/python');
  assert.deepStrictEqual(spawned[0].args, ['-I', '/repo/stt/lfm_stt.py']);
  assert.strictEqual(spawned[0].opts.env.HF_HOME, '/h/learner-ops/stt/hf');
  assert.strictEqual(spawned[0].opts.env.HF_HUB_OFFLINE, '1');
  kids[0].stdout.emit('data', 'warming\n{"po'); kids[0].stdout.emit('data', 'rt": 4242}\n');
  assert.strictEqual(await p, 'http://127.0.0.1:4242');
  assert.strictEqual(await stt.ensure(), 'http://127.0.0.1:4242');
  assert.strictEqual(spawned.length, 1, 'one server for the app lifetime');
});

test('stt: concurrent ensure() calls share one start', async () => {
  const { stt, spawned, kids } = mk();
  const a = stt.ensure(), b = stt.ensure(); await tick(); await tick();
  kids[0].stdout.emit('data', '{"port":1}\n');
  assert.strictEqual(await a, await b); assert.strictEqual(spawned.length, 1);
});

test('stt: env python wins, then scratch venv, then managed; first with mlx_vlm', async () => {
  assert.deepStrictEqual(candidates({ home: '/h', env: { PREMONITION_STT_PYTHON: '/p/py', PREMONITION_STT_HF_HOME: '/p/hf' }, managedPython: () => '/m/py' }).map((c) => c.python),
    ['/p/py', '/h/learner-ops/stt/.venv/bin/python', '/m/py']);
  const { stt, spawned, kids } = mk({ managedPython: () => '/m/py', hasMlx: async (py) => py === '/m/py' });
  const p = stt.ensure(); await tick(); await tick();
  assert.strictEqual(spawned[0].cmd, '/m/py');
  assert.strictEqual(spawned[0].opts.env.HF_HOME, undefined);
  kids[0].stdout.emit('data', '{"port":7}\n'); await p;
});

test('stt: no mlx_vlm anywhere -> plain error, no spawn', async () => {
  const { stt, spawned } = mk({ hasMlx: async () => false });
  await assert.rejects(stt.ensure(), (e) => e.message === MISSING);
  assert.strictEqual(spawned.length, 0);
});

test('stt: python files that do not exist are skipped', async () => {
  const { stt } = mk({ exists: () => false });
  await assert.rejects(stt.ensure(), /script, which is missing/);
  const m = mk({ exists: (f) => f.endsWith('lfm_stt.py') });
  await assert.rejects(m.stt.ensure(), (e) => e.message === MISSING);
});

test('stt: exit before the port is an error with the last stderr line; the next ensure() retries', async () => {
  const { stt, spawned, kids } = mk();
  const p = stt.ensure(); await tick(); await tick();
  kids[0].stderr.emit('data', 'x\nModuleNotFoundError: numpy\n'); kids[0].emit('exit', 1);
  await assert.rejects(p, /stopped before it was ready\. ModuleNotFoundError: numpy/);
  const p2 = stt.ensure(); await tick(); await tick();
  assert.strictEqual(spawned.length, 2);
  kids[1].stdout.emit('data', '{"port":9}\n'); assert.strictEqual(await p2, 'http://127.0.0.1:9');
});

test('stt: start timeout kills the child', async () => {
  const { stt, kids } = mk({ startMs: 20 });
  await assert.rejects(stt.ensure(), /did not start in time/);
  assert.ok(kids[0].killed);
});

test('stt: server dying later makes the next ensure() start a new one; stop() ends it', async () => {
  const { stt, spawned, kids } = mk();
  const p = stt.ensure(); await tick(); await tick(); kids[0].stdout.emit('data', '{"port":5}\n'); await p;
  kids[0].emit('exit', 1);
  const p2 = stt.ensure(); await tick(); await tick(); assert.strictEqual(spawned.length, 2);
  kids[1].stdout.emit('data', '{"port":6}\n'); await p2;
  stt.stop(); assert.ok(kids[1].stdin.ended && kids[1].killed);
});

test('stt: script path is the packaged resource when present, else the repo', () => {
  assert.strictEqual(scriptPath('/res', '/repo', (f) => f === '/res/stt/lfm_stt.py'), '/res/stt/lfm_stt.py');
  assert.strictEqual(scriptPath('/res', '/repo', () => false), '/repo/stt/lfm_stt.py');
  assert.strictEqual(scriptPath(undefined, '/repo', () => true), '/repo/stt/lfm_stt.py');
});
