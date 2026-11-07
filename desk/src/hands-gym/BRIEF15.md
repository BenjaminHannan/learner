# Brief 15: frozen-policy length check

This is a synthetic HANDS gym policy test, not Glim or the Mac app. No training,
optimizer, recording, production service, or source checkpoint is changed.

The optional `variant` argument to `tasks.build` and `BrowserEnv.reset` accepts
`letters_6` / `letters_10` for typing and `fields_5` for forms. Omit it for the
unchanged three-letter/two-field tasks. No variants enter `TASK_TYPES`, training,
the default evaluator, or reverse-start curricula. Variants reject `start_k`.
Five fields retain the existing label/input styles in a two-column card so all
fields and Submit fit inside the existing 640×360 viewport without scrolling.

`python -m hands_gym.length_check pilot --checkpoints <brief7/control> --output
<new-scratch-output> --gpu-root <shared-hands-gym-root>` verifies all three final
12,800-step CONTROL checkpoints against the brief-7 report. It runs eight
timing-only episodes per cell for seed 11. The conservative full-wave estimate
is 1.5 × pilot elapsed seconds × 100/8 × 3. Stop if it exceeds 7,200 seconds.
The incomplete pilot is not a verdict or part of the scored sample.

`wave` with the same arguments requires that pilot gate, then measures 100 fresh
episodes per cell for each checkpoint seed 11, 22, 33. Seeds are
80,000,000 + checkpoint_seed × 10,000 + episode_index, disjoint from brief-7
training and evaluation. Corresponding lengths share layout seeds and reset
the stochastic action RNG to checkpoint_seed + 15,000. Horizons are 20, 40,
60 for 3/6/10 letters and 20, 60 for 2/5 fields. Apply the fixed stop rule
after each completed baseline; do not select checkpoints or variants using
intermediate outcomes. The pilot overlap is excluded by rerunning the
complete 100-episode cell; no pilot episodes are added to its denominator.
After each completed baseline cell, stop immediately if its denominator is
unmeasurable. Later cells/seeds are UNMEASURED, never zero-filled.

The fixed comparisons are 10 versus 3 letters, and 5 versus 2 fields:
long success ≥ 0.8 × short success means NO WALL; ≤ 0.5 means WALL; otherwise
PARTIAL. A short-task baseline below 10/100 is UNMEASURABLE, not NO WALL at
0/0. This operationalizes Ben's low-baseline instruction before measurement.
On an unmeasurable mark, report and stop before another cell: no secondary arm, checkpoint swap,
training, or new mark. Raw counts remain observations, not evidence for WALL.

Longer words are unseen tokens and five-field layouts/instructions are new.
The experiment cannot identify counting memory as the cause of any drop.
The gym GRU is reset on every action, unlike the persistent toy-policy GRU.
