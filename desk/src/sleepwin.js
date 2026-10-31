'use strict';
// Sleep with the built-in model (Windows and Macs without the external assistant).
// HF training and the QAD chat GGUF are distinct variants; transfer is not assumed.
// Each new candidate is checked privately against the actual chat base before
// it can be published. Unbound legacy GGUFs remain on disk and are never loaded.
// Everything outside the process (spawn, the model, the installer, the battery) is injected so the logic is unit-testable.
const fs = require('fs');
const path = require('path');
const { spawn: realSpawn } = require('child_process');
const { Sleep } = require('./sleep');
const C = require('./runtime/constants');
const Candidates = require('./sleep-candidates');

const CK = require('./checkin');
// 15 minutes: a check-in can be at most about this late (it happens at a chunk boundary)
const CHUNK_BUDGET_S = 900;
const CHUNK_STARTUP_MARGIN_S = 300; // model startup and checkpointing are outside the worker budget
const NO_WORK = /no new diary day/i;
const sleepProfile = (platform) => (platform === 'darwin' ? 'lfm3_mps' : C.SLEEP_PROFILE);

function committedAdapter(home) {
  const manifest = path.join(home, 'adapters.json');
  if (!fs.existsSync(manifest)) return { dir: path.join(home, 'adapter'), generation: null };
  const r = JSON.parse(fs.readFileSync(manifest, 'utf8'));
  if (r.version !== 1 || typeof r.current !== 'string' || !r.current || path.isAbsolute(r.current)
      || r.current.split(/[\\/]/).includes('..')) throw new Error('Invalid committed adapter manifest');
  const dir = path.join(home, r.current);
  if (!fs.statSync(dir).isDirectory()) throw new Error('Committed adapter generation is missing');
  return { dir, generation: r.current };
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
    this.active = false; this.wakeReq = false; this.wakeCounter = 0; this.privateAbort = null; this.privateBlocked = false; this.child = null; this.lastQuiz = null; this.since = null; this.phase = '';
    this.platform = o.platform || process.platform;
  }
  python() { return this.installer.pythonExe(); }
  privateChecker() { return this.o.privateChecker || require('./private-check').getPrivateCheck(this.root); }
  available() { return { ok: true, app: this.home, python: this.python(), reason: '' }; }
  // the adapter to load when the app starts the model (the newest converted one, if any)
  currentLora() {
    const st = this.installer.state();
    const base = Candidates.baseIdentity(this.root, st.hfDir);
    return Candidates.accepted(this.home, base);
  }
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
    if (this.wakeAtMs) {
      this.deadlineTimer = (this.o.setDeadlineTimer || setTimeout)(() => this.wake(), Math.max(0, this.wakeAtMs - Date.now()));
      if (this.deadlineTimer.unref) this.deadlineTimer.unref();
    }
    this._run().catch((e) => { this.exit = { error: String(e && e.message || e) }; this.active = false; });
    return { ok: true, pid: 0 };
  }
  wake() {
    this.wakeCounter++;
    this.wakeReq = true;
    if (this.privateAbort) this.privateAbort.abort();
    if (this.privateBlocked) {
      this.privateBlocked = false;
      Promise.resolve().then(() => this.privateChecker().ensureIdle()).then((r) => { if (r && r.ok && r.processStopped) return this._finishCandidate(true); this.privateBlocked = true; }).catch(() => { this.privateBlocked = true; });
    }
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
      const idle = await this.privateChecker().ensureIdle();
      if (!idle || !idle.ok || !idle.processStopped) throw new Error(idle && idle.error || 'A private adapter check has not stopped.');
      if (this.hooks.pauseModel) {
        const paused = await this.hooks.pauseModel();
        if (paused && paused.ok === false) throw new Error(paused.error || 'The chat model did not stop.');
      }
      for (let i = 0; i < 200 && !this.wakeReq; i++) {
        if (this.wakeAtMs && Date.now() + (CHUNK_BUDGET_S + CHUNK_STARTUP_MARGIN_S) * 1000 >= this.wakeAtMs) break;
        const out = await this._chunk();
        this._event({ kind: 'chunk', quiz: out.quiz == null ? null : out.quiz, steps: out.steps || 0, interrupted: !!out.interrupted, message: out.message || '', error: out.error || '' });
        if (out.blocked === true) { this.exit = { error: out.message || out.error || 'Sleep is blocked and needs a manual re-check.' }; break; }
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
    const lora = this.currentLora();
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
    if (this.hooks.pauseModel) {
      const paused = await this.hooks.pauseModel();
      if (paused && paused.ok === false) throw new Error(paused.error || 'The chat model did not stop.');
    }
    const p = CK.parseReply(res.reply);
    this.checkins = this.checkins || [];
    this.seenLines = this.seenLines || new Set();
    if (!res.error && !res.aborted && !p.nothing && !CK.isRepeat(this.seenLines, p.line)) { notified = 1; this.checkins.push(p.line); try { this.hooks.onCheckin && this.hooks.onCheckin(p.line); } catch (e) { /* ignore */ } }
    this._event({ kind: 'checkin', nothing: p.nothing, line: p.line, notified, aborted: !!res.aborted, error: res.error || '' });
    this.phase = 'sleeping';
  }

  // Checked adapters stay separate from candidates. A conversion or an
  // inconclusive served check never replaces the adapter used by chat.
  async _stageCandidate() {
    const st = this.installer.state(), n = this.night;
    if (!n || n.status !== 'done' || n.reverted || !n.date || !Number.isInteger(n.day) || !Number.isSafeInteger(n.night) || n.night < 1 || !st.convert || !st.hfDir) return;
    const state = Candidates.read(path.join(this.home, 'state.json'));
    const last = state && state.last_night;
    if (!last || !last.id || last.date !== n.date || last.reverted || state.nights !== n.night) return;
    if (!Candidates.orderKey({ date: n.date, night_number: n.night, created: new Date().toISOString(), id: '0'.repeat(64) })) return;
    const base = Candidates.baseIdentity(this.root, st.hfDir);
    const held = Candidates.heldSnapshot(path.join(this.home, 'cards.jsonl'), n.day);
    if (!base || !held.length) return;
    const committed = committedAdapter(this.home), source = path.join(committed.dir, 'adapter_model.safetensors');
    if (!fs.existsSync(source)) return;
    const sourceHash = Candidates.fileHash(source);
    const heldText = held.map((row) => JSON.stringify(row)).join('\n') + '\n';
    const id = Candidates.hash(JSON.stringify({ generation: committed.generation, night_id: last.id, base, sourceHash, held: Candidates.hash(heldText) }));
    const root = path.join(this.home, 'adapter-candidates'), dir = path.join(root, id);
    fs.mkdirSync(root, { recursive: true });
    if (fs.lstatSync(root).isSymbolicLink()) throw new Error('Invalid candidate folder');
    if (fs.existsSync(dir)) return;
    const temp = path.join(root, '.staging-' + require('crypto').randomUUID());
    fs.mkdirSync(temp);
    try {
      const candidate = path.join(temp, 'adapter.gguf');
      const cmd = convertCommand({ python: this.python(), convertScript: st.convert, adapterDir: committed.dir, hfDir: st.hfDir, outFile: candidate });
      this.phase = 'converting';
      await (this.o.run || require('./runtime/sleepinstall').defaultRun)(cmd.cmd, cmd.args, { env: { PYTHONUTF8: '1', HF_HUB_OFFLINE: '1' } });
      if (!fs.statSync(candidate).isFile() || !fs.statSync(candidate).size || fs.lstatSync(candidate).isSymbolicLink()) throw new Error('The converter wrote no adapter');
      const current = committedAdapter(this.home), latestNight = Candidates.read(path.join(this.home, 'state.json'));
      if (current.dir !== committed.dir || current.generation !== committed.generation || !latestNight || !latestNight.last_night || latestNight.last_night.id !== last.id || latestNight.nights !== n.night || Candidates.fileHash(source) !== sourceHash || JSON.stringify(Candidates.baseIdentity(this.root, st.hfDir)) !== JSON.stringify(base)) throw new Error('Model or night identity changed during conversion');
      fs.writeFileSync(path.join(temp, 'held.jsonl'), heldText, { flag: 'wx' });
      Candidates.atomic(path.join(temp, 'record.json'), { version: 1, id, status: 'pending', base, generation: committed.generation, night_id: last.id, date: n.date, night_number: n.night, day: n.day, source_sha256: sourceHash, adapter_sha256: Candidates.fileHash(candidate), held_sha256: Candidates.hash(heldText), held_count: held.length, created: new Date().toISOString() });
      fs.renameSync(temp, dir); this.converted = true; this._event({ kind: 'converted_candidate', id });
    } finally { if (fs.existsSync(temp)) fs.rmSync(temp, { recursive: true, force: true }); }
  }

  async _finishCandidate(skipCheck = false) {
    const wakeAtFinish = this.wakeCounter;
    let checker, idle;
    try { checker = this.privateChecker(); idle = await checker.ensureIdle(); }
    catch (e) { idle = { ok: false, error: String(e.message || e) }; }
    if (!idle || !idle.ok || !idle.processStopped) {
      this.privateBlocked = true; this.exit = { error: idle && idle.error || 'A private adapter check has not stopped.' };
      this.phase = 'stopping private check'; return;
    }
    try { await this._stageCandidate(); } catch (e) { this._event({ kind: 'convert_failed', error: String(e.message || e) }); }
    this.phase = 'waking';
    const tried = [];
    try {
      const st = this.installer.state();
      const identity = Candidates.baseIdentity(this.root, st.hfDir);
      const candidate = Candidates.pending(this.home, identity);
      if (candidate && !skipCheck && this.wakeCounter === wakeAtFinish) {
        const wakeAtCheck = this.wakeCounter;
        let verdict = candidate.rec.served;
        if (candidate.rec.status !== 'accepted' || !Candidates.validVerdict(verdict, candidate.rec.held_count)) {
          const runtime = Candidates.read(path.join(this.root, 'runtime', 'state.json')) || {};
          const model = runtime.model && runtime.model.file;
          const flavors = this.platform === 'darwin' ? ['metal'] : ['cpu', 'vulkan'];
          let engine = flavors.map(f => runtime.llama && runtime.llama[f] && { ...runtime.llama[f], flavor: f }).find(e => e && e.exe && fs.existsSync(e.exe));
          const bundled = process.resourcesPath && path.join(process.resourcesPath, 'llama', 'llama-server.exe');
          if (!engine && this.platform === 'win32' && bundled && fs.existsSync(bundled)) engine = { exe: bundled, flavor: 'cpu' };
          this.phase = 'checking the adapter';
          this.privateAbort = new AbortController();
          try {
            verdict = engine && model ? await checker.check({ exe: engine.exe, model, adapter: candidate.adapter, cards: candidate.held,
              python: this.python(), sleepmlxParent: this.parent, expectedAdapterSha256: candidate.rec.adapter_sha256,
              expectedHeldSha256: candidate.rec.held_sha256, flavor: engine.flavor, signal: this.privateAbort.signal }) : { ok: null, processStopped: true, reasons: ['private model engine is unavailable'] };
          } catch (e) { verdict = { ok: null, processStopped: false, error: String(e.message || e) }; }
          this.privateAbort = null;
          if (!verdict || verdict.processStopped !== true) {
            this.privateBlocked = true; this.exit = { error: verdict && verdict.error || 'A private adapter check has not stopped.' };
            this.phase = 'stopping private check'; return;
          }
          if (this.wakeCounter !== wakeAtCheck) verdict = { ok: null, reasons: ['checking was interrupted'] };
          const fresh = Candidates.inspect(this.home, candidate.id, Candidates.baseIdentity(this.root, st.hfDir));
          if (fresh) {
            const accepted = Candidates.validVerdict(verdict, fresh.rec.held_count);
            const rejected = verdict && verdict.ok === false && Candidates.validDecision(verdict, fresh.rec.held_count);
            fresh.rec.status = accepted ? 'accepted' : rejected ? 'rejected' : 'pending';
            fresh.rec.served = verdict;
            Candidates.atomic(path.join(fresh.dir, 'record.json'), fresh.rec);
            const promoted = accepted && Candidates.promote(this.home, fresh);
            tried.push({ lora: candidate.id.slice(0, 8), why: promoted ? 'passed its check' : accepted ? 'passed its check but its night ordering is unclear' : rejected ? 'did not pass its check' : 'check is pending' });
          }
        } else if (Candidates.validVerdict(verdict, candidate.rec.held_count)) {
          Candidates.promote(this.home, candidate);
        }
      }
      const chosen = this.currentLora();
      const up = this.hooks.resumeModel ? await this.hooks.resumeModel(chosen) : { ok: false };
      this.loaded = { lora: chosen ? path.basename(chosen) : '', candidate: !!chosen, newKept: !!(this.converted && candidate && chosen === candidate.adapter), tried, ok: !!(up && up.ok), error: up && up.error || '' };
      if (up && up.loraFailed) {
        const base = await this.hooks.resumeModel('');
        this.loaded = { lora: '', tried, ok: !!(base && base.ok), error: base && base.error || '' };
      }
      this._event({ kind: 'loaded', lora: this.loaded.lora || 'plain model', tried });
    } catch (e) {
      this.exit = this.exit || { error: String(e.message || e) };
      try { const chosen = this.currentLora(); const up = this.hooks.resumeModel ? await this.hooks.resumeModel(chosen) : null; this.loaded = { lora: chosen ? path.basename(chosen) : '', candidate: !!chosen, newKept: false, tried, ok: !!(up && up.ok) }; } catch (_) {}
    }
    this._writeSummary(); this.active = false; this.phase = '';
  }

  async _finish() {
    clearTimeout(this.deadlineTimer); this.deadlineTimer = null;
    try { fs.rmSync(path.join(this.home, 'ASSISTANT_RUNNING'), { force: true }); } catch (e) { /* none */ }
    this._writeStatus();
    return this._finishCandidate(this.wakeReq);
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
    if (this.loaded) lines.push(loadedLine(this.loaded, !!this.loaded.newKept && this.finishedNight && !n.reverted));
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
  const which = l.candidate ? (newKept ? "tonight's checked adapter" : 'a previously checked adapter') : l.lora === 'adapter.gguf' ? (newKept ? "tonight's adapter" : 'its newest adapter') : 'the previous adapter';
  return 'Glim now runs with ' + which + ' (' + l.lora + ').' + check + (tried ? ' Set aside: ' + tried + '.' : '');
}

module.exports = { WinSleep, lessonsSection, nightLines, loadedLine, sleepProfile, workerCommand, workerEnv, convertCommand, sleepmlxParent, mayStart, CHUNK_BUDGET_S };
