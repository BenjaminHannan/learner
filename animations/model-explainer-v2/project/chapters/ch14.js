Kit.chapter('ch14', function (Ch) {
  const C = Kit.C;
  const col = (k) => (k && C[k]) || k;
  // status chip from a JSON spec {kind,label,color?}
  const mkChip = (S, spec, x, y, size) => S.chip(spec.kind, { x: x, y: y, label: spec.label, size: size || 28, color: spec.color ? col(spec.color) : undefined });
  const monoLab = (b) => { const l = b.querySelector('.lab'); if (l) l.classList.add('mono'); };

  // s01: the four-part ledger plus the outside calculator. Map first, then a status chip per part, stepping with the captions.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 215, w: 1720, h: 150 });
    const dkeys = ['reader', 'thinker', 'calc', 'stop', 'talker'];   // order of c.parts in the content file
    m.order.forEach((k, i) => S.show(m.parts[k], S.at(0.04) + i * 0.18));
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.08) + (i + 1) * 0.18, 0.3));
    const groups = c.parts.map((p, i) => {
      const x = m.colX[dkeys[i]], els = [];
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

  // s03: result one. Three bars grow and count.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 100, y: 240, w: 860, labelW: 420, rowH: 76, gap: 34, max: 100, dec: 2, labelSize: 40, valueSize: 52,
      items: c.bars.map((b) => ({ label: b.label, value: b.value, color: col(b.color), dec: 2 })) });
    const revealRow = (r, t, gd) => { S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 }); S.grow(r.b, t + 0.3, gd || 1.5, r.val, { dec: 2, comma: true }); };
    revealRow(hb.rows[0], S.capAt(0) + 0.3);
    revealRow(hb.rows[1], S.capAt(1) + 0.15, 0.9);   // counts finish about 1.8 s after the caption that names them appears
    revealRow(hb.rows[2], S.capAt(1) + 0.65, 0.8);
    S.pop(S.chip('tested', { x: 100, y: 600, label: c.labels.chip }), S.capAt(2) + 0.2);
    const gap = S.note(c.labels.gap, { x: 100, y: 675, w: 780, color: C.thinker, size: 36 });
    const cav = S.note(c.labels.caveat, { x: 930, y: 675, w: 890, color: C.warn, size: 32 });
    S.show(gap, S.capAt(2) + 0.6);
    S.show(cav, S.capAt(2) + 1.4);
  });

  // s04: result two. Slip out, reply back (made-up example), then the likely-range picture.
  Ch.scene('s04', function (S) {
    const c = S.c, L = c.labels, V = c.values;
    const slip = S.box({ x: 120, y: 230, w: 360, h: 130, label: L.slip, color: C.call, size: 46 }); monoLab(slip);
    const calc = S.box({ x: 700, y: 215, w: 400, h: 160, label: L.calc, color: C.calc, size: 46 });
    const rnote = S.text(L.replyNote, { x: 1240, y: 380, w: 460, size: 34, align: 'center', color: C.ink });
    const back = S.box({ x: 1320, y: 230, w: 300, h: 130, label: L.reply, color: C.calc, size: 64 }); monoLab(back);   // calculator slate: a made-up reply must not look 'tested'
    const tag = S.chip('placeholder', { x: 120, y: 392, label: L.tag, size: 26 });
    const ok = S.chip('tested', { x: 200, y: 545, label: L.chip, size: 26 });   // sits with the number line it describes
    const svg0 = S.svg();
    const a1 = S.arrow(svg0, 484, 295, 696, 295, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg0, 1104, 295, 1316, 295, { color: C.soft, width: 6 });
    S.show(slip, S.capAt(0) + 0.3);
    S.draw(a1, S.capAt(0) + 1.2, 0.6);
    S.show(calc, S.capAt(0) + 1.5);
    S.draw(a2, S.capAt(0) + 2.4, 0.6);
    S.show(back, S.capAt(0) + 3.0);
    S.show(rnote, S.capAt(0) + 3.2);
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
    S.show(off, S.capAt(2) + 0.3);
  });

  // s05: the two calculator checks that were not clean (swap check 5 of 6, leak check missed then cleared by the owner).
  Ch.scene('s05', function (S) {
    const c = S.c;
    const W = 860, H = 500, y0 = 215, xs = [80, 980];
    const cols = [C.warn, C.warn];
    const cards = c.cards.map((cd, i) => {
      const x = xs[i];
      return {
        card: S.card({ x: x, y: y0, w: W, h: H }),
        title: S.text(cd.title, { x: x + 30, y: y0 + 24, w: W - 60, size: 44, weight: 700 }),
        big: S.text(cd.big, { x: x + 30, y: y0 + 100, w: W - 60, size: 100, weight: 800, color: cols[i] }),
        tx: S.text(cd.text, { x: x + 30, y: y0 + 255, w: W - 60, size: 34 }),
        chip: mkChip(S, cd.chip, x + 30, y0 + H - 78, 28),
      };
    });
    cards.forEach((r) => { S.show(r.card, S.capAt(0) + 0.4, { dur: 0.5 }); S.show(r.title, S.capAt(0) + 0.7, { dur: 0.4 }); });
    const rv = (r, t) => { S.show(r.big, t, { dur: 0.5 }); S.show(r.tx, t + 0.6, { dur: 0.5 }); S.pop(r.chip, t + 1.4); };
    rv(cards[0], S.capAt(1) + 0.3);
    rv(cards[1], S.capAt(2) + 0.3);
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
    const hb = S.hbars({ x: 80, y: 265, w: 500, labelW: 250, rowH: 70, gap: 30, max: 100, dec: 2, labelSize: 38, valueSize: 46, valueW: 130,
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

  // s10: the next gates, in order (a plan; no dates promised). Four captions, two boxes each.
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
    S.draw(arrows[0], S.capAt(0) + 2.4, 0.5); S.show(boxes[1], S.capAt(0) + 3.0);
    S.draw(arrows[1], S.capAt(1) + 0.4, 0.5); S.show(boxes[2], S.capAt(1) + 1.0);
    S.draw(arrows[2], S.capAt(1) + 2.6, 0.5); S.show(boxes[3], S.capAt(1) + 3.2);
    S.draw(conn, S.capAt(2) + 0.3, 0.9);
    S.show(boxes[4], S.capAt(2) + 1.2);
    S.draw(arrows[3], S.capAt(2) + 3.6, 0.5); S.show(boxes[5], S.capAt(2) + 4.2);
    S.draw(arrows[4], S.capAt(3) + 0.3, 0.5); S.show(boxes[6], S.capAt(3) + 0.9);
    S.draw(arrows[5], S.capAt(3) + 2.4, 0.5); S.show(boxes[7], S.capAt(3) + 3.0);
    S.pulse(boxes[7], S.capAt(3) + 4.2);
  });

  // s12: recap. The five-part map with one short line and one status chip each, then the plan's own bottom line (labelled).
  Ch.scene('s12', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 215, w: 1720, h: 140 });
    const dkeys = ['reader', 'thinker', 'calc', 'stop', 'talker'];   // order of c.parts and of the status list
    m.order.forEach((k, i) => S.show(m.parts[k], S.at(0.04) + i * 0.18));
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.08) + (i + 1) * 0.18, 0.3));
    const lines = c.parts.map((p, i) => S.text(p, { x: m.colX[dkeys[i]], y: 372, w: 288, size: 34 }));
    S.stagger(lines, S.capAt(0) + 0.5, 0.45, { dur: 0.4 });
    // one status chip per part (kit default words, same statuses as s01), so "most of the rest is built or planned" is visible
    const stat = ['tested', 'tested', 'tested', 'untested', 'placeholder'].map((k, i) => S.chip(k, { x: m.colX[dkeys[i]], y: 500, size: 26 }));
    S.pop(stat[0], S.capAt(0) + 1.4); S.pop(stat[1], S.capAt(0) + 1.9);
    S.pop(stat[2], S.capAt(1) + 0.4);
    S.pop(stat[3], S.capAt(1) + 1.8); S.pop(stat[4], S.capAt(1) + 2.4);
    S.pulse(m.parts.thinker, S.capAt(0) + 3.0);
    S.pulse(m.parts.calc, S.capAt(1) + 0.8);
    const chip = S.chip('placeholder', { x: 100, y: 565, label: c.chip });
    const dz = S.text(c.design, { x: 100, y: 826, w: 1720, size: 29, weight: 600, color: C.soft });
    S.show(dz, S.capAt(1) + 3.2);
    const n0 = S.note(c.notes_on[0], { x: 100, y: 630, w: 1720, color: C.placeholder, size: 46 });
    const n1 = S.note(c.notes_on[1], { x: 100, y: 735, w: 1720, color: C.placeholder, size: 36 });
    S.pop(chip, S.capAt(2) + 0.2);
    S.show(n0, S.capAt(2) + 0.5);
    S.show(n1, S.capAt(2) + 1.6);
  });
});
