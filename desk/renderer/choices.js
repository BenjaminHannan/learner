'use strict';
// Ben Oct 28: "ask me with options to click". A final answer may end with lines starting "→ " (or "-> "): they become chips under it.
// Only trailing lines count; an arrow line in the middle of the text stays text. Used by the renderer (window.Choices) and tests.
(function (root) {
  const ARROW = /^\s*(?:→|->)\s+(\S.*)$/;
  // Ben Nov 4: a chip was cut mid-word at 80 characters ("...save each as a g"). A chip is sent as typed, so keep it whole;
  // only a runaway line is shortened, at a word boundary, with an ellipsis. The chip itself wraps (app.css .choice).
  const MAX = 240;
  const fit = (s) => { if (s.length <= MAX) return s; const cut = s.slice(0, MAX), sp = cut.lastIndexOf(' '); return (sp > MAX / 2 ? cut.slice(0, sp) : cut).replace(/[\s,;:–-]+$/, '') + '…'; };
  function parseChoices(raw) {
    const lines = String(raw == null ? '' : raw).replace(/\s+$/, '').split('\n');
    const found = [];
    while (lines.length && (!lines[lines.length - 1].trim() || ARROW.test(lines[lines.length - 1]))) {
      const l = lines.pop(), m = ARROW.exec(l);
      if (m) found.unshift(fit(m[1].replace(/\*\*|__|`/g, '').trim()));
    }
    if (!found.length) return { text: String(raw == null ? '' : raw), choices: [] };
    return { text: lines.join('\n').replace(/\s+$/, ''), choices: found.slice(0, 4) };
  }
  const api = { parseChoices };
  root.Choices = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
