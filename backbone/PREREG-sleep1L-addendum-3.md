# Sleep-1L addendum 3 (2026-10-24 ~11:25Z, after S0 only, before any slept arm was scored)
Base LFM2.5 scored 41.4% on ARC-Easy with the letter-logit method, far below what a 24B model should get, so the metric (not the
model) is the likely problem. The ARC score used for M4 is now a greedy 8-token answer parsed for its first standalone letter
(A-E); the logit score is kept as `acc_logit`. S0 is rerun with the new scorer. M4's rule is unchanged (S2 >= S0 - 2).
