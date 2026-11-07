'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const vm = require('node:vm');
const { EventEmitter } = require('node:events');
const source = fs.readFileSync(path.join(__dirname, '../../src/hands-toy/premonition-host.js'), 'utf8');
const temporaryRoot = process.platform === 'darwin' ? '/tmp' : os.tmpdir();

function harness(home, options = {}) {
  const app = new EventEmitter(), proc = new EventEmitter();
  const launches = [], intervals = [];
  app.whenReady = async () => {}; app.dock = { hide() {} }; app.commandLine = { appendSwitch() {} }; app.quit = () => app.emit('will-quit');
  app.exit = () => app.emit('will-quit'); app.setLoginItemSettings = () => {};
  proc.pid = process.pid; proc.env = options.env || process.env; proc.execPath = options.execPath || process.execPath; proc.kill = process.kill.bind(process);
  class FakeRecorder {
    constructor({ fake }) { this.fake = fake; this.enabled = false; }
    async on() { this.enabled = true; }
    async off() { this.enabled = false; }
    event() {}
    status() { return { enabled: this.enabled, paused: false }; }
  }
  const module = { exports: {} };
  const fakeRequire = name => name === 'electron' ? { app, systemPreferences: { getMediaAccessStatus: () => 'granted', isTrustedAccessibilityClient: () => true } }
    : name === 'node:child_process' ? { execFile(file, args, launchOptions, callback) {
      launches.push({ file, args, options: launchOptions });
      callback(null, JSON.stringify({ screen: true, input: true, accessibility: true }), '');
    } }
    : name === 'node:os' ? { homedir: () => home }
    : name === './recorder' ? { Recorder: options.Recorder || FakeRecorder } : require(name);
  vm.runInNewContext(source, { module, require: fakeRequire, process: proc, console, setTimeout, clearTimeout,
    setInterval(callback, milliseconds) { const timer = setInterval(callback, milliseconds); intervals.push({ callback, milliseconds }); return timer; }, clearInterval });
  module.exports.run();
  return { app, proc, launches, intervals };
}
async function query(socket, command) {
  return new Promise((resolve, reject) => {
    const c = net.createConnection(socket); let data = '';
    c.on('connect', () => c.write(JSON.stringify({ command }) + '\n'));
    c.on('data', x => { data += x; }); c.on('error', reject);
    c.on('end', () => { const row = JSON.parse(data); row.error ? reject(Error(row.error)) : resolve(row.result); });
  });
}
async function waitUntil(predicate) {
  const end = Date.now() + 3000;
  while (Date.now() < end) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 10)); }
  throw Error('timed out waiting for recorder host');
}
test('saved enabled switch resumes a fake recorder and survives host shutdown; stop turns it off', async () => {
  const home = fs.mkdtempSync(path.join(temporaryRoot, 'hands-host-test-'));
  const base = path.join(home, 'learner-ops/hands-recorder'); fs.mkdirSync(base, { recursive: true });
  const state = path.join(base, 'state.json'), socket = path.join(base, 'premonition-recorder.sock');
  fs.writeFileSync(state, JSON.stringify({ enabled: true, fake: true }));
  try {
    let host = harness(home);
    await waitUntil(() => fs.existsSync(socket) && fs.existsSync(path.join(base, 'status.json')) && JSON.parse(fs.readFileSync(path.join(base, 'status.json'))).enabled);
    assert.equal((await query(socket, 'status')).enabled, true);
    host.proc.emit('SIGTERM'); await waitUntil(() => !fs.existsSync(socket));
    assert.equal(JSON.parse(fs.readFileSync(state)).enabled, true);
    host = harness(home);
    await waitUntil(() => fs.existsSync(socket) && JSON.parse(fs.readFileSync(path.join(base, 'status.json'))).enabled);
    assert.equal((await query(socket, 'status')).enabled, true);
    await query(socket, 'stop'); await waitUntil(() => !fs.existsSync(socket));
    assert.equal(JSON.parse(fs.readFileSync(state)).enabled, false);
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});
test('activating a hidden host opens the main app with a clean Electron environment', async () => {
  const home = fs.mkdtempSync(path.join(temporaryRoot, 'hands-activation-test-'));
  const socket = path.join(home, 'learner-ops/hands-recorder/premonition-recorder.sock');
  const env = { ...process.env, ELECTRON_RUN_AS_NODE: '1', ELECTRON_NO_ATTACH_CONSOLE: '1', RECORDER_TEST: 'preserved' };
  const host = harness(home, { env, execPath: '/Applications/Premonition.app/Contents/MacOS/Premonition' });
  try {
    await waitUntil(() => fs.existsSync(socket));
    host.app.emit('activate', {}, false);
    assert.equal(host.launches.length, 1);
    assert.equal(host.launches[0].file, '/usr/bin/open');
    assert.deepEqual(Array.from(host.launches[0].args), ['-n', '/Applications/Premonition.app']);
    assert.equal(host.launches[0].options.env.ELECTRON_RUN_AS_NODE, undefined);
    assert.equal(host.launches[0].options.env.ELECTRON_NO_ATTACH_CONSOLE, undefined);
    assert.equal(host.launches[0].options.env.RECORDER_TEST, 'preserved');
    const result = await query(socket, 'preflight');
    assert.equal(result.screen, true);
    assert.equal(host.launches[1].options.env.ELECTRON_RUN_AS_NODE, undefined);
    assert.equal(host.launches[1].options.env.ELECTRON_NO_ATTACH_CONSOLE, undefined);
    assert.equal(env.ELECTRON_RUN_AS_NODE, '1');
  } finally {
    host.proc.emit('SIGTERM');
    await waitUntil(() => !fs.existsSync(socket));
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test('saved ON survives low-disk restarts; 60-second retry respects margin and explicit OFF', async () => {
  const { Recorder } = require('../../src/hands-toy/recorder');
  const { GiB } = require('../../src/hands-toy/retention');
  const home = fs.mkdtempSync(path.join(temporaryRoot, 'hands-disk-host-'));
  const base = path.join(home, 'learner-ops/hands-recorder');
  fs.mkdirSync(base, { recursive: true });
  const state = path.join(base, 'state.json'), socket = path.join(base, 'premonition-recorder.sock');
  const recorders = [];
  let free = 5.9 * GiB, host;
  class DiskRecorder extends Recorder {
    constructor(options) {
      super({ ...options, fake: true, retentionOptions: { freeBytes: () => free } });
      recorders.push(this);
    }
    async segment() {
      if (free < 11 * GiB) return super.segment();
      this.starts = (this.starts || 0) + 1;
    }
  }
  fs.writeFileSync(state, JSON.stringify({ enabled: true, fake: true }));
  try {
    host = harness(home, { Recorder: DiskRecorder });
    await waitUntil(() => fs.existsSync(socket) && recorders[0]?.enabled);
    assert.equal((await query(socket, 'status')).reason, 'low disk — paused, will resume');
    host.proc.emit('SIGTERM'); await waitUntil(() => !fs.existsSync(socket));
    assert.equal(JSON.parse(fs.readFileSync(state)).enabled, true);
    host = harness(home, { Recorder: DiskRecorder });
    await waitUntil(() => fs.existsSync(socket) && recorders[1]?.enabled);
    const retry = host.intervals.find(timer => timer.milliseconds === 60000);
    assert.ok(retry);
    free = 11 * GiB - 1; await retry.callback();
    assert.equal((await query(socket, 'status')).paused, true);
    assert.equal(recorders[1].starts, undefined);
    free = 11 * GiB; await retry.callback();
    assert.equal(recorders[1].starts, 1);
    assert.equal((await query(socket, 'status')).paused, false);
    await query(socket, 'stop'); await waitUntil(() => !fs.existsSync(socket));
    await retry.callback();
    assert.equal(JSON.parse(fs.readFileSync(state)).enabled, false);
    assert.equal(recorders[1].starts, 1);
    host = harness(home, { Recorder: DiskRecorder });
    await waitUntil(() => fs.existsSync(socket));
    await host.intervals.find(timer => timer.milliseconds === 60000).callback();
    assert.equal((await query(socket, 'status')).enabled, false);
    assert.equal(recorders.length, 2);
  } finally {
    host?.proc.emit('SIGTERM');
    await waitUntil(() => !fs.existsSync(socket));
    fs.rmSync(home, { recursive: true, force: true });
  }
});
