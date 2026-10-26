# Pick-1 report

192 pools, 2304 transcripts, 130 solvable pools.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| SELF-VOTE | 34.4 | 50.8 |  |
| FULL | 31.8 | 46.9 | 0.713 |
| THINK | 30.2 | 44.6 | 0.646 |

Verdict: **INCONCLUSIVE**
Pass marks (PREREG): P1 SELF >= RAND+15 pts; P2 max(SELF,SELF-VOTE) >= VOTE+5 pts; P3 SELF AUROC >= 0.70. Proved wrong: SELF <= RAND+5. HAIKU is reported only. P1=FAIL, P2=ok, P3=FAIL
