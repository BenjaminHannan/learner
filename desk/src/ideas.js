'use strict';
// Ben Oct 28: Motes put ideas worth testing in their reports as "IDEA: ..." lines; they are collected in userData/ideas.jsonl and judged once a day (ideajudge.js).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MAX_IDEAS = 8, MAX_LEN = 300, MAX_PENDING = 20;

// report text -> [{idea}]: each "IDEA: ..." line, trimmed, <= 300 chars, at most 8, no repeats.
function parseIdeas(report) {
  const out = [], seen = new Set();
  for (const line of String(report || '').split(/\r?\n/)) {
    const m = /^\s*(?:[-*]\s*)?(?:\*\*)?IDEA:(?:\*\*)?\s*(.+)$/i.exec(line);
    if (!m) continue;
    const idea = m[1].trim().slice(0, MAX_LEN).trim(), k = idea.toLowerCase();
    if (!idea || seen.has(k)) continue;
    seen.add(k); out.push({ idea });
    if (out.length >= MAX_IDEAS) break;
  }
  return out;
}

function readJsonl(file) {
  let txt = '';
  try { txt = fs.readFileSync(file, 'utf8'); } catch (e) { return []; }
  const out = [];
  for (const l of txt.split('\n')) { if (!l.trim()) continue; try { const j = JSON.parse(l); if (j && typeof j === 'object') out.push(j); } catch (e) { /* skip a bad line */ } }
  return out;
}

// -> the lines written (with ids). An idea already on file from the same Mote is not added twice.
function appendIdeas(dir, helper, threadId, ideas) {
  const all = readJsonl(path.join(dir, 'ideas.jsonl')), judged = new Set(readJsonl(path.join(dir, 'idea-verdicts.jsonl')).map((v) => v.id));
  const have = new Set(all.filter((x) => x.helper === helper).map((x) => String(x.idea).toLowerCase()));
  let room = MAX_PENDING - all.filter((x) => x.helper === helper && !judged.has(x.id)).length; // at most 20 unjudged ideas per Mote
  const rows = [];
  for (const i of ideas || []) {
    const idea = String(i && i.idea || '').trim();
    if (!idea || have.has(idea.toLowerCase())) continue;
    if (room-- <= 0) break;
    have.add(idea.toLowerCase());
    rows.push({ id: crypto.randomBytes(4).toString('hex'), ts: new Date().toISOString(), helper: helper || '', thread: threadId || '', idea });
  }
  if (!rows.length) return [];
  try { fs.mkdirSync(dir, { recursive: true }); fs.appendFileSync(path.join(dir, 'ideas.jsonl'), rows.map((r) => JSON.stringify(r)).join('\n') + '\n'); } catch (e) { return []; }
  return rows;
}

module.exports = { parseIdeas, appendIdeas, readJsonl };
