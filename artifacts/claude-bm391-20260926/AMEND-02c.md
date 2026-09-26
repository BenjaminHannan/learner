# bm-391 AMEND-02c: 0.2c's no-harm rows on GSM8K and MMLU-Redux (benchmarks thread, 2026-09-26 ~02:40 UTC)

Registered at Month-end's request (02:01 UTC), before any run of 0.2c on any public test. PLAN.md is sealed and
unchanged; this adds one arm, X02c, on the general tests only. LoCoMo is not run for 0.2c (it would not finish by
11:00 UTC), so this amendment cannot give 0.2c a benchmark PASS: M1 and M3 are not run and bm-391's scorecard for
0.2c stays incomplete. It registers only the no-harm reading.

## What is tested
- X02c = claude_e2e02c:build_02c, the agent AFTER its nights. The code is month-end's 07:30 UTC seal of 0.2c
  (switches set by its PASSMARKS-02c addendum). Before launch, the job records that seal file's path and sha256 in
  RESULTS-rent02c.md; every line must check OK.
- --model = the reader the 0.2c addendum names: the lis-319 merged reader (model.safetensors sha256
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76), or lis-301 (b4fd93a2…) if the addendum says so.
  --gen-model = BASE (MiniCPM5-1B, revision 87179e5c).
- The slept weights. Which case applies is fixed by where the Director puts the job, before it runs:
  - (a) inside Month-end's 0.2c rental: after its sleep step, with SLEEP02C_ADAPTER = that run's adapter02c.pt.
    Then X02c is exactly the agent 0.2c's own panels test.
  - (b) as its own job: first `python -B scripts/claude_twinb_wrap.py scripts/claude_sleep02c.py --arm
    claude_e2e02c:build_02c --model READER --gen-model BASE --out SLEEPDIR` (3 nights), then SLEEP02C_ADAPTER =
    SLEEPDIR/adapter02c.pt. Then it is an independent second night with the same recipe and seeds, and is reported
    that way.
- Harness, data, prompts and scorer: bm-390's, sealed and unchanged (GENERAL(task, B, name) exactly as in
  rent-bm391.md step 5, name X02c).

## Marks (M4 unchanged, bm-390's bars)
- M4a: X02c MMLU-Redux-300 right ≥ 41 (T − 3 points; T = 50).
- M4b: X02c GSM8K-300 right ≥ 182 (T − 3 points; T = 191).
- N1 (Month-end's no-harm reading, paired): on GSM8K, X02c − T ≥ −3.0 points over the same 300 items. Its point
  value equals M4b's; the paired bootstrap's 95% interval (seed 390, 10k, question-level) and the counts of items
  lost and gained against T are reported beside it.
- No-harm PASS = M4a and M4b. A miss is a registered FAIL of 0.2c's general no-harm row.

## Report only
X02c − R and X02c − ER on both tests, if bm-391's R and ER runs exist; route383 and ep-382 counters; GSM8K right under
a strict pick ("answer is N" only), for X02c and T, because the sealed pick can credit placeholder answers; MMLU
replies with no letter.

## Predictions
- M4a passes: 90% (point guess 150/300).
- M4b passes: 35% (point guess 172/300). The route samples 4 replies at temperature 0.7, where T is greedy, and the
  sleep adapter was trained on number puzzles, not word problems.
- In case (b), the second night's TEST gain is within 30% of 0.2c's own night: 60%.

## Where it runs
The Director's choice: case (a), two extra lanes in Month-end's 0.2c rental after its sleep step; or case (b), its own
job (BensPC at $0, or a 5090 at ~$0.50/h, about 2 h, cap $2). Each command is launched once. A crash with no output
may be relaunched once, unchanged, and that is disclosed.
