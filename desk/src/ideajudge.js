'use strict';
// Ben Oct 28: "research Motes' ideas get judged by Claude (refute poor ones, explain why)". Once a day the new ideas go to Claude in one call;
// the verdicts land in userData/idea-verdicts.jsonl (sleep learns from them) and as feedback to the Mote.
const fs = require('fs');
const path = require('path');
const { readJsonl } = require('./ideas');

const URL = 'https://api.anthropic.com/v1/messages', MODEL = 'claude-haiku-5-5', MAX_PER_CALL = 10;
const SYSTEM = "You are a skeptical reviewer for Ben's project Premonition: a local desktop assistant, Glim, that fine-tunes its own small model overnight (\"sleep\") on his chats. Motes are Glim's helper agents. For each idea below, say whether it is good or poor. Refute poor ideas plainly. Keep each reason to 2 sentences at most, and make it concrete. Reply with ONLY a JSON array: [{\"id\": \"...\", \"verdict\": \"good\" or \"poor\", \"reason\": \"...\"}]";

function findKey(dir, env = process.env) {
  const k = env.ANTHROPIC_API_KEY || env.LEARNER_ANTHROPIC_API_KEY;
  if (k && k.trim()) return k.trim();
  try { return fs.readFileSync(path.join(dir, 'anthropic-key.txt'), 'utf8').trim(); } catch (e) { return ''; }
}

// ideas without a verdict yet
function pending(dir, now = Date.now()) {
  const done = new Set(readJsonl(path.join(dir, 'idea-verdicts.jsonl')).map((v) => v.id));
  return readJsonl(path.join(dir, 'ideas.jsonl')).filter((i) => i.id && typeof i.idea === 'string' && i.idea && !done.has(i.id) && !(now - Date.parse(i.ts) > MAX_AGE)); // idea older than 14 days: never judged
}
const MAX_AGE = 14 * 86400000;
const clean = (x, n) => String(typeof x === 'string' ? x : '').replace(/\s+/g, ' ').trim().slice(0, n); // ideas and reasons are untrusted text
const localDay = (d = new Date()) => { const p = (n) => String(n).padStart(2, '0'); return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()); };

// model text -> [{id, verdict, reason}] for the first [...] block; null when it is not valid
function parseVerdicts(text, ids) {
  const s = String(text || ''), a = s.indexOf('['), b = s.lastIndexOf(']');
  if (a < 0 || b < a) return null;
  let arr;
  try { arr = JSON.parse(s.slice(a, b + 1)); } catch (e) { return null; }
  if (!Array.isArray(arr)) return null;
  const seen = new Set(), out = [];
  for (const v of arr) {
    if (!v || !ids.has(v.id) || seen.has(v.id) || (v.verdict !== 'good' && v.verdict !== 'poor')) continue;
    seen.add(v.id); out.push({ id: v.id, verdict: v.verdict, reason: clean(v.reason, 240) });
  }
  return out;
}

// -> [{id, verdict, reason, helper, idea}] (empty on any problem)
async function judge({ ideas, key, fetchImpl }) {
  const batch = (ideas || []).slice(0, MAX_PER_CALL);
  if (!batch.length || !key) return [];
  const f = fetchImpl || fetch;
  const res = await f(URL, {
    method: 'POST', signal: AbortSignal.timeout(60000),
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: MODEL, max_tokens: 1500, system: SYSTEM, messages: [{ role: 'user', content: batch.map((i) => 'id ' + i.id + ' (Mote ' + i.helper + '): ' + i.idea).join('\n') }] })
  });
  if (!res || !res.ok) return [];
  const j = await res.json();
  const text = ((j && j.content) || []).map((c) => c && c.text || '').join('');
  const by = new Map(batch.map((i) => [i.id, i]));
  const got = parseVerdicts(text, new Set(by.keys()));
  if (!got) return [];
  const have = new Set(got.map((v) => v.id)); // sent but not answered: "skipped" so it leaves pending (no starvation)
  for (const i of batch) if (!have.has(i.id)) got.push({ id: i.id, verdict: 'skipped', reason: 'not judged' });
  return got.map((v) => ({ ...v, helper: by.get(v.id).helper, idea: by.get(v.id).idea }));
}

function appendVerdicts(dir, verdicts) {
  if (!verdicts.length) return;
  const ts = new Date().toISOString();
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(path.join(dir, 'idea-verdicts.jsonl'), verdicts.map((v) => JSON.stringify({ id: v.id, ts, day: localDay(), verdict: v.verdict, reason: v.reason, helper: v.helper, idea: v.idea })).join('\n') + '\n');
}

// "good: <idea> (<reason>); poor: ..." per Mote, <= 600 chars
function feedbackFor(verdicts) {
  const by = new Map();
  for (const v of verdicts) { if (v.verdict === 'skipped') continue; if (!by.has(v.helper)) by.set(v.helper, []); by.get(v.helper).push(v); }
  const out = new Map();
  for (const [name, vs] of by) out.set(name, vs.map((v) => v.verdict + ': ' + clean(v.idea, 160) + ' (' + clean(v.reason, 240) + ')').join('; ').slice(0, 600));
  return out;
}

// the whole daily job; onFeedback(name, text, verdicts) runs per Mote. Network errors are swallowed (tomorrow is another day).
async function runJudge({ dir, fetchImpl, env, onFeedback }) {
  const key = findKey(dir, env), ideas = pending(dir);
  if (!key || !ideas.length) return [];
  let v;
  try { v = await judge({ ideas, key, fetchImpl }); } catch (e) { return []; }
  if (!v.length) return [];
  try { appendVerdicts(dir, v); } catch (e) { return []; }
  try {
    for (const [name, text] of feedbackFor(v)) { try { onFeedback && onFeedback(name, text, v.filter((x) => x.helper === name && x.verdict !== 'skipped')); } catch (e) { /* ignore */ } }
  } catch (e) { /* ignore */ }
  return v;
}

module.exports = { clean, localDay, pending, judge, parseVerdicts, findKey, appendVerdicts, feedbackFor, runJudge, MODEL, SYSTEM };
