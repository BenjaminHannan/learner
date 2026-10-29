'use strict';
// Candidate checking owns a private engine and HTTP-only grader. Neither process
// is ever attached to the ordinary gateway. A verdict is usable only after BOTH
// processes have exited. The durable intent precedes spawn, including its random
// command markers, so a crash before PID publication is recoverable by scanning
// for that exact owned job. Unknown ownership/exit status is deliberately blocked.
const fs = require('fs');
const path = require('path');
const net = require('net');
const http = require('http');
const crypto = require('crypto');
const { spawn: realSpawn, execFile } = require('child_process');

const hash = data => crypto.createHash('sha256').update(data).digest('hex');
function fileHash(file) {
  const digest = crypto.createHash('sha256'), buffer = Buffer.allocUnsafe(1024 * 1024), fd = fs.openSync(file, 'r');
  try { let n; while ((n = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) digest.update(buffer.subarray(0, n)); }
  finally { fs.closeSync(fd); }
  return digest.digest('hex');
}
const exists = file => fs.existsSync(file);
const defer = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const abortError = message => Object.assign(new Error(message || 'Private check was interrupted.'), { name: 'AbortError' });
const errorText = error => String(error && error.message || error || 'Private check failed.');
const normalize = (file, platform) => { const p = path.resolve(file); return platform === 'win32' ? p.toLowerCase() : p; };
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
function privateFetch(url, options = {}) {
  // Core HTTP has no environment proxy or redirect fallback. This capability
  // must never travel through the ordinary gateway or another origin.
  const parsed = new URL(url);
  if (parsed.protocol !== 'http:' || parsed.hostname !== '127.0.0.1' || parsed.username || parsed.password) return Promise.reject(new Error('Invalid private loopback endpoint.'));
  return new Promise((resolve, reject) => {
    const request = http.get({ hostname: '127.0.0.1', port: parsed.port, path: parsed.pathname + parsed.search,
      headers: options.headers, signal: options.signal, agent: false }, response => {
      let body = '';
      response.on('data', chunk => { body += String(chunk); if (body.length > 1024 * 1024) request.destroy(new Error('Private readiness response exceeded its limit.')); });
      response.once('error', reject);
      response.once('end', () => resolve({ ok: response.statusCode >= 200 && response.statusCode < 300,
        json: async () => JSON.parse(body) }));
    });
    request.once('error', reject);
  });
}
function atomic(file, value) {
  const temp = file + '.tmp-' + crypto.randomUUID();
  let fd;
  try {
    fd = fs.openSync(temp, 'wx', 0o600); fs.writeFileSync(fd, JSON.stringify(value)); fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    fs.renameSync(temp, file); fs.chmodSync(file, 0o600);
    if (process.platform !== 'win32') { const dir = fs.openSync(path.dirname(file), 'r'); try { fs.fsyncSync(dir); } finally { fs.closeSync(dir); } }
  } finally { if (fd !== undefined) fs.closeSync(fd); try { fs.unlinkSync(temp); } catch (_) {} }
}
function delay(ms, signal) {
  if (signal && signal.aborted) return Promise.reject(abortError());
  return new Promise((resolve, reject) => {
    const done = error => { clearTimeout(timer); if (signal) signal.removeEventListener('abort', cancelled); error ? reject(error) : resolve(); };
    const cancelled = () => done(abortError());
    const timer = setTimeout(() => done(), ms);
    if (signal) signal.addEventListener('abort', cancelled, { once: true });
  });
}
function bounded(promise, ms, signal, label) {
  if (signal && signal.aborted) return Promise.reject(abortError());
  return new Promise((resolve, reject) => {
    let done = false;
    const finish = (error, value) => { if (done) return; done = true; clearTimeout(timer); if (signal) signal.removeEventListener('abort', cancelled); error ? reject(error) : resolve(value); };
    const cancelled = () => finish(abortError());
    const timer = setTimeout(() => finish(new Error(label || 'Private check timed out.')), ms);
    if (signal) signal.addEventListener('abort', cancelled, { once: true });
    Promise.resolve(promise).then(value => finish(null, value), error => finish(error));
  });
}
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer(); server.once('error', reject);
    server.listen(0, '127.0.0.1', () => { const port = server.address().port; server.close(error => error ? reject(error) : resolve(port)); });
  });
}
function fileInfo(file) {
  const resolved = fs.realpathSync(file), stat = fs.statSync(resolved);
  if (!stat.isFile() || !stat.size || /[\r\n\0"]/.test(resolved)) throw new Error('Private check requires a regular nonempty file.');
  return { path: resolved, bytes: stat.size, mtimeMs: stat.mtimeMs, dev: stat.dev, ino: stat.ino };
}
function unchanged(info) {
  try { const now = fileInfo(info.path); return Object.keys(info).every(key => info[key] === now[key]); } catch (_) { return false; }
}
function hasArg(commandLine, flag, value, platform) {
  const escape = text => String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp('(?:^|\\s)' + escape(flag) + '\\s+(?:"' + escape(value) + '"|' + escape(value) + ')(?=\\s|$)', platform === 'win32' ? 'i' : '').test(commandLine || '');
}
function markers(record, role) {
  return role === 'server'
    ? [['--alias', record.alias], ['--api-key', record.apiKey], ['-m', record.model.path], ['--lora', record.adapter.path]]
    : [['--private-check-id', record.id], ['--server', record.url], ['--cards', record.cards.path]];
}
function matchesIdentity(identity, record, role, platform, checkBirth = true) {
  const expected = record.roles[role];
  return identity && identity.status === 'alive' && typeof identity.exe === 'string'
    && normalize(identity.exe, platform) === normalize(expected.exe, platform)
    && (!checkBirth || !expected.startTime || expected.startTime === identity.startTime)
    && markers(record, role).every(([flag, value]) => hasArg(identity.commandLine, flag, value, platform));
}
function validRecord(record, jobsDir) {
  if (!record || record.version !== 1 || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(record.id || '')
      || record.alias !== 'premonition-check-' + record.id || !/^[0-9a-f]{64}$/.test(record.apiKey || '')
      || !Number.isInteger(record.port) || record.port < 1 || record.port > 65535
      || record.url !== 'http://127.0.0.1:' + record.port || record.jobDir !== path.join(jobsDir, record.id)
      || !record.model || !record.adapter || !record.cards || !record.roles || typeof record.roles !== 'object') return false;
  for (const item of [record.model, record.adapter, record.cards]) if (typeof item.path !== 'string' || !path.isAbsolute(item.path)) return false;
  if (record.adapter.path !== path.join(record.jobDir, 'adapter.gguf') || record.cards.path !== path.join(record.jobDir, 'held.jsonl')) return false;
  for (const [role, item] of Object.entries(record.roles)) {
    if (!['server', 'grader'].includes(role) || !item || typeof item.exited !== 'boolean' || typeof item.exe !== 'string' || !path.isAbsolute(item.exe)
        || (item.pid !== null && (!Number.isInteger(item.pid) || item.pid < 1))
        || (item.startTime !== null && (typeof item.startTime !== 'string' || !item.startTime))) return false;
  }
  return true;
}

class PrivateCheck {
  constructor(root, options = {}) {
    this.root = path.resolve(root); this.home = path.join(this.root, 'sleep');
    this.jobsDir = path.join(this.home, 'private-check-jobs'); this.ledger = path.join(this.jobsDir, 'owned.json');
    this.o = options; this.platform = options.platform || process.platform;
    this.spawn = options.spawn || realSpawn; this.fetch = options.fetch || privateFetch;
    this.processes = options.processes || new ProcessIdentity({ platform: this.platform, exec: options.exec });
    this.active = null; this.recovering = null;
  }
  _save(record) {
    if (exists(this.ledger)) {
      if (fs.lstatSync(this.ledger).isSymbolicLink() || read(this.ledger).id !== record.id) throw new Error('A different private process job is still recorded.');
    }
    atomic(this.ledger, record);
  }
  _blocked(error) { return { ok: false, processStopped: false, blocked: true, error: errorText(error) }; }
  _clean() { return { ok: true, processStopped: true }; }
  async _probe(action) {
    try { return await bounded(Promise.resolve().then(action), this.o.inspectionTimeoutMs || 15000, null, 'Private process inspection timed out.'); }
    catch (_) { return { status: 'unknown' }; }
  }
  _checkAbort(run) { if (run.abort.signal.aborted) throw abortError(run.reason); }
  _event(run, role, child) {
    const finished = defer(), state = { child, finished: finished.promise, exited: false, code: null, stdout: '', stderr: '' };
    run.children[role] = state;
    const exit = code => {
      if (state.exited) return; state.exited = true; state.code = code; finished.resolve(state);
      if (role === 'server' && run.phase !== 'stopping') { run.reason = 'The private model exited during its check.'; run.abort.abort(); }
    };
    child.once('exit', exit);
    child.once('error', error => { state.error = errorText(error); if (!child.pid) { state.noProcess = true; exit(null); } });
    child.once('close', () => { if (!child.pid) { state.noProcess = true; exit(null); } });
    if (child.stdout) child.stdout.on('data', data => {
      if (state.stdout.length > 4 * 1024 * 1024) { run.reason = 'Private grader output exceeded its limit.'; run.abort.abort(); }
      state.stdout = (state.stdout + String(data)).slice(-4 * 1024 * 1024);
    });
    if (child.stderr) child.stderr.on('data', data => { state.stderr = (state.stderr + String(data)).slice(-4000); });
    return state;
  }
  async _spawn(run, role, exe, args, options) {
    this._checkAbort(run);
    run.record.roles[role] = { exe, pid: null, startTime: null, exited: false };
    this._save(run.record); // intent exists even if the app crashes inside spawn
    const child = this.spawn(exe, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], ...options });
    const state = this._event(run, role, child);
    if (child.pid) { run.record.roles[role].pid = child.pid; this._save(run.record); }
    else {
      await bounded(state.finished, this.o.spawnTimeoutMs || 5000, run.abort.signal, 'Private process did not spawn.');
      if (state.error) throw new Error(state.error);
      throw new Error('Private process did not return a PID.');
    }
    const identity = await this._probe(() => this.processes.inspect(child.pid));
    if (identity.status === 'gone' && (state.exited || child.exitCode != null || child.signalCode != null)) return state;
    if (!matchesIdentity(identity, run.record, role, this.platform, false) || !identity.startTime) throw new Error('Could not bind the private process identity.');
    run.record.roles[role].startTime = identity.startTime; this._save(run.record);
    this._checkAbort(run);
    return state;
  }
  async _ready(run) {
    const end = Date.now() + (this.o.startTimeoutMs || 180000);
    while (Date.now() < end) {
      this._checkAbort(run);
      const child = run.children.server;
      if (!child || child.exited || child.child.exitCode != null || child.child.signalCode != null) throw new Error('The private model exited before readiness.');
      const ctl = new AbortController(), abort = () => ctl.abort();
      run.abort.signal.addEventListener('abort', abort, { once: true });
      try {
        const task = (async () => {
          const response = await this.fetch(run.record.url + '/v1/models', { headers: { Authorization: 'Bearer ' + run.record.apiKey }, signal: ctl.signal, redirect: 'error' });
          if (!response.ok) return false;
          const body = await response.json(); return Array.isArray(body.data) && body.data.some(item => item.id === run.record.alias);
        })();
        const ready = await bounded(task, this.o.requestTimeoutMs || 2000, run.abort.signal, 'Private readiness request timed out.');
        this._checkAbort(run);
        if (ready && !child.exited && child.child.exitCode == null && child.child.signalCode == null) return;
      } catch (error) { if (run.abort.signal.aborted) throw abortError(run.reason); }
      finally { ctl.abort(); run.abort.signal.removeEventListener('abort', abort); }
      await delay(this.o.pollMs || 300, run.abort.signal);
    }
    throw new Error('The private model did not become ready in time.');
  }
  async _grader(run, input) {
    const args = ['-m', 'sleepmlx', 'served-check', '--server', run.record.url, '--cards', run.record.cards.path, '--private-check-id', run.record.id];
    const state = await this._spawn(run, 'grader', input.python, args, {
      cwd: input.sleepmlxParent,
      env: { ...process.env, PYTHONPATH: input.sleepmlxParent, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', HF_HUB_OFFLINE: '1',
        SLEEPMLX_SERVED_PRIVATE_API_KEY: run.record.apiKey, SLEEPMLX_SERVED_PRIVATE_ALIAS: run.record.alias },
    });
    await bounded(state.finished, this.o.graderTimeoutMs || 600000, run.abort.signal, 'Private grader timed out.');
    this._checkAbort(run);
    let verdict;
    try { verdict = JSON.parse(state.stdout.trim().split(/\r?\n/).pop()); } catch (_) { throw new Error('Private grader returned no complete verdict.'); }
    if (!verdict || typeof verdict !== 'object' || ![true, false, null].includes(verdict.ok)
        || (verdict.ok === true && state.code !== 0) || (verdict.ok === false && state.code !== 1) || (verdict.ok === null && state.code !== 2)) throw new Error('Private grader exit did not match its verdict.');
    return verdict;
  }
  async _prepare(run, input) {
    if (!/^[0-9a-f]{64}$/.test(input.expectedAdapterSha256 || '') || !/^[0-9a-f]{64}$/.test(input.expectedHeldSha256 || '')) throw new Error('Private check requires immutable candidate and held snapshot hashes.');
    const model = fileInfo(input.model), sourceAdapter = fileInfo(input.adapter), sourceCards = fileInfo(input.cards);
    const exe = fs.realpathSync(input.exe), python = fs.realpathSync(input.python), parent = fs.realpathSync(input.sleepmlxParent);
    if (sourceCards.bytes > 1024 * 1024 || fileHash(sourceAdapter.path) !== input.expectedAdapterSha256 || fileHash(sourceCards.path) !== input.expectedHeldSha256) throw new Error('Candidate or held snapshot changed before its private check.');
    fs.mkdirSync(this.home, { recursive: true, mode: 0o700 }); fs.mkdirSync(this.jobsDir, { recursive: true, mode: 0o700 });
    if (fs.lstatSync(this.jobsDir).isSymbolicLink()) throw new Error('Private process folder cannot be a symlink.');
    const secure = this.o.secureDirectory || (this.processes.secureDirectory && this.processes.secureDirectory.bind(this.processes));
    if (!secure || await this._probe(() => secure(this.jobsDir)) !== true) throw new Error('Could not protect the private process journal folder.');
    const id = crypto.randomUUID(), jobDir = path.join(this.jobsDir, id); fs.mkdirSync(jobDir, { mode: 0o700 }); run.jobDir = jobDir;
    const adapter = path.join(jobDir, 'adapter.gguf'), cards = path.join(jobDir, 'held.jsonl');
    fs.copyFileSync(sourceAdapter.path, adapter, fs.constants.COPYFILE_EXCL); fs.chmodSync(adapter, 0o600);
    fs.copyFileSync(sourceCards.path, cards, fs.constants.COPYFILE_EXCL); fs.chmodSync(cards, 0o600);
    if (fileHash(adapter) !== input.expectedAdapterSha256 || fileHash(cards) !== input.expectedHeldSha256) throw new Error('Private snapshot copy did not match its immutable input.');
    const port = await (this.o.freePort || freePort)(); this._checkAbort(run);
    const record = { version: 1, id, alias: 'premonition-check-' + id, apiKey: crypto.randomBytes(32).toString('hex'), port,
      url: 'http://127.0.0.1:' + port, jobDir, model,
      adapter: { path: adapter, sha256: input.expectedAdapterSha256 }, cards: { path: cards, sha256: input.expectedHeldSha256 },
      sources: { adapter: sourceAdapter, cards: sourceCards }, roles: {}, created: new Date().toISOString() };
    if (exists(this.ledger)) throw new Error('A private process job still needs recovery.');
    run.record = record; this._save(record);
    return { ...input, exe, python, sleepmlxParent: parent };
  }
  _intact(record) {
    return unchanged(record.model) && unchanged(record.sources.adapter) && unchanged(record.sources.cards)
      && fileHash(record.adapter.path) === record.adapter.sha256
      && fileHash(record.cards.path) === record.cards.sha256
      && fileHash(record.sources.adapter.path) === record.adapter.sha256 && fileHash(record.sources.cards.path) === record.cards.sha256;
  }
  async _stopChild(run, role) {
    const state = run.children[role], item = run.record.roles[role];
    if (!state) return this._stopRecovered(run.record, role);
    const stopped = () => state.exited || state.noProcess || state.child.exitCode != null || state.child.signalCode != null;
    if (!stopped()) {
      try { state.child.kill('SIGTERM'); } catch (_) {}
      try { await bounded(state.finished, this.o.stopWaitMs || 8000, null, 'Private process ignored stop.'); } catch (_) {}
    }
    if (!stopped()) {
      try { state.child.kill('SIGKILL'); } catch (_) {}
      try { await bounded(state.finished, this.o.forceWaitMs || 5000, null, 'Private process exit was not confirmed.'); } catch (_) {}
    }
    if (!stopped()) return this._blocked('The private ' + role + ' process has not exited.');
    item.exited = true; this._save(run.record); return this._clean();
  }
  async _stopRecovered(record, role) {
    const item = record.roles[role];
    if (item.exited) return this._clean();
    let identity;
    if (!item.pid || !item.startTime) {
      const found = await this._probe(() => this.processes.find(record, role));
      if (!found || found.status !== 'ok') return this._blocked('Private process discovery is unavailable; recovery remains blocked.');
      if (!Array.isArray(found.processes) || found.processes.some(value => !value || (value.status !== 'gone'
          && (value.status !== 'alive' || !Number.isInteger(value.pid) || !value.startTime || !value.exe || !value.commandLine)))) return this._blocked('A discovered private process could not be inspected.');
      const matches = found.processes.filter(value => matchesIdentity(value, record, role, this.platform, false));
      if (!matches.length) { item.exited = true; this._save(record); return this._clean(); }
      if (matches.length !== 1 || !matches[0].startTime) return this._blocked('Private process discovery was ambiguous.');
      identity = matches[0]; item.pid = identity.pid; item.startTime = identity.startTime; this._save(record);
    } else identity = await this._probe(() => this.processes.inspect(item.pid));
    if (!identity || identity.status === 'unknown') return this._blocked('Private process identity could not be inspected.');
    // A positive birth mismatch proves the old process is gone. Never signal
    // the unrelated new owner of the reused PID, even if it is llama-server.
    if (identity.status === 'gone' || (identity.status === 'alive' && identity.startTime && identity.startTime !== item.startTime)) {
      item.exited = true; this._save(record); return this._clean();
    }
    if (!matchesIdentity(identity, record, role, this.platform)) return this._blocked('Private process ownership cannot be confirmed.');
    const result = await this._probe(() => this.processes.terminate(record, role, this.o.forceWaitMs || 5000));
    if (!result || result.status !== 'gone') return this._blocked('Recovered private process exit could not be confirmed.');
    item.exited = true; this._save(record); return this._clean();
  }
  _clear(record) {
    if (exists(this.ledger)) {
      if (read(this.ledger).id !== record.id) throw new Error('A different private process job replaced the journal.');
      fs.unlinkSync(this.ledger);
    }
    if (record.jobDir === path.join(this.jobsDir, record.id) && exists(record.jobDir) && !fs.lstatSync(record.jobDir).isSymbolicLink()) fs.rmSync(record.jobDir, { recursive: true, force: true });
  }
  async _stopAll(run, clear = true) {
    run.phase = 'stopping'; const failures = [];
    for (const role of ['grader', 'server']) if (run.record.roles[role]) {
      try { const result = await this._stopChild(run, role); if (!result.ok) failures.push(result.error); }
      catch (error) { failures.push(errorText(error)); }
    }
    if (failures.length) return this._blocked(failures.join(' '));
    if (!clear) return this._clean();
    try { this._clear(run.record); return this._clean(); } catch (error) { return this._blocked(error); }
  }
  async _recover() {
    if (!exists(this.ledger)) return this._clean();
    let record;
    try { if (fs.lstatSync(this.ledger).isSymbolicLink()) throw new Error('Private process journal is a symlink.'); record = read(this.ledger); }
    catch (_) { return this._blocked('Private process journal is unreadable; recovery remains blocked.'); }
    if (!validRecord(record, this.jobsDir)) return this._blocked('Private process journal is invalid; recovery remains blocked.');
    return this._stopAll({ record, children: {}, phase: 'stopping' });
  }
  async ensureIdle() {
    const active = this.active;
    if (active) {
      if (!active.done) {
        active.reason = 'Private check was interrupted.'; active.abort.abort();
        const result = await active.finished.promise;
        return result.processStopped === true ? this._clean() : this._blocked(result.error || result.reasons && result.reasons.join(' '));
      }
      const result = await this._stopAll(active); if (result.ok) this.active = null; return result;
    }
    if (!this.recovering) this.recovering = this._recover().finally(() => { this.recovering = null; });
    return this.recovering;
  }
  async cancel() { return this.ensureIdle(); }
  async check(input) {
    if (!input || typeof input !== 'object' || (input.signal && typeof input.signal.addEventListener !== 'function')) return { ok: null, processStopped: true, reasons: ['Invalid private check request.'] };
    if (this.active || this.recovering) return { ok: null, processStopped: false, blocked: true, reasons: ['A private check is already active or recovering.'] };
    const run = { abort: new AbortController(), children: {}, finished: defer(), record: null, done: false, phase: 'recovering' };
    this.active = run;
    const cancelled = () => { run.reason = 'Private check was interrupted.'; run.abort.abort(); };
    if (input.signal) { input.signal.addEventListener('abort', cancelled, { once: true }); if (input.signal.aborted) cancelled(); }
    let verdict = { ok: null, reasons: ['Private check did not complete.'] }, clean = this._clean();
    try {
      const recovered = await this._recover();
      if (!recovered.ok) { clean = recovered; throw new Error(recovered.error); }
      this._checkAbort(run); input = await this._prepare(run, input); this._checkAbort(run);
      const record = run.record;
      const args = ['-m', record.model.path, '--host', '127.0.0.1', '--port', String(record.port), '-c', String(input.ctx || 2048), '-np', '1', '--jinja', '--no-webui', '-ngl', input.flavor === 'cpu' ? '0' : '99', '--lora', record.adapter.path, '--alias', record.alias, '--api-key', record.apiKey];
      if (input.flavor === 'cpu') args.push('-t', '2');
      run.phase = 'starting'; await this._spawn(run, 'server', input.exe, args, { cwd: path.dirname(input.exe) });
      await this._ready(run); this._checkAbort(run);
      run.phase = 'grading'; verdict = await this._grader(run, input); this._checkAbort(run);
      if (!this._intact(record)) throw new Error('Private check inputs changed during grading.');
    } catch (error) { verdict = { ok: null, reasons: [errorText(error)] }; }
    finally {
      if (run.record) {
        clean = await this._stopAll(run, false);
        if (clean.ok) {
          // Check again after shutdown, immediately before the verdict leaves
          // this controller. Slow/ignored termination must not open a mutation
          // window between validation and accepted promotion.
          try { if (!this._intact(run.record)) verdict = { ok: null, reasons: ['Private check inputs changed before completion.'] }; }
          catch (_) { verdict = { ok: null, reasons: ['Private check inputs could not be verified before completion.'] }; }
          try { this._clear(run.record); } catch (error) { clean = this._blocked(error); }
        }
      }
      else if (run.jobDir) { try { fs.rmSync(run.jobDir, { recursive: true, force: true }); } catch (_) {} }
      if (input.signal) input.signal.removeEventListener('abort', cancelled);
      if (run.abort.signal.aborted) verdict = { ok: null, reasons: [run.reason || 'Private check was interrupted.'] };
      if (!clean.ok) verdict = { ok: null, processStopped: false, blocked: true, reasons: [clean.error], error: clean.error };
      else verdict = { ...verdict, processStopped: true, checkId: run.record && run.record.id };
      if (run.record) verdict = JSON.parse(JSON.stringify(verdict).split(run.record.apiKey).join('[private key]'));
      run.done = true; if (clean.ok || !run.record) this.active = null; run.finished.resolve(verdict);
    }
    return verdict;
  }
}

// Windows recovery uses an open process handle throughout birth/executable/
// marker validation, termination and waiting. PID-only taskkill is intentionally
// absent: checking a PID then killing it in another command has a reuse race.
const WINDOWS_HELPER = String.raw`
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class PrivateProcessNative {
 [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr h);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GetProcessTimes(IntPtr h, out long created, out long exited, out long kernel, out long user);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool QueryFullProcessImageName(IntPtr h, uint flags, StringBuilder name, ref int size);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool TerminateProcess(IntPtr h, uint code);
 [DllImport("kernel32.dll")] public static extern uint WaitForSingleObject(IntPtr h, uint ms);
}
'@
$ErrorActionPreference = 'Stop'
$request = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__REQUEST__')) | ConvertFrom-Json
function Inspect-Owned($pidValue, $terminate) {
 $access = 0x100000 -bor 0x1000; if ($terminate) { $access = $access -bor 1 }
 $handle = [PrivateProcessNative]::OpenProcess($access, $false, [uint32]$pidValue)
 if ($handle -eq [IntPtr]::Zero) {
  $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
  if ($err -eq 87 -or $err -eq 1168) { return @{status='gone';pid=$pidValue} }
  return @{status='unknown';pid=$pidValue;error='OpenProcess failed'}
 }
 try {
  if ([PrivateProcessNative]::WaitForSingleObject($handle, 0) -eq 0) { return @{status='gone';pid=$pidValue} }
  [long]$created=0;[long]$exited=0;[long]$kernel=0;[long]$user=0
  if (-not [PrivateProcessNative]::GetProcessTimes($handle,[ref]$created,[ref]$exited,[ref]$kernel,[ref]$user)) { return @{status='unknown';pid=$pidValue} }
  $buffer=New-Object Text.StringBuilder 32768; [int]$size=32768
  if (-not [PrivateProcessNative]::QueryFullProcessImageName($handle,0,$buffer,[ref]$size)) { return @{status='unknown';pid=$pidValue} }
  $row=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$pidValue)
  if (-not $row) { if ([PrivateProcessNative]::WaitForSingleObject($handle,0) -eq 0) {return @{status='gone';pid=$pidValue}}; return @{status='unknown';pid=$pidValue} }
  $result=@{status='alive';pid=$pidValue;startTime=$created.ToString();exe=$buffer.ToString();commandLine=$row.CommandLine}
  if ($terminate) {
   if ($result.startTime -ne $request.startTime) { return @{status='gone';pid=$pidValue;reused=$true} }
   if (-not [String]::Equals($result.exe,$request.exe,[StringComparison]::OrdinalIgnoreCase)) { return @{status='unknown';pid=$pidValue} }
   foreach($marker in $request.markers) {
    $pattern='(?:^|\s)'+[Regex]::Escape($marker[0])+'\s+(?:"'+[Regex]::Escape($marker[1])+'"|'+[Regex]::Escape($marker[1])+')(?=\s|$)'
    if ($row.CommandLine -notmatch $pattern) { return @{status='unknown';pid=$pidValue} }
   }
   if (-not [PrivateProcessNative]::TerminateProcess($handle,1)) { return @{status='unknown';pid=$pidValue} }
   if ([PrivateProcessNative]::WaitForSingleObject($handle,[uint32]$request.waitMs) -eq 0) { return @{status='gone';pid=$pidValue} }
  }
  return $result
 } finally { [void][PrivateProcessNative]::CloseHandle($handle) }
}
try {
 if ($request.action -eq 'secure') {
  $acl=New-Object Security.AccessControl.DirectorySecurity
  $acl.SetAccessRuleProtection($true,$false)
  $userSid=[Security.Principal.WindowsIdentity]::GetCurrent().User
  $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
  $rule=[Security.AccessControl.FileSystemAccessRule]::new($userSid,[Security.AccessControl.FileSystemRights]::FullControl,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
  $acl.AddAccessRule($rule)
  (Get-Item -LiteralPath $request.path).SetAccessControl($acl)
  @{status='ok'} | ConvertTo-Json -Compress
 } elseif ($request.action -eq 'find') {
  $values=@(); $uncertain=$false; foreach($row in @(Get-CimInstance Win32_Process)) {
   if ($row.CommandLine -and $row.CommandLine.Contains($request.marker)) { $values+=Inspect-Owned $row.ProcessId $false }
   elseif (-not $row.CommandLine -and [String]::Equals($row.Name,$request.imageName,[StringComparison]::OrdinalIgnoreCase)) { $uncertain=$true }
  }
  if ($uncertain) { @{status='unknown'} | ConvertTo-Json -Compress }
  else {
   @{status='ok';processes=@($values)} | ConvertTo-Json -Depth 8 -Compress
  }
 } else { Inspect-Owned $request.pid ($request.action -eq 'terminate') | ConvertTo-Json -Depth 8 -Compress }
} catch { @{status='unknown';error='Private process inspection failed'} | ConvertTo-Json -Compress }
`;
class ProcessIdentity {
  constructor(options = {}) { this.platform = options.platform || process.platform; this.exec = options.exec || ((exe, args) => new Promise((resolve, reject) => execFile(exe, args, { windowsHide: true, timeout: 12000, maxBuffer: 4 * 1024 * 1024 }, (error, stdout) => error ? reject(error) : resolve(String(stdout))))); }
  async _windows(request) {
    try {
      const script = WINDOWS_HELPER.replace('__REQUEST__', Buffer.from(JSON.stringify(request), 'utf8').toString('base64'));
      const stdout = await this.exec('powershell.exe', ['-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(script, 'utf16le').toString('base64')]);
      return JSON.parse(stdout.trim());
    } catch (_) { return { status: 'unknown' }; }
  }
  async inspect(pid) {
    if (this.platform === 'win32') return this._windows({ action: 'inspect', pid });
    try {
      const [startTime, exe, commandLine] = await Promise.all([
        this.exec('/bin/ps', ['-p', String(pid), '-o', 'lstart=']), this.exec('/bin/ps', ['-ww', '-p', String(pid), '-o', 'comm=']), this.exec('/bin/ps', ['-ww', '-p', String(pid), '-o', 'args=']),
      ]);
      return startTime.trim() && exe.trim() && commandLine.trim() ? { status: 'alive', pid, startTime: startTime.trim(), exe: exe.trim(), commandLine: commandLine.trim() } : { status: 'unknown' };
    } catch (_) { try { process.kill(pid, 0); return { status: 'unknown' }; } catch (error) { return { status: error.code === 'ESRCH' ? 'gone' : 'unknown', pid }; } }
  }
  async secureDirectory(dir) {
    if (this.platform === 'win32') return (await this._windows({ action: 'secure', path: dir })).status === 'ok';
    try { fs.chmodSync(dir, 0o700); return (fs.statSync(dir).mode & 0o077) === 0; } catch (_) { return false; }
  }
  async find(record, role) {
    if (this.platform === 'win32') return this._windows({ action: 'find', marker: role === 'server' ? record.alias : record.id, imageName: record.roles[role].exe.split(/[\\/]/).pop() });
    return { status: 'unknown' }; // no safe arbitrary orphan signalling on other platforms
  }
  async terminate(record, role, waitMs) {
    if (this.platform !== 'win32') return { status: 'unknown' };
    const item = record.roles[role];
    return this._windows({ action: 'terminate', pid: item.pid, exe: item.exe, startTime: item.startTime, markers: markers(record, role), waitMs });
  }
}
const controllers = new Map();
function getPrivateCheck(root, options) {
  let key = path.resolve(root); try { key = fs.realpathSync(key); } catch (_) {}
  if (!controllers.has(key)) controllers.set(key, new PrivateCheck(key, options));
  return controllers.get(key);
}
module.exports = { PrivateCheck, ProcessIdentity, getPrivateCheck, matchesIdentity, validRecord, hasArg, privateFetch, WINDOWS_HELPER };
