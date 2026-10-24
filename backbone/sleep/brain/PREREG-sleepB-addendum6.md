# Sleep-B addendum 6: a bigger, fairer test, and the winners combined (written 2026-10-24 ~21:15Z, before any addendum-6 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), tests and scoring code as addenda 1-5, open-book rehearsal, and
training seed 1. Not the village model, not the card experiments.

## Why
Addenda 4 and 5 (seed 1 on Week-1; recall from weights only on C2+C4, 80 facts; control 56):

| arm | recall | ARC-Easy | diary pooled |
|---|---|---|---|
| ab_ob control | 56 | 92.4 | 82 |
| 2x night work (ab_ob_b2) | 66.5 | 92.0 | 83 |
| guess + dopamine (ab_ob_guess) | 64 | 92.4 | 84 |
| twisted dreams (ab_ob_twist) | 62.5 | 93.2 | 84 |

With 80 facts, an unpaired arm-to-arm gap has a noise of about 7 points (suggested; an outside check via another thread). So each
gain is only 1 to 1.5 noise widths. The result JSONs, and with them the per-question answers, were never recovered, so a paired
test was not possible. The twist arm also added 2 texts per item, so its gain may come from extra text, not from the twist.

## World: Week-2
- The same generator (`week.py`) and rules as Week-1, with a new plan seed (2) and about 2.5x the recurring facts: about 100
  facts each in C2 and C4 (200 recall questions), about 60 in C1, about 30 changing facts and about 20 routines. Chains scale to
  match. Written by the Claude API with a cost cap of $8.
- Week-2 is written and checked before any arm runs on it. Its counts and sha256 are recorded in RESULTS before the runs.
- No step schedule is carried over from Week-1. Every arm uses the code's own formula (min(300, 40 + 4 x active items) steps a
  night) times its work scale s.

## Arms (training seed 1, all on Week-2)
- **ab_ob (control, s = 1).**
- **ab_ob_b2 (s = 2):** repeats addendum 5 on a new world.
- **ab_ob_win, "the winners combined":** s = 2, plus guess + dopamine priority, plus twisted dreams. Each part is exactly as in
  addenda 4 and 5.
- **ab_ob_winp, "the winners, plain extra texts":** ab_ob_win, except that each kept twisted scene is replaced by a plain
  paraphrase. These come from the same extra generation call, asking for 2 more ordinary paraphrases, with the same checks and
  the same count kept. This isolates the twist.

## Scoring
- All arms answer the same questions, so arms are compared question by question.
- Primary measure: recall from weights only on the C2+C4 forward questions (about 200).
- Paired test: exact McNemar (two-sided) on the questions where the two arms disagree.
- A gain is **shown** if it is at least 5 points with p < 0.05. It is **suggested** if it is at least 5 points with p >= 0.05.
- The per-question answers must be recovered: the box is stopped, the result JSON is pulled with `vast.py cat` once the box
  shows as stopped, and only then is the box destroyed. If a JSON cannot be pulled, that comparison uses unpaired numbers and is
  labelled suggested.

## Pass marks (fixed now)
- **No harm (every arm):** ARC-Easy >= 87.6, and diary pooled >= control - 5.
- **W1 (more work helps, replication):** ab_ob_b2 - control >= +5, shown by the paired test.
- **W2 (the combination adds on top):** ab_ob_win - ab_ob_b2 >= +4. This is reported with its p-value and called shown only if
  p < 0.05.
- **W3 (the twist itself helps):** ab_ob_win - ab_ob_winp >= +4, with the same rule.
- **Wrong if:**
  - ab_ob_b2 <= control. Then the addendum-5 gain did not replicate.
  - ab_ob_win < ab_ob_b2 - 4. Then guess and twist hurt when combined with 2x work.
- **Reported, not marked:** two-hop, changed-new, routine, gate reverts per night, wall time, and the share of questions on
  which each pair of arms disagrees.

## Compute
- Vast A100 40GB boxes, one arm per box. A box is never used in California, where boxes failed to start twice.
- The cap is set with the coordinator after the weekly credit reset. Ben's PC is used if it is free.
- Each box is stopped, its result pulled and then destroyed. A box whose job has not started within 20 minutes, or that has not
  finished a night within 36 minutes, is destroyed.
