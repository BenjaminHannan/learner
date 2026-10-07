# Fast-sleep research loop, 10-07 (C2 first try to 70%)

Ben's ask: get the C2 first-try score to 70% on unseen questions with at most "5 hours of M1 Pro GPU" of counted compute (read as 10,000 TF).
Run with the research-loop harness on a Vast RTX 5090 (cap $4, spent about $2.9), DEV for the loop, a fresh 512-question holdout for checks.

**Result (compliant with Ben's deployed-autonomy rule): holdout 71.3 +/- 2.5% first try over 6 parents (s200-s205), from 41.6% at the start;
4 of 6 parents at or above 70. About 2,400 TF per sleep, no skills harm.** Segment 1 (not compliant: night temperature tuned on DEV answers,
replay inputs from the test generator's range) reached 72.7% on 2 parents and is reported separately.

- `report.md`: findings (headline, kept changes, failures, caveats, next ideas) and the harness's tables (segment 2 only).
- `program.md`: goal, benchmark, assumptions and every rule change during the loop. `hypotheses.md`, `notes.md`: idea cards and sources.
- `log.jsonl`: every reference, calibration, trial and holdout check of both segments. `runs/`: the harness's per-seed logs (segment 1's
  calibration logs were overwritten by segment 2's, same names). `patches/`: every trial's diff (`0007-bold.diff` = the second-night trial,
  stopped mid-run by the rule change and not counted). `final/`: the two post-loop holdout seeds (s204, s205), run outside the harness only to
  reach the 6-seed rule.
- Code: `creative/rl/` (method.py = the compliant sleep; eval_c2.py, refs.py, make_holdout.py, remote.py = the locked benchmark).
- Holdout file: creative/data/c2rl/holdout.jsonl (new generator tag, seed 7031); C2b's sealed test split was never read.
- Outside opinion: reviews/gpt-c2-affine-after-big-sleep-2026-10-07.md (why a·x+b stays at about 15%).
