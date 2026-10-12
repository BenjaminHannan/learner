/* Builds the whole timeline from content.js. Do not edit per chapter. */
window.__buildMain = function () {
  const CT = window.CONTENT, K = window.Kit, C = K.C;
  const root = document.getElementById('root');
  const chromeEl = document.createElement('div'); chromeEl.id = 'chrome';
  const scenesEl = document.createElement('div'); scenesEl.id = 'scenes';
  root.appendChild(scenesEl); root.appendChild(chromeEl);

  const tl = gsap.timeline({ paused: true });
  const order = (window.ONLY && window.ONLY.length) ? window.ONLY : CT.order;
  const G = CT.global || {};
  const cardSec = G.cardSeconds || 5;
  const FADE = 0.4;
  let t = 0;

  function sceneShell(id, t0, d) {
    const s = document.createElement('div'); s.className = 'scene'; s.id = 'sc-' + id; scenesEl.appendChild(s);
    tl.set(s, { visibility: 'visible' }, t0);
    tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: FADE, ease: 'power1.out', immediateRender: false }, t0);
    tl.to(s, { opacity: 0, duration: FADE, ease: 'power1.in' }, t0 + d - FADE);
    tl.set(s, { visibility: 'hidden' }, t0 + d);
    return s;
  }

  // chapter-wide chrome: a small chip top-left per chapter
  const chips = {};
  const chapterSpans = [];

  order.forEach((cid, ci) => {
    const ch = CT.chapters[cid];
    const build = K.chapters[cid];
    if (!ch) { console.warn('no content for', cid); return; }
    const accent = C[ch.accent] || ch.accent || C.thinker;
    const chStart = t;

    // chip for this chapter
    const chip = document.createElement('div'); chip.className = 'chip-ch';
    chip.innerHTML = '<i></i><span><b></b></span>';
    chip.querySelector('i').style.background = accent;
    chip.querySelector('b').textContent = ch.kicker || ('Part ' + ci);
    chip.querySelector('span').appendChild(document.createTextNode(ch.title ? '  ·  ' + ch.title : ''));
    chromeEl.appendChild(chip); chips[cid] = chip;

    // automatic title card
    if (ch.card !== false) {
      const id = cid + '-card';
      const s = sceneShell(id, t, cardSec);
      s.classList.add('title-card');
      const k = document.createElement('div'); k.className = 'kicker'; k.textContent = ch.kicker || ''; k.style.color = accent; s.appendChild(k);
      const r = document.createElement('div'); r.className = 'rule'; r.style.background = accent; s.appendChild(r);
      const b = document.createElement('div'); b.className = 'big'; b.textContent = ch.title || ''; s.appendChild(b);
      const bl = document.createElement('div'); bl.className = 'blurb'; bl.textContent = ch.blurb || ''; s.appendChild(bl);
      [k, b, r, bl].forEach((e, i) => { gsap.set(e, { autoAlpha: 0, y: 26 }); tl.to(e, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'power2.out' }, t + 0.3 + i * 0.35); });
      t += cardSec;
    }
    const sceneStart = t;
    (ch.scenes || []).forEach((sc) => {
      const d = sc.duration;
      const id = cid + '-' + sc.id;
      const shell = sceneShell(id, t, d);
      const S = new K.Scene(tl, shell, sc, t, d, ch);
      // automatic heading and caption from content
      if (sc.heading) {
        const h = document.createElement('div'); h.className = 'heading'; h.textContent = sc.heading; S.g.appendChild(h);
        gsap.set(h, { autoAlpha: 0, y: 18 }); tl.to(h, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'power2.out' }, t + 0.35);
      }
      if (sc.caption) {
        // caption: one string, or an array of strings / {at:0..1, text} shown one after another in the same box
        const items = (Array.isArray(sc.caption) ? sc.caption : [sc.caption]).map((x) => (typeof x === 'string' ? { text: x } : x));
        const box = document.createElement('div'); box.className = 'caption'; box.style.setProperty('--cap-accent', accent);
        const bar = document.createElement('div'); bar.className = 'cbar'; box.appendChild(bar);
        S.g.appendChild(box);
        const first = 0.6, last = d - FADE - 0.3, n = items.length, span = (last - first) / n;
        S.capTimes = items.map((it, i) => (it.at != null ? t + it.at * d : t + first + i * span));
        items.forEach((it, i) => {
          const tx = document.createElement('div'); tx.className = 'ctext'; tx.textContent = it.text; box.appendChild(tx);
          gsap.set(tx, { autoAlpha: 0, y: 12 });
          const t1 = S.capTimes[i], t2 = i < n - 1 ? S.capTimes[i + 1] : null;
          tl.to(tx, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'power2.out' }, t1);
          if (t2 != null) tl.to(tx, { autoAlpha: 0, duration: 0.3, ease: 'power1.in' }, t2 - 0.3);
        });
        gsap.set(box, { autoAlpha: 0, y: 16 }); tl.to(box, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'power2.out' }, t + 0.5);
      }
      S.accent = accent;
      const fn = build && build.scenes[sc.id];
      if (fn) fn(S); else console.warn('no builder for', id);
      t += d;
    });
    chapterSpans.push({ cid, start: chStart, end: t });
    // chip visible through the chapter (after its title card)
    tl.set(chip, { visibility: 'visible' }, sceneStart);
    tl.to(chip, { opacity: 1, duration: 0.4 }, sceneStart);
    tl.to(chip, { opacity: 0, duration: 0.3 }, t - 0.3);
    tl.set(chip, { visibility: 'hidden' }, t);
  });

  // optional end card
  if (G.endCard && !(window.ONLY && window.ONLY.length)) {
    const d = G.endCard.duration || 8;
    const s = sceneShell('end', t, d);
    s.classList.add('title-card');
    const b = document.createElement('div'); b.className = 'big'; b.textContent = G.endCard.title || ''; s.appendChild(b);
    const bl = document.createElement('div'); bl.className = 'blurb'; bl.textContent = G.endCard.blurb || ''; s.appendChild(bl);
    [b, bl].forEach((e, i) => { gsap.set(e, { autoAlpha: 0, y: 26 }); tl.to(e, { autoAlpha: 1, y: 0, duration: 0.6 }, t + 0.3 + i * 0.4); });
    t += d;
  }

  // progress bar across the whole video (global positions even when only some chapters are built, so chunked renders still line up)
  const pbar = document.createElement('div'); pbar.id = 'pbar';
  const pfill = document.createElement('div'); pfill.id = 'pfill';
  pbar.appendChild(pfill); chromeEl.appendChild(pbar);
  const gStart = {}; let gAcc = 0;
  CT.order.forEach((cid) => { const ch = CT.chapters[cid]; if (!ch) return; gStart[cid] = gAcc; gAcc += (ch.card === false ? 0 : cardSec) + (ch.scenes || []).reduce((a, s) => a + s.duration, 0); });
  const gTotal = gAcc + (G.endCard ? (G.endCard.duration || 8) : 0);
  CT.order.forEach((cid, i) => { if (i === 0 || gStart[cid] == null) return; const k = document.createElement('div'); k.className = 'ptick'; k.style.left = (1920 * gStart[cid] / gTotal) + 'px'; pbar.appendChild(k); });
  const firstId = order.find((cid) => gStart[cid] != null), lastId = order.slice().reverse().find((cid) => gStart[cid] != null);
  const pa = firstId ? gStart[firstId] / gTotal : 0;
  const pb = lastId ? Math.min(1, (gStart[lastId] + (t - (chapterSpans.length ? chapterSpans[chapterSpans.length - 1].start : 0))) / gTotal) : 1;
  const fullRun = !(window.ONLY && window.ONLY.length);
  tl.fromTo(pfill, { scaleX: fullRun ? 0 : pa }, { scaleX: fullRun ? 1 : pb, duration: t, ease: 'none', immediateRender: false }, 0);

  window.__TOTAL = t;
  return tl;
};
