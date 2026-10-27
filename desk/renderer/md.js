'use strict';
// Minimal markdown (escapes HTML first). Works in the page and in node (tests).
(function (root) {
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  // The model sometimes writes its "actions" as text, e.g. "[Action: Click Continue]". Those lines are noise: hide them.
  const ACTION_LINE = /^\s*\[Action:.*\]\s*$/i;
  const isActionLine = (l) => ACTION_LINE.test(l);
  const stripActions = (text) => String(text || '').split('\n').filter((l) => !isActionLine(l)).join('\n');

  function inline(s) {
    s = esc(s);
    const codes = [];
    s = s.replace(/`([^`\n]+)`/g, (m, c) => { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
    s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a data-href="$2">$1</a>');
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+[^\s<).,;:!?])/g, '$1<a data-href="$2">$2</a>');
    return s.replace(/\u0000(\d+)\u0000/g, (m, i) => '<code>' + codes[+i] + '</code>');
  }
  function md(text) {
    const out = [];
    const parts = stripActions(text).split(/```/);
    parts.forEach((part, i) => {
      if (i % 2 === 1) {
        const nl = part.indexOf('\n');
        const body = nl >= 0 && /^[\w+-]*$/.test(part.slice(0, nl).trim()) ? part.slice(nl + 1) : part;
        out.push('<pre><code>' + esc(body.replace(/\n$/, '')) + '</code></pre>');
        return;
      }
      let list = null;
      let para = [];
      const flushP = () => { if (para.length) { out.push('<p>' + para.map(inline).join('<br>') + '</p>'); para = []; } };
      const flushL = () => { if (list) { out.push('<' + list.t + '>' + list.items.map((x) => '<li>' + inline(x) + '</li>').join('') + '</' + list.t + '>'); list = null; } };
      for (const line of part.split('\n')) {
        let m;
        if ((m = /^\s*[-*•]\s+(.*)/.exec(line))) { flushP(); if (!list || list.t !== 'ul') { flushL(); list = { t: 'ul', items: [] }; } list.items.push(m[1]); }
        else if ((m = /^\s*\d+[.)]\s+(.*)/.exec(line))) { flushP(); if (!list || list.t !== 'ol') { flushL(); list = { t: 'ol', items: [] }; } list.items.push(m[1]); }
        else if (!line.trim()) { flushP(); flushL(); }
        else if ((m = /^#{1,4}\s+(.*)/.exec(line))) { flushP(); flushL(); out.push('<p><strong>' + inline(m[1]) + '</strong></p>'); }
        else { flushL(); para.push(line); }
      }
      flushP(); flushL();
    });
    return out.join('');
  }
  const api = { md, esc, inline, isActionLine, stripActions };
  root.Md = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
