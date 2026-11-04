'use strict';
// Glim's hands (track I5, Ben 2026-11-04): "It should definitely be able to click anywhere on the screen or type anything, but it
// should make sure to not interrupt the user. If it does, that is a huge negative and should be trained on in sleep."
//
//  1. FREEZE (always on): the user's own mouse/keyboard input during a Glim action stops it at once -> "[stopped: Ben is using the
//     computer]". Glim's own posted events also reset the Mac's idle clock, so they must not count: the deskhelper tags every event it
//     posts (CGEvent eventSourceUserData = GLIM_TAG) and `deskhelper watch-input` reports only UNTAGGED events (HelperWatch below).
//     Without that stream (old helper, Windows) the fallback reads system idle time and ignores input inside Glim's own action windows;
//     the fallback cannot see user input DURING an action (no freeze there), only between actions.
//  2. QUIET HANDS FIRST: an action that does not move the cursor or steal focus is tried first (AX press without the click fallback,
//     opening an app in the background). Quiet actions need no idle wait and no ask (the category levels still apply).
//  3. REAL MOUSE + KEYBOARD: only after the user has been idle >= 2 min (setting, never lower), then ONE ask per run (tap card
//     Yes / No / Always allow + a notification). No answer within 1 min (setting) while the user stays away -> go ahead. "No" -> don't,
//     logged. User active -> wait (up to 10 min per call, then the model is told to use quiet tools or try later).
//  4. INTERRUPTION LOG (day memory, features only, for the sleep-trained judge src/goodtime.js): collisions, undo/close (cmd+z / cmd+w)
//     within 30 s of a Glim action, "stop" / "not now" in chat, "No" answers, clean actions, and passive watch rows.
// The judge (setting hands.judge, OFF until its toy passes) is VETO ONLY: it can make Glim wait longer, never act sooner.
const GT = require('./goodtime');

const QUIET = { screen_click: (a) => a && a.id != null, open_app: () => true };
const REAL = new Set(['screen_click', 'screen_type', 'screen_key', 'open_app']);
const STOPPED = '[stopped: Ben is using the computer]';
const UNDO_MS = 30000, WATCH_EVERY = 60000, WATCH_MIN_S = 120, WATCH_MAX_S = 1800, WAIT_MAX = 10 * 60000;

// ---- who touched the computer: the user's own input only ------------------------------------------------------------------------------
class InputWatch {
  constructor(o) {
    o = o || {}; this.now = o.now || Date.now;
    this.lastUser = this.now();         // unknown at start: assume the user was just here (Glim must wait the full idle time)
    this.inputs = [];                   // user input times (deduped to 1 s), last 31 min
    this.pauses = [];                   // {end, len} gaps >= 30 s, last 30 min
    this.glim = null; this.glimWins = [];
    this.subs = new Set(); this.source = 'none';
  }
  onUser(fn) { this.subs.add(fn); return () => this.subs.delete(fn); }
  // one event of the USER's own input (never Glim's: the helper drops tagged events; the fallback drops Glim's windows)
  userInput(t, kind) {
    t = t || this.now(); kind = kind || 'in';
    const gap = t - this.lastUser;
    if (gap >= 30000) this.pauses.push({ end: t, len: gap });
    if (t > this.lastUser) this.lastUser = t;
    const last = this.inputs[this.inputs.length - 1];
    if (!last || t - last >= 1000) this.inputs.push(t);
    this.prune(t);
    for (const fn of [...this.subs]) { try { fn(kind, t); } catch (e) { /* a listener never breaks input */ } }
  }
  prune(now) {
    while (this.inputs.length && this.inputs[0] < now - 31 * 60000) this.inputs.shift();
    while (this.pauses.length && this.pauses[0].end < now - 30 * 60000) this.pauses.shift();
    while (this.glimWins.length && this.glimWins[0].e < now - 60000) this.glimWins.shift();
  }
  glimStart() { this.glim = { s: this.now(), e: Infinity }; }
  glimEnd() { if (this.glim) { this.glim.e = this.now(); this.glimWins.push(this.glim); this.glim = null; } }
  inGlimWindow(t) { const pad = 1500; if (this.glim && t >= this.glim.s - 200) return true; return this.glimWins.some((w) => t >= w.s - 200 && t <= w.e + pad); }
  // fallback source: the system idle clock (it counts Glim's own events too, so input inside Glim's windows is ignored)
  fromIdleSample(idleS, now) {
    now = now || this.now();
    const tIn = now - Math.max(0, Number(idleS) || 0) * 1000;
    if (tIn > this.lastUser + 900 && !this.inGlimWindow(tIn)) this.userInput(tIn, 'in');
  }
  idleMs(now) { return (now || this.now()) - this.lastUser; }
  firstInputAfter(t) { for (const x of this.inputs) if (x > t) return x; return this.lastUser > t ? this.lastUser : null; }
  features(now, app) {
    now = now || this.now(); this.prune(now);
    const slots = new Set(this.inputs.filter((x) => x >= now - 30 * 60000).map((x) => Math.floor(x / 5000)));
    const p = this.pauses.filter((x) => x.end >= now - 30 * 60000);
    return { hour: new Date(now).getHours() + new Date(now).getMinutes() / 60, app: app || 'other', idleS: Math.round(this.idleMs(now) / 1000), pauses30: p.length, lastPauseS: p.length ? Math.round(p[p.length - 1].len / 1000) : 0, activeMin30: slots.size * 5 / 60 };
  }
}

// `deskhelper watch-input` as a long-running child: one JSON line per user event {"k":"in"|"undo"|"close","t":ms}; {"k":"ready"} first.
// o: {spawn() -> child process, input: InputWatch, log, setTimeout}
class HelperWatch {
  constructor(o) { this.o = o; this.child = null; this.ready = false; this.fails = 0; this.stopped = false; this.timer = null; }
  start() {
    if (this.stopped || this.child) return;
    let ch; try { ch = this.o.spawn(); } catch (e) { return this.retry('spawn: ' + (e && e.message || e)); }
    if (!ch) return this.retry('no helper');
    this.child = ch; let buf = '';
    ch.stdout.on('data', (d) => {
      buf += String(d); let i;
      while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); this.line(line); }
    });
    ch.on('exit', () => { this.child = null; this.ready = false; this.retry('exited'); });
    ch.on('error', () => { /* exit follows */ });
  }
  line(l) {
    let j; try { j = JSON.parse(l); } catch (e) { return; }
    if (j.error) { this.log('watch-input: ' + j.error); return; }
    if (j.k === 'ready') { this.ready = true; this.fails = 0; this.o.input.source = 'helper'; return; }
    if (j.k) this.o.input.userInput(Number(j.t) || undefined, j.k);
  }
  retry(why) {
    if (this.stopped) return;
    this.fails++; this.log('watch-input ' + why + ' (try ' + this.fails + ')');
    const ms = Math.min(5 * 60000, 5000 * 2 ** Math.min(6, this.fails - 1));
    const st = this.o.setTimeout || setTimeout;
    this.timer = st(() => { this.timer = null; this.start(); }, ms); if (this.timer && this.timer.unref) this.timer.unref();
  }
  stop() { this.stopped = true; if (this.timer) clearTimeout(this.timer); try { if (this.child) this.child.kill(); } catch (e) { /* gone */ } this.child = null; }
  log(m) { try { if (this.o.log) this.o.log(m); } catch (e) { /* ignore */ } }
}

// ---- the hands ---------------------------------------------------------------------------------------------------------------------
// o: {input: InputWatch, levels: SafetyLevels, now, sleep(ms, signal), askUser(question, signal, options) -> Promise<answer>,
//     notify(text), notice({text, undo}), status(text), record(row) (judge day log), judge() -> model|null, frontApp() -> category}
class Hands {
  constructor(o) {
    this.o = o; this.now = o.now || Date.now; this.input = o.input;
    this.sleep = o.sleep || ((ms, signal) => new Promise((r) => { const t = setTimeout(r, ms); if (signal) signal.addEventListener('abort', () => { clearTimeout(t); r(); }, { once: true }); }));
    this.grants = new WeakMap();   // run signal -> {ok, denied, ask}
    this.pendingClean = null; this.watch = []; this.lastWatch = 0; this.acting = null; this.lastAction = null;
    this.input.onUser((kind, t) => this.onUser(kind, t));
  }
  isHands(name) { return REAL.has(name); }
  rec(row) { try { if (this.o.record) this.o.record(row); } catch (e) { /* logging never breaks the hands */ } }
  feats() { let app = 'other'; try { app = (this.o.frontApp && this.o.frontApp()) || 'other'; } catch (e) { /* unknown */ } return this.input.features(this.now(), app); }
  onUser(kind, t) {
    const p = this.pendingClean;
    if (p && (kind === 'undo' || kind === 'close') && t - p.end <= UNDO_MS) { this.pendingClean = null; this.rec({ t: p.t, f: p.f, y: 1, src: kind }); }
  }
  // Ben's own chat words right after (or during) a Glim action: "stop" / "not now" is an interruption label
  onBenText(text) {
    const s = String(text || '').toLowerCase();
    if (!/\b(stop|not now|don'?t do that|leave it|quit it|cut it out)\b/.test(s)) return false;
    const a = this.acting || (this.lastAction && this.now() - this.lastAction.end <= 120000 ? this.lastAction : null);
    if (!a) return false;
    if (this.pendingClean && this.pendingClean.t === a.t) this.pendingClean = null;
    this.rec({ t: a.t, f: a.f, y: 1, src: 'stop' }); return true;
  }
  // every ~15 s from main: passive watch rows (labelled later from the input stream), finalize clean actions after the undo window
  tick() {
    const now = this.now();
    if (this.pendingClean && now - this.pendingClean.end > UNDO_MS) { const p = this.pendingClean; this.pendingClean = null; this.rec({ t: p.t, f: p.f, y: 0, src: 'clean' }); }
    const idleS = this.input.idleMs(now) / 1000;
    if (!this.acting && idleS >= WATCH_MIN_S && idleS <= WATCH_MAX_S && now - this.lastWatch >= WATCH_EVERY) { this.lastWatch = now; this.watch.push({ t: now, f: this.feats() }); }
    const H = GT.H * 1000;
    while (this.watch.length && this.watch[0].t + H <= now) {
      const w = this.watch.shift(), x = this.input.firstInputAfter(w.t);
      this.rec({ t: w.t, f: w.f, y: x != null && x <= w.t + H ? 1 : 0, src: 'watch' });
    }
  }
  vetoed() {
    const h = this.o.levels.hands(); if (!h.judge || !this.o.judge) return false;
    let m = null; try { m = this.o.judge(); } catch (e) { return false; }
    return GT.veto(m, this.feats()).veto;
  }
  idleEnough() { return this.input.idleMs(this.now()) >= this.o.levels.hands().idleMin * 60000; }
  status(t) { try { if (this.o.status) this.o.status(t); } catch (e) { /* ui only */ } }

  // run one hands tool. run(args, ctx) = the real tool; sv = the safety check ({level of the category}); -> tool result
  async act(name, args, ctx, run, sv) {
    const signal = ctx.signal, L = this.o.levels;
    const lvl = L.level('hands');
    if (lvl === 'never') return { text: 'Not allowed: using the mouse and keyboard is set to Never. Use quiet tools (the built-in browser, files) or tell Ben what you need.', error: true };
    // 2. quiet hands first
    if (QUIET[name] && QUIET[name](args)) {
      try {
        const q = await run({ ...args, quiet: true }, ctx);
        const txt = typeof q === 'string' ? q : (q && q.text) || '';
        if (!(q && q.error) && !/^Error:/.test(txt)) return q;
      } catch (e) { /* fall through to real hands */ }
      if (signal && signal.aborted) return { text: '[stopped by user]', error: true };
    }
    // 3. real mouse and keyboard: idle >= 2 min, then one ask per run, then go
    if (ctx.helper && lvl === 'ask') return { text: 'A background Glim never uses the real mouse and keyboard (it would have to ask Ben). Use quiet tools, or finish with a short report saying what needs the mouse.', error: true };
    let g = this.grants.get(signal); if (!g) { g = { ok: false, denied: false, ask: null }; if (signal) this.grants.set(signal, g); }
    if (g.denied) return { text: 'Ben said no to using the mouse and keyboard during this task. Do not retry; use quiet tools or finish with what you have.', error: true };
    const deadline = this.now() + WAIT_MAX; let said = false;
    const needAsk = () => lvl === 'ask' && !g.ok;
    for (;;) {
      if (signal && signal.aborted) return { text: '[stopped by user]', error: true };
      // the judge vetoes ONLY going ahead without an answer (toy v3: vetoing the ask itself blocked consented actions)
      const idle = this.idleEnough(); let veto = false;
      if (idle) {
        if (!needAsk()) { if (!(veto = this.vetoed())) break; }
        else {
          if (!g.ask) g.ask = this.startAsk(name, args, ctx);
          const a = g.ask;
          if (a.answer != null) {
            const v = answerOf(a.answer);
            if (v === 'always') { const r = L.set([{ cat: 'hands', level: 'free' }], { source: 'tap-card' }); if (r.ok && this.o.notice) this.o.notice({ text: r.notice, undo: r.undo }); g.ok = true; break; }
            if (v === 'yes') { g.ok = true; break; }
            g.denied = true; this.rec({ t: this.now(), f: this.feats(), y: 1, src: 'no' });
            return { text: 'Ben said no to using the mouse and keyboard now. Do not retry; use quiet tools or finish with what you have.', error: true, summary: 'Ben said not now' };
          }
          if (this.now() - Math.max(a.shownAt, this.input.lastUser) >= L.hands().askWaitS * 1000 && !(veto = this.vetoed())) {   // no answer in time while the user stays away
            g.ok = true; try { a.ac.abort(); } catch (e) { /* closed */ }
            if (this.o.notice) this.o.notice({ text: 'No answer in ' + Math.round(L.hands().askWaitS / 60 * 10) / 10 + ' min, so Glim is using the mouse for a moment. Touch it any time to stop.' });
            break;
          }
        }
      }
      if ((!idle || veto) && !said) { said = true; this.status(veto ? 'Waiting for a better moment to use the mouse' : 'Waiting until you step away to use the mouse'); }
      if (this.now() >= deadline) return { text: '[waiting: Ben is using the computer. Use quiet tools (the built-in browser, files), or try this step again later.]', error: true, summary: 'Waited: you were using the computer' };
      await this.sleep(1000, signal);
    }
    // 1. freeze: the user's own input during the action stops it
    const ac = new AbortController(); const onAbort = () => ac.abort();
    if (signal) { if (signal.aborted) return { text: '[stopped by user]', error: true }; signal.addEventListener('abort', onAbort, { once: true }); }
    let collided = false;
    const off = this.input.onUser((kind) => { if (kind === 'ready') return; collided = true; ac.abort(); });
    const f = this.feats(), t0 = this.now();
    this.acting = { t: t0, f }; this.input.glimStart();
    let r, err = null;
    try { r = await run(args, { ...ctx, signal: ac.signal }); } catch (e) { err = e; }
    finally { this.input.glimEnd(); off(); if (signal) signal.removeEventListener('abort', onAbort); this.acting = null; }
    this.lastAction = { t: t0, f, end: this.now() };
    if (collided) { this.rec({ t: t0, f, y: 1, src: 'collision' }); this.status('Stopped: you are using the computer'); return { text: STOPPED, error: true, summary: 'Stopped: you are using the computer' }; }
    if (err) throw err;
    if (this.pendingClean) this.rec({ t: this.pendingClean.t, f: this.pendingClean.f, y: 0, src: 'clean' });
    this.pendingClean = { t: t0, f, end: this.now() };
    return r;
  }
  // freeze only (no idle wait, no ask): for actions Ben has just started himself (watch-me "Redo it" after his OK)
  async freezeOnly(fn) {
    const ac = new AbortController(); let collided = false;
    const off = this.input.onUser((kind) => { if (kind === 'ready') return; collided = true; ac.abort(); });
    this.input.glimStart();
    try { const r = await fn(ac.signal); return collided ? { text: STOPPED, error: true } : r; } finally { this.input.glimEnd(); off(); }
  }
  startAsk(name, args, ctx) {
    const what = String(ctx.summary || '').replace(/^(Pressed|Clicked|Typed|Pressed keys)\b/i, (m) => m.toLowerCase()) || 'finish this task';
    const q = 'Can I use the mouse and keyboard for a moment to ' + what.replace(/\.$/, '') + '?';
    const ac = new AbortController(); if (ctx.signal) ctx.signal.addEventListener('abort', () => ac.abort(), { once: true });
    const a = { shownAt: this.now(), answer: null, ac, question: q };
    try { if (this.o.notify) this.o.notify(q); } catch (e) { /* nicety */ }
    const ask = ctx.askUser || this.o.askUser;   // the run's own thread card (agent.js passes it), else the main one
    Promise.resolve().then(() => ask(q, ac.signal, ['Yes', 'No', 'Always allow'])).then((x) => { if (!ac.signal.aborted) a.answer = x; }, () => { /* closed */ });
    return a;
  }
}
const answerOf = (a) => { const s = String(a || '').trim().toLowerCase(); if (/^always/.test(s)) return 'always'; if (/^(y|yes|ok|okay|sure|go|go ahead|fine)\b/.test(s)) return 'yes'; return 'no'; };

module.exports = { Hands, InputWatch, HelperWatch, QUIET, REAL, STOPPED, UNDO_MS, answerOf };
