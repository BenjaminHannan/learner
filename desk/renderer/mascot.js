'use strict';
// Glim: Premonition's mascot. A small crystal-ball buddy with a flame wisp on top.
// Mascot.svg(mood, opts) -> SVG string. Mascot.el(mood, size, opts) -> span you can re-mood with Mascot.set().
// Moods: idle thinking working waiting done error sleepy.
(function (root) {
  const MOODS = ['idle', 'thinking', 'working', 'waiting', 'done', 'error', 'sleepy'];
  const INK = '#2b1707';
  let uid = 0;

  function eye(cx, cy, k) {
    const r = k || 1;
    return '<g class="eye"><ellipse cx="' + cx + '" cy="' + cy + '" rx="' + 5.6 * r + '" ry="' + 7.6 * r + '" fill="' + INK + '"/>' +
      '<circle cx="' + (cx + 1.9) + '" cy="' + (cy - 2.8 * r) + '" r="2.2" fill="#fff"/>' +
      '<circle cx="' + (cx - 2) + '" cy="' + (cy + 3 * r) + '" r="1" fill="#fff" opacity=".7"/></g>';
  }
  const arc = (d, w) => '<path d="' + d + '" fill="none" stroke="' + INK + '" stroke-width="' + (w || 3.2) + '" stroke-linecap="round" stroke-linejoin="round"/>';

  function face(mood) {
    const L = 39, R = 61, Y = 51;
    switch (mood) {
      case 'done':
        return '<g class="eyes">' + arc('M33 53 Q39 44 45 53', 3.4) + arc('M55 53 Q61 44 67 53', 3.4) + '</g>' +
          '<path d="M43.5 61 Q50 71 56.5 61 Z" fill="' + INK + '" stroke="' + INK + '" stroke-width="1.6" stroke-linejoin="round"/>';
      case 'sleepy': {
        const half = (cx) => '<path d="M' + (cx - 5.6) + ' ' + Y + ' H' + (cx + 5.6) + ' A5.6 6.4 0 0 1 ' + (cx - 5.6) + ' ' + Y + ' Z" fill="' + INK + '" stroke="' + INK + '" stroke-width="2" stroke-linejoin="round"/>';
        return '<g class="eyes">' + half(L) + half(R) + '</g><ellipse cx="50" cy="65" rx="2.3" ry="2.7" fill="' + INK + '" opacity=".85"/>';
      }
      case 'error':
        return '<g class="eyes"><g class="look">' + eye(L, Y + 1, .92) + eye(R, Y + 1, .92) + '</g></g>' +
          arc('M32 40 L45 35.5', 2.6) + arc('M55 35.5 L68 40', 2.6) +
          arc('M45 66 Q47.5 62.5 50 64.5 Q52.5 66.5 55 63.5', 2.4);
      case 'waiting':
        return '<g class="eyes blink"><g class="look">' + eye(L, Y) + eye(R, Y) + '</g></g>' + arc('M46 62 Q50 64.5 54 62', 2.6);
      case 'thinking':
        return '<g class="eyes blink"><g class="look">' + eye(L, Y) + eye(R, Y) + '</g></g>' + '<ellipse cx="56" cy="64" rx="3" ry="2" fill="' + INK + '" opacity=".85"/>';
      default: // idle, working
        return '<g class="eyes blink"><g class="look">' + eye(L, Y) + eye(R, Y) + '</g></g>' + arc('M44.5 61.5 Q50 67 55.5 61.5', 2.8);
    }
  }

  function extras(mood) {
    const star = (x, y, s, cls) => '<path class="' + cls + '" transform="translate(' + x + ' ' + y + ') scale(' + s + ')" d="M0 -9 Q1.2 -1.2 9 0 Q1.2 1.2 0 9 Q-1.2 1.2 -9 0 Q-1.2 -1.2 0 -9Z" fill="#fff4c4" stroke="#e8920c" stroke-width="1.3" stroke-linejoin="round"/>';
    if (mood === 'done') return star(81, 24, 1, 'spark') + star(20, 30, .55, 'spark s2');
    if (mood === 'waiting') {
      return '<g class="qspark"><circle cx="80" cy="22" r="10.5" fill="#fff4c4" stroke="#e8920c" stroke-width="2"/>' +
        '<path d="M76.6 19.2 Q76.6 15.2 80 15.2 Q83.4 15.2 83.4 18.6 Q83.4 21 80 22.4 V24.6" fill="none" stroke="#a85f06" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<circle cx="80" cy="29" r="1.5" fill="#a85f06"/></g>';
    }
    if (mood === 'sleepy') {
      const z = (x, y, s, cls) => '<path class="' + cls + '" transform="translate(' + x + ' ' + y + ') scale(' + s + ')" d="M0 0 H8 L0 9 H8" fill="none" stroke="#a85f06" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
      return z(74, 24, 1, 'zz') + z(86, 10, .7, 'zz z2');
    }
    return '';
  }

  // opts.still: no animation (small repeated avatars, contact sheets, icon render)
  function svg(mood, opts) {
    mood = MOODS.includes(mood) ? mood : 'idle';
    const id = 'g' + (++uid);
    const dim = mood === 'error' || mood === 'sleepy';
    const swirl = mood === 'thinking'
      ? '<g class="swirl"><circle cx="50" cy="52" r="25" fill="none" stroke="#fff8dc" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="16 14" opacity=".6"/></g>'
      : '';
    const wisp = mood === 'sleepy'
      ? '<path class="wisp" d="M50 9 C52.6 12 53.8 13.8 52.2 15.6 C51.4 16.5 48.6 16.5 47.8 15.6 C46.2 13.8 47.4 12 50 9Z" fill="#f5a524" stroke="#b86a05" stroke-width="1.2" stroke-linejoin="round"/>'
      : '<g class="wisp"><path d="M50 0 C56.5 6.5 58.5 11 55 15.2 C53.3 17.2 46.7 17.2 45 15.2 C41.5 11 43.5 6.5 50 0Z" fill="#ffb93a" stroke="#b86a05" stroke-width="1.4" stroke-linejoin="round"/>' +
        '<path d="M50 6.5 C53 9.6 54 12 52.2 14.2 C51.2 15.3 48.8 15.3 47.8 14.2 C46 12 47 9.6 50 6.5Z" fill="#fff1bf"/></g>';
    return '<svg class="mascot m-' + mood + (opts && opts.still ? ' still' : '') + '" data-mood="' + mood + '" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">' +
      '<defs><radialGradient id="' + id + 'b" cx="42%" cy="38%" r="75%"><stop offset="0" stop-color="#fff0bd"/><stop offset=".38" stop-color="#ffc552"/><stop offset=".8" stop-color="#ef9511"/><stop offset="1" stop-color="#c06c05"/></radialGradient>' +
      '<radialGradient id="' + id + 'g" cx="50%" cy="52%" r="50%"><stop offset="0" stop-color="#fffbe6" stop-opacity=".9"/><stop offset="1" stop-color="#fffbe6" stop-opacity="0"/></radialGradient></defs>' +
      '<g class="tilt">' +
      '<path d="M27 80 Q50 91 73 80 L70 91 Q50 97 30 91 Z" fill="#8a5a2e" stroke="#4a2c10" stroke-width="1.6" stroke-linejoin="round"/>' +
      '<g class="ball">' + wisp +
      '<circle cx="50" cy="52" r="31" fill="url(#' + id + 'b)" stroke="#9c5a05" stroke-width="2.2"/>' +
      '<circle class="glow" cx="50" cy="52" r="26" fill="url(#' + id + 'g)"/>' + swirl +
      '<ellipse cx="37" cy="31" rx="8.5" ry="4.4" transform="rotate(-38 37 31)" fill="#fff" opacity=".6"/>' +
      '<circle cx="30" cy="59" r="3.8" fill="#ff7d55" opacity=".38"/><circle cx="70" cy="59" r="3.8" fill="#ff7d55" opacity=".38"/>' +
      face(mood) +
      (dim ? '<circle class="dimmer" cx="50" cy="52" r="31" fill="#3a1f08" opacity="' + (mood === 'sleepy' ? '.3' : '.26') + '"/>' : '') +
      '</g></g>' + extras(mood) + '</svg>';
  }

  function el(mood, size, opts) {
    const s = document.createElement('span');
    s.className = 'mascot-wrap' + (opts && opts.cls ? ' ' + opts.cls : '');
    s.style.width = s.style.height = (size || 22) + 'px';
    s._still = !!(opts && opts.still);
    s.innerHTML = svg(mood, { still: s._still });
    return s;
  }
  function set(wrap, mood) {
    if (!wrap || wrap.firstChild && wrap.firstChild.getAttribute('data-mood') === mood) return;
    wrap.innerHTML = svg(mood, { still: wrap._still });
  }
  // one little hop (a tool step just started)
  function bounce(wrap) {
    const s = wrap && wrap.firstChild; if (!s) return;
    s.classList.remove('bounce'); void s.getBoundingClientRect(); s.classList.add('bounce');
  }

  const api = { MOODS, svg, el, set, bounce };
  root.Mascot = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
