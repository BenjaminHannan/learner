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
    bookmark: '<path d="M4.5 2.5h7v11L8 10.8 4.5 13.5z"/>',
    book: '<path d="M3 2.5h8.5A1.5 1.5 0 0113 4v9.5H4.5A1.5 1.5 0 013 12z"/><path d="M3 12a1.5 1.5 0 011.5-1.5H13"/>',
    question: '<circle cx="8" cy="8" r="6"/><path d="M6.2 6.3A1.9 1.9 0 018 5a1.8 1.8 0 011 3.3c-.7.5-1 .8-1 1.5M8 11.6h.01"/>',
    person: '<circle cx="8" cy="5.5" r="2.5"/><path d="M3 13.5c.5-3 2.5-4 5-4s4.5 1 5 4"/>',
    x: '<path d="M4 4l8 8M12 4l-8 8"/>',
    check: '<path d="M3 8.5l3.2 3.2L13 4.8"/>',
    spin: '<path d="M8 2a6 6 0 106 6" />',
    dot: '<circle cx="8" cy="8" r="2"/>'
  };
  const TOOL_ICON = { web_search: 'search', browser_go: 'globe', browser_click: 'cursor', browser_type: 'keyboard', browser_scroll: 'scroll', browser_back: 'back', browser_read: 'doc', screen_look: 'monitor', screen_click: 'monitor', screen_type: 'monitor', screen_key: 'keyboard', open_app: 'app', run_shell: 'terminal', diary_search: 'book', verify: 'check', memory_save: 'bookmark', memory_forget: 'bookmark', track_add: 'bookmark', track_done: 'bookmark', ask_user: 'question', agent_start: 'person', agent_list: 'person', agent_stop: 'person' };
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
  // Scroll follow: pinned to the bottom while Ben is at/near it; if he scrolled up we leave him alone and offer a jump button.
  let stick = true, forceUntil = 0;
  const jumpBtn = $('#jump');
  const gap = () => scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
  scroller.addEventListener('scroll', () => {
    if (Date.now() < forceUntil) return; // a smooth jump to the bottom is in flight
    stick = gap() < 80;
    if (stick) jumpBtn.hidden = true;
  });
  const toBottom = () => { if (stick) { scroller.scrollTop = scroller.scrollHeight; jumpBtn.hidden = true; } else if (running) jumpBtn.hidden = false; };
  // Ben sent something (or asked to jump): go to the newest message now (smooth, instant if far away)
  function jumpBottom() {
    stick = true; jumpBtn.hidden = true;
    const far = gap() > 1500;
    forceUntil = Date.now() + (far ? 0 : 600);
    if (far) scroller.scrollTop = scroller.scrollHeight;
    else scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' });
  }
  jumpBtn.onclick = jumpBottom;
  // content grew (streaming, cards, images): keep following if pinned; otherwise just flag it
  if (window.ResizeObserver) {
    new ResizeObserver(() => { if (stick) { if (Date.now() >= forceUntil) scroller.scrollTop = scroller.scrollHeight; } else if (running) jumpBtn.hidden = false; }).observe(msgs);
    new ResizeObserver(() => document.documentElement.style.setProperty('--composer-h', $('#composer').offsetHeight + 'px')).observe($('#composer'));
  }
  // opening/closing a block by hand must not drag the view to the bottom
  msgs.addEventListener('click', (e) => { if (e.target.closest('.act-head, .step .pill, details > summary')) { stick = false; forceUntil = 0; } }, true);
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
  // one fold state for every tool-use group (all threads, also later ones): body[data-acts] + one CSS rule, remembered across launches
  function setActsCollapsed(collapsed) {
    document.body.dataset.acts = Acts.attr(collapsed);
    document.querySelectorAll('.act-head').forEach((h) => h.setAttribute('aria-expanded', String(!collapsed)));
    try { localStorage.setItem(Acts.KEY, collapsed ? '1' : '0'); } catch (e) { /* ignore */ }
  }
  { let st = null; try { st = localStorage.getItem(Acts.KEY); } catch (e) { /* ignore */ } document.body.dataset.acts = Acts.attr(Acts.parse(st)); }
  function ensureAct(before) {
    if (act && !act.finished) return act;
    const b = ensureBlock();
    const root = el('div', 'activity running');
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
    const a = { root, head, ico, title, sub, live, liveT: live.lastChild, cards, body, steps: 0, bad: 0, t0: Date.now(), finished: false, lastNar: '', plan: null };
    head.setAttribute('aria-expanded', String(!Acts.isCollapsed(document.body.dataset.acts)));
    head.onclick = () => setActsCollapsed(!Acts.isCollapsed(document.body.dataset.acts));
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
      const wasStuck = stick;
      if (act && !act.finished) finishAct(act);
      if (wasStuck) { stick = true; scroller.scrollTop = scroller.scrollHeight; }
      toBottom();
      return;
    }
    // narration before tool calls: fold it into the activity group, one clamped line each, no repeats
    const a = ensureActTracked(t.think ? t.think.d : t.text);
    if (t.think) { a.body.append(t.think.d); }
    if (t.text) {
      const norm = clean.toLowerCase().replace(/\W+/g, ' ');
      // the plan has its own checklist; same rule as extractPlan in src/agent.js (2+ numbered lines, each short)
      const nums = clean.split('\n').filter((l) => /^\s*\d+[.)]\s+\S/.test(l)).map((l) => l.replace(/^\s*\d+[.)]\s+/, '').replace(/\*\*|__|`/g, '').trim());
      const isPlan = nums.length >= 2 && nums.every((l) => l.length <= 120);
      if (clean && !isPlan && norm !== a.lastNar) { a.lastNar = norm; { const one = clean.replace(/\s+/g, ' '); const n = el('div', 'nar sel', one); n.title = one; a.body.append(n); }; }
      t.text.remove();
    }
    toBottom();
  }

  // "Login access - You mentioned ... I need ..." reads as a wall of text: show the short head in bold and the rest as a
  // muted two-line note (full text on hover). Old saved threads still carry ** marks, so strip them here too.
  function planItem(text) {
    const t = String(text).replace(/\*\*|__|`/g, '').trim();
    const li = el('li'); const box = el('span', 'pt'); box.title = t;
    const m = /^(.{2,40}?)(?:\s+[-–—]\s+|:\s+)(.+)$/.exec(t);
    if (m) box.append(el('b', 'ph', m[1]), el('span', 'pd', m[2])); else box.append(el('span', 'pd solo', t));
    li.append(box); return li;
  }

  function setPlan(items) {
    if (!items || !items.length) return;
    const a = ensureActTracked();
    if (a.plan) a.plan.remove();
    const d = el('details', 'plan'); d.open = true;
    const s = el('summary'); s.append(document.createTextNode('Plan · ' + items.length + ' steps'));
    const ol = el('ol');
    for (const i of items) ol.append(planItem(i));
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
      root.onclick = () => desk.browser.open(c.key, c.urlFull, false, thread && thread.id);
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
    c.root.title = c.login ? 'Open the browser to sign in' : 'Open this page in the browser panel';
    syncBrowserKeys();
    toBottom();
    return c;
  }
  function syncBrowserKeys() {
    BrowserPanel.setKeys([...bcards.values()].filter((c) => c.urlFull !== undefined || c.key).map((c) => ({ key: c.key, url: c.urlFull })));
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
    const reply = (text, remote) => { if (!text || c.classList.contains('done')) return; if (!remote) desk.agent.respond(ev.id, text); c.classList.add('done'); ta.remove(); btns.remove(); c.append(el('div', 'dim small', 'You: ' + text)); refreshMood(); };
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
    paintSend(r); $('#btnStop').hidden = !r; $('#runState').hidden = !r;
    $('#runState span').textContent = 'Working…';
    paintGateway();
    input.placeholder = r ? 'Add a note to steer the current task…' : thread && thread.helper ? 'This is a Glim’s thread. Type here to steer it while it runs.' : 'Ask Glim to do something…';
    $('#hint').textContent = r ? 'Enter sends a steer note · Esc stops' : 'Enter to send · Shift+Enter for a new line';
  }

  // ---------- Glim's mood: one status source (main) + local run state ----------
  let slp = { asleep: false, waking: false, available: true };
  let mood = 'idle', gw = { state: 'down' }, glim = 'idle', errorUntil = 0, doneUntil = 0, moodTimer = 0, lastActive = Date.now(), glanceTimer = 0;
  const logo = Mascot.el('idle', 28, { cls: 'follow' });
  $('#logo').append(logo);
  function refreshMood() {
    const now = Date.now();
    let m = 'idle';
    if (slp.waking) m = 'thinking';
    else if (slp.asleep) m = 'sleepy';
    else if (gw.state === 'down' || gw.state === 'warming') m = 'sleepy';
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
    g.classList.add(st); g.classList.toggle('asleep', !!(slp.asleep || slp.waking));
    // one source of truth with the composer: while a run is on, both say what the run says
    const busy = running && st !== 'down';
    g.classList.toggle('busy', busy);
    g.querySelector('span').textContent = slp.waking ? 'Waking up…' : slp.asleep ? 'Asleep' : busy ? $('#runState span').textContent : st === 'ready' ? 'Ready' : st === 'warming' ? 'Warming up…' : (gwStarting && Date.now() - gwStarting < 120000) ? 'Starting…' : 'Offline';
    g.title = st === 'ready' ? 'Gateway reachable and warmed up' : st === 'warming' ? 'Warming up the model (typing still works)' : 'Model is off. Click to start it';
    g.classList.toggle('startable', st === 'down' && !slp.asleep && !slp.waking);
    refreshMood();
  }
  desk.onGateway((s) => { gw = s || gw; if (gw.state !== 'down') gwStarting = 0; paintGateway(); });
  // Offline chip: click to start the model (Settings > Model > Start command; the built-in model on Windows)
  let gwStarting = 0;
  $('#gw').addEventListener('click', async () => {
    if (gw.state !== 'down' || slp.asleep || slp.waking || (gwStarting && Date.now() - gwStarting < 120000)) return;
    gwStarting = Date.now(); paintGateway();
    const r = await desk.gateway.start();
    if (r && r.error) { gwStarting = 0; paintGateway(); $('#gw').title = r.error; addNotice('Model', r.error); }
  });
  desk.onFullscreen((on) => document.body.classList.toggle('fullscreen', !!on));
  desk.onGlim((s) => { glim = s; refreshMood(); });

  // ---------- sleep ----------
  let awakeWaiters = [];
  function paintSleep() {
    const asleep = slp.asleep || slp.waking;
    $('#composer').classList.toggle('asleep', asleep);
    $('#sleepBar').hidden = !asleep;
    $('#btnWake').textContent = slp.waking ? 'Waking up…' : 'Wake Glim'; $('#btnWake').disabled = !!slp.waking;
    $('#sleepTitle').textContent = slp.waking ? 'Waking up…' : 'Glim is asleep';
    $('#sleepSub').textContent = slp.waking ? 'Waiting for the model to come back.' : ['Learning from your chats', slp.wakeLabel || '', slp.checkingIn ? 'checking in' : '', slp.hours ? Math.round(slp.hours * 10) / 10 + ' h so far' : '', slp.demo ? 'demo run' : slp.lastQuiz != null ? 'quiz ' + Math.round(slp.lastQuiz * 10) / 10 : ''].filter(Boolean).join(' · ');
    $('#btnSend').hidden = asleep; $('#hint').hidden = asleep;
    if (!asleep) { $('#wakeAsk').hidden = true; setRunning(running); }
    else { input.placeholder = 'Glim is asleep. Type here and I will offer to wake it.'; $('#runState').hidden = true; }
    const b = $('#btnSleep'); b.disabled = !slp.available || asleep;
    b.title = !slp.available ? (slp.reason || 'The sleep app was not found.') : 'Sleep: let Glim learn from your chats while you are away';
    paintGateway();
  }
  function onSleepState(v) {
    const was = slp.asleep || slp.waking; slp = v || slp; paintSleep();
    if (was && !slp.asleep && !slp.waking) { const w = awakeWaiters; awakeWaiters = []; w.forEach((f) => f()); }
    if ($('#settings').hidden === false) paintSleepSettings();
  }
  desk.onSleep(onSleepState);
  desk.sleep.state().then(onSleepState);
  desk.onSleepNotice((n) => addNotice('Sleep', n.text));
  desk.onSleepWoke((w) => {
    if (w.summary) {
      const c = el('div', 'wslept sel');
      const h = el('div', 'ws-head'); h.innerHTML = svg('<path d="M13.2 9.6A5.6 5.6 0 016.4 2.8a5.6 5.6 0 106.8 6.8z"/>'); h.append(el('b', null, 'While you slept'));
      if (w.demo) h.append(el('span', 'ws-tag', 'demo run'));
      const body = el('div', 'ws-body atext'); body.innerHTML = md(w.summary.replace(/^#{1,3} +While you slept\s*\n+/i, ''));
      c.append(h, body); msgs.append(c); newBlock(); toBottom();
    } else addNotice('Sleep', 'Glim is awake. There was no summary this time.');
    input.focus();
  });
  $('#btnWake').onclick = () => desk.sleep.wake();
  $('#wakeAskNo').onclick = () => { $('#wakeAsk').hidden = true; input.focus(); };
  $('#wakeAskYes').onclick = async () => {
    const text = input.value; $('#wakeAsk').hidden = true;
    await desk.sleep.wake();
    await new Promise((r) => { if (!slp.asleep && !slp.waking) r(); else awakeWaiters.push(r); });
    input.value = text; autosize(); submit(false);
  };
  let sleepPick = 'morning';
  const paintDur = () => {
    for (const b of document.querySelectorAll('#sleepDur button')) { const on = b.dataset.d === sleepPick; b.setAttribute('aria-checked', on ? 'true' : 'false'); b.classList.toggle('on', on); }
    $('#sleepDurNote').textContent = sleepPick === 'morning' ? 'Until ' + (slp.nightTo || settings.sleepTo || '08:00') + '. Longer sleep learns more.' : sleepPick === 'open' ? 'It keeps going until you press Wake (it plans for about 8 hours). Longer sleep learns more.' : 'Longer sleep learns more.';
  };
  for (const b of document.querySelectorAll('#sleepDur button')) b.onclick = () => { sleepPick = b.dataset.d; paintDur(); };
  function openSleepSheet() {
    if (!slp.available || slp.asleep || slp.waking) return;
    sleepPick = ['30', '60', '120', '240', 'morning', 'open'].includes(String(settings.sleepDuration)) ? String(settings.sleepDuration) : 'morning'; paintDur();
    $('#sleepPause').checked = settings.sleepPauseGlims !== false; $('#sleepErr').hidden = true;
    $('#sleepSheet').hidden = false; $('#sleepGo').focus();
  }
  const closeSleepSheet = () => { $('#sleepSheet').hidden = true; input.focus(); };
  $('#btnSleep').onclick = openSleepSheet; desk.onSleepOpen(openSleepSheet);
  $('#sleepCancel').onclick = closeSleepSheet;
  $('#sleepGo').onclick = async () => {
    const r = await desk.sleep.start({ pauseGlims: $('#sleepPause').checked, minutes: sleepPick === 'morning' ? 'morning' : sleepPick === 'open' ? null : Number(sleepPick) });
    if (r && r.error) { $('#sleepErr').textContent = r.error; $('#sleepErr').hidden = false; return; }
    settings = { ...settings, sleepPauseGlims: $('#sleepPause').checked, sleepDuration: sleepPick }; closeSleepSheet();
  };
  $('#sleepSheet').addEventListener('mousedown', (e) => { if (e.target === $('#sleepSheet')) closeSleepSheet(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#sleepSheet').hidden) { e.stopPropagation(); closeSleepSheet(); } }, true);

  // ---------- built-in local model (Windows): first-run download screen ----------
  const mb = (n) => (n / 1048576 >= 1024 ? (n / 1073741824).toFixed(2) + ' GB' : Math.round(n / 1048576) + ' MB');
  let rtHidden = false;
  function paintRuntime(st) {
    const box = $('#runtime');
    if (!st) { box.hidden = true; return; }
    const busy = st.phase === 'downloading' || (st.phase === 'starting' && st.label !== 'Restarting the model');
    const show = (busy || st.phase === 'error') && !rtHidden;
    box.hidden = !show;
    if (!show) { if (st.phase === 'ready') rtHidden = false; return; }
    $('#rtBar').style.width = (st.phase === 'starting' ? 100 : st.pct || 0) + '%';
    $('#rtTitle').textContent = st.phase === 'error' ? 'The local model did not start' : 'Setting up Premonition';
    $('#rtStatus').textContent = st.phase === 'error' ? st.error : (st.label || '') + (st.total ? ' · ' + mb(st.done) + ' of ' + mb(st.total) + ' (' + (st.pct || 0) + '%)' : '');
    $('#rtRetry').hidden = st.phase !== 'error';
  }
  $('#rtRetry').onclick = () => { rtHidden = false; desk.runtime.retry(); };
  $('#rtHide').onclick = () => { rtHidden = true; $('#runtime').hidden = true; };
  desk.runtime.onState(paintRuntime);
  desk.runtime.state().then(paintRuntime);

  // Windows sleep: the first time, explain and download the sleep runtime (Python + torch + weights), then sleep
  desk.sleepInstall.onNeeded((plan) => { closeSleepSheet(); $('#ssText').textContent = plan.text; $('#ssBarWrap').hidden = true; $('#ssStatus').textContent = ''; $('#ssGo').disabled = false; $('#sleepSetup').hidden = false; $('#ssGo').focus(); });
  desk.sleepInstall.onProgress((p) => { if (p.stage === 'error') { $('#ssStatus').textContent = p.label; $('#ssGo').disabled = false; return; } $('#ssBarWrap').hidden = false; $('#ssBar').style.width = (p.pct || 0) + '%'; $('#ssStatus').textContent = p.label + (p.pct ? ' (' + p.pct + '%)' : '…'); });
  $('#ssCancel').onclick = () => { $('#sleepSetup').hidden = true; };
  $('#ssGo').onclick = async () => {
    $('#ssGo').disabled = true; $('#ssStatus').textContent = 'Starting…';
    const r = await desk.sleepInstall.run();
    if (r && r.error) { $('#ssStatus').textContent = r.error; $('#ssGo').disabled = false; return; }
    $('#sleepSetup').hidden = true;
  };

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
      case 'queued': $('#runState span').textContent = 'Waiting for a free slot…'; paintGateway(); break;
      case 'started': $('#runState span').textContent = 'Working…'; paintGateway(); break;
      case 'compacted': break;
      case 'error': { ensureBlock().col.append(el('div', 'errline sel', ev.message)); toBottom(); errorUntil = Date.now() + 6000; break; }
      case 'done': {
        setRunning(false); tn = null; finishAll();
        pendingSteers.forEach((p) => p.el.classList.remove('queued')); pendingSteers = [];
        if (ev.stopped) msgs.append(el('div', 'status', 'Stopped.'));
        if (!ev.stopped && errorUntil < Date.now()) doneUntil = Date.now() + 4000;
        loadThreads(); toBottom(); if (!$('#settings').hidden) { memRefresh(); trackRefresh(); } break;
      }
    }
    refreshMood();
  });

  // ---------- threads ----------
  const GREETINGS = ['I had a feeling you’d stop by.', 'What should we get done?', 'Something tells me you have a task for me.', 'Ready when you are.', 'I sensed a to-do list coming.', 'Good to see you. What’s first?'];
  function welcome() {
    msgs.textContent = '';
    const w = el('div', 'welcome');
    w.append(Mascot.el(mood, 96, { cls: 'follow' }), el('h2', null, GREETINGS[Math.floor(Math.random() * GREETINGS.length)]), el('p', null, 'I can browse, search, run commands and drive ' + Platform.osWords(info.platform).apps + ' apps. I ask before anything risky.'));
    const chips = el('div', 'chips');
    for (const t of Uses.chipsFor(settings.uses)) { const b = el('button', null, t); b.onclick = () => { input.value = t; input.focus(); autosize(); }; chips.append(b); }
    w.append(chips); msgs.append(w);
  }
  function resetView() { msgs.textContent = ''; stepEls.clear(); bcards.clear(); BrowserPanel.setKeys([]); rids.clear(); pendingSteers = []; newBlock(); }
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
    stick = true; forceUntil = 0; jumpBtn.hidden = true; scroller.scrollTop = scroller.scrollHeight;
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
    BrowserPanel.threadChanged();
    try { localStorage.setItem('lastThread', t.id); } catch (e) { /* ignore */ }
  }
  async function newThread() {
    const t = await desk.threads.create();
    try { settings = await desk.settings.get(); paintSegs(); } catch (e) { /* keep the current pills */ } // a new thread starts on the default pill
    thread = { id: t.id, title: t.title, helper: null };
    $('#title').textContent = t.title; renderThread(t); setRunning(false); closeDrawer(); loadThreads(); BrowserPanel.threadChanged(); input.focus();
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
        mk('Delete', async () => { if (confirm('Delete Glim "' + h.name + '" and its thread?')) { await desk.helpers.remove(h.id); if (thread && thread.id === h.threadId) await newThread(); } }, 'ghost sm del'));
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

  // links in answers open in the browser panel
  msgs.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-href]');
    if (!a) return;
    e.preventDefault();
    desk.browser.open(thread.id, a.getAttribute('data-href'), true, thread.id);
  });

  // ---------- composer ----------
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 9.2 * parseFloat(getComputedStyle(document.documentElement).fontSize)) + 'px'; }
  input.addEventListener('input', autosize);
  let submitting = false;
  async function submit(force) {
    const text = input.value.trim();
    if (!text || submitting) return;
    if (slp.asleep || slp.waking) { $('#wakeAsk').hidden = false; return; } // keep the text; offer to wake first
    submitting = true;
    try {
      if (!thread) await newThread();
      input.value = ''; autosize();
      if (thread.helper && !running) { msgs.append(el('div', 'errline', 'This is a Glim’s thread. Use Run now in the Glims list, or ask your main Glim.')); toBottom(); return; }
      if (running) {
        // shown at once (queued); the agent's 'user' event confirms it instead of adding it again
        const u = addUser(text, true, true); jumpBottom();
        pendingSteers.push({ text, el: u });
        const r = await desk.agent.send(thread.id, text);
        if (r && r.error) { u.classList.remove('queued'); msgs.append(el('div', 'errline', r.error)); }
        return;
      }
      addUser(text);
      jumpBottom();
      setRunning(true); // before the call: a fast run can finish before send() resolves
      const r = await desk.agent.send(thread.id, text);
      if (r && r.error) { setRunning(false); msgs.append(el('div', 'errline', r.error)); return; }
      if (r && r.title) { thread.title = r.title; $('#title').textContent = r.title; }
    } finally { submitting = false; }
  }
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(false); } });
  $('#btnSend').onclick = () => submit(false);
  $('#btnStop').onclick = () => desk.agent.stop(thread && thread.id);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!$('#screenModal').hidden) $('#screenModal').hidden = true;
      else if (!$('#settings').hidden) closeSettings();
      else if (document.body.classList.contains('drawer-open')) closeDrawer();
      else if (running) desk.agent.stop(thread && thread.id);
    }
    if ((e.metaKey || e.ctrlKey) && e.key === ',') { e.preventDefault(); if (!Onboard.isOpen()) openSettings(); }
  });

  // ---------- top bar ----------
  // round icon buttons: arrow up = send, a turning arrow = steer; the words stay for screen readers and tooltips
  const SEND_ICO = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5"/></svg>';
  const STEER_ICO = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 13V8.5A2.5 2.5 0 015.5 6H13M10 3l3 3-3 3"/></svg>';
  function paintSend(running) {
    const b = $('#btnSend'), word = running ? 'Steer' : 'Send';
    b.innerHTML = (running ? STEER_ICO : SEND_ICO) + '<span class="sr">' + word + '</span>';
    b.title = running ? 'Steer: send a note to the running Glim (Enter)' : 'Send (Enter)';
  }
  function paintSegs() {
    document.querySelectorAll('#modelSeg button').forEach((b) => { if (b.dataset.slot && settings[b.dataset.slot]) b.dataset.model = settings[b.dataset.slot]; b.classList.toggle('on', b.dataset.model === settings.model); });
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
  // the mode is shown here but changed only in Settings (and at onboarding)

  // ---------- settings ----------
  const isMac = () => document.body.classList.contains('darwin');
  const plat = () => (info && info.platform) || (isMac() ? 'darwin' : 'linux');
  const gate = () => Platform.settingsGating(plat());
  const SCHEMA = [
    { group: 'Model', rows: [
      { key: 'gatewayUrl', type: 'text', label: 'Gateway URL', help: 'Where the Premonition gateway listens. /chat/completions is added for you.', wide: true },
      { key: 'modelStartCmd', type: 'text', label: 'Start command', help: 'Runs when you click Offline in the top bar. Empty = the assistant\'s serve.sh on this Mac, or the built-in model on Windows.', wide: true },
      { type: 'preset', label: 'Model server', help: 'One tap fills in the address and model names below. Built-in (LFM3) is the model Premonition runs itself on Windows. llama.cpp server is a plain llama-server on this PC (it ignores the model name).' },
      { key: 'model', type: 'modelseg', label: 'Default mode', help: 'Auto picks for you, Think reasons longer, Fast answers quickest. Same as the top-bar pills.', options: [['modelAuto', 'Auto'], ['modelMain', 'Think'], ['modelFast', 'Fast']] },
      { key: 'modelAuto', type: 'text', label: 'Auto model name', help: 'The model id sent for Auto. "default" works for llama.cpp.', ph: 'qwen36-auto' },
      { key: 'modelMain', type: 'text', label: 'Think model name', help: 'The model id sent for Think.', ph: 'qwen36' },
      { key: 'modelFast', type: 'text', label: 'Fast model name', help: 'The model id sent for Fast. Also used for the warm-up and the double-check.', ph: 'qwen36-fast' },
      { type: 'test', label: 'Test connection', help: 'Checks that the gateway answers and how long it takes.' }
    ] },
    { group: 'Autonomy', rows: [
      { key: 'mode', type: 'seg', label: 'Main Glim', help: 'Ask first: shell commands and screen clicks/typing need your OK. Hands-off: only the danger list needs it.', options: [['ask', 'Ask first'], ['hands-off', 'Hands-off']] },
      { key: 'helperMode', type: 'seg', label: 'Glims on a schedule', help: 'The same choice for the extra Glims that run on their own.', options: [['ask', 'Ask first'], ['hands-off', 'Hands-off']] },
      { key: 'maxSteps', type: 'number', label: 'Max steps per task', help: 'Model calls before Glim stops and asks if you want it to continue (1 to 200).', min: 1, max: 200 },
      { key: 'verify', type: 'toggle', label: 'Double-check my work before saying done (a little slower)', help: 'After Glim changes something, a quick second look checks the result matches what you asked. Off skips it.' },
      { type: 'danger', label: 'Always asks first (danger list)', help: 'Even in Hands-off, shell commands like these always need your OK. This list is fixed for safety.' }
    ] },
    { group: 'Glims', rows: [
      { key: 'maxParallel', type: 'number', label: 'Runs at once', help: 'How many model runs go at the same time (your main Glim plus the others). Extra runs wait their turn. 1 to 4.', min: 1, max: 4 }
    ] },
    { group: 'Setup', rows: [
      { type: 'setup', label: 'Run setup again', help: 'Meet your Glims again: pick what you want them for, create recurring Glims and check permissions.' }
    ] },
    { group: 'Diary', rows: [
      { key: 'diaryEnabled', type: 'toggle', label: 'Use my diary', help: 'Lets Glim search past chats and notes. Applies right away.' },
      { key: 'diaryPath', type: 'text', label: 'diary_mcp.py path', help: 'Leave empty for ~/learner-ops/assistant/diary_mcp.py.', ph: '~/learner-ops/assistant/diary_mcp.py', wide: true },
      { key: 'pythonPath', type: 'text', label: 'Python path', help: 'Leave empty to use the learner-ops virtualenv if present, else python3.', ph: 'python3', wide: true }
    ] },
    { group: 'Memory', rows: [
      { type: 'memory', label: 'What Glim remembers', help: 'Glim remembers these between chats. It adds to this list itself when it learns something lasting, like your classes.' }
    ] },
    { group: 'Keeping track of', rows: [
      { type: 'tracking', label: 'Things Glim is watching', help: 'Orders, bookings, applications and deadlines Glim keeps an eye on for you. It adds to this list itself when you mention one, and flags what is due while you sleep.' }
    ] },
    { group: 'Sleep', rows: [
      { type: 'sleepstat', label: 'Sleep mode', help: 'Glim learns from your chats while you are away and checks your mail and calendar once an hour (read-only). It only sleeps while Glim is idle, because your chats come first.' },
      { key: 'sleepApp', type: 'text', label: 'Sleep app folder', help: 'Leave empty for ~/learner-ops/sleepmode/app.', ph: '~/learner-ops/sleepmode/app', wide: true },
      { key: 'sleepPython', type: 'text', label: 'Sleep Python', help: 'Leave empty to pick the first python found: sleepmode/venv312, learner-ops/.venv, Homebrew, then python3.', ph: 'python3', wide: true },
      { key: 'sleepPauseGlims', type: 'toggle', label: 'Hourly check-in while asleep', help: 'Once an hour Glim wakes with its old model, runs any Glims that are due and checks your mail and calendar. Otherwise the Glims wait and catch up after you wake it.' },
      { key: 'sleepCheckinMins', type: 'number', label: 'Minutes between check-ins', help: 'Windows. A check-in happens at the next training break after this (10 to 720).', min: 10, max: 720 },
      { key: 'awakeCheckinMins', type: 'number', label: 'Minutes between awake check-ins', help: 'While Glim is awake and you are away from the chat, a quick read-only look at mail, calendar, things Glim is tracking and the model server. It speaks up only if something needs you. 0 turns it off (0 to 720).', min: 0, max: 720 },
      { key: 'sleepCheckinTask', type: 'text', label: 'Check-in task', help: 'What Glim does at each check-in. Reply NOTHING means nothing needs you.', wide: true },
      { key: 'autoSleep', type: 'toggle', label: 'Sleep when idle at night', help: 'Only when no run is active, the gateway is idle and the Glim window is not in front.' },
      { type: 'window', label: 'Night window', help: 'Auto-sleep only starts between these times. This is the window in effect when Fit sleep to my routine is off, and until it has learned yours.' },
      { key: 'sleepAdapt', type: 'toggle', label: 'Fit sleep to my routine', help: 'Learns when you usually stop in the evening and start in the morning (from the last 3 weeks, once it has 5 days) and sleeps in that gap instead of the night window. It still waits for the idle time below. Off: the night window you set is used as it is.' },
      { key: 'sleepOnlyPlugged', type: 'toggle', label: 'Only sleep when plugged in', help: 'Sleep is slow and uses a lot of power on a laptop. Keep it plugged in overnight.' },
      { key: 'sleepIdleMin', type: 'number', label: 'Idle minutes before auto-sleep', help: 'How long you have to be away first, 120 minutes (2 hours) unless you change it (1 to 720).', min: 1, max: 720 },
      { key: 'wakeAt', type: 'toggle', label: 'Wake at the end of the window', help: 'Only for a sleep that Glim started by itself.' }
    ] },
    { group: 'Screen control', rows: [
      { key: 'helperPath', type: 'text', label: 'deskhelper path', help: 'The small program that clicks and types on your computer. Empty uses the one bundled with the app.', ph: '(bundled with the app)', wide: true },
      { type: 'perm', label: 'Mac permissions', help: 'Screen control needs Accessibility and Screen Recording for this app.' }
    ] },
    { group: 'Vision', rows: [
      { key: 'vision', type: 'toggle', label: 'Send screenshots to the model', help: 'Only turn on if the model can see images. Off keeps everything text-only and fast.', on: 'on' }
    ] },
    { group: 'Appearance', rows: [
      { key: 'theme', type: 'seg', label: 'Theme', help: 'System follows your computer.', options: [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']] },
      { key: 'textSize', type: 'seg', label: 'Text size', help: 'Small, medium or large text everywhere.', options: [['s', 'S'], ['m', 'M'], ['l', 'L']] },
      { key: 'highContrast', type: 'toggle', label: 'High contrast', help: 'Stronger text and borders everywhere.' },
      { key: 'pill', type: 'toggle', label: 'Status pill at the top of the screen', help: 'A small floating pill that shows what Glim is doing across apps. Hover it for details.' }
    ] },
    { group: 'Startup', rows: [
      { key: 'openAtLogin', type: 'toggle', label: 'Open at login', help: 'Starts quietly in the background when you log in, so Glim is already warmed up.' },
      { key: 'keepRunning', type: 'toggle', label: 'Keep running when the window is closed', help: () => 'Closing the window hides it; your Glims keep going. Quit for real with ' + Platform.quitHint(plat()) + '.' },
      { key: 'hotkey', type: 'hotkey', label: 'Global shortcut', help: 'Show or hide Glim from any app. Click, then press the keys. Backspace turns it off.' }
    ] }
  ];
  const controls = {};
  // Memory: facts Glim keeps between chats (src/memory.js). Rows save on blur or Enter; refusals show inline.
  let memRefresh = () => {};
  function memUi() {
    const box = el('div', 'mem'), list = el('div', 'mem-list'), note = el('div', 's-note mem-note');
    note.id = 'memNote'; list.id = 'memList'; note.setAttribute('role', 'status');
    const say = (msg, bad) => { note.className = 's-note mem-note ' + (bad ? 'bad' : 'ok'); note.textContent = msg || ''; };
    const rowFor = (f) => {
      const r = el('div', 'mem-row'); r.dataset.id = f.id;
      const chip = el('span', 'mem-chip' + (f.topic ? '' : ' none'), f.topic || 'general');
      const t = el('input', 'mem-text'); t.type = 'text'; t.value = f.text; t.spellcheck = false; t.maxLength = 300; t.setAttribute('aria-label', 'Remembered fact');
      let saved = f.text, busy = false; t.dataset.saved = saved;
      const commit = async () => {
        const v = t.value.trim();
        if (v === saved || busy) return;
        busy = true;
        const res = await desk.memory.edit(f.id, { text: v }).finally(() => { busy = false; });
        if (res && res.ok) { saved = res.fact.text; t.value = saved; t.dataset.saved = saved; say('Saved.'); }
        else { say((res && res.error) || 'Could not save.', true); t.value = saved; t.classList.add('bad'); setTimeout(() => t.classList.remove('bad'), 1600); }
      };
      t.addEventListener('blur', commit);
      t.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); commit(); t.blur(); } else if (e.key === 'Escape') { t.value = saved; e.stopPropagation(); t.blur(); } });
      const d = el('button', 'ghost sm del', 'Delete'); d.setAttribute('aria-label', 'Delete this fact');
      d.onclick = async () => { await desk.memory.remove(f.id); say(''); memRefresh(); };
      r.append(chip, t, d); return r;
    };
    memRefresh = async () => {
      const facts = await desk.memory.list();
      const ae = document.activeElement; if (ae && ae.classList && ae.classList.contains('mem-text') && list.contains(ae) && ae.value !== ae.dataset.saved) return; // never clobber an edit in progress
      list.textContent = '';
      if (!facts.length) list.append(el('div', 'mem-empty', 'Nothing yet. Add a fact below, or just tell Glim something to remember.'));
      for (const f of facts) list.append(rowFor(f));
    };
    const add = el('div', 'mem-add');
    const ai = el('input', 'mem-new'); ai.type = 'text'; ai.id = 'memNew'; ai.placeholder = 'Add a fact, e.g. "AP Chem is 3rd period with Mr. Phipps"'; ai.spellcheck = false; ai.maxLength = 300; ai.setAttribute('aria-label', 'Add a fact');
    const at = el('input', 'mem-topic'); at.type = 'text'; at.id = 'memTopic'; at.placeholder = 'topic'; at.maxLength = 30; at.spellcheck = false; at.setAttribute('aria-label', 'Topic (optional)');
    const ab = el('button', 'ghost sm', 'Add'); ab.id = 'memAdd';
    const doAdd = async () => {
      const v = ai.value.trim(); if (!v) return;
      const tp = at.value.trim(); ai.value = ''; at.value = '';
      const res = await desk.memory.add({ text: v, topic: tp || undefined });
      if (res && res.ok) { say(res.replaced ? 'Updated a similar fact.' : 'Added.'); } else { ai.value = v; at.value = tp; say((res && res.error) || 'Could not save.', true); }
      memRefresh();
    };
    ab.onclick = doAdd; ai.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); doAdd(); } });
    add.append(ai, at, ab);
    box.append(list, add, note);
    return box;
  }
  // Keeping track of: active items from src/tracking.js, with Done and Remove per item.
  let trackRefresh = () => {};
  function trackUi() {
    const box = el('div', 'mem'), list = el('div', 'mem-list');
    list.id = 'trackList';
    trackRefresh = async () => {
      const items = await desk.tracking.list();
      list.textContent = '';
      if (!items.length) list.append(el('div', 'mem-empty', 'Nothing yet. Tell Glim you ordered something or have a deadline, and it will appear here.'));
      for (const it of items) {
        const r = el('div', 'mem-row'); r.dataset.what = it.what;
        const chip = el('span', 'mem-chip' + (it.until ? '' : ' none'), it.until || 'no date');
        const t = el('div', 'track-text'); t.append(el('span', null, it.what));
        if (it.source) t.append(el('small', 'dim', 'from ' + it.source));
        const dn = el('button', 'ghost sm', 'Done'); dn.setAttribute('aria-label', 'Mark done: ' + it.what);
        dn.onclick = async () => { await desk.tracking.done(it.what); trackRefresh(); };
        const rm = el('button', 'ghost sm del', 'Remove'); rm.setAttribute('aria-label', 'Remove: ' + it.what);
        rm.onclick = async () => { await desk.tracking.remove(it.what); trackRefresh(); };
        r.append(chip, t, dn, rm); list.append(r);
      }
    };
    box.append(list);
    return box;
  }
  function buildSettings() {
    const col = $('#settingsCol'); col.textContent = '';
    const gt = gate();
    // gated rows: Windows has no Sleep group and no Mac permissions card; say so in plain words instead
    const groups = SCHEMA.map((g) => {
      if (g.group === 'Sleep') return { group: g.group, rows: g.rows.filter((r) => (gt.sleepWindows ? r.key !== 'sleepApp' && r.key !== 'sleepPython' : r.key !== 'sleepOnlyPlugged')) };
      if (g.group === 'Screen control' && !gt.showPermRow && !info.e2e) return { group: g.group, rows: g.rows.map((r) => (r.type === 'perm' ? { type: 'note', label: 'Permissions', help: gt.permsNote } : r)) };
      return g;
    });
    for (const g of groups) {
      const sec = el('section', 's-group'); sec.append(el('h2', null, g.group));
      const card = el('div', 's-card');
      for (const r of g.rows) {
        const row = el('div', 's-row' + (r.type === 'danger' || r.type === 'memory' || r.type === 'tracking' ? ' stack' : ''));
        const lab = el('div', 's-lab'); lab.append(el('b', null, r.label), el('span', null, typeof r.help === 'function' ? r.help() : r.help));
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
        } else if (r.type === 'note') {
          ctl.append(el('span', 's-note', ''));
        } else if (r.type === 'modelseg') {
          const seg = el('div', 'seg'); seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', r.label);
          const btns = r.options.map(([slot, l]) => { const b = el('button', null, l); b.dataset.slot = slot; b.onclick = () => { save({ model: settings[slot], modelDefault: slot }).then(paintSettings); }; seg.append(b); return b; });
          ctl.append(seg); controls[r.key] = { paint: () => btns.forEach((b) => { b.dataset.v = settings[b.dataset.slot]; b.classList.toggle('on', b.dataset.slot === (settings.modelDefault || 'modelAuto')); }) };
        } else if (r.type === 'preset') {
          const seg = el('div', 'seg'); seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', r.label);
          const btns = Platform.presetsFor(plat()).map((pr) => { const b = el('button', null, pr.label); b.dataset.preset = pr.id; b.onclick = () => { const { id, label, builtin, ...patch } = pr; save(patch).then(paintSettings); }; seg.append(b); return b; });
          ctl.append(seg); controls.preset = { paint: () => { const cur = Platform.presetFor(settings.gatewayUrl); btns.forEach((b) => b.classList.toggle('on', !!cur && cur.id === b.dataset.preset)); } };
        } else if (r.type === 'toggle') {
          const b = el('button', 'toggle'); b.setAttribute('role', 'switch'); b.setAttribute('aria-label', r.label);
          b.onclick = () => { const cur = b.getAttribute('aria-checked') === 'true'; save({ [r.key]: r.on ? (cur ? 'off' : r.on) : !cur }).then(paintSettings); };
          ctl.append(b); controls[r.key] = { paint: () => b.setAttribute('aria-checked', String(r.on ? settings[r.key] === r.on : !!settings[r.key])) };
        } else if (r.type === 'test') {
          const note = el('span', 's-note'); const b = el('button', 'ghost', 'Test connection');
          b.onclick = async () => { note.className = 's-note'; note.textContent = 'Testing…'; const t = await desk.gateway.test(); note.className = 's-note ' + (t.ok ? 'ok' : 'bad'); note.textContent = t.ok ? 'Connected · ' + t.ms + ' ms' : 'Could not connect' + (t.error ? ' (' + t.error + ')' : ''); };
          b.id = 'testConn'; note.id = 'testNote'; ctl.append(note, b);
        } else if (r.type === 'setup') {
          const b = el('button', 'ghost', 'Run setup again'); b.id = 'runSetup';
          b.onclick = () => { closeSettings(); Onboard.show(); };
          ctl.append(b);
        } else if (r.type === 'sleepstat') {
          const note = el('div', 's-note'); note.id = 'sleepStat';
          const b = el('button', 'ghost', 'Sleep now'); b.id = 'sleepNow'; b.onclick = () => { closeSettings(); openSleepSheet(); };
          const bw = el('button', 'ghost', 'Wake'); bw.id = 'sleepWakeS'; bw.onclick = () => desk.sleep.wake();
          const bx = el('div'); bx.style.cssText = 'display:flex;flex-direction:column;gap:.4rem;align-items:flex-end;text-align:right';
          const rb = el('div'); rb.style.cssText = 'display:flex;gap:.4rem'; rb.append(b, bw); bx.append(rb, note); ctl.append(bx);
        } else if (r.type === 'window') {
          const mk = (key) => { const i = el('input'); i.type = 'time'; i.id = key; i.setAttribute('aria-label', key === 'sleepFrom' ? 'Night starts' : 'Night ends'); i.style.width = '8rem'; i.addEventListener('change', () => save({ [key]: i.value || undefined }).then(paintSettings)); controls[key] = { paint: () => { if (document.activeElement !== i) i.value = settings[key] || ''; } }; return i; };
          const to = el('span', 'dim', 'to'); ctl.append(mk('sleepFrom'), to, mk('sleepTo'));
          const ln = el('div', 's-note dim'); ln.id = 'sleepLearned'; lab.append(ln);
        } else if (r.type === 'memory') {
          row.removeChild(ctl); row.append(memUi());
        } else if (r.type === 'tracking') {
          row.removeChild(ctl); row.append(trackUi());
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
          rowc.append(mk('Permissions…', () => Perms.show()), mk('Open Accessibility settings', () => desk.openSystem('accessibility')), mk('Open Screen Recording settings', () => desk.openSystem('screen')));
          bx.append(rowb, rowc, out); ctl.append(bx);
        } else if (r.type === 'hotkey') {
          const b = el('button', 'ghost hotkey'); const note = el('span', 's-note'); b.id = 'hotkeyBtn';
          const show = (acc) => { b.textContent = Platform.hotkeyLabel(plat(), acc); };
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
            if (!k || (!mods.length && !/^F\d/.test(k))) { note.className = 's-note bad'; note.textContent = 'Use at least one modifier key (' + Platform.modifierHint(plat()) + ').'; return; }
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
  function paintSleepSettings() {
    const n = $('#sleepStat'); if (!n) return;
    n.className = 's-note' + (slp.available ? '' : ' bad');
    n.textContent = !slp.available ? slp.reason : (slp.error || slp.statusLine || '');
    const ln = $('#sleepLearned');
    if (ln) ln.textContent = !settings.sleepAdapt ? 'In effect: the times above.' : slp.learned ? 'In effect, learned from your last ' + slp.learned.days + ' days: ' + slp.learned.from + ' to ' + slp.learned.to + '.' : 'Still learning your routine (it needs 5 days): the times above are in effect.';
    $('#sleepNow').disabled = !slp.available || slp.asleep || slp.waking; $('#sleepWakeS').hidden = !(slp.asleep || slp.waking);
  }
  function paintSettings() { for (const c of Object.values(controls)) c.paint(); paintSegs(); paintSleepSettings(); }
  let settingsBuilt = false;
  function openSettings() {
    if (!settingsBuilt) { buildSettings(); settingsBuilt = true; }
    desk.sleep.state().then((v) => { slp = v; paintSleep(); paintSleepSettings(); });
    paintSettings(); memRefresh(); trackRefresh(); $('#settings').hidden = false; $('#settingsClose').focus();
  }
  function closeSettings() { $('#settings').hidden = true; input.focus(); }
  $('#btnSettings').onclick = openSettings; $('#settingsClose').onclick = closeSettings;
  desk.onOpenSettings(openSettings);
  window.__openSettings = openSettings;

  BrowserPanel.ctx.threadId = () => thread && thread.id;
  BrowserPanel.ctx.switchThread = async (id) => { if (id && (!thread || thread.id !== id)) await openThread(id); };

  // first-run setup finished or skipped: pick up the saved picks, refresh the welcome chips, hand the keyboard back
  window.addEventListener('onboard-done', async () => {
    const s = await desk.settings.get(); const { _hotkey, ...rest } = s; settings = rest;
    if (!running && msgs.querySelector('.welcome')) welcome();
    desk.helpers.list().then(paintAgents);
    input.focus();
  });

  // ---------- boot ----------
  (async () => {
    info = await desk.info();
    document.body.classList.add(info.platform);
    if (!gate().showSleepButton) $('#btnSleep').hidden = true; // Windows: Sleep runs on the Macs for now
    settings = await desk.settings.get(); paintSegs(); applyAppearance();
    gw = (await desk.gateway.state()) || gw; paintGateway();
    let last = null; try { last = localStorage.getItem('lastThread'); } catch (e) { /* ignore */ }
    const list = await desk.threads.list();
    if (!info.e2e && last && list.find((t) => t.id === last)) await openThread(last);
    else if (!info.e2e && list.length) await openThread(list[0].id);
    else await newThread();
    desk.helpers.list().then(paintAgents);
    if (!settings.onboarded) Onboard.show();
    window.__ready = true;
  })();
})();
