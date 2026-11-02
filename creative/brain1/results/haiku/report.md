# Probe-1 report

192 pools, 2304 tries, 130 solvable pools. Replay gate: 100.00% of tries reproduce recorded success.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 |  |
| VOTE | 22.4 | 33.1 |  |
| SELF | 34.4 | 50.8 | 0.692 |
| PROBE-S | 36.5 | 53.8 | 0.661 |
| PROBE-R | 32.8 | 48.5 |  |
| HAIKU-PROBE | 49.5 | 73.1 | 0.838 |
| HAIKU-PROBE-R | 50.0 | 73.8 |  |
| PROBE-R (expected over ties) | 32.7 | 48.4 |  |
| HAIKU-PROBE-R (expected over ties) | 49.7 | 73.4 |  |

Verdict: **INCONCLUSIVE**
Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= 39.4%); P2 AUROC of the probe score >= 0.75. Proved wrong: PROBE-S <= SELF + 1 point (<= 35.4%). HAIKU-PROBE is reported only. P1=FAIL, P2=FAIL
Pick-1 numbers quoted in PREREG: RAND 19.7, VOTE 22.4, SELF 34.4 (SELF AUROC 0.692); the table recomputes them from the same files.

## Diagnostics: K2 probes

- samples 192 over 48 tasks; unparsable replies 0; samples with no valid probe 55; tasks with no valid probe 2
- validity rate 88.4% (372 of 421 checks pass the sandbox validator); checks per sample 2.19 raw, 1.94 valid; samples with more than 6 checks 1
- reference agreement 60.2% of 372 valid probes pass the reference plan's end state; 2 of 46 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 12.0% (23 of 192)

## Diagnostics: Haiku probes (reference)

- samples 192 over 48 tasks; unparsable replies 0; samples with no valid probe 0; tasks with no valid probe 0
- validity rate 99.8% (891 of 893 checks pass the sandbox validator); checks per sample 4.65 raw, 4.64 valid; samples with more than 6 checks 0
- reference agreement 81.0% of 891 valid probes pass the reference plan's end state; 13 of 48 tasks have every valid probe passing the reference
- uninformative pools (all 12 tries tie on the probe score): 5.7% (11 of 192)
