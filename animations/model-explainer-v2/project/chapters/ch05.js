Kit.chapter('ch05', function (Ch) {
  const C = Kit.C;

  // s01: where we are. The four-part model (reader, thinker, stop switch, talker) with the calculator OUTSIDE it, lit.
  // New design: the talker's line calls the calculator at the end of a turn; the reply starts the next turn and the whole reader reads it.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 440, w: 1720, h: 200, highlight: 'calc', tool: 'above' });
    // the kit greys the four dimmed boxes to the placeholder grey (too light on cream): one step darker, still quieter than the lit Calculator box
    ['reader', 'thinker', 'stop', 'talker'].forEach((k) => {
      m.parts[k].querySelectorAll('.lab').forEach((n) => { n.style.color = C.soft; });
      m.parts[k].querySelectorAll('.sub').forEach((n) => { n.style.color = C.soft; n.style.fontWeight = '600'; });
    });
    S.stagger(m.order.map((k) => m.parts[k]), S.at(0.05), 0.2);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.2) + i * 0.15, 0.3));
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    // new design: the talker's line calls the calculator at the end of a turn (no call writer inside the thinker); status tag below the map
    S.show(S.chip('untested', { x: 100, y: 760, label: c.labels.chip }), S.capAt(0));
    S.draw(m.tool.call, S.capAt(0) + 1.8, 0.7);
    S.show(m.tool.callLabel, S.capAt(0) + 2.2);
    S.draw(m.tool.reply, S.capAt(0) + 4.0, 0.7);
    S.show(m.tool.replyLabel, S.capAt(0) + 4.4);
    S.pulse(m.parts.calc, S.capAt(1));
  });

  // s02: why a calculator. The thinker's call goes out as text, the outside calculator answers, and the reader reads the reply.
  Ch.scene('s02', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const slip = S.box({ x: 80, y: 420, w: 380, h: 150, label: c.labels.slip, color: C.call, size: 38 });
    const calc = S.box({ x: 560, y: 380, w: 400, h: 230, label: c.labels.calc, sub: c.labels.calcsub, color: C.calc, size: 46, subSize: 30 });
    calc.style.borderStyle = 'dashed';
    const back = S.box({ x: 1060, y: 420, w: 340, h: 150, label: c.labels.back, color: C.calc, size: 38 });
    const rd = S.box({ x: 1500, y: 400, w: 340, h: 190, label: c.labels.reader, sub: c.labels.readersub, color: C.reader, size: 46, subSize: 30 });
    const a1 = S.arrow(svg, 460, 495, 560, 495, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 960, 495, 1060, 495, { color: C.soft, width: 6 });
    const a3 = S.arrow(svg, 1400, 495, 1500, 495, { color: C.soft, width: 6 });
    const n1 = S.text(c.labels.slipnote, { x: 80, y: 585, w: 440, size: 28, color: C.soft });
    const n2 = S.text(c.labels.backnote, { x: 1060, y: 585, w: 400, size: 28, color: C.soft });
    S.show(slip, S.capAt(0));
    S.show(n1, S.capAt(0) + 0.3);
    let t = S.draw(a1, S.capAt(1), 0.6);
    S.show(calc, S.capAt(1));
    const why = S.note(c.labels.why, { x: 80, y: 700, w: 1100, color: C.soft });
    S.show(why, S.capAt(1) + 0.3);
    t = S.draw(a2, S.capAt(2), 0.6);
    S.show(back, t);
    S.show(n2, t + 0.2);
    t = S.draw(a3, t + 0.8, 0.6);
    S.show(rd, t);
  });

  // s03 (tested version): the call writer reads control vector 0 and picks one of nine choices.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const v0 = S.text(c.labels.v0, { x: 160, y: 370, w: 560, size: 36, weight: 700, color: C.thinker });
    const v = S.vec({ x: 160, y: 430, n: 8, cell: 70, gap: 8, dir: 'h', color: C.thinker, seed: 4 });
    const pic = S.chip('placeholder', { x: 160, y: 600, label: c.labels.pic });
    const cw = S.box({ x: 920, y: 380, w: 380, h: 170, label: c.labels.cw, color: C.call, size: 42 });
    const cwn = S.text(c.labels.cwnote, { x: 920, y: 565, w: 380, align: 'center', size: 28, color: C.soft });
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
    S.show(cwn, S.capAt(0) + 1.2);
    let t = S.draw(a1, S.capAt(0) + 1.6, 0.7);
    S.pulse(v, t + 0.1);
    S.pulse(cw, t + 0.1);
    // the nine choices appear with the second caption
    S.draw(a2, S.capAt(1), 0.5);
    S.draw(a3, S.capAt(1), 0.5);
    S.show(none, S.capAt(1) + 0.4);
    S.show(ops, S.capAt(1) + 0.6);
    S.show(S.chip('tested', { x: 160, y: 740, label: c.labels.chip }), S.capAt(0) + 0.6);
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

  // s05 (tested version): the copy trick. Pointer lands on the last digit, copy steps left, a stop head says stop.
  Ch.scene('s05', function (S) {
    const c = S.c;
    const q = S.text(c.question, { x: 80, y: 205, w: 1600, size: 36, color: C.soft });
    S.show(q, S.at(0.02));
    const L = S.letters(c.labels.num, { x: 340, y: 300, size: 90 });
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
    const top = S.text(c.labels.cells, { x: 120, y: 290, w: 1600, size: 36, color: C.calc, weight: 700 });
    S.show(top, S.at(0.02));
    const cells = [];
    for (let i = 0; i < 21; i++) cells.push(S.box({ x: 120 + i * 80, y: 420, w: 74, h: 110, label: '', color: C.calc, fill: C.card, size: 50 }));
    S.sweep(cells, S.at(0.05), 0.9);
    const z = S.text(c.labels.z, { x: 120, y: 448, w: 74, align: 'center', size: 60, weight: 700, mono: true, color: C.ink });
    const o = S.text(c.labels.o, { x: 120 + 80, y: 448, w: 74, align: 'center', size: 60, weight: 700, mono: true, color: C.ink });
    const e = S.text(c.labels.end, { x: 120 + 2 * 80, y: 466, w: 74, align: 'center', size: 30, weight: 700, mono: true, color: C.calc });
    S.show(z, S.capAt(1));
    S.show(o, S.capAt(1) + 0.9);
    S.show(e, S.capAt(1) + 1.6);
    // after the end mark the other 18 cells are not used (tool.py: cells are read up to the first end mark): dim them and say so
    const tEnd = S.capAt(1) + 2.2;
    for (let i = 3; i < 21; i++) S.tint(cells[i], tEnd, { border: C.line, fill: '#FAF6EE', dur: 0.5 });
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const br = S.path(svg, [[364, 548], [364, 562], [1790, 562], [1790, 548]], { color: C.soft, width: 4, head: 0 });
    S.draw(br, tEnd + 0.4, 0.6);
    const un = S.text(c.labels.unused, { x: 364, y: 574, w: 1426, align: 'center', size: 32, weight: 700, color: C.soft });
    S.show(un, tEnd + 0.8);
    const first = S.note(c.labels.first, { x: 120, y: 650, w: 760, color: C.calc });
    S.show(first, S.capAt(1) + 2.0);
    // status: the 21-cell version is the new build (never run); the tested copies had 11 cells (said in the caption)
    S.show(S.chip('untested', { x: 120, y: 770, label: c.labels.chip }), S.at(0.06));
    S.show(S.chip('placeholder', { x: 900, y: 660, label: c.labels.pic }), S.capAt(1) + 0.9);
  });

  // s07: the OUTSIDE calculator takes call text and replies with text (read by the reader). Div of 12 by 5 gives a question mark.
  Ch.scene('s07', function (S) {
    const c = S.c;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    // two calls through the same calculator: row 1 runs (sub 12 5 -> 7), row 2 cannot run (div 12 5 -> ?)
    const inn = S.box({ x: 160, y: 330, w: 460, h: 150, label: c.labels.in, color: C.call, size: 42 });
    const calc = S.box({ x: 730, y: 300, w: 460, h: 390, label: c.labels.calc, sub: c.labels.calcsub, color: C.calc, size: 46, subSize: 32 });
    calc.style.borderStyle = 'dashed';
    const out = S.box({ x: 1290, y: 330, w: 460, h: 150, label: c.labels.out, color: C.calc, size: 42 });
    const in2 = S.box({ x: 160, y: 510, w: 460, h: 150, label: c.labels.in2, color: C.call, size: 42 });
    const out2 = S.box({ x: 1290, y: 510, w: 460, h: 150, label: c.labels.out2, color: C.calc, size: 42 });
    const a1 = S.arrow(svg, 620, 405, 730, 405, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 1190, 405, 1290, 405, { color: C.soft, width: 6 });
    const a3 = S.arrow(svg, 620, 585, 730, 585, { color: C.soft, width: 6 });
    const a4 = S.arrow(svg, 1190, 585, 1290, 585, { color: C.soft, width: 6 });
    const nf = S.text(c.labels.frm, { x: 160, y: 262, w: 480, size: 28, weight: 700, color: C.call });
    const nt = S.text(c.labels.to, { x: 1290, y: 262, w: 480, size: 28, weight: 700, color: C.reader });
    S.show(nf, S.capAt(0));
    S.show(inn, S.capAt(0));
    let t = S.draw(a1, S.capAt(0) + 0.3, 0.5);
    S.show(calc, t);
    t = S.draw(a2, t + 0.2, 0.5);
    S.show(out, t);
    S.show(nt, t);
    S.show(in2, S.capAt(1));
    t = S.draw(a3, S.capAt(1) + 0.4, 0.5);
    t = S.draw(a4, t + 0.2, 0.5);
    S.show(out2, t);
    S.show(S.chip('hand', { x: 730, y: 715, label: c.labels.tag }), S.capAt(1) + 0.5);
  });

  // s08 (tested version): the call goes out as text to the OUTSIDE calculator; the reply comes back as text, is read by the reader (letter window)
  // and only then added to the thinker's notes. The question is not read again.
  Ch.scene('s08', function (S) {
    const c = S.c;
    const q = S.box({ x: 80, y: 230, w: 460, h: 110, label: c.labels.q, color: C.soft, size: 34 });
    const cw = S.box({ x: 80, y: 390, w: 460, h: 130, label: c.labels.cw, sub: c.labels.cwsub, color: C.call, size: 40, subSize: 28 });
    const calc = S.box({ x: 80, y: 630, w: 460, h: 150, label: c.labels.calc, sub: c.labels.calcsub, color: C.calc, size: 40, subSize: 28 });
    calc.style.borderStyle = 'dashed';
    const r1 = S.box({ x: 640, y: 430, w: 360, h: 110, label: c.labels.r1, sub: c.labels.rd2, color: C.calc, size: 38, subSize: 28 });
    const r2 = S.box({ x: 640, y: 640, w: 360, h: 110, label: c.labels.r2, sub: c.labels.rd3, color: C.calc, size: 38, subSize: 28 });
    const rl = S.text(c.labels.replyTxt, { x: 640, y: 386, w: 360, size: 28, weight: 700, color: C.reader });
    const cl = S.text(c.labels.callTxt, { x: 316, y: 556, w: 220, size: 28, weight: 700, color: C.call });
    const rd = S.box({ x: 1090, y: 440, w: 260, h: 300, label: c.labels.reader, sub: c.labels.readersub, color: C.reader, size: 46, subSize: 30 });
    const notes = S.card({ x: 1440, y: 330, w: 400, h: 420, fill: C.card, color: C.thinker, r: 18 });
    const nlab = S.text(c.labels.notes, { x: 1470, y: 350, w: 360, size: 36, weight: 700, color: C.thinker });
    const n1 = S.text(c.labels.r1, { x: 1470, y: 450, w: 360, size: 40, mono: true, color: C.ink });
    const n2 = S.text(c.labels.r2, { x: 1470, y: 530, w: 360, size: 40, mono: true, color: C.ink });
    // drawing layer made after the boxes so no arrowhead is hidden
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    S.show(q, S.capAt(0));
    S.show(cw, S.capAt(0) + 0.2);
    S.draw(S.arrow(svg, 310, 524, 310, 626, { color: C.call, width: 6 }), S.capAt(0) + 0.4, 0.3);
    S.show(cl, S.capAt(0) + 0.5);
    S.show(calc, S.capAt(0) + 0.6);
    // second caption: reply text -> reader -> notes
    S.draw(S.curve(svg, 542, 690, 638, 495, { bend: 40, color: C.reader, width: 6 }), S.capAt(1) + 0.1, 0.6);
    S.show(r1, S.capAt(1) + 0.5);
    S.show(rl, S.capAt(1) + 0.5);
    S.draw(S.arrow(svg, 1002, 485, 1088, 590, { color: C.reader, width: 6 }), S.capAt(1) + 1.2, 0.5);
    S.show(rd, S.capAt(1) + 1.2);
    S.show(S.text(c.labels.newrd, { x: 1060, y: 752, w: 340, size: 25, weight: 700, color: C.reader }), S.capAt(1) + 1.6);
    S.show(notes, S.capAt(1) + 1.9);
    S.show(nlab, S.capAt(1) + 2.0);
    S.draw(S.arrow(svg, 1352, 590, 1438, 590, { color: C.reader, width: 6 }), S.capAt(1) + 2.2, 0.5);
    S.show(n1, S.capAt(1) + 2.7);
    // third caption: the question is not read again; the second reply takes the same road
    S.pulse(q, S.capAt(2));
    S.draw(S.arrow(svg, 542, 705, 638, 695, { color: C.reader, width: 6 }), S.capAt(2) + 0.2, 0.5);
    S.show(r2, S.capAt(2) + 0.6);
    S.draw(S.arrow(svg, 1002, 695, 1088, 590, { color: C.reader, width: 6 }), S.capAt(2) + 1.3, 0.5);
    S.show(n2, S.capAt(2) + 1.9);
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
    // rounds 1-8 and calls 1-7 are the tested copies; rounds 9-32 exist only in the built (never run) learned-stop code
    S.show(S.chip('untested', { x: 1460, y: 420, label: c.labels.chip2 }), S.capAt(2) + 0.3);
    S.show(S.chip('tested', { x: 160, y: 680, label: c.labels.chip }), S.capAt(2) + 0.3);
  });

  // s10: built, never run. Calls at any round from 2 to 32, a 16-slot tape, 1 row in 4 with 0-2 think-only rounds.
  Ch.scene('s10', function (S) {
    const c = S.c;
    const band = S.box({ x: 160, y: 290, w: 1680, h: 110, label: c.labels.any, color: C.thinker, size: 44 });
    S.show(band, S.at(0.03));
    // the tape label and the "picture only" tag share one line above the slots, with a clear gap before the slots start
    const tapeLbl = S.text(c.labels.tape, { x: 160, y: 440, w: 300, size: 34, color: C.call, weight: 700 });
    S.show(tapeLbl, S.capAt(2));
    const slots = [];
    for (let i = 0; i < 16; i++) slots.push(S.box({ x: 160 + i * 105, y: 520, w: 95, h: 100, label: '', color: C.call, fill: C.card, size: 30 }));
    S.sweep(slots, S.capAt(2), 0.7);
    for (let i = 0; i < 4; i++) S.tint(slots[i], S.capAt(2) + 1.2 + i * 0.3, { fill: C.call, dur: 0.3 });
    S.show(S.chip('placeholder', { x: 480, y: 436, label: c.labels.pic }), S.capAt(2) + 1.2);
    const gap = S.note(c.labels.gap, { x: 160, y: 690, w: 900, color: C.untested });
    S.show(gap, S.capAt(3));
    S.show(S.chip('untested', { x: 1150, y: 690, label: c.labels.chip }), S.capAt(3) + 0.3);
  });

  // s11: still hand-written (brown chips), then group 2 writes the whole call as letters.
  Ch.scene('s11', function (S) {
    const c = S.c;
    const items = [c.labels.ops, c.labels.num, c.labels.copy, c.labels.flip];
    // four hand-written parts in one row across the width; the group-2 call sits centred below them
    const boxes = items.map((t, i) => S.box({ x: 100 + i * 440, y: 260, w: 400, h: 170, label: t, color: C.hand, fill: C.card, size: 34, textColor: C.ink }));
    boxes.forEach((b, i) => S.show(b, S.capAt(0) + i * 0.4));
    S.show(S.chip('untested', { x: 733, y: 540, label: c.labels.chip }), S.capAt(2));
    const g2 = S.letters(c.labels.g2call, { x: 733, y: 630, size: 72 });
    S.stagger(g2.cells, S.capAt(2) + 0.2, 0.12);
    S.show(S.chip('placeholder', { x: 733, y: 760, label: c.labels.pic }), S.capAt(2) + 0.6);
  });

  // s12: the evidence on a number line (pooled-5 difference, with its likely range).
  Ch.scene('s12', function (S) {
    const c = S.c;
    const nl = c.numline;
    const X = (v) => 200 + (v - nl.min) / (nl.max - nl.min) * 1300;
    const line = S.card({ x: 200, y: 520, w: 1300, h: 4, fill: C.soft, r: 2 });
    S.show(line, S.capAt(0));
    [-1, 0, 1, 2].forEach((v, i) => {
      const tk = S.text(c.labels.ticks[i], { x: X(v) - 40, y: 565, w: 80, align: 'center', size: 34, color: C.soft });
      S.show(tk, S.capAt(0));
    });
    const axl = S.text(c.labels.axis, { x: 200, y: 615, w: 1300, align: 'center', size: 32, color: C.soft });
    S.show(axl, S.capAt(0));
    // likely range (green bar, labelled inside), then the zero line on top of it, then the T1SDR dot and its label
    const band = S.card({ x: X(nl.lo), y: 495, w: X(nl.hi) - X(nl.lo), h: 54, fill: C.tested, r: 8 });
    S.show(band, S.capAt(2));
    const zero = S.card({ x: X(0) - 1.5, y: 430, w: 3, h: 130, fill: C.calc, color: C.calc });
    S.show(zero, S.capAt(1));
    const zl = S.text(c.labels.ob, { x: X(0) - 420, y: 400, w: 400, align: 'right', size: 34, color: C.calc, weight: 700 });
    S.show(zl, S.capAt(1));
    const rl = S.text(c.labels.rng, { x: X(0) + 22, y: 503, w: 230, size: 30, color: '#FFFFFF', weight: 700 });
    S.show(rl, S.capAt(2) + 0.3);
    const dot = S.card({ x: X(nl.mean) - 16, y: 506, w: 32, h: 32, fill: C.thinker, color: '#FFFFFF', r: 16 });
    S.pop(dot, S.capAt(2) + 0.4);
    const ol = S.text(c.labels.out, { x: X(nl.mean) - 220, y: 400, w: 440, align: 'center', size: 34, color: C.thinker, weight: 700 });
    S.show(ol, S.capAt(2) + 0.4);
    S.show(S.chip('tested', { x: 200, y: 700, label: c.labels.chip }), S.capAt(3));
  });

  // s12b: chain-5 and calculator off (moved out of s12 so each result has its own picture).
  Ch.scene('s12b', function (S) {
    const c = S.c;
    const ch = c.chain;
    const X = (v) => 560 + (v - 99.3) / 0.6 * 1100;       // drawing scale only: 99.3 .. 99.9
    // faint grid lines and the axis
    c.labels.ticks.forEach((tk) => {
      const g = S.card({ x: X(Number(tk)) - 1, y: 250, w: 2, h: 190, fill: C.line, color: C.line, r: 1 });
      S.show(g, S.capAt(0));
    });
    const ax = S.card({ x: 560, y: 438, w: 1100, h: 4, fill: C.soft, r: 2 });
    S.show(ax, S.capAt(0));
    c.labels.ticks.forEach((tk) => {
      const t = S.text(tk, { x: X(Number(tk)) - 50, y: 455, w: 100, align: 'center', size: 32, color: C.soft });
      S.show(t, S.capAt(0));
    });
    const axl = S.text(c.labels.axis, { x: 560, y: 505, w: 1100, align: 'center', size: 32, color: C.soft });
    S.show(axl, S.capAt(0));
    // outside (T1SDR) first, then inside (B2)
    const lo1 = S.text(c.labels.outside, { x: 100, y: 273, w: 420, align: 'right', size: 34, weight: 700, color: C.ink });
    const bo = S.card({ x: X(ch.outLo), y: 270, w: X(ch.outHi) - X(ch.outLo), h: 48, fill: C.tested, r: 8 });
    const dm = S.card({ x: X(ch.outMean) - 14, y: 280, w: 28, h: 28, fill: C.thinker, color: '#FFFFFF', r: 14 });
    const ml = S.text(c.labels.mean, { x: X(ch.outMean) - 60, y: 224, w: 120, align: 'center', size: 30, weight: 700, color: C.thinker });
    S.show(lo1, S.capAt(0) + 0.6);
    S.show(bo, S.capAt(0) + 1.0);
    S.pop(dm, S.capAt(0) + 1.8);
    S.show(ml, S.capAt(0) + 1.9);
    const lo2 = S.text(c.labels.inside, { x: 100, y: 353, w: 420, align: 'right', size: 34, weight: 700, color: C.ink });
    const bi = S.card({ x: X(ch.inLo), y: 350, w: X(ch.inHi) - X(ch.inLo), h: 48, fill: C.calc, r: 8 });
    S.show(lo2, S.capAt(0) + 3.4);
    S.show(bi, S.capAt(0) + 3.8);
    // calculator switched off
    const div = S.card({ x: 100, y: 580, w: 1720, h: 3, fill: C.line, color: C.line, r: 2 });
    S.show(div, S.capAt(1));
    const lf = S.text(c.labels.off, { x: 100, y: 650, w: 420, align: 'right', size: 34, weight: 700, color: C.ink });
    const zr = S.text(c.labels.zero, { x: 560, y: 610, w: 260, size: 120, weight: 800, color: C.ink });
    const sb = S.text(c.labels.offsub, { x: 840, y: 655, w: 900, size: 36, color: C.soft });
    S.show(lf, S.capAt(1) + 0.3);
    S.show(zr, S.capAt(1) + 0.6);
    S.show(sb, S.capAt(1) + 0.9);
    S.show(S.chip('tested', { x: 100, y: 780, label: c.labels.chip }), S.capAt(1) + 1.2);
  });

  // s13: the swap test. Five copies at or above the 99 pass line; copy F unscored.
  Ch.scene('s13', function (S) {
    const c = S.c;
    const X = (v) => 300 + (v - 98.5) / 1.5 * 1200;
    const axis = S.card({ x: 300, y: 500, w: 1200, h: 4, fill: C.soft, r: 2 });
    S.show(axis, S.capAt(0));
    const pass = S.card({ x: X(99) - 2, y: 355, w: 4, h: 255, fill: C.ink, color: C.ink });
    S.show(pass, S.capAt(1));
    const pl = S.text(c.labels.pass, { x: X(99) - 200, y: 300, w: 400, align: 'center', size: 34, color: C.ink, weight: 700 });
    S.show(pl, S.capAt(1));
    c.vals.forEach((d, i) => {
      const t = S.capAt(2) + i * 0.3;
      const dot = S.card({ x: X(d.value) - 16, y: 484, w: 32, h: 32, fill: C.thinker, r: 16 });
      S.pop(dot, t);
      const lb = S.text(d.label, { x: X(d.value) - 40, y: 540, w: 80, align: 'center', size: 36, weight: 700 });
      S.show(lb, t);
      const vt = S.text('', { x: X(d.value) - 80, y: 430, w: 160, align: 'center', size: 30, color: C.ink });
      S.show(vt, t);
      S.count(vt, { from: 98.5, to: d.value, dec: 2 }, t, 0.6);
    });
    // chips sit below the end of the pass line (not beside it); grey = no result exists for copy F on this check
    S.show(S.chip('placeholder', { x: 300, y: 665, label: c.labels.lost }), S.capAt(3));
    S.show(S.chip('tested', { x: 300, y: 735, label: c.labels.chip }), S.capAt(3) + 0.3);
  });

  // s14: the leak test. Bars against the sealed limit of 5; one mark missed, then cleared by the owner.
  // Bars above the limit stay warning orange; E (exactly 5.00, at the limit) is grey; B2 is a floating range row on the same axis.
  Ch.scene('s14', function (S) {
    const c = S.c;
    const x0 = 520, W = 1100, max = 6, rowH = 68, barH = 50, y0 = 250;
    c.vals.forEach((d, i) => {
      const y = y0 + i * rowH;
      const t = S.capAt(1) + i * 0.2;
      const lb = S.text(d.label, { x: 440, y: y + 5, w: 60, align: 'right', size: 36, weight: 700 });
      S.show(lb, t);
      const bar = S.card({ x: x0, y: y, w: d.value / max * W, h: barH, fill: d.value > 5 ? C.warn : C.soft, r: 6 });
      S.show(bar, t);
      const num = S.text('', { x: x0 + d.value / max * W + 16, y: y + 5, w: 200, size: 36, weight: 700, color: C.ink });
      S.show(num, t);
      S.count(num, { from: 0, to: d.value, dec: 2 }, t, 0.6);
    });
    // B2 reference row (the caption's 3.09 to 3.75), drawn as a floating range bar on the same axis
    const yb = y0 + 6 * rowH + 24;
    const b2l = S.text(c.labels.b2, { x: 420, y: yb + 5, w: 80, align: 'right', size: 36, weight: 700, color: C.calc });
    const b2 = S.card({ x: x0 + c.b2.lo / max * W, y: yb, w: (c.b2.hi - c.b2.lo) / max * W, h: barH, fill: C.calc, r: 6 });
    const b2n = S.text(c.b2.lo.toFixed(2) + '–' + c.b2.hi.toFixed(2), { x: x0 + c.b2.lo / max * W - 16 - 260, y: yb + 5, w: 260, align: 'right', size: 36, weight: 700, color: C.ink });
    S.show(b2l, S.capAt(2) + 0.3);
    S.show(b2, S.capAt(2) + 0.3);
    S.show(b2n, S.capAt(2) + 0.6);
    // the limit line is made after the bars so it is drawn on top of them
    const lim = S.card({ x: x0 + 5 / max * W - 2, y: 242, w: 4, h: yb + barH + 10 - 242, fill: C.ink, color: C.ink });
    S.show(lim, S.capAt(1));
    const ll = S.text(c.labels.lim, { x: x0 + 5 / max * W - 200, y: 196, w: 400, align: 'center', size: 34, color: C.ink, weight: 700 });
    S.show(ll, S.capAt(1));
    S.show(S.chip('untested', { x: 520, y: 782, label: c.labels.chip, color: C.warn }), S.capAt(3));
  });

  // s15: what is tested, what is not, and a three-line recap.
  // Status chips on top (one column), a divider, then the three "remember" lines below it, so the two groups cannot be read as pairs.
  Ch.scene('s15', function (S) {
    const c = S.c;
    const a = S.chip('tested', { x: 160, y: 270, label: c.labels.t, size: 34 });
    const b = S.chip('untested', { x: 160, y: 360, label: c.labels.n, size: 34 });
    const d = S.chip('untested', { x: 160, y: 450, label: c.labels.b, size: 34 });
    S.pop(a, S.capAt(0));
    S.pop(b, S.capAt(1));
    S.pop(d, S.capAt(2));
    const div = S.card({ x: 160, y: 548, w: 1600, h: 3, fill: C.line, color: C.line, r: 2 });
    S.show(div, S.capAt(3));
    const r1 = S.text(c.labels.rem1, { x: 160, y: 595, w: 1600, size: 44, weight: 700, color: C.ink });
    const r2 = S.text(c.labels.rem2, { x: 160, y: 675, w: 1600, size: 44, weight: 700, color: C.ink });
    const r3 = S.text(c.labels.rem3, { x: 160, y: 755, w: 1600, size: 44, weight: 700, color: C.ink });
    S.show(r1, S.capAt(3));
    S.show(r2, S.capAt(3) + 0.8);
    S.show(r3, S.capAt(3) + 1.6);
  });
});
