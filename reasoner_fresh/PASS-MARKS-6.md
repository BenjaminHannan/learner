# Headline confirmation on a fresh new-STRUCTURE eval (EVAL-FORM-v2), marks fixed before training (2026-10-03, full sealed process)

Eval: 96 matched ADD/SUB pairs (192 questions), written by one subagent (templates_eval2.json), checked by an independent subagent
(EVAL2-CHECK-REPORT.md), sealed by hash (SEAL-v2.json) before any training. Six story structures never shown in training: question first, distractor
sentence, table layout, quoted dialogue, future tense with scene-setting, distance/units. Cells: answers unseen (48 pairs) / seen (48 pairs).
Scored ONCE per run, on this form only. The v1 eval is not used for these runs.

Arms (6 seeds each, 0-5, 3000 x 16 updates, lr 1e-3, copy path in both, call at loop 0):
 - COPY-ONLY: never-repeating stream, old 4 training templates.
 - COMBINED: never-repeating stream, half old templates + half procedurally composed frames (gen2.py).
Training streams exclude the operand pairs of v1 and v2, and use only train answers.

HEADLINE: right-call rate on all 192 v2 questions, per seed; paired gain = COMBINED minus COPY-ONLY on the same seed.
CONFIRMED: paired mean gain >= +8 points AND the 95% t-interval (n=6, t=2.571) lower bound > 0 AND COMBINED right-call mean >= 80%.
NOT CONFIRMED (falsified): paired mean gain < +3 points.
Between: anything else; partial, no claim.
Reported with no mark: final accuracy overall and on unseen answers; share of wrong unseen answers equal to a training answer;
per-family right-call rate; seed spread. Rows copied back and counted (192 x 12 = 2304) before boxes are destroyed.
Known limit: both arms still have the same train-time structure (two plain quantities); this tests wording-structure generalisation only.
