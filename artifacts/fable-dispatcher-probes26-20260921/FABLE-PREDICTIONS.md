# Experiment 26 (dispatcher fault-localisation probes) — coordinator's forecasts

Fable (coordinator), written 2026-09-21 UTC before any probe code exists. Statements are those of
`design/v3/26-dispatcher-stop-probes-registration-fable-review.md` §11 (sha 7d7708e7…); only the probabilities are mine.

| # | Same statement as | Probability |
|---|---|---|
| P112 | P102 positive control passes | 0.85 |
| P113 | P104 R1(8) holds in all three 19-awake checkpoints | 0.30 |
| P114 | P105 early-attribute fault in ≥ 6 of 9 19/19b checkpoints | 0.70 |
| P115 | P107 premature STOP on a handed prefix in ≥ 1 family | 0.20 |
| P116 | P108 both collapsed U8 checkpoints: STOP intact, operation pointer at fault | 0.50 |
| P117 | P111 operation-only does not rescue k8-held in all three 19-awake | 0.80 |
