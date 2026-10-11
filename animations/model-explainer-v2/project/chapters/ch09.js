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
    const extra = o.extra ? S.text(o.extra, { x: o.x + 300, y: o.y + 96, w: o.w - 330, size: 36, weight: 600 }) : null;
    return {
      big,
      play(t) {
        S.show(card, t); S.show(title, t + 0.15); S.show(big, t + 0.3);
        S.count(big, { from: o.from, to: o.to, dec: o.dec, comma: true }, t + 0.5, o.cdur || 1.8);
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
    const order = ['reader', 'thinker', 'stop', 'talker', 'calc'];
    const t = S.at(0.04);
    // the 3 arrows are inside the model: arrows[0] comes in with the thinker, arrows[1] with the stop switch, arrows[2] with the talker; the calculator (outside tool) has none
    order.forEach((k, i) => { S.show(m.parts[k], t + i * 0.3); if (i >= 1 && m.arrows[i - 1]) S.draw(m.arrows[i - 1], t + i * 0.3 + 0.25, 0.4); });
    const svg = S.svg();
    const loop = S.curve(svg, m.colC.thinker + 88, 448, m.colC.thinker - 88, 448, { color: C.thinker, bend: 170, width: 7, head: 20 });
    const note = S.note(c.note, { x: 100, y: 570, w: 1560, color: C.thinker, size: 40 });
    const design = S.note(c.design, { x: 100, y: 690, w: 1720, color: C.warn, size: 40 });
    S.pulse(m.parts.thinker, S.capAt(0) + 1.4);
    S.draw(loop, S.capAt(0) + 3.0, 1.0);
    S.show(note, S.capAt(0) + 4.2);
    S.show(design, S.capAt(1) + 1.0);
  });

  // ---------- s02: a score with nothing to compare it to ----------
  Ch.scene('s02', function (S) {
    const c = S.c;
    const big = S.text('', { x: 100, y: 275, w: 780, size: 200, weight: 800, color: C.thinker, lh: 1 });
    const unit = S.text(c.unit, { x: 106, y: 510, w: 760, size: 48, color: C.soft });
    const bar = S.bar({ x: 106, y: 605, w: 760, h: 56, value: c.score, max: 100, color: C.thinker });
    const cnt = S.text('', { x: 1000, y: 310, w: 800, size: 150, weight: 800, lh: 1 });
    const cntLab = S.text(c.rightLabel, { x: 1004, y: 485, w: 800, size: 46, color: C.soft });
    const design = S.note(c.design, { x: 1000, y: 600, w: 840, size: 40, color: C.warn });   // names the older design next to the 73.01
    const chip = S.chip('tested', { x: 106, y: 770, label: c.chip, size: 34 });
    let t = S.capAt(0);
    S.show(big, t + 0.2); S.count(big, { from: 0, to: c.score, dec: 2 }, t + 0.3, 1.8);
    S.show(bar.track, t + 0.4); S.grow(bar, t + 0.5, 1.8);
    S.show(unit, t + 1.2);
    S.show(design, t + 2.6);
    S.pop(chip, t + 3.0);
    t = S.capAt(1);
    S.show(cnt, t + 0.2); S.count(cnt, { from: 0, to: c.right, comma: true }, t + 0.3, 1.6);
    S.show(cntLab, t + 1.0);
  });

  // ---------- s03: what the 6,040 questions are ----------
  Ch.scene('s03', function (S) {
    const c = S.c;
    const tot = S.text('', { x: 560, y: 215, w: 800, size: 140, weight: 800, color: C.thinker, align: 'center', lh: 1 });
    const bw = 316, gap = 35, x0 = 100, by = 470;
    const boxes = c.kinds.map((k, i) => {
      const b = S.box({ x: x0 + i * (bw + gap), y: by, w: bw, h: 190, label: k.label, sub: nf(k.n), color: C.soft, size: 38, subSize: 56 });
      const sb = b.querySelector('.sub'); sb.style.fontWeight = '800'; sb.style.color = C.ink;
      // every label gets a two-line band, so a label that wraps ("New sentence frames") does not push its number lower than the others
      const lb = b.querySelector('.lab'); lb.style.minHeight = '90px'; lb.style.display = 'flex'; lb.style.alignItems = 'center'; lb.style.justifyContent = 'center';
      return b;
    });
    const svg = S.svg();
    const bends = [70, 40, 0, -40, -70];
    const arrows = boxes.map((b, i) => S.curve(svg, x0 + i * (bw + gap) + bw / 2, by - 6, 960 + (i - 2) * 80, 386, { color: C.soft, bend: bends[i], width: 4, head: 14 }));
    const gloss = S.note(c.gloss, { x: 100, y: 720, w: 1200, size: 40, color: C.soft });
    S.show(tot, S.capAt(0) + 0.3); S.count(tot, { from: 0, to: c.total, comma: true }, S.capAt(0) + 0.4, 2.2);
    S.stagger(boxes, S.capAt(1) + 0.3, 0.6);
    arrows.forEach((a, i) => S.draw(a, S.capAt(2) + 0.2 + i * 0.3, 0.8));
    S.pulse(tot, S.capAt(2) + 2.2);
    S.show(gloss, S.capAt(2) + 2.8);
  });

  // ---------- s04: turn the thinking down ----------
  Ch.scene('s04', function (S) {
    const c = S.c;
    const dial = makeDial(S, { cx: 400, cy: 500, R: 225, ticks: c.ticks, visit: c.rows.map((r) => r.rounds), units: c.rows.map((r) => r.label.replace(/^\d+\s*/, '')) });
    const head = S.text(c.scoreHead, { x: 1030, y: 262, w: 420, size: 32, color: C.soft });
    const hb = S.hbars({ x: 780, y: 330, w: 420, labelW: 250, rowH: 72, gap: 66, labelSize: 38, valueSize: 52, valueW: 220,
      items: c.rows.map((r) => ({ label: r.label, value: r.value, color: C.thinker, dec: 2 })) });
    const tchip = S.chip('tested', { x: 780, y: 200, label: c.testedChip, size: 30 });
    dial.start(S.at(0.03));
    S.show(head, S.capAt(0) + 0.4); S.pop(tchip, S.capAt(0) + 0.6);
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
    const tchip = S.chip('tested', { x: 780, y: 200, label: c.testedChip, size: 30 });
    dial.start(S.at(0.03));
    S.show(head, S.sec(0.8)); S.pop(tchip, S.sec(1.0));
    revealRow(S, hb.rows[0], S.sec(0.9), 1.0, 2);
    dial.go(1, S.sec(1.9), 1.4);
    // the 24-round bar counts up while the first sentence is on screen, so it has settled on 72.57 before the second sentence names it
    revealRow(S, hb.rows[1], S.sec(3.4), 1.2, 2);
    S.pop(chip, S.capAt(2) + 0.6);
  });

  // ---------- s06: multi-step questions ----------
  Ch.scene('s06', function (S) {
    const c = S.c;
    const ex = S.text(c.example, { x: 100, y: 270, w: 620, size: 46, weight: 600, lh: 1.25 });
    const tag = S.chip('placeholder', { x: 100, y: 440, label: c.illustration, size: 28 });
    const steps = S.note(c.stepsLabel, { x: 100, y: 540, w: 560, color: C.thinker, size: 38 });
    const head = S.text(c.scoreHead, { x: 1030, y: 262, w: 810, size: 32, color: C.soft });
    const tchip = S.chip('tested', { x: 780, y: 200, label: c.testedChip, size: 30 });
    const hb = S.hbars({ x: 780, y: 330, w: 420, labelW: 250, rowH: 62, gap: 40, labelSize: 36, valueSize: 48, valueW: 220,
      items: c.rows.map((r) => ({ label: r.label, value: r.value, color: C.thinker, dec: 1 })) });
    S.show(ex, S.capAt(0) + 0.3); S.show(tag, S.capAt(0) + 1.2); S.show(head, S.capAt(0) + 1.0); S.pop(tchip, S.capAt(0) + 1.4);
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
    // the cut: A's notes no longer reach the talker, so the arrow fades and a small cross sits in the gap (clear of both boxes)
    const x1 = S.path(svg, [[830, 326 + OY], [858, 354 + OY]], { color: C.warn, width: 9, head: 0 });
    const x2 = S.path(svg, [[858, 326 + OY], [830, 354 + OY]], { color: C.warn, width: 9, head: 0 });
    const wiring = S.note(c.wiring, { x: 90, y: 740, w: 960, size: 34, color: C.soft });
    const tchip = S.chip('tested', { x: 1130, y: 196, label: c.testedChip, size: 30 });
    const head = S.text(c.scoreHead, { x: 1130, y: 252, w: 710, size: 32, color: C.soft });
    const card1 = resultCard(S, { x: 1130, y: 294, w: 710, h: 260, title: c.cards[0].title, from: c.cards[0].was, to: c.cards[0].to, dec: 2, sub: c.cards[0].sub, extra: c.cards[0].extra, color: C.warn });
    const card2 = resultCard(S, { x: 1130, y: 568, w: 710, h: 260, title: c.cards[1].title, from: c.cards[1].was, to: c.cards[1].to, dec: 2, sub: c.cards[1].sub, color: C.warn, cdur: 1.4 });
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
    S.draw(swap, t, 1.0);
    S.hide(a2.line, t + 0.9, 0.3); S.hide(a2.head, t + 0.9, 0.3);
    S.draw(x1, t + 1.0, 0.25); S.draw(x2, t + 1.2, 0.25);
    S.tint(tkA, t + 1.6, { border: C.warn });
    S.show(head, S.capAt(1) + 1.3); S.pop(tchip, S.capAt(1) + 1.4);
    card1.play(S.capAt(1) + 1.6);
    S.pulse(nA, S.capAt(2) + 0.3); S.pulse(nB, S.capAt(2) + 0.3);
    card2.play(S.capAt(2) + 0.2);
    S.show(wiring, S.capAt(2) + 3.4);
  });

  // ---------- s08: break the calculator ----------
  Ch.scene('s08', function (S) {
    const c = S.c, L = c.labels, OY = 50;
    const svg = S.svg();
    const tag = S.chip('placeholder', { x: 90, y: 205, label: c.illustration, size: 28 });
    // the OLDER design tested here (G-B2): the calculator is built in, inside the frame, between thinker and talker
    const frame = S.card({ x: 70, y: 300, w: 1030, h: 340, r: 26, color: C.warn });
    const frameL = S.text(`<span style="background:${C.bg};padding:0 12px">${L.model}</span>`, { html: true, x: 90, y: 282, w: 520, size: 24, weight: 800, color: C.warn, lh: '34px' });
    const th = S.box({ x: 100, y: 400, w: 190, h: 120, label: L.thinker, color: C.thinker, size: 36 });
    const calc = S.card({ x: 400, y: 330, w: 420, h: 280, color: C.calc });
    const calcT = S.text(L.calc, { x: 400, y: 344, w: 420, size: 40, weight: 700, align: 'center', color: C.calc });
    const calcS = S.text(L.outside, { x: 400, y: 394, w: 420, size: 28, align: 'center', color: C.soft });
    const pAdd = S.box({ x: 416, y: 480, w: 190, h: 76, label: L.add, size: 34, color: C.calc });
    const pSub = S.box({ x: 614, y: 480, w: 190, h: 76, label: L.sub, size: 32, color: C.calc });
    const pAdd2 = S.box({ x: 416, y: 480, w: 190, h: 76, label: L.sub, size: 32, color: C.warn });
    const pSub2 = S.box({ x: 614, y: 480, w: 190, h: 76, label: L.add, size: 34, color: C.warn });
    const tk = S.box({ x: 910, y: 400, w: 170, h: 120, label: L.talker, color: C.talker, size: 34 });
    const svgA = S.svg();   // after the frame and boxes, so its arrows lie on top
    const call = S.arrow(svgA, 294, 440, 396, 440, { color: C.call, width: 5, head: 18 });
    const callL = S.text(L.call, { x: 296, y: 400, w: 100, size: 26, weight: 700, color: C.call, align: 'center' });
    const reply = S.arrow(svgA, 396, 490, 294, 490, { color: C.soft, width: 5, head: 18 });
    const replyL = S.text(L.reply, { x: 296, y: 500, w: 100, size: 26, weight: 700, color: C.soft, align: 'center' });
    const a2 = S.arrow(svgA, 824, 460, 904, 460, { color: C.soft, width: 5, head: 18 });
    const contrast = S.text(L.contrast, { x: 70, y: 665, w: 1030, size: 30, color: C.soft });
    const svg2 = S.svg();   // drawn after the card so the cross lies on top of it
    const cross1 = S.path(svg2, [[410, 340], [810, 600]], { color: C.warn, width: 10, head: 0 });
    const cross2 = S.path(svg2, [[810, 340], [410, 600]], { color: C.warn, width: 10, head: 0 });
    const tchip = S.chip('tested', { x: 1130, y: 196, label: c.testedChip, size: 30 });
    const head = S.text(c.scoreHead, { x: 1130, y: 252, w: 710, size: 32, color: C.soft });
    const cA = resultCard(S, { x: 1130, y: 294, w: 710, h: 260, title: c.cards[0].title, from: 0, to: c.cards[0].value, dec: 1, sub: c.cards[0].sub, color: C.thinker });
    const cB = resultCard(S, { x: 1130, y: 568, w: 710, h: 260, title: c.cards[1].title, from: c.cards[1].was, to: c.cards[1].to, dec: 1, sub: c.cards[1].sub, color: C.warn, cdur: 1.2 });
    let t = S.capAt(0) + 0.3;
    S.show(tag, t);
    S.show(frame, t + 0.2); S.show(frameL, t + 0.3);
    t = S.show(th, t + 0.5);
    S.show(calc, t + 0.3); S.show(calcT, t + 0.5); S.show(calcS, t + 0.6); S.show(pAdd, t + 0.8); S.show(pSub, t + 1.1);
    S.draw(call, t + 1.3, 0.4); S.show(callL, t + 1.5);
    S.draw(reply, t + 1.7, 0.4); S.show(replyL, t + 1.9);
    S.draw(a2, t + 2.1, 0.4); S.show(tk, t + 2.3);
    S.show(contrast, t + 2.8);
    t = S.capAt(0) + 5.2;
    S.hide(pAdd, t, 0.4); S.hide(pSub, t, 0.4);
    S.show(pAdd2, t + 0.3, { y: 0 }); S.show(pSub2, t + 0.3, { y: 0 });
    S.tint(tk, t + 0.8, { border: C.warn });
    // the swap card arrives while the first sentence ("...and the answers follow") is on screen, so 99.9 has settled before the second sentence
    S.show(head, S.capAt(0) + 6.0); S.pop(tchip, S.capAt(0) + 6.2);
    cA.play(S.capAt(0) + 6.4);
    t = S.capAt(2) + 0.2;
    S.hide(pAdd2, t, 0.3); S.hide(pSub2, t, 0.3);
    S.tint(calc, t, { border: C.warn });
    S.draw(cross1, t + 0.3, 0.4); S.draw(cross2, t + 0.6, 0.4);
    cB.play(S.capAt(2) + 0.9);
  });

  // ---------- s09: the leak ----------
  Ch.scene('s09', function (S) {
    const c = S.c;
    const X0 = 100, LW = 520, BW = 960;                     // the track is the same 0 to 100 track as every other chart
    const tchip = S.chip('tested', { x: X0 + LW, y: 196, label: c.testedChip, size: 30 });
    const sub = S.text(c.subtitle, { x: X0 + LW, y: 254, w: 1100, size: 32, color: C.soft });
    const cols = [C.ink, C.warn, C.thinker];                // neutral for the plain comparison, warning orange for the bar that breaks the pass mark
    const hb = S.hbars({ x: X0, y: 384, w: BW, labelW: LW, rowH: 76, gap: 56, dec: 2, labelSize: 36, valueSize: 54, valueW: 200,
      items: c.rows.map((r, i) => ({ label: r.label, value: r.value, color: cols[i], dec: 2 })) });
    const mx = X0 + LW + BW * c.mark / 100;
    const svg = S.svg();
    const mark = S.svgEl(svg, 'line', { x1: mx, y1: 352, x2: mx, y2: 730, stroke: C.ink, 'stroke-width': 5, 'stroke-dasharray': '16 10' });   // dashed: a limit, not a bar
    const markLab = S.text(c.markLabel + ' ' + c.mark, { x: mx - 210, y: 306, w: 420, size: 32, weight: 700, align: 'center', color: C.ink });
    const ax0 = S.text(c.axis[0], { x: X0 + LW, y: 738, w: 120, size: 32, color: C.soft });
    const ax1 = S.text(c.axis[1], { x: X0 + LW + BW - 200, y: 738, w: 200, size: 32, color: C.soft, align: 'right' });
    S.show(sub, S.capAt(0) + 0.3); S.pop(tchip, S.capAt(0) + 0.5);
    S.show(ax0, S.capAt(0) + 0.9); S.show(ax1, S.capAt(0) + 0.9);
    S.show(markLab, S.capAt(0) + 1.0); S.tl.to(mark, { autoAlpha: 1, duration: 0.6 }, S.capAt(0) + 1.2);
    // all three bars settle before the sentences that quote them (18.09 and 1.40 in the second, 0.96 in the third)
    revealRow(S, hb.rows[0], S.capAt(0) + 3.0, 1.0, 2);
    revealRow(S, hb.rows[1], S.capAt(0) + 4.0, 1.4, 2);
    revealRow(S, hb.rows[2], S.capAt(1) + 5.0, 1.4, 2);
  });

  // ---------- s10: side by side with a plain model ----------
  Ch.scene('s10', function (S) {
    const c = S.c, H = c.heads, HS = c.headSubs;
    const col = { ours: { x: 560, w: 380 }, plain: { x: 960, w: 380 }, calc: { x: 1360, w: 440 } };
    const clr = { ours: C.thinker, plain: C.placeholder, calc: C.calc };
    const keys = ['ours', 'plain', 'calc'];
    const tchip = S.chip('tested', { x: 90, y: 197, size: 30 });   // kit default word 'tested'; the caption says "on this one copy"
    const hd = {}, hs = {};
    keys.forEach((k) => {
      hd[k] = S.text(H[k], { x: col[k].x, y: 244, w: col[k].w, size: 40, weight: 800, align: 'center', color: clr[k] });
      hs[k] = S.text(HS[k], { x: col[k].x, y: 298, w: col[k].w, size: 30, align: 'center', color: C.soft });
    });
    const sizeLab = S.text(c.sizeLabel, { x: 100, y: 298, w: 440, size: 30, color: C.soft });
    // the two callouts together are as wide as the table (80 to 1840)
    const plainNote = S.note(c.plainNote, { x: 80, y: 716, w: 880, size: 32, color: C.soft });
    const gapNote = S.note(c.gapNote, { x: 980, y: 716, w: 860, size: 32, color: C.ink });
    const rowY = [352, 474, 596];
    const rows = c.table.map((r, i) => {
      const y = rowY[i];
      const bg = S.card({ x: 80, y: y - 12, w: 1760, h: 110 });
      const lab = S.text(r.label, { x: 100, y: y + 24, w: 440, size: 38, weight: 600 });
      const vals = {};
      keys.forEach((k) => { vals[k] = S.text(r[k] == null ? '–' : '', { x: col[k].x, y: y + 4, w: col[k].w, size: 68, weight: 800, align: 'center', color: clr[k] }); });
      return { bg, lab, vals, r };
    });
    // the gap of the third sentence is main test, ours minus plain + calculator: outline exactly those two cells
    const osvg = S.svg();
    const ring = (k, cx) => S.svgEl(osvg, 'rect', { x: cx - 120, y: rowY[0], width: 240, height: 94, rx: 16, fill: 'none', stroke: C.ink, 'stroke-width': 5 });
    const ringOurs = ring('ours', col.ours.x + col.ours.w / 2), ringCalc = ring('calc', col.calc.x + col.calc.w / 2);
    const showVal = (row, k, t) => {
      S.show(row.vals[k], t, { dur: 0.3 });
      if (row.r[k] != null) S.count(row.vals[k], { from: 0, to: row.r[k], dec: row.r.dec }, t + 0.1, 1.4);
    };
    let t = S.capAt(0) + 0.3;
    S.show(hd.ours, t); S.show(hs.ours, t + 0.2); S.show(sizeLab, t + 0.2); S.show(hd.plain, t + 0.4); S.show(hs.plain, t + 0.6);
    S.pop(tchip, t + 0.5);
    S.show(plainNote, S.capAt(0) + 1.4);
    [0, 1].forEach((i) => {
      const tt = S.capAt(0) + 1.8 + i * 2.6;
      S.show(rows[i].bg, tt); S.show(rows[i].lab, tt + 0.1); showVal(rows[i], 'ours', tt + 0.4); showVal(rows[i], 'plain', tt + 0.9);
    });
    S.pulse(rows[0].vals.ours, S.capAt(0) + 6.6);
    // the hours row builds at the end of the first sentence, so 6.51 and 2.38 have settled before the second sentence quotes them
    t = S.capAt(0) + 8.2;
    S.show(rows[2].bg, t); S.show(rows[2].lab, t + 0.1); showVal(rows[2], 'ours', t + 0.4); showVal(rows[2], 'plain', t + 0.9);
    // the calculator column builds at the end of the second sentence, so 69.62 and 99.0 have settled before the third sentence quotes them
    t = S.capAt(2) - 3.4;
    S.show(hd.calc, t); S.show(hs.calc, t + 0.2);
    showVal(rows[0], 'calc', t + 0.8); showVal(rows[1], 'calc', t + 1.6); showVal(rows[2], 'calc', t + 2.4);
    t = S.capAt(2) + 1.0;
    S.tl.to(ringOurs, { autoAlpha: 1, duration: 0.4 }, t); S.tl.to(ringCalc, { autoAlpha: 1, duration: 0.4 }, t + 0.2);
    S.show(gapNote, t + 0.6);
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
