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
const MAX_OBS = 40, MAX_TEXT = 600, MAX_TEXT_PERIPHERY = 1000;   // the periphery line holds up to 5 windows x ~150 characters

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
// Ben Nov 4 ("dont have it ask for now, just give it"): no start-up card. An undecided consent starts with EVERY sense on, as if
// Ben pressed Save with all switches on and "Remember my choice" ticked. Settings > Senses still switches each one off; macOS
// still asks for its own permissions. Set ASK_AT_START = true to bring the card back (one line).
const ASK_AT_START = false;
function given(now) { const s = {}; for (const id of IDS) s[id] = true; return normalize({ senses: s, remember: true, decidedAt: now || Date.now(), on: true }); }
// the consent to start with: { consent, granted } (granted = it was undecided and is now the all-on default; main saves it)
function startConsent(c, now, ask) { const a = ask === undefined ? ASK_AT_START : !!ask; return !a && needsConsent(c) ? { consent: given(now), granted: true } : { consent: normalize(c), granted: false }; }
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
    if (!IDS.includes(sense) && sense !== 'periphery') return null;   // the periphery is stored like a sense; the screen switch covers it
    let t = String(text || '').replace(/\s+/g, ' ').trim();
    if (!t) return null;
    if (isPrivate(t)) { this.dropped++; return null; }   // checked on the full text, before clipping
    if (require('./logins').holdsSecret(t)) { this.dropped++; return null; }   // LOGIN1: a saved password never enters the day log
    const cap = sense === 'periphery' ? MAX_TEXT_PERIPHERY : MAX_TEXT;
    if (t.length > cap) t = t.slice(0, cap - 1) + '…';
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
    // Nov 5: was 'Current focus: learn "X"', which the brain read as BEN's focus ("Ben, your current focus is learning X").
    // The topic is Glim's own study pick, so say whose it is.
    const f = this.focus ? "Glim's own " + (this.focus.kind === 'learn' ? 'learning topic' : this.focus.kind + ' topic') + ' (Glim picked it for its own study; Ben is not working on it and did not ask): "' + this.focus.topic + '".' : 'No current focus.';
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
    // E1 change-only intake (o.changeOnly: bool or () => bool, off by default): see sampleChangeOnly()
    this.probeGap = o.probeGapMs || 5000; this.staleMs = o.staleMs || 60000;
    this.co = { lastWin: null, winAtOcr: null, lastOcr: null, rich: false, skipped: 0 };
  }
  setConsent(c) { this.consent = normalize(c); }
  enabled(id) { return !!(this.consent.on && this.consent.senses[id]); }
  anyEnabled() { return this.consent.on && IDS.some((id) => this.consent.senses[id]); }
  changeOnly() { const c = this.o.changeOnly; return !!(typeof c === 'function' ? c() : c); }
  // how often the always-on loop should call sample()
  sampleEveryMs() { return this.changeOnly() ? this.probeGap : this.minGap; }
  // poll the two sampled senses that are on and due; returns the new (stored) entries
  async sample() {
    if (this.changeOnly()) return this.sampleChangeOnly();
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
      if (id === 'screen' && text) this.screenSeen(text);
      if (id === 'windows') this.co.lastWin = text;
    }
    const p = await this.periphery(); if (p) out.push(p);
    return out;
  }
  // The periphery (SWITCH-ON 2026-11-05, Ben: "focus on one screen but still know what's going on with the other screens"): a low-detail
  // look at the windows behind the front one and at other displays (o.samplers.periphery -> {items: [{app, title, text, how, display}]},
  // the helper's `glance`: ~110 characters of fast OCR per window, at most 5). It runs every periMs (3 min), or 30 s after the set of
  // open windows changed. Covered by the screen switch; each private-looking window is dropped on its own, the rest is kept.
  async periphery() {
    const fn = this.o.samplers && this.o.samplers.periphery;
    if (!fn || !this.enabled('screen') || this.busy.periphery) return null;
    const now = this.now(), key = openPart(this.co.lastWin), since = this.lastAt.periphery ? now - this.lastAt.periphery : Infinity;
    const due = since >= (this.o.periMs || 180000) || (key && key !== this.co.periKey && since >= (this.o.periMinMs || 30000));
    if (!due) return null;
    this.lastAt.periphery = now; this.co.periKey = key; this.busy.periphery = true; this.calls.periphery = (this.calls.periphery || 0) + 1;
    let r = null, err = ''; const t0 = Date.now(); try { r = await fn(); } catch (e) { r = null; err = String(e && e.message || e); } finally { this.busy.periphery = false; }
    const items = (r && !r.error && r.items) || [], priv = items.filter((x) => isPrivate([x.app, x.title, x.text].join(' '))).length;
    this.co.periSkipped = (this.co.periSkipped || 0) + priv;
    const text = peripheryText(r), e = text ? this.state.add('periphery', text) : null;
    this.co.periLast = { at: now, windows: items.length, private: priv, withText: items.filter((x) => x.text).length, how: [...new Set(items.map((x) => x.how))].join(','), chars: text.length, stored: !!e, ms: Date.now() - t0, error: err || (r && r.error) || '' };
    try { this.o.log && this.o.log('periphery: ' + JSON.stringify(this.co.periLast)); } catch (e2) { /* log only */ }
    return e;
  }
  push(id, text) { if (!this.enabled(id)) return null; return this.state.add(id, text); }
  // I1 (Glim can see): after each screen read, o.onScreen(screenText, latestWindowsText) may take a look with the eyes (fire and forget;
  // the eyes decide whether they are on and whether the screen is private). A failing listener never breaks sampling.
  screenSeen(text) { const f = this.o.onScreen; if (!f) return; try { const r = f(text, this.co.lastWin); if (r && r.catch) r.catch(() => {}); } catch (e) { /* never breaks sampling */ } }
  async run(id) {
    const fn = this.o.samplers && this.o.samplers[id];
    if (!fn) return null;
    this.lastAt[id] = this.now(); this.calls[id]++; this.busy[id] = true;
    let text = '';
    try { text = await fn(); } catch (e) { text = ''; } finally { this.busy[id] = false; }
    return typeof text === 'string' ? text : '';   // words only
  }
  // E1 change-only intake. The cheap look (the windows sense: app + window titles + the front window's accessibility text, already
  // a sense of its own) runs every probeGap (5 s). The costly look (screen OCR) runs only when
  //   - the cheap look changed since the last OCR (a window/app switch, new text in the front window), or
  //   - it has not run for staleMs (60 s) while the front window has rich accessibility text (>= RICH_CHARS: most text changes show
  //     up there first), or for minGap (20 s, the old pace) when it does not (games, video, canvases: only OCR sees them).
  // With the windows sense off there is no cheap look (a sense that is off is never read): screen OCR keeps the old 20 s pace.
  // What OCR stores is the change: the lines that were not on screen at the last OCR (the full text when most of it is new).
  async sampleChangeOnly() {
    const out = []; const now = this.now();
    let win = null;
    if (this.enabled('windows') && !this.busy.windows && (!this.lastAt.windows || now - this.lastAt.windows >= this.probeGap)) {
      win = await this.run('windows');
      if (win != null) { this.co.lastWin = win; this.co.rich = axChars(win) >= RICH_CHARS; const e = this.state.add('windows', win); if (e) out.push(e); }
    }
    if (this.enabled('screen') && !this.busy.screen) {
      const cheap = this.enabled('windows') && this.co.lastWin != null;
      const since = this.lastAt.screen ? now - this.lastAt.screen : Infinity;
      const changed = cheap && this.co.lastWin !== this.co.winAtOcr;
      const due = since === Infinity || changed || since >= (cheap && this.co.rich ? this.staleMs : this.minGap);
      if (due) {
        const text = await this.run('screen');
        if (text != null) {
          this.co.winAtOcr = this.co.lastWin;
          const d = screenDiff(this.co.lastOcr, text); this.co.lastOcr = text;
          if (text) this.screenSeen(text);
          const e = d ? this.state.add('screen', d) : null; if (e) out.push(e);
        }
      } else this.co.skipped++;
    }
    const p = await this.periphery(); if (p) out.push(p);
    return out;
  }
}
const RICH_CHARS = 80;
// characters of front-window accessibility text in a windowsText() line (the part after "In <app>: ")
function axChars(w) { const t = String(w || ''); const j = t.startsWith('In ') ? 0 : t.indexOf(' In '); if (j < 0) return 0; const i = t.indexOf(': ', j); return i < 0 ? 0 : t.length - i - 2; }
// OCR text -> what changed since the previous OCR: '' when nothing did; the new lines (in screen order) when under half are new;
// else the whole text (a different screen)
function screenDiff(prev, cur) {
  const lines = (t) => String(t || '').split(/\n+/).map((l) => l.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const c = lines(cur); if (!c.length) return '';
  if (prev == null) return c.join('\n');
  const p = new Set(lines(prev)); const added = c.filter((l) => !p.has(l));
  if (!added.length) return '';
  if (added.length * 2 >= c.length) return c.join('\n');
  return 'Changed on screen: ' + added.join(' / ');
}

// the "Open: ..." part of a windows line (which windows are open, front to back): its change wakes the periphery early
function openPart(w) { const m = /Open: ([^]*?)\.(?: In |$)/.exec(String(w || '')); return m ? m[1] : ''; }
// `deskhelper glance` JSON -> one inbox line, labelled as the periphery; private-looking windows are left out one by one
function peripheryText(r) {
  const items = ((r && !r.error && r.items) || []).filter((x) => x && !isPrivate([x.app, x.title, x.text].join(' ')));
  const parts = items.map((x) => (x.app || 'Other display') + (x.title ? ' \u2014 ' + String(x.title).slice(0, 60) : '') + (x.display === 'other' ? ' (other display)' : '') + (x.text ? ': "' + String(x.text).replace(/\s+/g, ' ').slice(0, 150) + '"' : ''));
  return parts.length ? 'Periphery (background windows, low detail; not what Ben is focused on): ' + parts.join(' | ') : '';
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

module.exports = { openPart, peripheryText, screenDiff, axChars, RICH_CHARS, windowsText, SENSES, IDS, FILE, STATE_FILE, MAX_OBS, MAX_TEXT, PRIVATE, isPrivate, defaults, normalize, loadConsent, saveConsent, needsConsent, ASK_AT_START, given, startConsent, missingPerms, AlwaysOnState, Senses };
