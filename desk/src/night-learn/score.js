'use strict';

// Pure scoring only. This module does not load, train, or promote a model.
const { createHash } = require('node:crypto');

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}

function score({ train, held, predictions }) {
  if (!Array.isArray(train) || !train.length || !Array.isArray(held) || !held.length) throw Error('train and held examples required');
  const ids = new Set();
  for (const e of [...train, ...held]) {
    if (!e || typeof e.id !== 'string' || !e.id || ids.has(e.id) || !Number.isSafeInteger(e.timeMs) || e.timeMs < 0) throw Error('invalid or duplicate example');
    ids.add(e.id);
  }
  const trainLastMs = train.reduce((v, e) => Math.max(v, e.timeMs), -Infinity);
  const heldFirstMs = held.reduce((v, e) => Math.min(v, e.timeMs), Infinity);
  if (trainLastMs >= heldFirstMs) throw Error('held examples must be later than every training example');
  if (!predictions || typeof predictions !== 'object') throw Error('predictions required');
  const arms = ['old', 'candidate', 'noIntent'];
  for (const arm of arms) {
    const p = predictions[arm];
    if (!p || typeof p !== 'object' || Array.isArray(p) || Object.keys(p).length !== held.length || held.some(e => !Object.hasOwn(p, e.id))) throw Error('each arm must predict every held example');
  }
  const counts = Object.fromEntries(arms.map(a => [a, { clicks: 0, keys: 0 }]));
  let clicks = 0, keys = 0;
  for (const e of held) {
    if (e.kind === 'click') {
      if (!Number.isFinite(e.x) || !Number.isFinite(e.y)) throw Error('invalid click label');
      clicks++;
      for (const arm of arms) {
        const p = predictions[arm][e.id];
        if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) throw Error('invalid click prediction');
        if (Math.hypot(p.x - e.x, p.y - e.y) <= 40) counts[arm].clicks++;
      }
    } else if (e.kind === 'key') {
      if (typeof e.key !== 'string' || !e.key) throw Error('invalid key label');
      keys++;
      for (const arm of arms) {
        const p = predictions[arm][e.id];
        if (!p || typeof p.key !== 'string' || !p.key) throw Error('invalid key prediction');
        if (p.key === e.key) counts[arm].keys++;
      }
    } else throw Error('unsupported held action');
  }
  if (!clicks || !keys) throw Error('held slice must include clicks and keys');
  const rates = Object.fromEntries(arms.map(a => [a, { click: counts[a].clicks / clicks, key: counts[a].keys / keys }]));
  // Integer comparisons avoid floating point rounding at the exact 5-point boundary.
  const beats = a => 20 * (counts.candidate.clicks - counts[a].clicks) >= clicks && counts.candidate.keys >= counts[a].keys;
  return {
    pass: beats('old') && beats('noIntent'),
    counts: { clickExamples: clicks, keyExamples: keys, arms: counts }, rates,
    heldSha256: createHash('sha256').update(canonical(held)).digest('hex'),
    heldFirstMs, trainLastMs,
    note: 'Caller must establish recording provenance, coordinates, model hashes, and that noIntent zeroed the intent vector.'
  };
}

module.exports = { score };
