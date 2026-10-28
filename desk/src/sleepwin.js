'use strict';
// Sleep on Windows: the same Sleep interface the Desk UI already uses, but driven by this runner instead of the Mac sleepmode app.
//   * runs `python -m sleepmlx.worker` in chunks (the env contract SLEEPMODE_BUDGET_S / SLEEPMODE_OUT / SLEEPMODE_PRACTICE),
//   * stops llama-server while asleep (RAM), and on wake converts the new LoRA adapter to GGUF (llama.cpp's convert_lora_to_gguf.py)
//     and restarts llama-server with --lora; the previous adapter stays as the fallback.
// Everything outside the process (spawn, the model, the installer, the battery) is injected so the logic is unit-testable.
const fs = require('fs');
const path = require('path');
const { spawn: realSpawn } = require('child_process');
const { Sleep } = require('./sleep');
const C = require('./runtime/constants');

const CK = require('./checkin');
// 15 minutes: a check-in can be at most about this late (it happens at a chunk boundary)
const CHUNK_BUDGET_S = 900;
const NO_WORK = /no new diary day/i;

// ---- pure builders (tested) -----------------------------------------------------------------------------------------
function workerEnv(o) {
  const env = {
    SLEEPMODE_BUDGET_S: String(o.budgetS || CHUNK_BUDGET_S), ...(o.nightBudgetS > 0 ? { SLEEPMLX_NIGHT_BUDGET_S: String(Math.round(o.nightBudgetS)) } : {}), SLEEPMODE_OUT: o.outFile, SLEEPMODE_PRACTICE: (o.practice || []).join(path.delimiter), SLEEPMODE_WORKDIR: o.home,
    SLEEPMLX_HOME: o.home, SLEEPMLX_DIARY_DIR: o.diaryDir, LEARNER_OPS: o.home,
    PYTHONPATH: o.sleepmlxParent + (o.basePythonPath ? path.delimiter + o.basePythonPath : ''), PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8',
    HF_HOME: o.hfHome, HF_HUB_CACHE: o.hfHome, HF_HUB_OFFLINE: '1', TOKENIZERS_PARALLELISM: 'false'
  };
  // the snapshot folder snapshot_download printed: the worker loads the model straight from it (no cache lookup, works offline)
  if (o.hfDir) env.SLEEPMLX_MODEL_DIR = o.hfDir;
  return env;
}
function workerCommand(o) { return { cmd: o.python, args: ['-m', 'sleepmlx.worker', '--profile', o.profile || C.SLEEP_PROFILE], env: workerEnv(o), cwd: o.sleepmlxParent }; }
function convertCommand(o) { return { cmd: o.python, args: [o.convertScript, o.adapterDir, '--base', o.hfDir, '--outfile', o.outFile] }; }
// where the sleepmlx package lives: next to the app resources when packaged, the repo root in development
function sleepmlxParent(resourcesPath, devRoot, exists) {
  exists = exists || fs.existsSync;
  if (resourcesPath && exists(path.join(resourcesPath, 'sleepmlx'))) return resourcesPath;
  return devRoot;
}
// may a sleep start now? (manual and scheduled both honour "only when plugged in")
function mayStart(settings, onBattery) {
  if (settings && settings.sleepOnlyPlugged === true && onBattery) return { ok: false, error: 'The laptop is on battery. Plug it in first (sleep is slow and uses a lot of power), or turn off "Only sleep when plugged in" in Settings > Sleep.' };
  return { ok: true };
}

class WinSleep extends Sleep {
  /** o: {getSettings, root, installer (SleepInstaller), hooks:{pauseModel(), resumeModel(lora)->Promise<{ok,loraFailed?}>}, onBattery(), sleepmlxParent, spawn, run} */
  constructor(o) {
    super({ ...o, home: path.join(o.root, 'sleep') });
    this.root = o.root; this.installer = o.installer; this.hooks = o.hooks || {};
    this.onBattery = o.onBattery || (() => false);
    this.parent = o.sleepmlxParent;
    this.diaryDir = path.join(o.root, 'diary', 'raw');
    this.active = false; this.wakeReq = false; this.child = null; this.lastQuiz = null; this.since = null; this.phase = '';
    this.adapterGguf = path.join(this.home, 'adapter.gguf'); this.adapterPrev = path.join(this.home, 'adapter.prev.gguf');
  }
  python() { return this.installer.pythonExe(); }
  available() { return { ok: true, app: this.home, python: this.python(), reason: '' }; }
  // the adapter to load when the app starts the model (the newest converted one, if any)
  currentLora() { return fs.existsSync(this.adapterGguf) ? this.adapterGguf : ''; }
  needsRuntime() { return !this.installer.installed(); }

  status() {
    const j = (() => { try { return JSON.parse(fs.readFileSync(this.p.status, 'utf8')); } catch (e) { return {}; } })();
    const since = this.active && this.since ? this.since : (j.since ? Date.parse(j.since) : null);
    const hours = this.active && this.since ? (Date.now() - this.since) / 3600000 : (j.hours_slept || 0);
    return { sleeping: this.active, marker: this.active, pid: 0, mode: 'windows', state: this.phase || null, since: Number.isFinite(since) ? since : null, hours: Math.round(hours * 100) / 100, lastQuiz: this.lastQuiz != null ? this.lastQuiz : (typeof j.last_quiz === 'number' ? j.last_quiz : null), lastCheckin: this.lastCheckinAt || null, needsPermission: null, demo: false, raw: j };
  }
  _writeStatus() {
    try {
      fs.mkdirSync(this.home, { recursive: true });
      fs.writeFileSync(this.p.status, JSON.stringify({ since: this.since ? new Date(this.since).toISOString() : null, updated: new Date().toISOString(), hours_slept: this.since ? Math.round(((Date.now() - this.since) / 3600000) * 100) / 100 : 0, last_quiz: this.lastQuiz, worker: 'sleepmlx' }));
    } catch (e) { /* ignore */ }
  }
  _event(e) { try { fs.mkdirSync(this.home, { recursive: true }); fs.appendFileSync(this.p.events, JSON.stringify({ ts: new Date().toISOString(), ...e }) + '\n'); } catch (x) { /* ignore */ } }
  _log(s) { try { fs.mkdirSync(this.home, { recursive: true }); fs.appendFileSync(this.p.log, s); } catch (e) { /* ignore */ } }

  /** o: {budgetS (the whole sleep, seconds), wakeAt (ms or null)} */
  start(o) {
    this.nightBudgetS = (o && o.budgetS) || 0; this.wakeAtMs = (o && o.wakeAt) || null; this.lastCheckinAt = null; this.checkins = []; this.ckAbort = null;
    this.finishedNight = false; this.nothingNew = false;
    if (this.active) return { ok: false, error: 'Already sleeping.' };
    if (this.needsRuntime()) return { ok: false, needsRuntime: true, error: 'Sleep needs a one-time download first.', plan: this.installer.plan() };
    const m = mayStart(this.getSettings(), this.onBattery());
    if (!m.ok) return m;
    this.active = true; this.wakeReq = false; this.exit = null; this.since = Date.now(); this.phase = 'sleeping'; this.lastQuiz = null;
    try { fs.rmSync(path.join(this.home, 'ASSISTANT_RUNNING'), { force: true }); } catch (e) { /* none */ }
    this._run().catch((e) => { this.exit = { error: String(e && e.message || e) }; this.active = false; });
    return { ok: true, pid: 0 };
  }
  wake() {
    this.wakeReq = true;
    if (this.ckAbort) { try { this.ckAbort.abort(); } catch (e) { /* done */ } } // a check-in in progress stops now
    // the worker stops cleanly (checkpoint, exit 0) when this flag file appears; if it ignores it, it is killed after a while
    try { fs.mkdirSync(this.home, { recursive: true }); fs.writeFileSync(path.join(this.home, 'ASSISTANT_RUNNING'), new Date().toISOString()); } catch (e) { /* ignore */ }
    const c = this.child;
    if (c) { const t = setTimeout(() => { try { c.kill(); } catch (e) { /* gone */ } }, this.o.wakeKillMs || 90000); if (t.unref) t.unref(); }
    return Promise.resolve({ ok: true, via: 'file' });
  }

  _chunk() {
    const spawn = this.o.spawn || realSpawn;
    const outFile = path.join(this.home, 'chunk_out.json');
    try { fs.rmSync(outFile, { force: true }); } catch (e) { /* none */ }
    const st = this.installer.state();
    const cmd = workerCommand({ python: this.python(), home: this.home, outFile, diaryDir: this.diaryDir, sleepmlxParent: this.parent, hfHome: path.join(this.installer.dir, 'hf'), hfDir: st.hfDir, budgetS: CHUNK_BUDGET_S, nightBudgetS: this.nightBudgetS, basePythonPath: '' });
    return new Promise((resolve) => {
      let c;
      try { c = spawn(cmd.cmd, cmd.args, { cwd: cmd.cwd, env: { ...process.env, ...cmd.env }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { return resolve({ error: String(e.message || e) }); }
      this.child = c;
      const log = (d) => this._log(String(d));
      if (c.stdout) c.stdout.on('data', log); if (c.stderr) c.stderr.on('data', log);
      c.on('error', (e) => { this.child = null; resolve({ error: String(e.message || e) }); });
      c.on('exit', (code) => {
        this.child = null;
        let out = null; try { out = JSON.parse(fs.readFileSync(outFile, 'utf8')); } catch (e) { /* none */ }
        resolve(out || { error: 'the sleep worker stopped without a result (exit ' + code + '); see ' + this.p.log });
      });
    });
  }

  async _run() {
    try {
      if (this.hooks.pauseModel) await this.hooks.pauseModel();
      for (let i = 0; i < 200 && !this.wakeReq; i++) {
        const out = await this._chunk();
        this._event({ kind: 'chunk', quiz: out.quiz == null ? null : out.quiz, steps: out.steps || 0, interrupted: !!out.interrupted, message: out.message || '', error: out.error || '' });
        if (out.error) { this.exit = { error: out.error }; break; }
        if (out.quiz != null) this.lastQuiz = out.quiz;
        this._writeStatus();
        if (out.quiz != null || NO_WORK.test(out.message || '')) { this.finishedNight = out.quiz != null; this.nothingNew = NO_WORK.test(out.message || ''); break; }
        const m = mayStart(this.getSettings(), this.onBattery());
        if (!m.ok) { this._event({ kind: 'unplugged' }); break; }
        if (!this.wakeReq) await this._maybeCheckin();
        if (out.interrupted && out.stop_reason) await new Promise((r) => { const t = setTimeout(r, this.o.retryMs === undefined ? 60000 : this.o.retryMs); if (t.unref) t.unref(); });
      }
    } catch (e) { this.exit = { error: String(e && e.message || e) }; }
    finally { await this._finish(); }
  }

  // Hourly check-in: at a chunk boundary, once the period has passed. The model comes up with the previous (gate-passed) adapter
  // or the plain model, never the half-trained one; the task runs through the app's agent (hooks.checkin); the server then stops
  // and training resumes. Capped at 5 minutes; a wake aborts it.
  async _maybeCheckin() {
    const st = this.getSettings();
    const d = CK.checkinDue({ enabled: st.sleepPauseGlims !== false && !!this.hooks.checkin, now: Date.now(), sleepStart: this.since, lastAt: this.lastCheckinAt, periodMin: st.sleepCheckinMins, wakeReq: this.wakeReq, onBattery: this.onBattery(), onlyPlugged: st.sleepOnlyPlugged === true });
    if (!d.due) return;
    this.lastCheckinAt = Date.now();
    const lora = CK.checkinAdapter(this.home, fs.existsSync);
    this.phase = 'checking in';
    this._event({ kind: 'checkin_start', adapter: lora ? path.basename(lora) : 'base' });
    const ac = new AbortController(); this.ckAbort = ac;
    const cap = setTimeout(() => ac.abort(), this.o.checkinCapMs || CK.CHECKIN_CAP_MS); if (cap.unref) cap.unref();
    let res = { reply: '' }; let notified = 0;
    try {
      const up = this.hooks.resumeModel ? await this.hooks.resumeModel(lora) : { ok: true };
      if (up && up.ok === false) res = { error: 'the model did not start for the check-in: ' + (up.error || '') };
      else res = (await this.hooks.checkin({ signal: ac.signal, task: CK.checkinTask(st, this.o.rules, this.o.tracked && this.o.tracked()), capMs: this.o.checkinCapMs || CK.CHECKIN_CAP_MS })) || {};
    } catch (e) { res = { error: String(e && e.message || e) }; }
    clearTimeout(cap); this.ckAbort = null;
    try { if (this.hooks.pauseModel) await this.hooks.pauseModel(); } catch (e) { /* the next chunk needs the RAM; the exit was awaited by the hook */ }
    const p = CK.parseReply(res.reply);
    this.checkins = this.checkins || [];
    this.seenLines = this.seenLines || new Set();
    if (!res.error && !res.aborted && !p.nothing && !CK.isRepeat(this.seenLines, p.line)) { notified = 1; this.checkins.push(p.line); try { this.hooks.onCheckin && this.hooks.onCheckin(p.line); } catch (e) { /* ignore */ } }
    this._event({ kind: 'checkin', nothing: p.nothing, line: p.line, notified, aborted: !!res.aborted, error: res.error || '' });
    this.phase = 'sleeping';
  }

  async _convert() {
    const st = this.installer.state();
    const adapterDir = path.join(this.home, 'adapter');
    if (!fs.existsSync(adapterDir) || !st.convert || !st.hfDir) return;
    // only when the adapter is newer than the GGUF we already have
    try { if (fs.existsSync(this.adapterGguf) && fs.statSync(this.adapterGguf).mtimeMs >= fs.statSync(path.join(adapterDir, 'adapter_model.safetensors')).mtimeMs) return; } catch (e) { /* convert */ }
    this.phase = 'converting';
    const next = path.join(this.home, 'adapter.next.gguf');
    const cmd = convertCommand({ python: this.python(), convertScript: st.convert, adapterDir, hfDir: st.hfDir, outFile: next });
    try {
      await (this.o.run || require('./runtime/sleepinstall').defaultRun)(cmd.cmd, cmd.args, { env: { PYTHONUTF8: '1', HF_HUB_OFFLINE: '1' } });
      if (!fs.existsSync(next)) throw new Error('the converter wrote no file');
      if (fs.existsSync(this.adapterGguf)) fs.renameSync(this.adapterGguf, this.adapterPrev);
      fs.renameSync(next, this.adapterGguf);
      this._event({ kind: 'converted' });
    } catch (e) { this._event({ kind: 'convert_failed', error: String(e.message || e) }); try { fs.rmSync(next, { force: true }); } catch (x) { /* none */ } }
  }

  async _finish() {
    try { fs.rmSync(path.join(this.home, 'ASSISTANT_RUNNING'), { force: true }); } catch (e) { /* none */ }
    this._writeStatus();
    try { await this._convert(); } catch (e) { /* the old adapter stays */ }
    this.phase = 'waking';
    try {
      // newest adapter, then the previous one, then the plain model
      const cands = [this.adapterGguf, this.adapterPrev].filter((f) => fs.existsSync(f)).concat('');
      for (const lora of cands) {
        const r = this.hooks.resumeModel ? await this.hooks.resumeModel(lora) : { ok: true };
        if (r && r.ok && !r.loraFailed) break;
        this._event({ kind: 'lora_failed', lora: lora ? path.basename(lora) : '', error: r && r.error || '' });
      }
    } catch (e) { this.exit = this.exit || { error: String(e.message || e) }; }
    this._writeSummary();
    this.active = false; this.phase = '';
  }
  _writeSummary() {
    const hrs = this.since ? (Date.now() - this.since) / 3600000 : 0;
    const line = this.exit && this.exit.error ? 'Sleep stopped early: ' + this.exit.error
      : this.nothingNew ? 'Nothing new to learn yet: chat with Glim, then sleep again.'
      : this.finishedNight ? 'Glim learned from your chats' + (this.lastQuiz != null ? ' (recall quiz ' + Math.round(this.lastQuiz) + '%)' : '') + '.'
      : this.wakeReq ? 'Woken early. What was learned so far is saved and the night continues next time.' : 'Sleep ended.';
    const early = (this.finishedNight || this.nothingNew) && this.wakeAtMs && Date.now() < this.wakeAtMs - 120000;
    const lines = [early ? 'Finished early: it practiced everything new.' : '', line];
    if (this.checkins && this.checkins.length) lines.push('Check-ins that needed you:\n' + this.checkins.map((c) => '- ' + c).join('\n'));
    try { fs.mkdirSync(this.home, { recursive: true }); fs.writeFileSync(this.p.summary, '# Sleep summary\n\n' + lines.filter(Boolean).join('\n\n') + '\n\nSlept ' + (Math.round(hrs * 10) / 10) + ' h.\n'); } catch (e) { /* ignore */ }
  }
}

module.exports = { WinSleep, workerCommand, workerEnv, convertCommand, sleepmlxParent, mayStart, CHUNK_BUDGET_S };
