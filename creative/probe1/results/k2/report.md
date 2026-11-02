# Probe-1 report

192 pools, 2304 tries, 130 solvable pools. Replay gate: 100.00% of tries reproduce recorded success.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| PROBE-S | 29.7 | 43.8 | 0.578 |
| PROBE-R | 21.9 | 32.3 |  |
| PROBE-R (expected over ties) | 21.4 | 31.6 |  |

Verdict: **PROVED WRONG**
Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= 39.4%); P2 AUROC of the probe score >= 0.75. Proved wrong: PROBE-S <= SELF + 1 point (<= 35.4%). HAIKU-PROBE is reported only. P1=FAIL, P2=FAIL
Pick-1 numbers quoted in PREREG: RAND 19.7, VOTE 22.4, SELF 34.4 (SELF AUROC 0.692); the table recomputes them from the same files.

## Diagnostics: K2 probes

- samples 192 over 48 tasks; unparsable replies 5; samples with no valid probe 87; tasks with no valid probe 4
- validity rate 86.1% (247 of 287 checks pass the sandbox validator); checks per sample 1.49 raw, 1.29 valid; samples with more than 6 checks 0
- reference agreement 38.5% of 247 valid probes pass the reference plan's end state; 2 of 44 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 33.9% (65 of 192)
