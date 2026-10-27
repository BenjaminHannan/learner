# slp-361 results (undo a whole sleep; Fix-sleep thread, 2026-09-25 ~01:05 UTC, CPU, $0)

**Verdict: PASS, 7/7 marks on both seeds.** Seal checked before the run (3/3 OK). Same combined tree and
rebuilt base checkpoint as slp-360 run 2.

| Mark | s1 | s2 |
|---|---|---|
| P361.1 files identical after a rejected night (except state.json) | 0 differ | 0 differ |
| P361.2 main notebook byte-identical | yes | yes |
| P361.3 12 probe replies identical to never sleeping | 12/12 | 12/12 |
| P361.4 experience log kept | 75 = 75 | 75 = 75 |
| P361.5 accepting judge = no 361 at all | 87/87 replies, installed both | same |
| P361.6 created files moved to undo361/, none deleted | 3/3 | 3/3 |
| P361.7 the undone night redone with an accepting judge | installed, 5/5 right | installed, 5/5 right |

What a rejected night left behind: nothing outside undo361/night001/ (the word-route file, the word checkpoint
and the scrap log were moved there). Probes after the rejected night: 5/5 "I don't know", exactly as if it had
never slept; after the redo, 5/5 right.

Limits: one sleeper (Sleep145) and one world; the snapshot restores plain in-memory state of the loop, reasoner
and sleeper, so a future sleep job that keeps state elsewhere must keep it in files under the state dir.
The default judge accepts everything; the checks that decide (364) come next.
