# Incident 2 — long-run launch refused by the capacity check (no training ran)

2026-09-20 19:42 UTC. Same cause as incident 1, repeated by the operator: `run_longrun.sh` was created and started in one shell command whose text contained the python path, the script name and the word `longrun`, so the worker counter counted the launching shell as a third audit worker. All five rounds of `longrun` calls exited with the registered capacity refusal within seconds; no model was initialised and no update taken. A `report` was written on the (unchanged) factorial results only. Logs kept unchanged in `logs-refused-launch-2/`. Relaunched 19:43:07 UTC with a bare `./run_longrun.sh`; script, plan, seeds, predictions unchanged; no `--force-capacity`.

Operator rule from now on: create launch scripts in one command and start them in a separate command that names only the launcher.
