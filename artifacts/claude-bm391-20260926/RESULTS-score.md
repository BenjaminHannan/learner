# bm-391 RESULTS: the 0.2 scorecard did not finish (benchmarks thread, 2026-09-26 ~08:55 UTC)

Verdict: **no verdict.** The rental stopped at its money rule (BUDGET-STOP, builder-outbox RESULTS-rent.md). Only
1 of the 9 registered commands finished. M1, M3 and M4 cannot be judged for any build, and nothing here is a PASS or
a FAIL of 0.2. Counts only.

## What ran
- The rental ran 01:51-08:03 UTC (6.21 h, about $3.17 projected). Uploading the tree and the 2 GB reader took until
  04:31, when the registered lanes started.
- The agent arms answered about 2 LoCoMo questions a minute (~25 s each; the GPU was mostly idle). The run's own
  measurement: a full arm (1,986 questions) needs about 14 h.
- Finished: GENERAL(mmlu, build_383, R), 300 rows, sha256 4660101142a21c0313b9d876753e2e70efe717bd8bd39faeb9534c23b526dfa8.
- Stopped with partial logs only (no answer file): LoCoMo ER (457 ep382 rows) and E (446), and GSM8K R (no output).
  Never started: the other five commands.

## The one finished row (report only)
- MMLU-Redux-300, sealed scorer: R 109 of 300, against T 50 (score-R/). This would clear M4's MMLU bar (≥ 41) for R.
  B8's point guess was 145.
- Much of the rise over T is probably format: T gave no letter on 234 of 300 (see bm-397t). Inferred, not checked.

## What it means
- Shown: the joined agent is far too slow for a full LoCoMo scorecard on one rental. It rebuilds itself for every
  question, at about 14 h per arm, or about $7 per arm at $0.51/h.
- A 0.2 or 0.2c LoCoMo scorecard needs either a faster agent path (build once per conversation, not once per
  question) or a sampled, registered subset. Neither is registered yet. No re-run without Ben's OK on money.
- Lesson: time one registered command on a small real slice before sealing a rental's budget.
