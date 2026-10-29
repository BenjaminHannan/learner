'use strict';
// The in-window browser panel (chrome only; the page itself is a WebContentsView that main.js stacks above this UI over #bSlot).
// Wide windows: a right-hand split with a draggable divider. Narrow windows (< 1000 px): a full-width sheet with a Chat button.
// The slide is driven here frame by frame: we move the chrome and tell main the slot rect, so the page moves with it.
window.BrowserPanel = (() => {
  const $ = (s) => document.querySelector(s);
  const desk = window.desk;
  const NARROW = 1000, MIN_W = 420, MIN_CHAT = 360, MS = 240;
  let key = null, open = false, frac = 0.58, vis = 0, anim = 0, dragging = false, held = false, keys = [];
  const states = new Map();
  try { const f = parseFloat(localStorage.getItem('bpanelFrac')); if (f > 0.2 && f < 0.85) frac = f; } catch (e) { /* ignore */ }
  const panel = $('#bpanel'), slot = $('#bSlot');
  const narrow = () => window.innerWidth < NARROW;
  const target = () => (narrow() ? window.innerWidth : Math.max(MIN_W, Math.min(Math.round(window.innerWidth * frac), window.innerWidth - MIN_CHAT)));
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const suspended = () => !$('#call').hidden || !$('#settings').hidden || !$('#screenModal').hidden || (narrow() && document.body.classList.contains('drawer-open'));
  // Ben Oct 28 (blank Apple sign-in): the permissions card no longer blanks the page in a narrow window either; the card just waits behind the page.
  // the permissions card no longer blanks a wide panel: it shrinks into the chat column (app.css body.bp-open #perms), and the page
  // stays up. It used to hide the page whenever the card showed, and the card stays up on a Mac that lacks Screen Recording/Accessibility.

  function rect() {
    const t = target();
    return { x: panel.offsetLeft + slot.offsetLeft + (vis > 0 ? t - vis : 0), y: panel.offsetTop + slot.offsetTop, width: slot.offsetWidth, height: slot.offsetHeight };
  }
  function layout() {
    const t = target();
    panel.style.width = t + 'px';
    panel.style.transform = 'translateX(' + (t - vis) + 'px)';
    panel.classList.toggle('shown', vis > 0 || open);
    document.body.classList.toggle('bp-open', open);
    document.body.classList.toggle('bp-narrow', narrow());
    document.documentElement.style.setProperty('--bp', (narrow() ? 0 : vis) + 'px');
    $('#btnBrowser').setAttribute('aria-pressed', open ? 'true' : 'false');
    $('#btnBrowser').classList.toggle('on', open);
  }
  let pend = false;
  function report() {
    if (pend) return; pend = true;
    requestAnimationFrame(() => {
      pend = false;
      desk.browser.layout({ key, open: open || vis > 0, top: !!key && vis > 0 && !dragging && !suspended() && (open || anim > 0), rect: rect() });
    });
  }
  function reportNow() { desk.browser.layout({ key, open: open || vis > 0, top: !!key && vis > 0 && !dragging && !suspended() && open, rect: rect() }); }
  function setVis(v) { vis = v; layout(); report(); }

  function slide(to, done) {
    const from = vis, t0 = performance.now(), id = ++anim;
    if (reduced() || from === to) { setVis(to); anim = 0; if (done) done(); return; }
    const step = (now) => {
      if (id !== anim) return;
      const p = Math.min(1, (now - t0) / MS), e = 1 - Math.pow(1 - p, 3);
      setVis(Math.round(from + (to - from) * e));
      if (p < 1) requestAnimationFrame(step); else { anim = 0; if (done) done(); }
    };
    requestAnimationFrame(step);
  }

  function paint(s) {
    if (s) states.set(s.key, s);
    s = states.get(key);
    if (!s) return;
    if (document.activeElement !== $('#bAddr')) $('#bAddr').value = s.url === 'about:blank' ? '' : (s.url || '');
    $('#bBack').disabled = !s.canGoBack; $('#bFwd').disabled = !s.canGoForward;
    $('#bTitle').textContent = s.title || (s.url ? s.url.replace(/^https?:\/\//, '').split('/')[0] : '') || s.label || 'Browser';
    const f = $('#bFav'); f.textContent = '';
    if (s.favicon) { const i = new Image(); i.alt = ''; i.src = s.favicon; i.onerror = () => { f.textContent = '·'; }; f.append(i); } else f.textContent = ((s.url || '').replace(/^\w+:\/\//, '')[0] || '·').toUpperCase();
    held = !!s.held;
    const w = $('#bWho'); const glim = !!s.active && !held && !s.login;
    w.classList.toggle('active', glim);
    w.querySelector('span').textContent = s.login ? 'Your turn to sign in' : glim ? 'Glim is browsing' : held ? 'You’re in control' : 'Glim is idle';
    const t = $('#bTake');
    t.textContent = held ? 'Hand back to Glim' : 'Take over';
    t.hidden = !!s.login;
    t.title = held ? 'Let Glim carry on from this page' : 'Pause Glim’s browsing so you can use the page';
    $('#bBanner').hidden = !s.login;
    panel.classList.toggle('login', !!s.login);
    $('#bpanel').dataset.state = s.login ? 'login' : held ? 'you' : glim ? 'glim' : 'idle';
    if (open) report();
  }

  function show(k) {
    if (dragging) endDrag();
    const switching = open && k !== key;
    key = k;
    paint();
    desk.browser.cmd(k, 'state').then(paint);
    if (open && !switching) { report(); return; }
    open = true;
    layout();
    if (switching) { report(); return; }
    slide(target());
  }
  function close(fromMain) {
    if (!open && !vis) return;
    const k = key;
    open = false;
    reportNow(); // the page stays above the UI for the slide-out (top is kept while anim runs)
    if (k && !fromMain) desk.browser.cmd(k, 'close');
    slide(0, () => { layout(); reportNow(); });
  }
  // Ben Oct 29: the button was hidden until Glim had made a browser, so he could not open one himself. With none yet, this chat's own
  // browser is made now (blank), with the address bar ready to type into.
  const toggle = () => {
    if (open) return close();
    if (keys.length) return desk.browser.open(keys[keys.length - 1].key, keys[keys.length - 1].url, false, ctx.threadId());
    const t = ctx.threadId() || 'ben';   // no chat yet: still a browser (sign-ins are shared with Glim's)
    desk.browser.open(t, '', false, t).then(() => setTimeout(() => { if (open && !$('#bAddr').value) $('#bAddr').focus(); }, 400)).catch(() => {});
  };

  // ---- divider
  const div = $('#bdiv');
  div.addEventListener('pointerdown', (e) => {
    if (narrow()) return;
    dragging = true; try { div.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ } div.classList.add('drag'); document.body.classList.add('bp-drag'); reportNow();
  });
  div.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const w = Math.max(MIN_W, Math.min(window.innerWidth - e.clientX, window.innerWidth - MIN_CHAT));
    frac = w / window.innerWidth; vis = w; layout(); report();
  });
  const endDrag = () => {
    if (!dragging) return;
    dragging = false; div.classList.remove('drag'); document.body.classList.remove('bp-drag');
    try { localStorage.setItem('bpanelFrac', String(frac)); } catch (e) { /* ignore */ }
    vis = target(); layout(); reportNow();
  };
  div.addEventListener('pointerup', endDrag); div.addEventListener('pointercancel', endDrag); div.addEventListener('lostpointercapture', endDrag); window.addEventListener('blur', endDrag);
  div.addEventListener('dblclick', () => { frac = 0.58; vis = target(); layout(); reportNow(); });

  window.addEventListener('resize', () => { if (open && !anim) vis = target(); layout(); report(); });
  new ResizeObserver(report).observe(slot);
  const mo = new MutationObserver(report);
  for (const id of ['#settings', '#screenModal', '#perms', '#call']) { const n = $(id); if (n) mo.observe(n, { attributes: true, attributeFilter: ['hidden'] }); }
  mo.observe(document.body, { attributes: true, attributeFilter: ['class'] });

  // ---- chrome
  const ctx = { threadId: () => null, switchThread: async () => {} };
  $('#bBack').onclick = () => desk.browser.cmd(key, 'back'); $('#bFwd').onclick = () => desk.browser.cmd(key, 'forward'); $('#bReload').onclick = () => desk.browser.cmd(key, 'reload');
  $('#bClose').onclick = () => close(); $('#bChat').onclick = () => close();
  $('#bTake').onclick = () => { if (held) { desk.browser.cmd(key, 'handback'); } else { desk.browser.cmd(key, 'takeover'); desk.browser.cmd(key, 'focus'); } };
  $('#bDone').onclick = () => desk.browser.cmd(key, 'done'); $('#bSkip').onclick = () => desk.browser.cmd(key, 'skip');
  $('#bAddr').addEventListener('keydown', (e) => { if (e.key === 'Enter') { desk.browser.cmd(key, 'go', $('#bAddr').value); $('#bAddr').blur(); } });
  $('#bAddr').addEventListener('focus', () => $('#bAddr').select());
  $('#btnBrowser').onclick = toggle;

  desk.onBrowserState((s) => paint(s));
  desk.onBrowserShow(async (ev) => { await ctx.switchThread(ev.threadId); show(ev.key); });
  desk.onBrowserHide((ev) => { if (ev.key === key) close(true); });
  desk.onBrowserGone((ev) => { if (ev.key === key) { open = false; vis = 0; anim++; layout(); reportNow(); } });
  layout(); report();

  return {
    ctx,
    show, close, isOpen: () => open,
    // the browser cards of the open thread (from app.js)
    setKeys(list) { keys = list; },
    async threadChanged() {
      if (!open) return;
      const last = keys[keys.length - 1];
      if (last && await desk.browser.exists(last.key)) { if (last.key !== key) show(last.key); } else close();
    }
  };
})();
