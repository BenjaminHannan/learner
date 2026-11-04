'use strict';
// I3 two-speed core, part 3: TIMED ACTIONS, Ben's "catching a baseball" idea. Game-agnostic.
// Each planned action sits in the schedule with a TIME-TO-GO. Every tick the gap to the thing it is timed against is measured again
// and time-to-contact is re-estimated (Lee's tau = gap / closing speed; here a least-squares fit of the last k gaps, with
// acceleration, so a falling or speeding-up object is not under-predicted). The action fires on the tick whose time-to-go is
// nearest 0, counting the action's own wind-up lag (a jump leaves the ground lagMs after the key). It can move earlier or later
// every tick, and is cancelled when the thing stops approaching or vanishes.
// Truth: the game later reports when contact really happened (contact(id, atMs)); error = (fire + lag) - contact, in ms.
// Modes (for controls): 'tau' (re-estimate every tick, default), 'once' (estimate once at arming, constant speed, never update),
// 'react' (fire when the measured gap reaches 0: no anticipation).
// An optional learned correction (o.timing(features) -> seconds to add) comes from the reflex-in-sleep hook.

const CAP = 5;   // seconds; "not coming" is clipped to this in features
const ZONE = 1.0;   // seconds; the learned correction is trained, judged and applied only where the plain estimate is inside this zone
function fit(samples) {
  // samples [{t (s, relative to now <= 0), g}] -> {c0, c1, c2}
  const n = samples.length; if (n < 2) return null;
  if (n < 5) { // linear
    let st = 0, sg = 0, stt = 0, stg = 0; for (const s of samples) { st += s.t; sg += s.g; stt += s.t * s.t; stg += s.t * s.g; }
    const d = n * stt - st * st; if (Math.abs(d) < 1e-12) return null; const c1 = (n * stg - st * sg) / d; return { c0: (sg - c1 * st) / n, c1, c2: 0 };
  }
  // quadratic normal equations (3x3)
  const S = [0, 0, 0, 0, 0], T = [0, 0, 0];
  for (const s of samples) { let p = 1; for (let k = 0; k < 5; k++) { S[k] += p; if (k < 3) T[k] += p * s.g; p *= s.t; } }
  const A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]];
  const x = solve3(A, T); return x ? { c0: x[0], c1: x[1], c2: x[2] } : null;
}
function solve3(A, b) {
  const M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < 3; c++) {
    let p = c; for (let r = c + 1; r < 3; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-15) return null; [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < 3; r++) if (r !== c) { const f = M[r][c] / M[c][c]; for (let k = c; k < 4; k++) M[r][k] -= f * M[c][k]; }
  }
  return [M[0][3] / M[0][0], M[1][3] / M[1][1], M[2][3] / M[2][2]];
}
// smallest positive root of c0 + c1 t + c2 t^2 = 0, or Infinity when it never reaches 0
function firstRoot(c) {
  if (!c) return Infinity;
  if (c.c0 <= 0) return 0;
  if (Math.abs(c.c2) < 1e-9) return c.c1 < 0 ? -c.c0 / c.c1 : Infinity;
  const D = c.c1 * c.c1 - 4 * c.c2 * c.c0; if (D < 0) return Infinity;
  const r = [(-c.c1 - Math.sqrt(D)) / (2 * c.c2), (-c.c1 + Math.sqrt(D)) / (2 * c.c2)].filter((x) => x > 0).sort((a, b) => a - b);
  return r.length ? r[0] : Infinity;
}

class TauEstimator {
  constructor(k) { this.k = k || 8; this.h = []; }
  add(tMs, gap) { this.h.push({ tMs, gap }); if (this.h.length > this.k) this.h.shift(); }
  estimate() {
    const n = this.h.length; if (!n) return { ttgS: Infinity, tau1S: Infinity, n: 0, gap: null };
    const now = this.h[n - 1].tMs, s = this.h.map((p) => ({ t: (p.tMs - now) / 1000, g: p.gap }));
    const lin = fit(s.length > 4 ? s.slice(-4) : s), quad = fit(s);
    const gap = quad ? quad.c0 : s[n - 1].g;
    const tau1S = lin && lin.c1 < 0 ? Math.max(0, lin.c0 / -lin.c1) : Infinity;   // Lee's tau: gap / closing speed
    let ttgS = firstRoot(quad); if (!Number.isFinite(ttgS) && Number.isFinite(tau1S) && quad && quad.c2 < 0) ttgS = tau1S;
    const acc = quad ? 2 * quad.c2 : 0;
    return { ttgS, tau1S, n, gap, rate: lin ? lin.c1 : 0, acc };
  }
  // fixed-length, unit-free (seconds / ratios) features: the same for every game
  features(e) {
    e = e || this.estimate(); const cl = (x) => Math.min(CAP, Number.isFinite(x) ? x : CAP);
    const accRatio = e.gap > 1e-6 && Number.isFinite(e.tau1S) ? Math.max(-2, Math.min(2, (e.acc / 2) * e.tau1S * e.tau1S / e.gap)) : 0;
    return [cl(e.ttgS), cl(e.tau1S), accRatio, e.n / this.k, cl(e.ttgS) - cl(e.tau1S)];
  }
}

class ActionSchedule {
  // o: {tickMs, mode: 'tau'|'once'|'react', timing: fn(features) -> seconds to add (learned), cancelAfterMs, k, keepSamples}
  constructor(o) { this.o = o || {}; this.tickMs = this.o.tickMs || 50; this.mode = this.o.mode || 'tau'; this.items = new Map(); this.fired = []; this.errors = []; this.misses = 0; this.cancelled = 0; }
  // an explicit plan: "in inMs I will <action>" (no measurement yet; counts down; measurements re-estimate it)
  plan(id, action, inMs, nowMs, lagMs) { this.items.set(id, { id, action, lagMs: lagMs || 0, est: new TauEstimator(this.o.k), status: 'armed', explicitAt: nowMs + inMs, samples: [], ttgLog: [] }); }
  move(id, deltaMs) { const it = this.items.get(id); if (it && it.explicitAt != null) it.explicitAt += deltaMs; }
  cancel(id) { const it = this.items.get(id); if (it && it.status === 'armed') { it.status = 'cancelled'; this.cancelled++; } }
  // every tick: targets = [{id, action, lagMs, gap}] measured now -> the actions that fire on THIS tick
  tick(nowMs, targets) {
    const out = [], seen = new Set(), half = this.tickMs / 2;
    for (const tg of targets || []) {
      seen.add(tg.id); let it = this.items.get(tg.id);
      if (!it) { it = { id: tg.id, action: tg.action, lagMs: tg.lagMs || 0, est: new TauEstimator(this.o.k), status: 'armed', samples: [], ttgLog: [] }; this.items.set(tg.id, it); }
      if (it.status !== 'armed') continue;
      it.est.add(nowMs, tg.gap);
      const e = it.est.estimate(); let ttgMs;
      if (this.mode === 'react') ttgMs = tg.gap <= 0 ? 0 : Infinity;
      else if (this.mode === 'once') { if (it.onceAt == null && e.n >= 2) it.onceAt = nowMs + (Number.isFinite(e.tau1S) ? e.tau1S * 1000 : Infinity); ttgMs = it.onceAt == null ? Infinity : it.onceAt - nowMs; }
      else {
        let s = e.ttgS; const f = it.est.features(e);
        if (this.o.timing && e.n >= 2 && s <= ZONE) { try { const c = this.o.timing(f); if (Number.isFinite(c)) s = Math.max(0, Math.min(CAP, Number.isFinite(s) ? s : CAP) + c); } catch (err) { /* plain tau */ } }
        ttgMs = s * 1000;
        if (e.n >= 2 && it.samples.length < (this.o.keepSamples || 400)) it.samples.push({ t: nowMs, f, q: Math.min(CAP, Number.isFinite(e.ttgS) ? e.ttgS : CAP) });
      }
      it.ttgLog.push(Math.round(ttgMs));
      if (!Number.isFinite(ttgMs)) { it.notComing = (it.notComing || 0) + this.tickMs; if (it.notComing > (this.o.cancelAfterMs || 400) && this.mode === 'tau' && e.n >= it.est.k) { it.status = 'cancelled'; this.cancelled++; } continue; }
      it.notComing = 0;
      if (ttgMs - it.lagMs <= half) { it.status = 'fired'; it.firedAt = nowMs; out.push({ id: it.id, action: it.action, atMs: nowMs }); this.fired.push(it.id); }
    }
    for (const it of this.items.values()) {
      if (it.status !== 'armed') continue;
      if (it.explicitAt != null && !seen.has(it.id) && it.explicitAt - it.lagMs - nowMs <= half) { it.status = 'fired'; it.firedAt = nowMs; out.push({ id: it.id, action: it.action, atMs: nowMs }); }
      else if (it.explicitAt == null && !seen.has(it.id)) { it.status = 'cancelled'; this.cancelled++; it.gone = true; }
    }
    return out;
  }
  // the game says when contact REALLY happened -> timing error in ms (null = it never fired: a miss)
  contact(id, atMs) {
    const it = this.items.get(id); if (!it) return null;
    it.contactAt = atMs;
    if (it.status === 'cancelled') { this.dropped = (this.dropped || 0) + 1; it.err = null; return null; }   // let go on purpose (no longer wanted): not a timing miss
    if (it.status !== 'fired') { this.misses++; it.err = null; return null; }
    it.err = it.firedAt + it.lagMs - atMs; this.errors.push(it.err); return it.err;
  }
  // hindsight labels for sleep: every tick an item was estimated, the TRUE seconds to go (known once contact happened)
  hindsight() {
    const out = []; for (const it of this.items.values()) if (it.contactAt != null) for (const s of it.samples) if (s.t <= it.contactAt) out.push({ f: s.f.map((v) => Math.round(v * 1e4) / 1e4), q: Math.round(s.q * 1e4) / 1e4, y: Math.round((it.contactAt - s.t) / 10) / 100 });
    return out;
  }
  report() {
    const a = this.errors.map(Math.abs).sort((x, y) => x - y), n = a.length + this.misses;
    return { contacts: n, fired: a.length, misses: this.misses, dropped: this.dropped || 0, medianAbsMs: n ? medianWithMisses(a, this.misses) : null, p90AbsMs: a.length ? a[Math.floor(a.length * 0.9)] : null, withinTick: n ? a.filter((x) => x <= this.tickMs).length / n : null };
  }
}
// misses count as infinitely late
function medianWithMisses(sorted, misses) { const all = sorted.concat(Array(misses).fill(Infinity)); return all[Math.floor((all.length - 1) / 2)]; }

module.exports = { ActionSchedule, TauEstimator, firstRoot, fit, CAP, ZONE };
