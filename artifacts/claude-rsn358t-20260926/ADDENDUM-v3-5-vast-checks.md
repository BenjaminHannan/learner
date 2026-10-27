# 358t v3 addendum 5: two tighter vast checks (sleep research thread, written 2026-09-27 13:44:06 UTC, before any v3 run)

Additive to ADDENDUM-v3-4-vast.md. Marks, seal, seeds and arms are unchanged.
1. Offers above $0.65/h are skipped (it was $0.75/h). With 8 runs of about 75 min at once, 16 evals and set-up (about 1.9 h at worst), that keeps the worst case near $1.24, under the $1.45 guard stop. If no 5090 is offered at or under $0.65/h, the start rents nothing and says so.
2. Expected files: before any destroy, every run that did not die must have brought back train_log.jsonl, train_summary.json, tests.json and tests-ema.json. Otherwise the instance is stopped, not destroyed, and flagged. The Director asked for this at 13:37 UTC for the 358u kit. 358u's released kit is left as it is while it runs.
