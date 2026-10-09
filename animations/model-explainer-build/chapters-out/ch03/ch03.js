/* ch03: The reader. Every on-screen string and number comes from content/ch03.json (S.c).
   Code holds only symbols ("+", "x", "=", "%"), layout, and tiny local helpers. */
Kit.chapter('ch03', function (Ch) {
  const C = Kit.C;

  // Pull plain numbers out of a JSON label such as "word table 134,217,728" (commas removed).
  const numsOf = (str) => (str.replace(/,/g, '').match(/[\d.]+/g) || []).map(Number);

  // Reveal one S.hbars row group: label, track, then grow with a counting value.
  function revealRows(hb, t, gap, dur) { return hb.reveal(t, gap, dur); }

  // Grow a stacked-bar segment (S.bar) and count its value label.
  function growBar(S, b, t, dur, valueEl, o) {
    return S.grow(b, t, dur, valueEl, o || {});
  }

  // A small box that is a picture of a letter or a cell (no text, decoration only).
  function cell(S, x, y, w, h, color, fill) {
    return S.box({ x: x, y: y, w: w, h: h, color: color || C.line, fill: fill || '#FFFFFF', r: 8, border: 3 });
  }

  // ---------- s01: where we are ----------
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 250, w: 1720, h: 190, highlight: 'reader' });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    let t = S.at(0.04);
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.3); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.3 + 0.25, 0.4); });
    const tag = S.text(c.illustration, { x: 100, y: 520, w: 1400, size: 34, color: C.soft });
    S.show(tag, S.capAt(1));
    S.pulse(m.parts.reader, S.capAt(0) + 0.8);
  });

  // ---------- s02: letters versus word pieces (the cut is a made-up example) ----------
  Ch.scene('s02', function (S) {
    const c = S.c;
    const L = S.letters(c.example, { x: 160, y: 250, size: 56, gap: 6 });
    S.sweep(L.cells, S.at(0.05), 1.4);
    // word-piece boxes drawn over the letters: one per word (made-up cut, picture only)
    const words = [];
    let i = 0;
    c.example.split(' ').forEach((w) => { words.push({ w: w, s: i }); i += w.length + 1; });
    const tok = words.map((o) => {
      const x0 = L.cx(o.s) - L.cw / 2;
      const x1 = L.cx(o.s + o.w.length - 1) + L.cw / 2;
      return S.box({ x: x0, y: 520, w: x1 - x0, h: 110, color: C.reader, fill: '#E6F4F4', label: o.w, size: 40, r: 10 });
    });
    S.stagger(tok, S.capAt(0) + 0.3, 0.6);
    const svg = S.svg();
    tok.forEach((b, k) => { const xc = L.cx(words[k].s); const a = S.arrow(svg, xc, 330, xc, 512, { color: C.soft, width: 4, head: 16 }); S.draw(a, S.capAt(0) + 0.5 + k * 0.2, 0.4); });
    const tag = S.text(c.illustration, { x: 160, y: 700, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(0) + 0.3);
    S.pulse(tok[0], S.capAt(1) + 0.2);
  });

  // ---------- s03: measured letters per token (ratio, not a score) ----------
  Ch.scene('s03', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 330, w: 860, labelW: 560, rowH: 84, gap: 40, max: 5, dec: 2, labelSize: 40, valueSize: 56, items: [
      { label: c.labels.skills, value: c.numbers.skills, color: C.thinker },
      { label: c.labels.web, value: c.numbers.web, color: C.reader },
    ] });
    hb.reveal(S.capAt(0), 0.8, 1.8);
    const chip = S.chip('tested', { x: 160, y: 640, label: c.chip_label });
    S.pop(chip, S.capAt(1));
  });

  // ---------- s04: the reader reads once, then copies meaning to each token ----------
  Ch.scene('s04', function (S) {
    const c = S.c;
    const svg = S.svg();
    const tok = S.box({ x: 120, y: 470, w: 340, h: 160, color: C.reader, fill: '#E6F4F4', label: c.labels.token, size: 40 });
    S.show(tok, S.at(0.02));
    S.pulse(tok, S.at(0.05));
    const rowLab = S.text(c.labels.row, { x: 640, y: 420, w: 560, size: 40, weight: 700, color: C.reader });
    const row = S.vec({ x: 640, y: 480, n: 12, cell: 40, gap: 6, color: C.reader, seed: 4 });
    const a1 = S.arrow(svg, 470, 550, 630, 550, { color: C.soft, width: 6, head: 20 });
    S.show(rowLab, S.capAt(1));
    S.show(row, S.capAt(1) + 0.2);
    S.draw(a1, S.capAt(1) + 0.3, 0.5);
    const let1 = S.box({ x: 1340, y: 470, w: 340, h: 160, color: C.thinker, fill: '#E9E8FA', label: c.labels.letter, size: 40 });
    const a2 = S.arrow(svg, 1210, 550, 1330, 550, { color: C.soft, width: 6, head: 20 });
    S.show(let1, S.capAt(2));
    S.draw(a2, S.capAt(2) - 0.1, 0.5);
    const tag = S.text(c.illustration, { x: 120, y: 700, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(2) + 0.6);
  });

  // ---------- s05: the borrowed reader: two parts that add up ----------
  Ch.scene('s05', function (S) {
    const c = S.c;
    const tableN = numsOf(c.labels.table)[0];
    const tfN = numsOf(c.labels.tf)[0];
    const totalN = tableN + tfN;
    const box = S.box({ x: 160, y: 230, w: 1600, h: 110, color: C.reader, fill: '#E6F4F4', label: c.labels.frozen, size: 44, r: 12, border: 4 });
    S.show(box, S.capAt(0));
    const t1 = S.text(c.labels.table, { x: 160, y: 390, w: 1200, size: 40, weight: 700, color: C.reader });
    const b1 = S.bar({ x: 160, y: 445, w: 1600, h: 70, value: tableN, max: totalN, color: C.reader });
    const t2 = S.text(c.labels.tf, { x: 160, y: 580, w: 1200, size: 40, weight: 700, color: C.thinker });
    const b2 = S.bar({ x: 160, y: 635, w: 1600, h: 70, value: tfN, max: totalN, color: C.thinker });
    S.show(t1, S.capAt(1)); S.show(b1.track, S.capAt(1) + 0.1); S.grow(b1, S.capAt(1) + 0.2, 1.4);
    S.show(t2, S.capAt(1) + 1.2); S.show(b2.track, S.capAt(1) + 1.3); S.grow(b2, S.capAt(1) + 1.4, 1.4);
    S.pulse(box, S.capAt(2));
  });

  // ---------- s06: the converter plug (768 numbers in, thinker width out) ----------
  Ch.scene('s06', function (S) {
    const c = S.c;
    const svg = S.svg();
    const inLab = S.text(c.labels.in, { x: 160, y: 380, w: 420, size: 40, weight: 700, color: C.reader });
    const vin = S.vec({ x: 160, y: 450, n: 10, cell: 40, gap: 6, color: C.reader, seed: 5 });
    const plug = S.box({ x: 700, y: 400, w: 300, h: 140, color: C.learned, fill: '#E7EFFD', r: 12, border: 4 });
    const a1 = S.arrow(svg, 630, 470, 695, 470, { color: C.soft, width: 6, head: 20 });
    const a2 = S.arrow(svg, 1010, 470, 1230, 470, { color: C.soft, width: 6, head: 20 });
    const outLab = S.text(c.labels.out, { x: 1240, y: 380, w: 520, size: 40, weight: 700, color: C.thinker });
    const vout = S.vec({ x: 1240, y: 450, n: 6, cell: 40, gap: 6, color: C.thinker, seed: 8, dir: 'h' });
    S.show(inLab, S.capAt(0)); S.show(vin, S.capAt(0) + 0.2);
    S.pop(plug, S.capAt(0) + 0.6);
    S.draw(a1, S.capAt(0) + 0.9, 0.6);
    S.draw(a2, S.capAt(0) + 1.5, 0.6);
    S.show(outLab, S.capAt(0) + 1.5); S.show(vout, S.capAt(0) + 1.7);
    S.show(S.chip('learned', { x: 680, y: 300 }), S.capAt(1));
    S.pulse(vout, S.capAt(1) + 0.2);
  });

  // ---------- s07: four parts added into one letter row ----------
  Ch.scene('s07', function (S) {
    const c = S.c;
    const svg = S.svg();
    const xs = [160, 560, 960, 1360];
    const parts = [c.labels.char, c.labels.pos, c.labels.place, c.labels.gemma].map((lab, i) =>
      S.box({ x: xs[i], y: 330, w: 340, h: 150, color: [C.reader, C.thinker, C.hand, C.call][i], fill: '#FFFFFF', label: lab, size: 36, r: 12, border: 4 }));
    const plus = [520, 920, 1320].map((x) => S.text('+', { x: x, y: 380, w: 40, size: 64, weight: 800, align: 'center', color: C.soft }));
    const sum = S.box({ x: 160, y: 610, w: 1560, h: 130, color: C.calc, fill: '#EEF1F5', label: c.labels.sum, size: 44, r: 12, border: 4 });
    const arrows = xs.map((x) => S.arrow(svg, x + 170, 490, x + 170, 602, { color: C.soft, width: 6, head: 20 }));
    const chip = S.chip('hand', { x: 960, y: 252, label: c.chip_label });
    S.show(parts[0], S.capAt(0));
    S.show(parts[1], S.capAt(1)); S.show(plus[0], S.capAt(1) + 0.2);
    S.show(parts[2], S.capAt(2)); S.show(plus[1], S.capAt(2) + 0.2); S.show(chip, S.capAt(2) + 0.4);
    S.show(parts[3], S.capAt(3)); S.show(plus[2], S.capAt(3) + 0.2);
    S.show(sum, S.capAt(3) + 0.4);
    arrows.forEach((a, i) => S.draw(a, S.capAt(3) + 0.6 + i * 0.1, 0.5));
    S.pulse(sum, S.capAt(3) + 1.6);
  });

  // ---------- s08: the letter window: each letter sees 4 letters each side ----------
  Ch.scene('s08', function (S) {
    const c = S.c;
    const cells = [];
    for (let i = 0; i < 9; i++) cells.push(cell(S, 160 + i * 100, 380, 90, 90, i === 4 ? C.thinker : C.line, i === 4 ? '#E9E8FA' : '#FFFFFF'));
    const l1 = S.box({ x: 360, y: 275, w: 490, h: 60, color: C.learned, fill: '#E7EFFD', label: c.labels.l1, size: 32, r: 10, border: 3 });
    const l2 = S.box({ x: 160, y: 200, w: 890, h: 60, color: C.learned, fill: '#E7EFFD', label: c.labels.l2, size: 32, r: 10, border: 3 });
    S.show(cells[4], S.capAt(0)); S.stagger(cells.filter((_, i) => i !== 4), S.capAt(0) + 0.1, 0.05);
    S.show(S.chip('learned', { x: 1100, y: 380 }), S.capAt(0) + 0.3);
    S.show(l1, S.capAt(1));
    S.pulse(cells[2], S.capAt(1) + 0.3); S.pulse(cells[6], S.capAt(1) + 0.3);
    S.show(l2, S.capAt(2));
    S.pulse(cells[0], S.capAt(2) + 0.3); S.pulse(cells[8], S.capAt(2) + 0.3);
  });

  // ---------- s09: without the window, cipher puzzles fall (score out of 100) ----------
  Ch.scene('s09', function (S) {
    const c = S.c;
    const h1 = S.text(c.labels.with, { x: 160, y: 250, w: 1200, size: 42, weight: 700, color: C.thinker });
    const g1 = S.hbars({ x: 160, y: 310, w: 1000, labelW: 40, rowH: 60, gap: 20, max: 100, dec: 1, valueSize: 46, items: [
      { label: '', value: c.numbers.ewith1, color: C.thinker },
      { label: '', value: c.numbers.ewith2, color: C.thinker },
    ] });
    const h2 = S.text(c.labels.without, { x: 160, y: 510, w: 1200, size: 42, weight: 700, color: C.call });
    const g2 = S.hbars({ x: 160, y: 570, w: 1000, labelW: 40, rowH: 60, gap: 20, max: 100, dec: 1, valueSize: 46, items: [
      { label: '', value: c.numbers.wo1, color: C.call },
      { label: '', value: c.numbers.wo2, color: C.call },
    ] });
    S.show(h1, S.capAt(0)); S.show(h2, S.capAt(0) + 0.3);
    g1.reveal(S.capAt(1), 0.5, 1.6);
    g2.reveal(S.capAt(2), 0.5, 1.6);
    const chip = S.chip('tested', { x: 160, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 1.0);
  });

  // ---------- s10: the position table (10 x 10 grid, each square is 1 percent of the sample) ----------
  Ch.scene('s10', function (S) {
    const c = S.c;
    const sq = [];
    for (let r = 0; r < 10; r++) for (let k = 0; k < 10; k++) sq.push(cell(S, 160 + k * 56, 260 + r * 56, 50, 50, C.line, '#FFFFFF'));
    S.sweep(sq, S.capAt(0), 1.2);
    const samp = S.text(c.labels.sample, { x: 820, y: 260, w: 900, size: 40, weight: 700 });
    S.show(samp, S.capAt(0) + 0.2);
    // square 0 = over 2,000 (purple); squares 1 to 31 more = over 280 (coral), so 32 coral in all
    const pa = S.text(c.labels.a, { x: 820, y: 370, w: 900, size: 40, weight: 700, color: C.call });
    const na = S.text('', { x: 820, y: 420, w: 900, size: 120, weight: 800, color: C.call, lh: 1 });
    const pb = S.text(c.labels.b, { x: 820, y: 580, w: 900, size: 40, weight: 700, color: C.stop });
    const nb = S.text('', { x: 820, y: 630, w: 900, size: 120, weight: 800, color: C.stop, lh: 1 });
    S.show(pa, S.capAt(1)); S.show(pb, S.capAt(1) + 0.4);
    S.show(na, S.capAt(1) + 0.1); S.show(nb, S.capAt(1) + 0.5);
    S.tint(sq[0], S.capAt(1) + 0.2, { fill: C.stop, dur: 0.2 });
    for (let i = 1; i < 32; i++) S.tint(sq[i], S.capAt(1) + 0.3 + i * 0.04, { fill: C.call, dur: 0.12 });
    S.count(na, { from: 0, to: c.numbers.over280, suf: '%' }, S.capAt(1) + 0.3, 1.6);
    S.count(nb, { from: 0, to: c.numbers.over2000, suf: '%' }, S.capAt(1) + 0.6, 1.0);
    const chip = S.chip('tested', { x: 820, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(1) + 2.0);
  });

  // ---------- s11: a hand-written pattern marks the numbers (records position, not value) ----------
  Ch.scene('s11', function (S) {
    const c = S.c;
    const strip = [];
    for (let i = 0; i < 16; i++) strip.push(cell(S, 160 + i * 64, 330, 52, 60, C.line, '#FFFFFF'));
    S.stagger(strip, S.capAt(0), 0.04);
    const pat = S.box({ x: 160, y: 250, w: 260, h: 56, color: C.hand, fill: '#F5ECE3', label: c.labels.regex, size: 30, r: 10, border: 3 });
    S.show(pat, S.capAt(0) + 0.2);
    S.move(pat, S.capAt(1), 2.4, { x: 800 });
    [2, 7, 11].forEach((i, k) => S.tint(strip[i], S.capAt(1) + 0.5 + k * 0.8, { fill: C.hand, dur: 0.2 }));
    const tag = S.text(c.illustration, { x: 160, y: 430, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(1) + 0.2);
    const nums = numsOf(c.labels.slots);
    const hb = S.hbars({ x: 160, y: 520, w: 900, labelW: 40, rowH: 56, gap: 16, max: nums[2], dec: 0, valueSize: 40, items: [
      { label: '', value: nums[0], color: C.hand, dec: 0 },
      { label: '', value: nums[1], color: C.hand, dec: 0 },
      { label: '', value: nums[2], color: C.hand, dec: 0 },
    ] });
    const slots = S.text(c.labels.slots, { x: 160, y: 470, w: 1200, size: 44, weight: 700, color: C.hand });
    S.show(slots, S.capAt(2));
    hb.reveal(S.capAt(2) + 0.3, 0.4, 1.2);
    const chip = S.chip('hand', { x: 160, y: 760, label: c.chip_label });
    S.show(chip, S.capAt(2) + 0.2);
  });

  // ---------- s12: calculator replies, read by the window only (built, never run) ----------
  Ch.scene('s12', function (S) {
    const c = S.c;
    const svg = S.svg();
    const slip = S.card({ x: 160, y: 330, w: 620, h: 150, r: 10 });
    const reply = S.text('', { x: 190, y: 370, w: 600, size: 56, weight: 700, mono: true, color: C.calc });
    S.show(slip, S.capAt(0));
    S.type(reply, c.example, S.capAt(0) + 0.2, 1.4);
    const win = S.box({ x: 1000, y: 330, w: 300, h: 150, color: C.calc, fill: '#EEF1F5', r: 12, border: 4 });
    const a1 = S.arrow(svg, 790, 405, 990, 405, { color: C.calc, width: 6, head: 20 });
    S.show(win, S.capAt(1)); S.draw(a1, S.capAt(1) + 0.2, 0.6);
    const gem = S.box({ x: 1000, y: 580, w: 300, h: 150, color: C.reader, fill: '#E6F4F4', r: 12, border: 4 });
    const a2 = S.arrow(svg, 780, 480, 990, 640, { color: C.soft, width: 5, head: 18 });
    const cross = S.text('x', { x: 868, y: 520, w: 60, size: 64, weight: 800, align: 'center', color: C.warn });
    S.show(gem, S.capAt(1) + 0.3); S.draw(a2, S.capAt(1) + 0.5, 0.5); S.show(cross, S.capAt(1) + 0.8);
    const tag = S.text(c.illustration, { x: 160, y: 660, w: 1200, size: 34, color: C.soft });
    S.show(tag, S.capAt(2));
    const chip = S.chip('untested', { x: 160, y: 740, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 0.3);
  });

  // ---------- s13: the gain, +2.67 points out of 100 (tested at 3M, 6 copies) ----------
  Ch.scene('s13', function (S) {
    const c = S.c;
    const egeR = numsOf(c.labels.ege), b2R = numsOf(c.labels.b2);
    const lo = Math.floor(Math.min(egeR[0], b2R[0])) - 1, hi = Math.ceil(Math.max(egeR[1], b2R[1])) + 1;
    const X = (v) => 160 + (v - lo) / (hi - lo) * 1400;
    const l1 = S.text(c.labels.ege, { x: 160, y: 250, w: 1400, size: 40, weight: 700, color: C.reader });
    const r1 = S.box({ x: X(egeR[0]), y: 310, w: X(egeR[1]) - X(egeR[0]), h: 56, color: C.reader, fill: C.reader, r: 8 });
    const l2 = S.text(c.labels.b2, { x: 160, y: 410, w: 1400, size: 40, weight: 700, color: C.calc });
    const r2 = S.box({ x: X(b2R[0]), y: 470, w: X(b2R[1]) - X(b2R[0]), h: 56, color: C.calc, fill: C.calc, r: 8 });
    S.show(l1, S.capAt(0)); S.show(r1, S.capAt(0) + 0.3);
    S.show(l2, S.capAt(1)); S.show(r2, S.capAt(1) + 0.3);
    const gain = S.text('', { x: 160, y: 590, w: 700, size: 130, weight: 800, color: C.thinker, lh: 1 });
    S.show(gain, S.capAt(2));
    S.count(gain, { from: 0, to: c.numbers.gain, dec: 2, pre: '+' }, S.capAt(2) + 0.2, 1.6);
    const note = S.note(c.warning, { x: 900, y: 600, w: 940, color: C.warn, size: 32 });
    S.show(note, S.capAt(2) + 0.6);
    const dots = [];
    for (let i = 0; i < c.numbers.copies; i++) dots.push(cell(S, 160 + i * 70, 760, 50, 50, C.tested, '#E9F6EF'));
    S.stagger(dots, S.capAt(2) + 0.8, 0.25);
    const chip = S.chip('tested', { x: 900, y: 740, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 1.0);
  });

  // ---------- s14: the leak warning light (caveat, not settled) ----------
  Ch.scene('s14', function (S) {
    const c = S.c;
    const max = Math.max(c.numbers.leak, c.numbers.ege) * 1.1;
    const lk = S.bar({ x: 160, y: 330, w: 1400, h: 56, value: c.numbers.leak, max: max, color: C.stop });
    const lkNum = S.text('', { x: 1600, y: 322, w: 240, size: 60, weight: 800, color: C.stop });
    const limX = 160 + c.numbers.limit / max * 1400;
    const mark = S.box({ x: limX - 3, y: 306, w: 6, h: 104, color: C.warn, fill: C.warn, r: 2 });
    S.show(lk.track, S.capAt(0)); S.show(lkNum, S.capAt(0) + 0.2);
    S.grow(lk, S.capAt(1), 1.4, lkNum, { dec: 2 });
    S.show(mark, S.capAt(1) + 0.8);
    const hb = S.hbars({ x: 160, y: 530, w: 1000, labelW: 40, rowH: 60, gap: 20, max: max, dec: 2, valueSize: 46, items: [
      { label: '', value: c.numbers.ege, color: C.reader },
      { label: '', value: c.numbers.other, color: C.placeholder },
    ] });
    hb.reveal(S.capAt(2), 0.5, 1.6);
    const chip = S.chip('untested', { x: 160, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 0.6);
  });

  // ---------- s15: tokens instead of letters (picture only; no result recorded) ----------
  Ch.scene('s15', function (S) {
    const c = S.c;
    const letters = [];
    for (let i = 0; i < 12; i++) letters.push(cell(S, 160 + i * 100, 300, 80, 80, C.line, '#FFFFFF'));
    S.sweep(letters, S.capAt(0), 1.2);
    const toks = [0, 1, 2, 3].map((k) => S.box({ x: 160 + k * 300, y: 500, w: 280, h: 100, color: C.reader, fill: '#E6F4F4', r: 10, border: 4 }));
    S.stagger(toks, S.capAt(1), 0.35);
    const tag = S.text(c.illustration, { x: 160, y: 680, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(1) + 0.6);
    const chip = S.chip('untested', { x: 160, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(1) + 1.0);
  });

  // ---------- s16: recap ----------
  Ch.scene('s16', function (S) {
    const c = S.c;
    const cards = c.cards.map((cd, i) =>
      S.box({ x: 160 + i * 540, y: 260, w: 500, h: 120, color: C.reader, fill: '#FFFFFF', r: 14, border: 6, label: cd.label, sub: cd.sub, size: 36, subSize: 26 }));
    S.show(cards[0], S.capAt(0)); S.show(cards[1], S.capAt(1)); S.show(cards[2], S.capAt(2));
    const m = S.modelMap({ x: 100, y: 500, w: 1720, h: 190, highlight: 'reader' });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    let t = S.capAt(2) + 0.3;
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.2); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.2 + 0.15, 0.3); });
  });
});
