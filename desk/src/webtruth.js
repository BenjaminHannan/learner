'use strict';
// Option B: a fact that came from the web is VERIFIED only when 2+ sources on different registrable
// domains agree on it. Everything else is an "unverified note": it is never trained on and Glim may
// only attribute it ("one site claims X, I haven't confirmed it"). When unsure the answer is "unverified".
// The Python mirror is sleepmlx/webtruth.py; both are checked against test/fixtures/webtruth-cases.json.
const fs = require('fs');
const path = require('path');

const SECOND_LEVEL = new Set(['co', 'com', 'org', 'net', 'gov', 'edu', 'ac', 'or', 'ne', 'go']);
// Hosts where every subdomain is a different owner: the registrable domain keeps one more label.
const SHARED_HOSTS = ['github.io', 'blogspot.com', 'wordpress.com', 'netlify.app', 'vercel.app', 'herokuapp.com', 'pages.dev', 'web.app', 'firebaseapp.com', 'substack.com', 'medium.com'];

function registrableDomain(url) {
  let host;
  try { host = new URL(String(url)).hostname.toLowerCase().replace(/\.$/, ''); } catch (e) { return null; }
  if (!host) return null;
  if (/^[\d.]+$/.test(host) || host.includes(':')) return host;   // an IP address is its own domain
  const labels = host.split('.');
  if (labels.length <= 2) return host;
  const tail2 = labels.slice(-2).join('.');
  if (SHARED_HOSTS.includes(tail2)) return labels.slice(-3).join('.');
  if (labels[labels.length - 1].length === 2 && SECOND_LEVEL.has(labels[labels.length - 2])) return labels.slice(-3).join('.');
  return tail2;
}

// Lowercase letters and digits only, single spaces: "Luma Ferry => Dock => Mossbank." and "luma ferry => dock => mossbank" agree.
function normClaim(text) {
  return String(text == null ? '' : text).normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

const isCard = (n) => /^card$/i.test(String(n.topic || '').trim());
const isSkill = (n) => /^skill\s*:/i.test(String(n.topic || '').trim());

// "Subject => relation => Object" lines (one note may hold several, split by ; or newline).
function cardClaims(text) {
  const out = [];
  for (const line of String(text || '').split(/[\n;]/)) {
    const p = line.split('=>').map((x) => x.trim());
    if (p.length === 3 && p.every(Boolean)) out.push({ subject: p[0], relation: p[1], object: p[2] });
  }
  return out;
}
const hasWord = (hay, needle) => !!needle && (' ' + hay + ' ').includes(' ' + needle + ' ');

// Committed research rows from memory-provenance.jsonl. A damaged ledger reads as { ok: false }.
function readLedger(dir) {
  let body;
  const local = readLocalOrigin(dir);
  try { body = fs.readFileSync(path.join(dir, 'memory-provenance.jsonl'), 'utf8'); }
  catch (e) { return { ok: !!(e && e.code === 'ENOENT'), rows: [], local }; }
  const prepared = new Map(), committed = new Set();
  try {
    for (const line of body.split('\n')) {
      if (!line.trim()) continue;
      const row = JSON.parse(line);
      if (row.type === 'research-note-prepare') prepared.set(row.tx_id, row);
      else if (row.type === 'research-note-commit') committed.add(row.tx_id);
    }
  } catch (e) { return { ok: false, rows: [], local }; }
  return { ok: true, rows: [...prepared.values()].filter((r) => committed.has(r.tx_id)), local };
}

// Claims Ben told Glim himself, or that Glim saved in a run that never touched the web (memory-local-origin.jsonl).
// A claim listed here is not a web fact. Hand-written lines (ids starting with "h") are Ben's too.
function readLocalOrigin(dir) {
  const out = new Set();
  try {
    for (const line of fs.readFileSync(path.join(dir, 'memory-local-origin.jsonl'), 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { const r = JSON.parse(line); if (r && typeof r.claim_norm === 'string') out.add(r.claim_norm); } catch (e) { /* skip a bad line */ }
    }
  } catch (e) { /* none yet */ }
  return out;
}

// Status of one note. web: it came from (or may have come from) the web. verified: 2+ domains agree on THIS text.
function noteStatus(note, ledger) {
  const claim = normClaim(note.text), topic = String(note.topic || '').trim().toLowerCase();
  const mine = ledger.rows.filter((r) => r.note_id === note.id);
  const local = (ledger.local && ledger.local.has(claim)) || /^h/.test(String(note.id || ''));
  const web = mine.length > 0 || (!local && (isCard(note) || isSkill(note) || (!ledger.ok && /^m/.test(String(note.id || '')))));
  const st = { web, verified: false, domains: [], urls: [] };
  if (!web) return st;
  const claims = isCard(note) ? cardClaims(note.text) : [];
  if (!claims.length) return st;   // free text cannot be checked for agreement: stays unverified
  const objects = claims.map((c) => normClaim(c.object));
  const domains = new Set(), urls = new Set();
  for (const r of ledger.rows) {
    const a = r.attribution;
    if (!a || a.status !== 'attributed' || !a.source || r.claim_norm !== claim || String(r.topic || '').toLowerCase() !== topic) continue;
    const quote = normClaim(a.source.quote), dom = registrableDomain(a.source.url);
    if (!dom || !objects.every((o) => hasWord(quote, o))) continue;   // the page text must contain the answer
    domains.add(dom); urls.add(a.source.url);
  }
  st.domains = [...domains].sort(); st.urls = [...urls].sort();
  st.verified = domains.size >= 2;
  return st;
}

const unverifiedNotes = (notes, ledger) => notes.map((n) => ({ note: n, status: noteStatus(n, ledger) })).filter((x) => x.status.web && !x.status.verified).map((x) => x.note);

const HEDGE = /\b(claims?|claimed|claiming|says|said|according to|reportedly|allegedly|unconfirmed|unverified|not confirmed|haven'?t confirmed|have not confirmed|can'?t confirm|cannot confirm|not sure|unsure|one (?:site|source|page|website)|a (?:site|source|page|website)|might|may be|possibly|perhaps|supposedly|i read|i saw|i found)\b/i;

// Post-check: sentences of a reply that state an unverified card's answer as plain fact.
// strict: a hedge does not excuse it (used when deciding what sleep may train on).
function assertedClaims(answer, question, notes, strict) {
  const hits = [];
  const ans = String(answer || ''), ctx = normClaim(ans + ' ' + (question || ''));
  const sentences = ans.split(/(?<=[.!?])\s+|\n+/);
  for (const n of notes) {
    if (!isCard(n)) continue;
    for (const c of cardClaims(n.text)) {
      const obj = normClaim(c.object), subj = normClaim(c.subject);
      if (!hasWord(ctx, subj)) continue;
      for (const s of sentences) {
        if (hasWord(normClaim(s), obj) && (strict || !HEDGE.test(s))) { hits.push({ id: n.id, claim: c, sentence: s.trim() }); break; }
      }
    }
  }
  return hits;
}

module.exports = { registrableDomain, normClaim, cardClaims, readLedger, readLocalOrigin, noteStatus, unverifiedNotes, assertedClaims, isCard, isSkill, HEDGE };
