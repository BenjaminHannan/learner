'use strict';
// Synthetic notes and days for the feeling-time and patterns tests (Task B, 2026-11-04). Not a test file itself.
// Everything is seeded; names are made fresh from syllables, so a query can use names the store has never seen.
// Toy world only: nothing here is a claim about the real Glim.
function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
const SYL = ['ka', 'mi', 'ro', 'la', 'zen', 'tor', 'vi', 'sa', 'nel', 'do', 'ra', 'fin', 'jo', 'bek', 'li', 'mar', 'qu', 'el', 'tas', 'wen', 'ny', 'gor', 'pa', 'su', 'ven', 'ho', 'dri', 'ax', 'yo', 'cel'];
const PLACE_KIND = ['Park', 'Mall', 'Field', 'Library', 'Center', 'Station', 'Hall', 'Plaza'];
const EVENT = ['practice', 'dinner', 'meeting', 'rehearsal', 'game', 'class', 'appointment', 'party', 'study session', 'shift'];
function maker(r) {
  const used = new Set();
  const word = (n) => { for (;;) { let w = ''; for (let i = 0; i < n; i++) w += SYL[Math.floor(r() * SYL.length)]; w = w[0].toUpperCase() + w.slice(1); if (!used.has(w)) { used.add(w); return w; } } };
  return {
    name: () => word(2 + Math.floor(r() * 2)),
    place: () => word(2) + ' ' + PLACE_KIND[Math.floor(r() * PLACE_KIND.length)],
    time: () => { const h = 1 + Math.floor(r() * 12), m = [0, 15, 30, 45][Math.floor(r() * 4)]; return h + (m ? ':' + String(m).padStart(2, '0') : '') + (r() < 0.5 ? 'am' : 'pm'); },
    num: () => String(2 + Math.floor(r() * 97)),
    event: () => EVENT[Math.floor(r() * EVENT.length)],
    pick: (a) => a[Math.floor(r() * a.length)]
  };
}
// 32 shapes. Slots: {P} {Q} people, {L} place, {T} time, {N} number, {E} an event word (NOT masked: shared across shapes on purpose)
const SHAPES = [
  '{P} texted {Q}: the {E} moved to {T}',
  '{P} asked if {Q} can drive to {L} at {T}',
  '{P} cancelled the {E} at {L}',
  '{P} sent {N} photos from {L}',
  'Got a reminder from {P}: {E} at {T} in {L}',
  '{P} owes {Q} {N} dollars for the {E}',
  '{P} is sick and will miss the {E} on Friday',
  'Package from {L} arrives at {T}, order {N}',
  '{P} and {Q} are meeting at {L} after the {E}',
  '{P} emailed: grades for the {E} are posted, score {N}',
  '{P} forgot their keys at {L} again',
  '{P} invited {Q} to a {E} at {T}',
  'Bus to {L} is {N} minutes late',
  '{P} said the {E} needs {N} more people',
  '{P} lent {Q} a charger at {L}',
  '{P} wants to swap the {E} with {Q}',
  'Doctor {P} moved the checkup to {T}',
  '{P} posted that {L} is closed today',
  '{P} lost {N} points on the {E}',
  '{P} is driving {Q} home from {L} at {T}',
  'Coach {P} added an extra {E} at {T}',
  '{P} bought {N} tickets for the {E} at {L}',
  '{P} thinks {Q} broke the printer',
  '{P} needs the {E} notes from {Q} by {T}',
  'Rain warning for {L} from {T}',
  '{P} got a new puppy called {Q}',
  '{P} is running {N} minutes behind for the {E}',
  '{P} booked a table at {L} for {N} people',
  '{P} shared a playlist with {Q}',
  '{P} complained the {E} at {L} was too loud',
  '{P} finished level {N} with {Q}',
  'Library book from {L} is due at {T}'
];
function fill(tpl, mk, fixed) {
  const v = Object.assign({ P: mk.name(), Q: mk.name(), L: mk.place(), T: mk.time(), N: mk.num(), E: mk.event() }, fixed || {});
  return { text: tpl.replace(/\{([PQLTNE])\}/g, (_, k) => v[k]), vars: v };
}
// filler: word salad from real everyday words (lowercase) + sometimes a name; it should not form patterns
const FILLW = 'opened page window scrolled clicked folder photo video song list note draft reply button menu tab search result map weather news clock battery update download upload screen light dark mode volume shuffle chart table slide doc sheet card link chat group thread call timer alarm cart price shop review comment like share save copy paste print zoom keyboard mouse wifi bluetooth camera mic speaker desk chair snack water coffee tea bike walk run jump read write draw paint build fix clean sort pack ship move stop wait'.split(' ');
function filler(r, mk) {
  const n = 4 + Math.floor(r() * 5), w = [];
  for (let i = 0; i < n; i++) w.push(FILLW[Math.floor(r() * FILLW.length)]);
  if (r() < 0.4) w.splice(Math.floor(r() * w.length), 0, mk.name());
  const s = w.join(' '); return s[0].toUpperCase() + s.slice(1);
}
const DAY = 86400000;
const T0 = new Date(2026, 9, 5, 0, 0, 0).getTime();   // Mon 5 Oct 2026, local midnight

// The analogy set: shapes x instances spread over days, + filler. Queries: new instances with brand-new names.
function analogySet(seed, o) {
  o = o || {}; const r = rng(seed), mk0 = maker(r);
  // o.cast: a recurring cast of that many people used in every note and query (post-hoc variant; the primary test uses fresh names)
  const cast = o.cast ? Array.from({ length: o.cast }, () => mk0.name()) : null;
  const mk = cast ? Object.assign({}, mk0, { name: () => cast[Math.floor(r() * cast.length)] }) : mk0;
  const per = o.per || 5, days = o.days || 10, nShapes = o.shapes || SHAPES.length;
  const notes = [];
  for (let s = 0; s < nShapes; s++) for (let i = 0; i < per; i++) { const f = fill(SHAPES[s], mk); notes.push({ id: 's' + s + 'i' + i, shape: s, text: f.text, vars: f.vars, t: T0 + Math.floor(r() * days) * DAY + (8 + Math.floor(r() * 14)) * 3600000 + Math.floor(r() * 3600000) }); }
  for (let i = 0; i < (o.filler || 200); i++) notes.push({ id: 'f' + i, shape: -1, text: filler(r, mk), t: T0 + Math.floor(r() * days * DAY) });
  // held-out: new instances of each shape with brand-new names (the maker never repeats a name or place)
  const shapeQueries = [];
  for (let s = 0; s < nShapes; s++) for (let i = 0; i < (o.queries || 2); i++) shapeQueries.push({ shape: s, text: fill(SHAPES[s], mk).text });
  // same-name queries: a stored note's own people/place + its event word, asked about directly (target = that exact note)
  const nameQueries = [];
  const stored = notes.filter((n) => n.shape >= 0);
  for (let i = 0; i < 64; i++) {
    const n = stored[Math.floor(r() * stored.length)], v = n.vars, tpl = SHAPES[n.shape];
    const bits = []; if (tpl.includes('{P}')) bits.push(v.P); if (tpl.includes('{Q}')) bits.push(v.Q); if (tpl.includes('{L}')) bits.push(v.L); if (tpl.includes('{E}')) bits.push(v.E);
    nameQueries.push({ target: n.id, text: 'What was that about ' + bits.join(' and ') + '?' });
  }
  return { notes: notes.sort((a, b) => a.t - b.t), shapeQueries, nameQueries };
}

// Pattern days: hidden sequences A_i -> B_i (B follows A within 5-50 min, fresh names each time) planted on some days,
// among random filler. -> {items (timeline rows), planted: [{a, b}], days}
const SEQS = [
  ['{P} texted: plans for the {E} changed', '{P} moved the {E} to {T}'],
  ['Bus to {L} is running late', '{P} asked for a ride to {L}'],
  ['Coach {P} posted the practice schedule', 'Calendar added practice at {T}'],
  ['{P} started a group call', '{P} shared a screen with the group'],
  ['Homework portal posted a new assignment for {E}', 'Opened the assignment due {T}'],
  ['Order {N} shipped from {L}', 'Delivery from {L} arrives at {T}'],
  ['{P} said dinner is ready', 'Left the desk for dinner with {P}'],
  ['Phone battery at {N} percent', 'Plugged in the charger at {T}'],
  ['{P} invited Ben to play online', 'Opened the game lobby with {P}'],
  ['Weather alert: storm near {L} at {T}', '{P} cancelled the {E} because of the storm']
];
function patternDays(seed, o) {
  o = o || {}; const r = rng(seed), mk = maker(r);
  const days = o.days || 8, perDay = o.fillerPerDay || 40, occ = o.occurrences || 4;
  const items = [];
  let id = 0;
  const push = (t, text, tag) => items.push({ id: 'x' + (id++), t, text, tag, status: 'seen' });
  for (let d = 0; d < days; d++) for (let i = 0; i < perDay; i++) push(T0 + d * DAY + (7 + r() * 16) * 3600000, filler(r, mk), 'filler');
  const planted = [];
  SEQS.forEach(([a, b], k) => {
    const ds = []; while (ds.length < occ) { const d = Math.floor(r() * days); if (!ds.includes(d)) ds.push(d); }
    for (const d of ds) {
      const base = T0 + d * DAY + (8 + r() * 12) * 3600000;
      const P = mk.name(), L = mk.place();
      push(base, fill(a, mk, { P, L }).text, 'A' + k);
      push(base + (5 + r() * 45) * 60000, fill(b, mk, { P, L }).text, 'B' + k);
    }
    planted.push({ k, a, b, query: fill(a, mk).text });
  });
  return { items: items.sort((x, y) => x.t - y.t), planted, days };
}

module.exports = { rng, maker, SHAPES, SEQS, fill, filler, analogySet, patternDays, T0, DAY };
