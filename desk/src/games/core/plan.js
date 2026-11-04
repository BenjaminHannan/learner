'use strict';
// I3 two-speed core, part 2: PERSISTENT PLAN MEMORY. Game-agnostic.
// A goal -> steps plan that lasts minutes (and survives an app restart when given a file). Each step = { id, call, ...anything the
// adapter wants (e.g. a target snapshot) }. Every tick the adapter's judge(step, obs) says how the CURRENT step is going:
//   { status: 'done' | 'going' | 'blocked', progress: number (bigger = closer) }
// Surprise -> needsReplan (the slow brain is asked for new remaining steps):
//   blocked            what I see contradicts the step (a door locked, a path cut, the target is gone)
//   stalled            no progress for patienceMs
//   interrupt(reason)  told from outside (e.g. I died / got knocked back / Ben took over)
// Done step ids are remembered: that memory is what the brain cannot see on the screen.
const fs = require('fs');

class PlanMemory {
  constructor(o) {
    this.o = o || {}; this.file = this.o.file || null; this.patienceMs = this.o.patienceMs || 6000; this.maxAgeMs = this.o.maxAgeMs || 15 * 60000;
    this.reset(); if (this.file) this.load();
  }
  reset() { this.goal = null; this.steps = []; this.done = []; this.replans = 0; this.needsReplan = null; this.surprises = []; this.best = -Infinity; this.bestAt = null; this.startedAt = null; this.finished = false; }
  setPlan(goal, steps, nowMs) { this.goal = goal; this.steps = (steps || []).slice(); this.done = []; this.needsReplan = null; this.finished = false; this.startedAt = nowMs; this.best = -Infinity; this.bestAt = nowMs; this.save(); }
  // the brain's new remaining steps after a surprise (done steps are kept)
  replan(steps, nowMs) { this.steps = (steps || []).slice(); this.replans++; this.needsReplan = null; this.best = -Infinity; this.bestAt = nowMs; this.save(); }
  current() { return this.steps[0] || null; }
  view() { return { goal: this.goal, done: this.done.slice(), remaining: this.steps.map((s) => s.id), replans: this.replans, surprise: this.needsReplan }; }
  interrupt(reason, nowMs) { this.surprise(reason || 'interrupted', nowMs); }
  surprise(reason, nowMs) { if (this.needsReplan) return; this.needsReplan = reason; this.surprises.push({ at: nowMs, reason, step: this.current() && this.current().id }); this.save(); }
  // -> { event: null | 'advanced' | 'finished' | 'surprise', step }
  tick(obs, judge, nowMs) {
    if (this.finished || !this.goal) return { event: null };
    if (this.startedAt != null && nowMs - this.startedAt > this.maxAgeMs) { this.surprise('plan too old', nowMs); return { event: 'surprise' }; }
    const st = this.current(); if (this.bestAt == null) this.bestAt = nowMs;
    if (!st) { this.finished = true; this.save(); return { event: 'finished' }; }
    let j; try { j = judge(st, obs) || { status: 'going' }; } catch (e) { j = { status: 'going' }; }
    if (j.status === 'done') {
      this.done.push(st.id); this.steps.shift(); this.best = -Infinity; this.bestAt = nowMs;
      if (!this.steps.length) { this.finished = true; this.save(); return { event: 'finished', step: st }; }
      this.save(); return { event: 'advanced', step: this.current() };
    }
    if (j.status === 'blocked') { this.surprise('blocked: ' + (j.why || st.id), nowMs); return { event: 'surprise', step: st }; }
    if (typeof j.progress === 'number') { if (j.progress > this.best + 1e-9) { this.best = j.progress; this.bestAt = nowMs; } else if (nowMs - this.bestAt > this.patienceMs) { this.surprise('stalled on ' + st.id, nowMs); return { event: 'surprise', step: st }; } }
    return { event: null };
  }
  save() {
    if (!this.file) return;
    try { const tmp = this.file + '.tmp'; fs.writeFileSync(tmp, JSON.stringify({ goal: this.goal, steps: this.steps, done: this.done, replans: this.replans, needsReplan: this.needsReplan, startedAt: this.startedAt, finished: this.finished, surprises: this.surprises.slice(-20) })); fs.renameSync(tmp, this.file); } catch (e) { /* memory only */ }
  }
  load() {
    try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); Object.assign(this, { goal: j.goal, steps: j.steps || [], done: j.done || [], replans: j.replans || 0, needsReplan: j.needsReplan || null, startedAt: j.startedAt, finished: !!j.finished, surprises: j.surprises || [] }); } catch (e) { /* fresh */ }
  }
}

module.exports = { PlanMemory };
