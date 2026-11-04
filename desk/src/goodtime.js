'use strict';
// "Is now a good time?" judge for Glim's real hands (track I5, 2026-11-04). VETO ONLY: it can make Glim wait longer before it asks
// or before it goes ahead; it can never loosen Ben's rule (user idle >= 2 min, then ask, then go after 1 min without an answer).
//
// A tiny logistic regression over hand-made features of the moment (hour, front-app category, how long the user has been idle,
// recent pauses). It predicts p = "the user's own input arrives within the next H seconds" (that would be a collision).
// Labels come from the day's real experience only (two-ways rule: it trains ONLY at night, in sleep):
//   - 'watch' rows: while the user is idle >= 2 min, once a minute, y = 1 if the user's own input came back within H s (seen
//     afterwards from the input stream; no action needed, so there is no selection bias);
//   - interruptions (y = 1): a collision (user input during a Glim action), an undo / close within 30 s, "stop" / "not now", a "No";
//   - clean positives (y = 0): a Glim action that finished with no user input during it.
// Nightly: src/sleepjudges.js engine (replay -> refit -> seatbelt on the held-out day -> keep or roll back). Features, never pictures.
// Toy result (premonition-handslab-i5 RESULTS.md): NOT PROVEN after 3 registered versions. Best (v3: veto only the unanswered
// go-ahead) cut collisions 20-40 % at ~7 % fewer tasks, short of the registered 50 % cut. So: hands.judge stays OFF and main.js does
// NOT train it at night yet; the interruption log keeps collecting rows for a future version.
// Two-ways rule: if it is ever switched on, it trains ONLY at night (sleepjudges engine), never while awake.

const APPS = ['code', 'browser', 'video', 'game', 'chat', 'docs', 'school', 'other'];
const H = 90;               // seconds ahead a collision would matter (the longest typical action + margin)
// veto when the moment is riskier than a typical idle moment: p > the base rate of y in the rows the judge was trained on (v2;
// v1's fixed 0.5 never fired: p sits at 0.1-0.4, see premonition-handslab-i5 DIAG-goodtime-v1.md). 0.5 = fallback for an old model.
const THRESHOLD = 0.5;
const L2S = [0.01, 0.1, 1];
const clip = (p) => Math.max(1e-4, Math.min(1 - 1e-4, p));
const bce = (p, y) => (y ? -Math.log(clip(p)) : -Math.log(clip(1 - p)));
const sig = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

// f: {hour, app, idleS, pauses30, lastPauseS, activeMin30}
function encode(f) {
  f = f || {};
  const x = [1];
  const hb = Math.max(0, Math.min(5, Math.floor((Number(f.hour) || 0) / 4)));
  for (let i = 0; i < 6; i++) x.push(i === hb ? 1 : 0);
  const a = APPS.includes(f.app) ? f.app : 'other';
  for (const c of APPS) x.push(c === a ? 1 : 0);
  const li = Math.log1p(Math.max(0, Number(f.idleS) || 0) / 60);
  x.push(li);
  for (const c of APPS) x.push(c === a ? li : 0);   // "a call that has been quiet for 5 min" differs from "the editor quiet for 5 min"
  x.push(Math.min(10, Number(f.pauses30) || 0) / 10);
  x.push(Math.log1p(Math.max(0, Number(f.lastPauseS) || 0) / 60));
  x.push(Math.min(30, Number(f.activeMin30) || 0) / 30);
  return x;
}
const DIM = encode({}).length;
function predict(m, f) {
  if (!m || !Array.isArray(m.w) || m.w.length !== DIM) return null;   // not trained yet: no opinion (never vetoes)
  const x = encode(f); let z = 0; for (let i = 0; i < DIM; i++) z += m.w[i] * x[i];
  return sig(z);
}
// full-batch gradient descent with L2 (bias not penalised); rows: [{f, y}]
function fit(rows, l2, iters) {
  const X = rows.map((r) => encode(r.f)), Y = rows.map((r) => (r.y ? 1 : 0)), n = Math.max(1, rows.length);
  const w = new Array(DIM).fill(0); const pos = Y.reduce((a, b) => a + b, 0); w[0] = Math.log((pos + 1) / (n - pos + 1));
  const lr = 0.5, T = iters || 300;
  for (let t = 0; t < T; t++) {
    const g = new Array(DIM).fill(0);
    for (let k = 0; k < X.length; k++) { let z = 0; const x = X[k]; for (let i = 0; i < DIM; i++) z += w[i] * x[i]; const e = sig(z) - Y[k]; for (let i = 0; i < DIM; i++) g[i] += e * x[i]; }
    for (let i = 0; i < DIM; i++) w[i] -= lr * (g[i] / n + (i ? l2 * w[i] : 0));
  }
  return w;
}
// veto only: {veto, p}. Never returns "go" on its own; the caller still applies Ben's fixed rule first.
function veto(m, f, threshold) {
  const p = predict(m, f);
  const th = threshold != null ? threshold : m && Number.isFinite(m.base) ? m.base : THRESHOLD;
  return { veto: p != null && p > th, p, th };
}

// sleepjudges part: the same engine as the other small judges (held-out day, keep or roll back, hold a contradicting day)
const goodTimePart = () => ({
  name: 'goodtime',
  init: () => ({ w: null }),
  score(m, log) {
    let L = 0, S = 0;
    for (const r of log) { const p = predict(m, r.f); const q = p == null ? 0.5 : p; L += bce(q, r.y); S += Math.sign(bce(q, r.y) - bce(1 - q, r.y)); }
    const n = Math.max(1, log.length);
    return { loss: L / n, gap: m && m.w ? S / n : 0, model: m };
  },
  candidates(train) {
    const all = [].concat(...train);
    if (all.length < 20) return [];
    const base = all.reduce((a, r) => a + (r.y ? 1 : 0), 0) / all.length;
    return L2S.map((l2) => ({ model: { w: fit(all, l2), l2, n: all.length, base }, tag: 'l2 ' + l2 + ', ' + all.length + ' rows' }));
  },
  deploy: (c, live, held, s) => s.model
});

module.exports = { encode, predict, fit, veto, goodTimePart, APPS, H, THRESHOLD, DIM };
