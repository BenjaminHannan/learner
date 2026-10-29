'use strict';
// Sleep with the built-in model (Windows, and any Mac without Ben's assistant): the same Sleep interface the Desk UI already uses,
// driven by this runner instead of the Mac sleepmode app. The trainer's base (LiquidAI/LFM3-1.7B) is the base of the built-in
// model (LFM3-1.7B GGUF), so the adapter really is used by the daytime Glim here.
//   * runs `python -m sleepmlx.worker` in chunks (the env contract SLEEPMODE_BUDGET_S / SLEEPMODE_OUT / SLEEPMODE_PRACTICE),
//   * stops llama-server while asleep (RAM), and on wake converts the new LoRA adapter to GGUF (llama.cpp's convert_lora_to_gguf.py)
//     and restarts llama-server with --lora; the previous adapter stays as the fallback,
//   * checks the adapter inside the running server (python -m sleepmlx served-check: adapter on vs off on general questions and the
//     night's held-out cards); one that does not load, does not fit this base (adapter.gguf.json) or scores worse is set aside.
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
// the base every adapter here is trained on and the built-in model is quantized from; adapter.gguf.json records it
const LORA_BASE = C.SLEEP_HF_REPO;
const sleepProfile = (platform) => (platform === 'darwin' ? 'lfm3_mps' : C.SLEEP_PROFILE);

// ---- adapter records (adapter.gguf.json next to each GGUF) ------------------------------------------------------------
const sidecar = (gguf) => gguf + '.json';
function readSidecar(gguf) { try { return JSON.parse(fs.readFileSync(sidecar(gguf), 'utf8')); } catch (e) { return null; } }
// May this GGUF be loaded on the built-in model? Only when it was trained on the same base. A GGUF with no record predates the
// records and was made by this runner, which only ever trains LORA_BASE, so it fits.
function loraFits(gguf, base) {
  if (!gguf || !fs.existsSync(gguf)) return false;
  const r = readSidecar(gguf);
  if (r && r.served && r.served.ok === false) return false;   // it scored worse in the model server once: never again
  return !r || !r.base_hf_id || r.base_hf_id === (base || LORA_BASE);
}
function moveWithSidecar(from, to) {
  fs.renameSync(from, to);
  try { if (fs.existsSync(sidecar(from))) fs.renameSync(sidecar(from), sidecar(to)); else fs.rmSync(sidecar(to), { force: true }); } catch (e) { /* record only */ }
}

// ---- pure builders (tested) -----------------------------------------------------------------------------------------
// The night's lesson cards (what went wrong in a chat and what to do instead), as the worker's chunk output lists them.
const LESSONS_SHOWN = 8;
function lessonsSection(lessons, reverted) {
  const items = (lessons || []).map((l) => String(l).replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, LESSONS_SHOWN);
  if (!items.length) return '';
  return 'Lessons' + (reverted ? ' (not kept: the night was undone by its safety check)' : '') + ':\n' + items.map((l) => '- ' + l).join('\n');
}
function workerEnv(o) {
  const env = {
    SLEEPMODE_BUDGET_S: String(o.budgetS || CHUNK_BUDGET_S), ...(o.nightBudgetS > 0 ? { SLEEPMLX_NIGHT_BUDGET_S: String(Math.round(o.nightBudgetS)) } : {}), SLEEPMODE_OUT: o.outFile, SLEEPMODE_PRACTICE: (o.practice || []).join(path.delimiter), SLEEPMODE_WORKDIR: o.home,
    SLEEPMLX_HOME: o.home, SLEEPMLX_DIARY_DIR: o.diaryDir, LEARNER_OPS: o.home,
    PYTHONPATH: o.sleepmlxParent + (o.basePythonPath ? path.delimiter + o.basePythonPath : ''), PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8',
    HF_HOME: o.hfHome, HF_HUB_CACHE: o.hfHome, HF_HUB_OFFLINE: '1', TOKENIZERS_PARALLELISM: 'false'
  };
  // the app's userData (memory.json, tracking.md): sleep turns saved notes and the "Keeping track of" list into cards too
  if (o.userData) env.SLEEPMLX_USERDATA = o.userData;
  // the snapshot folder snapshot_download printed: the worker loads the model straight from it (no cache lookup, works offline)
  if (o.hfDir) env.SLEEPMLX_MODEL_DIR = o.hfDir;
  return env;
}
function workerCommand(o) { return { cmd: o.python, args: ['-m', 'sleepmlx.worker', '--profile', o.profile || sleepProfile(o.platform || process.platform)], env: workerEnv(o), cwd: o.sleepmlxParent }; }
function servedCheckCommand(o) { return { cmd: o.python, args: ['-m', 'sleepmlx', 'served-check', '--server', o.url, '--cards', o.cards], env: { PYTHONPATH: o.sleepmlxParent, PYTHONUTF8: '1', HF_HUB_OFFLINE: '1' }, cwd: o.sleepmlxParent }; }
// run the served check; exit 0 pass, 1 worse, 2 no answer. -> {ok, reasons, ...}
function defaultServedCheck(cmd) {
  return new Promise((resolve) => {
    require('child_process').execFile(cmd.cmd, cmd.args, { windowsHide: true, timeout: 10 * 60000, maxBuffer: 4 * 1024 * 1024, cwd: cmd.cwd, env: { ...process.env, ...cmd.env } }, (err, so) => {
      const last = String(so || '').trim().split('\n').pop();
      let r = null; try { r = JSON.parse(last); } catch (e) { /* none */ }
      if (r && (typeof r.ok === 'boolean' || r.ok === null)) return resolve(r);
      // it could not run (python missing, timeout, crash): that is not a verdict on the adapter
      resolve({ ok: null, reasons: ['not checked: ' + String((err && err.message) || last || 'no output').slice(0, 200)] });
    });
  });
}
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
    this.adapterRejected = path.join(this.home, 'adapter.rejected.gguf');
    this.platform = o.platform || process.platform;
  }
  python() { return this.installer.pythonExe(); }
  available() { return { ok: true, app: this.home, python: this.python(), reason: '' }; }
  // the adapter to load when the app starts the model (the newest converted one, if any)
  currentLora() { return loraFits(this.adapterGguf) ? this.adapterGguf : (loraFits(this.adapterPrev) ? this.adapterPrev : ''); }
  needsRuntime() { return !this.installer.installed(); }

  status() {
    const j = (() => { try { return JSON.parse(fs.readFileSync(this.p.status, 'utf8')); } catch (e) { return {}; } })();
    const since = this.active && this.since ? this.since : (j.since ? Date.parse(j.since) : null);
    const hours = this.active && this.since ? (Date.now() - this.since) / 3600000 : (j.hours_slept || 0);
    return { sleeping: this.active, marker: this.active, pid: 0, mode: this.platform === 'win32' ? 'windows' : 'builtin', state: this.phase || null, since: Number.isFinite(since) ? since : null, hours: Math.round(hours * 100) / 100, lastQuiz: this.lastQuiz != null ? this.lastQuiz : (typeof j.last_quiz === 'number' ? j.last_quiz : null), lastCheckin: this.lastCheckinAt || null, needsPermission: null, demo: false, raw: j };
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
    if (this.active) return { ok: false, error: 'Already sleeping.' };   // before the resets below: a second start must not wipe the running night
    this.nightBudgetS = (o && o.budgetS) || 0; this.wakeAtMs = (o && o.wakeAt) || null; this.lastCheckinAt = null; this.checkins = []; this.ckAbort = null;
    this.finishedNight = false; this.nothingNew = false; this.lessons = []; this.lessonsReverted = false; this.night = null; this.loaded = null; this.converted = false;
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
    if (this.backoffDone) this.backoffDone();   // waiting a minute before the next chunk: wake now, not after the wait
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
    try { fs.mkdirSync(this.home, { recursive: true }); fs.rmSync(outFile, { force: true }); } catch (e) { /* none */ }
    const st = this.installer.state();
    const cmd = workerCommand({ platform: this.platform, python: this.python(), home: this.home, outFile, diaryDir: this.diaryDir, sleepmlxParent: this.parent, hfHome: path.join(this.installer.dir, 'hf'), hfDir: st.hfDir, budgetS: CHUNK_BUDGET_S, nightBudgetS: this.nightBudgetS, basePythonPath: '', userData: this.o.userData || this.root });
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
        if (out.quiz != null) { this.lastQuiz = out.quiz; this.night = out; }
        if (Array.isArray(out.lessons) && out.lessons.length) { this.lessons = out.lessons.map((l) => String(l)).slice(0, LESSONS_SHOWN); this.lessonsReverted = !!out.reverted; }
        this._writeStatus();
        // a dry run (too few cards in the day) ends the night too: running it again would only reload the model
        if (out.quiz != null || NO_WORK.test(out.message || '') || out.status === 'dry_run') { this.finishedNight = out.quiz != null; this.nothingNew = out.quiz == null; this.noWorkWhy = out.status === 'dry_run' ? out.message || '' : ''; break; }
        const m = mayStart(this.getSettings(), this.onBattery());
        if (!m.ok) { this._event({ kind: 'unplugged' }); break; }
        if (!this.wakeReq) await this._maybeCheckin();
        if (out.interrupted && out.stop_reason && !this.wakeReq) await new Promise((r) => { const t = setTimeout(r, this.o.retryMs === undefined ? 60000 : this.o.retryMs); if (t.unref) t.unref(); this.backoffDone = () => { clearTimeout(t); r(); }; });
        this.backoffDone = null;
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
    const lora = CK.checkinAdapter(this.home, fs.existsSync, (f) => loraFits(f));
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
    const src = path.join(adapterDir, 'adapter_model.safetensors');
    let srcMtime = null; try { srcMtime = fs.statSync(src).mtimeMs; } catch (e) { /* no weights file to compare: convert */ }
    // only when the adapter is newer than the GGUF we already have, and is not one already set aside as worse
    if (srcMtime != null) {
      try { if (fs.existsSync(this.adapterGguf) && fs.statSync(this.adapterGguf).mtimeMs >= srcMtime) return; } catch (e) { /* convert */ }
      const rej = readSidecar(this.adapterRejected);
      if (rej && rej.source_mtime === srcMtime) return;
    }
    this.phase = 'converting';
    const next = path.join(this.home, 'adapter.next.gguf');
    const cmd = convertCommand({ python: this.python(), convertScript: st.convert, adapterDir, hfDir: st.hfDir, outFile: next });
    try {
      await (this.o.run || require('./runtime/sleepinstall').defaultRun)(cmd.cmd, cmd.args, { env: { PYTHONUTF8: '1', HF_HUB_OFFLINE: '1' } });
      if (!fs.existsSync(next)) throw new Error('the converter wrote no file');
      if (fs.existsSync(this.adapterGguf)) moveWithSidecar(this.adapterGguf, this.adapterPrev);
      fs.renameSync(next, this.adapterGguf);
      fs.writeFileSync(sidecar(this.adapterGguf), JSON.stringify({ base_hf_id: LORA_BASE, profile: sleepProfile(this.platform), source_mtime: srcMtime, date: this.night && this.night.date || null, created: new Date().toISOString() }, null, 2));
      this.converted = true;
      this._event({ kind: 'converted' });
    } catch (e) { this._event({ kind: 'convert_failed', error: String(e.message || e) }); try { fs.rmSync(next, { force: true }); } catch (x) { /* none */ } }
  }

  // The served check of an adapter now loaded in the model server: once per adapter file (the result is kept in its record).
  async _servedCheck(lora) {
    const rec = readSidecar(lora) || {};
    if (rec.served && rec.served.ok === true) return rec.served;
    const url = this.hooks.servedUrl && this.hooks.servedUrl();
    if (!url) return { ok: null, reasons: ['not checked: the model server address is unknown'] };
    const cmd = servedCheckCommand({ python: this.python(), url, cards: path.join(this.home, 'cards.jsonl'), sleepmlxParent: this.parent });
    this.phase = 'checking the adapter';
    const r = await (this.o.servedCheck || defaultServedCheck)(cmd);
    try { if (fs.existsSync(lora)) fs.writeFileSync(sidecar(lora), JSON.stringify({ ...rec, served: { ...r, at: new Date().toISOString() } }, null, 2)); } catch (e) { /* record only */ }
    return r;
  }
  // the newest GGUF did not load or scored worse: set aside (not deleted) so it is never loaded or converted again; currentLora() then
  // falls back to adapter.prev.gguf, and the next good night's GGUF becomes adapter.gguf as usual
  // a bad adapter.prev.gguf goes to adapter.prev.rejected.gguf, so currentLora() never hands it to the next app start either
  _setAside(lora) {
    const to = lora === this.adapterGguf ? this.adapterRejected : (lora === this.adapterPrev ? path.join(this.home, 'adapter.prev.rejected.gguf') : '');
    if (!to) return;
    try { moveWithSidecar(lora, to); } catch (e) { /* the event says what happened */ }
  }

  async _finish() {
    try { fs.rmSync(path.join(this.home, 'ASSISTANT_RUNNING'), { force: true }); } catch (e) { /* none */ }
    this._writeStatus();
    try { await this._convert(); } catch (e) { /* the old adapter stays */ }
    this.phase = 'waking';
    try {
      // newest adapter, then the previous one, then the plain model; an adapter must fit this base, load, and pass the served check
      const cands = [this.adapterGguf, this.adapterPrev].filter((f) => fs.existsSync(f));
      const tried = [];
      for (const f of cands) {
        if (!loraFits(f)) { tried.push({ lora: path.basename(f), why: 'trained on another base (' + ((readSidecar(f) || {}).base_hf_id || '?') + ')' }); continue; }
        const r = this.hooks.resumeModel ? await this.hooks.resumeModel(f) : { ok: true };
        if (r && r.loraFailed) {   // the server started without it: the adapter itself is bad
          tried.push({ lora: path.basename(f), why: 'did not load' + (r.error ? ': ' + r.error : '') });
          this._event({ kind: 'lora_failed', lora: path.basename(f), error: r.error || '' });
          this._setAside(f);
          continue;
        }
        if (!(r && r.ok)) {   // the model did not start at all (memory, port): not the adapter's fault, keep it for next time
          tried.push({ lora: path.basename(f), why: 'not tried: the model did not start (' + (r && r.error || '?') + ')' });
          this._event({ kind: 'model_start_failed', lora: path.basename(f), error: r && r.error || '' });
          break;
        }
        if (r.skipped) { this.loaded = { lora: path.basename(f), tried, served: { ok: null, reasons: ['the built-in model is not the one in use'] } }; break; }
        const sc = await this._servedCheck(f);
        if (sc.ok === false) {
          tried.push({ lora: path.basename(f), why: 'scored worse in the model server: ' + (sc.reasons || []).join('; ') });
          this._event({ kind: 'lora_worse', lora: path.basename(f), reasons: sc.reasons || [] });
          this._setAside(f);
          continue;
        }
        this.loaded = { lora: path.basename(f), tried, served: sc };
        break;
      }
      if (!this.loaded) {
        const r = this.hooks.resumeModel ? await this.hooks.resumeModel('') : { ok: true };
        this.loaded = { lora: '', tried, ok: !!(r && r.ok), error: r && r.error || '' };
      }
      this._event({ kind: 'loaded', lora: this.loaded.lora || 'plain model', served: this.loaded.served || null, tried });
    } catch (e) { this.exit = this.exit || { error: String(e.message || e) }; }
    this._writeSummary();
    this.active = false; this.phase = '';
  }
  _writeSummary() {
    const hrs = this.since ? (Date.now() - this.since) / 3600000 : 0;
    const n = this.night || {};
    const line = this.exit && this.exit.error ? 'Sleep stopped early: ' + this.exit.error
      : this.nothingNew ? 'Nothing new to learn yet: chat with Glim, then sleep again.' + (this.noWorkWhy ? ' (' + this.noWorkWhy + ')' : '')
      : this.finishedNight ? (n.reverted ? 'Glim practiced your chats, but the morning check undid the night' : 'Glim learned from your chats') + (this.lastQuiz != null ? ' (recall quiz ' + Math.round(this.lastQuiz) + '%)' : '') + '.'
      : this.wakeReq ? 'Woken early. What was learned so far is saved and the night continues next time.' : 'Sleep ended.';
    const early = (this.finishedNight || this.nothingNew) && this.wakeAtMs && Date.now() < this.wakeAtMs - 120000;
    const lines = [early ? 'Finished early: it practiced everything new.' : '', line];
    if (this.finishedNight) lines.push(nightLines(n));
    if (this.loaded) lines.push(loadedLine(this.loaded, !!this.converted && this.finishedNight && !n.reverted));
    if (this.lessons && this.lessons.length) lines.push(lessonsSection(this.lessons, this.lessonsReverted));
    if (this.checkins && this.checkins.length) lines.push('Check-ins that needed you:\n' + this.checkins.map((c) => '- ' + c).join('\n'));
    try { fs.mkdirSync(this.home, { recursive: true }); fs.writeFileSync(this.p.summary, '# Sleep summary\n\n' + lines.filter(Boolean).join('\n\n') + '\n\nSlept ' + (Math.round(hrs * 10) / 10) + ' h.\n'); } catch (e) { /* ignore */ }
  }
}

// ---- the morning summary's facts, from the worker's last chunk (sleepmlx recipe res) and what was loaded (pure, tested) -------
const pct = (x) => (typeof x === 'number' ? Math.round(x) + '%' : '?');
function nightLines(n) {
  if (!n || n.quiz == null) return '';
  const out = [];
  out.push('Quiz (held-out recall, strict: ' + (n.held_out || 0) + ' questions it never trained on): ' + pct(n.recall_pre) + ' before -> ' + pct(n.quiz) + ' after.');
  if (typeof n.general === 'number') out.push('General questions: ' + pct(n.general) + ' (plain model ' + pct(n.general_base) + ').');
  if (n.reverted) out.push('Undone: ' + ((n.revert_reason || []).join('; ') || 'it did not pass the morning check') + '. Glim is as it was before the night.');
  else out.push('Kept: it passed the morning check (no harm to general questions, and it answered more held-out questions).');
  const d = n.dreamcheck;
  if (d && d.available === false) out.push('Dream check: not available (' + String(d.reason || '').slice(0, 80) + '); the cards were checked only against the chat text.');
  else if (d && d.n) out.push('Dream check against the diary: ' + d.n + ' cards, ' + (d.supported || 0) + ' supported, ' + (d.unknown || 0) + ' unknown, ' + (d.contradicted || 0) + ' contradicted (dropped)' + (d.unchecked ? ', ' + d.unchecked + ' not reached in time' : '') + '.');
  return out.join('\n');
}
function loadedLine(l, newKept) {
  if (!l) return '';
  const tried = (l.tried || []).map((t) => t.lora + ' ' + t.why).join('; ');
  if (!l.lora) return 'Glim runs on the plain model' + (tried ? ' (' + tried + ')' : '') + (l.ok === false ? '. The model did not start: ' + (l.error || '?') : '') + '.';
  const s = l.served || {};
  const check = s.ok === true ? ' Checked in the model server: general ' + s.general_on + '/' + s.general_n + ' with it vs ' + s.general_off + '/' + s.general_n + ' without; held-out ' + s.held_on + '/' + s.held_n + ' vs ' + s.held_off + '/' + s.held_n + '.'
    : s.ok === null ? ' Not checked in the model server (' + ((s.reasons || [])[0] || '') + ').' : '';
  const which = l.lora === 'adapter.gguf' ? (newKept ? "tonight's adapter" : 'its newest adapter') : 'the previous adapter';
  return 'Glim now runs with ' + which + ' (' + l.lora + ').' + check + (tried ? ' Set aside: ' + tried + '.' : '');
}

module.exports = { WinSleep, lessonsSection, nightLines, loadedLine, loraFits, readSidecar, sleepProfile, servedCheckCommand, workerCommand, workerEnv, convertCommand, sleepmlxParent, mayStart, CHUNK_BUDGET_S, LORA_BASE };
