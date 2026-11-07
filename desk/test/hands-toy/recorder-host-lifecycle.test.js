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

function harness(home) {
  const app = new EventEmitter(), proc = new EventEmitter();
  app.whenReady = async () => {}; app.dock = { hide() {} }; app.commandLine = { appendSwitch() {} }; app.quit = () => app.emit('will-quit');
  app.exit = () => app.emit('will-quit'); app.setLoginItemSettings = () => {};
  proc.pid = process.pid; proc.env = process.env; proc.execPath = process.execPath; proc.kill = process.kill.bind(process);
  class FakeRecorder {
    constructor({ fake }) { this.fake = fake; this.enabled = false; }
    async on() { this.enabled = true; }
    async off() { this.enabled = false; }
    event() {}
    status() { return { enabled: this.enabled, paused: false }; }
  }
  const module = { exports: {} };
  const fakeRequire = name => name === 'electron' ? { app, systemPreferences: {} }
    : name === 'node:os' ? { homedir: () => home }
    : name === './recorder' ? { Recorder: FakeRecorder } : require(name);
  vm.runInNewContext(source, { module, require: fakeRequire, process: proc, console, setTimeout, clearTimeout, setInterval, clearInterval });
  module.exports.run();
  return { app, proc };
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
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'hands-host-test-'));
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
