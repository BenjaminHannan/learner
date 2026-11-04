'use strict';
// The toolbar's Learn button (it replaced the Browser button). Click: "What should I learn about?" + Start. While a study runs the
// button reads "Learning: <topic>" and the popover has Stop. "Show browser" keeps Glim's browser panel one click away; the panel
// still opens by itself whenever Glim browses (panel.js, browser-show from main).
window.LearnButton = (() => {
  const desk = window.desk;
  const $ = (s) => document.querySelector(s);
  const btn = $('#btnLearn'), pop = $('#learnPop'), topic = $('#learnTopic'), err = $('#learnErr');
  let st = { learning: false };

  function paint(v) {
    if (v) st = v;
    const on = !!st.learning;
    $('#learnLabel').textContent = on ? 'Learning: ' + st.topic : 'Learn';
    btn.classList.toggle('on', on);
    btn.title = on ? 'Glim is learning about ' + st.topic + '. Click to stop or change it.' : 'Learn: send Glim off to study a topic until you stop it';
    $('#learnIdle').hidden = on; $('#learnBusy').hidden = !on;
    $('#learnTopicNow').textContent = on ? st.topic : '';
  }
  function showErr(t) { err.textContent = t || ''; err.hidden = !t; }
  function openPop() { pop.hidden = false; btn.setAttribute('aria-expanded', 'true'); showErr(''); if (!st.learning) setTimeout(() => topic.focus(), 0); }
  function closePop() { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); }

  async function start() {
    const t = topic.value.trim();
    if (!t) { showErr('Type what Glim should learn about.'); topic.focus(); return; }
    $('#learnStart').disabled = true;
    try {
      const r = await desk.learn.start(t);
      if (r && r.error) { showErr(r.error); return; }
      topic.value = ''; paint(r); closePop();
    } finally { $('#learnStart').disabled = false; }
  }
  async function stop() { const r = await desk.learn.stop(); paint(r || { learning: false }); closePop(); }

  btn.onclick = (e) => { e.stopPropagation(); if (pop.hidden) openPop(); else closePop(); };
  $('#learnStart').onclick = start;
  $('#learnStop').onclick = stop;
  topic.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); start(); } if (e.key === 'Escape') closePop(); });
  $('#learnShowBrowser').onclick = () => { closePop(); if (window.BrowserPanel) window.BrowserPanel.toggle(); };
  pop.addEventListener('click', (e) => e.stopPropagation());
  document.addEventListener('click', () => { if (!pop.hidden) closePop(); });
  if (desk.onLearn) desk.onLearn((v) => paint(v));
  if (desk.learn) desk.learn.state().then((v) => paint(v)).catch(() => {});
  paint();
  return { start, stop, paint, open: openPop, close: closePop };
})();
