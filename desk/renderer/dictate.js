'use strict';
// Dictation in the chat box: the mic button, Cmd+Shift+D, and the pure text-merging logic (DictateText, also required by the tests).
// All the listening happens in the main process (src/dictate.js + `deskhelper dictate`); this only puts the words in the textarea.
(function (root) {
  // ---- pure: existing text + finals + the in-progress partial -> the textarea value ----
  const join = (a, b) => (!a ? b : !b ? a : /\s$/.test(a) ? a + b : a + ' ' + b);
  function merge(base, finals, partial) {
    let t = String(base || '');
    for (const f of finals || []) { const s = String(f || '').trim(); if (s) t = join(t, s); }
    const p = String(partial || '').trim();
    return p ? join(t, p) : t;
  }
  // state: {base, finals: [], partial}. A partial replaces the previous partial; a final is committed and clears the partial.
  const begin = (base) => ({ base: String(base || ''), finals: [], partial: '' });
  function apply(st, ev) {
    if (ev.type === 'partial') return { ...st, partial: String(ev.text || '') };
    if (ev.type === 'final') return { ...st, finals: String(ev.text || '').trim() ? st.finals.concat(String(ev.text).trim()) : st.finals, partial: '' };
    return st;
  }
  const text = (st) => merge(st.base, st.finals, st.partial);
  const DictateText = { merge, begin, apply, text };
  root.DictateText = DictateText;
  if (typeof module !== 'undefined' && module.exports) module.exports = DictateText;
  if (typeof document === 'undefined') return;

  // ---- UI ----
  root.DictateUI = (() => {
    const $ = (s) => document.querySelector(s);
    let desk, ctx, btn, input, note, active = false, ignoring = false, st = null, saved = '', lastWritten = '';

    const showNote = (msg, pane) => {
      $('#dictNoteText').textContent = msg;
      const b = $('#dictSettings'); b.hidden = !pane; b.onclick = () => desk.openSystem(pane);
      note.hidden = false;
    };
    const hideNote = () => { note.hidden = true; };
    function paint() {
      btn.classList.toggle('on', active); btn.setAttribute('aria-pressed', String(active));
      btn.title = active ? 'Stop dictation (Cmd+Shift+D, Esc or Enter)' : 'Dictate: speak instead of typing (Cmd+Shift+D)';
      if (active) input.placeholder = 'Listening…';
    }
    function write() {
      input.value = lastWritten = DictateText.text(st);
      input.dispatchEvent(new Event('input', { bubbles: true })); // the box autosizes on input
      input.scrollTop = input.scrollHeight;
    }
    function finish() {
      if (!active) return;
      active = false;
      paint(); if (input.placeholder === 'Listening…') input.placeholder = saved; // only if nothing else changed it meanwhile
      input.focus();
      const n = input.value.length; try { input.setSelectionRange(n, n); } catch (e) { /* ignore */ }
    }
    async function start() {
      if (active || !ctx.enabled) return;
      if (typeof CallUI !== 'undefined' && CallUI.isOpen()) { showNote('End the call before dictating.'); return; }
      hideNote();
      st = DictateText.begin(input.value); ignoring = false; lastWritten = input.value;
      saved = input.placeholder; active = true; paint(); input.focus();
      const r = await desk.dictate.start();
      if (r && r.error) { active = false; paint(); if (input.placeholder === 'Listening…') input.placeholder = saved; showNote(r.error); }
    }
    function stop() { if (active) desk.dictate.stop(); }
    const toggle = () => (active ? stop() : start());

    function onDictate(ev) {
      switch (ev.type) {
        case 'partial': case 'final': if (active && !ignoring) {
          // the box was changed by something else (Send cleared it, a chip, wake-and-send): drop these words and stop
          if (input.value !== lastWritten) { ignoring = true; stop(); break; }
          st = DictateText.apply(st, ev); write();
        } break;
        case 'state': if (ev.state === 'ended') {
          if (active && ev.reason === 'silence') showNote('Stopped listening after a few seconds of silence.');
          else if (active && ev.reason === 'limit') showNote('Stopped after 2 minutes. Click the mic to keep going.');
          finish();
        } break;
        case 'error': {
          const pane = ev.kind === 'mic-denied' ? 'microphone' : '';
          showNote(ev.message, pane);
          finish(); break;
        }
      }
    }

    function init(c) {
      ctx = c; desk = window.desk; btn = $('#btnDictate'); input = $('#input'); note = $('#dictNote');
      ctx.enabled = !!Platform.features(c.platform, c.popts).dictate;
      if (!ctx.enabled) { btn.hidden = true; return; }
      btn.onclick = toggle;
      desk.onDictate(onDictate);
      $('#dictNoteClose').onclick = hideNote;
      // capture phase: Esc and Enter must stop dictation before the chat's own handlers (stop the agent / send) see them
      document.addEventListener('keydown', (e) => {
        if (active && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); stop(); return; }
        if (active && e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.target === input) { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); stop(); return; }
        if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.code === 'KeyD' && !e.altKey) { e.preventDefault(); if (active || !c.blocked || !c.blocked()) toggle(); }
      }, true);
      // typing while dictating ends it, and the words still on their way are dropped so they do not overwrite what was typed
      input.addEventListener('input', (e) => { if (active && e.isTrusted && !ignoring) { ignoring = true; stop(); } });
    }
    return { init, isActive: () => active, stop };
  })();
})(typeof window !== 'undefined' ? window : globalThis);
