'use strict';
// Tiny dependency-free MLP (1 hidden ReLU layer, Adam) shared by the small fast nets trained in sleep (T6: src/watcher.js,
// src/games/realtime.js). A copy of premonition-sleeplab-t6/lib/nn.js, where the toy tests ran.
function rng(seed) { let a = (seed >>> 0) || 1; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function gauss(r) { let u = 0, v = 0; while (u === 0) u = r(); while (v === 0) v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

class MLP {
  // nIn inputs, nHid hidden units, out = total output width (heads are slices interpreted by the caller)
  constructor(nIn, nHid, nOut, seed) {
    const r = rng(seed || 1);
    this.nIn = nIn; this.nHid = nHid; this.nOut = nOut;
    this.W1 = new Float64Array(nIn * nHid).map(() => gauss(r) * Math.sqrt(2 / nIn));
    this.b1 = new Float64Array(nHid);
    this.W2 = new Float64Array(nHid * nOut).map(() => gauss(r) * Math.sqrt(1 / nHid));
    this.b2 = new Float64Array(nOut);
    this.t = 0;
  }
  params() { return [this.W1, this.b1, this.W2, this.b2]; }
  forward(x) {
    const h = new Float64Array(this.nHid), o = new Float64Array(this.nOut);
    for (let j = 0; j < this.nHid; j++) { let s = this.b1[j]; for (let i = 0; i < this.nIn; i++) s += x[i] * this.W1[i * this.nHid + j]; h[j] = s > 0 ? s : 0; }
    for (let k = 0; k < this.nOut; k++) { let s = this.b2[k]; for (let j = 0; j < this.nHid; j++) s += h[j] * this.W2[j * this.nOut + k]; o[k] = s; }
    return { h, o };
  }
  // one Adam step on a minibatch. lossGrad(o, item) -> dL/do (Float64Array nOut) for that item
  step(batch, lossGrad, lr, wd) {
    const g = this.params().map((p) => new Float64Array(p.length));
    const [gW1, gb1, gW2, gb2] = g;
    for (const item of batch) {
      const x = item.x, { h, o } = this.forward(x), d = lossGrad(o, item);
      const dh = new Float64Array(this.nHid);
      for (let j = 0; j < this.nHid; j++) { if (h[j] <= 0) continue; let s = 0; for (let k = 0; k < this.nOut; k++) { s += d[k] * this.W2[j * this.nOut + k]; gW2[j * this.nOut + k] += d[k] * h[j]; } dh[j] = s; }
      for (let k = 0; k < this.nOut; k++) gb2[k] += d[k];
      for (let j = 0; j < this.nHid; j++) { if (!dh[j]) continue; gb1[j] += dh[j]; for (let i = 0; i < this.nIn; i++) if (x[i]) gW1[i * this.nHid + j] += dh[j] * x[i]; }
    }
    const n = batch.length; this.t++;
    if (!this.m) { this.m = this.params().map((p) => new Float64Array(p.length)); this.v = this.params().map((p) => new Float64Array(p.length)); }
    const b1 = 0.9, b2 = 0.999, c1 = 1 - Math.pow(b1, this.t), c2 = 1 - Math.pow(b2, this.t);
    this.params().forEach((p, pi) => {
      const m = this.m[pi], v = this.v[pi], gg = g[pi];
      for (let i = 0; i < p.length; i++) {
        const gi = gg[i] / n + (wd || 0) * p[i];
        m[i] = b1 * m[i] + (1 - b1) * gi; v[i] = b2 * v[i] + (1 - b2) * gi * gi;
        p[i] -= lr * (m[i] / c1) / (Math.sqrt(v[i] / c2) + 1e-8);
      }
    });
  }
  clone() { const c = Object.create(MLP.prototype); Object.assign(c, { nIn: this.nIn, nHid: this.nHid, nOut: this.nOut, t: 0 }); c.W1 = Float64Array.from(this.W1); c.b1 = Float64Array.from(this.b1); c.W2 = Float64Array.from(this.W2); c.b2 = Float64Array.from(this.b2); return c; }
  toJSON() { return { nIn: this.nIn, nHid: this.nHid, nOut: this.nOut, W1: Array.from(this.W1), b1: Array.from(this.b1), W2: Array.from(this.W2), b2: Array.from(this.b2) }; }
  static fromJSON(j) { const c = Object.create(MLP.prototype); Object.assign(c, { nIn: j.nIn, nHid: j.nHid, nOut: j.nOut, t: 0 }); c.W1 = Float64Array.from(j.W1); c.b1 = Float64Array.from(j.b1); c.W2 = Float64Array.from(j.W2); c.b2 = Float64Array.from(j.b2); return c; }
}
const sigmoid = (z) => 1 / (1 + Math.exp(-z));
function softmax(o, a, b) { let m = -Infinity; for (let i = a; i < b; i++) m = Math.max(m, o[i]); let s = 0; const p = []; for (let i = a; i < b; i++) { p.push(Math.exp(o[i] - m)); s += p[p.length - 1]; } return p.map((v) => v / s); }
function shuffle(r, xs) { for (let i = xs.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [xs[i], xs[j]] = [xs[j], xs[i]]; } return xs; }

// average precision of scores vs 0/1 labels (ties broken by order)
function averagePrecision(scores, labels) {
  const idx = scores.map((s, i) => i).sort((a, b) => scores[b] - scores[a]);
  let tp = 0, ap = 0; const P = labels.reduce((a, b) => a + b, 0); if (!P) return 0;
  idx.forEach((i, rank) => { if (labels[i]) { tp++; ap += tp / (rank + 1); } });
  return ap / P;
}

module.exports = { MLP, rng, gauss, sigmoid, softmax, shuffle, averagePrecision };
