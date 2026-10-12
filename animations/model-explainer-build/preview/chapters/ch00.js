Kit.chapter('ch00', function (Ch) {
  const C = Kit.C;
  const rowReveal = (S, hb, i, t, dur) => { const r = hb.rows[i]; S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 }); return S.grow(r.b, t + 0.3, dur, r.val, { dec: r.it.dec == null ? 2 : r.it.dec, suf: r.it.suf || '', comma: true }); };
  const flowBox = (S, o) => S.box(Object.assign({ size: 38, border: 5 }, o));

  // s01: status ladder, plan > built > tested > released (0)
  Ch.scene('s01', function (S) {
    const L = S.c.labels, svg = S.svg();
    const xs = [95, 545, 995, 1445], cols = [C.placeholder, C.untested, C.tested, C.line];
    const bx = L.stages.map((s, i) => S.box({ x: xs[i], y: 300, w: 380, h: 210, label: s.name, sub: s.sub, color: cols[i], size: 40, subSize: 32, fill: i === 3 ? '#FAF6EE' : '#fff' }));
    const ar = [0, 1, 2].map((i) => S.arrow(svg, xs[i] + 388, 405, xs[i + 1] - 8, 405, { color: C.soft, width: 6 }));
    S.stagger([bx[0], bx[1]], S.capAt(0), 0.5); S.draw(ar[0], S.capAt(0) + 0.9, 0.5);
    S.show(bx[2], S.capAt(1)); S.draw(ar[1], S.capAt(1) - 0.3, 0.5);
    S.show(bx[3], S.capAt(2)); S.draw(ar[2], S.capAt(2) - 0.3, 0.5); S.pulse(bx[3], S.capAt(2) + 0.7);
    S.show(S.note(L.note, { x: 95, y: 620, w: 1730, size: 36, color: C.soft }), S.capAt(2) + 0.8);
  });

  // s02: goals 1 and 2
  Ch.scene('s02', function (S) {
    const L = S.c.labels, svg = S.svg(), xs = [100, 1000], kinds = ['tested', 'untested'];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 270, w: 820, h: 200, label: s.t, color: i ? C.untested : C.tested, size: 52 }));
    const ch = L.steps.map((s, i) => S.chip(kinds[i], { x: xs[i], y: 520, label: s.cl, size: 36 }));
    const a = S.arrow(svg, 928, 370, 992, 370, { color: C.soft, width: 6 });
    S.show(bx[0], S.capAt(0)); S.pop(ch[0], S.capAt(0) + 0.8);
    S.show(bx[1], S.capAt(1)); S.draw(a, S.capAt(1) - 0.3, 0.4); S.pop(ch[1], S.capAt(1) + 0.8);
  });
  // s03: goals 3 and 4, both plan only
  Ch.scene('s03', function (S) {
    const L = S.c.labels, svg = S.svg(), xs = [100, 1000];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 270, w: 820, h: 200, label: s.t, color: C.placeholder, size: 52 }));
    const ch = L.steps.map((s, i) => S.chip('placeholder', { x: xs[i], y: 520, label: s.cl, size: 36 }));
    const a = S.arrow(svg, 928, 370, 992, 370, { color: C.soft, width: 6 });
    const later = S.note(L.later, { x: 100, y: 620, w: 820, size: 36, color: C.placeholder });
    S.show(bx[0], S.capAt(0)); S.pop(ch[0], S.capAt(0) + 0.8);
    S.show(later, S.capAt(1));
    S.show(bx[1], S.capAt(2)); S.draw(a, S.capAt(2) - 0.3, 0.4); S.pop(ch[1], S.capAt(2) + 0.8);
  });

  // s04: two rough odds on a 0-to-1 line
  Ch.scene('s04', function (S) {
    const L = S.c.labels, svg = S.svg();
    const tA = S.text(L.rowA, { x: 360, y: 235, w: 1200, size: 40, weight: 700 });
    const lnA = S.card({ x: 360, y: 340, w: 1200, h: 10, fill: C.line, r: 5 });
    const tB = S.text(L.rowB, { x: 360, y: 485, w: 1200, size: 40, weight: 700 });
    const lnB = S.card({ x: 360, y: 590, w: 1200, h: 10, fill: C.line, r: 5 });
    const tk = [[330, 355], [1530, 355], [330, 605], [1530, 605]].map((p, i) => S.text(i % 2 ? L.t1 : L.t0, { x: p[0], y: p[1], w: 60, size: 32, align: 'center', color: C.soft }));
    const chip = S.chip('placeholder', { x: 100, y: 760, label: L.chip, size: 34 });
    S.show(tA, S.capAt(0)); S.show(lnA, S.capAt(0)); S.show(tB, S.capAt(0) + 0.4); S.show(lnB, S.capAt(0) + 0.4);
    tk.forEach((e) => S.show(e, S.capAt(0) + 0.6)); S.pop(chip, S.capAt(0) + 0.8);
    S.show(S.text(L.pic, { x: 700, y: 765, w: 800, size: 32, color: C.soft }), S.capAt(0) + 0.8);
    const mk = S.card({ x: 355, y: 310, w: 12, h: 70, fill: C.thinker, r: 4 });
    S.show(mk, S.capAt(1)); S.move(mk, S.capAt(1) + 0.3, 1.2, { x: 400 });
    const mkL = S.text(L.markA, { x: 560, y: 390, w: 400, size: 40, weight: 800, align: 'center', color: C.thinker });
    S.show(mkL, S.capAt(1) + 1.6);
    const zone = S.card({ x: 360, y: 560, w: 120, h: 70, fill: '#FFF1E6', color: C.warn, r: 8 });
    const zL = S.text(L.zoneB, { x: 360, y: 650, w: 600, size: 40, weight: 800, color: C.warn });
    S.show(zone, S.capAt(2)); S.pulse(zone, S.capAt(2) + 0.5); S.show(zL, S.capAt(2) + 0.6);
  });

  // s05: a huge stack of numbers vs a small design that thinks in laps and uses a calculator
  Ch.scene('s05', function (S) {
    const L = S.c.labels, svg = S.svg();
    const tower = [];
    for (let i = 0; i < 12; i++) tower.push(S.card({ x: 100, y: 230 + i * 48, w: 460, h: 40, fill: '#E9E2D3', color: C.soft, r: 6 }));
    S.sweep(tower, S.capAt(0), 1.6);
    S.show(S.text(L.big, { x: 600, y: 300, w: 440, size: 44, weight: 800 }), S.capAt(0) + 0.8);
    S.show(S.text(L.bigSub, { x: 600, y: 440, w: 440, size: 34, color: C.soft }), S.capAt(0) + 1.1);
    S.pop(S.chip('placeholder', { x: 600, y: 650, label: L.pic, size: 34 }), S.capAt(0) + 1.4);
    const sm = S.box({ x: 1100, y: 280, w: 340, h: 170, label: L.small, color: C.thinker, size: 44 });
    const lap = S.text(L.lap + ' 1', { x: 1100, y: 480, w: 340, size: 64, weight: 800, align: 'center', color: C.thinker });
    const calc = S.box({ x: 1520, y: 280, w: 300, h: 170, label: L.calc, color: C.calc, size: 44 });
    const a = S.arrow(svg, 1448, 365, 1512, 365, { color: C.soft, width: 6 });
    S.show(sm, S.capAt(1)); S.show(lap, S.capAt(1) + 0.5);
    S.count(lap, { from: 1, to: 3, dec: 0, pre: L.lap + ' ' }, S.capAt(1) + 1.2, 3.0);
    S.draw(a, S.capAt(2), 0.5); S.show(calc, S.capAt(2) + 0.2); S.pulse(calc, S.capAt(2) + 0.9);
  });

  // s06: the five-part map, built one part per caption
  Ch.scene('s06', function (S) {
    const L = S.c.labels;
    const m = S.modelMap({ x: 100, y: 290, w: 1720, h: 250 });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    order.forEach((k, i) => {
      const t = S.capAt(i);
      S.show(m.parts[k], t);
      if (i > 0) S.draw(m.arrows[i - 1], t - 0.3, 0.4);
      S.show(S.text(L.jobs[i], { x: 100 + i * 358, y: 580, w: 288, size: 32, align: 'center', color: C.ink }), t + 0.5);
      S.pulse(m.parts[k], t + 0.9);
    });
    S.pop(S.chip('placeholder', { x: 1532, y: 680, label: L.chip, size: 32 }), S.capAt(4) + 0.9);
  });

  // s07: borrowed numbers vs ours, counted
  Ch.scene('s07', function (S) {
    const L = S.c.labels;
    const hb = S.hbars({ x: 100, y: 250, w: 900, labelW: 420, max: 400, dec: 1, items: [
      { label: L.rows[0].label, value: L.rows[0].value, color: C.reader, dec: 1 }, { label: L.rows[1].label, value: L.rows[1].value, color: C.thinker, dec: 1 }, { label: L.rows[2].label, value: L.rows[2].value, color: C.soft, dec: 1 }] });
    rowReveal(S, hb, 0, S.capAt(0), 1.4);
    S.show(S.text(L.unit, { x: 520, y: 505, w: 600, size: 32, color: C.soft }), S.capAt(0) + 0.6);
    const big = S.text('0', { x: 100, y: 570, w: 1100, size: 120, weight: 800, color: C.reader });
    S.show(big, S.capAt(0) + 0.8); S.count(big, { from: 0, to: L.big, dec: 0, comma: true }, S.capAt(0) + 1.0, 2.2);
    S.show(S.text(L.bigSub, { x: 100, y: 710, w: 1000, size: 36, color: C.soft }), S.capAt(0) + 1.4);
    rowReveal(S, hb, 1, S.capAt(1), 1.2); rowReveal(S, hb, 2, S.capAt(1) + 0.9, 1.2);
    S.pop(S.chip('placeholder', { x: 100, y: 780, label: L.chip, size: 32 }), S.capAt(2));
    S.show(S.note(L.note, { x: 700, y: 765, w: 1120, size: 32, color: C.placeholder }), S.capAt(2) + 0.4);
  });

  // s08: the student analogy, six cards in the part colours
  Ch.scene('s08', function (S) {
    const L = S.c.labels, cols = [C.reader, C.thinker, C.call, C.calc, C.stop, C.talker];
    const cards = L.cards.map((c, i) => S.box({ x: 100 + (i % 3) * 590, y: 230 + Math.floor(i / 3) * 290, w: 540, h: 250, label: c.t, sub: c.p, color: cols[i], size: 50, subSize: 34 }));
    S.stagger(cards, S.capAt(0), 0.45);
    S.pulse(cards[0], S.capAt(1)); S.pulse(cards[1], S.capAt(1) + 0.4);
    S.pulse(cards[2], S.capAt(2)); S.pulse(cards[3], S.capAt(2) + 0.4);
    S.pulse(cards[4], S.capAt(3)); S.pulse(cards[5], S.capAt(3) + 0.4);
  });

  // s09: the three status tags with one example each
  Ch.scene('s09', function (S) {
    const L = S.c.labels, svg = S.svg(), kinds = ['tested', 'untested', 'placeholder'], cols = [C.calc, C.stop, C.talker];
    L.rows.forEach((r, i) => {
      const y = 250 + i * 200, t = S.capAt(i);
      const chip = S.chip(kinds[i], { x: 100, y: y + 45, size: 38 });
      const a = S.arrow(svg, 560, y + 70, 740, y + 70, { color: C.soft, width: 6 });
      const bx = S.box({ x: 760, y: y, w: 1000, h: 140, label: r.name, sub: r.sub, color: cols[i], size: 44, subSize: 32 });
      S.pop(chip, t); S.draw(a, t + 0.6, 0.5); S.show(bx, t + 1.0); S.pulse(bx, t + 1.8);
    });
  });

  // s10: hand-written vs learned
  Ch.scene('s10', function (S) {
    const L = S.c.labels, svg = S.svg();
    const hand = S.chip('hand', { x: 100, y: 230, size: 38 });
    const call = S.box({ x: 100, y: 340, w: 280, h: 120, label: L.call, color: C.call, size: 44 });
    const calc = S.box({ x: 460, y: 320, w: 300, h: 160, label: L.calc, color: C.calc, size: 44 });
    const rep = S.box({ x: 840, y: 340, w: 140, h: 120, label: L.reply, color: C.calc, size: 64 });
    const a1 = S.arrow(svg, 388, 400, 452, 400, { color: C.soft, width: 6 }), a2 = S.arrow(svg, 768, 400, 832, 400, { color: C.soft, width: 6 });
    const ex = S.chip('placeholder', { x: 100, y: 520, label: L.ex, size: 32 });
    const lrn = S.chip('learned', { x: 1100, y: 230, size: 38 });
    const v = S.vec({ x: 1100, y: 340, n: 8, cell: 62, gap: 8, dir: 'h', color: C.learned, seed: 5 });
    const vl = S.text(L.vecLabel, { x: 1100, y: 430, w: 700, size: 36, color: C.ink });
    const pic = S.chip('placeholder', { x: 1100, y: 520, label: L.pic, size: 32 });
    S.pop(hand, S.capAt(0)); S.show(call, S.capAt(0) + 0.5); S.draw(a1, S.capAt(0) + 1.1, 0.4); S.show(calc, S.capAt(0) + 1.4);
    S.draw(a2, S.capAt(0) + 2.0, 0.4); S.show(rep, S.capAt(0) + 2.3); S.pop(ex, S.capAt(0) + 2.6);
    S.pop(lrn, S.capAt(1)); S.show(v, S.capAt(1) + 0.5); S.show(vl, S.capAt(1) + 1.0); S.pop(pic, S.capAt(1) + 1.3);
    S.pulse(calc, S.capAt(2)); S.pulse(v, S.capAt(2) + 0.5);
  });

  // s11: vector (a note card of numbers) and round (one lap)
  Ch.scene('s11', function (S) {
    const L = S.c.labels, svg = S.svg();
    const W = S.letters(L.word, { x: 100, y: 250, size: 90 });
    const v = S.vec({ x: 100, y: 520, n: 8, cell: 60, gap: 8, dir: 'h', color: C.reader, seed: 3 });
    const k = S.curve(svg, W.cx(1), W.cy + 60, 320, 515, { color: C.reader, bend: 50 });
    const vl = S.text(L.vecLabel, { x: 100, y: 600, w: 700, size: 36 });
    const pic = S.chip('placeholder', { x: 100, y: 680, label: L.pic, size: 32 });
    S.sweep(W.cells, S.capAt(0), 1.0); S.draw(k, S.capAt(0) + 1.2, 0.8); S.show(v, S.capAt(0) + 1.6); S.show(vl, S.capAt(0) + 2.0); S.pop(pic, S.capAt(0) + 2.3);
    const xs = [1000, 1290, 1580];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 300, w: 250, h: 130, label: s, color: C.thinker, size: 36 }));
    const ar = [0, 1].map((i) => S.arrow(svg, xs[i] + 256, 365, xs[i + 1] - 6, 365, { color: C.soft, width: 6 }));
    const back = S.path(svg, [[1705, 440], [1705, 500], [1125, 500], [1125, 440]], { color: C.thinker, width: 6, head: 18 });
    const cnt = S.text(L.lap + ' 1', { x: 1000, y: 560, w: 830, size: 90, weight: 800, align: 'center', color: C.thinker });
    S.stagger(bx, S.capAt(1), 0.5); S.draw(ar[0], S.capAt(1) + 0.4, 0.4); S.draw(ar[1], S.capAt(1) + 0.9, 0.4);
    S.draw(back, S.capAt(1) + 1.6, 0.9); S.show(cnt, S.capAt(1) + 1.6);
    S.count(cnt, { from: 1, to: 3, dec: 0, pre: L.lap + ' ' }, S.capAt(1) + 2.6, 2.6);
  });

  // s12: call and reply
  Ch.scene('s12', function (S) {
    const L = S.c.labels, svg = S.svg();
    const cl = S.text(L.callL, { x: 160, y: 255, w: 440, size: 38, weight: 700, align: 'center', color: C.call });
    const call = S.box({ x: 160, y: 320, w: 440, h: 150, label: L.call, color: C.call, size: 60 });
    const calc = S.box({ x: 760, y: 300, w: 400, h: 190, label: L.calcL, color: C.calc, size: 48 });
    const rl = S.text(L.replyL, { x: 1320, y: 255, w: 440, size: 38, weight: 700, align: 'center', color: C.calc });
    const rep = S.box({ x: 1320, y: 320, w: 440, h: 150, label: L.reply, color: C.calc, size: 90 });
    const a1 = S.arrow(svg, 608, 395, 752, 395, { color: C.soft, width: 6 }), a2 = S.arrow(svg, 1168, 395, 1312, 395, { color: C.soft, width: 6 });
    const line = S.text('', { x: 160, y: 590, w: 1600, size: 96, weight: 800, mono: true, align: 'center' });
    const ex = S.chip('placeholder', { x: 760, y: 740, label: L.ex, size: 34 });
    S.show(cl, S.capAt(0)); S.show(call, S.capAt(0) + 0.3); S.draw(a1, S.capAt(0) + 1.3, 0.5); S.show(calc, S.capAt(0) + 1.8);
    S.show(rl, S.capAt(1)); S.draw(a2, S.capAt(1) + 0.2, 0.5); S.show(rep, S.capAt(1) + 0.7);
    S.show(line, S.capAt(1) + 1.5); S.type(line, L.line, S.capAt(1) + 1.6, 1.4); S.pop(ex, S.capAt(1) + 3.0);
    S.pulse(call, S.capAt(2)); S.pulse(calc, S.capAt(2) + 0.4);
  });

  // s13: practice (try, told the answer, nudge) and kept-aside questions
  Ch.scene('s13', function (S) {
    const L = S.c.labels, svg = S.svg();
    const xs = [100, 400, 700];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 300, w: 250, h: 130, label: s, color: C.thinker, size: 34 }));
    const ar = [0, 1].map((i) => S.arrow(svg, xs[i] + 256, 365, xs[i + 1] - 6, 365, { color: C.soft, width: 6 }));
    const back = S.path(svg, [[825, 440], [825, 500], [225, 500], [225, 440]], { color: C.thinker, width: 6, head: 18 });
    const upd = S.text(L.upd + ' 1', { x: 100, y: 540, w: 850, size: 80, weight: 800, align: 'center', color: C.thinker });
    const pic = S.chip('placeholder', { x: 100, y: 700, label: L.pic, size: 32 });
    const pp = S.card({ x: 1000, y: 570, w: 360, h: 190, fill: '#fff', color: C.thinker, r: 16 });
    const ap = S.card({ x: 1460, y: 570, w: 360, h: 190, fill: '#fff', color: C.soft, r: 16 });
    const ppl = S.text(L.practice, { x: 1000, y: 515, w: 360, size: 34, weight: 700, align: 'center', color: C.thinker });
    const apl = S.text(L.aside, { x: 1460, y: 515, w: 360, size: 34, weight: 700, align: 'center', color: C.soft });
    const cards = [];
    for (let i = 0; i < 8; i++) cards.push(S.card({ x: 1000 + i * 100, y: 300, w: 70, h: 90, fill: '#fff', color: C.ink, r: 10 }));
    S.stagger(bx, S.capAt(0), 0.4); S.draw(ar[0], S.capAt(0) + 0.3, 0.4); S.draw(ar[1], S.capAt(0) + 0.7, 0.4);
    S.draw(back, S.capAt(0) + 1.3, 0.8); S.show(upd, S.capAt(0) + 1.3); S.pop(pic, S.capAt(0) + 1.6);
    S.count(upd, { from: 1, to: 3, dec: 0, pre: L.upd + ' ' }, S.capAt(0) + 2.3, 2.4);
    S.show(pp, S.capAt(0) + 3); S.show(ppl, S.capAt(0) + 3); S.sweep(cards, S.capAt(0) + 3.2, 1.0);
    for (let i = 0; i < 6; i++) S.move(cards[i], S.capAt(0) + 4.6 + i * 0.25, 0.8, { x: 30 + i * 55 - i * 100, y: 290 });
    S.show(ap, S.capAt(1)); S.show(apl, S.capAt(1));
    for (let i = 6; i < 8; i++) S.move(cards[i], S.capAt(1) + 0.6 + (i - 6) * 0.4, 0.9, { x: 500 + (i - 6) * 90 - i * 100, y: 290 });
  });

  // s14: score, copy
  Ch.scene('s14', function (S) {
    const L = S.c.labels;
    const num = S.text('0.00', { x: 100, y: 230, w: 800, size: 170, weight: 800, color: C.tested });
    S.show(num, S.capAt(0)); S.count(num, { from: 0, to: L.num, dec: 2 }, S.capAt(0) + 0.3, 2.4);
    S.show(S.text(L.outOf, { x: 100, y: 430, w: 800, size: 46, weight: 700 }), S.capAt(0) + 1.2);
    S.show(S.text(L.over, { x: 100, y: 495, w: 800, size: 38, color: C.soft }), S.capAt(0) + 1.5);
    S.pop(S.chip('tested', { x: 100, y: 570, size: 36 }), S.capAt(0) + 2.0);
    const bx = L.copies.map((l, i) => S.box({ x: 1000 + (i % 3) * 280, y: 260 + Math.floor(i / 3) * 130, w: 250, h: 100, label: L.copyW + ' ' + l, color: C.thinker, size: 36 }));
    S.stagger(bx, S.capAt(1), 0.4);
    S.pop(S.chip('placeholder', { x: 1000, y: 540, label: L.copyNote, size: 32 }), S.capAt(1) + 2.6);
    const n = S.note(L.careful, { x: 100, y: 680, w: 1700, size: 38, color: C.untested });
    S.show(n, S.capAt(2)); S.pulse(n, S.capAt(2) + 0.6);
  });

  // s15: plain model yardstick
  Ch.scene('s15', function (S) {
    const L = S.c.labels;
    const hb = S.hbars({ x: 100, y: 280, w: 900, labelW: 300, rowH: 80, gap: 40, max: 100, dec: 2, valueSize: 56, labelSize: 48, items: [
      { label: L.rows[0].label, value: L.rows[0].value, color: C.thinker }, { label: L.rows[1].label, value: L.rows[1].value, color: C.placeholder }] });
    rowReveal(S, hb, 1, S.capAt(0) + 0.6, 1.6);
    S.show(S.text(L.unit, { x: 400, y: 500, w: 700, size: 34, color: C.soft }), S.capAt(0) + 1.0);
    rowReveal(S, hb, 0, S.capAt(1), 1.8);
    S.pop(S.chip('tested', { x: 100, y: 580, size: 36 }), S.capAt(1) + 1.6);
    const n = S.note(L.care, { x: 100, y: 680, w: 1700, size: 38, color: C.untested });
    S.show(n, S.capAt(2)); S.pulse(n, S.capAt(2) + 0.6);
  });

  // s16-s18: contents, one row per caption
  const kindOf = { ch06: 'untested', ch07: 'placeholder', ch11: 'placeholder', ch12: 'untested' };
  const accOf = { ch01: C.thinker, ch03: C.reader, ch04: C.thinker, ch05: C.call, ch06: C.stop, ch07: C.talker, ch09: C.thinker };
  const contents = (S) => {
    S.c.labels.rows.forEach((r, i) => {
      const y = 225 + i * 120, t = S.capAt(i), col = accOf[r.id] || C.soft;
      const b = S.box({ x: 100, y: y, w: 150, h: 90, label: r.id, color: col, size: 38 });
      const tx = S.text(r.title, { x: 290, y: y + 22, w: 1100, size: 42, weight: 700 });
      S.show(b, t); S.show(tx, t + 0.2); S.pulse(b, t + 0.6);
      if (r.cl) S.pop(S.chip(kindOf[r.id], { x: 1420, y: y + 22, label: r.cl, size: 30 }), t + 0.8);
    });
  };
  Ch.scene('s16', contents); Ch.scene('s17', contents); Ch.scene('s18', contents);

  // s19: the honesty promise
  Ch.scene('s19', function (S) {
    const L = S.c.labels, svg = S.svg();
    const num = S.text('0.00', { x: 100, y: 240, w: 480, size: 110, weight: 800, color: C.ink });
    const a = S.arrow(svg, 600, 300, 700, 300, { color: C.soft, width: 6 });
    const tc = S.card({ x: 710, y: 255, w: 760, h: 90, fill: C.card, color: C.line, r: 14 });
    const tt = S.text(L.tag, { x: 740, y: 278, w: 720, size: 34, mono: true, color: C.ink });
    S.show(num, S.capAt(0)); S.count(num, { from: 0, to: L.num, dec: 2 }, S.capAt(0) + 0.3, 1.6);
    S.draw(a, S.capAt(0) + 1.4, 0.4); S.show(tc, S.capAt(0) + 1.7); S.show(tt, S.capAt(0) + 1.9);
    const cA = S.chip('placeholder', { x: 100, y: 470, label: L.chipA, size: 36 }), cB = S.chip('placeholder', { x: 520, y: 470, label: L.chipB, size: 36 });
    S.pop(cA, S.capAt(1)); S.pop(cB, S.capAt(1) + 0.5);
    const cC = S.chip('untested', { x: 100, y: 640, label: L.chipC, size: 36 }), cD = S.chip('placeholder', { x: 560, y: 640, label: L.chipD, size: 36 });
    const rel = S.box({ x: 920, y: 620, w: 420, h: 100, label: L.rel, color: C.line, size: 38, fill: '#FAF6EE' });
    S.pop(cC, S.capAt(2)); S.pop(cD, S.capAt(2) + 0.5); S.show(rel, S.capAt(2) + 1.0);
  });

  // s20: what to remember
  Ch.scene('s20', function (S) {
    const L = S.c.labels, cols = [C.thinker, C.reader, C.tested];
    L.cards.forEach((c, i) => {
      const y = 250 + i * 190, t = S.capAt(i);
      const b = S.box({ x: 160, y: y, w: 1600, h: 140, label: c.t, color: cols[i], size: 54 });
      const n = S.text(c.n, { x: 210, y: y + 28, w: 80, size: 80, weight: 800, color: cols[i] });
      S.show(b, t); S.show(n, t + 0.2); S.pulse(b, t + 0.7);
    });
  });
});
