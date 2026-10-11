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

  // The shared model map dims the parts that are not in focus. Locally: darker grey for the dimmed labels
  // (about 5.5:1 on cream instead of 3.5:1) and a 30 px subtitle (the kit default is 28 px). Colours only; no layout change.
  function dimMap(m, hl) {
    Object.keys(m.parts).forEach((k) => {
      m.parts[k].querySelectorAll('.sub').forEach((n) => { n.style.fontSize = '30px'; });
      if (k === hl) return;
      m.parts[k].querySelectorAll('.lab').forEach((n) => { n.style.color = C.soft; });
      m.parts[k].querySelectorAll('.sub').forEach((n) => { n.style.color = C.soft; });
    });
  }

  // ---------- s01: where we are ----------
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 410, w: 1720, h: 190, highlight: 'reader', tool: 'above' });
    dimMap(m, 'reader');
    const order = ['reader', 'thinker', 'stop', 'talker', 'calc'];
    let t = S.at(0.04);
    // the question enters the reader: a plain input card under the Reader box, with an arrow up into it
    const q = S.box({ x: 100, y: 720, w: 288, h: 100, color: C.soft, fill: '#FFFFFF', label: c.labels.question, size: 36, r: 12, border: 4 });
    const qsvg = S.svg();
    const qa = S.arrow(qsvg, 244, 720, 244, 600, { color: C.soft, width: 6, head: 20 });
    S.show(q, t + 0.2);
    S.draw(qa, t + 0.7, 0.5);
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.3); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.3 + 0.25, 0.4); });
    S.show(m.tool.callLabel, t + 1.6); S.draw(m.tool.call, t + 1.6, 0.6);
    S.show(m.tool.replyLabel, t + 2.2); S.draw(m.tool.reply, t + 2.2, 0.6);
    const tag = S.text(c.illustration, { x: 440, y: 755, w: 1400, size: 34, color: C.soft });
    S.show(tag, S.capAt(1));
    S.pulse(m.parts.reader, S.capAt(0) + 0.8);
  });

  // ---------- s02: letters versus word pieces (the cut is a made-up example) ----------
  Ch.scene('s02', function (S) {
    const c = S.c;
    // The row is centred on the screen. Its width is worked out the way S.letters lays the cells out.
    const SZ = 72, GAP = 8, CW = Math.round(SZ * 0.82), SP = Math.round(CW * 0.6);
    let rowW = -GAP;
    [...c.example].forEach((ch) => { rowW += ch === ' ' ? SP : CW + GAP; });
    const L = S.letters(c.example, { x: Math.round((1920 - rowW) / 2), y: 270, size: SZ, gap: GAP });
    S.sweep(L.cells, S.at(0.05), 1.4);
    // word-piece boxes drawn under the letters: one per word (made-up cut, picture only)
    const words = [];
    let i = 0;
    c.example.split(' ').forEach((w) => { words.push({ w: w, s: i }); i += w.length + 1; });
    const mids = [];
    const tok = words.map((o) => {
      const x0 = L.cx(o.s) - L.cw / 2;
      const x1 = L.cx(o.s + o.w.length - 1) + L.cw / 2;
      mids.push((x0 + x1) / 2);
      return S.box({ x: x0, y: 500, w: x1 - x0, h: 120, color: C.reader, fill: '#E6F4F4', label: o.w, size: 44, r: 10 });
    });
    S.stagger(tok, S.capAt(0) + 0.3, 0.6);
    const svg = S.svg();
    tok.forEach((b, k) => { const a = S.arrow(svg, mids[k], 270 + L.h + 8, mids[k], 500, { color: C.soft, width: 4, head: 16 }); S.draw(a, S.capAt(0) + 0.5 + k * 0.2, 0.4); });
    const tag = S.text(c.illustration, { x: 160, y: 670, w: 1600, size: 34, color: C.soft, align: 'center' });
    S.show(tag, S.capAt(0) + 0.3);
    S.pulse(tok[0], S.capAt(1) + 0.2);
  });

  // ---------- s03: measured letters per token (ratio, not a score) ----------
  Ch.scene('s03', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 330, w: 860, labelW: 560, rowH: 84, gap: 40, max: 5, dec: 2, labelSize: 40, valueSize: 56, items: [
      { label: c.labels.skills, value: c.numbers.skills, color: C.reader },
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
    // the cell row is centred on the arrows' line (y 550) and the arrows run edge to edge: token box 460 -> row 640, row 1186 -> letter box 1340
    const rowLab = S.text(c.labels.row, { x: 640, y: 470, w: 560, size: 40, weight: 700, color: C.reader });
    const row = S.vec({ x: 640, y: 530, n: 12, cell: 40, gap: 6, color: C.reader, seed: 4 });
    const a1 = S.arrow(svg, 460, 550, 640, 550, { color: C.soft, width: 6, head: 20 });
    S.show(rowLab, S.capAt(1));
    S.show(row, S.capAt(1) + 0.2);
    S.draw(a1, S.capAt(1) + 0.3, 0.5);
    const let1 = S.box({ x: 1340, y: 470, w: 340, h: 160, color: C.thinker, fill: '#E9E8FA', label: c.labels.letter, size: 40 });
    const a2 = S.arrow(svg, 1186, 550, 1340, 550, { color: C.soft, width: 6, head: 20 });
    S.show(let1, S.capAt(2));
    S.draw(a2, S.capAt(2) - 0.1, 0.5);
    // the "shaded cells are decoration" note arrives together with the cells
    const tag = S.text(c.illustration, { x: 120, y: 700, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(1) + 0.3);
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
    const t2 = S.text(c.labels.tf, { x: 160, y: 580, w: 1200, size: 40, weight: 700, color: C.reader });
    const b2 = S.bar({ x: 160, y: 635, w: 1600, h: 70, value: tfN, max: totalN, color: C.reader });
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
    const plug = S.box({ x: 700, y: 400, w: 300, h: 140, color: C.learned, fill: '#E7EFFD', r: 12, border: 4, label: c.labels.plug, size: 34 });
    // arrows run edge to edge: row (ends 614) -> plug (700), plug (ends 1000) -> row (1240)
    const a1 = S.arrow(svg, 614, 470, 700, 470, { color: C.soft, width: 6, head: 20 });
    const a2 = S.arrow(svg, 1000, 470, 1240, 470, { color: C.soft, width: 6, head: 20 });
    const outLab = S.text(c.labels.out, { x: 1240, y: 380, w: 520, size: 40, weight: 700, color: C.thinker });
    const vout = S.vec({ x: 1240, y: 450, n: 6, cell: 40, gap: 6, color: C.thinker, seed: 8, dir: 'h' });
    S.show(inLab, S.capAt(0)); S.show(vin, S.capAt(0) + 0.2);
    S.pop(plug, S.capAt(0) + 0.6);
    S.show(S.text(c.labels.full, { x: 160, y: 700, w: 1600, size: 38, weight: 700, color: C.reader }), S.capAt(1) + 0.6);
    S.draw(a1, S.capAt(0) + 0.9, 0.6);
    S.draw(a2, S.capAt(0) + 1.5, 0.6);
    S.show(outLab, S.capAt(0) + 1.5); S.show(vout, S.capAt(0) + 1.7);
    S.show(S.chip('learned', { x: 680, y: 300 }), S.capAt(1));
    S.pulse(vout, S.capAt(1) + 0.2);
    // the "picture only" note arrives together with the two cell rows
    const tag = S.text(c.illustration, { x: 160, y: 600, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(0) + 0.4);
  });

  // ---------- s07: four parts added into one letter row ----------
  Ch.scene('s07', function (S) {
    const c = S.c;
    const svg = S.svg();
    const xs = [160, 560, 960, 1360];
    const parts = [c.labels.char, c.labels.pos, c.labels.place, c.labels.gemma].map((lab, i) =>
      // colours follow the glossary: blue = learned from scratch, brown = hand-written count, teal = Gemma (the borrowed reader)
      S.box({ x: xs[i], y: 330, w: 340, h: 150, color: [C.learned, C.learned, C.hand, C.reader][i], fill: '#FFFFFF', label: lab, size: 36, r: 12, border: 4 }));
    const plus = [510, 910, 1310].map((x) => S.text('+', { x: x, y: 380, w: 40, size: 64, weight: 800, align: 'center', color: C.soft }));
    const sum = S.box({ x: 160, y: 610, w: 1560, h: 130, color: C.calc, fill: '#EEF1F5', label: c.labels.sum, size: 44, r: 12, border: 4 });
    // arrows run from the bottom edge of each part (480) to the top edge of the sum box (610)
    const arrows = xs.map((x) => S.arrow(svg, x + 170, 480, x + 170, 610, { color: C.soft, width: 6, head: 20 }));
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
    // the whole picture sits lower (cells at y 485) so the layer-2 label is well clear of the heading
    const cells = [];
    for (let i = 0; i < 9; i++) cells.push(cell(S, 160 + i * 100, 485, 90, 90, i === 4 ? C.thinker : C.line, i === 4 ? '#E9E8FA' : '#FFFFFF'));
    const l1 = S.box({ x: 360, y: 400, w: 490, h: 60, color: C.learned, fill: '#E7EFFD', label: c.labels.l1, size: 32, r: 10, border: 3 });
    const l2 = S.box({ x: 160, y: 320, w: 890, h: 60, color: C.learned, fill: '#E7EFFD', label: c.labels.l2, size: 32, r: 10, border: 3 });
    S.show(cells[4], S.capAt(0)); S.stagger(cells.filter((_, i) => i !== 4), S.capAt(0) + 0.1, 0.05);
    S.show(S.chip('learned', { x: 1100, y: 485, label: c.chip_label }), S.capAt(0) + 0.3);
    S.show(l1, S.capAt(1));
    S.pulse(cells[2], S.capAt(1) + 0.3); S.pulse(cells[6], S.capAt(1) + 0.3);
    S.show(l2, S.capAt(2));
    S.pulse(cells[0], S.capAt(2) + 0.3); S.pulse(cells[8], S.capAt(2) + 0.3);
  });

  // ---------- s09: without the window, cipher puzzles fall (score out of 100; 40 puzzles per copy; two copies per arm) ----------
  Ch.scene('s09', function (S) {
    const c = S.c;
    // one group = a heading and two bars (copy 1, copy 2)
    const group = (y, label, color, v1, v2) => {
      const h = S.text(label, { x: 160, y: y, w: 1500, size: 36, weight: 700, color: color });
      const g = S.hbars({ x: 160, y: y + 48, w: 1000, labelW: 40, rowH: 48, gap: 10, max: 100, dec: 1, valueSize: 40, items: [
        { label: '', value: v1, color: color },
        { label: '', value: v2, color: color },
      ] });
      return { h: h, g: g };
    };
    const A = group(205, c.labels.with, C.learned, c.numbers.ewith1, c.numbers.ewith2);
    const B = group(378, c.labels.without, C.warn, c.numbers.wo1, c.numbers.wo2);
    const D = group(551, c.labels.alone, C.warn, c.numbers.r0a, c.numbers.r0b);
    S.show(A.h, S.capAt(0) + 0.6); S.show(B.h, S.capAt(0) + 1.0); S.show(D.h, S.capAt(0) + 1.4);
    A.g.reveal(S.capAt(1) + 0.2, 0.5, 1.6);
    B.g.reveal(S.capAt(2) + 0.2, 0.5, 1.6);
    D.g.reveal(S.capAt(3) + 0.2, 0.5, 1.6);
    // scale under the bars: the track runs from 0 to 100 points (same scale for all six bars; track x 200 to 1200)
    const tsvg = S.svg();
    const t0 = S.svgEl(tsvg, 'line', { x1: 201.5, y1: 711, x2: 201.5, y2: 725, stroke: C.soft, 'stroke-width': 3 });
    const t1 = S.svgEl(tsvg, 'line', { x1: 1198.5, y1: 711, x2: 1198.5, y2: 725, stroke: C.soft, 'stroke-width': 3 });
    const s0 = S.text(c.labels.zero, { x: 200, y: 728, w: 200, size: 30, weight: 600, color: C.soft });
    const s1 = S.text(c.labels.full, { x: 1000, y: 728, w: 200, size: 30, weight: 600, color: C.soft, align: 'right' });
    const sm = S.text(c.labels.scale, { x: 400, y: 728, w: 600, size: 30, weight: 600, color: C.soft, align: 'center' });
    [s0, s1, sm].forEach((e) => S.show(e, S.capAt(1) + 0.2, { dur: 0.5 }));
    [t0, t1].forEach((e) => S.tl.to(e, { autoAlpha: 1, duration: 0.5, ease: 'power1.out' }, S.capAt(1) + 0.2));
    const chip = S.chip('tested', { x: 160, y: 778, label: c.chip_label });
    S.pop(chip, S.capAt(3) + 1.0);
  });

  // ---------- s10: the position table (10 x 10 grid, each square is 1 percent of the sample) ----------
  Ch.scene('s10', function (S) {
    const c = S.c;
    const sq = [];
    for (let r = 0; r < 10; r++) for (let k = 0; k < 10; k++) sq.push(cell(S, 160 + k * 56, 260 + r * 56, 50, 50, C.line, '#FFFFFF'));
    S.sweep(sq, S.capAt(0), 1.2);
    const samp = S.text(c.labels.sample, { x: 820, y: 260, w: 900, size: 40, weight: 700 });
    const unit = S.text(c.labels.unit, { x: 820, y: 312, w: 900, size: 32, weight: 600, color: C.soft });
    S.show(samp, S.capAt(0) + 0.2); S.show(unit, S.capAt(0) + 0.4);
    // square 0 = over 2,000 (dark); squares 1 to 31 more = over 280 (orange): 32 squares over 280 in all, the dark one included
    // key: a small orange swatch for "over 280", a small dark swatch for "over 2,000" (same colours as the squares)
    const swA = S.box({ x: 820, y: 380, w: 36, h: 36, color: C.warn, fill: C.warn, r: 6, border: 0 });
    const swB = S.box({ x: 820, y: 556, w: 36, h: 36, color: C.ink, fill: C.ink, r: 6, border: 0 });
    const pa = S.text(c.labels.a, { x: 872, y: 376, w: 850, size: 40, weight: 700, color: C.warn });
    const na = S.text('', { x: 820, y: 438, w: 900, size: 100, weight: 800, color: C.warn, lh: 1 });
    const pb = S.text(c.labels.b, { x: 872, y: 552, w: 850, size: 40, weight: 700, color: C.ink });
    const nb = S.text('', { x: 820, y: 614, w: 900, size: 100, weight: 800, color: C.ink, lh: 1 });
    const dk = S.text(c.labels.dark, { x: 820, y: 722, w: 1000, size: 32, weight: 600, color: C.soft });
    S.show(pa, S.capAt(1)); S.show(swA, S.capAt(1)); S.show(pb, S.capAt(1) + 0.4); S.show(swB, S.capAt(1) + 0.4);
    S.show(na, S.capAt(1) + 0.1); S.show(nb, S.capAt(1) + 0.5); S.show(dk, S.capAt(1) + 0.6);
    S.tint(sq[0], S.capAt(1) + 0.2, { fill: C.ink, dur: 0.2 });
    for (let i = 1; i < c.numbers.over280; i++) S.tint(sq[i], S.capAt(1) + 0.3 + i * 0.04, { fill: C.warn, dur: 0.12 });
    S.count(na, { from: 0, to: c.numbers.over280, suf: '%' }, S.capAt(1) + 0.3, 1.6);
    S.count(nb, { from: 0, to: c.numbers.over2000, suf: '%' }, S.capAt(1) + 0.6, 1.0);
    const chip = S.chip('tested', { x: 820, y: 774, label: c.chip_label });
    S.pop(chip, S.capAt(1) + 2.0);
  });

  // ---------- s11: a hand-written pattern marks the numbers (records position, not value) ----------
  Ch.scene('s11', function (S) {
    const c = S.c;
    const strip = [];
    for (let i = 0; i < 16; i++) strip.push(cell(S, 160 + i * 64, 330, 52, 60, C.line, '#FFFFFF'));
    S.stagger(strip, S.capAt(0), 0.04);
    const pat = S.box({ x: 160, y: 250, w: 380, h: 56, color: C.hand, fill: '#F5ECE3', label: c.labels.regex, size: 30, r: 10, border: 3 });
    S.show(pat, S.capAt(0) + 0.2);
    // the chip scans from the row's left end and settles centred over the 16-cell row (row 160 to 1172, chip 380 wide)
    S.move(pat, S.capAt(1), 2.4, { x: 316 });
    [2, 7, 10].forEach((i, k) => S.tint(strip[i], S.capAt(1) + 0.5 + k * 0.8, { fill: C.hand, dur: 0.2 }));
    const tag = S.text(c.illustration, { x: 160, y: 410, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(1) + 0.2);
    const slots = S.text(c.labels.slots, { x: 160, y: 480, w: 1200, size: 40, weight: 700, color: C.hand });
    S.show(slots, S.capAt(2));
    const n = c.numbers;
    const hb = S.hbars({ x: 160, y: 540, w: 650, labelW: 680, rowH: 56, gap: 16, max: n.b3, dec: 0, valueSize: 40, labelSize: 30, items: [
      { label: c.labels.t1sdr, value: n.t1sdr, color: C.hand, dec: 0 },
      { label: c.labels.g1, value: n.g1, color: C.hand, dec: 0 },
      { label: c.labels.b3, value: n.b3, color: C.hand, dec: 0 },
    ] });
    hb.reveal(S.capAt(2) + 0.3, 0.4, 1.2);
    const chip = S.chip('hand', { x: 160, y: 770, label: c.chip_label });
    S.show(chip, S.capAt(2) + 0.2);
  });

  // ---------- s12: calculator replies: new design = whole reader; built B3 = window only (never run) ----------
  Ch.scene('s12', function (S) {
    const c = S.c;
    const svg = S.svg();
    // status chip from the first beat: this whole path is how B3 group 1 is built, and it has never been run
    const chip = S.chip('untested', { x: 160, y: 250, label: c.chip_label });
    S.pop(chip, S.capAt(0) + 0.2);
    const slip = S.card({ x: 160, y: 330, w: 620, h: 150, r: 10 });
    const reply = S.text('', { x: 190, y: 370, w: 600, size: 56, weight: 700, mono: true, color: C.calc });
    const from = S.text(c.labels.from, { x: 160, y: 495, w: 600, size: 32, color: C.soft });
    S.show(slip, S.capAt(0)); S.show(from, S.capAt(0) + 0.2);
    S.type(reply, c.example, S.capAt(0) + 0.2, 1.4);
    const win = S.box({ x: 1000, y: 330, w: 300, h: 150, color: C.learned, fill: '#E7EFFD', r: 12, border: 4, label: c.labels.win, size: 34 });
    // arrows run edge to edge: slip right edge 780 -> window left edge 1000; slip bottom-right corner -> Gemma left edge 1000
    const a1 = S.arrow(svg, 780, 405, 1000, 405, { color: C.calc, width: 6, head: 20 });
    S.show(win, S.capAt(0) + 0.8); S.draw(a1, S.capAt(0) + 1.0, 0.6);
    const gem = S.box({ x: 1000, y: 580, w: 300, h: 150, color: C.reader, fill: '#E6F4F4', r: 12, border: 4, label: c.labels.gem, size: 34 });
    const a2 = S.arrow(svg, 780, 480, 1000, 640, { color: C.soft, width: 5, head: 18 });
    const cross = S.text('x', { x: 860, y: 520, w: 60, size: 64, weight: 800, align: 'center', color: C.warn });
    const old = S.text(c.labels.old, { x: 160, y: 570, w: 640, size: 30, weight: 700, color: C.warn });
    S.show(gem, S.capAt(0) + 1.4); S.draw(a2, S.capAt(0) + 1.6, 0.5);
    S.show(cross, S.capAt(1) + 0.3); S.show(old, S.capAt(1) + 0.4);
    // the X marks the built B3 version only: it leaves before the last caption so the final picture matches the new design (both readers)
    S.hide(cross, S.capAt(2) + 0.1); S.hide(old, S.capAt(2) + 0.1);
    const tag = S.text(c.illustration, { x: 160, y: 660, w: 1200, size: 34, color: C.soft });
    S.show(tag, S.capAt(2));
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
    const gain = S.text('', { x: 160, y: 560, w: 700, size: 130, weight: 800, color: C.reader, lh: 1 });
    S.show(gain, S.capAt(2));
    S.count(gain, { from: 0, to: c.numbers.gain, dec: 2, pre: '+' }, S.capAt(2) + 0.2, 1.6);
    const note = S.note(c.warning, { x: 900, y: 570, w: 940, color: C.warn, size: 32 });
    S.show(note, S.capAt(2) + 0.6);
    // how 2.67 is found (an average of six per-copy gaps, not the gap between the range ends shown above)
    const how = S.note(c.labels.how, { x: 900, y: 670, w: 940, color: C.reader, size: 32 });
    S.show(how, S.capAt(2) + 1.0);
    const dots = [];
    for (let i = 0; i < c.numbers.copies; i++) dots.push(cell(S, 160 + i * 70, 715, 50, 50, C.tested, '#E9F6EF'));
    S.stagger(dots, S.capAt(2) + 0.8, 0.25);
    const chip = S.chip('tested', { x: 160, y: 780, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 1.0);
  });

  // ---------- s14: the leak warning light (a measured caveat; the cause is not settled) ----------
  Ch.scene('s14', function (S) {
    const c = S.c;
    const max = Math.max(c.numbers.leak, c.numbers.ege) * 1.1;
    const lkLab = S.text(c.labels.leak, { x: 160, y: 262, w: 900, size: 36, weight: 700, color: C.warn });
    const lk = S.bar({ x: 160, y: 330, w: 1400, h: 56, value: c.numbers.leak, max: max, color: C.warn });
    const lkNum = S.text('', { x: 1600, y: 322, w: 240, size: 60, weight: 800, color: C.warn });
    const limX = 160 + c.numbers.limit / max * 1400;
    const mark = S.box({ x: limX - 3, y: 306, w: 6, h: 104, color: C.ink, fill: C.ink, r: 2 });
    const limLab = S.text(c.labels.limit, { x: limX - 150, y: 418, w: 300, size: 34, weight: 700, align: 'center', color: C.ink });
    S.show(lk.track, S.capAt(0)); S.show(lkNum, S.capAt(0) + 0.2);
    // the bar and its number finish counting just as caption 2 (which quotes 6.59) fades in
    S.show(lkLab, S.capAt(1) - 0.9);
    S.grow(lk, S.capAt(1) - 0.9, 1.1, lkNum, { dec: 2 });
    S.show(mark, S.capAt(1) + 0.8); S.show(limLab, S.capAt(1) + 0.8);
    const seed = S.text(c.labels.seed, { x: 160, y: 490, w: 1200, size: 34, color: C.soft });
    S.show(seed, S.capAt(2));
    const hb = S.hbars({ x: 160, y: 545, w: 900, labelW: 360, rowH: 56, gap: 20, max: max, dec: 2, valueSize: 46, labelSize: 34, items: [
      { label: c.labels.ege, value: c.numbers.ege, color: C.reader },
      { label: c.labels.other, value: c.numbers.other, color: C.placeholder },
    ] });
    hb.reveal(S.capAt(2) + 0.2, 0.5, 1.6);
    const chip = S.chip('tested', { x: 160, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 0.8);
  });

  // ---------- s15: tokens instead of letters (picture only; no result recorded) ----------
  Ch.scene('s15', function (S) {
    const c = S.c;
    const letters = [];
    for (let i = 0; i < 12; i++) letters.push(cell(S, 160 + i * 100, 300, 80, 80, C.line, '#FFFFFF'));
    const lLab = S.text(c.labels.letters, { x: 160, y: 245, w: 600, size: 36, weight: 700, color: C.ink });
    S.show(lLab, S.capAt(0));
    S.sweep(letters, S.capAt(0), 1.2);
    const toks = [0, 1, 2, 3].map((k) => S.box({ x: 160 + k * 300, y: 500, w: 280, h: 100, color: C.reader, fill: '#E6F4F4', r: 10, border: 4 }));
    const tLab = S.text(c.labels.tokens, { x: 160, y: 445, w: 600, size: 36, weight: 700, color: C.reader });
    S.show(tLab, S.capAt(1));
    S.stagger(toks, S.capAt(1), 0.35);
    const tag = S.text(c.illustration, { x: 160, y: 680, w: 1600, size: 34, color: C.soft });
    S.show(tag, S.capAt(1) + 0.6);
    const chip = S.chip('untested', { x: 160, y: 760, label: c.chip_label });
    S.pop(chip, S.capAt(1) + 1.0);
  });

  // ---------- s16: recap ----------
  Ch.scene('s16', function (S) {
    const c = S.c;
    // the three cards and the model map share the same left edge (100) and right edge (1820)
    const cards = c.cards.map((cd, i) =>
      S.box({ x: 100 + i * 587, y: 260, w: 546, h: 130, color: C.reader, fill: '#FFFFFF', r: 14, border: 6, label: cd.label, sub: cd.sub, size: 36, subSize: 30 }));
    S.show(cards[0], S.capAt(0)); S.show(cards[1], S.capAt(1)); S.show(cards[2], S.capAt(2));
    // status of the "No window" numbers: tested (the s09 result, 2 copies, one kind of question)
    const chip = S.chip(c.chip, { x: 100 + 2 * 587, y: 405, label: c.chip_label });
    S.pop(chip, S.capAt(2) + 0.4);
    const m = S.modelMap({ x: 100, y: 500, w: 1720, h: 190, highlight: 'reader', tool: 'below' });
    dimMap(m, 'reader');
    const order = ['reader', 'thinker', 'stop', 'talker', 'calc'];
    let t = S.capAt(2) + 0.3;
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.2); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.2 + 0.15, 0.3); });
    S.show(m.tool.callLabel, t + 1.1); S.draw(m.tool.call, t + 1.1, 0.5);
    S.show(m.tool.replyLabel, t + 1.5); S.draw(m.tool.reply, t + 1.5, 0.5);
  });
});
