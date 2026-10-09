/* ch10: Tests that cannot be gamed.
   Every word and number on screen comes from content/ch10.json (S.c). Code holds only symbols, layout and two tiny local helpers. */
Kit.chapter('ch10', function (Ch) {
  const C = Kit.C;

  // ---------- local helpers ----------
  // Reveal one S.hbars row (label, track, counting value) and grow it. Returns the end time.
  function revealRow(S, r, t, dur) {
    S.show(r.lab, t, { dur: 0.4 });
    S.show(r.track, t, { dur: 0.4 });
    S.show(r.val, t + 0.2, { dur: 0.3 });
    return S.grow(r.b, t + 0.3, dur, r.val, { dec: r.it.dec, suf: r.it.suf || '', comma: true });
  }
  // A thin stack of cards, drawn back to front, every card shifted a little: "a pile of questions". Returns the cards.
  function pile(S, x, y, w, h, n, color) {
    const out = [];
    for (let i = n - 1; i >= 0; i--) out.push(S.card({ x: x + i * 16, y: y - i * 16, w: w, h: h, color: color, r: 14 }));
    return out;
  }
  // A vertical thin line in the svg layer. Returns the element (reveal it with S.show).
  function vline(S, svg, x, y1, y2, color, width, dash) {
    const a = { x1: x, y1: y1, x2: x, y2: y2, stroke: color, 'stroke-width': width || 5, 'stroke-linecap': 'round' };
    if (dash) a['stroke-dasharray'] = dash;
    return S.svgEl(svg, 'line', a);
  }

  // ---------- s01: why a score alone means little ----------
  Ch.scene('s01', function (S) {
    const c = S.c;
    const svg = S.svg();
    const tag = S.chip('placeholder', { x: 1560, y: 205, label: c.illustration });
    S.show(tag, S.at(0.05));
    // practice pile (left)
    const pp = pile(S, 130, 430, 300, 190, 4, C.thinker);
    const plab = S.text(c.labels.practice, { x: 130, y: 640, w: 360, size: 38, weight: 700, color: C.thinker });
    S.sweep(pp, S.capAt(0), 1.2);
    S.show(plab, S.capAt(0) + 0.4);
    // two models of the same size, both fed by the same pile
    const mA = S.box({ x: 780, y: 290, w: 300, h: 150, label: c.labels.model, color: C.thinker, size: 44 });
    const mB = S.box({ x: 780, y: 560, w: 300, h: 150, label: c.labels.model, color: C.placeholder, size: 44 });
    const a1 = S.arrow(svg, 505, 440, 778, 365, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 505, 560, 778, 635, { color: C.soft, width: 6 });
    S.show(mA, S.capAt(0) + 1.2);
    S.draw(a1, S.capAt(0) + 1.6, 0.7);
    S.show(mB, S.capAt(1));
    S.draw(a2, S.capAt(1) + 0.4, 0.7);
    S.pulse(plab, S.capAt(1) + 1.2);
    // exam pile (right) + sealed locks
    const ep = pile(S, 1320, 420, 330, 190, 4, C.tested);
    const elab = S.text(c.labels.exam, { x: 1320, y: 635, w: 480, size: 38, weight: 700, color: C.tested });
    S.sweep(ep, S.capAt(2), 1.0);
    S.show(elab, S.capAt(2) + 0.4);
    const lx = [1100, 1380, 1590], lw = [270, 200, 160];
    const locks = c.locks.map((n, i) => S.box({ x: lx[i], y: 720, w: lw[i], h: 70, label: n, color: C.warn, size: 30 }));
    locks.forEach((b) => { b.querySelector('.lab').classList.add('mono'); });
    S.stagger(locks, S.capAt(2) + 1.0, 0.3);
    const lnote = S.text(c.labels.lock, { x: 1130, y: 795, w: 700, size: 32, color: C.soft });
    S.show(lnote, S.capAt(2) + 1.9);
  });

  // ---------- s02: the two exams ----------
  Ch.scene('s02', function (S) {
    const c = S.c;
    const pn = S.text(c.names.p, { x: 100, y: 215, w: 420, size: 54, weight: 800, mono: true });
    const big = S.text('', { x: 540, y: 205, w: 330, size: 84, weight: 800, color: C.tested, lh: 1 });
    const bigLab = S.text(c.totalLabel, { x: 880, y: 236, w: 360, size: 40, color: C.soft });
    const hb = S.hbars({ x: 100, y: 340, w: 520, labelW: 440, rowH: 56, gap: 22, max: 1400, dec: 0, labelSize: 34, valueSize: 40, valueW: 150,
      items: c.kinds.map((k, i) => ({ label: k.label, value: k.value, color: i === 0 ? C.tested : C.thinker })) });
    S.show(pn, S.capAt(0));
    S.show(big, S.capAt(0) + 0.2); S.show(bigLab, S.capAt(0) + 0.3);
    S.count(big, { from: 0, to: c.total, comma: true }, S.capAt(0) + 0.5, 1.6);
    hb.reveal(S.capAt(0) + 1.4, 0.4, 1.2);
    // chain-5 card
    const card = S.card({ x: 1290, y: 215, w: 530, h: 270 });
    const cn = S.text(c.names.c, { x: 1320, y: 235, w: 470, size: 54, weight: 800, mono: true });
    const cb = S.text('', { x: 1320, y: 310, w: 470, size: 110, weight: 800, color: C.tested, lh: 1 });
    const cl = S.text(c.chain.label, { x: 1320, y: 430, w: 470, size: 38, color: C.soft });
    S.show(card, S.capAt(1)); S.show(cn, S.capAt(1) + 0.2); S.show(cb, S.capAt(1) + 0.3); S.show(cl, S.capAt(1) + 0.5);
    S.count(cb, { from: 0, to: c.chain.value, comma: true }, S.capAt(1) + 0.5, 1.4);
    // families card
    const card2 = S.card({ x: 1290, y: 540, w: 530, h: 250 });
    const fb = S.text('', { x: 1320, y: 570, w: 470, size: 120, weight: 800, color: C.thinker, lh: 1 });
    const fl = S.text(c.families.label, { x: 1320, y: 710, w: 470, size: 38, color: C.soft });
    S.show(card2, S.capAt(2)); S.show(fb, S.capAt(2) + 0.2); S.show(fl, S.capAt(2) + 0.4);
    S.count(fb, { from: 0, to: c.families.n }, S.capAt(2) + 0.4, 1.2);
  });

  // ---------- s03: marks in a sealed envelope ----------
  Ch.scene('s03', function (S) {
    const c = S.c;
    const svg = S.svg();
    const xs = [120, 720, 1320];
    const steps = c.steps.map((t, i) => S.box({ x: xs[i], y: 225, w: 480, h: 110, label: t, color: i === 0 ? C.tested : (i === 1 ? C.thinker : C.soft), size: 42 }));
    const arrs = [S.arrow(svg, 604, 280, 716, 280, { color: C.soft, width: 6 }), S.arrow(svg, 1204, 280, 1316, 280, { color: C.soft, width: 6 })];
    S.show(S.chip('placeholder', { x: 1560, y: 580, label: c.illustration }), S.at(0.05));
    // the envelope with three things inside
    const env = S.card({ x: 120, y: 410, w: 480, h: 340, color: C.tested, r: 20 });
    const inner = c.env.map((t, i) => S.box({ x: 150, y: 435 + i * 100, w: 420, h: 84, label: t, color: C.line, size: 38 }));
    S.show(steps[0], S.capAt(0));
    S.show(env, S.capAt(0) + 0.3);
    S.stagger(inner, S.capAt(0) + 0.6, 0.5);
    // run: a bar fills under step two
    S.draw(arrs[0], S.capAt(1), 0.5);
    S.show(steps[1], S.capAt(1) + 0.3);
    const bar = S.bar({ x: 720, y: 420, w: 480, h: 44, value: 100, color: C.thinker });
    S.show(bar.track, S.capAt(1) + 0.6);
    S.grow(bar, S.capAt(1) + 0.8, 2.0);
    // read: the sealed envelope is opened against the result
    S.draw(arrs[1], S.capAt(2), 0.5);
    S.show(steps[2], S.capAt(2) + 0.3);
    const res = S.card({ x: 1320, y: 410, w: 480, h: 140, color: C.line, r: 20 });
    S.show(res, S.capAt(2) + 0.6);
    const cv = S.curve(svg, 604, 600, 1316, 480, { color: C.tested, bend: 90, width: 6 });
    S.draw(cv, S.capAt(2) + 1.0, 1.0);
    S.pulse(env, S.capAt(2) + 1.2);
  });

  // ---------- s04: a real mark (B3-1) on a number line drawn to scale ----------
  Ch.scene('s04', function (S) {
    const c = S.c;
    const svg = S.svg();
    const xv = (v) => 120 + (v + 1) * 210; // axis from -1 to 7 points, 210 px per point
    const chip = S.chip('untested', { x: 120, y: 205, label: c.chip });
    S.show(chip, S.at(0.05));
    const zc = [C.warn, C.untested, C.tested];
    const zx = [[-1, 1], [1, 3], [3, 7]];
    const zones = c.zones.map((z, i) => S.box({ x: xv(zx[i][0]), y: 330, w: (zx[i][1] - zx[i][0]) * 210 - 6, h: 130, label: z.name, sub: z.range, color: zc[i], size: 36, subSize: 32 }));
    const t1 = vline(S, svg, xv(1) - 3, 480, 540, C.ink, 5);
    const t3 = vline(S, svg, xv(3) - 3, 480, 540, C.ink, 5);
    const axis = S.text(c.axis, { x: 120, y: 700, w: 1680, size: 36, color: C.soft, align: 'center' });
    // prediction bracket from 3 to 6
    const pb = S.card({ x: xv(3), y: 580, w: 3 * 210 - 6, h: 18, fill: C.thinker, color: C.thinker, r: 9 });
    const pl = S.text(c.prediction, { x: xv(3), y: 615, w: 3 * 210, size: 38, weight: 700, color: C.thinker, align: 'center' });
    S.show(zones[2], S.capAt(0)); S.show(t3, S.capAt(0) + 0.5); S.show(axis, S.capAt(0) + 0.6);
    S.show(zones[0], S.capAt(1)); S.show(t1, S.capAt(1) + 0.3); S.show(zones[1], S.capAt(1) + 0.5);
    S.show(pb, S.capAt(1) + 1.3); S.show(pl, S.capAt(1) + 1.6);
    // kill-first: the red zone flashes, the run stops
    S.pulse(zones[0], S.capAt(2) + 0.3);
    S.tint(zones[0], S.capAt(2) + 0.3, { fill: '#FDE3DA', dur: 0.5 });
    S.pulse(zones[0], S.capAt(2) + 1.4);
  });

  // ---------- s05: paired copies ----------
  Ch.scene('s05', function (S) {
    const c = S.c;
    const svg = S.svg();
    S.show(S.chip('placeholder', { x: 1560, y: 205, label: c.illustration }), S.at(0.05));
    const lo = S.box({ x: 140, y: 215, w: 170, h: 64, label: c.labels.ours, color: C.thinker, size: 36 });
    const lp = S.box({ x: 340, y: 215, w: 170, h: 64, label: c.labels.plain, color: C.placeholder, size: 36 });
    S.show(lo, S.at(0.05)); S.show(lp, S.at(0.05));
    const pairs = [];
    for (let i = 0; i < 6; i++) {
      const x = 140 + i * 280;
      const a = S.card({ x: x, y: 340, w: 120, h: 120, fill: '#E6E4FB', color: C.thinker, r: 16 });
      const b = S.card({ x: x + 150, y: 340, w: 120, h: 120, fill: '#E9ECF0', color: C.placeholder, r: 16 });
      const bond = S.card({ x: x + 120, y: 395, w: 30, h: 10, fill: C.ink, color: C.ink, r: 5 });
      pairs.push([a, b, bond]);
    }
    const copies = S.text(c.labels.copies, { x: 140, y: 480, w: 600, size: 38, weight: 700, color: C.soft });
    S.show(copies, S.capAt(0) + 0.4);
    pairs.forEach((p, i) => { S.show(p[0], S.capAt(0) + 0.6 + i * 0.3); S.show(p[1], S.capAt(0) + 0.6 + i * 0.3); S.show(p[2], S.capAt(0) + 0.8 + i * 0.3); });
    // brackets: a screen uses the first two pairs, a claim needs all six
    const b1 = S.card({ x: 140, y: 560, w: 550, h: 14, fill: C.untested, color: C.untested, r: 7 });
    const l1 = S.text(c.labels.screen, { x: 140, y: 585, w: 550, size: 40, weight: 700, color: C.untested });
    const b2 = S.card({ x: 140, y: 670, w: 1670, h: 14, fill: C.tested, color: C.tested, r: 7 });
    const l2 = S.text(c.labels.claim, { x: 140, y: 695, w: 1000, size: 40, weight: 700, color: C.tested });
    S.show(b1, S.capAt(1)); S.show(l1, S.capAt(1) + 0.3);
    S.show(b2, S.capAt(1) + 1.6); S.show(l2, S.capAt(1) + 1.9);
    S.pulse(pairs[0][0], S.capAt(1) + 0.6); S.pulse(pairs[1][0], S.capAt(1) + 0.8);
  });

  // ---------- s06: the real six-copy result ----------
  Ch.scene('s06', function (S) {
    const c = S.c;
    S.show(S.chip('tested', { x: 120, y: 205, label: c.chip }), S.at(0.05));
    const cols = [C.thinker, C.placeholder, C.placeholder];
    const hb = S.hbars({ x: 100, y: 285, w: 700, labelW: 520, rowH: 64, gap: 36, max: 100, dec: 1, labelSize: 36, valueSize: 48, valueW: 180,
      items: c.bars.map((b, i) => ({ label: b.label, value: b.value, color: cols[i] })) });
    let t = S.capAt(0) + 0.2;
    hb.rows.forEach((r, i) => { revealRow(S, r, t + i * 0.45, 1.3); });
    // gains next to the two plain rows
    const g1 = S.text(c.gains[0], { x: 1560, y: 385, w: 240, size: 60, weight: 800, color: C.tested });
    const g2 = S.text(c.gains[1], { x: 1560, y: 485, w: 240, size: 60, weight: 800, color: C.tested });
    S.pop(g1, S.capAt(1) + 0.3); S.pop(g2, S.capAt(1) + 1.2);
    // six of six
    const sq = [];
    for (let i = 0; i < 6; i++) sq.push(S.card({ x: 120 + i * 84, y: 640, w: 64, h: 64, fill: C.tested, color: C.tested, r: 12 }));
    const ah = S.text(c.ahead, { x: 650, y: 646, w: 1100, size: 52, weight: 800, color: C.tested });
    S.stagger(sq, S.capAt(2), 0.2);
    S.show(ah, S.capAt(2) + 1.3);
    const cv = S.note(c.caveat, { x: 120, y: 745, w: 1650, color: C.untested, size: 34 });
    S.show(cv, S.capAt(2) + 1.8);
  });

  // ---------- s07: range of likely error on a number line drawn to scale ----------
  Ch.scene('s07', function (S) {
    const c = S.c;
    const svg = S.svg();
    const xv = (v) => 160 + (v + 3) * 320; // -3 .. 2 points
    S.show(S.chip('tested', { x: 120, y: 205, label: c.chip }), S.at(0.05));
    const axis = S.svgEl(svg, 'line', { x1: 160, y1: 620, x2: 1760, y2: 620, stroke: C.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
    const ticks = [0, 1].map((v, i) => ({ l: vline(S, svg, xv(v), 605, 635, C.ink, 5), t: S.text(c.ticks[i], { x: xv(v) - 40, y: 645, w: 80, size: 38, weight: 700, align: 'center' }) }));
    const zero = vline(S, svg, xv(-1), 330, 620, C.warn, 5, '12 10');
    const low = vline(S, svg, xv(-2), 330, 620, C.warn, 5, '12 10');
    const z1 = S.text(c.lines.m1, { x: xv(-1) - 160, y: 275, w: 320, size: 32, weight: 700, color: C.warn, align: 'center' });
    const z2 = S.text(c.lines.m2, { x: xv(-2) - 170, y: 275, w: 340, size: 32, weight: 700, color: C.warn, align: 'center' });
    const ax = S.text(c.axis, { x: 160, y: 730, w: 1600, size: 36, color: C.soft, align: 'center' });
    // the range bar and its middle dot
    const rb = S.svgEl(svg, 'rect', { x: xv(c.lo.value), y: 540, width: xv(c.hi.value) - xv(c.lo.value), height: 40, rx: 20, fill: '#BFE3D2', stroke: C.tested, 'stroke-width': 3 });
    const dot = S.svgEl(svg, 'circle', { cx: xv(c.mean.value), cy: 560, r: 22, fill: C.tested });
    const lo = S.text(c.lo.text, { x: xv(c.lo.value) - 90, y: 480, w: 180, size: 42, weight: 700, align: 'center' });
    const hi = S.text(c.hi.text, { x: xv(c.hi.value) - 90, y: 480, w: 180, size: 42, weight: 700, align: 'center' });
    const mn = S.text(c.mean.text, { x: xv(c.mean.value) - 140, y: 395, w: 280, size: 80, weight: 800, color: C.tested, align: 'center' });
    S.show(axis, S.capAt(0)); S.stagger(ticks.map((k) => k.l), S.capAt(0) + 0.2, 0.2); S.stagger(ticks.map((k) => k.t), S.capAt(0) + 0.2, 0.2); S.show(ax, S.capAt(0) + 0.6);
    S.show(rb, S.capAt(1) + 0.9, { y: 0 }); S.show(lo, S.capAt(1) + 1.3); S.show(hi, S.capAt(1) + 1.5);
    S.show(dot, S.capAt(1) + 1.8, { y: 0 }); S.show(mn, S.capAt(1) + 2.0);
    S.show(zero, S.capAt(2)); S.show(z1, S.capAt(2) + 0.2);
    S.show(low, S.capAt(2) + 0.7); S.show(z2, S.capAt(2) + 0.9);
  });

  // ---------- s08: lesion tests: score before and after ----------
  Ch.scene('s08', function (S) {
    const c = S.c;
    const xs = [120, 720, 1320];
    S.show(S.chip('tested', { x: 120, y: 205, label: c.chipTested }), S.at(0.05));
    c.cards.forEach((k, i) => {
      const card = S.card({ x: xs[i], y: 270, w: 520, h: 400 });
      const ti = S.text(k.title, { x: xs[i] + 30, y: 290, w: 470, size: 38, weight: 700 });
      const su = S.text(k.sub, { x: xs[i] + 30, y: 392, w: 460, size: 32, color: C.soft });
      const big = S.text('', { x: xs[i] + 30, y: 440, w: 460, size: 110, weight: 800, color: C.tested, lh: 1 });
      const bar = S.bar({ x: xs[i] + 30, y: 590, w: 460, h: 44, value: k.from, max: 100, color: C.tested });
      const t0 = S.capAt(0) + 0.2 + i * 0.4;
      S.show(card, t0); S.show(ti, t0 + 0.15); S.show(su, t0 + 0.25); S.show(big, t0 + 0.35); S.show(bar.track, t0 + 0.35);
      S.tl.to(bar.fill, { scaleX: k.from / 100, duration: 0.8, ease: 'power2.out' }, t0 + 0.5);
      // second beat: the part is switched off and everything collapses
      const t1 = S.capAt(1) + 0.3 + i * 0.3;
      S.count(big, { from: k.from, to: k.to, dec: k.dec }, t1, 1.8);
      S.tint(big, t1, { color: C.warn, dur: 0.8 });
      S.tl.to(bar.fill, { scaleX: Math.max(k.to / 100, 0.004), duration: 1.8, ease: 'power2.out' }, t1);
    });
    const b3 = S.chip('untested', { x: 120, y: 720, label: c.chipB3 });
    S.show(b3, S.capAt(2));
    const half = S.card({ x: 520, y: 733, w: 900, h: 22, fill: '#F6E7C8', color: C.untested, r: 11 });
    S.show(half, S.capAt(2) + 0.4);
    const hf = S.card({ x: 520, y: 733, w: 450, h: 22, fill: C.untested, color: C.untested, r: 11 });
    S.show(hf, S.capAt(2) + 0.9);
    const ln = S.svg();
    const ml = vline(S, ln, 520 + 540, 715, 773, C.warn, 5);
    S.show(ml, S.capAt(2) + 1.6);
  });

  // ---------- s09: two different leak checks ----------
  Ch.scene('s09', function (S) {
    const c = S.c;
    const panels = [
      { x: 80, d: c.check1, labW: 210, items: [[c.labels.limit, c.check1.limit, C.placeholder, 2], [c.labels.got, c.check1.got, C.warn, 2]] },
      { x: 990, d: c.check2, labW: 250, items: [[c.labels.limit, c.check2.limit, C.placeholder, 0], [c.labels.high, c.check2.got, C.warn, 2]] },
    ];
    const hbs = [];
    panels.forEach((p, i) => {
      const card = S.card({ x: p.x, y: 230, w: 840, h: 440 });
      const ti = S.text(p.d.title, { x: p.x + 30, y: 255, w: 780, size: 44, weight: 800 });
      const hb = S.hbars({ x: p.x + 20, y: 380, w: 360, labelW: p.labW, rowH: 64, gap: 40, max: 8, labelSize: 32, valueSize: 46, valueW: 150,
        items: p.items.map((it) => ({ label: it[0], value: it[1], color: it[2], dec: it[3] })) });
      const t0 = S.capAt(i === 0 ? 0 : 1);
      S.show(card, i === 0 ? S.capAt(0) + 1.2 : S.capAt(1)); S.show(ti, (i === 0 ? S.capAt(0) + 1.5 : S.capAt(1) + 0.2));
      hbs.push(hb);
    });
    const defn = S.svg();
    // reveal rows: left with caption 2, right with caption 3
    hbs[0].rows.forEach((r, k) => revealRow(S, r, S.capAt(1) + 0.3 + k * 0.6, 1.3));
    hbs[1].rows.forEach((r, k) => revealRow(S, r, S.capAt(2) + 0.3 + k * 0.6, 1.3));
    // limit marks as thin vertical lines across each pair of rows
    const lm1 = vline(S, defn, 80 + 20 + 210 + 360 * 4.62 / 8, 365, 575, C.ink, 4, '10 8');
    const lm2 = vline(S, defn, 990 + 20 + 250 + 360 * 5 / 8, 365, 575, C.ink, 4, '10 8');
    S.show(lm1, S.capAt(1) + 2.0, { y: 0 }); S.show(lm2, S.capAt(2) + 2.0, { y: 0 });
    const ch1 = S.chip('untested', { x: 110, y: 600, label: c.chipMissed, color: C.warn });
    const ch2 = S.chip('untested', { x: 1020, y: 600, label: c.chipCleared });
    S.show(ch1, S.capAt(1) + 3.0); S.show(ch2, S.capAt(2) + 3.0);
  });

  // ---------- s10: near-misses on a screen ----------
  Ch.scene('s10', function (S) {
    const c = S.c;
    const svg = S.svg();
    const met = S.text(c.met, { x: 120, y: 215, w: 1300, size: 56, weight: 800, color: C.tested });
    S.show(met, S.capAt(0));
    c.rows.forEach((r, i) => {
      const y = 330 + i * 150;
      const m = S.box({ x: 160, y: y, w: 420, h: 100, label: r.mark, color: C.soft, size: 46 });
      const g = S.box({ x: 860, y: y, w: 520, h: 100, label: r.got, color: C.tested, size: 46 });
      const a = S.arrow(svg, 584, y + 50, 856, y + 50, { color: C.soft, width: 6 });
      const t = S.capAt(1) + i * 1.4;
      S.show(m, t); S.draw(a, t + 0.4, 0.6); S.show(g, t + 0.9);
      S.pulse(g, t + 1.5);
    });
    const cf = S.box({ x: 160, y: 660, w: 1220, h: 110, label: c.confirm, color: C.warn, size: 46 });
    S.show(cf, S.capAt(2));
    S.pulse(cf, S.capAt(2) + 0.7);
  });

  // ---------- s11: an average hides a weak family; the harm rule ----------
  Ch.scene('s11', function (S) {
    const c = S.c;
    const svg = S.svg();
    const hb = S.hbars({ x: 80, y: 250, w: 420, labelW: 420, rowH: 54, gap: 20, max: 100, dec: 2, labelSize: 32, valueSize: 40, valueW: 150,
      items: c.kinds.map((k, i) => ({ label: k.label, value: k.value, color: i === 4 ? C.warn : C.thinker })) });
    hb.reveal(S.capAt(0) + 0.3, 0.45, 1.2);
    const ax = 80 + 420 + 420 * 0.7301;
    const avl = vline(S, svg, ax, 235, 625, C.ink, 4, '10 8');
    const avt = S.text(c.avg, { x: 80, y: 650, w: 1000, size: 46, weight: 800, align: 'right', color: C.ink });
    S.show(avl, S.capAt(0) + 3.4, { y: 0 }); S.show(avt, S.capAt(0) + 3.6);
    S.pulse(hb.rows[4].lab, S.capAt(0) + 4.2);
    // the harm rule, two limits
    [['a', 240], ['b', 440]].forEach((k, i) => {
      const card = S.card({ x: 1230, y: k[1], w: 590, h: 170 });
      const nb = S.text(c.rule[k[0]], { x: 1260, y: k[1] + 24, w: 170, size: 100, weight: 800, color: C.warn, lh: 1 });
      const nl = S.text(c.rule[k[0] + 'Label'], { x: 1440, y: k[1] + 62, w: 360, size: 38, weight: 700 });
      S.show(card, S.capAt(1) + 0.3 + i * 0.7); S.show(nb, S.capAt(1) + 0.5 + i * 0.7); S.show(nl, S.capAt(1) + 0.7 + i * 0.7);
    });
    // the trial that was proved wrong
    const rc = S.card({ x: 1230, y: 640, w: 590, h: 190, color: C.warn });
    const rb = S.text(c.result.big, { x: 1260, y: 660, w: 530, size: 84, weight: 800, color: C.warn, lh: 1 });
    const rh = S.chip('untested', { x: 1260, y: 760, label: c.result.chip, color: C.warn });
    S.show(rc, S.capAt(2)); S.show(rb, S.capAt(2) + 0.3); S.show(rh, S.capAt(2) + 0.8);
  });

  // ---------- s12: size counts every part (bars drawn to scale) ----------
  Ch.scene('s12', function (S) {
    const c = S.c;
    const X0 = 160, W = 1500;
    const tot = c.bars[0].total;
    const wl = (n) => Math.max(10, n / tot * W);
    const o = c.bars[0], p = c.bars[1];
    // row 1: ours (learned sliver + borrowed reader)
    const t1 = S.text(o.label, { x: X0, y: 225, w: 420, size: 46, weight: 800 });
    const tn = S.text('', { x: 560, y: 228, w: 440, size: 48, weight: 800, color: C.reader });
    const tl_ = S.text(c.labels.total, { x: 1010, y: 238, w: 300, size: 36, color: C.soft });
    const sc = S.text(c.scores.ours, { x: 1500, y: 222, w: 300, size: 56, weight: 800, color: C.thinker, align: 'right' });
    const lA = S.card({ x: X0, y: 310, w: wl(o.learned), h: 90, fill: C.learned, color: C.learned, r: 4 });
    const bA = S.card({ x: X0 + wl(o.learned), y: 310, w: W - wl(o.learned), h: 90, fill: '#BFE3E3', color: C.reader, r: 4 });
    const nA = S.text('', { x: X0, y: 415, w: 380, size: 44, weight: 800, color: C.learned });
    const nAl = S.text(c.labels.learned, { x: X0 + 380, y: 424, w: 220, size: 34, color: C.soft });
    const nB = S.text('', { x: 920, y: 415, w: 380, size: 44, weight: 800, color: C.reader });
    const nBl = S.text(c.labels.borrowed, { x: 1310, y: 424, w: 450, size: 34, color: C.soft });
    // row 2: plain model (only learned numbers)
    const t2 = S.text(p.label, { x: X0, y: 520, w: 420, size: 46, weight: 800 });
    const sp = S.text(c.scores.plain, { x: 1500, y: 517, w: 300, size: 56, weight: 800, color: C.placeholder, align: 'right' });
    const lP = S.card({ x: X0, y: 600, w: wl(p.learned), h: 90, fill: C.learned, color: C.learned, r: 4 });
    const nP = S.text('', { x: X0, y: 705, w: 380, size: 44, weight: 800, color: C.learned });
    const nPl = S.text(c.labels.learned, { x: X0 + 380, y: 714, w: 220, size: 34, color: C.soft });
    // beats
    S.show(t1, S.capAt(0)); S.show(lA, S.capAt(0) + 0.3); S.show(bA, S.capAt(0) + 0.6);
    S.show(nA, S.capAt(0) + 1.0); S.show(nAl, S.capAt(0) + 1.1); S.show(nB, S.capAt(0) + 1.4); S.show(nBl, S.capAt(0) + 1.5);
    S.show(tn, S.capAt(0) + 2.0); S.show(tl_, S.capAt(0) + 2.1);
    S.count(nA, { from: 0, to: o.learned, comma: true }, S.capAt(0) + 1.0, 1.4);
    S.count(nB, { from: 0, to: o.borrowed, comma: true }, S.capAt(0) + 1.4, 1.4);
    S.count(tn, { from: 0, to: o.total, comma: true }, S.capAt(0) + 2.0, 1.4);
    S.show(t2, S.capAt(1)); S.show(lP, S.capAt(1) + 0.4); S.show(nP, S.capAt(1) + 0.8); S.show(nPl, S.capAt(1) + 0.9);
    S.count(nP, { from: 0, to: p.learned, comma: true }, S.capAt(1) + 0.8, 1.4);
    S.pulse(lA, S.capAt(1) + 2.0); S.pulse(lP, S.capAt(1) + 2.0);
    S.show(sc, S.capAt(2)); S.show(sp, S.capAt(2) + 0.4);
    S.show(S.chip('placeholder', { x: X0, y: 775, label: c.chip }), S.capAt(2) + 1.0);
  });

  // ---------- s13: audit of the notes, and what tests cannot tell us ----------
  Ch.scene('s13', function (S) {
    const c = S.c;
    const card = S.card({ x: 80, y: 220, w: 840, h: 590 });
    const ti = S.text(c.audit.title, { x: 120, y: 245, w: 600, size: 46, weight: 800 });
    const big = S.text('', { x: 120, y: 305, w: 600, size: 140, weight: 800, color: C.tested, lh: 1 });
    S.show(card, S.capAt(0)); S.show(ti, S.capAt(0) + 0.3); S.show(big, S.capAt(0) + 0.6);
    S.count(big, { from: 0, to: c.audit.found, comma: true }, S.capAt(1), 1.6);
    const hb = S.hbars({ x: 110, y: 520, w: 380, labelW: 200, rowH: 52, gap: 22, max: 220, dec: 0, labelSize: 36, valueSize: 44, valueW: 150,
      items: c.audit.rows.map((r, i) => ({ label: r.label, value: r.value, color: [C.warn, C.untested, C.placeholder][i] })) });
    hb.reveal(S.capAt(1) + 0.4, 0.5, 1.2);
    const lt = S.text(c.limitsTitle, { x: 980, y: 235, w: 700, size: 46, weight: 800 });
    S.show(lt, S.capAt(2));
    const lb = c.limits.map((l, i) => S.box({ x: 980, y: 330 + i * 130, w: 840, h: 100, label: l.text, color: l.kind === 'untested' ? C.untested : C.placeholder, size: 40 }));
    S.stagger(lb, S.capAt(2) + 0.4, 0.55);
  });

  // ---------- s14: recap ----------
  Ch.scene('s14', function (S) {
    const c = S.c;
    c.badges.forEach((b, i) => {
      const y = 245 + i * 190;
      const num = S.box({ x: 160, y: y, w: 130, h: 130, label: String(i + 1), color: C.tested, size: 72, r: 65 });
      const card = S.card({ x: 330, y: y, w: 1300, h: 130, color: C.tested });
      const tx = S.text(b, { x: 370, y: y + 32, w: 1200, size: 60, weight: 800 });
      const t = S.capAt(i);
      S.show(num, t); S.show(card, t + 0.2); S.show(tx, t + 0.4);
    });
  });
});
