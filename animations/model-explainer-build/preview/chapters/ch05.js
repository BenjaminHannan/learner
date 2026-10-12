Kit.chapter('ch05', function (Ch) {
  const C = Kit.C;

  // s01: where we are. The five-part map, calculator lit, call writer added below.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 230, w: 1720, h: 200, highlight: 'calc' });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.05), 0.2);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.2) + i * 0.15, 0.3));
    const cw = S.box({ x: 640, y: 520, w: 640, h: 130, label: c.labels.call, color: C.call, size: 44 });
    S.show(cw, S.capAt(0));
    S.pulse(m.parts.calc, S.capAt(1));
  });

  // s02: why a calculator. Slip out, calculator, slip back.
  Ch.scene('s02', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const slip = S.box({ x: 160, y: 420, w: 430, h: 150, label: c.labels.slip, color: C.call, size: 40 });
    const calc = S.box({ x: 745, y: 380, w: 430, h: 230, label: c.labels.calc, color: C.calc, size: 46 });
    const back = S.box({ x: 1330, y: 420, w: 430, h: 150, label: c.labels.back, color: C.tested, size: 40 });
    const a1 = S.arrow(svg, 590, 495, 745, 495, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 1175, 495, 1330, 495, { color: C.soft, width: 6 });
    S.show(slip, S.capAt(0));
    let t = S.draw(a1, S.capAt(1), 0.6);
    S.show(calc, S.capAt(1));
    const why = S.note(c.labels.why, { x: 160, y: 680, w: 1100, color: C.soft });
    S.show(why, S.capAt(1) + 0.3);
    t = S.draw(a2, S.capAt(2), 0.6);
    S.show(back, t);
  });

  // s03: the call writer reads control vector 0 and picks one of nine choices.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const v0 = S.text(c.labels.v0, { x: 160, y: 370, w: 560, size: 36, weight: 700, color: C.thinker });
    const v = S.vec({ x: 160, y: 430, n: 8, cell: 70, gap: 8, dir: 'h', color: C.thinker, seed: 4 });
    const pic = S.chip('placeholder', { x: 160, y: 600, label: c.labels.pic });
    const cw = S.box({ x: 920, y: 380, w: 380, h: 170, label: c.labels.cw, color: C.call, size: 42 });
    const a1 = S.arrow(svg, 792, 465, 918, 465, { color: C.soft, width: 6 });
    const none = S.box({ x: 1440, y: 300, w: 400, h: 110, label: c.labels.none, color: C.soft, size: 36 });
    const ops = S.box({ x: 1440, y: 470, w: 400, h: 110, label: c.labels.ops, color: C.calc, size: 36 });
    const a2 = S.arrow(svg, 1302, 465, 1438, 355, { color: C.soft, width: 6 });
    const a3 = S.arrow(svg, 1302, 465, 1438, 525, { color: C.soft, width: 6 });
    S.show(v0, S.capAt(0));
    S.show(v, S.capAt(0) + 0.2);
    S.show(pic, S.capAt(0) + 0.4);
    // the call writer appears while the first caption says it reads the vector
    S.show(cw, S.capAt(0) + 1.0);
    let t = S.draw(a1, S.capAt(0) + 1.6, 0.7);
    S.pulse(v, t + 0.1);
    S.pulse(cw, t + 0.1);
    // the nine choices appear with the second caption
    S.draw(a2, S.capAt(1), 0.5);
    S.draw(a3, S.capAt(1), 0.5);
    S.show(none, S.capAt(1) + 0.4);
    S.show(ops, S.capAt(1) + 0.6);
  });

  // s04: the eight operations, one card each, with made-up example numbers.
  Ch.scene('s04', function (S) {
    const c = S.c;
    const cols = [120, 560, 1000, 1440];
    const rows = [230, 540];
    c.ops.forEach((op, i) => {
      const x = cols[i % 4];
      const y = rows[Math.floor(i / 4)];
      const card = S.card({ x: x, y: y, w: 400, h: 280, fill: C.card, color: C.calc, r: 18 });
      const nm = S.text(op.name, { x: x + 30, y: y + 22, w: 340, size: 60, weight: 800, color: C.calc });
      const mn = S.text(op.meaning, { x: x + 30, y: y + 110, w: 340, size: 32, color: C.ink });
      const ex = S.text(op.ex, { x: x + 30, y: y + 205, w: 360, size: 36, mono: true, color: C.ink });
      const t = S.at(0.06 + i * 0.07);
      S.show(card, t);
      S.show(nm, t + 0.2);
      S.show(mn, t + 0.35);
      S.show(ex, t + 0.5);
    });
  });

  // s05: the copy trick. Pointer lands on the last digit, copy steps left, a stop head says stop.
  Ch.scene('s05', function (S) {
    const c = S.c;
    const q = S.text(c.question, { x: 80, y: 205, w: 1600, size: 36, color: C.soft });
    S.show(q, S.at(0.02));
    const L = S.letters('12', { x: 340, y: 300, size: 90 });
    S.stagger(L.cells, S.at(0.03), 0.1);
    const ptr = S.box({ x: L.cx(1) - 90, y: 440, w: 180, h: 60, label: c.labels.ptr, color: C.call, size: 30 });
    S.show(ptr, S.capAt(0));
    S.tint(L.cells[1], S.capAt(0), { fill: C.call, dur: 0.4 });
    const outR = S.box({ x: 1000, y: 600, w: 110, h: 110, label: c.labels.d2, color: C.call, size: 60 });
    const outL = S.box({ x: 1130, y: 600, w: 110, h: 110, label: c.labels.d1, color: C.call, size: 60 });
    S.pop(outR, S.capAt(0) + 0.5);
    // the pointer slides one letter left; only the letter being copied stays lit
    S.move(ptr, S.capAt(1), 0.8, { x: L.cx(0) - L.cx(1) });
    S.tint(L.cells[1], S.capAt(1), { fill: '#ffffff', dur: 0.4 });
    S.tint(L.cells[0], S.capAt(1) + 0.4, { fill: C.call, dur: 0.4 });
    S.pop(outL, S.capAt(1) + 0.9);
    const stop = S.box({ x: 1300, y: 600, w: 340, h: 110, label: c.labels.stop, color: C.stop, size: 30 });
    S.show(stop, S.capAt(2));
    S.pulse(stop, S.capAt(2) + 0.5);
    const outNote = S.note(c.labels.out, { x: 1000, y: 740, w: 640, color: C.soft });
    S.show(outNote, S.capAt(2) + 0.3);
    c.bars.forEach((b, i) => {
      const y = 290 + i * 140;
      const t = S.capAt(3) + i * 0.3;
      const lb = S.text(b.label, { x: 1100, y: y, w: 600, size: 34, color: C.ink });
      S.show(lb, t);
      const bar = S.card({ x: 1100, y: y + 50, w: b.value / 100 * 560, h: 50, fill: C.tested, r: 6 });
      S.show(bar, t);
      const num = S.text('', { x: 1100 + b.value / 100 * 560 + 16, y: y + 56, w: 220, size: 36, weight: 700, color: C.ink });
      S.show(num, t);
      S.count(num, { from: 0, to: b.value, dec: Number.isInteger(b.value) ? 0 : 1, suf: '%' }, t, 0.8);
    });
    S.show(S.chip('tested', { x: 1100, y: 222, label: c.labels.chip }), S.capAt(3));
  });

  // s06: a number not in the text is built into 21 cells, units digit first (cell 0), then the next digit, then the end mark.
  Ch.scene('s06', function (S) {
    const c = S.c;
    const top = S.text(c.labels.cells, { x: 120, y: 330, w: 1600, size: 36, color: C.calc, weight: 700 });
    S.show(top, S.at(0.02));
    const cells = [];
    for (let i = 0; i < 21; i++) cells.push(S.box({ x: 120 + i * 80, y: 460, w: 74, h: 110, label: '', color: C.calc, fill: C.card, size: 50 }));
    S.sweep(cells, S.at(0.05), 0.9);
    const z = S.text(c.labels.z, { x: 120, y: 488, w: 74, align: 'center', size: 60, weight: 700, mono: true, color: C.ink });
    const o = S.text(c.labels.o, { x: 120 + 80, y: 488, w: 74, align: 'center', size: 60, weight: 700, mono: true, color: C.ink });
    const e = S.text(c.labels.end, { x: 120 + 2 * 80, y: 506, w: 74, align: 'center', size: 30, weight: 700, mono: true, color: C.calc });
    S.show(z, S.capAt(1));
    S.show(o, S.capAt(1) + 0.9);
    S.show(e, S.capAt(1) + 1.6);
    const first = S.note(c.labels.first, { x: 120, y: 610, w: 760, color: C.calc });
    S.show(first, S.capAt(1) + 2.0);
  });

  // s07: the calculator takes call text and replies with text. Div of 12 by 5 gives a question mark.
  Ch.scene('s07', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const inn = S.box({ x: 160, y: 380, w: 460, h: 150, label: c.labels.in, color: C.call, size: 42 });
    const calc = S.box({ x: 730, y: 340, w: 460, h: 230, label: c.labels.calc, color: C.calc, size: 46 });
    const out = S.box({ x: 1290, y: 380, w: 460, h: 150, label: c.labels.out, color: C.tested, size: 42 });
    const bad = S.box({ x: 160, y: 620, w: 460, h: 130, label: c.labels.bad, color: C.call, size: 40 });
    const a1 = S.arrow(svg, 620, 455, 730, 455, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 1190, 455, 1290, 455, { color: C.soft, width: 6 });
    const a3 = S.arrow(svg, 620, 685, 730, 540, { color: C.soft, width: 6 });
    S.show(inn, S.capAt(0));
    let t = S.draw(a1, S.capAt(0) + 0.3, 0.5);
    S.show(calc, t);
    t = S.draw(a2, t + 0.2, 0.5);
    S.show(out, t);
    S.show(bad, S.capAt(1));
    S.draw(a3, S.capAt(1) + 0.3, 0.5);
    S.show(S.chip('hand', { x: 730, y: 600, label: c.labels.tag }), S.capAt(1) + 0.5);
  });

  // s08: the reply goes into the thinker's notes; the question is not read again.
  Ch.scene('s08', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const q = S.box({ x: 160, y: 230, w: 540, h: 150, label: c.labels.q, color: C.soft, size: 36 });
    const cw = S.box({ x: 160, y: 470, w: 540, h: 130, label: c.labels.cw, sub: c.labels.rd2, color: C.call, size: 40, subSize: 32 });
    const calc = S.box({ x: 160, y: 640, w: 540, h: 130, label: c.labels.calc, color: C.calc, size: 40 });
    const notes = S.card({ x: 800, y: 230, w: 1040, h: 430, fill: C.card, color: C.thinker, r: 18 });
    const nlab = S.text(c.labels.notes, { x: 840, y: 250, w: 800, size: 36, weight: 700, color: C.thinker });
    const r1 = S.box({ x: 840, y: 330, w: 960, h: 120, label: c.labels.r1, sub: c.labels.rd2, color: C.calc, size: 40, subSize: 30 });
    const r2 = S.box({ x: 840, y: 500, w: 960, h: 120, label: c.labels.r2, sub: c.labels.rd3, color: C.calc, size: 40, subSize: 30 });
    S.show(q, S.capAt(0));
    S.show(cw, S.capAt(0) + 0.2);
    S.draw(S.arrow(svg, 430, 600, 430, 640, { color: C.soft, width: 6 }), S.capAt(0) + 0.4, 0.3);
    S.show(calc, S.capAt(0) + 0.5);
    S.show(notes, S.capAt(1));
    S.show(nlab, S.capAt(1) + 0.1);
    const c1 = S.curve(svg, 700, 705, 840, 390, { bend: 60, color: C.soft, width: 6 });
    S.draw(c1, S.capAt(1) + 0.2, 0.6);
    S.show(r1, S.capAt(1) + 0.6);
    S.pulse(q, S.capAt(2));
    const c2 = S.curve(svg, 700, 705, 840, 560, { bend: 40, color: C.soft, width: 6 });
    S.draw(c2, S.capAt(2) + 0.2, 0.6);
    S.show(r2, S.capAt(2) + 0.6);
  });

  // s09: timing today. Round k+1 feeds call k; rounds 9-32 cannot call.
  Ch.scene('s09', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const rounds = c.labels.rounds.map((r, i) => S.box({ x: 160 + i * 160, y: 300, w: 130, h: 100, label: r, color: C.thinker, size: 48 }));
    S.stagger(rounds, S.at(0.03), 0.06);
    const calls = c.labels.calls.map((r, i) => S.box({ x: 160 + (i + 1) * 160, y: 520, w: 130, h: 100, label: r, color: C.call, size: 28 }));
    const arrows = c.labels.calls.map((r, i) => S.arrow(svg, 160 + (i + 1) * 160 + 65, 402, 160 + (i + 1) * 160 + 65, 518, { color: C.call, width: 5 }));
    S.show(calls[0], S.capAt(0));
    S.draw(arrows[0], S.capAt(0) - 0.4, 0.4);
    calls.slice(1).forEach((b, i) => {
      S.show(b, S.capAt(1) + i * 0.25);
      S.draw(arrows[i + 1], S.capAt(1) + i * 0.25, 0.3);
    });
    const none = S.box({ x: 1460, y: 300, w: 380, h: 100, label: c.labels.none, color: C.soft, size: 32 });
    S.show(none, S.capAt(2));
    S.show(S.chip('tested', { x: 160, y: 680, label: c.labels.chip }), S.capAt(2) + 0.3);
  });

  // s10: built, never run. Calls at any round from 2 to 32, a 16-slot tape, 1 row in 4 with 0-2 think-only rounds.
  Ch.scene('s10', function (S) {
    const c = S.c;
    const band = S.box({ x: 160, y: 290, w: 1680, h: 110, label: c.labels.any, color: C.thinker, size: 44 });
    S.show(band, S.at(0.03));
    const tapeLbl = S.text(c.labels.tape, { x: 160, y: 455, w: 800, size: 34, color: C.call, weight: 700 });
    S.show(tapeLbl, S.at(0.05));
    const slots = [];
    for (let i = 0; i < 16; i++) slots.push(S.box({ x: 160 + i * 105, y: 500, w: 95, h: 100, label: '', color: C.call, fill: C.card, size: 30 }));
    S.sweep(slots, S.at(0.06), 0.7);
    for (let i = 0; i < 4; i++) S.tint(slots[i], S.capAt(1) + i * 0.3, { fill: C.call, dur: 0.3 });
    S.show(S.chip('placeholder', { x: 1250, y: 470, label: c.labels.pic }), S.capAt(1));
    const gap = S.note(c.labels.gap, { x: 160, y: 690, w: 900, color: C.untested });
    S.show(gap, S.capAt(3));
    S.show(S.chip('untested', { x: 1150, y: 690, label: c.labels.chip }), S.capAt(3) + 0.3);
  });

  // s11: still hand-written (brown chips), then group 2 writes the whole call as letters.
  Ch.scene('s11', function (S) {
    const c = S.c;
    const items = [c.labels.ops, c.labels.num, c.labels.copy, c.labels.flip];
    const boxes = items.map((t, i) => S.box({ x: 160 + (i % 2) * 520, y: 260 + Math.floor(i / 2) * 180, w: 480, h: 140, label: t, color: C.hand, fill: C.card, size: 34, textColor: C.ink }));
    boxes.forEach((b, i) => S.show(b, S.capAt(0) + i * 0.4));
    S.show(S.chip('untested', { x: 1200, y: 580, label: c.labels.chip }), S.capAt(2));
    const g2 = S.letters(c.labels.g2call, { x: 1200, y: 660, size: 72 });
    S.stagger(g2.cells, S.capAt(2) + 0.2, 0.12);
  });

  // s12: the evidence on a number line (pooled-5 difference, with its likely range).
  Ch.scene('s12', function (S) {
    const c = S.c;
    const nl = c.numline;
    const X = (v) => 200 + (v - nl.min) / (nl.max - nl.min) * 1300;
    const line = S.card({ x: 200, y: 520, w: 1300, h: 4, fill: C.soft, r: 2 });
    S.show(line, S.capAt(0));
    const zero = S.card({ x: X(0), y: 440, w: 3, h: 180, fill: C.calc });
    S.show(zero, S.capAt(1));
    [-1, 0, 1, 2].forEach((v, i) => {
      const tk = S.text(c.labels.ticks[i], { x: X(v) - 40, y: 540, w: 80, align: 'center', size: 34, color: C.soft });
      S.show(tk, S.capAt(0));
    });
    const zl = S.text(c.labels.ob, { x: X(0) - 200, y: 400, w: 400, align: 'center', size: 34, color: C.calc });
    S.show(zl, S.capAt(1));
    const band = S.card({ x: X(nl.lo), y: 500, w: X(nl.hi) - X(nl.lo), h: 44, fill: C.tested, r: 8 });
    S.show(band, S.capAt(2));
    const dot = S.card({ x: X(nl.mean) - 16, y: 494, w: 32, h: 32, fill: C.thinker, r: 16 });
    S.pop(dot, S.capAt(2) + 0.4);
    const ol = S.text(c.labels.out, { x: X(nl.mean) - 220, y: 400, w: 440, align: 'center', size: 34, color: C.thinker, weight: 700 });
    S.show(ol, S.capAt(2) + 0.4);
    S.show(S.chip('tested', { x: 200, y: 660, label: c.labels.chip }), S.capAt(4));
  });

  // s13: the swap test. Five copies at or above the 99 pass line; copy F unscored.
  Ch.scene('s13', function (S) {
    const c = S.c;
    const X = (v) => 300 + (v - 98.5) / 1.5 * 1200;
    const axis = S.card({ x: 300, y: 500, w: 1200, h: 4, fill: C.soft, r: 2 });
    S.show(axis, S.capAt(0));
    const pass = S.card({ x: X(99) - 2, y: 330, w: 4, h: 420, fill: C.tested });
    S.show(pass, S.capAt(1));
    const pl = S.text(c.labels.pass, { x: X(99) - 200, y: 300, w: 400, align: 'center', size: 34, color: C.tested, weight: 700 });
    S.show(pl, S.capAt(1));
    c.vals.forEach((d, i) => {
      const t = S.capAt(2) + i * 0.3;
      const dot = S.card({ x: X(d.value) - 16, y: 484, w: 32, h: 32, fill: C.thinker, r: 16 });
      S.pop(dot, t);
      const lb = S.text(d.label, { x: X(d.value) - 40, y: 540, w: 80, align: 'center', size: 36, weight: 700 });
      S.show(lb, t);
      const vt = S.text('', { x: X(d.value) - 80, y: 430, w: 160, align: 'center', size: 34, color: C.ink });
      S.count(vt, { from: 98.5, to: d.value, dec: 2 }, t, 0.6);
    });
    S.show(S.chip('placeholder', { x: 300, y: 620, label: c.labels.lost }), S.capAt(3));
    S.show(S.chip('tested', { x: 300, y: 700, label: c.labels.chip }), S.capAt(3) + 0.3);
  });

  // s14: the leak test. Bars against the sealed limit of 5; one mark missed, then cleared by the owner.
  Ch.scene('s14', function (S) {
    const c = S.c;
    const x0 = 520, W = 1100, max = 6;
    const lim = S.card({ x: x0 + 5 / max * W - 2, y: 240, w: 4, h: 500, fill: C.tested });
    S.show(lim, S.capAt(1));
    const ll = S.text(c.labels.lim, { x: x0 + 5 / max * W - 200, y: 200, w: 400, align: 'center', size: 34, color: C.tested, weight: 700 });
    S.show(ll, S.capAt(1));
    c.vals.forEach((d, i) => {
      const y = 260 + i * 80;
      const t = S.capAt(1) + i * 0.2;
      const lb = S.text(d.label, { x: 440, y: y + 8, w: 60, align: 'right', size: 36, weight: 700 });
      S.show(lb, t);
      const bar = S.card({ x: x0, y: y, w: d.value / max * W, h: 56, fill: C.untested, r: 6 });
      S.show(bar, t);
      const num = S.text('', { x: x0 + d.value / max * W + 16, y: y + 8, w: 200, size: 36, weight: 700, color: C.ink });
      S.count(num, { from: 0, to: d.value, dec: 2 }, t, 0.6);
    });
    S.show(S.chip('untested', { x: 520, y: 790, label: c.labels.chip }), S.capAt(3));
  });

  // s15: what is tested, what is not, and a three-line recap.
  Ch.scene('s15', function (S) {
    const c = S.c;
    const a = S.chip('tested', { x: 160, y: 300, label: c.labels.t });
    const b = S.chip('untested', { x: 160, y: 450, label: c.labels.n });
    const d = S.chip('untested', { x: 160, y: 600, label: c.labels.b });
    S.pop(a, S.capAt(0));
    S.pop(b, S.capAt(1));
    S.pop(d, S.capAt(2));
    const r1 = S.text(c.labels.rem1, { x: 1000, y: 300, w: 820, size: 44, weight: 700, color: C.ink });
    const r2 = S.text(c.labels.rem2, { x: 1000, y: 420, w: 820, size: 44, weight: 700, color: C.ink });
    const r3 = S.text(c.labels.rem3, { x: 1000, y: 540, w: 820, size: 44, weight: 700, color: C.ink });
    S.show(r1, S.capAt(3));
    S.show(r2, S.capAt(3) + 0.8);
    S.show(r3, S.capAt(3) + 1.6);
  });
});
