'use strict';
// The one short "what I'm doing now" line from Glim's narration before a tool call (Ben Oct 28: the live line showed
// the small model's thinking-out-loud). Used by the renderer's live line / side panel (window.Doing) and the pill (require).
(function (root) {
  const tidy = (s) => String(s || '').replace(/\*\*|__|`/g, '').replace(/^[#>*\-\s]+/, '').replace(/\s+/g, ' ').trim();
  const cap = (s) => (s.length > 90 ? s.slice(0, 89).trimEnd() + '…' : s);
  function doingLine(text) { return cap(pick(text)); }
  function pick(text) {
    const lines = String(text || '').split('\n').map(tidy).filter((l) => l && !/^\[Action:/i.test(l));
    if (!lines.length) return '';
    // a "Next: I'll click ..." line (older narration, some models) is the action: the last one wins
    const next = lines.filter((l) => /^(?:next|now|doing|step)\s*:/i.test(l)).pop();
    if (next) return next.replace(/^[^:]+:\s*/, '');
    // a numbered plan with no Next line: Glim is on its first step
    const step1 = lines.find((l) => /^\d+[.)]\s+\S/.test(l));
    if (step1) return step1.replace(/^\d+[.)]\s+/, '');
    // otherwise the last sentence (the earlier ones are reasoning about why)
    const last = lines.filter((l) => !/^plan\s*:/i.test(l)).pop() || lines.pop().replace(/^plan\s*:\s*/i, '');
    const sents = last.split(/(?<=[.!?])\s+(?=[A-Z])/);
    return sents[sents.length - 1];
  }
  const api = { doingLine };
  root.Doing = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
