'use strict';
// "Important updates" dashboard: what Ben has corrected. Today that is one thing: "these emails are not junk" (the "Put all back"
// button on the hidden-junk row). It is a tiny JSON file in userData, so the correction survives restarts. The dashboard only hides
// mail in its own list (nothing in the mailbox is touched), so "putting back" simply stops hiding.
//   { "notJunk": ["<subject>|<sender>", ...] }
// mailKey() is the same key the dashboard uses to tell one email from another.
const fs = require('fs');
const path = require('path');

const FILE = 'dashboard-overrides.json';
const MAX_KEYS = 500;   // old corrections drop off first; the list never grows without a limit

const mailKey = (m) => String((m && m.subject) || '') + '|' + String((m && m.sender) || '');
const cleanKeys = (keys) => [...new Set((Array.isArray(keys) ? keys : []).filter((k) => typeof k === 'string' && k.length > 1 && k.length < 400))];

function load(dir) {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(dir, FILE), 'utf8'));
    return { notJunk: cleanKeys(j && j.notJunk) };
  } catch (e) { return { notJunk: [] }; }
}

function save(dir, st) {
  fs.mkdirSync(dir, { recursive: true });
  const f = path.join(dir, FILE), tmp = f + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify({ notJunk: cleanKeys(st.notJunk).slice(-MAX_KEYS) }, null, 1));
  fs.renameSync(tmp, f);
}

// op: 'unhide' (these emails are not junk) | 'rehide' (undo that). Returns { ok, notJunk } or { error }.
function apply(dir, op, keys) {
  const ks = cleanKeys(keys);
  if (!ks.length) return { error: 'nothing to change' };
  const st = load(dir);
  if (op === 'unhide') st.notJunk = cleanKeys(st.notJunk.concat(ks));
  else if (op === 'rehide') { const gone = new Set(ks); st.notJunk = st.notJunk.filter((k) => !gone.has(k)); }
  else return { error: 'unknown change' };
  try { save(dir, st); } catch (e) { return { error: 'could not save: ' + String((e && e.message) || e) }; }
  return { ok: true, notJunk: st.notJunk };
}

module.exports = { FILE, mailKey, load, save, apply };
