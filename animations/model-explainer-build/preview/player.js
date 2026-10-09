// Browser player for the assembled explainer: scales the 1920x1080 stage to the window, adds play/pause, speed, scrub and chapter jumps.
(function () {
  var tl = window.__timelines.main, root = document.getElementById('root'), CT = window.CONTENT || {};
  var style = document.createElement('style');
  style.textContent = 'html,body{margin:0;height:100%;background:#0e0e12;overflow:hidden}#root{position:absolute;left:0;top:0;transform-origin:0 0}' +
    '#pl{position:fixed;left:0;right:0;bottom:0;height:46px;background:rgba(14,14,18,.92);color:#eee;font:13px/46px -apple-system,system-ui,sans-serif;display:flex;align-items:center;gap:10px;padding:0 12px;z-index:9;transition:opacity .25s}' +
    '#pl button,#pl select{flex:none;background:#2a2a35;color:#eee;border:0;border-radius:6px;padding:6px 10px;font:inherit;cursor:pointer}#pl input[type=range]{flex:1}#pl .plt{flex:none;min-width:112px;text-align:center;font-variant-numeric:tabular-nums}';
  document.head.appendChild(style);
  var bar = document.createElement('div'); bar.id = 'pl';
  bar.innerHTML = '<button id="pl_pp">Play</button><span class="plt" id="pl_tm">0:00 / 0:00</span><input id="pl_sc" type="range" min="0" max="1000" value="0"><select id="pl_ch"></select><select id="pl_sp"><option value="1">1x</option><option value="2">2x</option><option value="4">4x</option><option value="8">8x</option></select>';
  document.body.appendChild(bar);
  var total = tl.duration();
  function fmt(s) { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function fit() { var w = innerWidth, h = innerHeight - 46, k = Math.min(w / 1920, h / 1080); root.style.transform = 'scale(' + k + ')'; root.style.left = ((w - 1920 * k) / 2) + 'px'; root.style.top = ((h - 1080 * k) / 2) + 'px'; }
  addEventListener('resize', fit); fit();
  var sel = document.getElementById('pl_ch'), acc = 0, starts = [];
  (CT.order || []).forEach(function (cid) { var c = CT.chapters && CT.chapters[cid]; if (!c) return; starts.push([cid, acc, c.title || cid]); acc += (c.card === false ? 0 : 5) + (c.scenes || []).reduce(function (a, s) { return a + s.duration; }, 0); });
  starts.forEach(function (s) { var o = document.createElement('option'); o.value = s[1]; o.textContent = s[0] + ' - ' + s[2]; sel.appendChild(o); });
  sel.onchange = function () { tl.seek(+sel.value); };
  var pp = document.getElementById('pl_pp'), sc = document.getElementById('pl_sc'), tm = document.getElementById('pl_tm');
  pp.onclick = function () { if (tl.paused()) { tl.play(); } else { tl.pause(); } };
  document.getElementById('pl_sp').onchange = function (e) { tl.timeScale(+e.target.value); };
  sc.oninput = function () { tl.pause(); tl.seek(total * sc.value / 1000); };
  addEventListener('keydown', function (e) { if (e.code === 'Space') { e.preventDefault(); pp.onclick(); } else if (e.code === 'ArrowRight') tl.seek(tl.time() + 10); else if (e.code === 'ArrowLeft') tl.seek(Math.max(0, tl.time() - 10)); });
  (function tick() { var cur = 0; for (var i = 0; i < starts.length; i++) if (tl.time() >= starts[i][1]) cur = i; if (document.activeElement !== sel) sel.selectedIndex = cur; pp.textContent = tl.paused() ? 'Play' : 'Pause'; tm.textContent = fmt(tl.time()) + ' / ' + fmt(total); if (document.activeElement !== sc) sc.value = Math.round(1000 * tl.time() / total); requestAnimationFrame(tick); })();
  var hash = +(location.hash || '').slice(1); if (hash) tl.seek(hash);
})();
