'use strict';
// Always-on Premonition, part 2: the loop. Every tick it gathers new observations from the senses that are on, shows them to the
// local model with a short prompt, and acts on a strict JSON answer {"say", "note", "learn", "why"}.
// The rules that keep it polite live HERE, in code, not in the prompt:
//   - off (global switch, or no sense on) = no tick does anything
//   - Ben first: no tick while he types, a chat reply runs, a call or dictation is on; a tick in flight is cancelled when he starts
//   - memory pressure >= 2 (macOS warning or critical) = pause; the night sleep window and sleep itself = pause (quiet hours)
//   - at most one unprompted "say" per 20 minutes, unless it is marked urgent AND reads like a reminder or deadline
//   - an answer that is not the JSON asked for = the tick is skipped and logged; nothing is delivered and nothing throws
// Pure Node: ask / deliver / gates / timers are injected so the tests run with a fake model.
const { execFileSync } = require('child_process');
const { isPrivate } = require('./senses');

const BASE_MS = 60000, MAX_MS = 300000, SAY_GAP_MS = 20 * 60000;
// Nov 4: v1 hard-coded 'lfm3-fast'. On Ben's Mac the 8090 gateway does not know that id and routed it to Nanbeige WITH thinking
// on, unlike chat. The loop now asks exactly what chat's default (Fast) pill asks: the same gateway URL and the same model id, so
// it reaches the same Nanbeige4.2-3B with its native two loops (no extra loops), thinking off.
const chatModel = (s) => String((s && (s.modelFast || s.model)) || 'default');
const REMINDER = /\b(?:remind(?:er)?|deadline|due|overdue|appointment|meeting|exam|quiz|test|class|starts?|begins?|leave|late|tonight|tomorrow|today|in \d+ ?(?:min|minutes|hours?))\b/i;

const SYSTEM = 'You are the quiet background attention of Glim, a personal assistant on Ben\'s Mac. You see short notes about what is on his screen, what he said, and what you read. '
  + 'Most of the time you do nothing. Speak only when it clearly helps him right now (a reminder, a deadline, a real mistake, an answer he is looking for). '
  + 'Reply with ONE JSON object and nothing else: {"say": string or null, "note": string or null, "learn": string or null, "urgent": true or false, "why": string}. '
  + '"say" is one or two short sentences to Ben. "note" is one true fact worth remembering. "learn" is a topic worth studying on the web. "why" is a few words.';

function buildMessages(fresh, summary) {
  const lines = fresh.slice(-12).map((o) => '- [' + o.sense + ', ' + new Date(o.t).toTimeString().slice(0, 5) + '] ' + o.text.slice(0, 400));
  return [
    { role: 'system', content: SYSTEM },
    { role: 'user', content: summary + '\nNew observations:\n' + lines.join('\n') + '\nAnswer with the JSON object only.' }
  ];
}

// -> {say, note, learn, urgent, why} or null (anything else: skip the tick)
function parseDecision(text) {
  let s = String(text || '').replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  s = s.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  let j; try { j = JSON.parse(s.slice(a, b + 1)); } catch (e) { return null; }
  if (!j || typeof j !== 'object' || Array.isArray(j)) return null;
  const str = (v) => (v === null || v === undefined ? null : typeof v === 'string' ? (v.trim() || null) : undefined);
  const out = { say: str(j.say), note: str(j.note), learn: str(j.learn), urgent: j.urgent === true, why: typeof j.why === 'string' ? j.why.slice(0, 200) : '' };
  if (out.say === undefined || out.note === undefined || out.learn === undefined) return null;
  if (!('why' in j)) return null;
  if (out.say) out.say = out.say.slice(0, 400); if (out.note) out.note = out.note.slice(0, 400); if (out.learn) out.learn = out.learn.slice(0, 120);
  return out;
}

// macOS memory pressure: 1 normal, 2 warning, 4 critical (the same sysctl the assistant's watchdog reads). Cached 10 s.
let pCache = { at: 0, v: 1 };
function macPressure(now) {
  now = now || Date.now();
  if (process.platform !== 'darwin') return 1;
  if (now - pCache.at < 10000) return pCache.v;
  let v = 1;
  try { v = parseInt(String(execFileSync('/usr/sbin/sysctl', ['-n', 'kern.memorystatus_vm_pressure_level'], { timeout: 2000 })).trim(), 10) || 1; } catch (e) { v = 1; }
  pCache = { at: now, v };
  return v;
}

class AlwaysOn {
  // o: { senses, state, ask(messages, signal) -> Promise<string>, deliver: {say(text, d), note(text, d), learn(topic, d)},
  //      gates: {busy(), pressure(), night()}, now, setTimer, clearTimer, log, baseMs, maxMs, sayGapMs }
  constructor(o) {
    this.o = o; this.senses = o.senses; this.state = o.state;
    this.now = o.now || Date.now;
    this.setTimer = o.setTimer || ((fn, ms) => { const t = setTimeout(fn, ms); if (t.unref) t.unref(); return t; });
    this.clearTimer = o.clearTimer || clearTimeout;
    this.log = o.log || (() => {});
    this.baseMs = o.baseMs || BASE_MS; this.maxMs = o.maxMs || MAX_MS; this.sayGapMs = o.sayGapMs || SAY_GAP_MS;
    this.delay = this.baseMs; this.timer = null; this.running = false; this.ctl = null; this.inTick = false;
    this.last = { reason: 'not started', at: 0 };
    this.stats = { ticks: 0, asked: 0, said: 0, held: 0, parseFail: 0, notes: 0, learns: 0 };
  }
  enabled() { return !!(this.senses && this.senses.anyEnabled()); }
  start() {
    if (this.running) return; this.running = true; this.schedule(Math.min(this.baseMs, 15000));
    // the senses are read on their own gentle clock (every 20 s, stored only when the words changed); the model only on ticks
    const every = this.o.sampleMs || 20000;
    const loop = () => { this.sampleTimer = this.setTimer(() => { this.sampleNow().finally(() => { if (this.running) loop(); }); }, every); };
    loop();
  }
  async sampleNow() {
    const g = this.gate();
    if (g === 'off' || g === 'pressure' || g === 'night') return [];
    try { return await this.senses.sample(); } catch (e) { return []; }
  }
  stop() { this.running = false; if (this.timer) this.clearTimer(this.timer); if (this.sampleTimer) this.clearTimer(this.sampleTimer); this.timer = this.sampleTimer = null; this.cancel('stopped'); }
  schedule(ms) { if (!this.running) return; if (this.timer) this.clearTimer(this.timer); this.timer = this.setTimer(() => { this.timer = null; this.tick().catch((e) => this.log('alwayson tick error', e)).finally(() => this.schedule(this.delay)); }, ms); }
  cancel(why) { if (this.ctl) { try { this.ctl.abort(); } catch (e) { /* gone */ } this.ctl = null; this.log('alwayson: cancelled (' + why + ')'); } }
  gate() {
    const g = this.o.gates || {};
    if (!this.enabled()) return 'off';
    if (g.busy && g.busy()) return 'busy';
    if (g.pressure && g.pressure() >= 2) return 'pressure';
    if (g.night && g.night()) return 'night';
    return null;
  }
  result(reason, extra) { this.last = { reason, at: this.now(), ...(extra || {}) }; return { ran: reason === 'done', reason, ...(extra || {}) }; }
  statusLine() {
    const r = this.last.reason;
    const words = { off: 'Off.', busy: 'Waiting: you are using the chat.', pressure: 'Paused: the Mac is short on memory.', night: 'Quiet: it is the night sleep window.', quiet: 'Watching; nothing new.', done: 'Watching.', parse: 'Watching (last answer was unreadable, skipped).', 'not started': 'Starting…', error: 'Watching (the model did not answer last time).', cancelled: 'Waiting: you are using the chat.' };
    return 'Always-on: ' + (words[r] || 'Watching.') + (this.stats.said ? ' Spoke up ' + this.stats.said + ' time' + (this.stats.said === 1 ? '' : 's') + ' this session.' : '');
  }
  // may this "say" go out now?
  sayAllowed(d) {
    if (!this.state.lastSpokeAt) return true;
    if (this.now() - this.state.lastSpokeAt >= this.sayGapMs) return true;
    return !!(d.urgent && REMINDER.test(d.say));
  }

  async tick() {
    if (this.inTick) return this.result('busy');
    this.inTick = true;
    try { return await this._tick(); } finally { this.inTick = false; }
  }
  async _tick() {
    this.stats.ticks++;
    let why = this.gate();
    if (why) { if (why !== 'off') this.delay = this.baseMs; return this.result(why); }
    await this.sampleNow();
    const fresh = this.state.fresh();
    if (!fresh.length) { this.delay = Math.min(this.maxMs, this.delay * 2); return this.result('quiet'); }
    this.delay = this.baseMs;
    why = this.gate(); if (why) return this.result(why);   // sampling took a moment: check again before using the model
    const ctl = this.ctl = new AbortController();
    let text;
    this.stats.asked++;
    try { text = await this.o.ask(buildMessages(fresh, this.state.summary()), ctl.signal); }
    catch (e) { this.ctl = null; if (ctl.signal.aborted) return this.result('cancelled'); this.log('alwayson: model error', String(e && e.message || e)); return this.result('error'); }
    this.ctl = null;
    if (ctl.signal.aborted) return this.result('cancelled');
    this.state.markRead();
    const d = parseDecision(text);
    if (!d) { this.stats.parseFail++; this.log('alwayson: unreadable answer, tick skipped:', String(text || '').slice(0, 200)); return this.result('parse'); }
    // Ben may have started typing while the model thought: nothing goes out over him
    why = this.gate(); if (why) return this.result(why, { decision: d });
    const done = { decision: d, said: false, noted: false, learned: false };
    const dl = this.o.deliver || {};
    if (d.say && !isPrivate(d.say)) {
      if (this.sayAllowed(d)) { this.state.spoke(); this.stats.said++; done.said = true; try { dl.say && dl.say(d.say, d); } catch (e) { this.log('alwayson: say failed', e); } }
      else { this.stats.held++; this.log('alwayson: say held by the 20-minute limit:', d.say.slice(0, 80)); }
    }
    if (d.note && !isPrivate(d.note)) { this.stats.notes++; done.noted = true; try { dl.note && dl.note(d.note, d); } catch (e) { this.log('alwayson: note failed', e); } }
    if (d.learn && !isPrivate(d.learn)) {
      const cur = this.state.focus && this.state.focus.topic;
      if (!cur || cur.toLowerCase() !== d.learn.toLowerCase()) {
        let ok = true;
        try { ok = dl.learn ? dl.learn(d.learn, d) !== false : false; } catch (e) { ok = false; this.log('alwayson: learn failed', e); }
        if (ok) { this.state.setFocus(d.learn, 'learn'); this.stats.learns++; done.learned = true; }
      }
    }
    return this.result('done', done);
  }
}

module.exports = { AlwaysOn, parseDecision, buildMessages, macPressure, REMINDER, SYSTEM, chatModel, BASE_MS, MAX_MS, SAY_GAP_MS };
