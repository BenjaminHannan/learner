Kit.chapter('ch14', function (Ch) {
  const C = Kit.C;
  const col = (k) => (k && C[k]) || k;
  // status chip from a JSON spec {kind,label,color?}
  const mkChip = (S, spec, x, y, size) => S.chip(spec.kind, { x: x, y: y, label: spec.label, size: size || 28, color: spec.color ? col(spec.color) : undefined });
  const monoLab = (b) => { const l = b.querySelector('.lab'); if (l) l.classList.add('mono'); };

  // s01: the five-part ledger. Map first, then a status chip per part, stepping with the captions.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 215, w: 1720, h: 150 });
    const keys = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    keys.forEach((k, i) => S.show(m.parts[k], S.at(0.04) + i * 0.18));
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.08) + i * 0.18, 0.3));
    const groups = c.parts.map((p, i) => {
      const x = 100 + i * 358, els = [];
      p.chips.forEach((ch, j) => els.push(mkChip(S, ch, x, 400 + j * 62, 26)));
      if (p.text) els.push(S.text(p.text, { x: x, y: 400 + p.chips.length * 62 + 12, w: 300, size: 30 }));
      return els;
    });
    const legend = c.legend.map((l, i) => mkChip(S, l, 100 + i * 470, 770, 28));
    S.stagger(legend, S.capAt(0) + 0.6, 0.5);
    [0, 1, 2].forEach((gi, k) => groups[gi].forEach((e, j) => S.show(e, S.capAt(1) + k * 0.7 + j * 0.25, { dur: 0.4 })));
    [3, 4].forEach((gi, k) => groups[gi].forEach((e, j) => S.show(e, S.capAt(2) + k * 0.7 + j * 0.25, { dur: 0.4 })));
    S.pulse(m.parts.thinker, S.capAt(1) + 0.5);
    S.pulse(m.parts.stop, S.capAt(2) + 0.3);
  });

  // s02: rows for the smaller pieces, tests and plans.
  Ch.scene('s02', function (S) {
    const c = S.c;
    const y0 = 205, rh = 112, gp = 10;
    const rows = c.rows.map((r, i) => {
      const y = y0 + i * (rh + gp);
      const card = S.card({ x: 80, y: y, w: 1760, h: rh });
      const nm = S.text(r.name, { x: 110, y: y + (r.name.length > 20 ? 12 : 34), w: 430, size: 36, weight: 700 });
      const tx = S.text(r.text, { x: 570, y: y + (r.text.length > 50 ? 18 : 38), w: 800, size: 30 });
      const chips = r.chips.map((ch, j) => mkChip(S, ch, 1410, y + 32 + j * 56, 26));
      return { card: card, nm: nm, tx: tx, chips: chips };
    });
    const rev = (r, t) => { S.show(r.card, t, { dur: 0.4 }); S.show(r.nm, t + 0.15, { dur: 0.4 }); S.show(r.tx, t + 0.3, { dur: 0.4 }); r.chips.forEach((ch) => S.pop(ch, t + 0.7)); };
    rev(rows[0], S.capAt(0) + 0.3);
    rows.slice(1).forEach((r, i) => rev(r, S.capAt(1) + 0.3 + i * 1.1));
  });

  // s03: result one. Three bars grow and count.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 100, y: 240, w: 860, labelW: 420, rowH: 76, gap: 34, max: 100, dec: 2, labelSize: 40, valueSize: 52,
      items: c.bars.map((b) => ({ label: b.label, value: b.value, color: col(b.color), dec: 2 })) });
    const revealRow = (r, t) => { S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 }); S.grow(r.b, t + 0.3, 1.5, r.val, { dec: 2, comma: true }); };
    revealRow(hb.rows[0], S.capAt(0) + 0.3);
    revealRow(hb.rows[1], S.capAt(1) + 0.3);
    revealRow(hb.rows[2], S.capAt(1) + 1.6);
    S.pop(S.chip('tested', { x: 100, y: 600, label: c.labels.chip }), S.capAt(2) + 0.2);
    const gap = S.note(c.labels.gap, { x: 100, y: 675, w: 780, color: C.thinker, size: 36 });
    const cav = S.note(c.labels.caveat, { x: 930, y: 675, w: 890, color: C.untested, size: 32 });
    S.show(gap, S.capAt(2) + 0.6);
    S.show(cav, S.capAt(2) + 1.4);
  });

  // s04: result two. Slip out, reply back (made-up example), then the likely-range picture.
  Ch.scene('s04', function (S) {
    const c = S.c, L = c.labels, V = c.values;
    const slip = S.box({ x: 120, y: 230, w: 360, h: 130, label: L.slip, color: C.call, size: 46 }); monoLab(slip);
    const calc = S.box({ x: 700, y: 215, w: 400, h: 160, label: L.calc, color: C.calc, size: 46 });
    const back = S.box({ x: 1320, y: 230, w: 300, h: 130, label: L.reply, color: C.tested, size: 64 }); monoLab(back);
    const tag = S.chip('placeholder', { x: 120, y: 392, label: L.tag, size: 26 });
    const ok = S.chip('tested', { x: 1360, y: 392, label: L.chip, size: 26 });
    const svg0 = S.svg();
    const a1 = S.arrow(svg0, 484, 295, 696, 295, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg0, 1104, 295, 1316, 295, { color: C.soft, width: 6 });
    S.show(slip, S.capAt(0) + 0.3);
    S.draw(a1, S.capAt(0) + 1.2, 0.6);
    S.show(calc, S.capAt(0) + 1.5);
    S.draw(a2, S.capAt(0) + 2.4, 0.6);
    S.show(back, S.capAt(0) + 3.0);
    S.pop(tag, S.capAt(0) + 3.4);
    S.pulse(calc, S.capAt(0) + 2.0);
    // number line, drawn to scale for -1 .. +2 (400 px per point)
    const X = (v) => 200 + (v + 1) * 400;
    const line = S.card({ x: 200, y: 637, w: 1200, h: 6, fill: C.soft, color: C.soft, r: 3 });
    const tickCards = [-1, 0, 1, 2].map((v) => S.card({ x: X(v) - 2, y: 625, w: 4, h: 30, fill: C.soft, color: C.soft, r: 2 }));
    const tickTxt = L.ticks.map((t, i) => S.text(t, { x: X(i - 1) - 40, y: 662, w: 80, size: 30, align: 'center', color: C.soft }));
    const zero = S.card({ x: X(0) - 2, y: 560, w: 4, h: 70, fill: C.warn, color: C.warn, r: 2 });
    const range = S.card({ x: X(V.lo), y: 611, w: X(V.hi) - X(V.lo), h: 28, fill: C.calc, color: C.calc, r: 14 });
    const dot = S.box({ x: X(V.mid) - 22, y: 604, w: 44, h: 44, color: C.ink, fill: C.ink, r: 22 });
    const dl = S.text(L.dot, { x: X(V.mid) - 70, y: 548, w: 140, size: 40, weight: 800, align: 'center' });
    const rl = S.text(L.range, { x: X(V.lo), y: 704, w: 760, size: 32, color: C.ink });
    S.pop(ok, S.capAt(1) + 0.1);
    S.show(line, S.capAt(1) + 0.3); S.stagger(tickCards, S.capAt(1) + 0.4, 0.1); S.stagger(tickTxt, S.capAt(1) + 0.4, 0.1);
    S.show(zero, S.capAt(1) + 0.9);
    S.pop(dot, S.capAt(1) + 1.3); S.show(dl, S.capAt(1) + 1.5);
    S.show(range, S.capAt(1) + 2.3, { dur: 0.8 }); S.show(rl, S.capAt(1) + 2.8);
    const off = S.note(L.off, { x: 120, y: 765, w: 800, color: C.calc, size: 32 });
    const swap = S.note(L.swap, { x: 960, y: 765, w: 880, color: C.untested, size: 32 });
    S.show(off, S.capAt(2) + 0.3);
    S.show(swap, S.capAt(3) + 0.3);
  });

  // s05: result three. Six dots over a dashed 71.3 line; the average counts up to 76.1.
  Ch.scene('s05', function (S) {
    const c = S.c, L = c.labels;
    const yOf = (v) => 720 - (v - 70) / 10 * 440;
    const axis = S.card({ x: 186, y: 270, w: 6, h: 454, fill: C.soft, color: C.soft, r: 3 });
    const base = S.card({ x: 186, y: 717, w: 840, h: 6, fill: C.line, color: C.line, r: 3 });
    const ticks = c.ticks.map((t, i) => S.text(t, { x: 100, y: yOf(70 + i * 5) - 20, w: 70, size: 30, align: 'right', color: C.soft }));
    const dots = c.dots.map((d, i) => {
      const x = 260 + i * 140;
      return {
        dot: S.box({ x: x - 22, y: yOf(d.value) - 22, w: 44, h: 44, color: C.placeholder, fill: C.placeholder, r: 22 }),
        val: S.text(String(d.value), { x: x - 55, y: yOf(d.value) - 66, w: 110, size: 30, weight: 700, align: 'center' }),
        nm: S.text(d.name, { x: x - 40, y: 730, w: 80, size: 34, weight: 700, align: 'center', color: C.soft }),
      };
    });
    const meanLine = S.card({ x: 186, y: yOf(L.mean) - 2, w: 840, h: 5, fill: C.thinker, color: C.thinker, r: 2 });
    const svg = S.svg();
    const dash = S.svgEl(svg, 'line', { x1: 186, y1: yOf(71.3), x2: 1030, y2: yOf(71.3), stroke: C.untested, 'stroke-width': 5, 'stroke-dasharray': '16 10' });
    const dashTxt = S.text(L.line, { x: 186, y: 775, w: 900, size: 30, color: C.ink });
    const chip = S.chip('placeholder', { x: 1240, y: 200, label: c.chip });
    const big = S.text('', { x: 1240, y: 255, w: 580, size: 150, weight: 800, color: C.thinker });
    const bigSub = S.text(L.meanSub, { x: 1240, y: 425, w: 580, size: 34, color: C.soft });
    const upd = S.text(L.upd, { x: 1240, y: 520, w: 600, size: 42, weight: 700 });
    const loop = S.text(L.loop, { x: 1240, y: 590, w: 600, size: 34, color: C.soft });
    S.pop(chip, S.capAt(0) + 0.2);
    S.show(axis, S.capAt(0) + 0.3); S.show(base, S.capAt(0) + 0.3);
    S.stagger(ticks, S.capAt(0) + 0.4, 0.15);
    dots.forEach((d, i) => { const t = S.capAt(0) + 1.0 + i * 0.5; S.pop(d.dot, t); S.show(d.val, t + 0.2, { dur: 0.3 }); S.show(d.nm, t, { dur: 0.3 }); });
    const tm = S.capAt(0) + 1.0 + 6 * 0.5 + 0.3;
    S.show(meanLine, tm);
    S.show(big, tm); S.count(big, { from: 0, to: L.mean, dec: 1 }, tm, 1.6);
    S.show(bigSub, tm + 0.4);
    S.show(upd, S.capAt(1) + 0.3); S.show(loop, S.capAt(1) + 0.9);
    S.show(dash, S.capAt(2) + 0.3, { dur: 0.6 }); S.show(dashTxt, S.capAt(2) + 0.7);
  });

  // s06: what the sleep result does not show.
  Ch.scene('s06', function (S) {
    const c = S.c, L = c.labels, V = c.values;
    const ax = S.text(L.axis, { x: 100, y: 200, w: 900, size: 32, color: C.soft });
    const mk = (label, v, y, color) => ({
      lab: S.text(label, { x: 80, y: y + 8, w: 400, size: 40, weight: 700, align: 'right' }),
      b: S.bar({ x: 500, y: y, w: 640, h: 64, value: v, max: 2.5, color: color }),
      val: S.text('', { x: 1160, y: y + 6, w: 220, size: 46, weight: 800, color: color }),
    });
    const r1 = mk(L.sleep, V.sleep, 250, C.placeholder);
    const r2 = mk(L.practice, V.practice, 345, C.soft);
    const rev = (r, t) => { S.show(r.lab, t, { dur: 0.4 }); S.show(r.b.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 }); S.grow(r.b, t + 0.3, 1.4, r.val, { dec: 2, pre: '+' }); };
    S.show(ax, S.capAt(0) + 0.2);
    rev(r1, S.capAt(0) + 0.6); rev(r2, S.capAt(0) + 2.2);
    const tn = S.note(L.transfer, { x: 100, y: 470, w: 560, color: C.warn, size: 36 });
    const dn = S.text(L.diff, { x: 100, y: 565, w: 560, size: 30, color: C.soft });
    const dv = S.text('', { x: 700, y: 455, w: 420, size: 90, weight: 800, color: C.warn });
    S.show(tn, S.capAt(0) + 4.4); S.show(dn, S.capAt(0) + 4.6); S.show(dv, S.capAt(0) + 4.6);
    S.count(dv, { from: 0, to: V.diff, dec: 2 }, S.capAt(0) + 4.6, 1.4);
    const hm = S.box({ x: 1400, y: 215, w: 440, h: 150, label: L.harm, color: C.warn, size: 38 });
    S.show(hm, S.capAt(1) + 0.3); S.pulse(hm, S.capAt(1) + 1.0);
    const f = S.text(String(V.from), { x: 1400, y: 440, w: 150, size: 96, weight: 800, color: C.soft });
    const ar = S.text('→', { x: 1550, y: 455, w: 80, size: 70, weight: 700, color: C.soft });
    const tv = S.text('', { x: 1640, y: 440, w: 200, size: 96, weight: 800, color: C.warn });
    const em = S.text(L.earlier, { x: 1400, y: 570, w: 440, size: 30, color: C.soft });
    S.show(f, S.capAt(2) + 0.2); S.show(ar, S.capAt(2) + 0.6); S.show(tv, S.capAt(2) + 0.9); S.show(em, S.capAt(2) + 0.9);
    S.count(tv, { from: V.from, to: V.to, dec: 0 }, S.capAt(2) + 0.9, 1.6);
  });

  // s07: what has never been done. Four pieces slide together into a dashed frame (picture only), then the other gaps.
  Ch.scene('s07', function (S) {
    const c = S.c;
    const init = [120, 540, 960, 1380], fin = [330, 650, 970, 1290];
    const colors = [C.reader, C.calc, C.call, C.stop];
    const frame = S.card({ x: 300, y: 205, w: 1320, h: 165, fill: '#FFFFFF', color: C.warn, r: 24 });
    frame.style.borderStyle = 'dashed';
    const pieces = c.pieces.map((p, i) => S.box({ x: init[i], y: 225, w: 300, h: 125, label: p, color: colors[i], size: 36 }));
    const fl = S.text(c.frame, { x: 330, y: 380, w: 1260, size: 40, weight: 700, align: 'center', color: C.warn });
    const tag = S.chip('placeholder', { x: 80, y: 392, label: c.tag, size: 26 });
    S.stagger(pieces, S.capAt(0) + 0.3, 0.5);
    S.show(frame, S.capAt(1) + 0.1);
    pieces.forEach((p, i) => S.move(p, S.capAt(1) + 0.3, 1.4, { x: fin[i] - init[i] }));
    S.show(fl, S.capAt(1) + 1.6); S.pop(tag, S.capAt(1) + 1.8);
    const cards = c.cards.map((cd, i) => {
      const x = 80 + i * 455;
      return {
        card: S.card({ x: x, y: 470, w: 395, h: 230 }),
        tx: S.text(cd.text, { x: x + 25, y: 492, w: 345, size: 36, weight: 700 }),
        chip: mkChip(S, cd.chip, x + 25, 625, 28),
      };
    });
    const rv = (r, t) => { S.show(r.card, t, { dur: 0.4 }); S.show(r.tx, t + 0.15, { dur: 0.4 }); S.pop(r.chip, t + 0.5); };
    rv(cards[0], S.capAt(2) + 0.3);
    cards.slice(1).forEach((r, i) => rv(r, S.capAt(3) + 0.3 + i * 0.6));
  });

  // s08: open risks. Leak bars (6.59 against a limit of 4.62) and three risk cards.
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.labels;
    const ax = S.text(L.axis, { x: 80, y: 200, w: 900, size: 32, color: C.soft });
    const hb = S.hbars({ x: 80, y: 265, w: 440, labelW: 290, rowH: 70, gap: 30, max: 8, dec: 2, labelSize: 38, valueSize: 46, valueW: 150,
      items: c.bars.map((b) => ({ label: b.label, value: b.value, color: col(b.color), dec: 2 })) });
    const one = S.text(L.one, { x: 80, y: 565, w: 900, size: 32, color: C.soft });
    const lm = S.chip('untested', { x: 80, y: 465, label: L.chip, color: C.warn });
    S.show(ax, S.capAt(0) + 0.2);
    hb.rows.forEach((r, i) => {
      const t = S.capAt(0) + 0.8 + i * 1.4;
      S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 });
      S.grow(r.b, t + 0.3, 1.4, r.val, { dec: 2 });
    });
    S.pop(lm, S.capAt(0) + 4.0); S.show(one, S.capAt(0) + 4.6);
    c.cards.forEach((cd, i) => {
      const y = 215 + i * 192;
      const card = S.card({ x: 1010, y: y, w: 830, h: 180, color: C.line });
      const ti = S.text(cd.title, { x: 1040, y: y + 24, w: 770, size: 40, weight: 700 });
      const tx = S.text(cd.text, { x: 1040, y: y + 92, w: 770, size: 32, color: C.soft });
      const t = i === 0 ? S.capAt(1) + 0.3 : i === 1 ? S.capAt(1) + 1.6 : S.capAt(2) + 0.3;
      S.show(card, t, { dur: 0.4 }); S.show(ti, t + 0.15, { dur: 0.4 }); S.show(tx, t + 0.3, { dur: 0.4 });
    });
  });

  // s09: hand-written pieces still on the path, as stacks of blocks with counting numbers.
  Ch.scene('s09', function (S) {
    const c = S.c, L = c.labels;
    const chip = S.chip('hand', { x: 80, y: 198, label: c.chip });
    const nosum = S.text(L.nosum, { x: 520, y: 202, w: 1320, size: 32, color: C.soft });
    const base = 600;
    const cols = c.columns.map((cl, i) => {
      const x = 130 + i * 350;
      const blocks = [];
      for (let j = 0; j < cl.count; j++) blocks.push(S.box({ x: x, y: base - (j + 1) * 58, w: 220, h: 50, color: C.hand, fill: '#F3E6D8', r: 10 }));
      const num = S.text('', { x: x, y: base + 22, w: 220, size: 80, weight: 800, align: 'center', color: C.hand });
      const nm = S.text(cl.name, { x: x, y: base + 112, w: 220, size: 34, weight: 600, align: 'center' });
      return { x: x, blocks: blocks, num: num, nm: nm, n: cl.count };
    });
    S.show(chip, S.capAt(0) + 0.2);
    cols.forEach((cl, i) => {
      const t = S.capAt(0) + 0.6 + i * 1.5;
      S.show(cl.nm, t, { dur: 0.4 }); S.show(cl.num, t, { dur: 0.3 });
      cl.blocks.forEach((b, j) => S.show(b, t + 0.2 + j * 0.2, { dur: 0.3 }));
      S.count(cl.num, { from: 0, to: cl.n, dec: 0 }, t + 0.2, Math.max(0.3, cl.n * 0.2));
    });
    S.show(nosum, S.capAt(0) + 8.0);
    const lr = S.chip('learned', { x: 160, y: 520, label: L.learned, size: 26 });
    S.pop(lr, S.capAt(1) + 0.4);
    S.pulse(cols[0].num, S.capAt(1) + 0.5);
    const plan = S.note(L.plan, { x: 80, y: 770, w: 1080, color: C.placeholder, size: 32 });
    const pc = S.chip('placeholder', { x: 1230, y: 780, label: L.planChip });
    S.show(plan, S.capAt(2) + 0.3); S.pop(pc, S.capAt(2) + 0.9);
  });

  // s10: the next gates, in order (a plan; no dates promised).
  Ch.scene('s10', function (S) {
    const c = S.c;
    const bw = 380, gp = 66, x0 = 100, ys = [240, 500], bh = 170;
    const bx = (k) => x0 + k * (bw + gp);
    const boxes = c.steps.map((s, i) => S.box({ x: bx(i % 4), y: ys[Math.floor(i / 4)], w: bw, h: bh, label: s, color: C.placeholder, size: 38 }));
    const svg = S.svg();
    const arrows = [];
    for (let r = 0; r < 2; r++) for (let k = 0; k < 3; k++) arrows.push(S.arrow(svg, bx(k) + bw + 6, ys[r] + bh / 2, bx(k + 1) - 6, ys[r] + bh / 2, { color: C.soft, width: 6 }));
    const conn = S.path(svg, [[bx(3) + bw / 2, ys[0] + bh + 6], [bx(3) + bw / 2, 455], [bx(0) + bw / 2, 455], [bx(0) + bw / 2, ys[1] - 6]], { color: C.soft, width: 6 });
    const chip = S.chip('placeholder', { x: 100, y: 735, label: c.chip });
    S.pop(chip, S.capAt(0) + 0.2);
    // arrows[0..2] join boxes 0-3, arrows[3..5] join boxes 4-7, conn joins 3 to 4
    S.show(boxes[0], S.capAt(0) + 0.5);
    for (let i = 1; i < 4; i++) { S.draw(arrows[i - 1], S.capAt(0) + 0.5 + i * 1.6 - 0.6, 0.5); S.show(boxes[i], S.capAt(0) + 0.5 + i * 1.6); }
    S.draw(conn, S.capAt(1) + 0.2, 0.9);
    S.show(boxes[4], S.capAt(1) + 1.0);
    S.draw(arrows[3], S.capAt(1) + 1.7, 0.5); S.show(boxes[5], S.capAt(1) + 2.2);
    S.draw(arrows[4], S.capAt(2) + 0.2, 0.5); S.show(boxes[6], S.capAt(2) + 0.7);
    S.draw(arrows[5], S.capAt(2) + 1.8, 0.5); S.show(boxes[7], S.capAt(2) + 2.3);
    S.pulse(boxes[7], S.capAt(2) + 3.2);
  });

  // s11: what would prove the idea wrong: three marks as zones, with the one measured point (domain mode v1).
  Ch.scene('s11', function (S) {
    const c = S.c;
    const ys = [205, 385, 565];
    const fills = ['#FDECE3', '#F1ECE1', '#E3F3EA'];
    const borders = [C.warn, C.placeholder, C.tested];
    const tag = S.chip('placeholder', { x: 1360, y: 205, label: c.tag, size: 26 });
    S.pop(tag, S.capAt(0) + 0.2);
    const rows = c.gauges.map((g, i) => {
      const y = ys[i];
      const lab = S.text(g.label, { x: 100, y: y, w: 1100, size: 36, weight: 700 });
      const zones = g.zones.map((z, k) => S.box({ x: 100 + k * 400, y: y + 48, w: 400, h: 84, label: z, color: borders[k], fill: fills[k], size: 34 }));
      const bounds = g.bounds.map((b, k) => S.text(b, { x: 100 + (k + 1) * 400 - 60, y: y + 138, w: 120, size: 30, weight: 700, align: 'center', color: C.soft }));
      const chip = mkChip(S, g.chip, 1360, y + 70, 26);
      const mk = g.marker ? [S.card({ x: 128, y: y + 42, w: 8, h: 100, fill: C.ink, color: C.ink, r: 3 }), S.text('▲ ' + g.marker, { x: 100, y: y + 138, w: 300, size: 30, weight: 700, color: C.warn })] : [];
      return { lab: lab, zones: zones, bounds: bounds, chip: chip, mk: mk };
    });
    const rev = (r, t) => {
      S.show(r.lab, t, { dur: 0.4 });
      S.stagger(r.zones, t + 0.3, 0.3, { dur: 0.4 });
      r.bounds.forEach((b) => S.show(b, t + 1.3, { dur: 0.3 }));
      S.pop(r.chip, t + 1.6);
      r.mk.forEach((m, j) => S.show(m, t + 2.4 + j * 0.3, { dur: 0.4 }));
    };
    rev(rows[0], S.capAt(0) + 0.5);
    rev(rows[1], S.capAt(1) + 0.3);
    rev(rows[2], S.capAt(2) + 0.2);
    S.pulse(rows[2].zones[0], S.capAt(2) + 3.2);
    const past = S.note(c.past, { x: 100, y: 765, w: 1720, color: C.warn, size: 32 });
    S.show(past, S.capAt(2) + 3.4);
  });

  // s12: recap. The five-part map with one short line each, then the plan's own bottom line (labelled).
  Ch.scene('s12', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 215, w: 1720, h: 130 });
    const keys = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    keys.forEach((k, i) => S.show(m.parts[k], S.at(0.04) + i * 0.18));
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.08) + i * 0.18, 0.3));
    const lines = c.parts.map((p, i) => S.text(p, { x: 100 + i * 358, y: 365, w: 288, size: 34, align: 'center' }));
    S.stagger(lines, S.capAt(0) + 0.5, 0.45, { dur: 0.4 });
    S.pulse(m.parts.thinker, S.capAt(0) + 3.0);
    S.pulse(m.parts.calc, S.capAt(1) + 0.8);
    const chip = S.chip('placeholder', { x: 100, y: 500, label: c.chip });
    const n0 = S.note(c.notes_on[0], { x: 100, y: 570, w: 1720, color: C.placeholder, size: 46 });
    const n1 = S.note(c.notes_on[1], { x: 100, y: 670, w: 1720, color: C.placeholder, size: 36 });
    S.pop(chip, S.capAt(2) + 0.2);
    S.show(n0, S.capAt(2) + 0.5);
    S.show(n1, S.capAt(2) + 1.6);
  });
});
