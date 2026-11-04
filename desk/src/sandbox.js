'use strict';
// Little scientist, part 1: an airtight Python sandbox where the world answers back ("what will this print?" -> run it).
//
// Every run:
//   - a FRESH temp dir (realpath under the per-user TMPDIR); the program is the only file in it; it is deleted afterwards
//   - /usr/bin/sandbox-exec with a deny-by-default profile:
//       network: denied (nothing allows it)        process-fork: denied (a fork bomb cannot start)
//       process-exec: only the system python itself (no subprocess, no shell)
//       file-write: only inside the temp dir (+ /dev/null)
//       file-read: only the system python's own folders, system libraries, timezone data, /dev/null|urandom, and the temp dir.
//                  Nothing under /Users (Ben's home), /Volumes, or any other temp folder can be read.
//   - limits: CPU 5 s (ulimit -t), wall clock 5 s, file size ~2 MB (ulimit -f), 32 open files (ulimit -n), stdout 32 KB.
//     macOS has no working memory rlimit (ulimit -v / -d are refused), so a watchdog reads the process's RSS every 50 ms and kills
//     the whole process group above the limit (default 256 MB).
//   - on any limit: SIGKILL to the whole process group (the child is started detached, so it leads its own group).
//   - a minimal environment (PATH=/usr/bin:/bin, HOME=TMPDIR=the temp dir), python -I -S -B (no user site, no env vars, no .pyc).
// No Ben file is ever passed in: callers give program TEXT only. The system python3 is used (it has no torch, which is fine).
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, execFile, execFileSync } = require('child_process');

const SANDBOX_EXEC = '/usr/bin/sandbox-exec';
const DEFAULTS = { timeoutMs: 5000, cpuS: 5, memMB: 256, outBytes: 32768, fileKB: 2048, pollMs: 50 };

const q = (p) => '"' + String(p).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
const ancestors = (p) => { const out = []; let d = path.dirname(p); while (d && d !== '/' && !out.includes(d)) { out.push(d); d = path.dirname(d); } return out; };

// the system python: its executable, the real file, and the folders it needs to start (resolved once, without any user code)
let pyCache = null;
function systemPython(o) {
  if (pyCache && !(o && o.fresh)) return pyCache;
  pyCache = { ok: false, why: 'not macOS' };
  if (process.platform !== 'darwin') return pyCache;
  if (!fs.existsSync(SANDBOX_EXEC)) return (pyCache = { ok: false, why: 'no sandbox-exec' });
  try {
    const out = String(execFileSync('/usr/bin/python3', ['-I', '-S', '-c', 'import sys,os;print(sys.executable);print(os.path.realpath(sys.executable));print(sys.prefix);print(sys.base_prefix)'],
      { timeout: 20000, env: { PATH: '/usr/bin:/bin' }, stdio: ['ignore', 'pipe', 'ignore'] })).trim().split('\n');
    const [exe, real, prefix, base] = out.map((s) => s.trim());
    if (!exe || !real || !path.isAbsolute(exe)) return (pyCache = { ok: false, why: 'python3 did not report itself' });
    const roots = new Set([prefix, base, path.dirname(exe), path.dirname(real)].filter(Boolean));
    // the Command Line Tools / Xcode python lives in one developer folder; allow that folder whole (read only)
    for (const r of [...roots]) { const m = /^(\/Library\/Developer\/CommandLineTools|\/Applications\/Xcode[^/]*\.app\/Contents\/Developer)\//.exec(r + '/'); if (m) roots.add(m[1]); }
    for (const r of roots) if (/^\/(?:Users|Volumes)\b/.test(r) || /^\/private\/var\/folders\b/.test(r)) return (pyCache = { ok: false, why: 'python3 lives in a user folder (' + r + '); refused' });
    pyCache = { ok: true, exe, real, prefix, roots: [...roots] };
  } catch (e) { pyCache = { ok: false, why: 'python3 not runnable: ' + String(e && e.message || e).slice(0, 80) }; }
  return pyCache;
}
function available() { return systemPython().ok; }

// the sandbox profile for one run (dir = the run's temp dir, a realpath)
function profile(py, dir) {
  const read = ['/usr/lib', '/usr/share', '/System/Library', '/System/Volumes/Preboot/Cryptexes', '/System/Cryptexes', '/private/var/db/timezone', ...py.roots, dir];
  const meta = new Set(['/private', '/private/var', '/private/tmp', '/tmp', '/var', '/usr', '/System', '/Library', '/dev']);
  for (const r of read) for (const a of ancestors(r + '/x')) if (a !== r) meta.add(a);
  return [
    '(version 1)',
    '(deny default)',
    // exec: only the python binary itself and the framework's Python.app it re-execs into (not every tool in the developer folder)
    '(allow process-exec (literal ' + q(py.exe) + ') (literal ' + q(py.real) + ') (subpath ' + q(path.join(py.prefix, 'Resources', 'Python.app')) + '))',
    '(allow file-read* (literal "/") (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random")' + read.map((r) => ' (subpath ' + q(r) + ')').join('') + ')',
    '(allow file-read-metadata' + [...meta].map((m) => ' (literal ' + q(m) + ')').join('') + ')',
    '(allow file-write* (subpath ' + q(dir) + ') (literal "/dev/null"))',
    '(allow sysctl-read)'
  ].join('\n');
}

function rssKB(pid) {
  return new Promise((res) => execFile('/bin/ps', ['-o', 'rss=', '-p', String(pid)], { timeout: 1000 }, (e, out) => res(e ? null : parseInt(String(out).trim(), 10) || 0)));
}

// run one program. -> { ok, stdout, stderr, exitCode, signal, timedOut, memKilled, outKilled, ms, why }
// o: { timeoutMs, cpuS, memMB, outBytes, fileKB, signal (AbortSignal), keepDir (tests: return the dir instead of deleting it) }
async function runPython(code, o) {
  o = { ...DEFAULTS, ...(o || {}) };
  const py = systemPython();
  if (!py.ok) return { ok: false, why: 'unavailable: ' + py.why, stdout: '', stderr: '' };
  if (typeof code !== 'string' || !code.trim() || code.length > 20000) return { ok: false, why: 'no program', stdout: '', stderr: '' };
  const dir = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'glim-sbx-'));
  const t0 = Date.now();
  const r = { ok: false, stdout: '', stderr: '', exitCode: null, signal: null, timedOut: false, memKilled: false, outKilled: false, aborted: false, ms: 0, dir };
  try {
    fs.writeFileSync(path.join(dir, 'main.py'), code, { mode: 0o600 });
    const sh = 'ulimit -t ' + (o.cpuS | 0) + ' && ulimit -f ' + (o.fileKB | 0) + ' && ulimit -n 32 && exec "$0" "$@"';
    const child = spawn('/bin/sh', ['-c', sh, SANDBOX_EXEC, '-p', profile(py, dir), py.exe, '-I', '-S', '-B', 'main.py'], {
      cwd: dir, detached: true, stdio: ['ignore', 'pipe', 'pipe'],
      env: { PATH: '/usr/bin:/bin', HOME: dir, TMPDIR: dir + '/', LANG: 'en_US.UTF-8', PYTHONIOENCODING: 'utf-8', PYTHONHASHSEED: '0' }
    });
    const killGroup = () => { try { process.kill(-child.pid, 'SIGKILL'); } catch (e) { try { child.kill('SIGKILL'); } catch (e2) { /* gone */ } } };
    let out = Buffer.alloc(0), err = Buffer.alloc(0);
    child.stdout.on('data', (d) => { out = Buffer.concat([out, d]); if (out.length > o.outBytes) { r.outKilled = true; killGroup(); } });
    child.stderr.on('data', (d) => { if (err.length < 8192) err = Buffer.concat([err, d]); });
    const wall = setTimeout(() => { r.timedOut = true; killGroup(); }, o.timeoutMs);
    let alive = true;
    const watch = (async () => { while (alive) { await new Promise((s) => setTimeout(s, o.pollMs)); if (!alive) break; const kb = await rssKB(child.pid); if (alive && kb != null && kb > o.memMB * 1024) { r.memKilled = true; killGroup(); break; } } })();
    const onAbort = () => { r.aborted = true; killGroup(); };
    if (o.signal) { if (o.signal.aborted) onAbort(); else o.signal.addEventListener('abort', onAbort, { once: true }); }
    await new Promise((res) => { child.on('error', (e) => { r.why = 'spawn failed: ' + e.message; res(); }); child.on('close', (c, s) => { r.exitCode = c; r.signal = s; res(); }); });
    alive = false; clearTimeout(wall); killGroup(); await watch;
    if (o.signal) o.signal.removeEventListener('abort', onAbort);
    r.stdout = out.slice(0, o.outBytes).toString('utf8'); r.stderr = err.toString('utf8').slice(0, 2000);
    r.ok = r.exitCode === 0 && !r.timedOut && !r.memKilled && !r.outKilled && !r.aborted;
    if (!r.ok && !r.why) r.why = r.timedOut ? 'time limit' : r.memKilled ? 'memory limit' : r.outKilled ? 'output limit' : r.aborted ? 'stopped' : 'exit ' + r.exitCode + (r.signal ? ' ' + r.signal : '');
  } finally {
    r.ms = Date.now() - t0;
    if (!o.keepDir) { try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* tmp */ } r.cleaned = !fs.existsSync(dir); }
  }
  return r;
}

// the visible output, compared the way a person would: trailing spaces and the final newline do not count
const normOut = (s) => String(s == null ? '' : s).replace(/\r\n/g, '\n').split('\n').map((l) => l.replace(/\s+$/, '')).join('\n').replace(/\n+$/, '');

module.exports = { runPython, available, systemPython, profile, normOut, DEFAULTS, SANDBOX_EXEC };
