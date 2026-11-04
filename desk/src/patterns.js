'use strict';
// Ingredient "patterns = rules + analogy" (ingredients-plan.md step 4), INTERIM version on the notes and observations.
// The real version runs on the filing-cabinet vectors once Experiment M1 passes; it should keep the same interface
// (add / recall / patternsFor / whatFollows / sleep / markShown), so the always-on loop does not change when the cabinet arrives.
//
// What is here (pure Node: no model, no network, no child process; it never requires llm/call/agent):
//   - a timeline: every observation, surprise and truth note with its timestamp (words only, private text dropped first)
//   - a SHAPE KEY per record: the same small embedder run on the record with names, numbers, times and places masked by rules
//     ("Maya texted at 4pm: practice moved to Field 3" -> "<NAME> texted at <TIME>: practice moved to <PLACE> <NUM>")
//   - recall with an extra shape channel (analogy): new names, same shape -> the old situations come back. It gets at most
//     `shapeSlots` (2) of the recall budget, after the plain channel's first k - 2, so ordinary recall is not crowded out.
//   - patterns, made in sleep BY FORMULA ONLY (Ben's rule: the model never writes rules or decides what to store):
//     deterministic leader clustering of the shape keys -> a cluster with >= 3 members on >= 2 different days is a pattern:
//     centroid, template (its most common masked form), member ids, and counts of what follows it within an hour (time order).
//   - pruning: a pattern that stops getting new members or recalls, or that is shown often and never comes true, is FILED
//     (kept on file, not recalled). Its members are never deleted.
//   - `maybe` / `unsure` truth notes in a pattern make the pattern `maybe`; `wrong` notes never join one. Patterns are not sleep
//     training data at all (the handoff does not carry them), so a `maybe` pattern cannot reach training.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { isPrivate } = require('./senses');
const TS = require('./timesense');

const DIM = 256;                 // embedder size: 256 signed hash buckets (no learned weights, ~0 bytes of model)
const MAX_ITEMS = 2000;          // timeline cap (oldest dropped first; patterns keep member ids that may then be gone)
const MAX_TEXT = 240;
const TAU = 0.65;                // shape cosine to join a cluster (picked on dev seed 1 of the synthetic days: 0.55–0.65 all found 10/10; 0.72 split one)
const MIN_MEMBERS = 3, MIN_DAYS = 2;
const FOLLOW_MS = 60 * 60000;    // "what follows" looks one hour ahead
const FOLLOW_MIN_MS = 60000;     // ... starting one minute later
const KEEP_DAYS = 14;            // no new member and no recall for 14 days -> filed
const USELESS_SHOWN = 10;        // shown 10+ times and never came true -> filed
const SAME_PATTERN = 0.85;       // a rebuilt cluster with centroid cosine >= this is the same pattern as last night's

// ---- masking (rules, cheap) ---------------------------------------------------------------------------------------------
const COMMON = new Set(('a an the this that these those there here i it its we you he she they my your our his her their me us them ' +
  'what when where why how who which whose if then so but and or not no yes ok okay hey hi hello thanks please sorry dear ' +
  'new old front open opened close closed error warning note reminder remember today tomorrow tonight yesterday now later soon ' +
  'meeting practice class dinner lunch breakfast homework game test quiz exam party plans plan call text email message chat ' +
  'just also still again maybe ben glim mote motes saved checked heard unexpected something nothing everything someone ' +
  'got get go going went came come see saw look looking watch watching read reading playing play started start finished done ' +
  'is was are were be been will would can could should did does do has have had let lets after before during while because ' +
  'up down out on off in at to from for with by of about into over under all any some every each one two three first last next ' +
  'mom dad grandma grandpa uncle aunt brother sister friend teacher coach doctor app apps file files page tab window windows ' +
  'safari chrome terminal finder messages music notes mail calendar settings discord steam youtube spotify zoom facetime').split(/\s+/));
const WEEKDAY = '(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)';
const MONTH = '(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)';
const RULES = [
  [/\bhttps?:\/\/\S+|\bwww\.\S+|\b[\w.+-]+@[\w-]+\.[\w.-]+/gi, ' <LINK> '],
  [/\b\d{4}-\d{2}-\d{2}(?:[t ]\d{1,2}:\d{2}(?::\d{2})?)?\b/gi, ' <TIME> '],
  [/\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b/g, ' <TIME> '],
  [/\b\d{1,2}(?::\d{2})?\s?(?:am|pm|a\.m\.|p\.m\.)(?=\W|$)/gi, ' <TIME> '],
  [/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, ' <TIME> '],
  [new RegExp('\\b' + MONTH + '\\.?\\s+\\d{1,2}(?:st|nd|rd|th)?\\b', 'gi'), ' <TIME> '],
  [new RegExp('\\b(?:next\\s+|this\\s+|last\\s+)?' + WEEKDAY + '(?:\\s+(?:morning|afternoon|evening|night))?\\b', 'gi'), ' <TIME> '],
  [/\b(?:noon|midnight|tonight|tomorrow(?:\s+(?:morning|afternoon|evening|night))?|yesterday|this\s+(?:morning|afternoon|evening))\b/gi, ' <TIME> '],
  [/[$£€]\s?\d[\d,]*(?:\.\d+)?/g, ' <NUM> '],
  [/\b\d+(?:[.,]\d+)*(?:st|nd|rd|th|%|k|m)?\b/gi, ' <NUM> ']
];
const NAME_VERB = /^(?:texted|messaged|emailed|called|said|says|asked|asks|wants|wanted|thinks|thought|told|sent|sends|posted|posts|shared|invited|is|was|will|has|had|got|needs|needed|owes|lent|bought|booked|forgot|lost|left|finished|started|cancelled|canceled|moved|added|complained|replied|wrote|liked|and)$/i;
const PREP_PLACE = /^(?:at|in|to|from|near|inside|outside)$/i;
// text -> masked text. Order: links, times/dates, numbers; then capitalised words: after a place preposition -> <PLACE>,
// otherwise -> <NAME>, unless it is a common word (so a sentence's first word stays). Runs of the same mask collapse into one.
function mask(text) {
  let s = ' ' + String(text || '').replace(/\s+/g, ' ') + ' ';
  for (const [re, to] of RULES) s = s.replace(re, to);
  const toks = s.trim().split(/\s+/).filter(Boolean);
  const out = [];
  for (let i = 0; i < toks.length; i++) {
    const raw = toks[i];
    if (/^<[A-Z]+>$/.test(raw)) { out.push(raw); continue; }
    const m = /^([^A-Za-z0-9<]*)([A-Za-z][A-Za-z'’.-]*[A-Za-z]|[A-Za-z])([^A-Za-z0-9]*)$/.exec(raw);
    if (!m) { out.push(raw); continue; }
    const [, pre, w, post] = m;
    const cap = /^[A-Z]/.test(w);
    const common = COMMON.has(w.toLowerCase().replace(/['’]s$/, ''));
    let tok = w;
    // a capitalised word that is not a common word is a name; after a place preposition it is a place.
    // (A common word keeps its own form wherever it stands: "Front app: Terminal", "Practice moved".)
    // A sentence's FIRST word is capitalised anyway, so there it counts as a name only when the next word reads like a name's
    // verb or a surname ("Maya texted", "Sam said", "Sam Lee", "Maya and Jo"); "Bus to", "Phone battery", "Plugged in" stay words.
    const prev = out.length ? out[out.length - 1] : '';
    const first = !prev || /[.!?:;]$/.test(prev);
    const next = toks[i + 1] || '';
    const nameish = !first || /^(?:[A-Z][a-z]+|and|&|,)$/.test(next.replace(/[,.:;!?]+$/, '')) && next !== next.toUpperCase() || NAME_VERB.test(next.replace(/[^A-Za-z]/g, '')) || /,$/.test(post);
    if (cap && !common && nameish) {
      const prevWord = prev.replace(/[^A-Za-z<>]/g, '');
      tok = PREP_PLACE.test(prevWord) || prevWord === '<PLACE>' ? '<PLACE>' : '<NAME>';
    }
    const piece = pre + tok + post;
    // collapse "<NAME> <NAME>" (first + last name) and "<PLACE> <PLACE>"
    if (/^<(?:NAME|PLACE)>$/.test(tok) && out.length && out[out.length - 1] === tok && !pre) { if (post) out[out.length - 1] = tok + post; }
    else out.push(piece);
  }
  return out.join(' ').replace(/(<(?:TIME|NUM|LINK)>)(?:\s+\1)+/g, '$1').replace(/\s+([,.;:!?])/g, '$1').trim();
}

// ---- the embedder: signed feature hashing of words + word pairs, sublinear tf, L2-normalised ------------------------------
function fnv(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; }
const tokens = (s) => String(s || '').toLowerCase().replace(/<(name|place|time|num|link)>/g, ' _$1_ ').replace(/[^a-z0-9_\s]/g, ' ').split(/\s+/).filter((w) => w && (w.length > 1 || /\d/.test(w)));
function embed(text, dim) {
  dim = dim || DIM;
  const v = new Float32Array(dim), tf = new Map();
  const t = tokens(text);
  const add = (f, w) => tf.set(f, (tf.get(f) || 0) + w);
  for (let i = 0; i < t.length; i++) { add('u:' + t[i], 1); if (i + 1 < t.length) add('b:' + t[i] + ' ' + t[i + 1], 1); }
  for (const [f, c] of tf) { const h = fnv(f); v[h % dim] += ((h >>> 31) ? -1 : 1) * (1 + Math.log(c)); }
  let n = 0; for (let i = 0; i < dim; i++) n += v[i] * v[i];
  n = Math.sqrt(n) || 1; for (let i = 0; i < dim; i++) v[i] /= n;
  return v;
}
const cos = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
// store a unit vector as base64 int8 (DIM bytes); good to ~0.01 cosine
function pack(v) { const b = Buffer.alloc(v.length); for (let i = 0; i < v.length; i++) b.writeInt8(Math.max(-127, Math.min(127, Math.round(v[i] * 127))), i); return b.toString('base64'); }
function unpack(s, dim) {
  try { const b = Buffer.from(String(s), 'base64'); if (b.length !== (dim || DIM)) return null; const v = new Float32Array(b.length); let n = 0; for (let i = 0; i < b.length; i++) { v[i] = b.readInt8(i) / 127; n += v[i] * v[i]; } n = Math.sqrt(n) || 1; for (let i = 0; i < v.length; i++) v[i] /= n; return v; } catch (e) { return null; }
}
const shapeKey = (text) => embed(mask(text));

// ---- patterns by formula (sleep) --------------------------------------------------------------------------------------
// items: [{id, t, text, m (masked), status}] -> { patterns: [...], clusters } . Deterministic: same items -> same patterns.
const TRUSTED = new Set(['seen', 'confirmed', 'ben']);
function median(a) { const s = a.slice().sort((x, y) => x - y); return s.length ? s[Math.floor((s.length - 1) / 2)] : 0; }
function buildPatterns(items, o) {
  o = o || {};
  const tau = o.tau || TAU, minMembers = o.minMembers || MIN_MEMBERS, minDays = o.minDays || MIN_DAYS, followMs = o.followMs || FOLLOW_MS;
  const its = (items || []).filter((x) => x && TS.validT(x.t) && typeof x.text === 'string' && x.status !== 'wrong')
    .slice().sort((a, b) => a.t - b.t || String(a.id).localeCompare(String(b.id)));
  // 1) identical masked forms share one vector; 2) leader clustering of the forms in order of first appearance
  const forms = new Map();
  for (const x of its) { const m = x.m || mask(x.text); if (!forms.has(m)) forms.set(m, { m, v: embed(m), items: [] }); forms.get(m).items.push(x); }
  const clusters = [];
  for (const f of forms.values()) {
    let best = null, bs = tau;
    for (const c of clusters) { const s = cos(f.v, c.dir); if (s >= bs) { bs = s; best = c; } }
    if (!best) { best = { sum: new Float32Array(f.v.length), dir: f.v, forms: [], items: [] }; clusters.push(best); }
    best.forms.push(f); for (const x of f.items) best.items.push(x);
    for (let i = 0; i < f.v.length; i++) best.sum[i] += f.v[i] * f.items.length;
    let n = 0; for (let i = 0; i < best.sum.length; i++) n += best.sum[i] * best.sum[i]; n = Math.sqrt(n) || 1;
    best.dir = Float32Array.from(best.sum, (x) => x / n);
  }
  const clusterOf = new Map();
  clusters.forEach((c, ci) => { c.items.sort((a, b) => a.t - b.t); for (const x of c.items) clusterOf.set(x, ci); });
  const isPat = clusters.map((c) => c.items.length >= minMembers && new Set(c.items.map((x) => TS.dayKey(x.t))).size >= minDays);
  const template = (c) => c.forms.slice().sort((a, b) => b.items.length - a.items.length)[0].m;
  const patterns = [];
  clusters.forEach((c, ci) => {
    if (!isPat[ci]) return;
    // what follows: for each member, every OTHER cluster seen within followMs after it (once per member; first delay)
    const fol = new Map();
    for (const x of c.items) {
      const seen = new Set();
      for (let j = its.indexOf(x) + 1; j < its.length && its[j].t - x.t <= followMs; j++) {
        if (its[j].t - x.t < FOLLOW_MIN_MS) continue;   // the same moment seen by two senses is not "what came next"
        const cj = clusterOf.get(its[j]); if (cj === ci || seen.has(cj)) continue; seen.add(cj);
        const e = fol.get(cj) || { n: 0, delays: [] }; e.n++; e.delays.push((its[j].t - x.t) / 60000); fol.set(cj, e);
      }
    }
    const follows = [...fol.entries()].filter(([, e]) => e.n >= 2 && e.n >= 0.3 * c.items.length)
      .sort((a, b) => b[1].n - a[1].n || median(a[1].delays) - median(b[1].delays)).slice(0, 3)
      .map(([cj, e]) => ({ template: template(clusters[cj]), count: e.n, of: c.items.length, medianMin: Math.round(median(e.delays) * 10) / 10, key: pack(clusters[cj].dir) }));
    const days = [...new Set(c.items.map((x) => TS.dayKey(x.t)))];
    patterns.push({
      template: template(c), key: pack(c.dir), members: c.items.map((x) => x.id), size: c.items.length, days: days.length,
      firstAt: c.items[0].t, lastMemberAt: c.items[c.items.length - 1].t,
      maybe: c.items.some((x) => !TRUSTED.has(x.status || 'seen')), follows
    });
  });
  return { patterns, clusters: clusters.length };
}

// ---- the store ----------------------------------------------------------------------------------------------------------
const atomicWrite = (file, obj) => { const tmp = file + '.' + process.pid + '.' + crypto.randomUUID().slice(0, 8) + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(obj)); fs.renameSync(tmp, file); };
const readJson = (file) => { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return null; } };

class Timeline {
  // o: { dir (userData; omitted = memory only), now, max, saveDelayMs, shapeSlots }
  constructor(o) {
    this.o = o || {}; this.now = this.o.now || Date.now; this.max = this.o.max || MAX_ITEMS;
    this.file = this.o.dir ? path.join(this.o.dir, 'timeline.json') : null;
    this.pfile = this.o.dir ? path.join(this.o.dir, 'patterns.json') : null;
    const j = (this.file && readJson(this.file)) || {};
    // old / damaged rows load as "time unknown" (t null), never a crash
    this.items = (Array.isArray(j.items) ? j.items : []).filter((x) => x && typeof x.text === 'string' && x.text.trim())
      .map((x) => ({ ...x, id: String(x.id || 'x' + crypto.randomUUID().slice(0, 8)), t: TS.timeOf(x), status: String(x.status || 'seen') }))
      .slice(-this.max);
    const p = (this.pfile && readJson(this.pfile)) || {};
    this.patterns = Array.isArray(p.patterns) ? p.patterns.filter((x) => x && typeof x.template === 'string' && x.key) : [];
    this.filed = Array.isArray(p.filed) ? p.filed.filter((x) => x && typeof x.template === 'string') : [];
    this.lastSleep = p.lastSleep || null;
    this.cache = new Map(); this.dirty = false; this.timer = null;
    this.byRef = new Map(); for (const x of this.items) if (x.ref) this.byRef.set(x.ref, x);
    this.shown = new Map();   // pattern id -> time it was last shown (for "did it come true")
  }
  vecs(x) {
    let c = this.cache.get(x.id);
    if (!c) { c = { plain: embed(x.text), shape: (x.k && unpack(x.k)) || embed(x.m || mask(x.text)) }; this.cache.set(x.id, c); }
    return c;
  }
  // add one record: {t, kind: obs|surprise|note, sense, text, status, ref}. -> the item, or null (empty, private, same as the last)
  add(r) {
    let text = String((r && r.text) || '').replace(/\s+/g, ' ').trim();
    if (!text || isPrivate(text)) return null;
    if (text.length > MAX_TEXT) text = text.slice(0, MAX_TEXT - 1) + '…';
    const last = this.items[this.items.length - 1];
    if (last && last.text === text && last.kind === (r.kind || 'obs')) return null;
    const t = TS.validT(r.t) ? r.t : this.now();
    const m = mask(text);
    const x = { id: 'e' + t.toString(36) + crypto.randomUUID().slice(0, 4), t, kind: r.kind || 'obs', sense: r.sense ? String(r.sense).slice(0, 20) : undefined, text, m, k: pack(embed(m)), status: String(r.status || 'seen') };
    if (r.ref) { x.ref = String(r.ref); this.byRef.set(x.ref, x); }
    this.items.push(x);
    if (this.items.length > this.max) for (const old of this.items.splice(0, this.items.length - this.max)) { this.cache.delete(old.id); if (old.ref) this.byRef.delete(old.ref); }
    this.onEvent(x);
    this.saveSoon();
    return x;
  }
  // truth notes (truthnotes.js) -> timeline rows, keeping their own time and status (maybe / confirmed / wrong / unsure)
  syncNotes(notes) {
    let n = 0;
    for (const note of notes || []) {
      if (!note || !note.id || !note.text) continue;
      const have = this.byRef.get(note.id);
      const text = note.status === 'wrong' && note.correction ? note.correction : note.text;
      if (have) { if (have.status !== note.status) { have.status = String(note.status); if (note.status === 'wrong' && note.correction) { have.text = String(note.correction).slice(0, MAX_TEXT); have.m = mask(have.text); have.k = pack(embed(have.m)); have.status = 'confirmed'; this.cache.delete(have.id); } this.saveSoon(); n++; } continue; }
      // a correction's text is our checked belief: it counts as confirmed; the wrong claim itself is not kept
      if (this.add({ t: TS.timeOf(note) || this.now(), kind: 'note', text, status: note.status === 'wrong' ? 'confirmed' : note.status, ref: note.id })) n++;
    }
    return n;
  }
  saveSoon() {
    this.dirty = true;
    if (!this.file || this.timer) return;
    const ms = this.o.saveDelayMs == null ? 30000 : this.o.saveDelayMs;
    if (ms <= 0) { this.flush(); return; }
    this.timer = setTimeout(() => { this.timer = null; this.flush(); }, ms); if (this.timer.unref) this.timer.unref();
  }
  flush() {
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    if (!this.file || !this.dirty) return false;
    try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); atomicWrite(this.file, { v: 1, items: this.items }); atomicWrite(this.pfile, { v: 1, patterns: this.patterns, filed: this.filed, lastSleep: this.lastSleep }); this.dirty = false; return true; } catch (e) { return false; }
  }
  // ---- recall (analogy) ----
  // -> [{item, via: 'plain'|'shape', score}] at most k; the shape channel gets at most shapeSlots of them.
  // o.before: only records older than this time (the loop excludes what it is already showing); o.exclude: Set of ids
  recall(query, o) {
    o = o || {};
    const k = o.k || 5, slots = Math.min(k, o.shapeSlots == null ? (this.o.shapeSlots == null ? 2 : this.o.shapeSlots) : o.shapeSlots);
    const q = String(query || ''); if (!q.trim()) return [];
    const qp = embed(q), qs = embed(mask(q));
    const pool = this.items.filter((x) => (!o.before || !TS.validT(x.t) || x.t < o.before) && !(o.exclude && o.exclude.has(x.id)) && x.status !== 'wrong');
    const plain = pool.map((x) => ({ item: x, via: 'plain', score: cos(qp, this.vecs(x).plain) })).filter((r) => r.score > (o.minPlain || 0.05)).sort((a, b) => b.score - a.score);
    const out = [], used = new Set();
    const take = (r) => { if (out.length < k && !used.has(r.item.id)) { used.add(r.item.id); out.push(r); return true; } return false; };
    for (const r of plain) { if (out.length >= k - slots) break; take(r); }
    if (slots > 0) {
      const shape = pool.map((x) => ({ item: x, via: 'shape', score: cos(qs, this.vecs(x).shape) })).filter((r) => r.score >= (o.minShape || 0.5)).sort((a, b) => b.score - a.score);
      let n = 0; for (const r of shape) { if (n >= slots) break; if (take(r)) n++; }
    }
    for (const r of plain) { if (out.length >= k) break; take(r); }
    return out;
  }
  // the active patterns whose shape matches the query (cosine >= min), best first; each is counted as a recall hit
  patternsFor(query, o) {
    o = o || {};
    const q = String(query || ''); if (!q.trim() || !this.patterns.length) return [];
    const qs = embed(mask(q));
    const r = this.patterns.map((p) => ({ p, score: cos(qs, unpack(p.key) || new Float32Array(DIM)) })).filter((x) => x.score >= (o.min || 0.6)).sort((a, b) => b.score - a.score).slice(0, o.k || 2);
    if (o.mark !== false) for (const x of r) this.markShown(x.p);
    return r;
  }
  markShown(p) { const t = this.now(); p.hits = (p.hits || 0) + 1; p.lastHitAt = t; this.shown.set(p.id, t); this.saveSoon(); }
  // "what usually happens after X?" -> {pattern, follow} or null
  // A pattern matches by shape, or (for Ben's own wording, "after someone texts that practice moved") by the words of its template.
  whatFollows(query) {
    let best = this.patternsFor(query, { k: 1, mark: false })[0];
    if (!best) {
      const r = this.patterns.map((p) => ({ p, score: TS.matchScore(query, p.template.replace(/<[A-Z]+>/g, ' ')) })).filter((x) => x.score >= 0.5).sort((a, b) => b.score - a.score || b.p.size - a.p.size);
      best = r[0];
    }
    if (!best || !best.p.follows || !best.p.follows.length) return best ? { pattern: best.p, follow: null } : null;
    return { pattern: best.p, follow: best.p.follows[0] };
  }
  // a new record: does it make a recently shown pattern's prediction come true? (that is "recall through it was used")
  onEvent(x) {
    if (!this.shown.size) return;
    const v = this.vecs(x).shape;
    for (const p of this.patterns) {
      const at = this.shown.get(p.id); if (at == null || x.t - at > FOLLOW_MS || x.t < at) continue;
      if ((p.follows || []).some((f) => { const fv = unpack(f.key); return fv && cos(v, fv) >= TAU; })) { p.confirmed = (p.confirmed || 0) + 1; p.lastConfirmedAt = x.t; this.shown.delete(p.id); }
    }
  }
  // ---- sleep: rebuild patterns by formula, keep their history, file away the ones that stopped earning their place ----
  // -> {patterns, made, kept, filed, revived, clusters, ms}. Never calls a model (there is none to call in this file).
  sleep(o) {
    o = o || {}; const t0 = Date.now(), now = this.now();
    const built = buildPatterns(this.items, o);
    const old = this.patterns.concat(this.filed.map((p) => ({ ...p, wasFiled: true })));
    const oldV = old.map((p) => unpack(p.key));
    const next = [], filed = this.filed.slice(); let made = 0, revived = 0, filedN = 0;
    const taken = new Set();
    for (const p of built.patterns) {
      const v = unpack(p.key);
      let match = -1, bs = SAME_PATTERN;
      oldV.forEach((ov, i) => { if (ov && !taken.has(i)) { const s = cos(v, ov); if (s >= bs) { bs = s; match = i; } } });
      const prev = match >= 0 ? old[match] : null; if (match >= 0) taken.add(match);
      const q = { ...p, id: prev ? prev.id : 'p' + crypto.createHash('sha1').update(p.key).digest('hex').slice(0, 10), createdAt: prev ? prev.createdAt : now, hits: prev ? prev.hits || 0 : 0, lastHitAt: prev ? prev.lastHitAt || null : null, confirmed: prev ? prev.confirmed || 0 : 0, lastConfirmedAt: prev ? prev.lastConfirmedAt || null : null, shownAtFiling: prev ? prev.shownAtFiling || 0 : 0 };
      if (!prev) made++;
      // still earning its place? new members or recall hits within KEEP_DAYS, and not "shown a lot, never came true"
      const recent = now - KEEP_DAYS * 86400000;
      const fresh = q.lastMemberAt >= recent || (q.lastHitAt && q.lastHitAt >= recent);
      const useless = (q.hits - q.shownAtFiling) >= USELESS_SHOWN && !q.confirmed;
      if (prev && prev.wasFiled) {
        // a filed pattern comes back only when it got a new (recent) member since it was filed
        if (q.lastMemberAt > (prev.lastMemberAt || 0) && q.lastMemberAt >= now - KEEP_DAYS * 86400000 && !useless) { const i = filed.findIndex((f) => f.id === prev.id); if (i >= 0) filed.splice(i, 1); revived++; delete q.filedAt; next.push(q); }
        else { const i = filed.findIndex((f) => f.id === prev.id); if (i >= 0) filed[i] = { ...q, filedAt: prev.filedAt }; }
        continue;
      }
      if (!fresh || useless) { filed.push({ ...q, filedAt: now, why: useless ? 'shown ' + q.hits + ' times, never came true' : 'no new member or recall for ' + KEEP_DAYS + ' days', shownAtFiling: q.hits }); filedN++; continue; }
      next.push(q);
    }
    // an active pattern whose cluster vanished (its members aged out of the timeline) is filed too
    this.patterns.forEach((p, i) => { if (!taken.has(i)) { filed.push({ ...p, filedAt: now, why: 'its members are no longer on the timeline' }); filedN++; } });
    this.patterns = next; this.filed = filed.slice(-300);
    this.lastSleep = { at: now, made, kept: next.length, filed: filedN, revived, clusters: built.clusters, items: this.items.length, ms: Date.now() - t0 };
    this.dirty = true; this.flush();
    return { ...this.lastSleep, patterns: next };
  }
}

// "Pattern (seen 6×): <NAME> texted: plans moved → usually then <NAME> changed plans (within ~40 min, 5 of 6)."
function patternLine(p) {
  if (!p) return '';
  const f = p.follows && p.follows[0];
  const mins = f ? (f.medianMin < 1 ? 'within a minute' : f.medianMin < 90 ? 'within ~' + Math.max(1, Math.round(f.medianMin)) + ' min' : 'within ~' + Math.round(f.medianMin / 60) + ' h') : '';
  return ('Pattern (seen ' + p.size + '×' + (p.maybe ? ', maybe' : '') + '): ' + p.template.slice(0, 90) + (f ? ' → usually then: ' + f.template.slice(0, 80) + ' (' + mins + ', ' + f.count + ' of ' + f.of + ')' : '')).slice(0, 240);
}

module.exports = { mask, embed, cos, pack, unpack, shapeKey, buildPatterns, Timeline, patternLine, DIM, TAU, MIN_MEMBERS, MIN_DAYS, FOLLOW_MS, KEEP_DAYS, USELESS_SHOWN };
