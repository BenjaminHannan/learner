'use strict';
// Truth check before sleep (track I2, 2026-11-04). Before a nightly learner trains on logged labels, each label is compared with
// something TRUE: an executor re-run, the puzzle generator's answer, Ben's own facts, a recompute from raw text or logs, or the game's
// rulebook / server log. Never a model's opinion. Automatic and mathematical: fixed rules, no model calls.
//
// Rule (toy-proven, ~/learner-ops/premonition-sleeplab-i2 MARKS/RESULTS-truthcheck-v1: PASS 3/3 seeds, 2 label types, 30 and 60 %
// poison scattered or by whole sources -> wrong labels in training <= 0.7 %, clean labels kept >= 92.9 %, clean nights unchanged):
//   rows are grouped by SOURCE; per row the verifier says ok / bad / none (no truth for this row).
//   checked = ok + bad. TRUSTED if checked >= MIN_CHECKED and bad / checked <= MAX_FAIL -> train ok + none rows, drop bad rows.
//   Too many fails -> train the verified-ok rows only.
//   Too few truths (checked < MIN_CHECKED): no fail at all -> keep everything (unchecked, logged); any fail -> ok rows only.
//   (This small-source branch never ran in the toy: its effect is untested.)
// Toy limit: unverifiable rows of a poisoned source are dropped too, so clean labels kept ~ truth coverage. Poison that hits only rows
// without a truth can't be seen.
// Setting: settings.truthCheck (default ON). A verifier that throws counts as "no truth"; a crash in check() returns the rows unchanged.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MIN_CHECKED = 10, MAX_FAIL = 0.10, LOG = 'truthcheck-log.jsonl', MAX_LOG_LINES = 2000;
const norm = (v) => (v === true || v === 'ok' ? 'ok' : v === false || v === 'bad' ? 'bad' : 'none');
const J = (x) => JSON.stringify(x);

// rows -> { kept, dropped, verdict, sources, stats }. o: { verify(row), sourceOf(row), minChecked, maxFail, sample, seed }
function check(rows, o) {
  o = o || {}; rows = Array.isArray(rows) ? rows : [];
  const minChecked = o.minChecked == null ? MIN_CHECKED : o.minChecked, maxFail = o.maxFail == null ? MAX_FAIL : o.maxFail;
  const sourceOf = o.sourceOf || (() => 'all'), verify = o.verify || (() => 'none');
  const srcOf = (r) => { try { return String(sourceOf(r)); } catch (e) { return '?'; } };
  const by = new Map(), src = rows.map(srcOf);
  src.forEach((s, i) => { if (!by.has(s)) by.set(s, []); by.get(s).push(i); });
  const verdict = new Array(rows.length).fill('none'), sources = {};
  let seed = (o.seed == null ? 12345 : o.seed) >>> 0; const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  for (const [s, idx] of by) {
    let pick = idx;
    if (o.sample && idx.length > o.sample) { const a = idx.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } pick = a.slice(0, o.sample); }
    let ok = 0, bad = 0;
    for (const i of pick) { let v; try { v = norm(verify(rows[i])); } catch (e) { v = 'none'; } verdict[i] = v; if (v === 'ok') ok++; else if (v === 'bad') bad++; }
    const checked = ok + bad, fail = checked ? bad / checked : null;
    const mode = checked >= minChecked ? (fail <= maxFail ? 'trusted' : 'failed') : (bad === 0 ? 'unchecked' : 'failed');
    sources[s] = { n: idx.length, ok, bad, none: idx.length - checked, fail, mode, trusted: mode !== 'failed', kept: 0, dropped: 0 };
  }
  const kept = [], dropped = [];
  rows.forEach((r, i) => { const S = sources[src[i]], v = verdict[i]; if (v === 'ok' || (v === 'none' && S.trusted)) { kept.push(r); S.kept++; } else { dropped.push(r); S.dropped++; } });
  const stats = { n: rows.length, kept: kept.length, ok: 0, bad: 0, none: 0, sources: by.size, failed: 0, unchecked: 0 };
  for (const S of Object.values(sources)) { stats.ok += S.ok; stats.bad += S.bad; stats.none += S.none; if (S.mode === 'failed') stats.failed++; if (S.mode === 'unchecked') stats.unchecked++; }
  return { kept, dropped, verdict, sources, stats };
}

// ---- verifiers (each: row -> ok | bad | none) ------------------------------------------------------------------------------------
const verifiers = {
  // recompute a category from the raw text kept with the row (row.raw = {app, title}); no raw (private window, old row) -> none
  category(categorize, field) { const f = field || 'cat'; return (row) => (row && row.raw && (row.raw.app || row.raw.title) ? categorize(row.raw.app, row.raw.title) === row[f] : null); },
  // the game's own rulebook ("game server"): our move -> step/apply(s, m) must equal s2; opponent -> s2 must be a legal reply
  game(games) {
    return (row) => {
      const g = row && games[row.game]; if (!g || !row.s || !row.s2) return null;
      if (row.who === 'them') return typeof g.replies === 'function' ? g.replies(row.s).some((t) => J(t) === J(row.s2)) : null;
      const t = g.apply && g.replies ? g.apply(row.s, row.m) : g.step(row.s, row.m);
      return !!t && J(t) === J(row.s2);
    };
  },
  // text-anchored sense practice: the label must be one of the text pieces stored with its feature record (records by id)
  // textsOf(rec) -> the record's text pieces (default: subtitle, screen, caption, soundTag)
  anchorText(recordsById, textsOf) {
    const get = (id) => (recordsById instanceof Map ? recordsById.get(id) : recordsById && recordsById[id]);
    const texts = textsOf || ((rec) => { const tx = rec.text || {}; return [tx.subtitle, tx.screen, tx.caption, tx.soundTag]; });
    return (item) => {
      if (!item || item.from !== 'text') return null;   // 2-of-3 labels have no truth of their own
      const rec = get(item.id); if (!rec || !rec.text) return null;
      const pieces = texts(rec).filter((x) => typeof x === 'string' && x).map((x) => x.trim().toLowerCase());
      return pieces.includes(String(item.label || '').trim().toLowerCase());
    };
  },
  // executor / puzzle-generator truth kept as a sha256 of the normalised answer (stuck.js): row.answer vs row.truth {norm, value}
  answerHash(normFns) {
    return (row) => {
      const t = row && row.truth; if (!t || !t.value || !normFns[t.norm] || row.answer == null) return null;
      return crypto.createHash('sha256').update(normFns[t.norm](row.answer), 'utf8').digest('hex') === t.value;
    };
  },
  // Ben's own facts: notes [{subj, rel, obj, status}]; `maybe` / `unsure` notes are never a truth. A row {subj, rel, obj} that matches a
  // fact is ok; same subject + relation with another object is bad; anything else none.
  benFacts(notes) {
    const k = (s) => String(s || '').trim().toLowerCase(), m = new Map();
    for (const n of notes || []) { if (!n || n.status === 'maybe' || n.status === 'unsure' || n.status === 'wrong') continue; const key = k(n.subj) + '|' + k(n.rel); (m.get(key) || m.set(key, new Set()).get(key)).add(k(n.obj)); }
    return (row) => { const s = row && m.get(k(row.subj) + '|' + k(row.rel)); return s ? s.has(k(row.obj)) : null; };
  }
};

// ---- the night runner: one log line per learner (source) per night -----------------------------------------------------------------
class TruthCheck {
  // o: { dir (userData; omit = no file), enabled (default true), now }
  constructor(o) { o = o || {}; this.dir = o.dir || null; this.enabled = o.enabled !== false; this.now = o.now || Date.now; this.lines = []; }
  // rows of one learner -> { kept, rec, line }. o: verify, sourceOf, minChecked, maxFail, sample. Never throws.
  run(name, rows, o) {
    rows = Array.isArray(rows) ? rows : [];
    if (!this.enabled) return this.write({ part: name, mode: 'off', n: rows.length, kept: rows.length }, rows, name + ': truth check off (' + rows.length + ' labels unchecked)');
    let r; try { r = check(rows, o); } catch (e) { return this.write({ part: name, mode: 'error', why: String(e && e.message || e), n: rows.length, kept: rows.length }, rows, name + ': truth check error, labels unchecked'); }
    const s = r.stats, failed = Object.entries(r.sources).filter(([, S]) => S.mode === 'failed').map(([k]) => k).slice(0, 10);
    const rec = { part: name, mode: 'checked', n: s.n, kept: s.kept, ok: s.ok, bad: s.bad, none: s.none, sources: s.sources, failed: s.failed, unchecked: s.unchecked, failedSources: failed };
    const line = name + ': truth check ' + s.ok + ' right, ' + s.bad + ' wrong, ' + s.none + ' no truth; trained ' + s.kept + ' of ' + s.n + (s.failed ? '; ' + s.failed + ' of ' + s.sources + ' sources failed (only verified labels kept)' : '');
    const out = this.write(rec, r.kept, line); out.result = r; return out;
  }
  // a learner with no separate truth: logged so the morning shows it was not checked
  note(name, why) { return this.write({ part: name, mode: 'no-truth', why }, null, name + ': no truth check (' + why + ')'); }
  write(rec, kept, line) {
    rec = { t: this.now(), ...rec }; this.lines.push(line);
    if (this.dir) { try { fs.mkdirSync(this.dir, { recursive: true }); const f = path.join(this.dir, LOG); fs.appendFileSync(f, J(rec) + '\n'); trim(f); } catch (e) { /* log only */ } }
    return { kept, rec, line };
  }
}
function trim(f) { try { const st = fs.statSync(f); if (st.size < 400000) return; const ls = fs.readFileSync(f, 'utf8').split('\n').filter(Boolean); if (ls.length <= MAX_LOG_LINES) return; fs.writeFileSync(f + '.tmp', ls.slice(-MAX_LOG_LINES).join('\n') + '\n'); fs.renameSync(f + '.tmp', f); } catch (e) { /* keep */ } }
// the shared instance for a night, from the settings (settings.truthCheck !== false)
const forSettings = (settings, dir, now) => new TruthCheck({ dir, enabled: !settings || settings.truthCheck !== false, now });

module.exports = { check, verifiers, TruthCheck, forSettings, MIN_CHECKED, MAX_FAIL, LOG };
