# PASSMARKS — Experiment 190: reverse questions by VALUE lookup (loop190)

Base: loop138g (`scripts/fable_loop138g_agent.py`,
`artifacts/fable-agent138g-20260922/`,
`design/v3/30-modes/138g-merge-layer-a-muse.md`).
One change: `scripts/fable_fix190_reverse.py` (closed reverse shapes
E1–E4 over the closed teachable relation set, live-taught-triples
lookup, clarify-only replies), stacked in
`scripts/fable_loop190_agent.py`. New files only; no commits.

## The rule (frozen)

- The 190 stage runs only when the full 138g stack returns all-clarify.
  Forward asks and teaches/corrects always pass through byte-identical.
- Closed shapes: E1 `Whose <R> is <Y>?`, E2 `Who has <Y> as
  their|his|her <R>?`, E3 `Who lives in <Y>?` (city key only), E4 `Who
  was born in <Y>?` (birthplace key only). R/Y are single noun phrases
  (no `'s`/`of`/relative cues); E1/E2 require R in REVERSE_RELATIONS.
- Closed relations (union of loop138g's own code: PERSON_RELATIONS in
  `scripts/fable_agent_loop.py:91` + LISTED_RELATIONS in
  `scripts/fable_fix139e_tail.py:57`): mother father sister brother
  sibling spouse husband wife boss friend teacher coach pet dog
  neighbour neighbor partner city town hometown home_town country
  birthplace place_of_birth school.
- Lookup: live taught triples only (`notebook_triples`: corrections
  respected, inferences never). Value match is whitespace-collapsed,
  case-sensitive (153-identical semantics).
- Replies: 1 match → `S's R is V.`; several → one sentence each,
  notebook order, space-joined; none but Y known → `I don't know anyone
  whose R is V.`; unknown Y → `I don't know anyone called Y.` (the
  notebook's UNKNOWN_ENTITY text, verified byte-identical on loop138g).
- Never writes (clarify actions only). Each run < 1500 s Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; daemon wrappers take
  `idle_seconds`. Fresh tmp/state dirs only; never the repo-root
  notebook. Every seed/case reported, never averaged (one deterministic
  run per mark; each turn/case its own row).

## V1 — sealed case file (bar: 70/70 turn checks)

`case190.json` (70 turns, seed 1): 25 setup teaches + 12 single-match
reverse asks + 6 multi-match (2 subjects each) + 1 teach + 1 correct +
4 post-correction asks (old value excluded, new value included) + 5
no-match-known + 5 unknown + 10 forward/teach traps.
Bar: 32/32 reverse replies exact; 38/38 setup+traps byte-identical to
loop138g (reply AND stored triples); 0 writes on all 32 asks; 0 FAILs.
Any FAIL is recorded as FAIL with one diagnosis note; no silent re-runs.

## V2 — frozen suites + marks123 (bar: identical except predicted)

- redteam136 (145 cases): 0 verdict/reply moves vs sealed 138g rows, 0
  new WRONG/WRONG-WRITE/junk writes.
- redteam143 (124 cases): same bar.
- sessions152 (180 turns): 0 verdict/reply moves, 0 new wrong, 0 new
  writes vs sealed 138g rows.
- marks123 (10 reports: p2/p3/p4/rt110/q1/bench/rt81/sleep/soak/q4):
  per-case identical to sealed marks138g after scrubbing volatile
  metadata (seconds, tmp/out paths, PIDs). Only predicted move: the
  sleep SKIP reason names `fable_loop190_agent.py`.
- Basis (pre-seal, unregistered): static scan of all redteam136/143,
  sessions152, p2/p3(turns84)/p4, rt81, rt110, q1, bench121×4,
  bench132 and soak-generator texts with the sealed parser found 0
  turns matching the closed shapes; soak sends only city teaches,
  corrections and `What is X's city?` asks.

## V3 — bench (descriptive reversal rows + 0-new-wrong bar)

- bench121 4 splits through loop190, per-item verdicts vs sealed 138g
  rows: 0 moves, 0 new wrong.
- Reversal rows: every bench question scanned with the sealed parser;
  pre-seal scan found 0 matches (bench reversals are `Who is the R of
  X?` forward shapes, out of scope). Reported descriptively, no bar.

## Predicted intentional moves (190 vs 138g, V1 only)

On turns matching E1–E4 with an all-clarify base: 153-style
`V is the R of S.` replies become forward-style `S's R is V.`
sentences; 153's blanket `don't know anyone whose R is V.` splits into
known-name vs `anyone called Y`; former decline/smalltalk don't-knows
(`Who has … as their …`, `Who lives in …`, `Who was born in …`) become
answers. All other turns byte-identical.
