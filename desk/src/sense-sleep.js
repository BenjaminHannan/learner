'use strict';
// Sleep for the senses: the eyes and ears projectors (design section 9; toy track T4, 2026-11-04).
// Pure Node, no Electron, no model calls: the night job injects the senses' guesses and the logic check.
//
// Day: FeatureStore keeps ENCODER FEATURES (SigLIP / Whisper outputs) from watching and listening, never raw pictures or sound,
//      plus the short text read alongside (subtitles, sound tags like "[dog barks]", on-screen words, the title).
// Night: buildPractice turns the day into practice sets:
//   - text-anchored practice (toy PASS 3/3): subtitles -> ears (speech), sound tags -> ears (sounds), on-screen text / captions -> eyes;
//     every example must pass the logic check (the real design: a Nanbeige "does this make sense" check);
//   - the 2-of-3 rule (toy: NOT proven, so OFF by default, `twoOfThree: true` to try it): when one sense and the context agree and the
//     other sense disagrees with both, the odd one gets a practice example; a teaching direction is used only if, on the same day's
//     text-anchored clips, its labels agreed with the text >= 80 % (>= 20 cases);
//   - nothing agrees, or the senses agree against the context -> a `maybe` (logged, never trained);
//   - echo guard (toy PASS 3/3): the eyes and ears never teach each other without text or a passing logic check.
// Seatbelt (toy PASS 3/3): decideNight compares the fixed projector tests (V1 / A1 / VID1) before and after; any drop > 2 points, or a
//   missing score, undoes the night. NightLedger logs every night and quarantines a rolled-back night's practice so it is never replayed.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DIR = 'sense-sleep';
const MAX_DIM = 64 * 1024;             // one record's feature vector (64 x 768 SigLIP tokens = 49,152)
const MAX_TEXT = 300;
const MAX_RECORDS_PER_DAY = 2000;
const MAX_BYTES_PER_DAY = 200 * 1024 * 1024;   // float16 features; ~2,000 SigLIP frames
const SEAT_DROP = 2;
const TESTS = ['V1', 'A1', 'VID1'];
const GATE_PREC = 0.8, GATE_MIN = 20;
// Anything that looks like raw media is refused outright: only features and short text may be stored.
const RAW_KEYS = /^(image|img|png|jpe?g|pixels?|frame_?raw|screenshot|audio|wav|pcm|samples|waveform|mp3|m4a|video|mp4|raw|buffer|bytes)$/i;

const dayOf = (t) => new Date(t).toISOString().slice(0, 10);
const readJson = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; } };
function atomicWrite(p, obj) {
  const tmp = p + '.' + process.pid + '.' + crypto.randomUUID() + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2)); fs.renameSync(tmp, p);
}

// ---- float16 (Node 22 has no Float16Array) ------------------------------------------------------------
const f32 = new Float32Array(1), u32 = new Uint32Array(f32.buffer);
function toHalf(v) {
  f32[0] = v; const x = u32[0];
  const sign = (x >>> 16) & 0x8000; let exp = ((x >>> 23) & 0xff) - 127 + 15; let man = x & 0x7fffff;
  if (exp >= 31) return sign | 0x7c00;                     // overflow -> inf (finite inputs are checked before)
  if (exp <= 0) { if (exp < -10) return sign; man = (man | 0x800000) >>> (1 - exp); return sign | ((man + 0x1000) >>> 13); }
  const h = sign | (exp << 10) | (man >>> 13);
  return (man & 0x1000) ? h + 1 : h;                       // round half up on the dropped bits
}
function fromHalf(h) {
  const s = h & 0x8000 ? -1 : 1, e = (h >>> 10) & 0x1f, m = h & 0x3ff;
  if (e === 0) return s * m * 2 ** -24;
  if (e === 31) return m ? NaN : s * Infinity;
  return s * (1 + m / 1024) * 2 ** (e - 15);
}
function encodeF16(vec) {
  const b = Buffer.alloc(vec.length * 2);
  for (let i = 0; i < vec.length; i++) b.writeUInt16LE(toHalf(vec[i]), i * 2);
  return b;
}
function decodeF16(buf) {
  const out = new Float32Array(buf.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = fromHalf(buf.readUInt16LE(i * 2));
  return out;
}

function cleanText(s) {
  if (s == null) return null;
  const t = String(s).replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT);
  return t || null;
}
function checkVec(v, name) {
  if (v == null) return null;
  if (!(Array.isArray(v) || ArrayBuffer.isView(v)) || Buffer.isBuffer(v)) throw new Error(name + ': features must be a number array');
  if (!v.length || v.length > MAX_DIM) throw new Error(name + ': bad feature length ' + v.length);
  for (let i = 0; i < v.length; i++) if (!Number.isFinite(v[i]) || Math.abs(v[i]) > 65000) throw new Error(name + ': non-finite or out-of-range feature');
  return v;
}

// ---- day: feature store --------------------------------------------------------------------------------
// One day = features-<day>.bin (float16 vectors, appended) + features-<day>.jsonl (one line per record, with offsets).
// record: { t, clip, frame?, source: 'video'|'listen'|'screen', eye?: {encoder, vec, shape?}, ear?: {encoder, vec, shape?},
//           text?: {subtitle, soundTag, screen, caption, title}, ctx?: {category} }
class FeatureStore {
  constructor(userData, opts = {}) {
    this.dir = path.join(userData, DIR);
    this.isPrivate = opts.isPrivate || (() => false);
    this.maxRecords = opts.maxRecords || MAX_RECORDS_PER_DAY;
    this.maxBytes = opts.maxBytes || MAX_BYTES_PER_DAY;
  }
  files(day) { return { bin: path.join(this.dir, 'features-' + day + '.bin'), idx: path.join(this.dir, 'features-' + day + '.jsonl') }; }
  add(rec) {
    if (!rec || typeof rec !== 'object') throw new Error('record required');
    for (const k of Object.keys(rec)) if (RAW_KEYS.test(k)) throw new Error('raw media is never stored: ' + k);
    for (const s of ['eye', 'ear']) if (rec[s]) for (const k of Object.keys(rec[s])) if (RAW_KEYS.test(k)) throw new Error('raw media is never stored: ' + s + '.' + k);
    const eye = rec.eye ? checkVec(rec.eye.vec, 'eye') : null, ear = rec.ear ? checkVec(rec.ear.vec, 'ear') : null;
    if (!eye && !ear) return { stored: false, reason: 'no features' };
    if ((eye && !rec.eye.encoder) || (ear && !rec.ear.encoder)) throw new Error('encoder id required with features');
    const text = {};
    for (const k of ['subtitle', 'soundTag', 'screen', 'caption', 'title']) {
      const v = cleanText(rec.text && rec.text[k]);
      if (v && this.isPrivate(v)) return { stored: false, reason: 'private' };
      if (v) text[k] = v;
    }
    const t = Number(rec.t) || Date.now(), day = dayOf(t), f = this.files(day);
    fs.mkdirSync(this.dir, { recursive: true });
    const size = fs.existsSync(f.bin) ? fs.statSync(f.bin).size : 0;
    const add = (eye ? eye.length * 2 : 0) + (ear ? ear.length * 2 : 0);
    if (size + add > this.maxBytes) return { stored: false, reason: 'day full (bytes)' };
    const n = fs.existsSync(f.idx) ? fs.readFileSync(f.idx, 'utf8').split('\n').filter(Boolean).length : 0;
    if (n >= this.maxRecords) return { stored: false, reason: 'day full (records)' };
    const line = { id: day + '#' + n, t, clip: rec.clip == null ? null : String(rec.clip).slice(0, 120), frame: Number.isInteger(rec.frame) ? rec.frame : null,
      source: ['video', 'listen', 'screen'].includes(rec.source) ? rec.source : 'video', text,
      ctx: rec.ctx && rec.ctx.category ? { category: String(rec.ctx.category).slice(0, 60) } : null };
    let off = size;
    const parts = [];
    for (const [s, v] of [['eye', eye], ['ear', ear]]) {
      if (!v) continue;
      const b = encodeF16(v); parts.push(b);
      line[s] = { encoder: String(rec[s].encoder).slice(0, 120), off, len: v.length, shape: Array.isArray(rec[s].shape) ? rec[s].shape.slice(0, 4) : [v.length] };
      off += b.length;
    }
    fs.appendFileSync(f.bin, Buffer.concat(parts));
    fs.appendFileSync(f.idx, JSON.stringify(line) + '\n');
    return { stored: true, id: line.id };
  }
  records(day) {
    const f = this.files(day);
    try { return fs.readFileSync(f.idx, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); } catch (_) { return []; }
  }
  vector(day, ref) {
    const fd = fs.openSync(this.files(day).bin, 'r');
    try { const b = Buffer.alloc(ref.len * 2); fs.readSync(fd, b, 0, b.length, ref.off); return decodeF16(b); } finally { fs.closeSync(fd); }
  }
  days() {
    try { return fs.readdirSync(this.dir).map((f) => /^features-(\d{4}-\d{2}-\d{2})\.jsonl$/.exec(f)).filter(Boolean).map((m) => m[1]).sort(); } catch (_) { return []; }
  }
  // Delete feature days older than keepDays unless a kept night's practice still points at them.
  prune(keepDays, now = Date.now(), pinned = new Set()) {
    const cut = dayOf(now - keepDays * 86400000), gone = [];
    for (const d of this.days()) if (d < cut && !pinned.has(d)) { const f = this.files(d); for (const p of [f.bin, f.idx]) try { fs.unlinkSync(p); } catch (_) {} gone.push(d); }
    return gone;
  }
}

// ---- night: practice sets ------------------------------------------------------------------------------
// Default logic check (rule-based stand-in): text must not be a `maybe`, must not be empty, and when both the title's category and a
// categoryOf(text) are known they must match. The night job should pass the real Nanbeige check as opts.logicCheck(text, record).
function defaultLogic(categoryOf) {
  return (text, rec) => {
    if (!text || /^\s*maybe\b/i.test(text)) return false;
    const want = rec.ctx && rec.ctx.category, got = categoryOf ? categoryOf(text) : null;
    return !(want && got && want !== got);
  };
}
const soundTagText = (s) => { const m = /^\s*\[([^\]]{1,80})\]\s*$/.exec(s || ''); return m ? m[1].trim() : null; };

// opts: { logicCheck(text, rec) -> bool, encoders: {eye, ear} (current ids; other ids are stale), twoOfThree: false,
//         guesses: { [recId]: {eye: text|null, ear: text|null} } (the senses' own descriptions, for 2-of-3),
//         agree(a, b) -> bool, fitsContext(label, rec) -> bool }
function buildPractice(records, opts = {}) {
  const logic = opts.logicCheck || defaultLogic(opts.categoryOf);
  const enc = opts.encoders || {};
  const agree = opts.agree || ((a, b) => !!a && !!b && norm(a) === norm(b));
  const fits = opts.fitsContext || ((label, rec) => !(rec.ctx && rec.ctx.category && opts.categoryOf && opts.categoryOf(label) && opts.categoryOf(label) !== rec.ctx.category));
  const out = { eye: [], ear: [], maybe: [], stats: { anchored_eye: 0, anchored_ear: 0, rejected_logic: 0, stale: 0, two3_eye: 0, two3_ear: 0, maybe: 0 } };
  const fresh = (rec, s) => rec[s] && (!enc[s] || rec[s].encoder === enc[s]);
  const anchoredFor = new Map();
  for (const rec of records) {
    const got = { eye: null, ear: null };
    for (const s of ['eye', 'ear']) if (rec[s] && !fresh(rec, s)) out.stats.stale++;
    const tx = rec.text || {};
    // routing: subtitles -> ears (speech); sound tags -> ears (sounds); on-screen words and captions -> eyes
    const earText = tx.subtitle ? { text: tx.subtitle, kind: 'speech' } : soundTagText(tx.soundTag) ? { text: soundTagText(tx.soundTag), kind: 'sound' } : null;
    const eyeText = tx.screen ? { text: tx.screen, kind: 'reading' } : tx.caption ? { text: tx.caption, kind: 'scene' } : null;
    for (const [s, a] of [['ear', earText], ['eye', eyeText]]) {
      if (!a || !fresh(rec, s)) continue;
      if (!logic(a.text, rec)) { out.stats.rejected_logic++; continue; }
      out[s].push({ id: rec.id, sense: s, ref: rec[s], label: a.text, kind: a.kind, from: 'text' });
      out.stats['anchored_' + s]++; got[s] = a.text;
    }
    anchoredFor.set(rec.id, got);
  }
  if (opts.twoOfThree) {
    const guesses = opts.guesses || {};
    // direction gate: measured on today's anchored clips (the student's text vs the label the rule would give)
    const hit = { eye: [0, 0], ear: [0, 0] };
    const fire = (rec) => {
      const g = guesses[rec.id]; if (!g || !rec.ctx || !rec.ctx.category) return null;
      const eyeFits = g.eye && fits(g.eye, rec), earFits = g.ear && fits(g.ear, rec);
      if (eyeFits && g.ear && !agree(g.eye, g.ear) && !earFits) return { student: 'ear', label: g.eye };
      if (earFits && g.eye && !agree(g.eye, g.ear) && !eyeFits) return { student: 'eye', label: g.ear };
      return null;
    };
    for (const rec of records) {
      const f = fire(rec), a = anchoredFor.get(rec.id);
      if (f && a && a[f.student]) { hit[f.student][0]++; hit[f.student][1] += agree(f.label, a[f.student]) ? 1 : 0; }
    }
    const open = {}; for (const s of ['eye', 'ear']) open[s] = hit[s][0] >= GATE_MIN && hit[s][1] / hit[s][0] >= GATE_PREC;
    out.stats.gate = { open, measured: hit };
    for (const rec of records) {
      const a = anchoredFor.get(rec.id) || {}, g = guesses[rec.id];
      const f = fire(rec);
      if (f && !a[f.student] && open[f.student] && fresh(rec, f.student) && logic(f.label, rec)) {
        out[f.student].push({ id: rec.id, sense: f.student, ref: rec[f.student], label: f.label, kind: '2of3', from: f.student === 'ear' ? 'eye' : 'ear' });
        out.stats['two3_' + f.student]++;
      } else if (g && !a.eye && !a.ear && !f) {
        out.maybe.push({ id: rec.id, eye: g.eye || null, ear: g.ear || null, why: g.eye && g.ear && agree(g.eye, g.ear) ? 'agree-against-context-or-all-agree' : 'no-agreement' });
        out.stats.maybe++;
      }
    }
  }
  // truth check (I2, src/truthcheck.js): opts.truthcheck = a TruthCheck. Each text-anchored label must still match the text stored
  // with its record; 2-of-3 labels have no truth of their own (unchecked unless their source failed). Source = sense:day.
  if (opts.truthcheck) {
    try {
      const TC = require('./truthcheck'), byId = new Map(records.map((r) => [r.id, r]));
      const verify = TC.verifiers.anchorText(byId, (rec) => { const tx = rec.text || {}; return [tx.subtitle, soundTagText(tx.soundTag), tx.screen, tx.caption]; });
      for (const s of ['eye', 'ear']) out[s] = opts.truthcheck.run('sense-' + s, out[s], { verify, sourceOf: (x) => s + ':' + String(x.id).split('#')[0] }).kept;
    } catch (e) { /* the check never ends the night: unchecked */ }
  }
  return out;
}
const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();

// ---- seatbelt ------------------------------------------------------------------------------------------
// before/after: {V1, A1, VID1} percentages. A test present before but missing after counts as a failure.
function decideNight(before, after, opts = {}) {
  const maxDrop = opts.maxDrop == null ? SEAT_DROP : opts.maxDrop, tests = opts.tests || TESTS;
  const drops = {}, why = [];
  for (const k of tests) {
    if (!before || before[k] == null) continue;
    const a = after && after[k];
    if (a == null || !Number.isFinite(a)) { why.push(k + ' missing after'); drops[k] = null; continue; }
    drops[k] = +(before[k] - a).toFixed(3);
    if (drops[k] > maxDrop) why.push(k + ' dropped ' + drops[k]);
  }
  return { keep: why.length === 0, drops, reason: why.join('; ') || 'ok' };
}

// ---- ledger: practice manifests, replay, quarantine ---------------------------------------------------
class NightLedger {
  constructor(userData) { this.dir = path.join(userData, DIR); this.log = path.join(this.dir, 'nights.jsonl'); }
  manifestPath(night) { return path.join(this.dir, 'practice-' + night + '.json'); }
  // Writes the night's practice manifest for the trainer (sleepmlx sense_projector): features stay in the day files, by reference.
  writeManifest(night, practice, meta = {}) {
    fs.mkdirSync(this.dir, { recursive: true });
    const strip = (x) => ({ id: x.id, day: x.id.split('#')[0], off: x.ref.off, len: x.ref.len, shape: x.ref.shape, encoder: x.ref.encoder, label: x.label, kind: x.kind, from: x.from });
    const m = { night, created: Date.now(), featureDir: this.dir, dtype: 'float16', eye: practice.eye.map(strip), ear: practice.ear.map(strip),
      maybe_count: practice.maybe.length, stats: practice.stats, replay: this.keptNights(), ...meta };
    atomicWrite(this.manifestPath(night), m);
    return this.manifestPath(night);
  }
  entries() { try { return fs.readFileSync(this.log, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); } catch (_) { return []; } }
  keptNights() { return this.entries().filter((e) => e.kept).map((e) => e.night); }
  // Record the seatbelt outcome. A rolled-back night's manifest is renamed *.quarantined and never replayed.
  record(night, before, after, decision, extra = {}) {
    fs.mkdirSync(this.dir, { recursive: true });
    let quarantined = false;
    if (!decision.keep) {
      const p = this.manifestPath(night);
      if (fs.existsSync(p)) { fs.renameSync(p, p.replace(/\.json$/, '.quarantined.json')); quarantined = true; }
    }
    const e = { night, t: Date.now(), before, after, kept: decision.keep, drops: decision.drops, reason: decision.reason, quarantined, ...extra };
    fs.appendFileSync(this.log, JSON.stringify(e) + '\n');
    return e;
  }
  // Practice to replay tonight: kept nights only (older days to train, the newest day is tonight's).
  replay() {
    const out = { eye: [], ear: [] };
    for (const n of this.keptNights()) { const m = readJson(this.manifestPath(n)); if (m) { out.eye.push(...m.eye); out.ear.push(...m.ear); } }
    return out;
  }
  pinnedDays() { const s = new Set(); for (const n of this.keptNights()) { const m = readJson(this.manifestPath(n)); if (m) for (const x of [...m.eye, ...m.ear]) s.add(x.day); } return s; }
}

module.exports = { FeatureStore, buildPractice, decideNight, NightLedger, defaultLogic, encodeF16, decodeF16, toHalf, fromHalf,
  SEAT_DROP, TESTS, GATE_PREC, GATE_MIN, RAW_KEYS, DIR };
