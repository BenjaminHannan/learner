Kit.chapter('ch02', function (Ch) {
  const C = Kit.C;

  // Local helper: a card that grows from its left edge (seek-safe: absolute end states only).
  function growX(S, e, t, dur) {
    S.tl.set(e, { autoAlpha: 1, transformOrigin: '0% 50%' }, t);
    S.tl.fromTo(e, { scaleX: 0 }, { scaleX: 1, duration: dur, ease: 'power2.out' }, t);
    return t + dur;
  }
  // Local helper: a small number text that counts up.
  function counter(S, o, t, dur) {
    const e = S.text('', { x: o.x, y: o.y, w: o.w || 400, size: o.size || 50, weight: o.weight || 800, color: o.color || C.ink, align: o.align || 'left', nowrap: true });
    S.show(e, t, { dur: 0.3, y: 8 });
    S.count(e, { from: 0, to: o.to, dec: o.dec || 0, pre: o.pre || '', suf: o.suf || '', comma: !!o.comma }, t, dur);
    return e;
  }

  // s01: the goal, four rows, near to far.
  Ch.scene('s01', function (S) {
    const L = S.c.labels;
    const cols = [C.thinker, C.learned, C.soft, C.soft];
    const kinds = ['tested', 'tested', 'placeholder', 'placeholder'];
    ['g1', 'g2', 'g3', 'g4'].forEach((k, i) => {
      const y = 230 + i * 150;
      const b = S.box({ x: 120, y: y, w: 900, h: 120, label: L[k], color: cols[i], size: 46 });
      if (i === 3) b.style.borderStyle = 'dashed';
      const ch = S.chip(kinds[i], { x: 1080, y: y + 38, label: L['c' + (i + 1)] });
      S.show(b, S.capAt(i));
      S.pop(ch, S.capAt(i) + 0.6);
      S.pulse(b, S.capAt(i) + 0.9);
    });
  });

  // s02: the race as a staircase, tall steps are far away.
  Ch.scene('s02', function (S) {
    const L = S.c.labels;
    const b1 = S.box({ x: 120, y: 520, w: 520, h: 200, label: L.s1, color: C.thinker, size: 42 });
    const b2 = S.box({ x: 700, y: 400, w: 520, h: 320, label: L.s2, color: C.learned, size: 42 });
    const b3 = S.box({ x: 1280, y: 280, w: 520, h: 440, label: L.s3, color: C.soft, size: 42 });
    b3.style.borderStyle = 'dashed';
    const c1 = S.chip('placeholder', { x: 120, y: 450, label: L.c1 });
    const c2 = S.chip('placeholder', { x: 700, y: 330, label: L.c2 });
    const c3 = S.chip('placeholder', { x: 1280, y: 210, label: L.c3 });
    const pass = S.note(L.pass, { x: 120, y: 745, w: 520, size: 34, color: C.thinker });
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const a1 = S.arrow(svg, 644, 620, 696, 620, { color: C.soft, width: 6, head: 18 });
    const a2 = S.arrow(svg, 1224, 560, 1276, 560, { color: C.soft, width: 6, head: 18 });
    S.show(b1, S.capAt(0));
    S.show(pass, S.capAt(1));
    S.pulse(b1, S.capAt(1) + 0.4);
    S.draw(a1, S.capAt(2), 0.5);
    S.show(b2, S.capAt(2) + 0.4);
    S.pop(c2, S.capAt(2) + 1.1);
    S.pop(c1, S.capAt(3));
    S.draw(a2, S.capAt(3) + 1.2, 0.5);
    S.show(b3, S.capAt(3) + 1.6);
    S.pop(c3, S.capAt(3) + 2.4);
  });

  // s03: whole size counts everything. Two stacked bars to one scale (3.3 px per million).
  Ch.scene('s03', function (S) {
    const L = S.c.labels, N = S.c.nums, k = 3.3, x0 = 120;
    const seg = (x, y, w, col) => S.card({ x: x, y: y, w: w, h: 110, fill: col, color: col, r: 10 });
    const lab = (x, y, w, str, size) => S.text(str, { x: x, y: y, w: w, align: 'center', size: size || 34, weight: 600, color: C.ink });
    // bar 1: as built
    const wR = N.reader * k, wL = N.learned * k;
    const h1 = S.text(L.tot1, { x: x0, y: 236, w: 500, size: 40, weight: 800, color: C.soft });
    const sR = seg(x0, 290, wR, C.reader), sL = seg(x0 + wR, 290, wL, C.learned);
    const lR = lab(x0, 410, wR, L.reader), lL = lab(x0 + wR, 410, wL, L.learned);
    // bar 2: planned
    const wP1 = N.pr * k, wP2 = N.pt * k, wP3 = N.pk * k;
    const h2 = S.text(L.tot2, { x: x0, y: 536, w: 800, size: 40, weight: 800, color: C.soft });
    const pR = seg(x0, 590, wP1, C.reader), pT = seg(x0 + wP1, 590, wP2, C.thinker), pK = seg(x0 + wP1 + wP2, 590, wP3, C.talker);
    const qR = lab(x0, 710, wP1, L.pr), qT = lab(x0 + wP1, 710, wP2, L.pt), qK = lab(x0 + wP1 + wP2 - 40, 710, wP3 + 80, L.pk);
    const c1 = S.chip('placeholder', { x: x0 + wR + wL + 30, y: 420, label: L.c1 });
    const c2 = S.chip('placeholder', { x: x0 + wP1 + wP2 + wP3 + 50, y: 684, label: L.c2 });
    // capAt(0): the borrowed reader counts too
    let t = S.capAt(0);
    S.show(h1, t);
    growX(S, sR, t + 0.4, 1.4);
    S.show(lR, t + 1.2);
    // capAt(1): its size, then ours
    t = S.capAt(1);
    counter(S, { x: x0, y: 452, w: wR, align: 'center', size: 50, color: C.reader, to: N.reader, dec: 1, suf: ' M' }, t, 1.4);
    growX(S, sL, t + 1.6, 1.0);
    S.show(lL, t + 2.2);
    counter(S, { x: x0 + wR, y: 452, w: wL, align: 'center', size: 50, color: C.learned, to: N.learned, dec: 1, suf: ' M' }, t + 2.0, 1.2);
    // capAt(2): the sum
    t = S.capAt(2);
    counter(S, { x: x0 + wR + wL + 30, y: 300, w: 440, size: 76, to: N.total, dec: 1, pre: '= ', suf: ' M' }, t, 1.4);
    S.pop(c1, t + 1.0);
    // capAt(3): the plan, to the same scale
    t = S.capAt(3);
    S.show(h2, t);
    growX(S, pR, t + 0.3, 1.0);
    growX(S, pT, t + 1.3, 0.8);
    growX(S, pK, t + 2.1, 0.5);
    S.show(qR, t + 0.8); S.show(qT, t + 1.6); S.show(qK, t + 2.3);
    counter(S, { x: x0, y: 752, w: wP1, align: 'center', size: 46, color: C.reader, to: N.pr, pre: '≈ ', suf: ' M' }, t + 0.8, 1.0);
    counter(S, { x: x0 + wP1, y: 752, w: wP2, align: 'center', size: 46, color: C.thinker, to: N.pt, pre: '≈ ', suf: ' M' }, t + 1.6, 0.8);
    counter(S, { x: x0 + wP1 + wP2 - 40, y: 752, w: wP3 + 80, align: 'center', size: 46, color: C.talker, to: N.pk, pre: '≈ ', suf: ' M' }, t + 2.3, 0.6);
    counter(S, { x: x0 + wP1 + wP2 + wP3 + 30, y: 600, w: 420, size: 60, to: N.planned, pre: 'about ', suf: ' M' }, t + 3.0, 1.2);
    S.pop(c2, t + 4.2);
  });

  // s04: two growth lines, picture only. Ours must climb more than the plain model's.
  Ch.scene('s04', function (S) {
    const L = S.c.labels;
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const axY = S.arrow(svg, 260, 780, 260, 250, { color: C.soft, width: 5, head: 18 });
    const axX = S.arrow(svg, 260, 780, 1180, 780, { color: C.soft, width: 5, head: 18 });
    const xs = [380, 620, 860, 1100];
    const yo = xs.map((x) => 640 + (x - 380) * (300 - 640) / 720);
    const yp = xs.map((x) => 640 + (x - 380) * (500 - 640) / 720);
    const lnO = S.path(svg, [[380, 640], [1100, 300]], { color: C.thinker, width: 9, head: 0 });
    const lnP = S.path(svg, [[380, 640], [1100, 500]], { color: C.placeholder, width: 9, head: 0 });
    const dots = [];
    xs.forEach((x, i) => {
      dots.push(S.svgEl(svg, 'circle', { cx: x, cy: yp[i], r: 11, fill: C.placeholder }));
      dots.push(S.svgEl(svg, 'circle', { cx: x, cy: yo[i], r: 11, fill: C.thinker }));
    });
    const tScore = S.text(L.score, { x: 290, y: 205, w: 300, size: 36, weight: 700, color: C.soft });
    const tSize = S.text(L.size, { x: 1200, y: 750, w: 200, size: 36, weight: 700, color: C.soft });
    const rungs = ['r1', 'r2', 'r3', 'r4'].map((k, i) => S.text(L[k], { x: xs[i] - 70, y: 792, w: 140, align: 'center', size: 34, weight: 700, color: C.ink }));
    const bO = S.box({ x: 1260, y: 330, w: 520, h: 90, label: L.ours, color: C.thinker, size: 42 });
    const bP = S.box({ x: 1260, y: 450, w: 520, h: 90, label: L.plain, color: C.placeholder, size: 42 });
    const pic = S.chip('placeholder', { x: 1260, y: 600, label: L.pic });
    const c1 = S.chip('placeholder', { x: 1260, y: 680, label: L.c1 });
    S.show(pic, S.capAt(0));
    S.draw(axY, S.capAt(0) + 0.2, 0.6);
    S.draw(axX, S.capAt(0) + 0.2, 0.6);
    S.show(tScore, S.capAt(0) + 0.8); S.show(tSize, S.capAt(0) + 0.8);
    S.draw(lnO, S.capAt(0) + 1.4, 1.6);
    S.show(bO, S.capAt(0) + 1.6);
    S.draw(lnP, S.capAt(1), 1.4);
    S.show(bP, S.capAt(1) + 0.4);
    S.sweep(rungs, S.capAt(2), 2.0);
    S.sweep(dots, S.capAt(2) + 0.3, 2.4);
    S.pop(c1, S.capAt(3));
  });

  // s05: learned inside, hand code only outside as a tool the model calls.
  Ch.scene('s05', function (S) {
    const L = S.c.labels;
    const frame = S.card({ x: 100, y: 225, w: 1100, h: 540, fill: '#ffffff', color: C.learned, r: 24 });
    frame.style.borderWidth = '5px';
    const fl = S.text(L.frame, { x: 130, y: 245, w: 600, size: 38, weight: 800, color: C.learned });
    const fchip = S.chip('learned', { x: 860, y: 246 });
    const r = S.box({ x: 130, y: 320, w: 320, h: 150, label: L.r, sub: L.c2, color: C.reader, size: 42 });
    const t = S.box({ x: 480, y: 320, w: 320, h: 150, label: L.t, color: C.thinker, size: 42 });
    const cw = S.box({ x: 830, y: 320, w: 320, h: 150, label: L.cw, color: C.call, size: 42 });
    const st = S.box({ x: 130, y: 580, w: 320, h: 150, label: L.s, color: C.stop, size: 42 });
    const k = S.box({ x: 480, y: 580, w: 320, h: 150, label: L.k, color: C.talker, size: 42 });
    const calc = S.box({ x: 1430, y: 370, w: 370, h: 190, label: L.calc, color: C.calc, size: 46 });
    const hand = S.chip('hand', { x: 1370, y: 585, label: L.c1 });
    const warn = S.note(L.warn, { x: 1370, y: 665, w: 470, size: 32, color: C.warn });
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const aCall = S.arrow(svg, 1152, 395, 1428, 430, { color: C.call, width: 7, head: 22 });
    const aReply = S.path(svg, [[1430, 525], [640, 525], [640, 472]], { color: C.calc, width: 7, head: 22 });
    const tCall = S.text(L.call, { x: 1245, y: 340, w: 160, size: 36, weight: 700, color: C.call });
    const tReply = S.text(L.reply, { x: 1000, y: 540, w: 200, size: 36, weight: 700, color: C.calc });
    S.show(frame, S.capAt(0));
    S.show(fl, S.capAt(0) + 0.3);
    S.pop(fchip, S.capAt(0) + 0.6);
    S.stagger([r, t, cw, st, k], S.capAt(0) + 0.8, 0.35);
    S.show(calc, S.capAt(1));
    S.pop(hand, S.capAt(1) + 0.5);
    S.draw(aCall, S.capAt(1) + 1.0, 0.8);
    S.show(tCall, S.capAt(1) + 1.4);
    S.draw(aReply, S.capAt(1) + 2.4, 1.4);
    S.show(tReply, S.capAt(1) + 3.2);
    S.pulse(t, S.capAt(2));
    S.pulse(st, S.capAt(2) + 0.7);
    S.pulse(k, S.capAt(2) + 1.4);
    S.show(warn, S.capAt(3));
  });

  // s06: five honest-practice rules, one row per sentence.
  Ch.scene('s06', function (S) {
    const L = S.c.labels, N = S.c.nums;
    ['r1', 'r2', 'r3', 'r4', 'r5'].forEach((key, i) => {
      const b = S.box({ x: 160, y: 230 + i * 115, w: 1000, h: 90, label: L[key], color: C.thinker, size: 42 });
      S.show(b, S.capAt(i));
    });
    // rule 4: how many teaching rows exist
    counter(S, { x: 1220, y: 566, w: 300, size: 60, color: C.thinker, to: N.teach, comma: true }, S.capAt(3) + 0.3, 1.4);
    const tl = S.text(L.t4, { x: 1520, y: 586, w: 320, size: 36, weight: 600, color: C.soft });
    S.show(tl, S.capAt(3) + 0.6);
    // rule 5: six pairs, ours over plain (picture only)
    const sq = [];
    for (let i = 0; i < 6; i++) {
      sq.push(S.card({ x: 1220 + i * 100, y: 696, w: 44, h: 60, fill: C.thinker, color: C.thinker, r: 8 }));
      sq.push(S.card({ x: 1268 + i * 100, y: 696, w: 44, h: 60, fill: C.placeholder, color: C.placeholder, r: 8 }));
    }
    S.sweep(sq, S.capAt(4) + 0.4, 3.0);
    S.show(S.chip('placeholder', { x: 1220, y: 768, label: L.pic }), S.capAt(4) + 0.4);
  });

  // s07: where the rules slipped. Three plain cards.
  Ch.scene('s07', function (S) {
    const L = S.c.labels, N = S.c.nums;
    const xs = [100, 700, 1300];
    const cards = xs.map((x) => S.card({ x: x, y: 230, w: 540, h: 520, fill: '#ffffff', color: C.warn, r: 22 }));
    const heads = [L.a, L.b, L.c].map((s, i) => S.text(s, { x: xs[i] + 30, y: 252, w: 480, size: 46, weight: 800, color: C.warn }));
    const tag = S.chip('untested', { x: 100, y: 780, label: L.tag, color: C.warn });
    S.show(tag, S.capAt(0));
    // card A
    S.show(cards[0], S.capAt(0)); S.show(heads[0], S.capAt(0) + 0.2);
    counter(S, { x: 130, y: 330, w: 480, size: 76, color: C.warn, to: N.long, comma: true }, S.capAt(0) + 0.6, 1.8);
    const a1 = S.text(L.a1, { x: 130, y: 425, w: 480, size: 34, color: C.ink });
    S.show(a1, S.capAt(0) + 1.2);
    counter(S, { x: 130, y: 490, w: 480, size: 52, weight: 700, color: C.soft, to: N.pool, comma: true, pre: 'of ' }, S.capAt(0) + 1.6, 1.8);
    const a2 = S.text(L.a2, { x: 130, y: 565, w: 480, size: 34, color: C.ink });
    S.show(a2, S.capAt(0) + 2.2);
    const a3 = S.chip('tested', { x: 130, y: 660, label: L.a3 });
    S.pop(a3, S.capAt(1));
    S.pulse(a3, S.capAt(1) + 0.6);
    // card B
    S.show(cards[1], S.capAt(2)); S.show(heads[1], S.capAt(2) + 0.2);
    const rows = [['b1', N.lo, C.placeholder, 330], ['b2', N.hi, C.warn, 450]];
    const bw = 340, bx = 740;
    rows.forEach((r, i) => {
      const t0 = S.capAt(2) + 0.6 + i * 1.0;
      const lb = S.text(L[r[0]], { x: bx, y: r[3], w: 300, size: 34, color: C.ink });
      const bar = S.bar({ x: bx, y: r[3] + 52, w: bw, h: 40, value: r[1], max: 6, color: r[2] });
      S.show(lb, t0); S.show(bar.track, t0);
      const num = S.text('', { x: bx + bw + 24, y: r[3] + 44, w: 110, size: 44, weight: 800, color: r[2], align: 'left' });
      S.show(num, t0);
      S.grow(bar, t0 + 0.2, 1.2, num, { dec: 1 });
    });
    const lim = S.card({ x: bx + bw * N.lim / 6 - 3, y: 360, w: 6, h: 230, fill: C.ink, color: C.ink, r: 3 });
    const limT = S.text(L.b3 + ' ' + N.lim, { x: bx + bw * N.lim / 6 - 120, y: 600, w: 240, size: 36, weight: 700, color: C.ink, align: 'center' });
    S.show(lim, S.capAt(2) + 3.0); S.show(limT, S.capAt(2) + 3.2);
    // card C
    S.show(cards[2], S.capAt(3)); S.show(heads[2], S.capAt(3) + 0.2);
    const sqs = [];
    for (let i = 0; i < N.copies; i++) sqs.push(S.card({ x: 1330 + i * 78, y: 340, w: 60, h: 60, fill: C.thinker, color: C.thinker, r: 10 }));
    S.sweep(sqs, S.capAt(3) + 0.6, 1.6);
    counter(S, { x: 1330, y: 440, w: 110, size: 76, color: C.thinker, to: N.copies }, S.capAt(3) + 1.2, 0.8);
    const c1 = S.text(L.c1, { x: 1450, y: 462, w: 360, size: 34, color: C.ink });
    S.show(c1, S.capAt(3) + 1.4);
    S.tint(sqs[sqs.length - 1], S.capAt(3) + 3.0, { fill: '#D5D9E0', border: C.placeholder, dur: 0.6 });
    counter(S, { x: 1330, y: 560, w: 110, size: 76, color: C.warn, to: N.lost }, S.capAt(3) + 3.4, 0.6);
    const c2 = S.text(L.c2, { x: 1450, y: 582, w: 360, size: 34, color: C.ink });
    S.show(c2, S.capAt(3) + 3.6);
  });

  // s08: the spend rule, a size ladder that ends in one big planned run.
  Ch.scene('s08', function (S) {
    const L = S.c.labels;
    const keys = ['k1', 'k2', 'k3', 'k4', 'k5'];
    const cols = [C.thinker, C.thinker, C.thinker, C.soft, C.placeholder];
    const bx = keys.map((k, i) => S.box({ x: 120 + i * 350, y: 330, w: 280, h: 140, label: L[k], color: cols[i], size: 52 }));
    bx[4].style.borderStyle = 'dashed';
    const c1 = S.chip('placeholder', { x: 1170, y: 495, label: L.c1 });
    const c2 = S.chip('placeholder', { x: 1520, y: 495, label: L.c2 });
    const wk = S.text(L.wk, { x: 1440, y: 570, w: 400, size: 38, weight: 700, color: C.ink, align: 'center' });
    const mach = S.note(L.mach, { x: 120, y: 650, w: 1250, size: 40, color: C.hand });
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const ar = [0, 1, 2, 3].map((i) => S.arrow(svg, 124 + i * 350 + 280 - 4, 400, 120 + (i + 1) * 350 - 2, 400, { color: C.soft, width: 6, head: 18 }));
    S.pop(bx[4], S.capAt(0));
    S.pulse(bx[4], S.capAt(0) + 0.6);
    S.show(bx[0], S.capAt(1));
    S.draw(ar[0], S.capAt(1) + 0.8, 0.4);
    S.show(bx[1], S.capAt(1) + 1.2);
    S.draw(ar[1], S.capAt(1) + 2.0, 0.4);
    S.show(bx[2], S.capAt(1) + 2.4);
    S.show(mach, S.capAt(1) + 3.2);
    S.draw(ar[2], S.capAt(2), 0.4);
    S.show(bx[3], S.capAt(2) + 0.4);
    S.pop(c1, S.capAt(2) + 1.0);
    S.draw(ar[3], S.capAt(2) + 1.8, 0.4);
    S.pop(c2, S.capAt(3));
    S.show(wk, S.capAt(3) + 0.6);
  });

  // s09: the 90% bar and the plan's own judgement, drawn as two bars (picture only).
  Ch.scene('s09', function (S) {
    const L = S.c.labels;
    const bx = 420, bw = 1200;
    const t1 = S.bar({ x: bx, y: 340, w: bw, h: 60, value: 100 / 3, max: 100, color: C.thinker });
    const t2 = S.bar({ x: bx, y: 520, w: bw, h: 60, value: 9, max: 100, color: C.warn });
    const l1 = S.text(L.b1, { x: bx, y: 285, w: 800, size: 40, weight: 700, color: C.ink });
    const l2 = S.text(L.b2, { x: bx, y: 465, w: 800, size: 40, weight: 700, color: C.ink });
    const mk = S.card({ x: bx + bw * 0.9 - 4, y: 290, w: 8, h: 320, fill: C.ink, color: C.ink, r: 4 });
    const mkT = S.text(L.bar, { x: bx + bw * 0.9 - 120, y: 232, w: 240, size: 40, weight: 800, color: C.ink, align: 'center' });
    const v1 = S.text(L.v1, { x: bx + bw / 3 + 24, y: 346, w: 400, size: 44, weight: 800, color: C.thinker });
    const v2 = S.text(L.v2, { x: bx + bw * 0.09 + 24, y: 526, w: 400, size: 44, weight: 800, color: C.warn });
    const judge = S.chip('placeholder', { x: 120, y: 700, label: L.judge });
    S.show(t1.track, S.capAt(0)); S.show(t2.track, S.capAt(0) + 0.2);
    S.show(mk, S.capAt(0) + 0.6); S.show(mkT, S.capAt(0) + 0.8);
    S.pulse(mkT, S.capAt(0) + 1.6);
    S.show(judge, S.capAt(1));
    S.show(l1, S.capAt(1) + 0.2);
    S.grow(t1, S.capAt(1) + 0.6, 1.6);
    S.show(v1, S.capAt(1) + 2.0);
    S.show(l2, S.capAt(2) + 0.2);
    S.grow(t2, S.capAt(2) + 0.6, 1.0);
    S.show(v2, S.capAt(2) + 1.4);
  });

  // s10: the scorecard, nine squares that change colour with their status.
  Ch.scene('s10', function (S) {
    const L = S.c.labels, rows = S.c.rows;
    const fills = { part: ['#DDF1E6', C.tested], red: ['#FBDCCB', C.warn], none: ['#E6E8EC', C.placeholder] };
    const cards = rows.map((r, i) => S.box({ x: 120 + (i % 3) * 580, y: 230 + Math.floor(i / 3) * 150, w: 540, h: 120, label: r.name, color: C.line, size: 44 }));
    const l1 = S.chip('tested', { x: 120, y: 700, label: L.l1 });
    const l2 = S.chip('hand', { x: 420, y: 700, label: L.l2, color: C.warn });
    const l3 = S.chip('placeholder', { x: 770, y: 700, label: L.l3 });
    const lp = S.chip('placeholder', { x: 120, y: 790, label: L.pic });
    const score = S.text(L.score, { x: 1110, y: 690, w: 730, size: 60, weight: 800, color: C.ink, align: 'right' });
    S.sweep(cards, S.capAt(0), 3.0);
    S.show(lp, S.capAt(0));
    let t = S.capAt(1);
    S.pop(l1, t);
    let u = t + 0.5;
    rows.forEach((r, i) => { if (r.st === 'part') { S.tint(cards[i], u, { fill: fills.part[0], border: fills.part[1], dur: 0.4 }); u += 0.4; } });
    t = S.capAt(2);
    S.pop(l2, t);
    rows.forEach((r, i) => { if (r.st === 'red') S.tint(cards[i], t + 0.5, { fill: fills.red[0], border: fills.red[1], dur: 0.4 }); });
    S.pop(l3, t + 1.8);
    u = t + 2.3;
    rows.forEach((r, i) => { if (r.st === 'none') { S.tint(cards[i], u, { fill: fills.none[0], border: fills.none[1], dur: 0.4 }); u += 0.5; } });
    S.pop(score, S.capAt(3));
  });

  // s11: outside opinions. A hard question goes to two reviewers, the answers are checked against the code.
  Ch.scene('s11', function (S) {
    const L = S.c.labels;
    const q = S.box({ x: 120, y: 380, w: 400, h: 160, label: L.q, color: C.warn, size: 44 });
    const a = S.box({ x: 700, y: 250, w: 520, h: 140, label: L.a, color: C.learned, size: 38 });
    const b = S.box({ x: 700, y: 470, w: 520, h: 140, label: L.b, color: C.placeholder, size: 38 });
    const chk = S.box({ x: 1400, y: 360, w: 400, h: 180, label: L.chk, color: C.calc, size: 40 });
    const chips = [S.chip('tested', { x: 700, y: 640, label: L.t1 }), S.chip('learned', { x: 870, y: 640, label: L.t2 }), S.chip('untested', { x: 1110, y: 640, label: L.t3 })];
    const note = S.text(L.c1, { x: 120, y: 740, w: 900, size: 36, color: C.soft });
    const svg = S.svg({ x: 0, y: 0, w: 1920, h: 1080 });
    const a1 = S.arrow(svg, 524, 440, 696, 335, { color: C.soft, width: 6, head: 20 });
    const a2 = S.arrow(svg, 524, 480, 696, 545, { color: C.soft, width: 6, head: 20 });
    const a3 = S.arrow(svg, 1224, 330, 1396, 420, { color: C.soft, width: 6, head: 20 });
    const a4 = S.arrow(svg, 1224, 550, 1396, 480, { color: C.soft, width: 6, head: 20 });
    S.show(q, S.capAt(0));
    S.show(note, S.capAt(0) + 0.6);
    S.draw(a1, S.capAt(0) + 1.4, 0.6); S.draw(a2, S.capAt(0) + 1.4, 0.6);
    S.show(a, S.capAt(0) + 2.0); S.show(b, S.capAt(0) + 2.3);
    S.stagger(chips, S.capAt(1), 0.5);
    S.draw(a3, S.capAt(2), 0.6); S.draw(a4, S.capAt(2) + 0.3, 0.6);
    S.show(chk, S.capAt(2) + 0.8);
    S.pulse(chk, S.capAt(2) + 1.6);
  });

  // s12: recap, three rows.
  Ch.scene('s12', function (S) {
    const L = S.c.labels;
    const cols = [C.thinker, C.thinker, C.warn];
    [1, 2, 3].forEach((n, i) => {
      const y = 250 + i * 190;
      const card = S.card({ x: 120, y: y, w: 1680, h: 150, fill: '#ffffff', color: cols[i], r: 22 });
      const num = S.text(L['n' + n], { x: 150, y: y + 8, w: 110, size: 100, weight: 800, color: cols[i], align: 'center' });
      const w = S.text(L['w' + n], { x: 300, y: y + 14, w: 700, size: 58, weight: 800, color: C.ink });
      const p = S.text(L['p' + n], { x: 300, y: y + 84, w: 1440, size: 38, color: C.soft });
      S.show(card, S.capAt(i));
      S.show(num, S.capAt(i) + 0.2);
      S.show(w, S.capAt(i) + 0.4);
      S.show(p, S.capAt(i) + 0.7);
    });
  });
});
