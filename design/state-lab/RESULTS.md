# State lab results (00:20 UTC 2026-10-24, 14 runs; supersedes the 23:15 version below)

**Bottom line: with repeats, no training change is established.** The plain baseline itself spans 43.8-49.9 on validation
(8 loops) across 3 runs, and one recipe+seed spans 46.0-51.4 across two boxes. Every arm's runs fall inside or near that spread.

| arm | validation at 8 loops, per run | mean |
|---|---|---|
| base | 44.3, 43.8, 49.9 | 46.0 |
| inject | 43.3, 45.1 | 44.2 |
| reg16 | 49.4 | 49.4 |
| mq4 | 49.0, 46.0 | 47.5 |
| lastloss | 46.0, 51.4, 43.3, 49.5 | 47.5 |
| reg16mq4 | 45.4 | 45.4 |
| all3 | 51.6 | 51.6 |

Addendum-3 rule (mean >= base mean + 3 AND worst run > best base run): no arm passes. The single-run arms (reg16, all3)
cannot pass the "worst > best base (49.9)" test without repeats; reg16-s1 died with its host. Earlier "wins" reported at 23:15
were single-run luck.

What IS shown:
- Forcing 8 loops at inference (`answer(min_loops=8)`), no retraining: validation +2.4 points on average (up in 12/14 runs),
  dev +8.7 (up in 14/14). Cheap to adopt in v1 evaluation.
- lastloss changes how loops are used: validation gain from 2 loops to 8 is +13.0 (mean of 4) vs +7.9 for base (3), but it
  starts lower, so the 8-loop endpoint is level (47.5 vs 46.0). Its HALT-mode dev accuracy drops (~70 vs ~76).
- The decoder ignores the 4 registers in base (zeroing them: 42.5 -> 42.7); with 16 registers zeroing costs 5.4 (one run).
- inject (input injection): no effect.

Next if this line continues: reduce noise first (more seeds per arm, or longer runs / a larger validation set), then retest
reg16, mq4 and lastloss.

---

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
