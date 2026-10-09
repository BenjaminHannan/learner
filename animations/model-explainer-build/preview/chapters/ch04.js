/* Chapter 4: the thinker. Every on-screen string comes from content/ch04.json (S.c). */
Kit.chapter('ch04', function (Ch) {
  const C = Kit.C;
  // start a beat at time t, but no later than 0.78 of the scene minus its own length d (motion ends before 80%)
  const fin = (S, t, d = 0.8) => Math.min(t, S.at(0.78) - d);

  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 300, w: 1720, h: 200, highlight: 'thinker' });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.08), 0.25);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.3) + i * 0.2, 0.4));
    const chip = S.chip('untested', { x: 160, y: 600, label: c.chip });
    S.pop(chip, S.at(0.5));
    S.pulse(m.parts.thinker, S.at(0.6));
  });

  Ch.scene('s02', function (S) {
    const c = S.c;
    const q = S.card({ x: 480, y: 220, w: 960, h: 100, fill: C.card, color: C.line, r: 18 });
    const qt = S.text(c.labels.q, { x: 480, y: 252, w: 960, size: 44, weight: 700, align: 'center' });
    S.show(q, S.at(0.04)); S.show(qt, S.at(0.04));
    const xs = [530, 960, 1390];
    const notes = xs.map((x) => S.box({ x: x - 150, y: 430, w: 300, h: 170, label: c.labels.n, color: C.thinker, size: 40 }));
    const svg = S.svg();
    const looks = xs.map((x) => S.arrow(svg, x, 325, x, 425, { color: C.soft }));
    const pass = [S.arrow(svg, 680, 515, 810, 515, { color: C.thinker }), S.arrow(svg, 1110, 515, 1240, 515, { color: C.thinker })];
    const tag = S.chip('placeholder', { x: 80, y: 200, label: c.tag });
    S.stagger(notes, S.capAt(0), 0.25);
    S.pop(tag, S.at(0.1));
    looks.forEach((a, i) => S.draw(a, fin(S, S.capAt(1)) + i * 0.15, 0.5));
    pass.forEach((a, i) => S.draw(a, fin(S, S.capAt(2)) + i * 0.6, 0.5));
    S.pulse(notes[1], fin(S, S.capAt(3)));
  });

  Ch.scene('s03', function (S) {
    const c = S.c;
    const example = S.vec({ x: 200, y: 330, n: 8, cell: 56, gap: 12, color: C.thinker, seed: 2 });
    const cLbl = S.text(c.labels.ctrl, { x: 200, y: 250, w: 900, size: 40, weight: 700, color: C.thinker });
    const mLbl = S.text(c.labels.mem, { x: 200, y: 500, w: 1000, size: 40, weight: 700, color: C.thinker });
    const mem = S.vec({ x: 200, y: 550, n: 36, cell: 36, gap: 6, color: C.thinker, seed: 9 });
    const oldL = S.text(c.labels.old, { x: 200, y: 720, w: 1200, size: 40, color: C.soft });
    const chip = S.chip('untested', { x: 1380, y: 200, label: c.chip });
    S.show(example, S.at(0.06));
    S.show(cLbl, fin(S, S.capAt(1)));
    S.show(mLbl, fin(S, S.capAt(2))); S.show(mem, fin(S, S.capAt(2)));
    S.show(oldL, fin(S, S.capAt(3))); S.show(chip, fin(S, S.capAt(3)));
  });

  Ch.scene('s04', function (S) {
    const c = S.c;
    const c0 = S.box({ x: 160, y: 380, w: 440, h: 130, label: c.labels.c0, color: C.thinker, size: 40 });
    const cw = S.box({ x: 760, y: 380, w: 400, h: 130, label: c.labels.cw, color: C.call, size: 40 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 600, 445, 760, 445, { color: C.call });
    const a2 = S.arrow(svg, 1160, 445, 1280, 445, { color: C.call });
    const slip = S.card({ x: 1280, y: 360, w: 480, h: 170, fill: C.card, color: C.call, r: 16 });
    const slipT = S.text(c.labels.slip, { x: 1280, y: 402, w: 480, size: 60, mono: true, weight: 700, align: 'center', color: C.call });
    const none = S.text(c.labels.none, { x: 1280, y: 580, w: 480, size: 44, color: C.soft, align: 'center' });
    S.show(c0, S.at(0.05)); S.show(cw, S.at(0.08));
    S.draw(a1, S.at(0.2), 0.6);
    S.draw(a2, fin(S, S.capAt(1)), 0.5);
    S.show(slip, fin(S, S.capAt(1), 0.9)); S.show(slipT, fin(S, S.capAt(1), 0.9));
    S.show(none, fin(S, S.capAt(1) + 0.6, 0.7));
    S.pop(S.chip('tested', { x: 160, y: 600, label: c.chip }), S.at(0.45));
    S.pulse(slip, fin(S, S.capAt(2)));
  });

  Ch.scene('s05', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 300, w: 1000, labelW: 460, rowH: 90, gap: 40, max: 100, dec: 1, labelSize: 40, items: [
      { label: c.labels.on, value: c.values.on, color: C.thinker },
      { label: c.labels.off, value: c.values.off, color: C.warn },
    ] });
    hb.reveal(S.at(0.1), 0.5, 1.6);
    const ax = S.text(c.labels.axis, { x: 160, y: 620, w: 1400, size: 36, color: C.soft });
    S.show(ax, S.at(0.08));
    S.pop(S.chip('tested', { x: 160, y: 720, label: c.tag }), S.at(0.6));
  });

  Ch.scene('s06', function (S) {
    const c = S.c;
    const L = S.letters(c.labels.q, { x: 160, y: 250, size: 52, gap: 8 });
    S.sweep(L.cells, S.capAt(0), 1.2);
    const by = L.cy + L.h / 2 + 4;
    const rows = [0, 1, 2].map((i) => {
      const y = 520 + i * 110;
      const b = S.box({ x: 160, y, w: 200, h: 80, label: c.labels.look, color: C.thinker, size: 36 });
      const v = S.vec({ x: 420, y: y + 14, n: 16, cell: 40, gap: 6, color: C.thinker, seed: 3 + i * 7 });
      return { b, v, y };
    });
    const svg = S.svg();
    const looks = [0, 9, 17].map((ci, i) => S.arrow(svg, L.cx(ci), by, 620 + i * 60, rows[i].y - 4, { color: C.reader }));
    rows.forEach((r, i) => {
      S.show(r.b, fin(S, S.capAt(1)) + i * 0.2);
      S.show(r.v, fin(S, S.capAt(1)) + i * 0.2);
    });
    looks.forEach((a, i) => S.draw(a, fin(S, S.capAt(1)) + 0.3 + i * 0.2, 0.5));
    S.pop(S.chip('placeholder', { x: 1400, y: 200, label: c.tag }), S.at(0.1));
  });

  Ch.scene('s07', function (S) {
    const c = S.c;
    const strips = [300, 420, 540].map((y, i) => S.vec({ x: 160, y, n: 10, cell: 34, gap: 6, color: C.thinker, seed: 11 + i * 5 }));
    const cmp = S.box({ x: 660, y: 290, w: 280, h: 280, label: c.labels.compare, color: C.thinker, size: 40 });
    const thk = S.box({ x: 1040, y: 290, w: 340, h: 280, label: c.labels.think, color: C.thinker, size: 40 });
    const wid = S.box({ x: 1480, y: 290, w: 340, h: 280, label: c.labels.widen, color: C.thinker, size: 40 });
    const svg = S.svg();
    const toCmp = [317, 437, 557].map((y) => S.arrow(svg, 560, y, 660, 430, { color: C.thinker }));
    const a2 = S.arrow(svg, 940, 430, 1040, 430, { color: C.thinker });
    const a3 = S.arrow(svg, 1380, 430, 1480, 430, { color: C.thinker });
    const back = S.path(svg, [[1650, 570], [1650, 640], [330, 640], [330, 580]], { color: C.soft });
    S.stagger(strips, S.at(0.05), 0.2);
    S.show(cmp, fin(S, S.capAt(0)));
    toCmp.forEach((a, i) => S.draw(a, fin(S, S.capAt(1)) + i * 0.15, 0.5));
    S.pulse(cmp, fin(S, S.capAt(2)));
    S.show(thk, fin(S, S.capAt(3))); S.draw(a2, fin(S, S.capAt(3)) + 0.2, 0.5);
    S.show(wid, fin(S, S.capAt(3)) + 0.4); S.draw(a3, fin(S, S.capAt(3)) + 0.6, 0.5);
    S.draw(back, fin(S, S.capAt(4)), 0.7);
  });

  Ch.scene('s08', function (S) {
    const c = S.c;
    const xs = [200, 780, 1360];
    const bl = xs.map((x) => S.box({ x, y: 400, w: 360, h: 170, label: c.labels.block, color: C.thinker, size: 44 }));
    const svg = S.svg();
    const ar = [S.arrow(svg, 560, 485, 780, 485, { color: C.thinker }), S.arrow(svg, 1140, 485, 1360, 485, { color: C.thinker })];
    const stamps = xs.map((x) => S.chip('learned', { x: x + 60, y: 330, label: c.tag }));
    S.stagger(bl, S.at(0.05), 0.3);
    S.draw(ar[0], S.at(0.2), 0.5); S.draw(ar[1], S.at(0.3), 0.5);
    bl.forEach((b, i) => S.pulse(b, fin(S, S.capAt(1)) + i * 0.1));
    stamps.forEach((s, i) => S.pop(s, fin(S, S.capAt(2)) + i * 0.15));
    S.pop(S.chip('tested', { x: 200, y: 680, label: c.chip }), fin(S, S.capAt(2)) + 0.4);
  });

  Ch.scene('s09', function (S) {
    const c = S.c;
    const r2 = S.box({ x: 160, y: 330, w: 520, h: 120, label: c.labels.r2, color: C.call, size: 40 });
    const r2r = S.box({ x: 800, y: 330, w: 360, h: 120, label: c.labels.r2r, color: C.calc, size: 40 });
    const r3 = S.box({ x: 160, y: 580, w: 520, h: 120, label: c.labels.r3, color: C.call, size: 40 });
    const r3r = S.box({ x: 800, y: 580, w: 360, h: 120, label: c.labels.r3r, color: C.calc, size: 40 });
    const ans = S.box({ x: 1300, y: 455, w: 500, h: 130, label: c.labels.ans, color: C.talker, size: 44 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 680, 390, 800, 390, { color: C.soft });
    const a2 = S.path(svg, [[980, 450], [980, 520], [420, 520], [420, 580]], { color: C.soft });
    const a3 = S.arrow(svg, 680, 640, 800, 640, { color: C.soft });
    const a4 = S.arrow(svg, 1160, 640, 1300, 540, { color: C.soft });
    S.show(r2, S.at(0.05));
    S.draw(a1, fin(S, S.capAt(1)), 0.5); S.show(r2r, fin(S, S.capAt(1)) + 0.5);
    S.draw(a2, fin(S, S.capAt(2)), 0.6); S.show(r3, fin(S, S.capAt(2)) + 0.4);
    S.draw(a3, fin(S, S.capAt(2)) + 0.6, 0.4); S.show(r3r, fin(S, S.capAt(2)) + 0.9);
    S.draw(a4, fin(S, S.capAt(3)), 0.5); S.pop(ans, fin(S, S.capAt(3)) + 0.4);
    S.show(S.chip('untested', { x: 160, y: 740, label: c.chip }), fin(S, S.capAt(3)) + 0.6);
  });

  Ch.scene('s10', function (S) {
    const c = S.c;
    const mn = S.text(c.labels.min, { x: 200, y: 400, w: 500, size: 40, weight: 700, color: C.stop });
    const mx = S.text(c.labels.max, { x: 1000, y: 400, w: 476, size: 40, weight: 700, color: C.stop, align: 'right' });
    const cells = S.vec({ x: 200, y: 470, n: 32, cell: 36, gap: 4, color: C.stop, seed: 5 });
    S.show(mn, S.at(0.05)); S.show(mx, S.at(0.05));
    S.show(cells, S.at(0.1));
    S.pulse(mn, fin(S, S.capAt(1)));
    S.pulse(mx, fin(S, S.capAt(2)));
    S.pop(S.chip('untested', { x: 200, y: 640, label: c.chip }), fin(S, S.capAt(2)) + 0.3);
  });

  Ch.scene('s11', function (S) {
    const c = S.c;
    const num = S.text('', { x: 160, y: 230, w: 1600, size: 120, weight: 800, color: C.thinker });
    S.count(num, { from: 0, to: c.values.block, comma: true }, S.at(0.1), 2.0);
    const L21 = S.text(c.labels.b21, { x: 160, y: 430, w: 340, size: 40, weight: 700, align: 'right' });
    const b21 = S.bar({ x: 540, y: 420, w: 1100, h: 90, value: c.values.b21, max: 30, color: C.thinker });
    const L30 = S.text(c.labels.b30, { x: 160, y: 600, w: 340, size: 40, weight: 700, align: 'right' });
    const b30 = S.bar({ x: 540, y: 590, w: 1100, h: 90, value: c.values.b30, max: 30, color: C.learned });
    S.show(L21, S.at(0.4)); S.show(b21.track, S.at(0.4));
    S.grow(b21, S.at(0.4), 1.2);
    S.show(L30, fin(S, S.capAt(2))); S.show(b30.track, fin(S, S.capAt(2)));
    S.grow(b30, fin(S, S.capAt(2)), 1.2);
    S.pop(S.chip('placeholder', { x: 160, y: 740, label: c.chip }), fin(S, S.capAt(2)) + 0.6);
  });

  Ch.scene('s12', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 290, w: 880, labelW: 300, rowH: 80, gap: 24, max: c.values.r100, dec: 0, labelSize: 40, items: [
      { label: c.labels.r3, value: c.values.r3, color: C.thinker },
      { label: c.labels.r10, value: c.values.r10, color: C.thinker },
      { label: c.labels.r30, value: c.values.r30, color: C.thinker },
      { label: c.labels.r100, value: c.values.r100, color: C.thinker },
    ] });
    hb.reveal(S.at(0.1), 0.5, 1.4);
    S.pop(S.chip('untested', { x: 160, y: 740, label: c.chip }), S.at(0.6));
    S.show(S.text(c.note, { x: 160, y: 800, w: 1600, size: 34, color: C.soft }), S.at(0.6));
  });

  Ch.scene('s13', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 290, w: 900, labelW: 500, rowH: 90, gap: 40, max: c.values.eight, dec: 0, labelSize: 36, items: [
      { label: c.labels.all, value: c.values.all, color: C.warn },
      { label: c.labels.round, value: c.values.round, color: C.thinker },
      { label: c.labels.eight, value: c.values.eight, color: C.thinker },
    ] });
    hb.reveal(S.at(0.1), 0.6, 2.0);
    S.pop(S.chip('placeholder', { x: 160, y: 680, label: c.chip }), S.at(0.6));
  });

  Ch.scene('s14', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 300, w: 1100, labelW: 420, rowH: 100, gap: 40, max: 100, dec: 2, labelSize: 40, items: [
      { label: c.labels.on, value: c.values.on, color: C.thinker },
      { label: c.labels.off, value: c.values.off, color: C.warn },
    ] });
    hb.reveal(S.at(0.1), 0.6, 2.0);
    S.show(S.text(c.labels.axis, { x: 160, y: 630, w: 1400, size: 36, color: C.soft }), S.at(0.08));
    S.pop(S.chip('tested', { x: 160, y: 720, label: c.chip }), S.at(0.6));
  });

  Ch.scene('s15', function (S) {
    const c = S.c;
    const r = S.text(c.labels.r, { x: 160, y: 230, w: 800, size: 56, weight: 800, color: C.thinker });
    S.show(r, S.at(0.05));
    const m = S.modelMap({ x: 100, y: 300, w: 1720, h: 200, highlight: 'thinker' });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.1), 0.2);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.25) + i * 0.15, 0.4));
    S.pulse(m.parts.thinker, fin(S, S.capAt(1)));
    S.pop(S.chip('untested', { x: 160, y: 600, label: c.chip }), fin(S, S.capAt(3)));
  });
});
