'use strict';
// Sleep track T3 (2026-11-04). Toy-proven in ~/learner-ops/premonition-sleeplab-t3 (MARKS/RESULTS-shapekeys-v1: on a set where
// same-shape notes share no words, recall@5 53-58 % vs plain 14-17 % and rule-masked 14-19 %, 3/3 seeds). Used by src/patterns.js.
// Learned shape keys (mechanism 2): a small LOW-RANK correction on top of the rule-masked hashing shape vector,
//   key(x) = normalise(h + U (Vᵀ h)),  h = the 256-dim hashing vector of the masked text (src/patterns.js embed(mask(text))).
// U starts at zero, so an untrained projector gives exactly the rule-masked shape key. Sleep trains it contrastively (InfoNCE):
// positives = two members of the same pattern cluster, negatives = members of OTHER clusters in the same batch. Plain JS, no deps;
// 2 x 256 x rank floats (rank 32 -> 64 KB).

function rng(seed) { let a = (seed >>> 0) || 1; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const f32b64 = (a) => Buffer.from(a.buffer, a.byteOffset, a.byteLength).toString('base64');
const b64f32 = (s, n) => { const b = Buffer.from(String(s || ''), 'base64'); if (b.length !== n * 4) return null; const out = new Float32Array(n); for (let i = 0; i < n; i++) out[i] = b.readFloatLE(i * 4); return out; };

class ShapeProjector {
  constructor(o) {
    o = o || {}; this.dim = o.dim || 256; this.rank = o.rank || 32;
    const n = this.dim * this.rank;
    this.U = (o.U && b64f32(o.U, n)) || new Float32Array(n);
    this.V = (o.V && b64f32(o.V, n)) || null;
    if (!this.V) { const r = rng(o.seed || 1); this.V = new Float32Array(n); const sc = 1 / Math.sqrt(this.dim); for (let i = 0; i < n; i++) this.V[i] = (r() * 2 - 1) * sc * Math.sqrt(3); }
    this.trained = o.trained || null;
  }
  toJSON() { return { v: 1, dim: this.dim, rank: this.rank, U: f32b64(this.U), V: f32b64(this.V), trained: this.trained }; }
  static from(j) { return j && j.v === 1 ? new ShapeProjector(j) : null; }
  clone() { return new ShapeProjector(JSON.parse(JSON.stringify(this.toJSON()))); }
  // h (unit Float32Array, dim) -> {z, s, n}
  _fwd(h) {
    const D = this.dim, R = this.rank, s = new Float32Array(R), z = Float32Array.from(h);
    for (let k = 0; k < R; k++) { let a = 0; for (let i = 0; i < D; i++) a += this.V[i * R + k] * h[i]; s[k] = a; }
    for (let i = 0; i < D; i++) { let a = 0; for (let k = 0; k < R; k++) a += this.U[i * R + k] * s[k]; z[i] += a; }
    let n = 0; for (let i = 0; i < D; i++) n += z[i] * z[i]; n = Math.sqrt(n) || 1;
    return { z, s, n };
  }
  project(h) { const { z, n } = this._fwd(h); for (let i = 0; i < z.length; i++) z[i] /= n; return z; }
  // groups: [[h, h, ...], ...] (each group >= 2 vectors). -> {steps, loss0, loss}
  train(groups, o) {
    o = o || {}; const steps = o.steps || 400, B0 = o.batch || 32, lr = o.lr || 0.01, temp = o.temp || 0.1, r = rng(o.seed || 7);
    const G = (groups || []).filter((g) => g && g.length >= 2); if (G.length < 2) return { steps: 0, loss: null, why: 'fewer than 2 groups' };
    const D = this.dim, R = this.rank, n = D * R;
    // o.nearCos: two clusters whose mean vectors are already at least this similar are NOT used as each other's negatives
    let near = null;
    if (o.nearCos != null) {
      const cen = G.map((g) => { const c = new Float32Array(D); for (const h of g) for (let q = 0; q < D; q++) c[q] += h[q]; let m = 0; for (let q = 0; q < D; q++) m += c[q] * c[q]; m = Math.sqrt(m) || 1; for (let q = 0; q < D; q++) c[q] /= m; return c; });
      near = G.map((_, a) => G.map((__, b) => { if (a === b) return false; let d = 0; for (let q = 0; q < D; q++) d += cen[a][q] * cen[b][q]; return d >= o.nearCos; }));
    }
    const mU = new Float32Array(n), vU = new Float32Array(n), mV = new Float32Array(n), vV = new Float32Array(n);
    let loss0 = null, lossEnd = null, t = 0;
    for (let st = 0; st < steps; st++) {
      // B distinct groups, one anchor + one positive each
      const B = Math.min(B0, G.length), idx = [];
      const pool = G.map((_, i) => i); for (let i = 0; i < B; i++) { const j = i + Math.floor(r() * (pool.length - i)); [pool[i], pool[j]] = [pool[j], pool[i]]; idx.push(pool[i]); }
      const A = [], P = [];
      for (const gi of idx) { const g = G[gi], a = Math.floor(r() * g.length); let p = Math.floor(r() * (g.length - 1)); if (p >= a) p++; A.push(this._fwd(g[a])); P.push(this._fwd(g[p])); A[A.length - 1].h = g[a]; P[P.length - 1].h = g[p]; }
      const ua = A.map((x) => Float32Array.from(x.z, (v) => v / x.n)), up = P.map((x) => Float32Array.from(x.z, (v) => v / x.n));
      const gA = A.map(() => new Float32Array(D)), gP = P.map(() => new Float32Array(D));
      let loss = 0;
      // symmetric InfoNCE
      for (const dir of [0, 1]) {
        const X = dir ? up : ua, Y = dir ? ua : up, gX = dir ? gP : gA, gY = dir ? gA : gP;
        for (let i = 0; i < B; i++) {
          const lg = new Float64Array(B); let mx = -Infinity;
          for (let j = 0; j < B; j++) { if (near && j !== i && near[idx[i]][idx[j]]) { lg[j] = -Infinity; continue; } let d = 0; for (let q = 0; q < D; q++) d += X[i][q] * Y[j][q]; lg[j] = d / temp; if (lg[j] > mx) mx = lg[j]; }
          let se = 0; for (let j = 0; j < B; j++) { lg[j] = lg[j] === -Infinity ? 0 : Math.exp(lg[j] - mx); se += lg[j]; }
          loss += -Math.log(lg[i] / se) / (2 * B);
          for (let j = 0; j < B; j++) { const c = (lg[j] / se - (i === j ? 1 : 0)) / (2 * B * temp); if (!c) continue; for (let q = 0; q < D; q++) { gX[i][q] += c * Y[j][q]; gY[j][q] += c * X[i][q]; } }
        }
      }
      if (st === 0) loss0 = loss; lossEnd = loss;
      // back through the normalisation and the low-rank map
      const dU = new Float32Array(n), dV = new Float32Array(n);
      const back = (x, u, g) => {
        let ug = 0; for (let q = 0; q < D; q++) ug += u[q] * g[q];
        const dz = new Float32Array(D); for (let q = 0; q < D; q++) dz[q] = (g[q] - u[q] * ug) / x.n;
        const ds = new Float32Array(R);
        for (let q = 0; q < D; q++) { if (!dz[q]) continue; for (let k = 0; k < R; k++) { dU[q * R + k] += dz[q] * x.s[k]; ds[k] += this.U[q * R + k] * dz[q]; } }
        for (let q = 0; q < D; q++) { const hq = x.h[q]; if (!hq) continue; for (let k = 0; k < R; k++) dV[q * R + k] += hq * ds[k]; }
      };
      for (let i = 0; i < B; i++) { back(A[i], ua[i], gA[i]); back(P[i], up[i], gP[i]); }
      // Adam
      t++; const b1 = 0.9, b2 = 0.999, c1 = 1 - Math.pow(b1, t), c2 = 1 - Math.pow(b2, t);
      for (let i = 0; i < n; i++) {
        mU[i] = b1 * mU[i] + (1 - b1) * dU[i]; vU[i] = b2 * vU[i] + (1 - b2) * dU[i] * dU[i]; this.U[i] -= lr * (mU[i] / c1) / (Math.sqrt(vU[i] / c2) + 1e-8);
        mV[i] = b1 * mV[i] + (1 - b1) * dV[i]; vV[i] = b2 * vV[i] + (1 - b2) * dV[i] * dV[i]; this.V[i] -= lr * (mV[i] / c1) / (Math.sqrt(vV[i] / c2) + 1e-8);
      }
    }
    return { steps, loss0, loss: lossEnd, groups: G.length };
  }
}
module.exports = { ShapeProjector };
