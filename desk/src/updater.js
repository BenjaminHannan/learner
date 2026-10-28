'use strict';
// In-app updates for people Ben has sent the app to (Emma, Jacob...).
// Ben's release publishes dist/latest.json (version, per-platform zip url + sha256) next to the zips on GitHub (public repo, LFS).
// The app reads that file, and when its version is newer: downloads the zip, checks the sha256, unpacks it beside the running app,
// then a small detached script waits for the app to quit, swaps the folders (old one kept as a backup), signs it like
// dist/install-mac.sh does, and opens the new version. Chats, memory and settings live outside the app and are kept.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawn, execFile } = require('child_process');

const MANIFEST_URL = 'https://raw.githubusercontent.com/BenjaminHannan/learner/main/desk/dist/latest.json';
const CHECK_EVERY_MS = 6 * 3600 * 1000;

// "1.2.10" > "1.2.9"; anything that is not x.y.z counts as 0.0.0
function parseVersion(v) { const m = /^(\d+)\.(\d+)\.(\d+)/.exec(String(v || '').trim()); return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0]; }
function isNewer(remote, local) {
  const a = parseVersion(remote), b = parseVersion(local);
  for (let i = 0; i < 3; i++) { if (a[i] !== b[i]) return a[i] > b[i]; }
  return false;
}
// the zip for this computer, or null (Intel Macs and other platforms get no update)
function pickAsset(manifest, platform, arch) {
  if (!manifest || typeof manifest !== 'object') return null;
  const key = platform === 'darwin' && arch === 'arm64' ? 'mac' : platform === 'win32' && arch === 'x64' ? 'win' : null;
  const a = key && manifest[key];
  return a && /^https:\/\//.test(a.url || '') && /^[0-9a-f]{64}$/i.test(a.sha256 || '') ? a : null;
}

const shq = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'";
// The Mac swap. Runs detached after the app quits. If anything fails the old app is put back and opened.
function macScript({ pid, app, staged, backup }) {
  return [
    '#!/bin/bash',
    'PID=' + Number(pid) + '; APP=' + shq(app) + '; NEW=' + shq(staged) + '; BAK=' + shq(backup),
    'for i in $(seq 1 90); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done',
    'kill -9 "$PID" 2>/dev/null',
    'rm -rf "$BAK"; mkdir -p "$(dirname "$BAK")"',
    'mv "$APP" "$BAK" || { open "$APP"; exit 1; }',
    'if ! mv "$NEW" "$APP"; then mv "$BAK" "$APP"; open "$APP"; exit 1; fi',
    'xattr -cr "$APP"',
    'ID="$(/usr/libexec/PlistBuddy -c \'Print :CFBundleIdentifier\' "$APP/Contents/Info.plist" 2>/dev/null)"',
    // same signing as dist/install-mac.sh: seal it, then pin the signature to the bundle id so macOS keeps the permission grants
    'if ! codesign --force --deep -s - "$APP"; then rm -rf "$APP"; mv "$BAK" "$APP"; open "$APP"; exit 1; fi',
    '[ -n "$ID" ] && codesign --force -s - -r="designated => identifier \\"$ID\\"" "$APP"',
    'open "$APP"',
    ''
  ].join('\n');
}
// The Windows swap: wait for the app, copy the new files over the install folder, start it again.
function winScript({ pid, dir, staged, exe }) {
  return [
    '@echo off',
    'set PID=' + Number(pid),
    ':wait',
    'tasklist /FI "PID eq %PID%" 2>NUL | find "%PID%" >NUL',
    'if not errorlevel 1 (timeout /t 1 /nobreak >NUL & goto wait)',
    'robocopy "' + staged + '" "' + dir + '" /E /R:3 /W:2 /NFL /NDL /NJH /NJS >NUL',
    'start "" "' + path.join(dir, exe) + '"',
    ''
  ].join('\r\n');
}

class Updater {
  // o: { version, platform, arch, execPath, pid, tmp, fetch, onState, quit, spawn, execFile, packaged }
  constructor(o) {
    this.o = o;
    this.fetch = o.fetch || ((...a) => fetch(...a));
    this.state = { phase: 'idle', current: o.version, version: null, notes: '', pct: 0, error: '', checkedAt: 0 };
    this.manifest = null; this.timer = null; this.busy = false;
  }
  set(patch) { this.state = { ...this.state, ...patch }; try { this.o.onState && this.o.onState(this.state); } catch (e) { /* ignore */ } }
  // where the running app lives: Mac /Applications/Premonition.app, Windows the folder holding Premonition.exe
  location() {
    const ex = this.o.execPath;
    if (this.o.platform === 'darwin') { const i = ex.indexOf('.app/'); return i < 0 ? null : { app: ex.slice(0, i + 4), dir: path.dirname(ex.slice(0, i + 4)) }; }
    if (this.o.platform === 'win32') return { dir: path.dirname(ex), exe: path.basename(ex) };
    return null;
  }
  canInstall() {
    if (!this.o.packaged) return 'This copy is running from source, so it cannot update itself.';
    const loc = this.location();
    if (!loc) return 'This computer cannot update itself yet.';
    try { fs.accessSync(loc.dir, fs.constants.W_OK); } catch (e) { return "Premonition's folder is not writable for you. Move Premonition to your own Applications folder, then try again."; }
    return '';
  }
  async check() {
    if (this.busy) return this.state;
    this.busy = true; this.set({ phase: 'checking', error: '' });
    try {
      const r = await this.fetch(MANIFEST_URL, { headers: { 'cache-control': 'no-cache' }, signal: AbortSignal.timeout(15000) });
      if (!r.ok) throw new Error('The update list answered ' + r.status);
      const m = await r.json();
      this.manifest = m;
      const asset = pickAsset(m, this.o.platform, this.o.arch);
      if (asset && isNewer(m.version, this.o.version)) this.set({ phase: 'available', version: m.version, notes: String(m.notes || '').slice(0, 600), checkedAt: Date.now() });
      else this.set({ phase: 'idle', version: null, notes: '', checkedAt: Date.now() });
    } catch (e) {
      // a failed background check is not worth showing; the Settings button shows it
      this.set({ phase: 'idle', error: 'Could not check for updates (' + String(e && e.message || e).slice(0, 100) + ').', checkedAt: Date.now() });
    } finally { this.busy = false; }
    return this.state;
  }
  startTimer(firstMs) {
    this.stopTimer();
    const tick = () => { this.check().catch(() => {}); this.timer = setTimeout(tick, CHECK_EVERY_MS); };
    this.timer = setTimeout(tick, firstMs == null ? 20000 : firstMs);
    if (this.timer.unref) this.timer.unref();
  }
  stopTimer() { clearTimeout(this.timer); this.timer = null; }

  async download(asset, dest) {
    const r = await this.fetch(asset.url, { redirect: 'follow' });
    if (!r.ok || !r.body) throw new Error('The download answered ' + r.status);
    const total = Number(r.headers.get('content-length')) || asset.size || 0;
    const hash = crypto.createHash('sha256');
    const out = fs.createWriteStream(dest);
    let got = 0, last = 0;
    const reader = r.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      hash.update(value); got += value.length;
      if (!out.write(value)) await new Promise((res) => out.once('drain', res));
      if (total && Date.now() - last > 300) { last = Date.now(); this.set({ phase: 'downloading', pct: Math.min(99, Math.round(100 * got / total)) }); }
    }
    await new Promise((res, rej) => out.end((e) => (e ? rej(e) : res())));
    if (hash.digest('hex').toLowerCase() !== String(asset.sha256).toLowerCase()) throw new Error('The download was damaged (its checksum does not match). Try again.');
  }
  unzip(zip, dir) {
    return new Promise((resolve, reject) => {
      const run = this.o.execFile || execFile;
      const [cmd, args] = this.o.platform === 'darwin' ? ['/usr/bin/ditto', ['-x', '-k', zip, dir]] : ['tar', ['-xf', zip, '-C', dir]];
      run(cmd, args, { timeout: 300000 }, (e) => (e ? reject(new Error('The download could not be unpacked.')) : resolve()));
    });
  }
  // Windows zips hold a folder (Premonition-win32-x64) with Premonition.exe in it
  findRoot(dir, marker) {
    if (fs.existsSync(path.join(dir, marker))) return dir;
    for (const n of fs.readdirSync(dir)) { const p = path.join(dir, n); try { if (fs.statSync(p).isDirectory() && fs.existsSync(path.join(p, marker))) return p; } catch (e) { /* skip */ } }
    return null;
  }
  async install() {
    if (this.busy) return this.state;
    const why = this.canInstall();
    if (why) { this.set({ phase: 'error', error: why }); return this.state; }
    if (this.state.phase !== 'available' || !this.manifest) { this.set({ phase: 'error', error: 'There is no update to install.' }); return this.state; }
    const asset = pickAsset(this.manifest, this.o.platform, this.o.arch);
    const loc = this.location();
    this.busy = true; this.set({ phase: 'downloading', pct: 0, error: '' });
    const work = fs.mkdtempSync(path.join(this.o.tmp || os.tmpdir(), 'premonition-update-'));
    try {
      const zip = path.join(work, 'update.zip');
      await this.download(asset, zip);
      this.set({ phase: 'installing', pct: 100 });
      const mac = this.o.platform === 'darwin';
      // unpack inside the install folder on a Mac so the final move is a plain rename; anywhere in the temp folder on Windows
      const stage = mac ? fs.mkdtempSync(path.join(loc.dir, '.premonition-update-')) : path.join(work, 'new');
      fs.mkdirSync(stage, { recursive: true });
      await this.unzip(zip, stage);
      let script, file;
      if (mac) {
        const staged = path.join(stage, 'Premonition.app');
        if (!fs.existsSync(path.join(staged, 'Contents', 'MacOS'))) throw new Error('The download does not contain the app.');
        const backup = path.join(os.homedir(), 'Library', 'Application Support', 'Premonition', 'previous-version', 'Premonition.app');
        file = path.join(work, 'swap.sh'); script = macScript({ pid: this.o.pid, app: loc.app, staged, backup });
      } else {
        const root = this.findRoot(stage, loc.exe);
        if (!root) throw new Error('The download does not contain the app.');
        file = path.join(work, 'swap.cmd'); script = winScript({ pid: this.o.pid, dir: loc.dir, staged: root, exe: loc.exe });
      }
      fs.writeFileSync(file, script, { mode: 0o755 });
      this.set({ phase: 'restarting' });
      const sp = this.o.spawn || spawn;
      const child = mac ? sp('/bin/bash', [file], { detached: true, stdio: 'ignore' }) : sp('cmd.exe', ['/c', file], { detached: true, stdio: 'ignore', windowsHide: true });
      if (child && child.unref) child.unref();
      setTimeout(() => { try { this.o.quit && this.o.quit(); } catch (e) { /* ignore */ } }, 400);
    } catch (e) {
      try { fs.rmSync(work, { recursive: true, force: true }); } catch (e2) { /* ignore */ }
      this.set({ phase: 'available', pct: 0, error: String(e && e.message || e).slice(0, 200) });
    } finally { this.busy = false; }
    return this.state;
  }
}

module.exports = { Updater, parseVersion, isNewer, pickAsset, macScript, winScript, MANIFEST_URL, CHECK_EVERY_MS };
