/* Chapter 12 (Part 10 of 10): creative mode. Every on-screen string lives in content/ch12.json. Deterministic. */
Kit.chapter('ch12', function (Ch) {
  const C = Kit.C;

  // Scene 1: hook. A stuck puzzle, ideas tried one by one, the last one checked green.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const pz = S.box({ x: 160, y: 330, w: 420, h: 250, label: c.puzzle, color: C.warn, size: 64 });
    S.show(pz, S.capAt(0));
    S.pulse(pz, S.capAt(0) + 0.8);
    const svg = S.svg();
    const xs = [760, 1120, 1480];
    const boxes = c.ideas.map((t, i) => S.box({ x: xs[i] - 120, y: 340, w: 330, h: 150, label: t, color: C.learned, size: 40 }));
    const arrs = xs.map((x, i) => S.arrow(svg, i === 0 ? 580 : xs[i - 1] + 210, 415, x - 120, 415, { color: C.soft }));
    const marks = [
      S.text(c.no, { x: xs[0] - 120, y: 510, w: 330, size: 44, weight: 800, color: C.warn, align: 'center' }),
      S.text(c.no, { x: xs[1] - 120, y: 510, w: 330, size: 44, weight: 800, color: C.warn, align: 'center' }),
      S.text(c.yes, { x: xs[2] - 120, y: 510, w: 330, size: 44, weight: 800, color: C.good, align: 'center' }),
    ];
    let t = S.capAt(1);
    boxes.forEach((b, i) => {
      S.draw(arrs[i], t + i * 0.9, 0.4);
      S.show(b, t + 0.3 + i * 0.9);
      S.pop(marks[i], t + 0.9 + i * 0.9);
    });
    S.tint(boxes[0], t + 1.0, { border: C.line, color: C.soft });
    S.tint(boxes[1], t + 1.9, { border: C.line, color: C.soft });
    S.tint(boxes[2], t + 2.8, { border: C.good });
    S.tint(pz, t + 3.0, { border: C.good });
    const chip = S.chip('learned', { x: 160, y: 700, label: c.chip, size: 36 });
    S.pop(chip, S.capAt(2));
    const note = S.text(c.picture, { x: 160, y: 780, w: 600, size: 30, color: C.soft });
    S.show(note, S.capAt(2) + 0.2);
  });

  // Scene 2: how it notices it is stuck.
  Ch.scene('s02', function (S) {
    const c = S.c;
    const q = S.card({ x: 120, y: 220, w: 520, h: 360 });
    const qt = S.text(c.q, { x: 150, y: 240, w: 460, size: 34, weight: 700, color: C.ink });
    const e1 = S.text(c.examples[0], { x: 150, y: 330, w: 460, size: 46, mono: true, color: C.ink });
    const e2 = S.text(c.examples[1], { x: 150, y: 410, w: 460, size: 46, mono: true, color: C.ink });
    const tag = S.text(c.picture, { x: 150, y: 510, w: 460, size: 28, color: C.soft });
    S.show(q, S.capAt(0)); S.show(qt, S.capAt(0) + 0.2); S.show(e1, S.capAt(0) + 0.5); S.show(e2, S.capAt(0) + 0.8); S.show(tag, S.capAt(0) + 1);
    const svg = S.svg();
    const a1 = S.arrow(svg, 640, 330, 760, 330, { color: C.soft });
    const tr = S.box({ x: 760, y: 250, w: 520, h: 160, label: c.try, color: C.thinker, size: 36 });
    S.draw(a1, S.capAt(0) + 1.4, 0.4);
    S.show(tr, S.capAt(0) + 1.8);
    const a2 = S.arrow(svg, 1280, 330, 1400, 330, { color: C.soft });
    const rs = S.box({ x: 1400, y: 250, w: 420, h: 160, label: c.result, color: C.warn, size: 34 });
    S.draw(a2, S.capAt(1), 0.4);
    S.show(rs, S.capAt(1) + 0.4);
    S.pulse(e1, S.capAt(1) + 0.4);
    const badge = S.box({ x: 1000, y: 500, w: 520, h: 150, label: c.badge, color: C.warn, size: 72, fill: '#FFF1E8' });
    S.pop(badge, S.capAt(2));
    S.pulse(badge, S.capAt(2) + 0.6);
    const chip = S.chip('hand', { x: 120, y: 700, label: c.chip, size: 32 });
    S.pop(chip, S.capAt(2) + 0.5);
  });

  // Scene 3: stuck-first search, a fan of 32 tries, then 480 more.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const cells = [], xs = [];
    for (let i = 0; i < 32; i++) {
      const cx = 120 + (i % 8) * 54, cy = 200 + Math.floor(i / 8) * 54;
      cells.push(S.box({ x: cx, y: cy, w: 44, h: 44, color: C.learned, size: 20 }));
      xs.push(S.text('x', { x: cx, y: cy + 2, w: 44, size: 34, weight: 800, color: C.warn, align: 'center' }));
    }
    const lab32 = S.text(c.tries32, { x: 120, y: 424, w: 430, size: 38, weight: 700, color: C.learned, nowrap: true });
    S.sweep(cells, S.capAt(0) + 0.2, 1.8);
    S.show(lab32, S.capAt(0) + 0.6);
    S.sweep(xs, S.capAt(1) - 0.2, 1.6);
    const row = [];
    for (let r = 0; r < 10; r++) {
      const v = S.vec({ x: 120, y: 520 + r * 24, n: 48, cell: 16, gap: 3, dir: 'h', color: C.learned, seed: 1 });
      v.querySelectorAll('i').forEach((q) => { q.style.opacity = '0.55'; });
      row.push(v);
    }
    const big = S.text(c.more480, { x: 1060, y: 540, w: 700, size: 64, weight: 800, color: C.learned, nowrap: true });
    S.sweep(row, S.capAt(1) + 0.6, 2.2);
    S.pop(big, S.capAt(1) + 0.8);
    const tot = S.text(c.total512, { x: 1060, y: 660, w: 700, size: 64, weight: 800, color: C.ink, nowrap: true });
    S.pop(tot, S.capAt(1) + 1.8);
    // a few green fits in the big fan (made up)
    if (typeof gsap !== 'undefined') {
      [[2, 7], [5, 30], [8, 12]].forEach((p, k) => {
        const cell = row[p[0]].querySelectorAll('i')[p[1]];
        S.tl.to(cell, { backgroundColor: C.good, opacity: 1, duration: 0.3 }, S.capAt(1) + 3 + k * 0.3);
      });
    }
    const done = S.box({ x: 1060, y: 220, w: 700, h: 120, label: c.picture, color: C.placeholder, size: 30 });
    S.show(done, S.capAt(1));
    const solved = S.box({ x: 1060, y: 360, w: 700, h: 120, label: c.solved, color: C.good, size: 34 });
    S.show(solved, S.capAt(2));
    const chip = S.chip('tested', { x: 1060, y: 790, label: c.chip, size: 30 });
    S.pop(chip, S.capAt(2) + 0.4);
  });

  // Scene 4: example checker.
  Ch.scene('s04', function (S) {
    const c = S.c;
    const ex = S.note(c.examples, { x: 120, y: 200, w: 1000, color: C.thinker, size: 38 });
    S.show(ex, S.capAt(0));
    const rows = c.tries.map((r, i) => {
      const y = 300 + i * 100;
      const b = S.box({ x: 120, y: y, w: 560, h: 80, label: r.t, color: C.learned, size: 34 });
      const v = S.box({ x: 720, y: y, w: 560, h: 80, label: r.r, color: i === 1 ? C.good : C.warn, size: 34 });
      return { b, v };
    });
    rows.forEach((r, i) => {
      S.show(r.b, S.capAt(0) + 0.8 + i * 0.5);
      S.show(r.v, S.capAt(0) + 1.1 + i * 0.5);
    });
    S.pulse(ex, S.capAt(0) + 2.9);
    // second caption: bad ones go grey, the good one is kept
    rows.forEach((r, i) => {
      if (i !== 1) { S.tint(r.b, S.capAt(1) + 0.3, { border: C.line, color: C.soft }); S.tint(r.v, S.capAt(1) + 0.3, { border: C.line, color: C.soft }); }
    });
    S.pulse(rows[1].v, S.capAt(1) + 0.5);
    const svg = S.svg();
    const a = S.arrow(svg, 1280, 440, 1380, 440, { color: C.good });
    const kept = S.box({ x: 1380, y: 380, w: 440, h: 120, label: c.kept, color: C.good, size: 34 });
    S.draw(a, S.capAt(1) + 0.8, 0.4);
    S.show(kept, S.capAt(1) + 1.1);
    const cap2 = S.box({ x: 1380, y: 540, w: 440, h: 110, label: c.cap2, color: C.learned, size: 36 });
    S.show(cap2, S.capAt(2));
    S.pulse(cap2, S.capAt(2) + 0.5);
    const tag = S.text(c.picture, { x: 120, y: 720, w: 600, size: 30, color: C.soft });
    S.show(tag, S.capAt(0) + 1);
    const chip = S.chip('hand', { x: 120, y: 790, label: c.chip, size: 28 });
    S.pop(chip, S.capAt(2) + 0.6);
  });

  // Scene 5: the job-8 result with the honest miss.
  Ch.scene('s05', function (S) {
    const c = S.c;
    const lt = S.text(c.leftTitle, { x: 80, y: 190, w: 820, size: 36, weight: 700, color: C.ink });
    const rt = S.text(c.rightTitle, { x: 980, y: 190, w: 820, size: 36, weight: 700, color: C.ink });
    S.show(lt, S.capAt(0)); S.show(rt, S.capAt(0));
    const hl = S.hbars({ x: 80, y: 260, w: 380, labelW: 380, rowH: 80, gap: 20, max: 260, dec: 0,
      items: c.left.map((b) => ({ label: b.label, value: b.value, color: C.learned })) });
    const hr = S.hbars({ x: 980, y: 260, w: 340, labelW: 380, rowH: 80, gap: 20, max: 12, dec: 1,
      items: c.right.map((b, i) => ({ label: b.label, value: b.value, color: i === 0 ? C.good : C.untested })) });
    hl.reveal(S.capAt(1), 0.4, 1.4);
    hr.reveal(S.capAt(2), 0.4, 1.4);
    const miss = S.note(c.miss, { x: 1000, y: 470, w: 820, color: C.untested, size: 36 });
    S.show(miss, S.capAt(3));
    S.pulse(miss, S.capAt(3) + 0.5);
    const chip = S.chip('tested', { x: 100, y: 470, label: c.chip, size: 28 });
    S.pop(chip, S.capAt(0) + 0.6);
    const verdict = S.box({ x: 1000, y: 620, w: 820, h: 100, label: c.verdict, color: C.untested, size: 38 });
    S.pop(verdict, S.capAt(3) + 0.9);
  });

  // Scene 6: day, night, day, night.
  Ch.scene('s06', function (S) {
    const c = S.c;
    const svg = S.svg();
    const bs = c.steps.map((t, i) => S.box({ x: 100 + i * 450, y: 220, w: 380, h: 130, label: t, color: i % 2 ? C.stop : C.untested, size: 34 }));
    bs.forEach((b, i) => {
      S.show(b, S.capAt(0) + i * 0.4);
      if (i > 0) S.draw(S.arrow(svg, 100 + (i - 1) * 450 + 380, 285, 100 + i * 450, 285, { color: C.soft }), S.capAt(0) + i * 0.4, 0.3);
    });
    S.pulse(bs[1], S.capAt(0) + 2.2);
    S.pulse(bs[3], S.capAt(1) + 0.6);
    const cA = S.card({ x: 100, y: 420, w: 800, h: 250 });
    const cB = S.card({ x: 960, y: 420, w: 860, h: 250 });
    const tA = S.text(c.cardA, { x: 130, y: 440, w: 740, size: 32, weight: 700, color: C.ink });
    const tB = S.text(c.cardB, { x: 990, y: 440, w: 800, size: 32, weight: 700, color: C.ink });
    S.show(cA, S.capAt(2)); S.show(tA, S.capAt(2));
    S.show(cB, S.capAt(3)); S.show(tB, S.capAt(3));
    const nums = [];
    c.a.forEach((v, i) => nums.push([S.text('0', { x: 160 + i * 380, y: 520, w: 340, size: 88, weight: 800, color: C.good, nowrap: true }), v, S.capAt(2) + 0.3 + i * 0.3]));
    c.b.forEach((v, i) => nums.push([S.text('0', { x: 1020 + i * 380, y: 520, w: 340, size: 88, weight: 800, color: C.learned, nowrap: true }), v, S.capAt(3) + 0.3 + i * 0.3]));
    nums.forEach((n) => { S.show(n[0], n[2]); S.count(n[0], { from: 0, to: n[1], dec: 1, pre: n[1] > 0 ? '+' : '' }, n[2], 0.9); });
    const chip = S.chip('tested', { x: 100, y: 720, label: c.chip, size: 32 });
    S.pop(chip, S.capAt(3) + 1.0);
  });

  // Scene 7: status as of Oct 11.
  Ch.scene('s07', function (S) {
    const c = S.c;
    const bs = c.parts.map((t, i) => S.box({ x: 100 + (i % 2) * 560, y: 210 + Math.floor(i / 2) * 130, w: 520, h: 100, label: t, color: C.learned, size: 36 }));
    S.show(bs[0], S.capAt(0)); S.show(bs[1], S.capAt(1) - 0.5);
    S.show(bs[2], S.capAt(1) - 0.2); S.show(bs[3], S.capAt(1) + 0.1);
    const chip = S.chip('untested', { x: 100, y: 490, label: c.partsChip, size: 32 });
    S.pop(chip, S.capAt(1) + 0.6);
    const dropped = S.box({ x: 1260, y: 210, w: 560, h: 120, label: c.dropped, color: C.placeholder, size: 36 });
    S.show(dropped, S.capAt(2));
    S.tint(dropped, S.capAt(2) + 0.5, { border: C.warn });
    const tests = S.box({ x: 1260, y: 380, w: 560, h: 120, label: c.tests, color: C.placeholder, size: 34 });
    S.show(tests, S.capAt(3));
    const tchip = S.chip('placeholder', { x: 1260, y: 530, label: c.testsChip, size: 32 });
    S.pop(tchip, S.capAt(3) + 0.5);
    S.pulse(tests, S.capAt(3) + 0.8);
  });
});
