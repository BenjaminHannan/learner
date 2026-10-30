# Notebook-2 stage 0 results (retrieval only, no model), 2026-10-26 00:35Z

Shown for LongMemEval-S, 8k-token budget, one fixed sample; no reader involved. AllHit = every answer session
contributes at least one evidence turn pair to the context.

## Decision set: 111 non-abstention questions of the 120-question Stage-1 set (Amendment A)
| Arm | AllHit | EvRecall |
|---|---|---|
| S0 BM25 | 83.8 | 86.3 |
| S1 dense bge-small | 87.4 | 90.1 |
| S2 hybrid RRF | **91.0** | 93.2 |
| S3 hybrid + neighbour pairs | 87.4 | 90.8 |
| S4 whole sessions | 82.0 | 87.5 |

Per type (AllHit S0 / S2 / S3 / S4): knowledge-update 100/100/100/95; multi-session 47/53/53/47;
single-session-assistant 95/100/100/100; single-session-preference 60/85/80/70; single-session-user 100/100/100/94;
temporal 95/100/84/79. Paired S2 vs S0: S2 wins 8, loses 0 (exact sign test p = 0.008).

## Verdicts
- Z1 (S2 >= S0 + 10): **FAIL**, +7.2 points. The gain is real (8-0 paired) but smaller than the pre-set mark. "Wrong if
  S2 <= S0 + 3" is not triggered.
- Z2 (S3 >= S2 + 3): fail; neighbours cost budget and push other hits out (S3 -3.6).
- Z3 (S4 >= max + 3): fail; whole sessions are worst (82.0), as 2505.19549 predicts, against 2410.10813's Table 3 (LongMemEval-M, different setup).
- **Stage-1 retriever = S2** (by the pre-set rule).
- Running total on 174 of 470 so far: S0 82.2, S1 86.8, S2 89.1, S3 85.1, S4 80.5 (same order).

## Link to Notebook-1 (shown, 55 non-abstention sample items, Haiku reader)
R (BM25 top 10) was wrong on 16. In 9 of those, BM25 had missed an evidence session, and the oracle reader got all 9
right, so they are search misses. The hybrid finds the evidence for 3 of those 9. In the other 7, the evidence was
already in the context and the oracle reader also failed them (reader-hard items). Suggested: the remaining misses
are mostly multi-session questions that need more sessions than an 8k budget holds; that is where model-written queries
or a second round (Stage-1 Q/T) or a bigger budget would have to help.
