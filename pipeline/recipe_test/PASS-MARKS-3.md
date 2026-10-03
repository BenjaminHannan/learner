# Round 3: two-step chained calls on the real pipeline, with and without the ordered read. Marks fixed before training (2026-10-03, fast lane)

Base recipe = round-2 recipe (copy path + half composed wording + contextual reader), real modules, fresh weights, 4 loops, predicted calls, 3000 x 16, same optimiser.
Change for the task (both arms): up to 3 literals and the result slots of earlier OK calls are candidates (the real CalculatorPath already allows this); the real
label policy is extended to chains (task calls in order, each repeated until a correct predicted call, then NONE; the second call's refs are the first OK correct result and literal 2);
the copy path uses the latest OK result.
Training: 70% two-step items (x op1 y, then that result op2 z; 3,378 frames: narrative + table / question-first / distance training variants from the stand-in test) + 30% one-step
items (round-2 wording). Never repeating; final answers only in the 60 train answers T of the round-2 split (seed 20261201), intermediates any two-digit value.

Arms (6 paired seeds 0-5, RT_ROUND=2): TWO = base. TWO-O = base + ordered read: each loop reads the question with its own learned attention query (4 x 256, init 0.02 randn)
in place of the mean for the action and pointer heads. Nothing else differs.

## Fresh eval (not used before)
192 new two-step questions, wording authored for this round (`gen_two_r3.py`): 4 structures x 4 op pairs x unseen/seen finals x 6 = 192: narrative, question-first, table layout, distance.
Unseen finals are in the 30 held-out answers H, seen finals in T. New names/nouns from `templates_eval_r2.json`. Operand triples excluded from training. No training frame shares a sentence
or word 6-gram with any eval frame (DISJOINTNESS-TWO-r3.json). Authored by the model that designed the test, not independently checked (fast lane).

## Measures
chain = the two task calls were both executed in order (call 2 uses the right result); final = emitted answer right (first token and EOS); call1; call2 given call1; by structure; second operation ADD/SUB; unseen final.
Gate: TWO train fit (last 192 two-step training items, chain) mean >= 70%, else UNDERFIT-VOID.
## HEADLINE: chain rate on all 192 questions, paired gain TWO-O minus TWO (6 seeds, t = 2.571).
PASS: mean gain >= +15 AND interval lower bound > 0. FAILS: mean gain < +5. Otherwise partial, no claim.
Also reported with no mark: TWO's own level (stand-in prior: V arm 56.5%, VO 70.8% chain), table-layout and question-first chain rates (the weak spots there: 31-48% / 47-59%), seed SD.
Rows for every run copied back and sha-checked before any box is destroyed. Budget cap ~$2.5.

## Addendum (written 22:48 UTC, before the relaunch; no run had finished): the real core refuses questions over 49 tokens (with EOS)
The first launch crashed in 8 of 12 runs when a long training item reached the real core (`ordered_begin`: query cap 49). No run had finished, no result was read. Fix: training items and eval items are
resampled until they fit 49 tokens (`fits` in `gen_two_r3.py`); all 192 eval questions already fit (max 47 tokens), so the eval set is unchanged. Marks above are unchanged.
