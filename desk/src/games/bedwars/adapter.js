'use strict';
// Glim team, Bedwars side (plan v4.1 §1, §2, P3): the Bedwars game adapter for Glim's two-speed core. Game-agnostic logic stays in
// the core (reached only through ./core-iface.js); this file only says what Bedwars looks like to Glim and how a tactical call turns
// into reflex conditioning and timed actions.
//   observations  the screen frame (a reference; frames stay on BensPC), the allowed HUD, sound events. No minimap, no reach or
//                 distance display, no freelook, no coordinates; FOV <= 110; one F5 view at a time. The truth log is NEVER an input.
//   actions       keys + mouse every 50 ms tick, plus timed actions (skill, time-to-go) on the core's action schedule
//   realtime      true; budget <= 30 ms frame->key (p95), 50 ms tick; the last call is kept when none arrives for > 2 s
//   sleep         data hooks only (that day's real games: replay, hindsight labels, cards, mechanics). NO games at night.
const core = require('./core-iface');
const Tactics = require('./tactics');
const Timing = require('./timing');
const Truth = require('./truthlog');

const TICK_MS = 50, FRAME_TO_KEY_MS = 30, STALE_MS = 2000, FOV_MAX = 110;

// ---- observation spec (a whitelist: anything else is refused) ------------------------------------------------------------------
const OBS_SPEC = {
  frame: { ref: 'id of the frame on BensPC (frames never leave it)', w: 'px', h: 'px', t: 'capture time, ms', fov: '<= ' + FOV_MAX, view: 'first | f5 (one at a time)' },
  hud: {   // what a human sees on the Hypixel-allowed HUD
    hp: 'health 0..20', hunger: '0..20', armor: '0..20', hotbar: '9 slots [{item, count}]', held: 'hotbar slot 0..8',
    inventory: 'resource counts the player sees {iron, gold, diamond, emerald, blocks}', xp: 'level',
    scoreboard: 'team beds alive / players left', chat: 'game messages only (bed destroyed, kills); never Ben\'s chat',
    tnt_timer: 'TNT fuse timer', title: 'big screen text (respawning, victory)', zoom: 'on | off', bossbar: 'text'
  },
  sound: 'events [{name, t, volume, pan}] from the game audio (hurt, bow, bed break, footsteps)'
};
const HUD_FIELDS = Object.keys(OBS_SPEC.hud);
const FORBIDDEN = ['minimap', 'reach', 'distance', 'reach_display', 'freelook', 'coords', 'xyz', 'f3', 'truth', 'server_log', 'entities', 'opp_pos', 'radar'];
function validateObs(obs) {
  if (!obs || typeof obs !== 'object') return { ok: false, error: 'no observation' };
  for (const k of Object.keys(obs)) if (!['frame', 'hud', 'sound', 't', 'est'].includes(k)) return { ok: false, error: 'not an allowed input: ' + k };
  const hud = obs.hud || {};
  for (const k of Object.keys(hud)) { if (FORBIDDEN.includes(k.toLowerCase())) return { ok: false, error: 'forbidden HUD field: ' + k }; if (!HUD_FIELDS.includes(k)) return { ok: false, error: 'HUD field not allowed: ' + k }; }
  if (obs.frame && obs.frame.fov != null && obs.frame.fov > FOV_MAX) return { ok: false, error: 'FOV above ' + FOV_MAX };
  if (obs.frame && obs.frame.view && !['first', 'f5'].includes(obs.frame.view)) return { ok: false, error: 'one view at a time: first or f5' };
  return { ok: true };
}
// obs.est = Glim's OWN estimates from the screen (eyes), used by the timing estimators: {dist, closing, edgeDist, speed, hitAgoMs}

// ---- action spec ------------------------------------------------------------------------------------------------------------
const ACTION_SPEC = {
  keys: ['w', 'a', 's', 'd', 'space', 'shift', 'ctrl', 'q', 'e', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'f5'],
  mouse: { dx: 'yaw delta, degrees', dy: 'pitch delta, degrees', lmb: 'down|up', rmb: 'down|up', wheel: 'int' },
  timed: { skill: Object.keys(Timing.SKILLS), ttgMs: 'time-to-go, re-estimated every tick' },
  tickMs: TICK_MS
};
const TIMED_BY_CODE = {}; for (const c of Tactics.CODES) if (Tactics.VOCAB[c].timed) TIMED_BY_CODE[c] = Tactics.VOCAB[c].timed;

// ---- reflex conditioning: a call line -> a fixed-width vector (one-hot per slot + normalised params) --------------------------
const SLOT = Tactics.CODES.length + 4;   // code one-hot + up to 4 numbers (dir, flag, numeric, enum index)
const COND_WIDTH = SLOT * Tactics.MAX_CALLS + 1;   // + 1 = "stale" (no fresh call for > 2 s)
function conditioning(calls, stale) {
  const x = new Float64Array(COND_WIDTH);
  (calls || []).slice(0, Tactics.MAX_CALLS).forEach((c, i) => {
    const o = i * SLOT, ci = Tactics.CODES.indexOf(c.code); if (ci < 0) return; x[o + ci] = 1;
    let j = Tactics.CODES.length;
    for (const p of Tactics.VOCAB[c.code].p) {
      const v = c.params[p.name];
      if (p.type === 'flag') x[o + j + 1] = v ? 1 : 0;
      else if (p.name === 'dir') x[o + j] = v === 'l' ? -1 : 1;
      else if (p.type === 'enum') x[o + j + 3] = (p.values.indexOf(v) + 1) / p.values.length;
      else x[o + j + 2] = v / p.max;
    }
  });
  x[COND_WIDTH - 1] = stale ? 1 : 0;
  return x;
}

class BedwarsAdapter {
  // o: {me, intent, plan, schedule} (core pieces; default = the core-iface ones)
  constructor(o) {
    o = o || {}; this.me = o.me || 'GlimBot';
    this.intent = o.intent || new core.IntentChannel({ staleMs: STALE_MS });
    this.plan = o.plan || new core.PlanMemory(); this.schedule = o.schedule || new core.ActionSchedule({ tickMs: TICK_MS });
    this.callLog = []; this.planLog = []; this.lastObs = null; this.stepStartedAt = null;
  }
  get name() { return 'bedwars'; }
  get realtime() { return true; }
  get budget() { return { frameToKeyMs: FRAME_TO_KEY_MS, tickMs: TICK_MS, staleMs: STALE_MS }; }
  // the slow brain's line -> intent (+ timed actions for timed codes). A bad line keeps the last good call.
  onCall(text, t) {
    const p = Tactics.parse(text); this.callLog.push({ t, text: String(text).slice(0, 80), ok: p.ok, error: p.ok ? null : p.error });
    if (!p.ok) return p;
    this.intent.send(p.calls, t);
    for (const c of p.calls) {
      const skill = TIMED_BY_CODE[c.code]; if (!skill) continue;
      for (const it of this.schedule.list()) if (it.skill === skill) this.schedule.cancel(it.id, t, 'replaced by a new call');
      const ttg = Timing.SKILLS[skill]((this.lastObs && this.lastObs.est) || {});
      if (ttg != null) this.schedule.add({ skill, ttgMs: ttg, t });
    }
    return p;
  }
  // every 50 ms tick: the current call (kept when stale), its conditioning vector, and the timed actions that fire now
  tick(t, obs) {
    if (obs) { const v = validateObs(obs); if (!v.ok) throw new Error(v.error); this.lastObs = obs; }
    const cur = this.intent.current(t);
    const fired = this.schedule.tick(t, Timing.estimateHook(() => (this.lastObs && this.lastObs.est) || {}));
    return { calls: cur.call, stale: cur.stale, cond: conditioning(cur.call, cur.stale), fired };
  }
  // long horizon: start a plan; check triggers each observation; replan when disrupted
  startPlan(steps, t, goal) { this.plan.set(goal || 'break the enemy bed', steps || Tactics.RUSH_PLAN, t); this.stepStartedAt = t; this.planLog.push({ t, type: 'plan', steps: (steps || Tactics.RUSH_PLAN).slice() }); }
  stepDone(t) { this.plan.advance(t); this.stepStartedAt = t; }
  checkPlan(t, o) {
    const step = this.plan.step(); if (!step) return null;
    const hud = (this.lastObs && this.lastObs.hud) || {};
    const why = Tactics.replanTriggers({ ...(o || {}), hp: hud.hp, step, stepStartedAt: this.stepStartedAt, now: t });
    if (!why.length) return null;
    const steps = Tactics.replan(why, step); this.plan.replan(why.join('+'), steps, t); this.stepStartedAt = t;
    this.planLog.push({ t, type: 'replan', reason: why.join('+'), steps });
    return { reasons: why, steps };
  }
  stepCall(step) { const s = Tactics.PLAN_STEPS[step]; return s ? Tactics.toText(s.call()) : null; }
}

// ---- sleep: day data only (plan §2). The core owns training and the seatbelt; these just turn a day's logs into data. -----------
const sleepHooks = {
  game: 'bedwars',
  nightPlay: false,   // Ben: no self-play, no practice games at night
  // day: {events (truth log), calls [{t, text}], frames [{t, ref}], keys [{t, ...}], planLog, me}
  replayDay(day) { return { frames: (day.frames || []).length, keys: (day.keys || []).length, calls: (day.calls || []).length, events: (day.events || []).length }; },
  labels(day) { return Truth.hindsight((day.frames || []).map((f) => f.t), day.events, day.me || 'GlimBot'); },
  rewards(day) { return Truth.rewards(day.events, day.me || 'GlimBot'); },
  cards(day) { return Truth.cards(day.calls, day.events, day.me || 'GlimBot'); },
  goal(day) { return Truth.goalScore(day.events, day.me || 'GlimBot', day.plan || Tactics.RUSH_PLAN, day.planLog); },
  // mechanics data for the world model: what an action did (crit or not, price paid, generator timing, blocks placed)
  mechanics(day) {
    const me = day.me || 'GlimBot', ev = Truth.normalize(day.events), out = []; let lastPick = {};
    for (const e of ev) {
      if (e.type === 'hit') out.push({ t: e.t, kind: 'hit', crit: e.crit === true, damage: e.damage != null ? Number(e.damage) : null, mine: (e.attacker || e.by) === me });
      else if (e.type === 'purchase') out.push({ t: e.t, kind: 'price', item: e.item, cost: e.cost != null ? e.cost : null, currency: e.currency || null });
      else if (e.type === 'pickup') { const k = String(e.item); out.push({ t: e.t, kind: 'generator', item: k, count: Number(e.count || 1), sinceLastMs: lastPick[k] != null ? e.t - lastPick[k] : null }); lastPick[k] = e.t; }
      else if (e.type === 'block_place' || e.type === 'void_death' || e.type === 'bed_broken') out.push({ t: e.t, kind: e.type });
    }
    return out;
  }
};
core.registerSleepHook(sleepHooks);

module.exports = { BedwarsAdapter, OBS_SPEC, ACTION_SPEC, HUD_FIELDS, FORBIDDEN, validateObs, conditioning, COND_WIDTH, TIMED_BY_CODE, sleepHooks,
  realtime: true, TICK_MS, FRAME_TO_KEY_MS, STALE_MS, FOV_MAX };
