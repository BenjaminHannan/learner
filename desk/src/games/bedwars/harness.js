'use strict';
// Glim team, Bedwars side (plan v4.1 P4, §3b): measurements. Reads logs only; trains nothing; no grader output enters here.
//   latency()     p95 frame->key from timestamps (mark: <= 30 ms p95)
//   timing()      timing error in ms per skill (jump-at-edge, block-at-hit, crit-on-fall) against the truth-log ideal moment
//   longHorizon() the goal scorer (steps done in order, replans) from the server truth log
//   acceptance()  self-sufficient play: decide -> launch -> match -> play -> quit, >= 9 of 10 (per-step failures reported)
// The pass marks used for a real run are the ones committed in MARKS before it; the defaults here are only the plan's numbers.
const fs = require('fs');
const Timing = require('./timing');
const Truth = require('./truthlog');
const Tactics = require('./tactics');

const MARKS_DEFAULT = { p95FrameToKeyMs: 30, acceptance: { passes: 9, of: 10 } };

// records: [{frameT, keyT}] (ms; frame capture time and the time the keys went out) -> {n, p50, p95, max, over}
function latency(records, budgetMs) {
  const d = (records || []).map((r) => Number(r.keyT) - Number(r.frameT)).filter((x) => Number.isFinite(x) && x >= 0);
  const b = budgetMs == null ? MARKS_DEFAULT.p95FrameToKeyMs : budgetMs;
  const p95 = Timing.quant(d, 0.95);
  return { n: d.length, p50: Timing.quant(d, 0.5), p95, max: d.length ? Math.max(...d) : null, overBudget: d.length ? d.filter((x) => x > b).length / d.length : null,
    budgetMs: b, pass: d.length ? p95 <= b : null };
}

// actions: what the schedule fired [{skill, t}]; events: the truth log -> per-skill report (median / p90 |error|, bias, within a tick)
function timing(actions, events, me, o) { return Timing.timingReport(actions, events, me || 'GlimBot', o); }

function longHorizon(events, me, plan, planLog) {
  const g = Truth.goalScore(events, me || 'GlimBot', plan || Tactics.RUSH_PLAN, planLog);
  return { ...g, milestone: g.finished && g.replans >= 1 && g.replanAfterInterruption };
}

// sessions: PlaySession results (session.js). A try passes when every stage is reached and nothing was left running.
const STAGES = ['decide', 'launch', 'match', 'play', 'quit'];
function acceptance(sessions, marks) {
  const m = (marks && marks.acceptance) || MARKS_DEFAULT.acceptance;
  const tries = (sessions || []).map((s, i) => {
    const r = s.reached || {}, firstMiss = STAGES.find((k) => !r[k]) || null;
    const failedStep = (s.steps || []).find((x) => x && x.ok === false);
    const cleanupFail = (s.cleanup || []).filter((c) => !c.ok).map((c) => c.what);
    return { i, pass: !firstMiss && s.outcome === 'played', outcome: s.outcome || null, firstMiss, failedStep: failedStep ? failedStep.step : null,
      error: failedStep && failedStep.errors && failedStep.errors.length ? failedStep.errors[failedStep.errors.length - 1] : s.error || null,
      askedBen: s.askedBen ? s.askedBen.reason : null, cleanupFail };
  });
  const perStep = {}, perStage = {};
  for (const t of tries) { if (t.failedStep) perStep[t.failedStep] = (perStep[t.failedStep] || 0) + 1; if (t.firstMiss) perStage[t.firstMiss] = (perStage[t.firstMiss] || 0) + 1; }
  const passes = tries.filter((t) => t.pass).length;
  return { n: tries.length, passes, rate: tries.length ? passes / tries.length : null, mark: m, pass: tries.length >= m.of ? passes >= m.passes : null,
    perStepFailures: perStep, perStageMisses: perStage, gpuLeftHeld: tries.filter((t) => t.cleanupFail.includes('gpu')).length,
    askedBen: tries.filter((t) => t.askedBen).map((t) => ({ i: t.i, reason: t.askedBen })), tries };
}

// a JSONL log (read-only); bad lines are skipped
function readJsonl(p) {
  let txt = ''; try { txt = fs.readFileSync(p, 'utf8'); } catch (e) { return []; }
  const out = []; for (const l of txt.split('\n')) { if (!l.trim()) continue; try { out.push(JSON.parse(l)); } catch (e) { /* skip */ } }
  return out;
}

module.exports = { latency, timing, longHorizon, acceptance, readJsonl, STAGES, MARKS_DEFAULT };
