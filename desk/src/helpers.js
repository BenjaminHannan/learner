'use strict';
// Helper agents: schedules, the persisted helper list, the scheduler, the run slots and the screen lock.
// Pure Node (no Electron) so it can be unit tested. main.js wires in the real agent, browser and notifications.
const fs = require('fs');
const path = require('path');
const { P } = require('./user');

const MIN_EVERY_MS = 5 * 60 * 1000;
const MAX_HELPERS = 500;   // effectively unlimited (Ben Oct 28); only a runaway guard
const TICK_MS = 30000;
const REPORT_KEEP = 600;
const SUMMARY_KEEP = 200;
const MAX_ITEMS = 400;
const RETRY_MS = 5 * 60 * 1000;   // a recurring Glim that failed once tries again soon, not at its next slot
const RESUME_MS = 60 * 1000;     // a one-time Glim cut off by quitting runs again shortly after launch
const QUIET_RE = /^\s*NO_UPDATE\W*$/i;

const short = (s, n) => { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
const p2 = (n) => String(n).padStart(2, '0');

// ---- schedules -------------------------------------------------------------------------------
function parseEvery(s) {
  const m = /^(\d+(?:\.\d+)?)\s*(m|min|h|hr|d)$/i.exec(String(s || '').trim());
  if (!m) throw new Error('every must look like "30m", "2h" or "1d"');
  const unit = m[2].toLowerCase();
  const ms = Math.round(Number(m[1]) * (unit === 'd' ? 86400000 : unit[0] === 'h' ? 3600000 : 60000));
  if (ms < MIN_EVERY_MS) throw new Error('every must be at least 5m');
  return ms;
}

function parseAt(s) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(s || '').trim());
  if (!m || Number(m[1]) > 23 || Number(m[2]) > 59) throw new Error('at must look like "08:00" (24 hour, local time)');
  return { h: Number(m[1]), m: Number(m[2]) };
}

function everyLabel(ms) {
  if (ms % 86400000 === 0) return ms / 86400000 + 'd';
  if (ms % 3600000 === 0) return ms / 3600000 + 'h';
  return Math.round(ms / 60000) + 'm';
}

// -> {kind:'once'} | {kind:'every', ms, label} | {kind:'at', h, m, label}
const SIM_STOP = new Set(['agent', 'glim', 'helper', 'the', 'and', 'for', 'ben', 'bens', 'his', 'every', 'daily', 'check', 'watch']);

function parseSchedule(o) {
  o = o || {};
  const every = o.every != null && o.every !== '' ? o.every : null;
  const at = o.at != null && o.at !== '' ? o.at : null;
  // Models often send both for "every morning at 8:00"; `at` wins (daily), whatever `every` says.
  if (every && !at) { const ms = parseEvery(every); return { kind: 'every', ms, label: 'every ' + everyLabel(ms) }; }
  if (at) { const t = parseAt(at); return { kind: 'at', h: t.h, m: t.m, label: 'daily ' + p2(t.h) + ':' + p2(t.m) }; }
  return { kind: 'once', label: 'once' };
}

// Next run strictly after `from` (ms). Uses local Date arithmetic by calendar day, so a DST change
// moves "08:00" by zero hours on the clock, not by 24 h of elapsed time.
function nextRun(sched, from) {
  if (sched.kind === 'every') return from + sched.ms;
  if (sched.kind === 'at') {
    const d = new Date(from);
    let t = new Date(d.getFullYear(), d.getMonth(), d.getDate(), sched.h, sched.m, 0, 0).getTime();
    if (t <= from) t = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1, sched.h, sched.m, 0, 0).getTime();
    return t;
  }
  return null;
}

function fmtWhen(ts, now) {
  if (!ts) return '-';
  const d = new Date(ts), n = new Date(now || Date.now());
  const hm = p2(d.getHours()) + ':' + p2(d.getMinutes());
  if (d.toDateString() === n.toDateString()) return hm;
  return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()] + ' ' + hm;
}

// ---- run slots (concurrency limit) and the screen lock: one FIFO queue -------------------------
class Limiter {
  constructor(getMax) { this.getMax = typeof getMax === 'function' ? getMax : () => getMax; this.active = 0; this.q = []; }
  max() { const n = Math.floor(Number(this.getMax())); return n > 0 ? n : Infinity; } // 0 / unset = no limit
  full() { return this.active >= this.max() || this.q.length > 0; }
  // resolves to a release function; rejects (Error 'aborted') if the signal fires while queued
  acquire(signal) {
    return new Promise((resolve, reject) => {
      if (signal && signal.aborted) return reject(new Error('aborted'));
      const grant = () => {
        this.active++;
        let done = false;
        resolve(() => { if (!done) { done = true; this.active--; this._pump(); } });
      };
      if (!this.full()) return grant();
      const w = { grant };
      this.q.push(w);
      if (signal) signal.addEventListener('abort', () => {
        const i = this.q.indexOf(w);
        if (i >= 0) { this.q.splice(i, 1); reject(new Error('aborted')); }
      }, { once: true });
    });
  }
  _pump() { while (this.q.length && this.active < this.max()) this.q.shift().grant(); }
}

// One mouse: a FIFO lock. holder() is one agent's view of it: the first screen tool of a run takes the
// lock and it is kept until the run ends (so another agent cannot move the mouse between look and click).
class ScreenLock {
  constructor() { this.l = new Limiter(1); }
  holder() {
    let rel = null;
    return {
      held: () => !!rel,
      ensure: async (signal) => { if (!rel) rel = await this.l.acquire(signal); },
      release: () => { if (rel) { const r = rel; rel = null; r(); } }
    };
  }
}

// ---- notices (finished-helper messages for the primary thread) ---------------------------------
function addNotice(thread, name, summary) {
  summary = short(summary, SUMMARY_KEEP);
  thread.items = thread.items || [];
  thread.pendingNotices = thread.pendingNotices || [];
  thread.items.push({ t: 'notice', helper: name, text: summary });
  thread.pendingNotices.push({ name, summary });
}
// One short line for the model, or '' when nothing is queued. Clears the queue.
function takeNotices(thread) {
  const n = thread.pendingNotices;
  if (!n || !n.length) return '';
  thread.pendingNotices = [];
  return '[helper updates] ' + n.map((x) => x.name + ': ' + x.summary).join('; ');
}

function helperText(h) {
  let t = "You are helper '" + h.name + "'. Task: " + h.task + '. Work on your own: if a tool or a step fails, fix it or try another way yourself (agent_update changes a helper); do not ask Ben about errors or tool problems. Finish with a short report of the result only, with no notes about your own tools.';
  if (h.lastReport && (h.every || h.at)) t += '\nPrevious report: ' + short(h.lastReport, REPORT_KEEP) + '\nSay what changed since then.' + P('\nIf nothing worth telling Ben changed since then, reply with exactly: NO_UPDATE');
  return t;
}

// One desktop notification for the Glims that finished close together. list: [{name, summary, threadId, parent, failed}] -> {title, body, threadId}
// (a lone Glim opens its own thread; several open the thread that started them all, or just the window)
function batchNotice(list) {
  const f = list.filter((x) => x.failed).length;
  if (list.length === 1) return { title: "Spark '" + list[0].name + "' " + (f ? "couldn't finish" : 'finished'), body: list[0].summary, threadId: list[0].threadId };
  const parent = list.every((x) => x.parent && x.parent === list[0].parent) ? list[0].parent : null;
  return { title: list.length + ' Sparks finished' + (f ? ' (' + f + " couldn't finish)" : ''), body: list.map((x) => x.name).join(', ') + ': ' + short(list[0].summary, 100), threadId: parent };
}

// A Glim's report is its FINAL answer: the last assistant message with no tool call, minus any leading "I need to... / Let me..." narration
// (with thinking off the model writes a planning sentence before each tool call, and those must not become the summary shown in the list and pill).
const NARRATION = /^(?:i need to|i'll|i will|i'm going to|i am going to|i should|let me|let's|first,|now,|okay,|ok,|alright,|next,)\b/i;
function stripNarration(text) {
  const parts = String(text || '').trim().split(/(?<=[.!?:])\s+/);
  let k = 0;
  while (k < parts.length - 1 && NARRATION.test(parts[k].trim())) k++;
  return parts.slice(k).join(' ').trim();
}
function lastAssistantText(messages) {
  const ok = (m, withCalls) => m.role === 'assistant' && typeof m.content === 'string' && m.content.trim() && (withCalls || !(m.tool_calls && m.tool_calls.length));
  for (const withCalls of [false, true]) {
    for (let i = (messages || []).length - 1; i >= 0; i--) {
      const m = messages[i];
      if (ok(m, withCalls)) return stripNarration(m.content) || m.content.trim();
    }
  }
  return '';
}

// ---- the helper list + scheduler ---------------------------------------------------------------
class Helpers {
  /**
   * @param {object} o
   *  file: helpers.json path; store: Store (threads); runner(h, text, {signal, onState, attach}) -> {report, stopped, error}
   *  now(): ms; onChange(); onFinish(h, summary, parentThreadId); onNeedBen(h)
   */
  constructor(o) {
    this.o = o;
    this.now = o.now || Date.now;
    this.items = [];
    this.active = new Map(); // id -> {ctl, agent}
    this.timer = null;
    this.load();
  }

  load() {
    try { this.items = JSON.parse(fs.readFileSync(this.o.file, 'utf8')).helpers || []; } catch (e) { this.items = []; }
    const now = this.now();
    for (const h of this.items) {
      const cut = h.status === 'running' || h.status === 'queued' || h.status === 'waiting-for-Ben';
      if (h.status !== 'stopped' && h.status !== 'failed') h.status = 'idle'; // nothing survives a restart mid-run
      h.hold = null; h.dueHeld = false;
      // a one-time Glim cut off by quitting would never run again: give it one more go, but only one
      if (cut && !h.every && !h.at && !h.lastReport) {
        if (h.resumed) { h.next = null; h.lastSummary = 'Interrupted twice; use Run now to try again.'; }
        else { h.resumed = 1; h.next = now + RESUME_MS; h.lastSummary = 'Interrupted when the app closed; running again.'; }
      }
    }
  }
  save() {
    try {
      fs.mkdirSync(path.dirname(this.o.file), { recursive: true });
      const tmp = this.o.file + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify({ helpers: this.items }, null, 1));
      fs.renameSync(tmp, this.o.file);
    } catch (e) { /* a failed save must not kill a run */ }
  }
  changed() { this.save(); try { this.o.onChange && this.o.onChange(); } catch (e) { /* ignore */ } }

  sched(h) { try { return parseSchedule(h); } catch (e) { return { kind: 'once', label: 'once' }; } }
  view(h) {
    return { id: h.id, name: h.name, task: h.task, status: h.status, schedule: this.sched(h).label, next: h.next || null, paused: !!h.paused,
      threadId: h.threadId, parent: h.parent, lastRun: h.lastRun || null, lastSummary: h.lastSummary || '', quiet: !!h.quiet, lastError: h.lastError || null, hold: h.hold || null, holdCount: h.holdCount || 0, dueHeld: !!h.dueHeld };
  }
  list() { return this.items.map((h) => this.view(h)); }
  find(ref) {
    ref = String(ref || '').trim().toLowerCase();
    if (!ref) return null;
    const byName = (h) => h.name.toLowerCase() === ref; // a live helper wins over a stopped one of the same name
    return this.items.find((h) => h.id.toLowerCase() === ref) || this.items.find((h) => byName(h) && h.status !== 'stopped') || this.items.find(byName) || null;
  }
  byThread(threadId) { return this.items.find((h) => h.threadId === threadId) || null; }

  // deferFirst: do not run now; the first run is the next scheduled slot. mode: 'ask' | 'hands-off' for this Glim only (default: the helperMode setting).
  add({ name, task, every, at, parent, deferFirst, mode }) {
    name = short(name, 40);
    task = String(task || '').trim();
    if (!name) throw new Error('name is required');
    if (!task) throw new Error('task is required');
    const sched = parseSchedule({ every, at });
    if (this.find(name) && this.find(name).status !== 'stopped') throw new Error("a Glim named '" + name + "' already exists; stop it first or pick another name");
    const dup = this.similar(name, task, sched.label);
    if (dup) throw new Error("a similar Glim '" + dup.name + "' already exists (" + dup.schedule + '); use it, or stop it first');
    if (this.items.length >= MAX_HELPERS) throw new Error('too many Glims (max ' + MAX_HELPERS + '); delete one first');
    const id = 'h' + this.now().toString(36).slice(-4) + Math.random().toString(36).slice(2, 5);
    const t = this.o.store.newThread();
    t.title = 'Glim: ' + name; t.helper = id;
    this.o.store.saveThread(t);
    const h = { id, name, task, every: every || null, at: at || null, next: null, paused: false, status: 'idle', threadId: t.id, parent: parent || null, created: this.now(), lastRun: null, lastReport: '', lastSummary: '' };
    if (mode === 'ask' || mode === 'hands-off') h.mode = mode;
    this.items.push(h);
    if (sched.kind === 'at' || (deferFirst && sched.kind === 'every')) { h.next = nextRun(sched, this.now()); this.changed(); } else { this.changed(); this._run(h); }
    return this.view(h);
  }

  // An active Glim with the same schedule whose name or task shares most words with this one (the model re-creates existing ones).
  similar(name, task, label) {
    const words = (s) => new Set(String(s || '').toLowerCase().match(/[a-z0-9]+/g)?.filter((w) => w.length > 2 && !SIM_STOP.has(w)) || []);
    const overlap = (a, b) => { if (!a.size || !b.size) return 0; let n = 0; for (const w of a) if (b.has(w)) n++; return n / Math.min(a.size, b.size); };
    const n = words(name), t = words(task);
    for (const h of this.items) {
      if (h.status === 'stopped' || this.sched(h).label !== label) continue;
      if (overlap(n, words(h.name)) >= 0.5 || overlap(t, words(h.task)) >= 0.7) return this.view(h);
    }
    return null;
  }

  // Change a Glim in place: its task, name and/or schedule (every / at; an empty string clears that one), without stopping and re-creating it.
  update(ref, { name, task, every, at }) {
    const h = this.find(ref);
    if (!h) return null;
    const newEvery = every !== undefined ? (every || null) : h.every, newAt = at !== undefined ? (at || null) : h.at;
    const scheduleChanged = every !== undefined || at !== undefined;
    const sched = scheduleChanged ? parseSchedule({ every: newEvery, at: newAt }) : this.sched(h);
    if (name !== undefined) {
      name = short(name, 40);
      if (!name) throw new Error('name cannot be empty');
      const other = this.find(name);
      if (other && other !== h && other.status !== 'stopped') throw new Error("a Glim named '" + name + "' already exists");
      h.name = name;
    }
    if (task !== undefined) { task = String(task || '').trim(); if (!task) throw new Error('task cannot be empty'); h.task = task; }
    if (scheduleChanged) {
      h.every = newEvery; h.at = newAt;
      h.next = sched.kind === 'once' ? null : nextRun(sched, this.now());
      h.dueHeld = false;
      if (h.status === 'stopped' && sched.kind !== 'once') h.status = 'idle'; // a stopped Glim given a schedule is live again
    }
    this.changed();
    return this.view(h);
  }

  // Cancel the schedule, abort a running run, keep the helper (and its thread) as "stopped".
  stop(ref) {
    const h = this.find(ref);
    if (!h) return null;
    h.status = 'stopped'; h.every = null; h.at = null; h.next = null; h.paused = false;
    this.abort(h.id);
    this.changed();
    return this.view(h);
  }
  remove(ref) {
    const h = this.find(ref);
    if (!h) return false;
    h.status = 'stopped'; // no "finished" notice for a deleted helper
    const rec = this.active.get(h.id);
    this.abort(h.id);
    this.items = this.items.filter((x) => x !== h);
    if (rec) rec.deleteThread = true; // the aborted run still saves its thread; delete it once the run is over
    else try { this.o.store.deleteThread(h.threadId); } catch (e) { /* ignore */ }
    this.changed();
    return true;
  }
  pause(ref, on) {
    const h = this.find(ref);
    if (!h) return null;
    h.paused = on === undefined ? !h.paused : !!on;
    if (!h.paused && (this.sched(h).kind !== 'once') && (!h.next || h.next <= this.now())) h.next = nextRun(this.sched(h), this.now());
    this.changed();
    return this.view(h);
  }
  runNow(ref) {
    const h = this.find(ref);
    if (!h || this.active.has(h.id)) return false;
    if (h.status === 'stopped') h.status = 'idle';
    this._run(h);
    return true;
  }
  abort(id) { const a = this.active.get(id); if (a) a.ctl.abort(); return !!a; }
  steer(id, text) { const a = this.active.get(id); return !!(a && a.agent && a.agent.steer(text)); }
  isRunning(id) { return this.active.has(id); }

  // Run every helper whose time has come. A helper whose time passed while the app was closed is due once
  // (its next time is a single value, recomputed from "now" when the run starts), not once per missed slot.
  tick(force) {
    const now = this.now();
    if (!force && this.o.hold && this.o.hold()) { // force: the sleep check-in runs what is due // e.g. sleeping: due runs wait and fire once after wake
      let n = 0;
      for (const h of this.items) if (!h.dueHeld && !h.paused && h.status !== 'stopped' && !this.active.has(h.id) && h.next && h.next <= now) { h.dueHeld = true; n++; }
      if (n) this.changed(); // so the list can say "will run after Glim wakes up"
      return;
    }
    for (const h of this.items) {
      if (h.paused || h.status === 'stopped' || this.active.has(h.id)) continue;
      if (h.next && h.next <= now) this._run(h);
    }
  }
  start() {
    this.tick();
    this.timer = setInterval(() => this.tick(), this.o.tickMs || TICK_MS);
    if (this.timer.unref) this.timer.unref();
  }
  // closing: the app is quitting. Runs it aborts must not finish normally (that would save them as done, so an interrupted one-time
  // Glim would never resume, and would post a bogus "finished" notice); their saved running state is what load() resumes from.
  close() { this.closing = true; if (this.timer) clearInterval(this.timer); this.timer = null; for (const id of [...this.active.keys()]) this.abort(id); }

  async _run(h) {
    if (this.active.has(h.id)) return;
    const rec = { ctl: new AbortController(), agent: null };
    this.active.set(h.id, rec);
    const sched = this.sched(h);
    const start = this.now();
    h.status = 'queued'; h.lastRun = start; h.dueHeld = false; h.hold = null; h.quiet = false;
    h.next = sched.kind === 'once' ? null : nextRun(sched, start);
    this.changed();
    const onState = (s, info) => {
      if (rec.done || h.status === 'stopped') return;
      const next = s === 'waiting' ? 'waiting-for-Ben' : s;
      const hold = s === 'queued' ? 'slot' : null; // why it is waiting: every run slot is busy (the screen lock wait is not reported)
      if (h.status === next && h.hold === hold) return;
      h.status = next; h.hold = hold; h.holdCount = hold && info && info.running || 0;
      this.changed();
      if (s === 'waiting') { try { this.o.onNeedBen && this.o.onNeedBen(this.view(h)); } catch (e) { /* ignore */ } }
    };
    let res;
    try {
      res = await this.o.runner(h, helperText(h), { signal: rec.ctl.signal, onState, attach: (a) => { rec.agent = a; } });
    } catch (e) { res = { error: String(e && e.message || e) }; }
    rec.done = true;
    this.active.delete(h.id);
    if (rec.deleteThread) { try { this.o.store.deleteThread(h.threadId); } catch (e) { /* ignore */ } }
    if (this.closing) return;
    res = res || {};
    const wasStopped = h.status === 'stopped';
    h.hold = null;
    const failed = !!res.error && !res.stopped && !wasStopped, recurring = !!(h.every || h.at);
    const quiet = !failed && !wasStopped && !res.error && recurring && !!h.lastReport && QUIET_RE.test(res.report || '');
    if (!wasStopped) h.status = failed ? 'failed' : 'idle';
    let report = res.report || '';
    if (!report) report = res.error ? 'Failed: ' + res.error : res.stopped ? 'Stopped before finishing.' : 'Finished with no report.';
    if (failed) {
      h.lastError = short(res.error, 150); h.fails = (h.fails || 0) + 1;
      report = 'Failed: ' + h.lastError;
      if (h.fails === 1 && recurring) h.next = h.next ? Math.min(h.next, this.now() + RETRY_MS) : this.now() + RETRY_MS;
    } else if (!wasStopped && !res.stopped) { h.fails = 0; h.lastError = null; }
    if (quiet) { h.quiet = true; h.lastSummary = 'No change (checked ' + fmtWhen(this.now(), this.now()) + ')'; } // lastReport stays: the next run compares against real content
    else { if (!failed) h.lastReport = report; h.lastSummary = short(report, SUMMARY_KEEP); }
    this.changed();
    if (!wasStopped) { try { this.o.onFinish && this.o.onFinish(this.view(h), h.lastSummary, h.parent, { quiet, failed }); } catch (e) { /* ignore */ } }
  }
}

// Runner used by the app (and the tests): a helper run is one Agent run in the helper's own thread.
// makeAgent(h, {onState}) -> {agent, dispose}
function createRunner({ store, makeAgent }) {
  return async (h, text, { signal, onState, attach }) => {
    const thread = store.loadThread(h.threadId) || { ...store.newThread(), id: h.threadId, title: 'Glim: ' + h.name, helper: h.id };
    thread.messages = []; // fresh context per run; the last report rides in the message
    thread.items = (thread.items || []).slice(-MAX_ITEMS);
    thread.title = 'Glim: ' + h.name; thread.helper = h.id;
    if (signal.aborted) return { stopped: true };
    const made = await makeAgent(h, { onState });
    attach(made.agent);
    const onAbort = () => made.agent.stop();
    if (signal.aborted) onAbort(); else signal.addEventListener('abort', onAbort, { once: true });
    let r;
    try { r = await made.agent.run(thread, text); } finally { try { made.dispose && made.dispose(); } catch (e) { /* ignore */ } }
    return { report: lastAssistantText(thread.messages), stopped: !!(r && r.stopped), error: r && r.error };
  };
}

module.exports = { Helpers, Limiter, ScreenLock, createRunner, parseSchedule, parseEvery, parseAt, nextRun, fmtWhen, addNotice, takeNotices, helperText, batchNotice, lastAssistantText, short, MIN_EVERY_MS, MAX_HELPERS };
