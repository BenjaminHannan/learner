'use strict';

// Pure data preparation. It does not read recordings, invent clock mappings,
// train, or verify whether a claimed correction is true.
function splitEpisodes(actions, maxGapMs = 120000) {
  if (!Array.isArray(actions) || !Number.isSafeInteger(maxGapMs) || maxGapMs < 1) throw Error('invalid episode input');
  const episodes = [];
  let last = -1;
  for (const action of actions) {
    if (!action || !Number.isSafeInteger(action.timeMs) || action.timeMs < 0 || action.timeMs < last) throw Error('actions must be in time order');
    if (!episodes.length || action.timeMs - last > maxGapMs) episodes.push([]);
    episodes.at(-1).push(action);
    last = action.timeMs;
  }
  return episodes;
}

// A time cutoff, not the last 20% of actions. Ties stay on one side.
function splitByTime(examples, startMs, endMs) {
  if (!Array.isArray(examples) || !Number.isSafeInteger(startMs) || !Number.isSafeInteger(endMs) || startMs < 0 || endMs <= startMs) throw Error('invalid day interval');
  const cutoffMs = startMs + (endMs - startMs) * 0.8;
  const train = [], held = [];
  for (const e of examples) {
    if (!e || !Number.isSafeInteger(e.timeMs) || e.timeMs < startMs || e.timeMs > endMs) throw Error('example outside day');
    (e.timeMs < cutoffMs ? train : held).push(e);
  }
  return { train, held, cutoffMs };
}

// Corrections are labels only when independently verified or supplied by Ben.
// Verification of evidence and observation is the caller's responsibility.
function correctionCandidates(attempt) {
  if (!attempt || attempt.schema !== 'hands-attempt/v1' || typeof attempt.attemptId !== 'string' || !attempt.attemptId || !Array.isArray(attempt.corrections)) throw Error('invalid attempt');
  return attempt.corrections.filter(c => c && ['ben', 'independently_verified'].includes(c.source) && typeof c.evidence === 'string' && c.evidence.trim() && typeof c.observation === 'string' && c.observation.trim() && c.action && typeof c.action === 'object' && !Array.isArray(c.action)).map(c => ({ attemptId: attempt.attemptId, action: structuredClone(c.action), observation: c.observation, evidence: c.evidence, source: c.source, weight: 3, verificationRequired: true }));
}

module.exports = { splitEpisodes, splitByTime, correctionCandidates };
