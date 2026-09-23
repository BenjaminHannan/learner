# Experiment 19 — forgetting readout, amended per Astra's ruling 7

Written 2026-09-20 by Fable before any registered seed (1900–1902) exists. Supersedes the TRIGGER in `FORGETTING-READOUT.md` (sha256 40ad7018…, kept unchanged for provenance). Authority: `design/v3/19-rulings-1.md`, ruling 7. Secondary; cannot alter experiment 19's primary verdict, choose recipes or checkpoints, or show that recent activity is the cause.

## Registered trigger ("replicated forgetting screen", not a significance test)
Score awake-final and offline-final on the identical 7 F + 4 H development cells for every architecture × seed × arm. Answer and strict counts are recorded separately (each /64, never added). TRIGGER = one fixed (architecture, arm, cell, metric) with awake_count − offline_count ≥ 7 in ≥ 2 of the 3 registered seeds. Different cells, metrics or arms cannot supply the two replications. Runs must pass the awake-fit gate; an H cell is eligible for a metric only when its awake count for that metric is ≥ 58/64. All counts and eligibility reported; denominator stays three seeds.
- Any D trigger → experiment 20 advances to implementation and its own freeze.
- T-only trigger → baseline note; 20 stays parked for D.
- Complete evidence, no trigger → 20 parked. Missing evidence → UNDETERMINED (not "no forgetting").

## Fable's predictions
P62–P64 in the original file were written against the looser original trigger (any cell per seed); they stay on the ledger as such and will be scored against that original wording. New forecasts for the amended trigger:
| # | Statement | Probability |
|---|---|---|
| P65 | D: TRIGGER under the amended rule | 0.08 |
| P66 | T: TRIGGER under the amended rule | 0.25 |
| P67 | At least one architecture ends UNDETERMINED (a seed fails the awake-fit gate or a run is missing) | 0.55 |
