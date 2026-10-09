/* Chapter 6: the stop switch. Built, never run. Every on-screen string lives in content/ch06.json. */
Kit.chapter('ch06', function (Ch) {
  const C = Kit.C;

  // Scene 1: the five-part map with the stop switch lit.
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 380, w: 1720, h: 240, highlight: 'stop' });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    let t = S.at(0.08);
    order.forEach((k, i) => {
      S.show(m.parts[k], t + i * 0.2);
      if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.2 + 0.25, 0.3);
    });
    S.pulse(m.parts.stop, S.capAt(1));
    const chip = S.chip('untested', { x: 100, y: 690, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 2: a fixed dial sets the same number of rounds for every question.
  Ch.scene('s02', function (S) {
    const c = S.c;
    const dial = S.box({ x: 160, y: 380, w: 480, h: 180, label: c.dial, color: C.stop, size: 40 });
    const qE = S.box({ x: 900, y: 290, w: 560, h: 130, label: c.easy, color: C.reader, size: 40 });
    const qH = S.box({ x: 900, y: 520, w: 560, h: 130, label: c.hard, color: C.call, size: 40 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 640, 470, 900, 355, { color: C.soft });
    const a2 = S.arrow(svg, 640, 470, 900, 585, { color: C.soft });
    const vE = S.vec({ x: 1490, y: 330, n: 12, cell: 24, gap: 5, dir: 'h', color: C.reader, seed: 4 });
    const vH = S.vec({ x: 1490, y: 560, n: 12, cell: 24, gap: 5, dir: 'h', color: C.call, seed: 7 });
    S.show(dial, S.capAt(0));
    S.draw(a1, S.capAt(1), 0.6);
    S.draw(a2, S.capAt(1) + 0.2, 0.6);
    S.show(qE, S.capAt(1));
    S.show(qH, S.capAt(1) + 0.2);
    S.show(vE, S.capAt(1) + 0.4);
    S.show(vH, S.capAt(1) + 0.6);
    const note = S.note(c.picture, { x: 160, y: 700, w: 1100, color: C.placeholder });
    S.show(note, S.capAt(0) + 0.5);
  });

  // Scene 3: the G1 dial numbers, one trained copy, scores out of 100.
  Ch.scene('s03', function (S) {
    const c = S.c;
    const cols = [C.stop, C.stop, C.stop, C.thinker];
    const hb = S.hbars({
      x: 160, y: 230, w: 1080, labelW: 420, rowH: 80, gap: 20, max: 100, dec: 2,
      items: c.bars.map((b, i) => ({ label: b.label, value: b.value, color: cols[i] })),
    });
    hb.reveal(S.capAt(1), 0.4, 1.4);
    const chip = S.chip('tested', { x: 160, y: 690, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
    const note = S.text(c.note, { x: 160, y: 770, w: 1500, size: 32, color: C.soft });
    S.show(note, S.capAt(2) + 0.2);
  });

  // Scene 4: hard questions need more rounds (chain-5).
  Ch.scene('s04', function (S) {
    const c = S.c;
    const cols = [C.stop, C.stop, C.thinker];
    const hb = S.hbars({
      x: 160, y: 230, w: 1080, labelW: 420, rowH: 80, gap: 20, max: 100, dec: 1,
      items: c.bars.map((b, i) => ({ label: b.label, value: b.value, color: cols[i] })),
    });
    hb.reveal(S.capAt(1), 0.4, 1.4);
    const chip = S.chip('tested', { x: 160, y: 690, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
    const note = S.text(c.note, { x: 160, y: 770, w: 1500, size: 32, color: C.soft });
    S.show(note, S.capAt(2) + 0.2);
  });

  // Scene 5: too many rounds can cost points (one older probe).
  Ch.scene('s05', function (S) {
    const c = S.c;
    const a = S.box({ x: 160, y: 380, w: 620, h: 170, label: c.eight, color: C.thinker, size: 40 });
    const b = S.box({ x: 860, y: 380, w: 620, h: 170, label: c.sixteen, color: C.call, size: 40 });
    S.show(a, S.capAt(0));
    S.show(b, S.capAt(1));
    S.pulse(b, S.capAt(1) + 0.4);
    const big = S.text(c.big, { x: 160, y: 620, w: 1600, size: 96, weight: 800, color: C.call });
    S.pop(big, S.capAt(1) + 0.3);
    const chip = S.chip('tested', { x: 160, y: 770, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 6: after each round a tiny head reads the notes and gives a number; 0.5 or more stops.
  Ch.scene('s06', function (S) {
    const c = S.c;
    const th = S.box({ x: 120, y: 360, w: 360, h: 150, label: c.thinker, color: C.thinker, size: 40 });
    const hd = S.box({ x: 620, y: 360, w: 360, h: 150, label: c.head, color: C.stop, size: 40 });
    const svg = S.svg();
    const a1 = S.arrow(svg, 480, 435, 620, 435, { color: C.soft });
    const a2 = S.arrow(svg, 980, 435, 1120, 435, { color: C.soft });
    const meter = S.bar({ x: 1120, y: 420, w: 640, h: 44, value: 100, max: 100, color: C.stop });
    if (typeof gsap !== 'undefined') gsap.set(meter.fill, { transformOrigin: '0% 50%' });
    const line = S.svgEl(svg, 'rect', { x: 1438, y: 400, width: 4, height: 84, fill: C.ink });
    const lineTxt = S.text(c.line, { x: 1290, y: 500, w: 300, size: 32, align: 'center', color: C.ink });
    S.show(th, S.capAt(0));
    S.draw(a1, S.capAt(0) + 0.3, 0.5);
    S.show(hd, S.capAt(1));
    S.draw(a2, S.capAt(1) + 0.3, 0.5);
    S.show(meter.track, S.capAt(1) + 0.4);
    S.show(line, S.capAt(2));
    S.show(lineTxt, S.capAt(2));
    let t = S.capAt(2);
    if (typeof gsap !== 'undefined') {
      S.tl.to(meter.fill, { scaleX: 0.12, duration: 0.5, ease: 'none' }, t);
      S.tl.to(meter.fill, { scaleX: 0.31, duration: 0.5, ease: 'none' }, t + 0.7);
      S.tl.to(meter.fill, { scaleX: 0.58, duration: 0.5, ease: 'none' }, t + 1.4);
    }
    S.pulse(hd, S.capAt(3));
    const note = S.note(c.picture, { x: 120, y: 640, w: 1000, color: C.placeholder });
    S.show(note, S.capAt(3) - 0.5);
    const chip = S.chip('untested', { x: 1120, y: 640, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(3));
  });

  // Scene 7: one stop for the whole answer; calls may come at any round (built, untested).
  Ch.scene('s07', function (S) {
    const c = S.c;
    const xs = [];
    for (let i = 0; i < 10; i++) xs.push(160 + i * 166);
    const rounds = xs.map((x) => S.card({ x, y: 330, w: 140, h: 110, fill: C.card, color: C.line }));
    const rLabel = S.text(c.round, { x: 160, y: 280, w: 400, size: 36, color: C.soft });
    S.show(rLabel, S.capAt(0));
    S.stagger(rounds, S.capAt(0), 0.12);
    const calls = [1, 4, 7].map((i) => S.box({ x: xs[i], y: 480, w: 140, h: 90, label: c.call, color: C.call, size: 34 }));
    S.stagger(calls, S.capAt(1), 0.3);
    const bell = S.box({ x: xs[9], y: 480, w: 140, h: 90, label: c.bell, color: C.stop, size: 34 });
    S.show(bell, S.capAt(2));
    const note = S.note(c.picture, { x: 160, y: 640, w: 1000, color: C.placeholder });
    S.show(note, S.capAt(0) + 0.5);
    const chip = S.chip('untested', { x: 160, y: 740, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 8: the settled label on two made-up rows.
  Ch.scene('s08', function (S) {
    const c = S.c;
    const rowA = [];
    const rowB = [];
    for (let i = 0; i < 8; i++) {
      const x = 160 + i * 170;
      rowA.push(S.box({ x, y: 330, w: 150, h: 80, label: i < 3 ? c.go : c.stop, color: i < 3 ? C.card : C.stop, size: 34 }));
      rowB.push(S.box({ x, y: 520, w: 150, h: 80, label: c.stop, color: C.stop, size: 34 }));
    }
    const la = S.text(c.rowA, { x: 160, y: 280, w: 1400, size: 36, color: C.soft });
    const lb = S.text(c.rowB, { x: 160, y: 470, w: 1400, size: 36, color: C.soft });
    S.show(la, S.capAt(0));
    S.stagger(rowA, S.capAt(0), 0.15);
    S.show(lb, S.capAt(1));
    S.stagger(rowB, S.capAt(1), 0.15);
    const note = S.note(c.picture, { x: 160, y: 680, w: 1000, color: C.placeholder });
    S.show(note, S.capAt(0) + 0.5);
    const chip = S.chip('untested', { x: 160, y: 760, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 9: why the settled label counts only in full 32-round batches.
  Ch.scene('s09', function (S) {
    const c = S.c;
    const short = [];
    for (let i = 0; i < 8; i++) short.push(S.box({ x: 160 + i * 130, y: 340, w: 120, h: 70, label: c.stop, color: C.call, size: 30 }));
    const full = [];
    for (let i = 0; i < 12; i++) full.push(S.box({ x: 160 + i * 130, y: 540, w: 120, h: 70, label: i < 9 ? c.go : c.stop, color: i < 9 ? C.card : C.stop, size: 30 }));
    const ls = S.text(c.short, { x: 160, y: 290, w: 1400, size: 36, color: C.soft });
    const lf = S.text(c.full, { x: 160, y: 490, w: 1400, size: 36, color: C.soft });
    S.show(ls, S.capAt(0));
    S.stagger(short, S.capAt(0), 0.1);
    S.show(lf, S.capAt(2));
    S.stagger(full, S.capAt(2), 0.1);
    const note = S.note(c.picture, { x: 160, y: 680, w: 1000, color: C.placeholder });
    S.show(note, S.capAt(1));
    const chip = S.chip('untested', { x: 160, y: 760, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2) + 0.5);
  });

  // Scene 10: the risk: a stop that fires early is never shown a later right answer.
  Ch.scene('s10', function (S) {
    const c = S.c;
    const ran = [0, 1, 2].map((i) => S.box({ x: 160 + i * 170, y: 360, w: 150, h: 80, label: i < 2 ? c.go : c.stop, color: i < 2 ? C.card : C.stop, size: 34 }));
    const unseen = S.box({ x: 670, y: 360, w: 700, h: 80, label: c.unseen, color: C.placeholder, size: 34 });
    const lr = S.text(c.ran, { x: 160, y: 300, w: 1000, size: 36, color: C.soft });
    const le = S.text(c.early, { x: 330, y: 470, w: 300, size: 32, align: 'center', color: C.call });
    S.show(lr, S.capAt(0));
    S.stagger(ran, S.capAt(0), 0.2);
    S.show(le, S.capAt(1));
    S.show(unseen, S.capAt(2));
    const chip = S.chip('untested', { x: 160, y: 620, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 11: marks written in advance, drawn as empty dashed targets.
  Ch.scene('s11', function (S) {
    const c = S.c;
    const svg = S.svg();
    const la = S.text(c.barA, { x: 160, y: 290, w: 1400, size: 40, color: C.ink });
    const lb = S.text(c.barB, { x: 160, y: 470, w: 1400, size: 40, color: C.ink });
    const ra = S.svgEl(svg, 'rect', { x: 160, y: 340, width: 450, height: 80, fill: 'none', stroke: C.soft, 'stroke-width': 4, 'stroke-dasharray': '14 10' });
    const rb = S.svgEl(svg, 'rect', { x: 160, y: 520, width: 900, height: 80, fill: 'none', stroke: C.soft, 'stroke-width': 4, 'stroke-dasharray': '14 10' });
    S.show(la, S.capAt(0));
    S.show(ra, S.capAt(1));
    S.show(lb, S.capAt(1));
    S.show(rb, S.capAt(2));
    const tgt = S.text(c.target, { x: 160, y: 660, w: 1400, size: 40, color: C.soft });
    S.show(tgt, S.capAt(2));
    const chip = S.chip('placeholder', { x: 160, y: 740, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(3));
  });

  // Scene 12: the stop has no build switch; the fallback is T1SDR.
  Ch.scene('s12', function (S) {
    const c = S.c;
    const sw1 = S.box({ x: 160, y: 320, w: 500, h: 150, label: c.sw1, color: C.thinker, size: 36 });
    const sw2 = S.box({ x: 700, y: 320, w: 500, h: 150, label: c.sw2, color: C.thinker, size: 36 });
    const noSw = S.box({ x: 1240, y: 320, w: 500, h: 150, label: c.noSw, color: C.placeholder, size: 36 });
    const fb = S.box({ x: 700, y: 540, w: 500, h: 130, label: c.fallback, color: C.calc, size: 36 });
    S.show(sw1, S.capAt(0));
    S.show(sw2, S.capAt(0) + 0.3);
    S.show(noSw, S.capAt(0) + 0.8);
    S.pulse(noSw, S.capAt(0) + 1.2);
    S.show(fb, S.capAt(1));
    const chip = S.chip('untested', { x: 160, y: 740, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(2));
  });

  // Scene 13: fast and slow thinking as one looped thinker (suggested), then the recap.
  Ch.scene('s13', function (S) {
    const c = S.c;
    const svg = S.svg();
    const one = S.box({ x: 660, y: 240, w: 600, h: 130, label: c.one, color: C.thinker, size: 40 });
    const fast = S.box({ x: 160, y: 500, w: 560, h: 120, label: c.fast, color: C.reader, size: 36 });
    const slow = S.box({ x: 1200, y: 500, w: 560, h: 120, label: c.slow, color: C.stop, size: 36 });
    const a1 = S.arrow(svg, 800, 370, 440, 500, { color: C.soft });
    const a2 = S.arrow(svg, 1020, 370, 1400, 500, { color: C.soft });
    S.show(one, S.capAt(0));
    S.show(fast, S.capAt(0) + 0.3);
    S.show(slow, S.capAt(0) + 0.5);
    S.draw(a1, S.capAt(1), 0.5);
    S.draw(a2, S.capAt(1) + 0.3, 0.5);
    const chip = S.chip('placeholder', { x: 160, y: 700, label: c.chip, size: 34 });
    S.pop(chip, S.capAt(1));
    S.pulse(one, S.capAt(2));
  });
});
