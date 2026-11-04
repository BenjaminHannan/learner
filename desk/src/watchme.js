'use strict';
// "Watch me once" (Ben's round-2 idea, 2026-11-04): Ben narrates out loud while he does a task on screen. Glim watches:
//   - the screen at 1-2 fps (the helper's `look` = front app, window title, accessibility elements; plus OCR words),
//   - Ben's speech turned into text (src/stt.js through a Dictation process; the narration is the TEXT ANCHOR),
//   - app / click / key / typing events where the helper can report them (often it can't: then steps are inferred from the frames
//     and the narration).
// Result: a SKILL CARD = a numbered list of steps, each with Ben's words, the tool action that redoes it, and what the screen should
// show afterwards. Next time Glim can redo the skill with its own screen tools, step by step, checking the screen after each step
// (and stopping at the first step that does not check out). Sleep trains on the card text (sleepmlx reads watchme-skills.json).
//
// Pure Node: the samplers, the tools and the clock are injected, so the tests run with a fake screen (no helper, no microphone).
// Privacy: a frame that looks private (passwords, banking, keys: senses.isPrivate) is never stored, as text or as a picture.
// Raw pictures are kept only as EVIDENCE (Ben 2026-11-04): Mac only, at most KEEP_DAYS days, at most CAP_BYTES in total, oldest first out.
const fs = require('fs');
const path = require('path');

const SKILLS_FILE = 'watchme-skills.json';
const CLIPS_DIR = 'watchme-clips';
const KEEP_DAYS = 3;
const CAP_BYTES = 300 * 1024 * 1024;
const MAX_SKILLS = 200, MAX_STEPS = 40, MAX_FRAMES = 3600;
const TOOLS = ['open_app', 'click', 'type', 'key'];

const norm = (s) => String(s == null ? '' : s).toLowerCase().replace(/[^a-z0-9+]+/g, ' ').trim();
const clip = (s, n) => { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
let isPrivateFn = null;
const isPrivate = (t) => { if (!isPrivateFn) isPrivateFn = require('./senses').isPrivate; return isPrivateFn(t); };

// ---- frames ----------------------------------------------------------------------------------------------------------
// A frame: {t (ms), app, title, elements: [{id, role, title, value, frame:[x,y,w,h]}], text (OCR words)}
function frameFromLook(t, look, ocr) {
  const w = (look && look.windows && look.windows[0]) || {};
  return { t, app: String((look && look.app) || ''), title: String(w.title || ''),
    elements: ((look && look.elements) || []).slice(0, 120).map((e) => ({ id: e.id, role: String(e.role || ''), title: String(e.title || ''), value: e.value == null ? '' : String(e.value), frame: Array.isArray(e.frame) ? e.frame.slice(0, 4).map(Number) : null })),
    text: String(ocr || '') };
}
const frameText = (f) => [f.app, f.title, ...(f.elements || []).map((e) => e.title + ' ' + e.value), f.text].join(' ');
const elKey = (e) => (e.role || '') + '|' + norm(e.title);

function elementAt(f, x, y) {
  let best = null, area = Infinity;
  for (const e of (f && f.elements) || []) {
    if (!e.frame || !e.title) continue;
    const [ex, ey, w, h] = e.frame;
    if (x >= ex && x <= ex + w && y >= ey && y <= ey + h && w * h < area) { best = e; area = w * h; }
  }
  return best;
}
const frameAtOrBefore = (frames, t) => { let f = null; for (const x of frames) { if (x.t <= t) f = x; else break; } return f; };

// ---- narration parsing -------------------------------------------------------------------------------------------------
const KEYNAMES = { command: 'cmd', cmd: 'cmd', control: 'ctrl', ctrl: 'ctrl', option: 'alt', alt: 'alt', shift: 'shift' };
const SOLO = /\b(?:press|hit|tap)\s+(enter|return|tab|escape|esc|delete|space)\b/i;
function narratedKey(text) {
  const t = String(text || '');
  const m = t.match(/\b(?:press|hit|tap)\s+((?:(?:command|cmd|control|ctrl|option|alt|shift)[\s+-]*)+)([a-z0-9])\b/i);
  if (m) return m[1].trim().split(/[\s+-]+/).filter(Boolean).map((k) => KEYNAMES[k.toLowerCase()]).concat(m[2].toLowerCase()).join('+');
  const s = t.match(SOLO);
  if (s) return { esc: 'escape', return: 'enter' }[s[1].toLowerCase()] || s[1].toLowerCase();
  return null;
}
// the longest element label in `f` that the narration names after a click verb
function narratedLabel(text, f) {
  const t = ' ' + norm(text) + ' ';
  if (!/\b(click|press|tap|choose|select|hit|pick|open)\b/.test(t)) return null;
  let best = null;
  for (const e of (f && f.elements) || []) {
    const l = norm(e.title);
    if (l.length >= 2 && t.includes(' ' + l + ' ') && (!best || l.length > norm(best.title).length)) best = e;
  }
  return best;
}

// ---- 1. steps from a recording ---------------------------------------------------------------------------------------
// rec: {frames, events: [{t, kind: 'app'|'click'|'key'|'type', name?, x?, y?, keys?, text?}], narration: [{t0, t1, text}]}
// -> [{t, tool, args, how: 'event'|'frames'|'narration'}]
function actionsFrom(rec, o) {
  o = o || {};
  const frames = (rec.frames || []).slice().sort((a, b) => a.t - b.t);
  const events = (rec.events || []).slice().sort((a, b) => a.t - b.t);
  const narr = (rec.narration || []).slice().sort((a, b) => a.t0 - b.t0);
  const acts = [];
  // a) events (the best evidence)
  for (const e of events) {
    if (e.kind === 'app' && e.name) acts.push({ t: e.t, tool: 'open_app', args: { name: String(e.name) }, how: 'event' });
    else if (e.kind === 'key' && e.keys) acts.push({ t: e.t, tool: 'key', args: { keys: String(e.keys).toLowerCase() }, how: 'event' });
    else if (e.kind === 'type' && typeof e.text === 'string') {
      const last = acts[acts.length - 1];
      if (last && last.tool === 'type' && last.how === 'event' && e.t - last.tEnd < 3000) { last.args.text += e.text; last.tEnd = e.t; }
      else acts.push({ t: e.t, tEnd: e.t, tool: 'type', args: { text: e.text }, how: 'event' });
    } else if (e.kind === 'click' && Number.isFinite(e.x) && Number.isFinite(e.y)) {
      const f = frameAtOrBefore(frames, e.t);
      const el = elementAt(f, e.x, e.y);
      acts.push(el ? { t: e.t, tool: 'click', args: { label: el.title }, how: 'event' } : { t: e.t, tool: 'click', args: { x: Math.round(e.x), y: Math.round(e.y) }, how: 'event' });
    }
  }
  if (o.eventsOnly) return finish(acts);
  // b) frame changes no event explains
  const used = new Set();
  narr.forEach((s, i) => {
    const said = ' ' + norm(s.text) + ' ';
    if (acts.some((a) => Math.abs(a.t - s.t0) < 4000 && ((a.tool === 'click' && a.args.label && said.includes(' ' + norm(a.args.label) + ' ')) ||
        (a.tool === 'key' && narratedKey(s.text) === a.args.keys) || (a.tool === 'open_app' && said.includes(' ' + norm(a.args.name) + ' '))))) used.add(i);
  });
  const explained = (t0, t1, kinds) => acts.some((a) => a.t > t0 - 600 && a.t <= t1 + 200 && (!kinds || kinds.includes(a.tool)));
  for (let i = 1; i < frames.length; i++) {
    const p = frames[i - 1], c = frames[i];
    if (p.app !== c.app && c.app) {
      if (!explained(p.t, c.t, ['open_app', 'click', 'key'])) {
        const n = narr.find((s) => s.t0 <= c.t + 500 && s.t1 >= p.t - 3000 && narratedLabel(s.text, p));
        const el = n && narratedLabel(n.text, p);
        acts.push(el && norm(el.title) !== norm(c.app) ? { t: c.t - 1, tool: 'click', args: { label: el.title }, how: 'narration' } : { t: c.t - 1, tool: 'open_app', args: { name: c.app }, how: 'frames' });
      }
      continue;
    }
    // other changes (window title / elements): a click or key the events missed
    const changed = p.title !== c.title || norm((p.elements || []).map((e) => e.title).join('|')) !== norm((c.elements || []).map((e) => e.title).join('|'));
    if (changed && !explained(p.t, c.t, ['click', 'key', 'open_app'])) {
      let a = null;
      // a "saved" marker appeared in the same window (title or a label): the save key
      const savedNow = (f) => /\bsaved\b/.test(norm(f.title + ' ' + (f.elements || []).map((e) => e.title).join(' ')));
      if (!savedNow(p) && savedNow(c) && norm(c.title).startsWith(norm(p.title).replace(/\s*edited$/, ''))) a = { t: c.t - 1, tool: 'key', args: { keys: 'cmd+s' }, how: 'frames' };
      // otherwise the narration closest in time to the change that names a key or a button of the old screen (not one an event already used)
      const near = narr.map((s, i) => ({ s, i })).filter(({ s, i }) => !used.has(i) && s.t0 <= c.t + 500 && s.t1 >= p.t - 4000)
        .sort((x, y) => Math.abs(x.s.t0 - (p.t + c.t) / 2) - Math.abs(y.s.t0 - (p.t + c.t) / 2));
      for (const { s, i } of a ? [] : near) {
        const k = narratedKey(s.text);
        if (k) { a = { t: c.t - 1, tool: 'key', args: { keys: k }, how: 'narration' }; used.add(i); break; }
        const el = narratedLabel(s.text, p);
        if (el) { a = { t: c.t - 1, tool: 'click', args: { label: el.title }, how: 'narration' }; used.add(i); break; }
      }
      if (!a && c.title) {   // the new window is named like a button of the old one
        const el = (p.elements || []).find((e) => e.title && norm(e.title) === norm(c.title));
        if (el) a = { t: c.t - 1, tool: 'click', args: { label: el.title }, how: 'frames' };
      }
      if (a) acts.push(a);
    }
  }
  // typing runs become type steps unless an event already covers them
  // (collected per element: the final value minus the value before typing started)
  const runs = [];
  const seen = new Map();
  for (let i = 0; i < frames.length; i++) {
    for (const e of frames[i].elements || []) {
      const k = elKey(e) + '@' + frames[i].app + '|' + frames[i].title;
      if (!seen.has(k)) { seen.set(k, { first: e.value || '', last: e.value || '', t: null, tLast: null }); continue; }
      const r = seen.get(k);
      if ((e.value || '') !== r.last) { if (r.t === null) r.t = frames[i].t - 1; r.last = e.value || ''; r.tLast = frames[i].t; }
    }
  }
  for (const r of seen.values()) if (r.t !== null && r.last.startsWith(r.first) && r.last.length > r.first.length) runs.push({ t: r.t, tEnd: r.tLast, text: r.last.slice(r.first.length) });
  for (const r of runs) {
    if (acts.some((a) => a.tool === 'type' && a.t <= r.tEnd + 200 && (a.tEnd || a.t) >= r.t - 3000)) continue;
    acts.push({ t: r.t, tEnd: r.tEnd, tool: 'type', args: { text: r.text }, how: 'frames' });
  }
  return finish(acts);
}
function finish(acts) {
  acts.sort((a, b) => a.t - b.t);
  const out = [];
  for (const a of acts) {
    const last = out[out.length - 1];
    if (last && a.tool === 'type' && last.tool === 'type' && a.t - (last.tEnd || last.t) < 3000) { last.args.text += a.args.text; last.tEnd = a.tEnd || a.t; continue; }
    if (last && a.tool === last.tool && a.tool !== 'type' && a.t - last.t < 400 && JSON.stringify(a.args) === JSON.stringify(last.args)) continue;
    out.push(a);
  }
  return out.slice(0, MAX_STEPS);
}

// ---- 2. the skill card -----------------------------------------------------------------------------------------------
function describe(a) {
  if (a.tool === 'open_app') return 'Open ' + a.args.name;
  if (a.tool === 'click') return a.args.label ? 'Click "' + a.args.label + '"' : 'Click at ' + a.args.x + ',' + a.args.y;
  if (a.tool === 'type') return 'Type "' + clip(a.args.text, 80) + '"';
  return 'Press ' + a.args.keys;
}
const words = (s) => new Set(norm(s).split(' ').filter((w) => w.length >= 3));
// what the screen should show after the step: app, window title, and up to 6 new words
function expectAfter(frames, a, next) {
  const before = frameAtOrBefore(frames, a.t - 1);
  const until = next ? next.t : Infinity;
  const after = frames.filter((f) => f.t > (a.tEnd || a.t) && f.t < until).pop() || frames.find((f) => f.t > (a.tEnd || a.t));
  if (!after) return null;
  const old = words(before ? frameText(before) : '');
  const fresh = [...words((after.elements || []).map((e) => e.title + ' ' + e.value).join(' ') + ' ' + after.title)].filter((w) => !old.has(w)).slice(0, 6);
  return { app: after.app, title: after.title, words: fresh };
}
// rec + name -> {id, name, created, steps: [{n, say, do: {tool, args}, expect}], how: {event, frames, narration}}
function skillCard(rec, name, o) {
  o = o || {};
  const frames = (rec.frames || []).slice().sort((a, b) => a.t - b.t);
  const acts = actionsFrom(rec, o);
  const narr = (rec.narration || []).filter((s) => s && s.text && !isPrivate(s.text)).slice().sort((a, b) => a.t0 - b.t0);
  const say = acts.map(() => []);
  for (const s of narr) {   // narration belongs to the first step at or after it (people say it just before or while they act)
    let i = acts.findIndex((a) => a.t >= s.t0 - 1000);
    if (i < 0) i = acts.length - 1;
    if (i >= 0) say[i].push(clip(s.text, 200));
  }
  const steps = acts.map((a, i) => ({ n: i + 1, say: say[i].join(' '), what: describe(a), do: { tool: a.tool, args: a.args }, expect: expectAfter(frames, a, acts[i + 1]), how: a.how }));
  const how = { event: 0, frames: 0, narration: 0 };
  for (const a of acts) how[a.how]++;
  const nm = clip(name || (narr[0] && narr[0].text) || 'Skill', 80);
  return { id: o.id || 'skill-' + Date.now().toString(36), name: nm, created: o.created || new Date().toISOString(), steps, how };
}
// the card as text: what sleep trains on and what Glim reads before redoing it
function cardText(card) {
  return 'Skill "' + card.name + '" (Ben showed it once):\n' + card.steps.map((s) => s.n + '. ' + s.what + (s.say ? ' (Ben: "' + clip(s.say, 160) + '")' : '')).join('\n');
}

// ---- 3. redo a skill with the screen tools, checking each step -------------------------------------------------------
// tools: {look() -> the helper's look json {app, windows, elements} (a frame-like {app, title, ...} also works), open_app({name}), press({id}), click({x, y}), type({text}), key({keys})}
// o: {confirm(card) -> bool (Ben's permission; required), retries (re-looks per check), wait(ms), signal}
function checkScreen(f, exp) {
  if (!exp) return { ok: true };
  if (exp.app && norm(f.app) !== norm(exp.app)) return { ok: false, why: 'front app is "' + f.app + '", expected "' + exp.app + '"' };
  if (exp.title && norm(f.title) !== norm(exp.title)) return { ok: false, why: 'window is "' + f.title + '", expected "' + exp.title + '"' };
  const have = words(frameText(f));
  const miss = (exp.words || []).filter((w) => !have.has(w));
  if (miss.length > Math.floor((exp.words || []).length / 2)) return { ok: false, why: 'missing on screen: ' + miss.join(', ') };
  return { ok: true };
}
const asFrame = (j) => (j && typeof j.title === 'string' && !j.windows ? j : frameFromLook(0, j || {}, (j && j.text) || ''));
async function replaySkill(card, tools, o) {
  o = o || {};
  const wait = o.wait || ((ms) => new Promise((r) => setTimeout(r, ms)));
  const log = [];
  if (typeof o.confirm !== 'function' || !(await o.confirm(card))) return { ok: false, done: 0, failedAt: null, why: 'Ben did not say yes', log };
  for (const s of card.steps) {
    if (o.signal && o.signal.aborted) return { ok: false, done: s.n - 1, failedAt: s.n, why: 'stopped', log };
    const { tool, args } = s.do;
    let r;
    try {
      if (tool === 'open_app') r = await tools.open_app({ name: args.name });
      else if (tool === 'type') r = await tools.type({ text: args.text });
      else if (tool === 'key') r = await tools.key({ keys: args.keys });
      else if (tool === 'click' && args.label) {
        const f = asFrame(await tools.look());
        const want = norm(args.label);
        const el = (f.elements || []).find((e) => norm(e.title) === want) || (f.elements || []).find((e) => norm(e.title).includes(want) && want.length >= 3);
        r = el ? await tools.press({ id: el.id }) : { error: 'no "' + args.label + '" on screen' };
      } else if (tool === 'click') r = await tools.click({ x: args.x, y: args.y });
      else r = { error: 'unknown step ' + tool };
    } catch (e) { r = { error: String((e && e.message) || e) }; }
    if (r && r.error) { log.push({ n: s.n, ok: false, why: r.error }); return { ok: false, done: s.n - 1, failedAt: s.n, why: r.error, log }; }
    let chk = { ok: false, why: 'not checked' };
    for (let k = 0; k <= (o.retries == null ? 1 : o.retries); k++) {
      if (k) await wait(o.retryMs || 700);
      chk = checkScreen(asFrame(await tools.look()), s.expect);
      if (chk.ok) break;
    }
    log.push({ n: s.n, ok: chk.ok, why: chk.why || '' });
    if (!chk.ok) return { ok: false, done: s.n - 1, failedAt: s.n, why: chk.why, log };
  }
  return { ok: true, done: card.steps.length, failedAt: null, why: '', log };
}

// ---- 4. the store of skill cards (userData/watchme-skills.json, read by sleep) ----------------------------------------
class SkillStore {
  constructor(dir) { this.file = path.join(dir, SKILLS_FILE); this.dir = dir; }
  list() { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); return Array.isArray(j.skills) ? j.skills : []; } catch (e) { return []; } }
  save(card) {
    if (!card || !Array.isArray(card.steps) || !card.steps.length) return { ok: false, error: 'no steps' };
    if (isPrivate(card.name + ' ' + cardText(card))) return { ok: false, error: 'looks private; not saved' };
    const skills = this.list().filter((s) => s.id !== card.id && norm(s.name) !== norm(card.name)).concat([{ ...card, text: cardText(card) }]).slice(-MAX_SKILLS);
    fs.mkdirSync(this.dir, { recursive: true });
    const tmp = this.file + '.' + process.pid + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify({ v: 1, skills }, null, 1)); fs.renameSync(tmp, this.file);
    return { ok: true, id: card.id };
  }
  remove(id) { const s = this.list(); const k = s.filter((x) => x.id !== id); if (k.length === s.length) return false; fs.writeFileSync(this.file, JSON.stringify({ v: 1, skills: k }, null, 1)); return true; }
  find(q) { const n = norm(q); const s = this.list(); return s.find((x) => norm(x.name) === n) || s.find((x) => n && norm(x.name).includes(n)) || null; }
}

// ---- 5. raw evidence clips: Mac only, <= KEEP_DAYS days, <= CAP_BYTES, private frames never stored -----------------
class Clips {
  constructor(dir, o) { o = o || {}; this.root = path.join(dir, CLIPS_DIR); this.platform = o.platform || process.platform; this.cap = o.capBytes || CAP_BYTES; this.keepMs = (o.keepDays || KEEP_DAYS) * 86400000; this.now = o.now || Date.now; }
  // -> stored file path or null
  put(skillId, i, jpeg, text) {
    if (this.platform !== 'darwin' || !jpeg || !jpeg.length || isPrivate(text || '')) return null;
    if (!/^[A-Za-z0-9_-]{1,80}$/.test(String(skillId))) return null;
    const d = path.join(this.root, String(skillId));
    fs.mkdirSync(d, { recursive: true });
    const f = path.join(d, String(i).padStart(5, '0') + '.jpg');
    fs.writeFileSync(f, jpeg);
    this.prune();
    return fs.existsSync(f) ? f : null;
  }
  files() {
    const out = [];
    let dirs = [];
    try { dirs = fs.readdirSync(this.root); } catch (e) { return out; }
    for (const d of dirs) {
      let fl = [];
      try { fl = fs.readdirSync(path.join(this.root, d)); } catch (e) { continue; }
      for (const f of fl) { try { const p = path.join(this.root, d, f); const st = fs.statSync(p); out.push({ p, size: st.size, mtime: st.mtimeMs }); } catch (e) { /* gone */ } }
    }
    return out.sort((a, b) => a.mtime - b.mtime || (a.p < b.p ? -1 : 1));
  }
  // drop clips older than KEEP_DAYS, then the oldest until the total is under the cap; empty folders go too
  prune() {
    const fl = this.files();
    let total = fl.reduce((s, f) => s + f.size, 0), n = 0;
    for (const f of fl) {
      if (this.now() - f.mtime > this.keepMs || total > this.cap) { try { fs.rmSync(f.p, { force: true }); total -= f.size; n++; } catch (e) { /* ignore */ } }
    }
    try { for (const d of fs.readdirSync(this.root)) { const p = path.join(this.root, d); try { if (!fs.readdirSync(p).length) fs.rmdirSync(p); } catch (e) { /* not empty */ } } } catch (e) { /* none */ }
    return { removed: n, bytes: total };
  }
}

// ---- 6. a live recording session (main.js drives it; tests drive it with fakes) --------------------------------------
// o: {look: async () => helper look json, ocr: async () => text, shot: async () => Buffer|null (only when clips are on),
//     fps (1-2), now, setInterval, clearInterval, clips: Clips|null}
class WatchSession {
  constructor(o) {
    this.o = o; this.now = o.now || Date.now; this.t0 = this.now(); this.id = 'skill-' + this.t0.toString(36);
    this.rec = { frames: [], events: [], narration: [] }; this.timer = null; this.busy = false; this.dropped = 0; this.shots = 0;
  }
  start() {
    const fps = Math.min(2, Math.max(1, Number(this.o.fps) || 1));
    const si = this.o.setInterval || setInterval;
    this.timer = si(() => { this.tick(); }, Math.round(1000 / fps));
    return this.tick();
  }
  async tick() {
    if (this.busy || this.rec.frames.length >= MAX_FRAMES) return;
    this.busy = true;
    try {
      const look = await this.o.look();
      if (!look || look.error) return;
      const ocr = this.o.ocr ? await this.o.ocr() : '';
      const f = frameFromLook(this.now() - this.t0, look, ocr);
      if (isPrivate(frameText(f))) { this.dropped++; return; }   // never kept: no text, no picture
      this.rec.frames.push(f);
      if (this.o.clips && this.o.shot) { const j = await this.o.shot(); if (j && this.o.clips.put(this.id, this.rec.frames.length, j, frameText(f))) this.shots++; }
    } catch (e) { /* a missed frame */ } finally { this.busy = false; }
  }
  event(e) { if (e && TOOLS.concat(['app']).includes(e.kind)) this.rec.events.push({ ...e, t: this.now() - this.t0 }); }
  // a finished utterance from the speech-to-text stream
  heard(text, t0, t1) { const t = String(text || '').trim(); if (!t || isPrivate(t)) return; const now = this.now() - this.t0; this.rec.narration.push({ t0: t0 == null ? Math.max(0, now - 2000) : t0 - this.t0, t1: t1 == null ? now : t1 - this.t0, text: t }); }
  stop(name) {
    if (this.timer) (this.o.clearInterval || clearInterval)(this.timer);
    this.timer = null;
    return skillCard(this.rec, name, { id: this.id });
  }
}

module.exports = { SKILLS_FILE, CLIPS_DIR, KEEP_DAYS, CAP_BYTES, frameFromLook, elementAt, narratedKey, narratedLabel, actionsFrom, skillCard, cardText, describe, checkScreen, replaySkill, SkillStore, Clips, WatchSession, norm };
