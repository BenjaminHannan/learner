'use strict';
// Little scientist, part 2: a puzzle generator that KNOWS the answer. A JS port of puzzle school's generator
// (~/learner-ops/premonition-research-20261031.noindex/puzzle-school/puzzles.py: families A-D, the same train / held-out rule split
// and the same ambiguity guard: an item is rejected if another rule of its family fits the shown part but gives another answer).
// Puzzle school found practice transfers to new rules of the same KINDS but over-applies moves on KidsARC, so three broader families
// are added: E size (the output grid has another size), F count (the answer is a number counted from a grid), G shape (objects).
// Held-out rules are never practised in bored mode; they are kept for the "poking vs reading" test. Pure JS, seeded, no model.
const { rng } = require('./index');

const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');
const TRAIN = { A: ['succ_last', 'extend', 'remove_double', 'reverse'], B: ['const_row', 'plus1', 'shuffle3', 'same_rows'], C: ['recolor', 'flip_lr', 'move_right', 'fill_bg'], D: ['plus_k', 'times2', 'alt', 'cycle3'],
  E: ['scale2', 'crop', 'tile_lr'], F: ['count_cells', 'count_colors'], G: ['hollow', 'keep_biggest'] };
const HELD = { A: ['pred_first', 'sort', 'fix_wrong', 'succ2_last'], B: ['minus1', 'sum', 'twodigit', 'double'], C: ['flip_ud', 'gravity', 'rot90', 'move_down'], D: ['squares', 'fib', 'grow', 'minus_k'],
  E: ['top_half', 'tile_ud'], F: ['count_rows', 'most_color'], G: ['fill_box', 'drop_singles'] };
const ALL = {}; for (const f of Object.keys(TRAIN)) ALL[f] = TRAIN[f].concat(HELD[f]);
const FAMILIES = Object.keys(TRAIN);
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ri = (r, lo, hi) => lo + Math.floor(r() * (hi - lo + 1));
const sample = (r, xs, k) => { const a = xs.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, k); };

// ---- A: letter strings ----------------------------------------------------------------------------------------------------
function aApply(rule, s) {
  const n = s.length;
  switch (rule) {
    case 'succ_last': return s[n - 1] < 25 ? s.slice(0, -1).concat([s[n - 1] + 1]) : null;
    case 'extend': return s[n - 1] < 25 ? s.concat([s[n - 1] + 1]) : null;
    case 'remove_double': { const p = []; for (let i = 0; i < n - 1; i++) if (s[i] === s[i + 1]) p.push(i); return p.length === 1 ? s.slice(0, p[0]).concat(s.slice(p[0] + 1)) : null; }
    case 'reverse': return s.slice().reverse();
    case 'pred_first': return s[0] > 0 ? [s[0] - 1].concat(s.slice(1)) : null;
    case 'sort': return s.slice().sort((a, b) => a - b);
    case 'fix_wrong': { const f = s.map((_, j) => s[0] + j); const d = f.map((v, j) => (v !== s[j] ? j : -1)).filter((j) => j >= 0); return d.length === 1 && d[0] >= 1 && f[n - 1] <= 25 ? f : null; }
    case 'succ2_last': return s[n - 1] <= 23 ? s.slice(0, -1).concat([s[n - 1] + 2]) : null;
  }
  throw new Error('rule ' + rule);
}
function aGen(rule, r) {
  const run = () => { const L = ri(r, 3, 5), st = ri(r, 0, 26 - L); return Array.from({ length: L }, (_, j) => st + j); };
  const side = () => {
    if (rule === 'succ_last' || rule === 'extend') { const L = ri(r, 3, 5), st = ri(r, 0, 25 - L); return Array.from({ length: L }, (_, j) => st + j); }
    if (rule === 'succ2_last') { const L = ri(r, 3, 5), st = ri(r, 0, 24 - L); return Array.from({ length: L }, (_, j) => st + j); }
    if (rule === 'pred_first') { const L = ri(r, 3, 5), st = ri(r, 1, 26 - L); return Array.from({ length: L }, (_, j) => st + j); }
    if (rule === 'remove_double') { const x = run(), i = ri(r, 0, x.length - 1); return x.slice(0, i + 1).concat(x.slice(i)); }
    if (rule === 'sort') { const x = run(); for (;;) { const y = sample(r, x, x.length); if (!eq(x, y)) return y; } }
    if (rule === 'fix_wrong') { const x = run(), i = ri(r, 1, x.length - 1); let w; do { w = ri(r, 0, 25); } while (w === x[i]); x[i] = w; return x; }
    return run();
  };
  const A = side(), C = side(); if (eq(A, C)) return null;
  const B = aApply(rule, A), D = aApply(rule, C);
  if (!B || !D || eq(B, A) || eq(D, C)) return null;
  return { shown: [A, B, C], answer: D };
}
const aText = (s) => s.map((i) => LETTERS[i]).join(' ');
function aPredict(rule, [A, B, C]) { const b = aApply(rule, A); return b && eq(b, B) ? aApply(rule, C) : null; }

// ---- B: 3x3 number matrices, last cell hidden -------------------------------------------------------------------------------
function bPredict(rule, [rows, p]) {
  const [r1, r2] = rows;
  switch (rule) {
    case 'const_row': return rows.every((x) => x[0] === x[1] && x[1] === x[2]) && p[0] === p[1] ? p[0] : null;
    case 'plus1': case 'minus1': { const d = rule === 'plus1' ? 1 : -1; return rows.every((x) => x[1] - x[0] === d && x[2] - x[1] === d) && p[1] - p[0] === d ? p[1] + d : null; }
    case 'shuffle3': {
      if (new Set(r1).size !== 3 || !eq(r1.slice().sort(), r2.slice().sort()) || eq(r1, r2) || p[0] === p[1] || !r1.includes(p[0]) || !r1.includes(p[1])) return null;
      const z = r1.find((v) => v !== p[0] && v !== p[1]); const t = [p[0], p[1], z]; return !eq(t, r1) && !eq(t, r2) ? z : null;
    }
    case 'same_rows': return eq(r1, r2) && p[0] === r1[0] && p[1] === r1[1] && new Set(r1).size === 3 ? r1[2] : null;
    case 'sum': return rows.every((x) => x[0] + x[1] === x[2]) ? p[0] + p[1] : null;
    case 'twodigit': return rows.every((x) => x[0] >= 10 && Math.floor(x[0] / 10) === Math.floor(x[1] / 10) && Math.floor(x[1] / 10) === Math.floor(x[2] / 10) && x[1] - x[0] === 1 && x[2] - x[1] === 1) && p[0] >= 10 && Math.floor(p[0] / 10) === Math.floor(p[1] / 10) && p[1] - p[0] === 1 && p[1] % 10 <= 8 ? p[1] + 1 : null;
    case 'double': return rows.every((x) => x[1] === 2 * x[0] && x[2] === 2 * x[1] && x[0] > 0) && p[1] === 2 * p[0] && p[0] > 0 ? 2 * p[1] : null;
  }
  throw new Error('rule ' + rule);
}
function bGen(rule, r) {
  const d3 = (lo, hi) => sample(r, Array.from({ length: hi - lo + 1 }, (_, i) => lo + i), 3);
  let rows;
  if (rule === 'const_row') rows = d3(0, 9).map((v) => [v, v, v]);
  else if (rule === 'plus1') rows = d3(0, 7).map((a) => [a, a + 1, a + 2]);
  else if (rule === 'minus1') rows = d3(2, 9).map((a) => [a, a - 1, a - 2]);
  else if (rule === 'shuffle3') { const v = d3(0, 9); rows = sample(r, [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]], 3).map((q) => q.map((i) => v[i])); }
  else if (rule === 'same_rows') { let row; do { row = d3(0, 9); } while (row[1] - row[0] === row[2] - row[1] && Math.abs(row[1] - row[0]) === 1); rows = [row, row.slice(), row.slice()]; }
  else if (rule === 'sum') { const pairs = []; for (let a = 1; a < 10; a++) for (let b = 1; b < 10; b++) pairs.push([a, b]); rows = sample(r, pairs, 3).map(([a, b]) => [a, b, a + b]); }
  else if (rule === 'twodigit') rows = d3(1, 9).map((t) => { const o = ri(r, 0, 7); return [10 * t + o, 10 * t + o + 1, 10 * t + o + 2]; });
  else if (rule === 'double') rows = d3(1, 6).map((a) => [a, 2 * a, 4 * a]);
  else throw new Error('rule ' + rule);
  return { shown: [[rows[0], rows[1]], rows[2].slice(0, 2)], answer: rows[2][2], rows };
}

// ---- grids (C, E, F, G): digits 0-7, 0 = background --------------------------------------------------------------------------
const gText = (g) => g.map((row) => row.join('')).join('/');
function randGrid(r, n, m, o) {
  o = o || {}; m = m || n;
  const k = o.k || (n * m <= 9 ? ri(r, 2, 5) : ri(r, 3, Math.min(9, Math.floor(n * m / 2))));
  const cells = []; for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) if (!(o.edge === 'right' && j === m - 1) && !(o.edge === 'bottom' && i === n - 1)) cells.push([i, j]);
  const g = Array.from({ length: n }, () => Array(m).fill(0)); const cols = [1, 2, 3, 4, 5, 6, 7].filter((c) => !(o.forbid || []).includes(c));
  for (const [i, j] of sample(r, cells, k)) g[i][j] = cols[Math.floor(r() * cols.length)];
  if (o.force != null && !g.some((row) => row.includes(o.force))) { const nz = []; g.forEach((row, i) => row.forEach((v, j) => v && nz.push([i, j]))); const [i, j] = nz[Math.floor(r() * nz.length)]; g[i][j] = o.force; }
  return g;
}
const G = {
  flip_lr: (g) => g.map((r) => r.slice().reverse()),
  flip_ud: (g) => g.slice().reverse().map((r) => r.slice()),
  rot90: (g) => g[0].map((_, i) => g.map((r) => r[i]).reverse()),
  move_right: (g) => (g.some((r) => r[r.length - 1] !== 0) ? null : g.map((r) => [0].concat(r.slice(0, -1)))),
  move_down: (g) => (g[g.length - 1].some((v) => v) ? null : [Array(g[0].length).fill(0)].concat(g.slice(0, -1).map((r) => r.slice()))),
  gravity: (g) => { const n = g.length, out = g.map((r) => r.map(() => 0)); for (let j = 0; j < g[0].length; j++) { const col = g.map((r) => r[j]).filter(Boolean); col.reverse().forEach((v, k) => { out[n - 1 - k][j] = v; }); } return out; },
  // E: size
  scale2: (g) => g.flatMap((r) => { const w = r.flatMap((v) => [v, v]); return [w, w.slice()]; }),
  crop: (g) => { const nz = []; g.forEach((r, i) => r.forEach((v, j) => v && nz.push([i, j]))); if (!nz.length) return null; const i0 = Math.min(...nz.map((p) => p[0])), i1 = Math.max(...nz.map((p) => p[0])), j0 = Math.min(...nz.map((p) => p[1])), j1 = Math.max(...nz.map((p) => p[1])); if (i0 === 0 && j0 === 0 && i1 === g.length - 1 && j1 === g[0].length - 1) return null; return g.slice(i0, i1 + 1).map((r) => r.slice(j0, j1 + 1)); },
  tile_lr: (g) => g.map((r) => r.concat(r)),
  tile_ud: (g) => g.map((r) => r.slice()).concat(g.map((r) => r.slice())),
  top_half: (g) => (g.length % 2 ? null : g.slice(0, g.length / 2).map((r) => r.slice())),
  // G: shape
  hollow: (g) => { const box = solidBox(g); if (!box) return null; const { i0, i1, j0, j1 } = box; if (i1 - i0 < 2 || j1 - j0 < 2) return null; return g.map((r, i) => r.map((v, j) => (i > i0 && i < i1 && j > j0 && j < j1 ? 0 : v))); },
  fill_box: (g) => { const b = ringBox(g); if (!b) return null; return g.map((r, i) => r.map((v, j) => (i > b.i0 && i < b.i1 && j > b.j0 && j < b.j1 ? b.c : v))); },
  keep_biggest: (g) => { const cnt = {}; g.flat().forEach((v) => v && (cnt[v] = (cnt[v] || 0) + 1)); const e = Object.entries(cnt).sort((a, b) => b[1] - a[1]); if (e.length < 2 || e[0][1] === e[1][1]) return null; const c = +e[0][0]; return g.map((r) => r.map((v) => (v === c ? v : 0))); },
  drop_singles: (g) => { let ch = false; const out = g.map((r, i) => r.map((v, j) => { if (!v) return 0; const nb = [[i - 1, j], [i + 1, j], [i, j - 1], [i, j + 1]].some(([a, b]) => g[a] && g[a][b] === v); if (!nb) { ch = true; return 0; } return v; })); return ch ? out : null; }
};
function solidBox(g) { const nz = []; g.forEach((r, i) => r.forEach((v, j) => v && nz.push([i, j, v]))); if (!nz.length) return null; const c = nz[0][2]; const i0 = Math.min(...nz.map((p) => p[0])), i1 = Math.max(...nz.map((p) => p[0])), j0 = Math.min(...nz.map((p) => p[1])), j1 = Math.max(...nz.map((p) => p[1])); for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) if (g[i][j] !== c) return null; return nz.length === (i1 - i0 + 1) * (j1 - j0 + 1) ? { i0, i1, j0, j1, c } : null; }
function ringBox(g) { const nz = []; g.forEach((r, i) => r.forEach((v, j) => v && nz.push([i, j, v]))); if (!nz.length) return null; const c = nz[0][2]; const i0 = Math.min(...nz.map((p) => p[0])), i1 = Math.max(...nz.map((p) => p[0])), j0 = Math.min(...nz.map((p) => p[1])), j1 = Math.max(...nz.map((p) => p[1])); if (i1 - i0 < 2 || j1 - j0 < 2) return null; for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const edge = i === i0 || i === i1 || j === j0 || j === j1; if (edge ? g[i][j] !== c : g[i][j] !== 0) return null; } return nz.length === 2 * (i1 - i0 + 1) + 2 * (j1 - j0 - 1) ? { i0, i1, j0, j1, c } : null; }
const COUNT = {
  count_cells: (g) => g.flat().filter(Boolean).length,
  count_colors: (g) => new Set(g.flat().filter(Boolean)).size,
  count_rows: (g) => g.filter((r) => r.some(Boolean)).length,
  most_color: (g) => { const cnt = {}; g.flat().forEach((v) => v && (cnt[v] = (cnt[v] || 0) + 1)); const e = Object.entries(cnt).sort((a, b) => b[1] - a[1]); return e.length && (e.length === 1 || e[0][1] > e[1][1]) ? +e[0][0] : null; }
};
// C keeps puzzle school's parameterised rules (recolor x->y, fill background with c): the parameter is read off A -> B
function cInfer(rule, A, B) {
  if (rule === 'recolor') { const d = []; A.forEach((r, i) => r.forEach((a, j) => { if (a !== B[i][j]) d.push([a, B[i][j]]); })); if (!d.length) return null; const xs = new Set(d.map((x) => x[0])), ys = new Set(d.map((x) => x[1])); if (xs.size !== 1 || ys.size !== 1) return null; const [x] = xs, [y] = ys; return x && y && x !== y ? [x, y] : null; }
  if (rule === 'fill_bg') { const cs = new Set(); A.forEach((r, i) => r.forEach((a, j) => { if (a === 0) cs.add(B[i][j]); })); if (cs.size !== 1) return null; const [c] = cs; return c || null; }
  return [];
}
function cApply(rule, g, extra) {
  if (rule === 'recolor') { const [x, y] = extra; return g.some((r) => r.includes(x)) ? g.map((r) => r.map((v) => (v === x ? y : v))) : null; }
  if (rule === 'fill_bg') return g.some((r) => r.includes(extra)) ? null : g.map((r) => r.map((v) => v || extra));
  return G[rule] ? G[rule](g) : null;
}
function gridPredict(fam, rule, shown) {
  const pairs = shown.examples, C = shown.test;
  if (fam === 'F') { for (const [a, b] of pairs) if (COUNT[rule](a) !== b) return null; return COUNT[rule](C); }
  if (fam === 'C') { const [[A, B]] = pairs; const ex = cInfer(rule, A, B); if (ex == null) return null; if (!eq(cApply(rule, A, ex), B)) return null; return cApply(rule, C, ex); }
  for (const [a, b] of pairs) if (!eq(G[rule](a), b)) return null;
  return G[rule](C);
}
function gridGen(fam, rule, r) {
  const n = fam === 'E' && rule === 'top_half' ? 4 : ri(r, 3, 4);
  let ex = [];
  if (fam === 'C' && rule === 'recolor') { const x = ri(r, 1, 7); let y; do { y = ri(r, 1, 7); } while (y === x); ex = [x, y]; }
  if (fam === 'C' && rule === 'fill_bg') ex = ri(r, 1, 7);
  const mk = () => {
    if (fam === 'C') {
      const edge = { move_right: 'right', move_down: 'bottom' }[rule];
      return randGrid(r, n, n, { edge, forbid: rule === 'fill_bg' ? [ex] : [], force: rule === 'recolor' ? ex[0] : null });
    }
    if (fam === 'G' && rule === 'hollow') { const g = Array.from({ length: 5 }, () => Array(5).fill(0)); const h = ri(r, 3, 5), w = ri(r, 3, 5), i0 = ri(r, 0, 5 - h), j0 = ri(r, 0, 5 - w), c = ri(r, 1, 7); for (let i = i0; i < i0 + h; i++) for (let j = j0; j < j0 + w; j++) g[i][j] = c; return g; }
    if (fam === 'G' && rule === 'fill_box') { const g = Array.from({ length: 5 }, () => Array(5).fill(0)); const h = ri(r, 3, 5), w = ri(r, 3, 5), i0 = ri(r, 0, 5 - h), j0 = ri(r, 0, 5 - w), c = ri(r, 1, 7); for (let i = i0; i < i0 + h; i++) for (let j = j0; j < j0 + w; j++) if (i === i0 || i === i0 + h - 1 || j === j0 || j === j0 + w - 1) g[i][j] = c; return g; }
    if (fam === 'G') return randGrid(r, 4, 4, { k: ri(r, 4, 8) });
    if (fam === 'E' && rule === 'crop') { const g = Array.from({ length: 5 }, () => Array(5).fill(0)); const h = ri(r, 1, 3), w = ri(r, 1, 3), i0 = ri(r, 0, 5 - h), j0 = ri(r, 0, 5 - w); for (let i = i0; i < i0 + h; i++) for (let j = j0; j < j0 + w; j++) g[i][j] = r() < 0.7 ? ri(r, 1, 7) : 0; g[i0][j0] = ri(r, 1, 7); g[i0 + h - 1][j0 + w - 1] = ri(r, 1, 7); return g; }
    if (fam === 'E') return randGrid(r, n, fam === 'E' && rule === 'top_half' ? 3 : n, { k: ri(r, 2, 5) });
    return randGrid(r, n, n, { k: ri(r, 2, Math.min(9, n * n - 2)) });
  };
  const apply = (g, ex) => (fam === 'F' ? COUNT[rule](g) : cApply(rule, g, ex));
  const nEx = fam === 'C' ? 1 : 2;
  const grids = [];
  for (let i = 0; i < nEx + 1; i++) {
    grids.push(mk());
  }
  if (new Set(grids.map(gText)).size !== grids.length) return null;
  const outs = grids.map((g) => apply(g, ex));
  if (outs.some((o) => o == null) || (fam !== 'F' && grids.some((g, i) => eq(g, outs[i])))) return null;
  return { shown: { examples: grids.slice(0, nEx).map((g, i) => [g, outs[i]]), test: grids[nEx] }, answer: outs[nEx] };
}

// ---- D: number sequences, 5 shown, the 6th asked --------------------------------------------------------------------------------
function dPredict(rule, t) {
  const df = [0, 1, 2, 3].map((i) => t[i + 1] - t[i]);
  switch (rule) {
    case 'plus_k': return new Set(df).size === 1 && df[0] > 0 ? t[4] + df[0] : null;
    case 'minus_k': return new Set(df).size === 1 && df[0] < 0 ? t[4] + df[0] : null;
    case 'times2': return [0, 1, 2, 3].every((i) => t[i + 1] === 2 * t[i]) ? 2 * t[4] : null;
    case 'alt': return df[0] === df[2] && df[1] === df[3] && df[0] !== df[1] && df[0] > 0 && df[1] > 0 ? t[4] + df[0] : null;
    case 'cycle3': return t[3] === t[0] && t[4] === t[1] && new Set([t[0], t[1], t[2]]).size === 3 ? t[2] : null;
    case 'squares': { const r = Math.round(Math.sqrt(t[0])); return r >= 1 && r * r === t[0] && t.every((v, i) => v === (r + i) * (r + i)) ? (r + 5) * (r + 5) : null; }
    case 'fib': return [0, 1, 2].every((i) => t[i + 2] === t[i] + t[i + 1]) ? t[3] + t[4] : null;
    case 'grow': return df[0] >= 1 && [0, 1, 2].every((i) => df[i + 1] === df[i] + 1) ? t[4] + df[3] + 1 : null;
  }
  throw new Error('rule ' + rule);
}
function dGen(rule, r) {
  let t;
  if (rule === 'plus_k') { const s = ri(r, 1, 40), k = ri(r, 1, 5); t = [0, 1, 2, 3, 4, 5].map((i) => s + k * i); }
  else if (rule === 'minus_k') { const s = ri(r, 30, 50), k = ri(r, 1, 5); t = [0, 1, 2, 3, 4, 5].map((i) => s - k * i); }
  else if (rule === 'times2') { const s = ri(r, 1, 40); t = [0, 1, 2, 3, 4, 5].map((i) => s * 2 ** i); }
  else if (rule === 'alt') { const s = ri(r, 1, 20), [a, b] = sample(r, [1, 2, 3, 4, 5], 2); t = [s]; for (let i = 0; i < 5; i++) t.push(t[t.length - 1] + (i % 2 ? b : a)); }
  else if (rule === 'cycle3') { const [x, y, z] = sample(r, [1, 2, 3, 4, 5, 6, 7, 8, 9], 3); t = [x, y, z, x, y, z]; }
  else if (rule === 'squares') { const s = ri(r, 1, 20); t = [0, 1, 2, 3, 4, 5].map((i) => (s + i) * (s + i)); }
  else if (rule === 'fib') { t = [ri(r, 1, 5), ri(r, 1, 5)]; while (t.length < 6) t.push(t[t.length - 1] + t[t.length - 2]); }
  else if (rule === 'grow') { const s = ri(r, 1, 10), g = ri(r, 1, 3); t = [s]; for (let i = 0; i < 5; i++) t.push(t[t.length - 1] + g + i); }
  else throw new Error('rule ' + rule);
  return { shown: t.slice(0, 5), answer: t[5] };
}

// ---- generic ------------------------------------------------------------------------------------------------------------------
function predict(fam, rule, shown) {
  if (fam === 'A') return aPredict(rule, shown);
  if (fam === 'B') return bPredict(rule, shown);
  if (fam === 'D') return dPredict(rule, shown);
  return gridPredict(fam, rule, shown);
}
function ambiguousWith(fam, rule, shown, answer) { for (const r2 of ALL[fam]) { if (r2 === rule) continue; let a2 = null; try { a2 = predict(fam, r2, shown); } catch (e) { a2 = null; } if (a2 != null && !eq(a2, answer)) return r2; } return null; }
const ansText = (fam, a) => (fam === 'A' ? aText(a) : Array.isArray(a) ? gText(a) : String(a));
function render(fam, shown) {
  if (fam === 'A') return 'If ' + aText(shown[0]) + ' changes to ' + aText(shown[1]) + ', what does ' + aText(shown[2]) + ' change to?';
  if (fam === 'B') return shown[0].concat([shown[1].concat(['?'])]).map((r, i) => 'Row ' + (i + 1) + ': ' + r.join(' ')).join('\n') + '\nWhat number replaces the ?';
  if (fam === 'D') return shown.join(', ') + ', ?\nWhat number comes next?';
  const ex = shown.examples.map(([a, b], i) => 'Example ' + (i + 1) + ': ' + gText(a) + ' -> ' + (fam === 'F' ? b : gText(b))).join('\n');
  return 'Grids are rows separated by /, digits are colours, 0 is empty.\n' + ex + '\nTest: ' + gText(shown.test) + ' -> ?\n' + (fam === 'F' ? 'What number?' : 'What is the output grid?');
}
// one unambiguous puzzle for (family, rule, seed): {family, rule, puzzle, answer (text), seed} or null after 400 tries
function make(fam, rule, seed) {
  const r = rng(seed * 101 + fam.charCodeAt(0) * 7 + ALL[fam].indexOf(rule));
  for (let i = 0; i < 400; i++) {
    const g = fam === 'A' ? aGen(rule, r) : fam === 'B' ? bGen(rule, r) : fam === 'D' ? dGen(rule, r) : gridGen(fam, rule, r);
    if (!g) continue;
    if (!eq(predict(fam, rule, g.shown), g.answer)) throw new Error('generator disagrees with its own rule: ' + fam + ' ' + rule);
    if (ambiguousWith(fam, rule, g.shown, g.answer)) continue;
    return { family: fam, rule, puzzle: render(fam, g.shown), answer: ansText(fam, g.answer), seed };
  }
  return null;
}
// answers are compared after removing spaces and case (grids may be written with or without spaces/commas)
const normAns = (s) => String(s == null ? '' : s).toLowerCase().replace(/^\s*(?:answer|output)\s*[:=]\s*/, '').replace(/[`"'.]/g, '').replace(/[\s,]+/g, ' ').trim().replace(/(\d) (?=\d)/g, '$1');
const correct = (given, answer) => normAns(given) === normAns(answer) || normAns(given).replace(/ /g, '') === normAns(answer).replace(/ /g, '');

module.exports = { make, predict, ambiguousWith, render, correct, normAns, TRAIN, HELD, ALL, FAMILIES, G, COUNT, gText };
