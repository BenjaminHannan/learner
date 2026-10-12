Kit.chapter('ch07', function (Ch) {
  const C = Kit.C;
  const PINK = '#F9C5DA';            // pale talker pink for copied cells
  const num = (s) => parseFloat(s);   // number at the start of a label string
  const tail = (s) => s.slice(String(parseFloat(s)).length);

  // s01: where we are. The map with the talker lit, then what goes into the talker.
  Ch.scene('s01', function (S) {
    const c = S.c, L = c.labels;
    const m = S.modelMap({ x: 100, y: 215, w: 1720, h: 150, highlight: 'talker' });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.03), 0.15);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.06) + i * 0.12, 0.3));
    S.pulse(m.parts.talker, S.at(0.09));

    const qBox = S.box({ x: 100, y: 450, w: 470, h: 110, label: L.question, color: C.reader, size: 36 });
    const rBox = S.box({ x: 100, y: 640, w: 470, h: 110, label: L.replies, color: C.calc, size: 36 });
    const stLab = S.text(L.state, { x: 700, y: 392, w: 520, size: 32, weight: 700, color: C.thinker });
    const vec = S.vec({ x: 700, y: 440, n: 8, cell: 46, gap: 6, color: C.thinker, seed: 7 });
    const tk = S.box({ x: 900, y: 580, w: 400, h: 160, label: L.talker, sub: L.talkerSub, color: C.talker, size: 52, subSize: 32 });
    const ansLab = S.text(L.answer, { x: 1460, y: 535, w: 300, align: 'center', size: 32, color: C.soft });
    const ans = S.box({ x: 1460, y: 580, w: 300, h: 160, label: L.ten, color: C.talker, size: 96 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 574, 505, 896, 628, { color: C.soft, width: 5 });
    const a2 = S.arrow(svg, 574, 695, 896, 690, { color: C.soft, width: 5 });
    const a3 = S.arrow(svg, 1000, 492, 1000, 576, { color: C.thinker, width: 9, head: 28 });
    const a4 = S.arrow(svg, 1304, 660, 1456, 660, { color: C.talker, width: 6 });
    const pLab = S.text(L.points, { x: 1030, y: 515, w: 200, size: 34, weight: 700, color: C.thinker });
    const tag = S.chip('placeholder', { x: 1400, y: 760, label: L.tag });
    const stand = S.chip('placeholder', { x: 900, y: 760, label: L.chip });

    S.show(tk, S.capAt(1));
    S.show(stLab, S.capAt(2));
    S.show(vec, S.capAt(2) + 0.2);
    S.stagger([qBox, rBox], S.capAt(2) + 0.7, 0.4);
    S.draw(a1, S.capAt(2) + 1.6, 0.7);
    S.draw(a2, S.capAt(2) + 2.0, 0.7);
    S.draw(a3, S.capAt(3), 0.7);
    S.show(pLab, S.capAt(3) + 0.5);
    S.draw(a4, S.capAt(3) + 1.3, 0.6);
    S.pop(ans, S.capAt(3) + 1.9);
    S.show(ansLab, S.capAt(3) + 1.9);
    S.show(tag, S.capAt(3) + 2.4);
    S.pop(stand, S.capAt(3) + 2.8);
  });

  // s02: three ways to write an answer, one card each (all made-up examples).
  Ch.scene('s02', function (S) {
    const c = S.c, L = c.labels;
    const xs = [100, 686, 1272];
    const cards = [], titles = [], froms = [], results = [], arrows = [];
    const svgHolder = [];
    xs.forEach((x, i) => {
      cards.push(S.card({ x, y: 230, w: 546, h: 400, fill: C.card, color: C.talker, r: 22 }));
      titles.push(S.text(L.titles[i], { x: x + 20, y: 254, w: 506, size: 48, weight: 800, align: 'center', color: C.talker }));
    });
    const L0 = S.letters(L.from[0], { x: xs[0] + 103, y: 360, size: 36, gap: 4 });
    const L1 = S.letters(L.from[1], { x: xs[1] + 26, y: 360, size: 32, gap: 4 });
    const t2 = S.text(L.from[2], { x: xs[2] + 20, y: 366, w: 506, size: 36, italic: true, align: 'center', color: C.soft });
    xs.forEach((x, i) => {
      results.push(S.box({ x: x + 123, y: 505, w: 300, h: 100, label: L.to[i], color: C.talker, size: 56 }));
    });
    const svg = S.svg();
    xs.forEach((x) => arrows.push(S.arrow(svg, x + 273, 430, x + 273, 500, { color: C.soft, width: 6, head: 20 })));
    const gone = S.note(L.gone, { x: 100, y: 690, w: 1720, color: C.hand });
    const tag = S.chip('placeholder', { x: 100, y: 775, label: L.tag });

    S.stagger(cards, S.capAt(0), 0.25);
    S.stagger(titles, S.capAt(0) + 0.3, 0.25);
    // span copy: letters appear, "10" is lit, arrow, result
    S.sweep(L0.cells, S.capAt(1), 0.9);
    S.tint(L0.byIndex[10], S.capAt(1) + 1.2, { fill: PINK, dur: 0.4 });
    S.tint(L0.byIndex[11], S.capAt(1) + 1.2, { fill: PINK, dur: 0.4 });
    S.draw(arrows[0], S.capAt(1) + 1.7, 0.5);
    S.pop(results[0], S.capAt(1) + 2.3);
    // word pointer: "Tom" is lit
    S.sweep(L1.cells, S.capAt(2), 1.0);
    [0, 1, 2].forEach((k) => S.tint(L1.byIndex[k], S.capAt(2) + 1.3, { fill: PINK, dur: 0.4 }));
    S.draw(arrows[1], S.capAt(2) + 1.8, 0.5);
    S.pop(results[1], S.capAt(2) + 2.4);
    // letter slots: not in the text
    S.show(t2, S.capAt(3));
    S.draw(arrows[2], S.capAt(3) + 0.9, 0.5);
    S.pop(results[2], S.capAt(3) + 1.5);
    S.show(gone, S.at(0.72));
    S.show(tag, S.at(0.72) + 0.3);
  });

  // s03: span copy on "add 7 3 = 10": pointer on the 0, step left to the 1, stop head at the space.
  Ch.scene('s03', function (S) {
    const c = S.c, L = c.labels;
    const R1 = S.letters(L.reply1, { x: 170, y: 215, size: 60, color: C.soft });
    const R2 = S.letters(L.reply2, { x: 170, y: 325, size: 80 });
    S.sweep(R1.cells, S.at(0.03), 0.8);
    S.sweep(R2.cells, S.at(0.05), 1.0);
    const ptr = S.box({ x: R2.cx(11) - 90, y: 450, w: 180, h: 60, label: L.ptr, color: C.thinker, size: 30 });
    const stop = S.box({ x: R2.cx(9) - 105, y: 450, w: 210, h: 60, label: L.stop, color: C.stop, size: 30 });
    const o0 = S.box({ x: 1250, y: 321, w: 110, h: 110, label: L.out[0], color: C.talker, size: 60 });
    const o1 = S.box({ x: 1380, y: 321, w: 110, h: 110, label: L.out[1], color: C.talker, size: 60 });
    const fin = S.box({ x: 1250, y: 540, w: 240, h: 150, label: L.final, color: C.talker, size: 100 });
    const svg = S.svg();
    const aRow = S.arrow(svg, 930, 376, 1236, 376, { color: C.soft, width: 5 });
    const aFlip = S.arrow(svg, 1370, 436, 1370, 536, { color: C.hand, width: 6 });
    const tag = S.chip('placeholder', { x: 1380, y: 205, label: L.tag });
    const learned = S.chip('learned', { x: 170, y: 570, label: L.learnedChip });
    const hand = S.chip('hand', { x: 170, y: 650, label: L.handChip });
    S.show(tag, S.at(0.06));

    // 1: pointer lands on the 0
    S.show(ptr, S.capAt(0) + 1.3);
    S.tint(R2.byIndex[11], S.capAt(0) + 2.0, { fill: PINK, dur: 0.4 });
    S.draw(aRow, S.capAt(0) + 2.2, 0.6);
    S.pop(o0, S.capAt(0) + 2.9);
    // 2: step left, take the 1
    S.move(ptr, S.capAt(1), 0.8, { x: R2.cx(10) - R2.cx(11) });
    S.tint(R2.byIndex[10], S.capAt(1) + 0.8, { fill: PINK, dur: 0.4 });
    S.pop(o1, S.capAt(1) + 1.3);
    // 3: a space on the left, the stop head says stop
    S.hide(ptr, S.capAt(2), 0.3);
    S.show(stop, S.capAt(2) + 0.4);
    S.pulse(stop, S.capAt(2) + 1.1);
    // 4: flip
    S.draw(aFlip, S.capAt(3), 0.6);
    S.pop(fin, S.capAt(3) + 0.7);
    S.show(learned, S.capAt(3) + 1.7);
    S.show(hand, S.capAt(3) + 2.2);
  });

  // s04: how often (bars), the three hand-written pieces, and the one-learned-writer plan.
  Ch.scene('s04', function (S) {
    const c = S.c, L = c.labels;
    const hb = S.hbars({
      x: 100, y: 270, w: 340, labelW: 360, rowH: 56, gap: 40, max: 100, labelSize: 34, valueSize: 42, valueW: 200,
      items: [
        { label: L.bars[0].label, value: L.bars[0].value, dec: 1, suf: '%', color: C.talker },
        { label: L.bars[1].label, value: L.bars[1].value, dec: 0, suf: '%', color: C.talker },
      ],
    });
    const chip = S.chip('tested', { x: 100, y: 450, label: L.chip });
    const barNote = S.note(L.barNote, { x: 100, y: 530, w: 880, size: 34, color: C.warn });
    const hChip = S.chip('hand', { x: 1100, y: 205, label: L.handChip });
    const hBoxes = L.hand.map((t, i) => S.box({ x: 1100, y: 275 + i * 95, w: 700, h: 76, label: t, color: C.hand, size: 34 }));
    const plan = S.box({ x: 1100, y: 600, w: 700, h: 100, label: L.plan, color: C.placeholder, size: 38, fill: '#EEF0F3' });
    const svg = S.svg();
    const ar = S.arrow(svg, 1450, 560, 1450, 596, { color: C.soft, width: 6, head: 20 });
    const planChip = S.chip('placeholder', { x: 1100, y: 730, label: L.planChip });

    hb.reveal(S.capAt(0) + 0.3, 0.7, 1.4);
    S.show(chip, S.capAt(0) + 2.6);
    S.show(barNote, S.capAt(1));
    S.pulse(hb.rows[0].val, S.capAt(1) + 0.3);
    S.show(hChip, S.capAt(2));
    S.stagger(hBoxes, S.capAt(2) + 0.4, 0.5);
    S.draw(ar, S.capAt(3), 0.5);
    S.show(plan, S.capAt(3) + 0.5);
    S.pop(planChip, S.capAt(3) + 1.3);
  });

  // s05: nine slots; "yes" fills s, e, y, end; the code flips it.
  Ch.scene('s05', function (S) {
    const c = S.c, L = c.labels;
    const x0 = 320, step = 144, y0 = 340;
    const slots = [];
    for (let i = 0; i < 9; i++) slots.push(S.box({ x: x0 + i * step, y: y0, w: 120, h: 130, label: '', color: C.line, size: 40 }));
    const marks = L.slots.map((t, i) => S.text(t, { x: x0 + i * step, y: y0 + (i === 3 ? 40 : 20), w: 120, size: i === 3 ? 40 : 72, weight: 800, mono: true, align: 'center', color: i === 3 ? C.soft : C.talker }));
    const order = S.text(L.order, { x: x0, y: 275, w: 900, size: 36, color: C.soft });
    const tag = S.chip('placeholder', { x: 1500, y: 270, label: L.tag });
    const word = S.box({ x: 720, y: 590, w: 480, h: 140, label: '', color: C.talker, size: 40 });
    const yes = S.text('', { x: 720, y: 616, w: 480, size: 84, weight: 800, mono: true, align: 'center', color: C.talker });
    const flipNote = S.note(L.flip, { x: 1240, y: 630, w: 520, color: C.hand, size: 34 });
    const svg = S.svg();
    const ar = S.arrow(svg, 960, 482, 960, 586, { color: C.hand, width: 7, head: 24 });

    S.sweep(slots, S.capAt(0) + 0.2, 1.4);
    S.show(tag, S.capAt(0) + 1.8);
    // each place can pick or copy: a ripple of pulses
    slots.forEach((s, i) => S.pulse(s, S.capAt(1) + 0.4 + i * 0.22));
    S.show(order, S.capAt(2));
    marks.forEach((m, i) => S.pop(m, S.capAt(2) + 0.5 + i * 0.9));
    S.draw(ar, S.capAt(2) + 4.4, 0.6);
    S.show(word, S.capAt(2) + 5.0);
    S.type(yes, L.word, S.capAt(2) + 5.3, 0.8);
    S.show(flipNote, S.capAt(2) + 5.8);
  });

  // s06: the 8-letter limit (nine places: 8 letters + end mark), the zero count, and the 35-letter path.
  Ch.scene('s06', function (S) {
    const c = S.c, L = c.labels;
    const x0 = 170, step = 112, y0 = 215;
    const letters = [...L.word];
    const boxes = [];
    for (let i = 0; i < 8; i++) boxes.push(S.box({ x: x0 + i * step, y: y0, w: 96, h: 110, label: letters[i], color: C.talker, size: 56 }));
    const endBox = S.box({ x: x0 + 8 * step, y: y0, w: 96, h: 110, label: L.end, color: C.soft, size: 32, fill: '#EEF0F3' });
    const cutBox = S.box({ x: x0 + 9 * step, y: y0, w: 96, h: 110, label: letters[8], color: C.warn, size: 56 });
    const cutLab = S.text(L.cutLabel, { x: x0 + 9 * step - 40, y: 335, w: 176, align: 'center', size: 32, weight: 700, color: C.warn });
    const tag = S.chip('placeholder', { x: 1420, y: 245, label: L.tag });
    const zeroOf = S.text('0 of', { x: 170, y: 410, w: 240, size: 100, weight: 800, color: C.ink });
    const zeroN = S.text('', { x: 420, y: 410, w: 700, size: 100, weight: 800, color: C.talker });
    const zeroLab = S.text(L.zeroLabel, { x: 170, y: 530, w: 900, size: 36, color: C.soft });
    const hb = S.hbars({
      x: 170, y: 640, w: 640, labelW: 230, rowH: 52, gap: 24, max: 35, labelSize: 34, valueSize: 38, valueW: 260,
      items: [
        { label: L.bars[0].label, value: L.bars[0].value, dec: 0, suf: ' ' + L.unit, color: C.soft },
        { label: L.bars[1].label, value: L.bars[1].value, dec: 0, suf: ' ' + L.unit, color: C.talker },
      ],
    });
    const chipToday = S.chip('hand', { x: 1360, y: 636, label: L.chipToday, color: C.soft });
    const chipB3 = S.chip('untested', { x: 1360, y: 712, label: L.chipB3 });

    S.sweep(boxes, S.capAt(0) + 0.3, 1.6);
    S.show(endBox, S.capAt(0) + 2.0);
    S.show(cutBox, S.capAt(0) + 3.0);
    S.tl.to(cutBox, { autoAlpha: 0.4, duration: 0.6, ease: 'power1.inOut' }, S.capAt(0) + 4.2);
    S.show(cutLab, S.capAt(0) + 3.6);
    S.show(tag, S.capAt(0) + 4.4);
    S.show(zeroOf, S.capAt(1));
    S.show(zeroN, S.capAt(1) + 0.1);
    S.count(zeroN, { from: 0, to: 200000, dec: 0, comma: true }, S.capAt(1) + 0.3, 2.2);
    S.show(zeroLab, S.capAt(1) + 1.2);
    S.pulse(cutLab, S.capAt(2) + 0.3);
    S.pulse(cutBox, S.capAt(2) + 0.3);
    hb.reveal(S.capAt(3), 0.8, 1.3);
    S.pop(chipToday, S.capAt(3) + 1.5);
    S.pop(chipB3, S.capAt(3) + 2.3);
    S.pulse(chipB3, S.capAt(4) + 0.3);
  });

  // s07: size strip, 271.0 : 102.1 : 25 drawn to scale; the 25M English talker is a grey dashed placeholder.
  Ch.scene('s07', function (S) {
    const c = S.c, L = c.labels;
    const b = L.bars, total = b[0].value + b[1].value + b[2].value, k = 1680 / total;
    const w1 = Math.round(b[0].value * k), w2 = Math.round(b[1].value * k), w3 = Math.round(b[2].value * k);
    const x1 = 120, x2 = x1 + w1, x3 = x2 + w2, y = 330, h = 110;
    const c1 = S.card({ x: x1, y, w: w1, h, fill: '#DDF1F1', color: C.reader, r: 14 });
    const c2 = S.card({ x: x2, y, w: w2, h, fill: '#E4E2FB', color: C.thinker, r: 14 });
    const c3 = S.card({ x: x3, y, w: w3, h, fill: '#EEF0F3', color: C.placeholder, r: 14 });
    c3.style.borderStyle = 'dashed';
    const nm = (x, w, v, col) => S.text('', { x, y: y + 24, w, size: v < 50 ? 40 : 60, weight: 800, align: 'center', color: C.ink });
    const n1 = nm(x1, w1, b[0].value), n2 = nm(x2, w2, b[1].value), n3 = nm(x3, w3, b[2].value);
    const l1 = S.text(b[0].label, { x: x1, y: 455, w: w1, size: 34, weight: 700, align: 'center', color: C.reader });
    const l2 = S.text(b[1].label, { x: x2, y: 455, w: w2, size: 34, weight: 700, align: 'center', color: C.thinker });
    const l3 = S.text(b[2].label, { x: 1380, y: 600, w: 420, size: 34, weight: 700, align: 'right', color: C.soft });
    const chip = S.chip('placeholder', { x: 1610, y: 655, label: L.chip });
    const totalEl = S.text('', { x: x1, y: 212, w: x3 - x1 - 6, size: 60, weight: 800, align: 'center', color: C.ink });
    const svg = S.svg();
    const br = S.path(svg, [[x1, 318], [x1, 298], [x3 - 6, 298], [x3 - 6, 318]], { color: C.soft, width: 5, head: 0 });
    const conn = S.arrow(svg, x3 + w3 / 2, 446, x3 + w3 / 2, 594, { color: C.soft, width: 5, head: 18 });
    const note = S.note(L.note, { x: 100, y: 720, w: 1720, color: C.talker, size: 34 });

    S.show(c3, S.capAt(0), { x: -40 });
    S.show(n3, S.capAt(0) + 0.4);
    S.count(n3, { from: 0, to: b[2].value, dec: 0, suf: 'M' }, S.capAt(0) + 0.4, 1.2);
    S.draw(conn, S.capAt(0) + 1.2, 0.6);
    S.show(l3, S.capAt(0) + 1.8);
    S.pop(chip, S.capAt(0) + 2.3);
    S.show(c1, S.capAt(1), { x: -50, dur: 0.7 });
    S.show(c2, S.capAt(1) + 0.5, { x: -50, dur: 0.7 });
    S.show(n1, S.capAt(1) + 0.9);
    S.count(n1, { from: 0, to: b[0].value, dec: 1, suf: 'M' }, S.capAt(1) + 0.9, 1.4);
    S.show(n2, S.capAt(1) + 1.2);
    S.count(n2, { from: 0, to: b[1].value, dec: 1, suf: 'M' }, S.capAt(1) + 1.2, 1.4);
    S.stagger([l1, l2], S.capAt(1) + 1.8, 0.4);
    S.draw(br, S.capAt(1) + 3.0, 0.7);
    S.show(totalEl, S.capAt(1) + 3.4);
    S.count(totalEl, { from: 0, to: num(L.total), dec: 1, suf: tail(L.total) }, S.capAt(1) + 3.4, 1.4);
    S.show(note, S.capAt(2) + 0.6);
  });

  // s08: two older pairs of scores (older design, not today's talker).
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.labels;
    const chip = S.chip('tested', { x: 100, y: 205, label: L.chip });
    const head = S.text(L.head, { x: 500, y: 211, w: 1300, size: 32, weight: 700, color: C.warn });
    const mk = (y, title, sub, rows) => {
      const t = S.text(title, { x: 100, y, w: 1500, size: 36, weight: 800, color: C.talker });
      const s = S.text(sub, { x: 100, y: y + 46, w: 1500, size: 32, color: C.soft });
      const hb = S.hbars({
        x: 100, y: y + 96, w: 700, labelW: 420, rowH: 54, gap: 20, max: 100, dec: 1, labelSize: 32, valueSize: 40, valueW: 200,
        items: [
          { label: rows[0].label, value: rows[0].value, dec: 1, color: C.talker },
          { label: rows[1].label, value: rows[1].value, dec: 1, color: C.soft },
        ],
      });
      return { t, s, hb };
    };
    const A = mk(270, L.panelA, L.subA, L.rowsA);
    const B = mk(530, L.panelB, L.subB, L.rowsB);
    const unit = S.text(L.unit, { x: 100, y: 788, w: 480, size: 32, color: C.soft });
    const risk = S.note(L.risk, { x: 600, y: 770, w: 1220, color: C.warn, size: 34 });

    S.show(chip, S.capAt(0) + 0.3);
    S.show(head, S.capAt(0) + 0.8);
    S.show(A.t, S.capAt(1)); S.show(A.s, S.capAt(1) + 0.3);
    A.hb.reveal(S.capAt(1) + 0.9, 0.7, 1.4);
    S.show(unit, S.capAt(1) + 1.5);
    S.show(B.t, S.capAt(2)); S.show(B.s, S.capAt(2) + 0.3);
    B.hb.reveal(S.capAt(2) + 0.9, 0.7, 1.4);
    S.show(risk, S.at(0.62));
  });

  // s09: thinking on 73.01, thinking off 0.66 (older design, one copy), and the earlier 18.09 on its own card.
  Ch.scene('s09', function (S) {
    const c = S.c, L = c.labels;
    const hb = S.hbars({
      x: 100, y: 300, w: 420, labelW: 300, rowH: 60, gap: 40, max: 100, labelSize: 34, valueSize: 46, valueW: 200,
      items: [
        { label: L.bars[0].label, value: L.bars[0].value, dec: 2, color: C.thinker },
        { label: L.bars[1].label, value: L.bars[1].value, dec: 2, color: C.soft },
      ],
    });
    const unit = S.text(L.unit, { x: 400, y: 475, w: 600, size: 32, color: C.soft });
    const chip = S.chip('untested', { x: 100, y: 550, label: L.chip });
    const card = S.card({ x: 1100, y: 280, w: 720, h: 290, fill: C.card, color: C.untested, r: 22 });
    const big = S.text('', { x: 1100, y: 300, w: 720, size: 130, weight: 800, align: 'center', color: C.ink });
    const bigLab = S.text(L.earlierLabel, { x: 1140, y: 455, w: 640, size: 32, color: C.soft, align: 'center' });
    const note = S.note(L.note, { x: 100, y: 660, w: 1720, color: C.soft, size: 34 });

    hb.rows.forEach((r) => { S.show(r.lab, S.capAt(0) + 0.4); S.show(r.track, S.capAt(0) + 0.4); });
    hb.rows.forEach((r, i) => {
      const t = S.capAt(1) + 0.3 + i * 0.9;
      S.show(r.val, t);
      S.grow(r.b, t, 1.4, r.val, { dec: 2 });
    });
    S.show(unit, S.capAt(1) + 0.8);
    S.pop(chip, S.capAt(2) + 0.2);
    S.show(card, S.capAt(3));
    S.show(big, S.capAt(3) + 0.4);
    S.count(big, { from: 0, to: num(L.earlier), dec: 2 }, S.capAt(3) + 0.4, 1.4);
    S.show(bigLab, S.capAt(3) + 1.2);
    S.show(note, S.capAt(3) + 2.0);
  });

  // s10: fill-in-the-blank rows teach reading; the 84 / 16 plan split.
  Ch.scene('s10', function (S) {
    const c = S.c, L = c.labels;
    const sent = S.text('', { x: 100, y: 262, w: 1000, size: 56, mono: true, weight: 600, color: C.ink });
    const fillBox = S.box({ x: 718, y: 248, w: 170, h: 84, label: L.fill, color: C.talker, size: 56 });
    const rng = S.text(L.range, { x: 100, y: 380, w: 900, size: 38, weight: 700, color: C.talker });
    const tag = S.chip('placeholder', { x: 100, y: 450, label: L.tag });
    const chunk = S.note(L.chunk, { x: 100, y: 550, w: 960, color: C.reader, size: 34 });
    const wW = 588, wO = 112;
    const web = S.card({ x: 1100, y: 330, w: wW, h: 100, fill: '#E9EDF5', color: C.soft, r: 14 });
    const own = S.card({ x: 1100 + wW, y: 330, w: wO, h: 100, fill: PINK, color: C.talker, r: 14 });
    const webLab = S.text(L.web, { x: 1100, y: 448, w: 400, size: 34, weight: 700, color: C.soft });
    const ownLab = S.text(L.own, { x: 1500, y: 448, w: 300, size: 34, weight: 700, color: C.talker, align: 'right' });
    const chip = S.chip('placeholder', { x: 1100, y: 540, label: L.chip });

    S.type(sent, L.sentence + ' ' + L.blank, S.capAt(0) + 0.3, 1.8);
    S.pop(fillBox, S.capAt(1) + 0.4);
    S.show(rng, S.capAt(1) + 1.2);
    S.show(tag, S.capAt(1) + 1.8);
    S.show(chunk, S.capAt(2));
    S.pulse(fillBox, S.capAt(2) + 0.4);
    S.show(web, S.capAt(3), { x: -30 });
    S.show(own, S.capAt(3) + 0.4);
    S.stagger([webLab, ownLab], S.capAt(3) + 0.9, 0.4);
    S.pop(chip, S.capAt(3) + 1.8);
  });

  // s11: three steps the race needs; the first one (English talker) does not exist.
  Ch.scene('s11', function (S) {
    const c = S.c, L = c.labels;
    const xs = [160, 700, 1240];
    const cols = [C.talker, C.soft, C.soft];
    const boxes = xs.map((x, i) => S.box({ x, y: 300, w: 480, h: 190, label: L.steps[i], color: cols[i], size: 38 }));
    const kinds = ['placeholder', 'placeholder', 'placeholder'];
    const chips = xs.map((x, i) => S.chip(kinds[i], { x: x + 20, y: 525, label: L.chipLabels[i] }));
    const svg = S.svg();
    const a1 = S.arrow(svg, 644, 395, 696, 395, { color: C.soft, width: 6, head: 20 });
    const a2 = S.arrow(svg, 1184, 395, 1236, 395, { color: C.soft, width: 6, head: 20 });
    const note = S.note(L.note, { x: 160, y: 640, w: 1560, color: C.untested, size: 36 });

    S.show(boxes[0], S.capAt(0));
    S.draw(a1, S.capAt(0) + 0.9, 0.5);
    S.show(boxes[1], S.capAt(0) + 1.5);
    S.pop(chips[1], S.capAt(0) + 2.4);
    S.draw(a2, S.capAt(1), 0.5);
    S.show(boxes[2], S.capAt(1) + 0.5);
    S.pop(chips[2], S.capAt(1) + 1.4);
    S.pop(chips[0], S.capAt(2));
    S.pulse(boxes[0], S.capAt(2) + 0.6);
    S.show(note, S.at(0.7));
  });

  // s12: recap, three cards and four status chips, plus the map with the talker lit.
  Ch.scene('s12', function (S) {
    const c = S.c, L = c.labels;
    const xs = [100, 686, 1272];
    const cols = [C.talker, C.talker, C.placeholder];
    const cards = xs.map((x, i) => S.box({ x, y: 250, w: 546, h: 170, label: L.cards[i], color: cols[i], size: 44 }));
    const pos = [[100, 520], [686, 520], [686, 600], [1272, 520]];
    const chips = L.chips.map((ch, i) => S.chip(ch.kind, { x: pos[i][0], y: pos[i][1], label: ch.label }));
    const m = S.modelMap({ x: 100, y: 710, w: 1720, h: 110, highlight: 'talker' });

    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.04), 0.12);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.06) + i * 0.1, 0.3));
    S.show(cards[0], S.capAt(0) + 0.3);
    S.pop(chips[0], S.capAt(0) + 1.4);
    S.show(cards[1], S.capAt(1));
    S.pop(chips[1], S.capAt(1) + 1.0);
    S.pop(chips[2], S.capAt(1) + 1.6);
    S.show(cards[2], S.capAt(2));
    S.pop(chips[3], S.capAt(2) + 1.0);
    S.pulse(m.parts.talker, S.capAt(2) + 1.8);
  });
});
