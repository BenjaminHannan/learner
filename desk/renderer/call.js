'use strict';
// Call Glim: the call button, the full-window call overlay and Cmd+Shift+C. All the listening / speaking happens in the main
// process (src/call.js + deskhelper); this only draws what it reports. CallUI.init({info, openThread}) is called once at boot.
window.CallUI = (() => {
  const $ = (s) => document.querySelector(s);
  const MOOD = { connecting: 'idle', listening: 'idle', thinking: 'thinking', speaking: 'working', ended: 'idle' };
  const STATUS = { connecting: 'Connecting…', listening: 'Listening…', thinking: 'Thinking…', speaking: 'Speaking…' };
  let desk, glim, active = false, muted = false, state = 'connecting', t0 = 0, timer = 0, ctx = null, hadError = false, threadId = null;

  const isOpen = () => !$('#call').hidden;
  const mmss = () => { const s = Math.floor((Date.now() - t0) / 1000); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  function paint() {
    const root = $('#call');
    root.classList.toggle('speaking', state === 'speaking'); root.classList.toggle('muted', muted);
    $('#callStatus').textContent = hadError ? 'Call ended' : muted && state === 'listening' ? 'Muted' : STATUS[state] || '';
    Mascot.set(glim, hadError ? 'error' : muted && state === 'listening' ? 'sleepy' : MOOD[state] || 'idle');
    $('#callMute').textContent = muted ? 'Unmute' : 'Mute'; $('#callMute').setAttribute('aria-pressed', String(muted));
    $('#callHang').textContent = active ? 'Hang up' : 'Close';
    $('#callMute').hidden = !active;
  }
  function open() {
    const root = $('#call');
    root.hidden = false; active = true; muted = false; state = 'connecting'; hadError = false; threadId = null; t0 = Date.now();
    for (const id of ['#callYou', '#callSay']) $(id).textContent = '';
    for (const id of ['#callErr', '#callNote']) $(id).hidden = true;
    $('#callRing').style.setProperty('--lv', 0);
    clearInterval(timer); timer = setInterval(() => { if (active) $('#callTime').textContent = mmss(); }, 1000); $('#callTime').textContent = '0:00';
    paint(); $('#callHang').focus();
  }
  function showError(msg, kind) {
    $('#callErrText').textContent = msg;
    const pane = kind === 'mic-denied' ? 'microphone' : kind === 'speech-denied' ? 'speech' : '';
    const b = $('#callSettings'); b.hidden = !pane; b.onclick = () => desk.openSystem(pane);
    $('#callErr').hidden = false;
  }
  function close() {
    clearInterval(timer); $('#call').hidden = true; active = false;
    const id = threadId; threadId = null;
    if (id && !hadError && ctx.openThread) ctx.openThread(id); // the call is a normal chat: show what was said
    const i = $('#input'); if (i) i.focus();
  }
  async function start() {
    if (active || isOpen() || !ctx.enabled) return;
    open();
    const r = await desk.call.start();
    if (r && r.error) { active = false; hadError = true; showError(r.error); paint(); return; }
    threadId = r && r.threadId;
  }
  async function hangup() { if (active) { await desk.call.stop(); } else close(); }

  function onCall(ev) {
    if (!isOpen()) return;
    switch (ev.type) {
      case 'state':
        muted = !!ev.muted; state = ev.state;
        if (ev.state === 'ended') { active = false; clearInterval(timer); if (!hadError) { close(); return; } }
        if (ev.state === 'thinking') { $('#callSay').textContent = ''; }
        paint(); break;
      case 'partial': $('#callYou').textContent = ev.text ? '“' + ev.text + '”' : ''; break;
      case 'final': $('#callYou').textContent = '“' + ev.text + '”'; $('#callSay').textContent = ''; break;
      case 'reply': $('#callSay').textContent = ev.text; break;
      case 'level': $('#callRing').style.setProperty('--lv', Math.min(1, ev.level)); break;
      case 'bargein': $('#callSay').textContent = ''; break;
      case 'note': {
        const n = ev.note === 'offline-unavailable' ? 'Offline speech recognition is not installed on this Mac, so Apple’s servers may be used to understand you.' : ev.note === 'no-echo-cancel' ? 'Echo cancelling is not available here. Use headphones so Glim does not hear itself.' : '';
        if (n) { $('#callNote').textContent = n; $('#callNote').hidden = false; }
        break;
      }
      case 'error':
        showError(ev.message, ev.kind);
        if (ev.fatal) { hadError = true; active = false; paint(); }
        break;
    }
  }

  function init(c) {
    ctx = c; desk = window.desk;
    const btn = $('#btnCall');
    ctx.enabled = !!Platform.features(c.platform, c.popts).call;
    if (!ctx.enabled) { btn.disabled = true; btn.title = 'Calling is coming to Windows soon'; btn.setAttribute('aria-label', 'Calling is coming to Windows soon'); }
    glim = Mascot.el('idle', 150, { cls: 'follow' }); $('#callGlim').append(glim);
    btn.onclick = start;
    $('#callHang').onclick = hangup;
    $('#callMute').onclick = () => { muted = !muted; paint(); desk.call.mute(muted); };
    desk.onCall(onCall);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen()) { e.preventDefault(); e.stopPropagation(); hangup(); return; }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.code === 'KeyC' && !e.altKey) { e.preventDefault(); if (isOpen()) hangup(); else if (!c.blocked || !c.blocked()) start(); }
    }, true);
  }
  return { init, isOpen };
})();
