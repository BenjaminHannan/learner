'use strict';
// An isolated role of Premonition.app. No chat, neural model, replay, or input API.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const { execFile } = require('node:child_process');
const { Recorder } = require('./recorder');

function run() {
  const { app, systemPreferences } = require('electron');
  app.commandLine.appendSwitch('disable-gpu');
  const base = path.join(os.homedir(), 'learner-ops/hands-recorder');
  const socket = path.join(base, 'premonition-recorder.sock');
  const statePath = path.join(base, 'state.json');
  const statusPath = path.join(base, 'status.json');
  const lockPath = path.join(base, '.recorder-host.lock');
  const nativeHelper = process.execPath;
  const nativeArgs = ['--glim-recorder-native'];
  let benchmark = null;
  let openingMain = false;
  let recorder = null, server = null, closing = false, busy = false, fakeTimer = null;
  fs.mkdirSync(base, { recursive: true, mode: 0o700 });
  fs.chmodSync(base, 0o700);
  const readState = () => { try { return JSON.parse(fs.readFileSync(statePath, 'utf8')); } catch (_) { return { enabled: false }; } };
  const writeState = (state) => { const tmp = statePath + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(state), { mode: 0o600 }); fs.renameSync(tmp, statePath); };
  const status = () => ({ ...(recorder ? recorder.status() : { enabled: false }),
    hostPid: process.pid, host: 'Premonition', fake: !!recorder?.fake,
    stopped: closing, at: new Date().toISOString() });
  const saveStatus = () => fs.writeFileSync(statusPath, JSON.stringify(status()), { mode: 0o600 });
  const native = (file, args) => new Promise((resolve, reject) => {
    const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE; delete env.ELECTRON_NO_ATTACH_CONSOLE;
    execFile(nativeHelper, [...nativeArgs, ...(file === 'canary' ? ['--glim-canary'] : []), ...args], { env, timeout: 20000, maxBuffer: 65536 }, (error, stdout, stderr) => {
      if (error) { error.message = stderr || error.message; reject(error); }
      else resolve(stdout.trim());
    });
  });
  async function acquireLock() {
    let acquired = false;
    for (let attempt = 0; attempt < 20 && !acquired; attempt++) {
      try { fs.mkdirSync(lockPath, { mode: 0o700 }); acquired = true; break; }
      catch (error) { if (error.code !== 'EEXIST') throw error; }
      let stat; try { stat = fs.lstatSync(lockPath); } catch (error) { if (error.code === 'ENOENT') continue; throw error; }
      if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('Unsafe recorder lock');
      let pid; try { pid = Number(fs.readFileSync(path.join(lockPath, 'pid'), 'utf8')); } catch (_) {}
      let live = !Number.isSafeInteger(pid) || pid <= 0 ? Date.now() - stat.mtimeMs < 10000 : false;
      if (!live && Number.isSafeInteger(pid) && pid > 0) {
        try { process.kill(pid, 0); live = true; } catch (probe) { if (probe.code !== 'ESRCH') throw probe; }
      }
      if (live) { await new Promise(resolve => setTimeout(resolve, 100)); continue; }
      try { fs.unlinkSync(path.join(lockPath, 'pid')); } catch (e) { if (e.code !== 'ENOENT') throw e; }
      try { fs.rmdirSync(lockPath); } catch (e) { if (e.code !== 'ENOENT') throw e; }
    }
    if (!acquired) throw Error('Recorder host already running or starting');
    fs.writeFileSync(path.join(lockPath, 'pid'), String(process.pid), { mode: 0o600 });
    if (fs.existsSync(socket)) {
      if (!fs.lstatSync(socket).isSocket()) throw Error('Unsafe recorder socket');
      const active = await new Promise((resolve, reject) => {
        const client = net.createConnection(socket);
        client.once('connect', () => { client.destroy(); resolve(true); });
        client.once('error', error => { if (error.code === 'ECONNREFUSED' || error.code === 'ENOENT') resolve(false); else reject(error); });
      });
      if (active) throw Error('Recorder socket already in use');
      if (fs.existsSync(socket)) fs.unlinkSync(socket);
    }
  }
  function releaseLock() {
    try { if (Number(fs.readFileSync(path.join(lockPath, 'pid'), 'utf8')) === process.pid) { fs.unlinkSync(path.join(lockPath, 'pid')); fs.rmdirSync(lockPath); } } catch (_) {}
  }
  async function stop(disable = true) {
    if (closing) return;
    closing = true;
    if (disable) writeState({ enabled: false });
    clearInterval(fakeTimer);
    if (recorder) await recorder.off();
    if (benchmark) { benchmark.stop(); await benchmark.done; }
    saveStatus();
    if (server) server.close();
    setTimeout(() => app.quit(), 100);
  }
  async function command(request) {
    switch (request.command) {
      case 'status': return {...status(), benchmark:benchmark?.result};
      case 'scratch-benchmark': {
        if (recorder?.enabled || benchmark?.result.enabled) throw Error('Stop existing capture first');
        if (request.benConfirmedAway !== true) throw Error('Explicit away confirmation required');
        benchmark = require('./scratch-benchmark').startScratchBenchmark(base, nativeHelper);
        return {...status(), benchmark:benchmark.result};
      }
      case 'preflight': return { ...JSON.parse(await native(nativeHelper, ['--preflight'])), hostPid: process.pid, hostScreen: systemPreferences.getMediaAccessStatus('screen'), hostAccessibility: systemPreferences.isTrustedAccessibilityClient(false) };
      case 'permissions': return { message: await native(nativeHelper, ['--request-permissions']) };
      case 'canary-permissions': return { message: await native('canary', ['--request-permissions']) };
      case 'canary': {
        if (recorder?.enabled || benchmark?.result.enabled) throw Error('Stop recording before the fake-field test');
        const dir = path.join(base, 'premonition-canary');
        fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
        const out = path.join(dir, 'result.json');
        for (const name of ['result.json', 'canary-tap-stream.log', 'verified.json']) {
          const file = path.join(dir, name);
          if (fs.existsSync(file)) fs.unlinkSync(file);
        }
        try { await native('canary', [...(request.benConfirmedAway === true ? ['--ben-confirmed-away'] : []), out]); } catch (error) {
          if (!fs.existsSync(out)) throw error;
        }
        const result = JSON.parse(fs.readFileSync(out, 'utf8'));
        if (result.status !== 'PASS') return result;
        return require(path.join(base, 'verify-canary.js')).verifyCanary(dir, [path.join(base, 'premonition-fake-recordings')]);
      }
      case 'start': {
        if (benchmark?.result.enabled) throw Error('Scratch measurement is still running');
        if (recorder?.enabled) return status();
        const fake = request.fake === true;
        writeState({ enabled: true, fake });
        // A separate lead release file is required for Ben's data. Installation never creates it.
        const release = path.join(base, 'LEAD-RELEASE.json');
        let approved = false;
        try { approved = JSON.parse(fs.readFileSync(release)).approved === true; } catch (_) {}
        if (!fake && !approved) throw Error('Recording Ben is OFF: lead release is still required');
        recorder = new Recorder({ root: path.join(base, fake ? 'premonition-fake-recordings' : 'recordings'),
          fake, releaseApproved: !fake && approved, nativeHelper, nativeArgs, shutdownMs: 5000 });
        await recorder.on();
        if (closing) { await recorder.off(); throw Error('Recorder stopped while starting'); }
        if (fake) fakeTimer = setInterval(() => recorder.event({ type: 'frame', frameId: recorder.frames + 1, t: Date.now() }), 50);
        try { app.setLoginItemSettings({ openAtLogin: true }); } catch (error) { console.error('Could not enable login startup:', error.message); }
        saveStatus();
        return status();
      }
      case 'stop':
        await stop();
        return { enabled: false, stopped: true, hostPid: process.pid };
      default: throw Error('Unknown recorder command');
    }
  }
  app.whenReady().then(async () => {
    app.dock?.hide();
    app.on('activate', () => {
      if (closing || openingMain) return;
      openingMain = true;
      const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE; delete env.ELECTRON_NO_ATTACH_CONSOLE;
      const bundle = path.resolve(process.execPath, '../../..');
      execFile('/usr/bin/open', ['-n', bundle], { env }, error => {
        openingMain = false;
        if (error) console.error('Could not open Premonition chat:', error.message);
      });
    });
    await acquireLock();
    saveStatus();
    server = net.createServer(connection => {
      let data = '', handled = false;
      connection.setTimeout(25000, () => connection.destroy());
      connection.on('error', () => {});
      connection.on('data', async bytes => {
        if (handled) return;
        data += bytes;
        if (data.length > 2048) { connection.destroy(); return; }
        if (!data.includes('\n')) return;
        handled = true;
        let request;
        try { request = JSON.parse(data); } catch (_) { connection.destroy(); return; }
        if (busy && request.command !== 'stop') { connection.end(JSON.stringify({ error: 'Recorder busy' }) + '\n'); return; }
        const exclusive = request.command !== 'stop';
        if (exclusive) busy = true;
        try { connection.end(JSON.stringify({ result: await command(request) }) + '\n'); }
        catch (error) { connection.end(JSON.stringify({ error: error.message }) + '\n'); }
        finally { if (exclusive) busy = false; }
      });
    });
    server.listen(socket, async () => {
      fs.chmodSync(socket, 0o600);
      const saved = readState();
      if (saved.enabled === true) {
        busy = true;
        try { await command({ command: 'start', fake: saved.fake === true }); }
        catch (error) { console.error('Recorder auto-start failed:', error.message); }
        finally { busy = false; }
      }
    });
    server.on('error', error => { console.error(error); stop(false); });
    const heartbeat = setInterval(saveStatus, 500);
    const retry = setInterval(async () => {
      if (closing || busy || readState().enabled !== true) return;
      busy = true;
      try {
        if (recorder?.enabled && recorder.paused) {
          await recorder.retryDisk();
        } else if (!recorder?.enabled) {
          if (recorder) await recorder.off();
          const saved = readState(); await command({ command: 'start', fake: saved.fake === true });
        }
      } catch (error) { console.error('Recorder retry failed:', error.message); }
      finally { busy = false; }
    }, 60000);
    app.once('will-quit', () => {
      clearInterval(heartbeat); clearInterval(retry);
      if (fs.existsSync(socket)) fs.unlinkSync(socket);
      releaseLock();
    });
  }).catch(error => { console.error(error); app.exit(1); });
  app.on('window-all-closed', () => {});
  process.on('SIGTERM', () => stop(false));
  process.on('SIGINT', () => stop(false));
  process.on('uncaughtException', error => { console.error(error); stop(false); });
  process.on('unhandledRejection', error => { console.error(error); stop(false); });
}
module.exports = { run };
