'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { Updater, isNewer, pickAsset, macScript, winScript } = require('../src/updater');

const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');

test('isNewer compares x.y.z numerically', () => {
  assert.ok(isNewer('1.0.10', '1.0.9')); assert.ok(isNewer('1.1.0', '1.0.99')); assert.ok(isNewer('2.0.0', '1.9.9'));
  assert.ok(!isNewer('1.0.0', '1.0.0')); assert.ok(!isNewer('1.0.1', '1.0.2')); assert.ok(!isNewer('junk', '1.0.0'));
});

test('pickAsset: Apple-chip Mac and 64-bit Windows get a zip; others and bad entries get none', () => {
  const good = { url: 'https://github.com/x/y.zip', sha256: 'a'.repeat(64) };
  const m = { mac: good, win: good };
  assert.strictEqual(pickAsset(m, 'darwin', 'arm64'), good);
  assert.strictEqual(pickAsset(m, 'win32', 'x64'), good);
  assert.strictEqual(pickAsset(m, 'darwin', 'x64'), null);
  assert.strictEqual(pickAsset(m, 'linux', 'x64'), null);
  assert.strictEqual(pickAsset({ mac: { url: 'http://insecure/x.zip', sha256: 'a'.repeat(64) } }, 'darwin', 'arm64'), null);
  assert.strictEqual(pickAsset({ mac: { url: good.url, sha256: 'short' } }, 'darwin', 'arm64'), null);
  assert.strictEqual(pickAsset(null, 'darwin', 'arm64'), null);
});

test('swap scripts wait for the app, keep a backup, sign like install-mac.sh, and put the old app back on failure', () => {
  const s = macScript({ pid: 123, app: "/Applications/Premonition.app", staged: "/Applications/.u/Premonition.app", backup: '/b/Premonition.app' });
  assert.match(s, /kill -0 "\$PID"/); assert.match(s, /mv "\$APP" "\$BAK"/); assert.match(s, /mv "\$BAK" "\$APP"/);
  assert.match(s, /xattr -cr/); assert.match(s, /codesign --force --deep -s -/); assert.match(s, /designated => identifier/); assert.match(s, /open "\$APP"/);
  assert.ok(!/123;.*rm -rf \//.test(s));
  const w = winScript({ pid: 9, dir: 'C:\\Premonition', staged: 'C:\\t\\new', exe: 'Premonition.exe' });
  assert.match(w, /tasklist/); assert.match(w, /robocopy "C:\\t\\new" "C:\\Premonition"/); assert.match(w, /start "" "C:\\Premonition[\\/]Premonition\.exe"/);
});

function fakeFetch(manifest, zip) {
  return async (url) => {
    if (/latest\.json/.test(url)) return new Response(JSON.stringify(manifest), { status: 200 });
    return new Response(zip, { status: 200, headers: { 'content-length': String(zip.length) } });
  };
}

test('check: offers only a newer version that has a zip for this computer', async () => {
  const zip = Buffer.from('zipbytes');
  const m = { version: '1.2.0', notes: 'Faster voice.', mac: { url: 'https://example.com/m.zip', sha256: sha(zip) } };
  const states = [];
  const u = new Updater({ version: '1.1.0', platform: 'darwin', arch: 'arm64', execPath: '/x/Premonition.app/Contents/MacOS/Premonition', pid: 1, packaged: true, fetch: fakeFetch(m, zip), onState: (s) => states.push(s.phase) });
  const st = await u.check();
  assert.strictEqual(st.phase, 'available'); assert.strictEqual(st.version, '1.2.0'); assert.strictEqual(st.notes, 'Faster voice.');
  const same = new Updater({ version: '1.2.0', platform: 'darwin', arch: 'arm64', execPath: '/x', pid: 1, packaged: true, fetch: fakeFetch(m, zip) });
  assert.strictEqual((await same.check()).phase, 'idle');
  const intel = new Updater({ version: '1.1.0', platform: 'darwin', arch: 'x64', execPath: '/x', pid: 1, packaged: true, fetch: fakeFetch(m, zip) });
  assert.strictEqual((await intel.check()).phase, 'idle');
  const down = new Updater({ version: '1.1.0', platform: 'darwin', arch: 'arm64', execPath: '/x', pid: 1, packaged: true, fetch: async () => { throw new Error('offline'); } });
  const ds = await down.check(); assert.strictEqual(ds.phase, 'idle'); assert.match(ds.error, /Could not check/);
});

test('install (Mac): downloads, verifies the checksum, unpacks beside the app, starts the swap script, quits', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'upd-'));
  const appDir = path.join(root, 'Applications'); const exec = path.join(appDir, 'Premonition.app', 'Contents', 'MacOS', 'Premonition');
  fs.mkdirSync(path.dirname(exec), { recursive: true }); fs.writeFileSync(exec, 'old');
  const zip = Buffer.from('pretend zip');
  const m = { version: '1.2.0', mac: { url: 'https://example.com/m.zip', sha256: sha(zip) } };
  let spawned = null, quit = 0;
  const mk = (extra) => new Updater({ version: '1.1.0', platform: 'darwin', arch: 'arm64', execPath: exec, pid: 4242, packaged: true, tmp: root,
    fetch: fakeFetch(m, zip), quit: () => { quit++; },
    execFile: (cmd, args, o, cb) => { fs.mkdirSync(path.join(args[3], 'Premonition.app', 'Contents', 'MacOS'), { recursive: true }); cb(null); },
    spawn: (cmd, args) => { spawned = { cmd, args, script: fs.readFileSync(args[0], 'utf8') }; return { unref() {} }; }, ...extra });
  const u = mk(); await u.check();
  await u.install();
  assert.ok(spawned, 'the swap script was started'); assert.strictEqual(spawned.cmd, '/bin/bash');
  assert.match(spawned.script, /PID=4242/); assert.ok(spawned.script.includes(path.join(appDir, 'Premonition.app')));
  await new Promise((r) => setTimeout(r, 600)); assert.strictEqual(quit, 1);
  // a damaged download is refused and nothing starts
  spawned = null; quit = 0;
  const bad = mk({ fetch: fakeFetch({ ...m, mac: { ...m.mac, sha256: 'b'.repeat(64) } }, zip) });
  bad.manifest = { ...m, mac: { ...m.mac, sha256: 'b'.repeat(64) } }; bad.state.phase = 'available';
  const r = await bad.install();
  assert.strictEqual(r.phase, 'available'); assert.match(r.error, /damaged/); assert.strictEqual(spawned, null);
});

test('install refuses when running from source or when the folder is not writable', async () => {
  const u = new Updater({ version: '1.0.0', platform: 'darwin', arch: 'arm64', execPath: '/x/Premonition.app/Contents/MacOS/P', pid: 1, packaged: false });
  assert.match(u.canInstall(), /from source/);
  if (process.getuid && process.getuid() === 0) return; // root can write anywhere
  const ro = fs.mkdtempSync(path.join(os.tmpdir(), 'ro-')); fs.chmodSync(ro, 0o555);
  const u2 = new Updater({ version: '1.0.0', platform: 'darwin', arch: 'arm64', execPath: path.join(ro, 'Premonition.app/Contents/MacOS/P'), pid: 1, packaged: true });
  assert.match(u2.canInstall(), /not writable/);
});
