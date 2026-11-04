'use strict';
// I3 two-speed core, part 4: the REFLEX and its SLEEP HOOK. Game-agnostic.
// The reflex outputs (action, time-to-go): an action head (adapter features + the current call -> one of nA moves) and a timing head
// (the schedule's unit-free tau features -> a correction in seconds to the fitted time-to-contact).
// Sleep (nightly), from the DAY's real frames only (no games at night, nothing is played or practised):
//   1. replay the logged frames of the last poolDays days (each day: first 80 % train, last 20 % held out, never trained on);
//   2. label (timing: only samples whose plain estimate is inside schedule.ZONE, where firing is decided): actions by the adapter's slow night labeller (it reads the day's truth log, at its own pace); times by HINDSIGHT
//      (the true seconds until contact, known once it happened);
//   3. distil a candidate from the current reflex (or a fresh net);
//   4. SEATBELT on held-out day replays, head by head: on the newest day's held-out frames a head's action agreement may not drop
//      > 2 points / its timing error may not grow > 1 ms; on the OLDER days' held-out frames it may not get worse at all (v2: a
//      poisoned day poisons its own held-out too, so only the older days are a clean referee); and it must improve on the newest
//      held-out day. A head that fails keeps yesterday's version (or none: the hand rule / plain tau);
//   5. keep (model.prev.json kept for rollback()) or roll back. Logged to nightly.jsonl. Any error skips the step (crash-safe).
const fs = require('fs');
const path = require('path');
const { MLP, rng, softmax } = require('../../tinynet');
const { ZONE } = require('./schedule');

const NT = 5;   // timing features (schedule.TauEstimator.features)
const DEFAULTS = { hidden: 32, tHidden: 16, steps: 1500, tSteps: 1500, batch: 64, lr: 0.002, tlr: 0.003, poolDays: 7, maxPerDay: 20000, agreeTol: 0.02, timeTol: 1.0, anchorAgreeTol: 0, anchorTimeTol: 0 };
const argmax = (o) => { let b = 0; for (let k = 1; k < o.length; k++) if (o[k] > o[b]) b = k; return b; };

class ReflexNet {
  constructor(act, tim) { this.act = act || null; this.tim = tim || null; }
  action(x) { return this.act ? argmax(this.act.forward(x).o) : null; }
  timing() { const t = this.tim; return t ? (f) => t.forward(f).o[0] : null; }
  toJSON() { return { act: this.act && this.act.toJSON(), tim: this.tim && this.tim.toJSON() }; }
  static fromJSON(j) { return new ReflexNet(j.act ? MLP.fromJSON(j.act) : null, j.tim ? MLP.fromJSON(j.tim) : null); }
}

const dayKey = (t) => { const d = new Date(t); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
function readJson(p) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; } }
function writeJson(p, v) { const tmp = p + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(v)); fs.renameSync(tmp, p); }
function readLines(p) { try { return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { return []; } }

class ReflexSleep {
  // o: {dir, now, log, cfg}
  constructor(o) {
    this.o = o || {}; this.dir = this.o.dir || '.'; this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.cfg = { ...DEFAULTS, ...(this.o.cfg || {}) }; this.net = null;
    try { fs.mkdirSync(this.dir, { recursive: true }); } catch (e) { /* later */ }
    const j = readJson(path.join(this.dir, 'model.json')); if (j && j.net) { try { this.net = ReflexNet.fromJSON(j.net); } catch (e) { this.net = null; } }
  }
  ready() { return !!this.net; }
  // the day's experience: acts [{r: raw frame, a: action taken}], times [{f, q, y}] (schedule.hindsight())
  logDay(acts, times) {
    const f = path.join(this.dir, 'frames-' + dayKey(this.now()) + '.jsonl');
    try {
      let n = 0; try { n = fs.readFileSync(f, 'utf8').split('\n').length; } catch (e) { /* new day */ }
      const lines = [...(acts || []).map((x) => JSON.stringify({ k: 'a', r: x.r, a: x.a })), ...(times || []).map((x) => JSON.stringify({ k: 't', f: x.f, q: x.q, y: x.y }))];
      const room = Math.max(0, this.cfg.maxPerDay - n); if (!room) return 0;
      fs.appendFileSync(f, lines.slice(0, room).join('\n') + '\n'); return Math.min(room, lines.length);
    } catch (e) { this.log('reflex-core: frames not saved', e); return 0; }
  }
  // ad: {features(raw) -> x, label(raw) -> action|null, fallback(raw) -> action, nIn, nA}; opts: {poison, seed}
  nightly(ad, opts) {
    try { return this._nightly(ad, opts || {}); } catch (e) { return this.record({ at: this.now(), kind: 'reflex-core-nightly', kept: false, why: 'error: ' + (e && e.message) }); }
  }
  _nightly(ad, opts) {
    const cfg = this.cfg, r = rng(opts.seed || 13), rec = { at: this.now(), kind: 'reflex-core-nightly' };
    let files = []; try { files = fs.readdirSync(this.dir).filter((n) => /^frames-\d{4}-\d{2}-\d{2}\.jsonl$/.test(n)).sort().slice(-cfg.poolDays); } catch (e) { /* none */ }
    if (!files.length) return this.record({ ...rec, kept: false, why: 'no frames today' });
    const train = { a: [], t: [] }, held = { a: [], t: [] }, anchor = { a: [], t: [] };
    files.forEach((name, di) => {
      const newest = di === files.length - 1, lines = readLines(path.join(this.dir, name));
      for (const kind of ['a', 't']) {
        const xs = lines.filter((l) => l.k === kind), cut = Math.floor(xs.length * 0.8);
        xs.forEach((l, i) => {
          let it;
          if (kind === 'a') { const y = ad.label(l.r); if (y == null) return; it = { x: ad.features(l.r), y, raw: l.r }; if (newest && opts.poison && r() < opts.poison) it.y = (y + 1 + Math.floor(r() * (ad.nA - 1))) % ad.nA; }
          else { if (!(l.q <= ZONE)) return; it = { x: Float64Array.from(l.f), y: l.y - l.q, q: l.q, yt: l.y }; if (newest && opts.poison && r() < opts.poison) { it.yt = r() * 2; it.y = it.yt - l.q; } }
          if (i < cut) train[kind].push(it); else if (newest) held[kind].push(it); else anchor[kind].push(it);
        });
      }
    });
    rec.train = { a: train.a.length, t: train.t.length }; rec.held = { a: held.a.length, t: held.t.length }; rec.anchor = { a: anchor.a.length, t: anchor.t.length };
    if (!train.a.length && !train.t.length) return this.record({ ...rec, kept: false, why: 'too few frames' });
    const cur = this.net;
    let act = cur && cur.act ? cur.act.clone() : null, tim = cur && cur.tim ? cur.tim.clone() : null;
    if (train.a.length) {
      act = act || new MLP(ad.nIn, cfg.hidden, ad.nA, 5);
      const lg = (o, it) => { const p = softmax(o, 0, ad.nA); return Float64Array.from(p.map((v, k) => v - (k === it.y ? 1 : 0))); };
      for (let st = 0; st < cfg.steps; st++) { const b = []; for (let i = 0; i < cfg.batch; i++) b.push(train.a[Math.floor(r() * train.a.length)]); act.step(b, lg, cfg.lr, 1e-4); }
    }
    if (train.t.length) {
      tim = tim || new MLP(NT, cfg.tHidden, 1, 7);
      const lg = (o, it) => Float64Array.of(Math.max(-1, Math.min(1, o[0] - it.y)));   // Huber-like (clipped) squared loss
      for (let st = 0; st < cfg.tSteps; st++) { const b = []; for (let i = 0; i < cfg.batch; i++) b.push(train.t[Math.floor(r() * train.t.length)]); tim.step(b, lg, cfg.tlr, 1e-4); }
    }
    const cand = new ReflexNet(act, tim);   // judged head by head below
    const agree = (net, set) => set.length ? set.filter((it) => (net && net.act ? net.action(it.x) : ad.fallback(it.raw)) === it.y).length / set.length : null;
    const mae = (net, set) => set.length ? 1000 * set.reduce((s, it) => s + Math.abs(it.q + (net && net.tim ? net.tim.forward(it.x).o[0] : 0) - it.yt), 0) / set.length : null;
    const m = (net) => ({ heldAgree: agree(net, held.a), heldMs: mae(net, held.t), anchorAgree: agree(net, anchor.a), anchorMs: mae(net, anchor.t) });
    const mc = m(cand), mo = m(cur), R = (v) => (v == null ? null : Math.round(v * 1000) / 1000);
    const okA = (c, o, tol) => c == null || o == null || c >= o - tol, okT = (c, o, tol) => c == null || o == null || c <= o + tol;
    // each head has its own seatbelt: it must be safe on the newest held-out day AND the older days' held-out, and better somewhere
    const safeA = okA(mc.heldAgree, mo.heldAgree, cfg.agreeTol) && okA(mc.anchorAgree, mo.anchorAgree, cfg.anchorAgreeTol), betterA = mc.heldAgree != null && mc.heldAgree > mo.heldAgree + 0.005;
    const safeT = okT(mc.heldMs, mo.heldMs, cfg.timeTol) && okT(mc.anchorMs, mo.anchorMs, cfg.anchorTimeTol), betterT = mc.heldMs != null && mc.heldMs < mo.heldMs * 0.98 - 0.5;
    const keepA = !!(train.a.length && safeA && betterA), keepT = !!(train.t.length && safeT && betterT), keep = keepA || keepT;
    const why = (k, safe) => (k ? 'kept' : safe ? 'no improvement on the held-out day' : 'seatbelt: worse on held-out day replays; rolled back');
    const out = { ...rec, kept: keep, keptAction: keepA, keptTiming: keepT, action: why(keepA, safeA), timing: why(keepT, safeT), cand: Object.fromEntries(Object.entries(mc).map(([k, v]) => [k, R(v)])), cur: Object.fromEntries(Object.entries(mo).map(([k, v]) => [k, R(v)])), against: cur ? 'previous reflex' : 'hand rule + plain tau', poison: opts.poison || 0 };
    if (!keep) return this.record(out);
    const next = new ReflexNet(keepA ? act : (cur ? cur.act : null), keepT ? tim : (cur ? cur.tim : null));
    const mf = path.join(this.dir, 'model.json'); try { if (fs.existsSync(mf)) fs.copyFileSync(mf, path.join(this.dir, 'model.prev.json')); } catch (e) { /* first */ }
    writeJson(mf, { net: next.toJSON(), at: this.now(), metrics: out.cand }); this.net = next;
    return this.record(out);
  }
  rollback() { const j = readJson(path.join(this.dir, 'model.prev.json')); if (!j || !j.net) return false; writeJson(path.join(this.dir, 'model.json'), j); this.net = ReflexNet.fromJSON(j.net); this.record({ at: this.now(), kind: 'reflex-core-rollback' }); return true; }
  record(o) { try { fs.appendFileSync(path.join(this.dir, 'nightly.jsonl'), JSON.stringify(o) + '\n'); } catch (e) { /* log only */ } this.log('reflex-core nightly: ' + JSON.stringify(o)); return o; }
}

module.exports = { ReflexNet, ReflexSleep, DEFAULTS, NT };
