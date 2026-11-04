'use strict';
// Sleep track T3 (2026-11-04): a LEARNED world model for the sandbox games, "what happens after move a", learned by COUNTING
// from the day's game logs. src/imagine.js plans with it (o.world) and falls back to the rulebook when it has no idea.
// Toy-proven in ~/learner-ops/premonition-sleeplab-t3 (MARKS/RESULTS-worldmodel-v1: 4/4 games, 3/3 seeds, ratio 0.997 by night 16).
//   - LEARNED (from logs only): the effect of our move given a small local view, and the replies the opponent was seen to make.
//   - NOT learned (fixed): the perception (which cells form the view), the legal moves, the scorer (who won / the game's value).
// Nightly (sleep rule: replay -> update -> seatbelt -> keep or roll back): the candidate is learned from every day except the
// latest; it must be at least as accurate as the current model on the latest day (held out) AND on fixed rulebook checks, or it
// is rolled back. Pure JS, no model, no network.
const fs = require('fs');
const path = require('path');
const DIRS = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };
const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const winnerOf = (b) => { for (const [a, c, d] of LINES) if (b[a] !== '.' && b[a] === b[c] && b[a] === b[d]) return b[a]; return b.includes('.') ? null : 'draw'; };
const clone = (s) => JSON.parse(JSON.stringify(s));

// ---- per-game adapters: views (perception), effects (what changed, relative), apply (effect -> state) ----------------------
const ADAPT = {
  maze: {
    cell(s, p) { if (p[0] < 0 || p[1] < 0 || p[0] >= s.grid.length || p[1] >= s.grid.length) return 'E'; return s.grid[p[0]][p[1]] === '#' ? '#' : '.'; },
    // fine view: the move + the 4 neighbouring cells; coarse: the move + the cell it points at; then the move alone
    views(s, m) { const n = Object.values(DIRS).map((d) => ADAPT.maze.cell(s, [s.pos[0] + d[0], s.pos[1] + d[1]])).join(''); const d = DIRS[m] || [0, 0]; return [m + '|' + n, m + '>' + ADAPT.maze.cell(s, [s.pos[0] + d[0], s.pos[1] + d[1]]), m]; },
    effect(s, s2) { return (s2.pos[0] - s.pos[0]) + ',' + (s2.pos[1] - s.pos[1]) + ',' + (s2.steps - s.steps); },
    apply(s, m, e) { const [a, b, c] = e.split(',').map(Number); const t = clone(s); t.pos = [s.pos[0] + a, s.pos[1] + b]; t.steps = s.steps + c; return t; }
  },
  tiles: {
    views(s, m) { const z = s.board.indexOf('0'); return [m + '|' + z, m + '|r' + Math.floor(z / 3) + 'c' + (z % 3 === 0 ? 'L' : z % 3 === 2 ? 'R' : 'M'), m]; },
    effect(s, s2) { return (s2.board.indexOf('0') - s.board.indexOf('0')) + ',' + (s2.steps - s.steps); },
    apply(s, m, e) {
      const [d, c] = e.split(',').map(Number); const z = s.board.indexOf('0'), t = z + d;
      if (t < 0 || t > 8) return { ...s, steps: s.steps + c };
      const a = s.board.split(''); a[z] = a[t]; a[t] = '0'; return { ...s, board: a.join(''), steps: s.steps + c };
    }
  },
  nim: {
    // the move's pile first, then the others in order: effect = the change of each pile, in that order
    order(s, m) { return [m.pile].concat(s.piles.map((_, i) => i).filter((i) => i !== m.pile)); },
    views(s, m) { return ['take' + m.take + '|v' + s.piles[m.pile], 'take' + m.take]; },
    effect(s, s2, m) { return ADAPT.nim.order(s, m).map((i) => s2.piles[i] - s.piles[i]).join(','); },
    apply(s, m, e) { const d = e.split(',').map(Number), o = ADAPT.nim.order(s, m), t = clone(s); o.forEach((i, j) => { t.piles[i] = s.piles[i] + d[j]; }); if (t.piles.some((p) => p < 0)) return null; t.ply = s.ply + 1; return t; },
    // the opponent: one pile went from v to v - d. Learned: the (v, d) pairs seen.
    replyOf(s, s2) { const ch = s.piles.map((p, i) => [i, s2.piles[i] - p]).filter(([, d]) => d !== 0); if (ch.length !== 1 || ch[0][1] >= 0) return null; return 'v' + s.piles[ch[0][0]] + 'd' + (-ch[0][1]); },
    replies(s, seen) { const out = []; s.piles.forEach((p, i) => { for (const k of seen) { const [, v, d] = /^v(\d+)d(\d+)$/.exec(k).map(Number); if (v === p) { const t = clone(s); t.piles[i] = p - d; t.ply = s.ply + 1; out.push(t); } } }); return out; },
    // scorer (fixed, not learned): whoever empties the last pile wins
    finalize(t, who) { if (t && !t.winner && t.piles.every((p) => p === 0)) t.winner = who === 'me' ? 'me' : 'them'; return t; }
  },
  ttt: {
    views(s, m) { return ['sq' + m + '=' + s.board[m], '=' + s.board[m]]; },
    // effect: which squares changed, relative to the move's square ('@' = the move's own square)
    effect(s, s2, m) { const out = []; for (let i = 0; i < 9; i++) if (s.board[i] !== s2.board[i]) out.push((i === m ? '@' : i) + ':' + s2.board[i]); return out.join(';'); },
    apply(s, m, e) { const b = s.board.split(''); if (e) for (const part of e.split(';')) { const [i, v] = part.split(':'); b[i === '@' ? m : +i] = v; } return { ...s, board: b.join(''), ply: s.ply + 1 }; },
    replyOf(s, s2) { const ch = []; for (let i = 0; i < 9; i++) if (s.board[i] !== s2.board[i]) ch.push(i + ':' + s.board[i] + '>' + s2.board[i]); return ch.length === 1 ? ch[0] : null; },
    replies(s, seen) { const out = []; for (const k of seen) { const [, i, from, to] = /^(\d):(.)>(.)$/.exec(k); if (s.board[+i] === from) { const b = s.board.split(''); b[+i] = to; out.push({ ...s, board: b.join(''), ply: s.ply + 1 }); } } return out; },
    finalize(t) { if (t && !t.winner) { const w = winnerOf(t.board); if (w) t.winner = w; } return t; }
  }
};

// ---- the model -------------------------------------------------------------------------------------------------------------
class WorldModel {
  constructor(j) { j = j || {}; this.v = 1; this.counts = j.counts || {}; this.replySeen = j.replySeen || {}; this.n = j.n || {}; }
  toJSON() { return { v: 1, counts: this.counts, replySeen: this.replySeen, n: this.n }; }
  static from(j) { return new WorldModel(j); }
  clone() { return new WorldModel(JSON.parse(JSON.stringify(this.toJSON()))); }
  // learn from log rows (counting). Returns how many rows were used.
  learn(rows) {
    let used = 0;
    for (const r of rows || []) {
      const A = ADAPT[r && r.game]; if (!A || !r.s || !r.s2) continue;
      if (r.who === 'them') {
        const k = A.replyOf && A.replyOf(r.s, r.s2); if (!k) continue;
        const set = this.replySeen[r.game] || (this.replySeen[r.game] = {}); set[k] = (set[k] || 0) + 1; used++; continue;
      }
      if (r.m == null) continue;
      const e = A.effect(r.s, r.s2, r.m); const g = this.counts[r.game] || (this.counts[r.game] = {});
      for (const v of A.views(r.s, r.m)) { const c = g[v] || (g[v] = {}); c[e] = (c[e] || 0) + 1; }
      this.n[r.game] = (this.n[r.game] || 0) + 1; used++;
    }
    return used;
  }
  // the most-counted effect at the finest view seen -> {effect, level} | null
  effectFor(game, s, m) {
    const A = ADAPT[game], g = this.counts[game]; if (!A || !g) return null;
    const vs = A.views(s, m);
    for (let i = 0; i < vs.length; i++) { const c = g[vs[i]]; if (!c) continue; let best = null, bn = -1; for (const [e, n] of Object.entries(c)) if (n > bn || (n === bn && e < best)) { best = e; bn = n; } return { effect: best, level: i }; }
    return null;
  }
  // predicted state after OUR move (null = no idea)
  predict(game, s, m) {
    const A = ADAPT[game]; const e = this.effectFor(game, s, m); if (!e) return null;
    let t = A.apply(s, m, e.effect); if (A.finalize) t = A.finalize(t, 'me');
    return t;
  }
  // predicted opponent replies (two-player games): every reply seen in the logs that fits this state; [] = none known
  replies(game, s) {
    const A = ADAPT[game]; if (!A || !A.replies) return null;
    const seen = Object.keys(this.replySeen[game] || {}); const out = A.replies(s, seen);
    return A.finalize ? out.map((t) => A.finalize(t, 'them')) : out;
  }
  // a game-shaped view for the planner (src/imagine.js): the same scorer and legal moves, the dynamics from this model
  asGame(game) {
    const W = this, name = game.name, two = !!(game.apply && game.replies);
    const p = Object.assign({}, game);
    if (two) { p.apply = (s, m) => W.predict(name, s, m); p.replies = (s) => W.replies(name, s) || []; }
    else p.step = (s, m) => W.predict(name, s, m) || s;   // no idea -> imagine "nothing happens"
    return p;
  }
  // accuracy of OUR-move predictions on log rows (the seatbelt's held-out check): -> {n, right, acc}
  score(rows) {
    let n = 0, right = 0;
    for (const r of rows || []) {
      if (!r || r.who === 'them' || r.m == null || !ADAPT[r.game]) continue;
      n++; const t = this.predict(r.game, r.s, r.m); if (!t) continue;
      const A = ADAPT[r.game]; if (A.effect(r.s, t, r.m) === A.effect(r.s, r.s2, r.m)) right++;
    }
    return { n, right, acc: n ? right / n : null };
  }
}


// ---- the game log (userData/game-log.jsonl): one row per half-step, {t, game, who, s, m, s2} ----------------------------------
const MAX_ROWS = 6000, KEEP_ROWS = 5000, GUARD_GAP = 0.15;
class GameLog {
  constructor(o) { this.o = o || {}; this.now = this.o.now || Date.now; this.file = this.o.dir ? path.join(this.o.dir, 'game-log.jsonl') : null; this.mem = []; }
  add(r) {
    if (!r || !ADAPT[r.game] || !r.s || !r.s2) return null;
    const row = { t: this.now(), game: r.game, who: r.who === 'them' ? 'them' : 'me', s: r.s, m: r.m, s2: r.s2 };
    if (this.file) { try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); fs.appendFileSync(this.file, JSON.stringify(row) + '\n'); return row; } catch (e) { /* memory */ } }
    this.mem.push(row); if (this.mem.length > MAX_ROWS) this.mem.splice(0, this.mem.length - KEEP_ROWS); return row;
  }
  // one rulebook step as half-steps (two-player games: our move, then the opponent's change)
  addStep(game, s, m, s2) {
    if (game.apply && game.replies) { const mid = game.apply(s, m); if (!mid) return; this.add({ game: game.name, who: 'me', s, m, s2: mid }); if (!game.done(mid) && s2) this.add({ game: game.name, who: 'them', s: mid, s2 }); }
    else this.add({ game: game.name, who: 'me', s, m, s2 });
  }
  rows() {
    let out = [];
    if (this.file) { try { out = fs.readFileSync(this.file, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { /* none */ } }
    return out.concat(this.mem);
  }
  // keep the file bounded (called at night)
  trim() {
    if (!this.file) return;
    try { const rows = this.rows(); if (rows.length <= MAX_ROWS) return; const tmp = this.file + '.tmp'; fs.writeFileSync(tmp, rows.slice(-KEEP_ROWS).map((r) => JSON.stringify(r)).join('\n') + '\n'); fs.renameSync(tmp, this.file); } catch (e) { /* keep */ }
  }
}

// fixed checks: rulebook transitions from fixed seeds (never practice seeds), the seatbelt's second test
function fixedChecks(games, n) {
  const out = []; const { rng } = require('./games');
  for (const g of Object.values(games)) {
    if (!ADAPT[g.name]) continue;
    for (let i = 0; i < (n || 12); i++) {
      const r = rng(910000 + i * 31 + g.name.length); let s = g.init(910000 + i);
      for (let k = 0, j = Math.floor(r() * 4); k < j && !g.done(s); k++) { const ms = g.moves(s); s = g.step(s, ms[Math.floor(r() * ms.length)]); }
      if (g.done(s)) continue;
      const ms = g.moves(s), m = ms[Math.floor(r() * ms.length)];
      out.push({ game: g.name, who: 'me', s, m, s2: g.apply ? g.apply(s, m) : g.step(s, m) });
    }
  }
  return out;
}
const dayOf = (t) => { const d = new Date(t); return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate(); };
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return null; } };
function load(dir) { const j = dir && readJson(path.join(dir, 'worldmodel.json')); return j && j.model ? WorldModel.from(j.model) : null; }
// the nightly update. -> {kept, why, rows, heldout: {old, new}, fixed: {old, new}, line}
function nightly(o) {
  o = o || {}; const dir = o.dir, now = (o.now || Date.now)();
  const log = o.log || new GameLog({ dir, now: o.now }); if (log.trim) log.trim();
  const prevJ = dir ? readJson(path.join(dir, 'worldmodel.json')) : null;
  const quarantine = new Set((prevJ && prevJ.quarantine) || []);
  const rows = log.rows().filter((r) => r && r.t && ADAPT[r.game] && !quarantine.has(dayOf(r.t)));
  const cur = load(dir);
  const res = { at: now, rows: rows.length, kept: false, why: '' };
  if (!rows.length) { res.why = 'no game logs'; res.line = 'World model: no games played, nothing to learn.'; return finish(dir, res); }
  const last = Math.max(...rows.map((r) => dayOf(r.t)));
  const train = rows.filter((r) => dayOf(r.t) < last), held = rows.filter((r) => dayOf(r.t) === last);
  const cand = new WorldModel(); cand.learn(train);
  const fixed = fixedChecks(o.games || require('./games').GAMES);
  const score = (m, rs) => (m ? m.score(rs) : { n: rs.filter((r) => r.who !== 'them').length, right: 0, acc: 0 });
  const hOld = score(cur, held), hNew = score(cand, held), fOld = score(cur, fixed), fNew = score(cand, fixed);
  res.heldout = { old: hOld.acc, new: hNew.acc, n: hNew.n }; res.fixed = { old: fOld.acc, new: fNew.acc, n: fNew.n };
  // poison guard (on unless o.guard === false; adopted by its pre-registered rule, sleeplab RESULTS-poison-control-v1): the current model reads the latest day much worse than the fixed checks -> that day is quarantined
  // (never learned, now or later). Threshold GUARD_GAP, registered in the sleeplab MARKS-poison-control-v1.
  if (o.guard !== false && cur && hOld.acc != null && fOld.acc != null && hOld.n >= 5 && hOld.acc < fOld.acc - GUARD_GAP) {
    quarantine.add(last); res.quarantined = last;
    res.why = 'the latest day disagrees with what I know (' + pct(hOld.acc) + ' vs fixed ' + pct(fOld.acc) + '): quarantined';
    res.line = 'World model: kept the old one; quarantined the latest day of games (' + pct(hOld.acc) + ' agree vs ' + pct(fOld.acc) + ' on fixed checks).';
    try { const f = path.join(dir, 'worldmodel.json'), tmp = f + '.tmp'; fs.writeFileSync(tmp, JSON.stringify({ ...prevJ, quarantine: [...quarantine] })); fs.renameSync(tmp, f); } catch (e) { /* in memory only */ }
    return finish(dir, res);
  }
  const notWorse = (a, b) => (a == null || b == null) ? true : b >= a - 1e-9;
  if (!train.length) res.why = 'only one day of logs: nothing held out yet';
  else if (!notWorse(hOld.acc, hNew.acc)) res.why = 'worse on the latest day (' + pct(hOld.acc) + ' -> ' + pct(hNew.acc) + ')';
  else if (!notWorse(fOld.acc, fNew.acc)) res.why = 'worse on the fixed checks (' + pct(fOld.acc) + ' -> ' + pct(fNew.acc) + ')';
  else res.kept = true;
  if (res.kept) {
    const all = new WorldModel(); all.learn(rows);   // the kept model learns the held-out day too
    try { fs.mkdirSync(dir, { recursive: true }); const f = path.join(dir, 'worldmodel.json'), tmp = f + '.tmp'; fs.writeFileSync(tmp, JSON.stringify({ v: 1, at: now, rows: rows.length, heldout: res.heldout, fixed: res.fixed, quarantine: [...quarantine], model: all.toJSON() })); fs.renameSync(tmp, f); } catch (e) { res.kept = false; res.why = 'could not save: ' + e.message; }
  }
  res.line = 'World model: ' + (res.kept ? 'kept' : 'rolled back') + ', latest day ' + pct(hOld.acc) + ' -> ' + pct(hNew.acc) + ', fixed checks ' + pct(fOld.acc) + ' -> ' + pct(fNew.acc) + ' (' + rows.length + ' logged moves)' + (res.kept ? '' : ': ' + res.why) + '.';
  return finish(dir, res);
}
const pct = (x) => (x == null ? 'n/a' : Math.round(x * 100) + '%');
function finish(dir, res) { if (dir) { try { fs.mkdirSync(dir, { recursive: true }); fs.appendFileSync(path.join(dir, 'worldmodel-log.jsonl'), JSON.stringify({ ...res, line: undefined }) + '\n'); } catch (e) { /* log only */ } } return res; }

module.exports = { WorldModel, ADAPT, GameLog, fixedChecks, nightly, load, winnerOf };
