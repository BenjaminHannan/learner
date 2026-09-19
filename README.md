# Beautiful Model experiment harness

This repository contains a bounded persistent-memory prototype. The runnable harness performs real differentiable meta-training: every episode starts from zero persistent memory, applies accepted teaching statements through the functional writer, scores an immediate factual support query after each write, and then scores fresh post-write queries with teacher-forced cross-entropy. Evaluation uses greedy generation and reports exact match, a zero-memory causal control, persistent-memory change norms, and scored-restart identity.

Tier 3 persistent-memory training is intentionally gated. The separate PC-R in-context reader is implemented, but tier 3 remains gated until a real PC-R training run reaches at least 95% exact match on each requested held-out validation tier. Harness completion and that quality threshold are reported separately.

## Local commands

Run these from the project root:

~~~sh
./run.sh audit
./run.sh test
./run.sh smoke --device cpu --steps 2 --seconds 30 --tiers 1 --eval-worlds 1
./run.sh pilot --device cpu --steps 64 --seconds 300 --tiers 1,2 --eval-worlds 4
./run.sh pc-reader --device cpu --steps 64 --seconds 300 --tiers 2,3 --eval-worlds 4
./run.sh evaluate --device cpu --seconds 60 --tiers 1,2 --eval-split validation --eval-worlds 2
~~~

Smoke accepts only 1-3 optimizer steps. Pilot and PC-R are hard-capped at 600 seconds. The pilot defaults to a high step ceiling and a 480-second wall limit, so time normally bounds it; one quarter of a training run is reserved for held-out evaluation and restart checks. CUDA is never selected automatically. Each run writes a uniquely named bounded JSON result, and a completed persistent-memory evaluation also writes one bounded restart checkpoint through Budget. Long per-step logs are capped in result JSON instead of growing without bound.

The JSON status is one of completed, time_limit, or failed_controls. Completed means the requested bounded harness run completed and its causal/restart controls passed; it is not a claim that the model answered correctly. Model quality is reported separately through measured exact-match fields.

## Conservative BensPC workflow

The existing remote helper performs a read-only GPU preflight, syncs without deleting remote files, and never installs packages or kills unrelated processes:

~~~sh
sh scripts/remote_benspc.sh preflight
sh scripts/remote_benspc.sh sync
sh scripts/remote_benspc.sh test
BENSPC_PILOT_SECONDS=600 sh scripts/remote_benspc.sh pilot pilot --device=cuda --steps=10000 --seconds=480 --tiers=1,2 --eval-worlds=4
BENSPC_PILOT_SECONDS=600 sh scripts/remote_benspc.sh pilot pc-reader --device=cuda --steps=10000 --seconds=480 --tiers=2,3 --eval-worlds=8
~~~

Keep the helper's VRAM gate enabled. A pilot does not automatically launch a smoke run, evaluation-only run, or any follow-on training.

The local runtime and fallback guard both use the project-wide 100,000,000,000-byte hard limit and 80,000,000,000-byte steady-state target. Registered shared dependency roots are counted by physical inode where the platform exposes that information.

## Current measured status

The full local suite passes. One-step CPU smoke runs prove the differentiable write/read path, nonzero writer and encoder gradients, W-only causal influence, and bit-identical save/restart. They do not prove learned task performance: the one-step quality result is expectedly 0% exact match. A one-step PC-R run also completes its controls with W exactly zero but does not meet the 95% quality gate. Longer bounded training is the next measurement.
