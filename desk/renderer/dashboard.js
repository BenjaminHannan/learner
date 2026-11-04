'use strict';
// "Important updates" dashboard: the LOOK and the KEEP-FRESH logic. No data rules live here (those are in src/dashboard.js);
// this file only turns a dashboard model into a picture and keeps it up to date. To change the design, replace the view
// functions (dashboardView / morningCardView / mount) and leave the rest alone: they take the same model.
//
//   views return plain "vnodes" { t, cls, text, attrs, on, kids, ns } so they can be tested without a browser, and mount() makes real DOM.
//   createDashboard() is the refresher: it asks for a fresh model every 60 s, whenever the window gets focus, and whenever the
//   main process says a source file changed; a changed model repaints (hero line included) without a reload. It also runs the
//   buttons (act / undo), holds the "Done. Undo" toast, and decides honestly when the screen is loading, stale or in error.
//
// Look: the design in dashboard-design/DESIGN.md (urgency order, colour only for state, one row per event, a "Why:" line,
// "updated N min ago" always shown, line icons, two columns when wide, keyboard shortcuts). Colours are the app's own theme variables.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Dashboard = factory();
})(typeof window !== 'undefined' ? window : globalThis, () => {
  const REFRESH_MS = 60000;
  const TICK_MS = 20000;                     // how often the "updated … ago" line is redrawn
  const STALE_AFTER_MS = 15 * 60000;         // no good update for this long: say "this may be old"
  const FETCH_TIMEOUT_MS = 10000;            // the files did not answer: that is an error, not an endless "Checking…"
  const TOAST_MS = 10000;
  const SVG_NS = 'http://www.w3.org/2000/svg';

  // ---------- tiny vnode helpers
  const h = (t, cls, kids, extra) => ({ t, cls: cls || '', kids: [].concat(kids == null ? [] : kids).filter((k) => k != null && k !== false), ...(extra || {}) });
  const txt = (t, cls, s, extra) => h(t, cls, [], { text: s, ...(extra || {}) });

  // ---------- line icons (24x24, one colour, drawn with currentColor)
  const ICON_SRC = {
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    game: '<rect x="2" y="7" width="20" height="11" rx="5"/><path d="M7 10.5v4M5 12.5h4M15.5 11.5h.01M18 14h.01"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    alert: '<path d="M12 7v6M12 16.5v.5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l2 2"/>',
    reply: '<path d="M10 8L4 13l6 5M4 13h11a5 5 0 0 1 5 5"/>',
    chev: '<path d="M9 6l6 6-6 6"/>',
    plug: '<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5"/>',
    wrench: '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 12.6 12.6 21a2.1 2.1 0 0 1-3-3L18 9.6"/><path d="M14.7 6.3L17 4l3 3-2.3 2.3"/>'
  };
  // "<path d=.../>" -> [{tag, attrs}] (so the icons need no DOM until mount())
  const parseIcon = (s) => [...s.matchAll(/<(\w+)([^>]*?)\/>/g)].map((m) => ({ tag: m[1], attrs: Object.fromEntries([...m[2].matchAll(/([\w-]+)="([^"]*)"/g)].map((a) => [a[1], a[2]])) }));
  const ICONS = Object.fromEntries(Object.keys(ICON_SRC).map((k) => [k, parseIcon(ICON_SRC[k])]));
  const iconView = (name, cls) => h('svg', 'db-i' + (cls ? ' ' + cls : ''), (ICONS[name] || ICONS.bolt).map((p) => h(p.tag, '', [], { ns: 'svg', attrs: p.attrs })), { ns: 'svg', attrs: { viewBox: '0 0 24 24', 'aria-hidden': 'true' } });

  // ---------- time words
  const pad2 = (n) => String(n).padStart(2, '0');
  const clock = (ms) => { const d = new Date(ms); let hr = d.getHours(); const ap = hr >= 12 ? 'pm' : 'am'; hr = hr % 12 || 12; return hr + ':' + pad2(d.getMinutes()) + ' ' + ap; };
  const sameDay = (a, b) => { const x = new Date(a), y = new Date(b); return x.getFullYear() === y.getFullYear() && x.getMonth() === y.getMonth() && x.getDate() === y.getDate(); };
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // "4:10 pm" for today, "Nov 2, 4:10 pm" for another day
  const stamp = (ms, now) => (sameDay(ms, now) ? clock(ms) : MONTHS[new Date(ms).getMonth()] + ' ' + new Date(ms).getDate() + ', ' + clock(ms));
  const greet = (now, user) => { const hr = new Date(now).getHours(); return (hr < 5 ? 'Late night' : hr < 12 ? 'Good morning' : hr < 18 ? 'Good afternoon' : 'Good evening') + (user ? ', ' + user : ''); };
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  // "updated just now" / "updated 2 min ago" / "updated 3 h ago"
  function agoText(updatedAt, now) {
    if (!Number.isFinite(updatedAt)) return 'not updated yet';
    const s = Math.max(0, Math.round(((now == null ? Date.now() : now) - updatedAt) / 1000));
    if (s < 45) return 'updated just now';
    const m = Math.round(s / 60);
    if (m < 60) return 'updated ' + (m <= 1 ? '1 min' : m + ' min') + ' ago';
    const hr = Math.round(m / 60);
    if (hr < 48) return 'updated ' + hr + ' h ago';
    return 'updated ' + Math.round(hr / 24) + ' days ago';
  }

  // the top-bar words: "Updated 2 min ago" while live, "Last update 3 h ago" once it is stale
  function agoLabel(status, updatedAt, now) {
    const a = agoText(updatedAt, now);
    return status === 'stale' ? 'Last update ' + a.replace(/^updated /, '') : cap(a);
  }

  // The screen's honest state, from real conditions only:
  //   loading: no model yet and no failure so far | error: no model and the first read failed
  //   stale: there is a model but the last good update is older than 15 min (the files stopped answering) | live: otherwise
  function feedStatus(st) {
    st = st || {};
    const now = Number.isFinite(st.now) ? st.now : Date.now();
    if (!st.model) return st.error ? 'error' : 'loading';
    if (!Number.isFinite(st.updatedAt) || now - st.updatedAt > STALE_AFTER_MS) return 'stale';
    return 'live';
  }

  const isNew = (item, st) => Number.isFinite(st.lastSeenAt) && Number.isFinite(item.createdAt) && item.createdAt > st.lastSeenAt;

  // ---------- views (replaceable)
  const SECTIONS = [
    { level: 'needs', name: 'Needs you', col: 0 },
    { level: 'worth', name: 'Worth knowing', col: 0 },
    { level: 'done', name: 'Done for you', col: 1 },
    { level: 'quiet', name: 'Other news', col: 1 }
  ];

  function actionBtn(a, fn) {
    return txt('button', 'db-btn' + (a.primary ? ' primary' : ''), a.label, { attrs: { type: 'button' }, on: { click: (e) => { if (e && e.stopPropagation) e.stopPropagation(); if (fn.act) fn.act(a); } } });
  }

  // one event = one row: [new dot] icon, title (+ sub-line), meta, chevron; quick actions always visible; facts / why / buttons when opened
  function rowView(item, st, fn, showNew) {
    const isOpen = st.open.has(item.id);
    const fresh = showNew && isNew(item, st);
    const row = h('button', 'db-row', [
      fresh ? h('span', 'db-newdot', [], { attrs: { role: 'img', 'aria-label': 'New since you last looked' } }) : null,
      h('span', 'db-ico', iconView(item.icon)),
      h('span', 'db-main', txt('span', 'db-title', item.title)),
      txt('span', 'db-meta' + (item.metaTone === 'soon' ? ' soon' : ''), item.meta || ''),
      h('span', 'db-chev', iconView('chev')),
      item.sub ? txt('span', 'db-sub', item.sub) : null
    ], { attrs: { type: 'button', 'aria-expanded': String(!!isOpen), 'data-id': item.id }, on: { click: () => fn.toggle && fn.toggle(item.id) } });
    const detail = [];
    if (item.facts && item.facts.length) detail.push(h('ul', 'db-facts', item.facts.map((s) => txt('li', '', s))));
    if (item.list && item.list.length) detail.push(h('ul', 'db-facts db-list', item.list.map((s) => txt('li', '', s))));
    if (item.why) detail.push(h('div', 'db-why', [txt('b', '', 'Why:'), ' ' + item.why]));
    if (item.details && item.details.length) detail.push(h('details', 'db-details', [txt('summary', '', 'Details'), h('div', 'db-raw', item.details.map((s) => txt('code', '', s)))]));
    if (item.actions && item.actions.length) detail.push(h('div', 'db-actions', item.actions.map((a) => actionBtn(a, fn))));
    return h('div', 'db-item' + (isOpen ? ' open' : ''), [
      row,
      item.quick && item.quick.length ? h('div', 'db-quick', item.quick.map((a) => actionBtn(a, fn))) : null,
      isOpen ? h('div', 'db-detail', detail) : null
    ], { attrs: { 'data-item': item.id } });
  }

  function sectionView(sec, items, st, fn, showNew) {
    if (!items.length) return null;
    return h('section', 'db-sec ' + sec.level, [txt('h3', 'db-h', sec.name), h('div', 'db-list-box', items.map((i) => rowView(i, st, fn, showNew)))]);
  }

  function badge(icon) { return h('div', 'db-badge', iconView(icon)); }
  const tryNow = (fn) => txt('button', 'db-btn', 'Try now', { attrs: { type: 'button' }, on: { click: () => fn.refresh && fn.refresh() } });

  function heroView(model, status, st, fn) {
    const now = st.now, g = txt('div', 'db-greet', greet(now, model && model.user));
    if (status === 'error') {
      return h('div', 'db-hero', [badge('plug'), h('div', 'db-hero-body', [g,
        txt('h1', 'db-hero-title', "Can't load your updates"),
        txt('p', 'db-hero-sub', "I can't read my update files right now. I'll try again in a minute."),
        h('div', 'db-hero-actions', tryNow(fn)),
        h('details', 'db-details', [txt('summary', '', 'Details'), txt('code', 'db-raw', st.error || 'No answer.')])])], { attrs: { 'data-tone': 'err', role: 'status', 'aria-live': 'polite' } });
    }
    if (status === 'stale') {
      const n = model.hero.needs;
      return h('div', 'db-hero', [badge('clock'), h('div', 'db-hero-body', [g,
        txt('h1', 'db-hero-title', (n === 0 ? 'Nothing needed you' : n === 1 ? '1 thing needed you' : n + ' things needed you') + ' at ' + clock(st.updatedAt)),
        txt('p', 'db-hero-sub', "I can't update right now, so this may be old. " + (st.error ? "I can't read my update files." : 'Updates stopped coming in.')),
        h('div', 'db-hero-actions', tryNow(fn))])], { attrs: { 'data-tone': 'stale', role: 'status', 'aria-live': 'polite' } });
    }
    const calm = model.hero.needs === 0;
    return h('div', 'db-hero db-hero-live ' + (calm ? 'calm' : 'busy'), [badge(calm ? 'check' : 'alert'), h('div', 'db-hero-body', [g,
      txt('h1', 'db-hero-title', model.hero.title), txt('p', 'db-hero-sub', model.hero.sub)])], { attrs: { 'data-tone': calm ? 'ok' : 'attn', role: 'status', 'aria-live': 'polite' } });
  }

  function skeletonView() {
    const sk = (w, hgt, extra) => h('span', 'db-sk', [], { attrs: { style: 'width:' + w + ';height:' + hgt }, ...(extra || {}) });
    const rowSk = (w) => h('div', 'db-sk-row', [h('span', 'db-sk round', [], { attrs: { style: 'width:32px;height:32px' } }), h('div', 'db-sk-text', [sk(w + '%', '12px'), sk(w - 20 + '%', '10px')])]);
    return h('div', '', [
      h('div', 'db-hero', [h('span', 'db-sk round', [], { attrs: { style: 'width:48px;height:48px' } }), h('div', 'db-hero-body', [sk('140px', '11px'), sk('260px', '26px')])], { attrs: { 'data-tone': 'stale', 'aria-busy': 'true' } }),
      h('div', 'db-cols', [h('div', 'db-col', h('section', 'db-sec', [h('div', 'db-list-box', [rowSk(70), rowSk(55)])])), h('div', 'db-col', h('section', 'db-sec', [h('div', 'db-list-box', [rowSk(60), rowSk(50)])]))])
    ]);
  }

  function topbarView(model, status, st) {
    const bits = [];
    if (status === 'loading') bits.push(txt('span', '', 'Checking…'));
    else if (status === 'error') bits.push(h('span', 'warn', [h('span', 'db-sdot stale'), 'Not connected']));
    else {
      if (status === 'live') {
        const fresh = [].concat(model.needs, model.worth, model.done, model.quiet).filter((i) => isNew(i, st)).length;
        if (fresh) bits.push(h('span', 'db-newlegend', [h('span', 'db-sdot new'), fresh + ' new', txt('span', 'long', ' since ' + stamp(st.lastSeenAt, st.now))]));
      }
      bits.push(h('span', status === 'stale' ? 'warn' : '', [h('span', 'db-sdot ' + (status === 'stale' ? 'stale' : 'live')),
        txt('time', '', agoLabel(status, st.updatedAt, st.now), { attrs: Object.assign({ 'data-role': 'ago', title: 'Last update ' + stamp(st.updatedAt, st.now) }, Number.isFinite(st.updatedAt) ? { datetime: new Date(st.updatedAt).toISOString() } : {}) })]));
    }
    return h('div', 'db-topbar', h('span', 'db-right', bits));
  }

  function toastView(st, fn) {
    if (!st.toast) return null;
    return h('div', 'db-toast', [txt('span', '', st.toast.msg),
      st.toast.undo ? h('button', 'db-undo', ['Undo ', txt('kbd', '', 'Z')], { attrs: { type: 'button' }, on: { click: () => fn.undo && fn.undo() } }) : null], { attrs: { role: 'status' } });
  }
  function keysView(st) {
    if (!st.keys) return null;
    const rows = [['Move', ['J', 'K']], ['Open / close', ['Enter']], ['Close all', ['Esc']], ['Undo', ['Z']], ['This list', ['?']]];
    return h('div', 'db-keys', rows.map(([a, ks]) => h('div', '', [txt('span', '', a), h('span', '', ks.map((k, i) => [i ? ' ' : '', txt('kbd', '', k)]).flat())])), { attrs: { role: 'dialog', 'aria-label': 'Shortcuts' } });
  }

  // the whole screen: model + {open:Set, updatedAt, now, error, toast, keys, lastSeenAt} + {toggle, refresh, act, undo, close}
  function dashboardView(model, st, fn) {
    st = Object.assign({ open: new Set(), now: Date.now() }, st || {}); fn = fn || {};
    if (st.model === undefined) st.model = model;   // callers that hand over the model separately
    const status = !model ? (st.error ? 'error' : 'loading') : feedStatus({ ...st, model });
    let body;
    if (status === 'loading') body = skeletonView();
    else if (status === 'error') body = heroView(null, 'error', st, fn);
    else {
      const showNew = status === 'live';
      const hero = heroView(model, status, st, fn);
      const cols = [[], []];
      for (const s of SECTIONS) { const v = sectionView(s, model[s.level] || [], st, fn, showNew); if (v) cols[s.col].push(v); }
      const empty = !(model.items ? model.items.length : [].concat(model.needs, model.worth, model.done, model.quiet).length);
      body = empty
        ? h('div', '', [hero, h('div', 'db-list-box db-empty', [txt('div', '', Number.isFinite(st.lastSeenAt) ? 'Nothing new since ' + stamp(st.lastSeenAt, st.now) + '.' : 'Nothing to report yet.'),
          model.checkedAt ? txt('div', 'db-checked', 'My last check-in was at ' + stamp(model.checkedAt, st.now) + '.') : null])])
        : h('div', '', [hero, cols[0].length && cols[1].length   // two columns only when both have something; otherwise one column, not a half-empty page
          ? h('div', 'db-cols', [h('div', 'db-col', cols[0]), h('div', 'db-col', cols[1])])
          : h('div', 'db-cols one', h('div', 'db-col', cols[0].concat(cols[1])))]);
    }
    return h('div', 'pdash', [
      topbarView(model, status, st), body,
      h('div', 'db-foot', [txt('span', '', 'Press ? for shortcuts'), txt('button', 'db-link', 'Refresh', { attrs: { type: 'button' }, on: { click: () => fn.refresh && fn.refresh() } })]),
      toastView(st, fn), keysView(st)
    ], { attrs: { 'data-status': status } });
  }

  // the card in the chat that replaces the long "While you slept" text: the same hero line, plus a way into the dashboard
  function morningCardView(model, fn) {
    const calm = model.hero.needs === 0;
    return h('div', 'wslept db-morning ' + (calm ? 'calm' : 'busy'), [
      h('div', 'ws-head', [txt('b', '', 'While you slept')]),
      txt('div', 'db-hero-title', model.hero.title),
      txt('div', 'db-hero-sub', model.hero.sub),
      txt('button', 'amber-btn sm db-open', 'Open dashboard', { attrs: { type: 'button' }, on: { click: () => fn && fn.open && fn.open() } })
    ]);
  }

  // vnode -> real DOM (svg parts need the SVG namespace)
  function mount(v, doc) {
    if (typeof v === 'string') return doc.createTextNode(v);
    const e = v.ns === 'svg' ? doc.createElementNS(SVG_NS, v.t) : doc.createElement(v.t);
    if (v.cls) e.setAttribute('class', v.cls);
    if (v.text != null) e.textContent = v.text;
    for (const k of Object.keys(v.attrs || {})) e.setAttribute(k, v.attrs[k]);
    for (const k of Object.keys(v.on || {})) e.addEventListener(k, v.on[k]);
    for (const c of v.kids || []) e.appendChild(mount(c, doc));
    return e;
  }

  // ---------- keyboard: J/K or arrows move between rows, Esc closes everything open, Z undoes, ? lists the shortcuts
  function keyAction(e) {
    if (!e || e.ctrlKey || e.metaKey || e.altKey) return null;
    const k = e.key;
    if (k === 'j' || k === 'J' || k === 'ArrowDown') return 'next';
    if (k === 'k' || k === 'K' || k === 'ArrowUp') return 'prev';
    if (k === 'Escape') return 'escape';
    if (k === 'z' || k === 'Z') return 'undo';
    if (k === '?') return 'keys';
    return null;
  }
  // moves focus to the next / previous row button inside rootEl; returns the row focused (or null)
  function moveFocus(rootEl, dir) {
    const rows = [...rootEl.querySelectorAll('.db-row')];
    if (!rows.length) return null;
    const i = rows.indexOf(rootEl.ownerDocument.activeElement);
    const to = rows[i < 0 ? (dir > 0 ? 0 : rows.length - 1) : Math.max(0, Math.min(rows.length - 1, i + dir))];
    to.focus();
    return to;
  }

  // ---------- keeping it fresh
  // o: { fetch: () => Promise<model>, act: (action) => Promise<{error?}>, onChange(state, {changed, kind}), now(), setInterval, clearInterval, setTimeout, clearTimeout }
  // state: { model, open:Set, updatedAt, error, now, toast, keys, lastSeenAt }
  // change kinds: 'refresh' (asked the main process), 'ui' (a row opened/closed, toast, shortcut list), 'tick' (only the "ago" text moved)
  function createDashboard(o) {
    const now = o.now || Date.now;
    const setI = o.setInterval || setInterval, clearI = o.clearInterval || clearInterval;
    const setT = o.setTimeout || setTimeout, clearT = o.clearTimeout || clearTimeout;
    const st = { model: null, open: new Set(), updatedAt: NaN, error: '', now: now(), toast: null, keys: false, lastSeenAt: Number.isFinite(o.lastSeenAt) ? o.lastSeenAt : NaN };
    let seq = 0, timers = [], running = false, inflight = null, again = false, toastTimer = null;
    const emit = (changed, kind) => { st.now = now(); if (o.onChange) o.onChange(st, { changed, kind: kind || 'refresh' }); };

    const readModel = () => new Promise((resolve, reject) => {
      const t = setT(() => reject(new Error('The update files did not answer in time.')), o.fetchTimeoutMs || FETCH_TIMEOUT_MS);
      if (t && t.unref) t.unref();
      let p; try { p = Promise.resolve(o.fetch()); } catch (e) { p = Promise.reject(e); }   // asked right now, not on the next tick
      p.then((v) => { clearT(t); resolve(v); }, (e) => { clearT(t); reject(e); });
    });

    async function refresh() {
      if (inflight) { again = true; return inflight; }   // one request at a time; one more after it if something changed meanwhile
      const my = ++seq;
      inflight = (async () => {
        let changed = false;
        try {
          const m = await readModel();
          if (my === seq) {
            if (!m || !m.hero) throw new Error('No update came back.');   // the main process could not build one: say so instead of waiting forever
            changed = !st.model || st.model.signature !== m.signature;
            if (changed) st.model = m;
            st.updatedAt = now(); st.error = '';
          }
        } catch (e) { st.error = String((e && e.message) || e); changed = true; }
        emit(changed);
        return changed;
      })();
      try { return await inflight; } finally { inflight = null; if (again) { again = false; refresh(); } }
    }

    function setToast(t) {
      if (toastTimer) { clearT(toastTimer); toastTimer = null; }
      st.toast = t;
      if (t) { toastTimer = setT(() => { toastTimer = null; st.toast = null; emit(false, 'ui'); }, TOAST_MS); if (toastTimer && toastTimer.unref) toastTimer.unref(); }
      emit(false, 'ui');
    }

    // run a button's action (the main process really does it); an action with a "toast" shows it, with an undo when the action has one
    async function act(a) {
      if (!a || !o.act) return;
      let r;
      try { r = await o.act(a); } catch (e) { r = { error: String((e && e.message) || e) }; }
      if (r && r.error) { setToast({ msg: 'That did not work: ' + r.error, undo: null }); return r; }
      if (a.toast) setToast({ msg: a.toast, undo: a.undo || null });
      if (a.kind === 'override') await refresh();
      return r;
    }
    async function undo() {
      const u = st.toast && st.toast.undo;
      if (!u) return false;
      setToast({ msg: 'Undone.', undo: null });
      try { const r = await o.act(u); if (r && r.error) setToast({ msg: 'Could not undo: ' + r.error, undo: null }); } catch (e) { setToast({ msg: 'Could not undo: ' + String((e && e.message) || e), undo: null }); }
      await refresh();
      return true;
    }
    return {
      state: st,
      refresh, act, undo,
      // call when the window comes to the front / the main process says a file changed
      onFocus: () => refresh(),
      onSourceChanged: () => refresh(),
      toggle(id) { if (st.open.has(id)) st.open.delete(id); else st.open.add(id); emit(false, 'ui'); },
      toggleKeys() { st.keys = !st.keys; emit(false, 'ui'); },
      // Esc: close what is open (rows, the shortcut list, the toast); false when there was nothing to close
      closeAll() { const any = st.open.size > 0 || st.keys || !!st.toast; if (!any) return false; st.open.clear(); st.keys = false; setToast(null); return true; },
      setLastSeen(ms) { st.lastSeenAt = Number.isFinite(ms) ? ms : NaN; },
      start() {
        if (running) return; running = true;
        refresh();
        timers.push(setI(refresh, o.refreshMs || REFRESH_MS));
        timers.push(setI(() => emit(false, 'tick'), o.tickMs || TICK_MS));   // only the "updated … ago" text moves
      },
      stop() { running = false; for (const t of timers) clearI(t); timers = []; if (toastTimer) { clearT(toastTimer); toastTimer = null; } }
    };
  }

  return { REFRESH_MS, TICK_MS, STALE_AFTER_MS, agoText, agoLabel, feedStatus, isNew, rowView, dashboardView, morningCardView, mount, createDashboard, keyAction, moveFocus, iconView, ICONS, clock, h };
});
