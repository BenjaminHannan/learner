# Exp 192 RESULTS — corrections say what they replaced (Muse)

Loop192 = loop167e + one reply-text change: a turn that REPLACES a
single-valued fact now answers `Updated: Kim's boss is Lee (it was
Sam).` instead of `Saved: Kim's boss is Lee.` Nothing else changes —
the notebook, stored facts, events, questions, and first-time teaches
are byte-identical to loop167e.

## Marks (integer counts, every case reported, never averaged)

| mark | result |
|---|---|
| C1 probe (40 turns: 11 explicit corrections, 4 yes-to-change, 25 traps) | 40/40 OK; 15/15 exact sealed template; 25/25 traps byte-identical; stored equal; scrubbed events equal; 1.0 s |
| C2 event identity | identical on all 40 turns |
| redteam136 (145 cases) | 0 verdict / 0 stored / 0 reply moves, 0 new wrong |
| redteam143 (124 cases) | exactly Q1–Q7 verdict →HARNESS-ERROR (Q1,Q2 from MISSED, Q3–Q7 from OK) by the sealed teach-accepted gate; 7/7 teach moves satisfy the move rule; stored 0 moves; 0 new WRONG-ANSWER |
| sessions152 (180 turns) | exactly 2 reply moves, verbatim as predicted (Rao/Denver was-seattle; Vera/Quito was-Lima); 0 verdict, 0 write, 0 new WRONG moves |
| bench (600 items, 3 splits) | 0 verdict / 0 reply / 0 teach-reply moves, 0 new wrong; 27.0 s; PASS |
| marks123 p2/p4/q1/bench/rt110/q4 | per-case byte-identical; sleep SKIP naming loop192 |
| marks123 rt81 (74 cases) | cases 8, 11, 34, 53, 69 OK→UNCLEAR by the sealed [wanted 'Saved'] gate (ok 61→56, unclear 13→18); rest identical |
| marks123 p3/l5z1 (60 turns) | turns 26–33, 35 (9 Actually replacements) observed SAVED→WRITE_OTHER by the sealed startswith("Saved") gate, wrong_writes 0; rest identical |
| marks123 soak (2000 turns) | registered wrong 41 = 39 Actually→Updated + 2 question misses from a lost first teach (startup mailbox race, proven in daemon log); open re-run wrong 40, all Actually→Updated; audits clean both |
| wall-clock | max run 167.8 s < 1500 s; OMP/MKL=1; daemon idle_seconds honored |
| seal | shasum -c 10/10 OK after all runs; zero post-seal edits |

Director probe verbatim: after "Kim's boss is Sam.", "No, Kim's boss
is Lee." → "Updated: Kim's boss is Lee (it was Sam)."; plain re-teach
still asks the change question; "yes" → Updated template.

## What it means

Corrections now tell the user what got replaced, naming old and new
values, while every stored fact and event stays identical to loop167e.

## What it does not mean

It does not change what the assistant knows, learns, or remembers —
only the confirmation sentence on replacement turns. Sealed harnesses
that assert the literal word "Saved:" (143 teach gate, rt81, soak,
l5z1 status) count the new sentence as a miss; the notebook is
unaffected (0 stored-fact differences everywhere).

## Deviations (all open, none post-seal)

1. Resumed work: the inherited PASSMARKS had a `<PACT>` placeholder and
   wrongly claimed marks123 summary numbers would be unchanged. Fixed
   pre-seal using a dev marks123 run (rt81/soak/l5z1 consequences above).
2. Suites driver and marksdiff exit nonzero on the predicted moves
   (143 abort changes the recorded final-reply field; session replies
   carry a trailing newline the shared rule does not strip; counts are
   numeric). Every move was verified individually against the
   predictions; no code was edited post-seal to chase green exits.
3. Soak registered 41 vs predicted 40 (race, see row); re-run once in
   the open: 40, exactly the predicted composition. Both reported.

## Reproduce (from worktree root, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_probe.py --out artifacts/fable-correctreply192-20260922/probe192-loop192.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_suites.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop192_agent.py --config artifacts/fable-correctreply192-20260922/loop192-config.json --out artifacts/fable-correctreply192-20260922/marks192 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_marksdiff.py

## Questions for Ben

None. Conservative default kept: silent auto-correct re-teaches still
say "Saved:" so the strictest old tests keep passing.
