# Round 2: contextual reader for the calculator decision. Marks fixed before training (2026-10-03, fast lane)

One change (CTX): the reader (and so the calculator decision and the core) reads the frozen LM's contextual last-layer hidden states for the
question tokens instead of word-by-word lexical embeddings. Everything else is the round-1 RECIPE (copy path + half composed wording, real modules,
3000 x 16, same optimiser). Calculator result tokens still go through the same reader as lexical embeddings. Compared with RECIPE re-run on the
fresh set, paired seeds 0-5. Run with RT_ROUND=2 (`gen.py`).

Why: round 1 found ADD calls on new wording near 0% for three families; suggested cause (untested): context-free input to the call decision.
This keeps to the calculator decision / input boundary; it does not touch the exit (the info-flow thread tests pointer exit / wider entry on the stand-in).

## Fresh held-out set (round 1's 192 questions are used up)
- New answer split, seed 20261201 (60 train answers T, 30 held-out H); eval seed 20261203; stream seeds 7,200,000+seed (old wording) and 8,200,000+seed (composed).
- 6 NEW new-wording families authored for this round (`templates_eval_r2.json`), new names and nouns, disjoint from all training names/nouns; composed training frames
  share 0 sentences and 0 word 6-grams with them (`gen2.disjointness_report()`, saved as DISJOINTNESS-REPORT-r2.json). Same structure as round 1: 96 pairs, cells
  unseen/seen answers x train/new wording, 24 pairs each. Authored by the same model that designed the test, not independently checked (fast lane).

## Measures: as round 1 (final, right-call = any loop made the task call; per-op split also reported).
## Gate: RECIPE train fit (192) mean >= 90% on this set, else UNDERFIT-VOID.
## HEADLINE (paired over 6 seeds, t = 2.571): new-wording right-call rate, CTX minus RECIPE.
- PASS: mean gain >= +8 points AND 95% interval lower bound > 0 AND CTX train-wording right-call mean >= 95% AND CTX unseen-answer final mean not more than 5 points below RECIPE.
- FALSIFIED: mean gain < +3.
- Otherwise: partial, no claim.
Also reported: ADD vs SUB call rates on new wording, final accuracy per cell, seed SD, train fit.
Rows for every run are copied back and sha-checked before any box is destroyed. Budget cap for this round ~$2.
