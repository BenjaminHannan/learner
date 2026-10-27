# PASSMARKS — Experiment 190b: reverse no-match rewording (loop190b)

Base: loop190 (`scripts/fable_loop190_agent.py`,
`artifacts/fable-reverse190-20260922/`,
`design/v3/30-modes/190-reverse-muse.md`).
One change: `scripts/fable_loop190b_agent.py` (subclass of 190, no 190
file edited) — any closed-shape (E1–E4) reverse question with zero
stored matches replies `I don't know anyone whose <R> is <V>.` with
the relation display name, even when the value was never taught.
Plain who-is / forward unknown-name asks never parse as reverse and
are byte-identical. Clarify-only, never writes; notebook events
identical to 190 by construction. New files only (`fable_loop190b_*`,
`fable_fix190b_*`, `artifacts/fable-reverse190b-20260922/`,
`design/v3/30-modes/190b-reverse-muse.md`); no commits.

## The rule (frozen)

- The 190b wrapper runs the FULL 190 stack first and only rewrites a
  single clarify whose text is exactly `I don't know anyone called
  <V>.` when the turn parses as a closed 190 shape (E1–E4 via the
  sealed `parse_reverse190`) and the called name equals the parsed
  value. New text: `I don't know anyone whose <R> is <V>.` (`_` →
  space in the relation key, value cleaned as 190 does).
- Matches, known-value no-match (already whose-sentences), 153 frames
  (`Who is V the R of?`, `V is the R of whom?`, `its`-frame),
  forward asks, teaches/corrects, unlisted relations, compound and
  multi-hop shapes: byte-identical reply AND stored triples.
- Every run < 1500 s Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
  daemon wrappers take `idle_seconds`. Fresh tmp/state dirs only;
  never the repo-root notebook. Every seed/case reported, never
  averaged (one deterministic run per mark; each turn/case its own
  row). Fictional names only.

## R1 — sealed new case (bar: 15/15 r1 + full parity)

`case190b.json` (46 turns, seed 1): 11 setup teaches + 1 match check +
1 correction + 15 no-match reverse asks (R1–R12 unknown values across
boss/city/birthplace/mother/teacher/school/coach/friend/country in all
four shapes E1–E4; R13–R14 the correction-removed value Zep, which
190 already treats as unknown (moves `called` → `whose`); R15 the 153
frame `Who is Zed the boss of?`) + 8
who-is unknown-name rows + 10 forward/teach traps.
Bar: 15/15 r1 replies exact (the new sentence); S12 match exact;
31/31 r2+trap+teach/correct rows byte-identical to loop190 (reply AND
stored triples); 0 writes on all 32 asks; 0 FAILs.

## R2 — who-is unknown-name (bar: 8/8 unchanged)

W1–W6 forward possessive asks with unknown subjects keep the
notebook's `I don't know anyone called <Name>.`; W7–W8 plain
`Who is <Name>?` keep the base decline — all byte-identical to 190.

## R3 — the 190 V1 suite (bar: only the predicted rows move)

`case190.json` (70 turns) through loop190b vs sealed 190 rows:
ONLY rows E1–E5 (the 5 unknown rows) move, each `called <V>` →
`whose <R> is <V>` with the same value; all other 65 rows reply- and
event-identical; stored triples identical after every turn.

## R4 — frozen suites + marks123 + bench (bar: 0 moves)

- redteam136 (145 cases): 0 verdict/reply moves vs sealed 190 rows, 0
  new WRONG/WRONG-WRITE/junk writes.
- redteam143 (124 cases): same bar.
- sessions152 (180 turns): 0 verdict/reply moves, 0 new wrong, 0 new
  writes vs sealed 190 rows.
- marks123 (10 reports, scrubbed as 190 did): per-case identical to
  sealed marks190; only the scrubbed agent-filename line may differ.
- bench121 4 splits through loop190b, per-item verdicts vs sealed 190
  rows: 0 moves, 0 new wrong. Reversal rows reported descriptively.
- Basis (pre-seal, unregistered): the 190 pre-seal static scan found 0
  frozen/bench/marks turns matching the closed E1–E4 shapes, and 190b
  fires on a strict subset of 190's no-match paths, so 0 moves are
  predicted everywhere in R4.

## Predicted intentional moves (190b vs 190, in writing)

- V1b: the 15 r1 rows give the new whose-sentence (R1–R14 move
  `called` → `whose`, R15 already whose-form on 190 and stays
  identical in text but counts as r1 exact).
- V1: exactly E1, E2, E3, E4, E5 move `called` → `whose`; no other
  row moves.
- R4: NO moves anywhere (frozen suites, marks123, bench).

Any FAIL is recorded as FAIL with one diagnosis note; no silent
re-runs.
