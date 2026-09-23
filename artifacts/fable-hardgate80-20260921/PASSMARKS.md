# Experiment 80 — pass marks (fixed before any registered run)

One-change stress of the live sleep recipe (exp 46, harden-before-gate with
robust loss epsilon FIXED at 0.10). Single change: the TRUE number of wrong
teacher answers in 20 episodes varies over 0, 2, 4, 6, 8, 10, 20. Epsilon,
gate (OOF >= 0.80, refit agreement >= 0.90, base probe unchanged, reload
identical), optimiser, start, checkpoints, villages, words, and the 60-start
audit (evaluation only) are all identical to exp 46 (imported read-only from
scripts/fable_hardgate46.py). Seeds 4101, 4102, 4103. 3 words x 7 levels =
21 rows/seed, 63 total. Lessons: N.episodes() with the same per-(word,wrong)
RNG stream as exp 45/46, so levels 0/2/4/20 reuse the identical episodes.

Definitions: "install" = gate ACCEPTS (record installed=true). "Wrong
install" = installed AND (audit_disagree_of_60 > 0 OR fresh_accuracy < 0.99),
the exp-46 H1 definition.

Scale note: the brief's "15/15" is exp 46's 5-seed batch size (5x3 words).
This wave runs 3 seeds, so the same bar is 9/9 per level (3x3); the pooled
count over 0/2/4 is 27/27. Both framings are scored identically (all cells).

- J1 replicate: at each of 0, 2, 4 wrong: 9/9 installs (pooled 27/27 over
  the three levels), 0 wrong installs. Bit-identity vs exp 46 reported for
  the overlapping seeds (4102, 4103) at 0/2/4/20 where comparison rows exist.
- J2 measure (no gate): report installs/9 and wrong installs at each of 6,
  8, 10 wrong, pooled AND per seed (per-seed installs /3, never averaged).
- J3 nonsense: at 20/20 wrong: 0 installs accepted AND 0 wrong installs
  (pooled 0/9; safety property must hold).
- J4 breakpoint: name the first noise level in (0,2,4,6,8,10) where a WRONG
  INSTALL occurs on any seed, or "none up to 10/20".
- J5 time: whole wave (3 seeds sequential, one process at a time,
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, Mac CPU) < 30 min wall-clock.

Reading rule: J2 levels are measurement only — installs may fall and the
gate may refuse; refusal is not failure. Any WRONG INSTALL at any level
fails J1/J3 at that level and fixes J4 there. A registered FAIL is recorded
as FAIL, never re-run into a pass. Toy village, no language.
