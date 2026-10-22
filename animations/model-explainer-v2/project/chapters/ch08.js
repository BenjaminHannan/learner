/* Chapter 8: Practice, one small nudge at a time. Every word and number comes from content/ch08.json (S.c). */
Kit.chapter('ch08', function (Ch) {
  const C = Kit.C;
  const chipW = (s) => Math.round(String(s).length * 15.5 + 70);   // estimate, to centre a chip under a box
  const mono = (b) => { b.querySelectorAll('.lab').forEach((n) => n.classList.add('mono')); return b; };
  const dashed = (b) => { b.style.borderStyle = 'dashed'; return b; };

  // A "settings" picture: a round face with one needle. The needle is rotated with absolute values only.
  function dial(S, o) {
    const wrap = S.card({ x: o.x - o.r, y: o.y - o.r, w: o.r * 2, h: o.r * 2, r: o.r, color: o.color || C.learned });
    const n = document.createElement('div');
    n.style.cssText = 'position:absolute;left:calc(50% - 4px);top:12%;width:8px;height:38%;border-radius:4px;background:' + (o.color || C.learned);
    wrap.appendChild(n);
    gsap.set(n, { rotation: o.a0, transformOrigin: '50% 100%' });
    const hub = document.createElement('div');
    hub.style.cssText = 'position:absolute;left:calc(50% - 9px);top:calc(50% - 9px);width:18px;height:18px;border-radius:50%;background:' + (o.color || C.learned);
    wrap.appendChild(hub);
    return { wrap, needle: n };
  }
  function turn(S, d, a1, t, dur) { S.tl.to(d.needle, { rotation: a1, duration: dur || 2, ease: 'power2.inOut' }, t); }

  // ---------------------------------------------------------------- s01
  Ch.scene('s01', function (S) {
    const L = S.c.labels;
    const m = S.modelMap({ x: 100, y: 320, w: 1720, h: 210 });
    const order = ['reader', 'thinker', 'stop', 'talker', 'calc'];
    let t = S.at(0.05);
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.3); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.3 + 0.3, 0.4); });
    const chips = {};
    order.forEach((k, i) => {
      const lab = L[k], w = chipW(lab), x = m.colC[k] - w / 2;
      if (k === 'reader') chips[k] = S.chip('frozen', { color: C.reader, label: lab, x, y: 575 });
      else if (k === 'calc') chips[k] = S.chip('hand', { label: lab, x, y: 575 });
      else if (k === 'stop') chips[k] = S.chip('untested', { label: lab, x, y: 575 });   // built, never run: amber
      else chips[k] = S.chip('learned', { label: lab, x, y: 575 });
    });
    const t0 = S.capAt(0), t1 = S.capAt(1);
    ['thinker', 'stop', 'talker'].forEach((k, i) => S.pop(chips[k], t0 + 0.6 + i * 0.5));
    S.pop(chips.reader, t1 + 0.4);
    S.pop(chips.calc, t1 + 1.0);
  });

  // ---------------------------------------------------------------- s02
  Ch.scene('s02', function (S) {
    const L = S.c.labels;
    const svg = S.svg();
    const q = mono(S.box({ x: 120, y: 300, w: 520, h: 130, label: L.q, color: C.ink, size: 46 }));
    const qchip = S.chip('placeholder', { x: 120, y: 452, label: L.pic });
    const mdl = S.box({ x: 760, y: 300, w: 400, h: 130, label: L.model, color: C.learned, size: 46, border: 5 });
    const tr = mono(S.box({ x: 1280, y: 300, w: 520, h: 130, label: L.try, color: C.untested, size: 42 }));
    const key = mono(S.box({ x: 1280, y: 480, w: 520, h: 120, label: L.key, color: C.tested, size: 42 }));
    const a1 = S.arrow(svg, 650, 365, 750, 365, { color: C.soft });
    const a2 = S.arrow(svg, 1170, 365, 1270, 365, { color: C.soft });
    const chk = S.path(svg, [[1270, 540], [960, 540], [960, 430]], { color: C.tested, width: 6 });   // tip touches the bottom edge of the model box (y 300 + h 130)
    const nud = S.arrow(svg, 780, 430, 780, 634, { color: C.learned });   // from the model box down onto the bracket over the four dials
    const brk = S.path(svg, [[642, 650], [642, 634], [1238, 634], [1238, 650]], { color: C.learned, width: 5, head: 0 });
    const nudT = S.text(L.nudge, { x: 560, y: 505, w: 200, size: 44, weight: 700, align: 'right', color: C.learned });
    const dx = [700, 860, 1020, 1180], a0 = [-55, 20, -25, 45], a1s = [-43, 9, -12, 33];
    const ds = dx.map((x, i) => dial(S, { x, y: 715, r: 58, a0: a0[i] }));
    const setT = S.text(L.settings, { x: 640, y: 784, w: 600, size: 36, weight: 600, align: 'center', color: C.soft });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(q, t0); S.pop(qchip, t0 + 0.5);
    S.draw(a1, t0 + 0.8, 0.5); S.show(mdl, t0 + 1.2);
    S.draw(a2, t0 + 1.8, 0.5); S.show(tr, t0 + 2.3);
    ds.forEach((d, i) => S.show(d.wrap, t0 + 1.6 + i * 0.25, { dur: 0.4 }));
    S.show(setT, t0 + 2.6);
    S.show(key, t1); S.draw(chk, t1 + 0.6, 1.4);
    S.show(nudT, t2); S.draw(brk, t2 + 0.2, 0.6); S.draw(nud, t2 + 0.3, 0.8);
    ds.forEach((d, i) => turn(S, d, a1s[i], t2 + 1.2 + i * 0.35, 1.6));
  });

  // ---------------------------------------------------------------- s03
  Ch.scene('s03', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const cells = [];
    for (let r = 0; r < 16; r++) for (let q = 0; q < 16; q++) {
      const e = S.card({ x: 160 + q * 32, y: 225 + r * 32, w: 28, h: 28, r: 6, color: C.learned, fill: '#DCE7FD' });
      e.style.borderWidth = '2px'; cells.push(e);
    }
    const chip = S.chip('tested', { x: 160, y: 762, label: L.chip });
    const updV = S.text('', { x: 800, y: 232, w: 420, size: 96, weight: 800, color: C.learned });
    const updL = S.text(L.updates, { x: 1240, y: 268, w: 500, size: 46, weight: 600 });
    const rowV = S.text('', { x: 800, y: 372, w: 420, size: 96, weight: 800 });
    const rowL = S.text(L.rows, { x: 1240, y: 408, w: 560, size: 46, weight: 600 });
    const drwV = S.text('', { x: 800, y: 512, w: 640, size: 96, weight: 800, color: C.warn });
    const drwL = S.text(L.draws, { x: 1480, y: 548, w: 360, size: 46, weight: 600 });
    const mult = S.text(L.mult, { x: 800, y: 630, w: 700, size: 36, weight: 600, italic: true, color: C.soft });
    const div = S.text(L.div, { x: 800, y: 700, w: 960, size: 38, weight: 600 });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.sweep(cells, t0, 1.6);
    S.show(rowV, t0, { dur: 0.4 }); S.show(rowL, t0 + 0.1, { dur: 0.4 });
    S.count(rowV, { from: 0, to: N.rows, comma: true }, t0 + 0.2, 1.6, 'none');
    S.pop(chip, t1 + 0.2);
    S.show(updV, t1, { dur: 0.4 }); S.show(updL, t1 + 0.1, { dur: 0.4 });
    S.count(updV, { from: 0, to: N.updates, comma: true }, t1 + 0.3, 3.5, 'power1.inOut');
    S.show(drwV, t2, { dur: 0.4 }); S.show(drwL, t2 + 0.1, { dur: 0.4 });
    S.count(drwV, { from: 0, to: N.draws, comma: true }, t2 + 0.2, 2.8, 'power1.inOut');
    S.show(mult, t2 + 1.2);
    S.show(div, t2 + 3.6);
  });

  // ---------------------------------------------------------------- s04
  Ch.scene('s04', function (S) {
    const L = S.c.labels;
    const svg = S.svg();
    const ax = S.arrow(svg, 160, 700, 830, 700, { color: C.soft, width: 5, head: 18 });
    const ay = S.arrow(svg, 160, 700, 160, 250, { color: C.soft, width: 5, head: 18 });
    const yl = S.text(L.y, { x: 190, y: 218, w: 380, size: 34, weight: 600, color: C.soft });
    const pic = S.chip('placeholder', { x: 640, y: 214, label: L.pic });
    const pts = [[160, 700], [220, 300]];
    for (let i = 1; i <= 24; i++) { const u = i / 24, lr = 0.1 + 0.45 * (1 + Math.cos(Math.PI * u)); pts.push([Math.round(220 + u * 560), Math.round(700 - 400 * lr)]); }
    const lc = S.path(svg, pts, { color: C.learned, width: 8, head: 0 });
    const wl = S.text(L.warm, { x: 170, y: 712, w: 220, size: 30, weight: 600, color: C.soft });
    const xl = S.text(L.x1, { x: 540, y: 712, w: 290, size: 30, weight: 600, align: 'right', color: C.soft });
    const pk = S.text(L.peak, { x: 240, y: 252, w: 200, size: 36, weight: 800, color: C.learned });
    const tn = S.text(L.tenth, { x: 800, y: 628, w: 230, size: 30, weight: 700, color: C.learned });
    const ys = [250, 352, 454, 556, 658];
    const names = ['adamw', 'clip', 'bf16', 'shuf', 'rand'];
    const bx = names.map((k, i) => S.box({ x: 1060, y: ys[i], w: 740, h: 84, label: L[k], color: i < 2 ? C.learned : C.soft, size: 38 }));
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.draw(ax, t0, 0.8); S.draw(ay, t0 + 0.2, 1.0); S.show(yl, t0 + 0.9);
    S.show(bx[0], t0 + 0.6); S.show(bx[1], t0 + 1.6);
    S.pop(pic, t1); S.show(xl, t1 + 0.1); S.show(wl, t1 + 0.4);
    S.draw(lc, t1 + 0.3, 3.0);
    S.show(pk, t1 + 0.9); S.show(tn, t1 + 3.0);
    S.show(bx[2], t2); S.show(bx[3], t2 + 0.9); S.show(bx[4], t2 + 1.8);
  });

  // ---------------------------------------------------------------- s05
  Ch.scene('s05', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const svg = S.svg();
    const W = 1600, wOwn = Math.round(W * N.own / 100), wWeb = W - wOwn;
    const poolT = S.text(L.pool, { x: 160, y: 214, w: 900, size: 46, weight: 800 });
    const chip = S.chip('tested', { x: 1300, y: 216, label: L.chip });
    const bOwn = S.bar({ x: 160, y: 300, w: wOwn, h: 150, value: 100, max: 100, color: C.learned });
    const bWeb = S.bar({ x: 160 + wOwn, y: 300, w: wWeb, h: 150, value: 100, max: 100, color: C.soft });
    const ownP = S.text('', { x: 160, y: 312, w: wOwn, size: 72, weight: 800, align: 'center', color: '#fff' });
    const ownL = S.text(L.own, { x: 160, y: 402, w: wOwn, size: 34, weight: 600, align: 'center', color: '#fff' });
    const webP = S.text('', { x: 160 + wOwn, y: 312, w: wWeb, size: 72, weight: 800, align: 'center', color: '#fff' });
    const webL = S.text(L.web, { x: 160 + wOwn, y: 402, w: wWeb, size: 34, weight: 600, align: 'center', color: '#fff' });
    // the three row counts sit in one full-width panel that says they are ROWS (the bar above is a share of PIECES)
    const panel = S.card({ x: 160, y: 514, w: 1600, h: 276, color: C.learned });
    const down = S.arrow(svg, 464, 458, 464, 514, { color: C.learned, width: 5, head: 16 });
    const rh = S.text(L.rowsHead, { x: 190, y: 538, w: 1540, size: 38, weight: 700, color: C.learned });
    const bxs = [[L.skills, L.skillsN], [L.english, L.englishN], [L.teach, L.teachN]].map((p, i) =>
      S.box({ x: 190 + i * 525, y: 604, w: 490, h: 150, label: p[0], sub: p[1], color: C.learned, size: 32, subSize: 34 }));
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(poolT, t0); S.show(bOwn.track, t0 + 0.3); S.show(bWeb.track, t0 + 0.5); S.pop(chip, t0 + 1.0);
    S.grow(bOwn, t1, 1.6); S.grow(bWeb, t1 + 0.5, 1.6);
    S.show(ownP, t1 + 0.2, { dur: 0.3 }); S.show(ownL, t1 + 0.4, { dur: 0.3 });
    S.count(ownP, { from: 0, to: N.own, suf: '%' }, t1 + 0.3, 1.6);
    S.show(webP, t1 + 0.7, { dur: 0.3 }); S.show(webL, t1 + 0.9, { dur: 0.3 });
    S.count(webP, { from: 0, to: N.web, suf: '%' }, t1 + 0.8, 1.6);
    S.draw(down, t2, 0.5); S.show(panel, t2 + 0.4); S.show(rh, t2 + 0.8);
    S.show(bxs[0], t2 + 1.4); S.show(bxs[1], t2 + 2.3); S.show(bxs[2], t2 + 3.5);
    S.pulse(bxs[2], t2 + 4.3);
  });

  // ---------------------------------------------------------------- s06
  Ch.scene('s06', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const row = document.createElement('div');
    row.style.cssText = 'position:absolute;left:150px;top:250px;display:flex;align-items:flex-start;gap:18px;font-size:56px;font-weight:600;white-space:nowrap;color:' + C.ink;
    S.g.appendChild(row);
    const mk = (txt) => { const s = document.createElement('span'); s.textContent = txt; s.style.lineHeight = '84px'; row.appendChild(s); return s; };
    mk(L.pre);
    const blank = document.createElement('span');
    blank.style.cssText = 'position:relative;display:inline-block;min-width:330px;height:128px;border:4px dashed ' + C.untested + ';border-radius:14px;text-align:center;line-height:76px;padding-top:0;font-weight:800;color:' + C.tested;
    row.appendChild(blank);
    const word = document.createElement('span'); word.textContent = L.word; blank.appendChild(word); gsap.set(word, { autoAlpha: 0 });
    const rng = document.createElement('div');
    rng.style.cssText = 'position:absolute;left:0;top:80px;width:100%;text-align:center;font-size:30px;font-weight:600;line-height:1.2;color:' + C.soft;
    rng.textContent = N.lo + '–' + N.hi; blank.appendChild(rng);
    mk(L.post);
    gsap.set(row, { autoAlpha: 0 });
    const ex = S.chip('placeholder', { x: 150, y: 400, label: L.ex });
    const hb = S.hbars({ x: 140, y: 490, w: 760, labelW: 330, rowH: 60, gap: 36, max: N.b2, dec: 0, valueSize: 46, labelSize: 38, valueW: 150, items: [
      { label: L.b1, value: N.b1, color: C.tested, dec: 0 }, { label: L.b2, value: N.b2, color: C.untested, dec: 0 }] });
    const c1 = S.chip('tested', { x: 1440, y: 497, label: L.b1chip });
    const c2 = S.chip('untested', { x: 1440, y: 593, label: L.b2chip });
    const wl = S.text(L.w, { x: 140, y: 706, w: 306, size: 38, weight: 700, align: 'right' });
    const wv = S.text('', { x: 470, y: 692, w: 300, size: 64, weight: 800 });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(row, t0); S.pop(ex, t0 + 0.8);
    S.tl.to(word, { autoAlpha: 1, duration: 0.5 }, t0 + 3.5);
    S.tint(blank, t0 + 3.5, { border: C.tested, dur: 0.5 });
    const e = hb.reveal(t1);
    S.pop(c1, e + 0.1); S.pop(c2, e + 0.6);
    S.show(wl, t2); S.show(wv, t2 + 0.2, { dur: 0.3 });
    S.count(wv, { from: 0, to: N.w, dec: 1 }, t2 + 0.3, 1.4);
  });

  // ---------------------------------------------------------------- s07
  Ch.scene('s07', function (S) {
    const L = S.c.labels;
    const xs = [380, 860, 1340], W = 420;
    const outline = dashed(S.card({ x: 840, y: 222, w: 940, h: 590, r: 24, color: C.talker, fill: 'transparent' }));
    const svg = S.svg();
    const kn = S.text(L.key, { x: 80, y: 390, w: 270, size: 34, weight: 700, align: 'right', color: C.tested });
    const wn = S.text(L.cw, { x: 80, y: 550, w: 270, size: 34, weight: 700, align: 'right', color: C.call });
    const heads = xs.map((x, i) => S.box({ x, y: 235, w: W, h: 78, label: L.round + ' ' + [L.r1, L.r2, L.r3][i], color: C.thinker, size: 38 }));
    const keys = xs.map((x, i) => mono(S.box({ x, y: 360, w: W, h: 96, label: [L.c1, L.c2, L.c3][i], color: C.tested, size: 36 })));
    const wr = xs.map((x, i) => mono(S.box({ x, y: 520, w: W, h: 96, label: [L.c1, L.c2, L.c3][i], color: C.call, size: 36 })));
    const ar = xs.map((x) => S.arrow(svg, x + W / 2, 456, x + W / 2, 520, { color: C.soft, width: 5, head: 16 }));
    const clT = S.text(L.callLoss, { x: 80, y: 470, w: 270, size: 34, weight: 700, align: 'right', color: C.call });
    const ans = S.box({ x: 1340, y: 690, w: W, h: 90, label: L.ans, color: C.talker, size: 38 });
    const alT = S.text(L.ansLoss, { x: 800, y: 710, w: 500, size: 40, weight: 700, align: 'right', color: C.talker });
    const ex = S.chip('placeholder', { x: 80, y: 690, label: L.ex });
    const nr = S.chip('untested', { x: 80, y: 748, label: L.chip });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    heads.forEach((h, i) => S.show(h, t0 + i * 0.4));
    S.show(kn, t0 + 1.4);
    keys.forEach((k, i) => S.show(k, t0 + 1.6 + i * 0.5));
    S.pop(ex, t0 + 0.4); S.pop(nr, t0 + 1.0);
    S.show(wn, t1);
    wr.forEach((w, i) => { S.show(w, t1 + 0.3 + i * 0.5); S.draw(ar[i], t1 + 0.1 + i * 0.5, 0.4); });
    S.show(clT, t1 + 0.4);
    S.pulse(wr[2], t1 + 2.6);
    S.show(outline, t2); S.show(ans, t2 + 0.6); S.show(alT, t2 + 0.8);
  });

  // ---------------------------------------------------------------- s08
  Ch.scene('s08', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const svg = S.svg();
    const l1 = S.text(L.lane1, { x: 80, y: 272, w: 250, size: 42, weight: 800, color: C.learned });
    const kc = S.box({ x: 340, y: 245, w: 270, h: 100, label: L.k, color: C.tested, size: 38 });
    const r1 = S.box({ x: 680, y: 245, w: 340, h: 100, label: L.r, color: C.calc, size: 34 });
    const d1 = S.box({ x: 1090, y: 245, w: 190, h: 100, label: L.rd, color: C.reader, size: 36 });
    const n1 = S.box({ x: 1350, y: 245, w: 300, h: 100, label: L.n, color: C.thinker, size: 38 });
    const g1 = dashed(S.box({ x: 340, y: 372, w: 340, h: 76, label: L.g, color: C.call, size: 32, border: 3 }));
    const a1 = S.arrow(svg, 618, 295, 672, 295, { color: C.soft, width: 5, head: 16 });
    const a2 = S.arrow(svg, 1028, 295, 1082, 295, { color: C.soft, width: 5, head: 16 });
    const a5 = S.arrow(svg, 1288, 295, 1342, 295, { color: C.soft, width: 5, head: 16 });
    const l2 = S.text(L.lane2, { x: 80, y: 542, w: 250, size: 42, weight: 800 });
    const oc = S.box({ x: 340, y: 515, w: 270, h: 100, label: L.o, color: C.call, size: 38 });
    const r2 = S.box({ x: 680, y: 515, w: 340, h: 100, label: L.r, color: C.calc, size: 34 });
    const d2 = S.box({ x: 1090, y: 515, w: 190, h: 100, label: L.rd, color: C.reader, size: 36 });
    const n2 = S.box({ x: 1350, y: 515, w: 300, h: 100, label: L.n, color: C.thinker, size: 38 });
    const a3 = S.arrow(svg, 618, 565, 672, 565, { color: C.soft, width: 5, head: 16 });
    const a4 = S.arrow(svg, 1028, 565, 1082, 565, { color: C.soft, width: 5, head: 16 });
    const a6 = S.arrow(svg, 1288, 565, 1342, 565, { color: C.soft, width: 5, head: 16 });
    const nl = S.text(L.none, { x: 80, y: 738, w: 250, size: 36, weight: 700 });
    const nb = S.bar({ x: 340, y: 728, w: 900, h: 56, value: N.share, max: 100, color: C.soft });
    const nv = S.text('', { x: 1264, y: 722, w: 300, size: 52, weight: 800 });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(l1, t0); S.show(kc, t0 + 0.4); S.draw(a1, t0 + 0.9, 0.5); S.show(r1, t0 + 1.3);
    S.draw(a2, t0 + 1.8, 0.5); S.show(d1, t0 + 2.0); S.draw(a5, t0 + 2.3, 0.4); S.show(n1, t0 + 2.6); S.show(g1, t0 + 3.2);
    S.show(l2, t1); S.show(oc, t1 + 0.4); S.draw(a3, t1 + 0.9, 0.5); S.show(r2, t1 + 1.3);
    S.draw(a4, t1 + 1.8, 0.5); S.show(d2, t1 + 2.0); S.draw(a6, t1 + 2.3, 0.4); S.show(n2, t1 + 2.6);
    S.show(nl, t2); S.show(nb.track, t2 + 0.2); S.grow(nb, t2 + 0.6, 1.8);
    S.show(nv, t2 + 0.6, { dur: 0.3 });
    S.count(nv, { from: 0, to: N.share, dec: 1, suf: '%' }, t2 + 0.7, 1.8);
  });

  // ---------------------------------------------------------------- s09
  Ch.scene('s09', function (S) {
    const L = S.c.labels, N = S.c.nums, I = S.c.illustration;
    const xs = [100, 700, 1300], W = 520;
    const cards = xs.map((x) => S.card({ x, y: 225, w: W, h: 548 }));
    const svg = S.svg();   // made after the cards, so the cap line and the wall sit on top of them
    const ttl = ['c1', 'c2', 'c3'].map((k, i) => S.text(L[k], { x: xs[i] + 30, y: 250, w: 460, size: 42, weight: 800 }));
    // rule 1: an answer's letters stay under the cap
    const strip = S.vec({ x: 130, y: 350, n: 7, cell: 40, gap: 6, color: C.learned, seed: 5 });
    const capLine = S.path(svg, [[470, 335], [470, 405]], { color: C.call, width: 7, head: 0 });
    const c1b = S.text(L.c1b, { x: 130, y: 430, w: 460, size: 34, weight: 700 });
    const c1chip = S.chip('untested', { x: 130, y: 535, label: L.c1chip });
    const c1a = S.text(L.c1a, { x: 130, y: 625, w: 460, size: 32, weight: 500 });
    // rule 2: exam questions kept apart
    const kv = S.text('', { x: 730, y: 340, w: 460, size: 110, weight: 800, align: 'center', color: C.learned });
    const left = S.vec({ x: 760, y: 560, n: 5, cell: 34, gap: 6, color: C.learned, seed: 11 });
    const wall = S.path(svg, [[980, 530], [980, 610]], { color: C.soft, width: 6, head: 0 });
    const right = S.vec({ x: 1010, y: 560, n: 3, cell: 34, gap: 6, color: C.calc, seed: 21 });
    // rule 3: web text scanned against exam sets
    const web = S.vec({ x: 1330, y: 360, n: 11, cell: 36, gap: 4, color: C.soft, seed: 31 });
    const scan = S.box({ x: 1322, y: 351, w: 92, h: 54, color: C.untested, fill: 'transparent', r: 10, border: 4 });
    const c3chip = S.chip('placeholder', { x: 1330, y: 470, label: L.c3chip });   // a scan that has not run (the hash file waits on a Mac job): grey
    // the squares are drawings, not counts: one chip and a colour key under the cards
    const lg = S.chip('placeholder', { x: 100, y: 786, label: I.pic });
    const keyT = (str, x, col) => S.text(str, { x, y: 796, w: 420, size: 30, weight: 700, color: col, nowrap: true });
    const kRed = keyT(I.cap, 390, C.call), kBlue = keyT(I.blue, 715, C.learned), kGrey = keyT(I.grey, 990, C.soft), kOr = keyT(I.orange, 1415, C.untested);
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(cards[0], t0); S.show(ttl[0], t0 + 0.3); S.show(strip, t0 + 0.8); S.draw(capLine, t0 + 1.4, 0.4);
    S.pop(lg, t0 + 1.0); S.show(kRed, t0 + 1.6); S.show(kBlue, t0 + 1.9);
    S.show(c1b, t0 + 2.0); S.pop(c1chip, t0 + 2.6); S.show(c1a, t0 + 3.2);
    S.show(cards[1], t1); S.show(ttl[1], t1 + 0.3);
    S.show(kv, t1 + 0.8, { dur: 0.3 }); S.count(kv, { from: 0, to: N.kept, comma: true }, t1 + 0.9, 2.2);
    S.show(left, t1 + 3.2); S.draw(wall, t1 + 3.8, 0.4); S.show(right, t1 + 4.4); S.show(kGrey, t1 + 4.8);
    S.show(cards[2], t2); S.show(ttl[2], t2 + 0.3); S.show(web, t2 + 0.8); S.show(scan, t2 + 1.4);
    S.show(kOr, t2 + 1.6); S.move(scan, t2 + 2.1, 3.2, { x: 340, ease: 'power1.inOut' });
    S.pop(c3chip, t2 + 5.5);
  });

  // ---------------------------------------------------------------- s10
  Ch.scene('s10', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const chip = S.chip('tested', { x: 120, y: 216, label: L.chip });
    const hb = S.hbars({ x: 120, y: 300, w: 800, labelW: 380, rowH: 90, gap: 40, max: 7, dec: 2, valueSize: 56, labelSize: 42, valueW: 380, items: [
      { label: L.ours, value: N.oursH, color: C.learned, suf: ' ' + L.hrs },
      { label: L.plain, value: N.plainH, color: C.soft, suf: ' ' + L.hrs }] });
    const rv = S.text('', { x: 500, y: 556, w: 330, size: 120, weight: 800, color: C.warn });
    const rl = S.text(L.ratio, { x: 850, y: 600, w: 900, size: 42, weight: 600 });
    const pc = S.chip('placeholder', { x: 120, y: 735, label: L.plan });
    const wk = S.text(L.weeks, { x: 360, y: 722, w: 1000, size: 50, weight: 700 });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2), t3 = S.capAt(3);
    // one hbars row per caption (ours first, then plain)
    const rowIn = (i, t, dur) => {
      const r = hb.rows[i];
      S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 });
      S.grow(r.b, t + 0.3, dur, r.val, { dec: 2, suf: r.it.suf, comma: true });
    };
    S.pop(chip, t0);
    rowIn(0, t0 + 0.4, 2.4);
    rowIn(1, t1 + 0.4, 1.2);
    S.show(rv, t2, { dur: 0.3 }); S.show(rl, t2 + 0.2);
    S.count(rv, { from: 0, to: N.ratio, dec: 1, suf: '×' }, t2 + 0.3, 1.8);
    S.pop(pc, t3); S.show(wk, t3 + 0.4);
  });

  // ---------------------------------------------------------------- s11
  Ch.scene('s11', function (S) {
    const L = S.c.labels;
    const svg = S.svg();
    const xs = [200, 520, 840, 1160, 1480], bw = 220;
    const labs = [L.r1, L.r2, L.r3, L.dots, L.r32];
    const boxes = xs.map((x, i) => S.box({ x, y: 380, w: bw, h: 140, label: labs[i], color: C.thinker, size: 56, border: 5 }));
    const rl = S.text(L.rounds, { x: 30, y: 432, w: 150, size: 34, weight: 600, align: 'right', color: C.soft });
    const fwd = S.arrow(svg, 200, 330, 1700, 330, { color: C.soft, width: 6 });
    const fwdT = S.text(L.fwd, { x: 200, y: 262, w: 1500, size: 40, weight: 700, align: 'center', color: C.soft });
    const link = [0, 1, 2, 3].map((i) => S.arrow(svg, xs[i] + bw + 8, 450, xs[i + 1] - 8, 450, { color: C.thinker, width: 5, head: 16 }));
    const back = [3, 2, 1, 0].map((i) => S.curve(svg, xs[i + 1] + 110, 528, xs[i] + 110, 528, { color: C.learned, width: 6, bend: 80 }));
    const backT = S.text(L.back, { x: 200, y: 604, w: 1500, size: 44, weight: 700, align: 'center', color: C.learned });
    // key for the cream fill: only the later rounds (rounds 9 to 32 in the code; '...' stands for 4 to 31) redo their work
    const sw = S.box({ x: 80, y: 690, w: 44, h: 44, color: C.thinker, fill: '#FFF1D6', r: 10, border: 4 });
    const swT = S.text(L.redo, { x: 140, y: 692, w: 1200, size: 34, weight: 600, color: C.ink });
    // the outlined box is round 32: the design allows up to 32 rounds (the 16-round probe is a caption fact)
    const c32 = S.text(L.cap32, { x: 1598, y: 536, w: 240, size: 30, weight: 700, color: C.warn, nowrap: true });
    const pic = S.chip('placeholder', { x: 80, y: 770, label: L.pic });
    const pr = S.chip('tested', { x: 380, y: 770, label: L.probe });
    const nr = S.chip('untested', { x: 900, y: 770, label: L.chip });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(rl, t0); S.draw(fwd, t0 + 0.2, 1.4); S.show(fwdT, t0 + 0.4);
    boxes.forEach((b, i) => { S.show(b, t0 + 0.6 + i * 0.35); if (i < 4) S.draw(link[i], t0 + 0.9 + i * 0.35, 0.3); });
    S.pop(pic, t0 + 2.6);
    back.forEach((b, i) => S.draw(b, t0 + 3.8 + i * 0.8, 0.7));
    S.show(backT, t0 + 7.2);
    S.pop(nr, t1);
    S.show(sw, t1 + 0.4); S.show(swT, t1 + 0.6);
    [3, 4].forEach((i, j) => S.tint(boxes[i], t1 + 0.8 + j * 0.4, { fill: '#FFF1D6', dur: 0.4 }));
    S.tint(boxes[4], t2, { border: C.warn, dur: 0.5 });
    S.show(c32, t2 + 0.3); S.pop(pr, t2 + 1.2);
    S.pulse(boxes[4], t2 + 0.6);
  });

  // ---------------------------------------------------------------- s12
  Ch.scene('s12', function (S) {
    const L = S.c.labels;
    const svg = S.svg();
    const pl = S.card({ x: 140, y: 230, w: 700, h: 470 });
    const pr = S.card({ x: 1080, y: 230, w: 700, h: 470, color: C.learned });
    const A0 = [-60, 25, -10, 80, -35, 50], A1 = [20, -45, 55, -20, 35, -70];
    const off = [[130, 120], [350, 120], [570, 120], [130, 330], [350, 330], [570, 330]];
    const dl = off.map((p, i) => dial(S, { x: 140 + p[0], y: 230 + p[1], r: 70, a0: A0[i], color: C.placeholder }));
    const dr = off.map((p, i) => dial(S, { x: 1080 + p[0], y: 230 + p[1], r: 70, a0: A0[i], color: C.learned }));
    const bt = S.text(L.before, { x: 140, y: 718, w: 700, size: 44, weight: 700, align: 'center' });
    const at = S.text(L.after, { x: 1080, y: 718, w: 700, size: 44, weight: 700, align: 'center', color: C.learned });
    const arr = S.arrow(svg, 840, 465, 1080, 465, { color: C.soft });
    const pic = S.chip('placeholder', { x: 832, y: 786, label: L.pic });
    const t0 = S.capAt(0), t1 = S.capAt(1);
    S.show(pl, t0); dl.forEach((d, i) => S.show(d.wrap, t0 + 0.4 + i * 0.25, { dur: 0.4 }));
    S.show(bt, t0 + 0.6); S.pop(pic, t0 + 1.2);
    S.draw(arr, t1, 0.6); S.show(pr, t1 + 0.4); S.show(at, t1 + 0.6);
    dr.forEach((d, i) => S.show(d.wrap, t1 + 0.8 + i * 0.2, { dur: 0.4 }));
    dr.forEach((d, i) => turn(S, d, A1[i], t1 + 2.4 + i * 0.2, 2.2));
  });

  // ---------------------------------------------------------------- s13
  Ch.scene('s13', function (S) {
    const L = S.c.labels, N = S.c.nums, I = S.c.illustration;
    const xs = [100, 700, 1300], W = 520;
    const cards = xs.map((x) => S.card({ x, y: 230, w: W, h: 570 }));
    const svg = S.svg();   // made after the cards, so the wall line sits on top of them
    const ttl = ['t1', 't2', 't3'].map((k, i) => S.text(L[k], { x: xs[i], y: 256, w: W, size: 46, weight: 800, align: 'center' }));
    const unit = (str, x, y) => S.text(str, { x, y, w: W, size: 34, weight: 600, align: 'center', color: C.soft });
    // card 1: the loop (each number has its unit under it)
    const d1 = dial(S, { x: 360, y: 402, r: 78, a0: -70 });
    const uV = S.text('', { x: 100, y: 500, w: W, size: 72, weight: 800, align: 'center', color: C.learned });
    const uU = unit(L.upd, 100, 590);
    const rV = S.text('', { x: 100, y: 640, w: W, size: 72, weight: 800, align: 'center' });
    const rU = unit(L.rpu, 100, 730);
    // card 2: the rows (three rows of squares, labelled in caption order, and the exam rows kept aside)
    const s1 = S.vec({ x: 712, y: 340, n: 9, cell: 30, gap: 4, color: C.learned, seed: 2 });
    const s2 = S.vec({ x: 712, y: 384, n: 9, cell: 30, gap: 4, color: C.learned, seed: 4 });
    const s3 = S.vec({ x: 712, y: 428, n: 9, cell: 30, gap: 4, color: C.soft, seed: 6 });
    const rl = [[L.rCode, 336], [L.rTeach, 380], [L.rWeb, 424]].map((p) => S.text(p[0], { x: 1028, y: p[1], w: 180, size: 30, weight: 600, color: C.soft, nowrap: true }));
    const wall = S.path(svg, [[760, 498], [1160, 498]], { color: C.soft, width: 5, head: 0 });
    const kV = S.text('', { x: 700, y: 512, w: W, size: 84, weight: 800, align: 'center', color: C.ink });
    const kU = unit(L.kept, 700, 612);
    const pc = S.chip('placeholder', { x: 700 + Math.round((W - chipW(I.pic)) / 2), y: 700, label: I.pic });
    // card 3: the cost (same green chip as scene s10: the bars are the faster 3M copy)
    const xV = S.text('', { x: 1300, y: 326, w: W, size: 130, weight: 800, align: 'center', color: C.warn });
    const xU = S.text(L.x, { x: 1300, y: 478, w: W, size: 36, weight: 600, align: 'center', color: C.soft });
    const oL = S.text(L.ours, { x: 1360, y: 536, w: 400, size: 30, weight: 700, color: C.learned });
    const b1 = S.bar({ x: 1360, y: 574, w: 400, h: 40, value: N.ratio, max: N.ratio, color: C.learned });
    const pL = S.text(L.plain, { x: 1360, y: 622, w: 400, size: 30, weight: 700, color: C.soft });
    const b2 = S.bar({ x: 1360, y: 660, w: 400, h: 40, value: 1, max: N.ratio, color: C.soft });
    const cc = S.chip('tested', { x: 1300 + Math.round((W - chipW(L.chip)) / 2), y: 722, label: L.chip });
    const t0 = S.capAt(0), t1 = S.capAt(1), t2 = S.capAt(2);
    S.show(cards[0], t0); S.show(ttl[0], t0 + 0.3); S.show(d1.wrap, t0 + 0.6); turn(S, d1, 45, t0 + 1.2, 2.4);
    S.show(uV, t0 + 1.0, { dur: 0.3 }); S.count(uV, { from: 0, to: N.updates, comma: true }, t0 + 1.1, 2.2);
    S.show(uU, t0 + 1.4, { dur: 0.3 });
    S.show(rV, t0 + 1.6, { dur: 0.3 }); S.count(rV, { from: 0, to: N.rows, comma: true }, t0 + 1.7, 1.6);
    S.show(rU, t0 + 2.0, { dur: 0.3 });
    S.show(cards[1], t1); S.show(ttl[1], t1 + 0.3);
    S.show(s1, t1 + 0.7); S.show(rl[0], t1 + 0.9); S.show(s2, t1 + 1.1); S.show(rl[1], t1 + 1.3); S.show(s3, t1 + 1.5); S.show(rl[2], t1 + 1.7);
    S.pop(pc, t1 + 2.0);
    S.draw(wall, t1 + 2.4, 0.5);
    S.show(kV, t1 + 3.0, { dur: 0.3 }); S.count(kV, { from: 0, to: N.kept, comma: true }, t1 + 3.1, 2.0);
    S.show(kU, t1 + 3.4, { dur: 0.3 });
    S.show(cards[2], t2); S.show(ttl[2], t2 + 0.3);
    S.show(xV, t2 + 0.7, { dur: 0.3 }); S.count(xV, { from: 0, to: N.ratio, dec: 1, suf: '×' }, t2 + 0.8, 1.8);
    S.show(xU, t2 + 1.2, { dur: 0.3 });
    S.show(oL, t2 + 2.6); S.show(b1.track, t2 + 2.8); S.grow(b1, t2 + 3.0, 1.2);
    S.show(pL, t2 + 3.0); S.show(b2.track, t2 + 3.2); S.grow(b2, t2 + 3.4, 1.2);
    S.pop(cc, t2 + 4.8);
  });
});
