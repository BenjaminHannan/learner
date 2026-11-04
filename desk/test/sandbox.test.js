'use strict';
// Little scientist: the Python sandbox must be airtight. Every pass mark from the brief is one test here.
// These run the REAL /usr/bin/sandbox-exec + the system python3 (macOS only; skipped elsewhere).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/sandbox');

const skip = process.platform !== 'darwin' || !S.available() ? 'needs macOS sandbox-exec + /usr/bin/python3' : false;

test('sandbox: a plain program runs and its output comes back', { skip }, async () => {
  const r = await S.runPython('print(sum(range(10)))\nprint("hi")');
  assert.strictEqual(r.ok, true, r.why + ' ' + r.stderr);
  assert.strictEqual(S.normOut(r.stdout), '45\nhi');
});

test('sandbox: a network attempt is blocked', { skip }, async () => {
  const r = await S.runPython('import socket\ns = socket.create_connection(("1.1.1.1", 80), timeout=2)\nprint("CONNECTED")');
  assert.strictEqual(r.ok, false); assert.ok(!/CONNECTED/.test(r.stdout));
  assert.match(r.stderr, /PermissionError|Operation not permitted/);
  const r2 = await S.runPython('import urllib.request\nprint(urllib.request.urlopen("http://example.com", timeout=2).status)');
  assert.strictEqual(r2.ok, false); assert.ok(!/200/.test(r2.stdout));
});

test('sandbox: a write outside the temp dir is blocked (and nothing appears there)', { skip }, async () => {
  const target = path.join(os.tmpdir(), 'glim-sbx-escape-' + process.pid + '.txt');
  const home = path.join(os.homedir(), '.glim-sbx-escape-' + process.pid);
  const r = await S.runPython('for p in [' + JSON.stringify(target) + ', ' + JSON.stringify(home) + ', "/tmp/glim-sbx-escape.txt"]:\n    try:\n        open(p, "w").write("x")\n        print("WROTE", p)\n    except Exception as e:\n        print("blocked", type(e).__name__)');
  assert.ok(!/WROTE/.test(r.stdout), r.stdout);
  assert.strictEqual((r.stdout.match(/blocked PermissionError/g) || []).length, 3, r.stdout);
  assert.ok(!fs.existsSync(target) && !fs.existsSync(home) && !fs.existsSync('/tmp/glim-sbx-escape.txt'));
  // inside its own temp dir it may write
  const ok = await S.runPython('open("scratch.txt", "w").write("hello")\nprint(open("scratch.txt").read())');
  assert.strictEqual(S.normOut(ok.stdout), 'hello');
});

test('sandbox: reading a file in ~/Desktop (and the home folder) is blocked', { skip }, async () => {
  const desk = path.join(os.homedir(), 'Desktop');
  // an existing regular file on the Desktop (only its NAME is used here; Python inside the sandbox tries to read it)
  let file = null; try { file = fs.readdirSync(desk).map((n) => path.join(desk, n)).find((p) => { try { return fs.statSync(p).isFile(); } catch (e) { return false; } }) || null; } catch (e) { file = null; }
  let made = false;
  if (!file) { file = path.join(desk, '.glim-sbx-probe-' + process.pid); fs.writeFileSync(file, 'secret'); made = true; }
  try {
    const r = await S.runPython('import os\ntry:\n    print("READ", len(open(' + JSON.stringify(file) + ', "rb").read()))\nexcept Exception as e:\n    print("blocked", type(e).__name__)\nfor p in [' + JSON.stringify(desk) + ', ' + JSON.stringify(os.homedir()) + ', "/Users"]:\n    try:\n        print("LISTED", p, len(os.listdir(p)))\n    except Exception as e:\n        print("blocked", type(e).__name__)');
    assert.ok(!/READ|LISTED/.test(r.stdout), r.stdout);
    assert.strictEqual((r.stdout.match(/blocked PermissionError/g) || []).length, 4, r.stdout);
  } finally { if (made) fs.rmSync(file, { force: true }); }
});

test('sandbox: an infinite loop is killed in 6 s or less', { skip }, async () => {
  const t0 = Date.now();
  const r = await S.runPython('while True:\n    pass');
  const ms = Date.now() - t0;
  assert.strictEqual(r.ok, false); assert.ok(r.timedOut || r.signal, 'killed by a limit');
  assert.ok(ms <= 6000, 'killed after ' + ms + ' ms');
});

test('sandbox: a memory bomb is killed', { skip }, async () => {
  const t0 = Date.now();
  const r = await S.runPython('x = bytearray(6 * 1024 ** 3)\nprint("ALLOCATED", len(x))');
  assert.strictEqual(r.ok, false); assert.ok(!/ALLOCATED/.test(r.stdout));
  assert.ok(r.memKilled || /MemoryError/.test(r.stderr), 'killed by the memory limit (' + r.why + ')');
  assert.ok(Date.now() - t0 < 6000);
  const r2 = await S.runPython('xs = []\nwhile True:\n    xs.append(bytearray(50 * 1024 * 1024))');
  assert.strictEqual(r2.ok, false); assert.ok(r2.memKilled || /MemoryError/.test(r2.stderr), r2.why);
});

test('sandbox: a fork bomb is contained (no new process starts; no subprocess, no exec)', { skip }, async () => {
  const before = Number(require('child_process').execFileSync('/bin/sh', ['-c', 'ps -A | wc -l']).toString().trim());
  const r = await S.runPython('import os\nn = 0\ntry:\n    while True:\n        os.fork(); n += 1\nexcept Exception as e:\n    print("fork", type(e).__name__, n)');
  assert.match(r.stdout, /fork PermissionError 0/, r.stdout + r.stderr);
  const after = Number(require('child_process').execFileSync('/bin/sh', ['-c', 'ps -A | wc -l']).toString().trim());
  assert.ok(after - before < 20, 'no process explosion (' + before + ' -> ' + after + ')');
  const r2 = await S.runPython('import subprocess\ntry:\n    subprocess.run(["/bin/ls"])\n    print("RAN")\nexcept Exception as e:\n    print("blocked", type(e).__name__)\nimport os\ntry:\n    os.execv("/bin/sh", ["sh", "-c", "echo EXEC"])\nexcept Exception as e:\n    print("blocked", type(e).__name__)');
  assert.ok(!/RAN|EXEC/.test(r2.stdout)); assert.strictEqual((r2.stdout.match(/blocked/g) || []).length, 2, r2.stdout);
});

test('sandbox: the temp dir is cleaned up after every run (also after a kill)', { skip }, async () => {
  const a = await S.runPython('open("f.txt", "w").write("x" * 1000)\nprint("ok")');
  assert.strictEqual(a.cleaned, true); assert.ok(!fs.existsSync(a.dir));
  const b = await S.runPython('while True:\n    pass', { timeoutMs: 800 });
  assert.strictEqual(b.cleaned, true); assert.ok(!fs.existsSync(b.dir));
  // the temp dir is never under the home folder, and holds nothing but the program while it runs
  const c = await S.runPython('import os\nprint(sorted(os.listdir(".")))', { keepDir: true });
  try { assert.strictEqual(S.normOut(c.stdout), "['main.py']"); assert.ok(!c.dir.startsWith(os.homedir() + '/Desktop')); }
  finally { fs.rmSync(c.dir, { recursive: true, force: true }); }
});

test('sandbox: output floods and an abort signal are stopped too', { skip }, async () => {
  const r = await S.runPython('while True:\n    print("x" * 1000)');
  assert.strictEqual(r.ok, false); assert.ok(r.outKilled); assert.ok(r.stdout.length <= S.DEFAULTS.outBytes);
  const ctl = new AbortController(); setTimeout(() => ctl.abort(), 200);
  const t0 = Date.now(); const s = await S.runPython('while True:\n    pass', { signal: ctl.signal });
  assert.strictEqual(s.aborted, true); assert.ok(Date.now() - t0 < 2000);
});

test('sandbox: the profile denies by default and never allows network, fork or the home folder', () => {
  const p = S.profile({ exe: '/usr/bin/python3', real: '/x/python3.9', prefix: '/x', roots: ['/x'] }, '/private/var/folders/aa/T/glim-sbx-1');
  assert.match(p, /^\(version 1\)\n\(deny default\)/);
  assert.ok(!/network/.test(p)); assert.ok(!/process-fork/.test(p)); assert.ok(!/\/Users/.test(p));
  assert.match(p, /\(allow file-write\* \(subpath "\/private\/var\/folders\/aa\/T\/glim-sbx-1"\) \(literal "\/dev\/null"\)\)/);
});
