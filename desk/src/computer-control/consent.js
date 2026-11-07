'use strict';

// This protects the chat path from the legacy hands timeout. It is not an
// input lease and does not make the legacy desktop helper safe for takeover.
const grants = new WeakMap();
const affirmative = (answer) => /^(?:y|yes|ok|okay|sure|go|go ahead|fine|always allow)$/i.test(String(answer || '').trim());

function guardHandsConsent({ hands, signal, askUser, run }) {
  const ask = async (question, askSignal, options) => {
    const answer = await askUser(question, askSignal, options);
    if (signal && !signal.aborted && !(askSignal && askSignal.aborted) && affirmative(answer)) {
      grants.set(signal, true);
      return answer;
    }
    return 'no';
  };
  const guardedRun = (args, ctx) => {
    let level;
    try { level = hands.o.levels.level('hands'); } catch (_) { /* unknown means no grant */ }
    if (!signal || signal.aborted || (level !== 'free' && !(level === 'ask' && grants.get(signal) === true))) {
      return { text: 'Mouse and keyboard action stopped: no clear permission was received.', error: true };
    }
    return run(args, ctx);
  };
  return { ask, guardedRun };
}

module.exports = { guardHandsConsent };
