HELD-UNTIL: scripts/claude_dir_lr_stage_net.py, scripts/claude_dir_lr_stage_report.py and artifacts/claude-dir-lr-20260928/STAGE-PASSMARKS.md are on origin/main; runs/qual-{loop,plain}-s{0,1}/source.pt are on the run machine.
GPU: no
LOAD-HEAVY: yes (8 dev runs, like the baseline's 169 min loop / 120 min plain when 8 run at once; staged runs skip body gradients for the first quarter, so likely a bit faster; run 4 at once with JOBS=4 if cores are short. Estimate, untested.)
WHAT: Lead 1, staged unfreeze at adaptation (head and stop head only for the first 512 of 2,048 updates, then everything), same rule for fresh, plain, practised. Dev only. Sealed eq harness through --plugin; resumable is not built in for a rung, so rerun a run only after deleting its half-written folder.
SETUP: torch==2.14.0 CPU, fp32. Clone origin/main; source nets in artifacts/claude-fewex-20260927/runs/qual-*/.
RUN (repo root): 
  for arm in loop plain; do for seed in 0 1; do for init in pre fresh; do
    python -B scripts/claude_fewex_eq_bench.py adapt --arm $arm --seed $seed --init $init --plugin claude_dir_lr_stage_net --out artifacts/claude-dir-lr-20260928/stage-runs/$arm-s$seed-$init > artifacts/claude-dir-lr-20260928/stage-$arm-s$seed-$init.log 2>&1 &
  done; done; done; wait
(8 processes at once; or split into two waves of 4.) Watch the logs for Traceback.
AFTER: `python3 -B scripts/claude_dir_lr_stage_report.py dev` prints the deltas and the STAGE-PASSMARKS.md verdict. Commit adapt.json files and logs (git add -f; NOT the .pt files) before anything else. Holdout only if the verdict is PROMOTE, once per arm and seed (`claude_fewex_eq_bench.py holdout ... --plugin claude_dir_lr_stage_net --out <same folder>`; needs the k*.pt files kept), then `report holdout`.
NOT THIS JOB: any change to the recipe or the marks after a dev score is seen; the blind recount (Director's call).
