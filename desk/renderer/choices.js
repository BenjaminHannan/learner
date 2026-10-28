'use strict';
// Ben Oct 28: "ask me with options to click". A final answer may end with lines starting "→ " (or "-> "): they become chips under it.
// Only trailing lines count; an arrow line in the middle of the text stays text. Used by the renderer (window.Choices) and tests.
(function (root) {
  const ARROW = /^\s*(?:→|->)\s+(\S.*)$/;
  function parseChoices(raw) {
    const lines = String(raw == null ? '' : raw).replace(/\s+$/, '').split('\n');
    const found = [];
    while (lines.length && (!lines[lines.length - 1].trim() || ARROW.test(lines[lines.length - 1]))) {
      const l = lines.pop(), m = ARROW.exec(l);
      if (m) found.unshift(m[1].replace(/\*\*|__|`/g, '').trim().slice(0, 80));
    }
    if (!found.length) return { text: String(raw == null ? '' : raw), choices: [] };
    return { text: lines.join('\n').replace(/\s+$/, ''), choices: found.slice(0, 4) };
  }
  const api = { parseChoices };
  root.Choices = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
