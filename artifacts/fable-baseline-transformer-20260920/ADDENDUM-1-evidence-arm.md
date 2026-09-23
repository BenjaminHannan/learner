# Addendum 1 — register the supervision-parity arm (written 2026-09-20 after A-long, before any evidence-aux run)

Observed (A-long, seeds 0/1/2, 11,000 updates): final token accuracy ≈ 0.50/0.50/0.53; every cell at chance, including one-hop (1–9/64).
By the registered fit gate this is **"under-trained — inconclusive"**, not evidence for System S. It looks like the same start-up stall the
lookup model shows when trained from answers alone (no arm of S was ever trained that way on full stories successfully either).

New arm **A-ev**: `steps`/`line`, 6,000 updates, `--evidence-aux 0.5`, `--time-cap 1700`, folder `steps-line-evidence`, seeds 0/1/2.
This gives the baseline the same supporting-line supervision S's v1 lookup had (S's dispatcher result used that lookup). The targeting was
verified by `tests/test_fable_baseline_evidence_aux.py` (28 checks, no bug; the scored position is the one *predicting* each output token; the
loss is pooled over (question, step) pairs). Frozen files are unchanged; `run_wave.sh` cannot pass the flag, so this arm uses
`run_wave_ev.sh` (hash appended to FREEZE.sha256).

Predictions (Fable): P10 fit gate ≥ 0.95 in ≥ 2/3 seeds — p 0.65. P11 given fit, k ≤ 3 practised-relation cells pass in ≥ 2/3 seeds — p 0.6.
P12 any seed passes all k = 4…8 cells — p 0.07. Falsifiers are the complements.
