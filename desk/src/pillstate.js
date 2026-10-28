'use strict';
// One state source for "what is Glim doing right now", with a fixed priority (error > waiting for Ben > working >
// done). It feeds the top pill, the top-bar Glim and the dock badge, so they never disagree. Pure Node (unit tested).
const PRIORITY = { error: 4, waiting: 3, working: 2, done: 1 };
const MOOD = { error: 'error', waiting: 'waiting', working: 'working', done: 'done' };
const short = (s, n) => { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
const firstLine = (s) => String(s || '').split('\n').map((l) => l.replace(/^[#*\-\s\d.)]+/, '').trim()).find((l) => l && !/^\[Action:/i.test(l)) || '';

class PillState {
  constructor(o) {
    o = o || {};
    this.now = o.now || Date.now;
    this.onChange = o.onChange || (() => {});
    this.doneMs = o.doneMs || 8000;
    this.agents = new Map();
    this.callSince = 0; // while a Call Glim call is on: when it started
    this.sleep = null; // {line, detail, since} while the sleep app runs (the pill's quiet resting state)
  }
  setCall(since) { this.callSince = since || 0; this.onChange(); }
  setSleep(info) { this.sleep = info ? { ...info, since: (this.sleep && this.sleep.since) || this.now() } : null; this.onChange(); }
  // a short heads-up (e.g. a check-in alert) that fades like a finished run
  flash(line, name) { const a = this._get('sleep-alert', name || 'Glim', null); a.status = 'done'; a.line = short(line, 60); a.step = short(line, 120); a.endedAt = this.now(); a.startedAt = this.now(); a.error = ''; a.approval = null; this._touch(a); }
  _get(key, name, threadId) {
    let a = this.agents.get(key);
    if (!a) { a = { key, name: name || 'Glim', threadId: threadId || null, status: 'working', line: '', step: '', error: '', approval: null, startedAt: this.now(), endedAt: 0, at: this.now(), lastText: '', title: '' }; this.agents.set(key, a); }
    if (name) a.name = name;
    if (threadId) a.threadId = threadId;
    return a;
  }
  _touch(a) { a.at = this.now(); this.onChange(); }

  // ev: the same events the chat gets. meta: {title}
  onEvent(key, name, threadId, ev, meta) {
    if (!ev || !ev.type) return;
    const t = ev.type;
    if (t === 'text' || t === 'reasoning' || t === 'compacted' || t === 'bcard' || t === 'scard' || t === 'user' || t === 'notice' || t === 'plan' || t === 'step_end') return;
    if (t === 'done') {
      const a = this.agents.get(key);
      if (!a) return;
      if (ev.stopped) { this.agents.delete(key); this.onChange(); return; }
      if (a.status !== 'error') {
        a.status = 'done'; a.approval = null; a.endedAt = this.now();
        const what = short((meta && meta.title) || firstLine(a.lastText), 36);
        a.line = what ? 'Done: ' + what : 'Done';
      }
      this._touch(a); return;
    }
    const a = this._get(key, name, threadId);
    if (meta && meta.title) a.title = meta.title;
    if (t === 'queued') { a.status = 'working'; a.line = 'Waiting for a free slot'; a.step = ''; }
    else if (t === 'started') { a.status = 'working'; a.line = 'Starting'; a.step = ''; a.startedAt = this.now(); a.error = ''; a.endedAt = 0; a.said = ''; }
    else if (t === 'status') { a.said = String(ev.text || ''); if (a.status === 'working') { a.step = a.said; a.line = short(a.said, 40); } }
    // what the pill says is what Glim wrote with set_status; until it has, just "Working"
    else if (t === 'step_start') { a.status = 'working'; a.step = a.said || 'Working'; a.line = short(a.step, 40); a.approval = null; }
    else if (t === 'assistant_end') {
      if (ev.text) a.lastText = ev.text;
      // what the pill says is what Glim itself said it is doing (its line before the tool calls)
      if (ev.text && ev.toolCalls > 0) { const l = firstLine(ev.text); if (l) { a.said = l; if (a.status === 'working') { a.step = l; a.line = short(l, 40); } } }
      return;
    }
    else if (t === 'approval') { a.status = 'waiting'; a.approval = { rid: ev.rid, kind: ev.kind, text: ev.text, danger: !!ev.danger, always: ev.alwaysLabel || '' }; a.line = 'Waiting for you'; }
    else if (t === 'ask') { a.status = 'waiting'; a.approval = { rid: ev.id, kind: 'ask', text: ev.question }; a.line = 'Waiting for you'; }
    else if (t === 'login') { a.status = 'waiting'; a.approval = { rid: null, kind: 'login', text: 'Sign in in the browser window, then click Done.' }; a.line = 'Waiting for you: sign in'; }
    else if (t === 'resumed') { a.status = 'working'; a.approval = null; a.line = short(a.step, 40) || 'Working'; }
    else if (t === 'error') { a.status = 'error'; a.error = String(ev.message || 'Unknown error'); a.line = 'Something went wrong'; a.endedAt = this.now(); }
    else return;
    this._touch(a);
  }

  // Ben has looked at this thread: finished and failed entries for it are "seen"
  markSeen(threadId) {
    let ch = false;
    for (const [k, a] of this.agents) if (a.threadId === threadId && (a.status === 'done' || a.status === 'error')) { this.agents.delete(k); ch = true; }
    if (ch) this.onChange();
  }
  dismiss(key) { if (this.agents.delete(key)) this.onChange(); }
  // drop finished entries after doneMs; returns true if anything went away
  tick() {
    let ch = false;
    for (const [k, a] of this.agents) if (a.status === 'done' && this.now() - a.endedAt > this.doneMs) { this.agents.delete(k); ch = true; }
    if (ch) this.onChange();
    return ch;
  }

  top() {
    let best = null;
    for (const a of this.agents.values()) if (!best || PRIORITY[a.status] > PRIORITY[best.status] || (PRIORITY[a.status] === PRIORITY[best.status] && a.at > best.at)) best = a;
    return best;
  }
  // status for the top-bar Glim / dock badge: 'idle' when nothing is going on
  status() { const t = this.top(); return t ? t.status : this.callSince ? 'call' : this.sleep ? 'sleeping' : 'idle'; }
  view() {
    const top = this.top();
    const now = this.now();
    if (!top && this.sleep) {
      const sl = this.sleep;
      return { visible: true, status: 'sleeping', mood: 'sleepy', line: sl.line, top: { key: 'sleep', name: 'Glim', threadId: null, status: 'sleeping', step: sl.detail || '', line: sl.line, error: '', approval: null, title: '', elapsedMs: Math.max(0, now - sl.since) }, others: [], now };
    }
    if (!top && this.callSince) {
      const secs = Math.max(0, Math.floor((now - this.callSince) / 1000)), line = 'On a call · ' + Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0');
      return { visible: true, status: 'call', mood: 'idle', line, top: { key: 'call', name: 'Glim', threadId: null, status: 'call', step: 'Talking hands-free', line, error: '', approval: null, title: '', elapsedMs: secs * 1000 }, others: [], now };
    }
    if (!top) return { visible: false, status: 'idle', mood: 'idle', line: '', top: null, others: [] };
    const pack = (a) => ({ key: a.key, name: a.name, threadId: a.threadId, status: a.status, step: a.step, line: a.line, error: a.error, approval: a.approval, title: a.title, elapsedMs: Math.max(0, (a.endedAt || now) - a.startedAt) });
    return { visible: true, status: top.status, mood: MOOD[top.status], line: top.line, top: pack(top), others: [...this.agents.values()].filter((a) => a !== top).sort((x, y) => PRIORITY[y.status] - PRIORITY[x.status]).slice(0, 3).map((a) => ({ key: a.key, name: a.name, status: a.status, line: a.line })), now };
  }
}

module.exports = { PillState, firstLine };
