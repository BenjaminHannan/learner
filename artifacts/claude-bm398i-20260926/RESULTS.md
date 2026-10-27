# bm-398i RESULTS: adapter on/off switch (benchmarks thread, written 2026-09-26 15:33 UTC)

**Verdict: PASS.** Turning the adapter off gives back the plain model exactly, and switching it on and off
between requests leaves no trace. This is the CPU run with the fixed-seed random adapter. Run 2 was launched once,
from a fresh process, under AMEND-1 (the memory fix). Counts only: no question, answer or reply is quoted.

## Marks (PLAN.md, fixed before the run)

| Mark | Needed | Result |
|---|---|---|
| I1: off replies equal base | 75 of 75, logits diff exactly 0.0 | 75 of 75 (GSM8K 15/15, MMLU 40/40, LoCoMo 20/20); logits diff 0.0 |
| I2: mixed-off replies equal base | 75 of 75 | 75 of 75 |
| I2: mixed-on replies equal the on pass | 75 of 75 | 75 of 75 |
| I2: off logits after mixing equal base | exactly 0.0 | 0.0 |
| I3: the adapter changes replies | at least 20% (15 of 75) | 57 of 75 (GSM8K 14/15, MMLU 30/40, LoCoMo 13/20) |

- The mixed pass switched between requests 149 times.
- With the adapter on, the largest logit change on the compared items was 3.56.
- No off or mixed-off reply differed from base, so the "proved wrong" condition did not occur.

## Predictions
- P1 (95%) PASS: **right**.
- P2 (90%) at least 60 of 75 replies changed: **wrong**. 57 changed. MMLU's 16-token answers changed least
  (30 of 40).

## Check
- Seals: SEAL.sha256.txt 5 of 5 OK and SEAL-amend1.sha256.txt 3 of 3 OK, both checked after the run.
- Recount: a separate script compared the four reply passes in replies398i.jsonl and got the same counts for
  every row of the table. It is not a blind recount, because nothing here was judged.

## Run facts
- Start 13:58 UTC, end 15:32 UTC, 5,674 seconds. Pass timings (cumulative seconds): base 3,369, off 4,010,
  on 4,541, mixed 5,674.
- Peak resident memory was 4.77 GiB. Run 1 was killed at 14 GB, so the AMEND-1 fix worked.
- **Deviation (timing only):** the base pass took 3,369 s, against 672 s in run 1. For most of it the bm-398e
  drafts job shared the 4 CPU cores. It was paused at about 14:45 UTC and resumed automatically at 15:32 UTC.
  Outputs are deterministic compares, so the marks are unaffected.
- Files:
  - result.json (sha256 b006d054…73a7) is in this folder.
  - replies398i.jsonl (75 rows, sha256 59c56998…2807) holds benchmark replies, so it stays in the scratchpad and
    is not committed.

## What it means and what follows
- The switch is ready for bm-397m inside Month-end's agent once the router exists, and for any later adapter
  such as bm-398r's.
- It shows only that switching can't harm the base. It says nothing about whether an adapter helps.
- The confirmation with the real bm-397t adapter now runs on a rental (rent-bm398r part 1, twice on one GPU,
  same marks). It replaces the BensPC run the PLAN named, under Ben's 13:30 rule.
