'use strict';
// Always-on Premonition, part 1: which inputs ("senses") Glim may use, and the persistent state it keeps between runs.
// Pure Node, no Electron: the samplers are injected, so the tests drive everything with fakes (no helper, no Python, no network).
//
// Privacy rules enforced here, in code:
//   - every sense is OFF until Ben turns it on (userData/senses.json); a sense that is off is never sampled
//   - only TEXT is kept: no screenshot or audio is ever written by this module or handed to it (samplers return strings)
//   - an observation that looks private (passwords, keychain, banking/sign-in screens, codes, keys) is dropped before storage
const fs = require('fs');
const path = require('path');
const { SENSITIVE } = require('./agent');
const { looksSecret } = require('./memory');
const { timeOf } = require('./timesense');

const SENSES = [
  { id: 'screen', label: 'Screen', help: 'Reads the words on your screen every so often. Only the words are kept, never a picture.', perm: 'screenRecording' },
  { id: 'windows', label: 'Open windows', help: 'Which apps and windows are open, their titles, and the text inside the front one.', perm: 'accessibility' },
  { id: 'hearing', label: 'Hearing', help: 'Listens through the microphone and turns speech into words on this Mac. Nothing leaves the Mac; no audio is saved.', perm: 'microphone' },
  { id: 'chats', label: 'Chats', help: 'What you and Glim say in chat.', perm: null },
  { id: 'web', label: 'Web reading', help: 'What Glim reads on the web while learning.', perm: null }
];
const IDS = SENSES.map((s) => s.id);
const FILE = 'senses.json';
const STATE_FILE = 'alwayson-state.json';
const MAX_OBS = 40, MAX_TEXT = 600;

// passwords and banking: the agent's SENSITIVE list, memory's secret detector, and the screens below
const PRIVATE = /\bpass(?:word|code|phrase)s?\b|\bkeychain\b|\b1password\b|\bbitwarden\b|\blastpass\b|\b(?:online|mobile)\s+banking\b|\bbank(?:ing)?\s+(?:log\s?in|sign[\s-]?in|account)\b|\b(?:chase|wells\s+fargo|bank\s+of\s+america|citi(?:bank)?|capital\s+one|paypal|venmo)\b[\s\S]{0,80}\b(?:log\s?in|sign[\s-]?in|account|balance)\b|\b(?:routing|account)\s+number\b|\bcard\s+number\b|\bcvv\b|\bsocial\s+security\b|\bssn\b/i;
function isPrivate(text) {
  const t = String(text || '');
  return PRIVATE.test(t) || SENSITIVE.test(t) || looksSecret(t);
}

const atomicWrite = (file, obj) => { const tmp = file + '.' + process.pid + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(obj, null, 2)); fs.renameSync(tmp, file); };
const readJson = (file) => { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return null; } };

// ---- consent -------------------------------------------------------------------------------------------
// { senses: {screen: false, ...}, remember: bool, decidedAt: ms, on: bool (the global always-on switch) }
function defaults() { const s = {}; for (const id of IDS) s[id] = false; return { senses: s, remember: false, decidedAt: 0, on: true }; }
function normalize(c) {
  const d = defaults();
  if (!c || typeof c !== 'object') return d;
  for (const id of IDS) d.senses[id] = !!(c.senses && c.senses[id] === true);
  d.remember = c.remember === true; d.decidedAt = Number(c.decidedAt) || 0; d.on = c.on !== false;
  return d;
}
function loadConsent(dir) { return normalize(readJson(path.join(dir, FILE))); }
function saveConsent(dir, c) { const n = normalize(c); fs.mkdirSync(dir, { recursive: true }); atomicWrite(path.join(dir, FILE), n); return n; }
// The card shows at every start until Ben ticks "Remember my choice".
const needsConsent = (c) => !c || !c.remember || !c.decidedAt;
// Which macOS permissions the chosen senses need and are missing (perm: {accessibility, screenRecording, microphone} booleans).
function missingPerms(c, perm) {
  const out = [];
  for (const s of SENSES) if (c.senses[s.id] && s.perm && perm && perm[s.perm] === false) out.push({ sense: s.id, label: s.label, perm: s.perm });
  return out;
}

// ---- persistent state ----------------------------------------------------------------------------------
// userData/alwayson-state.json: { inbox: [{t, sense, text}], focus: {kind, topic, since} | null, lastSpokeAt, lastTickAt, seen: {sense: lastText} }
class AlwaysOnState {
  constructor(dir, o) {
    this.file = path.join(dir, STATE_FILE); this.dir = dir; this.o = o || {};
    this.now = this.o.now || Date.now; this.max = this.o.max || MAX_OBS;
    const j = readJson(this.file) || {};
    // feeling time: every record carries t (ms). Older files may lack it: such rows load with t = null ("time unknown"), never a crash
    const stamp = (x) => ({ ...x, t: timeOf(x) });
    this.inbox = Array.isArray(j.inbox) ? j.inbox.filter((x) => x && IDS.includes(x.sense) && typeof x.text === 'string').slice(-this.max).map(stamp) : [];
    this.focus = j.focus && typeof j.focus.topic === 'string' ? j.focus : null;
    this.lastSpokeAt = Number(j.lastSpokeAt) || 0;
    this.lastTickAt = Number(j.lastTickAt) || 0;
    this.cursor = Number(j.cursor) || 0;
    // always-on v2: surprising moments (the guesser's big surprises, quiz misses), urges, wonder list, and an activity log
    this.surprises = Array.isArray(j.surprises) ? j.surprises.filter((x) => x && typeof x === 'object').slice(-100).map(stamp) : [];
    this.urges = j.urges && typeof j.urges === 'object' ? j.urges : null;
    this.wonder = Array.isArray(j.wonder) ? j.wonder.filter((x) => x && typeof x.text === 'string').slice(-50).map(stamp) : [];
    this.activity = Array.isArray(j.activity) ? j.activity.filter((x) => x && typeof x === 'object').slice(-400).map(stamp) : [];   // inbox entries with t > cursor have not been shown to the model yet
    this.dropped = 0;
  }
  save() { try { fs.mkdirSync(this.dir, { recursive: true }); atomicWrite(this.file, { inbox: this.inbox, focus: this.focus, lastSpokeAt: this.lastSpokeAt, lastTickAt: this.lastTickAt, cursor: this.cursor, surprises: this.surprises, urges: this.urges, wonder: this.wonder, activity: this.activity }); return true; } catch (e) { return false; } }
  // -> the stored entry, or null when it was empty, private, or the same as the last one from that sense
  add(sense, text) {
    if (!IDS.includes(sense)) return null;
    let t = String(text || '').replace(/\s+/g, ' ').trim();
    if (!t) return null;
    if (isPrivate(t)) { this.dropped++; return null; }   // checked on the full text, before clipping
    if (t.length > MAX_TEXT) t = t.slice(0, MAX_TEXT - 1) + '…';
    const last = [...this.inbox].reverse().find((x) => x.sense === sense);
    if (last && last.text === t) return null;
    let at = this.now(); const lastT = this.inbox.length ? this.inbox[this.inbox.length - 1].t : null; if (lastT && at <= lastT) at = lastT + 1;
    const e = { t: at, sense, text: t };
    this.inbox.push(e);
    if (this.inbox.length > this.max) this.inbox.splice(0, this.inbox.length - this.max);
    this.save();
    if (this.o.onAdd) { try { this.o.onAdd(e); } catch (err) { /* listeners (guesser, stuck detector) never break storage */ } }
    return e;
  }
  // a surprising moment, filed as words only: {t, stream, what, kl}. Private-looking text is dropped like any observation.
  addSurprise(o) {
    const what = String((o && o.what) || '').replace(/\s+/g, ' ').trim().slice(0, 300);
    if (!what || isPrivate(what)) return null;
    const e = { t: this.now(), stream: String(o.stream || ''), what, kl: Math.round((Number(o.kl) || 0) * 1000) / 1000 };
    this.surprises.push(e); if (this.surprises.length > 100) this.surprises.shift();
    this.save(); return e;
  }
  addWonder(text, why) {
    const t = String(text || '').replace(/\s+/g, ' ').trim().slice(0, 200);
    if (!t || isPrivate(t) || this.wonder.some((w) => w.text.toLowerCase() === t.toLowerCase())) return null;
    const e = { t: this.now(), text: t, why: String(why || '').slice(0, 120) };
    this.wonder.push(e); if (this.wonder.length > 50) this.wonder.shift();
    this.save(); return e;
  }
  // the diary's raw material: {t, kind, ...} (kept 400)
  logActivity(kind, o) { this.activity.push({ t: this.now(), kind, ...(o || {}) }); if (this.activity.length > 400) this.activity.splice(0, this.activity.length - 400); this.save(); }
  fresh() { return this.inbox.filter((x) => x.t > this.cursor); }
  markRead() { if (this.inbox.length) this.cursor = this.inbox[this.inbox.length - 1].t; this.save(); }
  setFocus(topic, kind) { this.focus = topic ? { kind: kind || 'learn', topic: String(topic).slice(0, 200), since: this.now() } : null; this.save(); }
  spoke() { this.lastSpokeAt = this.now(); this.save(); }
  summary() {
    const f = this.focus ? 'Current focus: ' + this.focus.kind + ' "' + this.focus.topic + '".' : 'No current focus.';
    const ago = this.lastSpokeAt ? Math.round((this.now() - this.lastSpokeAt) / 60000) + ' min ago' : 'never';
    return f + ' Last spoke to Ben unprompted: ' + ago + '.';
  }
}

// ---- sampling ------------------------------------------------------------------------------------------
// samplers: { screen: async () => text, windows: async () => text } (both return '' / throw on failure).
// Hearing, chats and web are pushed in by their owners through push(); push() of a disabled sense is ignored.
class Senses {
  constructor(o) {
    this.o = o; this.consent = o.consent || defaults(); this.state = o.state;
    this.now = o.now || Date.now; this.minGap = o.minGapMs || 20000;
    this.lastAt = {}; this.calls = { screen: 0, windows: 0 }; this.busy = {};
  }
  setConsent(c) { this.consent = normalize(c); }
  enabled(id) { return !!(this.consent.on && this.consent.senses[id]); }
  anyEnabled() { return this.consent.on && IDS.some((id) => this.consent.senses[id]); }
  // poll the two sampled senses that are on and due; returns the new (stored) entries
  async sample() {
    const out = [];
    for (const id of ['screen', 'windows']) {
      if (!this.enabled(id) || this.busy[id]) continue;   // off = never sampled
      const fn = this.o.samplers && this.o.samplers[id];
      if (!fn) continue;
      const now = this.now();
      if (this.lastAt[id] && now - this.lastAt[id] < this.minGap) continue;
      this.lastAt[id] = now; this.calls[id]++; this.busy[id] = true;
      let text = '';
      try { text = await fn(); } catch (e) { text = ''; } finally { this.busy[id] = false; }
      if (typeof text !== 'string') text = '';   // a sampler must hand back words only; anything else is ignored
      const e = this.state.add(id, text); if (e) out.push(e);
    }
    return out;
  }
  push(id, text) { if (!this.enabled(id)) return null; return this.state.add(id, text); }
}

// `deskhelper windows` + `deskhelper look` JSON -> one short line of words (no ids, no coordinates)
function windowsText(w, look) {
  const parts = [];
  if (w && !w.error) {
    if (w.front) parts.push('Front app: ' + w.front + '.');
    const list = (w.windows || []).map((x) => x.app + (x.title ? ' — ' + x.title : '')).filter((x, i, a) => a.indexOf(x) === i).slice(0, 15);
    if (list.length) parts.push('Open: ' + list.join('; ') + '.');
  }
  if (look && !look.error) {
    const words = (look.elements || []).map((e) => [e.title, e.value].filter(Boolean).join(': ')).filter((x) => x && x.length > 1).slice(0, 40);
    if (words.length) parts.push('In ' + (look.app || 'the front app') + ': ' + words.join(' | '));
  }
  return parts.join(' ');
}

module.exports = { windowsText, SENSES, IDS, FILE, STATE_FILE, MAX_OBS, MAX_TEXT, PRIVATE, isPrivate, defaults, normalize, loadConsent, saveConsent, needsConsent, missingPerms, AlwaysOnState, Senses };
