# Dopamine-1: can the deployed model learn from one try per task?

Ben (2026-10-24 17:53Z): "Is there a way to include dopamine into our model after it's deployed?"

## Why this is the test

Dopamine is a reward prediction error: delta = (what happened) - (what I expected). In RL terms that is the
advantage, and GRPO already computes one: reward minus the mean of 4 tries at the same task. After deployment
there are no 4 tries. Ben asks for something once, the assistant does it once, and it gets one outcome. So the
deployed model needs its own expectation, a learned value V, to turn a single outcome into a surprise.
Dopamine-1 asks whether that learned expectation is what makes single-try learning work.

## Design (one change only)

Same code, model, tasks, seed, steps, lr and rollouts in both arms. Only the baseline differs.

- Model: Qwen/Qwen3-1.7B, thinking off, LoRA r=32 (the RLAIF-1 setup, `rlaif/train.py`).
- Tasks: `rlaif/data/tasks_train.jsonl` (320) for learning, `tasks_heldout.jsonl` (100) for scoring.
- Deployment-like: G=1 (one try per task), 20 steps x 16 tasks = 320 tries.
- Reward: end-state checks only, `--reward checks` (fraction of checks passed). No Claude grader, so no API
  cost and no grader to game. This is the "did the task actually get done" reward that exists in daily use.
- Arm `d_none`: A = r (plain REINFORCE; "good outcome = do more of that").
- Arm `d_value` (dopamine): A = r - V[scenario], with V[scenario] a running average updated
  V += 0.1 * (r - V) after each try, starting at 0.5. Scenario = the task type label
  (single_tool, multi_step, clarify, ...). Deployed, a router would supply this label.
- lr 1e-5, max_new 384, max_total 2048, seed 0. One seed (noted as a limit below).

Commands:

    python -m rlaif.train --reward checks --baseline none  --group 1 --tasks-per-step 16 --steps 20 --outdir runs/d_none
    python -m rlaif.train --reward checks --baseline value --group 1 --tasks-per-step 16 --steps 20 --outdir runs/d_value
    python -m rlaif.train --eval-only --adapter runs/d_none/adapter_final  --outdir runs/d_none
    python -m rlaif.train --eval-only --adapter runs/d_value/adapter_final --outdir runs/d_value
    python -m rlaif.train --eval-only --outdir runs/base

## Pass marks (fixed 2026-10-24 before any run)

Held-out = 100 tasks, check-only success (all checks pass), greedy. Untrained reference: measured in the same
job (RLAIF-1 measured 25/100).

- P1 dopamine helps: d_value >= d_none + 5 points.
- P2 dopamine learns at all: d_value >= base + 5 points.
- P3 the expectation is real: mean |delta| over steps 16-20 is lower than over steps 1-5 in d_value.
- Proved wrong: d_value <= d_none. Then the learned expectation does not matter at this scale and the
  deployed design should not depend on it.
- Harm alarm: either arm below base by >= 5 points.

Gaps under 5 points are a tie (100 tasks gives about +-4.5 points of noise at 25%). One seed; a pass gets a
second seed before it changes the v2 design.

## What it does not test

The other two dopamine jobs (steering what sleep replays, and explore-vs-routine in the creative loop),
DPO from Ben's corrections, and the LFM2.5 backbone. Those come after, one at a time.
