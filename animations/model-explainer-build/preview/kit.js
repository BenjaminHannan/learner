/* Scene kit for the long explainer. Every helper is seek-safe: initial states are set at build time with gsap.set,
   tweens always state their visible end state, and nothing random or wall-clock is used. Do not edit per chapter. */
(function () {
  const SVGNS = 'http://www.w3.org/2000/svg';
  const K = (window.Kit = { chapters: {} });

  K.C = {
    ink: '#1F2430', soft: '#5B6475', bg: '#FBF7F0', card: '#FFFFFF', line: '#E4DAC8', track: '#EFE8DA',
    reader: '#0F8B8D', thinker: '#4F46E5', call: '#E4572E', calc: '#64748B', stop: '#9333EA', talker: '#DB2777',
    tested: '#16875A', untested: '#C77D00', placeholder: '#7B8494', hand: '#8A5A2B', learned: '#2F6FEB', warn: '#C2410C',
    good: '#16875A',
  };
  const C = K.C;

  // Deterministic random numbers (mulberry32). NEVER use Math.random: renders must be identical every time.
  K.rng = function (seed) {
    let a = (seed || 1) >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  // Chapter files call: Kit.chapter('ch03', function (Ch) { Ch.scene('s01', function (S) { ... }); });
  K.chapter = function (id, build) {
    K.chapters[id] = { scenes: {} };
    build({
      id,
      data: (window.CONTENT && window.CONTENT.chapters && window.CONTENT.chapters[id]) || {},
      scene(sceneId, fn) { K.chapters[id].scenes[sceneId] = fn; },
    });
  };

  function fmt(v, o) {
    const dec = o.dec || 0;
    let s = Math.abs(v).toFixed(dec);
    if (o.comma) { const p = s.split('.'); p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ','); s = p.join('.'); }
    return (v < 0 ? '-' : '') + (o.pre || '') + s + (o.suf || '');
  }
  K.fmt = fmt;

  function el(tag, cls, parent) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (parent) parent.appendChild(e);
    return e;
  }

  class Scene {
    constructor(tl, root, c, t0, d, chapter) {
      this.tl = tl; this.root = root; this.c = c; this.t0 = t0; this.d = d; this.end = t0 + d; this.chapter = chapter;
      this.g = el('div', 'g', root);
      this.C = C;
    }
    // ---------- time ----------
    // at(f): f is a fraction 0..1 of THIS scene's length. Prefer it, so slowing a scene stretches the beats with it.
    at(f) { return this.t0 + Math.max(0, Math.min(1, f)) * this.d; }
    // sec(s): seconds after the scene starts (capped inside the scene).
    sec(s) { return this.t0 + Math.max(0, Math.min(s, this.d - 0.05)); }
    // capAt(i): the time caption number i (0-based) starts. Use it to sync a picture with the sentence that explains it.
    capAt(i) { const c = this.capTimes; return c && c.length ? c[Math.min(i, c.length - 1)] : this.at(0.1); }

    // ---------- elements (all start hidden unless opts.hidden === false) ----------
    _place(e, o) {
      e.style.left = (o.x || 0) + 'px'; e.style.top = (o.y || 0) + 'px';
      if (o.w != null) e.style.width = o.w + 'px';
      if (o.h != null) e.style.height = o.h + 'px';
      if (o.hidden !== false) gsap.set(e, { autoAlpha: 0 });
      return e;
    }
    text(str, o = {}) {
      const e = el('div', 't' + (o.mono ? ' mono' : ''), o.parent || this.g);
      if (o.html) e.innerHTML = str; else e.textContent = str;
      e.style.fontSize = (o.size || 40) + 'px';
      if (o.weight) e.style.fontWeight = o.weight;
      e.style.color = o.color || C.ink;
      e.style.textAlign = o.align || 'left';
      if (o.lh) e.style.lineHeight = o.lh;
      if (o.italic) e.style.fontStyle = 'italic';
      if (o.nowrap) e.style.whiteSpace = 'nowrap';
      if (o.w == null) o.w = 1200;
      return this._place(e, o);
    }
    box(o = {}) {
      const e = el('div', 'box', o.parent || this.g);
      e.style.borderColor = o.color || C.line;
      e.style.background = o.fill || '#fff';
      if (o.r != null) e.style.borderRadius = o.r + 'px';
      if (o.border != null) e.style.borderWidth = o.border + 'px';
      if (o.label != null) { const l = el('div', 'lab', e); l.textContent = o.label; l.style.fontSize = (o.size || 34) + 'px'; l.style.color = o.textColor || C.ink; }
      if (o.sub != null) { const s = el('div', 'sub', e); s.textContent = o.sub; s.style.fontSize = (o.subSize || Math.round((o.size || 34) * 0.7)) + 'px'; }
      return this._place(e, o);
    }
    card(o = {}) {
      const e = el('div', 'card', o.parent || this.g);
      if (o.fill) e.style.background = o.fill;
      if (o.color) e.style.borderColor = o.color;
      if (o.r != null) e.style.borderRadius = o.r + 'px';
      return this._place(e, o);
    }
    // kind: tested | untested | placeholder | hand | learned | custom color via o.color. label defaults per kind.
    chip(kind, o = {}) {
      const defaults = { tested: 'tested', untested: 'built, never tested', placeholder: 'placeholder', hand: 'hand-written', learned: 'learned' };
      const e = el('div', 'chip', o.parent || this.g);
      const col = o.color || C[kind] || C.soft;
      e.style.color = col; e.style.borderColor = col;
      e.textContent = o.label || defaults[kind] || kind;
      if (o.size) e.style.fontSize = o.size + 'px';
      return this._place(e, o);
    }
    bar(o = {}) {
      const track = el('div', 'track', o.parent || this.g);
      track.style.width = (o.w || 800) + 'px'; track.style.height = (o.h || 44) + 'px';
      const fill = el('div', 'fill', track);
      const frac = Math.max(0, Math.min(1, o.value / (o.max || 100)));
      fill.style.width = '100%'; fill.style.background = o.color || C.thinker;
      gsap.set(fill, { scaleX: 0 });
      this._place(track, o);
      return { track, fill, frac, value: o.value, o };
    }
    // Inline SVG layer: returns the <svg>. Draw with S.svgEl(svg,'path',{d:...,stroke:...}).
    svg(o = {}) {
      const s = document.createElementNS(SVGNS, 'svg');
      s.setAttribute('width', o.w || 1920); s.setAttribute('height', o.h || 1080);
      s.setAttribute('viewBox', `0 0 ${o.w || 1920} ${o.h || 1080}`);
      s.style.position = 'absolute'; s.style.left = (o.x || 0) + 'px'; s.style.top = (o.y || 0) + 'px'; s.style.overflow = 'visible';
      (o.parent || this.g).appendChild(s);
      if (o.hidden === true) gsap.set(s, { autoAlpha: 0 });
      return s;
    }
    svgEl(svg, tag, attrs = {}, hidden = true) {
      const e = document.createElementNS(SVGNS, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      svg.appendChild(e);
      if (hidden) gsap.set(e, { autoAlpha: 0 });
      return e;
    }
    // A drawable arrow: line + separate head (so the head only shows when the line has arrived).
    arrow(svg, x1, y1, x2, y2, o = {}) {
      const col = o.color || C.ink, w = o.width || 6, hl = o.head || 22;
      const ang = Math.atan2(y2 - y1, x2 - x1);
      const bx = x2 - Math.cos(ang) * hl * 0.8, by = y2 - Math.sin(ang) * hl * 0.8;
      const line = this.svgEl(svg, 'path', { d: `M ${x1} ${y1} L ${bx} ${by}`, stroke: col, 'stroke-width': w, fill: 'none', 'stroke-linecap': 'butt' }, false);
      const len = Math.max(1, Math.hypot(bx - x1, by - y1));
      line.setAttribute('stroke-dasharray', String(len)); line.setAttribute('stroke-dashoffset', String(len));
      const px = Math.cos(ang + Math.PI / 2) * hl * 0.5, py = Math.sin(ang + Math.PI / 2) * hl * 0.5;
      const head = this.svgEl(svg, 'path', { d: `M ${x2} ${y2} L ${bx + px} ${by + py} L ${bx - px} ${by - py} Z`, fill: col }, true);
      gsap.set(line, { autoAlpha: 0 });
      return { line, head, len };
    }
    // A drawable polyline through points [[x,y],...] with a head on the last segment.
    path(svg, pts, o = {}) {
      const col = o.color || C.ink, w = o.width || 6, hl = o.head === 0 ? 0 : (o.head || 22);
      let d = `M ${pts[0][0]} ${pts[0][1]}`;
      const last = pts[pts.length - 1], prev = pts[pts.length - 2];
      const ang = Math.atan2(last[1] - prev[1], last[0] - prev[0]);
      const ex = hl ? last[0] - Math.cos(ang) * hl * 0.8 : last[0], ey = hl ? last[1] - Math.sin(ang) * hl * 0.8 : last[1];
      for (let i = 1; i < pts.length - 1; i++) d += ` L ${pts[i][0]} ${pts[i][1]}`;
      d += ` L ${ex} ${ey}`;
      const line = this.svgEl(svg, 'path', { d, stroke: col, 'stroke-width': w, fill: 'none', 'stroke-linejoin': 'round' }, false);
      let len = 0;
      { const q = pts.slice(0, -1).concat([[ex, ey]]); for (let i = 1; i < q.length; i++) len += Math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]); }
      len = Math.max(1, len);
      line.setAttribute('stroke-dasharray', String(len)); line.setAttribute('stroke-dashoffset', String(len));
      let head = null;
      if (hl) {
        const px = Math.cos(ang + Math.PI / 2) * hl * 0.5, py = Math.sin(ang + Math.PI / 2) * hl * 0.5;
        head = this.svgEl(svg, 'path', { d: `M ${last[0]} ${last[1]} L ${ex + px} ${ey + py} L ${ex - px} ${ey - py} Z`, fill: col }, true);
      }
      gsap.set(line, { autoAlpha: 0 });
      return { line, head, len };
    }

    // A drawable curve (quadratic) from (x1,y1) to (x2,y2). o.bend = pixels the middle is pushed sideways (+ = left of travel). o.head=0 for no head.
    curve(svg, x1, y1, x2, y2, o = {}) {
      const col = o.color || C.ink, w = o.width || 5, hl = o.head === 0 ? 0 : (o.head || 18), bend = o.bend || 0;
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1, dl = Math.hypot(dx, dy) || 1;
      const cx = mx + (dy / dl) * bend, cy = my - (dx / dl) * bend;
      const ang = Math.atan2(y2 - cy, x2 - cx);
      const ex = hl ? x2 - Math.cos(ang) * hl * 0.8 : x2, ey = hl ? y2 - Math.sin(ang) * hl * 0.8 : y2;
      const line = this.svgEl(svg, 'path', { d: `M ${x1} ${y1} Q ${cx} ${cy} ${ex} ${ey}`, stroke: col, 'stroke-width': w, fill: 'none', 'stroke-linecap': 'round' }, false);
      let len = 0, px0 = x1, py0 = y1;
      for (let i = 1; i <= 24; i++) { const u = i / 24, a = (1 - u) * (1 - u), b = 2 * (1 - u) * u, c2 = u * u; const px = a * x1 + b * cx + c2 * ex, py = a * y1 + b * cy + c2 * ey; len += Math.hypot(px - px0, py - py0); px0 = px; py0 = py; }
      len = Math.max(1, len);
      line.setAttribute('stroke-dasharray', String(len)); line.setAttribute('stroke-dashoffset', String(len));
      let head = null;
      if (hl) { const hx = Math.cos(ang + Math.PI / 2) * hl * 0.5, hy = Math.sin(ang + Math.PI / 2) * hl * 0.5; head = this.svgEl(svg, 'path', { d: `M ${x2} ${y2} L ${ex + hx} ${ey + hy} L ${ex - hx} ${ey - hy} Z`, fill: col }, true); }
      gsap.set(line, { autoAlpha: 0 });
      return { line, head, len };
    }
    // A row of letter cells for a string: shows how text is cut into letters. o = {x,y,size=44,gap=6,color,fill,mono=true}
    // returns {cells[] (one per non-space char, in order), byIndex[] (cell or null for a space, indexed by character position),
    //          cx(i), cy, left, right, w, h}  cx(i) = the x centre of character i (spaces included), for aiming arrows.
    letters(str, o = {}) {
      const size = o.size || 44, gap = o.gap == null ? 6 : o.gap, cw = Math.round(size * 0.82), chh = Math.round(size * 1.28);
      const x0 = o.x || 0, y0 = o.y || 0, cells = [], byIndex = [], centers = [];
      let x = x0;
      [...str].forEach((ch) => {
        if (ch === ' ') { centers.push(x + cw * 0.3); byIndex.push(null); x += Math.round(cw * 0.6); return; }
        const e = el('div', 'lcell' + (o.mono === false ? '' : ' mono'), o.parent || this.g);
        e.textContent = ch; e.style.left = x + 'px'; e.style.top = y0 + 'px'; e.style.width = cw + 'px'; e.style.height = chh + 'px';
        e.style.fontSize = size + 'px'; e.style.lineHeight = (chh - 4) + 'px'; e.style.color = o.color || C.ink; e.style.background = o.fill || '#fff';
        if (o.border) e.style.borderColor = o.border;
        gsap.set(e, { autoAlpha: 0 });
        cells.push(e); byIndex.push(e); centers.push(x + cw / 2); x += cw + gap;
      });
      return { cells, byIndex, cx: (i) => centers[i], cy: y0 + chh / 2, left: x0, right: x - gap, w: x - gap - x0, h: chh, cw };
    }
    // A picture of a vector (a list of numbers): a strip of shaded cells. o = {x,y,n=8,cell=30,gap=4,dir:'h'|'v',color,seed=1,fill}
    // The strip is ONE element (show/hide/move it as a whole). The shading is deterministic; it means nothing.
    vec(o = {}) {
      const n = o.n || 8, cell = o.cell || 30, gap = o.gap == null ? 4 : o.gap, horiz = o.dir !== 'v', col = o.color || C.thinker, rnd = K.rng(o.seed || 1);
      const e = el('div', 'vec', o.parent || this.g);
      e.style.left = (o.x || 0) + 'px'; e.style.top = (o.y || 0) + 'px';
      e.style.width = (horiz ? n * cell + (n - 1) * gap : cell) + 'px'; e.style.height = (horiz ? cell : n * cell + (n - 1) * gap) + 'px';
      for (let i = 0; i < n; i++) {
        const c = el('i', null, e); c.style.width = cell + 'px'; c.style.height = cell + 'px';
        c.style.left = (horiz ? i * (cell + gap) : 0) + 'px'; c.style.top = (horiz ? 0 : i * (cell + gap)) + 'px';
        c.style.background = col; c.style.opacity = (0.18 + rnd() * 0.8).toFixed(2);
      }
      if (o.hidden !== false) gsap.set(e, { autoAlpha: 0 });
      return e;
    }
    // A callout card with a coloured left edge. o = {x,y,w,color,size=34,fill}. Auto height. Use for a definition or a "careful" note.
    note(str, o = {}) {
      const e = el('div', 'note', o.parent || this.g);
      e.style.left = (o.x || 0) + 'px'; e.style.top = (o.y || 0) + 'px'; e.style.width = (o.w || 800) + 'px';
      e.style.borderLeftColor = o.color || C.thinker; e.style.fontSize = (o.size || 34) + 'px';
      if (o.fill) e.style.background = o.fill;
      if (o.html) e.innerHTML = str; else e.textContent = str;
      if (o.hidden !== false) gsap.set(e, { autoAlpha: 0 });
      return e;
    }
    // Horizontal bars with labels and counting values. o = {x,y,w=900,labelW=420,rowH=64,gap=26,max=100,dec=2,suf='',valueSize=46,labelSize=40,items:[{label,value,color,suf,dec}]}
    // returns {rows:[{lab,track,fill,val,b}], reveal(t, gapSec=0.35, dur=1.6) -> end time}
    hbars(o = {}) {
      const w = o.w || 900, labelW = o.labelW || 420, rowH = o.rowH || 64, gap = o.gap || 26, S = this;
      const rows = o.items.map((it, i) => {
        const y = (o.y || 0) + i * (rowH + gap);
        const lab = S.text(it.label, { x: o.x || 0, y: y + (rowH - (o.labelSize || 40) * 1.25) / 2, w: labelW - 24, size: o.labelSize || 40, weight: 700, align: 'right', color: it.labelColor || C.ink });
        const b = S.bar({ x: (o.x || 0) + labelW, y, w, h: rowH, value: it.value, max: o.max || 100, color: it.color || C.thinker });
        const val = S.text('', { x: (o.x || 0) + labelW + w + 24, y: y + (rowH - (o.valueSize || 46) * 1.25) / 2, w: o.valueW || 260, size: o.valueSize || 46, weight: 800, color: it.color || C.ink });
        return { lab, track: b.track, fill: b.fill, val, b, it };
      });
      return {
        rows,
        reveal(t, gapSec = 0.35, dur = 1.6) {
          let u = t;
          rows.forEach((r) => {
            S.show(r.lab, u, { dur: 0.4 }); S.show(r.track, u, { dur: 0.4 }); S.show(r.val, u + 0.2, { dur: 0.3 });
            S.grow(r.b, u + 0.3, dur, r.val, { dec: r.it.dec == null ? (o.dec == null ? 2 : o.dec) : r.it.dec, suf: r.it.suf || o.suf || '', comma: true });
            u += gapSec;
          });
          return u - gapSec + 0.3 + dur;
        },
      };
    }

    // ---------- animation (each returns the time it finishes) ----------
    show(e, t, o = {}) {
      const dur = o.dur || 0.5, y = o.y == null ? 22 : o.y, x = o.x || 0, s = o.s == null ? 1 : o.s;
      gsap.set(e, { autoAlpha: 0, x, y, scale: s });
      this.tl.to(e, { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: dur, ease: o.ease || 'power2.out' }, t);
      return t + dur;
    }
    hide(e, t, dur = 0.4) { this.tl.to(e, { autoAlpha: 0, duration: dur, ease: 'power1.in' }, t); return t + dur; }
    // reveal a list one after another
    stagger(list, t, gap = 0.4, o = {}) { let u = t; list.forEach((e) => { this.show(e, u, o); u += gap; }); return u; }

    // reveal many small things (letters, dots) evenly across `total` seconds, each with a short fade. Cheap and tidy for long lists.
    sweep(list, t, total = 1.5, o = {}) {
      const step = total / Math.max(1, list.length), dur = o.dur || 0.25;
      list.forEach((e, i) => { gsap.set(e, { autoAlpha: 0 }); this.tl.to(e, { autoAlpha: 1, duration: dur, ease: 'power1.out' }, t + i * step); });
      return t + total + dur;
    }
    pop(e, t, o = {}) {
      gsap.set(e, { autoAlpha: 0, scale: 0.6 });
      this.tl.to(e, { autoAlpha: 1, scale: 1, duration: o.dur || 0.45, ease: 'back.out(1.7)' }, t);
      return t + (o.dur || 0.45);
    }
    pulse(e, t, o = {}) {
      const s = o.scale || 1.08;
      this.tl.to(e, { scale: s, duration: 0.25, ease: 'power2.out' }, t);
      this.tl.to(e, { scale: 1, duration: 0.35, ease: 'power2.inOut' }, t + 0.25);
      return t + 0.6;
    }
    // move relative to the element's resting spot (x/y are pixel offsets). Resting spot = its CSS left/top.
    move(e, t, dur, o = {}) { this.tl.to(e, { x: o.x || 0, y: o.y || 0, duration: dur, ease: o.ease || 'power2.inOut' }, t); return t + dur; }
    // change border/fill/text colour with absolute end values
    tint(e, t, o = {}) {
      const v = { duration: o.dur || 0.4, ease: 'none' };
      if (o.border) v.borderColor = o.border; if (o.fill) v.backgroundColor = o.fill; if (o.color) v.color = o.color;
      this.tl.to(e, v, t); return t + v.duration;
    }
    draw(a, t, dur = 0.7) {
      this.tl.set(a.line, { autoAlpha: 1 }, t);
      this.tl.to(a.line, { strokeDashoffset: 0, duration: dur, ease: 'power1.inOut' }, t);
      if (a.head) this.tl.to(a.head, { autoAlpha: 1, duration: 0.2 }, t + dur - 0.05);
      return t + dur;
    }
    // type a string out letter by letter. The element keeps its position and style.
    type(e, str, t, dur = 1.2) {
      e.textContent = '';
      const spans = [];
      for (const ch of str) { const s = el('span', null, e); s.textContent = ch; s.style.whiteSpace = 'pre-wrap'; spans.push(s); }
      gsap.set(spans, { autoAlpha: 0 });
      const step = dur / Math.max(1, spans.length);
      spans.forEach((s, i) => this.tl.to(s, { autoAlpha: 1, duration: 0.001 }, t + i * step));
      gsap.set(e, { autoAlpha: 1 });
      return t + dur;
    }
    // count a number up (or down). o = {from,to,dec,pre,suf,comma}. The element text is set to the start value now.
    count(e, o, t, dur = 1.2, ease = 'power2.out') {
      const ob = { v: o.from == null ? 0 : o.from };
      e.textContent = fmt(ob.v, o);
      this.tl.to(ob, { v: o.to, duration: dur, ease, onUpdate: () => { e.textContent = fmt(ob.v, o); } }, t);
      return t + dur;
    }
    // grow a bar made with S.bar(...). Also counts its value label if one is given (valueEl).
    grow(b, t, dur = 1.0, valueEl, valueOpts) {
      this.tl.to(b.fill, { scaleX: b.frac, duration: dur, ease: 'power2.out' }, t);
      if (valueEl) this.count(valueEl, Object.assign({ from: 0, to: b.value }, valueOpts || {}), t, dur);
      return t + dur;
    }
  }

  // The five-part map of the whole machine, reused so every chapter shows the same picture.
  // o = {x,y,w,h, highlight:'reader'|'thinker'|'calc'|'stop'|'talker'|null, labels:false}
  Scene.prototype.modelMap = function (o = {}) {
    const x = o.x || 100, y = o.y || 300, W = o.w || 1720, H = o.h || 200, hl = o.highlight || null;
    const parts = [
      { k: 'reader', label: 'Reader', sub: 'borrowed', col: C.reader },
      { k: 'thinker', label: 'Thinker', sub: 'ours', col: C.thinker },
      { k: 'calc', label: 'Calculator', sub: 'outside tool', col: C.calc },
      { k: 'stop', label: 'Stop switch', sub: 'ours', col: C.stop },
      { k: 'talker', label: 'Talker', sub: 'ours', col: C.talker },
    ];
    const gap = 70, bw = (W - gap * 4) / 5, out = { parts: {}, arrows: [] };
    const svg = this.svg({ x: 0, y: 0 });
    parts.forEach((p, i) => {
      const bx = x + i * (bw + gap);
      const dim = hl && hl !== p.k;
      const b = this.box({ x: bx, y, w: bw, h: H, label: p.label, sub: p.sub, color: dim ? C.line : p.col, size: 40, subSize: 28, border: 5, fill: dim ? '#FAF6EE' : '#fff', parent: this.g });
      if (dim) { b.querySelectorAll('.lab').forEach((n) => { n.style.color = C.placeholder; }); }
      out.parts[p.k] = b;
      if (i < parts.length - 1) {
        const a = this.arrow(svg, bx + bw + 8, y + H / 2, bx + bw + gap - 8, y + H / 2, { color: C.soft, width: 6, head: 20 });
        out.arrows.push(a);
      }
    });
    out.svg = svg;
    return out;
  };

  K.Scene = Scene;
})();
