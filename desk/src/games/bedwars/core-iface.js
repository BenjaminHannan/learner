'use strict';
// Glim team, Bedwars side (plan v4.1 §1): the ONE place the Bedwars adapter touches Glim's game-agnostic two-speed core.
// I3 builds that core in src/games/core/. It did not exist when this was written, so this shim holds small stand-ins that follow the
// shape in /tmp/aon/task-I3.md and plan §1. Wiring the adapter to the real core = edit THIS file only (map the four pieces below).
//
// What the adapter needs from the core:
//   1. IntentChannel   the slow brain (Nanbeige) sends tactical calls; the reflex reads the current one every tick.
//                      send(call, t)  -> stores {call, t}
//                      current(t)     -> {call, t, ageMs, stale}; with no call for > staleMs (2 s) it KEEPS the last call (stale: true)
//   2. PlanMemory      a goal -> steps plan that lasts minutes; progress checked against what is observed; replans on surprise.
//                      set(goal, steps, t), step() -> the current step or null, advance(t), replan(reason, steps, t), view()
//   3. ActionSchedule  timed actions ("baseball"): each action has a time-to-go re-estimated every tick; it fires at the tick
//                      nearest to 0 and can move earlier / later or be cancelled.
//                      add({skill, ttgMs, t}) -> id, tick(t, estimate) -> fired [{id, skill, t, ttgAtFire}], cancel(id), list()
//                      estimate(item, t) -> a new ttgMs, or null to cancel (the Bedwars estimators live in ./timing.js)
//   4. registerSleepHook({game, ...}) the night pulls DAY data only through these hooks (no games at night). The core owns training.
//
// The stand-ins are deliberately tiny; they are only here so the adapter is testable before I3 lands.
//
// I3's core appeared while this was built (src/games/core/, untracked, still in progress at 13:53). Its API as seen then, and the
// one-file wiring once I3 is done (all Bedwars pieces it needs already exist):
//   IntentChannel  core/intent.js  new IntentChannel(vocab, {holdMs: 2000}); send(call|text, nowMs, source); current(nowMs) -> {call, ageMs, stale}
//                  vocab = tactics.coreVocab(); a parsed call -> tactics.toCoreCall(call) before send (our short text "st l w" is
//                  parsed by tactics.parse, not by intent.parse, which wants "st dir=l wtap=1")
//   PlanMemory     core/plan.js    setPlan(goal, steps, nowMs) / current() / tick(obs, judge, nowMs) / interrupt(reason) / replan(steps)
//                  steps = [{id, call}] from tactics.PLAN_STEPS; judge(step, obs) -> {status, progress} from the truth-log STEP_CHECKs
//   ActionSchedule core/schedule.js tick(nowMs, targets) with targets = timing.timedTargets(obs.est, skills) ({id, action, lagMs, gap});
//                  the core fits tau itself; contact(id, atMs) from the truth log's ideal moments (timing.idealMoments)
//   sleep hook     core/reflex.js  ReflexSleep: give it the day's acts/times from adapter.sleepHooks (labels / hindsight)
// Not done here on purpose: I3 is still changing those files, and its loop.js adapter interface (init/step/done) is for games that
// run inside the process; Bedwars runs on BensPC, so the wiring will be a live-loop variant, not runEpisode().

const STALE_MS = 2000, TICK_MS = 50;

class IntentChannel {
  constructor(o) { this.staleMs = (o && o.staleMs) || STALE_MS; this.last = null; }
  send(call, t) { this.last = { call, t }; return this.last; }
  current(t) {
    if (!this.last) return { call: null, t: null, ageMs: Infinity, stale: true };
    const ageMs = t - this.last.t;
    return { call: this.last.call, t: this.last.t, ageMs, stale: ageMs > this.staleMs };
  }
}

class PlanMemory {
  constructor() { this.goal = null; this.steps = []; this.i = 0; this.replans = []; this.log = []; }
  set(goal, steps, t) { this.goal = goal; this.steps = steps.slice(); this.i = 0; this.log.push({ t, kind: 'set', goal, steps: this.steps.slice() }); }
  step() { return this.i < this.steps.length ? this.steps[this.i] : null; }
  advance(t) { if (this.i < this.steps.length) { this.log.push({ t, kind: 'done', step: this.steps[this.i] }); this.i++; } return this.step(); }
  replan(reason, steps, t) {
    this.replans.push({ t, reason });
    this.log.push({ t, kind: 'replan', reason, steps: steps ? steps.slice() : null });
    if (steps) { this.steps = steps.slice(); this.i = 0; }
  }
  view() { return { goal: this.goal, steps: this.steps.slice(), at: this.i, replans: this.replans.length }; }
}

// fire rule shared with ./timing.js: fire on this tick when this tick is the closest one to the ideal moment (ttg <= tick / 2)
class ActionSchedule {
  constructor(o) { this.tickMs = (o && o.tickMs) || TICK_MS; this.items = new Map(); this.n = 0; this.log = []; }
  add(a) { const id = ++this.n; this.items.set(id, { id, skill: a.skill, ttgMs: a.ttgMs, t: a.t, firstTtg: a.ttgMs, moves: 0 }); return id; }
  cancel(id, t, why) { const it = this.items.get(id); if (!it) return false; this.items.delete(id); this.log.push({ t, kind: 'cancel', id, skill: it.skill, why: why || 'cancelled' }); return true; }
  // advance to time t: re-estimate each item (estimate may be null -> cancel), fire the ones whose best tick is now
  tick(t, estimate) {
    const fired = [];
    for (const it of Array.from(this.items.values())) {
      let ttg = it.ttgMs - (t - it.t);
      if (estimate) { const e = estimate(it, t); if (e == null) { this.cancel(it.id, t, 'estimate gone'); continue; } if (Math.abs(e - ttg) > 1e-9) it.moves++; ttg = e; }
      it.ttgMs = ttg; it.t = t;
      if (ttg <= this.tickMs / 2) { this.items.delete(it.id); const f = { id: it.id, skill: it.skill, t, ttgAtFire: ttg, moves: it.moves }; fired.push(f); this.log.push({ kind: 'fire', ...f }); }
    }
    return fired;
  }
  list() { return Array.from(this.items.values()).map((x) => ({ ...x })); }
}

const sleepHooks = new Map();
function registerSleepHook(h) {
  if (!h || !h.game) throw new Error('sleep hook needs a game name');
  if (h.play || h.selfPlay || h.practice) throw new Error('sleep never plays games: a hook may only give day data');
  sleepHooks.set(h.game, h); return h;
}

module.exports = { IntentChannel, PlanMemory, ActionSchedule, registerSleepHook, sleepHooks, STALE_MS, TICK_MS, CORE: 'stand-in (I3 core not wired yet)' };
