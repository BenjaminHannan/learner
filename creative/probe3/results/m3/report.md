# Probe-1 report

192 pools, 2304 tries, 130 solvable pools. Replay gate: 100.00% of tries reproduce recorded success.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| PROBE-S | 48.4 | 71.5 | 0.784 |
| PROBE-R | 47.9 | 70.8 |  |
| PROBE-R (expected over ties) | 47.0 | 69.4 |  |

Verdict: **PASS**
Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= 39.4%); P2 AUROC of the probe score >= 0.75. Proved wrong: PROBE-S (<= 37.5%). HAIKU-PROBE is reported only. P1=ok, P2=ok
Pick-1 numbers quoted in PREREG: RAND 19.7, VOTE 22.4, SELF 34.4 (SELF AUROC 0.692); the table recomputes them from the same files.

## Diagnostics: K2 probes

- samples 192 over 48 tasks; unparsable replies 0; samples with no valid probe 0; tasks with no valid probe 0
- validity rate 99.0% (773 of 781 checks pass the sandbox validator); checks per sample 4.07 raw, 4.03 valid; samples with more than 6 checks 0
- reference agreement 77.7% of 773 valid probes pass the reference plan's end state; 11 of 48 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 7.3% (14 of 192)
