# CardFold sleep experiment — freeze note (Fable, 22 Sep 2026; written BEFORE seeds 4101-4103 are run)

Script: scripts/fable_cardfold_sleep.py (drafted by GPT xhigh from my spec; I fixed a literal-"\n" reporting bug and
raised budgets). Practice seed 4001 only was used for calibration: run 1 (1,200/300 updates) was VOID (base 0.70);
run 2 (12,000/3,000 updates, ~11 min) base 0.995, S fresh 0.895, R fresh 0.045, S long 0.005, S regression drop 0.
Frozen: BASE_UPDATES 12000, SLEEP_UPDATES 3000, everything else as drafted. Marks M1-M5 unchanged from the spec.
Registered seeds: 4101, 4102, 4103. Verdict per seed, never averaged. One change after this = a new registration.

Predictions (coordinator):
- P-a: coded verdict FAIL in all three seeds (because of M3, longer inputs) — 0.90
- P-b: M1 (S fresh >= 0.80) passes 3/3 — 0.70
- P-c: M2 (S beats same-compute raw-log by >= 0.20) passes 3/3 — 0.93
- P-d: M3 (S long >= 0.50) passes in >= 1 seed — 0.05
- P-e: M4 (S regression drop < 0.03) passes 3/3 — 0.90
- P-f: no seed VOID — 0.80
- P-g: S0 (no replay) regression accuracy < 0.20 in 3/3 — 0.90
