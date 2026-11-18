# Pick-1 results (Oct 26)

Verdict (prereg): **INCONCLUSIVE**. P1 fails narrowly (SELF +14.7 pts over RAND, mark +15), P2 passes (+12.0 over VOTE),
P3 fails narrowly (AUROC 0.692, mark 0.70). Not proved wrong (SELF far above RAND + 5).

| picker | pick rate, all 192 pools | 130 solvable pools | AUROC |
|---|---|---|---|
| RAND (one guess) | 19.7 | 29.1 | |
| VOTE (most common plan) | 22.4 | 33.1 | |
| SELF (K2 judges own tries, P(yes)) | 34.4 | 50.8 | 0.692 |
| SELF-VOTE | 34.4 | 50.8 | |
| HAIKU (Claude Haiku 5.5, batch, reference) | 34.4 | 50.8 | 0.728 |

Shown: SELF and HAIKU reach the same pick rate with different picks (same pick in 47/192 pools; recomputed
independently). K2-3.7B judging its own 12 tries is about as good a picker as Haiku here. 131/2304 Haiku replies
refused to score ("can't verify, tool output truncated") and were scored 5 per the code.
Suggested: 12 sandboxed tries + self-judge turns ~20% first-try success into ~34% (1.7x) on these hard jobs,
without any answer key. Raw: /mnt/project-files/creative/pick1/out/pick1/ (Kaggle T4 fp16, 8 min) and
/mnt/project-files/creative/pick1/haiku_scores.jsonl (batch msgbatch_011dAaz9UiPeqid28BWQWEiN, ~$0.04).
