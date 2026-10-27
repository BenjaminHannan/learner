'use strict';
// Helper agents: schedules, the persisted helper list, the scheduler, the run slots and the screen lock.
// Pure Node (no Electron) so it can be unit tested. main.js wires in the real agent, browser and notifications.
const fs = require('fs');
const path = require('path');

const MIN_EVERY_MS = 5 * 60 * 1000;
const MAX_HELPERS = 12;
const TICK_MS = 30000;
const REPORT_KEEP = 600;
const SUMMARY_KEEP = 200;
const MAX_ITEMS = 400;

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
function parseSchedule(o) {
  o = o || {};
  const every = o.every != null && o.every !== '' ? o.every : null;
  const at = o.at != null && o.at !== '' ? o.at : null;
  if (every && at) throw new Error('give every or at, not both');
  if (every) { const ms = parseEvery(every); return { kind: 'every', ms, label: 'every ' + everyLabel(ms) }; }
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
  max() { return Math.max(1, Math.floor(Number(this.getMax())) || 1); }
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
  let t = "You are helper '" + h.name + "'. Task: " + h.task + '. Finish with a short report.';
  if (h.lastReport && (h.every || h.at)) t += '\nPrevious report: ' + short(h.lastReport, REPORT_KEEP) + '\nSay what changed since then.';
  return t;
}

function lastAssistantText(messages) {
  for (let i = (messages || []).length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === 'assistant' && typeof m.content === 'string' && m.content.trim()) return m.content.trim();
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
    for (const h of this.items) if (h.status !== 'stopped') h.status = 'idle'; // nothing survives a restart mid-run
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
      threadId: h.threadId, parent: h.parent, lastRun: h.lastRun || null, lastSummary: h.lastSummary || '' };
  }
  list() { return this.items.map((h) => this.view(h)); }
  find(ref) {
    ref = String(ref || '').trim().toLowerCase();
    if (!ref) return null;
    return this.items.find((h) => h.id.toLowerCase() === ref) || this.items.find((h) => h.name.toLowerCase() === ref) || null;
  }
  byThread(threadId) { return this.items.find((h) => h.threadId === threadId) || null; }

  add({ name, task, every, at, parent }) {
    name = short(name, 40);
    task = String(task || '').trim();
    if (!name) throw new Error('name is required');
    if (!task) throw new Error('task is required');
    const sched = parseSchedule({ every, at });
    if (this.find(name) && this.find(name).status !== 'stopped') throw new Error("a helper named '" + name + "' already exists; stop it first or pick another name");
    if (this.items.length >= MAX_HELPERS) throw new Error('too many helpers (max ' + MAX_HELPERS + '); delete one first');
    const id = 'h' + this.now().toString(36).slice(-4) + Math.random().toString(36).slice(2, 5);
    const t = this.o.store.newThread();
    t.title = 'Helper: ' + name; t.helper = id;
    this.o.store.saveThread(t);
    const h = { id, name, task, every: every || null, at: at || null, next: null, paused: false, status: 'idle', threadId: t.id, parent: parent || null, created: this.now(), lastRun: null, lastReport: '', lastSummary: '' };
    this.items.push(h);
    if (sched.kind === 'at') { h.next = nextRun(sched, this.now()); this.changed(); } else { this.changed(); this._run(h); }
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
    this.abort(h.id);
    this.items = this.items.filter((x) => x !== h);
    try { this.o.store.deleteThread(h.threadId); } catch (e) { /* ignore */ }
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
  tick() {
    const now = this.now();
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
  close() { if (this.timer) clearInterval(this.timer); this.timer = null; for (const id of [...this.active.keys()]) this.abort(id); }

  async _run(h) {
    if (this.active.has(h.id)) return;
    const rec = { ctl: new AbortController(), agent: null };
    this.active.set(h.id, rec);
    const sched = this.sched(h);
    const start = this.now();
    h.status = 'queued'; h.lastRun = start;
    h.next = sched.kind === 'once' ? null : nextRun(sched, start);
    this.changed();
    const onState = (s) => {
      if (rec.done || h.status === 'stopped') return;
      const next = s === 'waiting' ? 'waiting-for-Ben' : s;
      if (h.status === next) return;
      h.status = next;
      this.changed();
      if (s === 'waiting') { try { this.o.onNeedBen && this.o.onNeedBen(this.view(h)); } catch (e) { /* ignore */ } }
    };
    let res;
    try {
      res = await this.o.runner(h, helperText(h), { signal: rec.ctl.signal, onState, attach: (a) => { rec.agent = a; } });
    } catch (e) { res = { error: String(e && e.message || e) }; }
    rec.done = true;
    this.active.delete(h.id);
    res = res || {};
    const wasStopped = h.status === 'stopped';
    if (!wasStopped) h.status = 'idle';
    let report = res.report || '';
    if (!report) report = res.error ? 'Failed: ' + res.error : res.stopped ? 'Stopped before finishing.' : 'Finished with no report.';
    h.lastReport = report;
    h.lastSummary = short(report, SUMMARY_KEEP);
    this.changed();
    if (!wasStopped) { try { this.o.onFinish && this.o.onFinish(this.view(h), h.lastSummary, h.parent); } catch (e) { /* ignore */ } }
  }
}

// Runner used by the app (and the tests): a helper run is one Agent run in the helper's own thread.
// makeAgent(h, {onState}) -> {agent, dispose}
function createRunner({ store, makeAgent }) {
  return async (h, text, { signal, onState, attach }) => {
    const thread = store.loadThread(h.threadId) || { ...store.newThread(), id: h.threadId, title: 'Helper: ' + h.name, helper: h.id };
    thread.messages = []; // fresh context per run; the last report rides in the message
    thread.items = (thread.items || []).slice(-MAX_ITEMS);
    thread.title = 'Helper: ' + h.name; thread.helper = h.id;
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

module.exports = { Helpers, Limiter, ScreenLock, createRunner, parseSchedule, parseEvery, parseAt, nextRun, fmtWhen, addNotice, takeNotices, helperText, lastAssistantText, short, MIN_EVERY_MS, MAX_HELPERS };
