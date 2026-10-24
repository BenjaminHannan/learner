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

## Addendum 1 (2026-10-24 18:05Z, before any run): the "guessing brain" arm

Ben (18:00Z) asked for the model to predict how a task will go first, with the dopamine coming from doing better
than it predicted. Arm `d_self` adds this. Before each try, the model answers "how likely are you to complete
this task fully? 0-100". With its stated chance p, A = r - p. The prediction tokens are not trained. Everything
else is the same as the other two arms.

- S1 guessing beats plain: d_self >= d_none + 5.
- S2 own guess vs running average: d_self >= d_value + 5 means the stated guess is the better baseline. A
  result within 5 points either way is a tie, and then the cheaper running average wins.
- S3 the guess means something: on the untrained model's held-out run, the correlation between the stated
  chance and success is >= 0.2. If it is lower, the guesses are noise, and a d_self result says nothing about
  self-prediction.
- Proved wrong: d_self <= d_none.

## Addendum 2 (2026-10-24 19:00Z, before any result): batch-mean control arm `d_batch`

Research (`/mnt/project-files/research/dopamine/lit-baselines.md`; REINFORCE++ 2501.03262, SPO 2509.13232) points
to a confound. d_value could beat d_none only because subtracting any average centres the rewards, not because
it carries a per-task-type expectation. `d_batch` uses A = r - mean(r of this step's 16 tries). It is the same
in every other way.
- B1: d_batch >= d_none + 5 means centring alone helps.
- B2: d_value >= d_batch + 5 means the per-type expectation (the dopamine part) adds something beyond centring.
  If d_value - d_batch is under 5, report that d_value's gain is explained by centring.

## Addendum 3 (2026-10-24 19:40Z, before any result): noise

A research note (`/mnt/project-files/research/dopamine-rlaif-grader.md`) points out that two arms on 100 tasks
differ by about 6 points of noise (1 SE) at a 25% success rate. So a gap that meets a +5 mark is at most
"suggested", not "shown". The marks above stay as they are. Also report the paired exact McNemar p-value on
the shared 100 held-out tasks for every comparison. Any mark that passes is then rerun with 3 seeds before
the v2 design adopts it. A mark that passes with p >= 0.1 is described as "within noise".
