Kit.chapter('ch00', function (Ch) {
  const C = Kit.C;
  const rowReveal = (S, hb, i, t, dur) => { const r = hb.rows[i]; S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 }); return S.grow(r.b, t + 0.3, dur, r.val, { dec: r.it.dec == null ? 2 : r.it.dec, suf: r.it.suf || '', comma: true }); };

  // Illustration tag ("picture only", "made-up example"): a dashed pill in dark ink, so it is never read as a status chip.
  // Grey (placeholder) stays the status colour for "does not exist yet / plan only" and nothing else.
  const picTag = (S, label, o) => {
    const e = S.chip('placeholder', Object.assign({ label: label, color: C.ink }, o));
    e.style.borderColor = C.soft; e.style.borderStyle = 'dashed';
    return e;
  };

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

  // s02: goals 1 and 2 (caption 1 names goal 1, caption 2 gives its evidence, caption 3 is goal 2)
  Ch.scene('s02', function (S) {
    // Goal boxes are neutral (they are goals, not statuses); the chips carry the status. Both chips are green: a result exists
    // (for goal 2 only for older models, hence the label "partly shown"). Amber is kept for "built, never tested".
    const L = S.c.labels, svg = S.svg(), xs = [100, 1000];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 330, w: 820, h: 240, label: s.t, color: C.ink, size: 52 }));
    const ch = L.steps.map((s, i) => S.chip('tested', { x: xs[i], y: 620, label: s.cl, size: 36 }));
    const a = S.arrow(svg, 928, 450, 992, 450, { color: C.soft, width: 6 });
    S.show(bx[0], S.capAt(0)); S.pop(ch[0], S.capAt(1) + 0.8);
    S.show(bx[1], S.capAt(2)); S.draw(a, S.capAt(2) - 0.3, 0.4); S.pop(ch[1], S.capAt(2) + 0.8);
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
      S.show(S.text(L.jobs[i], { x: 100 + i * 358, y: 580, w: 288, size: 32, align: 'center', color: C.ink }), t + 0.2, { dur: 0.4 });
      S.pulse(m.parts[k], t + 0.9);
    });
    S.pop(S.chip('untested', { x: 1143, y: 680, label: L.chipStop, size: 32 }), S.capAt(3) + 0.9);
    S.pop(S.chip('placeholder', { x: 1528, y: 680, label: L.chip, size: 32 }), S.capAt(4) + 0.9);
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
      // chips share one width so each arrow can leave its chip's right edge (x 534) and end at its box (x 759, box starts at 760)
      const chip = S.chip(kinds[i], { x: 100, y: y + 38, w: 430, size: 38 }); chip.style.justifyContent = 'center';
      const a = S.arrow(svg, 534, y + 70, 759, y + 70, { color: C.soft, width: 6 });
      const bx = S.box({ x: 760, y: y, w: 1000, h: 140, label: r.name, sub: r.sub, color: cols[i], size: 44, subSize: 32 });
      S.pop(chip, t); S.draw(a, t + 0.6, 0.5); S.show(bx, t + 1.0); S.pulse(bx, t + 1.8);
    });
  });

  // s11: vector (a note card of numbers) and round (one lap)
  Ch.scene('s11', function (S) {
    const L = S.c.labels, svg = S.svg();
    const W = S.letters(L.word, { x: 100, y: 250, size: 90 });
    const v = S.vec({ x: 100, y: 520, n: 8, cell: 60, gap: 8, dir: 'h', color: C.reader, seed: 3 });
    const k = S.curve(svg, W.cx(1), W.cy + 60, 320, 515, { color: C.reader, bend: 50 });
    const vl = S.text(L.vecLabel, { x: 100, y: 600, w: 700, size: 36 });
    const pic = picTag(S, L.pic, { x: 100, y: 680, size: 32 });
    S.sweep(W.cells, S.capAt(0), 1.0); S.draw(k, S.capAt(0) + 1.2, 0.8); S.show(v, S.capAt(0) + 1.6); S.show(vl, S.capAt(0) + 2.0); S.pop(pic, S.capAt(0) + 2.3);
    const xs = [1000, 1290, 1580];
    const bx = L.steps.map((s, i) => S.box({ x: xs[i], y: 300, w: 250, h: 130, label: s, color: C.thinker, size: 36 }));
    const ar = [0, 1].map((i) => S.arrow(svg, xs[i] + 256, 365, xs[i + 1] - 6, 365, { color: C.soft, width: 6 }));
    const back = S.path(svg, [[1705, 440], [1705, 500], [1125, 500], [1125, 440]], { color: C.thinker, width: 6, head: 18 });
    const cnt = S.text(L.lap + ' 1', { x: 1000, y: 560, w: 830, size: 90, weight: 800, align: 'center', color: C.thinker });
    S.stagger(bx, S.capAt(1), 0.5); S.draw(ar[0], S.capAt(1) + 0.4, 0.4); S.draw(ar[1], S.capAt(1) + 0.9, 0.4);
    S.draw(back, S.capAt(1) + 1.6, 0.9); S.show(cnt, S.capAt(1) + 1.6);
    S.count(cnt, { from: 1, to: 3, dec: 0, pre: L.lap + ' ' }, S.capAt(1) + 2.6, 2.6);
    S.pop(picTag(S, L.pic, { x: 1000, y: 680, size: 32 }), S.capAt(1) + 2.0);
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
    const ex = picTag(S, L.ex, { x: 760, y: 740, size: 34 });
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
    const pic = picTag(S, L.pic, { x: 100, y: 700, size: 32 });   // the one 'picture only' tag for the whole scene
    // practice pile is 400 wide: six cards (70 wide, 56 apart = 350) sit inside it with 22 px padding on both sides
    const pp = S.card({ x: 1000, y: 570, w: 400, h: 190, fill: '#fff', color: C.thinker, r: 16 });
    const ap = S.card({ x: 1460, y: 570, w: 360, h: 190, fill: '#fff', color: C.soft, r: 16 });
    const ppl = S.text(L.practice, { x: 1000, y: 515, w: 400, size: 34, weight: 700, align: 'center', color: C.thinker });
    const apl = S.text(L.aside, { x: 1460, y: 515, w: 360, size: 34, weight: 700, align: 'center', color: C.soft });
    const cards = [];
    for (let i = 0; i < 8; i++) cards.push(S.card({ x: 1000 + i * 100, y: 300, w: 70, h: 90, fill: '#fff', color: C.ink, r: 10 }));
    S.stagger(bx, S.capAt(0), 0.4); S.draw(ar[0], S.capAt(0) + 0.3, 0.4); S.draw(ar[1], S.capAt(0) + 0.7, 0.4);
    S.draw(back, S.capAt(0) + 1.3, 0.8); S.show(upd, S.capAt(0) + 1.3); S.pop(pic, S.capAt(0) + 1.6);
    S.count(upd, { from: 1, to: 3, dec: 0, pre: L.upd + ' ' }, S.capAt(0) + 2.3, 2.4);
    S.show(pp, S.capAt(0) + 3); S.show(ppl, S.capAt(0) + 3); S.sweep(cards, S.capAt(0) + 3.2, 1.0);
    for (let i = 0; i < 6; i++) S.move(cards[i], S.capAt(0) + 4.6 + i * 0.25, 0.8, { x: 25 - 44 * i, y: 320 });
    S.show(ap, S.capAt(1)); S.show(apl, S.capAt(1));
    for (let i = 6; i < 8; i++) S.move(cards[i], S.capAt(1) + 0.6 + (i - 6) * 0.4, 0.9, { x: 560 + (i - 6) * 90 - 100 * i, y: 320 });
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
    S.pop(picTag(S, L.copyNote, { x: 1000, y: 540, size: 32 }), S.capAt(1) + 2.6);
    const n = S.note(L.careful, { x: 100, y: 680, w: 1700, size: 38, color: C.soft });
    S.show(n, S.capAt(2)); S.pulse(n, S.capAt(2) + 0.6);
  });

  // s15: plain model yardstick
  Ch.scene('s15', function (S) {
    const L = S.c.labels;
    const hb = S.hbars({ x: 100, y: 280, w: 900, labelW: 300, rowH: 80, gap: 40, max: 100, dec: 2, valueSize: 56, labelSize: 48, items: [
      { label: L.rows[0].label, value: L.rows[0].value, color: C.thinker }, { label: L.rows[1].label, value: L.rows[1].value, color: C.placeholder }] });
    rowReveal(S, hb, 1, S.capAt(0) + 0.6, 1.6);
    S.show(S.text(L.unit, { x: 400, y: 500, w: 700, size: 34, color: C.soft }), S.capAt(0) + 1.0);
    rowReveal(S, hb, 0, S.capAt(1) - 2.3, 1.8);   // the Ours bar lands before caption 2 (which states 73.01) fades in
    S.pop(S.chip('tested', { x: 100, y: 580, size: 36 }), S.capAt(1) + 1.0);
    const n = S.note(L.care, { x: 100, y: 680, w: 1700, size: 38, color: C.soft });
    S.show(n, S.capAt(2)); S.pulse(n, S.capAt(2) + 0.6);
  });

  // s19: the honesty promise
  Ch.scene('s19', function (S) {
    const L = S.c.labels, svg = S.svg();
    // block 1: one real number traced to its source (the arrow leaves the numeral's right edge and ends at the file card)
    const num = S.text('0.00', { x: 100, y: 250, w: 330, size: 110, weight: 800, color: C.ink });
    const a = S.arrow(svg, 380, 317, 539, 317, { color: C.soft, width: 6 });
    const tc = S.card({ x: 540, y: 251, w: 600, h: 132, fill: C.card, color: C.line, r: 14 });
    const tt = S.text(L.tag, { x: 570, y: 266, w: 680, size: 38, mono: true, color: C.ink });
    const ts = S.text(L.tagSub, { x: 570, y: 322, w: 680, size: 34, color: C.soft });
    S.show(num, S.capAt(0)); S.count(num, { from: 0, to: L.num, dec: 2 }, S.capAt(0) + 0.3, 1.6);
    S.show(S.text(L.numL, { x: 100, y: 395, w: 900, size: 32, color: C.soft }), S.capAt(0) + 1.0);
    S.draw(a, S.capAt(0) + 2.0, 0.4); S.show(tc, S.capAt(0) + 2.3); S.show(tt, S.capAt(0) + 2.5); S.show(ts, S.capAt(0) + 2.7);
    // block 2: illustration tags, under a lead-in so they cannot be read as describing the real score above
    S.show(S.text(L.tagsLead, { x: 100, y: 520, w: 1200, size: 36, weight: 700, color: C.soft }), S.capAt(1));
    const cA = picTag(S, L.chipA, { x: 100, y: 580, size: 38 }), cB = picTag(S, L.chipB, { x: 430, y: 580, size: 38 });
    S.pop(cA, S.capAt(1) + 0.5); S.pop(cB, S.capAt(1) + 1.0);
    // block 3: status pills (amber, grey) and the released count, all in the one pill style
    const cC = S.chip('untested', { x: 100, y: 730, label: L.chipC, size: 38 }), cD = S.chip('placeholder', { x: 544, y: 730, label: L.chipD, size: 38 });
    const rel = S.chip('placeholder', { x: 822, y: 730, label: L.rel, size: 38 });
    S.pop(cC, S.capAt(2)); S.pop(cD, S.capAt(2) + 0.5); S.pop(rel, S.capAt(2) + 1.0);
  });
});
