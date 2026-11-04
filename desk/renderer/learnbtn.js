'use strict';
// The toolbar's Learn button (it replaced the Browser button). Ben Nov 4: no popup to type in. Click Learn and the chat box itself
// turns into the Learn box: a soft green glow, "What should Glim learn about?", a green send button. Enter starts the study
// (desk.learn.start), Esc or a second click on Learn puts the box back exactly as it was; typed text stays in the box either way.
// While a study runs the button reads "Learning: <topic>" and a small popover has Stop, View quiz and Show browser.
// "Show browser" keeps Glim's browser panel one click away; the panel still opens by itself whenever Glim browses (panel.js).
window.LearnButton = (() => {
  const desk = window.desk;
  const $ = (s) => document.querySelector(s);
  const btn = $('#btnLearn'), pop = $('#learnPop'), err = $('#learnErr');
  const input = $('#input'), box = $('#composer .box') || $('#composerBox'), send = $('#btnSend'), hint = $('#hint');
  const PLACEHOLDER = 'What should Glim learn about?', HINT = 'Enter to start learning · Esc to cancel', NUDGE = 'Type a topic first, like “volcanoes”. Esc to cancel.';
  const ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5"/></svg>';
  let st = { learning: false }, composing = false, saved = null, busy = false;
  // app.js sets this: repaint the box for the current state (placeholder, hint, send button, read-only) after learn mode ends
  const api = { restore: null };

  function paint(v) {
    if (v) st = v;
    const on = !!st.learning;
    // always-on v2: the honest quiz score, e.g. "Lv1 81% · Lv2 30%" (* = not yet measured after a sleep)
    const lv = on && Array.isArray(st.levels) ? st.levels.filter((x) => x.pct != null).map((x) => 'Lv' + x.level + ' ' + x.pct + '%' + (x.official ? '' : '*')).join(' · ') : '';
    $('#learnLabel').textContent = on ? 'Learning: ' + st.topic + (lv ? ' · ' + lv : '') : 'Learn';
    const sc = $('#learnScore'); if (sc) { sc.hidden = !on; sc.textContent = !on ? '' : st.writing ? 'Writing a locked quiz from several websites…' : st.score ? 'Quiz: ' + st.score + (lv.includes('*') ? '  (* not yet measured after a sleep)' : '') : 'The quiz is written once the Mac is free.'; }
    btn.classList.toggle('on', on);
    btn.title = on ? 'Glim is learning about ' + st.topic + '. Click to stop or change it.' : 'Learn: send Glim off to study a topic until you stop it';
    $('#learnTopicNow').textContent = on ? st.topic : '';
    if (on && composing) cancel();
    if (!on && !pop.hidden) closePop();   // the busy popover only exists while learning
  }
  function showErr(t) { err.textContent = t || ''; err.hidden = !t; }
  function openPop() { pop.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
  function closePop() { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
  const asleep = () => { const b = $('#sleepBar'); return !!(b && !b.hidden); };

  // ---- learn mode in the chat box ----
  function dress() {   // learn mode's look; app.js calls it again after it repaints the box for its own reasons
    if (!composing) return;
    box.classList.add('learning'); send.classList.add('learn');
    input.placeholder = PLACEHOLDER; input.readOnly = false;
    if (hint.textContent !== NUDGE) hint.textContent = HINT;
    send.innerHTML = ARROW + '<span class="sr">Start learning</span>'; send.title = 'Start learning (Enter)';
    btn.classList.add('composing'); btn.setAttribute('aria-pressed', 'true');
  }
  function enter() {
    if (composing) return;
    if (asleep()) { showErr('Glim is asleep. Wake Glim first, then press Learn.'); return; }
    saved = { placeholder: input.placeholder, hint: hint.textContent, sendHTML: send.innerHTML, sendTitle: send.title, readOnly: input.readOnly };
    composing = true; showErr(''); dress();
    setTimeout(() => input.focus(), 0);
  }
  function cancel() {
    if (!composing) return;
    composing = false;
    box.classList.remove('learning'); send.classList.remove('learn');
    btn.classList.remove('composing'); btn.setAttribute('aria-pressed', 'false');
    if (saved) { input.placeholder = saved.placeholder; hint.textContent = saved.hint; send.innerHTML = saved.sendHTML; send.title = saved.sendTitle; input.readOnly = saved.readOnly; }
    saved = null; showErr('');
    if (typeof api.restore === 'function') { try { api.restore(); } catch (e) { /* the saved look is already back */ } }
  }
  async function submitTopic() {
    if (!composing || busy) return;
    const t = input.value.trim();
    if (!t) { hint.textContent = NUDGE; input.focus(); return; }
    busy = true; send.disabled = true; showErr('');
    try {
      const r = await desk.learn.start(t);
      if (!r || r.error) { showErr((r && r.error) || 'Glim could not start learning. Try again.'); return; }
      input.value = ''; input.dispatchEvent && input.dispatchEvent(new Event('input'));   // the box shrinks back
      cancel(); paint(r);
    } catch (e) { showErr(String(e && e.message || e)); }
    finally { busy = false; send.disabled = false; }
  }
  async function stop() { const r = await desk.learn.stop(); paint(r || { learning: false }); closePop(); }

  btn.onclick = (e) => {
    e.stopPropagation();
    if (st.learning) { if (pop.hidden) openPop(); else closePop(); return; }
    if (composing) cancel(); else enter();
  };
  input.addEventListener('keydown', (e) => {
    if (!composing) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cancel(); return; }   // not the chat's Esc (that stops a running task)
    if (hint.textContent === NUDGE && e.key.length === 1) hint.textContent = HINT;
  });
  $('#learnStop').onclick = stop;
  // Ben can peek at the locked quiz: questions, the answers from the sources, and the source pages
  if ($('#learnViewQuiz')) $('#learnViewQuiz').onclick = async () => {
    const qb = $('#learnQuiz'); if (!qb.hidden) { qb.hidden = true; return; }
    const z = desk.learn.quiz ? await desk.learn.quiz() : null; qb.textContent = '';
    if (!z || !z.levels.length) qb.append(Object.assign(document.createElement('p'), { className: 'lb-sub', textContent: z && z.status === 'failed' ? 'Glim could not write a quiz from the web for this topic.' : 'No quiz yet: it is written when the Mac is free.' }));
    else for (const L of z.levels) {
      qb.append(Object.assign(document.createElement('b'), { textContent: 'Level ' + L.level }));
      const ol = document.createElement('ol');
      for (const q of L.questions) { const li = document.createElement('li'); li.append(document.createTextNode(q.q + ' — ' + q.answer + ' ')); const a = document.createElement('a'); a.href = q.source; a.textContent = 'source'; a.target = '_blank'; a.rel = 'noreferrer'; li.append(a); ol.append(li); }
      qb.append(ol);
    }
    qb.hidden = false;
  };
  $('#learnShowBrowser').onclick = () => { closePop(); if (window.BrowserPanel) window.BrowserPanel.toggle(); };
  pop.addEventListener('click', (e) => e.stopPropagation());
  document.addEventListener('click', () => { if (!pop.hidden) closePop(); });
  if (desk.onLearn) desk.onLearn((v) => paint(v));
  if (desk.learn) desk.learn.state().then((v) => paint(v)).catch(() => {});
  paint();
  return Object.assign(api, { stop, paint, open: openPop, close: closePop, enter, cancel, dress, submitTopic, composing: () => composing });
})();
