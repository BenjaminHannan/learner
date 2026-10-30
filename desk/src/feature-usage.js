'use strict';
// Only daily totals are stored locally; no choice text or identifying data.
const fs = require('fs');
const path = require('path');
const { dayKey } = require('./followup');
const KINDS = new Set(['followup', 'idea']);
function count(file, kind, now = new Date()) {
  if (!KINDS.has(kind)) return false;
  let data = {};
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) { /* first use */ }
  const day = dayKey(now);
  if (!data[day] || typeof data[day] !== 'object') data[day] = {};
  data[day][kind] = (Number(data[day][kind]) || 0) + 1;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data));
  fs.renameSync(tmp, file);
  return true;
}
module.exports = { count };
