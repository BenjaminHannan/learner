# Probe-1 report

192 pools, 2304 tries, 130 solvable pools. Replay gate: 100.00% of tries reproduce recorded success.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| PROBE-S | 37.5 | 55.4 | 0.663 |
| PROBE-R | 36.5 | 53.8 |  |
| PROBE-R (expected over ties) | 34.5 | 50.9 |  |

Verdict: **PROVED WRONG**
Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= 39.4%); P2 AUROC of the probe score >= 0.75. Proved wrong: PROBE-S (<= 37.5%). HAIKU-PROBE is reported only. P1=FAIL, P2=FAIL
Pick-1 numbers quoted in PREREG: RAND 19.7, VOTE 22.4, SELF 34.4 (SELF AUROC 0.692); the table recomputes them from the same files.

## Diagnostics: K2 probes

- samples 192 over 48 tasks; unparsable replies 1; samples with no valid probe 49; tasks with no valid probe 0
- validity rate 87.8% (373 of 425 checks pass the sandbox validator); checks per sample 2.21 raw, 1.94 valid; samples with more than 6 checks 1
- reference agreement 57.6% of 373 valid probes pass the reference plan's end state; 4 of 48 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 15.1% (29 of 192)
