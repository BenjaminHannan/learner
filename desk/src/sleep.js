'use strict';
// Sleep mode bridge (no Electron). The sleep app is a separate stdlib-Python program (~/learner-ops/sleepmode/app) that
// trains on the diary while Glim is idle. We only start it, wake it and read the files it leaves in its home dir:
//   status.json (mode, since, hours_slept, last_quiz, last_checkin, pid, needs_permission), events.jsonl, inbox.md,
//   summary.md, a SLEEPING marker while it runs, and a WAKE file that asks it to stop.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, execFileSync } = require('child_process');

const tilde = (p) => String(p || '').replace(/^~(?=$|[\\/])/, os.homedir());
const homeDir = (env) => tilde((env || process.env).SLEEPMODE_HOME) || path.join(os.homedir(), 'learner-ops', 'sleepmode');
const isDir = (p) => { try { return fs.statSync(p).isDirectory(); } catch (e) { return false; } };
const isFile = (p) => { try { return fs.statSync(p).isFile(); } catch (e) { return false; } };

function appDir(settings, home) {
  const s = tilde(settings && settings.sleepApp).trim();
  return s || path.join(home, 'app');
}
// first existing of the usual interpreters. On a Mac there is no bare 'python3' fallback (that would be Apple's stub, without the
// sleep app's needs): returns '' so Settings can say "Set the Sleep Python path". Elsewhere 'python3' is the last resort.
function findPython(settings, home, exists, platform) {
  exists = exists || isFile;
  const s = tilde(settings && settings.sleepPython).trim();
  if (s) return s;
  const ops = path.dirname(home);
  const cands = [path.join(home, 'venv312', 'bin', 'python'), path.join(ops, 'speedbench', 'venv312', 'bin', 'python'), path.join(ops, '.venv', 'bin', 'python'), '/opt/homebrew/bin/python3'];
  return cands.find((c) => exists(c)) || ((platform || process.platform) === 'darwin' ? '' : 'python3');
}
const PY_MISSING = 'No Python was found for the sleep app. Set the Sleep Python path in Settings > Sleep.';
function pidAlive(pid) {
  if (!(pid > 0)) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return null; } };
const readText = (f) => { try { return fs.readFileSync(f, 'utf8'); } catch (e) { return ''; } };

class Sleep {
  /**
   * getSettings() -> settings; home: sleepmode state dir; onEvent(ev) for each new events.jsonl line ({kind, ...}) and
   * inbox lines ({kind:'inbox', line}); spawnFn / pythonExists: test seams.
   */
  constructor(o) {
    this.o = o || {};
    this.getSettings = this.o.getSettings || (() => ({}));
    this.home = this.o.home || homeDir(this.o.env);
    this.spawn = this.o.spawn || spawn;
    this.timer = null;
    this.evOffset = null;
    this.inboxSeen = null;
    this.child = null;
    this.lastError = '';
    this.p = { status: path.join(this.home, 'status.json'), events: path.join(this.home, 'events.jsonl'), inbox: path.join(this.home, 'inbox.md'), summary: path.join(this.home, 'summary.md'), sleeping: path.join(this.home, 'SLEEPING'), wake: path.join(this.home, 'WAKE'), log: path.join(this.home, 'desk-sleep.log') };
  }
  app() { return appDir(this.getSettings(), this.home); }
  python() { return findPython(this.getSettings(), this.home, this.o.pythonExists, this.o.platform); }
  // {ok, app, python, reason}: the sleep app has to be there to be started
  available() {
    const app = this.app(), python = this.python();
    if (!isDir(app)) return { ok: false, app, python, reason: 'The sleep app was not found at ' + app + '. Set its folder in Settings > Sleep.' };
    if (!python) return { ok: false, app, python, reason: PY_MISSING };
    return { ok: true, app, python, reason: '' };
  }
  // SLEEPMLX_NIGHT_BUDGET_S: how long this sleep may last (about 85% of the chosen time); the trainer scales its work to it.
  // The sleepmode app's CommandWorker starts the trainer with dict(os.environ) + its own vars, so it inherits this
  // (checked in sleepmode/workers.py on origin/claude/project-thread-sl2x88).
  _env() { return { ...process.env, ...(this.o.env || {}), PYTHONPATH: this.app() + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : ''), SLEEPMODE_HOME: this.home, ...(this.nightBudgetS > 0 ? { SLEEPMLX_NIGHT_BUDGET_S: String(Math.round(this.nightBudgetS)) } : {}) }; }

  // Start sleeping: a detached process with its output in a log file. It outlives Desk.
  start(o) {
    this.nightBudgetS = (o && o.budgetS) || 0; this.wakeAtMs = (o && o.wakeAt) || null;
    const a = this.available();
    if (!a.ok) return { ok: false, error: a.reason };
    if (this.status().sleeping) return { ok: false, error: 'Already sleeping.' };
    try {
      fs.mkdirSync(this.home, { recursive: true });
      try { fs.unlinkSync(this.p.wake); } catch (e) { /* none */ }
      const fd = fs.openSync(this.p.log, 'a');
      const c = this.spawn(a.python, ['-m', 'sleepmode', 'start'], { cwd: a.app, env: this._env(), detached: true, stdio: ['ignore', fd, fd] });
      try { fs.closeSync(fd); } catch (e) { /* ignore */ }
      this.child = c; this.exit = null; this.lastError = '';
      c.on('error', (e) => { this.lastError = String(e && e.message || e); this.exit = { error: this.lastError }; });
      c.on('exit', (code) => { this.exit = { code }; });
      if (c.unref) c.unref();
      this.evOffset = this._size(this.p.events); // only events from now on
      return { ok: true, pid: c.pid };
    } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
  }
  // Ask it to stop: `-m sleepmode wake`, falling back to touching WAKE. Resolves {ok, via}.
  wake(timeoutMs) {
    const a = this.available();
    const touch = () => { try { fs.mkdirSync(this.home, { recursive: true }); fs.writeFileSync(this.p.wake, new Date().toISOString()); return { ok: true, via: 'file' }; } catch (e) { return { ok: false, error: String(e && e.message || e) }; } };
    if (!a.ok) return Promise.resolve(touch());
    return new Promise((resolve) => {
      let done = false;
      const fin = (r) => { if (done) return; done = true; clearTimeout(t); resolve(r); };
      let c;
      try { c = this.spawn(a.python, ['-m', 'sleepmode', 'wake'], { cwd: a.app, env: this._env(), stdio: ['ignore', 'ignore', 'ignore'] }); } catch (e) { return resolve(touch()); }
      const t = setTimeout(() => { try { c.kill(); } catch (e) { /* ignore */ } fin(touch()); }, timeoutMs || 45000);
      c.on('error', () => fin(touch()));
      c.on('exit', (code) => fin(code === 0 || !this.status().sleeping ? { ok: true, via: 'cli' } : touch()));
    });
  }
  _size(f) { try { return fs.statSync(f).size; } catch (e) { return 0; } }

  // Is this pid really the sleep app? `ps` is asked once per pid (cached), never on every poll.
  isSleepmodePid(pid) {
    if (!this.psCache) this.psCache = new Map();
    if (this.psCache.has(pid)) return this.psCache.get(pid);
    let ok;
    try { ok = /sleepmode/i.test(String((this.o.psCommand || ((p) => execFileSync('ps', ['-p', String(p), '-o', 'command='], { encoding: 'utf8', timeout: 3000 })))(pid))); } catch (e) { ok = false; }
    if (this.psCache.size > 50) this.psCache.clear();
    this.psCache.set(pid, ok);
    return ok;
  }
  // Live state: sleeping needs the marker, a strictly numeric pid in it, a live process, and that process being sleepmode
  // (a stale marker, a timestamp, or a pid reused by something else never counts).
  status() {
    const j = readJson(this.p.status) || {};
    const marker = isFile(this.p.sleeping);
    const first = String(readText(this.p.sleeping)).trim().split(/\s+/)[0] || '';
    const pid = /^\d+$/.test(first) ? parseInt(first, 10) : 0;
    const alive = pidAlive(pid) && this.isSleepmodePid(pid);
    const since = j.since ? Date.parse(j.since) : NaN;
    const sleeping = marker && alive;
    const hours = typeof j.hours_slept === 'number' ? j.hours_slept : (Number.isFinite(since) && sleeping ? (Date.now() - since) / 3600000 : 0);
    return {
      sleeping, marker, pid: alive ? pid : 0, mode: j.mode || null, state: j.state || null,
      since: Number.isFinite(since) ? since : null, hours: Math.round(hours * 100) / 100,
      lastQuiz: typeof j.last_quiz === 'number' ? j.last_quiz : null,
      lastCheckin: j.last_checkin ? Date.parse(j.last_checkin) || null : null,
      needsPermission: j.needs_permission || null, demo: this.isDemo(j), raw: j
    };
  }
  // A demo run uses the fake worker. Decided from status.json (small, read every poll) or from a fake/demo event the tail reader saw;
  // the whole events file is never read here.
  isDemo(j) {
    return !!(j && (j.fake === true || j.demo === true || /fake|demo/i.test(String(j.worker || '')))) || !!this.demoSeen;
  }
  readSummary() { return readText(this.p.summary).trim(); }
  // Settings status line: honest, no invented numbers.
  statusLine() {
    const st = this.status();
    if (st.sleeping) return 'Sleeping now' + (st.hours ? ' (' + fmtHours(st.hours) + ')' : '') + '.';
    const j = st.raw;
    if (!j.since && !j.updated) return 'Has not slept yet.';
    const bits = [];
    const when = Date.parse(j.updated || j.since);
    if (Number.isFinite(when)) bits.push('Last slept ' + new Date(when).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    if (st.demo) bits.push('demo run');
    else {
      if (st.hours) bits.push(fmtHours(st.hours) + ' slept');
      if (st.lastCheckin) bits.push('last check-in ' + new Date(st.lastCheckin).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }));
    }
    return bits.join(' · ') + '.';
  }
  // Short pill text: "Sleeping · 2.5 h · quiz 78"
  pillLine(st) {
    st = st || this.status();
    return pillLine(st);
  }

  // New events since the last poll (offset based; a truncated file restarts from 0) and new inbox lines.
  poll() {
    const out = [];
    const f = this.p.events;
    const size = this._size(f);
    if (this.evOffset == null) this.evOffset = size; // first look: do not replay history
    if (size < this.evOffset) this.evOffset = 0;
    if (size > this.evOffset) {
      let buf = '';
      try { const fd = fs.openSync(f, 'r'); const b = Buffer.alloc(size - this.evOffset); fs.readSync(fd, b, 0, b.length, this.evOffset); fs.closeSync(fd); buf = b.toString('utf8'); } catch (e) { buf = ''; }
      const nl = buf.lastIndexOf('\n');
      if (nl >= 0) { // only whole lines; a half-written one waits for the next poll
        this.evOffset += Buffer.byteLength(buf.slice(0, nl + 1));
        for (const line of buf.slice(0, nl).split('\n')) { try { const e = JSON.parse(line); if (e && e.kind) { out.push(e); if (e.fake === true || e.demo === true || (e.info && e.info.fake === true) || /^(fake|demo)/i.test(String(e.worker || ''))) this.demoSeen = true; } } catch (e) { /* skip bad line */ } }
      }
    }
    let sig = '';
    try { const st = fs.statSync(this.p.inbox); sig = st.size + ':' + st.mtimeMs; } catch (e) { sig = ''; }
    if (this.inboxSeen != null && sig === this.inboxSig) return out; // unchanged: no read
    this.inboxSig = sig;
    const lines = (sig ? readText(this.p.inbox) : '').split('\n').map((l) => l.trim()).filter(Boolean);
    if (this.inboxSeen == null) this.inboxSeen = new Set(lines);
    else for (const l of lines) if (!this.inboxSeen.has(l)) { this.inboxSeen.add(l); out.push({ kind: 'inbox', line: l.replace(/^[-*]\s*/, '') }); }
    return out;
  }
  // baseline for poll(): everything already there counts as seen
  mark() { this.demoSeen = false; try { const st = fs.statSync(this.p.inbox); this.inboxSig = st.size + ':' + st.mtimeMs; } catch (e) { this.inboxSig = ''; } this.evOffset = this._size(this.p.events); this.inboxSeen = new Set(readText(this.p.inbox).split('\n').map((l) => l.trim()).filter(Boolean)); }
  watch(ms, cb) {
    this.mark();
    this.stop();
    this.timer = setInterval(() => { try { cb(this.status(), this.poll()); } catch (e) { /* never crash the app */ } }, ms || 5000);
    if (this.timer.unref) this.timer.unref();
  }
  stop() { if (this.timer) clearInterval(this.timer); this.timer = null; }
}

function fmtHours(h) { return (Math.round(h * 10) / 10) + ' h'; }
function pillLine(st) {
  const bits = ['Sleeping'];
  if (st.hours) bits.push(fmtHours(st.hours));
  if (st.demo) bits.push('demo');
  else if (st.lastQuiz != null) bits.push('quiz ' + (Math.round(st.lastQuiz * 10) / 10));
  return bits.join(' · ');
}

// ---- auto-sleep (pure) ----------------------------------------------------------------------------------
const hm = (s, d) => { const m = /^(\d{1,2}):(\d{2})$/.exec(String(s || '')); if (!m) return d; const h = +m[1], mi = +m[2]; return h < 24 && mi < 60 ? h * 60 + mi : d; };
// is `now` inside the from..to window (which may cross midnight)?
function inWindow(now, from, to) {
  const t = now.getHours() * 60 + now.getMinutes(), a = hm(from, 23 * 60), b = hm(to, 7 * 60);
  if (a === b) return false;
  return a < b ? t >= a && t < b : t >= a || t < b;
}
// The window auto-sleep uses: the one learned from Ben's routine (src/rhythm.js) when "Fit sleep to my routine" is on and there is one,
// else the one set by hand in Settings (also what is used while it is still learning). Every check of "is it night" goes through here so they cannot disagree.
function effectiveWindow(settings, learned) {
  const s = settings || {};
  if (s.sleepAdapt && learned && learned.from && learned.to) return { from: learned.from, to: learned.to, learned: true };
  return { from: s.sleepFrom, to: s.sleepTo, learned: false };
}
// one key per night (the date the window started), so Ben waking at 2 am is not put back to sleep at 2:30
function windowKey(now, from, to) {
  const t = now.getHours() * 60 + now.getMinutes(), a = hm(from, 23 * 60), b = hm(to, 7 * 60);
  const d = new Date(now);
  if (a > b && t < b) d.setDate(d.getDate() - 1);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
/**
 * Should Desk put Glim to sleep now? i: {now: Date, settings, idleMs (since Ben last used Desk), runActive, gatewayBusy,
 * windowFocused, asleep, available, lastKey (night already handled), learned ({from, to} from src/rhythm.js or null)} -> {sleep, reason, key}
 */
function shouldAutoSleep(i) {
  const s = i.settings || {};
  const no = (reason) => ({ sleep: false, reason });
  if (!s.autoSleep) return no('off');
  if (i.asleep) return no('already asleep');
  if (i.available === false) return no('sleep app not found');
  const w = effectiveWindow(s, i.learned);
  if (!inWindow(i.now, w.from, w.to)) return no('outside the night window');
  const key = windowKey(i.now, w.from, w.to);
  if (i.lastKey === key) return no('already handled tonight');
  if (i.runActive) return no('a run is active');
  if (i.gatewayBusy) return no('the gateway is busy');
  if (s.sleepOnlyPlugged === true && i.onBattery) return no('on battery');
  if (i.windowFocused) return no('Desk is in front');
  const need = Math.max(1, Number(s.sleepIdleMin) || 120) * 60000;
  // Desk's own idle time AND the Mac's (keyboard, mouse in any app): Ben working in another app is not idle
  const idle = Math.min(Number(i.idleMs) || 0, i.systemIdleMs == null ? Infinity : Number(i.systemIdleMs) || 0);
  if (!(idle >= need)) return no('not idle long enough');
  return { sleep: true, reason: 'idle at night', key };
}
// The night key to remember when Ben wakes Glim: the one recorded when this sleep STARTED, else the current night if now is inside the window.
// Waking at 08:00 (or auto-waking at 07:00) must never block tonight's auto-sleep.
function wakeKey({ sleepKey, now, settings, learned }) {
  if (sleepKey) return sleepKey;
  const w = effectiveWindow(settings, learned);
  return inWindow(now, w.from, w.to) ? windowKey(now, w.from, w.to) : null;
}
// ---- sleep length (pure) ------------------------------------------------------------------------------------
const DURATIONS = { '30': 30, '60': 60, '120': 120, '240': 240, morning: 'morning', open: null };
const OPEN_SLEEP_H = 8;   // "until I wake it" plans for 8 hours of work
const BUDGET_SHARE = 0.85; // the rest is for converting the adapter and waking up
// when should this sleep end? minutes (number) | 'morning' (the next time the Settings night end comes round) | null (until woken) -> ms or null
function computeWakeAt(now, d, settings, learned) {
  if (typeof d === 'number' && d > 0) return now.getTime() + d * 60000;
  if (d === 'morning') {
    const m = hm(effectiveWindow(settings, learned).to, 7 * 60);
    const t = new Date(now); t.setHours(Math.floor(m / 60), m % 60, 0, 0);
    if (t.getTime() <= now.getTime()) t.setDate(t.getDate() + 1); // already past it today: tomorrow's (a night that crosses midnight)
    return t.getTime();
  }
  return null;
}
// seconds the trainer may spend: ~85% of the sleep, 8 h when open-ended; at least 5 minutes
function nightBudgetS(startMs, wakeAtMs) {
  const total = wakeAtMs ? (wakeAtMs - startMs) / 1000 : OPEN_SLEEP_H * 3600;
  return Math.max(300, Math.floor(total * BUDGET_SHARE));
}
// the sleepDuration setting ('30' ... 'morning', 'open') -> what startSleep takes
const durationFromSetting = (v) => (Object.prototype.hasOwnProperty.call(DURATIONS, String(v)) ? DURATIONS[String(v)] : 'morning');
// "wakes at 3:40 (1 h 12 m left)" / "until you wake it"
function wakeLabel(wakeAtMs, nowMs) {
  if (!wakeAtMs) return 'until you wake it';
  const left = Math.max(0, Math.round((wakeAtMs - nowMs) / 60000));
  const t = new Date(wakeAtMs); const h = t.getHours() % 12 || 12;
  const at = h + ':' + String(t.getMinutes()).padStart(2, '0');
  return 'wakes at ' + at + ' (' + (left >= 60 ? Math.floor(left / 60) + ' h ' + (left % 60) + ' m' : left + ' m') + ' left)';
}
// the 60-second tick: is a timed sleep over?
const shouldTimedWake = (i) => !!(i.asleep && !i.waking && i.wakeAt && i.nowMs >= i.wakeAt);

// Optional wake at the end of the window (only for a sleep Desk started itself)
function shouldAutoWake(i) {
  const s = i.settings || {};
  if (!s.wakeAt || !s.autoSleep || !i.asleep || !i.startedAuto) return { wake: false };
  const w = effectiveWindow(s, i.learned);
  if (inWindow(i.now, w.from, w.to)) return { wake: false };
  return { wake: true, reason: 'the night window ended' };
}

module.exports = { effectiveWindow, computeWakeAt, nightBudgetS, durationFromSetting, wakeLabel, shouldTimedWake, DURATIONS, OPEN_SLEEP_H, BUDGET_SHARE, PY_MISSING, wakeKey, Sleep, homeDir, findPython, appDir, pidAlive, inWindow, windowKey, shouldAutoSleep, shouldAutoWake, pillLine, fmtHours };
