'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const desk = window.desk;
  const md = Md.md;
  window.__md = md; // for tests

  // ---------- icons ----------
  const svg = (inner, cls) => '<svg class="' + (cls || '') + '" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + inner + '</svg>';
  const P = {
    search: '<circle cx="7" cy="7" r="4.2"/><path d="M10.3 10.3L14 14"/>',
    globe: '<circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2c2 2 2 10 0 12M8 2c-2 2-2 10 0 12"/>',
    cursor: '<path d="M3.5 2.5l9 4.5-4 1.2-1.2 4z"/>',
    keyboard: '<rect x="1.5" y="4" width="13" height="8" rx="1.8"/><path d="M4.5 7h.01M7 7h.01M9.5 7h.01M12 7h.01M5 10h6"/>',
    scroll: '<path d="M8 2v12M5 5l3-3 3 3M5 11l3 3 3-3"/>',
    back: '<path d="M13 8H3M7 4L3 8l4 4"/>',
    doc: '<path d="M4 1.5h5.5L13 5v9.5H4z"/><path d="M6 8h5M6 11h5"/>',
    monitor: '<rect x="1.5" y="2.5" width="13" height="9" rx="1.5"/><path d="M5.5 14h5M8 11.5V14"/>',
    app: '<rect x="2" y="2" width="12" height="12" rx="3.5"/>',
    terminal: '<path d="M2 4l4 4-4 4M8 12h6"/>',
    book: '<path d="M3 2.5h8.5A1.5 1.5 0 0113 4v9.5H4.5A1.5 1.5 0 013 12z"/><path d="M3 12a1.5 1.5 0 011.5-1.5H13"/>',
    question: '<circle cx="8" cy="8" r="6"/><path d="M6.2 6.3A1.9 1.9 0 018 5a1.8 1.8 0 011 3.3c-.7.5-1 .8-1 1.5M8 11.6h.01"/>',
    person: '<circle cx="8" cy="5.5" r="2.5"/><path d="M3 13.5c.5-3 2.5-4 5-4s4.5 1 5 4"/>',
    x: '<path d="M4 4l8 8M12 4l-8 8"/>',
    check: '<path d="M3 8.5l3.2 3.2L13 4.8"/>',
    spin: '<path d="M8 2a6 6 0 106 6" />',
    dot: '<circle cx="8" cy="8" r="2"/>'
  };
  const TOOL_ICON = { web_search: 'search', browser_go: 'globe', browser_click: 'cursor', browser_type: 'keyboard', browser_scroll: 'scroll', browser_back: 'back', browser_read: 'doc', screen_look: 'monitor', screen_click: 'monitor', screen_type: 'monitor', screen_key: 'keyboard', open_app: 'app', run_shell: 'terminal', diary_search: 'book', ask_user: 'question', agent_start: 'person', agent_list: 'person', agent_stop: 'person' };
  const icon = (name) => svg(P[name] || P.dot);
  const CHEV = '<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M4 2l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  // ---------- state ----------
  let thread = null;      // {id,title,helper}
  let running = false;
  let settings = {};
  let info = {};
  let blk = null;         // current assistant block {root, col}
  let act = null;         // current activity group
  let tn = null;          // streaming text of the current model response {text, raw, think, thinkRaw, t0, anchor}
  const stepEls = new Map();
  const bcards = new Map();   // card id -> {root, key, ...}
  const scards = new Map();   // screen card id -> {thumb, text, image}
  const rids = new Map();     // approval rid / ask id -> {card, btns}
  let pendingSteers = [];     // steer notes shown but not yet confirmed by the agent
  const msgs = $('#msgs');
  const scroller = $('#scroll');
  const input = $('#input');
  let stick = true;
  scroller.addEventListener('scroll', () => { stick = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80; });
  const toBottom = () => { if (stick) scroller.scrollTop = scroller.scrollHeight; };
  const secs = (ms) => { const s = Math.max(1, Math.round(ms / 1000)); return s < 60 ? s + ' s' : Math.floor(s / 60) + ' min ' + (s % 60 ? s % 60 + ' s' : ''); };
  const hostOf = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u || ''; } };

  // ---------- blocks, activity groups ----------
  function newBlock() { blk = null; act = null; tn = null; }
  function ensureBlock() {
    if (blk) return blk;
    const root = el('div', 'ablock');
    root.append(Mascot.el('idle', 28, { cls: 'avatar', still: true }));
    const col = el('div', 'acol');
    root.append(col); msgs.append(root);
    blk = { root, col };
    return blk;
  }
  function ensureAct(before) {
    if (act && !act.finished) return act;
    const b = ensureBlock();
    const root = el('div', 'activity running open');
    const head = el('button', 'act-head');
    const ico = el('span', 'act-ico'); ico.innerHTML = svg(P.spin);
    const title = el('span', 'act-title', 'Glim is working');
    const sub = el('span', 'act-sub', '');
    const chevWrap = el('span'); chevWrap.innerHTML = CHEV; chevWrap.style.display = 'inline-flex';
    head.append(ico, title, sub, chevWrap);
    const live = el('div', 'act-live'); live.append(el('i', 'dot'), el('span', 't', 'Starting…'));
    const cards = el('div', 'act-cards');
    const body = el('div', 'act-body');
    root.append(head, live, cards, body);
    const a = { root, head, ico, title, sub, live, liveT: live.lastChild, cards, body, steps: 0, bad: 0, t0: Date.now(), userToggled: false, finished: false, lastNar: '', plan: null };
    head.onclick = () => { a.userToggled = true; root.classList.toggle('open'); };
    if (before && before.parentNode === b.col) b.col.insertBefore(root, before); else b.col.append(root);
    root._act = a;
    act = a;
    return a;
  }
  function relabel(a) {
    if (a.finished) {
      a.title.textContent = 'Did ' + (a.steps === 1 ? '1 thing' : a.steps + ' things');
      a.sub.textContent = '· ' + secs(a.endT - a.t0) + (a.bad ? ' · ' + a.bad + ' failed' : '');
    } else {
      a.title.textContent = 'Glim is working';
      a.sub.textContent = a.steps ? '· ' + (a.steps === 1 ? '1 step' : a.steps + ' steps') : '';
    }
  }
  function finishAct(a) {
    if (!a || a.finished) return;
    a.finished = true; a.endT = Date.now();
    a.root.classList.remove('running'); a.root.classList.add('done');
    a.ico.innerHTML = svg(P.check);
    a.live.hidden = true;
    if (!a.userToggled) a.root.classList.remove('open');
    if (a.plan) a.plan.classList.add('done');
    a.root.querySelectorAll('.step.run').forEach((s) => { s.classList.remove('run'); s.classList.add('bad'); });
    for (const c of a.cards.querySelectorAll('.bcard.active')) c.classList.remove('active');
    if (!a.steps && !a.cards.children.length && !a.body.children.length) a.root.remove();
    relabel(a);
  }
  const finishAll = () => { document.querySelectorAll('.activity.running').forEach((r) => { if (r._act) finishAct(r._act); }); if (act) finishAct(act); };
  const ensureActTracked = ensureAct;

  // ---------- Ben's messages ----------
  function addUser(text, steer, queued) {
    const w = msgs.querySelector('.welcome'); if (w) w.remove();
    if (act && !act.finished) finishAct(act);
    const u = el('div', 'user' + (steer ? ' steer' : '') + (queued ? ' queued' : ''), text);
    msgs.append(u); newBlock(); toBottom();
    return u;
  }

  // ---------- streaming text of one model response ----------
  function startTn() { tn = { text: null, raw: '', think: null, thinkRaw: '', t0: Date.now() }; return tn; }
  function thinkBlock(secsN, text, live) {
    const d = el('details', 'think' + (live ? ' live' : ''));
    const s = el('summary', null, live ? 'Thinking…' : 'Thought for ' + (secsN || 1) + ' s');
    const pre = el('pre', null, text || '');
    d.append(s, pre);
    return { d, s, pre };
  }
  let raf = 0;
  function paintText() {
    if (raf) return;
    raf = requestAnimationFrame(() => { raf = 0; if (tn && tn.text) { tn.text.innerHTML = md(tn.raw); toBottom(); } });
  }
  function onReasoning(d) {
    const t = tn || startTn();
    if (!t.think) { const b = thinkBlock(0, '', true); t.think = b; ensureBlock().col.append(b.d); }
    t.thinkRaw += d; t.think.pre.textContent = t.thinkRaw;
    t.think.pre.scrollTop = t.think.pre.scrollHeight;
  }
  function onText(d) {
    const t = tn || startTn();
    if (!t.text) { t.text = el('div', 'atext'); ensureBlock().col.append(t.text); }
    t.raw += d; paintText();
  }
  function ttftNote(ms) { return ms ? 'first word in ' + (ms < 1000 ? ms + ' ms' : (ms / 1000).toFixed(1) + ' s') : ''; }
  function onAssistantEnd(ev) {
    const t = tn;
    tn = null;
    const hasTools = (ev.toolCalls || 0) > 0;
    if (!t) return;
    const clean = Md.stripActions(t.raw).trim();
    if (t.think) { t.think.d.classList.remove('live'); t.think.s.textContent = 'Thought for ' + (ev.thinkSecs || Math.max(1, Math.round((Date.now() - t.t0) / 1000))) + ' s'; }
    if (!hasTools) {
      // the answer: stays prominent below the (collapsed) activity group
      if (t.text) {
        if (!clean) t.text.remove();
        else { t.text.innerHTML = md(t.raw); const n = ttftNote(ev.ttftMs); if (n) t.text.append(el('span', 'ttft', n)); }
      }
      if (act && !act.finished) finishAct(act);
      toBottom();
      return;
    }
    // narration before tool calls: fold it into the activity group, one clamped line each, no repeats
    const a = ensureActTracked(t.think ? t.think.d : t.text);
    if (t.think) { a.body.append(t.think.d); }
    if (t.text) {
      const norm = clean.toLowerCase().replace(/\W+/g, ' ');
      const isPlan = /^\s*\d+[.)]\s/m.test(clean); // the plan has its own checklist
      if (clean && !isPlan && norm !== a.lastNar) { a.lastNar = norm; a.body.append(el('div', 'nar sel', clean.replace(/\s+/g, ' '))); }
      t.text.remove();
    }
    toBottom();
  }

  function setPlan(items) {
    if (!items || !items.length) return;
    const a = ensureActTracked();
    if (a.plan) a.plan.remove();
    const d = el('details', 'plan'); d.open = true;
    const s = el('summary'); s.append(document.createTextNode('Plan · ' + items.length + ' steps'));
    const ol = el('ol');
    for (const i of items) ol.append(el('li', null, i));
    d.append(s, ol);
    a.body.prepend(d); a.plan = d;
    if (a.finished) d.classList.add('done');
  }

  // ---------- steps ----------
  function stepEl(id, tool, args, summary, state, preview) {
    const wrap = el('div', 'step ' + (state || 'run'));
    const row = el('button', 'pill');
    const ico = el('span', 'ico'); ico.innerHTML = icon(state === 'bad' ? 'x' : TOOL_ICON[tool]);
    const sum = el('span', 'sum', summary);
    row.append(ico, sum); row.insertAdjacentHTML('beforeend', CHEV);
    const detail = el('div', 'detail'); detail.hidden = true;
    const fill = (pv) => {
      detail.textContent = '';
      const a = el('div'); const b = el('b', null, tool + ' '); a.append(b, document.createTextNode(typeof args === 'string' ? args : JSON.stringify(args)));
      detail.append(a);
      if (pv) { detail.append(document.createTextNode('\n')); detail.append(document.createTextNode(pv)); }
    };
    fill(preview);
    row.onclick = () => { detail.hidden = !detail.hidden; wrap.classList.toggle('open', !detail.hidden); };
    wrap.append(row, detail);
    wrap._fill = fill; wrap._sum = sum; wrap._ico = ico; wrap._tool = tool;
    return wrap;
  }
  function onStepStart(ev) {
    const a = ensureActTracked();
    const w = stepEl(ev.id, ev.tool, ev.args, ev.summary, 'run');
    a.body.append(w); stepEls.set(ev.id, w);
    a.steps++; relabel(a);
    a.liveT.textContent = ev.summary;
    a.body.scrollTop = a.body.scrollHeight;
    toBottom();
  }
  function onStepEnd(ev) {
    const w = stepEls.get(ev.id); if (!w) return;
    w.classList.remove('run'); w.classList.add(ev.ok ? 'ok' : 'bad');
    w._sum.textContent = ev.summary;
    w._ico.innerHTML = icon(ev.ok ? TOOL_ICON[w._tool] : 'x');
    w._fill(ev.result || ev.preview);
    if (!ev.ok && act) { act.bad++; relabel(act); }
    if (act && !act.finished) act.liveT.textContent = ev.summary;
    toBottom();
  }

  // ---------- live browser / screen cards ----------
  function favNode(c) {
    c.fav.textContent = '';
    if (c.favicon) { const i = new Image(); i.alt = ''; i.src = c.favicon; i.onerror = () => { c.fav.textContent = (hostOf(c.urlFull)[0] || '·').toUpperCase(); }; c.fav.append(i); }
    else c.fav.textContent = (hostOf(c.urlFull)[0] || '·').toUpperCase();
  }
  function upsertBCard(ev) {
    let c = bcards.get(ev.id);
    if (!c) {
      const root = el('button', 'bcard');
      const top = el('div', 'bc-top');
      const fav = el('span', 'bc-fav');
      const names = el('div', 'bc-names'); const title = el('span', 'bc-title'); const url = el('span', 'bc-url');
      names.append(title, url); top.append(fav, names);
      const th = el('div', 'bc-thumb'); const ph = el('div', 'ph', 'Loading the page…'); th.append(ph);
      const foot = el('div', 'bc-foot'); const live = el('i', 'live'); const lbl = el('span', 'lbl'); const open = el('span', 'open', 'Open');
      foot.append(live, lbl, open);
      root.append(top, th, foot);
      c = { id: ev.id, root, fav, title, url, th, ph, lbl, key: ev.key, favicon: '', thumbImg: null };
      root.onclick = () => desk.browser.open(c.key, c.urlFull);
      bcards.set(ev.id, c);
      ensureActTracked().cards.append(root);
    }
    c.key = ev.key || c.key;
    if (ev.url !== undefined) c.urlFull = ev.url;
    if (ev.favicon !== undefined && ev.favicon !== c.favicon) { c.favicon = ev.favicon; favNode(c); } else if (!c.fav.textContent && !c.fav.firstChild) favNode(c);
    c.title.textContent = ev.title || hostOf(ev.url) || 'Browser';
    c.url.textContent = hostOf(ev.url) || 'Starting…';
    if (ev.thumb) {
      if (!c.thumbImg) { c.thumbImg = new Image(); c.thumbImg.alt = 'Live preview of the page'; c.th.textContent = ''; c.th.append(c.thumbImg); }
      c.thumbImg.src = ev.thumb;
    }
    if (ev.active !== undefined) c.active = !!ev.active;
    if (ev.login !== undefined) c.login = !!ev.login;
    c.root.classList.toggle('active', !!c.active && !c.login);
    c.root.classList.toggle('login', !!c.login);
    c.lbl.textContent = c.login ? 'Sign-in needed: click to open' : c.active ? 'Glim is browsing' : 'Click to open the browser';
    c.root.title = c.login ? 'Open the sign-in window' : 'Open this page in a popup you can use';
    toBottom();
    return c;
  }
  function upsertSCard(ev) {
    let c = scards.get(ev.id);
    if (!c) {
      const root = el('button', 'bcard screen');
      const top = el('div', 'bc-top'); const fav = el('span', 'bc-fav'); fav.innerHTML = icon('monitor'); fav.firstChild.style.width = '1rem';
      const names = el('div', 'bc-names'); names.append(el('span', 'bc-title', 'Glim looked at your screen'), el('span', 'bc-url', 'Latest capture'));
      top.append(fav, names);
      const th = el('div', 'bc-thumb'); const foot = el('div', 'bc-foot'); foot.append(el('span', 'lbl', 'Click to see the full capture'), el('span', 'open', 'View'));
      root.append(top, th, foot);
      c = { id: ev.id, root, th, thumb: '', text: '', image: null };
      root.onclick = () => openScreen(c);
      scards.set(ev.id, c);
      ensureActTracked().cards.append(root);
    }
    if (ev.thumb) { c.thumb = ev.thumb; c.th.textContent = ''; const i = new Image(); i.alt = 'Screen capture'; i.src = ev.thumb; c.th.append(i); }
    if (ev.text !== undefined) c.text = ev.text;
    if (ev.image) c.image = ev.image;
    toBottom();
  }
  function openScreen(c) {
    $('#screenImg').src = c.image || c.thumb || ''; $('#screenImg').hidden = !(c.image || c.thumb);
    $('#screenText').textContent = c.text || '';
    $('#screenModal').hidden = false;
  }
  $('#screenClose').onclick = () => { $('#screenModal').hidden = true; };
  $('#screenModal').addEventListener('mousedown', (e) => { if (e.target.id === 'screenModal') $('#screenModal').hidden = true; });
  const lastBCard = () => { const all = [...bcards.values()]; return all.length ? all[all.length - 1] : null; };

  // ---------- approvals / questions ----------
  function card(cls, why) { const c = el('div', 'card ' + (cls || '')); c.append(el('div', 'why', why)); return c; }
  function onApproval(ev) {
    const host = ensureActTracked().cards;
    const c = card(ev.danger ? 'danger' : '', ev.danger ? 'Risky command: needs your OK' : 'Needs your OK');
    if (ev.kind === 'shell') { c.append(el('code', 'cmd sel', ev.text)); } else c.append(el('div', null, ev.text));
    const btns = el('div', 'btns');
    const done = (v, label, remote) => { if (c.classList.contains('done')) return; if (!remote) desk.agent.respond(ev.rid || ev.id, v); c.classList.add('done'); btns.remove(); c.append(el('div', 'dim small', label)); refreshMood(); };
    const once = el('button', 'amber-btn', 'Allow once'); once.onclick = () => done('once', 'Allowed once');
    btns.append(once);
    if (!ev.danger) { const task = el('button', 'ghost', 'Allow for this task'); task.onclick = () => done('task', 'Allowed for this task'); btns.append(task); }
    const deny = el('button', 'deny', 'Deny'); deny.onclick = () => done('deny', 'Denied');
    btns.append(deny); c.append(btns);
    rids.set(ev.rid || ev.id, { done });
    host.append(c); toBottom(); refreshMood();
  }
  function onAsk(ev) {
    const host = ensureActTracked().cards;
    const c = card('', 'Glim asks');
    c.append(el('div', null, ev.question));
    const ta = el('textarea'); ta.placeholder = 'Your answer…'; ta.setAttribute('aria-label', 'Your answer');
    const btns = el('div', 'btns');
    const send = el('button', 'amber-btn', 'Reply');
    const reply = (text, remote) => { if (!text || c.classList.contains('done')) return; if (!remote) desk.agent.respond(ev.id, text); c.classList.add('done'); ta.disabled = true; btns.remove(); c.append(el('div', 'dim small', 'You: ' + text)); refreshMood(); };
    send.onclick = () => reply(ta.value.trim());
    ta.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); reply(ta.value.trim()); } });
    btns.append(send);
    for (const q of ['Yes, go ahead', 'No']) { const b = el('button', 'ghost', q); b.onclick = () => reply(q); btns.append(b); }
    c.append(ta, btns); host.append(c); toBottom(); setTimeout(() => ta.focus(), 50);
    rids.set(ev.id, { done: (v) => reply(String(v), true) });
    refreshMood();
  }
  function addNotice(who, text) {
    const n = el('div', 'notice sel');
    n.append(el('b', null, who ? who + ': ' : ''), document.createTextNode(text || ''));
    msgs.append(n); newBlock(); toBottom();
  }

  // ---------- run state ----------
  function setRunning(r) {
    running = r;
    $('#btnSend').textContent = r ? 'Steer' : 'Send'; $('#btnStop').hidden = !r; $('#runState').hidden = !r;
    refreshMood();
    input.placeholder = r ? 'Add a note to steer the current task…' : thread && thread.helper ? 'This is a helper’s thread. Type here to steer it while it runs.' : 'Ask Glim to do something…';
    $('#hint').textContent = r ? 'Enter sends a steer note · Esc stops' : 'Enter to send · Shift+Enter for a new line';
  }

  // ---------- Glim's mood: one status source (main) + local run state ----------
  let mood = 'idle', gw = { state: 'down' }, glim = 'idle', errorUntil = 0, doneUntil = 0, moodTimer = 0, lastActive = Date.now(), glanceTimer = 0;
  const logo = Mascot.el('idle', 28, { cls: 'follow' });
  $('#logo').append(logo);
  function refreshMood() {
    const now = Date.now();
    let m = 'idle';
    if (gw.state === 'down' || gw.state === 'warming') m = 'sleepy';
    else if (document.querySelector('.card:not(.done)')) m = 'waiting';
    else if (running) m = document.querySelector('.step.run') ? 'working' : 'thinking';
    else if (errorUntil > now) m = 'error';
    else if (doneUntil > now) m = 'done';
    else if (glim === 'error') m = 'error'; else if (glim === 'waiting') m = 'waiting'; else if (glim === 'working') m = 'working';
    else if (now - lastActive > 5 * 60000) m = 'sleepy';
    mood = m;
    document.querySelectorAll('.mascot-wrap.follow').forEach((w) => Mascot.set(w, m));
    clearTimeout(moodTimer);
    const next = Math.max(errorUntil, doneUntil);
    if (next > now) moodTimer = setTimeout(refreshMood, next - now + 20);
  }
  window.__mood = () => mood;
  // alive but calm: an occasional glance while idle, never anything pushy
  (function glance() {
    glanceTimer = setTimeout(() => {
      const s = logo.firstChild;
      if (s && mood === 'idle') { s.classList.add('glance'); setTimeout(() => s.classList.remove('glance'), 900); }
      refreshMood(); glance();
    }, 6000 + Math.random() * 9000);
  })();
  for (const evn of ['keydown', 'mousedown']) document.addEventListener(evn, () => { const was = Date.now() - lastActive > 5 * 60000; lastActive = Date.now(); if (was) refreshMood(); }, true);

  function paintGateway() {
    const g = $('#gw');
    g.classList.remove('ready', 'warming', 'down');
    const st = gw.state === 'ready' ? 'ready' : gw.state === 'warming' ? 'warming' : 'down';
    g.classList.add(st);
    g.querySelector('span').textContent = st === 'ready' ? 'Ready' : st === 'warming' ? 'Warming up…' : 'Offline';
    g.title = st === 'ready' ? 'Gateway reachable and warmed up' : st === 'warming' ? 'Warming up the model (typing still works)' : 'Gateway not reachable';
    refreshMood();
  }
  desk.onGateway((s) => { gw = s || gw; paintGateway(); });
  desk.onGlim((s) => { glim = s; refreshMood(); });

  // ---------- agent events ----------
  desk.onAgent((ev) => {
    if (!thread || ev.threadId !== thread.id) return;
    switch (ev.type) {
      case 'text': onText(ev.delta); break;
      case 'reasoning': onReasoning(ev.delta); break;
      case 'assistant_end': onAssistantEnd(ev); break;
      case 'step_start': onStepStart(ev); Mascot.bounce(logo); break;
      case 'step_end': onStepEnd(ev); break;
      case 'bcard': upsertBCard(ev); break;
      case 'scard': upsertSCard(ev); break;
      case 'login': { const c = lastBCard(); if (c) upsertBCard({ id: c.id, login: true }); break; }
      case 'resumed': { const c = lastBCard(); if (c) upsertBCard({ id: c.id, login: false }); break; }
      case 'approval': onApproval(ev); break;
      case 'ask': onAsk(ev); break;
      case 'resolved': { const r = rids.get(ev.rid); if (r) r.done(ev.value, ev.value === 'deny' ? 'Denied' : 'Allowed from the status pill', true); break; }
      case 'plan': setPlan(ev.items); break;
      case 'user': {
        if (ev.steer) {
          const i = pendingSteers.findIndex((p) => p.text === ev.text);
          if (i >= 0) { const p = pendingSteers.splice(i, 1)[0]; p.el.classList.remove('queued'); break; } // already shown when typed: confirm, do not add again
        }
        addUser(ev.text, ev.steer); break;
      }
      case 'notice': addNotice(ev.helper, ev.text); break;
      case 'queued': $('#runState span').textContent = 'Waiting for a free slot…'; break;
      case 'started': $('#runState span').textContent = 'Working…'; break;
      case 'compacted': break;
      case 'error': { ensureBlock().col.append(el('div', 'errline sel', ev.message)); toBottom(); errorUntil = Date.now() + 6000; break; }
      case 'done': {
        setRunning(false); tn = null; finishAll();
        pendingSteers.forEach((p) => p.el.classList.remove('queued')); pendingSteers = [];
        if (ev.stopped) msgs.append(el('div', 'status', 'Stopped.'));
        if (!ev.stopped && errorUntil < Date.now()) doneUntil = Date.now() + 4000;
        loadThreads(); toBottom(); break;
      }
    }
    refreshMood();
  });

  // ---------- threads ----------
  const GREETINGS = ['I had a feeling you’d stop by.', 'What should we get done?', 'Something tells me you have a task for me.', 'Ready when you are.', 'I sensed a to-do list coming.', 'Good to see you. What’s first?'];
  const SUGGESTIONS = ['Check my email', 'Plan my week', 'Find cheap flights to Boston next month', 'Every morning, brief me on the weather'];
  function welcome() {
    msgs.textContent = '';
    const w = el('div', 'welcome');
    w.append(Mascot.el(mood, 96, { cls: 'follow' }), el('h2', null, GREETINGS[Math.floor(Math.random() * GREETINGS.length)]), el('p', null, 'I can browse, search, run commands and drive Mac apps. I ask before anything risky.'));
    const chips = el('div', 'chips');
    for (const t of SUGGESTIONS) { const b = el('button', null, t); b.onclick = () => { input.value = t; input.focus(); autosize(); }; chips.append(b); }
    w.append(chips); msgs.append(w);
  }
  function resetView() { msgs.textContent = ''; stepEls.clear(); bcards.clear(); rids.clear(); pendingSteers = []; newBlock(); }
  function renderThread(t) {
    resetView();
    const items = t.items || [];
    if (!items.length) { welcome(); return; }
    items.forEach((it, i) => {
      if (it.t === 'user') addUser(it.text);
      else if (it.t === 'assistant') {
        const nextIsTool = items[i + 1] && items[i + 1].t === 'step';
        if (it.thinking) onReasoning(it.thinking);
        if (it.text) onText(it.text);
        if (tn) { tn.text && (tn.text.innerHTML = md(tn.raw)); }
        onAssistantEnd({ toolCalls: nextIsTool ? 1 : 0, thinkSecs: it.thinkSecs, ttftMs: it.ttftMs });
      } else if (it.t === 'step') {
        const a = ensureActTracked();
        const w = stepEl(it.id, it.tool, it.args, it.summary, it.ok ? 'ok' : 'bad', it.preview);
        a.body.append(w); stepEls.set(it.id, w); a.steps++; if (!it.ok) a.bad++;
      } else if (it.t === 'browser') upsertBCard({ id: it.id, key: it.key, url: it.url, title: it.title, favicon: it.favicon, thumb: it.thumb, active: false, login: false });
      else if (it.t === 'screen') upsertSCard({ id: it.id, thumb: it.thumb, text: it.text });
      else if (it.t === 'notice') addNotice(it.helper, it.text);
      else if (it.t === 'plan') setPlan(it.items);
    });
    tn = null;
    if (!t.running) finishAll();
    else if (act) { act.t0 = Date.now() - 1000; relabel(act); }
    if (t.running && act) { /* keep the live group running */ }
    stick = true; scroller.scrollTop = scroller.scrollHeight;
  }

  async function openThread(id) {
    const t = await desk.threads.load(id);
    if (!t) return;
    thread = { id: t.id, title: t.title, helper: t.helper || null };
    $('#title').textContent = t.title;
    renderThread(t);
    setRunning(!!t.running);
    if (t.loginWaiting) { const c = lastBCard(); if (c) upsertBCard({ id: c.id, login: true, active: true }); }
    for (const ev of t.pendingCards || []) { if (ev.type === 'approval') onApproval(ev); else if (ev.type === 'ask') onAsk(ev); }
    errorUntil = 0; doneUntil = 0; refreshMood();
    closeDrawer(); loadThreads();
    try { localStorage.setItem('lastThread', t.id); } catch (e) { /* ignore */ }
  }
  async function newThread() {
    const t = await desk.threads.create();
    thread = { id: t.id, title: t.title, helper: null };
    $('#title').textContent = t.title; renderThread(t); setRunning(false); closeDrawer(); loadThreads(); input.focus();
  }
  function ago(ts) {
    const m = Math.round((Date.now() - ts) / 60000);
    if (m < 1) return 'now'; if (m < 60) return m + 'm'; if (m < 1440) return Math.round(m / 60) + 'h'; return Math.round(m / 1440) + 'd';
  }
  async function renameCurrent(cur) { const n = prompt('Rename thread', cur); return n; }
  async function loadThreads() {
    const list = await desk.threads.list();
    const ul = $('#threadList'); ul.textContent = '';
    for (const t of list.filter((x) => !x.helper)) {
      const li = el('li', t.id === (thread && thread.id) ? 'on' : '');
      const title = el('span', 't', t.title); const d = el('span', 'd', ago(t.updated));
      const x = el('button', null, '✕'); x.title = 'Delete'; x.setAttribute('aria-label', 'Delete thread');
      x.onclick = async (e) => { e.stopPropagation(); if (confirm('Delete "' + t.title + '"?')) { await desk.threads.remove(t.id); if (thread && thread.id === t.id) { await newThread(); } else loadThreads(); } };
      title.ondblclick = async (e) => { e.stopPropagation(); const n = await renameCurrent(t.title); if (n) { await desk.threads.rename(t.id, n); if (thread && thread.id === t.id) $('#title').textContent = n; loadThreads(); } };
      li.append(title, d, x); li.onclick = () => openThread(t.id); ul.append(li);
    }
    if (thread) { const cur = list.find((t) => t.id === thread.id); if (cur) $('#title').textContent = cur.title; }
  }

  // ---------- agents (helpers) ----------
  const STATUS_TEXT = { idle: 'idle', queued: 'waiting for a slot', running: 'running', 'waiting-for-Ben': 'waiting for you', stopped: 'stopped' };
  const HELPER_MOOD = { idle: 'idle', queued: 'thinking', running: 'working', 'waiting-for-Ben': 'waiting', stopped: 'sleepy' };
  function when(ts) {
    if (!ts) return '';
    const d = new Date(ts), p = (n) => String(n).padStart(2, '0'), hm = p(d.getHours()) + ':' + p(d.getMinutes());
    return d.toDateString() === new Date().toDateString() ? hm : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()] + ' ' + hm;
  }
  function paintAgents(list) {
    const ul = $('#agentList'); ul.textContent = '';
    $('#agentsSec').hidden = !list.length;
    for (const h of list) {
      const li = el('li', thread && thread.id === h.threadId ? 'on' : '');
      const top = el('div', 'a-top');
      const dot = Mascot.el(HELPER_MOOD[h.status] || 'idle', 24, { still: h.status === 'idle' || h.status === 'stopped' });
      dot.title = STATUS_TEXT[h.status] || h.status;
      top.append(dot, el('span', 't', h.name), el('span', 'd', STATUS_TEXT[h.status] || h.status));
      const meta = el('div', 'a-meta dim small', h.schedule + (h.paused ? ' (paused)' : '') + (h.next ? ' · next ' + when(h.next) : ''));
      const btns = el('div', 'a-btns');
      const mk = (label, fn, cls) => { const b = el('button', cls || 'ghost sm', label); b.onclick = (e) => { e.stopPropagation(); fn(); }; return b; };
      btns.append(
        mk('Run now', () => desk.helpers.run(h.id)),
        mk(h.paused ? 'Resume' : 'Pause', () => desk.helpers.pause(h.id)),
        mk('Delete', async () => { if (confirm('Delete helper "' + h.name + '" and its thread?')) { await desk.helpers.remove(h.id); if (thread && thread.id === h.threadId) await newThread(); } }, 'ghost sm del'));
      li.append(top, meta); if (h.lastSummary) li.append(el('div', 'a-last dim small', h.lastSummary)); li.append(btns);
      li.onclick = () => openThread(h.threadId);
      ul.append(li);
    }
  }
  desk.onHelpers(paintAgents);
  desk.onOpenThread((id) => { $('#settings').hidden = true; openThread(id); });
  desk.onNewThread(() => newThread());
  desk.onFocusComposer(() => { $('#settings').hidden = true; input.focus(); });
  function openDrawer() { document.body.classList.add('drawer-open'); $('#drawer').setAttribute('aria-hidden', 'false'); loadThreads(); desk.helpers.list().then(paintAgents); }
  function closeDrawer() { document.body.classList.remove('drawer-open'); $('#drawer').setAttribute('aria-hidden', 'true'); }
  $('#btnThreads').onclick = () => document.body.classList.contains('drawer-open') ? closeDrawer() : openDrawer();
  $('#drawerShade').onclick = closeDrawer;
  $('#newThread').onclick = newThread;
  const renameTitle = async () => { if (!thread) return; const n = prompt('Rename thread', $('#title').textContent); if (n) { await desk.threads.rename(thread.id, n); $('#title').textContent = n; loadThreads(); } };
  $('#title').onclick = renameTitle;
  $('#title').addEventListener('keydown', (e) => { if (e.key === 'Enter') renameTitle(); });

  // links in answers open in the browser popup
  msgs.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-href]');
    if (!a) return;
    e.preventDefault();
    desk.browser.open('primary', a.getAttribute('data-href'), true);
  });

  // ---------- composer ----------
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 9.2 * parseFloat(getComputedStyle(document.documentElement).fontSize)) + 'px'; }
  input.addEventListener('input', () => { autosize(); if ($('#pwWarn').hidden === false && !Guard.looksLikeSecret(input.value)) $('#pwWarn').hidden = true; });
  let submitting = false;
  async function submit(force) {
    const text = input.value.trim();
    if (!text || submitting) return;
    if (!force && Guard.looksLikeSecret(text)) { $('#pwWarn').hidden = false; return; }
    $('#pwWarn').hidden = true;
    submitting = true;
    try {
      if (!thread) await newThread();
      input.value = ''; autosize();
      if (thread.helper && !running) { msgs.append(el('div', 'errline', 'This is a helper’s thread. Use Run now in the Agents list, or ask the primary agent.')); toBottom(); return; }
      if (running) {
        // shown at once (queued); the agent's 'user' event confirms it instead of adding it again
        const u = addUser(text, true, true); stick = true;
        pendingSteers.push({ text, el: u });
        const r = await desk.agent.send(thread.id, text);
        if (r && r.error) { u.classList.remove('queued'); msgs.append(el('div', 'errline', r.error)); }
        return;
      }
      addUser(text);
      stick = true;
      setRunning(true); // before the call: a fast run can finish before send() resolves
      const r = await desk.agent.send(thread.id, text);
      if (r && r.error) { setRunning(false); msgs.append(el('div', 'errline', r.error)); return; }
      if (r && r.title) { thread.title = r.title; $('#title').textContent = r.title; }
    } finally { submitting = false; }
  }
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(false); } });
  $('#btnSend').onclick = () => submit(false);
  $('#pwSend').onclick = () => submit(true);
  $('#pwCancel').onclick = () => { $('#pwWarn').hidden = true; input.focus(); };
  $('#btnStop').onclick = () => desk.agent.stop(thread && thread.id);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!$('#screenModal').hidden) $('#screenModal').hidden = true;
      else if (!$('#settings').hidden) closeSettings();
      else if (document.body.classList.contains('drawer-open')) closeDrawer();
      else if (running) desk.agent.stop(thread && thread.id);
    }
    if ((e.metaKey || e.ctrlKey) && e.key === ',') { e.preventDefault(); openSettings(); }
  });

  // ---------- top bar ----------
  function paintSegs() {
    document.querySelectorAll('#modelSeg button').forEach((b) => b.classList.toggle('on', b.dataset.model === settings.model));
    document.querySelectorAll('#modeSeg button').forEach((b) => b.classList.toggle('on', b.dataset.mode === settings.mode));
  }
  function applyAppearance() {
    const h = document.documentElement;
    h.classList.remove('ts-s', 'ts-m', 'ts-l'); h.classList.add('ts-' + (settings.textSize || 'm'));
    h.classList.toggle('hc', !!settings.highContrast);
  }
  async function save(patch) {
    const r = await desk.settings.set(patch);
    const { _hotkey, ...s } = r; settings = s; paintSegs(); applyAppearance();
    return r;
  }
  document.querySelectorAll('#modelSeg button').forEach((b) => b.onclick = () => { save({ model: b.dataset.model }); if ($('#settings').hidden === false) paintSettings(); });
  document.querySelectorAll('#modeSeg button').forEach((b) => b.onclick = () => { save({ mode: b.dataset.mode }); if ($('#settings').hidden === false) paintSettings(); });

  // ---------- settings ----------
  const isMac = () => document.body.classList.contains('darwin');
  const SCHEMA = [
    { group: 'Model', rows: [
      { key: 'gatewayUrl', type: 'text', label: 'Gateway URL', help: 'Where the Premonition gateway listens. /chat/completions is added for you.', wide: true },
      { key: 'model', type: 'seg', label: 'Default mode', help: 'Auto picks for you, Think reasons longer, Fast answers quickest. Same as the top-bar pills.', options: [['qwen36-auto', 'Auto'], ['qwen36', 'Think'], ['qwen36-fast', 'Fast']] },
      { type: 'test', label: 'Test connection', help: 'Checks that the gateway answers and how long it takes.' }
    ] },
    { group: 'Autonomy', rows: [
      { key: 'mode', type: 'seg', label: 'Main agent', help: 'Ask first: shell commands and Mac clicks/typing need your OK. Hands-off: only the danger list needs it.', options: [['ask', 'Ask first'], ['hands-off', 'Hands-off']] },
      { key: 'helperMode', type: 'seg', label: 'Helpers', help: 'The same choice for helper agents that run on a schedule.', options: [['ask', 'Ask first'], ['hands-off', 'Hands-off']] },
      { key: 'maxSteps', type: 'number', label: 'Max steps per task', help: 'Model calls before Glim stops and asks if you want it to continue (1 to 200).', min: 1, max: 200 },
      { type: 'danger', label: 'Always asks first (danger list)', help: 'Even in Hands-off, shell commands like these always need your OK. This list is fixed for safety.' }
    ] },
    { group: 'Helpers', rows: [
      { key: 'maxParallel', type: 'number', label: 'Runs at once', help: 'How many model runs go at the same time (you plus helpers). Extra runs wait their turn. 1 to 4.', min: 1, max: 4 }
    ] },
    { group: 'Memory', rows: [
      { key: 'diaryEnabled', type: 'toggle', label: 'Use my diary', help: 'Lets Glim search past chats and notes. Applies right away.' },
      { key: 'diaryPath', type: 'text', label: 'diary_mcp.py path', help: 'Leave empty for ~/learner-ops/assistant/diary_mcp.py.', ph: '~/learner-ops/assistant/diary_mcp.py', wide: true },
      { key: 'pythonPath', type: 'text', label: 'Python path', help: 'Leave empty to use the learner-ops virtualenv if present, else python3.', ph: 'python3', wide: true }
    ] },
    { group: 'Screen control', rows: [
      { key: 'helperPath', type: 'text', label: 'deskhelper path', help: 'The small program that clicks and types on your Mac. Empty uses the one bundled with the app.', ph: '(bundled with the app)', wide: true },
      { type: 'perm', label: 'Mac permissions', help: 'Screen control needs Accessibility and Screen Recording for this app.' }
    ] },
    { group: 'Vision', rows: [
      { key: 'vision', type: 'toggle', label: 'Send screenshots to the model', help: 'Only turn on if the model can see images. Off keeps everything text-only and fast.', on: 'on' }
    ] },
    { group: 'Appearance', rows: [
      { key: 'theme', type: 'seg', label: 'Theme', help: 'System follows your Mac.', options: [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']] },
      { key: 'textSize', type: 'seg', label: 'Text size', help: 'Small, medium or large text everywhere.', options: [['s', 'S'], ['m', 'M'], ['l', 'L']] },
      { key: 'highContrast', type: 'toggle', label: 'High contrast', help: 'Stronger text and borders everywhere.' },
      { key: 'pill', type: 'toggle', label: 'Status pill at the top of the screen', help: 'A small floating pill that shows what Glim is doing across apps. Hover it for details.' }
    ] },
    { group: 'Startup', rows: [
      { key: 'openAtLogin', type: 'toggle', label: 'Open at login', help: 'Starts quietly in the background when you log in, so Glim is already warmed up.' },
      { key: 'keepRunning', type: 'toggle', label: 'Keep running when the window is closed', help: 'Closing the window hides it; helpers keep going. Cmd+Q really quits.' },
      { key: 'hotkey', type: 'hotkey', label: 'Global shortcut', help: 'Show or hide Glim from any app. Click, then press the keys. Backspace turns it off.' }
    ] }
  ];
  const controls = {};
  function buildSettings() {
    const col = $('#settingsCol'); col.textContent = '';
    for (const g of SCHEMA) {
      const sec = el('section', 's-group'); sec.append(el('h2', null, g.group));
      const card = el('div', 's-card');
      for (const r of g.rows) {
        const row = el('div', 's-row' + (r.type === 'danger' ? ' stack' : ''));
        const lab = el('div', 's-lab'); lab.append(el('b', null, r.label), el('span', null, r.help));
        const ctl = el('div', 's-ctl');
        row.append(lab, ctl);
        if (r.type === 'text' || r.type === 'number') {
          const i = el('input'); i.type = r.type; if (r.ph) i.placeholder = r.ph; if (r.type === 'number') { i.min = r.min; i.max = r.max; } i.spellcheck = false; i.setAttribute('aria-label', r.label);
          let t = 0;
          i.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => save({ [r.key]: r.type === 'number' ? Number(i.value) : i.value }), 450); });
          i.addEventListener('change', () => { clearTimeout(t); save({ [r.key]: r.type === 'number' ? Number(i.value) : i.value }).then(paintSettings); });
          ctl.append(i); controls[r.key] = { paint: () => { if (document.activeElement !== i) i.value = settings[r.key] == null ? '' : settings[r.key]; } };
        } else if (r.type === 'seg') {
          const seg = el('div', 'seg'); seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', r.label);
          for (const [v, l] of r.options) { const b = el('button', null, l); b.dataset.v = v; b.onclick = () => { save({ [r.key]: v }).then(paintSettings); }; seg.append(b); }
          ctl.append(seg); controls[r.key] = { paint: () => seg.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.v === settings[r.key])) };
        } else if (r.type === 'toggle') {
          const b = el('button', 'toggle'); b.setAttribute('role', 'switch'); b.setAttribute('aria-label', r.label);
          b.onclick = () => { const cur = b.getAttribute('aria-checked') === 'true'; save({ [r.key]: r.on ? (cur ? 'off' : r.on) : !cur }).then(paintSettings); };
          ctl.append(b); controls[r.key] = { paint: () => b.setAttribute('aria-checked', String(r.on ? settings[r.key] === r.on : !!settings[r.key])) };
        } else if (r.type === 'test') {
          const note = el('span', 's-note'); const b = el('button', 'ghost', 'Test connection');
          b.onclick = async () => { note.className = 's-note'; note.textContent = 'Testing…'; const t = await desk.gateway.test(); note.className = 's-note ' + (t.ok ? 'ok' : 'bad'); note.textContent = t.ok ? 'Connected · ' + t.ms + ' ms' : 'Could not connect' + (t.error ? ' (' + t.error + ')' : ''); };
          b.id = 'testConn'; note.id = 'testNote'; ctl.append(note, b);
        } else if (r.type === 'danger') {
          const ul = el('ul', 'danger-list'); for (const d of info.danger || []) ul.append(el('li', null, d)); lab.append(ul);
        } else if (r.type === 'perm') {
          const out = el('div', 's-note dim'); out.id = 'permOut'; out.textContent = 'Not checked yet.';
          const show = (x) => { out.className = 's-note ' + (x.error ? 'bad' : x.accessibility && x.screenRecording ? 'ok' : ''); out.textContent = x.error ? x.error : 'Accessibility: ' + (x.accessibility ? 'granted' : 'not granted') + ' · Screen recording: ' + (x.screenRecording ? 'granted' : 'not granted'); };
          const mk = (t, fn) => { const b = el('button', 'ghost sm', t); b.onclick = fn; return b; };
          const bx = el('div'); bx.style.cssText = 'display:flex;flex-direction:column;gap:.4rem;align-items:flex-end';
          const rowb = el('div'); rowb.style.cssText = 'display:flex;gap:.4rem;flex-wrap:wrap;justify-content:flex-end';
          rowb.append(mk('Check permissions', async () => { out.textContent = 'Checking…'; show(await desk.screen.check()); }), mk('Ask macOS', async () => { out.textContent = 'Asking macOS…'; const a = await desk.screen.ask(); show(a.error ? a : await desk.screen.check()); }));
          const rowc = el('div'); rowc.style.cssText = rowb.style.cssText;
          rowc.append(mk('Open Accessibility settings', () => desk.openSystem('accessibility')), mk('Open Screen Recording settings', () => desk.openSystem('screen')));
          bx.append(rowb, rowc, out); ctl.append(bx);
        } else if (r.type === 'hotkey') {
          const b = el('button', 'ghost hotkey'); const note = el('span', 's-note'); b.id = 'hotkeyBtn';
          const show = (acc) => { b.textContent = acc ? (isMac() ? acc.replace(/\bAlt\b/g, 'Option').replace(/\bCommand\b/g, 'Cmd').replace(/\bControl\b/g, 'Ctrl') : acc) : 'Off'; };
          let rec = false;
          const stop = () => { rec = false; b.classList.remove('rec'); show(settings.hotkey); };
          b.onclick = () => { rec = true; b.classList.add('rec'); b.textContent = 'Press keys…'; note.textContent = ''; b.focus(); };
          b.addEventListener('blur', () => { if (rec) stop(); });
          b.addEventListener('keydown', async (e) => {
            if (!rec) return;
            e.preventDefault(); e.stopPropagation();
            if (e.key === 'Escape') return stop();
            if (e.key === 'Backspace' || e.key === 'Delete') { rec = false; b.classList.remove('rec'); await save({ hotkey: '' }); show(''); note.className = 's-note'; note.textContent = 'Shortcut off'; return; }
            if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;
            const mods = [e.metaKey && 'Command', e.ctrlKey && 'Control', e.altKey && 'Alt', e.shiftKey && 'Shift'].filter(Boolean);
            const c = e.code; let k = null;
            if (/^Key[A-Z]$/.test(c)) k = c.slice(3); else if (/^Digit\d$/.test(c)) k = c.slice(5); else if (/^F\d{1,2}$/.test(c)) k = c; else if (c === 'Space') k = 'Space'; else if (/^Arrow/.test(c)) k = c.slice(5); else if (c === 'Enter') k = 'Return'; else if (c === 'Tab') k = 'Tab';
            if (!k || (!mods.length && !/^F\d/.test(k))) { note.className = 's-note bad'; note.textContent = 'Use at least one modifier key (Option, Cmd, Ctrl).'; return; }
            const acc = mods.concat(k).join('+');
            rec = false; b.classList.remove('rec');
            const res = await save({ hotkey: acc }); show(settings.hotkey);
            const hk = res._hotkey;
            note.className = 's-note ' + (hk && hk.ok ? 'ok' : 'bad'); note.textContent = hk && !hk.ok ? hk.error : 'Saved';
          });
          ctl.append(note, b); controls[r.key] = { paint: () => { if (!rec) show(settings.hotkey); } };
        }
        card.append(row);
      }
      sec.append(card); col.append(sec);
    }
  }
  function paintSettings() { for (const c of Object.values(controls)) c.paint(); paintSegs(); }
  let settingsBuilt = false;
  function openSettings() {
    if (!settingsBuilt) { buildSettings(); settingsBuilt = true; }
    paintSettings(); $('#settings').hidden = false; $('#settingsClose').focus();
  }
  function closeSettings() { $('#settings').hidden = true; input.focus(); }
  $('#btnSettings').onclick = openSettings; $('#settingsClose').onclick = closeSettings;
  desk.onOpenSettings(openSettings);
  window.__openSettings = openSettings;

  // ---------- boot ----------
  (async () => {
    info = await desk.info();
    document.body.classList.add(info.platform);
    settings = await desk.settings.get(); paintSegs(); applyAppearance();
    gw = (await desk.gateway.state()) || gw; paintGateway();
    let last = null; try { last = localStorage.getItem('lastThread'); } catch (e) { /* ignore */ }
    const list = await desk.threads.list();
    if (!info.e2e && last && list.find((t) => t.id === last)) await openThread(last);
    else if (!info.e2e && list.length) await openThread(list[0].id);
    else await newThread();
    desk.helpers.list().then(paintAgents);
    window.__ready = true;
  })();
})();
