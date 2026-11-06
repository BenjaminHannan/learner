'use strict';
// "Glim can see" (track I1, 2026-11-04). Setting glimCanSee, OFF by default.
// Day: when the screen sense reads the screen (at the change-only pace when that is on), the eyes also take one small screenshot,
//   turn it into 64 x 768 SigLIP2 features (desk/tools/glim_eyes.py, a Python worker on this Mac), and:
//   - keep the features with the screen words as their text anchor (sense-sleep FeatureStore: what sense sleep practises on);
//   - keep the latest frame for the always-on loop's next look (sent to the model server as an image_features part);
//   - with keepSenseEvidence on (OFF by default), keep the screenshot itself as evidence (EvidenceStore below: Mac only, 3 days, 2 GB).
//   Nothing is kept, and no picture is even taken, when the screen or the windows look private (passwords, banking, sign-in,
//   private / incognito browser windows).
// Night: nightly() turns the day's anchored features into sense sleep's practice manifest (sense-sleep/practice-<night>.json), and
//   prunes old features (3 days, unless a kept night still uses them) and old evidence. The sleep app trains the projector on it
//   under the seatbelt (sleepmlx/sense_night.py).
// The ears stay off: the sound projector failed its marks (A1 30 % < 40 %). The ear hooks of FeatureStore are left in place.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const SenseSleep = require('./sense-sleep');

const EYE_ID = 'siglip2-base-patch16-256/pool2x2/v1';   // must equal glim_eyes.EYE_ID
const SHAPE = [64, 768];
const EVIDENCE_DIR = 'sense-evidence';
const EVIDENCE_DAYS = 3, EVIDENCE_BYTES = 2 * 1024 ** 3;
const FEATURE_DAYS = 3;
const FRAME_FRESH_MS = 120000;
// vid-in (2026-11-05): short clips. While the eyes are on, a light ticker (clipTick, every CLIP_EVERY_MS) adds frames to an in-memory
// ring (never stored, never evidence). When the last CLIP_WINDOW_MS hold >= CLIP_MIN frames and the screen MOVED (some neighbour pair
// of frames has feature cosine < STILL_COS), seePart() sends them as ONE clip part through the video projector (model server
// "clip" field); a still screen keeps the single-picture part (image projector). On a still screen the ticker slows to CLIP_STILL_MS.
const CLIP_FRAMES = 8, CLIP_MIN = 3, CLIP_EVERY_MS = 2500, CLIP_STILL_MS = 10000, CLIP_WINDOW_MS = 20000, STILL_COS = 0.995;
// CHAT-FIRST C (2026-11-05): the always-on tick (tickPart) carries a picture only when the newest frame differs meaningfully from the
// last frame Glim was SENT (feature cosine < SEND_COS), and a clip only then AND >= CLIP_GAP_MS after the last clip. Otherwise no
// picture at all (the text senses still go). A chat that asks about the screen keeps seePart().
const SEND_COS = 0.98, CLIP_GAP_MS = 180000;
const PRIVATE_WINDOW = /\b(?:private\s+browsing|incognito|inprivate|private\s+window)\b|\b(?:1password|bitwarden|lastpass|keychain\s+access|passwords)\b\s*(?:—|-|:|\.|$)/i;

const dayOf = (t) => new Date(t).toISOString().slice(0, 10);

// ---- raw evidence: screenshots, Mac only, short window, size cap ---------------------------------------------------------------
class EvidenceStore {
  constructor(userData, o = {}) {
    this.dir = path.join(userData, EVIDENCE_DIR);
    this.platform = o.platform || process.platform;
    this.maxDays = o.maxDays || EVIDENCE_DAYS; this.maxBytes = o.maxBytes || EVIDENCE_BYTES;
    this.now = o.now || Date.now;
  }
  enabled() { return this.platform === 'darwin'; }
  // jpeg: Buffer. private: true -> never stored. -> {stored, file?, reason?}
  add(jpeg, meta = {}) {
    if (!this.enabled()) return { stored: false, reason: 'Mac only' };
    if (meta.private) return { stored: false, reason: 'private' };
    if (!Buffer.isBuffer(jpeg) || jpeg.length < 4 || jpeg[0] !== 0xff || jpeg[1] !== 0xd8) return { stored: false, reason: 'not a jpeg' };
    if (jpeg.length > 8 * 1024 * 1024) return { stored: false, reason: 'too big' };
    const t = this.now(), d = path.join(this.dir, dayOf(t));
    fs.mkdirSync(d, { recursive: true });
    const name = t + '-' + crypto.randomBytes(3).toString('hex');
    const file = path.join(d, name + '.jpg');
    fs.writeFileSync(file, jpeg);
    if (meta.featureId || meta.text) fs.writeFileSync(path.join(d, name + '.json'), JSON.stringify({ t, featureId: meta.featureId || null, text: String(meta.text || '').slice(0, 300) }));
    this.prune();
    return { stored: true, file };
  }
  files() {
    const out = [];
    let days = [];
    try { days = fs.readdirSync(this.dir).filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(x)).sort(); } catch (_) { return out; }
    for (const day of days) {
      let names = [];
      try { names = fs.readdirSync(path.join(this.dir, day)).sort(); } catch (_) { continue; }
      for (const n of names) { const p = path.join(this.dir, day, n); try { out.push({ day, file: p, size: fs.statSync(p).size }); } catch (_) {} }
    }
    return out;
  }
  bytes() { return this.files().reduce((s, f) => s + f.size, 0); }
  // Older than maxDays -> gone; then the oldest go until the total is under maxBytes.
  prune() {
    const cut = dayOf(this.now() - (this.maxDays - 1) * 86400000);
    let gone = 0;
    const all = this.files();
    let total = 0;
    const keep = [];
    for (const f of all) { if (f.day < cut) { try { fs.unlinkSync(f.file); gone++; } catch (_) {} } else { keep.push(f); total += f.size; } }
    for (const f of keep) { if (total <= this.maxBytes) break; try { fs.unlinkSync(f.file); gone++; total -= f.size; } catch (_) {} }
    try { for (const d of fs.readdirSync(this.dir)) { const p = path.join(this.dir, d); try { if (!fs.readdirSync(p).length) fs.rmdirSync(p); } catch (_) {} } } catch (_) {}
    return { gone, bytes: total };
  }
  clear() { fs.rmSync(this.dir, { recursive: true, force: true }); }
}

// ---- the Python eyes worker (JSON lines) ------------------------------------------------------------------------------------------
class EyesWorker {
  constructor(o) {
    this.o = o; this.proc = null; this.ready = false; this.pending = new Map(); this.buf = ''; this.seq = 0;
    this.fails = 0; this.nextTryAt = 0; this.now = o.now || Date.now; this.timeoutMs = o.timeoutMs || 30000;
  }
  start() {
    if (this.proc || this.now() < this.nextTryAt) return !!this.proc;
    let p;
    try { p = this.o.spawn(); } catch (e) { this.failed('spawn: ' + e.message); return false; }
    this.proc = p; this.ready = false; this.buf = '';
    p.stdout.on('data', (b) => this.onData(b));
    if (p.stderr) p.stderr.on('data', () => {});
    p.on('exit', (code) => { if (this.proc === p) { this.proc = null; this.ready = false; for (const [, r] of this.pending) r.reject(new Error('eyes stopped (' + code + ')')); this.pending.clear(); this.failed('exit ' + code); } });
    p.on('error', (e) => this.failed('error ' + e.message));
    return true;
  }
  failed(why) { this.fails++; this.nextTryAt = this.now() + Math.min(600000, 5000 * 2 ** Math.min(this.fails, 7)); if (this.o.log) this.o.log('eyes worker: ' + why); }
  onData(b) {
    this.buf += b.toString('utf8');
    let i;
    while ((i = this.buf.indexOf('\n')) >= 0) {
      const line = this.buf.slice(0, i); this.buf = this.buf.slice(i + 1);
      let j; try { j = JSON.parse(line); } catch (_) { continue; }
      if (j.ready) { this.ready = true; this.fails = 0; continue; }
      const r = this.pending.get(j.id); if (!r) continue;
      this.pending.delete(j.id); clearTimeout(r.timer);
      if (j.ok) r.resolve(j); else r.reject(new Error(j.error || 'eyes failed'));
    }
  }
  encode(file) {
    if (!this.start()) return Promise.reject(new Error('eyes not running'));
    const id = String(++this.seq);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error('eyes timeout')); }, this.timeoutMs);
      if (timer.unref) timer.unref();
      this.pending.set(id, { resolve, reject, timer });
      try { this.proc.stdin.write(JSON.stringify({ id, path: file }) + '\n'); } catch (e) { this.pending.delete(id); clearTimeout(timer); reject(e); }
    });
  }
  stop() { const p = this.proc; this.proc = null; this.ready = false; if (p) { try { p.stdin.end(JSON.stringify({ quit: true }) + '\n'); } catch (_) {} setTimeout(() => { try { p.kill(); } catch (_) {} }, 2000).unref?.(); } }
}

// the screen tool's screenshot (a data URL) -> JPEG bytes, or null
function fromDataUrl(u) { if (typeof u !== 'string' || !u.startsWith('data:image/jpeg;base64,')) return null; const b = Buffer.from(u.slice(u.indexOf(',') + 1), 'base64'); return b.length ? b : null; }
function f16ToFloats(b64) { return SenseSleep.decodeF16(Buffer.from(b64, 'base64')); }

// ---- the day pipeline ------------------------------------------------------------------------------------------------------------
// o: { userData, on: () => bool (glimCanSee), keepEvidence: () => bool, shot: async () => Buffer|null (JPEG), worker: EyesWorker,
//      isPrivate(text) -> bool, now, log }
class Eyes {
  constructor(o) {
    this.o = o; this.now = o.now || Date.now; this.busy = false; this.latest = null; this.ring = []; this.clipSentAt = 0; this.lastTickAt = 0;
    this.store = new SenseSleep.FeatureStore(o.userData, { isPrivate: o.isPrivate || (() => false) });
    this.evidence = new EvidenceStore(o.userData, { platform: o.platform, now: this.now });
    this.stats = { frames: 0, private: 0, errors: 0, stored: 0, evidence: 0, ms: [] };
  }
  on() { return !!(this.o.on && this.o.on()); }
  privateNow(screenText, windowsText) {
    const p = this.o.isPrivate || (() => false);
    return p(screenText || '') || p(windowsText || '') || PRIVATE_WINDOW.test(windowsText || '') || PRIVATE_WINDOW.test(screenText || '');
  }
  // Called after each screen read (senses onScreen). Never throws; one frame at a time (a busy frame is skipped).
  async look(screenText, windowsText) {
    if (!this.on() || this.busy) return null;
    if (this.privateNow(screenText, windowsText)) { this.stats.private++; this.latest = null; this.ring = []; return { skipped: 'private' }; }
    this.busy = true;
    const tmp = path.join(os.tmpdir(), 'premonition-eyes-' + process.pid + '-' + crypto.randomBytes(4).toString('hex') + '.jpg');
    try {
      const jpeg = await this.o.shot();
      if (!jpeg) return null;
      fs.writeFileSync(tmp, jpeg, { mode: 0o600 });
      const r = await this.o.worker.encode(tmp);
      if (r.eye !== EYE_ID || !Array.isArray(r.shape) || r.shape[0] !== SHAPE[0] || r.shape[1] !== SHAPE[1]) throw new Error('eyes: unexpected encoder ' + r.eye + ' ' + r.shape);
      this.stats.frames++; this.stats.ms.push(r.ms); if (this.stats.ms.length > 50) this.stats.ms.shift();
      const t = this.now();
      this.latest = { t, f16: r.f16, shape: r.shape, text: String(screenText || '').slice(0, 300) };
      this.pushRing({ t, f16: r.f16 });
      const title = /Front app: ([^.]{1,80})\./.exec(windowsText || '');
      const s = this.store.add({ t, source: 'screen', eye: { encoder: EYE_ID, vec: f16ToFloats(r.f16), shape: r.shape },
        text: { screen: screenText ? String(screenText).slice(0, 300) : null, title: title ? title[1] : null } });
      if (s.stored) this.stats.stored++;
      if (this.o.keepEvidence && this.o.keepEvidence()) { const e = this.evidence.add(jpeg, { featureId: s.id, text: screenText }); if (e.stored) this.stats.evidence++; }
      return { stored: !!s.stored, id: s.id || null, ms: r.ms };
    } catch (e) {
      this.stats.errors++; if (this.o.log) this.o.log('eyes: ' + e.message); return { error: e.message };
    } finally { this.busy = false; fs.rm(tmp, { force: true }, () => {}); }
  }
  // ---- clips (vid-in) ----
  pushRing(f) {
    f.vec = f16ToFloats(f.f16);
    this.ring.push(f);
    const cut = this.now() - CLIP_WINDOW_MS;
    while (this.ring.length > CLIP_FRAMES || (this.ring.length && this.ring[0].t < cut)) this.ring.shift();
  }
  // the ring's frames inside the clip window, and whether the screen moved between neighbours
  recentClip() {
    const cut = this.now() - CLIP_WINDOW_MS;
    const fr = this.ring.filter((f) => f.t >= cut);
    let moved = false;
    for (let i = 1; i < fr.length && !moved; i++) if (cosine(fr[i - 1].vec, fr[i].vec) < STILL_COS) moved = true;
    return { frames: fr, moved };
  }
  // Called by main.js every CLIP_EVERY_MS while the eyes and the screen sense are on: one more frame for the ring (memory only).
  // Slows to CLIP_STILL_MS while the screen stays still. Never throws.
  async clipTick(screenText, windowsText) {
    if (!this.on() || this.clipBusy) return null;
    const now = this.now();
    if (this.lastTickAt && now - this.lastTickAt < CLIP_EVERY_MS - 50) return null;
    const { frames, moved } = this.recentClip();
    if (frames.length >= 2 && !moved && now - frames[frames.length - 1].t < CLIP_STILL_MS) return null;
    if (this.privateNow(screenText, windowsText)) { this.ring = []; this.latest = null; return { skipped: 'private' }; }
    this.clipBusy = true; this.lastTickAt = now;
    const tmp = path.join(os.tmpdir(), 'premonition-eyes-' + process.pid + '-' + crypto.randomBytes(4).toString('hex') + '.jpg');
    try {
      const jpeg = await this.o.shot();
      if (!jpeg) return null;
      fs.writeFileSync(tmp, jpeg, { mode: 0o600 });
      const r = await this.o.worker.encode(tmp);
      if (r.eye !== EYE_ID || !Array.isArray(r.shape) || r.shape[0] !== SHAPE[0] || r.shape[1] !== SHAPE[1]) throw new Error('eyes: unexpected encoder ' + r.eye + ' ' + r.shape);
      this.stats.clipFrames = (this.stats.clipFrames || 0) + 1;
      const t = this.now();
      this.pushRing({ t, f16: r.f16 });
      this.latest = { t, f16: r.f16, shape: r.shape, text: this.latest ? this.latest.text : '' };
      return { ok: true, ms: r.ms };
    } catch (e) {
      this.stats.errors++; if (this.o.log) this.o.log('eyes clip: ' + e.message); return { error: e.message };
    } finally { this.clipBusy = false; fs.rm(tmp, { force: true }, () => {}); }
  }
  // The recent frames as ONE clip part (2..8 frames, times in seconds from the first), or null (off, too few, or a still screen).
  // once=true: the same newest frame is never sent twice.
  clipPart(once = true) {
    if (!this.on()) return null;
    const { frames, moved } = this.recentClip();
    if (frames.length < CLIP_MIN || !moved) return null;
    const fr = frames.slice(-CLIP_FRAMES);
    const newest = fr[fr.length - 1].t;
    if (once && newest <= this.clipSentAt) return null;
    if (once) { this.clipSentAt = newest; this.latest = null; }
    const t0 = fr[0].t;
    const f16 = Buffer.concat(fr.map((f) => Buffer.from(f.f16, 'base64'))).toString('base64');
    return { type: 'image_features', image_features: { f16, shape: [fr.length * SHAPE[0], SHAPE[1]], eye: EYE_ID,
      clip: { frames: fr.length, times: fr.map((f) => Math.round((f.t - t0) / 1000)), seconds: Math.round((newest - t0) / 1000) } } };
  }
  // what an always-on tick carries (CHAT-FIRST C): null unless the screen changed meaningfully since the last part sent
  tickPart() {
    const f = this.latest;
    if (!this.on() || !f || this.now() - f.t > FRAME_FRESH_MS) return null;
    const v = f16ToFloats(f.f16);
    if (this.sentVec && cosine(this.sentVec, v) >= SEND_COS) { this.stats.tickSkips = (this.stats.tickSkips || 0) + 1; return null; }
    const now = this.now();
    let part = now - (this.clipSentTickAt || 0) >= CLIP_GAP_MS ? this.clipPart(true) : null;
    if (part) this.clipSentTickAt = now; else part = this.framePart(true);
    if (part) { this.sentVec = v; this.stats.tickSends = (this.stats.tickSends || 0) + 1; }
    return part;
  }
  // what the loop / a chat ask carries: a clip when the screen moved, else the single latest picture
  seePart(once = true) { return this.clipPart(once) || this.framePart(once); }
  // The latest frame as an image_features content part, or null (off, none, too old, or used already when once=true).
  framePart(once = true) {
    const f = this.latest;
    if (!this.on() || !f || this.now() - f.t > FRAME_FRESH_MS) return null;
    if (once) this.latest = null;
    return { type: 'image_features', image_features: { f16: f.f16, shape: f.shape, eye: EYE_ID } };
  }
  // Night: the day's practice manifest + pruning. -> summary. Never throws.
  nightly(o = {}) {
    const now = o.now || this.now();
    const ledger = new SenseSleep.NightLedger(this.o.userData);
    const out = { manifests: [], pruned: [], evidence: null };
    try {
      const night = dayOf(now);
      const done = new Set(ledger.entries().map((e) => e.night));
      for (const day of this.store.days()) {
        const name = day;
        if (done.has(name) || fs.existsSync(ledger.manifestPath(name)) || fs.existsSync(ledger.manifestPath(name).replace(/\.json$/, '.quarantined.json'))) continue;
        if (day > night) continue;
        const practice = SenseSleep.buildPractice(this.store.records(day), { encoders: { eye: EYE_ID }, logicCheck: o.logicCheck });
        practice.ear = [];   // ears stay off (sound projector failed A1); their features are never practised
        if (!practice.eye.length) continue;
        ledger.writeManifest(name, practice, { encoders: { eye: EYE_ID }, senses: ['eye'] });
        out.manifests.push({ night: name, eye: practice.eye.length, stats: practice.stats });
      }
      out.pruned = this.store.prune(FEATURE_DAYS, now, ledger.pinnedDays());
      out.evidence = this.evidence.prune();
    } catch (e) { out.error = e.message; }
    return out;
  }
  status() {
    const ms = [...this.stats.ms].sort((a, b) => a - b);
    return { on: this.on(), frames: this.stats.frames, stored: this.stats.stored, private: this.stats.private, errors: this.stats.errors,
      evidence: this.stats.evidence, clipFrames: this.stats.clipFrames || 0, ring: this.ring.length, medianMs: ms.length ? ms[ms.length >> 1] : null };
  }
}

function cosine(a, b) {
  let d = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? d / Math.sqrt(na * nb) : 1;
}
// the words in front of a part: a clip says how long it covers
function labelFor(part) {
  const c = part && part.image_features && part.image_features.clip;
  return c ? 'What the screen showed over the last ' + Math.max(1, c.seconds || 0) + ' seconds (a short clip, oldest frame first):' : 'What the screen looks like now:';
}
// A chat question about the screen or a video (vid-in): the chat's first request of that turn carries the eyes' part.
const SEE_ASK = /\b(?:video|clip|movie|screen|display|watch(?:ing|ed)?|playing|happen(?:ed|ing)?|see|seeing|look(?:ing)? at|showing|shown)\b/i;
function wantsSight(text) { return typeof text === 'string' && SEE_ASK.test(text); }

// Put the latest frame in front of the last user message's text (the layout the projector was trained with: media, then words).
function withFrame(messages, part, label) {
  if (!part || !Array.isArray(messages) || !messages.length) return messages;
  const out = messages.map((m) => ({ ...m }));
  for (let i = out.length - 1; i >= 0; i--) {
    if (out[i].role !== 'user') continue;
    const c = out[i].content;
    const text = typeof c === 'string' ? c : Array.isArray(c) ? c.filter((p) => p && p.type === 'text').map((p) => p.text).join('\n') : '';
    out[i].content = [{ type: 'text', text: (label || 'What the screen looks like now:') + '\n' }, part, { type: 'text', text: '\n' + text }];
    return out;
  }
  return messages;
}

module.exports = { SEND_COS, CLIP_GAP_MS, fromDataUrl, Eyes, EyesWorker, EvidenceStore, withFrame, labelFor, wantsSight, cosine, CLIP_FRAMES, CLIP_MIN, CLIP_EVERY_MS, CLIP_STILL_MS, CLIP_WINDOW_MS, STILL_COS, EYE_ID, SHAPE, PRIVATE_WINDOW, EVIDENCE_DAYS, EVIDENCE_BYTES, FEATURE_DAYS, FRAME_FRESH_MS, EVIDENCE_DIR };
