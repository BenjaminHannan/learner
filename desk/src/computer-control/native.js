'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { execFile, spawn } = require('node:child_process');
const { promisify } = require('node:util');
const { randomUUID } = require('node:crypto');
const run = promisify(execFile);

let compiled, active = false;

function takeLock() {
  const root = path.join(os.homedir(), 'learner-ops', 'hands-attempts');
  fs.mkdirSync(root, { recursive:true, mode:0o700 });
  const file = path.join(root, 'desktop-control.lock'), token = randomUUID();
  let fd;
  try { fd = fs.openSync(file, 'wx', 0o600); }
  catch (error) { if (error.code === 'EEXIST') throw Error('Desktop control is already reserved or needs recovery'); throw error; }
  try { fs.writeFileSync(fd, JSON.stringify({ pid:process.pid, token })); } finally { fs.closeSync(fd); }
  return { file, token };
}

// The build ships the sources. Compile into a private, per-process directory;
// load the bridge in an isolated Premonition process so TCC checks its identity.
async function compile() {
  if (compiled) return compiled;
  compiled = (async () => {
    if (process.platform !== 'darwin' || process.arch !== 'arm64') throw Error('Mac Apple silicon required');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'glim-hands-'));
    fs.chmodSync(dir, 0o700);
    const library = path.join(dir, 'hands-guard.dylib'), bridge = path.join(dir, 'hands-bridge.node');
    try {
      await run('/usr/bin/xcrun', ['swiftc', '-O', '-target', 'arm64-apple-macos13.0', '-emit-library', '-module-name', 'GlimHands', path.join(__dirname, 'guard.swift'), '-o', library], { timeout: 60000 });
      await run('/usr/bin/xcrun', ['clang++', '-arch', 'arm64', '-std=c++17', '-bundle', '-undefined', 'dynamic_lookup', '-I/opt/homebrew/include/node', path.join(__dirname, 'native-bridge.cc'), '-o', bridge], { timeout: 60000 });
      await run('/usr/bin/codesign', ['--force', '-s', '-', library], { timeout: 15000 });
      await run('/usr/bin/codesign', ['--force', '-s', '-', bridge], { timeout: 15000 });
      return { dir, library, bridge };
    } catch (error) { fs.rmSync(dir, { recursive:true, force:true }); throw error; }
  })().catch(error => { compiled = null; throw error; });
  return compiled;
}

class NativeSession {
  constructor() { this.pending = new Map(); this.seq = 0; this.stopped = false; this.cancelled = false; this.buffer = ''; this.events = []; }
  static async start({ preflight = false } = {}) {
    if (active) throw Error('The desktop is already in use by Glim');
    active = true;
    const session = new NativeSession();
    try {
      session.lock = takeLock();
      const built = await compile();
      session.dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gh-'));
      fs.chmodSync(session.dir, 0o700);
      session.socketPath = path.join(session.dir, 's');
      session.server = net.createServer();
      await new Promise((resolve, reject) => { session.server.once('error', reject); session.server.listen(session.socketPath, resolve); });
      const connected = new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(Error('native input guard did not connect')), 10000);
        session.server.once('connection', socket => { clearTimeout(timer); resolve(socket); });
        session.server.once('error', error => { clearTimeout(timer); reject(error); });
      });
      const env = { ...process.env, ELECTRON_RUN_AS_NODE:'1' };
      session.child = spawn(process.execPath, [path.join(__dirname, 'native-child.js'), built.library, built.bridge, session.socketPath, preflight ? 'preflight' : 'watch'], { env, stdio:['ignore','ignore','pipe'] });
      session.childError = '';
      session.child.stderr.on('data', chunk => { session.childError = (session.childError + chunk.toString()).slice(-4096); });
      session.nativeDone = new Promise(resolve => {
        session.child.once('error', error => { session.childError = error.message; resolve(); if (!session.stopped) session.stop('native guard stopped'); });
        session.child.once('exit', () => { resolve(); if (!session.stopped && !preflight) session.stop('native guard stopped'); });
      });
      session.socket = await connected;
      session.server.close();
      const ready = new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(Error('native input guard did not become ready')), 10000);
        session.ready = row => { clearTimeout(timer); row.error ? reject(Error(row.error)) : resolve(row); };
      });
      session.socket.on('data', chunk => session.onData(chunk));
      session.socket.on('error', error => session.stop(error.message));
      session.socket.on('close', () => session.stop('native guard disconnected'));
      session.status = await ready;
      if (!preflight && session.status.ready !== true) throw Error('native input watcher unavailable');
      if (preflight) await session.close();
      return session;
    } catch (error) { await session.close(); throw error; }
  }
  onData(chunk) {
    this.buffer += chunk.toString('utf8');
    if (this.buffer.length > 16 * 1024 * 1024) return this.stop('bad guard response');
    let i;
    while ((i = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, i); this.buffer = this.buffer.slice(i + 1);
      let row; try { row = JSON.parse(line); } catch (_) { this.stop('bad guard response'); return; }
      if (this.ready) { const fn = this.ready; this.ready = null; fn(row); continue; }
      if (row.event === 'revoked') {
        this.events.push(row); if (this.events.length > 1000) this.events.shift();
        if (row.terminal) { this.cancelled = true; this.stopReason = row.reason; }
        if (this.onRevoke) { try { this.onRevoke(row); } catch (_) { /* observers do not control the guard */ } }
      }
      const p = this.pending.get(row.id);
      if (p) { this.pending.delete(row.id); clearTimeout(p.timer); row.ok ? p.resolve(row) : p.reject(Error(row.error || 'input refused')); }
    }
  }
  command(op, body = {}) {
    if (this.stopped || this.cancelled || !this.socket) return Promise.reject(Error(this.stopReason || 'control stopped'));
    const id = String(++this.seq);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.stop('guard response timed out'); reject(Error('guard response timed out')); }, op === 'look' ? 15000 : 1000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.write(JSON.stringify({ ...body, op, id }) + '\n');
    });
  }
  stop(reason) {
    if (this.stopped) return;
    this.stopped = true; this.cancelled = true; this.stopReason = reason || 'control stopped';
    for (const p of this.pending.values()) { clearTimeout(p.timer); p.reject(Error(this.stopReason)); }
    this.pending.clear();
    if (this.ready) { const fn = this.ready; this.ready = null; fn({ error:this.stopReason }); }
    if (this.socket) this.socket.destroy();
  }
  async close() {
    this.stop('control closed');
    if (this.server) this.server.close();
    if (this.nativeDone) await this.nativeDone;
    if (this.dir) fs.rmSync(this.dir, { recursive:true, force:true });
    if (this.lock) {
      try { if (JSON.parse(fs.readFileSync(this.lock.file, 'utf8')).token === this.lock.token) fs.unlinkSync(this.lock.file); } catch (_) { /* already gone */ }
      this.lock = null;
    }
    active = false;
  }
}
module.exports = { NativeSession, compile };
