'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

const MAX = 4000;

function trim(s) {
  if (s.length <= MAX) return s;
  const head = Math.floor(MAX * 0.6);
  return s.slice(0, head) + '\n…[' + (s.length - MAX) + ' chars cut]…\n' + s.slice(s.length - (MAX - head));
}

function runShell(command, opts) {
  opts = opts || {};
  const timeoutMs = opts.timeoutMs || 60000;
  const zsh = fs.existsSync('/bin/zsh') ? '/bin/zsh' : null;
  const sh = zsh || '/bin/bash';
  return new Promise((resolve) => {
    let out = '';
    let done = false;
    const child = spawn(sh, ['-lc', command], { cwd: os.homedir(), env: process.env, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
    const finish = (txt) => { if (done) return; done = true; clearTimeout(timer); if (opts.signal) opts.signal.removeEventListener('abort', onAbort); resolve(trim(txt)); };
    const kill = () => { try { process.kill(-child.pid, 'SIGKILL'); } catch (e) { try { child.kill('SIGKILL'); } catch (e2) { /* gone */ } } };
    const timer = setTimeout(() => { kill(); finish(out + '\n[timed out after ' + timeoutMs / 1000 + ' s]'); }, timeoutMs);
    const onAbort = () => { kill(); finish(out + '\n[stopped]'); };
    if (opts.signal) { if (opts.signal.aborted) return onAbort(); opts.signal.addEventListener('abort', onAbort); }
    child.stdout.on('data', (d) => { out += d; if (out.length > 200000) out = out.slice(-100000); });
    child.stderr.on('data', (d) => { out += d; if (out.length > 200000) out = out.slice(-100000); });
    child.on('error', (e) => finish('Error: ' + e.message));
    child.on('close', (code) => finish((out.trim() || '(no output)') + (code ? '\n[exit ' + code + ']' : '')));
  });
}

module.exports = { runShell, trim };
