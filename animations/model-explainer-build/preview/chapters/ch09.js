/* ch09: Does the thinking really do the work?
   Every word and number on screen comes from content/ch09.json (S.c). Code only holds symbols ("–"), list numbers on the recap badges,
   layout, and tiny helpers local to this chapter (the rounds dial, the result card). */
Kit.chapter('ch09', function (Ch) {
  const C = Kit.C;
  const nf = (v, dec) => Kit.fmt(v, { dec: dec || 0, comma: true });

  // ---------- local helpers ----------
  // Reveal one S.hbars row (label, track, counting value) and grow it. Returns the end time.
  function revealRow(S, r, t, dur, dec) {
    S.show(r.lab, t, { dur: 0.4 });
    S.show(r.track, t, { dur: 0.4 });
    S.show(r.val, t + 0.2, { dur: 0.3 });
    return S.grow(r.b, t + 0.3, dur, r.val, { dec: dec, comma: true });
  }

  // The rounds dial: a 270-degree dial from 0 to 24 rounds with a needle and a big readout.
  // o = {cx, cy, R, ticks:[...], visit:[v0, v1, ...] (the values the needle will rest on, in order), units:[word for each visit]}
  // dial.start(t) shows it at visit[0]; dial.go(i, t, dur) turns the needle to visit[i].
  function makeDial(S, o) {
    const cx = o.cx, cy = o.cy, R = o.R, max = 24, sv = cx + ' ' + cy;
    const ang = (v) => -135 + 270 * v / max;
    const X = (a, r) => cx + r * Math.sin(a * Math.PI / 180);
    const Y = (a, r) => cy - r * Math.cos(a * Math.PI / 180);
    const svg = S.svg();
    const base = S.svgEl(svg, 'g', {}, true);
    S.svgEl(base, 'path', { d: `M ${X(-135, R)} ${Y(-135, R)} A ${R} ${R} 0 1 1 ${X(135, R)} ${Y(135, R)}`, fill: 'none', stroke: C.line, 'stroke-width': 22, 'stroke-linecap': 'round' }, false);
    for (let v = 0; v <= max; v++) {
      const major = o.ticks.indexOf(v) >= 0, a = ang(v), r2 = R - (major ? 64 : 42);
      S.svgEl(base, 'line', { x1: X(a, R - 20), y1: Y(a, R - 20), x2: X(a, r2), y2: Y(a, r2), stroke: major ? C.ink : C.soft, 'stroke-width': major ? 6 : 3, 'stroke-linecap': 'round' }, false);
    }
    o.ticks.forEach((v) => {
      const a = ang(v);
      const tx = S.svgEl(base, 'text', { x: X(a, R + 52), y: Y(a, R + 52), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': 40, 'font-weight': 700, 'font-family': 'DejaVu Sans Mono, monospace', fill: C.ink }, false);
      tx.textContent = String(v);
    });
    const needle = S.svgEl(svg, 'g', {}, true);
    S.svgEl(needle, 'line', { x1: cx, y1: cy, x2: cx, y2: cy - (R - 34), stroke: C.thinker, 'stroke-width': 12, 'stroke-linecap': 'round' }, false);
    S.svgEl(needle, 'circle', { cx: cx, cy: cy, r: 22, fill: C.thinker }, false);
    gsap.set(needle, { rotation: ang(o.visit[0]), svgOrigin: sv });
    const unitEls = {};
    o.units.forEach((u) => { if (!unitEls[u]) unitEls[u] = S.text(u, { x: cx - 10, y: cy + 212, w: 220, size: 40, color: C.soft }); });
    const reads = o.visit.map((v) => S.text(String(v), { x: cx - 190, y: cy + 168, w: 170, size: 100, weight: 800, align: 'right', color: C.thinker, lh: 1 }));
    return {
      start(t) {
        S.show(base, t, { dur: 0.6 });
        S.tl.to(needle, { autoAlpha: 1, duration: 0.4 }, t + 0.4);
        S.show(unitEls[o.units[0]], t + 0.5, { dur: 0.4, y: 10 });
        S.show(reads[0], t + 0.5, { dur: 0.4, y: 10 });
        return t + 1.0;
      },
      go(i, t, dur) {
        S.tl.to(needle, { rotation: ang(o.visit[i]), svgOrigin: sv, duration: dur, ease: 'power2.inOut' }, t);
        S.hide(reads[i - 1], t, 0.25);
        S.show(reads[i], t + dur * 0.5, { dur: 0.4, y: 10 });
        if (o.units[i] !== o.units[i - 1]) { S.hide(unitEls[o.units[i - 1]], t, 0.25); S.show(unitEls[o.units[i]], t + dur * 0.5, { dur: 0.4, y: 10 }); }
        return t + dur;
      },
    };
  }

  // A result card with a number that counts from `from` to `to`. o = {x,y,w,h,title,from,to,dec,sub,extra,color}
  function resultCard(S, o) {
    const card = S.card({ x: o.x, y: o.y, w: o.w, h: o.h });
    const title = S.text(o.title, { x: o.x + 30, y: o.y + 18, w: o.w - 60, size: 36, weight: 700 });
    const big = S.text('', { x: o.x + 30, y: o.y + 70, w: 330, size: 112, weight: 800, color: o.color, lh: 1 });
    const sub = S.text(o.sub, { x: o.x + 30, y: o.y + o.h - 64, w: o.w - 60, size: 32, color: C.soft });
    const extra = o.extra ? S.text(o.extra, { x: o.x + 380, y: o.y + 96, w: o.w - 410, size: 36, weight: 600 }) : null;
    return {
      big,
      play(t) {
        S.show(card, t); S.show(title, t + 0.15); S.show(big, t + 0.3);
        S.count(big, { from: o.from, to: o.to, dec: o.dec, comma: true }, t + 0.5, 1.8);
        S.show(sub, t + 0.6);
        if (extra) S.show(extra, t + 2.0);
        return t + 2.4;
      },
    };
  }

  // ---------- s01: where we are ----------
  Ch.scene('s01', function (S) {
    const c = S.c;
    const m = S.modelMap({ x: 100, y: 250, w: 1720, h: 190, highlight: 'thinker' });
    const order = ['reader', 'thinker', 'calc', 'stop', 'talker'];
    const t = S.at(0.04);
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.3); if (m.arrows[i]) S.draw(m.arrows[i], t + i * 0.3 + 0.25, 0.4); });
    const svg = S.svg();
    const loop = S.curve(svg, 690, 448, 514, 448, { color: C.thinker, bend: 170, width: 7, head: 20 });
    const note = S.note(c.note, { x: 100, y: 640, w: 1120, color: C.thinker, size: 40 });
    S.pulse(m.parts.thinker, S.capAt(0) + 1.4);
    S.draw(loop, S.capAt(0) + 3.0, 1.0);
    S.show(note, S.capAt(0) + 4.2);
  });

  // ---------- s02: a score with nothing to compare it to ----------
  Ch.scene('s02', function (S) {
    const c = S.c;
    const big = S.text('', { x: 100, y: 275, w: 780, size: 200, weight: 800, color: C.thinker, lh: 1 });
    const unit = S.text(c.unit, { x: 106, y: 510, w: 760, size: 48, color: C.soft });
    const bar = S.bar({ x: 106, y: 605, w: 760, h: 56, value: c.score, max: 100, color: C.thinker });
    const cnt = S.text('', { x: 1000, y: 310, w: 800, size: 150, weight: 800, lh: 1 });
    const cntLab = S.text(c.rightLabel, { x: 1004, y: 485, w: 800, size: 46, color: C.soft });
    const chip = S.chip('tested', { x: 106, y: 740, label: c.chip, size: 30 });
    let t = S.capAt(0);
    S.show(big, t + 0.2); S.count(big, { from: 0, to: c.score, dec: 2 }, t + 0.3, 2.4);
    S.show(bar.track, t + 0.4); S.grow(bar, t + 0.5, 2.4);
    S.show(unit, t + 1.6);
    t = S.capAt(1);
    S.show(cnt, t + 0.2); S.count(cnt, { from: 0, to: c.right, comma: true }, t + 0.3, 2.0);
    S.show(cntLab, t + 1.2);
    S.pop(chip, t + 2.6);
  });

  // ---------- s03: what the 6,040 questions are ----------
  Ch.scene('s03', function (S) {
    const c = S.c;
    const tot = S.text('', { x: 560, y: 215, w: 800, size: 140, weight: 800, color: C.thinker, align: 'center', lh: 1 });
    const bw = 316, gap = 35, x0 = 100, by = 470;
    const boxes = c.kinds.map((k, i) => {
      const b = S.box({ x: x0 + i * (bw + gap), y: by, w: bw, h: 190, label: k.label, sub: nf(k.n), color: C.soft, size: 38, subSize: 56 });
      const sb = b.querySelector('.sub'); sb.style.fontWeight = '800'; sb.style.color = C.ink;
      return b;
    });
    const svg = S.svg();
    const bends = [70, 40, 0, -40, -70];
    const arrows = boxes.map((b, i) => S.curve(svg, x0 + i * (bw + gap) + bw / 2, by - 6, 960 + (i - 2) * 80, 372, { color: C.soft, bend: bends[i], width: 4, head: 14 }));
    S.show(tot, S.capAt(0) + 0.3); S.count(tot, { from: 0, to: c.total, comma: true }, S.capAt(0) + 0.4, 2.2);
    S.stagger(boxes, S.capAt(1) + 0.3, 0.6);
    arrows.forEach((a, i) => S.draw(a, S.capAt(2) + 0.2 + i * 0.3, 0.8));
    S.pulse(tot, S.capAt(2) + 2.2);
  });

  // ---------- s04: turn the thinking down ----------
  Ch.scene('s04', function (S) {
    const c = S.c;
    const dial = makeDial(S, { cx: 400, cy: 500, R: 225, ticks: c.ticks, visit: c.rows.map((r) => r.rounds), units: c.rows.map((r) => r.label.replace(/^\d+\s*/, '')) });
    const head = S.text(c.scoreHead, { x: 1030, y: 262, w: 420, size: 32, color: C.soft });
    const hb = S.hbars({ x: 780, y: 330, w: 420, labelW: 250, rowH: 72, gap: 66, labelSize: 38, valueSize: 52, valueW: 220,
      items: c.rows.map((r) => ({ label: r.label, value: r.value, color: C.thinker, dec: 2 })) });
    dial.start(S.at(0.03));
    S.show(head, S.capAt(0) + 0.4);
    revealRow(S, hb.rows[0], S.capAt(0) + 0.8, 1.8, 2);
    dial.go(1, S.capAt(1) + 0.3, 1.6); revealRow(S, hb.rows[1], S.capAt(1) + 1.2, 1.4, 2);
    dial.go(2, S.capAt(2) + 0.2, 0.9); revealRow(S, hb.rows[2], S.capAt(2) + 0.7, 1.0, 2);
    dial.go(3, S.capAt(3) + 0.1, 1.3); revealRow(S, hb.rows[3], S.capAt(3) + 0.6, 1.2, 2);
  });

  // ---------- s05: more rounds than it practised ----------
  Ch.scene('s05', function (S) {
    const c = S.c;
    const dial = makeDial(S, { cx: 400, cy: 500, R: 225, ticks: c.ticks, visit: c.rows.map((r) => r.rounds), units: c.rows.map((r) => r.label.replace(/^\d+\s*/, '')) });
    const head = S.text(c.scoreHead, { x: 1030, y: 292, w: 420, size: 32, color: C.soft });
    const hb = S.hbars({ x: 780, y: 360, w: 420, labelW: 250, rowH: 72, gap: 90, labelSize: 38, valueSize: 52, valueW: 220,
      items: c.rows.map((r) => ({ label: r.label, value: r.value, color: C.thinker, dec: 2 })) });
    const chip = S.chip('untested', { x: 780, y: 680, label: c.chip, size: 30 });
    dial.start(S.at(0.03));
    S.show(head, S.sec(1.2));
    revealRow(S, hb.rows[0], S.sec(1.4), 1.6, 2);
    dial.go(1, S.capAt(0) + 1.0, 2.2);
    revealRow(S, hb.rows[1], S.capAt(1) + 0.4, 1.6, 2);
    S.pop(chip, S.capAt(2) + 0.6);
  });

  // ---------- s06: multi-step questions ----------
  Ch.scene('s06', function (S) {
    const c = S.c;
    const ex = S.text(c.example, { x: 100, y: 270, w: 620, size: 46, weight: 600, lh: 1.25 });
    const tag = S.chip('placeholder', { x: 100, y: 440, label: c.illustration, size: 28 });
    const steps = S.note(c.stepsLabel, { x: 100, y: 540, w: 560, color: C.thinker, size: 38 });
    const head = S.text(c.scoreHead, { x: 1030, y: 262, w: 420, size: 32, color: C.soft });
    const hb = S.hbars({ x: 780, y: 330, w: 420, labelW: 250, rowH: 62, gap: 40, labelSize: 36, valueSize: 48, valueW: 220,
      items: c.rows.map((r) => ({ label: r.label, value: r.value, color: C.thinker, dec: 1 })) });
    S.show(ex, S.capAt(0) + 0.3); S.show(tag, S.capAt(0) + 1.2); S.show(head, S.capAt(0) + 1.0);
    S.show(steps, S.capAt(1) + 0.4);
    const t1 = S.capAt(1) + 2.8, t2 = S.capAt(2) + 0.5;
    [0, 1, 2].forEach((i) => revealRow(S, hb.rows[i], t1 + i * 0.8, 1.2, 1));
    [3, 4].forEach((i) => revealRow(S, hb.rows[i], t2 + (i - 3) * 0.9, 1.6, 1));
  });

  // ---------- s07: break the notes ----------
  Ch.scene('s07', function (S) {
    const c = S.c, L = c.labels, OY = 50;
    const svg = S.svg();
    const tag = S.chip('placeholder', { x: 90, y: 205, label: c.illustration, size: 28 });
    const badgeA = S.box({ x: 90, y: 300 + OY, w: 84, h: 84, label: L.a, size: 44, color: C.soft });
    const thA = S.box({ x: 200, y: 280 + OY, w: 220, h: 120, label: L.thinker, color: C.thinker, size: 38 });
    const a1 = S.arrow(svg, 424, 340 + OY, 478, 340 + OY, { color: C.soft, width: 5, head: 18 });
    const labA = S.text(L.notes, { x: 486, y: 262 + OY, w: 323, size: 32, color: C.soft, align: 'center' });
    const nA = S.vec({ x: 486, y: 322 + OY, n: 8, cell: 36, gap: 5, color: C.thinker, seed: 3 });
    const a2 = S.arrow(svg, 818, 340 + OY, 872, 340 + OY, { color: C.soft, width: 5, head: 18 });
    const tkA = S.box({ x: 878, y: 280 + OY, w: 190, h: 120, label: L.talker, color: C.talker, size: 38 });
    const badgeB = S.box({ x: 90, y: 530 + OY, w: 84, h: 84, label: L.b, size: 44, color: C.soft });
    const thB = S.box({ x: 200, y: 510 + OY, w: 220, h: 120, label: L.thinker, color: C.thinker, size: 38 });
    const b1 = S.arrow(svg, 424, 570 + OY, 478, 570 + OY, { color: C.soft, width: 5, head: 18 });
    const nB = S.vec({ x: 486, y: 552 + OY, n: 8, cell: 36, gap: 5, color: C.thinker, seed: 11 });
    const swap = S.curve(svg, 814, 556 + OY, 968, 408 + OY, { color: C.warn, bend: 60, width: 8, head: 22 });
    const x1 = S.path(svg, [[826, 320 + OY], [864, 360 + OY]], { color: C.warn, width: 9, head: 0 });
    const x2 = S.path(svg, [[864, 320 + OY], [826, 360 + OY]], { color: C.warn, width: 9, head: 0 });
    const wiring = S.note(c.wiring, { x: 90, y: 740, w: 960, size: 34, color: C.untested });
    const head = S.text(c.scoreHead, { x: 1130, y: 222, w: 710, size: 32, color: C.soft });
    const card1 = resultCard(S, { x: 1130, y: 270, w: 710, h: 260, title: c.cards[0].title, from: c.cards[0].was, to: c.cards[0].to, dec: 2, sub: c.cards[0].sub, extra: c.cards[0].extra, color: C.warn });
    const card2 = resultCard(S, { x: 1130, y: 555, w: 710, h: 260, title: c.cards[1].title, from: c.cards[1].was, to: c.cards[1].to, dec: 2, sub: c.cards[1].sub, color: C.warn });
    let t = S.capAt(0) + 0.3;
    S.show(tag, t);
    t = S.stagger([badgeA, thA], t + 0.2, 0.35);
    t = S.draw(a1, t, 0.4);
    S.show(labA, t); t = S.show(nA, t);
    t = S.draw(a2, t, 0.4);
    S.show(tkA, t);
    t = S.capAt(0) + 4.2;
    S.stagger([badgeB, thB], t, 0.35); S.draw(b1, t + 0.8, 0.4); S.show(nB, t + 1.3);
    t = S.capAt(1) + 0.4;
    S.draw(swap, t, 1.0); S.draw(x1, t + 1.0, 0.25); S.draw(x2, t + 1.2, 0.25);
    S.tint(tkA, t + 1.6, { border: C.warn });
    S.show(head, S.capAt(1) + 1.3);
    card1.play(S.capAt(1) + 1.6);
    S.pulse(nA, S.capAt(2) + 0.3); S.pulse(nB, S.capAt(2) + 0.3);
    card2.play(S.capAt(2) + 0.6);
    S.show(wiring, S.capAt(2) + 3.4);
  });

  // ---------- s08: break the calculator ----------
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.labels, OY = 50;
    const svg = S.svg();
    const tag = S.chip('placeholder', { x: 90, y: 205, label: c.illustration, size: 28 });
    const th = S.box({ x: 90, y: 350 + OY, w: 210, h: 120, label: L.thinker, color: C.thinker, size: 36 });
    const a1 = S.arrow(svg, 304, 410 + OY, 358, 410 + OY, { color: C.soft, width: 5, head: 18 });
    const calc = S.card({ x: 364, y: 270 + OY, w: 460, h: 280, color: C.calc });
    const calcT = S.text(L.calc, { x: 364, y: 288 + OY, w: 460, size: 40, weight: 700, align: 'center', color: C.calc });
    const pAdd = S.box({ x: 384, y: 390 + OY, w: 200, h: 76, label: L.add, size: 34, color: C.calc });
    const pSub = S.box({ x: 604, y: 390 + OY, w: 200, h: 76, label: L.sub, size: 32, color: C.calc });
    const pAdd2 = S.box({ x: 384, y: 390 + OY, w: 200, h: 76, label: L.sub, size: 32, color: C.warn });
    const pSub2 = S.box({ x: 604, y: 390 + OY, w: 200, h: 76, label: L.add, size: 34, color: C.warn });
    const a2 = S.arrow(svg, 828, 410 + OY, 882, 410 + OY, { color: C.soft, width: 5, head: 18 });
    const tk = S.box({ x: 888, y: 350 + OY, w: 190, h: 120, label: L.talker, color: C.talker, size: 38 });
    const svg2 = S.svg();   // drawn after the card so the cross lies on top of it
    const cross1 = S.path(svg2, [[392, 300 + OY], [796, 540 + OY]], { color: C.warn, width: 10, head: 0 });
    const cross2 = S.path(svg2, [[796, 300 + OY], [392, 540 + OY]], { color: C.warn, width: 10, head: 0 });
    const head = S.text(c.scoreHead, { x: 1130, y: 222, w: 710, size: 32, color: C.soft });
    const cA = resultCard(S, { x: 1130, y: 270, w: 710, h: 260, title: c.cards[0].title, from: 0, to: c.cards[0].value, dec: 1, sub: c.cards[0].sub, color: C.thinker });
    const cB = resultCard(S, { x: 1130, y: 555, w: 710, h: 260, title: c.cards[1].title, from: c.cards[1].was, to: c.cards[1].to, dec: 1, sub: c.cards[1].sub, color: C.warn });
    let t = S.capAt(0) + 0.3;
    S.show(tag, t);
    t = S.show(th, t + 0.2);
    t = S.draw(a1, t, 0.4);
    S.show(calc, t); S.show(calcT, t + 0.2); S.show(pAdd, t + 0.5); S.show(pSub, t + 0.8);
    S.draw(a2, t + 1.2, 0.4); S.show(tk, t + 1.6);
    t = S.capAt(0) + 5.2;
    S.hide(pAdd, t, 0.4); S.hide(pSub, t, 0.4);
    S.show(pAdd2, t + 0.3, { y: 0 }); S.show(pSub2, t + 0.3, { y: 0 });
    S.tint(tk, t + 0.8, { border: C.warn });
    S.show(head, S.capAt(1) + 0.3);
    cA.play(S.capAt(1) + 0.6);
    t = S.capAt(2) + 0.2;
    S.hide(pAdd2, t, 0.3); S.hide(pSub2, t, 0.3);
    S.tint(calc, t, { border: C.warn });
    S.draw(cross1, t + 0.3, 0.4); S.draw(cross2, t + 0.6, 0.4);
    cB.play(S.capAt(2) + 1.2);
  });

  // ---------- s09: the leak ----------
  Ch.scene('s09', function (S) {
    const c = S.c;
    const X0 = 100, LW = 520, BW = 700, MAX = 20;
    const sub = S.text(c.subtitle, { x: X0 + LW, y: 250, w: 900, size: 32, color: C.soft });
    const cols = [C.placeholder, C.warn, C.thinker];
    const hb = S.hbars({ x: X0, y: 370, w: BW, labelW: LW, rowH: 76, gap: 56, max: MAX, dec: 2, labelSize: 36, valueSize: 54, valueW: 220,
      items: c.rows.map((r, i) => ({ label: r.label, value: r.value, color: cols[i], dec: 2 })) });
    const mx = X0 + LW + BW * c.mark / MAX;
    const svg = S.svg();
    const mark = S.path(svg, [[mx, 345], [mx, 730]], { color: C.warn, width: 5, head: 0 });
    const markLab = S.text(c.markLabel + ': ' + c.mark, { x: mx - 160, y: 300, w: 320, size: 32, weight: 700, align: 'center', color: C.warn });
    S.show(sub, S.capAt(0) + 0.3);
    S.show(markLab, S.capAt(0) + 1.2); S.draw(mark, S.capAt(0) + 1.4, 0.9);
    revealRow(S, hb.rows[0], S.capAt(1) + 0.4, 1.2, 2);
    revealRow(S, hb.rows[1], S.capAt(1) + 1.8, 2.2, 2);
    revealRow(S, hb.rows[2], S.capAt(2) + 0.4, 1.4, 2);
  });

  // ---------- s10: side by side with a plain model ----------
  Ch.scene('s10', function (S) {
    const c = S.c, H = c.heads, HS = c.headSubs;
    const col = { ours: { x: 560, w: 380 }, plain: { x: 960, w: 380 }, calc: { x: 1360, w: 440 } };
    const clr = { ours: C.thinker, plain: C.placeholder, calc: C.calc };
    const keys = ['ours', 'plain', 'calc'];
    const hd = {}, hs = {};
    keys.forEach((k) => {
      hd[k] = S.text(H[k], { x: col[k].x, y: 216, w: col[k].w, size: 40, weight: 800, align: 'center', color: clr[k] });
      hs[k] = S.text(HS[k], { x: col[k].x, y: 268, w: col[k].w, size: 30, align: 'center', color: C.soft });
    });
    const rowY = [350, 490, 630];
    const rows = c.table.map((r, i) => {
      const y = rowY[i];
      const bg = S.card({ x: 80, y: y - 12, w: 1760, h: 118 });
      const lab = S.text(r.label, { x: 100, y: y + 24, w: 440, size: 38, weight: 600 });
      const vals = {};
      keys.forEach((k) => { vals[k] = S.text(r[k] == null ? '–' : '', { x: col[k].x, y: y + 4, w: col[k].w, size: 68, weight: 800, align: 'center', color: clr[k] }); });
      return { bg, lab, vals, r };
    });
    const showVal = (row, k, t) => {
      S.show(row.vals[k], t, { dur: 0.3 });
      if (row.r[k] != null) S.count(row.vals[k], { from: 0, to: row.r[k], dec: row.r.dec }, t + 0.1, 1.4);
    };
    let t = S.capAt(0) + 0.3;
    S.show(hd.ours, t); S.show(hs.ours, t + 0.2); S.show(hd.plain, t + 0.4); S.show(hs.plain, t + 0.6);
    [0, 1].forEach((i) => {
      const tt = S.capAt(0) + 1.8 + i * 2.6;
      S.show(rows[i].bg, tt); S.show(rows[i].lab, tt + 0.1); showVal(rows[i], 'ours', tt + 0.4); showVal(rows[i], 'plain', tt + 0.9);
    });
    S.pulse(rows[0].vals.ours, S.capAt(0) + 6.6);
    t = S.capAt(1) + 0.5;
    S.show(rows[2].bg, t); S.show(rows[2].lab, t + 0.1); showVal(rows[2], 'ours', t + 0.4); showVal(rows[2], 'plain', t + 0.9);
    t = S.capAt(2) + 0.3;
    S.show(hd.calc, t); S.show(hs.calc, t + 0.2);
    showVal(rows[0], 'calc', t + 1.0); showVal(rows[1], 'calc', t + 2.4); showVal(rows[2], 'calc', t + 3.4);
  });

  // ---------- s11: what this does not show ----------
  Ch.scene('s11', function (S) {
    const c = S.c;
    const items = c.rows.map((r, i) => {
      const y = 290 + i * 135;
      const chip = S.chip(r.kind, { x: 100, y: y, label: r.label, size: 30, color: r.color ? C[r.color] : undefined });
      const txt = S.text(r.text, { x: 560, y: y - 4, w: 1260, size: 44, weight: 600 });
      return { chip, txt };
    });
    const at = [S.capAt(0) + 1.0, S.capAt(0) + 2.8, S.capAt(1) + 1.0, S.capAt(1) + 2.8];
    items.forEach((it, i) => { S.pop(it.chip, at[i]); S.show(it.txt, at[i] + 0.3); });
  });

  // ---------- s12: recap ----------
  Ch.scene('s12', function (S) {
    const c = S.c;
    const head = S.text(c.scoreHead, { x: 250, y: 226, w: 700, size: 32, color: C.soft });
    S.show(head, S.at(0.08));
    c.lines.forEach((ln, i) => {
      const y = 290 + i * 160;
      const b = S.box({ x: 100, y: y, w: 100, h: 100, label: String(i + 1), size: 56, color: C.thinker });
      const tx = S.text(ln, { x: 250, y: y + 8, w: 1560, size: 52, weight: 600, lh: 1.2 });
      const t = S.at(0.16 + i * 0.17);
      S.pop(b, t); S.show(tx, t + 0.3);
    });
  });
});
