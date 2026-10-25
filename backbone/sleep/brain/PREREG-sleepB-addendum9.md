# Sleep-B addendum 9: combine the winners and test them on two seeds (written 2026-10-25 ~08:40Z, before any addendum-9 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), Week-2 world (sha256 70db7146...), tests, scoring and code
version as addendum 8 (PR #114 trainer), open-book rehearsal. Not the village model, not the card experiments.

## Why
Addendum 8 (Week-2, recall from weights only on 200 C2+C4 forward questions, paired McNemar):
- Re-reading the day for names at 4x work (ab_ob_b4_names, seed 1): recall 88.0 vs 76.0 for 4x work, p = 0.0007. That is shown,
  but on one seed. Two-hop fell to 1.3 (3 of 78 two-hop questions had a kept chain dream).
- Guided two-step dreams at 4x work (ab_ob_b4_bridge, seed 1): two-hop 28.2 vs 5.1, p = 0.0001 (27 of 78 dreamed), recall 77.0.
  That is shown, on one seed.
- 4x work beat 2x on seed 2 (76.5 vs 64.0, p < 0.0001), and 4x matched itself across seeds (76.0 vs 76.5, p = 1.0).
The two fixes touch different parts of the night: names adds items during the day pass, and the bridge prompt changes how REM
writes chain dreams. Nobody has run them together, and each has only one seed.

## References
- Seed 1: ab_ob_b4_names (`results_a8/result_ab_ob_b4_names.json`).
- Seed 2: ab_ob_b4 (`results_a8/result_ab_ob_b4_s2.json`) for R1, and this addendum's ab_ob_b4_names seed 2 for K2 and K3.
The new arm only adds a code path. Every existing arm stays bit-identical, which is checked by the selftest and a CPU smoke, so
the addendum-8 runs are valid paired references.

## Arms (Week-2, work scale 4, training seeds as listed)
- **ab_ob_b4_nb, "names + guided two-step dreams" (seeds 1 and 2):** ab_ob_b4_names's re-read pass after the day tagging, and
  ab_ob_b4_bridge's bridge prompt in REM (start, answer and middle name given). Both are the addendum-8 code paths, unchanged.
  Nothing else changes.
- **ab_ob_b4_names, seed 2:** the addendum-8 names arm repeated with training seed 2.

## Scoring
Paired, exact two-sided McNemar on per-question rows (`paired.py`). A gain is **shown** if it reaches its mark with p < 0.05,
and **suggested** if it reaches the mark with p >= 0.05. If a JSON cannot be pulled, that arm is unpaired and at most
suggested; the box is kept stopped and the pull retried first.

## Pass marks (fixed now)
- **No harm (every arm):** ARC-Easy >= 87.6, and diary pooled >= reference - 5.
- **R1 (names replicates on seed 2):** seed-2 names - seed-2 b4 >= +4 on C2+C4 recall. **Wrong if** it is <= 0.
- **M1 (mechanism, each seed):** ab_ob_b4_nb covers >= 20 of the 78 two-hop questions with a kept chain dream (names seed 1: 3).
- **K1 (two-step dreams add two-hop on top of names, seed 1):** nb - names >= +10 on two-hop (78 questions, paired).
  **Wrong if** M1 passes on seed 1 but the gain is below +5.
- **K2 (the same on seed 2):** seed-2 nb - seed-2 names >= +10 on two-hop.
- **K3 (combining keeps the recall gain, each seed):** nb - names >= -3 on C2+C4 recall. **Wrong if** nb is lower by more than 3
  with p < 0.05 on either seed: then the two fixes interfere.
- **Adopt:** if R1, K1, K2 and K3 all pass, ab_ob_b4_nb becomes the recipe carried to the next step (the LFM2.5 port).
- **Reported, not marked:** reverse, changed-new, routine, eligibility by class, the names pass's counts, chain pairs kept, nb vs
  b4_bridge on two-hop (seed 1), nb vs the Week-2 control, reverts, wall time and dollars.
- **Expectation (not a mark):** recall 85-90 and two-hop 20-35 for nb on both seeds.

## Compute
- RTX 5090 boxes on hosts that already ran these jobs cleanly (Slovakia machine 141056, Portugal machine 152963, South Korea).
  Otherwise the best TFLOPS per dollar with >= 24 GB (`tools/vast_pick.py`), never China or California, plus Ben's PC if it is free.
- A box that is not running within 10 minutes is dropped. Each JSON is pulled after the self-stop, and only then is the box
  destroyed. A box the host keeps "running" after the stop is waited out, not destroyed with its JSON.
- Expected: about 1.3 h per arm on a 5090, so about $2.20 for the three arms.
