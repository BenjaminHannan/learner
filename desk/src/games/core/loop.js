'use strict';
// I3 two-speed core, part 5: THE LOOP that joins the parts. Game-agnostic: everything game-specific comes from the adapter.
//
//   slow brain (every ~0.5-2 s, answers arrive LATE)  --plan steps + tactical calls-->  plan memory  --call-->  intent channel
//   fast reflex (every tick)  reads the current call  -> a move now;  timed actions go through the schedule (fire at time-to-go 0)
//
// Adapter interface (see src/games/adapters/*.js):
//   name, tickMs, maxTicks, vocab, nIn, nA, goal, actEveryTicks (moves count only every k-th tick; default 1)
//   init(seed) -> state                    observe(state, tMs) -> obs (what Glim can see; no hidden truth)
//   planner(obs, doneIds) -> steps         the stand-in slow brain (the real one is the model: see brain.js)
//   judge(step, obs) -> {status, progress} how the current step is going (core/plan.js)
//   fallback(obs, call) -> move            the hand rule, used until sleep has kept a reflex
//   fallbackRaw(raw) -> move               the same hand rule on a logged frame (the night's seatbelt compares against it)
//   rawFrame(obs, call, truth?) -> JSON    what the night needs to rebuild features and labels (truth only when logging; features()
//                                          must never read raw.truth: the reflex is given rawFrame(obs, call) without it)
//   features(raw) -> Float64Array(nIn)     the reflex's input
//   nightLabel(raw) -> move | null         the slow night labeller (truth log, hindsight; never plays)
//   timedTargets(obs, call) -> [{id, action, lagMs, gap}]
//   step(state, move, fired, tMs) -> {state, contacts: [{id, atMs}]}
//   done(state, tMs)  outcome(state) -> {goalDone, ...}
const { IntentChannel } = require('./intent');
const { PlanMemory } = require('./plan');
const { ActionSchedule } = require('./schedule');
const { rng } = require('../../tinynet');

// the stand-in brain: plans with adapter.planner; its answer is computed from the picture it was GIVEN and arrives latencyMs later
function standInBrain(adapter) {
  return { think(obs, view, need) { const steps = adapter.planner(obs, view.done); return { steps, call: steps[0] ? steps[0].call : null }; } };
}

// o: {seed, brain, reflex (ReflexNet|null), planMemory (true), replan (true), mode ('tau'), latencyMs [lo, hi], periodMs, log: true}
function runEpisode(adapter, o) {
  o = o || {};
  const seed = o.seed || 1, tick = adapter.tickMs, r = rng(seed * 7919 + 17), brain = o.brain || standInBrain(adapter);
  const usePlan = o.planMemory !== false, useReplan = o.replan !== false, [lo, hi] = o.latencyMs || [500, 2000], period = o.periodMs || 1000;
  const intent = new IntentChannel(adapter.vocab), plan = new PlanMemory({ patienceMs: o.patienceMs || 6000 });
  const sched = new ActionSchedule({ tickMs: tick, mode: o.mode || 'tau', timing: o.reflex ? o.reflex.timing() : null });
  let state = adapter.init(seed), pending = null, lastAsk = -Infinity;
  const acts = [], lat = [], reflexMs = [];
  for (let i = 0; i < (adapter.maxTicks || 1e9); i++) {
    const t = i * tick;
    if (adapter.done(state, t)) break;
    const obs = adapter.observe(state, t);
    // 1. a brain answer arrives (it was thought about an OLD picture)
    if (pending && t >= pending.due) {
      const res = pending.res, kind = pending.kind; pending = null;
      if (res && res.steps) {
        if (!plan.goal || !usePlan) plan.setPlan(adapter.goal, res.steps, t);
        else if (kind === 'replan' && useReplan) plan.replan(res.steps, t);
      }
      const c = plan.current(); if (c) intent.send(c.call, t, 'brain');
    }
    // 2. plan memory checks progress against what is seen
    const ev = plan.tick(obs, adapter.judge, t);
    if (ev.event === 'advanced') intent.send(plan.current().call, t, 'plan');
    // 3. ask the slow brain: no plan yet, a surprise, or its regular look (without plan memory it must re-plan from the screen)
    if (!pending && t - lastAsk >= period) {
      const need = !plan.goal ? 'plan' : (plan.needsReplan && useReplan ? 'replan' : (!usePlan ? 'plan' : null));
      if (need) {
        const view = usePlan ? plan.view() : { goal: adapter.goal, done: [] };
        const res = brain.think(JSON.parse(JSON.stringify(obs)), view, need); const L = lo + (hi - lo) * r();
        pending = { due: t + L, res, kind: need }; lat.push(L); lastAsk = t;
      }
    }
    // 4. the fast reflex follows the current call (kept when the brain is quiet)
    const call = intent.current(t).call;
    const t0 = process.hrtime.bigint();
    let move;
    if (o.reflex && o.reflex.act && call) move = o.reflex.action(adapter.features(adapter.rawFrame(obs, call)));
    else move = call ? adapter.fallback(obs, call) : 0;
    const fired = sched.tick(t, call ? adapter.timedTargets(obs, call) : []);
    reflexMs.push(Number(process.hrtime.bigint() - t0) / 1e6);
    if (o.log !== false && call && i % (adapter.actEveryTicks || 1) === 0) acts.push({ r: adapter.rawFrame(obs, call, state), a: move });   // state = the truth log, for hindsight labels at night
    const res = adapter.step(state, move, fired, t); state = res.state;
    for (const c of res.contacts || []) sched.contact(c.id, c.atMs);
  }
  const rm = reflexMs.slice().sort((a, b) => a - b);
  return {
    outcome: adapter.outcome(state), replans: plan.replans, surprises: plan.surprises.length, surpriseReasons: plan.surprises.map((x) => x.reason), planFinished: plan.finished,
    timing: sched.report(), errors: sched.errors.slice(), misses: sched.misses, intent: intent.stats(), brainLatencyMs: lat,
    reflexP95Ms: rm.length ? rm[Math.floor(rm.length * 0.95)] : null, acts, times: sched.hindsight()
  };
}

module.exports = { runEpisode, standInBrain };
