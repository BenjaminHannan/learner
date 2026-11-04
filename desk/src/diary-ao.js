'use strict';
// Always-on v2, phase 7: the diary (shown ONLY when Ben asks "Glim, what did you do?") and the always-on sleep handoff.
// Pure Node.
const fs = require('fs');
const path = require('path');

// "Glim, what did you do?" and close variants
const ASK = /^\s*(?:(?:hey|ok|okay|so)[,\s]+)?(?:glim[,\s]+)?(?:what\s+(?:did|have)\s+you\s+(?:do|done|been\s+(?:doing|up\s+to)|get\s+up\s+to|learn(?:ed|t)?)|what\s+(?:were|are)\s+you\s+(?:doing|up\s+to)|what\s+have\s+you\s+been\s+up\s+to|(?:show|read|tell)\s+me\s+(?:your|the)\s+diary|your\s+diary|what\s+happened\s+while\s+i\s+was\s+(?:away|gone|out))\b[^\n]{0,60}\??\s*$/i;
const isDiaryAsk = (text) => ASK.test(String(text || ''));

const mins = (m) => (m < 1 ? '<1 min' : m < 60 ? Math.round(m) + ' min' : (Math.round(m / 6) / 10) + ' h');

// activity: [{t, kind, ...}] from alwayson-state.json; truth: {maybe, confirmed, wrong, unsure}; since: ms
function recap({ activity, truth, since, now }) {
  now = now || Date.now(); since = since || now - 24 * 3600000;
  const a = (activity || []).filter((x) => x && x.t >= since);
  const lines = [];
  // time per topic (bored-mode Motes; each counts its own minutes)
  const per = {};
  for (const x of a) if (x.kind === 'mote' && x.ok && x.topic) per[x.topic] = (per[x.topic] || 0) + (Number(x.minutes) || 0.5);
  const top = Object.entries(per).sort((p, q) => q[1] - p[1]).slice(0, 4);
  if (top.length) lines.push('Thought about: ' + top.map(([t, m]) => t.slice(0, 50) + ' (' + mins(m) + ')').join(', ') + '.');
  // quiz score changes
  const quiz = a.filter((x) => x.kind === 'quiz');
  const byLevel = {};
  for (const q of quiz) { const k = q.topic + ' Lv' + q.level; byLevel[k] = byLevel[k] ? { ...byLevel[k], pct: q.pct, official: q.official } : { first: q.was != null ? q.was : q.pct, pct: q.pct, official: q.official }; }
  const qs = Object.entries(byLevel).map(([k, v]) => k + ' ' + (v.first !== v.pct ? v.first + '% → ' : '') + v.pct + '%' + (v.official ? '' : ' (not after a sleep yet)'));
  if (qs.length) lines.push('Quiz: ' + qs.join('; ') + '.');
  const written = a.filter((x) => x.kind === 'quiz-written');
  if (written.length) lines.push('Wrote ' + written.map((w) => w.questions + ' quiz questions on ' + w.topic + ' from ' + w.sites + ' sites').join('; ') + '.');
  // notes checked
  const notes = a.filter((x) => x.kind === 'note');
  const ok = notes.filter((x) => x.status === 'confirmed').length, wrong = notes.filter((x) => x.status === 'wrong');
  if (notes.length) lines.push('Checked notes on the web: ' + ok + ' confirmed, ' + wrong.length + ' wrong' + (wrong.length ? ' (e.g. "' + wrong[0].text.slice(0, 90) + '")' : '') + '.');
  if (truth) lines.push('Notes waiting for a check: ' + (truth.maybe || 0) + '; confirmed in total: ' + (truth.confirmed || 0) + '; corrections: ' + (truth.wrong || 0) + '.');
  // surprises
  const sur = a.filter((x) => x.kind === 'surprise');
  if (sur.length) lines.push('Surprised ' + sur.length + ' time' + (sur.length === 1 ? '' : 's') + (sur.length ? ', e.g. ' + sur.slice(-2).map((s) => '"' + String(s.what).slice(0, 70) + '"').join(', ') : '') + '.');
  const said = a.filter((x) => x.kind === 'said').length;
  if (said) lines.push('Spoke up by myself ' + said + ' time' + (said === 1 ? '' : 's') + '.');
  const drift = a.filter((x) => x.kind === 'thought').reduce((s, x) => s + (x.drift || 0), 0);
  if (drift) lines.push('Skipped ' + drift + ' thought' + (drift === 1 ? '' : 's') + ' that drifted off topic.');
  // sleep tune-ups (each part's seatbelt result, one line each, the latest per part)
  const parts = {}; for (const x of a.filter((y) => y.kind === 'sleep-part' && y.line)) parts[x.part || '?'] = x.line;
  for (const l of Object.values(parts)) lines.push(String(l).slice(0, 240));
  if (!lines.length) return 'Nothing yet since ' + new Date(since).toLocaleString() + ': I have not studied, checked notes, or been surprised.';
  return lines.join('\n');
}

// The always-on part of what the nightly sleep may learn from: confirmed notes, corrections and surprises. Never a `maybe`.
// (Confirmed notes and corrections are ALSO saved to memory.md, which the sleep worker already reads.)
function sleepHandoff({ truth, surprises, now }) {
  const cands = truth && truth.sleepCandidates ? truth.sleepCandidates() : [];
  const whenOf = (c) => { const n = truth && Array.isArray(truth.notes) ? truth.notes.find((x) => x.id === c.id) : null; return (n && (Number(n.settledAt) || Number(n.t))) || null; };
  return {
    at: now || Date.now(),
    // feeling time: every sleep candidate carries t (ms, or null = unknown for old records)
    confirmed: cands.filter((c) => c.kind === 'confirmed').map((c) => ({ t: whenOf(c), text: c.text, sources: (c.sources || []).map((s) => s.url).filter(Boolean) })),
    corrections: cands.filter((c) => c.kind === 'correction').map((c) => ({ t: whenOf(c), text: c.text, sources: (c.sources || []).map((s) => s.url).filter(Boolean) })),
    surprises: (surprises || []).slice(-50).map((s) => ({ t: s.t || null, stream: s.stream, text: s.what, kl: s.kl }))
  };
}
function writeHandoff(dir, h) {
  const f = path.join(dir, 'alwayson-sleep.json'), tmp = f + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(h, null, 1)); fs.renameSync(tmp, f);
  return f;
}

module.exports = { isDiaryAsk, recap, sleepHandoff, writeHandoff };
