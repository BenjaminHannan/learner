# State lab results (as of 23:15 UTC, 2026-10-23; more copies still running)

Village model D alone, FULL recipe, 6,000 steps, validation = held-out names/templates/styles/rules (8,675 questions).
Numbers are validation accuracy with HALT / with 8 loops forced (`min_loops=8`). Raw: results/ (final + diag per run), summary.txt.

| arm | runs (HALT / 8 loops) | 8-loop mean |
|---|---|---|
| base | s0 42.5/44.3, s1 42.4/43.8 | 44.0 |
| inject | s0 42.2/43.3, s0b 44.1/45.1 | 44.2 |
| reg16 | s0 48.7/49.4 | 49.4 |
| mq4 | s0 50.0/49.0 | 49.0 |
| lastloss | s0 41.0/46.0, s0b 45.0/51.4 | 48.7 |
| reg16mq4 | s0 44.0/45.4 | 45.4 |
| all3 (reg16+mq4+lastloss) | s0 45.4/51.6 | 51.6 |

Verdicts against PASSMARKS.md:
- Original per-run marks (bar 45.5 from N = |base - base-s1| = 0.15): reg16, mq4, lastloss pass; inject wrong; mq4's mechanism mark
  FAILS (first-ASK recall +0.8, needed +5), so its gain is not from better retrieval.
- Addendum 3 (two runs of lastloss seed 0 on two boxes gave 46.0 vs 51.4: GPU nondeterminism alone moves validation ~5 points):
  lastloss HELPS on 2 runs (mean +4.7 over base at 8 loops, worst run 46.0 > best base 44.3). reg16, mq4, all3 have one run each:
  promising, not established. inject: no effect. reg16mq4: no gain on its one run.
- lastloss loop mark: 8 loops vs 2 loops on validation +15.9 (51.4 vs 35.5) and +12.7 (46.0 vs 33.3): PASS. The loops do work.
- Inference-only, base: min_loops 3/5/8 gives validation +2.1/+2.0/+1.8 (mark +3: FAIL) but dev +6.1/+7.1/+6.8.

Descriptive (diag):
- Zeroing all 4 registers just before decoding changes nothing in base (42.5 -> 42.7): the decoder does not read them; their only
  role is ASK/HALT and steering the other rows. With 16 registers, zeroing them costs 5.4 points (48.7 -> 43.3): used.
- Resetting the question rows to their loop-0 values costs ~10 points in base and ~24-30 in lastloss: the loops write real
  work into the question rows.
- State change per loop falls fast (registers ~6.7x their size in loop 1, 1.8 in loop 2, 0.14 by loop 8).

Caveats: 6,000 steps (half of v1); D only, no bridge or creative module; one data build; few runs per arm.
