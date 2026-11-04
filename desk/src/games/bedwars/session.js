'use strict';
// Glim team, Bedwars side (plan v4.1 §3b, HARD REQUIREMENT): the self-sufficient play session. Glim decides to play (motivation ->
// wantToPlay()), then does every step itself through the BensPC tool (./benspc.js, contract ./TOOLS.md):
//   gpu-acquire -> server-start -> map-list / match-start -> client-launch -> play loop -> match-stop -> client-stop -> server-stop -> gpu-release
// Each step retries with backoff, reads the error text, and tries the tool's `next` alternatives (the runbook). It asks Ben ONLY when
// truly blocked: BensPC signed out (no signed-in session), a login it does not have, a purchase, or a UAC prompt.
// It ALWAYS stops what it started and releases the GPU, also on failure, abort or an exception. It never stops what it did not start
// (a server that was already running is reused and left running) and never names a pid: the tools stop only their own pids.json.
// The GPU being busy (Ben's duels first) is not a failure and never asks Ben: the session is 'deferred' and Glim does something else.
// Local server only (127.0.0.1), never Hypixel. Pure apart from the injected benspc / sleep / clock.

const { VERBS } = require('./benspc');

const ASK_BEN_REASONS = ['signed_out', 'login', 'purchase', 'uac'];
const BLOCKED = [
  ['signed_out', /no signed-in session|signed out|not signed in|sign in to benspc|logged off|no interactive session|session is locked out/i],
  ['uac', /\buac\b|user account control|elevation|run as administrator|administrator approval/i],
  ['login', /\blog ?in\b|microsoft account|password|credentials|authenticat|sign in to (minecraft|microsoft|lunar)/i],
  ['purchase', /\bpurchase\b|payment|\bpaid\b|billing|buy (minecraft|a licen[cs]e)|licen[cs]e required/i]
];
function blockedReason(text) { const s = String(text || ''); for (const [k, re] of BLOCKED) if (re.test(s)) return k; return null; }
const GPU_BUSY = /busy|in use|held by|not free/i;
// runbook alternatives a step may run from `next` (stop verbs only inside the start step of the same thing; see header)
const ALT_READ = ['ping', 'disk', 'gpu-status', 'server-status', 'map-list', 'match-status', 'log-read'];
const ALT_STOP = { 'server-start': 'server-stop', 'match-start': 'match-stop', 'client-launch': 'client-stop' };
const LOCAL_SERVER = /^(127\.0\.0\.1|localhost):\d{2,5}$/;
const WHO = 'glim-bedwars';

const DEFAULTS = { retries: 3, backoffMs: 2000, name: 'GlimBot', mode: '1v1', opponent: 'scripted:L2', maxPlayMs: 10 * 60000, pollMs: 2000,
  why: 'Glim wants to play Bedwars (its own choice, plan 3b)' };

class PlaySession {
  // o: {benspc, askBen(reason, detail), sleep(ms), now(), log, map, opponent, play(ctx) -> {ok, why, events}, retries, backoffMs, ...}
  constructor(o) {
    o = o || {}; if (!o.benspc) throw new Error('PlaySession needs a benspc client');
    this.o = { ...DEFAULTS, ...o }; this.pc = o.benspc; this.now = o.now || Date.now; this.log = o.log || (() => {});
    this.sleep = o.sleep || ((ms) => new Promise((r) => setTimeout(r, ms)));
    this.askBenFn = o.askBen || (() => {});
    this.res = { outcome: null, ok: false, askedBen: null, steps: [], cleanup: [], calls: [], matchId: null, map: null, events: [],
      reached: { decide: true, launch: false, match: false, play: false, quit: false } };
    this.own = { gpu: false, gpuUnsure: false, server: false, match: false, client: false };
  }
  async call(verb, args) { const r = await this.pc.call(verb, args); this.res.calls.push({ verb, ok: !!(r && r.ok), error: r && r.error ? String(r.error).slice(0, 200) : null }); return r || { ok: false, error: 'no reply', next: [] }; }
  askBen(reason, detail) {
    if (!ASK_BEN_REASONS.includes(reason)) { this.log('not asking Ben (' + reason + ' is not a blocked case): ' + detail); return false; }
    if (!this.res.askedBen) { this.res.askedBen = { reason, detail: String(detail || '').slice(0, 200) }; try { this.askBenFn(reason, detail); } catch (e) { /* the message is best effort */ } }
    return true;
  }
  aborted(ctl) { return !!((ctl.signal && ctl.signal.aborted) || (ctl.gateOk && !ctl.gateOk())); }

  // one step: retries + backoff + error reading + runbook alternatives. o: {check() -> ok-ish result when an uncertain call ran}
  async attempt(step, verb, args, ctl, o) {
    o = o || {}; const rec = { step, verb, ok: false, tries: 0, errors: [], alternatives: [] }; this.res.steps.push(rec);
    const triedAlt = new Set(); let last = null, uncertain = false;
    for (let k = 1; k <= this.o.retries; k++) {
      rec.tries = k;
      let r = await this.call(verb, args); last = r;
      if (!r.ok && r.uncertain) uncertain = true;
      // an uncertain call may have run; a refusal (noRetry, e.g. "GPU busy") may be our own earlier call: check before giving up
      if (!r.ok && o.check && (r.uncertain || (o.noRetry && o.noRetry(r)))) { const c = await o.check(); if (c && c.ok) r = c; }
      if (r.ok) { rec.ok = true; return { ok: true, r, rec }; }
      rec.errors.push(String(r.error || 'unknown error').slice(0, 200));
      // a transport error is our ssh talking (e.g. "Permission denied (publickey,password)"), not BensPC being blocked: retry it
      const b = r.transport ? null : blockedReason(r.error) || (r.next || []).map((n) => /^ask-ben/i.test(String(n)) ? blockedReason(n) : null).find(Boolean);
      if (b) { this.askBen(b, r.error); rec.blocked = b; return { ok: false, blocked: b, r, rec, uncertain }; }
      if (o.noRetry && o.noRetry(r)) return { ok: false, r, rec, stop: true, uncertain };
      for (const n of r.next || []) {
        const v = String(n).trim().split(/[\s:]/)[0];
        if (!VERBS.includes(v) || triedAlt.has(v) || v === verb) { rec.alternatives.push({ hint: String(n).slice(0, 120), ran: false }); continue; }
        if (!(ALT_READ.includes(v) || ALT_STOP[verb] === v)) { rec.alternatives.push({ hint: v, ran: false, why: 'not allowed here' }); continue; }
        triedAlt.add(v); const a = await this.call(v, {}); rec.alternatives.push({ hint: v, ran: true, ok: !!a.ok });
      }
      if (this.aborted(ctl) || k === this.o.retries) break;
      await this.sleep(this.o.backoffMs * Math.pow(2, k - 1));
    }
    return { ok: false, r: last, rec, uncertain };
  }

  async run(ctl) {
    ctl = ctl || {}; const res = this.res; res.startedAt = this.now();
    try { await this.steps(ctl); }
    catch (e) { res.outcome = res.outcome || 'failed'; res.error = String(e && e.message || e).slice(0, 200); }
    finally { await this.cleanup(); }
    res.endedAt = this.now();
    res.reached.quit = res.cleanup.every((c) => c.ok) && !this.own.gpu;
    res.ok = res.outcome === 'played' && res.reached.quit;
    return res;
  }

  async steps(ctl) {
    const res = this.res, o = this.o;
    // 1. the GPU (GPU_LOAN.txt): busy = deferred, never ask Ben
    const g = await this.attempt('gpu-acquire', 'gpu-acquire', { who: WHO, why: o.why }, ctl, {
      noRetry: (r) => GPU_BUSY.test(String(r.error || '')),
      check: async () => { const s = await this.call('gpu-status', {}); return s.ok && s.holder === WHO ? { ok: true, holder: WHO } : null; } });
    if (!g.ok) { if (g.uncertain) this.own.gpuUnsure = true; res.outcome = g.blocked ? 'blocked' : g.stop ? 'deferred' : 'failed'; return; }
    this.own.gpu = true;
    if (this.aborted(ctl)) { res.outcome = 'yielded'; return; }
    // 2. the server: reuse one that is already up (and leave it up), else start ours
    let port = null; const st = await this.call('server-status', {});
    if (st.ok && st.running) { port = st.port; res.steps.push({ step: 'server-start', verb: 'server-status', ok: true, tries: 1, reused: true }); }
    else {
      const s = await this.attempt('server-start', 'server-start', o.map ? { map: o.map } : {}, ctl, {
        check: async () => { const x = await this.call('server-status', {}); return x.ok && x.running ? { ok: true, port: x.port, pid: x.pid } : null; } });
      if (!s.ok) { res.outcome = s.blocked ? 'blocked' : 'failed'; return; }
      this.own.server = true; port = s.r.port;
    }
    if (this.aborted(ctl)) { res.outcome = 'yielded'; return; }
    // 3. a map and a match
    const ml = await this.attempt('map-list', 'map-list', {}, ctl);
    if (!ml.ok) { res.outcome = ml.blocked ? 'blocked' : 'failed'; return; }
    const maps = (ml.r.maps || []).map(String);
    if (!maps.length) { res.steps.push({ step: 'map-list', ok: false, errors: ['no maps'] }); res.outcome = 'failed'; return; }
    res.map = o.map && maps.includes(o.map) ? o.map : maps[0];
    const m = await this.attempt('match-start', 'match-start', { map: res.map, mode: o.mode, opponent: o.opponent }, ctl, {
      check: async () => { const x = await this.call('match-status', {}); return x.ok && x.state && x.state !== 'none' && x.state !== 'ended' ? { ok: true, match_id: x.match_id || null } : null; } });
    if (!m.ok) { res.outcome = m.blocked ? 'blocked' : 'failed'; return; }
    this.own.match = true; res.matchId = m.r.match_id || null;
    // 4. the client: our offline launcher, local server only
    const server = '127.0.0.1:' + (port || 25565);
    if (!LOCAL_SERVER.test(server)) { res.outcome = 'failed'; res.error = 'refusing a non-local server'; return; }
    const c = await this.attempt('client-launch', 'client-launch', { name: o.name, server }, ctl, {
      check: async () => { const x = await this.call('match-status', {}); return x.ok && (x.teams || []).length ? { ok: true } : null; } });
    if (!c.ok) { res.outcome = c.blocked ? 'blocked' : 'failed'; return; }
    this.own.client = true; res.reached.launch = true; res.reached.match = true;   // the client is in the match we started
    // 5. play
    const p = await this.play(ctl);
    res.events = p.events || []; res.play = { ok: !!p.ok, why: p.why || null };
    res.steps.push({ step: 'play', ok: !!p.ok, tries: 1, errors: p.ok ? [] : [p.why || 'play failed'] });
    res.reached.play = !!p.ok;
    res.outcome = p.yielded ? 'yielded' : p.ok ? 'played' : 'failed';
  }

  // the play loop. The real reflex runs next to the game on BensPC; from here we watch the match and read the truth log.
  // o.play(ctx) replaces it (ctx: {benspc, matchId, signal, gateOk, call}). Ends at match end, maxPlayMs, abort or Ben-first yield.
  async play(ctl) {
    if (this.o.play) return this.o.play({ benspc: this.pc, matchId: this.res.matchId, signal: ctl.signal, gateOk: ctl.gateOk, call: (v, a) => this.call(v, a) });
    const t0 = this.now(), events = []; let since = new Date(t0 - 5000).toISOString(), running = false, fails = 0;
    while (true) {
      if (this.aborted(ctl)) return { ok: running, yielded: true, why: 'Ben first: yielded', events };
      const s = await this.call('match-status', {});
      if (s.ok) { fails = 0; if (s.state === 'running') running = true; } else if (++fails >= 5) return { ok: false, why: 'match-status failed 5 times: ' + s.error, events };
      const lr = await this.call('log-read', { since, max: 500 });
      if (lr.ok) { for (const e of lr.events || []) events.push(e); if (lr.next_since) since = lr.next_since; }
      if (s.ok && (s.state === 'ended' || s.state === 'over')) return { ok: running || events.some((e) => e.type === 'match_start'), why: 'match ended', events };
      if (this.now() - t0 >= this.o.maxPlayMs) return { ok: running, why: 'time limit', events };
      await this.sleep(this.o.pollMs);
    }
  }

  // stop what we started, newest first; then the GPU. Never throws.
  async cleanup() {
    const own = this.own, out = this.res.cleanup;
    const stop = async (what, verb) => {
      let ok = false, err = null;
      for (let k = 1; k <= this.o.retries && !ok; k++) {
        try { const r = await this.call(verb, {}); ok = !!r.ok; err = r.error || null; } catch (e) { err = String(e && e.message || e); }
        if (!ok && k < this.o.retries) try { await this.sleep(this.o.backoffMs); } catch (e) { /* keep going */ }
      }
      out.push({ what, verb, ok, error: ok ? null : err });
      return ok;
    };
    if (own.client && await stop('client', 'client-stop')) own.client = false;
    if (own.match && await stop('match', 'match-stop')) own.match = false;
    if (own.server && await stop('server', 'server-stop')) own.server = false;
    if (own.gpuUnsure) { try { const s = await this.call('gpu-status', {}); if (s.ok && s.holder === WHO) own.gpu = true; } catch (e) { own.gpu = true; } }
    if (own.gpu && await stop('gpu', 'gpu-release')) own.gpu = false;
  }
}

// the activity descriptor the motivation / bored path can run (a Mote-pool job: {kind, topic, run(ctl)}; ctl = {signal, gateOk, ask}).
// o: the PlaySession options (benspc is required when it runs). o.enabled === false -> null (nothing to do).
function wantToPlay(o) {
  o = o || {}; if (o.enabled === false) return null;
  return { kind: 'game:bedwars', topic: 'play Bedwars on BensPC (local server, ' + (o.mode || DEFAULTS.mode) + ')', realtime: true, needs: ['benspc', 'gpu'],
    run: (ctl) => new PlaySession(o).run(ctl || {}) };
}

module.exports = { PlaySession, wantToPlay, blockedReason, ASK_BEN_REASONS, DEFAULTS, WHO, LOCAL_SERVER };
