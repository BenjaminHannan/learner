/* Demo chapter: shows every helper once. Copy this pattern. */
Kit.chapter('ch99', function (Ch) {
  const C = Kit.C;

  Ch.scene('s01', function (S) {
    const c = S.c;
    const q = S.text('', { x: 160, y: 270, w: 1600, size: 52, weight: 600 });
    S.type(q, c.question, S.at(0.05), 1.6);
    const svg = S.svg();
    const bx = [160, 700, 1240];
    const names = [c.labels.r, c.labels.t, c.labels.k];
    const cols = [C.reader, C.thinker, C.talker];
    const boxes = names.map((n, i) => S.box({ x: bx[i], y: 470, w: 460, h: 190, label: n, color: cols[i], size: 46 }));
    const a1 = S.arrow(svg, 630, 565, 700, 565, { color: C.soft });
    const a2 = S.arrow(svg, 1170, 565, 1240, 565, { color: C.soft });
    let t = S.at(0.25);
    S.show(boxes[0], t); t = S.draw(a1, t + 0.5, 0.5);
    S.show(boxes[1], t); t = S.draw(a2, t + 0.5, 0.5);
    S.show(boxes[2], t);
    const ans = S.text(c.answer, { x: 1240, y: 690, w: 460, size: 96, weight: 800, align: 'center', color: C.talker });
    S.pop(ans, S.at(0.75));
    S.pulse(boxes[1], S.at(0.5));
  });

  Ch.scene('s02', function (S) {
    const c = S.c;
    const hb = S.hbars({ x: 160, y: 300, w: 900, items: [
      { label: c.ours.label, value: c.ours.value, color: C.thinker },
      { label: c.plain.label, value: c.plain.value, color: C.placeholder },
    ] });
    hb.reveal(S.at(0.12));
    const chip = S.chip('tested', { x: 160, y: 590, label: c.tag });
    S.pop(chip, S.at(0.6));
    const note = S.text(c.unit, { x: 160, y: 660, w: 800, size: 32, color: C.soft });
    S.show(note, S.at(0.6));
  });

  Ch.scene('s03', function (S) {
    const m = S.modelMap({ x: 100, y: 330, w: 1720, h: 210 });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    let t = S.at(0.08);
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.25); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.25 + 0.3, 0.4); });
    const chips = [
      S.chip('tested', { x: 100 + 0 * 358, y: 600, label: 'tested' }),
      S.chip('tested', { x: 100 + 1 * 358, y: 600, label: 'tested' }),
      S.chip('tested', { x: 100 + 2 * 358, y: 600, label: 'tested' }),
      S.chip('untested', { x: 100 + 3 * 358, y: 600, label: 'never tested' }),
      S.chip('placeholder', { x: 100 + 4 * 358, y: 600, label: 'placeholder' }),
    ];
    S.stagger(chips, S.at(0.45), 0.3);
    S.pulse(m.parts.thinker, S.at(0.8));
  });

  Ch.scene('s04', function (S) {
    const c = S.c;
    const L = S.letters(c.word, { x: 160, y: 270, size: 56 });
    S.sweep(L.cells, S.capAt(0), 1.2);
    const v1 = S.vec({ x: 200, y: 520, n: 10, cell: 34, color: C.reader, seed: 3 });
    const v2 = S.vec({ x: 200, y: 640, n: 10, cell: 34, color: C.thinker, seed: 9 });
    const svg = S.svg();
    const k = S.curve(svg, L.cx(2), L.cy + 60, 380, 520, { color: C.reader, bend: 60 });
    S.show(v1, S.capAt(1)); S.draw(k, S.capAt(1) + 0.3, 0.8);
    S.show(v2, S.capAt(2));
    const n = S.note(c.note, { x: 760, y: 520, w: 960, color: C.untested });
    S.show(n, S.capAt(2) + 0.3);
  });
});
