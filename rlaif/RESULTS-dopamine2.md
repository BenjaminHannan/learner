# Dopamine-2 results (2026-10-25, PC bf16, lr 1e-4, one seed, code 92471e270)

Raw files: branch claude/dopamine2-pc-results (dopamine2-pc/).

| arm | held-out success | train reward, steps 1-5 -> 16-20 | single-turn share in training | gen tokens/step | held-out tool tasks answered in one turn |
|---|---|---|---|---|---|
| base (Dopamine-1) | 25 | - | - | - | 26 |
| d_none | 14 | 0.358 -> 0.335 | 0.44 -> 0.58 | 2,351 -> 5,476 | 45 |
| d_value | 7 | 0.315 -> 0.233 | 0.14 -> 0.00 | 4,047 -> 5,770 | 0 |

## Verdicts against PREREG-dopamine2.md

- Q1 (learning moves): FAIL. Neither arm's training reward rose, and both fell.
- Harm alarm (either arm <= 20): FIRED for both. lr 1e-4 breaks the model.
- Shortcut alarm (>= 41 one-turn answers on tool tasks): FIRED for d_none (45). d_value broke the other way:
  it never stopped after one turn and produced the longest outputs, so it ran on to the turn limit.
- Q2 (d_value >= d_none + 5): FAIL (7 vs 14).

## Conclusion (what the prereg said to do)

Single-try RL from check rewards does not learn at this scale. lr 1e-5 doesn't move the model and lr 1e-4 breaks
it. With a per-type dopamine baseline, it gets worse at both rates. So, as preregistered, v2's nightly update moves
to correction pairs (DPO/KTO, see /mnt/project-files/research/dopamine/lit-user-feedback.md). Surprise
(reward - expected) stays useful as a SIGNAL (what to replay, which task types are stuck), not as an RL baseline.
This is untested beyond these two runs on one seed.
