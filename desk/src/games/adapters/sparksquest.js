'use strict';
// I3 adapter 1: "Sparks quest". T6's real-time Sparks arena (src/games/realtime.js, used as is, not edited) plus a long goal and a
// timing skill, so the two-speed core can be tested on it:
//   goal     touch checkpoints C1..C5 in order, then home H. Which ones are done is NOT shown on screen (memory needed).
//   surprise once per game, the next checkpoint gets LOCKED and a key appears somewhere: the plan must change (fetch the key first).
//   timing   shockwaves: a ring grows from a far point (starting speed and acceleration vary). Jump so you are in the air when the
//            ring front reaches you. A jump leaves the ground 150 ms after the key and you are airborne +-50 ms around that moment.
//            A ring that catches you on the ground costs a life (sparks still cost lives as in T6's game).
// Time: one tick = 50 ms; Sparks moves one frame every 4 ticks (200 ms), the rings move every tick. The lock comes right after
// checkpoint 1, 2 or 3 is touched (seeded), so every game needs a replan.
const RT = require('../realtime');
const { rng } = require('../../tinynet');

const BRACE = 4;   // cells: inside this gap the hand rule stands still (unless a spark threatens) so the last gap readings are clean
const N = 11, TICK = 50, FRAME_TICKS = 4, MAX_TICKS = 1600, LAG = 150, AIR = 50;
const NAMES = ['C1', 'C2', 'C3', 'C4', 'C5', 'H'];
const ACT = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const inside = (r, c) => r >= 0 && c >= 0 && r < N && c < N;
const vocab = {
  GOTO: { args: { to: { enum: [...NAMES, 'KEY'] }, guard: { enum: ['jump', 'none'], default: 'jump' } }, help: 'walk to a checkpoint (or the key), dodging sparks; guard=jump: jump every shockwave at contact' },
  HOLD: { args: { guard: { enum: ['jump', 'none'], default: 'jump' } }, help: 'stay put, dodge, jump shockwaves' }
};

function init(seed, o) {
  o = o || {}; const r = rng(seed * 104729 + 3);
  const sp = RT.sparks.init(seed, { spawn: o.spawn || 0.12, turn: 0.3 });
  const used = new Set(['5,5']), cps = [];
  for (const name of NAMES) {
    if (name === 'H') { cps.push({ name, r: 5, c: 5, locked: false }); continue; }
    let p; do { p = [Math.floor(r() * N), Math.floor(r() * N)]; } while (used.has(p.join()) || cheb(p, [5, 5]) < 2 || (cps.length && cheb(p, [cps[cps.length - 1].r, cps[cps.length - 1].c]) < 4));
    used.add(p.join()); cps.push({ name, r: p[0], c: p[1], locked: false });
  }
  return { sp, cps, next: 0, key: null, keyHeld: false, waves: [], wid: 0, nextWave: 40 + Math.floor(r() * 30), lockWhen: 1 + Math.floor(r() * 3), locked: false, jumps: [], rs: (seed * 31337 + 7) >>> 0, tick: 0, ringHits: 0, ringSaves: 0, spark: 0, noise: o.noise == null ? 0.04 : o.noise };
}
const me = (s) => s.sp.me;
const waveGap = (s, w, t) => { const dt = (t - w.t0) / TICK; return Math.hypot(me(s)[0] - w.er, me(s)[1] - w.ec) - (w.v0 * dt + 0.5 * w.a * dt * dt); };

function observe(s, tMs) {
  const r = rng((s.rs ^ (s.tick * 2654435761)) >>> 0);
  return {
    t: tMs, me: me(s).slice(), lives: s.sp.lives, sparks: s.sp.sparks.map((p) => [p.r, p.c, p.h]),
    cps: s.cps.map((c) => ({ name: c.name, r: c.r, c: c.c, locked: c.locked })), key: s.key && !s.keyHeld ? s.key.slice() : null, keyHeld: s.keyHeld,
    waves: s.waves.map((w) => ({ id: w.id, gap: waveGap(s, w, tMs) + s.noise * gauss(r) }))
  };
}
function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }

// the stand-in slow brain: remaining checkpoints in order; a locked one gets "fetch the key" in front of it
function planner(obs, done) {
  const steps = [];
  for (const name of NAMES) {
    if ((done || []).includes('go:' + name)) continue;
    const cp = obs.cps.find((c) => c.name === name);
    if (cp.locked && !obs.keyHeld && obs.key) steps.push({ id: 'key:' + name, call: { code: 'GOTO', args: { to: 'KEY', guard: 'jump' } }, target: obs.key.slice() });
    steps.push({ id: 'go:' + name, call: { code: 'GOTO', args: { to: name, guard: 'jump' } }, target: [cp.r, cp.c], locked: cp.locked });
  }
  return steps;
}
function judge(step, obs) {
  const tg = step.target;
  if (step.id.startsWith('key:')) { if (obs.keyHeld) return { status: 'done' }; if (!obs.key) return { status: 'blocked', why: 'key gone' }; return { status: 'going', progress: -cheb(obs.me, obs.key) }; }
  const cp = obs.cps.find((c) => 'go:' + c.name === step.id);
  if (cp.locked && !obs.keyHeld) return { status: 'blocked', why: cp.name + ' is locked' };
  if (obs.me[0] === tg[0] && obs.me[1] === tg[1]) return { status: 'done' };
  return { status: 'going', progress: -cheb(obs.me, tg) };
}
function targetOf(obs, call) {
  if (!call) return obs.me;
  if (call.code === 'HOLD') return obs.me;
  if (call.args.to === 'KEY') return obs.key || obs.me;
  const cp = obs.cps.find((c) => c.name === call.args.to); return cp ? [cp.r, cp.c] : obs.me;
}
// sparks next frame, if they keep their heading
const HEAD = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [-1, 1], [1, -1], [1, 1]];
function threat(sparks, from, to) { let k = 0; for (const [r, c, h] of sparks) { const nr = r + HEAD[h][0], nc = c + HEAD[h][1]; if ((nr === to[0] && nc === to[1]) || (r === to[0] && c === to[1]) || (r === to[0] && c === to[1] && nr === from[0] && nc === from[1])) k++; } return k; }
const braceGap = (obs) => Math.min(9, ...obs.waves.map((w) => w.gap));
// the hand rule (on the logged frame, so the night can compare it with the reflex): safe from sparks first, then toward the target;
// inside BRACE cells of a shockwave, stand still unless a spark threatens
function fallbackRaw(raw) {
  const brace = raw.b < BRACE; let best = 0, bv = Infinity;
  for (let a = 0; a < 5; a++) {
    const p = [raw.me[0] + ACT[a][0], raw.me[1] + ACT[a][1]]; if (!inside(p[0], p[1])) continue;
    const v = threat(raw.sp, raw.me, p) * 100 + cheb(p, raw.tg) + 0.01 * (Math.abs(p[0] - raw.tg[0]) + Math.abs(p[1] - raw.tg[1])) + (brace && a ? 3 : 0);
    if (v < bv - 1e-9) { bv = v; best = a; }
  }
  return best;
}
const fallback = (obs, call) => fallbackRaw(rawFrame(obs, call));
function rawFrame(obs, call) { return { me: obs.me, sp: obs.sparks, tg: targetOf(obs, call), b: call && call.args.guard === 'jump' ? Math.round(braceGap(obs) * 100) / 100 : 9 }; }
const NIN = RT.NIN + 3;
function features(raw) {
  const x = new Float64Array(NIN), f = RT.features({ me: raw.me, sparks: raw.sp.map(([r, c, h]) => ({ r, c, h })) });
  x.set(f); x[RT.NIN] = (raw.tg[0] - raw.me[0]) / 10; x[RT.NIN + 1] = (raw.tg[1] - raw.me[1]) / 10; x[RT.NIN + 2] = raw.b < BRACE ? 1 : 0; return x;
}
// the night labeller (offline, its own pace): 2-frame lookahead over 16 imagined spark futures, safety first, then the target
function nightLabel(raw) {
  const r = rng((raw.me[0] * 131 + raw.me[1] * 7 + raw.sp.length * 977 + raw.tg[0] * 13) >>> 0);
  const base = { seed: 1, f: 0, lives: 3, me: raw.me.slice(), sparks: raw.sp.map(([a, b, h]) => ({ r: a, c: b, h, pr: a, pc: b })), turn: 0.3, spawn: 0 };
  let best = 0, bv = -Infinity;
  for (let a = 0; a < 5; a++) {
    const p = [raw.me[0] + ACT[a][0], raw.me[1] + ACT[a][1]]; if (!inside(p[0], p[1])) continue;
    let surv = 0;
    for (let k = 0; k < 16; k++) { let s = { ...base, rs: Math.floor(r() * 4294967296) >>> 0 }; s = RT.sparks.step(s, a); let ok = s.lives === 3; if (ok) { let bestNext = 0; for (let b = 0; b < 5; b++) { const s2 = RT.sparks.step({ ...s, rs: (s.rs + b * 977) >>> 0 }, b); if (s2.lives === 3) { bestNext = 1; break; } } ok = bestNext === 1; } surv += ok ? 1 : 0; }
    const v = surv / 16 * 10 - cheb(p, raw.tg) - 0.01 * (Math.abs(p[0] - raw.tg[0]) + Math.abs(p[1] - raw.tg[1])) - (raw.b < BRACE && a ? 3 : 0);
    if (v > bv + 1e-9) { bv = v; best = a; }
  }
  return best;
}
function timedTargets(obs, call) { if (!call || call.args.guard !== 'jump') return []; return obs.waves.map((w) => ({ id: 'wave' + w.id, action: 'jump', lagMs: LAG, gap: w.gap })); }

function step(s0, move, fired, tMs) {
  const s = { ...s0, cps: s0.cps.map((c) => ({ ...c })), waves: s0.waves.map((w) => ({ ...w })), jumps: s0.jumps.slice(), tick: s0.tick + 1 };
  const contacts = []; const r = rng((s.rs + s.tick * 7477) >>> 0);
  for (const f of fired || []) if (f.action === 'jump') s.jumps.push(f.atMs + LAG);
  if (s0.tick % FRAME_TICKS === 0) {
    const lives0 = s.sp.lives; s.sp = RT.sparks.step(s.sp, move); if (s.sp.lives < lives0) s.spark += lives0 - s.sp.lives;
    const m = me(s);
    if (s.key && !s.keyHeld && m[0] === s.key[0] && m[1] === s.key[1]) s.keyHeld = true;
    const cp = s.cps[s.next];
    if (cp && m[0] === cp.r && m[1] === cp.c) { if (cp.locked && s.keyHeld) { cp.locked = false; s.keyHeld = false; s.key = null; } if (!cp.locked) s.next++; }
  }
  // the surprise: lock the next checkpoint, show a key
  if (!s.locked && s.next >= s.lockWhen && s.next < NAMES.length) {
    s.locked = true; s.cps[s.next].locked = true; let k; do { k = [Math.floor(r() * N), Math.floor(r() * N)]; } while (cheb(k, me(s)) < 3 || s.cps.some((c) => c.r === k[0] && c.c === k[1])); s.key = k;
  }
  // shockwaves: contact = the moment the ring front reaches me (solved inside the tick, continuous time)
  const t1 = tMs + TICK, keep = [];
  for (const w of s.waves) {
    const g1 = waveGap(s, w, t1);
    if (g1 <= 0) {
      let lo = tMs, hi = t1; for (let it = 0; it < 30; it++) { const mid = (lo + hi) / 2; if (waveGap(s, w, mid) > 0) lo = mid; else hi = mid; }
      const at = (lo + hi) / 2; contacts.push({ id: 'wave' + w.id, atMs: at });
      if (s.jumps.some((j) => Math.abs(j - at) <= AIR)) s.ringSaves++; else { s.ringHits++; s.sp = { ...s.sp, lives: s.sp.lives - 1 }; }
    } else if (s.tick - w.t0 / TICK < 300) keep.push(w);
  }
  s.waves = keep; s.jumps = s.jumps.filter((j) => j > tMs - 200);
  if (s.tick >= s.nextWave) {
    const ang = r() * 2 * Math.PI, d = 6 + r() * 4, m = me(s);
    s.waves.push({ id: ++s.wid, er: m[0] + d * Math.cos(ang), ec: m[1] + d * Math.sin(ang), t0: t1, v0: 0.12 + 0.18 * r(), a: 0.008 * r() });
    s.nextWave = s.tick + 60 + Math.floor(r() * 40);
  }
  return { state: s, contacts };
}
const done = (s) => s.sp.lives <= 0 || s.next >= NAMES.length || s.tick >= MAX_TICKS;
const outcome = (s) => ({ goalDone: s.next >= NAMES.length, reached: s.next, lives: s.sp.lives, ticks: s.tick, ringHits: s.ringHits, ringSaves: s.ringSaves, sparkHits: s.spark });
function describe(obs) {
  return 'Arena 11x11, you are at row ' + obs.me[0] + ' col ' + obs.me[1] + ', lives ' + obs.lives + '. Checkpoints: ' + obs.cps.map((c) => c.name + '@' + c.r + ',' + c.c + (c.locked ? '(LOCKED)' : '')).join(' ') +
    '. ' + (obs.key ? 'A key is at ' + obs.key.join(',') + '. ' : '') + (obs.keyHeld ? 'You hold the key. ' : '') + obs.sparks.length + ' sparks; ' + obs.waves.length + ' shockwave(s) coming.';
}

module.exports = { name: 'sparks-quest', tickMs: TICK, actEveryTicks: FRAME_TICKS, maxTicks: MAX_TICKS, vocab, nIn: NIN, nA: 5, goal: 'touch C1..C5 in order, then home H', init, observe, planner, judge, fallback, fallbackRaw, rawFrame, features, nightLabel, timedTargets, step, done, outcome, describe };
