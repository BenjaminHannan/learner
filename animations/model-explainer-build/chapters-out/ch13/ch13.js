/* ch13: Size, and whether it pays off. Every word and number on screen is read from the scene JSON (S.c).
   Illustrations are tagged "picture only" from the moment they appear. All motion ends by 80% of each scene. */
Kit.chapter('ch13', function (Ch) {
  const C = Kit.C;
  // light fills so dark text stays readable on them
  const TINT = { reader: '#D7EFEF', thinker: '#E3E1FB', grey: '#ECEEF1', warn: '#FDE3D6', good: '#D5EFE2', amber: '#FBEBCB' };

  // a plain straight line (no head) that can be drawn on with S.draw
  function ln(S, svg, pts, color, width) { return S.path(svg, pts, { color: color, width: width || 5, head: 0 }); }

  // grow a card from its left edge (to-scale segment of a bar)
  function growX(S, el, t, dur) {
    gsap.set(el, { transformOrigin: '0% 50%', scaleX: 0, autoAlpha: 0 });
    S.tl.to(el, { scaleX: 1, autoAlpha: 1, duration: dur, ease: 'power2.out' }, t);
    return t + dur;
  }

  // s01: two lines on a picture (not a measurement). Ours must climb steeper.
  Ch.scene('s01', function (S) {
    const c = S.c, L = c.labels;
    const svg = S.svg();
    const ox = 260, oy = 740;
    const ya = S.arrow(svg, ox, oy, ox, 250, { color: C.soft, width: 5, head: 20 });
    const xa = S.arrow(svg, ox, oy, 1440, oy, { color: C.soft, width: 5, head: 20 });
    const plain = S.curve(svg, ox + 12, oy - 12, 1400, 560, { color: C.placeholder, width: 9, bend: -35, head: 0 });
    const ours = S.curve(svg, ox + 12, oy - 12, 1400, 330, { color: C.thinker, width: 9, bend: -60, head: 0 });
    const gap = S.arrow(svg, 1420, 548, 1420, 342, { color: C.soft, width: 5, head: 18 });
    const tag = S.chip('placeholder', { x: 420, y: 205, label: c.tag });
    const yl = S.text(L.y, { x: 110, y: 205, w: 220, size: 36, weight: 700, color: C.soft });
    const xs = S.text(L.xs, { x: ox, y: 760, w: 300, size: 36, color: C.soft });
    const xe = S.text(L.xe, { x: 1140, y: 760, w: 300, size: 36, color: C.soft, align: 'right' });
    const oursL = S.text(L.ours, { x: 1455, y: 300, w: 380, size: 40, weight: 700, color: C.thinker });
    const plainL = S.text(L.plain, { x: 1455, y: 540, w: 380, size: 38, weight: 600, color: C.soft });
    const moreL = S.text(L.more, { x: 1455, y: 420, w: 380, size: 38, weight: 700, color: C.ink });

    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.draw(ya, t, 0.8); S.draw(xa, t, 0.8);
    S.stagger([yl, xs, xe], t + 0.7, 0.35);
    t = S.capAt(1);
    S.draw(plain, t, 1.6);
    S.show(plainL, t + 1.4);
    S.draw(ours, t + 2.0, 1.8);
    S.show(oursL, t + 3.6);
    t = S.capAt(2);
    S.draw(gap, t, 0.8);
    S.show(moreL, t + 0.6);
    S.pulse(oursL, t + 1.6);
  });

  // s02: the ladder, bars drawn to scale with exact counts.
  Ch.scene('s02', function (S) {
    const c = S.c, L = c.labels;
    const chip = S.chip('untested', { x: 100, y: 205, label: c.chip });
    const unit = S.text(L.unit, { x: 100, y: 275, w: 1200, size: 34, color: C.soft });
    const hb = S.hbars({
      x: 100, y: 340, w: 900, labelW: 200, rowH: 66, gap: 30, max: c.rungs[3].value, dec: 0,
      valueSize: 46, labelSize: 44, valueW: 420,
      items: c.rungs.map(function (r) { return { label: r.label, value: r.value, color: C.thinker, labelColor: C.thinker, dec: 0 }; }),
    });
    const big = S.note(L.big, { x: 300, y: 735, w: 900, size: 34, color: C.thinker });
    S.show(unit, S.capAt(0));
    hb.reveal(S.capAt(0) + 0.5, 0.8, 1.6);
    S.show(chip, S.capAt(1));
    S.show(big, S.capAt(2));
    S.pulse(hb.rows[3].track, S.capAt(2) + 0.6);
  });

  // s03: one stacked bar drawn to scale: reader + ours = 373.1 as built; talker is a plan.
  Ch.scene('s03', function (S) {
    const c = S.c, L = c.labels, V = c.values;
    const svg = S.svg();
    const x0 = 160, y = 330, h = 150, per = 1400 / V.total;
    const wR = V.reader * per, wO = V.ours * per, wT = V.talker * per;
    const reader = S.card({ x: x0, y: y, w: wR, h: h, fill: TINT.reader, color: C.reader, r: 14 });
    const ours = S.card({ x: x0 + wR, y: y, w: wO, h: h, fill: TINT.thinker, color: C.thinker, r: 14 });
    const talker = S.card({ x: x0 + wR + wO, y: y, w: wT, h: h, fill: '#FFFFFF', color: C.placeholder, r: 14 });
    talker.style.borderStyle = 'dashed';
    const nR = S.text('', { x: x0, y: y + 36, w: wR, size: 76, weight: 800, align: 'center', color: C.ink });
    const nO = S.text('', { x: x0 + wR, y: y + 42, w: wO, size: 64, weight: 800, align: 'center', color: C.ink });
    const nT = S.text('', { x: x0 + wR + wO, y: y + 50, w: wT, size: 44, weight: 800, align: 'center', color: C.soft });
    const lR = S.text(L.reader, { x: x0, y: 272, w: wR, size: 36, weight: 700, align: 'center', color: C.ink });
    const lO = S.text(L.ours, { x: x0 + wR, y: 272, w: wO, size: 36, weight: 700, align: 'center', color: C.ink });
    const lT = S.text(L.talker, { x: 1400, y: 495, w: 300, size: 34, align: 'right', color: C.soft });
    const brace = ln(S, svg, [[x0, 565], [x0, 590], [x0 + wR + wO, 590], [x0 + wR + wO, 565]], C.ink, 5);
    const total = S.text('', { x: x0, y: 605, w: 330, size: 92, weight: 800, color: C.ink });
    const unit = S.text(L.built, { x: x0 + 350, y: 648, w: 600, size: 42, color: C.soft });
    const plan = S.note(L.plan, { x: 1010, y: 615, w: 800, size: 36, color: C.placeholder });

    let t = S.capAt(0);
    S.show(lR, t);
    growX(S, reader, t + 0.3, 1.2);
    S.show(nR, t + 0.5);
    S.count(nR, { from: 0, to: V.reader, dec: 1 }, t + 0.6, 1.4);
    t = S.capAt(1);
    S.show(lO, t);
    growX(S, ours, t + 0.3, 1.0);
    S.show(nO, t + 0.5);
    S.count(nO, { from: 0, to: V.ours, dec: 1 }, t + 0.6, 1.4);
    S.draw(brace, t + 2.0, 0.9);
    S.show(total, t + 2.2);
    S.count(total, { from: 0, to: V.total, dec: 1 }, t + 2.3, 1.4);
    S.show(unit, t + 2.6);
    t = S.capAt(2);
    S.show(talker, t, { dur: 0.6 });
    S.show(nT, t + 0.3);
    S.count(nT, { from: 0, to: V.talker, dec: 0 }, t + 0.4, 1.0);
    S.show(lT, t + 0.5);
    S.show(plan, t + 1.2);
  });

  // s04: three gain bars with a marker at the needed gain (3.0).
  Ch.scene('s04', function (S) {
    const c = S.c, L = c.labels;
    const svg = S.svg();
    const bx = 580, bw = 900, max = 16, per = bw / max;
    const ys = [330, 450, 570];
    const chip = S.chip('tested', { x: 1290, y: 205, label: c.chip });
    const head = S.text(L.head, { x: bx, y: 205, w: 600, size: 36, weight: 700, color: C.soft });
    const mx = bx + c.needed * per;
    const marker = ln(S, svg, [[mx, 300], [mx, 665]], C.warn, 6);
    const need = S.text(L.need, { x: mx - 10, y: 258, w: 360, size: 34, weight: 700, color: C.warn });
    const rows = c.rows.map(function (r, i) {
      const col = i === 0 ? C.thinker : C.placeholder;
      const lab = S.text(r.label, { x: 80, y: ys[i] + 10, w: 480, size: 36, weight: 700, align: 'right', color: i === 0 ? C.thinker : C.ink });
      const b = S.bar({ x: bx, y: ys[i], w: bw, h: 64, value: r.value, max: max, color: col });
      const val = S.text('', { x: bx + bw + 24, y: ys[i] + 6, w: 300, size: 46, weight: 800, color: i === 0 ? C.thinker : C.ink });
      return { lab: lab, b: b, val: val };
    });
    const sc = S.text(c.rows[0].from.toFixed(2) + ' → ' + c.rows[0].to.toFixed(2), { x: bx, y: ys[0] + 68, w: 600, size: 30, color: C.soft });
    const range = S.note(L.range, { x: bx, y: 700, w: 1100, size: 32, color: C.thinker });

    function reveal(i, t) {
      const r = rows[i];
      S.show(r.lab, t, { dur: 0.4 }); S.show(r.b.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 });
      S.grow(r.b, t + 0.3, 1.4, r.val, { dec: 2, pre: '+' });
    }
    let t = S.capAt(0);
    S.show(chip, t); S.show(head, t + 0.2);
    reveal(0, t + 0.6);
    S.show(sc, t + 2.2);
    t = S.capAt(1);
    S.draw(marker, t, 0.8);
    S.show(need, t + 0.7);
    S.show(range, t + 1.4);
    S.pulse(rows[0].b.track, t + 2.2);
    t = S.capAt(2);
    reveal(1, t);
    reveal(2, t + 0.8);
  });

  // s05: a 3-row table; each cell counts from the 3M score to the 10M score.
  Ch.scene('s05', function (S) {
    const c = S.c, H = c.heads;
    const colX = [700, 1260], cw = 480, ys = [380, 530, 680], ch = 110;
    const chip = S.chip('tested', { x: 100, y: 205, label: c.chip });
    const sub = H.from + ' → ' + H.to;
    const hO = S.text(H.ours, { x: colX[0], y: 262, w: cw, size: 42, weight: 800, align: 'center', color: C.thinker });
    const hP = S.text(H.plain, { x: colX[1], y: 262, w: cw, size: 42, weight: 800, align: 'center', color: C.soft });
    const sO = S.text(sub, { x: colX[0], y: 318, w: cw, size: 32, align: 'center', color: C.soft });
    const sP = S.text(sub, { x: colX[1], y: 318, w: cw, size: 32, align: 'center', color: C.soft });
    const rows = c.rows.map(function (r, i) {
      const lab = S.text(r.label, { x: 80, y: ys[i] + 32, w: 590, size: 40, weight: 700, color: C.ink });
      const cO = S.card({ x: colX[0], y: ys[i], w: cw, h: ch, fill: '#FFFFFF', color: C.thinker, r: 16 });
      const cP = S.card({ x: colX[1], y: ys[i], w: cw, h: ch, fill: '#FFFFFF', color: C.placeholder, r: 16 });
      const nO = S.text('', { x: colX[0], y: ys[i] + 22, w: cw, size: 60, weight: 800, align: 'center', color: C.thinker });
      const nP = S.text('', { x: colX[1], y: ys[i] + 22, w: cw, size: 60, weight: 800, align: 'center', color: C.ink });
      return { lab: lab, cO: cO, cP: cP, nO: nO, nP: nP, r: r };
    });
    S.show(chip, S.at(0.03));
    S.stagger([hO, hP], S.at(0.05), 0.2);
    S.stagger([sO, sP], S.at(0.08), 0.2);
    rows.forEach(function (w, i) {
      const t = S.capAt(i) + 0.3;
      S.show(w.lab, t); S.show(w.cO, t + 0.2); S.show(w.cP, t + 0.2);
      S.show(w.nO, t + 0.4); S.show(w.nP, t + 0.4);
      S.count(w.nO, { from: w.r.o3, to: w.r.o10, dec: 1 }, t + 0.6, 1.8);
      S.count(w.nP, { from: w.r.p3, to: w.r.p10, dec: 1 }, t + 0.6, 1.8);
    });
    S.pulse(rows[1].cO, S.capAt(1) + 3.0);
    S.pulse(rows[1].cP, S.capAt(1) + 3.0);
  });

  // s06: the settings said 36 note vectors; it ran with 9. Cell shading means nothing.
  Ch.scene('s06', function (S) {
    const c = S.c, L = c.labels, N = c.counts;
    const cell = 38, gap = 4;
    const sw = function (n) { return n * cell + (n - 1) * gap; };
    const tag = S.chip('placeholder', { x: 100, y: 205, label: c.tag });
    const l1 = S.text(L.said, { x: 100, y: 285, w: 1000, size: 36, weight: 700, color: C.thinker });
    const v1 = S.vec({ x: 100, y: 340, n: N.said, cell: cell, gap: gap, color: C.thinker, seed: 5 });
    const n1 = S.text('', { x: 100 + sw(N.said) + 30, y: 326, w: 200, size: 62, weight: 800, color: C.thinker });
    const l2 = S.text(L.ran, { x: 100, y: 440, w: 1000, size: 36, weight: 700, color: C.warn });
    const ghost = S.card({ x: 100 + sw(N.ran) + gap, y: 495, w: sw(N.said) - sw(N.ran) - gap, h: cell, fill: 'rgba(0,0,0,0)', color: C.line, r: 6 });
    ghost.style.borderStyle = 'dashed';
    const v2 = S.vec({ x: 100, y: 495, n: N.ran, cell: cell, gap: gap, color: C.warn, seed: 8 });
    const n2 = S.text('', { x: 100 + sw(N.said) + 30, y: 481, w: 200, size: 62, weight: 800, color: C.warn });
    const cut = S.note(L.cut, { x: 100, y: 610, w: 1000, size: 36, color: C.warn });
    const real = S.chip('tested', { x: 100, y: 760, label: L.real });
    const unt = S.chip('untested', { x: 700, y: 760, label: L.untested });

    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.show(l1, t);
    S.show(v1, t + 0.3, { dur: 0.8 });
    S.show(n1, t + 0.6);
    S.count(n1, { from: 0, to: N.said }, t + 0.7, 1.2);
    S.show(l2, t + 2.2);
    S.show(ghost, t + 2.4);
    S.show(v2, t + 2.5, { dur: 0.8 });
    S.show(n2, t + 2.8);
    S.count(n2, { from: 0, to: N.ran }, t + 2.9, 1.0);
    t = S.capAt(1);
    S.show(cut, t + 0.2);
    t = S.capAt(2);
    S.pop(real, t);
    S.pop(unt, t + 0.8);
  });

  // s07: the first G1 result. Two bars, counts of questions right, and our subtraction.
  Ch.scene('s07', function (S) {
    const c = S.c, L = c.labels, K = c.counts;
    const chip = S.chip('tested', { x: 100, y: 205, label: c.chip });
    const rung = S.text(L.rung, { x: 100, y: 268, w: 900, size: 40, weight: 700, color: C.thinker });
    const hb = S.hbars({
      x: 100, y: 345, w: 800, labelW: 330, rowH: 80, gap: 130, max: 100, dec: 2,
      valueSize: 56, labelSize: 44,
      items: [
        { label: c.rows[0].label, value: c.rows[0].value, color: C.thinker, labelColor: C.thinker },
        { label: c.rows[1].label, value: c.rows[1].value, color: C.placeholder },
      ],
    });
    const cnO = S.text('', { x: 430, y: 433, w: 800, size: 36, color: C.soft });
    const cnP = S.text('', { x: 430, y: 643, w: 800, size: 36, color: C.soft });
    const diff = S.text('', { x: 430, y: 700, w: 340, size: 90, weight: 800, color: C.ink });
    const diffL = S.text(L.diff, { x: 790, y: 732, w: 1030, size: 34, color: C.soft });
    S.show(chip, S.capAt(0)); S.show(rung, S.capAt(0) + 0.3);
    let t = S.capAt(1);
    hb.reveal(t, 0.9, 1.6);
    S.show(cnO, t + 0.5);
    S.count(cnO, { from: 0, to: K.ours, comma: true, suf: ' ' + L.of }, t + 0.6, 1.6);
    S.show(cnP, t + 1.4);
    S.count(cnP, { from: 0, to: K.plain, comma: true, suf: ' ' + L.of }, t + 1.5, 1.6);
    t = S.capAt(2);
    S.show(diff, t);
    S.count(diff, { from: 0, to: c.diff, dec: 2, pre: '+' }, t + 0.1, 1.4);
    S.show(diffL, t + 0.6);
  });

  // s08: the written screening rule as a number line (picture only) and run status.
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.labels, T = c.status;
    const svg = S.svg();
    const x0 = 200, xz = 760, xo = 1160, x1 = 1720, y = 400, h = 130;
    const tag = S.chip('placeholder', { x: 100, y: 205, label: c.tag });
    const zS = S.box({ x: x0, y: y, w: xz - x0, h: h, label: L.stop, color: C.warn, fill: TINT.warn, size: 46 });
    const zU = S.box({ x: xz, y: y, w: xo - xz, h: h, label: L.unclear, color: C.placeholder, fill: TINT.grey, size: 46 });
    const zG = S.box({ x: xo, y: y, w: x1 - xo, h: h, label: L.go, color: C.tested, fill: TINT.good, size: 46 });
    const k0 = ln(S, svg, [[xz, y - 14], [xz, y + h + 14]], C.ink, 6);
    const k1 = ln(S, svg, [[xo, y - 14], [xo, y + h + 14]], C.ink, 6);
    const t0 = S.text(L.t0, { x: xz - 60, y: y + h + 22, w: 120, size: 44, weight: 800, align: 'center' });
    const t1 = S.text(L.t1, { x: xo - 60, y: y + h + 22, w: 120, size: 44, weight: 800, align: 'center' });
    const axis = S.text(L.axis, { x: x0, y: y + h + 92, w: x1 - x0, size: 36, align: 'center', color: C.soft });
    const q = S.box({ x: xz - 45, y: 290, w: 90, h: 90, r: 45, label: L.q, color: C.thinker, fill: TINT.thinker, size: 56 });
    const sa = S.chip('tested', { x: 100, y: 730, label: T.a });
    const sb = S.chip('untested', { x: 540, y: 730, label: T.b });
    const sc = S.chip('placeholder', { x: 1030, y: 730, label: T.c });

    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.pop(sa, t + 0.2); S.pop(sb, t + 1.2); S.pop(sc, t + 2.2);
    t = S.capAt(1);
    S.stagger([zS, zU, zG], t, 0.4);
    S.draw(k0, t + 1.0, 0.5); S.draw(k1, t + 1.3, 0.5);
    S.stagger([t0, t1], t + 1.4, 0.3);
    S.show(axis, t + 2.0);
    S.pulse(zG, t + 3.0);
    t = S.capAt(2);
    S.pulse(zS, t + 0.2);
    S.pulse(zU, t + 1.0);
    S.pop(q, t + 1.8);
    S.pulse(q, t + 2.6);
  });

  // s09: the finished design climbs its own ladder; every rung is paired with a plain model.
  Ch.scene('s09', function (S) {
    const c = S.c, L = c.labels;
    const svg = S.svg();
    const ours = S.text(L.ours, { x: 100, y: 205, w: 700, size: 40, weight: 700, color: C.thinker });
    const tag = S.chip('placeholder', { x: 100, y: 285, label: c.tag });
    const pos = c.rungs.map(function (r, i) { return { x: 100 + i * 440, y: 560 - i * 90 }; });
    const items = c.rungs.map(function (r, i) {
      const p = pos[i];
      const box = S.box({ x: p.x, y: p.y, w: 340, h: 120, label: r.label, color: C.thinker, fill: TINT.thinker, size: 62 });
      const chip = S.chip(i === 0 ? 'untested' : 'placeholder', { x: p.x, y: p.y - 62, label: r.chip });
      const link = S.arrow(svg, p.x + 170, p.y + 124, p.x + 170, p.y + 150, { color: C.soft, width: 5, head: 14 });
      const pair = S.box({ x: p.x, y: p.y + 152, w: 340, h: 98, label: L.pair, color: C.placeholder, fill: TINT.grey, size: 30 });
      const next = i < c.rungs.length - 1 ? S.arrow(svg, p.x + 350, p.y + 60, pos[i + 1].x - 10, pos[i + 1].y + 60, { color: C.soft, width: 6, head: 20 }) : null;
      return { box: box, chip: chip, link: link, pair: pair, next: next };
    });
    function rung(i, t) {
      const it = items[i];
      S.show(it.box, t);
      S.show(it.chip, t + 0.3);
      S.draw(it.link, t + 0.6, 0.4);
      S.show(it.pair, t + 0.9);
    }
    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.show(ours, t);
    rung(0, t + 0.4);
    t = S.capAt(1);
    S.draw(items[0].next, t, 0.6);
    rung(1, t + 0.5);
    S.draw(items[1].next, t + 2.2, 0.6);
    rung(2, t + 2.7);
    t = S.capAt(2);
    S.draw(items[2].next, t, 0.6);
    rung(3, t + 0.5);
  });

  // s10: odds drawn as boxes. 1 of 3 filled; none of 10 filled. Judgment, not measured.
  Ch.scene('s10', function (S) {
    const c = S.c, L = c.labels;
    const chip = S.chip('placeholder', { x: 100, y: 205, label: c.chip });
    const tag = S.chip('placeholder', { x: 100, y: 735, label: c.tag });
    const step = 120, bs = 100;
    const lA = S.text(L.a, { x: 100, y: 285, w: 1500, size: 38, weight: 700, color: C.thinker });
    const lB = S.text(L.b, { x: 100, y: 530, w: 1500, size: 38, weight: 700, color: C.ink });
    const rowA = [0, 1, 2].map(function (i) { return S.box({ x: 100 + i * step, y: 345, w: bs, h: bs, color: C.thinker, fill: '#FFFFFF', r: 14, border: 5 }); });
    const rowB = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(function (i) { return S.box({ x: 100 + i * step, y: 590, w: bs, h: bs, color: C.placeholder, fill: '#FFFFFF', r: 14, border: 5 }); });
    const oA = S.text(L.aOdds, { x: 100 + 3 * step + 40, y: 370, w: 900, size: 56, weight: 800, color: C.thinker });
    const oB = S.text(L.bOdds, { x: 100 + 9 * step + bs + 40, y: 618, w: 440, size: 40, weight: 800, color: C.ink });
    S.show(chip, S.at(0.03));
    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.show(lA, t); S.show(lB, t + 0.5);
    S.stagger(rowA, t + 0.8, 0.2);
    S.sweep(rowB, t + 1.6, 1.4);
    t = S.capAt(1);
    S.tint(rowA[0], t, { fill: C.thinker, border: C.thinker, dur: 0.6 });
    S.show(oA, t + 0.6);
    S.pulse(rowA[0], t + 0.9);
    t = S.capAt(2);
    S.show(oB, t);
    S.pulse(oB, t + 1.0);
  });

  // s11: three places it could run. Mac count is measured; the rest are estimates or plans.
  Ch.scene('s11', function (S) {
    const c = S.c, K = c.cards;
    const cw = 540, cx = [100, 680, 1260], cy = 240, chh = 500;
    function build(i, d, kind, big, bigOpts) {
      const x = cx[i];
      const card = S.card({ x: x, y: cy, w: cw, h: chh, fill: '#FFFFFF', color: C.line, r: 22 });
      const name = S.text(d.name, { x: x + 30, y: cy + 26, w: cw - 60, size: 44, weight: 800, color: C.ink });
      const chip = S.chip(kind, { x: x + 30, y: cy + 100, label: d.chip });
      const bg = S.text(big, { x: x + 30, y: cy + 190, w: cw - 60, size: 108, weight: 800, color: C.ink, nowrap: true });
      const unit = S.text(d.unit, { x: x + 30, y: cy + 330, w: cw - 60, size: 34, color: C.soft });
      const days = d.days ? S.text(d.days, { x: x + 30, y: cy + 392, w: cw - 60, size: 32, weight: 600, color: C.ink }) : null;
      return { card: card, name: name, chip: chip, bg: bg, unit: unit, days: days };
    }
    const pc = build(0, K.pc, 'untested', K.pc.big);
    const mac = build(1, K.mac, 'tested', '');
    const rent = build(2, K.rent, 'placeholder', K.rent.big);
    function reveal(w, t) {
      S.show(w.card, t); S.show(w.name, t + 0.2); S.pop(w.chip, t + 0.5);
      S.show(w.bg, t + 0.8); S.show(w.unit, t + 1.1);
      if (w.days) S.show(w.days, t + 1.4);
    }
    let t = S.capAt(0);
    reveal(pc, t);
    t = S.capAt(1);
    reveal(mac, t);
    S.count(mac.bg, { from: 0, to: K.mac.big, dec: 1 }, t + 0.9, 1.6);
    t = S.capAt(2);
    reveal(rent, t);
    S.pulse(pc.bg, t + 1.8);
  });

  // s12: a race that has not happened. Two lanes slide to the start line; the finish is a question mark.
  Ch.scene('s12', function (S) {
    const c = S.c, L = c.labels;
    const svg = S.svg();
    const lane1 = ln(S, svg, [[100, 467], [1700, 467]], C.line, 6);
    const lane2 = ln(S, svg, [[100, 637], [1700, 637]], C.line, 6);
    const startL = ln(S, svg, [[700, 300], [700, 690]], C.ink, 8);
    const finL = ln(S, svg, [[1560, 300], [1560, 690]], C.soft, 8);
    const tag = S.chip('placeholder', { x: 100, y: 205, label: c.tag });
    const ours = S.box({ x: 100, y: 345, w: 380, h: 110, label: L.ours, color: C.thinker, fill: TINT.thinker, size: 40 });
    const rival = S.box({ x: 100, y: 515, w: 380, h: 110, label: L.rival, color: C.placeholder, fill: TINT.grey, size: 40 });
    const start = S.text(L.start, { x: 600, y: 700, w: 200, size: 36, weight: 700, align: 'center', color: C.ink });
    const fin = S.text(L.finish, { x: 1460, y: 420, w: 200, size: 150, weight: 800, align: 'center', color: C.soft });
    const talker = S.chip('placeholder', { x: 100, y: 770, label: L.talker });

    S.show(tag, S.at(0.03));
    let t = S.capAt(0);
    S.draw(lane1, t, 0.7); S.draw(lane2, t + 0.2, 0.7);
    S.show(ours, t + 0.8); S.show(rival, t + 1.0);
    S.move(ours, t + 1.9, 1.6, { x: 200 });
    S.move(rival, t + 2.0, 1.6, { x: 200 });
    t = S.capAt(1);
    S.draw(startL, t, 0.7);
    S.show(start, t + 0.5);
    S.pulse(ours, t + 1.2); S.pulse(rival, t + 1.4);
    t = S.capAt(2);
    S.draw(finL, t, 0.7);
    S.pop(fin, t + 0.6);
    S.pulse(fin, t + 1.4);
    S.pop(talker, t + 1.8);
  });

  // s13: recap ladder. Only the 3M rung has a result; the rest are not shown.
  Ch.scene('s13', function (S) {
    const c = S.c;
    const svg = S.svg();
    const bx = c.rungs.map(function (r, i) { return 100 + i * 450; });
    const fills = [TINT.good, TINT.amber, TINT.grey, TINT.grey];
    const cols = [C.tested, C.untested, C.placeholder, C.placeholder];
    const kinds = ['tested', 'untested', 'placeholder', 'placeholder'];
    const items = c.rungs.map(function (r, i) {
      const box = S.box({ x: bx[i], y: 340, w: 360, h: 200, label: r.label, sub: r.sub, color: cols[i], fill: fills[i], size: 84, subSize: 40 });
      const chip = S.chip(kinds[i], { x: bx[i] + 20, y: 580, label: r.chip });
      const next = i < c.rungs.length - 1 ? S.arrow(svg, bx[i] + 368, 440, bx[i + 1] - 8, 440, { color: C.soft, width: 6, head: 20 }) : null;
      return { box: box, chip: chip, next: next };
    });
    let t = S.capAt(0);
    S.show(items[0].box, t);
    S.pop(items[0].chip, t + 0.5);
    S.pulse(items[0].box, t + 1.4);
    t = S.capAt(1);
    for (let i = 1; i < 4; i++) {
      S.draw(items[i - 1].next, t + (i - 1) * 0.9, 0.5);
      S.show(items[i].box, t + (i - 1) * 0.9 + 0.4);
      S.pop(items[i].chip, t + (i - 1) * 0.9 + 0.8);
    }
    t = S.capAt(2);
    S.pulse(items[1].box, t); S.pulse(items[2].box, t + 0.3); S.pulse(items[3].box, t + 0.6);
  });
});
