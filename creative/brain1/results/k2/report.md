# Probe-1 report

192 pools, 2304 tries, 130 solvable pools. Replay gate: 100.00% of tries reproduce recorded success.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| PROBE-S | 42.7 | 63.1 | 0.782 |
| PROBE-R | 40.1 | 59.2 |  |
| PROBE-R (expected over ties) | 39.4 | 58.2 |  |

Verdict: **PASS**
Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= 39.4%); P2 AUROC of the probe score >= 0.75. Proved wrong: PROBE-S <= SELF + 1 point (<= 35.4%). HAIKU-PROBE is reported only. P1=ok, P2=ok
Pick-1 numbers quoted in PREREG: RAND 19.7, VOTE 22.4, SELF 34.4 (SELF AUROC 0.692); the table recomputes them from the same files.

## Diagnostics: K2 probes

- samples 192 over 48 tasks; unparsable replies 3; samples with no valid probe 3; tasks with no valid probe 0
- validity rate 94.1% (619 of 658 checks pass the sandbox validator); checks per sample 3.43 raw, 3.22 valid; samples with more than 6 checks 2
- reference agreement 60.1% of 619 valid probes pass the reference plan's end state; 5 of 48 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 6.8% (13 of 192)
