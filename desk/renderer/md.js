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
    // Links go into placeholders too, so italics never touch a URL (URLs often contain _ or *).
    const links = [];
    const keep = (h) => { links.push(h); return '\u0001' + (links.length - 1) + '\u0001'; };
    s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (m, t, u) => keep('<a data-href="' + u + '">' + t + '</a>'));
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+[^\s<).,;:!?])/g, (m, p, u) => p + keep('<a data-href="' + u + '">' + u + '</a>'));
    // *italic* and _italic_: no space just inside the marks, and not glued to letters (keeps 2 * 3 and snake_case as they are).
    s = s.replace(/(^|[^*\w])\*(?![\s*])([^*\n]*?[^\s*])\*(?![*\w])/g, '$1<em>$2</em>');
    s = s.replace(/(^|[^\w])_(?![\s_])([^_\n]*?[^\s_])_(?!\w)/g, '$1<em>$2</em>');
    s = s.replace(/\u0001(\d+)\u0001/g, (m, i) => links[+i]);
    return s.replace(/\u0000(\d+)\u0000/g, (m, i) => '<code>' + codes[+i] + '</code>');
  }
  // Tables: "| a | b |" rows. A table only counts once its "|---|---|" line is there.
  const isRow = (l) => /^\s*\|.*\|\s*$/.test(l);
  const cells = (l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
  const isSep = (l) => isRow(l) && cells(l).every((c) => /^:?-+:?$/.test(c));
  function table(rows) {
    const head = cells(rows[0]);
    const body = rows.slice(2).map(cells);
    return '<div class="tablewrap"><table><thead><tr>' + head.map((c) => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>' +
      body.map((r) => '<tr>' + head.map((_, j) => '<td>' + inline(r[j] || '') + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
  }
  // opts.streaming: the reply is still arriving. Ben Nov 3: tables should appear when the message is done, not as raw "|" lines.
  const TABLE_WAIT = '<p class="tablewait">making a table…</p>';
  function md(text, opts) {
    const streaming = !!(opts && opts.streaming);
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
      let olNext = 0; // a numbered list split by blank lines keeps counting (models write "1." ... blank ... "2." or even "1." again)
      const flushP = () => { if (para.length) { out.push('<p>' + para.map(inline).join('<br>') + '</p>'); para = []; } };
      const flushL = () => { if (list) { if (list.t === 'ol') olNext = list.start + list.items.length; out.push('<' + list.t + (list.t === 'ol' && list.start !== 1 ? ' start="' + list.start + '"' : '') + '>' + list.items.map((x) => '<li>' + inline(x) + '</li>').join('') + '</' + list.t + '>'); list = null; } };
      const lines = part.split('\n');
      for (let k = 0; k < lines.length; k++) {
        const line = lines[k];
        let m;
        if (isRow(line) || (streaming && i === parts.length - 1 && /^\s*\|/.test(line))) {
          let e = k; while (e + 1 < lines.length && isRow(lines[e + 1])) e++;
          const rows = lines.slice(k, e + 1);
          const isTable = rows.length >= 2 && isSep(rows[1]);
          if (streaming && i === parts.length - 1) {
            // still being written: hold the table back, show a quiet note instead
            flushP(); flushL(); olNext = 0;
            if (!out.length || out[out.length - 1] !== TABLE_WAIT) out.push(TABLE_WAIT);
            k = e; continue;
          }
          if (isTable) { flushP(); flushL(); olNext = 0; out.push(table(rows)); k = e; continue; }
        }
        if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flushP(); flushL(); olNext = 0; out.push('<hr>'); }
        else if ((m = /^\s*[-*•]\s+(.*)/.exec(line))) { flushP(); if (!list || list.t !== 'ul') { flushL(); list = { t: 'ul', items: [] }; } list.items.push(m[1]); }
        else if ((m = /^\s*(\d+)[.)]\s+(.*)/.exec(line))) { flushP(); if (!list || list.t !== 'ol') { flushL(); const n = parseInt(m[1], 10); list = { t: 'ol', items: [], start: olNext && n <= 1 ? olNext : n }; } list.items.push(m[2]); }
        else if (!line.trim()) { flushP(); flushL(); }
        else if ((m = /^#{1,4}\s+(.*)/.exec(line))) { flushP(); flushL(); olNext = 0; out.push('<p><strong>' + inline(m[1]) + '</strong></p>'); }
        else { flushL(); olNext = 0; para.push(line); }
      }
      flushP(); flushL();
    });
    return out.join('');
  }
  const api = { md, isSep, esc, inline, isActionLine, stripActions };
  root.Md = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
