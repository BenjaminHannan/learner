# Sleep-B addendum 10: four tries per two-step dream (written 2026-10-25 ~13:00Z, before any addendum-10 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), Week-2 world (sha256 70db7146...), tests, scoring and code
version as addendum 9, open-book rehearsal. Not the village model, not the card experiments.

## Why
Addendum 9 adopted ab_ob_b4_nb (4x work + names re-read + guided two-step dreams): recall 91.5 / 91.0 and two-hop 38.5 / 35.9
on seeds 1 / 2. CPU analysis of its result JSONs (shown, from the logs):
- 70 of the 78 two-hop questions have both facts as eligible items that share a name REM can pair. Only 32 (seed 1) and 28
  (seed 2) of them got a kept chain dream.
- REM already tries the pairs with the fewest kept dreams first, and there are fewer pairs (about 270 by night 7) than tries
  (up to 480 chain prompts per night at 4x). So pairs are not left untried. The limit is the yield of each try: 87 of 2,040 chain
  prompts were kept on seed 1 (4%). In the raw samples the 2B writer mostly asks a one-step question about one fact, which the
  two-step check drops.
- Across every Week-2 run, two-hop correct is close to the number of two-hop pairs dreamed (suggested: the per-question
  dreamed flag was not logged, so the link is across runs, not question by question).

## Reference
ab_ob_b4_nb, seeds 1 and 2 (`results_a9/result_ab_ob_b4_nb.json`, `results_a9/result_ab_ob_b4_nb_s2.json`). The new arm only
adds a code path. Every existing arm stays bit-identical in behaviour, which is checked by the selftest and a CPU smoke. The one
output change for every arm is a new diagnostics field: the per-question dreamed flag for the 78 two-hop questions.

## Arm (Week-2, work scale 4, seeds 1 and 2)
- **ab_ob_b4_nb_x4, "four tries per two-step dream":** ab_ob_b4_nb, except that in each REM cycle every chain prompt is sampled
  4 times instead of once. Every sample goes through the unchanged parse, two-step, leak and diary-verification checks. Per
  pair per cycle, at most one sample is kept: the first one, in sample order, that passes every check. So each pair keeps at
  most one new dream per cycle, as before; only its chance of getting one rises. Gist dreams, pair choice and everything else
  are unchanged.

## Scoring
Paired, exact two-sided McNemar on per-question rows (`paired.py`). A gain is **shown** if it reaches its mark with p < 0.05,
and **suggested** if it reaches the mark with p >= 0.05. If a JSON cannot be pulled, that arm is unpaired and at most
suggested; the box is kept stopped and the pull retried first.

## Pass marks (fixed now)
- **No harm (each seed):** ARC-Easy >= 87.6, and diary pooled >= reference - 5.
- **X1 (mechanism, each seed):** at least 45 of the 78 two-hop questions have a kept chain dream (nb: 32 and 28).
- **X2 (more tries teach more two-step answers):** x4 - nb >= +8 on two-hop (78 questions, paired) on seed 1 and on seed 2.
  **Wrong if** X1 passes on a seed but that seed's two-hop gain is below +3: then dream coverage is not what limits two-hop.
- **X3 (no recall cost, each seed):** x4 - nb >= -3 on C2+C4 recall.
- **X4 (the coverage claim, within each x4 run):** two-hop accuracy on dreamed questions minus accuracy on not-dreamed questions
  >= +30 points. Reported with Fisher's exact test.
- **Adopt** x4 into the recipe if X2 passes on both seeds and X3 passes on both.
- **Reported, not marked:** chain yield per night (kept / prompts), parse failures, reverse, changed-new, routine, chain pairs
  kept, wall time and dollars.
- **Expectation (not a mark):** dreamed 45-60 of 78, two-hop 50-65 on both seeds.

## Compute
- A Week-2 4x arm takes about 1.1 h on an RTX 5090. On a Kaggle T4 it would take about 11-12 h (a Week-1 2x run took 4.6 h
  there), would need fp16 and a 1024-token budget instead of bf16 and 2048, and so would need its own same-hardware reference:
  about 24 of Kaggle's 30 GPU-hours per week for one comparison.
- So: two RTX 5090 boxes on proven hosts (Slovakia machine 141056, South Korea host 406325), about $1.20 for both seeds, if the
  coordinator approves the rental under this week's $30 cap. Otherwise Ben's PC (RTX 5070 Ti) when it is free, with GPU
  differences treated like seed noise as in addendum 6 (a rerun on a different GPU matched, p = 1.0).
- A box that is not running within 10 minutes is dropped. Each JSON is pulled after the self-stop, and only then is the box
  destroyed.
