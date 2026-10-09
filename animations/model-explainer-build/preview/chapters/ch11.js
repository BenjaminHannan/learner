Kit.chapter('ch11', function (Ch) {
  const C = Kit.C;
  const TINT = '#FFF1E8';

  // ---- local helpers ----
  // reveal one row of an S.hbars object (label, track, counting value, growing bar)
  function showRow(S, hb, i, t, dur) {
    const r = hb.rows[i];
    S.show(r.lab, t, { dur: 0.4 }); S.show(r.track, t, { dur: 0.4 }); S.show(r.val, t + 0.2, { dur: 0.3 });
    S.grow(r.b, t + 0.3, dur, r.val, { dec: r.it.dec == null ? 1 : r.it.dec, suf: r.it.suf || '', comma: true });
    return t + 0.3 + dur;
  }
  // a short bar with end caps (range of likely error) centred on y
  function whisker(S, xa, xb, y, t) {
    const parts = [
      S.card({ x: xa, y: y - 3, w: xb - xa, h: 6, fill: C.ink, color: C.ink, r: 3 }),
      S.card({ x: xa - 2, y: y - 13, w: 4, h: 26, fill: C.ink, color: C.ink, r: 2 }),
      S.card({ x: xb - 2, y: y - 13, w: 4, h: 26, fill: C.ink, color: C.ink, r: 2 }),
    ];
    parts.forEach((p) => S.show(p, t, { dur: 0.4, y: 0 }));
    return t + 0.4;
  }
  // label, thin track, range card from lo to hi, a dot sliding from zero to v, and a counting value
  function intervalRow(S, o) {
    const ax = o.ax, col = o.col || C.learned;
    const px = (u) => ax.x0 + ((u - ax.min) / (ax.max - ax.min)) * (ax.x1 - ax.x0);
    const lab = S.text(o.label, { x: ax.labX, y: o.y - 24, w: ax.labW, size: 34, weight: 700, align: 'right' });
    const track = S.card({ x: ax.x0, y: o.y - 3, w: ax.x1 - ax.x0, h: 6, fill: C.line, color: C.line, r: 3 });
    const rng = S.card({ x: px(o.lo), y: o.y - 15, w: Math.max(6, px(o.hi) - px(o.lo)), h: 30, fill: col + '33', color: col, r: 15 });
    S.show(lab, o.t, { dur: 0.4 }); S.show(track, o.t, { dur: 0.4 });
    S.show(rng, o.t + 0.2, { dur: 0.5 });
    if (o.v == null) {
      const a = S.text('', { x: px(o.lo) - 150, y: o.y - 22, w: 138, size: 34, weight: 800, align: 'right', color: col });
      const b = S.text('', { x: px(o.hi) + 12, y: o.y - 22, w: 150, size: 34, weight: 800, color: col });
      S.show(a, o.t + 0.5, { dur: 0.3 }); S.show(b, o.t + 0.5, { dur: 0.3 });
      S.count(a, { from: 0, to: o.lo, dec: 2, pre: '+' }, o.t + 0.5, 0.8);
      S.count(b, { from: 0, to: o.hi, dec: 2, pre: '+' }, o.t + 0.5, 0.8);
      return o.t + 1.4;
    }
    const dot = S.card({ x: px(0) - 20, y: o.y - 20, w: 40, h: 40, fill: col, color: col, r: 20 });
    const val = S.text('', { x: px(o.v) - 120, y: o.y - 84, w: 240, size: 44, weight: 800, align: 'center', color: col });
    S.show(dot, o.t + 0.3, { dur: 0.3 });
    S.move(dot, o.t + 0.7, 1.0, { x: px(o.v) - px(0) });
    S.show(val, o.t + 0.7, { dur: 0.3 });
    S.count(val, { from: 0, to: o.v, dec: o.dec == null ? 2 : o.dec, pre: o.v > 0 ? '+' : '' }, o.t + 0.7, 1.0);
    return o.t + 1.9;
  }
  // axis furniture shared by the two number-line scenes: zero line, tick numbers
  function axisBits(S, ax, ticks, y0, y1, yTick, t) {
    const px = (u) => ax.x0 + ((u - ax.min) / (ax.max - ax.min)) * (ax.x1 - ax.x0);
    const zero = S.card({ x: px(0) - 2, y: y0, w: 4, h: y1 - y0, fill: C.ink, color: C.ink, r: 2 });
    S.show(zero, t, { dur: 0.5, y: 0 });
    ticks.forEach((tv) => {
      const tx = S.text(String(tv), { x: px(tv) - 40, y: yTick, w: 80, size: 32, weight: 700, align: 'center', color: C.soft });
      S.show(tx, t + 0.2, { dur: 0.4, y: 0 });
    });
  }

  // s01: where we are. Five-part map with nothing lit; sleep sits outside it as day -> night.
  Ch.scene('s01', function (S) {
    const c = S.c, L = c.L;
    const m = S.modelMap({ x: 100, y: 205, w: 1720, h: 190 });
    S.stagger([m.parts.reader, m.parts.thinker, m.parts.calc, m.parts.stop, m.parts.talker], S.at(0.04), 0.2);
    m.arrows.forEach((a, i) => S.draw(a, S.at(0.1) + i * 0.12, 0.3));
    const day = S.box({ x: 120, y: 540, w: 520, h: 150, label: L.day, color: C.soft, size: 44 });
    const night = S.box({ x: 860, y: 540, w: 520, h: 150, label: L.night, color: C.learned, fill: '#EEF3FF', size: 44 });
    const svg = S.svg();
    const arr = S.arrow(svg, 650, 615, 850, 615, { color: C.soft, width: 6 });
    const mA = S.svgEl(svg, 'circle', { cx: 1120, cy: 480, r: 40, fill: C.learned });
    const mB = S.svgEl(svg, 'circle', { cx: 1140, cy: 466, r: 34, fill: C.bg });
    const chip = S.chip('tested', { x: 1440, y: 545, label: L.chip });
    const note = S.note(L.note, { x: 1440, y: 615, w: 400, color: C.warn, size: 30 });
    S.show(day, S.capAt(1));
    S.draw(arr, S.capAt(1) + 0.7, 0.7);
    S.tl.to([mA, mB], { autoAlpha: 1, duration: 0.5 }, S.capAt(1) + 1.2);
    S.show(night, S.capAt(1) + 1.5);
    S.show(chip, S.capAt(2));
    S.show(note, S.capAt(2) + 0.5);
    S.pulse(night, S.capAt(2) + 1.5);
  });

  // s02: a made-up puzzle. Three rules are tried; only the one that fits all examples answers.
  Ch.scene('s02', function (S) {
    const c = S.c, L = c.L;
    const head = S.text(L.exHead, { x: 100, y: 210, w: 360, size: 34, weight: 700, color: C.soft });
    const grp = S.card({ x: 100, y: 255, w: 360, h: 380 });
    const ex = L.ex.map((s, i) => S.box({ x: 130, y: 280 + i * 115, w: 300, h: 95, label: s, color: C.soft, size: 48 }));
    const ys = [270, 410, 550];
    const rules = L.rules.map((s, i) => S.box({ x: 560, y: ys[i], w: 380, h: 110, label: s, color: C.learned, size: 50 }));
    const svg = S.svg();
    const arrs = ys.map((y) => S.arrow(svg, 470, y + 55, 552, y + 55, { color: C.soft, width: 5, head: 18 }));
    const fits = L.fits.map((f, i) => S.text('', { x: 970, y: ys[i] + 22, w: 300, size: 58, weight: 800, color: C.ink }));
    const tag = S.chip('placeholder', { x: 100, y: 700, label: L.tag });
    const q = S.box({ x: 1400, y: 420, w: 380, h: 120, label: L.query, color: C.soft, size: 58 });
    const out = S.arrow(svg, 1290, 465, 1392, 480, { color: C.tested, width: 6 });
    const ans = S.text(L.answer, { x: 1400, y: 565, w: 380, size: 84, weight: 800, align: 'center', color: C.tested });
    S.show(head, S.capAt(0)); S.show(grp, S.capAt(0)); S.stagger(ex, S.capAt(0) + 0.3, 0.4);
    S.show(tag, S.capAt(0) + 2.0);
    S.stagger(rules, S.capAt(1) + 0.2, 0.5);
    arrs.forEach((a, i) => S.draw(a, S.capAt(1) + 0.2 + i * 0.5, 0.4));
    fits.forEach((f, i) => {
      const t = S.capAt(1) + 2.3 + i * 1.1;
      S.show(f, t, { dur: 0.3 });
      S.count(f, { from: 0, to: L.fits[i], suf: L.fitSuf }, t, 0.8);
    });
    // third caption: the two rules that fit once are dimmed, the middle one wins
    const t3 = S.capAt(2);
    [0, 2].forEach((i) => { S.tl.to([rules[i], fits[i]], { autoAlpha: 0.35, duration: 0.5 }, t3); });
    S.tint(rules[1], t3, { border: C.tested });
    S.pulse(fits[1], t3 + 0.3);
    S.show(q, t3 + 1.0);
    S.draw(out, t3 + 1.6, 0.5);
    S.pop(ans, t3 + 2.2);
  });

  // s03: what the test really is: five kinds, 65 rules, read which rule then answer first try.
  Ch.scene('s03', function (S) {
    const c = S.c, L = c.L;
    const kinds = L.kinds.map((k, i) => S.box({ x: 100 + i * 350, y: 215, w: 320, h: 110, label: k, color: C.soft, size: 40 }));
    const num = S.text('', { x: 100, y: 350, w: 240, size: 110, weight: 800, color: C.learned });
    const nl = S.text(L.nLabel, { x: 350, y: 395, w: 380, size: 40, color: C.soft });
    const tag = S.chip('placeholder', { x: 1330, y: 395, label: L.tag });
    const b1 = S.box({ x: 100, y: 560, w: 460, h: 130, label: L.ex, color: C.soft, size: 40 });
    const b2 = S.box({ x: 700, y: 560, w: 460, h: 130, label: L.which, color: C.learned, size: 40 });
    const b3 = S.box({ x: 1300, y: 560, w: 460, h: 130, label: L.ans, color: C.tested, size: 40 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 566, 625, 694, 625, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 1166, 625, 1294, 625, { color: C.soft, width: 6 });
    const up = S.arrow(svg, 930, 552, 930, 334, { color: C.learned, width: 6 });
    const pic = S.chip('placeholder', { x: 100, y: 730, label: L.pic });
    S.stagger(kinds, S.capAt(0) + 0.3, 0.35);
    S.show(num, S.capAt(0) + 2.2); S.count(num, { from: 0, to: L.n }, S.capAt(0) + 2.2, 1.6);
    S.show(nl, S.capAt(0) + 2.6);
    S.show(tag, S.capAt(0) + 3.6);
    S.show(b1, S.capAt(1) + 0.2);
    S.draw(a1, S.capAt(1) + 0.9, 0.5);
    S.show(b2, S.capAt(1) + 1.4);
    S.draw(a2, S.capAt(1) + 2.2, 0.5);
    S.show(b3, S.capAt(1) + 2.7);
    S.show(pic, S.capAt(1) + 3.2);
    S.draw(up, S.capAt(2) + 0.3, 0.7);
    S.pulse(kinds[1], S.capAt(2) + 1.1);
    S.pulse(b2, S.capAt(2) + 1.1);
    S.pulse(tag, S.capAt(3) + 0.5);
  });

  // s04: start 41.6, old sleep 71.3 with its range, 558 to 610 updates, score by kind.
  Ch.scene('s04', function (S) {
    const c = S.c, L = c.L;
    const hb = S.hbars({ x: 100, y: 225, w: 700, labelW: 230, rowH: 70, gap: 34, max: 100, dec: 1, labelSize: 38, valueSize: 48, valueW: 200,
      items: [{ label: L.start, value: L.startVal, color: C.placeholder, dec: 1 }, { label: L.old, value: L.oldVal, color: C.learned, dec: 1 }] });
    const px = (v) => 330 + (v / 100) * 700;
    const rng = S.text(L.range, { x: 1180, y: 344, w: 160, size: 36, weight: 700, color: C.soft });
    const big = S.text('', { x: 1380, y: 205, w: 440, size: 130, weight: 800, color: C.learned });
    const to = S.text(L.stepsTo, { x: 1380, y: 355, w: 440, size: 56, weight: 700, color: C.soft });
    const sl = S.text(L.stepsLabel, { x: 1380, y: 430, w: 440, size: 34, color: C.soft });
    const kh = S.text(L.kindHead, { x: 100, y: 520, w: 1100, size: 38, weight: 700, color: C.soft });
    const cards = L.kinds.map((k, i) => {
      const x = 100 + i * 350;
      const card = S.card({ x, y: 575, w: 320, h: 190 });
      const nm = S.text(k, { x: x + 10, y: 595, w: 300, size: 38, weight: 700, align: 'center' });
      const v = S.text('', { x: x + 10, y: 665, w: 300, size: 76, weight: 800, align: 'center', color: C.learned });
      return { card, nm, v };
    });
    showRow(S, hb, 0, S.capAt(0) + 0.3, 1.4);
    let t = showRow(S, hb, 1, S.capAt(1) + 0.2, 1.6);
    whisker(S, px(L.oldVal - 2.5), px(L.oldVal + 2.5), 225 + 104 + 35, t);
    S.show(rng, t);
    S.show(big, S.capAt(2) + 0.2); S.count(big, { from: 0, to: L.steps, comma: true }, S.capAt(2) + 0.2, 1.6);
    S.show(to, S.capAt(2) + 1.8); S.show(sl, S.capAt(2) + 2.4);
    S.show(kh, S.capAt(3));
    cards.forEach((k, i) => {
      const u = S.capAt(3) + 0.5 + i * 0.5;
      S.show(k.card, u); S.show(k.nm, u + 0.1); S.show(k.v, u + 0.2);
      S.count(k.v, { from: 0, to: L.kindVals[i], dec: 1 }, u + 0.2, 1.0);
    });
  });

  // s05: one night: tries + chain search -> 1,024 rows (dream half, skills half) -> 256 updates with a check every 32.
  Ch.scene('s05', function (S) {
    const c = S.c, L = c.L;
    const b1 = S.box({ x: 100, y: 210, w: 420, h: 120, label: L.tries, color: C.learned, size: 40 });
    const b2 = S.box({ x: 620, y: 210, w: 420, h: 120, label: L.search, color: C.soft, size: 40 });
    const b3 = S.box({ x: 1140, y: 210, w: 360, h: 120, label: L.rows, color: C.soft, size: 40 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 526, 270, 614, 270, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 1046, 270, 1134, 270, { color: C.soft, width: 6 });
    const cells = [];
    for (let i = 0; i < 20; i++) cells.push(S.card({ x: 320 + i * 64 + (i >= 10 ? 40 : 0), y: 400, w: 56, h: 56, r: 10, fill: i < 10 ? C.learned : C.placeholder, color: i < 10 ? C.learned : C.placeholder }));
    const dl = S.text(L.dreams, { x: 320, y: 470, w: 632, size: 38, weight: 700, align: 'center', color: C.learned });
    const sl = S.text(L.skills, { x: 1000, y: 470, w: 632, size: 38, weight: 700, align: 'center', color: C.soft });
    const pic = S.chip('placeholder', { x: 100, y: 470, label: L.pic });
    const cnt = S.text('', { x: 100, y: 632, w: 200, size: 56, weight: 800, align: 'right', color: C.learned });
    const bar = S.bar({ x: 320, y: 640, w: 1280, h: 44, value: L.total, max: L.total, color: C.learned });
    const ul = S.text(L.updates, { x: 1620, y: 646, w: 220, size: 34, color: C.soft });
    const flags = [];
    for (let k = 1; k <= 8; k++) flags.push(S.card({ x: 320 + ((32 * k) / 256) * 1280 - (k === 8 ? 6 : 3), y: 626, w: 6, h: 72, r: 3, fill: C.ink, color: C.ink }));
    const ck = S.text(L.check, { x: 320, y: 706, w: 400, size: 34, color: C.soft });
    const keep = S.box({ x: 1180, y: 740, w: 420, h: 90, label: L.keep, color: C.tested, size: 36 });
    S.show(b1, S.capAt(0) + 0.2); S.draw(a1, S.capAt(0) + 0.9, 0.5); S.show(b2, S.capAt(0) + 1.4);
    S.draw(a2, S.capAt(0) + 2.1, 0.5); S.show(b3, S.capAt(1) + 0.2);
    S.sweep(cells, S.capAt(2), 2.4);
    S.show(dl, S.capAt(2) + 0.3); S.show(sl, S.capAt(2) + 1.6); S.show(pic, S.capAt(2) + 2.2);
    S.show(bar.track, S.capAt(1) + 1.5, { dur: 0.4 }); S.show(cnt, S.capAt(1) + 1.6, { dur: 0.3 }); S.show(ul, S.capAt(1) + 1.6, { dur: 0.3 });
    S.grow(bar, S.capAt(1) + 2.0, 6.0, cnt, { from: 0, dec: 0 });
    S.stagger(flags, S.capAt(3), 0.12, { dur: 0.3 });
    S.show(ck, S.capAt(3) + 0.2);
    flags.forEach((f, i) => S.pulse(f, S.capAt(3) + 1.6 + i * 0.5, { scale: 1.6 }));
    S.show(keep, S.capAt(3) + 5.8);
  });

  // s06: six copies and their average.
  Ch.scene('s06', function (S) {
    const c = S.c, L = c.L;
    const hb = S.hbars({ x: 100, y: 215, w: 900, labelW: 230, rowH: 52, gap: 18, max: 100, dec: 1, labelSize: 38, valueSize: 44, valueW: 200,
      items: L.labels.map((l, i) => ({ label: l, value: L.values[i], color: C.tested, dec: 1 })) });
    const av = S.hbars({ x: 100, y: 655, w: 900, labelW: 230, rowH: 52, gap: 18, max: 100, dec: 1, labelSize: 38, valueSize: 44, valueW: 200,
      items: [{ label: L.avg, value: L.avgVal, color: C.tested, dec: 1 }] });
    const chip = S.chip('tested', { x: 1380, y: 210, label: L.chip });
    const note = S.note(L.note, { x: 1400, y: 340, w: 420, color: C.warn, size: 30 });
    S.show(chip, S.capAt(0));
    L.labels.forEach((l, i) => showRow(S, hb, i, S.capAt(0) + 0.4 + i * 0.5, 1.2));
    showRow(S, av, 0, S.capAt(1) + 0.3, 1.5);
    const t = S.capAt(2);
    S.tint(hb.rows[2].fill, t, { fill: C.warn });
    S.tint(hb.rows[2].val, t, { color: C.warn });
    S.show(note, t + 0.3);
    S.pulse(hb.rows[2].track, t + 0.6, { scale: 1.03 });
  });

  // s07: new sleep next to old sleep: scores, updates, and the not-paired stamp.
  Ch.scene('s07', function (S) {
    const c = S.c, L = c.L;
    const h1 = S.text(L.scoreHead, { x: 100, y: 210, w: 1000, size: 34, weight: 700, color: C.soft });
    const sc = S.hbars({ x: 100, y: 255, w: 800, labelW: 220, rowH: 62, gap: 22, max: 100, dec: 1, labelSize: 36, valueSize: 46, valueW: 200,
      items: [{ label: L.old, value: L.oldVal, color: C.learned, dec: 1 }, { label: L.new, value: L.newVal, color: C.tested, dec: 1 }] });
    const px = (v) => 320 + (v / 100) * 800;
    const rg = S.text(L.range, { x: 1260, y: 268, w: 160, size: 34, weight: 700, color: C.soft });
    const h2 = S.text(L.stepsHead, { x: 100, y: 450, w: 1000, size: 34, weight: 700, color: C.soft });
    const st = S.hbars({ x: 100, y: 495, w: 800, labelW: 220, rowH: 62, gap: 22, max: 610, dec: 0, labelSize: 36, valueSize: 46, valueW: 200,
      items: [{ label: L.old, value: L.oldStepsVal, color: C.learned, dec: 0 }, { label: L.new, value: L.newSteps, color: C.tested, dec: 0 }] });
    const ext = S.card({ x: 320 + (L.oldStepsVal / 610) * 800, y: 495, w: 800 - (L.oldStepsVal / 610) * 800, h: 62, fill: C.learned + '44', color: C.learned + '44', r: 6 });
    const to = S.text(L.oldSteps, { x: 1250, y: 509, w: 200, size: 36, weight: 700, color: C.soft });
    const hx = 320 + (279 / 610) * 800;
    const svg = S.svg();
    const mk = S.svgEl(svg, 'line', { x1: hx, y1: 485, x2: hx, y2: 655, stroke: C.ink, 'stroke-width': 4, 'stroke-dasharray': '10 8' });
    const hl = S.text(L.half, { x: hx - 130, y: 660, w: 260, size: 32, weight: 700, align: 'center' });
    const stamp = S.box({ x: 100, y: 735, w: 760, h: 90, label: L.stamp, color: C.warn, fill: TINT, size: 44 });
    S.show(h1, S.capAt(0));
    showRow(S, sc, 0, S.capAt(0) + 0.4, 1.4);
    const t = showRow(S, sc, 1, S.capAt(0) + 1.3, 1.4);
    whisker(S, px(L.oldVal - 2.5), px(L.oldVal + 2.5), 255 + 31, S.capAt(0) + 2.7);
    S.show(rg, S.capAt(0) + 2.9);
    S.show(h2, S.capAt(1));
    showRow(S, st, 0, S.capAt(1) + 0.4, 1.6);
    S.show(ext, S.capAt(1) + 1.8, { dur: 0.5 }); S.show(to, S.capAt(1) + 2.0);
    showRow(S, st, 1, S.capAt(1) + 2.6, 1.2);
    S.tl.to(mk, { autoAlpha: 1, duration: 0.5 }, S.capAt(1) + 4.0);
    S.show(hl, S.capAt(1) + 4.2);
    S.pop(stamp, S.capAt(2));
    S.pulse(stamp, S.capAt(2) + 1.0);
  });

  // s08: the pass-mark table, one row per beat.
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.L;
    const rows = L.rows.map((r, i) => {
      const y = 215 + i * 118;
      const pass = r.v === 'pass';
      const card = S.card({ x: 100, y, w: 1720, h: 100, color: pass ? C.tested : C.placeholder });
      const nm = S.text(r.name, { x: 140, y: y + 28, w: 480, size: 42, weight: 700 });
      const rs = S.text(r.res, { x: 640, y: y + 30, w: 800, size: 40, color: C.ink });
      const chip = S.chip(pass ? 'tested' : 'placeholder', { x: 1500, y: y + 26, label: r.v });
      return { card, nm, rs, chip };
    });
    const when = [S.capAt(0), S.capAt(1), S.capAt(2), S.capAt(2) + 3.2, S.capAt(3)];
    rows.forEach((r, i) => {
      const t = when[i];
      S.show(r.card, t); S.show(r.nm, t + 0.15); S.show(r.rs, t + 0.3); S.pop(r.chip, t + 0.9);
    });
    S.pulse(rows[4].card, S.capAt(3) + 1.8, { scale: 1.02 });
  });

  // s09: old skills on a number line: each copy band, pooled sleep, control, and the difference.
  Ch.scene('s09', function (S) {
    const c = S.c, L = c.L;
    const ax = { x0: 600, x1: 1700, min: -2.5, max: 3, labX: 80, labW: 490 };
    const chip = S.chip('tested', { x: 1480, y: 205, label: L.chip });
    axisBits(S, ax, L.ticks, 250, 730, 740, S.capAt(0));
    const ah = S.text(L.axisHead, { x: 600, y: 782, w: 1100, size: 32, color: C.soft, align: 'center' });
    S.show(chip, S.capAt(0) + 0.3); S.show(ah, S.capAt(0) + 0.4);
    intervalRow(S, { label: L.copyRow.label, v: null, lo: L.copyRow.lo, hi: L.copyRow.hi, ax, y: 300, t: S.capAt(0) + 1.0 });
    const cols = [C.learned, C.soft, C.warn];
    L.rows.forEach((r, i) => {
      intervalRow(S, { label: r.label, v: r.v, lo: r.lo, hi: r.hi, ax, y: 425 + i * 125, t: S.capAt(i + 1) + 0.2, col: cols[i] });
    });
  });

  // s10: re-read rows (same cards, looped) against fresh dreams (a new card each time), then two interval rows.
  Ch.scene('s10', function (S) {
    const c = S.c, L = c.L;
    const lr = S.text(L.reread, { x: 100, y: 210, w: 600, size: 38, weight: 700, color: C.soft });
    const same = [0, 1, 2, 3].map((i) => S.box({ x: 100 + i * 190, y: 265, w: 170, h: 110, label: L.same, color: C.soft, size: 44 }));
    const lf = S.text(L.fresh, { x: 1000, y: 210, w: 400, size: 38, weight: 700, color: C.learned });
    const diff = L.diff.map((s, i) => S.box({ x: 1000 + i * 190, y: 265, w: 170, h: 110, label: s, color: C.learned, size: 44 }));
    const svg = S.svg();
    const loop = S.curve(svg, 755, 384, 185, 384, { color: C.soft, bend: 70, width: 5 });
    const pic = S.chip('placeholder', { x: 1480, y: 205, label: L.pic });
    const hd = S.text(L.head, { x: 100, y: 500, w: 1200, size: 34, weight: 700, color: C.soft });
    const chip = S.chip('tested', { x: 1400, y: 495, label: L.chip });
    const ax = { x0: 560, x1: 1600, min: 0, max: 12, labX: 80, labW: 450 };
    S.show(pic, S.capAt(0) + 0.2);
    S.show(lr, S.capAt(0) + 0.4); S.stagger(same, S.capAt(0) + 0.8, 0.4); S.draw(loop, S.capAt(0) + 2.8, 0.9);
    S.show(lf, S.capAt(0) + 6.0); S.stagger(diff, S.capAt(0) + 6.4, 0.5);
    S.show(hd, S.capAt(1));
    axisBits(S, ax, L.ticks, 560, 780, 790, S.capAt(1) + 0.3);
    L.rows.forEach((r, i) => {
      intervalRow(S, { label: r.label, v: r.v, lo: r.lo, hi: r.hi, ax, y: 640 + i * 105, t: S.capAt(1) + 1.0 + i * 2.0, col: C.learned, dec: 1 });
    });
    S.show(chip, S.capAt(2));
  });

  // s11: four careful cards, one per beat.
  Ch.scene('s11', function (S) {
    const c = S.c, L = c.L;
    const pos = [[100, 215], [980, 215], [100, 475], [980, 475]];
    const cards = L.cards.map((s, i) => ({
      box: S.box({ x: pos[i][0], y: pos[i][1], w: 840, h: 220, label: s, color: C.warn, fill: TINT, size: 42 }),
      chip: S.chip('warn', { x: pos[i][0] + 22, y: pos[i][1] + 16, label: L.tag, size: 28 }),
    }));
    const sub = S.text(L.sub4, { x: 980, y: 713, w: 840, size: 38, weight: 700, color: C.warn });
    cards.forEach((k, i) => { S.show(k.box, S.capAt(i)); S.pop(k.chip, S.capAt(i) + 0.5); });
    S.show(sub, S.capAt(4));
    S.pulse(cards[3].box, S.capAt(4) + 0.5, { scale: 1.03 });
  });

  // s12: SC failed the harm mark, SCL passed on two copies; everything on hold.
  Ch.scene('s12', function (S) {
    const c = S.c, L = c.L;
    const sc = S.box({ x: 100, y: 215, w: 840, h: 220, label: L.sc, sub: L.scRes, color: C.warn, fill: TINT, size: 70, subSize: 42 });
    const scl = S.box({ x: 980, y: 215, w: 840, h: 220, label: L.scl, sub: L.sclRes, color: C.tested, fill: '#EAF7F0', size: 70, subSize: 38 });
    const c1 = S.chip('tested', { x: 100, y: 450 });
    const c2 = S.chip('tested', { x: 980, y: 450 });
    const hold = S.card({ x: 100, y: 520, w: 1720, h: 300, color: C.placeholder });
    const hh = S.text(L.holdHead, { x: 140, y: 545, w: 600, size: 46, weight: 800, color: C.soft });
    const hc = S.chip('placeholder', { x: 1500, y: 548, label: L.chip });
    const items = L.hold.map((s, i) => S.box({ x: 140 + i * 410, y: 650, w: 390, h: 110, label: s, color: C.placeholder, fill: '#F3F1EC', size: 36 }));
    S.show(sc, S.capAt(0) + 0.2); S.show(c1, S.capAt(0) + 0.9);
    S.pulse(sc, S.capAt(1) + 0.5, { scale: 1.03 });
    S.show(scl, S.capAt(1) + 4.0); S.show(c2, S.capAt(1) + 4.7);
    S.show(hold, S.capAt(2)); S.show(hh, S.capAt(2) + 0.3); S.show(hc, S.capAt(2) + 0.6);
    S.stagger(items, S.capAt(2) + 1.0, 0.6);
  });

  // s13: a different test (Oct 7): six bars, pass markers set before the run.
  Ch.scene('s13', function (S) {
    const c = S.c, L = c.L;
    const hb = S.hbars({ x: 100, y: 215, w: 1000, labelW: 300, rowH: 58, gap: 20, max: 40, dec: 1, labelSize: 36, valueSize: 44, valueW: 260,
      items: L.rows.map((r, i) => ({ label: r.label, value: r.value, color: i % 3 === 2 ? C.tested : C.placeholder, dec: 1 })) });
    const svg = S.svg();
    const xa = 400 + (15.4 / 40) * 1000, xb = 400 + (16.2 / 40) * 1000;
    const ma = S.svgEl(svg, 'line', { x1: xa, y1: 210, x2: xa, y2: 429, stroke: C.ink, 'stroke-width': 4, 'stroke-dasharray': '10 8' });
    const mb = S.svgEl(svg, 'line', { x1: xb, y1: 444, x2: xb, y2: 683, stroke: C.ink, 'stroke-width': 4, 'stroke-dasharray': '10 8' });
    const ln = S.text(L.line, { x: 535, y: 692, w: 520, size: 32, weight: 700, align: 'center' });
    const bx = S.box({ x: 1180, y: 700, w: 420, h: 90, label: L.box, color: C.warn, fill: TINT, size: 40 });
    const chip = S.chip('tested', { x: 100, y: 712, label: 'tested, ' + L.chip });
    S.show(bx, S.capAt(0) + 0.3);
    S.show(chip, S.capAt(0) + 1.0);
    [0, 1, 3, 4].forEach((r, k) => showRow(S, hb, r, S.capAt(1) + 0.3 + k * 0.6, 1.2));
    S.tl.to([ma, mb], { autoAlpha: 1, duration: 0.5 }, S.capAt(2) + 0.1);
    S.show(ln, S.capAt(2) + 0.4);
    showRow(S, hb, 2, S.capAt(2) + 1.4, 1.4);
    showRow(S, hb, 5, S.capAt(2) + 2.6, 1.4);
    S.pulse(bx, S.capAt(3) + 0.4);
  });

  // s14: recap.
  Ch.scene('s14', function (S) {
    const c = S.c, L = c.L;
    const cols = [C.tested, C.tested, C.placeholder];
    L.cards.forEach((txt, i) => {
      const x = 100 + i * 600;
      const b = S.box({ x, y: 225, w: 540, h: 260, label: txt, color: cols[i], size: 50 });
      const ch = L.chips[i];
      const chip = S.chip(ch === 'tested' ? 'tested' : 'placeholder', { x: x + 20, y: 505, label: ch });
      S.show(b, S.capAt(i)); S.pop(chip, S.capAt(i) + 0.6);
    });
    const note = S.note(L.compute, { x: 100, y: 620, w: 1720, color: C.soft, size: 36 });
    S.show(note, S.capAt(2) + 1.5);
  });
});
