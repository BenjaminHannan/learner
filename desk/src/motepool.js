'use strict';
// Always-on v2, phase 4c: bored-mode Motes. When Glim is bored it sends a small batch of thinking/learning Motes through the SAME
// local model as chat. How many may run is the memory gauge's budget (src/memgauge.js); Ben chatting or 🔴 stops every one of them
// at once: stopAll() aborts the request in flight and clears the queue, and every tick() re-checks the gate first.
//
// Batching, honestly: Ben's local server (stock mlx_lm on :8090 behind the Premonition gateway) serves ONE request at a time, so
// the batch is sent back-to-back, one request after the other, re-checking the gate between them. If an `askBatch` is supplied (a
// server that takes many prompts at once) the whole batch goes in one call instead.
//
// A Mote's answer is strict JSON {"claims": [string], "question": string|null}: claims become `maybe` notes for the truth check
// (src/truthnotes.js), the question goes on the wonder list. Pure Node: ask / gate / prompt / onResult are injected.

function parseThought(text) {
  let s = String(text || '').replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  let j; try { j = JSON.parse(s.slice(a, b + 1)); } catch (e) { return null; }
  if (!j || typeof j !== 'object') return null;
  const claims = (Array.isArray(j.claims) ? j.claims : []).filter((c) => typeof c === 'string' && c.trim()).map((c) => c.trim().slice(0, 300)).slice(0, 5);
  const question = typeof j.question === 'string' && j.question.trim() ? j.question.trim().slice(0, 200) : null;
  return { claims, question };
}

let seq = 0;
class MotePool {
  // o: { ask(messages, signal) -> text, askBatch(listOfMessages, signal) -> [text] (optional), gate() -> {budget, why},
  //      prompt(job) -> messages, onResult(job, parsed|null, text), onChange(), log, now }
  constructor(o) {
    this.o = o; this.log = o.log || (() => {}); this.now = o.now || Date.now;
    this.queue = []; this.current = null; this.ctl = null; this.batchSize = 0;
    this.stats = { started: 0, done: 0, stopped: 0, failed: 0, batches: 0 };
    this.lastStop = null;
  }
  // Motes alive now (queued + running): what the ear shows as "N Motes"
  count() { return this.queue.length + (this.current ? 1 : 0); }
  thinking() { return this.current ? this.current.topic : null; }
  changed() { try { this.o.onChange && this.o.onChange(); } catch (e) { /* UI only */ } }
  // queue a batch of {kind, topic} (trimmed to the gate's budget now)
  startBatch(topics) {
    const g = this.o.gate();
    if (!g || g.budget <= 0) { this.lastStop = g ? g.why : 'off'; return 0; }
    const room = Math.max(0, g.budget - this.count());
    const add = topics.slice(0, room).map((t) => ({ id: 'mote-' + (++seq), kind: t.kind, topic: t.topic, at: this.now() }));
    if (!add.length) return 0;
    this.queue.push(...add); this.stats.batches++; this.batchSize = this.count();
    this.changed();
    this.pump();
    return add.length;
  }
  // stop everything now (Ben chatting, 🔴, sleep, off)
  stopAll(why) {
    const n = this.count();
    if (!n) return 0;
    this.queue = [];
    if (this.ctl) { try { this.ctl.abort(); } catch (e) { /* gone */ } }
    this.current = null; this.ctl = null;   // gone now, not when the aborted request finally rejects
    this.stats.stopped += n; this.lastStop = why || 'stopped';
    this.log('motes: stopped ' + n + ' (' + (why || 'stopped') + ')');
    this.changed();
    return n;
  }
  // the gate check; main calls this every second. Over budget -> trim the queue; budget 0 -> stop all.
  tick() {
    if (!this.count()) return { running: 0 };
    const g = this.o.gate();
    if (!g || g.budget <= 0) { this.stopAll(g ? g.why : 'off'); return { running: 0, stopped: true }; }
    while (this.count() > g.budget && this.queue.length) { this.queue.pop(); this.stats.stopped++; }
    if (!this.current) this.pump();
    return { running: this.count() };
  }
  async pump() {
    if (this.current || !this.queue.length) return;
    if (this.o.askBatch && this.queue.length > 1) return this.runBatch();
    const job = this.current = this.queue.shift();
    const ctl = this.ctl = new AbortController();
    this.stats.started++; this.changed();
    let text = null;
    try {
      const g = this.o.gate();
      if (!g || g.budget <= 0) throw Object.assign(new Error('gate'), { gate: true });
      text = await this.o.ask(this.o.prompt(job), ctl.signal);
    } catch (e) {
      if (!ctl.signal.aborted && !e.gate) { this.stats.failed++; this.log('motes: ask failed', String(e && e.message || e)); }
    }
    const stopped = ctl.signal.aborted;
    if (this.current === job) this.current = null; if (this.ctl === ctl) this.ctl = null;
    if (!stopped && text != null) {
      this.stats.done++;
      try { this.o.onResult && this.o.onResult(job, parseThought(text), text); } catch (e) { this.log('motes: result failed', e); }
    }
    this.changed();
    if (!stopped && this.queue.length) { const g = this.o.gate(); if (g && g.budget > 0) return this.pump(); this.stopAll(g ? g.why : 'off'); }
  }
  async runBatch() {
    const jobs = this.queue.splice(0); const ctl = this.ctl = new AbortController();
    this.current = jobs[0]; this.stats.started += jobs.length; this.changed();
    let texts = null;
    try { texts = await this.o.askBatch(jobs.map((j) => this.o.prompt(j)), ctl.signal); } catch (e) { if (!ctl.signal.aborted) this.stats.failed += jobs.length; }
    const stopped = ctl.signal.aborted; if (this.current === jobs[0]) this.current = null; if (this.ctl === ctl) this.ctl = null;
    if (!stopped && Array.isArray(texts)) jobs.forEach((j, i) => { this.stats.done++; try { this.o.onResult(j, parseThought(texts[i]), texts[i]); } catch (e) { /* next */ } });
    this.changed();
  }
}

module.exports = { MotePool, parseThought };
