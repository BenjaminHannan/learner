# lis-319k verify: FAIL (K1)

Written 2026-09-26 15:52 UTC by the reading thread. Counts only; no panel text. Reads: lis319k-panel-mac (lis-319, read once; RESULTS-read.md on builder-outbox).
Its step 4 needed design/v3/60-listener; the Mac agent added only that data path after the read, so the read was not repeated (ADDENDUM-reread.md case 1).
Two blind Opus judges, JUDGE_SAME.md, neutral names, shuffled order (judged/ORDER.txt), 0 disagreements. Verdicts and scorer outputs in judged/.

| Mark | OLD 0.995 | NEW (CORRECT at 0.95) | Bar | Result |
|---|---|---|---|---|
| K1 corrections saved right (of 60) | 2 | 4 | NEW >= OLD + 5 | FAIL |
| K2 wrong saves | 2 | 2 | <= OLD + 1 | pass |
| K3 stale saves | 0 | 0 | <= OLD | pass |
| K4 lookalike saves | 0 | 0 | <= OLD + 1 | pass |
Valid (60 >= 40 corrections, 58 missed >= 8). Not proved wrong (gain 2 > 1). The bar raised only 8 CORRECT facts on the panel.
Fallback (PASSMARKS-FALLBACK): K1 failed, so the diagnosis runs instead of the 0.98 variant.

## Diagnosis (counts only, after the verdict; this panel now chooses nothing further)
Of the 60 correction facts, for lis-319: saved 2; compiler-rejected 22 (owner_not_span 16, rel_not_in_table 3, other 3);
read but under the bar 15 (CORRECT 8, ASSERT 7); other facts read from that turn but not this one 16; nothing read 5.
lis-319f (lis-319t2's read, same panel): saved 4; compiler-rejected 19 (owner_not_span 14); under the bar 12; other facts 17; nothing 8.
The largest single cause is the compiler's owner check: a correction's owner is usually named in an earlier turn ("sorry, she's 13"),
and the compiler only accepts an owner found in this turn or the previous reply. Dev agrees (gold-as-read dry run: 14 of 131 owner_not_span).
Report only: lis-319k's rule on the lis-319f read gives 4 -> 7 corrections, wrong 4 -> 5 (judged/fk_*.json).
