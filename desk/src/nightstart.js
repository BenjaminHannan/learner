'use strict';
// Ben's Mac, Oct 29-30: Premonition was quit at 10:10 PM, the sleep window opened at 11 PM, and nothing was left to start the night's
// sleep. With auto-sleep on, a LaunchAgent opens Premonition in the background (hidden, --night) when the sleep window starts; if it is
// already running the agent does nothing (a plain `open` would bring its window up). Turning auto-sleep off removes the agent. Mac only;
// never for a test profile, a dev run, or a copy run from a disk image or a translocated download.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const LABEL = 'com.premonition.nightstart';
const NIGHT_ARG = '--night';
const LAUNCHCTL = '/bin/launchctl';
const MAX_TRIES = 3;   // launchd refusing the same file three times (Login Items switched off, a managed Mac): leave it until something changes

// /Applications/Premonition.app/Contents/MacOS/Premonition -> /Applications/Premonition.app ('' when it should not get an agent)
function bundleOf(execPath) {
  const m = /^(.*?\.app)\/Contents\/MacOS\/[^/]+$/.exec(String(execPath || ''));
  if (!m || m[1].includes('/AppTranslocation/') || m[1].startsWith('/Volumes/')) return '';
  return m[1];
}
function at(from) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(from || '').trim());
  if (!m) return null;
  const h = Number(m[1]), mi = Number(m[2]);
  return h < 24 && mi < 60 ? { h, mi } : null;
}
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const sq = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'";
// pgrep -x matches this user's process name exactly, so the Helper processes, the sh line itself and another account's copy never count as
// "running". macOS keeps only the first 16 characters of a process name, so a longer one could never match: no agent then.
function command(execPath, uid) {
  const bundle = bundleOf(execPath), name = path.basename(String(execPath || ''));
  if (!bundle || name.length > 15) return '';
  return '/usr/bin/pgrep -xq -U ' + Number(uid) + ' ' + sq(name) + ' || exec /usr/bin/open -g -j -a ' + sq(bundle) + ' --args ' + NIGHT_ARG;
}
// bundleId: shown as Premonition (not "sh") under Login Items > Allow in the Background on macOS 13+
function plist(execPath, from, uid, bundleId) {
  const t = at(from), cmd = command(execPath, uid);
  if (!cmd || !t) return '';
  const args = ['/bin/sh', '-c', cmd].map((a) => '<string>' + esc(a) + '</string>').join('');
  return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n' +
    '<plist version="1.0"><dict><key>Label</key><string>' + LABEL + '</string><key>ProgramArguments</key><array>' + args + '</array>' +
    (bundleId ? '<key>AssociatedBundleIdentifiers</key><string>' + esc(bundleId) + '</string>' : '') +
    '<key>StartCalendarInterval</key><dict><key>Hour</key><integer>' + t.h + '</integer><key>Minute</key><integer>' + t.mi + '</integer></dict></dict></plist>\n';
}

// Keeps ~/Library/LaunchAgents/<LABEL>.plist in step with the settings. Cheap to call every minute: it writes (and reloads launchd) only
// when the wanted file differs from what this process last put in place, and tries again next call when launchd refused it.
// Returns 'installed' | 'removed' | 'same' | 'skip' | 'failed'.
class NightStart {
  constructor(o) {
    this.o = {
      fs, uid: typeof process.getuid === 'function' ? process.getuid() : 501,
      run: (cmd, args) => { try { execFileSync(cmd, args, { stdio: 'ignore', timeout: 3000 }); return true; } catch (e) { return false; } },
      wait: (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms),
      ...o
    };
    this.file = path.join(this.o.home, 'Library', 'LaunchAgents', LABEL + '.plist');
    this.target = 'gui/' + this.o.uid;
    this.last = null;   // what is in place: the file's text while launchd has it loaded, '' = nothing, '?' = unknown (redo it)
    this.fails = 0; this.failedWant = null;
  }
  read() { try { return this.o.fs.readFileSync(this.file, 'utf8'); } catch (e) { return ''; } }
  loaded() { return this.o.run(LAUNCHCTL, ['print', this.target + '/' + LABEL]); }
  bundleId() {
    if (this.bid == null) {
      try { const m = /<key>CFBundleIdentifier<\/key>\s*<string>([^<]+)<\/string>/.exec(this.o.fs.readFileSync(path.join(bundleOf(this.o.execPath), 'Contents', 'Info.plist'), 'utf8')); this.bid = m ? m[1] : ''; } catch (e) { this.bid = ''; }
    }
    return this.bid;
  }
  // bootout returns before launchd has let go, and a bootstrap straight after it fails ("5: Input/output error"): wait until it is gone
  unload() {
    if (!this.o.run(LAUNCHCTL, ['bootout', this.target + '/' + LABEL])) return;
    for (let i = 0; i < 20 && this.loaded(); i++) this.o.wait(100);
  }
  sync({ on, from }) {
    const want = on ? plist(this.o.execPath, from, this.o.uid, this.bundleId()) : '';
    if (on && !want) return 'skip';   // not inside an installed .app (a dev run, a disk image) or no usable window start
    if (this.last === null) {         // first call in this process: what is on disk only counts if launchd agrees
      const disk = this.read(), up = this.loaded();
      this.last = disk && up ? disk : !disk && !up ? '' : '?';
    }
    if (want === this.last) return 'same';
    if (want === this.failedWant && this.fails >= MAX_TRIES) return 'failed';
    try {
      if (this.last !== '') this.unload();
      if (!want) { this.o.fs.rmSync(this.file, { force: true }); this.last = ''; return 'removed'; }
      this.o.fs.mkdirSync(path.dirname(this.file), { recursive: true });
      this.o.fs.writeFileSync(this.file, want);
      if (!this.o.run(LAUNCHCTL, ['bootstrap', this.target, this.file])) throw new Error('bootstrap');
      this.last = want; this.fails = 0;
      return 'installed';
    } catch (e) {
      this.last = '?';
      if (want !== this.failedWant) { this.failedWant = want; this.fails = 0; }
      this.fails++;
      return 'failed';
    }
  }
}

module.exports = { NightStart, plist, command, bundleOf, LABEL, NIGHT_ARG };
