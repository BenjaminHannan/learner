# Optional reverse curriculum

`tasks.build(kind, seed, start_k=None)` preserves every existing normal start
by default. `BrowserEnv.reset` accepts the same optional argument. Positive k
leaves only the last k task-progress units undone. No initializer solves the
task, changes its instruction/target/reward, or supplies inputs to the policy.

Text progress is focus, individual characters, submit. Form progress is
focus/name characters, focus/city characters, submit. Dropdown and menu progress
is open, select. Slider progress is ten percentage points along its original
start-to-target path; the existing native drag action remains atomic. A slider
near-start remains ten points outside the target with `dragged=false`. k at or
beyond the total yields identical normal HTML; single-step families never change.

`--start-k 1` enables independent training-only stages for the five multi-step
families. Every twenty current-stage completions form a non-overlapping window.
Strictly more than 70% success advances that family by exactly one unit. Old
in-flight completions cannot promote a newer stage. Full recovery checkpoints
preserve stage outcomes and each live task's original k.

`--task-families` optionally selects a uniform training mixture and the same
held-out evaluation families. Omitting it preserves the original popup-heavy
seven-family harness. Evaluation never uses reverse starts, including when
`--start-k` is enabled. Remote environments do not support this option yet and
are rejected when reverse starts are requested.

The frozen brief-7 harness uses nine uniform families in both arms, three seeds,
12,800 training steps, twenty-step episode horizons, sixteen normal-start held-out
episodes per family at baseline and budget end, and self-imitation OFF. It uses
the existing trainer, evaluator, GPU lease and atomic recovery mechanism.

On BensPC, from the deployment root:

```powershell
.\venv\Scripts\python.exe -u brief7.py pilot
.\venv\Scripts\python.exe -u brief7.py wave
```

Run the pilot first. The wave command refuses a failed time gate (nine times
pilot active wall time, excluding GPU waits, must be at most 7,200 seconds).
Each run takes its own existing `gpu_gate` lease. Busy admission waits and
foreign-client yields are recorded separately; no other process or lease is
removed. Repeating a command resumes its own incomplete run, never overwrites
completed results, and refuses a changed source manifest. A deployment manifest
and the frozen preregistration must exist under `runs/brief7/` before execution.
If a reboot leaves a stale lease, its owner must reconcile it manually.

Tests: run `hands-gym-curriculum.test.py`, `hands-gym.test.py`, and
`hands-gym-resume.test.py` directly from `desk/test`. Set
`HANDS_GYM_BROWSER_TESTS=1` for real Chromium checks. Browser oracle actions are
test-only and never become training trajectories or policy inputs.
