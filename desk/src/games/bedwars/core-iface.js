'use strict';
// Glim team, Bedwars side: the ONE door to Glim's two-speed core (I3, src/games/core/, commit f6ae55afa). No stand-ins: the real
// intent channel, plan memory, timed-action schedule, reflex + sleep hook, episode loop and brain prompt are re-exported as they are.
// core/ is not edited and holds no Bedwars code.
//
// Added here: LiveLoop, a tick-by-tick driver built only from those core parts, for a game that runs in REAL time (Bedwars runs on
// BensPC; core/loop.js runEpisode() steps an in-process game). It is game-agnostic; it lives here only because core/ is I3's.
// Differences from runEpisode, all because the real slow brain is slow and often wrong (I3's measurement: ~2.7 s per call, the right
// call 6/12, whole plans 1/12, done-list ignored, follow-ups never sent):
//   - play starts at once on the rules' own plan (adapter.repair of nothing: the goal and what it needs); the brain's first plan
//     replaces it when it lands (3.5-11 s later);
//   - the brain is asked only for a first plan or a surprise the rules cannot fix, never more than once per minAskGapMs
//     (default 2857 ms = 0.35 calls/s), and its answer may arrive late (simulated latency, or a Promise for the real model);
//   - every plan (the brain's or ours) goes through adapter.repair(steps, obs, doneIds) before the plan memory takes it;
//   - surprises the adapter's rules can fix (died, blocked for lack of something, an urgent threat) are fixed AT ONCE by the plan;
//   - between answers the plan memory advances by itself (judge says done -> next step's call goes to the intent channel), and the
//     reflex keeps acting every tick on the current call; timed actions keep being re-estimated and fire on their tick.
// Optional adapter hooks used here (besides the I3 interface): repair(steps, obs, done), urgent(obs, currentStep) -> steps | null,
// interrupted(obs) -> reason | null, stepsFromCalls(calls) -> steps (for the real model's parsed calls).
const intent = require('../core/intent');
const plan = require('../core/plan');
const schedule = require('../core/schedule');
const reflex = require('../core/reflex');
const loop = require('../core/loop');
const brain = require('../core/brain');
const { rng } = require('../../tinynet');

const MIN_ASK_GAP_MS = 2857;   // 0.35 calls/s: the measured real rate (I3 real/, ~2.7 s per call)
const sameIds = (a, b) => a.length === b.length && a.every((s, i) => s.id === b[i].id);

class LiveLoop {
  // o: {brain, reflex (ReflexNet), patienceMs, minAskGapMs, latencyMs [lo, hi] (simulated brains only), mode, seed, planFile, rulesFirst (true)}
  constructor(adapter, o) {
    this.ad = adapter; this.o = o || {};
    this.intent = new intent.IntentChannel(adapter.vocab, { holdMs: 2000 });
    this.plan = new plan.PlanMemory({ patienceMs: this.o.patienceMs || 6000, file: this.o.planFile || null });
    this.sched = new schedule.ActionSchedule({ tickMs: adapter.tickMs, mode: this.o.mode || 'tau', timing: this.o.reflex ? this.o.reflex.timing() : null });
    this.brain = this.o.brain || loop.standInBrain(adapter); this.gap = this.o.minAskGapMs == null ? MIN_ASK_GAP_MS : this.o.minAskGapMs;
    this.r = rng((this.o.seed || 1) * 7919 + 17); this.pending = null; this.arrived = []; this.lastAsk = -Infinity; this.lastObs = null; this.askedPlan = false;
    this.stats = { ticks: 0, brainAsks: 0, brainAnswers: 0, brainReplans: 0, ruleReplans: 0, urgent: 0, advancedByPlan: 0, moves: 0, fired: 0, askTimes: [] };
    this.planLog = [];   // for the truth-log goal scorer: [{t, type: 'plan'|'replan', reason, by}]
  }
  steps(res) { if (!res) return null; if (res.steps) return res.steps; if (res.calls && this.ad.stepsFromCalls) return this.ad.stepsFromCalls(res.calls); return null; }
  fix(steps, obs) { return this.ad.repair ? this.ad.repair(steps, obs, this.plan.done) : steps; }
  setSteps(steps, t, why, by) {
    const first = !this.plan.goal;
    if (first) this.plan.setPlan(this.ad.goal, steps, t); else this.plan.replan(steps, t);
    this.planLog.push({ t, type: first ? 'plan' : 'replan', reason: why, by, steps: steps.map((s) => s.id) });
    const c = this.plan.current(); if (c) this.intent.send(c.call, t, by === 'brain' ? 'brain' : 'plan');
  }
  // the brain's answer, whenever it lands (it was thought about an OLD picture: repaired against what is seen NOW)
  deliver(res, kind, t) {
    this.stats.brainAnswers++; const raw = this.steps(res); if (!raw || !this.lastObs) return;
    const steps = this.fix(raw, this.lastObs); if (!steps.length) return;
    if (this.plan.goal && kind !== 'plan' && !this.plan.needsReplan && sameIds(steps, this.plan.steps)) return;
    this.stats.brainReplans += this.plan.goal ? 1 : 0; this.setSteps(steps, t, kind, 'brain');
  }
  ask(obs, need, t) {
    this.lastAsk = t; this.stats.brainAsks++; this.stats.askTimes.push(t);
    const res = this.brain.think(JSON.parse(JSON.stringify(obs)), this.plan.goal ? this.plan.view() : { goal: this.ad.goal, done: [] }, need);
    if (res && typeof res.then === 'function') { this.pending = { kind: need, promise: true }; res.then((x) => this.arrived.push({ res: x, kind: need }), () => this.arrived.push({ res: null, kind: need })); return; }
    const [lo, hi] = this.o.latencyMs || [2700, 2900]; this.pending = { kind: need, due: t + lo + (hi - lo) * this.r(), res };
  }
  // the plan fixes what its rules can, at once
  ruleFix(obs, t, why) {
    const steps = this.fix(this.plan.steps, obs);
    if (!steps.length || sameIds(steps, this.plan.steps)) return false;
    this.stats.ruleReplans++; this.setSteps(steps, t, why, 'rules'); return true;
  }
  // one tick: obs = what Glim sees now -> {call, stale, move, fired, event}
  tick(obs, t) {
    this.stats.ticks++; this.lastObs = obs;
    // 1. brain answers that have landed
    if (this.pending && !this.pending.promise && t >= this.pending.due) { const p = this.pending; this.pending = null; this.deliver(p.res, p.kind, t); }
    while (this.arrived.length) { const a = this.arrived.shift(); this.pending = null; this.deliver(a.res, a.kind, t); }
    // 2. the plan's own rules: start on the rules' plan while the brain thinks; an interruption (I died); an urgent threat
    if (!this.plan.goal && this.ad.repair && this.o.rulesFirst !== false) { const steps = this.fix([], obs); if (steps.length) { this.stats.ruleReplans++; this.setSteps(steps, t, 'rules first (the brain is slow)', 'rules'); } }
    if (this.plan.goal) {
      const why = this.ad.interrupted ? this.ad.interrupted(obs) : null;
      if (why) {   // an interruption the rules always handle: re-plan from what is seen now (the brain is asked only if the rules leave nothing)
        this.plan.interrupt(why, t); const steps = this.fix(this.plan.steps, obs);
        if (steps.length) { this.stats.ruleReplans++; this.setSteps(steps, t, why, 'rules'); }
      }
      const u = this.ad.urgent ? this.ad.urgent(obs, this.plan.current()) : null;
      if (u && u.length) { this.stats.urgent++; const steps = this.fix(u.concat(this.plan.steps), obs); this.stats.ruleReplans++; this.setSteps(steps, t, 'urgent: ' + u.map((s) => s.kind).join('+'), 'rules'); }
    }
    // 3. plan memory checks progress; it advances by itself, and fixes a surprise by rule when it can
    const ev = this.plan.tick(obs, this.ad.judge, t);
    if (ev.event === 'advanced') { this.stats.advancedByPlan++; this.intent.send(this.plan.current().call, t, 'plan'); }
    if (this.plan.needsReplan) this.ruleFix(obs, t, this.plan.needsReplan);
    // 4. the slow brain: a first plan, or a surprise the rules could not fix; never faster than its measured rate
    if (!this.pending && t - this.lastAsk >= this.gap) {
      const need = !this.askedPlan ? 'plan' : this.plan.needsReplan ? 'replan' : null;
      if (need) { if (need === 'plan') this.askedPlan = true; this.ask(obs, need, t); }
    }
    // 5. the fast reflex follows the current call (kept when the brain is quiet); timed actions re-estimated every tick
    const cur = this.intent.current(t), call = cur.call;
    let move = null;
    if (this.o.reflex && this.o.reflex.act && call) move = this.o.reflex.action(this.ad.features(this.ad.rawFrame(obs, call)));
    if (move == null) move = this.ad.fallback(obs, call);
    const fired = this.sched.tick(t, this.ad.timedTargets(obs, call));
    if (move) this.stats.moves++; this.stats.fired += fired.length;
    return { call, stale: cur.stale, move, fired, event: ev.event };
  }
  contacts(list) { for (const c of list || []) this.sched.contact(c.id, c.atMs); }
  report() {
    const asks = this.stats.askTimes, span = asks.length > 1 ? asks[asks.length - 1] - asks[0] : 0;
    return { ...this.stats, brainRatePerS: span ? (asks.length - 1) / (span / 1000) : null, plan: this.plan.view(), finished: this.plan.finished, replans: this.plan.replans,
      surprises: this.plan.surprises.map((x) => x.reason), intent: this.intent.stats(), timing: this.sched.report(), planLog: this.planLog };
  }
}

// play the adapter's own practice model with a LiveLoop in simulated time (tests and toy practice; the real game is on BensPC)
function runLive(adapter, o) {
  o = o || {}; const lp = new LiveLoop(adapter, o), acts = [];
  let state = adapter.init(o.seed || 1, o.game);
  for (let i = 0; i < (o.maxTicks || adapter.maxTicks || 1e9); i++) {
    const t = i * adapter.tickMs; if (adapter.done(state, t)) break;
    const obs = adapter.observe(state, t), out = lp.tick(obs, t);
    if (o.log !== false && out.call && i % (adapter.actEveryTicks || 1) === 0) acts.push({ r: adapter.rawFrame(obs, out.call, state), a: out.move });
    if (o.onTick) o.onTick(t, out, obs, lp);
    const res = adapter.step(state, out.move, out.fired, t); state = res.state; lp.contacts(res.contacts);
  }
  return { outcome: adapter.outcome(state), ...lp.report(), acts, times: lp.sched.hindsight() };
}

module.exports = { intent, plan, schedule, reflex, loop, brain, IntentChannel: intent.IntentChannel, PlanMemory: plan.PlanMemory, ActionSchedule: schedule.ActionSchedule,
  ReflexSleep: reflex.ReflexSleep, ReflexNet: reflex.ReflexNet, runEpisode: loop.runEpisode, standInBrain: loop.standInBrain, buildPrompt: brain.buildPrompt, parseCalls: brain.parseCalls,
  LiveLoop, runLive, MIN_ASK_GAP_MS };
