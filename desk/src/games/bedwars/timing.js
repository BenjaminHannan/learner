'use strict';
// Glim team, Bedwars side (plan v4.1 §1, "catching a baseball"): the Bedwars hooks for the core's timed-action schedule.
//   - time-to-go estimators per skill from observation features (Lee's tau = distance / closing speed), re-run every 50 ms tick
//   - the fire rule: fire on the tick closest to the ideal moment (time-to-go <= half a tick); move earlier / later; cancel
//   - the timing-error metric in ms against the ideal moment reconstructed from the server truth log (hindsight)
// Observation features are what the eyes estimate from the screen (no reach / distance display: these are Glim's own estimates).
// Pure; no I/O.

const TICK_MS = 50;
const REACH = 3.0;          // 1.8 melee reach, blocks
const BLOCK_DELAY_MS = 50;  // block-hit: right-click one tick after the landed hit (PVP-HABITS: 1-2 ticks)
const MAX_LATE_MS = 100;    // ours: a timed action more than 2 ticks past its moment is cancelled, not fired

// 1.8 jump: vy = 0.42 on the jump tick; each tick y += vy, then vy = (vy - 0.08) * 0.98. A crit needs the hit while falling
// (moving down, not on the ground). Simulated once: which ticks after the jump are "falling".
function jumpArc() {
  let y = 0, vy = 0.42; const ticks = [];
  for (let k = 1; k <= 40; k++) { const y0 = y; y += vy; vy = (vy - 0.08) * 0.98; if (y <= 0) break; ticks.push({ k, y, falling: y < y0 }); }
  return ticks;
}
const ARC = jumpArc();
const FALL = ARC.filter((x) => x.falling).map((x) => x.k);
const CRIT_WINDOW_MS = { from: FALL[0] * TICK_MS, to: FALL[FALL.length - 1] * TICK_MS };
const CRIT_MID_MS = Math.round((CRIT_WINDOW_MS.from + CRIT_WINDOW_MS.to) / 2 / TICK_MS) * TICK_MS;

// tau: time to contact in ms; Infinity when not closing
function tau(dist, closing) { if (!(closing > 1e-6) || !Number.isFinite(dist)) return Infinity; return 1000 * Math.max(0, dist) / closing; }

// estimators: obs -> time-to-go in ms, or null = cancel (the moment is not coming)
const SKILLS = {
  // jump the gap: jump as the feet reach the edge. obs: {edgeDist (blocks), speed (blocks/s toward the edge)}
  jump_at_edge(obs) { const t = tau(obs.edgeDist, obs.speed); return Number.isFinite(t) ? t : null; },
  // block-hit: one tick after my hit lands. obs: {hitAgoMs (my last landed hit, if any)} or {dist, closing} before it lands
  block_at_hit(obs) {
    if (Number.isFinite(obs.hitAgoMs) && obs.hitAgoMs <= BLOCK_DELAY_MS + MAX_LATE_MS) return BLOCK_DELAY_MS - obs.hitAgoMs;
    const t = tau(obs.dist - REACH, obs.closing); return Number.isFinite(t) ? t + BLOCK_DELAY_MS : null;
  },
  // jump-crit: jump so the hit (when he enters reach) lands mid-fall. obs: {dist, closing}
  crit_on_fall(obs) { const t = tau(obs.dist - REACH, obs.closing); return Number.isFinite(t) ? t - CRIT_MID_MS : null; }
};

// the fire rule: the tick nearest to the moment (k = 0 -> fire now); late by more than MAX_LATE_MS -> cancel
function bestTick(ttgMs, tickMs) { return Math.round(ttgMs / (tickMs || TICK_MS)); }
function decide(ttgMs, tickMs) {
  if (ttgMs == null || Number.isNaN(ttgMs)) return 'cancel';
  if (ttgMs < -MAX_LATE_MS) return 'cancel';
  return ttgMs <= (tickMs || TICK_MS) / 2 ? 'fire' : 'wait';
}
// the estimate hook in the shape core-iface ActionSchedule.tick wants: (item, t) -> ttg | null; obsAt(t) gives the features
function estimateHook(obsAt) {
  return (item, t) => { const f = SKILLS[item.skill]; if (!f) return null; const e = f(obsAt(t) || {}); return e == null || decide(e) === 'cancel' ? null : e; };
}

// the same three skills as gap targets in the I3 core's schedule shape (src/games/core/schedule.js tick(nowMs, [{id, action, lagMs,
// gap}]): the core fits tau to the gap itself; lagMs = how long after the key the effect lands (fire + lag = contact).
//   jump_at_edge  gap = edge distance, lag 0;  block_at_hit  gap = distance - reach, lag -1 tick (block one tick AFTER contact);
//   crit_on_fall  gap = distance - reach, lag = CRIT_MID_MS (the jump pays off mid-fall)
function timedTargets(est, skills) {
  const e = est || {}, out = [];
  for (const k of skills || []) {
    if (k === 'jump_at_edge' && Number.isFinite(e.edgeDist)) out.push({ id: k, action: k, lagMs: 0, gap: e.edgeDist });
    if (k === 'block_at_hit' && Number.isFinite(e.dist)) out.push({ id: k, action: k, lagMs: -BLOCK_DELAY_MS, gap: Math.max(0, e.dist - REACH) });
    if (k === 'crit_on_fall' && Number.isFinite(e.dist)) out.push({ id: k, action: k, lagMs: CRIT_MID_MS, gap: Math.max(0, e.dist - REACH) });
  }
  return out;
}

// ---- hindsight: ideal moments from the truth log, and the timing error ----------------------------------------------------
function toMs(t) { if (typeof t === 'number') return t; const n = Date.parse(t); return Number.isFinite(n) ? n : NaN; }
const actorOf = (e) => e.attacker || e.by || e.player || null;
// events: truth-log events; me: my player name -> {skill: [ideal ms]}
//   block_at_hit  my landed hit + 1 tick
//   crit_on_fall  my landed hit - CRIT_MID_MS (the jump that would put that hit mid-fall)
//   jump_at_edge  `edge` events for me (the plugin's moment the feet leave the last block); see README: not in TOOLS.md v1 yet
function idealMoments(events, me) {
  const out = { block_at_hit: [], crit_on_fall: [], jump_at_edge: [] };
  for (const e of events || []) {
    const t = toMs(e.t); if (!Number.isFinite(t)) continue;
    if (e.type === 'hit' && actorOf(e) === me) { out.block_at_hit.push(t + BLOCK_DELAY_MS); out.crit_on_fall.push(t - CRIT_MID_MS); }
    if (e.type === 'edge' && (e.player === me)) out.jump_at_edge.push(t);
  }
  for (const k of Object.keys(out)) out[k].sort((a, b) => a - b);
  return out;
}
// pair fired actions with ideal moments one-to-one (closest pairs first, within maxPairMs); error = fired - ideal (+ = late)
function pairErrors(fired, ideals, maxPairMs) {
  const max = maxPairMs == null ? 300 : maxPairMs, cand = [];
  fired.forEach((a, i) => ideals.forEach((b, j) => { const d = a - b; if (Math.abs(d) <= max) cand.push({ i, j, d }); }));
  cand.sort((x, y) => Math.abs(x.d) - Math.abs(y.d) || x.i - y.i || x.j - y.j);
  const ui = new Set(), uj = new Set(), errs = [];
  for (const c of cand) { if (ui.has(c.i) || uj.has(c.j)) continue; ui.add(c.i); uj.add(c.j); errs.push({ fired: fired[c.i], ideal: ideals[c.j], errMs: c.d }); }
  errs.sort((a, b) => a.fired - b.fired);
  return { errs, extra: fired.length - ui.size, missed: ideals.length - uj.size };
}
const quant = (xs, q) => { if (!xs.length) return null; const s = xs.slice().sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.max(0, Math.ceil(q * s.length) - 1))]; };
const median = (xs) => { if (!xs.length) return null; const s = xs.slice().sort((a, b) => a - b), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
// actions: [{skill, t}] (what the schedule fired; t = key time); events: truth log -> per skill timing report in ms
function timingReport(actions, events, me, o) {
  const ideal = idealMoments(events, me), rep = {};
  for (const skill of Object.keys(SKILLS)) {
    const fired = (actions || []).filter((a) => a.skill === skill).map((a) => toMs(a.t)).filter(Number.isFinite).sort((a, b) => a - b);
    const p = pairErrors(fired, ideal[skill], o && o.maxPairMs), e = p.errs.map((x) => x.errMs), abs = e.map(Math.abs);
    rep[skill] = { fired: fired.length, ideal: ideal[skill].length, matched: e.length, extra: p.extra, missed: p.missed,
      medianAbsMs: median(abs), p90AbsMs: quant(abs, 0.9), meanSignedMs: e.length ? e.reduce((a, b) => a + b, 0) / e.length : null,
      withinTick: e.length ? abs.filter((x) => x <= TICK_MS).length / e.length : null, errs: p.errs };
  }
  return rep;
}

module.exports = { timedTargets, TICK_MS, REACH, BLOCK_DELAY_MS, MAX_LATE_MS, ARC, CRIT_WINDOW_MS, CRIT_MID_MS, tau, SKILLS, bestTick, decide, estimateHook,
  toMs, idealMoments, pairErrors, timingReport, median, quant };
