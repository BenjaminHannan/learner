'use strict';
// "Important updates" dashboard: the LOOK and the KEEP-FRESH logic. No data rules live here (those are in src/dashboard.js);
// this file only turns a dashboard model into a picture and keeps it up to date. To change the design, replace the view
// functions (dashboardView / morningCardView / mount) and leave the rest alone: they take the same model.
//
//   views return plain "vnodes" { t, cls, text, attrs, on, kids } so they can be tested without a browser, and mount() makes real DOM.
//   createDashboard() is the refresher: it asks for a fresh model every 60 s, whenever the window gets focus, and whenever the
//   main process says a source file changed; a changed model repaints (hero line included) without a reload.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Dashboard = factory();
})(typeof window !== 'undefined' ? window : globalThis, () => {
  const REFRESH_MS = 60000;
  const TICK_MS = 20000;   // how often the "updated … ago" line is redrawn

  // ---------- tiny vnode helpers
  const h = (t, cls, kids, extra) => ({ t, cls: cls || '', kids: [].concat(kids == null ? [] : kids).filter((k) => k != null && k !== false), ...(extra || {}) });
  const txt = (t, cls, s, extra) => h(t, cls, [], { text: s, ...(extra || {}) });

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

  // ---------- views (replaceable)
  function cardView(item, isOpen, onToggle) {
    const body = [];
    for (const l of item.lines || []) body.push(txt('p', 'db-line', l));
    if (item.list && item.list.length) body.push(h('ul', 'db-list', item.list.map((s) => txt('li', '', s))));
    if (item.details && item.details.length) body.push(h('details', 'db-details', [txt('summary', '', 'Details'), h('div', 'db-raw', item.details.map((s) => txt('code', '', s)))]));
    return h('div', 'db-card' + (item.dim ? ' dim' : '') + (isOpen ? ' open' : ''), [
      h('button', 'db-row', [
        txt('span', 'db-icon', item.icon, { attrs: { 'aria-hidden': 'true' } }),
        txt('span', 'db-title', item.title),
        txt('span', 'db-tag ' + item.tag.tone, item.tag.text)
      ], { attrs: { type: 'button', 'aria-expanded': String(!!isOpen), 'data-id': item.id }, on: { click: () => onToggle(item.id) } }),
      isOpen ? h('div', 'db-body', body) : null
    ], { attrs: { 'data-id': item.id } });
  }

  function section(label, items, st, onToggle) {
    if (!items.length) return null;
    return h('section', 'db-sec', [txt('h3', 'db-label', label), h('div', 'db-cards', items.map((i) => cardView(i, st.open.has(i.id), onToggle)))]);
  }

  // the whole screen: model + {open:Set, updatedAt, now} + {toggle, refresh, close}
  function dashboardView(model, st, fn) {
    st = st || { open: new Set() }; fn = fn || {};
    const calm = model.hero.needs === 0;
    return h('div', 'db', [
      h('div', 'db-hero ' + (calm ? 'calm' : 'busy'), [
        txt('div', 'db-hero-icon', calm ? '✅' : '❗', { attrs: { 'aria-hidden': 'true' } }),
        h('div', 'db-hero-text', [txt('div', 'db-hero-title', model.hero.title), txt('div', 'db-hero-sub', model.hero.sub)])
      ], { attrs: { role: 'status', 'aria-live': 'polite' } }),
      section('NEEDS YOU', model.needs, st, fn.toggle || (() => {})),
      section('DONE FOR YOU', model.done, st, fn.toggle || (() => {})),
      section('WORTH KNOWING', model.worth, st, fn.toggle || (() => {})),
      h('div', 'db-foot', [
        txt('span', 'db-ago', agoText(st.updatedAt, st.now), { attrs: { 'data-role': 'ago' } }),
        txt('button', 'ghost sm db-refresh', 'Refresh', { attrs: { type: 'button' }, on: { click: () => fn.refresh && fn.refresh() } })
      ])
    ]);
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

  // vnode -> real DOM
  function mount(v, doc) {
    if (typeof v === 'string') return doc.createTextNode(v);
    const e = doc.createElement(v.t);
    if (v.cls) e.className = v.cls;
    if (v.text != null) e.textContent = v.text;
    for (const k of Object.keys(v.attrs || {})) e.setAttribute(k, v.attrs[k]);
    for (const k of Object.keys(v.on || {})) e.addEventListener(k, v.on[k]);
    for (const c of v.kids || []) e.appendChild(mount(c, doc));
    return e;
  }

  // ---------- keeping it fresh
  // o: { fetch: () => Promise<model>, onChange(state, {changed}), now(), setInterval, clearInterval }
  // state: { model, open:Set, updatedAt, error, now }
  function createDashboard(o) {
    const now = o.now || Date.now;
    const setI = o.setInterval || setInterval, clearI = o.clearInterval || clearInterval;
    const st = { model: null, open: new Set(), updatedAt: NaN, error: '', now: now() };
    let seq = 0, timers = [], running = false, inflight = null, again = false;
    // kind: 'refresh' (asked the main process), 'toggle' (a card opened/closed), 'tick' (only the "ago" text moved)
    const emit = (changed, kind) => { st.now = now(); if (o.onChange) o.onChange(st, { changed, kind: kind || 'refresh' }); };

    async function refresh() {
      if (inflight) { again = true; return inflight; }   // one request at a time; one more after it if something changed meanwhile
      const my = ++seq;
      inflight = (async () => {
        let changed = false;
        try {
          const m = await o.fetch();
          if (my === seq && m && m.hero) {
            changed = !st.model || st.model.signature !== m.signature;
            if (changed) st.model = m;
            st.updatedAt = now(); st.error = '';
          }
        } catch (e) { st.error = String((e && e.message) || e); }
        emit(changed);
        return changed;
      })();
      try { return await inflight; } finally { inflight = null; if (again) { again = false; refresh(); } }
    }
    return {
      state: st,
      refresh,
      // call when the window comes to the front / the main process says a file changed
      onFocus: () => refresh(),
      onSourceChanged: () => refresh(),
      toggle(id) { if (st.open.has(id)) st.open.delete(id); else st.open.add(id); emit(false, 'toggle'); },
      start() {
        if (running) return; running = true;
        refresh();
        timers.push(setI(refresh, o.refreshMs || REFRESH_MS));
        timers.push(setI(() => emit(false, 'tick'), o.tickMs || TICK_MS));   // only the "updated … ago" text moves
      },
      stop() { running = false; for (const t of timers) clearI(t); timers = []; }
    };
  }

  return { REFRESH_MS, TICK_MS, agoText, cardView, dashboardView, morningCardView, mount, createDashboard, h };
});
