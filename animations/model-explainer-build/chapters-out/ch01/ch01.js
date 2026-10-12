/* Chapter 1: one question, start to finish. Every on-screen string lives in content/ch01.json. */
Kit.chapter('ch01', function (Ch) {
  const C = Kit.C;
  const TINT = '#cfe3ff';

  // the example question as two rows of letter boxes (row A = chars 0-34, row B = chars 36-70)
  function question(S, c, x, y) {
    return { a: S.letters(c.question_a, { x, y, size: 30 }), b: S.letters(c.question_b, { x, y: y + 90, size: 30 }) };
  }

  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 300, w: 1720, h: 200 });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.capAt(0), 0.35);
    S.pop(S.chip('untested', { x: 560, y: 600, label: c.chip }), S.capAt(2));
  });

  Ch.scene('s02', function (S) {
    const c = S.c;
    const q = question(S, c, 420, 330);
    S.sweep(q.a.cells, S.capAt(0), 1.4);
    S.sweep(q.b.cells, S.capAt(1), 1.2);
    S.show(S.note(c.tag, { x: 420, y: 560, w: 700, color: C.placeholder }), S.capAt(2));
    S.show(S.text(c.chars_note, { x: 420, y: 660, w: 1100, size: 32, color: C.soft }), S.capAt(2) + 0.3);
  });

  Ch.scene('s03', function (S) {
    const c = S.c;
    const q = S.letters(c.question_a, { x: 420, y: 250, size: 30 });
    S.sweep(q.cells, S.capAt(0), 1.2);
    const rd = S.box({ x: 660, y: 380, w: 600, h: 150, label: c.labels[0], sub: c.labels[1], color: C.reader, size: 46, subSize: 32 });
    S.show(rd, S.capAt(1));
    const svg = S.svg();
    S.draw(S.arrow(svg, 960, 290, 960, 375, { color: C.soft }), S.capAt(1) + 0.3, 0.5);
    const strips = [0, 1, 2].map((i) => S.vec({ x: 480 + i * 460, y: 600, n: 12, cell: 26, color: C.reader, seed: 3 + i }));
    S.stagger(strips, S.capAt(2), 0.6);
    S.show(S.text(c.labels[2], { x: 420, y: 660, w: 1200, size: 36, color: C.soft }), S.capAt(2) + 0.3);
    const num = S.text('0', { x: 420, y: 720, w: 600, size: 90, weight: 800, color: C.reader });
    S.show(num, S.capAt(3));
    S.count(num, { from: 0, to: c.reader_numbers, comma: true }, S.capAt(3), 1.6);
    S.show(S.text(c.labels[3], { x: 1080, y: 740, w: 700, size: 36, color: C.soft }), S.capAt(3) + 0.3);
  });

  Ch.scene('s04', function (S) {
    const c = S.c;
    const q = S.letters(c.question_a, { x: 420, y: 330, size: 30 });
    S.sweep(q.cells, S.at(0.02), 0.8);
    for (let j = 15; j <= 23; j++) if (q.byIndex[j]) S.tint(q.byIndex[j], S.capAt(1), { fill: TINT });
    S.pulse(q.byIndex[19], S.capAt(0));
    S.show(S.text(c.labels[0], { x: q.cx(19) - 200, y: 260, w: 400, size: 32, align: 'center', color: C.soft }), S.capAt(0));
    S.show(S.text(c.labels[1], { x: 760, y: 430, w: 500, size: 32, align: 'center', color: C.reader }), S.capAt(1));
    S.pop(S.chip('learned', { x: 420, y: 560 }), S.capAt(2));
  });

  Ch.scene('s05', function (S) {
    const c = S.c;
    const svg = S.svg();
    const bx = [260, 760, 1260];
    const boxes = c.labels.map((n, i) => S.box({ x: bx[i], y: 420, w: 400, h: 150, label: n, color: C.thinker, size: 46 }));
    S.show(boxes[0], S.capAt(0));
    S.show(boxes[1], S.capAt(0) + 0.4);
    S.show(boxes[2], S.capAt(0) + 0.8);
    S.draw(S.arrow(svg, 660, 495, 760, 495, { color: C.soft }), S.capAt(1), 0.5);
    S.draw(S.arrow(svg, 1160, 495, 1260, 495, { color: C.soft }), S.capAt(1) + 0.6, 0.5);
    S.draw(S.curve(svg, 1460, 590, 460, 590, { bend: 140, color: C.thinker, width: 4 }), S.capAt(2), 1.0);
    S.pop(S.chip('learned', { x: 260, y: 700 }), S.capAt(2) + 0.5);
  });

  Ch.scene('s06', function (S) {
    const c = S.c;
    const q = S.letters(c.question_a, { x: 420, y: 230, size: 30 });
    S.sweep(q.cells, S.capAt(0), 1.2);
    const th = S.box({ x: 620, y: 400, w: 680, h: 150, label: c.labels[1], color: C.thinker, size: 46 });
    S.show(th, S.capAt(0) + 0.5);
    const svg = S.svg();
    S.draw(S.arrow(svg, 960, 275, 960, 395, { color: C.reader }), S.capAt(0) + 0.8, 0.5);
    S.show(S.text(c.labels[0], { x: 160, y: 430, w: 400, size: 72, weight: 800, color: C.thinker }), S.capAt(1));
    S.show(S.box({ x: 1420, y: 400, w: 380, h: 150, label: c.labels[2], color: C.placeholder, size: 36 }), S.capAt(2));
  });

  Ch.scene('s07', function (S) {
    const c = S.c;
    const grid = c.ops.map((op, i) => S.box({ x: 260 + (i % 4) * 300, y: 300 + Math.floor(i / 4) * 130, w: 240, h: 100, label: op, color: C.call, size: 44 }));
    S.stagger(grid, S.capAt(0), 0.25);
    S.show(S.box({ x: 1500, y: 420, w: 300, h: 130, label: c.labels[0], sub: c.labels[1], color: C.soft, size: 40, subSize: 28 }), S.capAt(1));
    S.pulse(grid[1], S.capAt(2));
    S.show(S.chip('tested', { x: 260, y: 700, label: c.chips[0] }), S.capAt(2) + 0.4);
  });

  Ch.scene('s08', function (S) {
    const c = S.c;
    const q = S.letters(c.question_a, { x: 420, y: 250, size: 30 });
    S.sweep(q.cells, S.at(0.02), 0.8);
    const svg = S.svg();
    S.show(S.box({ x: q.cx(9) - 130, y: 400, w: 260, h: 90, label: c.labels[0], color: C.learned, size: 34 }), S.capAt(0));
    S.draw(S.arrow(svg, q.cx(9), 400, q.cx(9), 292, { color: C.learned }), S.capAt(0) + 0.4, 0.5);
    S.tint(q.byIndex[8], S.capAt(1), { fill: TINT });
    S.tint(q.byIndex[9], S.capAt(1), { fill: TINT });
    S.show(S.box({ x: 260, y: 560, w: 300, h: 90, label: c.labels[1], color: C.learned, size: 34 }), S.capAt(1));
    S.show(S.box({ x: 620, y: 560, w: 420, h: 90, label: c.labels[2], color: C.hand, size: 34 }), S.capAt(1) + 0.4);
    S.show(S.text(c.call, { x: 420, y: 700, w: 1000, size: 90, mono: true, color: C.call }), S.capAt(2));
  });

  Ch.scene('s09', function (S) {
    const c = S.c;
    const svg = S.svg();
    S.show(S.box({ x: 700, y: 360, w: 520, h: 200, label: c.labels[0], color: C.calc, size: 46 }), S.capAt(0));
    S.pop(S.chip('hand', { x: 700, y: 600 }), S.capAt(0) + 0.4);
    S.show(S.text(c.request, { x: 160, y: 415, w: 480, size: 52, mono: true, color: C.call }), S.capAt(1));
    S.draw(S.arrow(svg, 660, 430, 700, 430, { color: C.call }), S.capAt(1) + 0.4, 0.4);
    const num = S.text('0.0', { x: 1280, y: 380, w: 500, size: 150, weight: 800, align: 'center', color: C.calc });
    S.show(num, S.capAt(2));
    S.count(num, { from: 0, to: c.zero_score, dec: 1 }, S.capAt(2), 1.2);
    S.show(S.text(c.labels[1], { x: 1180, y: 560, w: 700, size: 36, align: 'center', color: C.soft }), S.capAt(2) + 0.3);
  });

  Ch.scene('s10', function (S) {
    const c = S.c;
    const svg = S.svg();
    S.show(S.box({ x: 1240, y: 330, w: 520, h: 200, label: c.labels[0], color: C.calc, size: 46 }), S.capAt(0));
    S.show(S.text(c.request, { x: 160, y: 415, w: 480, size: 52, mono: true, color: C.call }), S.capAt(0));
    S.draw(S.arrow(svg, 660, 430, 1240, 430, { color: C.call }), S.capAt(0) + 0.4, 0.6);
    S.draw(S.arrow(svg, 1240, 500, 660, 500, { color: C.calc }), S.capAt(1), 0.6);
    S.show(S.text(c.reply, { x: 160, y: 540, w: 700, size: 52, mono: true, color: C.calc }), S.capAt(1) + 0.4);
    S.show(S.box({ x: 160, y: 680, w: 560, h: 120, label: c.labels[1], color: C.thinker, size: 40 }), S.capAt(2));
    S.draw(S.arrow(svg, 420, 600, 420, 680, { color: C.soft }), S.capAt(2) + 0.3, 0.5);
    S.pop(S.chip('hand', { x: 1240, y: 580 }), S.capAt(0) + 0.6);
  });

  Ch.scene('s11', function (S) {
    const c = S.c;
    const svg = S.svg();
    S.show(S.text(c.labels[0], { x: 160, y: 230, w: 600, size: 72, weight: 800, color: C.thinker }), S.capAt(0));
    const qb = S.letters(c.question_b, { x: 420, y: 330, size: 30 });
    S.sweep(qb.cells, S.capAt(0), 0.8);
    const ra = S.letters(c.reply1, { x: 420, y: 470, size: 30 });
    S.show(S.text(c.labels[2], { x: 160, y: 470, w: 240, size: 32, color: C.soft }), S.capAt(0));
    S.sweep(ra.cells, S.capAt(0) + 0.3, 0.8);
    S.show(S.text(c.call2, { x: 160, y: 600, w: 700, size: 80, mono: true, color: C.call }), S.capAt(1));
    S.draw(S.arrow(svg, 380, 640, ra.cx(11), 515, { color: C.call }), S.capAt(1) + 0.4, 0.6);
    S.draw(S.arrow(svg, 480, 640, qb.cx(10), 375, { color: C.soft }), S.capAt(1) + 0.8, 0.6);
    S.show(S.text(c.reply2, { x: 160, y: 740, w: 900, size: 60, mono: true, color: C.calc }), S.capAt(2));
    S.show(S.text(c.labels[1], { x: 1250, y: 740, w: 500, size: 52, weight: 800, color: C.calc }), S.capAt(2) + 0.4);
  });

  Ch.scene('s12', function (S) {
    const c = S.c;
    const calls = ['', c.call1, c.call2, '', '', '', '', ''];
    const tiles = calls.map((t, i) => S.box({ x: 160 + i * 200, y: 330, w: 180, h: 130, label: t, color: i === 1 || i === 2 ? C.call : C.soft, size: 34 }));
    S.stagger(tiles.slice(0, 3), S.capAt(0), 0.5);
    S.show(S.text(c.labels[1], { x: 160, y: 500, w: 900, size: 32, color: C.soft }), S.capAt(0));
    S.stagger(tiles.slice(3), S.capAt(1), 0.25);
    S.show(S.box({ x: 160, y: 620, w: 1600, h: 90, label: c.labels[3], color: C.soft, size: 36 }), S.capAt(1) + 0.5);
    S.show(S.text(c.labels[0], { x: 1300, y: 250, w: 500, size: 32, align: 'right', color: C.placeholder }), S.capAt(0));
    S.pop(S.chip('untested', { x: 160, y: 760 }), S.capAt(2));
    S.show(S.text(c.labels[2], { x: 700, y: 765, w: 1100, size: 36, color: C.soft }), S.capAt(2) + 0.3);
  });

  Ch.scene('s13', function (S) {
    const c = S.c;
    S.show(S.card({ x: 160, y: 560, w: 1600, h: 30, fill: C.stop }), S.capAt(0));
    S.show(S.text(c.labels[0], { x: 160, y: 500, w: 400, size: 40, color: C.stop }), S.capAt(0));
    S.show(S.text(c.labels[1], { x: 1360, y: 500, w: 400, size: 40, align: 'right', color: C.stop }), S.capAt(0));
    const sw = S.box({ x: 700, y: 400, w: 400, h: 110, label: c.labels[2], color: C.stop, size: 46 });
    S.show(sw, S.capAt(1));
    S.tint(sw, S.capAt(1) + 0.8, { fill: C.tested });
    S.show(S.text(c.labels[3], { x: 700, y: 640, w: 400, size: 32, align: 'center', color: C.placeholder }), S.capAt(1) + 0.8);
    S.pop(S.chip('learned', { x: 160, y: 740 }), S.capAt(2));
    S.pop(S.chip('untested', { x: 640, y: 740 }), S.capAt(2) + 0.4);
  });

  Ch.scene('s14', function (S) {
    const c = S.c;
    const svg = S.svg();
    const L = S.letters(c.last_reply, { x: 160, y: 300, size: 30 });
    S.sweep(L.cells, S.capAt(0), 0.9);
    S.tint(L.byIndex[10], S.capAt(1), { fill: C.talker });
    S.tint(L.byIndex[11], S.capAt(1), { fill: C.talker });
    S.show(S.box({ x: 560, y: 470, w: 520, h: 150, label: c.labels[0], color: C.talker, size: 46 }), S.capAt(0));
    S.draw(S.arrow(svg, L.cx(10), 350, 760, 470, { color: C.talker }), S.capAt(1), 0.6);
    S.show(S.text(c.answer, { x: 1200, y: 480, w: 500, size: 150, weight: 800, align: 'center', color: C.talker }), S.capAt(2));
    S.pop(S.chip('placeholder', { x: 1140, y: 680, label: c.labels[1] }), S.capAt(2) + 0.4);
  });

  Ch.scene('s15', function (S) {
    const c = S.c;
    S.pop(S.chip('tested', { x: 160, y: 300 }), S.capAt(0));
    S.pop(S.chip('tested', { x: 160, y: 420 }), S.capAt(1));
    S.pop(S.chip('untested', { x: 160, y: 540 }), S.capAt(2));
    S.pop(S.chip('placeholder', { x: 160, y: 660 }), S.capAt(3));
    S.pop(S.chip('untested', { x: 160, y: 780, label: c.labels[0] }), S.capAt(4));
  });

  Ch.scene('s16', function (S) {
    const m = S.modelMap({ x: 100, y: 300, w: 1720, h: 200 });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.capAt(0), 0.3);
    S.pulse(m.parts.thinker, S.capAt(2));
  });
});
