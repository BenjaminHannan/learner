# M1 new-names (experiment 21) — Fable coordinator's predictions

Written 2026-09-20 by Fable (coordinator) after the reviewer's rulings 21b and the C1 logging change, and
BEFORE run_data.sh, any registered training or any score. They change no pass mark. The reviewer's own
P1–P14 are in design/v3/21b-new-names-rulings-fable-review.md and are scored separately.

Exposure disclosure: before writing these I saw one builder observation from a 500-update run on FIXTURE
seed 9 (not a registered seed): `code_scale` fell 0.1386 → 0.0128 while `entity_output_bias` rose to +0.299.
I also know the control recipe's history (late start-up around 1,900–2,250 updates; one of three registered
grow-blind seeds weaker than the others).

| # | Statement | Probability |
|---|---|---|
| P94 | Treatment (random re-drawn name codes) passes all marks in 3/3 seeds | 0.25 |
| P95 | Treatment passes in at least 1 seed | 0.55 |
| P96 | Some seed passes on training-pool codes but fails on reserved (never-trained) codes | 0.05 |
| P97 | Control reproduces (passes) in at least 2/3 seeds | 0.80 |
| P98 | Never-started signature in at least 1 treatment seed | 0.40 |
| P99 | Speed-limit flag (code_scale ≥ 0.50 at update 500 or ≥ 0.90 at 1,000) fires in at least 1 treatment seed | 0.10 |
| P100 | `code_scale` at update 500 is BELOW its initial 0.13856 in at least 2/3 treatment seeds | 0.65 |
| P101 | In every passing treatment seed the final code_scale lies in [0.7, 2.5] (not scorable if no seed passes) | 0.40 |
