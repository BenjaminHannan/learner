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
const TS = require('./timesense');

const BASE_MS = 60000, MAX_MS = 300000, SAY_GAP_MS = 20 * 60000;
// Nov 4: v1 hard-coded 'lfm3-fast'. On Ben's Mac the 8090 gateway does not know that id and routed it to Nanbeige WITH thinking
// on, unlike chat. The loop now asks exactly what chat's default (Fast) pill asks: the same gateway URL and the same model id, so
// it reaches the same Nanbeige4.2-3B with its native two loops (no extra loops), thinking off.
const chatModel = (s) => String((s && (s.modelFast || s.model)) || 'default');
const REMINDER = /\b(?:remind(?:er)?|deadline|due|overdue|appointment|meeting|exam|quiz|test|class|starts?|begins?|leave|late|tonight|tomorrow|today|in \d+ ?(?:min|minutes|hours?))\b/i;

// Speak filter (SWITCH-ON 2026-11-05, Ben: "Glim should decide, but trained to not speak up unless something is important"): the brain
// marks each moment with "important"; a say goes out only when that is not "none" (missing or unknown = "none" = quiet). Every limit
// below still sits on top of it. Each decision is logged (o.onDecision) so sleep can train Glim's own decision; nothing learns online.
const IMPORTANT = ['none', 'urgent', 'stuck', 'deadline', 'asked'];
const SYSTEM = 'You are the quiet background attention of Glim, a personal assistant on Ben\'s Mac. You see short notes about what is on his screen, what he said, and what you read. '
  + 'Most of the time you do nothing. Speak only when the moment is important for Ben right now. Important means one of: "urgent" (something will go wrong very soon unless he acts, e.g. battery about to die, unsaved work about to be lost), '
  + '"stuck" (he keeps hitting the same error or problem), "deadline" (something is due or starts soon), "asked" (he asked to be told about exactly this). '
  + 'Everything else is "none": ordinary work, browsing, videos, chats, what he is focused on, your own learning, patterns you noticed. With "none", say must be null. '
  + 'Reply with ONE JSON object and nothing else: {"important": "none" | "urgent" | "stuck" | "deadline" | "asked", "say": string or null, "note": string or null, "learn": string or null, "urgent": true or false, "why": string}. '
  + '"say" is one or two short sentences to Ben. "note" is one true fact worth remembering. "learn" is a topic worth studying on the web that would help Ben. "why" is a few words.';

// feeling time (Task B): a clock line, "(N min ago)" on each observation, and the recalled memories + patterns
// (extra = {now, recall: [lines], patterns: [lines], likely}); each list is capped so the prompt stays small.
// Track E1 (prefix reuse): the same lines as before, ordered stable -> changing, so consecutive ticks share the longest prompt
// prefix and the model server's prompt cache skips re-reading it: system, the focus sentence, patterns, memories, the new
// observations, and last the parts that change every minute (when Glim last spoke, the clock, the usual-activity guess).
// buildMessagesV1 is the old order (kept for the equivalence test and as a fallback).
function splitSummary(summary) {
  const s = String(summary || ''); const i = s.indexOf(' Last spoke to Ben');
  return i < 0 ? { stable: s, moving: '' } : { stable: s.slice(0, i), moving: s.slice(i + 1) };
}
function promptParts(fresh, extra) {
  const x = extra || {}, now = x.now || Date.now();
  return {
    now: 'Now: ' + TS.clockWords(now) + '.' + (x.likely ? ' ' + String(x.likely).slice(0, 80) : ''),
    lines: fresh.slice(-12).map((o) => '- [' + o.sense + ', ' + (TS.validT(o.t) ? TS.hhmm(o.t) : 'time unknown') + '] ' + o.text.slice(0, 400) + (TS.validT(o.t) ? ' (' + TS.ago(o.t, now) + ')' : '')),
    rec: (x.recall || []).slice(0, 5).map((l) => '- ' + String(l).slice(0, 180)),
    pat: (x.patterns || []).slice(0, 2).map((l) => '- ' + String(l).slice(0, 240))
  };
}
function buildMessagesV1(fresh, summary, extra) {
  const { now, lines, rec, pat } = promptParts(fresh, extra);
  return [
    { role: 'system', content: SYSTEM },
    { role: 'user', content: now + '\n' + summary + '\nNew observations:\n' + lines.join('\n')
      + (rec.length ? '\nRelated memories (data):\n' + rec.join('\n') : '') + (pat.length ? '\nPatterns seen before (data):\n' + pat.join('\n') : '') + '\nAnswer with the JSON object only.' }
  ];
}
function buildMessages(fresh, summary, extra) {
  const { now, lines, rec, pat } = promptParts(fresh, extra);
  const sm = splitSummary(summary);
  return [
    { role: 'system', content: SYSTEM },
    { role: 'user', content: sm.stable + (pat.length ? '\nPatterns seen before (data):\n' + pat.join('\n') : '') + (rec.length ? '\nRelated memories (data):\n' + rec.join('\n') : '')
      + '\nNew observations:\n' + lines.join('\n') + (sm.moving ? '\n' + sm.moving : '') + '\n' + now + '\nAnswer with the JSON object only.' }
  ];
}

// Speak filter v2 (SWITCH-ON 2026-11-05, MARKS A-v2): Glim's "important" counts only when the tick's observations back it with a signal
// the code can check; otherwise the moment is "none" (quiet). v1 let the brain call a chat ABOUT deadlines a deadline (5/20 replayed ticks).
const EVIDENCE = {
  deadline: /\b(?:due|starts?|starting|begins?|expires?|closes?|ends?|leaves?|departs?|meeting|exam|quiz|test|class|appointment)\b[^.!?\n]{0,50}?\b(?:(?:at|by) \d{1,2}(?::\d{2})?\s?(?:am|pm)?|\d{1,2}:\d{2}\s?(?:am|pm)?|\d{1,2}\s?(?:am|pm)|in \d+\s?(?:min(?:ute)?s?|hours?|h)\b|today|tonight|tomorrow|now)\b|\bin \d+\s?min(?:ute)?s?\b/i,
  urgent: /\bbattery\b[^.!?\n]{0,30}\b\d{1,2}\s?%|\blow (?:battery|power)\b|\bwill (?:sleep|shut ?down|restart)\b|\bsession (?:expires|expired|is expiring|ending)\b|\bunsaved (?:work|changes)\b|\b(?:lose|lost) (?:your )?(?:work|changes)\b|\bdisk (?:is )?(?:almost )?full\b|\bout of (?:disk )?(?:space|storage)\b|\brestart(?:ing)? in \d+/i,
  asked: /\b(?:tell|let) me (?:know )?(?:when|if|once|as soon as)\b|\bremind me\b|\b(?:ping|notify|alert) me\b/i
};
const benLine = (o) => o.sense === 'hearing' || (o.sense === 'chats' && /^Ben (?:wrote|said)\b/.test(o.text)) || /\bBen said\b/.test(o.text);
// fresh: the tick's observations; sig: {stuck: bool} from main's stuck detector. -> true when the moment really is what Glim says
function evidenceFor(important, fresh, sig) {
  const obs = fresh || [];
  if (important === 'stuck') {
    if (sig && sig.stuck) return true;
    const { Stuck } = require('./speakometer'); let t = 0; const st = new Stuck({ now: () => t });
    for (const o of obs) { t += 1000; st.observe(o.sense, o.text); }
    return !!st.error();
  }
  if (important === 'asked') return obs.some((o) => benLine(o) && EVIDENCE.asked.test(o.text));
  const re = EVIDENCE[important]; if (!re) return false;
  return obs.some((o) => o.sense !== 'periphery' && re.test(o.text));
}

// -> {say, note, learn, urgent, why} or null (anything else: skip the tick)
function parseDecision(text) {
  let s = String(text || '').replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  s = s.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  let j; try { j = JSON.parse(s.slice(a, b + 1)); } catch (e) { return null; }
  if (!j || typeof j !== 'object' || Array.isArray(j)) return null;
  const NOSAY = /^(?:null|none|nothing\b.*|n\/a|no|-+)\.?$/i;   // v2: "say": "null" / "None — ..." / "Nothing urgent ..." = no say
  const str = (v) => (v === null || v === undefined ? null : typeof v === 'string' ? (v.trim() || null) : undefined);
  const imp = typeof j.important === 'string' ? j.important.trim().toLowerCase() : 'none';
  const out = { say: str(j.say), note: str(j.note), learn: str(j.learn), urgent: j.urgent === true, important: IMPORTANT.includes(imp) ? imp : 'none', why: typeof j.why === 'string' ? j.why.slice(0, 200) : '' };
  if (out.say === undefined || out.note === undefined || out.learn === undefined) return null;
  if (out.say && (NOSAY.test(out.say) || /^none\s*[—-]/i.test(out.say))) out.say = null;
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
    // E1: with change-only intake on, the senses set a shorter pace (src/senses.js sampleEveryMs: 5 s cheap look, OCR on change)
    const every = () => this.o.sampleMs || (this.senses && this.senses.sampleEveryMs ? this.senses.sampleEveryMs() : 20000);
    const loop = () => { this.sampleTimer = this.setTimer(() => { this.sampleNow().finally(() => { if (this.running) loop(); }); }, every()); };
    loop();
  }
  async sampleNow() {
    const g = this.gate();
    if (g === 'off' || g === 'pressure' || g === 'night') return [];
    try { return await this.senses.sample(); } catch (e) { return []; }
  }
  stop() { this.running = false; if (this.timer) this.clearTimer(this.timer); if (this.sampleTimer) this.clearTimer(this.sampleTimer); this.timer = this.sampleTimer = null; this.cancel('stopped'); }
  schedule(ms) { if (!this.running) return; if (this.timer) this.clearTimer(this.timer); this.timer = this.setTimer(() => { this.timer = null; this.tick().catch((e) => this.log('alwayson tick error', e)).finally(() => this.schedule(this.delay)); }, ms); }
  // v2: a big surprise wakes a tick early (it still passes every gate; a tick in flight is left alone)
  wake() { if (!this.running || this.inTick) return false; this.delay = this.baseMs; this.schedule(0); return true; }
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

  // every brain decision, with what happened to it (sleep trains Glim's own speak decision from this log; logging only)
  decided(d, outcome, fresh) { if (this.o.onDecision) { try { this.o.onDecision({ important: d.important, claimed: d.claimed || null, say: d.say, urgent: d.urgent, why: d.why, outcome, senses: [...new Set((fresh || []).map((o) => o.sense))] }); } catch (e) { /* logging only */ } } }
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
    if (!fresh.length) { this.delay = Math.min(this.maxMs, this.delay * 2); if (this.o.onIdle) { try { this.o.onIdle({ quiet: true }); } catch (e) { this.log('alwayson: idle hook failed', e); } } return this.result('quiet'); }
    this.delay = this.baseMs;
    why = this.gate(); if (why) return this.result(why);   // sampling took a moment: check again before using the model
    const ctl = this.ctl = new AbortController();
    let text;
    this.stats.asked++;
    let extra = { now: this.now() };
    if (this.o.context) { try { extra = { ...extra, ...(this.o.context(fresh) || {}) }; } catch (e) { this.log('alwayson: context failed', e); } }
    // lead 2026-11-04: E1's stable-first order missed its registered mark (prefix share 0.47 < 0.80), so the live loop keeps the old
    // order unless o.stableFirst is set (untested on the real model: the clock line moves to the end)
    const build = this.o.stableFirst ? buildMessages : buildMessagesV1;
    try { text = await this.o.ask(build(fresh, this.state.summary(), extra), ctl.signal); }
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
      // the speak filter: Glim's own decision first (quiet unless important), then the code limits, then the speak-o-meter (it can hold, never force)
      let outcome;
      if (d.important !== 'none' && !this.o.legacySpeak && this.o.evidence !== false && !evidenceFor(d.important, fresh, this.o.signals ? this.o.signals() : null)) { d.claimed = d.important; d.important = 'none'; }
      if (d.important === 'none' && !this.o.legacySpeak) { this.stats.quiet = (this.stats.quiet || 0) + 1; done.quiet = true; outcome = 'quiet'; }
      else {
        const meter = this.sayAllowed(d) ? (this.o.speakGate ? this.o.speakGate({ ...d, urgent: d.urgent || d.important !== 'none' }) : { speak: true }) : null;
        if (meter && meter.speak) { d.features = meter.x || null; d.p = meter.p; this.state.spoke(); this.stats.said++; done.said = true; outcome = 'said'; try { dl.say && dl.say(d.say, d); } catch (e) { this.log('alwayson: say failed', e); } }
        else if (meter) { this.stats.meterHeld = (this.stats.meterHeld || 0) + 1; done.meterHeld = true; outcome = meter.defer ? 'waited' : 'held-meter'; this.log('alwayson: say held by the speak-o-meter (p=' + (meter.p != null ? meter.p.toFixed(2) : '?') + '):', d.say.slice(0, 80)); }
        else { this.stats.held++; outcome = 'held-limit'; this.log('alwayson: say held by the 20-minute limit:', d.say.slice(0, 80)); }
      }
      this.decided(d, outcome, fresh);
    } else this.decided(d, d.say ? 'private' : 'nothing', fresh);
    if (d.note && !isPrivate(d.note)) { this.stats.notes++; done.noted = true; try { dl.note && dl.note(d.note, d); } catch (e) { this.log('alwayson: note failed', e); } }
    if (d.learn && !isPrivate(d.learn)) {
      const cur = this.state.focus && this.state.focus.topic;
      if (!cur || cur.toLowerCase() !== d.learn.toLowerCase()) {
        let ok = true;
        try { ok = dl.learn ? dl.learn(d.learn, d) !== false : false; } catch (e) { ok = false; this.log('alwayson: learn failed', e); }
        if (ok) { this.state.setFocus(d.learn, 'learn'); this.stats.learns++; done.learned = true; }
      }
    }
    if (!done.said && this.o.onIdle) { try { this.o.onIdle(done); } catch (e) { this.log('alwayson: idle hook failed', e); } }   // Ben's rule: nothing to say -> go study
    return this.result('done', done);
  }
}

module.exports = { AlwaysOn, IMPORTANT, EVIDENCE, evidenceFor, parseDecision, buildMessages, buildMessagesV1, splitSummary, macPressure, REMINDER, SYSTEM, chatModel, BASE_MS, MAX_MS, SAY_GAP_MS };
