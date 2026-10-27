# Test D addendum 1: move to the equal-practice ruler

Written 2026-09-28 02:58 UTC (`date -u`), after this design's practice and source guard and **before any maze run
or maze score of this design**. No threshold changes.

**Why.** PASSMARKS-D.md was committed at 23883c699 (01:41 UTC) against the first ruler. That ruler has since
reported INCONCLUSIVE at V3 (artifacts/claude-fewex-20260927/RESULTS.md) and was replaced by the equal-practice
ruler (ADDENDUM-4.md) with RACE-ADDENDUM-1.md for the design races (sealed at bcb64da89; harness
scripts/claude_fewex_eq_bench.py at db814a8fb). I read the baseline's dev tables there. No score of this design
existed then or exists now.

**The substitution, exactly as RACE-ADDENDUM-1.md makes it for every race mark:**
- Every `F_all` in PASSMARKS-D.md (the common gates, the +10 over the loop, and the proved-wrong clause) becomes
  `F_eq`: the mean over the eight positive rungs k = 1, 4, 16, 64, 256, 1,024, 4,096 and 16,384 of 100 x right /
  300 on the 9x9 holdout, learned stop. Each rung trains a clean copy for exactly 2,048 updates.
- The 64k sleep branch becomes the 16,384 sleep branch (`sleep.16384`); the k = 64 sleep stays.
- Thresholds unchanged: +10 over the paired loop in both seeds; +5 over the paired practised plain net and over
  this design's own fresh copy; old kinds at least 190 of 200 before, and not more than 6 of 200 below the loop
  before and after both sleeps. Proved wrong: `F_eq` no higher than the loop in both seeds (ties count as no
  higher), or a maze gain only by breaking an old-kind gate.
- "The loop" and "the practised plain net" are the baseline's equal-practice runs `eq-runs/loop-s{seed}-pre` and
  `eq-runs/plain-s{seed}-pre`. The loop is not retrained.
- The report-only routing check uses k = 0, 64 and 16,384 and the 16,384 sleep.

**How it runs (no harness edit):** `python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_sparse_net
--arm loop --seed {0,1} --init {pre,fresh} --source artifacts/claude-sparse-20260928/runs/sparse-s{seed} --out
artifacts/claude-sparse-20260928/eq-runs/sparse-{pre,fresh}-s{seed}`, fp32 on CPU. Dev runs start only after the
baseline's `EQ-DEV-GATE.json` on main says PASS. The holdout runs once, after all four dev runs finish, with the same
harness's `holdout` command (which itself refuses unless that gate passed). If the baseline's gate says
INCONCLUSIVE, Test D is INCONCLUSIVE and no maze run of this design is scored.
