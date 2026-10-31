'use strict';
// Suggestions, not a judgment of truth. Only explicit information questions are
// eligible; failed actions, personal choices and conversational replies are not.
const { looksSecret } = require('./memory');
const GAP = /\b(?:i (?:do not|don't|don’t) know|i(?:'m| am) not sure|i (?:could not|couldn't|can not|cannot|can't|was unable to|wasn't able to) (?:find|answer|determine|identify|verify|tell)|i reached the step limit|unable to (?:find|answer|determine|identify|verify))\b/i;
function detectGap(question, answer, checks = []) {
  const q = String(question || '').replace(/\s+/g, ' ').trim();
  if (q.length < 12 || q.length > 500 || looksSecret(q)) return null;
  if (!/^(?:(?:please|hey|hi)[, ]+)?(?:what|who|when|where|why|how|which)\b/i.test(q) || !/\?\s*$/.test(q)) return null;
  const failed = GAP.test(String(answer || '')) || checks.some(c => /\bnot done\b/i.test(String(c)));
  return failed ? { question: q, reason: GAP.test(String(answer || '')) ? 'Glim could not answer' : 'Self-check found it was not done' } : null;
}
module.exports = { detectGap };
