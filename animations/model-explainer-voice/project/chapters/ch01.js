/* Chapter 1: one question, start to finish. Every on-screen string lives in content/ch01.json. */
Kit.chapter('ch01', function (Ch) {
  const C = Kit.C;
  const TINT = '#cfe3ff';
  const STOP_ON = '#e9d5ff';   // light purple = the stop switch lit (illustration); green would wrongly mean tested

  // ---- local layout helpers (same arithmetic as S.letters, so rows can be centred and arrows aimed) ----
  function rowW(str, size, gap) {
    gap = gap == null ? 6 : gap;
    const cw = Math.round(size * 0.82), sp = Math.round(cw * 0.6);
    let w = 0;
    [...str].forEach((ch) => { w += ch === ' ' ? sp : cw + gap; });
    return w - gap;
  }
  const centreX = (str, size) => Math.round((1920 - rowW(str, size)) / 2);
  // x centre of character i, measured from the start of the row
  function relCx(str, size, i, gap) {
    gap = gap == null ? 6 : gap;
    const cw = Math.round(size * 0.82), sp = Math.round(cw * 0.6);
    let x = 0;
    for (let k = 0; k < i; k++) x += str[k] === ' ' ? sp : cw + gap;
    return str[i] === ' ' ? x + cw * 0.3 : x + cw / 2;
  }
  const monoW = (str, size) => [...str].length * size * 0.592;   // DejaVu Sans Mono advance, bold, kit letter-spacing

  // a status chip centred on cx (a full-width flex row holds it, so no transform is needed to centre it)
  function cchip(S, kind, o, cx, y) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;display:flex;justify-content:center;pointer-events:none;width:1200px;';
    wrap.style.left = (cx - 600) + 'px'; wrap.style.top = y + 'px';
    S.g.appendChild(wrap);
    const chip = S.chip(kind, Object.assign({ parent: wrap, x: 0, y: 0 }, o));
    chip.style.position = 'relative';
    return chip;
  }
  // a bracket with its two ends pointing up (to the things it groups); drawn with S.draw
  function bracket(S, svg, x1, x2, y, tick, color) {
    return S.path(svg, [[x1, y - tick], [x1, y], [x2, y], [x2, y - tick]], { color, width: 4, head: 0 });
  }

  // the example question as two centred rows of letter boxes (row A = chars 0-34, row B = chars 36-70)
  function question(S, c, y, rowGap) {
    const x = centreX(c.question_a, 30);
    return { a: S.letters(c.question_a, { x, y, size: 30 }), b: S.letters(c.question_b, { x, y: y + (rowGap || 90), size: 30 }) };
  }

  Ch.scene('s01', function (S) {
    const c = S.c;
    const keys = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    const m = S.modelMap({ x: 100, y: 300, w: 1720, h: 200 });
    S.stagger(keys.map((k) => m.parts[k]), S.capAt(0), 0.35);
    // third caption: a status chip under each part (the map's boxes are 288 wide, 358 apart), then one for all five
    const kinds = ['tested', 'tested', 'tested', 'untested', 'placeholder'];
    const t = S.capAt(2);
    kinds.forEach((k, i) => S.pop(cchip(S, k, { label: c.part_chips[i] }, 100 + i * 358 + 144, 520), t + i * 0.2));
    const svg = S.svg();
    S.draw(bracket(S, svg, 100, 1820, 640, 18, C.untested), t + 1.3, 0.8);
    S.pop(cchip(S, 'untested', { label: c.chip }, 960, 660), t + 2.0);
  });

  Ch.scene('s02', function (S) {
    const c = S.c;
    const q = question(S, c, 330);
    S.sweep(q.a.cells, S.capAt(0), 1.4);
    S.sweep(q.b.cells, S.capAt(1), 1.2);
    S.show(S.note(c.tag, { x: 310, y: 560, w: 1300, color: C.placeholder }), S.capAt(2));
    S.show(S.text(c.chars_note, { x: 310, y: 660, w: 1300, size: 32, align: 'center', color: C.soft }), S.capAt(2) + 0.3);
  });

  Ch.scene('s03', function (S) {
    const c = S.c;
    const q = question(S, c, 215);
    S.sweep(q.a.cells, S.capAt(0), 1.0);
    S.sweep(q.b.cells, S.capAt(0) + 0.9, 1.0);
    const rd = S.box({ x: 660, y: 415, w: 600, h: 130, label: c.labels[0], sub: c.labels[1], color: C.reader, size: 46, subSize: 32 });
    S.show(rd, S.capAt(1));
    const svg = S.svg();
    S.draw(S.arrow(svg, 960, 353, 960, 415, { color: C.soft }), S.capAt(1) + 0.3, 0.5);
    // three strips centred under the Reader box (356 wide each, 420 apart)
    const strips = [0, 1, 2].map((i) => S.vec({ x: 362 + i * 420, y: 578, n: 12, cell: 26, color: C.reader, seed: 3 + i }));
    S.stagger(strips, S.capAt(2), 0.6);
    S.show(S.text(c.labels[2], { x: 560, y: 612, w: 800, size: 36, align: 'center', color: C.soft }), S.capAt(2) + 0.3);
    S.pop(cchip(S, 'placeholder', { label: c.labels[4] }, 960, 660), S.capAt(2) + 0.6);   // illustration tag: the shading is decoration
    const num = S.text('0', { x: 290, y: 726, w: 640, size: 90, weight: 800, align: 'right', color: C.reader });
    S.show(num, S.capAt(3));
    S.count(num, { from: 0, to: c.reader_numbers, comma: true }, S.capAt(3), 1.6);
    S.show(S.text(c.labels[3], { x: 960, y: 737, w: 430, size: 36, color: C.soft }), S.capAt(3) + 0.3);
  });

  Ch.scene('s04', function (S) {
    const c = S.c;
    const q = question(S, c, 390, 140);
    S.sweep(q.a.cells, S.at(0.02), 0.8);
    S.sweep(q.b.cells, S.at(0.02) + 0.7, 0.8);
    const A = q.a;
    for (let j = 15; j <= 23; j++) if (A.byIndex[j]) S.tint(A.byIndex[j], S.capAt(1), { fill: TINT });
    S.pulse(A.byIndex[19], S.capAt(0));
    const cx = A.cx(19);
    S.show(S.text(c.labels[0], { x: cx - 200, y: 312, w: 400, size: 32, align: 'center', color: C.soft }), S.capAt(0));
    const svg = S.svg();
    S.draw(S.arrow(svg, cx, 354, cx, 388, { color: C.soft, width: 4, head: 16 }), S.capAt(0) + 0.3, 0.4);
    // bracket under the window (letters 15 to 23), its label and the chip centred on the marked letter
    const xl = parseFloat(A.byIndex[15].style.left), xr = parseFloat(A.byIndex[23].style.left) + parseFloat(A.byIndex[23].style.width);
    S.draw(bracket(S, svg, xl, xr, 452, 12, C.learned), S.capAt(1), 0.6);
    S.show(S.text(c.labels[1], { x: cx - 250, y: 464, w: 500, size: 32, align: 'center', color: C.reader }), S.capAt(1));
    S.pop(S.chip('learned', { x: cx + 190, y: 458 }), S.capAt(2));
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
    // the return loop starts on the bottom edge of Think and ends on the bottom edge of Look; its apex is at y = 642
    S.draw(S.curve(svg, 1460, 570, 460, 570, { bend: 140, color: C.thinker, width: 4 }), S.capAt(2), 1.0);
    S.pop(cchip(S, 'learned', {}, 960, 662), S.capAt(2) + 0.5);
  });

  Ch.scene('s06', function (S) {
    const c = S.c;
    const q = question(S, c, 215);
    S.sweep(q.a.cells, S.capAt(0), 1.0);
    S.sweep(q.b.cells, S.capAt(0) + 0.9, 1.0);
    const th = S.box({ x: 620, y: 420, w: 680, h: 150, label: c.labels[1], color: C.thinker, size: 46 });
    S.show(th, S.capAt(0) + 1.4);
    const svg = S.svg();
    S.draw(S.arrow(svg, 960, 352, 960, 420, { color: C.reader }), S.capAt(0) + 1.7, 0.5);
    S.show(S.text(c.labels[0], { x: 160, y: 450, w: 400, size: 72, weight: 800, color: C.thinker }), S.capAt(0) + 2.4);
    // the empty call slot appears with the sentence that says it stays empty
    S.show(S.box({ x: 1420, y: 420, w: 380, h: 150, label: c.labels[2], color: C.placeholder, size: 36 }), S.capAt(1) + 0.4);
  });

  Ch.scene('s07', function (S) {
    const c = S.c;
    // the 4 x 2 grid is centred on the picture (1140 wide); "no call" sits centred under it, so the group is balanced with or without it
    const grid = c.ops.map((op, i) => S.box({ x: 390 + (i % 4) * 300, y: 250 + Math.floor(i / 4) * 130, w: 240, h: 100, label: op, color: C.call, size: 44 }));
    S.stagger(grid, S.capAt(0), 0.25);
    S.show(S.box({ x: 810, y: 520, w: 300, h: 110, label: c.labels[0], sub: c.labels[1], color: C.soft, size: 40, subSize: 28 }), S.capAt(1));
    S.pulse(grid[1], S.capAt(2));
    // the green chip is tied to the whole call-writer group by a bracket
    const svg = S.svg();
    S.draw(bracket(S, svg, 390, 1530, 690, 18, C.tested), S.capAt(2) + 0.3, 0.8);
    S.pop(cchip(S, 'tested', { label: c.chips[0] }, 960, 708), S.capAt(2) + 1.0);
  });

  Ch.scene('s08', function (S) {
    const c = S.c;
    const q = question(S, c, 400);
    S.sweep(q.a.cells, S.at(0.02), 0.8);
    S.sweep(q.b.cells, S.at(0.02) + 0.7, 0.8);
    const svg = S.svg();
    const x9 = q.a.cx(9), x7 = q.a.cx(7);
    // caption 1: the learned pointer lands on the last digit of 12
    S.show(S.box({ x: x9 - 130, y: 240, w: 260, h: 90, label: c.labels[0], color: C.learned, size: 34 }), S.capAt(0));
    S.draw(S.arrow(svg, x9, 330, x9, 398, { color: C.learned }), S.capAt(0) + 0.4, 0.5);
    // caption 2: the code copies to the left (2, then 1) until the learned stop head says stop at the space
    S.tint(q.a.byIndex[9], S.capAt(1) + 0.3, { fill: TINT });
    S.tint(q.a.byIndex[8], S.capAt(1) + 0.9, { fill: TINT });
    S.draw(S.arrow(svg, x9 + 14, 452, x7, 452, { color: C.hand, width: 5, head: 16 }), S.capAt(1) + 0.5, 0.8);
    S.show(S.box({ x: 250, y: 240, w: 300, h: 90, label: c.labels[1], color: C.learned, size: 34 }), S.capAt(1) + 1.4);
    S.draw(S.path(svg, [[400, 330], [400, 366], [x7, 366], [x7, 398]], { color: C.learned, width: 5, head: 18 }), S.capAt(1) + 1.7, 0.9);
    // caption 3: hand-written flip, then the call (the request to the calculator)
    S.show(S.box({ x: 489, y: 623, w: 420, h: 90, label: c.labels[2], color: C.hand, size: 34 }), S.capAt(2));
    S.draw(S.arrow(svg, 912, 668, 996, 668, { color: C.hand }), S.capAt(2) + 0.4, 0.4);
    S.show(S.text(c.labels[3], { x: 1000, y: 568, w: 700, size: 32, color: C.soft }), S.capAt(2) + 0.8);
    S.show(S.text(c.call, { x: 1000, y: 612, w: 600, size: 90, mono: true, color: C.call }), S.capAt(2) + 0.8);
  });

  Ch.scene('s09', function (S) {
    const c = S.c;
    const svg = S.svg();
    S.show(S.box({ x: 700, y: 360, w: 520, h: 200, label: c.labels[0], color: C.calc, size: 46 }), S.capAt(0));
    S.pop(S.chip('hand', { x: 700, y: 600 }), S.capAt(0) + 0.4);
    S.show(S.text(c.request, { x: 160, y: 415, w: 480, size: 52, align: 'right', mono: true, color: C.call }), S.capAt(1));
    S.draw(S.arrow(svg, 656, 447, 700, 447, { color: C.call }), S.capAt(1) + 0.4, 0.4);
    const num = S.text('0.0', { x: 1280, y: 380, w: 500, size: 150, weight: 800, align: 'center', color: C.calc });
    S.show(num, S.capAt(2));
    S.count(num, { from: 0, to: c.zero_score, dec: 1 }, S.capAt(2), 1.2);
    S.show(S.text(c.labels[1], { x: 1250, y: 560, w: 560, size: 34, align: 'center', color: C.soft }), S.capAt(2) + 0.3);
    // status: a green chip says this figure is a measured result (6 copies, 3M size), not an illustration
    S.pop(cchip(S, 'tested', { label: c.chips[1] }, 1530, 668), S.capAt(2) + 0.7);
  });

  Ch.scene('s10', function (S) {
    const c = S.c;
    const svg = S.svg();
    const wReq = monoW(c.request, 52), wRep = monoW(c.reply, 52);
    S.show(S.box({ x: 1240, y: 330, w: 520, h: 200, label: c.labels[0], color: C.calc, size: 46 }), S.capAt(0));
    S.show(S.text(c.request, { x: 160, y: 358, w: 480, size: 52, mono: true, color: C.call }), S.capAt(0));
    // each arrow starts or ends at the edge of the text it carries
    S.draw(S.arrow(svg, 160 + wReq + 24, 390, 1240, 390, { color: C.call }), S.capAt(0) + 0.4, 0.6);
    S.draw(S.arrow(svg, 1240, 480, 160 + wRep + 24, 480, { color: C.calc }), S.capAt(1), 0.6);
    S.show(S.text(c.reply, { x: 160, y: 448, w: 700, size: 52, mono: true, color: C.calc }), S.capAt(1) + 0.4);
    S.show(S.box({ x: 160, y: 680, w: 560, h: 120, label: c.labels[1], color: C.thinker, size: 40 }), S.capAt(2));
    S.draw(S.arrow(svg, 160 + wRep / 2, 524, 160 + wRep / 2, 680, { color: C.soft }), S.capAt(2) + 0.3, 0.5);
    S.pop(S.chip('hand', { x: 1240, y: 580 }), S.capAt(0) + 0.6);
  });

  Ch.scene('s11', function (S) {
    const c = S.c;
    const svg = S.svg();
    const SZ = 36, CALL = 80, adv = CALL * 0.592;
    S.show(S.text(c.labels[0], { x: 160, y: 195, w: 600, size: 72, weight: 800, color: C.thinker }), S.capAt(0));
    const qb = S.letters(c.question_b, { x: centreX(c.question_b, SZ), y: 320, size: SZ });
    S.sweep(qb.cells, S.capAt(0), 0.8);
    // the call 'add 7 3' is placed so its 3 sits under the question's 3 and its 7 under the 7 at the end of the first notes line:
    // two straight, parallel arrows that cross neither each other nor any letter
    const x3 = qb.cx(10);
    const callX = Math.round(x3 - 6.5 * adv), x7 = callX + 4.5 * adv;
    const notesX = Math.round(x7 - (rowW(c.reply1, SZ) - Math.round(SZ * 0.82) / 2));
    S.show(S.text(c.labels[2], { x: 160, y: 452, w: 140, size: 32, color: C.soft }), S.capAt(0));
    const ra = S.letters(c.reply1, { x: notesX, y: 440, size: SZ });
    S.sweep(ra.cells, S.capAt(0) + 0.3, 0.8);
    S.show(S.text(c.call2, { x: callX, y: 625, w: 600, size: CALL, mono: true, color: C.call }), S.capAt(1));
    const a7 = S.arrow(svg, x7, 641, x7, 490, { color: C.call });
    const a3 = S.arrow(svg, x3, 641, x3, 372, { color: C.soft });
    S.draw(a7, S.capAt(1) + 0.4, 0.6);
    S.draw(a3, S.capAt(1) + 0.8, 0.6);
    // caption 3: the arrows have done their job; the reply appears under the call and slides up into the notes as a second line
    const t = S.capAt(2);
    [a7.line, a7.head, a3.line, a3.head].forEach((e) => S.hide(e, t, 0.4));
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;left:0;top:0;width:1920px;height:1080px;pointer-events:none;';
    S.g.appendChild(wrap);
    const rb = S.letters(c.reply2, { x: notesX, y: 770, size: SZ, parent: wrap });
    S.sweep(rb.cells, t + 0.6, 0.8);
    S.move(wrap, t + 1.9, 1.2, { y: -260 });
    S.show(S.text(c.labels[1], { x: notesX + rowW(c.reply2, SZ) + 40, y: 516, w: 300, size: 40, weight: 800, color: C.calc }), t + 3.1);
  });

  Ch.scene('s12', function (S) {
    const c = S.c;
    const calls = ['', c.call1, c.call2, '', '', '', '', ''];
    const tiles = calls.map((t, i) => S.box({ x: 160 + i * 200, y: 330, w: 180, h: 130, label: t, color: i === 1 || i === 2 ? C.call : C.soft, size: 34 }));
    S.stagger(tiles.slice(0, 3), S.capAt(0), 0.5);
    S.show(S.text(c.labels[1], { x: 160, y: 500, w: 900, size: 32, color: C.soft }), S.capAt(0));
    S.stagger(tiles.slice(3), S.capAt(1), 0.25);
    S.show(S.text(c.labels[0], { x: 1300, y: 250, w: 500, size: 32, align: 'right', color: C.placeholder }), S.capAt(0));
    S.show(S.text(c.labels[2], { x: 860, y: 500, w: 900, size: 32, align: 'right', color: C.soft }), S.capAt(1));
    // the "newest version" bar and its status chip appear together, with the caption that talks about the newest version
    S.show(S.box({ x: 160, y: 620, w: 1600, h: 90, label: c.labels[3], color: C.soft, size: 36 }), S.capAt(2));
    S.pop(S.chip('untested', { x: 160, y: 732 }), S.capAt(2) + 0.5);
  });

  Ch.scene('s13', function (S) {
    const c = S.c;
    S.show(S.card({ x: 160, y: 560, w: 1600, h: 30, fill: C.stop }), S.capAt(0));
    S.show(S.text(c.labels[0], { x: 160, y: 500, w: 400, size: 40, color: C.stop }), S.capAt(0));
    S.show(S.text(c.labels[1], { x: 1360, y: 500, w: 400, size: 40, align: 'right', color: C.stop }), S.capAt(0));
    // the switch is centred; its two chips sit right under it, so both read as describing the switch
    const sw = S.box({ x: 760, y: 300, w: 400, h: 110, label: c.labels[2], color: C.stop, size: 46 });
    S.show(sw, S.capAt(1));
    S.tint(sw, S.capAt(1) + 0.8, { fill: STOP_ON });
    S.show(S.text(c.labels[3], { x: 1190, y: 340, w: 300, size: 32, color: C.placeholder }), S.capAt(1) + 0.8);
    S.pop(cchip(S, 'learned', {}, 790, 426), S.capAt(2));
    S.pop(cchip(S, 'untested', {}, 1070, 426), S.capAt(2) + 0.4);
  });

  Ch.scene('s14', function (S) {
    const c = S.c;
    const svg = S.svg();
    const SZ = 40;
    // the reply row is placed so the copied "10" sits above the middle of the Talker box
    const x0 = Math.round(820 - (relCx(c.last_reply, SZ, 10) + relCx(c.last_reply, SZ, 11)) / 2);
    const L = S.letters(c.last_reply, { x: x0, y: 290, size: SZ });
    S.sweep(L.cells, S.capAt(0), 0.9);
    S.tint(L.byIndex[10], S.capAt(1), { fill: C.talker });
    S.tint(L.byIndex[11], S.capAt(1), { fill: C.talker });
    S.show(S.box({ x: 560, y: 470, w: 520, h: 150, label: c.labels[0], color: C.talker, size: 46 }), S.capAt(0));
    S.draw(S.arrow(svg, 820, 350, 820, 470, { color: C.talker }), S.capAt(1), 0.6);
    // the answer comes out of the Talker; the grey chip sits under the Talker, not under the answer
    S.draw(S.arrow(svg, 1086, 545, 1330, 545, { color: C.talker }), S.capAt(1) + 0.8, 0.5);
    S.show(S.text(c.answer, { x: 1250, y: 451, w: 400, size: 150, weight: 800, align: 'center', color: C.talker }), S.capAt(1) + 1.2);
    S.pop(cchip(S, 'placeholder', { label: c.labels[1] }, 820, 645), S.capAt(2));
  });

  Ch.scene('s15', function (S) {
    const c = S.c;
    // one row per claim: status chip + the part it is about, so the last picture reads on its own
    const kinds = ['tested', 'tested', 'untested', 'placeholder', 'untested', 'untested'];
    const opts = [{}, {}, {}, {}, { label: c.chip_open, color: C.warn }, { label: c.chip_all }];
    const when = [S.capAt(0), S.capAt(1), S.capAt(2), S.capAt(3), S.capAt(4), S.capAt(4) + 0.5];
    c.rows.forEach((r, i) => {
      const y = 260 + i * 100;
      S.pop(S.chip(kinds[i], Object.assign({ x: 160, y }, opts[i])), when[i]);
      S.show(S.text(r, { x: 620, y: y - 2, w: 1200, size: 38, color: C.ink }), when[i] + 0.2);
    });
  });

  Ch.scene('s16', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 330, w: 1720, h: 200 });
    const parts = [m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker];
    // the recap builds with the sentences: three parts with the first, two with the second, then each box lights in turn
    const when = [S.capAt(0), S.capAt(0) + 1.0, S.capAt(0) + 2.0, S.capAt(1), S.capAt(1) + 1.0];
    parts.forEach((p, i) => {
      S.show(p, when[i]);
      S.show(S.text(c.labels[i], { x: 100 + i * 358 + 144 - 165, y: 560, w: 330, size: 34, weight: 600, align: 'center', color: C.ink }), when[i] + 0.3);
      if (i > 0) S.draw(m.arrows[i - 1], when[i], 0.4);
    });
    parts.forEach((p, i) => S.pulse(p, S.capAt(2) + i * 0.4));
  });
});
