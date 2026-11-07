'use strict';
// Explicit real-device test only. Start through Premonition's executable with
// GLIM_HANDS_TEST=1. It opens a throwaway window and stops if Ben returns.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn, execFile } = require('node:child_process');
const { promisify } = require('node:util');
const { NativeSession, compile } = require('./native');
const { execute } = require('./actions');
const { report } = require('./test-status');
const run = promisify(execFile);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

class Aux {
  constructor() { this.rows = []; this.waiters = []; }
  static async start(library, bridge, monitor) {
    const a = new Aux(); a.dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gha-')); fs.chmodSync(a.dir, 0o700);
    a.server = net.createServer(); const socket = path.join(a.dir, 's');
    await new Promise((resolve, reject) => { a.server.once('error', reject); a.server.listen(socket, resolve); });
    const connected = new Promise((resolve, reject) => { const timer = setTimeout(() => reject(Error('test helper did not connect')), 10000); a.server.once('connection', s => { clearTimeout(timer); resolve(s); }); });
    a.child = spawn(process.execPath, [path.join(__dirname, 'native-child.js'), library, bridge, socket, monitor ? 'preflight' : 'inject'], { env:{ ...process.env, ELECTRON_RUN_AS_NODE:'1' }, stdio:['ignore','ignore','pipe'] });
    a.child.stderr.resume(); a.socket = await connected; a.server.close();
    a.socket.on('error', () => {});
    let buf = '';
    a.socket.on('data', data => {
      buf += data; let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i+1); let row;
        try { row = JSON.parse(line); } catch (_) { continue; }
        a.rows.push(row); if (a.onEvent) { try { a.onEvent(row); } catch (_) {} }
        for (const w of [...a.waiters]) if (w.match(row)) { a.waiters.splice(a.waiters.indexOf(w), 1); clearTimeout(w.timer); w.resolve(row); }
      }
    });
    a.ready = await a.next(row => row.ready || row.error, 10000);
    if (a.ready.error) throw Error(a.ready.error);
    return a;
  }
  next(match, timeout = 1000) {
    return new Promise((resolve, reject) => {
      const w = { match, resolve, timer:setTimeout(() => { const i = this.waiters.indexOf(w); if (i >= 0) this.waiters.splice(i, 1); reject(Error('test helper timed out')); }, timeout) };
      this.waiters.push(w);
    });
  }
  async close() { if (this.socket) this.socket.destroy(); if (this.server) this.server.close(); if (this.dir) fs.rmSync(this.dir, { recursive:true, force:true }); }
}

async function main() {
  if (process.env.GLIM_HANDS_TEST !== '1' || process.argv[2] !== '--run') throw Error('explicit test mode and --run required');
  const built = await compile(), dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hands-trial-')); fs.chmodSync(dir, 0o700);
  const lib = path.join(dir, 'aux.dylib'), windowBin = path.join(dir, 'window');
  await run('/usr/bin/xcrun', ['swiftc','-O','-target','arm64-apple-macos13.0','-emit-library','-module-name','HandsTestAux',path.join(__dirname,'test-aux.swift'),'-o',lib], { timeout:60000 });
  await run('/usr/bin/xcrun', ['swiftc','-O','-target','arm64-apple-macos13.0',path.join(__dirname,'test-window.swift'),'-o',windowBin], { timeout:60000 });
  await run('/usr/bin/codesign', ['--force','-s','-',lib], { timeout:15000 });
  let monitor, injector, window, session; const result = { mode:'separate-process CGEvent simulation', trials:[], probes:[], status:'incomplete' };
  try {
    monitor = await Aux.start(lib, built.bridge, true);
    if (monitor.ready.idleSeconds < 300) throw Error('Ben has not been idle for five minutes');
    injector = await Aux.start(lib, built.bridge, false);
    if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled')) throw Error('Ben returned or the monitor stopped');
    window = spawn(windowBin, [], { stdio:['ignore','pipe','pipe'] }); window.stderr.resume(); window.on('error', () => {});
    const rows = []; let data = '';
    window.stdout.on('data', chunk => { data += chunk; let i; while ((i = data.indexOf('\n')) >= 0) { const line=data.slice(0,i); data=data.slice(i+1); try { rows.push(JSON.parse(line)); } catch (_) {} } });
    for (let i=0; i<100 && !rows.some(r => r.ready); i++) { if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled')) throw Error('Ben returned'); await pause(50); }
    const ready = rows.find(r => r.ready); if (!ready || !ready.front) throw Error('test window is not in front');
    for (let i=0; i<10; i++) {
      if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled')) throw Error('Ben returned or the monitor stopped');
      if (rows.some(r => r.event === 'focus-lost')) throw Error('test window lost focus');
      session = await NativeSession.start(); const kind = i % 2 ? 'mouse' : 'key', first = rows.length;
      try {
        if (!/^\d+$/.test(session.status.tag || '')) throw Error('guard tag missing');
        const tagged = monitor.next(r => r.event === 'tagged' && r.tag === session.status.tag, 1000);
        monitor.socket.write('tag ' + session.status.tag + '\n'); await tagged;
        if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled') || rows.some(r => r.event === 'focus-lost')) throw Error('Ben returned or the test window lost focus');
        await session.command('grant');
        await session.command('send', kind === 'key' ? {kind:'key',code:56,down:true} : {kind:'mouse',state:'down',button:'left',x:ready.x,y:ready.y});
        if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled') || rows.some(r => r.event === 'focus-lost')) throw Error('Ben returned or the test window lost focus');
        const takeover = new Promise((resolve, reject) => { const timer=setTimeout(() => reject(Error('no takeover within 200 ms')),200); session.onRevoke = row => { if (row.reason === 'user input' && row.terminal) { clearTimeout(timer); resolve(row); } }; });
        const posted = injector.next(row => row.event === 'posted', 1000);
        injector.socket.write('fire\n');
        const [p, revoke] = await Promise.all([posted, takeover]);
        await pause(100);
        const evidence = rows.slice(first), down = kind === 'key' ? evidence.some(r => r.event === 'flags' && r.shift) : evidence.some(r => r.event === 'mouseDown'), up = kind === 'key' ? evidence.some(r => r.event === 'flags' && !r.shift) : evidence.some(r => r.event === 'mouseUp');
        let rejected = false; try { await session.command('send', {kind:'key',code:56,down:true}); } catch (_) { rejected = true; }
        const ms = (revoke.releaseDoneNs - p.atNs)/1e6;
        result.trials.push({ trial:i+1, kind, ms, released:revoke.released, down, up, rejected, pass:ms >= 0 && ms <= 200 && revoke.released >= 1 && down && up && rejected });
      } catch (e) { result.trials.push({ trial:i+1, kind, pass:false, error:String(e.message || e) }); }
      finally { await session.close(); session = null; }
      if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled')) throw Error('Ben returned or the monitor stopped');
      if (rows.some(r => r.event === 'focus-lost')) throw Error('test window lost focus');
      if (!result.trials.at(-1).pass) { result.status = 'fail'; break; }
    }
    result.status = result.trials.length === 10 && result.trials.every(t => t.pass) ? 'pass' : 'fail';
    if (result.status === 'pass') {
      result.takeoverPass = true;
      session = await NativeSession.start();
      if (!/^\d+$/.test(session.status.tag || '')) throw Error('guard tag missing');
      const tagged = monitor.next(r => r.event === 'tagged' && r.tag === session.status.tag, 1000);
      monitor.socket.write('tag ' + session.status.tag + '\n'); await tagged;
      const probes = [
        { name:'click', action:{type:'click',x:ready.x,y:ready.y}, pass:r => r.some(e => e.event === 'mouseDown') && r.some(e => e.event === 'mouseUp') },
        { name:'drag', action:{type:'drag',x:ready.x,y:ready.y,toX:ready.x+40,toY:ready.y+20}, pass:r => r.some(e => e.event === 'mouseDown') && r.some(e => e.event === 'mouseDragged') && r.some(e => e.event === 'mouseUp') },
        { name:'scroll', action:{type:'scroll',dy:-100}, pass:r => r.some(e => e.event === 'scroll') },
        { name:'type', action:{type:'type',text:'OK'}, pass:r => r.filter(e => e.event === 'keyDown').map(e => e.characters).join('').includes('OK') },
        { name:'press', action:{type:'press',combo:'a'}, pass:r => r.some(e => e.event === 'keyDown' && e.characters === 'a') }
      ];
      for (const probe of probes) {
        if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled') || rows.some(r => r.event === 'focus-lost')) throw Error('Ben returned or the test window lost focus');
        const first = rows.length;
        try { await execute(session,probe.action,new AbortController().signal); await pause(100); result.probes.push({ name:probe.name, pass:probe.pass(rows.slice(first)) }); }
        catch (e) { result.probes.push({ name:probe.name, pass:false, error:String(e.message || e) }); }
        if (!result.probes.at(-1).pass) break;
      }
      await session.close(); session = null;
      if (result.probes.length !== 5 || result.probes.some(p => !p.pass)) result.status = 'fail';
    }
  } catch (error) { result.error = String(error.message || error); result.status = 'incomplete'; }
  finally {
    if (session) await session.close();
    if (window && window.pid) window.kill(); // the exact process opened above
    if (injector) await injector.close(); if (monitor) await monitor.close();
    fs.rmSync(dir, { recursive:true, force:true });
  }
  const root = path.join(os.homedir(), 'learner-ops', 'hands-attempts'); fs.mkdirSync(root, { recursive:true, mode:0o700 });
  const file = path.join(root, 'takeover-' + Date.now() + '.json'); fs.writeFileSync(file, JSON.stringify(result, null, 2) + '\n', { mode:0o600 });
  report({ file, ...result });
  console.log(JSON.stringify({ file, ...result })); if (result.status !== 'pass') process.exitCode = 1;
}
if (require.main === module) main().catch(error => { report({ status:'error', error:error.message }); console.error(error.message); process.exitCode = 1; });
module.exports = { Aux };
