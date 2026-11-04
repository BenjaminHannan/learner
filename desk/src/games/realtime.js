'use strict';
// T6 (2026-11-04): a REAL-TIME sandbox game with a reflex (muscle memory) fast path. Glim's own; not the Bedwars bot track.
// "Sparks": an 11x11 arena; sparks fly in from the walls and wander (each frame a spark may turn to one of 8 headings). Move one cell
// (or stay) per frame; 3 lives; score = 100 * frames survived / 400. Reaction matters: an old picture of the arena is soon wrong.
// Kept OUT of GAMES in ./index.js on purpose (that registry is turn-based; the scientist and the world model expect its interface).
//
// Two ways to choose a move:
//   planner  slow and careful (Monte-Carlo lookahead, 125 move sequences x 24 imagined futures). In the app its answer comes late:
//            it stands in for the big brain, whose reply takes many frames.
//   reflex   a tiny net (9x9 window around me -> 5 moves), well under 1 ms. The fast path.
// Sleep (nightly): every frame the fast path played is replayed; the planner labels each one at its own pace (no time limit); each
// labelled frame is also replayed in the arena's 7 other symmetric versions (rotations / mirror images, by formula); the reflex is
// distilled from all labels so far (last 7 days). SEATBELT: (1) the candidate plays fixed validation games and must not score worse
// than the current fast path (night 1: it must beat the late planner); (2) its agreement with the planner on OLDER days' held-out
// frames (20 % of each day, never trained on) may not drop by more than 2 points. Otherwise roll back. Logged to reflex/nightly.jsonl.
// Toy evidence: premonition-sleeplab-t6 MARKS-reflex-v3 (PASS 3/3 seeds: 78-82 vs untimed planner 92, late planner 14-15) and the
// seatbelt-v2 control in MARKS-reflex-v2 (60 % / 30 % poisoned nights rejected 3/3). Real-Glim: only these sandbox games; untested.
const fs = require('fs');
const path = require('path');
const { MLP, rng, softmax } = require('../tinynet');

const N = 11, FRAMES = 400, LIVES = 3;
const ACTIONS = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]];
const ACTION_NAMES = ['stay', 'up', 'down', 'left', 'right'];
const HEAD = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [-1, 1], [1, -1], [1, 1]];
const inside = (r, c) => r >= 0 && c >= 0 && r < N && c < N;

const sparks = {
  name: 'sparks', realtime: true, frames: FRAMES,
  init(seed, o) { return { seed, f: 0, lives: LIVES, me: [5, 5], sparks: [], rs: (seed * 9973 + 1) >>> 0, spawn: (o && o.spawn) || 0.55, turn: (o && o.turn) || 0.3 }; },
  moves() { return [0, 1, 2, 3, 4]; },
  step(s, a) {
    const t = clone(s), r = rng(t.rs); const prev = t.me; t.me = moveMe(t.me, a);
    t.sparks = moveSparks(t.sparks, r, t.turn);
    const keep = []; for (const p of t.sparks) { if (hitBy(t.me, prev, p)) t.lives--; else keep.push(p); }
    t.sparks = keep; spawn(t, r); t.f++; t.rs = Math.floor(r() * 4294967296) >>> 0;
    return t;
  },
  done(s) { return s.lives <= 0 || s.f >= FRAMES; },
  result(s) { return sparks.done(s) ? s.f / FRAMES : null; },
  score(s) { return 100 * s.f / FRAMES; },
  render(s) { const g = Array.from({ length: N }, () => Array(N).fill('.')); for (const p of s.sparks) g[p.r][p.c] = '*'; g[s.me[0]][s.me[1]] = '@'; return g.map((r) => r.join('')).join('\n') + '\nFrame ' + s.f + ', lives ' + s.lives + '.'; },
  moveText: (a) => ACTION_NAMES[a]
};
function clone(s) { return { ...s, me: s.me.slice(), sparks: s.sparks.map((p) => ({ ...p })) }; }
function moveMe(me, a) { const d = ACTIONS[a] || ACTIONS[0], r = me[0] + d[0], c = me[1] + d[1]; return inside(r, c) ? [r, c] : me.slice(); }
function moveSparks(list, r, turn) { const out = []; for (const p of list) { let h = p.h; if (r() < turn) h = Math.floor(r() * 8); const r1 = p.r + HEAD[h][0], c1 = p.c + HEAD[h][1]; if (inside(r1, c1)) out.push({ r: r1, c: c1, h, pr: p.r, pc: p.c }); } return out; }
function spawn(s, r) {
  if (r() >= s.spawn) return;
  const side = Math.floor(r() * 4), k = Math.floor(r() * N);
  const pos = side === 0 ? [0, k] : side === 1 ? [N - 1, k] : side === 2 ? [k, 0] : [k, N - 1];
  const dr = Math.sign(s.me[0] - pos[0]), dc = Math.sign(s.me[1] - pos[1]);
  let h = HEAD.findIndex((d) => d[0] === dr && d[1] === dc); if (h < 0) h = 0;
  s.sparks.push({ r: pos[0], c: pos[1], h, pr: pos[0], pc: pos[1] });
}
const hitBy = (me, prev, p) => (p.r === me[0] && p.c === me[1]) || (p.r === prev[0] && p.c === prev[1] && p.pr === me[0] && p.pc === me[1]);

// the slow careful planner (see the header). o: {K futures, L = how many frames old the picture is, past = my moves since then}
function plan(s, o) {
  const K = (o && o.K) || 24, D = 3, L = (o && o.L) || 0, past = (o && o.past) || [], r = rng((o && o.seed) || (s.f * 7 + s.seed));
  let me = s.me.slice(); for (const a of past) me = moveMe(me, a);
  const futures = [];
  for (let k = 0; k < K; k++) { let sp = s.sparks.map((p) => ({ ...p })); const fr = []; for (let i = 0; i < L + D; i++) { sp = moveSparks(sp, r, s.turn); fr.push(sp); } futures.push(fr.slice(L)); }
  let best = -Infinity, bestA = 0;
  for (let a = 0; a < 5; a++) for (let b = 0; b < 5; b++) for (let c = 0; c < 5; c++) {
    const seq = [a, b, c]; let v = 0;
    for (const fr of futures) {
      let m = me, ok = 1;
      for (let i = 0; i < D && ok; i++) { const pm = m; m = moveMe(m, seq[i]); for (const p of fr[i]) if (hitBy(m, pm, p)) { ok = 0; break; } }
      let dmin = 6; if (ok) for (const p of fr[D - 1]) dmin = Math.min(dmin, Math.max(Math.abs(p.r - m[0]), Math.abs(p.c - m[1])));
      v += ok * (1 + 0.05 * dmin - 0.02 * (Math.abs(m[0] - 5) + Math.abs(m[1] - 5)));
    }
    if (v > best + 1e-9) { best = v; bestA = a; }
  }
  return bestA;
}
// the reflex's input: a 9x9 window around me; channels: spark here, its heading (dr, dc), wall/outside
const R = 4, WIN = 2 * R + 1, NIN = WIN * WIN * 4;
function features(s) {
  const x = new Float64Array(NIN), at = (dr, dc) => ((dr + R) * WIN + (dc + R)) * 4;
  for (let dr = -R; dr <= R; dr++) for (let dc = -R; dc <= R; dc++) if (!inside(s.me[0] + dr, s.me[1] + dc)) x[at(dr, dc) + 3] = 1;
  for (const p of s.sparks) { const dr = p.r - s.me[0], dc = p.c - s.me[1]; if (Math.abs(dr) > R || Math.abs(dc) > R) continue; const i = at(dr, dc); x[i] = 1; x[i + 1] += HEAD[p.h][0]; x[i + 2] += HEAD[p.h][1]; }
  return x;
}
// the arena's 8 symmetries: a frame and its move, transformed together (rotations and mirror images about the centre cell)
const MATS = [[1, 0, 0, 1], [0, -1, 1, 0], [-1, 0, 0, -1], [0, 1, -1, 0], [1, 0, 0, -1], [-1, 0, 0, 1], [0, 1, 1, 0], [0, -1, -1, 0]];
const mv = (m, dr, dc) => [m[0] * dr + m[1] * dc, m[2] * dr + m[3] * dc];
const mp = (m, r, c) => { const [a, b] = mv(m, r - 5, c - 5); return [a + 5, b + 5]; };
function transform(s, a, k) {
  const m = MATS[k], me = mp(m, s.me[0], s.me[1]);
  const list = s.sparks.map((p) => { const [r, c] = mp(m, p.r, p.c), [pr, pc] = mp(m, p.pr, p.pc), hv = mv(m, HEAD[p.h][0], HEAD[p.h][1]); return { r, c, pr, pc, h: HEAD.findIndex((d) => d[0] === hv[0] && d[1] === hv[1]) }; });
  const av = mv(m, ACTIONS[a][0], ACTIONS[a][1]);
  return { s: { ...s, me, sparks: list }, a: ACTIONS.findIndex((d) => d[0] === av[0] && d[1] === av[1]) };
}
// a policy for the planner arriving L frames late (the big brain under the time limit)
function latePlanner(L, K) { return (s, hist, acts) => { const i = hist.length - 1 - L; if (i < 0) return 0; return plan(hist[i], { K, L, past: acts.slice(i) }); }; }
function play(seed, policy, keepFrames) {
  let s = sparks.init(seed); const hist = [s], acts = [], frames = [];
  while (!sparks.done(s)) { const a = policy(s, hist, acts); if (keepFrames) frames.push(clone(s)); acts.push(a); s = sparks.step(s, a); hist.push(s); }
  return { score: sparks.score(s), frames };
}

const DEFAULTS = { hidden: 32, steps: 2500, batch: 64, lr: 0.002, tol: 1, valGames: 12, delay: 8, K: 24, maxFrames: 20000, poolDays: 7 };
class Reflex {
  // o: {dir, now, log, cfg}
  constructor(o) {
    this.o = o || {}; this.dir = path.join(this.o.dir || '.', 'reflex'); this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.cfg = { ...DEFAULTS, ...(this.o.cfg || {}) }; this.net = null; this.val = null; this.today = [];
    try { fs.mkdirSync(this.dir, { recursive: true }); } catch (e) { /* later */ }
    const j = readJson(path.join(this.dir, 'model.json')); if (j && j.net) { try { this.net = MLP.fromJSON(j.net); this.val = j.val; } catch (e) { this.net = null; } }
  }
  ready() { return !!this.net; }
  // the fast path: a move now (the late planner when no reflex has been kept yet)
  policy() { if (this.net) return (s) => argmax(this.net.forward(features(s)).o); return latePlanner(this.cfg.delay, this.cfg.K); }
  // play one game with the fast path and log its frames for tonight
  playDay(seed) { const g = play(seed, this.policy(), true); this.logFrames(g.frames); return g.score; }
  logFrames(frames) {
    const f = path.join(this.dir, 'frames-' + dayKey(this.now()) + '.jsonl');
    try { fs.appendFileSync(f, frames.map((s) => JSON.stringify({ f: s.f, seed: s.seed, me: s.me, sparks: s.sparks.map((p) => [p.r, p.c, p.h]), turn: s.turn })).join('\n') + '\n'); } catch (e) { this.log('reflex: frames not saved', e); }
  }
  // night: label + distill + seatbelt + keep/roll back
  nightly(opts) {
    opts = opts || {}; const cfg = this.cfg, r = rng(opts.seed || 11);
    let files = []; try { files = fs.readdirSync(this.dir).filter((n) => /^frames-\d{4}-\d{2}-\d{2}\.jsonl$/.test(n)).sort().slice(-cfg.poolDays); } catch (e) { /* none */ }
    const perDay = files.map((n) => readLines(path.join(this.dir, n)).slice(-Math.ceil(cfg.maxFrames / Math.max(1, files.length))));
    const frames = [].concat(...perDay);
    const rec = { at: this.now(), kind: 'reflex-nightly', frames: frames.length };
    if (!frames.length) return this.record({ ...rec, kept: false, why: 'no frames played' });
    // labels: cached per frame (the planner is the slow part; a frame labelled on an earlier night keeps its label)
    const cacheF = path.join(this.dir, 'labels.json'), cache = readJson(cacheF) || {};
    const label = (fr) => {
      const s = { seed: fr.seed, f: fr.f, lives: 3, me: fr.me, sparks: fr.sparks.map(([a, b, h]) => ({ r: a, c: b, h, pr: a, pc: b })), turn: fr.turn };
      const key = fr.seed + ':' + fr.f + ':' + fr.me.join(',') + ':' + fr.sparks.map((p) => p.join(',')).join(';');
      let y = cache[key]; if (y == null) { y = plan(s, { K: cfg.K }); cache[key] = y; }
      return { s, y };
    };
    // per day: the first 80 % trains (each frame + its 7 symmetric versions), the last 20 % is held out; the older days' held-out = anchor
    const items = [], anchor = [];
    perDay.forEach((day, di) => {
      const cut = Math.floor(day.length * 0.8), newest = di === perDay.length - 1;
      day.forEach((fr, i) => {
        const { s, y: y0 } = label(fr), y = newest && opts.poison ? poisonLabel(y0, opts.poison, r) : y0;
        if (i >= cut) { if (!newest) anchor.push({ x: features(s), y }); return; }
        for (let k = 0; k < 8; k++) { const t = k ? transform(s, y, k) : { s, a: y }; items.push({ x: features(t.s), y: t.a }); }
      });
    });
    if (!items.length) return this.record({ ...rec, kept: false, why: 'too few frames' });
    try { const keys = Object.keys(cache); if (keys.length > cfg.maxFrames * 2) for (const k of keys.slice(0, keys.length - cfg.maxFrames * 2)) delete cache[k]; writeJson(cacheF, cache); } catch (e) { /* recompute next night */ }
    const cand = this.net ? this.net.clone() : new MLP(NIN, cfg.hidden, 5, 5);
    const lossGrad = (o, it) => { const p = softmax(o, 0, 5); return Float64Array.from(p.map((v, k) => v - (k === it.y ? 1 : 0))); };
    for (let st = 0; st < cfg.steps; st++) { const b = []; for (let i = 0; i < cfg.batch; i++) b.push(items[Math.floor(r() * items.length)]); cand.step(b, lossGrad, cfg.lr, 1e-4); }
    const valSeeds = Array.from({ length: cfg.valGames }, (_, i) => 700000 + i);
    const score = (pol) => valSeeds.reduce((a, sd) => a + play(sd, pol).score, 0) / valSeeds.length;
    const candVal = score((s) => argmax(cand.forward(features(s)).o));
    const curVal = this.net ? (this.val != null ? this.val : score(this.policy())) : score(latePlanner(cfg.delay, cfg.K));
    const agree = (net) => anchor.length ? anchor.filter((it) => argmax(net.forward(it.x).o) === it.y).length / anchor.length : null;
    const aC = this.net ? agree(cand) : null, aO = this.net ? agree(this.net) : null;
    const keep = candVal >= curVal - (this.net ? cfg.tol : 0) && (this.net || candVal > curVal) && (aC == null || aO == null || aC >= aO - 0.02);
    const out = { ...rec, kept: !!keep, candVal: Math.round(candVal * 10) / 10, curVal: Math.round(curVal * 10) / 10, anchorAgree: aC == null ? null : { cand: Math.round(aC * 1000) / 1000, old: Math.round(aO * 1000) / 1000 }, against: this.net ? 'previous reflex' : 'late planner' };
    if (!keep) return this.record({ ...out, why: 'seatbelt: candidate worse on the validation games or on older held-out frames; rolled back' });
    const mf = path.join(this.dir, 'model.json'); try { if (fs.existsSync(mf)) fs.copyFileSync(mf, path.join(this.dir, 'model.prev.json')); } catch (e) { /* first */ }
    writeJson(mf, { net: cand.toJSON(), val: candVal, at: this.now() }); this.net = cand; this.val = candVal;
    return this.record(out);
  }
  rollback() { const j = readJson(path.join(this.dir, 'model.prev.json')); if (!j || !j.net) return false; writeJson(path.join(this.dir, 'model.json'), j); this.net = MLP.fromJSON(j.net); this.val = j.val; this.record({ at: this.now(), kind: 'reflex-rollback' }); return true; }
  record(o) { try { fs.appendFileSync(path.join(this.dir, 'nightly.jsonl'), JSON.stringify(o) + '\n'); } catch (e) { /* log only */ } this.log('reflex nightly: ' + JSON.stringify(o)); return o; }
}
function poisonLabel(y, frac, r) { return r() < frac ? (y + 1 + Math.floor(r() * 4)) % 5 : y; }
const argmax = (o) => { let b = 0; for (let k = 1; k < o.length; k++) if (o[k] > o[b]) b = k; return b; };
const dayKey = (t) => { const d = new Date(t); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
function readJson(p) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; } }
function writeJson(p, v) { const tmp = p + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(v)); fs.renameSync(tmp, p); }
function readLines(p) { try { return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { return []; } }

module.exports = { sparks, plan, features, transform, latePlanner, play, Reflex, NIN, ACTION_NAMES, DEFAULTS };
