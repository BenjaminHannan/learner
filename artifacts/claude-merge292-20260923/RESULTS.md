# Exp 292: 291 + 266b + 268b + 293 — registered result: PASS (M1–M5 all pass)

**Verdict: PASS.** Every predicted move exact; every bar met with integer
counts below. No blind panel item is quoted anywhere in this file (ids,
families and counts only).

## Marks table (registered runs, CPU only)

| mark | result | counts |
|---|---|---|
| M1 chainpanel266b (70 items; fidelity 266b, then 292; sealed scorer) | PASS | fidelity families 24/8/8/4/9/8/6 = 67/70 exact registered table; 292 vs piece: right_lost 0, new_wrong 0, new_write 0 |
| M1 nhoppanel268b (60 items) | PASS | fidelity total 55/60, bug 11/16 + 1 wrong exact registered table; 292 vs piece: 0/0/0 |
| M1 yesnopanel293 (85 items) | PASS | fidelity 85/85, 0 wrong, 0 writes exact registered PASS; 292 vs piece: 0/0/0 |
| M1 corrpanel291 (96 items) | PASS | fidelity 291 table 73/96 wrong 17 junk 3 fclaim 1 exact director-verified table; 292 byte-identical 96/96 replies+stores: right_lost 0, new_wrong 0 |
| M2 frozen suites vs 291 rows | PASS | sessions152 0 moves; bench 0; marks123 exactly 1 reply-only (rt81-report.json:D_q_vs_s-04 OK→UNCLEAR); rt136 move set identical to 291 (21 inherited) 0 new; rt143 exactly 2 (M3 Q2→Yes, O5 Q2→IDK); GATE clean; 0 new WRONG/WRONG-WRITE/junk/lost-OK |
| M3 restart + verifier | PASS | restart probes 0 reply/store moves (15+2+1+15+3 turns); verifier exactly 1 reply-only (N02 rows[1] Q2→honest IDK, ev 0, stored identical); supp 0; 0 ghosts, 0 dup fails, 0 bad writes |
| M4 latency (alternating, 208 turns ×3) | PASS | medians added +0.53/+0.41/+0.61 ms (bar ≤ +5) |
| M5 mixpanel292 (80 items, once per arm, sealed scorer) | PASS | 291: 35/80 0 wrong (writer table reproduced); 266b: 24/80 10 wrong; 268b: 29/80 6 wrong; 293: 44/80 8 wrong; 292: 73/80 0 wrong 7 miss; union-right on piece arms 56, lost on 292: 0; wrong beyond 291: 0; controls 24/24 byte-identical replies; question writes 0 all arms; mixed 9/12 (no bar) |

## Every move (by id; predictions in predicted_moves292.json, all exact)

- M2: rt81-report.json:D_q_vs_s-04; rt143 M3, O5. Nothing else moved.
- M3: verifier N02 rows[1] only. Nothing else moved.
- M1/M4/M5: as the table (M1 zero-diffs; M5 family counts in m5-check.json).

## Deviations (all disclosed; sealed files untouched after the seal)

- D1: corr M1 first ran under scripts/claude_corr252_run.py (7-field
  rows); the sealed corr scorer gated SCHEMA-MISMATCH exit 3 on both
  arms (VOID, no verdict; rows kept as corr291-291/292.jsonl). New
  post-seal driver scripts/claude_292_corrarm_run.py mirrors the
  panel's run_base.py one-for-one (only the arm differs); redo:
  fidelity 291 table exact, 292 identical 96/96.
- D2: scripts/claude_292_m5.sh called the mixpanel scorer positionally;
  it needs --panel/--rows/--base (exit 2, scoring VOID; the once-per-arm
  rows were valid). Rescored with the sealed flags, all exits 0.
- D3: pre-seal draft fixes listed in PASSMARKS.md (agent _check ears
  object, 268 install order, runall tally --out, score rt143 arrays,
  design pilot amendment). Post-seal: NO sealed file edited (seal
  re-verified 10/10 OK); one new driver file (above).

## What it means (plain high-school English)

- One agent now does what four agents did: plain asks and corrections
  like 291, chain questions like 266b (12/12 on the mix panel, was 0),
  yes/no answers like 293 (14/14, was 0), and it keeps every backwards
  answer 268b fixed. Total on the fresh mix panel: 73/80 with zero
  wrong answers (the base had 35/80).
- It never writes a fact on a question turn (0 writes on 80 mix items,
  96 corr items, 70+60+85 piece items, and every suite/probe turn).
- It never guesses: the 7 mix misses and every piece-panel miss are
  honest "I don't know"-style replies, and no item any piece got right
  got lost (56/56 kept).

## What it doesn't mean

- It doesn't mean chains are solved: yes/no about a chain still passes
  through unanswered by design, and the 268b employer-shape hole
  ("Who works for V?") travels with the piece.
- It doesn't mean corrections are perfect: corrpanel291 still shows the
  inherited 17 wrong values / 3 junk / 1 false claim from the parents
  (denials in verb wording fail on every arm); 292 adds none.
- It doesn't mean the mix panel tested 268b's guard: as the director
  noted, no backwards_bug item reaches the n-hop frame on 291, so that
  bar was "no piece-right item lost", which held.
