# Brief 15b: opt-in design-equivalent typing

`--design-typing` on `hands_gym.train` defaults off. For `type_text` and
`form_fill` only, each printable-key action gates emission of the next character
from the typing target's plain-code text reference, at `text[textIndex:textIndex+1]`.
For a form, the reference belongs to the currently focused field.
As in `desk/tools/hands-toy/policy.py`, the network does not choose character
identity. The existing key head's printable categories are equivalent emission
gates; Enter/Tab/Backspace/Escape retain their original meanings. No automatic
focus, field advance, submission, prefix repair, or completion oracle is added.
Emission without input focus has no effect; an exhausted reference is a no-op.

The observation includes a twelve-element `own` vector for these two families:
slots 2/3 are `textIndex/20` and `textLength/20`, matching the toy;
other slots remain zero. The index is the actual string length, not its correct
prefix. No target characters, field coordinates or IDs enter the network.
Other families and default-off observations/actions remain unchanged.
Task generation, rewards, action space, architecture, parameter count, PPO
settings, and GRU hidden-state handling are unchanged. Remote workers reject
the flag rather than silently running the old behavior.

The GRU still resets on every action. This is a separate finding, not fixed here.
This synthetic gym change is not validation of the production Mac app.

Frozen CONTROL: seeds 11/22/33; 200 updates × 8 environments × 8 rollout steps;
20-action horizons, nine uniform task families, normal starts, no imitation;
same brief-7 PPO and 16-episode/family held-out evaluation. Only the flag differs.
Length measurement reuses brief-15 `CELLS`, `measure`, `task_seed`, and `verdict`:
100 held-out episodes/cell; horizons 20/40/60 letters, 20/60 fields.
Below-10/100 baselines are UNMEASURABLE; do not run their longer cells.
Continue independent baselines/seeds because the fixed fix-work mark needs all
three short-word scores. Do not manufacture zeroes for skipped cells.

Fix works: >=30/100 three-letter successes on at least two seeds; proves it
wrong: <10/100 on at least two; otherwise PARTIAL. Length thresholds stay
>=0.8× NO WALL, <=0.5× WALL, otherwise PARTIAL, per seed. Non-regression is
report-only against the hash-verified brief-7 CONTROL held-out results.
