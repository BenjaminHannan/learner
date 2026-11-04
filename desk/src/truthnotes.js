'use strict';
// Always-on v2, phase 5: truth-seeking notes. Every note that comes from Glim's own thinking or learning is stored as `maybe`
// (userData/truth-notes.json, NOT the memory sleep trains on). A check step searches the web, looks for 2 INDEPENDENT sources
// (different sites), and asks a judge whether each one supports or contradicts the note:
//   2+ independent sources support it      -> `confirmed`  -> saved to memory (sleep's input)
//   2+ independent sources contradict it   -> `wrong`      -> kept as a correction "I thought X; actually Y" -> saved to memory
//   otherwise (after 3 tries)              -> `unsure`     -> never reaches sleep
// Only `confirmed` notes and corrections are ever handed to save(); a `maybe` note can never reach the sleep candidates.
// Ben can settle a note himself (benSays). Pure Node: search / judge / save are injected (tests use fakes, no network).
const fs = require('fs');
const path = require('path');
const { isPrivate } = require('./senses');

const MAX_NOTES = 500, MAX_TRIES = 3, NEED = 2;

// "https://www.en.wikipedia.org/wiki/x" -> "wikipedia.org"; "news.bbc.co.uk" -> "bbc.co.uk" (independence = different site)
function siteOf(url) {
  let h = ''; try { h = new URL(url).hostname.toLowerCase(); } catch (e) { return ''; }
  h = h.replace(/^www\d?\./, '');
  const parts = h.split('.');
  if (parts.length <= 2) return h;
  const sld2 = /^(?:co|com|org|net|gov|ac|edu)$/.test(parts[parts.length - 2]) && parts[parts.length - 1].length === 2;
  return parts.slice(sld2 ? -3 : -2).join('.');
}
// DuckDuckGo text from src/tools/web.js ("1. title\n   url\n   snippet") -> [{title, url, snippet}]
function parseResults(text) {
  if (Array.isArray(text)) return text;
  const out = []; const lines = String(text || '').split('\n');
  for (let i = 0; i < lines.length; i++) {
    const m = /^\s*\d+\.\s+(.*)$/.exec(lines[i]); if (!m) continue;
    const url = (lines[i + 1] || '').trim(); const sn = (lines[i + 2] || '').trim();
    if (/^https?:\/\//.test(url)) out.push({ title: m[1].trim(), url, snippet: /^\d+\.\s/.test(sn) || /^https?:/.test(sn) ? '' : sn });
  }
  return out;
}
// a judge that needs no model: the snippet supports the claim when most of its content words appear in it (it can never say
// "contradicts", so on its own it only confirms or leaves a note unsure). main uses the local model as the judge, with this as fallback.
const STOP = new Set('the a an of and or to in on at by for with is are was were be been it its this that as from which who what when where how than then into about over has have had not no can will'.split(' '));
const words = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w));
function lexicalJudge(claim, src) {
  const cw = [...new Set(words(claim))]; if (!cw.length) return { verdict: 'unclear' };
  const sw = new Set(words(src.title + ' ' + src.snippet));
  const hit = cw.filter((w) => sw.has(w)).length / cw.length;
  return { verdict: hit >= 0.7 ? 'supports' : 'unclear' };
}

class TruthNotes {
  // o: { dir, now, search(query, signal) -> text|[{title,url,snippet}], judge(claim, src, signal) -> {verdict, correction},
  //      save(text, topic) -> {ok} (the memory sleep reads), onSettled(note), log }
  constructor(o) {
    this.o = o || {}; this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.file = this.o.dir ? path.join(this.o.dir, 'truth-notes.json') : null;
    this.notes = [];
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (Array.isArray(j.notes)) this.notes = j.notes.slice(-MAX_NOTES); } catch (e) { /* none */ } }
    this.checking = null;
  }
  save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const tmp = this.file + '.tmp'; fs.writeFileSync(tmp, JSON.stringify({ notes: this.notes })); fs.renameSync(tmp, this.file); } catch (e) { /* kept in memory */ } }
  // a new note from thinking / learning: always `maybe`. -> the note, or null (empty, private, duplicate)
  add(text, meta) {
    const t = String(text || '').replace(/\s+/g, ' ').trim().slice(0, 300);
    if (t.length < 8 || isPrivate(t)) return null;
    if (this.notes.some((n) => n.text.toLowerCase() === t.toLowerCase())) return null;
    meta = meta || {};
    const n = { id: 'n' + this.now().toString(36) + Math.random().toString(36).slice(2, 5), text: t, status: 'maybe', topic: String(meta.topic || '').slice(0, 120), from: String(meta.from || 'thinking'), t: this.now(), tries: 0, sources: [] };
    this.notes.push(n); if (this.notes.length > MAX_NOTES) this.notes.splice(0, this.notes.length - MAX_NOTES);
    this.save();
    return n;
  }
  next() { return this.notes.find((n) => n.status === 'maybe' && n.tries < MAX_TRIES) || null; }
  // check one note against the web. -> the note (status may have changed)
  async check(n, signal) {
    if (!n || n.status !== 'maybe') return n;
    this.checking = n.id; n.tries++;
    try {
      const raw = await this.o.search(n.text, signal);
      const results = parseResults(raw).filter((r) => r && r.url && !isPrivate(r.snippet || ''));
      const support = new Map(), contra = new Map();
      for (const r of results.slice(0, 6)) {
        if (signal && signal.aborted) break;
        const site = siteOf(r.url); if (!site || support.has(site) || contra.has(site)) continue;
        let v = { verdict: 'unclear' };
        try { v = (this.o.judge ? await this.o.judge(n.text, r, signal) : lexicalJudge(n.text, r)) || v; } catch (e) { if (signal && signal.aborted) throw e; v = lexicalJudge(n.text, r); }
        if (v.verdict === 'supports') support.set(site, { url: r.url, site });
        else if (v.verdict === 'contradicts') contra.set(site, { url: r.url, site, correction: v.correction ? String(v.correction).slice(0, 240) : '' });
        if (support.size >= NEED || contra.size >= NEED) break;
      }
      if (signal && signal.aborted) { n.tries--; return n; }
      if (support.size >= NEED && contra.size < NEED) this.settle(n, 'confirmed', [...support.values()]);
      else if (contra.size >= NEED) {
        const c = [...contra.values()]; const fix = (c.find((x) => x.correction) || {}).correction || '';
        this.settle(n, 'wrong', c, fix);
      } else if (n.tries >= MAX_TRIES) { n.status = 'unsure'; n.settledAt = this.now(); this.save(); }
      else this.save();
    } catch (e) {
      if (signal && signal.aborted) n.tries--;
      else this.log('truth: check failed', String(e && e.message || e));
      this.save();
    } finally { this.checking = null; }
    return n;
  }
  // confirmed / wrong: saved to the memory sleep reads. A wrong note is kept as a correction.
  settle(n, status, sources, correction) {
    n.status = status; n.sources = (sources || []).map((s) => ({ url: s.url, site: s.site })); n.settledAt = this.now();
    if (status === 'wrong') n.correction = correction ? 'I thought ' + n.text.replace(/[.\s]+$/, '') + '; actually ' + correction.replace(/^actually,?\s*/i, '') : 'I thought ' + n.text.replace(/[.\s]+$/, '') + ', but sources say otherwise.';
    this.save();
    const text = status === 'confirmed' ? n.text : n.correction;
    try { const r = this.o.save && this.o.save(text, status === 'confirmed' ? (n.topic ? 'skill: ' + n.topic.slice(0, 40) : 'checked') : 'correction'); n.saved = !!(r && r.ok); } catch (e) { n.saved = false; }
    this.save();
    try { this.o.onSettled && this.o.onSettled(n); } catch (e) { /* listener */ }
  }
  // Ben settles a note himself: right=true -> confirmed; right=false -> wrong (with his correction, if he gave one)
  benSays(id, right, correction) {
    const n = this.notes.find((x) => x.id === id); if (!n) return null;
    this.settle(n, right ? 'confirmed' : 'wrong', [{ url: '', site: 'Ben' }], correction);
    return n;
  }
  // what may go to sleep: confirmed notes and corrections only (never `maybe` or `unsure`)
  sleepCandidates() { return this.notes.filter((n) => n.status === 'confirmed' || n.status === 'wrong').map((n) => ({ id: n.id, text: n.status === 'confirmed' ? n.text : n.correction, kind: n.status === 'confirmed' ? 'confirmed' : 'correction', sources: n.sources })); }
  counts() { const c = { maybe: 0, confirmed: 0, wrong: 0, unsure: 0 }; for (const n of this.notes) c[n.status] = (c[n.status] || 0) + 1; return c; }
}

module.exports = { TruthNotes, siteOf, parseResults, lexicalJudge, NEED, MAX_TRIES };
