'use strict';
// I3 adapter 2: "Orchard", a small catch game written to test TRANSFER of the two-speed core (core/ is not changed for it).
// A basket slides along the ground (x 0..30). Six trees, two of each kind (apple, pear, plum), drop fruit now and then; fruit falls
// with gravity (each tree's fruit is heavier or lighter) and drifts a little sideways.
//   goal     deliver three fruits to the barrel in a given order (e.g. plum, apple, pear). The tally is NOT shown (memory needed).
//   surprise right after delivery 1 or 2 (seeded), the tree the plan is heading to next withers: the plan must change trees.
//   timing   the net snaps shut 100 ms after the key and catches only within +-50 ms of the fruit reaching the basket rim.
// One tick = 50 ms.
const { rng } = require('../../tinynet');

const TICK = 50, MAX_TICKS = 1600, LAG = 100, WIN = 50, SPEED = 0.25, REACH = 0.8;
const KINDS = ['apple', 'pear', 'plum'], TREES = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6'];
const vocab = {
  CATCH: { args: { tree: { enum: TREES } }, help: 'go under that tree and catch the next fruit it drops' },
  DEPOSIT: { args: {}, help: 'carry the fruit to the barrel' },
  HOLD: { args: {}, help: 'stay put' }
};
function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }

function init(seed, o) {
  o = o || {}; const r = rng(seed * 6007 + 11);
  const kinds = [...KINDS, ...KINDS]; for (let i = kinds.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [kinds[i], kinds[j]] = [kinds[j], kinds[i]]; }
  const trees = TREES.map((name, i) => ({ name, x: 2.5 + 5 * i, kind: kinds[i], g: 0.004 + 0.006 * r(), withered: false, nextDrop: 10 + Math.floor(r() * 40) }));
  const order = [0, 1, 2].map(() => KINDS[Math.floor(r() * 3)]);
  return { x: 15, carry: null, trees, barrel: 12 + 6 * r(), order, delivered: 0, fruits: [], fid: 0, tick: 0, witherAfter: 1 + Math.floor(r() * 2), withered: false, events: [], net: [], rs: (seed * 7333 + 5) >>> 0, caught: 0, missed: 0, noise: o.noise == null ? 0.04 : o.noise };
}
const fruitH = (f, t) => { const dt = (t - f.t0) / TICK; return f.h0 - 0.5 * f.g * dt * dt; };
const fruitX = (f, t) => f.x0 + f.vx * (t - f.t0) / TICK;
function observe(s, tMs) {
  const r = rng((s.rs ^ (s.tick * 2246822519)) >>> 0);
  return {
    t: tMs, x: s.x, carry: s.carry, barrel: s.barrel, events: s.events.slice(), order: s.order.slice(),
    trees: s.trees.map((t) => ({ name: t.name, x: t.x, kind: t.kind, withered: t.withered })),
    fruits: s.fruits.map((f) => ({ id: f.id, tree: f.tree, x: fruitX(f, tMs) + 0.02 * gauss(r), h: fruitH(f, tMs) + s.noise * gauss(r), vx: f.vx + 0.01 * gauss(r) }))
  };
}
// the stand-in slow brain: for each fruit still to deliver, the living tree of that kind nearest the barrel, then the barrel
function planner(obs, done) {
  const steps = [];
  obs.order.forEach((kind, i) => {
    const haveIt = obs.carry === kind && !(done || []).includes('catch:' + i) && !steps.length;
    if (!(done || []).includes('catch:' + i) && !haveIt) {
      const ts = obs.trees.filter((t) => t.kind === kind && !t.withered).sort((a, b) => Math.abs(a.x - obs.barrel) - Math.abs(b.x - obs.barrel));
      if (ts.length) steps.push({ id: 'catch:' + i, call: { code: 'CATCH', args: { tree: ts[0].name } }, kind, tree: ts[0].name });
    }
    if (!(done || []).includes('dep:' + i)) steps.push({ id: 'dep:' + i, call: { code: 'DEPOSIT', args: {} } });
  });
  return steps;
}
function judge(step, obs) {
  if (step.id.startsWith('catch:')) {
    if (obs.carry === step.kind) return { status: 'done' };
    const t = obs.trees.find((x) => x.name === step.tree); if (t.withered) return { status: 'blocked', why: t.name + ' withered' };
    return { status: 'going', progress: -Math.round(Math.abs(obs.x - t.x)) };
  }
  if (step.id.startsWith('dep:')) { if (obs.events.includes('deposit')) return { status: 'done' }; return { status: 'going', progress: -Math.round(Math.abs(obs.x - obs.barrel)) }; }
  return { status: 'going' };
}
function aim(obs, call) {
  if (!call || call.code === 'HOLD') return { tg: obs.x, f: null };
  if (call.code === 'DEPOSIT') return { tg: obs.barrel, f: null };
  const t = obs.trees.find((x) => x.name === call.args.tree);
  const f = obs.fruits.filter((q) => q.tree === call.args.tree).sort((a, b) => a.h - b.h)[0] || null;
  return { tg: f ? f.x : t.x, f };
}
const toward = (x, tg) => (Math.abs(tg - x) <= 0.15 ? 0 : tg < x ? 1 : 2);
function fallback(obs, call) { return toward(obs.x, aim(obs, call).tg); }
const fallbackRaw = (raw) => toward(raw.x, raw.tg);
// state (the truth log) is passed only when frames are LOGGED for the night; the reflex's features never read raw.truth
function rawFrame(obs, call, state) {
  const { tg, f } = aim(obs, call), raw = { x: obs.x, tg, code: call ? call.code : 'HOLD', carry: obs.carry ? 1 : 0, f: f ? [f.x, f.h, f.vx] : null };
  if (state && f) { const tf = state.fruits.find((q) => q.id === f.id); if (tf) { const T = Math.sqrt(2 * tf.h0 / tf.g); raw.truth = { land: tf.x0 + tf.vx * T }; } }
  return raw;
}
const NIN = 9;
function features(raw) {
  const x = new Float64Array(NIN); x[0] = (raw.tg - raw.x) / 30; x[1] = raw.f ? 1 : 0;
  if (raw.f) { x[2] = (raw.f[0] - raw.x) / 3; x[3] = raw.f[1] / 9; x[4] = raw.f[2] * 25; }
  x[5] = raw.carry; x[6] = raw.code === 'CATCH' ? 1 : 0; x[7] = raw.code === 'DEPOSIT' ? 1 : 0; x[8] = raw.x / 30; return x;
}
// night labeller: hindsight from the truth log: go where the fruit really landed
function nightLabel(raw) { return toward(raw.x, raw.truth ? raw.truth.land : raw.tg); }
function timedTargets(obs, call) {
  if (!call || call.code !== 'CATCH' || obs.carry) return [];
  return obs.fruits.filter((f) => f.tree === call.args.tree && Math.abs(f.x - obs.x) <= 2).map((f) => ({ id: 'fruit' + f.id, action: 'catch', lagMs: LAG, gap: f.h }));
}
function step(s0, move, fired, tMs) {
  const s = { ...s0, trees: s0.trees.map((t) => ({ ...t })), fruits: s0.fruits.slice(), net: s0.net.slice(), events: [], tick: s0.tick + 1 };
  const r = rng((s.rs + s.tick * 9241) >>> 0), contacts = [], t1 = tMs + TICK;
  for (const f of fired || []) if (f.action === 'catch') s.net.push(f.atMs + LAG);
  s.x = Math.max(0, Math.min(30, s.x + (move === 1 ? -SPEED : move === 2 ? SPEED : 0)));
  if (s.carry && Math.abs(s.x - s.barrel) <= 0.5) { if (s.carry === s.order[s.delivered]) s.delivered++; s.carry = null; s.events.push('deposit'); }
  if (!s.withered && s.delivered >= s.witherAfter && s.delivered < s.order.length) {
    const kind = s.order[s.delivered], ts = s.trees.filter((t) => t.kind === kind && !t.withered).sort((a, b) => Math.abs(a.x - s.barrel) - Math.abs(b.x - s.barrel));
    if (ts.length > 1) { ts[0].withered = true; s.withered = true; s.events.push('wither'); s.fruits = s.fruits.filter((f) => f.tree !== ts[0].name); }   // its fruit in the air spoils
  }
  const keep = [];
  for (const f of s.fruits) {
    if (fruitH(f, t1) > 0) { keep.push(f); continue; }
    let lo = tMs, hi = t1; for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (fruitH(f, mid) > 0) lo = mid; else hi = mid; }
    const at = (lo + hi) / 2, fx = fruitX(f, at); contacts.push({ id: 'fruit' + f.id, atMs: at });
    if (!s.carry && Math.abs(fx - s.x) <= REACH && s.net.some((n) => Math.abs(n - at) <= WIN)) { s.carry = s.trees.find((t) => t.name === f.tree).kind; s.caught++; s.events.push('caught'); } else s.missed++;
  }
  s.fruits = keep; s.net = s.net.filter((n) => n > tMs - 200);
  for (const t of s.trees) if (!t.withered && s.tick >= t.nextDrop) { s.fruits.push({ id: ++s.fid, tree: t.name, x0: t.x + (r() - 0.5), h0: 6 + 3 * r(), vx: 0.04 * (2 * r() - 1), g: t.g, t0: t1 }); t.nextDrop = s.tick + 30 + Math.floor(r() * 30); }
  return { state: s, contacts };
}
const done = (s) => s.delivered >= s.order.length || s.tick >= MAX_TICKS;
const outcome = (s) => ({ goalDone: s.delivered >= s.order.length, delivered: s.delivered, ticks: s.tick, caught: s.caught, withered: s.withered });
function describe(obs) {
  return 'Basket at x=' + obs.x.toFixed(1) + (obs.carry ? ', carrying a ' + obs.carry : ', empty') + '. Barrel at x=' + obs.barrel.toFixed(1) + '. Trees: ' + obs.trees.map((t) => t.name + ' ' + t.kind + '@' + t.x + (t.withered ? '(WITHERED)' : '')).join(', ') + '. Deliver in order: ' + obs.order.join(', ') + '.';
}

module.exports = { name: 'orchard', tickMs: TICK, maxTicks: MAX_TICKS, vocab, nIn: NIN, nA: 3, goal: 'deliver the three fruits in order', init, observe, planner, judge, fallback, fallbackRaw, rawFrame, features, nightLabel, timedTargets, step, done, outcome, describe };
