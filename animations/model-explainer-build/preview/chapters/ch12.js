/* Chapter 12: ideas built or planned, not yet proven. Every string comes from content/ch12.json (S.c). */
Kit.chapter('ch12', function (Ch) {
  const C = Kit.C;
  const CHIP_Y = 784;

  // status chip bottom-left, "picture only" tag bottom-right
  function status(S, kind, label, t) {
    const ch = S.chip(kind, { x: 80, y: CHIP_Y, label });
    S.show(ch, t);
    return ch;
  }
  function pic(S, label, t) {
    const ch = S.chip('placeholder', { x: 1500, y: CHIP_Y, label });
    S.show(ch, t);
    return ch;
  }
  // a small on/off switch picture: knob on the left = off
  function toggle(S, x, y) {
    const track = S.card({ x, y, w: 130, h: 62, fill: '#EFE8DA', color: C.soft, r: 31 });
    const knob = S.card({ x: x + 6, y: y + 6, w: 50, h: 50, fill: '#fff', color: C.soft, r: 25 });
    return { track, knob };
  }
  // a coral line struck through something
  function strike(S, x1, y1, x2, y2) {
    const svg = S.svg();
    return S.path(svg, [[x1, y1], [x2, y2]], { color: C.call, width: 8, head: 0 });
  }

  // ---------------------------------------------------------------- s01 map
  Ch.scene('s01', function (S) {
    const c = S.c, lb = c.labels;
    const m = S.modelMap({ x: 100, y: 230, w: 1720, h: 170 });
    const keys = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    S.stagger(keys.map((k) => m.parts[k]), S.at(0.05), 0.25);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.05) + i * 0.25 + 0.3, 0.3));
    const bw = (1720 - 280) / 5;
    const tags = keys.map((k, i) => S.text(lb[k], { x: 100 + i * (bw + 70), y: 414, w: bw, size: 32, weight: 700, align: 'center' }));
    S.stagger(tags, S.capAt(0) + 1.0, 0.3);
    const lg1 = S.chip('untested', { x: 100, y: 524, label: c.chips.built });
    const lg2 = S.chip('placeholder', { x: 560, y: 524, label: c.chips.plan });
    S.show(lg1, S.capAt(1));
    S.show(lg2, S.capAt(1) + 0.4);
    const card1 = S.card({ x: 100, y: 610, w: 840, h: 160, fill: '#fff', color: C.line });
    const card2 = S.card({ x: 980, y: 610, w: 840, h: 160, fill: '#fff', color: C.line });
    const t1 = S.text(lb.domain, { x: 130, y: 628, w: 780, size: 44, weight: 700 });
    const t2 = S.text(lb.later, { x: 1010, y: 628, w: 780, size: 44, weight: 700 });
    const ch1 = S.chip('tested', { x: 130, y: 698, label: c.chips.ran });
    const ch2 = S.chip('placeholder', { x: 1010, y: 698, label: c.chips.plan });
    S.show(card1, S.capAt(1) + 1.0); S.show(t1, S.capAt(1) + 1.2); S.pop(ch1, S.capAt(1) + 1.6);
    S.show(card2, S.capAt(1) + 1.4); S.show(t2, S.capAt(1) + 1.6); S.pop(ch2, S.capAt(1) + 2.0);
    S.pulse(ch1, S.capAt(1) + 3.5);
  });

  // ---------------------------------------------------------------- s02 group 1: four changes, two switches
  Ch.scene('s02', function (S) {
    const c = S.c, lb = c.labels;
    const xs = [90, 540, 990, 1440];
    const cols = [C.reader, C.call, C.reader, C.stop];
    const names = [lb.a, lb.b, lb.c, lb.d];
    const tags = [lb.a_tag, lb.b_tag, lb.c_tag, lb.d_tag];
    const boxes = xs.map((x, i) => S.box({ x, y: 290, w: 390, h: 190, label: names[i], sub: tags[i], color: cols[i], size: 38, subSize: 32 }));
    S.stagger(boxes, S.capAt(0) + 0.2, 0.5);
    const tg = [toggle(S, xs[0] + 130, 540), toggle(S, xs[1] + 130, 540)];
    const offs = [S.text(lb.off, { x: xs[0] + 130, y: 612, w: 130, size: 36, weight: 700, align: 'center', color: C.soft }), S.text(lb.off, { x: xs[1] + 130, y: 612, w: 130, size: 36, weight: 700, align: 'center', color: C.soft })];
    tg.forEach((g, i) => { S.pop(g.track, S.capAt(1) + 0.3 + i * 0.4); S.pop(g.knob, S.capAt(1) + 0.4 + i * 0.4); S.show(offs[i], S.capAt(1) + 0.8 + i * 0.4); });
    S.pulse(boxes[0], S.capAt(1) + 1.6); S.pulse(boxes[1], S.capAt(1) + 2.0);
    const svg = S.svg();
    const a = S.arrow(svg, xs[0] + 270, 571, xs[1] + 120, 571, { color: C.call, width: 6 });
    S.tint(tg[0].track, S.capAt(2) + 0.2, { border: C.call, dur: 0.3 });
    S.pulse(tg[0].track, S.capAt(2) + 0.2);
    S.draw(a, S.capAt(2) + 1.2, 0.6);
    S.tint(tg[1].track, S.capAt(2) + 2.2, { border: C.call, dur: 0.3 });
    S.pulse(tg[1].track, S.capAt(2) + 2.2);
    status(S, 'untested', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s03 calls in any round, tape of 16
  Ch.scene('s03', function (S) {
    const c = S.c, lb = c.labels;
    const rl = S.text(lb.rounds, { x: 120, y: 196, w: 400, size: 32, weight: 700, color: C.soft });
    S.show(rl, S.capAt(0));
    const rb = lb.rnums.map((n, i) => S.box({ x: 120 + i * 160, y: 240, w: 130, h: 100, label: n, color: C.thinker, size: 44 }));
    S.stagger(rb, S.capAt(0) + 0.3, 0.25);
    const dots = S.text('…', { x: 1090, y: 245, w: 80, size: 64, weight: 700, color: C.soft });
    S.show(dots, S.capAt(0) + 2.0);
    // calls after round 2 (index 1) and round 5 (index 4)
    const cb = [1, 4].map((r, k) => S.box({ x: 120 + r * 160, y: 390, w: 130, h: 70, label: k === 0 ? lb.c1 : lb.c2, color: C.call, size: 32 }));
    const svg = S.svg();
    const down = [1, 4].map((r) => S.arrow(svg, 185 + r * 160, 342, 185 + r * 160, 388, { color: C.call, width: 5, head: 16 }));
    const tl = S.text(lb.tape, { x: 1100, y: 512, w: 578, size: 32, weight: 700, align: 'right', color: C.soft });
    const cells = [];
    for (let i = 0; i < 16; i++) cells.push(S.box({ x: 120 + i * 98, y: 560, w: 90, h: 70, label: i < 2 ? lb.pl[i] : '', color: C.call, size: 36, border: 3 }));
    const full = S.box({ x: 1000, y: 680, w: 700, h: 70, label: lb.full, color: C.soft, size: 32 });
    const arr2 = [0, 1].map((k) => S.curve(svg, 185 + [1, 4][k] * 160, 462, 165 + k * 98, 558, { color: C.call, width: 5, bend: k === 0 ? 20 : 40, head: 16 }));
    const t0 = S.capAt(1);
    S.show(tl, t0); S.sweep(cells, t0 + 0.2, 0.8);
    S.show(cb[0], t0 + 1.0); S.draw(down[0], t0 + 1.0, 0.4); S.draw(arr2[0], t0 + 1.6, 0.6);
    S.tint(cells[0], t0 + 2.2, { fill: '#FBE3DB', dur: 0.3 });
    S.show(cb[1], t0 + 3.0); S.draw(down[1], t0 + 3.0, 0.4); S.draw(arr2[1], t0 + 3.6, 0.6);
    S.tint(cells[1], t0 + 4.2, { fill: '#FBE3DB', dur: 0.3 });
    cells.slice(2).forEach((cl, i) => S.tint(cl, t0 + 5.0 + i * 0.08, { fill: '#FBE3DB', dur: 0.2 }));
    S.show(full, t0 + 6.5);
    S.pulse(rb[0], S.capAt(2) + 0.3); S.pulse(rb[1], S.capAt(2) + 0.8);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, S.capAt(0) + 0.3);
  });

  // ---------------------------------------------------------------- s04 group 1 marks
  Ch.scene('s04', function (S) {
    const c = S.c, lb = c.labels;
    const U = 1600 / 6, X0 = 160;
    const ax = S.text(lb.axis, { x: X0, y: 262, w: 700, size: 32, weight: 700, color: C.soft });
    S.show(ax, S.capAt(0) + 0.3);
    const z3 = S.card({ x: X0 + 3 * U, y: 340, w: 3 * U, h: 90, fill: '#E4E7EE', color: C.ink });
    const z2 = S.card({ x: X0 + U, y: 340, w: 2 * U, h: 90, fill: '#EFE8DA', color: C.placeholder });
    const z1 = S.card({ x: X0, y: 340, w: U, h: 90, fill: '#FBE3D6', color: C.warn });
    const l3 = S.text(lb.pass, { x: X0 + 3 * U, y: 444, w: 3 * U, size: 34, weight: 700, align: 'center' });
    const l2 = S.text(lb.mid, { x: X0 + U, y: 444, w: 2 * U, size: 34, weight: 700, align: 'center', color: C.soft });
    const l1 = S.text(lb.wrong, { x: X0, y: 444, w: U, size: 32, weight: 700, align: 'center', color: C.warn });
    const br = S.card({ x: X0 + 3 * U, y: 322, w: 3 * U, h: 8, fill: C.thinker, color: C.thinker, r: 4 });
    const gs = S.text(lb.guess, { x: X0 + 3 * U, y: 270, w: 3 * U, size: 34, weight: 700, align: 'center', color: C.thinker });
    S.show(z3, S.capAt(1) + 0.3); S.show(l3, S.capAt(1) + 0.6);
    S.show(br, S.capAt(1) + 2.0); S.show(gs, S.capAt(1) + 2.3);
    S.show(z2, S.capAt(2) + 0.3); S.show(z1, S.capAt(2) + 0.6);
    S.show(l2, S.capAt(2) + 0.9); S.show(l1, S.capAt(2) + 1.1);
    const gt = S.text(lb.gt, { x: X0, y: 548, w: 800, size: 32, weight: 700, color: C.soft });
    const gx = [160, 640, 1120];
    const gb = lb.groups.map((g, i) => S.box({ x: gx[i], y: 596, w: 360, h: 90, label: g, color: i === 0 ? C.reader : C.soft, size: 40 }));
    const svg = S.svg();
    const a1 = S.arrow(svg, 524, 641, 636, 641, { color: C.call, width: 5, head: 16 });
    const a2 = S.curve(svg, 340, 690, 1300, 690, { color: C.call, width: 5, bend: -80, head: 16 });
    S.show(gt, S.capAt(2) + 1.8);
    S.stagger(gb, S.capAt(2) + 2.0, 0.3);
    S.draw(a1, S.capAt(2) + 3.2, 0.5); S.draw(a2, S.capAt(2) + 3.6, 0.8);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, S.capAt(1) + 0.3);
  });

  // ---------------------------------------------------------------- s05 group 2: counting hand-written pieces
  Ch.scene('s05', function (S) {
    const c = S.c, lb = c.labels, v = c.values;
    const items = [
      { label: lb.stop, value: v.stop }, { label: lb.arith, value: v.arith }, { label: lb.read, value: v.read },
      { label: lb.write, value: v.write }, { label: lb.kinds, value: v.kinds },
    ].map((it) => Object.assign(it, { color: C.hand }));
    const hb = S.hbars({ x: 80, y: 250, w: 560, labelW: 300, rowH: 58, gap: 34, max: 6, dec: 0, valueW: 90, valueSize: 44, labelSize: 36, items });
    hb.reveal(S.capAt(0) + 0.5, 0.4, 1.0);
    const line = S.card({ x: 378, y: 236, w: 5, h: 450, fill: C.ink, color: C.ink, r: 2 });
    const ml = S.text(lb.mark, { x: 392, y: 196, w: 420, size: 32, weight: 700 });
    S.show(line, S.capAt(1)); S.show(ml, S.capAt(1) + 0.3);
    S.pulse(hb.rows[2].track, S.capAt(1) + 1.0); S.pulse(hb.rows[4].track, S.capAt(1) + 1.4);
    const svg = S.svg();
    const reps = [lb.r_stop, lb.r_arith, lb.r_read, lb.r_write, lb.r_kinds];
    reps.forEach((r, i) => {
      const y = 250 + i * 92;
      const box = S.box({ x: 1110, y, w: 730, h: 58, label: r, color: C.learned, size: 30, border: 3 });
      const ar = S.arrow(svg, 1030, y + 29, 1100, y + 29, { color: C.soft, width: 4, head: 14 });
      S.show(box, S.capAt(1) + 2.0 + i * 0.4);
      S.draw(ar, S.capAt(1) + 1.8 + i * 0.4, 0.3);
    });
    status(S, 'untested', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s06 group 2: one writer spells the call
  Ch.scene('s06', function (S) {
    const c = S.c, lb = c.labels;
    const card = S.card({ x: 80, y: 230, w: 520, h: 380, fill: '#fff', color: C.hand });
    const today = S.text(lb.today, { x: 110, y: 248, w: 460, size: 34, weight: 700, color: C.hand });
    const ops = lb.ops.map((o, i) => S.text(o, { x: 130 + (i % 2) * 230, y: 320 + Math.floor(i / 2) * 68, w: 200, size: 44, mono: true, weight: 700, color: C.hand }));
    S.show(card, S.capAt(0)); S.show(today, S.capAt(0) + 0.2);
    S.stagger(ops, S.capAt(0) + 0.5, 0.2);
    const sk = strike(S, 100, 600, 580, 290);
    const t1 = S.capAt(1);
    S.draw(sk, t1 + 0.2, 0.6);
    [card, today].concat(ops).forEach((e) => S.tl.to(e, { autoAlpha: 0.4, duration: 0.4 }, t1 + 0.9));
    const th = S.text(lb.thinker, { x: 680, y: 235, w: 440, size: 30, weight: 700, color: C.thinker });
    const vec = S.vec({ x: 680, y: 285, n: 8, cell: 50, gap: 6, color: C.thinker, seed: 5 });
    const wr = S.box({ x: 1190, y: 265, w: 240, h: 100, label: lb.writer, color: C.call, size: 40 });
    const call = S.text('', { x: 1460, y: 268, w: 380, size: 70, mono: true, weight: 800, color: C.call });
    const Q = S.letters(lb.q, { x: 660, y: 530, size: 30, gap: 4 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 1130, 315, 1186, 315, { color: C.soft, width: 5, head: 16 });
    const i12 = lb.q.indexOf('12'), i5 = lb.q.lastIndexOf('5');
    const cv1 = S.curve(svg, (Q.cx(i12) + Q.cx(i12 + 1)) / 2, 526, 1670, 346, { color: C.reader, width: 5, bend: 70, head: 16 });
    const cv2 = S.curve(svg, Q.cx(i5), 526, 1776, 346, { color: C.reader, width: 5, bend: 40, head: 16 });
    S.show(th, t1 + 0.6); S.show(vec, t1 + 0.8); S.draw(a1, t1 + 1.3, 0.4); S.show(wr, t1 + 1.6);
    S.sweep(Q.cells, t1 + 0.8, 1.2);
    S.type(call, lb.call, t1 + 2.4, 1.4);
    S.draw(cv1, t1 + 2.6, 0.9); S.draw(cv2, t1 + 3.0, 0.9);
    pic(S, lb.pic, t1 + 0.8);
    const toy = S.note(lb.toy, { x: 660, y: 640, w: 1180, size: 30, color: C.untested });
    S.show(toy, t1 + 7.0);
    status(S, 'untested', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s07 group 2: learn steps as written
  Ch.scene('s07', function (S) {
    const c = S.c, lb = c.labels;
    // row 1: the old hand rule
    const o1 = S.box({ x: 80, y: 260, w: 260, h: 90, label: lb.old, color: C.hand, size: 36 });
    const o2 = S.box({ x: 400, y: 260, w: 260, h: 90, label: lb.old_to, color: C.soft, size: 40 });
    const sk = strike(S, 400, 350, 660, 260);
    const svg = S.svg();
    const ar1 = S.arrow(svg, 344, 305, 396, 305, { color: C.soft, width: 5, head: 16 });
    S.show(o1, S.capAt(0) + 0.2); S.draw(ar1, S.capAt(0) + 0.8, 0.4); S.show(o2, S.capAt(0) + 1.3); S.draw(sk, S.capAt(0) + 2.0, 0.5);
    // row 2: as written
    const n1 = S.box({ x: 80, y: 380, w: 260, h: 90, label: lb.new, color: C.learned, size: 36 });
    const n2 = S.box({ x: 400, y: 380, w: 260, h: 90, label: lb.new_call, color: C.call, size: 40 });
    const n3 = S.box({ x: 720, y: 380, w: 380, h: 90, label: lb.reply, color: C.calc, size: 36 });
    const tick = S.text('✓', { x: 1120, y: 384, w: 80, size: 64, weight: 800, color: C.tested });
    const ar2 = S.arrow(svg, 344, 425, 396, 425, { color: C.soft, width: 5, head: 16 });
    const ar3 = S.arrow(svg, 664, 425, 716, 425, { color: C.soft, width: 5, head: 16 });
    const t1 = S.capAt(1);
    S.show(n1, t1 + 0.2); S.draw(ar2, t1 + 0.8, 0.4); S.show(n2, t1 + 1.3); S.pulse(n2, t1 + 2.0);
    S.draw(ar3, t1 + 2.6, 0.4); S.show(n3, t1 + 3.1); S.pop(tick, t1 + 3.9);
    // practice alone
    const kept = S.box({ x: 1100, y: 585, w: 500, h: 100, label: '', color: C.learned, size: 36 });
    const kl = S.text(lb.kept, { x: 1100, y: 535, w: 500, size: 32, weight: 700, color: C.learned });
    const q = S.box({ x: 80, y: 585, w: 240, h: 100, label: lb.q, color: C.thinker, size: 38 });
    const tl = S.text(lb.tries, { x: 400, y: 535, w: 400, size: 32, weight: 700, color: C.soft });
    const marks = ['✗', '✓', '✗', '✓'];
    const tries = marks.map((m, i) => S.box({ x: 400 + i * 150, y: 585, w: 130, h: 100, label: m, color: m === '✓' ? C.tested : C.warn, size: 54, border: 4 }));
    const ar4 = S.arrow(svg, 324, 635, 396, 635, { color: C.soft, width: 5, head: 16 });
    const t2 = S.capAt(2);
    S.show(kept, t2 + 0.2); S.show(kl, t2 + 0.3); S.show(q, t2 + 0.4); S.draw(ar4, t2 + 0.9, 0.4); S.show(tl, t2 + 1.0);
    S.stagger(tries, t2 + 1.4, 0.3);
    S.move(tries[1], t2 + 3.6, 0.9, { x: 1130 - 550, y: 0 });
    S.move(tries[3], t2 + 3.8, 0.9, { x: 1290 - 850, y: 0 });
    S.pulse(kept, t2 + 4.9);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, S.capAt(2) + 1.2);
  });

  // ---------------------------------------------------------------- s08 experts
  Ch.scene('s08', function (S) {
    const c = S.c, lb = c.labels, v = c.values;
    const old = S.box({ x: 80, y: 250, w: 380, h: 110, label: lb.old, color: C.thinker, size: 38 });
    S.show(old, S.capAt(0) + 0.3); S.pulse(old, S.capAt(0) + 1.5);
    const router = S.box({ x: 80, y: 420, w: 380, h: 100, label: lb.router, color: C.learned, size: 38 });
    const nl = S.text(lb.new, { x: 560, y: 200, w: 500, size: 32, weight: 700, color: C.thinker });
    const grid = [];
    for (let i = 0; i < 52; i++) grid.push(S.card({ x: 560 + (i % 13) * 66, y: 250 + Math.floor(i / 13) * 66, w: 56, h: 56, fill: '#fff', color: C.thinker, r: 10 }));
    const ul = S.text(lb.unit, { x: 560, y: 516, w: 600, size: 32, weight: 700, color: C.soft });
    const svg = S.svg();
    const ar = S.arrow(svg, 466, 470, 552, 400, { color: C.soft, width: 6, head: 18 });
    const t1 = S.capAt(1);
    S.show(nl, t1 + 0.2); S.sweep(grid, t1 + 0.3, 1.2); S.show(ul, t1 + 1.6);
    S.show(router, t1 + 1.8); S.draw(ar, t1 + 2.4, 0.5);
    [3, 9, 14, 22, 27, 35, 41, 48].forEach((g, i) => {
      S.tint(grid[g], t1 + 3.1 + i * 0.25, { fill: '#DAD8F8', border: C.thinker, dur: 0.3 });
    });
    const pk = S.text(lb.picked, { x: 1440, y: 290, w: 380, size: 36, weight: 700, color: C.thinker });
    const sm = S.text(lb.sum, { x: 1440, y: 395, w: 380, size: 40, weight: 700 });
    const big = S.text('', { x: 1440, y: 440, w: 400, size: 80, weight: 800, color: C.thinker });
    const t2 = S.capAt(2);
    S.show(pk, t1 + 3.2); S.show(sm, t2 + 0.2); S.show(big, t2 + 0.4);
    S.count(big, { from: 0, to: v.units, comma: true }, t2 + 0.5, 1.2);
    const hb = S.hbars({ x: 80, y: 600, w: 860, labelW: 340, rowH: 40, gap: 14, max: v.stored, dec: 0, valueW: 420, valueSize: 38, labelSize: 34, items: [
      { label: lb.stored, value: v.stored, color: C.thinker },
      { label: lb.used, value: v.used, color: C.thinker },
      { label: lb.plain, value: v.plain, color: C.placeholder },
    ] });
    hb.reveal(t2 + 1.8, 0.4, 1.2);
    S.pulse(hb.rows[2].track, S.capAt(3) + 0.3);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, t1 + 3.0);
  });

  // ---------------------------------------------------------------- s09 experts kept alive
  Ch.scene('s09', function (S) {
    const c = S.c, lb = c.labels;
    const ol = S.text(lb.old, { x: 100, y: 200, w: 500, size: 34, weight: 700, color: C.warn });
    const vA = S.vec({ x: 100, y: 260, n: 10, cell: 44, gap: 4, color: C.thinker, seed: 11 });
    const vB = S.vec({ x: 100, y: 330, n: 10, cell: 44, gap: 4, color: C.thinker, seed: 11 });
    const eq = S.text('=', { x: 600, y: 280, w: 80, size: 90, weight: 800, align: 'center', color: C.warn });
    const sm = S.text(lb.same, { x: 700, y: 318, w: 260, size: 34, weight: 700, color: C.warn });
    S.show(ol, S.capAt(0) + 0.2); S.show(vA, S.capAt(0) + 0.6);
    S.show(vB, S.capAt(1) + 0.2); S.pop(eq, S.capAt(1) + 0.8); S.show(sm, S.capAt(1) + 1.2);
    // right: 52 experts, how often each is picked
    const nw = S.text(lb.new, { x: 1000, y: 196, w: 300, size: 34, weight: 700 });
    const band = S.card({ x: 1000, y: 290, w: 832, h: 180, fill: '#EEF0FB', color: C.thinker, r: 6 });
    const bl = S.text(lb.band, { x: 1000, y: 245, w: 832, size: 30, weight: 700, color: C.thinker });
    const rnd = Kit.rng(7);
    const bars = [];
    for (let i = 0; i < 52; i++) { const h = Math.round(70 + rnd() * 140); bars.push(S.card({ x: 1000 + i * 16, y: 530 - h, w: 12, h, fill: C.thinker, color: C.thinker, r: 2 })); }
    const even = S.card({ x: 1000, y: 410, w: 832, h: 3, fill: C.ink, color: C.ink, r: 1 });
    const el = S.text(lb.even, { x: 1000, y: 546, w: 832, size: 30, weight: 700 });
    const t2 = S.capAt(2);
    S.show(nw, t2 + 0.2); S.show(band, t2 + 0.4); S.show(bl, t2 + 0.6);
    S.sweep(bars, t2 + 1.0, 1.6);
    S.show(even, t2 + 2.8); S.show(el, t2 + 3.0);
    const why = S.note(lb.why, { x: 100, y: 640, w: 1000, size: 32, color: C.untested });
    S.show(why, S.capAt(3) + 0.2);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, t2 + 1.0);
  });

  // ---------------------------------------------------------------- s10 tokens
  Ch.scene('s10', function (S) {
    const c = S.c, lb = c.labels, v = c.values;
    const Q = S.letters(lb.letters, { x: 160, y: 260, size: 56 });
    const ll = S.text(lb.today, { x: 160, y: 212, w: 500, size: 32, weight: 700, color: C.soft });
    S.show(ll, S.capAt(0) + 0.2); S.sweep(Q.cells, S.capAt(0) + 0.4, 1.6);
    const groups = [[0, 2], [4, 6], [8, 9], [11, 13], [14, 16], [17, 17]];
    const tb = groups.map((g) => {
      const left = Q.cx(g[0]) - Q.cw / 2, right = Q.cx(g[1]) + Q.cw / 2;
      return S.box({ x: left, y: 440, w: right - left, h: 70, label: '', color: C.reader, border: 4 });
    });
    const tl = S.text(lb.tok, { x: 160, y: 396, w: 500, size: 32, weight: 700, color: C.reader });
    const t1 = S.capAt(1);
    S.show(tl, t1 + 0.2); S.stagger(tb, t1 + 0.5, 0.3);
    const ul = S.text(lb.unit, { x: 1150, y: 212, w: 690, size: 32, weight: 700, color: C.soft });
    const cards = [1150, 1500].map((x) => S.card({ x, y: 260, w: 320, h: 240, fill: '#fff', color: C.reader }));
    const nums = [1150, 1500].map((x) => S.text('', { x, y: 290, w: 320, size: 100, weight: 800, align: 'center', color: C.reader }));
    const cl = [lb.skills, lb.web].map((s, i) => S.text(s, { x: [1150, 1500][i], y: 430, w: 320, size: 32, weight: 700, align: 'center' }));
    S.show(ul, t1 + 1.8);
    [0, 1].forEach((i) => {
      const t = t1 + 2.2 + i * 0.9;
      S.show(cards[i], t); S.show(nums[i], t + 0.2); S.show(cl[i], t + 0.3);
      S.count(nums[i], { from: 0, to: i === 0 ? v.skills : v.web, dec: 2 }, t + 0.3, 1.2);
    });
    tb.forEach((b, i) => S.pulse(b, S.capAt(2) + 0.3 + i * 0.15));
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, t1 + 0.5);
  });

  // ---------------------------------------------------------------- s11 tokens: the risk is spelling
  Ch.scene('s11', function (S) {
    const c = S.c, lb = c.labels, v = c.values;
    const svg = S.svg();
    function row(y, tag, struck, t) {
      const tx = S.text(tag, { x: 80, y: y - 52, w: 1000, size: 34, weight: 700, color: C.ink });
      const b1 = S.box({ x: 80, y, w: 260, h: 90, label: lb.l, color: C.reader, size: 36 });
      const b2 = S.box({ x: 400, y, w: 260, h: 90, label: lb.w, color: struck ? C.placeholder : C.reader, size: 36 });
      const b3 = S.box({ x: 720, y, w: 300, h: 90, label: lb.t, color: C.thinker, size: 36 });
      const a1 = S.arrow(svg, 344, y + 45, 396, y + 45, { color: C.soft, width: 5, head: 16 });
      const a2 = S.arrow(svg, 664, y + 45, 716, y + 45, { color: C.soft, width: 5, head: 16 });
      S.show(tx, t); S.show(b1, t + 0.3); S.draw(a1, t + 0.8, 0.4); S.show(b2, t + 1.1); S.draw(a2, t + 1.6, 0.4); S.show(b3, t + 1.9);
      return { b2 };
    }
    row(300, lb.tk, false, S.capAt(0) + 0.2);
    const ol = S.text(lb.old, { x: 1260, y: 235, w: 580, size: 32, weight: 700, color: C.warn });
    const cards = [1260, 1570].map((x) => S.card({ x, y: 290, w: 270, h: 210, fill: '#fff', color: C.warn }));
    const nums = [1260, 1570].map((x) => S.text('', { x, y: 340, w: 270, size: 90, weight: 800, align: 'center', color: C.warn }));
    const t1 = S.capAt(1);
    S.show(ol, t1 + 0.2);
    [0, 1].forEach((i) => {
      const t = t1 + 0.6 + i * 0.9;
      S.show(cards[i], t); S.show(nums[i], t + 0.2);
      S.count(nums[i], { from: 0, to: -(i === 0 ? v.lost1 : v.lost2), dec: 1 }, t + 0.3, 1.4);
    });
    const t2 = S.capAt(2);
    const r2 = row(500, lb.tkn, true, t2 + 0.2);
    const sk = strike(S, 400, 590, 660, 500);
    S.draw(sk, t2 + 2.4, 0.6);
    const runs = S.note(lb.runs, { x: 80, y: 650, w: 1000, size: 32, color: C.untested });
    S.show(runs, t2 + 3.4);
    status(S, 'untested', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s12 reading long text (plan)
  Ch.scene('s12', function (S) {
    const c = S.c, lb = c.labels;
    const xs = [140, 700, 1260];
    const ps = [lb.p1, lb.p2, lb.p3].map((p, i) => S.box({ x: xs[i], y: 380, w: 420, h: 120, label: p, color: C.reader, size: 40 }));
    const lim = S.text(lb.limit, { x: 140, y: 296, w: 400, size: 30, weight: 700, color: C.soft });
    S.show(ps[0], S.capAt(0) + 0.3); S.show(lim, S.capAt(0) + 1.0);
    const svg = S.svg();
    const a1 = S.arrow(svg, 566, 455, 694, 455, { color: C.thinker, width: 6, head: 18 });
    const a2 = S.arrow(svg, 1126, 455, 1254, 455, { color: C.thinker, width: 6, head: 18 });
    const v1 = S.vec({ x: 578, y: 400, n: 3, cell: 32, gap: 4, color: C.thinker, seed: 3 });
    const v2 = S.vec({ x: 1138, y: 400, n: 3, cell: 32, gap: 4, color: C.thinker, seed: 8 });
    const nc = S.text(lb.notes, { x: 1020, y: 334, w: 340, size: 30, weight: 700, align: 'center', color: C.thinker });
    const t1 = S.capAt(1);
    S.show(ps[1], t1 + 0.3); S.show(v1, t1 + 0.6); S.draw(a1, t1 + 0.9, 0.5);
    S.show(ps[2], t1 + 2.0); S.show(v2, t1 + 2.3); S.draw(a2, t1 + 2.6, 0.5); S.show(nc, t1 + 3.0);
    const lk = S.curve(svg, 1470, 500, 350, 500, { color: C.learned, width: 6, bend: 170, head: 20 });
    const ll = S.text(lb.look, { x: 660, y: 604, w: 500, size: 34, weight: 700, align: 'center', color: C.learned });
    const t2 = S.capAt(2);
    S.draw(lk, t2 + 0.3, 1.2); S.show(ll, t2 + 1.2);
    status(S, 'placeholder', c.chip, S.at(0.05));
    pic(S, lb.pic, S.capAt(1) + 0.3);
  });

  // ---------------------------------------------------------------- s13 domain mode: the loop
  Ch.scene('s13', function (S) {
    const c = S.c, lb = c.labels;
    const pos = [[100, 260], [550, 260], [1000, 260], [1450, 260], [100, 490], [550, 490], [1000, 490]];
    const names = [lb.s1, lb.s2, lb.s3, lb.s4, lb.s5, lb.s6, lb.s7];
    const bx = pos.map((p, i) => S.box({ x: p[0], y: p[1], w: 370, h: 120, label: names[i], color: C.soft, size: 38 }));
    const svg = S.svg();
    const links = [[0, 1], [1, 2], [2, 3], [4, 5], [5, 6]].map(([a, b]) => S.arrow(svg, pos[a][0] + 374, pos[a][1] + 60, pos[b][0] - 4, pos[b][1] + 60, { color: C.soft, width: 5, head: 16 }));
    const ret = S.path(svg, [[1635, 384], [1635, 436], [285, 436], [285, 486]], { color: C.soft, width: 5, head: 16 });
    const mk = S.card({ x: 106, y: 238, w: 36, h: 36, fill: C.untested, color: C.untested, r: 18 });
    const goTo = (i, t) => S.move(mk, t, 0.6, { x: pos[i][0] - 100, y: pos[i][1] - 260 });
    const t0 = S.capAt(0);
    S.show(bx[0], t0 + 0.3); S.pop(mk, t0 + 0.8);
    S.draw(links[0], t0 + 3.0, 0.4); S.show(bx[1], t0 + 3.3); goTo(1, t0 + 3.5);
    const t1 = S.capAt(1);
    S.draw(links[1], t1 + 0.3, 0.4); S.show(bx[2], t1 + 0.6); goTo(2, t1 + 0.8);
    S.draw(links[2], t1 + 3.0, 0.4); S.show(bx[3], t1 + 3.3); goTo(3, t1 + 3.5);
    S.draw(ret, t1 + 6.0, 1.0);
    const t2 = S.capAt(2);
    S.show(bx[4], t2 + 0.2); goTo(4, t2 + 0.4);
    S.draw(links[3], t2 + 1.1, 0.3); S.show(bx[5], t2 + 1.4); goTo(5, t2 + 1.6);
    S.draw(links[4], t2 + 2.3, 0.3); S.show(bx[6], t2 + 2.6); goTo(6, t2 + 2.8);
    status(S, 'untested', c.chip, S.at(0.05));
    pic(S, lb.pic, S.capAt(0) + 0.5);
  });

  // ---------------------------------------------------------------- s14 domain mode: the first run
  Ch.scene('s14', function (S) {
    const c = S.c, lb = c.labels, v = c.values;
    const BX = 250, BW = 1000;
    function row(y, lab, val, col, dec, pre) {
      const l = S.text(lab, { x: 80, y: y + 4, w: 150, size: 32, weight: 700, align: 'right' });
      const b = S.bar({ x: BX, y, w: BW, h: 40, value: val, max: 100, color: col });
      const n = S.text('', { x: BX + BW + 24, y: y - 2, w: 260, size: 40, weight: 800 });
      return { l, b, n, dec, pre };
    }
    function reveal(r, t) {
      S.show(r.l, t, { dur: 0.4 }); S.show(r.b.track, t, { dur: 0.4 }); S.show(r.n, t + 0.2, { dur: 0.3 });
      S.grow(r.b, t + 0.3, 1.2, r.n, { dec: r.dec, pre: r.pre || '' });
    }
    function group(y, title, v0, v1, col, dec, pre1) {
      const g = S.text(title, { x: BX, y: y - 44, w: 500, size: 32, weight: 700, color: C.soft });
      return { g, r0: row(y, lb.before, v0, C.placeholder, dec), r1: row(y + 52, lb.after, v1, col, dec, pre1) };
    }
    function revealGroup(gp, t) { S.show(gp.g, t); reveal(gp.r0, t + 0.3); reveal(gp.r1, t + 1.1); }
    const g1 = group(280, lb.quiz, v.quiz0, v.quiz1, C.tested, 0, '~');
    g1.r0.dec = 1;
    const g2 = group(440, lb.near, v.near0, v.near1, C.warn, 2);
    const g3 = group(610, lb.far, v.far0, v.far1, C.warn, 2);
    revealGroup(g1, S.capAt(0) + 0.4);
    const t1 = S.capAt(1);
    revealGroup(g2, t1 + 0.3);
    const mark = S.card({ x: BX + BW * (v.near0 + 30) / 100, y: 432, w: 5, h: 116, fill: C.warn, color: C.warn, r: 2 });
    const ml = S.text(lb.need, { x: BX + BW * (v.near0 + 30) / 100 + 14, y: 394, w: 300, size: 30, weight: 700, color: C.warn });
    S.show(mark, t1 + 3.0); S.show(ml, t1 + 3.2);
    revealGroup(g3, t1 + 4.5);
    status(S, 'tested', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s15 plans with no design yet
  Ch.scene('s15', function (S) {
    const c = S.c, lb = c.labels;
    const xs = [110, 690, 1270], ys = [270, 490];
    const keys = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];
    const cards = keys.map((k, i) => S.box({ x: xs[i % 3], y: ys[Math.floor(i / 3)], w: 540, h: 170, label: lb[k], color: C.placeholder, size: 38 }));
    S.stagger(cards.slice(0, 3), S.capAt(0) + 0.4, 0.8);
    S.stagger(cards.slice(3), S.capAt(1) + 0.4, 0.8);
    status(S, 'placeholder', c.chip, S.at(0.05));
  });

  // ---------------------------------------------------------------- s16 order and recap
  Ch.scene('s16', function (S) {
    const c = S.c, lb = c.labels;
    const xs = [80, 335, 590, 845, 1100, 1355, 1610];
    const names = [lb.g1, lb.ex, lb.b1, lb.b2, lb.m10, lb.m30, lb.m100];
    const cols = [C.soft, C.untested, C.untested, C.untested, C.placeholder, C.placeholder, C.placeholder];
    const bx = xs.map((x, i) => S.box({ x, y: 330, w: 215, h: 110, label: names[i], color: cols[i], size: 32, border: 4 }));
    const svg = S.svg();
    const ar = xs.slice(0, -1).map((x, i) => S.arrow(svg, x + 219, 385, xs[i + 1] - 4, 385, { color: C.soft, width: 4, head: 14 }));
    const mk = S.card({ x: xs[0] + 90, y: 288, w: 36, h: 36, fill: C.untested, color: C.untested, r: 18 });
    const t0 = S.capAt(0);
    S.stagger(bx, t0 + 0.2, 0.3);
    ar.forEach((a, i) => S.draw(a, t0 + 0.5 + i * 0.3, 0.3));
    S.pulse(bx[2], t0 + 3.2); S.pulse(bx[3], t0 + 3.6);
    const t1 = S.capAt(1);
    const side = S.box({ x: 200, y: 570, w: 720, h: 100, label: lb.side, color: C.soft, size: 34 });
    const dom = S.box({ x: 980, y: 570, w: 720, h: 100, label: lb.dom, color: C.soft, size: 34 });
    S.show(side, t1 + 0.4); S.show(dom, t1 + 1.0); S.pulse(bx[1], t1 + 1.6);
    const t2 = S.capAt(2);
    S.pop(mk, t2 + 0.2);
    xs.slice(1).forEach((x, i) => S.move(mk, t2 + 0.8 + i * 0.9, 0.7, { x: x - xs[0], y: 0 }));
    status(S, 'placeholder', c.chip, S.at(0.05));
  });
});
