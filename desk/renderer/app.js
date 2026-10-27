'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const desk = window.desk;

  // ---------- minimal markdown (escapes HTML first) ----------
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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
    const parts = String(text || '').split(/```/);
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
  window.__md = md; // for tests

  // ---------- state ----------
  let thread = null;      // {id,title}
  let running = false;
  let runThread = null;
  let turn = null;        // current assistant turn elements
  let trail = null;
  let settings = {};
  const stepEls = new Map();
  const msgs = $('#msgs');
  const scroller = $('#scroll');
  let stick = true;
  scroller.addEventListener('scroll', () => { stick = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 60; });
  const toBottom = () => { if (stick) scroller.scrollTop = scroller.scrollHeight; };

  const ICONS = { web_search: '⌕', browser_go: '◎', browser_click: '◉', browser_type: 'Aa', browser_scroll: '↕', browser_back: '←', browser_read: '≡', screen_look: '▣', screen_click: '▣', screen_type: '▣', screen_key: '⌘', open_app: '▶', run_shell: '>_', diary_search: '✎', ask_user: '?' };

  // ---------- rendering ----------
  function openLink(e) {
    const a = e.target.closest('a[data-href]');
    if (!a) return;
    e.preventDefault();
    setTab('browser');
    desk.browser.go(a.getAttribute('data-href'));
  }
  msgs.addEventListener('click', openLink);

  function welcome() {
    msgs.textContent = '';
    const w = el('div', 'welcome');
    w.append(el('div', 'mark', 'P'), el('h2', null, 'What should I take care of?'), el('div', null, 'I can browse, search, run commands and drive Mac apps. I ask before anything risky.'));
    const chips = el('div', 'chips');
    for (const t of ['Find the three best-reviewed ramen places near me and summarize them', 'What is in my Downloads folder? Group it by type', 'Search my diary for what I decided about the village model']) {
      const b = el('button', null, t); b.onclick = () => { $('#input').value = t; $('#input').focus(); autosize(); }; chips.append(b);
    }
    w.append(chips);
    msgs.append(w);
  }

  function newTurn() {
    const t = el('div', 'turn');
    msgs.append(t);
    turn = { root: t, think: null, thinkPre: null, text: null, raw: '', thinkRaw: '', t0: Date.now() };
    trail = null;
    return turn;
  }
  function ensureTurn() { return turn || newTurn(); }

  function addUser(text, steer) {
    const w = msgs.querySelector('.welcome'); if (w) w.remove();
    const u = el('div', 'user' + (steer ? ' steer' : ''), text);
    msgs.append(u); turn = null; trail = null; toBottom();
  }

  function thinkBlock(t, secs, text, live) {
    const d = el('details', 'think' + (live ? ' live' : ''));
    const s = el('summary', null, live ? 'Thinking…' : 'Thought for ' + (secs || 1) + ' s');
    const pre = el('pre', null, text || '');
    d.append(s, pre);
    return { d, s, pre };
  }

  let raf = 0;
  function paintText() {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      if (turn && turn.text) { turn.text.innerHTML = md(turn.raw); toBottom(); }
    });
  }

  function onReasoning(d) {
    const t = ensureTurn();
    if (!t.think) { const b = thinkBlock(t, 0, '', true); t.think = b; t.root.append(b.d); trail = null; }
    t.thinkRaw += d; t.think.pre.textContent = t.thinkRaw;
    t.think.pre.scrollTop = t.think.pre.scrollHeight;
  }
  function onText(d) {
    const t = ensureTurn();
    if (!t.text) { t.text = el('div', 'atext'); t.root.append(t.text); trail = null; }
    t.raw += d; paintText();
  }
  function onAssistantEnd(ev) {
    if (turn) {
      if (turn.text) turn.text.innerHTML = md(turn.raw);
      if (turn.think) { turn.think.d.classList.remove('live'); turn.think.s.textContent = 'Thought for ' + (ev.thinkSecs || Math.max(1, Math.round((Date.now() - turn.t0) / 1000))) + ' s'; }
      if (!turn.text && !turn.think) { /* tool-only turn: keep the root for the trail */ }
    }
    // next deltas belong to a new text block but the same trail container may continue
    if (turn) { const keep = turn; keep.text = null; keep.raw = ''; keep.think = null; keep.thinkRaw = ''; keep.t0 = Date.now(); }
    toBottom();
  }

  function setPlan(items) {
    const p = $('#plan');
    if (!items || !items.length) { p.hidden = true; return; }
    const ol = $('#planList'); ol.textContent = '';
    for (const i of items) ol.append(el('li', null, i));
    p.hidden = false;
  }
  $('#planToggle').onclick = () => { const p = $('#plan'); p.classList.toggle('min'); $('#planToggle').textContent = p.classList.contains('min') ? '+' : '–'; };

  function ensureTrail() {
    const t = ensureTurn();
    if (!trail) { trail = el('div', 'trail'); t.root.append(trail); }
    return trail;
  }

  function stepEl(id, tool, args, summary, state, preview) {
    const wrap = el('div', 'step ' + (state || 'run'));
    const row = el('button', 'row');
    const ico = el('span', 'ico', ICONS[tool] || '·');
    const sum = el('span', 'sum', summary);
    row.append(ico, sum, el('span', 'chev', '▾'));
    const detail = el('div', 'detail'); detail.hidden = true;
    const fill = (pv) => {
      detail.textContent = '';
      const a = el('div'); const b = el('b', null, tool + ' '); a.append(b, document.createTextNode(typeof args === 'string' ? args : JSON.stringify(args)));
      detail.append(a);
      if (pv) { detail.append(document.createTextNode('\n')); detail.append(document.createTextNode(pv)); }
    };
    fill(preview);
    row.onclick = () => { detail.hidden = !detail.hidden; };
    wrap.append(row, detail);
    wrap._fill = fill; wrap._sum = sum;
    return wrap;
  }

  function onStepStart(ev) {
    const w = stepEl(ev.id, ev.tool, ev.args, ev.summary, 'run');
    ensureTrail().append(w); stepEls.set(ev.id, w); toBottom();
  }
  function onStepEnd(ev) {
    const w = stepEls.get(ev.id); if (!w) return;
    w.classList.remove('run'); w.classList.add(ev.ok ? 'ok' : 'bad');
    w._sum.textContent = ev.summary;
    w._fill(ev.result || ev.preview);
    toBottom();
  }

  function card(cls, why) { const c = el('div', 'card ' + (cls || '')); c.append(el('div', 'why', why)); return c; }
  function onApproval(ev) {
    const host = stepEls.get(ev.id) || ensureTrail();
    const c = card(ev.danger ? 'danger' : '', ev.danger ? 'Risky command: needs your OK' : (ev.kind === 'password' ? 'Sensitive field: needs your OK' : 'Needs your OK'));
    if (ev.kind === 'shell') { const code = el('code', 'cmd', ev.text); c.append(code); } else c.append(el('div', null, ev.text));
    const btns = el('div', 'btns');
    const done = (v, label) => { window.desk.agent.respond(ev.rid || ev.id, v); c.classList.add('done'); btns.remove(); c.append(el('div', 'dim small', label)); };
    const once = el('button', 'amber-btn', 'Allow once'); once.onclick = () => done('once', 'Allowed once');
    btns.append(once);
    if (!ev.danger) { const task = el('button', 'ghost', 'Allow for this task'); task.onclick = () => done('task', 'Allowed for this task'); btns.append(task); }
    const deny = el('button', 'deny', 'Deny'); deny.onclick = () => done('deny', 'Denied');
    btns.append(deny); c.append(btns);
    host.append(c); toBottom();
  }
  function onAsk(ev) {
    const host = stepEls.get(ev.id) || ensureTrail();
    const c = card('', 'Premonition asks');
    c.append(el('div', null, ev.question));
    const ta = el('textarea'); ta.placeholder = 'Your answer…';
    const btns = el('div', 'btns');
    const send = el('button', 'amber-btn', 'Reply');
    const reply = (text) => { if (!text) return; window.desk.agent.respond(ev.id, text); c.classList.add('done'); ta.disabled = true; btns.remove(); c.append(el('div', 'dim small', 'You: ' + text)); };
    send.onclick = () => reply(ta.value.trim());
    ta.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); reply(ta.value.trim()); } });
    btns.append(send);
    for (const q of ['Yes, go ahead', 'No']) { const b = el('button', 'ghost', q); b.onclick = () => reply(q); btns.append(b); }
    c.append(ta, btns); ensureTrail().append(c); toBottom(); setTimeout(() => ta.focus(), 50);
  }

  function addNotice(who, text) {
    const n = el('div', 'notice');
    n.append(el('b', null, who ? who + ': ' : ''), document.createTextNode(text || ''));
    msgs.append(n); turn = null; trail = null; toBottom();
  }

  function setRunning(r) {
    running = r;
    $('#btnSend').textContent = r ? 'Steer' : 'Send'; $('#btnStop').hidden = !r; $('#runState').hidden = !r;
    $('#input').placeholder = r ? 'Add a note to steer the current task…' : thread && thread.helper ? 'This is a helper’s thread. Type here to steer it while it runs.' : 'Ask Premonition to do something on your Mac…';
  }
  // Send stays usable while running (steer): Enter sends the note.

  desk.onAgent((ev) => {
    if (!thread || ev.threadId !== thread.id) return;
    switch (ev.type) {
      case 'text': onText(ev.delta); break;
      case 'reasoning': onReasoning(ev.delta); break;
      case 'assistant_end': onAssistantEnd(ev); break;
      case 'step_start': onStepStart(ev); break;
      case 'step_end': onStepEnd(ev); break;
      case 'approval': onApproval(ev); break;
      case 'ask': onAsk(ev); break;
      case 'plan': setPlan(ev.items); break;
      case 'user': addUser(ev.text, ev.steer); break;
      case 'notice': addNotice(ev.helper, ev.text); break;
      case 'queued': $('#runState span').textContent = 'Waiting for a free slot…'; break;
      case 'started': $('#runState span').textContent = 'Working…'; break;
      case 'compacted': break;
      case 'error': { const e = el('div', 'errline', ev.message); ensureTurn().root.append(e); toBottom(); break; }
      case 'done': {
        setRunning(false); turn = null; trail = null;
        document.querySelectorAll('.step.run').forEach((s) => { s.classList.remove('run'); s.classList.add('bad'); });
        if (ev.stopped) { const n = el('div', 'dim small', 'Stopped.'); msgs.append(n); }
        loadThreads(); toBottom(); break;
      }
    }
  });

  // ---------- threads ----------
  function renderThread(t) {
    msgs.textContent = ''; stepEls.clear(); turn = null; trail = null; setPlan(null);
    if (!t.items || !t.items.length) { welcome(); return; }
    let plan = null;
    for (const it of t.items) {
      if (it.t === 'user') addUser(it.text);
      else if (it.t === 'assistant') {
        const tr = newTurn();
        if (it.thinking) { const b = thinkBlock(tr, it.thinkSecs, it.thinking, false); tr.root.append(b.d); }
        if (it.text) { const x = el('div', 'atext'); x.innerHTML = md(it.text); tr.root.append(x); }
        trail = null;
      } else if (it.t === 'step') {
        const w = stepEl(it.id, it.tool, it.args, it.summary, it.ok ? 'ok' : 'bad', it.preview);
        ensureTrail().append(w); stepEls.set(it.id, w);
      } else if (it.t === 'notice') { addNotice(it.helper, it.text); }
      else if (it.t === 'plan') plan = it.items;
    }
    setPlan(plan); turn = null; trail = null; stick = true; scroller.scrollTop = scroller.scrollHeight;
  }

  async function openThread(id) {
    const t = await desk.threads.load(id);
    if (!t) return;
    thread = { id: t.id, title: t.title, helper: t.helper || null };
    $('#title').textContent = t.title;
    renderThread(t);
    setRunning(!!t.running);
    for (const ev of t.pendingCards || []) { if (ev.type === 'approval') onApproval(ev); else if (ev.type === 'ask') onAsk(ev); }
    closeDrawer(); loadThreads();
    try { localStorage.setItem('lastThread', t.id); } catch (e) { /* ignore */ }
  }
  async function newThread() {
    const t = await desk.threads.create();
    thread = { id: t.id, title: t.title, helper: null };
    $('#title').textContent = t.title; renderThread(t); setRunning(false); closeDrawer(); loadThreads(); $('#input').focus();
  }
  async function loadThreads() {
    const list = await desk.threads.list();
    const ul = $('#threadList'); ul.textContent = '';
    for (const t of list.filter((x) => !x.helper)) {
      const li = el('li', t.id === (thread && thread.id) ? 'on' : '');
      const title = el('span', 't', t.title); const d = el('span', 'd', ago(t.updated));
      const x = el('button', null, '✕'); x.title = 'Delete';
      x.onclick = async (e) => { e.stopPropagation(); if (confirm('Delete "' + t.title + '"?')) { await desk.threads.remove(t.id); if (thread && thread.id === t.id) { await newThread(); } else loadThreads(); } };
      title.ondblclick = async (e) => { e.stopPropagation(); const n = prompt('Rename thread', t.title); if (n) { await desk.threads.rename(t.id, n); if (thread && thread.id === t.id) $('#title').textContent = n; loadThreads(); } };
      li.append(title, d, x); li.onclick = () => openThread(t.id); ul.append(li);
    }
    if (thread) { const cur = list.find((t) => t.id === thread.id); if (cur) $('#title').textContent = cur.title; }
  }
  // ---------- agents (helpers) ----------
  const STATUS_TEXT = { idle: 'idle', queued: 'waiting for a slot', running: 'running', 'waiting-for-Ben': 'waiting for you', stopped: 'stopped' };
  function when(ts) {
    if (!ts) return '';
    const d = new Date(ts), p = (n) => String(n).padStart(2, '0'), hm = p(d.getHours()) + ':' + p(d.getMinutes());
    return d.toDateString() === new Date().toDateString() ? hm : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()] + ' ' + hm;
  }
  function paintAgents(list) {
    const ul = $('#agentList'); ul.textContent = '';
    $('#agentsSec').hidden = !list.length;
    for (const h of list) {
      const li = el('li', t_on(h.threadId));
      const top = el('div', 'a-top');
      const dot = el('i', 'dot ' + h.status.replace(/[^\w]/g, ''));
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
  function t_on(id) { return thread && thread.id === id ? 'on' : ''; }
  desk.onHelpers(paintAgents);
  desk.onOpenThread((id) => openThread(id));
  function ago(ts) {
    const m = Math.round((Date.now() - ts) / 60000);
    if (m < 1) return 'now'; if (m < 60) return m + 'm'; if (m < 1440) return Math.round(m / 60) + 'h'; return Math.round(m / 1440) + 'd';
  }
  function openDrawer() { document.body.classList.add('drawer-open'); $('#drawer').setAttribute('aria-hidden', 'false'); loadThreads(); desk.helpers.list().then(paintAgents); }
  function closeDrawer() { document.body.classList.remove('drawer-open'); $('#drawer').setAttribute('aria-hidden', 'true'); }
  $('#btnThreads').onclick = () => document.body.classList.contains('drawer-open') ? closeDrawer() : openDrawer();
  $('#drawerShade').onclick = closeDrawer;
  $('#newThread').onclick = newThread;
  $('#title').onclick = async () => { if (!thread) return; const n = prompt('Rename thread', $('#title').textContent); if (n) { await desk.threads.rename(thread.id, n); $('#title').textContent = n; loadThreads(); } };

  // ---------- composer ----------
  const input = $('#input');
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(180, input.scrollHeight) + 'px'; }
  input.addEventListener('input', autosize);
  async function submit() {
    const text = input.value.trim();
    if (!text) return;
    if (!thread) await newThread();
    input.value = ''; autosize();
    if (thread.helper && !running) { msgs.append(el('div', 'errline', 'This is a helper’s thread. Use Run now in the Agents list, or ask the primary agent.')); toBottom(); return; }
    if (running) { addUser(text, true); await desk.agent.send(thread.id, text); return; }
    addUser(text);
    stick = true;
    setRunning(true); // before the call: a fast run can finish before send() resolves
    const r = await desk.agent.send(thread.id, text);
    if (r && r.error) { setRunning(false); msgs.append(el('div', 'errline', r.error)); return; }
    if (r && r.title) { thread.title = r.title; $('#title').textContent = r.title; }
  }
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); } });
  $('#btnSend').onclick = submit;
  $('#btnStop').onclick = () => desk.agent.stop(thread && thread.id);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (!$('#sheetWrap').hidden) closeSheet(); else if (document.body.classList.contains('drawer-open')) closeDrawer(); else if (running) desk.agent.stop(thread && thread.id); } });

  // ---------- top bar ----------
  function paintSegs() {
    document.querySelectorAll('#modelSeg button').forEach((b) => b.classList.toggle('on', b.dataset.model === settings.model));
    document.querySelectorAll('#modeSeg button').forEach((b) => b.classList.toggle('on', b.dataset.mode === settings.mode));
  }
  document.querySelectorAll('#modelSeg button').forEach((b) => b.onclick = async () => { settings = await desk.settings.set({ model: b.dataset.model }); paintSegs(); });
  document.querySelectorAll('#modeSeg button').forEach((b) => b.onclick = async () => { settings = await desk.settings.set({ mode: b.dataset.mode }); paintSegs(); });
  async function ping() { const r = await desk.ping(); const g = $('#gw'); g.classList.toggle('ok', !!r.ok); g.classList.toggle('bad', !r.ok); g.title = r.ok ? 'Gateway reachable' : 'Gateway not reachable'; }

  // ---------- work pane ----------
  let tab = 'browser';
  let hasPage = false;
  function setTab(t) {
    tab = t;
    document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('on', b.dataset.tab === t));
    $('#paneBrowser').hidden = t !== 'browser'; $('#paneScreen').hidden = t !== 'screen';
    syncView();
  }
  document.querySelectorAll('.tab').forEach((b) => b.onclick = () => setTab(b.dataset.tab));
  function syncView() {
    const show = hasPage && tab === 'browser' && $('#sheetWrap').hidden;
    desk.browser.visible(show);
    if (show) { const r = $('#browserHost').getBoundingClientRect(); desk.browser.bounds({ x: r.left, y: r.top, width: r.width, height: r.height }); }
  }
  new ResizeObserver(syncView).observe($('#browserHost'));
  window.addEventListener('resize', syncView);
  desk.onBrowser((s) => {
    hasPage = !!s.url && s.url !== 'about:blank';
    $('#browserHost .empty').style.display = hasPage ? 'none' : '';
    if (document.activeElement !== $('#addr')) $('#addr').value = s.url === 'about:blank' ? '' : s.url;
    $('#bBack').disabled = !s.canGoBack; $('#bFwd').disabled = !s.canGoForward;
    $('#bBack').style.opacity = s.canGoBack ? 1 : .35; $('#bFwd').style.opacity = s.canGoForward ? 1 : .35;
    syncView();
  });
  $('#bBack').onclick = () => desk.browser.back(); $('#bFwd').onclick = () => desk.browser.forward(); $('#bReload').onclick = () => desk.browser.reload();
  $('#addr').addEventListener('keydown', (e) => { if (e.key === 'Enter') { desk.browser.go($('#addr').value); $('#addr').blur(); } });
  $('#addr').addEventListener('focus', () => $('#addr').select());

  desk.onScreen((s) => {
    const box = $('#shotBox'); box.textContent = '';
    if (s.image) { const img = new Image(); img.src = s.image; img.alt = 'Latest screen capture'; box.append(img); }
    else box.append(el('div', 'empty', 'No screenshot available.'));
    const pre = $('#elList'); pre.hidden = false; pre.textContent = s.text;
    setTab('screen');
  });

  // splitter
  (() => {
    const sp = $('#splitter'); let drag = false;
    try { const w = localStorage.getItem('chatW'); if (w) document.documentElement.style.setProperty('--chat-w', w + 'px'); } catch (e) { /* ignore */ }
    sp.addEventListener('mousedown', (e) => { drag = true; sp.classList.add('drag'); e.preventDefault(); });
    window.addEventListener('mousemove', (e) => { if (!drag) return; const w = Math.max(340, Math.min(window.innerWidth * 0.7, e.clientX)); document.documentElement.style.setProperty('--chat-w', w + 'px'); syncView(); });
    window.addEventListener('mouseup', () => { if (!drag) return; drag = false; sp.classList.remove('drag'); try { localStorage.setItem('chatW', String(Math.round($('#chat').getBoundingClientRect().width))); } catch (e) { /* ignore */ } syncView(); });
  })();

  // ---------- settings ----------
  function openSheet() {
    $('#sGateway').value = settings.gatewayUrl || ''; $('#sModel').value = settings.model || ''; $('#sSteps').value = settings.maxSteps || 40; $('#sParallel').value = settings.maxParallel || 2;
    $('#sVision').value = settings.vision === 'on' ? 'on' : 'off'; $('#sDiary').value = settings.diaryPath || ''; $('#sPython').value = settings.pythonPath || ''; $('#sHelper').value = settings.helperPath || '';
    $('#sheetWrap').hidden = false; syncView();
  }
  function closeSheet() { $('#sheetWrap').hidden = true; syncView(); }
  $('#btnSettings').onclick = openSheet; $('#sheetClose').onclick = closeSheet;
  $('#sheetWrap').addEventListener('mousedown', (e) => { if (e.target.id === 'sheetWrap') closeSheet(); });
  $('#sheetSave').onclick = async () => {
    settings = await desk.settings.set({ gatewayUrl: $('#sGateway').value.trim(), model: $('#sModel').value.trim() || 'qwen36-auto', maxSteps: Math.max(1, Number($('#sSteps').value) || 40), maxParallel: Math.min(4, Math.max(1, Number($('#sParallel').value) || 2)), vision: $('#sVision').value, diaryPath: $('#sDiary').value.trim(), pythonPath: $('#sPython').value.trim(), helperPath: $('#sHelper').value.trim() });
    paintSegs(); closeSheet(); ping();
  };
  const permShow = (r) => {
    const o = $('#permOut');
    if (r.error) { o.textContent = r.error; return; }
    o.textContent = 'Accessibility: ' + (r.accessibility ? 'granted' : 'not granted') + ' · Screen recording: ' + (r.screenRecording ? 'granted' : 'not granted');
  };
  $('#permCheck').onclick = async () => { $('#permOut').textContent = 'Checking…'; permShow(await desk.screen.check()); };
  $('#permAsk').onclick = async () => { $('#permOut').textContent = 'Asking macOS…'; const r = await desk.screen.ask(); permShow(r.error ? r : await desk.screen.check()); };

  // ---------- boot ----------
  (async () => {
    const info = await desk.info();
    document.body.classList.add(info.platform);
    settings = await desk.settings.get(); paintSegs(); ping(); setInterval(ping, 10000);
    let last = null; try { last = localStorage.getItem('lastThread'); } catch (e) { /* ignore */ }
    const list = await desk.threads.list();
    if (!info.e2e && last && list.find((t) => t.id === last)) await openThread(last);
    else if (!info.e2e && list.length) await openThread(list[0].id);
    else await newThread();
    const st = await desk.browser.state(); if (st && st.url && st.url !== 'about:blank') desk.browser.visible(true);
    desk.helpers.list().then(paintAgents);
    window.__ready = true;
  })();
})();
