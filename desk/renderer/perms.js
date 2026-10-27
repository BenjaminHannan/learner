'use strict';
// Permissions card: one row per macOS permission with a live status dot, an Open Settings button, and a draggable tile of
// the real app icon to drop into the list in System Settings (like OpenBot). It is a sheet inside the main window.
window.Perms = (() => {
  const desk = window.desk;
  const root = document.getElementById('perms');
  let timer = null, last = new Map(), busy = false;
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };

  function tile(st, which) {
    const name = which === 'helper' ? st.helperPath.split('/').pop() : st.appName;
    const t = el('div', 'p-tile'); t.draggable = true; t.tabIndex = 0; t.setAttribute('role', 'button');
    const label = 'Drag ' + name + ' into System Settings, or click to show it in Finder';
    t.title = label; t.setAttribute('aria-label', label);
    const img = new Image(); img.alt = ''; img.draggable = false; img.src = st.icon;
    t.append(img, el('span', null, name));
    t.addEventListener('dragstart', (e) => { e.preventDefault(); desk.perms.drag(which); });
    t.onclick = () => desk.perms.reveal(which);
    t.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); desk.perms.reveal(which); } });
    return t;
  }

  function paint(st) {
    root.textContent = '';
    const card = el('div', 'p-card');
    const head = el('div', 'p-head'); head.append(el('h2', null, 'Let Glim use your Mac'), (() => { const b = el('button', 'amber-btn', 'Done'); b.id = 'permsDone'; b.onclick = hide; return b; })());
    card.append(head, el('p', 'p-sub', 'Glim needs your OK before it can click, type or look at the screen. Open the pane, then drag the app tile into the list and switch it on.'));
    st.rows.forEach((r) => {
      const row = el('div', 'p-row'); row.dataset.id = r.id;
      const on = r.granted === true, was = last.get(r.id);
      row.classList.toggle('on', on); row.classList.toggle('unknown', r.granted === null);
      if (was === false && on) row.classList.add('flip');
      const dot = el('i', 'p-dot'); dot.setAttribute('aria-hidden', 'true');
      const lab = el('div', 'p-lab'); lab.append(el('b', null, r.label + (r.optional ? ' (optional)' : '')), el('span', null, r.why));
      const stat = el('span', 'p-stat', on ? 'On' : r.granted === false ? 'Off' : 'Not checked');
      const open = el('button', 'ghost sm', 'Open Settings'); open.onclick = () => desk.perms.open(r.id);
      row.append(dot, lab, stat, open);
      card.append(row);
      last.set(r.id, r.granted);
    });
    const drag = el('div', 'p-drag');
    const tiles = el('div', 'p-tiles'); tiles.append(tile(st, 'app'));
    if (st.helperPath) tiles.append(tile(st, 'helper'));
    const hint = el('div', 'p-hint');
    hint.append(el('b', null, 'Drag this into the list, then switch it on'), el('span', null, 'Drag ' + st.appName + ' into System Settings, or click to show it in Finder.'));
    if (st.helperPath) hint.append(el('span', 'p-note', 'macOS also lists the helper (' + st.helperPath.split('/').pop() + ') on its own: add it the same way if Glim still cannot click or see.'));
    drag.append(tiles, hint);
    card.append(drag);
    root.append(card);
  }

  async function refresh() {
    if (busy || root.hidden) return;
    busy = true;
    try {
      const st = await desk.perms.status();
      if (root.hidden) return;
      // repaint only when something changed (keeps a drag in progress, focus and hover intact)
      const key = JSON.stringify([st.rows.map((r) => r.granted), st.helperPath, st.icon.length]);
      if (key !== refresh.key) { refresh.key = key; paint(st); }
    } finally { busy = false; }
  }
  function show() { if (!root.hidden) return; root.hidden = false; refresh.key = ''; last = new Map(); refresh(); clearInterval(timer); timer = setInterval(refresh, 2000); }
  function hide() { root.hidden = true; clearInterval(timer); timer = null; }

  root.addEventListener('mousedown', (e) => { if (e.target === root) hide(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !root.hidden) { hide(); e.stopPropagation(); } }, true);
  desk.onPermsShow(show);
  desk.onPermsRecheck(() => { if (!root.hidden) refresh(); });
  return { show, hide, refresh, isOpen: () => !root.hidden };
})();
