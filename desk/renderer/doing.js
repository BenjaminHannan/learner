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
  // UI2 (Ben Nov 4, M3): "[cut off: Ben sent a new message]" was a note for the model, and the model copied it into its own replies (then
  // stopped without acting). It never shows on screen and never goes back to the model. An unclosed one (still streaming) goes too.
  const CUT_MARK = /[ \t]*\n?[ \t]*\[cut off:[^\]\n]{0,120}(?:\]|$)/gi;
  function cleanReply(text) { const s = String(text == null ? '' : text); const c = s.replace(CUT_MARK, ''); return c === s ? s : c.trimEnd(); }
  // UI2 safety net (Ben Nov 4: the same "Plan: 1. ... 2. ..." in the chat each time he steered, and again on the plan card): a reply that opens
  // with a plan block (a "Plan:" heading with numbered steps, or numbered steps first) matching the plan card loses that block; the card keeps it.
  const words = (x) => new Set(tidy(x).toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2));
  const near = (a, b) => { const A = words(a), B = words(b); if (!A.size || !B.size) return false; let n = 0; for (const w of A) if (B.has(w)) n++; return n / Math.min(A.size, B.size) >= 0.5; };
  function stripPlan(text, card) {
    const s = String(text == null ? '' : text);
    if (!Array.isArray(card) || !card.length) return s;
    const lines = s.split('\n'), num = (l) => /^\s*\d+[.)]\s+\S/.test(l);
    let start = lines.findIndex((l) => /^\s*[*_#\s]*plan\s*:?\s*[*_]*\s*:?\s*$/i.test(l)), i;
    if (start >= 0) i = start + 1;
    else { start = lines.findIndex((l) => l.trim()); if (start < 0 || !num(lines[start])) return s; i = start; }
    const steps = [];
    while (i < lines.length && (num(lines[i]) || (!lines[i].trim() && !steps.length))) { if (num(lines[i])) steps.push(lines[i].replace(/^\s*\d+[.)]\s+/, '')); i++; }
    if (steps.length < 2 || steps.filter((x) => card.some((c) => near(x, c))).length * 2 < steps.length) return s;
    return lines.slice(0, start).concat(lines.slice(i)).join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }
  const api = { doingLine, cleanReply, stripPlan };
  root.Doing = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
