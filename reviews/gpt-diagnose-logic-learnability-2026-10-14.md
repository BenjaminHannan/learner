# Prompt for GPT (web): why does a 3M model not learn a simple text-lookup puzzle? (standalone; you cannot see the repo)

You are advising on a small machine-learning experiment. Please give an outside opinion on a diagnosis. Do not suggest edits you
cannot justify from the facts below, and do not assume facts I have not given. This is the SMALL-MODEL experiment only; do not reason
about any other model or project I might have (a separate "village model" exists and is out of scope).

## What the model is
T1SDR: 3,314,132 parameters, character-level (95 printable ASCII characters, prompts up to 208 characters). A reader of 2 convolution
blocks (kernel 5, so about +-4 characters of reach, 256 channels, learned position table of 208 rows), then a looped "thinker"
(8 control tokens + 9 register tokens, 8 loops of attention over the reader features), then a "talker" with three answer modes:
NUM (a number from a calculator tool), WORD (a pointer over the words of the prompt: softmax over all words, up to 64 words) and GEN
(letters). It was trained on a 200,000-row curriculum of 34 skills (arithmetic word problems, syllogisms, kinship chains, ordering
chains, true/false property evaluation, ...) and scores about 90% in-distribution; that curriculum has no "unknown" answers and
only 2.5% true/false-word rows. Optimiser AdamW, constant lr 1e-4 after 100 warm-up steps, batch 64, gradient clipping at 1.0.

## The task I tried to add
Program-checked deductive logic puzzles, answer true / false / unknown, e.g.
"Heidi is not empty when Heidi is pifflo. Jill was kind. All kind and mubwug are pifflo. Jill is truly mubwug. A red thing is zorgri.
True or false or unknown: Jill is empty. (unknown/true/false)"  (the three answer words are appended in a per-row random order so
the answer is a word the pointer can copy). Predicates are nonsense words, 149 names, 72 training sentence templates plus 30
held-out templates, depths 0-3 (and 4-5 for testing), labels balanced in thirds. A control ("placebo") uses the same templates at
depth 0: the answer is a lookup of one stated fact, e.g. "... Nate is tepwug, yes. ... Is Nate tepwug? -> true". A text-only solver
that finds the one sentence containing both the query's name and word and reads its polarity (not/never/isn't/surely not/...) scores
98.7-100% on the placebo and the depth-0 puzzles.

## Results (accuracy on held-out puzzles, chance = 33.3%; n = 1,200-1,608 per file, standard error about 1.2 points)
| run | updates | share of logic rows | logic gate (held-out wording) | logic dev (train wording) | placebo dev (depth-0 lookup) |
|---|---|---|---|---|---|
| marked recipe, parent A | 8,000 | 25% | 31.4 | 32.8 | 34.5 |
| marked recipe, parent B | 8,000 | 25% | 37.4 | 36.2 | 33.7 |
| placebo arm, parent A / B | 8,000 | 25% placebo | 32.8 / 35.3 | 33.7 / 34.2 | 33.8 / 32.2 |
| long run, parent C | 5,000 | 94% | 36.8 | 38.3 | 35.9 |
Training loss on the logic rows (the answer-pointer term): 6.9 over the first 100 updates, 1.17 by update 200 (the pointer moves onto the
three option words), then it sits at ln 3 = 1.0986 for ~1,500 updates and falls slowly to about 1.035 at update 3,500 of the long run
(training rows only; held-out stays at ln 3). Held-out gold-vs-shuffled-label pointer-loss gap on logic dev: +0.007 at update 500,
+0.066 at 1,500, +0.134 at 2,500, +0.162 at 3,500 of the long run; about 0 at the 1,000-update checkpoints of the 25% recipe. After
temperature calibration the real information over ln 3 is only about 0.009 nats (gate) / 0.036 nats (dev). The long run's checkpoints
from 1,500 to 3,500 have flat gate accuracy (36.7-38.5%, +-4). The signal appears to be a polarity lean ("is not" -> false, "is" ->
true: negated questions answered "false" 49.6%, positive ones "true" 47.2%), not content use.

## What has been ruled out (shown, each re-derived by a second checker with its own code)
- Gold labels: an independent parser and solver reproduce the label on 100% of 267,608 puzzles; no train/eval duplicates.
- Scorer: oracle = 100%, constant and position predictors exact; saved numbers recompute; decode is 100% WORD mode with >= 99.4% of
  pointer mass on the three option words.
- Row-to-loss path: no unknown characters, no truncation, no loss mask; gradient from logic rows reaches reader, thinker and pointer;
  training-path loss equals scoring-path loss to ~4e-6.
- Data: held-out templates are really unseen; the answer's slot in the option suffix is independent of the label; cheap surface cues
  reach 37-40% (count of negation words + sentence count) and a "dangling fresh predicate word" cue in logic rows (not placebo) reaches
  39-45% by wording-independent lookup.
- Behaviour of the long-run checkpoint: replacing the queried name or predicate with a word absent from the puzzle leaves the answer
  unchanged 86-93% of the time (a content reader would say "unknown" ~100%); deleting the supporting sentence changes the answer no more
  than deleting an irrelevant one; flipping the stated fact flips only 8% of true/false answers; adding two spaces changes 29%.
Geometry fact: the name ends 5-16 characters before the word it is bound to (outside the conv reach); all cross-sentence matching and
nearly all name-word binding must be done by the thinker's attention.

## Questions
1. Rank these explanations for "does not even learn the depth-0 lookup in 5,000-8,000 updates": (a) simply too few updates (the
   signal only starts after ~1,500 updates at 94% logic), (b) the reader/thinker cannot bind name to word across sentences at this
   size, (c) the format is too far from the 200,000-row curriculum (no "unknown", no never/isn't/surely, 175 vs 81 characters,
   randomly ordered option words), (d) optimisation (constant lr 1e-4, clipping at 1.0, near-zero gradient agreement at the plateau),
   (e) the pointer-over-options interface itself. Add any I missed.
2. For the top three, give ONE next experiment each (a single change), with the pass mark fixed in advance and the result that would
   prove the explanation wrong. Keep each run under ~2,000 updates on a CPU. Our planned first rung is a positive control in the same
   format where the answer is stated in the prompt ("Answer: true" in a fact): pass >= 90% held-out accuracy within 500 updates at a 25%
   mix, falsifier < 50% after 2,000 updates. Tell me if that rung is badly designed.
3. What would you read as the first sign of real learning (not the polarity lean) in the numbers above?

## Format of your answer
- Label every claim shown / suggested / untested.
- One change at a time; pass marks fixed before looking at results.
- End with a plain-language summary for a high-school senior (no jargon).
