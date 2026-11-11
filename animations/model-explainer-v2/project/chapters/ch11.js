/* Chapter 11: learning while it sleeps. All on-screen strings live in content/ch11.json. */
Kit.chapter('ch11', function (Ch) {
  const C = Kit.C;
  const NIGHT = '#EEF3FF';

  function intervalRow(S, o) {
    const ax = o.ax, col = o.col || C.learned;
    const px = (u) => ax.x0 + ((u - ax.min) / (ax.max - ax.min)) * (ax.x1 - ax.x0);
    const lab = S.text(o.label, { x: ax.labX, y: o.y - 24, w: ax.labW, size: 34, weight: 700, align: 'right' });
    const track = S.card({ x: ax.x0, y: o.y - 3, w: ax.x1 - ax.x0, h: 6, fill: C.line, color: C.line, r: 3 });
    const rng = S.card({ x: px(o.lo), y: o.y - 15, w: Math.max(6, px(o.hi) - px(o.lo)), h: 30, fill: col + '33', color: col, r: 15 });
    S.show(lab, o.t, { dur: 0.4 }); S.show(track, o.t, { dur: 0.4 }); S.show(rng, o.t + 0.2, { dur: 0.5 });
    const dot = S.card({ x: px(0) - 20, y: o.y - 20, w: 40, h: 40, fill: col, color: col, r: 20 });
    const val = S.text('', { x: px(o.v) - 120, y: o.y - 84, w: 240, size: 44, weight: 800, align: 'center', color: col });
    S.show(dot, o.t + 0.3, { dur: 0.3 });
    S.move(dot, o.t + 0.7, 1.0, { x: px(o.v) - px(0) });
    S.show(val, o.t + 0.7, { dur: 0.3 });
    S.count(val, { from: 0, to: o.v, dec: 2, pre: o.v > 0 ? '+' : '' }, o.t + 0.7, 1.0);
  }

  function sunMoon(S, svg, cx, cy, kind) {
    if (kind === 'sun') {
      const els = [S.svgEl(svg, 'circle', { cx, cy, r: 34, fill: '#F2B01E' })];
      for (let i = 0; i < 8; i++) {
        const a = i * Math.PI / 4;
        els.push(S.svgEl(svg, 'line', { x1: cx + Math.cos(a) * 46, y1: cy + Math.sin(a) * 46, x2: cx + Math.cos(a) * 62, y2: cy + Math.sin(a) * 62, stroke: '#F2B01E', 'stroke-width': 7, 'stroke-linecap': 'round' }));
      }
      return els;
    }
    return [S.svgEl(svg, 'circle', { cx, cy, r: 36, fill: C.learned }), S.svgEl(svg, 'circle', { cx: cx + 18, cy: cy - 14, r: 31, fill: NIGHT })];
  }
  function stars(S, svg, x, y, w, h, n, seed) {
    const r = K_rng(seed);
    const out = [];
    for (let i = 0; i < n; i++) out.push(S.svgEl(svg, 'circle', { cx: x + r() * w, cy: y + r() * h, r: 3 + r() * 3, fill: C.learned }));
    return out;
  }
  const K_rng = (s) => Kit.rng(s);
  function reveal(S, list, t, dur) { list.forEach((e) => S.tl.to(e, { autoAlpha: 1, duration: dur || 0.5 }, t)); }

  // s01: hook. Day tiles settle into the night box.
  Ch.scene('s01', function (S) {
    const L = S.c.L;
    const day = S.box({ x: 120, y: 280, w: 640, h: 330, color: '#D69A12', fill: '#FFF6DD' });
    const night = S.box({ x: 1160, y: 280, w: 640, h: 330, color: C.learned, fill: NIGHT });
    const dT = S.text(L.day, { x: 145, y: 295, w: 500, size: 44, weight: 800 });
    const nT = S.text(L.night, { x: 1185, y: 360, w: 500, size: 44, weight: 800 });
    const svg = S.svg();
    const sun = sunMoon(S, svg, 690, 345, 'sun');
    const moon = sunMoon(S, svg, 1730, 345, 'moon');
    const st = stars(S, svg, 1190, 300, 420, 50, 9, 7);
    const arr = S.arrow(svg, 780, 445, 1140, 445, { color: C.soft, width: 8 });
    const tiles = L.tiles.map((s, i) => S.box({ x: 150 + i * 200, y: 450, w: 180, h: 100, label: s, color: C.soft, size: 40 }));
    const set = L.tiles.map((s, i) => S.box({ x: 1190 + i * 200, y: 450, w: 180, h: 100, label: s, color: C.tested, fill: '#E8F6EE', size: 40 }));
    const sl = S.text(L.settled, { x: 1190, y: 556, w: 600, size: 30, color: C.tested, weight: 700 });
    const pic = S.chip('placeholder', { x: 120, y: 660, label: L.pic });
    const chip = S.chip('tested', { x: 1160, y: 660, label: L.chip });
    const note = S.note(L.note, { x: 1160, y: 730, w: 640, color: C.warn, size: 30 });
    S.show(day, S.capAt(0)); S.show(dT, S.capAt(0)); reveal(S, sun, S.capAt(0) + 0.3);
    S.stagger(tiles, S.capAt(0) + 0.8, 0.45);
    S.pulse(day, S.capAt(0) + 2.4);
    S.show(pic, S.capAt(0) + 2.0);
    S.draw(arr, S.capAt(1), 0.8);
    S.show(night, S.capAt(1) + 0.6); S.show(nT, S.capAt(1) + 0.6); reveal(S, moon, S.capAt(1) + 0.9); reveal(S, st, S.capAt(1) + 1.2, 0.8);
    S.tl.to(tiles, { autoAlpha: 0.3, duration: 0.6 }, S.capAt(1) + 1.6);
    S.stagger(set, S.capAt(1) + 1.8, 0.5);
    S.show(sl, S.capAt(1) + 3.2);
    st.forEach((s, i) => S.tl.to(s, { autoAlpha: 0.35, duration: 0.7 }, S.capAt(1) + 2.5 + i * 0.15).to(s, { autoAlpha: 1, duration: 0.7 }, '>'));
    S.show(chip, S.capAt(2)); S.show(note, S.capAt(2) + 0.5);
  });

  // s02: the puzzle.
  Ch.scene('s02', function (S) {
    const L = S.c.L;
    const head = S.text(L.exHead, { x: 100, y: 210, w: 360, size: 34, weight: 700, color: C.soft });
    const grp = S.card({ x: 100, y: 255, w: 360, h: 380 });
    const ex = L.ex.map((s, i) => S.box({ x: 130, y: 280 + i * 115, w: 300, h: 95, label: s, color: C.soft, size: 48 }));
    const ys = [270, 410, 550];
    const rules = L.rules.map((s, i) => S.box({ x: 560, y: ys[i], w: 380, h: 110, label: s, color: C.learned, size: 50 }));
    const svg = S.svg();
    const arrs = ys.map((y) => S.arrow(svg, 470, y + 55, 552, y + 55, { color: C.soft, width: 5, head: 18 }));
    const fits = L.fits.map((f, i) => S.text('', { x: 970, y: ys[i] + 22, w: 300, size: 58, weight: 800, color: C.ink }));
    const tag = S.chip('placeholder', { x: 100, y: 700, label: L.tag });
    const q = S.box({ x: 1400, y: 330, w: 380, h: 120, label: L.query, color: C.soft, size: 58 });
    const out = S.arrow(svg, 1590, 460, 1590, 540, { color: C.tested, width: 6 });
    const ans = S.text(L.answer, { x: 1400, y: 560, w: 380, size: 84, weight: 800, align: 'center', color: C.tested });
    const keep = S.note(L.keep, { x: 1400, y: 690, w: 420, color: C.tested, size: 32 });
    S.show(head, S.capAt(0)); S.show(grp, S.capAt(0)); S.stagger(ex, S.capAt(0) + 0.3, 0.5);
    S.show(tag, S.capAt(0) + 2.0);
    S.stagger(rules, S.capAt(1) + 0.2, 0.5);
    arrs.forEach((a, i) => S.draw(a, S.capAt(1) + 0.2 + i * 0.5, 0.4));
    fits.forEach((f, i) => { const t = S.capAt(1) + 2.3 + i * 1.0; S.show(f, t, { dur: 0.3 }); S.count(f, { from: 0, to: L.fits[i], suf: L.fitSuf }, t, 0.8); });
    const t3 = S.capAt(2);
    [0, 2].forEach((i) => S.tl.to([rules[i], fits[i]], { autoAlpha: 0.3, duration: 0.5 }, t3));
    S.tint(rules[1], t3, { border: C.tested }); S.pulse(fits[1], t3 + 0.3);
    S.show(q, t3 + 1.0); S.draw(out, t3 + 1.6, 0.5); S.pop(ans, t3 + 2.1); S.show(keep, t3 + 3.0);
  });

  // s03: old sleep next to new sleep.
  Ch.scene('s03', function (S) {
    const L = S.c.L;
    const hd = S.text(L.head, { x: 100, y: 205, w: 1000, size: 34, weight: 700, color: C.soft });
    const hb = S.hbars({ x: 100, y: 270, w: 700, labelW: 380, rowH: 90, gap: 40, max: 100, dec: 1, items: [{ label: L.old, value: L.oldVal, color: C.learned }, { label: L.new, value: L.newVal, color: C.tested }] });
    const sh = S.text(L.stepsHead, { x: 100, y: 540, w: 400, size: 34, weight: 700, color: C.soft });
    const n1 = S.text('', { x: 100, y: 590, w: 880, size: 60, weight: 800, color: C.learned, nowrap: true });
    const l1 = S.text(L.oldSteps, { x: 100, y: 690, w: 600, size: 32, color: C.soft });
    const n2 = S.text('', { x: 1100, y: 590, w: 500, size: 60, weight: 800, color: C.tested });
    const l2 = S.text(L.newSteps, { x: 1100, y: 690, w: 700, size: 32, color: C.soft });
    const stamp = S.note(L.stamp, { x: 1360, y: 330, w: 460, color: C.warn, size: 40, fill: '#FFF1E8' });
    const chip = S.chip('tested', { x: 100, y: 755, label: L.chip });
    S.show(hd, S.capAt(0)); S.show(sh, S.capAt(0) + 1.5);
    S.show(hb.rows[0].lab, S.capAt(0) + 0.3, { dur: 0.4 }); S.show(hb.rows[0].track, S.capAt(0) + 0.3, { dur: 0.4 }); S.show(hb.rows[0].val, S.capAt(0) + 0.5, { dur: 0.3 });
    S.grow(hb.rows[0].b, S.capAt(0) + 0.6, 1.4, hb.rows[0].val, { dec: 1 });
    S.show(n1, S.capAt(0) + 2.2); S.count(n1, { from: 0, to: L.oldStepsVal, suf: L.oldSuf }, S.capAt(0) + 2.2, 1.6); S.show(l1, S.capAt(0) + 2.4);
    S.show(hb.rows[1].lab, S.capAt(1) + 0.3, { dur: 0.4 }); S.show(hb.rows[1].track, S.capAt(1) + 0.3, { dur: 0.4 }); S.show(hb.rows[1].val, S.capAt(1) + 0.5, { dur: 0.3 });
    S.grow(hb.rows[1].b, S.capAt(1) + 0.6, 1.4, hb.rows[1].val, { dec: 1 });
    S.show(n2, S.capAt(1) + 2.2); S.count(n2, { from: 0, to: L.newStepsVal }, S.capAt(1) + 2.2, 1.2); S.show(l2, S.capAt(1) + 2.4);
    S.pulse(n2, S.capAt(1) + 3.6);
    S.show(chip, S.capAt(1) + 0.5);
    S.pop(stamp, S.capAt(2));
  });

  // s04: one night.
  Ch.scene('s04', function (S) {
    const L = S.c.L;
    const tries = S.box({ x: 100, y: 260, w: 400, h: 110, label: L.tries, color: C.soft, size: 38 });
    const search = S.box({ x: 100, y: 410, w: 400, h: 110, label: L.search, color: C.soft, size: 38 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 510, 315, 620, 380, { color: C.soft, width: 6 });
    const a2 = S.arrow(svg, 510, 465, 620, 420, { color: C.soft, width: 6 });
    const night = S.card({ x: 630, y: 215, w: 760, h: 380, fill: NIGHT, color: C.learned });
    const rowsN = S.text('', { x: 660, y: 235, w: 340, size: 60, weight: 800, color: C.learned });
    const rowsL = S.text(L.rows, { x: 920, y: 255, w: 300, size: 36, color: C.soft });
    const dl = S.text(L.dreams, { x: 660, y: 345, w: 600, size: 34, weight: 700, color: C.thinker });
    const dv = S.vec({ x: 660, y: 390, n: 16, cell: 30, gap: 6, color: C.thinker, seed: 3 });
    const sl = S.text(L.skills, { x: 660, y: 460, w: 600, size: 34, weight: 700, color: C.reader });
    const sv = S.vec({ x: 660, y: 505, n: 16, cell: 30, gap: 6, color: C.reader, seed: 9 });
    const upN = S.text('', { x: 1450, y: 270, w: 340, size: 120, weight: 800, color: C.tested, align: 'center' });
    const upL = S.text(L.updates, { x: 1450, y: 410, w: 340, size: 40, color: C.soft, align: 'center' });
    const flags = [];
    for (let i = 0; i < 8; i++) flags.push(S.box({ x: 640 + i * 95, y: 640, w: 80, h: 60, label: '✓', color: C.tested, fill: '#E8F6EE', size: 34 }));
    const ck = S.text(L.check, { x: 640, y: 715, w: 760, size: 32, color: C.soft });
    const keep = S.box({ x: 1450, y: 620, w: 340, h: 120, label: L.keep, color: C.tested, size: 34 });
    const pic = S.chip('placeholder', { x: 100, y: 590, label: L.pic });
    S.show(tries, S.capAt(0)); S.show(search, S.capAt(0) + 0.4);
    S.draw(a1, S.capAt(0) + 1.0, 0.5); S.draw(a2, S.capAt(0) + 1.2, 0.5);
    S.show(night, S.capAt(0) + 1.4); S.show(rowsN, S.capAt(0) + 1.8); S.count(rowsN, { from: 0, to: L.rowsTo, comma: true }, S.capAt(0) + 1.8, 1.6); S.show(rowsL, S.capAt(0) + 2.0);
    S.show(upN, S.capAt(0) + 3.0); S.count(upN, { from: 0, to: L.total }, S.capAt(0) + 3.0, 3.0); S.show(upL, S.capAt(0) + 3.2);
    S.show(pic, S.capAt(0) + 1.0);
    S.show(dl, S.capAt(1)); S.show(dv, S.capAt(1) + 0.3); S.show(sl, S.capAt(1) + 2.6); S.show(sv, S.capAt(1) + 2.9);
    S.pulse(dv, S.capAt(1) + 4.0); S.pulse(sv, S.capAt(1) + 4.6);
    S.stagger(flags, S.capAt(2), 0.45); S.show(ck, S.capAt(2) + 0.3);
    S.show(keep, S.capAt(2) + 4.2);
  });

  // s05: credit.
  Ch.scene('s05', function (S) {
    const L = S.c.L;
    const ax = { x0: 640, x1: 1700, min: -2.5, max: 3, labX: 60, labW: 540 };
    const px = (u) => ax.x0 + ((u - ax.min) / (ax.max - ax.min)) * (ax.x1 - ax.x0);
    const chip = S.chip('tested', { x: 1440, y: 205, label: L.chip });
    const zero = S.card({ x: px(0) - 2, y: 270, w: 4, h: 470, fill: C.ink, color: C.ink, r: 2 });
    const ticks = L.ticks.map((tv) => S.text(String(tv), { x: px(tv) - 40, y: 745, w: 80, size: 32, weight: 700, align: 'center', color: C.soft }));
    const ah = S.text(L.axisHead, { x: 640, y: 795, w: 1060, size: 32, color: C.soft, align: 'center' });
    S.show(chip, S.capAt(0) + 0.3); S.show(zero, S.capAt(0), { dur: 0.5, y: 0 }); ticks.forEach((t) => S.show(t, S.capAt(0) + 0.2, { dur: 0.4, y: 0 })); S.show(ah, S.capAt(0) + 0.4);
    const cols = [C.learned, C.soft, C.warn];
    L.rows.forEach((r, i) => intervalRow(S, { label: r.label, v: r.v, lo: r.lo, hi: r.hi, ax, y: 400 + i * 150, t: S.capAt(i) + 0.4, col: cols[i] }));
  });

  // s06: two nights, SCM2. Grouped bars, then the multi-step marks, then the caveat.
  Ch.scene('s06', function (S) {
    const L = S.c.L;
    const cols = [C.soft, C.warn, C.tested];
    const hd = S.text(L.head, { x: 100, y: 200, w: 1100, size: 32, weight: 700, color: C.soft });
    const chip = S.chip('tested', { x: 1330, y: 195, label: L.chip, color: C.warn });
    // legend
    const bars = []; const gx = [100, 700];
    L.groups.forEach((g, gi) => {
      const gl = S.text(g, { x: gx[gi], y: 250, w: 520, size: 40, weight: 800 });
      const rows = L.vals[gi].map((v, ci) => {
        const y = 310 + ci * 90;
        const b = S.bar({ x: gx[gi], y, w: 400, h: 56, value: v, max: 100, color: cols[ci] });
        const val = S.text('', { x: gx[gi] + 410, y: y + 4, w: 150, size: 40, weight: 800, color: cols[ci] });
        const lab = S.text(L.cols[ci], { x: gx[gi], y: y + 58, w: 420, size: 22, color: C.soft });
        return { b, val, lab };
      });
      bars.push({ gl, rows });
    });
    S.show(hd, S.capAt(0) + 2.0);
    // 3 day/night dots for the two-night picture
    const ys = 600;
    const n1 = S.box({ x: 100, y: 420, w: 220, h: 80, label: L.night1, color: C.learned, fill: NIGHT, size: 32 });
    const d = S.box({ x: 400, y: 420, w: 300, h: 80, label: L.day2, color: '#D69A12', fill: '#FFF6DD', size: 32 });
    const n2 = S.box({ x: 780, y: 420, w: 220, h: 80, label: L.night2, color: C.learned, fill: NIGHT, size: 32 });
    const svg = S.svg();
    const ar1 = S.arrow(svg, 330, 460, 392, 460, { color: C.soft, width: 5, head: 14 });
    const ar2 = S.arrow(svg, 710, 460, 772, 460, { color: C.soft, width: 5, head: 14 });
    S.show(n1, S.capAt(0) + 0.6); S.draw(ar1, S.capAt(0) + 1.2, 0.4); S.show(d, S.capAt(0) + 1.5); S.draw(ar2, S.capAt(0) + 2.1, 0.4); S.show(n2, S.capAt(0) + 2.4);
    // bars
    const show1 = (gi, t) => { const g = bars[gi]; S.show(g.gl, t); g.rows.forEach((r, ci) => { const tt = t + 0.3 + ci * 0.8; S.show(r.b.track, tt, { dur: 0.3 }); S.show(r.lab, tt, { dur: 0.3 }); S.show(r.val, tt + 0.2, { dur: 0.3 }); S.grow(r.b, tt + 0.3, 1.0, r.val, { dec: 1 }); }); };
    // bars of copy 1 replace the day/night picture in space: move picture away at capAt(1)
    S.tl.to([n1, d, n2, ar1.line, ar1.head, ar2.line, ar2.head], { autoAlpha: 0, duration: 0.4 }, S.capAt(1) - 0.2);
    show1(0, S.capAt(1) + 0.2);
    show1(1, S.capAt(2) + 0.2);
    S.show(chip, S.capAt(0) + 0.8);
    // marks
    const mh = S.text(L.mHead, { x: 100, y: 650, w: 1000, size: 32, weight: 700, color: C.soft });
    const m = L.mVals.map((v, i) => S.box({ x: 100 + i * 330, y: 700, w: 300, h: 90, label: v, color: C.tested, fill: '#E8F6EE', size: 56 }));
    const mk = S.text(L.mark, { x: 780, y: 722, w: 600, size: 34, color: C.soft });
    S.tl.to(chip, { autoAlpha: 1 }, S.capAt(0));
    S.show(mh, S.capAt(3)); S.stagger(m, S.capAt(3) + 0.5, 0.6); S.show(mk, S.capAt(3) + 1.8);
    const warn = S.note(L.warn, { x: 1130, y: 640, w: 700, color: C.warn, size: 34, fill: '#FFF1E8' });
    S.pop(warn, S.capAt(4));
  });

  // s07: planned timeline.
  Ch.scene('s07', function (S) {
    const L = S.c.L;
    const chip = S.chip('placeholder', { x: 1500, y: 195, label: L.chip, size: 36 });
    const main = S.box({ x: 100, y: 300, w: 520, h: 150, label: L.main, color: C.thinker, size: 40 });
    const phase = S.card({ x: 760, y: 280, w: 760, h: 190, fill: '#fff', color: C.placeholder });
    const pl = S.text(L.phase, { x: 780, y: 292, w: 720, size: 32, weight: 800, color: C.soft, align: 'center' });
    const seq = [['day', '#D69A12', '#FFF6DD'], ['night', C.learned, NIGHT], ['day', '#D69A12', '#FFF6DD'], ['night', C.learned, NIGHT]];
    const sb = seq.map((q, i) => S.box({ x: 785 + i * 180, y: 360, w: 160, h: 85, label: L[q[0]], color: q[1], fill: q[2], size: 32 }));
    const ship = S.box({ x: 1640, y: 300, w: 200, h: 150, label: L.ship, color: C.tested, size: 32 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 625, 375, 755, 375, { color: C.soft, width: 7 });
    const a2 = S.arrow(svg, 1525, 375, 1635, 375, { color: C.soft, width: 7 });
    const g1 = S.box({ x: 400, y: 560, w: 360, h: 100, label: L.gate1, color: C.warn, fill: '#FFF1E8', size: 36 });
    const g2 = S.box({ x: 840, y: 560, w: 360, h: 100, label: L.gate2, color: C.warn, fill: '#FFF1E8', size: 36 });
    const nr = S.chip('placeholder', { x: 520, y: 690, label: L.notRun, color: C.warn, size: 34 });
    const ga = S.arrow(svg, 580, 550, 780, 475, { color: C.warn, width: 5 });
    const est = S.note(L.est, { x: 1280, y: 580, w: 520, color: C.placeholder, size: 38 });
    S.show(chip, S.capAt(0));
    S.show(main, S.capAt(0) + 0.5); S.draw(a1, S.capAt(0) + 1.2, 0.5);
    S.show(phase, S.capAt(1)); S.show(pl, S.capAt(1) + 0.2); S.stagger(sb, S.capAt(1) + 0.6, 0.5);
    S.draw(a2, S.capAt(1) + 3.0, 0.5); S.show(ship, S.capAt(1) + 3.4);
    S.show(g1, S.capAt(2)); S.show(g2, S.capAt(2) + 0.8); S.draw(ga, S.capAt(2) + 1.4, 0.5); S.show(nr, S.capAt(2) + 2.0);
    S.show(est, S.capAt(3));
  });

  // s08: recap + teaser.
  Ch.scene('s08', function (S) {
    const L = S.c.L;
    const cards = L.cards.map((s, i) => S.box({ x: 100 + i * 590, y: 270, w: 560, h: 230, label: s, color: [C.learned, C.tested, C.placeholder][i], size: 40 }));
    const chips = L.cards.map((s, i) => S.chip(L.chips[i], { x: 100 + i * 590, y: 530, label: L.chipLabels[i], size: 32, color: i === 1 ? C.warn : undefined }));
    const nx = S.text(L.next, { x: 100, y: 640, w: 600, size: 34, weight: 700, color: C.soft });
    const nt = S.box({ x: 100, y: 690, w: 1200, h: 100, label: L.nextT, color: C.call, size: 44 });
    S.stagger(cards, S.capAt(0), 0.7); S.stagger(chips, S.capAt(0) + 0.5, 0.7);
    S.pulse(cards[1], S.capAt(1)); S.pulse(cards[2], S.capAt(1) + 1.2);
    S.show(nx, S.capAt(2)); S.pop(nt, S.capAt(2) + 0.4);
  });
});
