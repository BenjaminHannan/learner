'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const P = window.deskPill;
  const pill = $('#pill');
  const g = Mascot.el('idle', 24, {}); $('#g').append(g);
  let view = null, openT = 0, closeT = 0;
  const mmss = (ms) => { const s = Math.round(ms / 1000); return s < 60 ? s + ' s' : Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

  function btn(label, cls, fn) { const b = el('button', cls, label); b.onclick = (e) => { e.stopPropagation(); fn(); }; return b; }
  function paint(v) {
    view = v;
    const geo = v.geo || {};
    pill.style.setProperty('--pt', (geo.pt != null ? geo.pt : 4) + 'px');
    pill.style.setProperty('--nh', (geo.notchH || 36) + 'px'); pill.style.setProperty('--nw', (geo.notchW || 0) + 'px');
    pill.classList.toggle('notch', !!geo.notchH);
    pill.classList.toggle('gone', !v.visible);
    if (!v.visible) { close(); return; }
    $('#dIdle').hidden = true;
    pill.classList.remove('working', 'waiting', 'error', 'done', 'sleeping', 'call', 'idle'); pill.classList.add(v.status);
    Mascot.set(g, v.mood);
    if (v.status === 'idle') { idle(v); return; } // just the icon; hover opens the summary card
    const t = v.top;
    $('#line').textContent = v.line || '';
    $('#mini').textContent = v.status === 'working' ? mmss(t.elapsedMs) : '';
    $('#dName').textContent = t.name; $('#dName').parentElement.hidden = !!v.oneGlim; // the main one is just "Glim", never a chat title like "Plan my week"
    $('#dStep').textContent = t.step || (v.status === 'done' ? 'Finished' : v.status === 'sleeping' ? 'Resting while you are away' : '-');
    $('#dTime').textContent = mmss(t.elapsedMs);
    $('#dErr').hidden = !t.error; $('#dErr').textContent = t.error || '';
    const ap = t.approval;
    $('#dAsk').hidden = !ap; $('#dAsk').textContent = ap ? (ap.kind === 'ask' ? 'Glim asks: ' + ap.text : ap.text) : '';
    $('#dOthers').textContent = v.others.length ? 'Also: ' + v.others.map((o) => o.name + ' (' + o.status + ')').join(', ') : '';
    const b = $('#btns'); b.textContent = '';
    b.append(btn('Open', 'go', () => P.act('open', { threadId: t.threadId, key: v.status === 'done' || v.status === 'error' ? t.key : null })));
    if (ap && (ap.kind === 'shell' || ap.kind === 'screen')) {
      b.append(btn('Allow once', '', () => P.act('respond', { rid: ap.rid, value: 'once', threadId: t.threadId })));
      if (!ap.danger && ap.always) b.append(btn('Always allow', '', () => P.act('respond', { rid: ap.rid, value: 'always', threadId: t.threadId })));
      b.append(btn('Deny', 'no', () => P.act('respond', { rid: ap.rid, value: 'deny', threadId: t.threadId })));
    }
    if (ap && ap.kind === 'login') b.append(btn('Open browser', '', () => P.act('openBrowser', t.key)));
    if (v.status === 'call') { b.textContent = ''; b.append(btn('Open', 'go', () => P.act('open', {})), btn('Hang up', 'no', () => P.act('hangup'))); return; }
    if (v.status === 'sleeping') { b.textContent = ''; b.append(btn('Wake Glim', 'go', () => P.act('wake'))); return; }
    if (v.status === 'working' || v.status === 'waiting') b.append(btn('Stop', 'no', () => P.act('stop', t.key)));
    if (v.status === 'done' || v.status === 'error') b.append(btn('Dismiss', '', () => P.act('dismiss', t.key)));
  }
  // resting pill: a plain summary (set by main.js as v.idle) and an Open button
  function idle(v) {
    const i = v.idle, d = $('#dIdle');
    $('#line').textContent = i ? i.head : '';
    d.textContent = ''; d.hidden = !i;
    if (i) for (const l of i.lines) d.append(el('div', '', l));
    const b = $('#btns'); b.textContent = ''; b.append(btn('Open', 'go', () => P.act('open', { threadId: null, key: null })));
    if (!i) close();
  }
  function open() { clearTimeout(closeT); clearTimeout(openT); openT = setTimeout(() => pill.classList.add('open'), 150); }
  function close() { clearTimeout(openT); clearTimeout(closeT); closeT = setTimeout(() => { pill.classList.remove('open'); if (!pill.classList.contains('hover')) P.act('hover', false); }, 220); } // a hovered island stays clickable
  // notched Mac: hovering the island grows it a little (OpenBot-style) and makes it clickable, even when idle
  pill.addEventListener('mouseenter', () => {
    clearTimeout(closeT);
    if (!view || !view.visible) return;
    if (pill.classList.contains('notch')) { pill.classList.add('hover'); P.act('hover', true); }
    if (view.status === 'idle' && !view.idle) return;
    P.act('hover', true); open();
  });
  pill.addEventListener('mouseleave', () => { clearTimeout(openT); pill.classList.remove('hover'); close(); });
  $('.row1').addEventListener('click', () => { if (view && view.status === 'idle') P.act('open', { threadId: null, key: null }); else if (view && view.top) P.act('open', { threadId: view.top.threadId, key: null }); });
  P.onView(paint);
  window.__open = () => { clearTimeout(closeT); pill.classList.add('open'); };       // for screenshots
  window.__close = () => { pill.classList.remove('open'); };
})();
