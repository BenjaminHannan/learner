# Incident 1 — first launch refused by the capacity check (no training ran)

2026-09-20 19:19:54–19:20:02 UTC. `run_factorial_waves.sh` was started from a shell command whose own text contained the python path, `scripts/fable_startup_factorial_v2.py` and the word `train`. The script's worker counter reads `ps` and counted that launching shell as a third audit worker, so every `train` call saw 3 ≥ 3 and exited with the registered "capacity" refusal (a scheduling result, not a model failure). `transfer` and `report` then ran on nothing. No model was initialised, no update was taken, no run directory was written. The refusal logs are kept unchanged in `logs-refused-launch-1/`.

Fix: relaunched at 19:21:14 UTC with a bare `./run_factorial_waves.sh` command (nothing for the counter to mis-match). Script, plan, manifest, seeds and predictions (FABLE-PREDICTIONS.md sha256 ea9cb332…) are unchanged. No `--force-capacity` was used.
