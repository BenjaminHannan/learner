'use strict';
// The side panel beside the chat (wide windows only): Now (what Glim is doing, the plan, Motes), Goals (goals and skills kept in memory),
// Ideas (starter cards that put a request in the box). app.js feeds Now through Side.set*; Goals reads memory when opened.
(function () {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const KEY_OPEN = 'side.open', KEY_TAB = 'side.tab', KEY_DONE = 'side.goalsDone';
  const get = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } };
  const put = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } };

  const IDEAS = [
    ['Plan my week', 'Look at my calendar and mail and help me plan this week, with the most important thing first.'],
    ['Catch me up on email', 'Check my email and tell me only what needs me today.'],
    ['Learn something for me', 'Go learn about '],
    ['Break a goal into steps', 'Help me turn a goal of mine into a plan with small steps for this week.'],
    ['Watch something for me', 'Keep an eye on this for me and tell me when it changes: '],
    ['Get ready for tomorrow', 'What do I have tomorrow, and what should I do tonight to be ready?']
  ];

  const st = { tab: get(KEY_TAB, 'now'), open: get(KEY_OPEN, '1') !== '0', said: '', running: false, plan: [], sparks: [], showMotes: false, onPick: null, desk: null };
  let root, body, tabs;

  function nowView() {
    const v = el('div', 'sd-view');
    const h = el('div', 'sd-sec');
    h.append(el('div', 'sd-label', 'Glim'), el('div', 'sd-big', st.running ? (st.said || 'Working…') : 'Ready'));
    v.append(h);
    if (st.plan.length) {
      const s = el('div', 'sd-sec'); s.append(el('div', 'sd-label', 'Plan'));
      const ol = el('ol', 'sd-plan');
      for (const p of st.plan) ol.append(el('li', null, String(p).replace(/\*\*|__|`/g, '')));
      s.append(ol); v.append(s);
    }
    if (!st.showMotes) return v; // one Glim: its helpers stay invisible unless Show Motes is on
    const s2 = el('div', 'sd-sec'); s2.append(el('div', 'sd-label', 'Motes'));
    const list = st.sparks.filter((h2) => !(h2.status === 'stopped' && h2.schedule === 'once'));
    if (!list.length) s2.append(el('div', 'sd-dim', 'None yet. Ask Glim for a helper and it will show up here.'));
    for (const sp of list) {
      const r = el('div', 'sd-row'); r.append(el('b', null, sp.name), el('span', 'sd-dim', (sp.status === 'running' ? 'working' : sp.paused ? 'paused' : sp.next ? 'next ' + new Date(sp.next).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' }) : sp.status || '')));
      s2.append(r);
    }
    v.append(s2); return v;
  }
  async function goalsView() {
    const v = el('div', 'sd-view');
    let facts = [];
    try { const r = await st.desk.memory.list(); facts = Array.isArray(r) ? r : (r && r.facts) || []; } catch (e) { /* no memory yet */ }
    let done = {}; try { done = JSON.parse(get(KEY_DONE, '{}')) || {}; } catch (e) { done = {}; }
    const group = (title, re, tickable, empty) => {
      const s = el('div', 'sd-sec'); s.append(el('div', 'sd-label', title));
      const items = facts.filter((f) => re.test(String(f.topic || '')));
      if (!items.length) s.append(el('div', 'sd-dim', empty));
      for (const f of items) {
        const r = el('label', 'sd-goal' + (done[f.id] ? ' done' : ''));
        if (tickable) { const c = el('input'); c.type = 'checkbox'; c.checked = !!done[f.id]; c.onchange = () => { done[f.id] = c.checked; put(KEY_DONE, JSON.stringify(done)); r.classList.toggle('done', c.checked); }; r.append(c); }
        r.append(el('span', null, f.text)); s.append(r);
      }
      v.append(s);
    };
    group('Goals', /^goal/i, true, 'Tell Glim your short-term and long-term goals and it will plan them here.');
    group('Skills I am learning', /^skill/i, false, 'Say "go learn about ..." and what Glim learns shows up here.');
    return v;
  }
  function ideasView() {
    const v = el('div', 'sd-view');
    for (const [t, text] of IDEAS) {
      const b = el('button', 'sd-idea'); b.append(el('b', null, t), el('span', 'sd-dim', text.length > 70 ? text.slice(0, 68) + '…' : text));
      b.onclick = () => st.onPick && st.onPick(text); v.append(b);
    }
    return v;
  }

  let paintSeq = 0;
  async function paint() {
    if (!root) return;
    const seq = ++paintSeq;
    for (const b of tabs.children) b.classList.toggle('on', b.dataset.tab === st.tab);
    const view = st.tab === 'goals' ? await goalsView() : st.tab === 'ideas' ? ideasView() : nowView();
    if (seq !== paintSeq) return;
    body.textContent = ''; body.append(view);
  }
  function layout() {
    document.body.classList.toggle('side-on', st.open);
    const b = $('#btnSide'); if (b) { b.setAttribute('aria-pressed', st.open ? 'true' : 'false'); b.classList.toggle('on', st.open); }
  }
  const api = {
    init(desk, onPick) {
      st.desk = desk; st.onPick = onPick; root = $('#side'); if (!root) return;
      const head = el('div', 'sd-head'); tabs = el('div', 'sd-tabs');
      for (const [k, label] of [['now', 'Now'], ['goals', 'Goals'], ['ideas', 'Ideas']]) {
        const b = el('button', null, label); b.dataset.tab = k; b.onclick = () => { st.tab = k; put(KEY_TAB, k); paint(); }; tabs.append(b);
      }
      const x = el('button', 'sd-x', '×'); x.title = 'Close the panel'; x.setAttribute('aria-label', 'Close the panel'); x.onclick = () => api.toggle(false);
      head.append(tabs, x); body = el('div', 'sd-body'); root.append(head, body);
      const tb = $('#btnSide'); if (tb) tb.onclick = () => api.toggle();
      layout(); paint();
    },
    toggle(on) { st.open = on == null ? !st.open : !!on; put(KEY_OPEN, st.open ? '1' : '0'); layout(); if (st.open) paint(); },
    setRunning(r) { st.running = !!r; if (!r) st.said = ''; if (st.tab === 'now') paint(); },
    setSaid(t) { st.said = String(t || '').slice(0, 160); if (st.tab === 'now') paint(); },
    setPlan(items) { st.plan = Array.isArray(items) ? items.slice(0, 8) : []; if (st.tab === 'now') paint(); },
    setSparks(list, show) { st.sparks = Array.isArray(list) ? list : []; st.showMotes = !!show; if (st.tab === 'now') paint(); },
    refresh() { if (st.open && st.tab === 'goals') paint(); }
  };
  window.Side = api;
})();
