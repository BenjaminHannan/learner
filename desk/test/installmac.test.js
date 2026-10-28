'use strict';
// dist/install-mac.sh, run for real with stand-ins for the macOS tools (ditto, xattr, codesign, open, osascript, sysctl, uname, pgrep)
// placed first on PATH, a small fake Premonition.app zip, and file:// as the download address. Skipped when bash, zip or unzip is missing.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync, execFileSync } = require('child_process');

const SCRIPT = path.join(__dirname, '..', 'dist', 'install-mac.sh');
const have = (c) => spawnSync('sh', ['-c', 'command -v ' + c]).status === 0;
const can = have('bash') && have('zip') && have('unzip');
const tmp = (n) => fs.mkdtempSync(path.join(os.tmpdir(), n));

// bin/ holds the stand-in tools; every call is appended to calls.log
function shims(dir, o) {
  o = o || {};
  const bin = path.join(dir, 'bin'); fs.mkdirSync(bin, { recursive: true });
  const w = (name, body) => { fs.writeFileSync(path.join(bin, name), '#!/bin/sh\n' + body + '\n', { mode: 0o755 }); };
  const log = path.join(dir, 'calls.log');
  w('uname', o.nonMac ? 'echo Linux' : (o.noArgs ? 'echo Darwin' : 'case "$1" in -s) echo Darwin;; -m) echo arm64;; *) echo Darwin;; esac'));
  w('sysctl', o.intel ? 'echo 0' : 'echo 1');
  w('pgrep', o.running ? 'exit 0' : 'exit 1');
  w('pkill', 'echo "pkill $*" >> "' + log + '"');
  w('osascript', 'echo "osascript $*" >> "' + log + '"');
  w('ditto', 'echo "ditto $*" >> "' + log + '"; [ "$1 $2" = "-x -k" ] || exit 9; ' + (o.badDitto ? 'exit 1' : 'unzip -q "$3" -d "$4"'));
  w('xattr', 'echo "xattr $*" >> "' + log + '"');
  w('codesign', 'echo "codesign $*" >> "' + log + '"; ' + (o.badSign ? 'exit 1' : 'exit 0'));
  w('open', 'echo "open $*" >> "' + log + '"');
  return { bin, log };
}
function fakeZip(dir, o) {
  o = o || {};
  const src = path.join(dir, 'zsrc'); const app = path.join(src, 'Premonition.app', 'Contents', 'MacOS'); fs.mkdirSync(app, { recursive: true });
  fs.writeFileSync(path.join(app, 'Premonition'), '#!/bin/sh\n', { mode: 0o755 });
  fs.mkdirSync(path.join(src, 'Premonition.app', 'Contents', 'Frameworks', 'F.framework', 'Versions', 'A'), { recursive: true });
  fs.symlinkSync('A', path.join(src, 'Premonition.app', 'Contents', 'Frameworks', 'F.framework', 'Versions', 'Current'));
  fs.writeFileSync(path.join(src, 'Premonition.app', 'Contents', 'big.bin'), require('crypto').randomBytes(o.small ? 10 : 1100000));
  if (o.wrongName) fs.renameSync(path.join(src, 'Premonition.app'), path.join(src, 'Other.app'));
  const z = path.join(dir, 'Premonition-mac-arm64.zip');
  execFileSync('zip', ['-qry', z, o.wrongName ? 'Other.app' : 'Premonition.app'], { cwd: src });
  return z;
}
function run(dir, sh, env) {
  const r = spawnSync('bash', [SCRIPT], { env: { PATH: sh.bin + ':' + process.env.PATH, HOME: path.join(dir, 'home'), TMPDIR: dir, ...env }, encoding: 'utf8', input: '' });
  return { ...r, calls: fs.existsSync(sh.log) ? fs.readFileSync(sh.log, 'utf8').trim().split('\n') : [] };
}

test('install-mac.sh is valid bash and starts with a shebang', { skip: !have('bash') }, () => {
  assert.strictEqual(spawnSync('bash', ['-n', SCRIPT]).status, 0);
  assert.match(fs.readFileSync(SCRIPT, 'utf8'), /^#!\/bin\/bash\n/);
});

test('install-mac.sh: downloads, unpacks (symlinks kept), clears flags, signs, opens; running it again replaces the app', { skip: !can }, () => {
  const d = tmp('inst-'); const sh = shims(d); const z = fakeZip(d); const dest = path.join(d, 'Applications');
  const env = { INSTALL_DIR: dest, ZIP_URL: 'file://' + z };
  let r = run(d, sh, env);
  assert.strictEqual(r.status, 0, r.stderr + r.stdout);
  assert.ok(fs.existsSync(path.join(dest, 'Premonition.app', 'Contents', 'MacOS', 'Premonition')));
  assert.ok(fs.lstatSync(path.join(dest, 'Premonition.app', 'Contents', 'Frameworks', 'F.framework', 'Versions', 'Current')).isSymbolicLink());
  const app = path.join(dest, 'Premonition.app');
  assert.ok(r.calls.includes('xattr -cr ' + app), r.calls.join('\n')); assert.ok(r.calls.includes('codesign --force --deep -s - ' + app)); assert.ok(r.calls.includes('open -a ' + app));
  assert.ok(r.calls.findIndex((c) => c.startsWith('xattr')) < r.calls.findIndex((c) => c.startsWith('codesign')) && r.calls.findIndex((c) => c.startsWith('codesign')) < r.calls.findIndex((c) => c.startsWith('open')), 'order: xattr, codesign, open');
  assert.match(r.stdout, /\[1\/4\] Downloading/); assert.match(r.stdout, /\[4\/4\] Opening Premonition/); assert.match(r.stdout, /about 1 GB/);
  assert.deepStrictEqual(fs.readdirSync(dest), ['Premonition.app'], 'no staging folder left behind');
  assert.deepStrictEqual(fs.readdirSync(d).filter((n) => n.startsWith('premonition-install')), [], 'the temporary download folder is removed');
  // idempotent: an older copy (with a leftover file) is replaced, not merged
  fs.writeFileSync(path.join(app, 'stale.txt'), 'old');
  r = run(d, sh, env);
  assert.strictEqual(r.status, 0, r.stderr); assert.ok(!fs.existsSync(path.join(app, 'stale.txt')));
});

test('install-mac.sh: closes a running Premonition first', { skip: !can }, () => {
  const d = tmp('inst-run-'); const sh = shims(d, { running: true }); const z = fakeZip(d);
  const r = run(d, sh, { INSTALL_DIR: path.join(d, 'A'), ZIP_URL: 'file://' + z, NO_OPEN: '1' });
  assert.strictEqual(r.status, 0, r.stderr); assert.ok(r.calls.some((c) => c.startsWith('osascript') && /quit/.test(c)));
  assert.ok(!r.calls.some((c) => c.startsWith('open ')), 'NO_OPEN');
});

test('install-mac.sh: falls back to ~/Applications when /Applications is not writable (no sudo)', { skip: !can || (fs.existsSync('/Applications') && (() => { try { fs.accessSync('/Applications', fs.constants.W_OK); return true; } catch (e) { return false; } })()) }, () => {
  const d = tmp('inst-fb-'); const sh = shims(d); const z = fakeZip(d);
  const r = run(d, sh, { ZIP_URL: 'file://' + z, NO_OPEN: '1' });
  assert.strictEqual(r.status, 0, r.stderr + r.stdout);
  assert.ok(fs.existsSync(path.join(d, 'home', 'Applications', 'Premonition.app')));
  assert.match(r.stdout, /own Applications folder/);
  assert.ok(!/\bsudo\b/.test(fs.readFileSync(SCRIPT, 'utf8').replace(/#.*$/gm, '').replace(/"[^"]*"/g, '""')), 'the script never calls sudo');
});

test('install-mac.sh: plain-English failures (not a Mac, Intel Mac, bad download, tiny file, bad zip, wrong app, signing)', { skip: !can }, () => {
  const d = tmp('inst-bad-'); const z = fakeZip(d); const dest = path.join(d, 'A');
  const base = { INSTALL_DIR: dest, ZIP_URL: 'file://' + z, NO_OPEN: '1' };
  let r = run(d, shims(d, { nonMac: true }), base); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /Something went wrong: this installer is for Macs/);
  r = run(d, shims(d, { intel: true }), base); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /Intel chip/);
  r = run(d, shims(d), { ...base, ZIP_URL: 'file://' + path.join(d, 'missing.zip') }); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /the download did not work/);
  const small = fakeZip(tmp('inst-small-'), { small: true });
  r = run(d, shims(d), { ...base, ZIP_URL: 'file://' + small }); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /is not the app|only \d+ bytes/);
  r = run(d, shims(d, { badDitto: true }), base); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /could not be unpacked/);
  const wrong = fakeZip(tmp('inst-wrong-'), { wrongName: true });
  r = run(d, shims(d), { ...base, ZIP_URL: 'file://' + wrong }); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /does not contain Premonition\.app/);
  r = run(d, shims(d, { badSign: true }), base); assert.notStrictEqual(r.status, 0); assert.match(r.stderr, /could not sign the app/); assert.match(r.stderr, /paste the same line/);
});

test('install-mac.sh DRY_RUN=1: prints the steps, changes nothing, downloads nothing', { skip: !have('bash') }, () => {
  const d = tmp('inst-dry-'); const sh = shims(d); const dest = path.join(d, 'Applications');
  const r = run(d, sh, { DRY_RUN: '1', INSTALL_DIR: dest, ZIP_URL: 'file://' + path.join(d, 'none.zip') });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.stdout, /\(dry run\) curl -fL/); assert.match(r.stdout, /\(dry run\) ditto -x -k/); assert.match(r.stdout, /\(dry run\) xattr -cr /); assert.match(r.stdout, /\(dry run\) codesign --force --deep -s - /); assert.match(r.stdout, /\(dry run\) open -a /);
  assert.strictEqual(fs.existsSync(dest), false); assert.deepStrictEqual(r.calls, []);
});

test('install-mac.sh also works the way it is really used: the script piped into bash (curl | bash)', { skip: !can }, () => {
  const d = tmp('inst-pipe-'); const sh = shims(d); const z = fakeZip(d); const dest = path.join(d, 'Applications');
  const r = spawnSync('bash', [], { env: { PATH: sh.bin + ':' + process.env.PATH, HOME: path.join(d, 'home'), TMPDIR: d, INSTALL_DIR: dest, ZIP_URL: 'file://' + z }, encoding: 'utf8', input: fs.readFileSync(SCRIPT, 'utf8') });
  assert.strictEqual(r.status, 0, r.stderr + r.stdout);
  assert.ok(fs.existsSync(path.join(dest, 'Premonition.app', 'Contents', 'MacOS', 'Premonition'))); assert.match(r.stdout, /Done\. Premonition is in /);
});
