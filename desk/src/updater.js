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
// The Radeon/Nanbeige Windows build (Nov 4) has its OWN list and key, so it can never be "updated" back to the LFM3 Windows zip
// that latest.json's "win" entry points at (1.2.4 and older). Ben publishes it next to latest.json (docs/win-amd/REPORT.md).
const WINAMD_MANIFEST_URL = 'https://raw.githubusercontent.com/BenjaminHannan/learner/main/desk/dist/latest-winamd.json';
// The built-in Mac (Nanbeige, Nov 5 "uncle" build) likewise: latest-macnb.json, key "macnb", never the LFM3/Ben "mac" entry.
const MACNB_MANIFEST_URL = 'https://raw.githubusercontent.com/BenjaminHannan/learner/main/desk/dist/latest-macnb.json';
const CHECK_EVERY_MS = 5 * 60 * 1000;   // Ben Oct 29: "make it so that it checks every five minutes"

// "1.2.10" > "1.2.9"; anything that is not x.y.z counts as 0.0.0
function parseVersion(v) { const m = /^(\d+)\.(\d+)\.(\d+)/.exec(String(v || '').trim()); return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0]; }
function isNewer(remote, local) {
  const a = parseVersion(remote), b = parseVersion(local);
  for (let i = 0; i < 3; i++) { if (a[i] !== b[i]) return a[i] > b[i]; }
  return false;
}
// the zip for this computer, or null (Intel Macs and other platforms get no update)
// o.key overrides the entry name ('winamd'); o.allowLoopback lets a local test list (PREMONITION_UPDATE_MANIFEST) serve http://127.0.0.1
function pickAsset(manifest, platform, arch, o) {
  o = o || {};
  if (!manifest || typeof manifest !== 'object') return null;
  const key = platform === 'darwin' && arch === 'arm64' ? (o.key || 'mac') : platform === 'win32' && arch === 'x64' ? (o.key || 'win') : null;
  const a = key && manifest[key];
  const okUrl = /^https:\/\//.test(a && a.url || '') || (o.allowLoopback && /^http:\/\/(127\.0\.0\.1|localhost)[:/]/.test(a && a.url || ''));
  return a && okUrl && /^[0-9a-f]{64}$/i.test(a.sha256 || '') ? a : null;
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
// args: only --user-data-dir=... is passed on to the new copy (so a test install keeps its own data folder)
function winScript({ pid, dir, staged, exe, args }) {
  const keep = (args || []).filter((a) => /^--user-data-dir=[^"%&|<>^]+$/.test(String(a))).map((a) => ' "' + a + '"').join('');
  return [
    '@echo off',
    'set PID=' + Number(pid),
    // no pipes and no `timeout`: started hidden with no console, `tasklist | find` never ended and `timeout` fails at once (BensPC, Nov 4)
    'set N=0',
    ':wait',
    'set /a N+=1',
    'if %N% GTR 120 goto go',
    'tasklist /FI "PID eq %PID%" /NH /FO CSV > "%~dp0alive.txt" 2>NUL',
    'findstr /C:"\"%PID%\"" "%~dp0alive.txt" >NUL 2>NUL',
    'if not errorlevel 1 (ping -n 2 127.0.0.1 >NUL & goto wait)',
    ':go',
    'robocopy "' + staged + '" "' + dir + '" /E /R:3 /W:2 /NFL /NDL /NJH /NJS >NUL',
    'start "" "' + path.join(dir, exe) + '"' + keep,
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
    this.url = o.manifestUrl || MANIFEST_URL;
    this.pick = { key: o.assetKey, allowLoopback: !!o.allowLoopback };
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
    const was = this.state.phase;   // every 5 minutes: an update already on offer stays on screen while it checks again
    this.busy = true; if (was !== 'available') this.set({ phase: 'checking', error: '' });
    try {
      const r = await this.fetch(this.url, { headers: { 'cache-control': 'no-cache' }, signal: AbortSignal.timeout(15000) });
      if (!r.ok) throw new Error('The update list answered ' + r.status);
      const m = await r.json();
      this.manifest = m;
      const asset = pickAsset(m, this.o.platform, this.o.arch, this.pick);
      if (asset && isNewer(m.version, this.o.version) && this.o.autoInstall) { this.set({ phase: 'available', version: m.version, notes: '', checkedAt: Date.now() }); this.busy = false; return await this.install(); }
      if (asset && isNewer(m.version, this.o.version)) this.set({ phase: 'available', version: m.version, notes: String(m.notes || '').slice(0, 600), checkedAt: Date.now() });
      else this.set({ phase: 'idle', version: null, notes: '', checkedAt: Date.now() });
    } catch (e) {
      // a failed background check is not worth showing; the Settings button shows it. An update already on offer stays.
      if (was === 'available' && this.manifest) return this.state;
      this.set({ phase: 'idle', error: 'Could not check for updates (' + String(e && e.message || e).slice(0, 100) + ').', checkedAt: Date.now() });
    } finally { this.busy = false; }
    return this.state;
  }
  // a finished update leaves its download (~275 MB) in the temp folder: remove ones older than 10 minutes
  cleanOld(now) {
    const tmp = this.o.tmp || os.tmpdir(); now = now || Date.now();
    let n = 0;
    try {
      for (const d of fs.readdirSync(tmp)) {
        if (!d.startsWith('premonition-update-')) continue;
        const p = path.join(tmp, d);
        try { if (now - fs.statSync(p).mtimeMs > 10 * 60 * 1000) { fs.rmSync(p, { recursive: true, force: true }); n++; } } catch (e) { /* in use */ }
      }
    } catch (e) { /* no temp folder */ }
    return n;
  }
  startTimer(firstMs) {
    this.stopTimer();
    try { this.cleanOld(); } catch (e) { /* ignore */ }
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
    // a write error (disk full) with no listener would crash the app; a dropped connection must not leave the file open
    let outErr = null;
    out.on('error', (e) => { outErr = e; });
    let got = 0, last = 0;
    const reader = r.body.getReader();
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        if (outErr) throw outErr;
        hash.update(value); got += value.length;
        if (!out.write(value)) await new Promise((res) => { const go = () => { out.off('drain', go); out.off('error', go); res(); }; out.on('drain', go); out.on('error', go); });
        if (total && Date.now() - last > 300) { last = Date.now(); this.set({ phase: 'downloading', pct: Math.min(99, Math.round(100 * got / total)) }); }
      }
      if (outErr) throw outErr;
      await new Promise((res, rej) => out.end((e) => (e ? rej(e) : res())));
      if (outErr) throw outErr;
    } catch (e) { out.destroy(); throw e; }
    if (hash.digest('hex').toLowerCase() !== String(asset.sha256).toLowerCase()) throw new Error('The download was damaged (its checksum does not match). Try again.');
  }
  unzip(zip, dir) {
    return new Promise((resolve, reject) => {
      const run = this.o.execFile || execFile;
      // Windows: the system tar by full path (a Git/MSYS tar first on PATH cannot read zips, and a planted tar.exe must not run)
      const [cmd, args] = this.o.platform === 'darwin' ? ['/usr/bin/ditto', ['-x', '-k', zip, dir]] : [require('./runtime/install').tarExe('win32'), ['-xf', zip, '-C', dir]];
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
    const asset = pickAsset(this.manifest, this.o.platform, this.o.arch, this.pick);
    const loc = this.location();
    this.busy = true; this.set({ phase: 'downloading', pct: 0, error: '' });
    const work = fs.mkdtempSync(path.join(this.o.tmp || os.tmpdir(), 'premonition-update-'));
    let stage = null;
    try {
      const zip = path.join(work, 'update.zip');
      await this.download(asset, zip);
      this.set({ phase: 'installing', pct: 100 });
      const mac = this.o.platform === 'darwin';
      // unpack inside the install folder on a Mac so the final move is a plain rename; anywhere in the temp folder on Windows
      stage = mac ? fs.mkdtempSync(path.join(loc.dir, '.premonition-update-')) : path.join(work, 'new');
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
        file = path.join(work, 'swap.cmd'); script = winScript({ pid: this.o.pid, dir: loc.dir, staged: root, exe: loc.exe, args: this.o.args });
      }
      fs.writeFileSync(file, script, { mode: 0o755 });
      this.set({ phase: 'restarting' });
      const sp = this.o.spawn || spawn;
      const child = mac ? sp('/bin/bash', [file], { detached: true, stdio: 'ignore' }) : sp('cmd.exe', ['/c', file], { detached: true, stdio: 'ignore', windowsHide: true });
      if (child && child.unref) child.unref();
      setTimeout(() => { try { this.o.quit && this.o.quit(); } catch (e) { /* ignore */ } }, 400);
    } catch (e) {
      try { fs.rmSync(work, { recursive: true, force: true }); } catch (e2) { /* ignore */ }
      if (stage && !stage.startsWith(work)) { try { fs.rmSync(stage, { recursive: true, force: true }); } catch (e2) { /* ignore */ } }   // the Mac stage sits in /Applications: no half-unpacked copy left there
      this.set({ phase: 'available', pct: 0, error: String(e && e.message || e).slice(0, 200) });
    } finally { this.busy = false; }
    return this.state;
  }
}

module.exports = { Updater, parseVersion, isNewer, pickAsset, macScript, winScript, MANIFEST_URL, WINAMD_MANIFEST_URL, MACNB_MANIFEST_URL, CHECK_EVERY_MS };
