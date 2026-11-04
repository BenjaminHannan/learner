'use strict';
// Little scientist, part 3: small grid / text games with a deterministic rule simulator (our own simple versions of classic
// puzzles: a maze, Nim, tic-tac-toe, sliding tiles). Every game has the same interface:
//   init(seed) -> state            moves(state) -> [move]         step(state, move) -> state (the rulebook; never mutates)
//   done(state) -> bool            result(state) -> 1 win | 0 loss | 0.5 draw | null (still going)
//   render(state) -> text          value(state) -> 0..1 heuristic (for lookahead when the game is not over)
//   moveText(move) -> text          parseMove(state, text) -> move | null
// Two-player games (nim, ttt) include the opponent inside step(): after our move the opponent replies with a fixed, seeded policy,
// so the "world" is deterministic given the seed. Pure JS, no model.

// a small seeded PRNG (mulberry32)
function rng(seed) { let a = (seed >>> 0) || 1; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pick = (r, xs) => xs[Math.floor(r() * xs.length)];
const clone = (s) => JSON.parse(JSON.stringify(s));

// ---- maze: reach the goal G from S on a 7x7 grid within a step limit ---------------------------------------------------
const DIRS = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };
const maze = {
  name: 'maze',
  init(seed) {
    const r = rng(seed * 7 + 1), n = 7;
    for (let tries = 0; ; tries++) {
      const g = Array.from({ length: n }, () => Array(n).fill('.'));
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (r() < 0.28) g[i][j] = '#';
      const s = [0, 0], goal = [n - 1, n - 1]; g[0][0] = '.'; g[n - 1][n - 1] = '.';
      const d = bfs(g, s, goal);
      if (d != null && d >= 8) return { grid: g.map((row) => row.join('')), pos: s, goal, steps: 0, limit: d + 6, seed };
    }
  },
  moves(s) { return Object.keys(DIRS); },
  key: (s) => s.pos.join(','),
  step(s, m) {
    const t = clone(s), d = DIRS[m]; if (!d) return t;
    const p = [s.pos[0] + d[0], s.pos[1] + d[1]];
    if (p[0] >= 0 && p[1] >= 0 && p[0] < s.grid.length && p[1] < s.grid.length && s.grid[p[0]][p[1]] !== '#') t.pos = p;   // a wall: you stay put
    t.steps++;
    return t;
  },
  done(s) { return (s.pos[0] === s.goal[0] && s.pos[1] === s.goal[1]) || s.steps >= s.limit; },
  result(s) { if (s.pos[0] === s.goal[0] && s.pos[1] === s.goal[1]) return 1; return s.steps >= s.limit ? 0 : null; },
  value(s) { const d = bfs(s.grid.map((r) => r.split('')), s.pos, s.goal); return d == null ? 0 : 1 / (1 + d); },
  render(s) { return s.grid.map((row, i) => row.split('').map((c, j) => (i === s.pos[0] && j === s.pos[1] ? 'S' : i === s.goal[0] && j === s.goal[1] ? 'G' : c)).join('')).join('\n') + '\nYou are S at row ' + s.pos[0] + ', column ' + s.pos[1] + '. Step ' + s.steps + ' of ' + s.limit + '.'; },
  stateText(s) { return 'row ' + s.pos[0] + ', column ' + s.pos[1]; },
  moveText: (m) => m,
  parseMove(s, t) { const m = /\b(up|down|left|right)\b/i.exec(String(t || '')); return m ? m[1].toLowerCase() : null; }
};
function bfs(g, s, goal) {
  const n = g.length, seen = new Set([s.join()]); let q = [s], d = 0;
  while (q.length) {
    const nq = [];
    for (const p of q) {
      if (p[0] === goal[0] && p[1] === goal[1]) return d;
      for (const [di, dj] of Object.values(DIRS)) { const x = [p[0] + di, p[1] + dj]; if (x[0] < 0 || x[1] < 0 || x[0] >= n || x[1] >= n || g[x[0]][x[1]] === '#' || seen.has(x.join())) continue; seen.add(x.join()); nq.push(x); }
    }
    q = nq; d++;
  }
  return null;
}

// ---- Nim: piles of stones, take 1-3 from one pile; whoever takes the LAST stone wins. The opponent plays a seeded mix ---------
const nim = {
  name: 'nim',
  init(seed) { const r = rng(seed * 13 + 5); return { piles: [1 + Math.floor(r() * 5), 1 + Math.floor(r() * 5), 1 + Math.floor(r() * 5)], turn: 'me', winner: null, seed, ply: 0 }; },
  moves(s) { const out = []; s.piles.forEach((p, i) => { for (let k = 1; k <= Math.min(3, p); k++) out.push({ pile: i, take: k }); }); return out; },
  take(s, m) { const t = clone(s); if (!m || !(t.piles[m.pile] >= m.take) || m.take < 1 || m.take > 3) return null; t.piles[m.pile] -= m.take; t.ply++; return t; },
  // for imagining (src/imagine.js): our move only, and every possible opponent reply (the opponent's real policy is not used)
  apply(s, m) { const t = nim.take(s, m); if (t && t.piles.every((p) => p === 0)) t.winner = 'me'; return t; },
  replies(s) { return nim.moves(s).map((m) => { const t = nim.take(s, m); if (t.piles.every((p) => p === 0)) t.winner = 'them'; return t; }); },
  key: (s) => s.piles.join(',') + '|' + (s.winner || ''),
  // the opponent: takes the winning move (nim-sum with the 1-3 rule = xor of pile mod 4) 60% of the time, else a random move
  reply(s) {
    const ms = nim.moves(s); if (!ms.length) return null;
    const r = rng(s.seed * 31 + s.ply * 7 + s.piles.reduce((a, b) => a * 7 + b, 0));
    if (r() < 0.6) { const win = ms.find((m) => { const t = nim.take(s, m); return t.piles.reduce((a, p) => a ^ (p % 4), 0) === 0; }); if (win) return win; }
    return pick(r, ms);
  },
  step(s, m) {
    let t = nim.take(s, m); if (!t) return clone(s);
    if (t.piles.every((p) => p === 0)) { t.winner = 'me'; return t; }
    const o = nim.reply(t); t = nim.take(t, o);
    if (t.piles.every((p) => p === 0)) t.winner = 'them';
    return t;
  },
  done(s) { return !!s.winner; },
  result(s) { return s.winner === 'me' ? 1 : s.winner === 'them' ? 0 : null; },
  render(s) { return 'Piles: ' + s.piles.join(' ') + '. You may take 1 to 3 stones from one pile. Whoever takes the last stone wins.'; },
  stateText(s) { return s.winner ? (s.winner === 'me' ? 'I win' : 'they win') : 'piles ' + s.piles.join(' '); },
  moveText: (m) => 'take ' + m.take + ' from pile ' + (m.pile + 1),
  parseMove(s, t) { const m = /take\s+(\d)\s+(?:stones?\s+)?from\s+pile\s+(\d)/i.exec(String(t || '')); if (!m) return null; const mv = { pile: +m[2] - 1, take: +m[1] }; return nim.take(s, mv) ? mv : null; }
};
// value(): evaluated on states where it is MY turn (after the opponent replied). A nonzero nim-sum (piles mod 4, xor) on my turn
// means I have a winning move against perfect play; zero means I am losing unless the opponent errs (it errs 40% of the time).
nim.value = (s) => (s.winner ? (s.winner === 'me' ? 1 : 0) : (s.piles.reduce((a, p) => a ^ (p % 4), 0) !== 0 ? 0.7 : 0.35));

// ---- tic-tac-toe: I am X and move first; O replies (wins if it can, blocks if it must, else random, seeded) ---------------
const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const winnerOf = (b) => { for (const [a, c, d] of LINES) if (b[a] !== '.' && b[a] === b[c] && b[a] === b[d]) return b[a]; return b.includes('.') ? null : 'draw'; };
const ttt = {
  name: 'ttt',
  init(seed) { return { board: '.........', seed, ply: 0, winner: null }; },
  moves(s) { const out = []; for (let i = 0; i < 9; i++) if (s.board[i] === '.') out.push(i); return out; },
  reply(s) {
    const b = s.board.split(''), free = ttt.moves(s); if (!free.length) return null;
    const r = rng(s.seed * 17 + s.ply * 3 + 11);
    for (const who of ['O', 'X']) for (const i of free) { const c = b.slice(); c[i] = who; if (winnerOf(c) === who) return i; }
    if (r() < 0.5 && s.board[4] === '.') return 4;
    return pick(r, free);
  },
  apply(s, m) { if (s.winner || s.board[m] !== '.') return null; const b = s.board.split(''); b[m] = 'X'; const w = winnerOf(b); return { ...s, board: b.join(''), ply: s.ply + 1, winner: w }; },
  replies(s) { return ttt.moves(s).map((i) => { const b = s.board.split(''); b[i] = 'O'; return { ...s, board: b.join(''), ply: s.ply + 1, winner: winnerOf(b) }; }); },
  key: (s) => s.board,
  step(s, m) {
    if (s.winner || s.board[m] !== '.') return clone(s);
    const b = s.board.split(''); b[m] = 'X'; let t = { ...s, board: b.join(''), ply: s.ply + 1 };
    let w = winnerOf(b); if (w) return { ...t, winner: w };
    const o = ttt.reply(t); const b2 = t.board.split(''); b2[o] = 'O'; t = { ...t, board: b2.join(''), ply: t.ply + 1 };
    w = winnerOf(b2); return w ? { ...t, winner: w } : t;
  },
  done(s) { return !!s.winner; },
  result(s) { return s.winner === 'X' ? 1 : s.winner === 'O' ? 0 : s.winner === 'draw' ? 0.5 : null; },
  value(s) {
    if (s.winner) return ttt.result(s);
    // my open lines minus theirs, squashed to 0..1
    let v = 0; for (const L of LINES) { const cs = L.map((i) => s.board[i]); if (!cs.includes('O')) v += cs.filter((c) => c === 'X').length; if (!cs.includes('X')) v -= cs.filter((c) => c === 'O').length; }
    return 1 / (1 + Math.exp(-v / 3));
  },
  render(s) { return [0, 3, 6].map((i) => s.board.slice(i, i + 3)).join('\n') + '\nYou are X. Squares are numbered 1-9, left to right, top to bottom.'; },
  stateText(s) { return s.winner ? (s.winner === 'draw' ? 'draw' : s.winner + ' wins') : 'board ' + [0, 3, 6].map((i) => s.board.slice(i, i + 3)).join('/'); },
  moveText: (m) => 'square ' + (m + 1),
  parseMove(s, t) { const m = /\b([1-9])\b/.exec(String(t || '')); if (!m) return null; const i = +m[1] - 1; return s.board[i] === '.' ? i : null; }
};

// ---- sliding tiles: a 3x3 board (1-8 and a blank 0), scrambled by N seeded moves; solve within a move limit ----------------
const GOAL = '123456780';
const tiles = {
  name: 'tiles',
  init(seed) {
    const r = rng(seed * 19 + 3); let b = GOAL, last = null;
    const n = 8 + Math.floor(r() * 5);
    for (let i = 0; i < n; i++) { const ms = tiles.moves({ board: b }).filter((m) => m !== OPP[last]); last = pick(r, ms); b = slide(b, last); }
    if (b === GOAL) b = slide(b, 'down');
    return { board: b, steps: 0, limit: 30, seed };
  },
  moves(s) { const z = s.board.indexOf('0'), out = []; if (z >= 3) out.push('up'); if (z < 6) out.push('down'); if (z % 3) out.push('left'); if (z % 3 < 2) out.push('right'); return out; },
  key: (s) => s.board,
  step(s, m) { if (!tiles.moves(s).includes(m)) return { ...s, steps: s.steps + 1 }; return { ...s, board: slide(s.board, m), steps: s.steps + 1 }; },
  done(s) { return s.board === GOAL || s.steps >= s.limit; },
  result(s) { return s.board === GOAL ? 1 : s.steps >= s.limit ? 0 : null; },
  value(s) { let d = 0; for (let i = 0; i < 9; i++) { const v = +s.board[i]; if (!v) continue; d += Math.abs(Math.floor(i / 3) - Math.floor((v - 1) / 3)) + Math.abs(i % 3 - (v - 1) % 3); } return 1 / (1 + d); },
  render(s) { return [0, 3, 6].map((i) => s.board.slice(i, i + 3).replace('0', '_')).join('\n') + '\nMoves name where the blank (_) goes: up, down, left, right.'; },
  stateText(s) { return [0, 3, 6].map((i) => s.board.slice(i, i + 3).replace('0', '_')).join('/'); },
  moveText: (m) => m,
  parseMove(s, t) { const m = /\b(up|down|left|right)\b/i.exec(String(t || '')); return m && tiles.moves(s).includes(m[1].toLowerCase()) ? m[1].toLowerCase() : null; }
};
const OPP = { up: 'down', down: 'up', left: 'right', right: 'left' };
function slide(b, m) { const z = b.indexOf('0'), t = z + ({ up: -3, down: 3, left: -1, right: 1 })[m]; const a = b.split(''); a[z] = a[t]; a[t] = '0'; return a.join(''); }

const GAMES = { maze, nim, ttt, tiles };

// play one game to the end. choose(state, game) -> move. -> {result, moves, state}
function play(game, seed, choose, maxPly) {
  let s = game.init(seed), n = 0;
  while (!game.done(s) && n < (maxPly || 60)) { const m = choose(s, game); if (m == null) break; s = game.step(s, m); n++; }
  return { result: game.result(s) == null ? 0 : game.result(s), moves: n, state: s };
}

module.exports = { GAMES, play, rng, bfs, winnerOf, GOAL };
