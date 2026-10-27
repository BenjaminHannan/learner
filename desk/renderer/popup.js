'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const p = window.deskPopup;
  document.body.classList.add(navigator.platform.startsWith('Mac') ? 'darwin' : 'other');
  const paint = (s) => {
    if (!s) return;
    if (document.activeElement !== $('#addr')) $('#addr').value = s.url === 'about:blank' ? '' : (s.url || '');
    $('#back').disabled = !s.canGoBack; $('#fwd').disabled = !s.canGoForward;
    document.title = s.title || 'Browser';
  };
  p.onState(paint);
  const active = (a) => { const w = $('#who'); w.classList.toggle('active', !!a); w.querySelector('span').textContent = a ? 'Glim is browsing' : 'You’re in control'; };
  p.onActive(active);
  p.onBanner((on) => { $('#banner').hidden = !on; });
  $('#back').onclick = () => p.cmd('back'); $('#fwd').onclick = () => p.cmd('forward'); $('#reload').onclick = () => p.cmd('reload');
  $('#close').onclick = () => p.cmd('close');
  $('#handback').onclick = () => p.cmd('handback');
  $('#done').onclick = () => p.cmd('done');
  $('#skip').onclick = () => p.cmd('skip');
  $('#addr').addEventListener('keydown', (e) => { if (e.key === 'Enter') { p.cmd('go', $('#addr').value); $('#addr').blur(); } });
  $('#addr').addEventListener('focus', () => $('#addr').select());
  p.cmd('state').then((s) => { paint(s); if (s) { active(s.active); $('#banner').hidden = !s.banner; } });
})();
